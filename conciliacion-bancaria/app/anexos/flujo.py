"""Flujo de revisión y aprobación, permisos, documentación sustentatoria y protección de datos personales."""
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.anexos.generador import auditar, configuracion
from app.compensacion.servicio import rol_de
from app.core import config
from app.models import (AdjuntoAnexo, Anexo, AprobacionAnexo, AsignacionAnexo, ComentarioAnexo, ConfiguracionAnexos,
                        HallazgoAnexo, RevisionAnexo, VersionAnexo)
from app.models.anexos import CATEGORIAS_ADJUNTO

TODOS = {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA", "AUDITOR", "CONSULTA", "TESORERO", "PLANILLAS"}
PERMISOS = {
    "consultar": TODOS, "exportar": TODOS,
    "generar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA"},
    "elaborar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA"},
    "adjuntar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA"},
    "revisar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "AUDITOR"},
    "comentar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA", "AUDITOR"},
    "aprobar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR"},
    "cerrar": {"ADMINISTRADOR", "SUPERVISOR"}, "reabrir": {"ADMINISTRADOR", "SUPERVISOR"},
    "plantillas": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR"}, "autorizar_plantillas": {"ADMINISTRADOR", "SUPERVISOR"},
    "asignar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR"}, "configurar": {"ADMINISTRADOR", "SUPERVISOR"},
    "datos_personales": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR"},
    "registros": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA"},
}
# transición → (acción de permiso, estados de origen)
TRANSICIONES = {
    "EN_ELABORACION": ("elaborar", {"GENERADO", "REABIERTO", "OBSERVADO"}),
    "EN_REVISION": ("elaborar", {"GENERADO", "EN_ELABORACION", "SUBSANADO", "REABIERTO"}),
    "OBSERVADO": ("revisar", {"EN_REVISION", "SUBSANADO", "REVISADO"}),
    "SUBSANADO": ("elaborar", {"OBSERVADO"}),
    "REVISADO": ("revisar", {"EN_REVISION", "SUBSANADO"}),
    "APROBADO": ("aprobar", {"REVISADO"}),
    "CERRADO": ("cerrar", {"APROBADO"}),
    "REABIERTO": ("reabrir", {"APROBADO", "CERRADO"}),
}
EDITABLES = ("conclusion", "acciones_correctivas", "responsable_elaboracion", "responsable_revision", "responsable_aprobacion", "fecha_limite")
MAX_ADJUNTO = 20 * 1024 * 1024
EXT_PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".csv", ".txt", ".docx", ".doc", ".xml", ".zip"}


class SinPermiso(Exception):
    status = 403


class ErrorFlujo(Exception):
    status = 422


class Conflicto(Exception):
    status = 409


def rol(db: Session, empresa_id: int, usuario: str) -> tuple[str | None, bool]:
    return rol_de(db, empresa_id, usuario)


def puede(db: Session, empresa_id: int, usuario: str, accion: str) -> bool:
    r, _ = rol(db, empresa_id, usuario)
    return r in PERMISOS[accion]


def exigir(db: Session, empresa_id: int, usuario: str, accion: str) -> str:
    r, _ = rol(db, empresa_id, usuario)
    if r not in PERMISOS[accion]:
        raise SinPermiso(f"El usuario «{usuario}» ({r or 'sin rol en la empresa'}) no puede {accion.replace('_', ' ')} anexos.")
    return r


def cuentas_permitidas(db: Session, empresa_id: int, usuario: str) -> list[str] | None:
    """None = todas. Con asignaciones de tipo ACCESO, el usuario (salvo administrador/supervisor) solo ve esas cuentas."""
    r, _ = rol(db, empresa_id, usuario)
    if r in ("ADMINISTRADOR", "SUPERVISOR"):
        return None
    acc = db.scalars(select(AsignacionAnexo.cuenta).where(AsignacionAnexo.empresa_id == empresa_id, AsignacionAnexo.tipo == "ACCESO",
                                                          AsignacionAnexo.activa.is_(True), AsignacionAnexo.usuario == usuario)).all()
    return [a for a in acc if a] or None


def exigir_cuenta(db: Session, empresa_id: int, usuario: str, cuenta: str) -> None:
    perm = cuentas_permitidas(db, empresa_id, usuario)
    if perm is not None and not any(cuenta.startswith(p) or p.startswith(cuenta) for p in perm):
        raise SinPermiso(f"El usuario «{usuario}» no tiene acceso a la cuenta {cuenta}.")


def _cargar(db: Session, empresa_id: int, anexo_id: int) -> Anexo:
    a = db.get(Anexo, anexo_id)
    if not a or a.empresa_id != empresa_id:
        raise LookupError("Anexo no encontrado")
    return a


def _lock(db: Session, a: Anexo, lock_version: int | None):
    """Control de concurrencia optimista: el cliente envía la versión que vio."""
    if lock_version is None:
        return
    r = db.execute(update(Anexo).where(Anexo.id == a.id, Anexo.lock_version == lock_version).values(lock_version=lock_version + 1))
    if r.rowcount != 1:
        db.rollback()
        raise Conflicto("El anexo fue modificado por otro usuario. Actualice la pantalla y vuelva a intentarlo.")
    db.refresh(a)


def cambiar_estado(db: Session, empresa_id: int, anexo_id: int, usuario: str, nuevo: str, comentario: str | None,
                   lock_version: int | None = None) -> Anexo:
    a = _cargar(db, empresa_id, anexo_id)
    if nuevo not in TRANSICIONES:
        raise ErrorFlujo(f"Estado no válido: {nuevo}")
    accion, origenes = TRANSICIONES[nuevo]
    r = exigir(db, empresa_id, usuario, accion)
    exigir_cuenta(db, empresa_id, usuario, a.cuenta)
    if a.estado_revision not in origenes:
        raise ErrorFlujo(f"No se puede pasar de {a.estado_revision} a {nuevo}.")
    if not a.version_id:
        raise ErrorFlujo("El anexo no tiene versiones generadas.")
    comentario = (comentario or "").strip() or None
    if nuevo in ("OBSERVADO", "REABIERTO") and (not comentario or len(comentario) < 10):
        raise ErrorFlujo("Indique el motivo (mínimo 10 caracteres).")
    pol = configuracion(db, empresa_id)
    _lock(db, a, lock_version)
    v = db.get(VersionAnexo, a.version_id)
    ahora = datetime.now()
    if nuevo == "APROBADO":
        if pol.get("separacion_funciones", True):
            elaboradores = {x for x in (a.elaborado_por, a.responsable_elaboracion) if x}
            if usuario.lower() in {x.lower() for x in elaboradores}:
                raise SinPermiso("Separación de funciones: quien elabora el anexo no puede aprobarlo.")
        a.aprobado_por, a.aprobado_en = usuario, ahora
        v.inmutable, v.estado_al_cerrar = True, "APROBADO"
        db.add(AprobacionAnexo(anexo_id=a.id, version_id=v.id, accion="APROBAR", usuario=usuario, rol=r, comentario=comentario))
    elif nuevo == "CERRADO":
        v.inmutable, v.estado_al_cerrar = True, "CERRADO"
        db.add(AprobacionAnexo(anexo_id=a.id, version_id=v.id, accion="CERRAR", usuario=usuario, rol=r, comentario=comentario))
    elif nuevo == "REABIERTO":
        db.add(AprobacionAnexo(anexo_id=a.id, version_id=v.id, accion="REABRIR", usuario=usuario, rol=r, comentario=comentario))
    elif nuevo == "REVISADO":
        a.revisado_por, a.revisado_en = usuario, ahora
    elif nuevo in ("EN_ELABORACION", "SUBSANADO") and not a.elaborado_por:
        a.elaborado_por = usuario
    previo = a.estado_revision
    a.estado_revision = nuevo
    a.lock_version = (a.lock_version or 0) + 1
    db.add(RevisionAnexo(anexo_id=a.id, version_id=v.id, de_estado=previo, a_estado=nuevo, usuario=usuario, rol=r, comentario=comentario))
    auditar(db, empresa_id, usuario, f"ESTADO_{nuevo}", "anexo", a.id, {"de": previo, "a": nuevo, "comentario": comentario}, r)
    db.commit()
    return a


def editar(db: Session, empresa_id: int, anexo_id: int, usuario: str, datos: dict, lock_version: int | None = None) -> Anexo:
    a = _cargar(db, empresa_id, anexo_id)
    campos = {k: v for k, v in datos.items() if k in EDITABLES}
    responsables = {k for k in campos if k.startswith("responsable_") or k == "fecha_limite"}
    r = exigir(db, empresa_id, usuario, "asignar" if responsables and set(campos) <= responsables else "elaborar")
    exigir_cuenta(db, empresa_id, usuario, a.cuenta)
    if a.estado_revision in ("APROBADO", "CERRADO"):
        raise ErrorFlujo("El anexo está aprobado o cerrado: su versión es inmutable. Solicite una reapertura autorizada.")
    _lock(db, a, lock_version)
    cambios = {}
    for k, v in campos.items():
        if k == "fecha_limite" and v and not isinstance(v, date):
            v = date.fromisoformat(str(v))
        antes = getattr(a, k)
        if antes != v:
            cambios[k] = {"antes": str(antes) if antes is not None else None, "despues": str(v) if v is not None else None}
            setattr(a, k, v)
    if cambios:
        if a.estado_revision == "GENERADO" and set(cambios) & {"conclusion", "acciones_correctivas"}:
            db.add(RevisionAnexo(anexo_id=a.id, version_id=a.version_id, de_estado="GENERADO", a_estado="EN_ELABORACION",
                                 usuario=usuario, rol=r, comentario="Inicio de la elaboración"))
            a.estado_revision = "EN_ELABORACION"
            a.elaborado_por = a.elaborado_por or usuario
        a.lock_version = (a.lock_version or 0) + 1
        db.add(RevisionAnexo(anexo_id=a.id, version_id=a.version_id, de_estado=a.estado_revision, a_estado=a.estado_revision,
                             usuario=usuario, rol=r, comentario="Actualización de campos de revisión",
                             cambios=json.dumps(cambios, ensure_ascii=False)))
        auditar(db, empresa_id, usuario, "EDITAR_ANEXO", "anexo", a.id, cambios, r)
    db.commit()
    return a


def agregar_hallazgo(db: Session, empresa_id: int, anexo_id: int, usuario: str, datos: dict) -> HallazgoAnexo:
    a = _cargar(db, empresa_id, anexo_id)
    r = exigir(db, empresa_id, usuario, "comentar")
    exigir_cuenta(db, empresa_id, usuario, a.cuenta)
    if a.estado_revision in ("APROBADO", "CERRADO"):
        raise ErrorFlujo("El anexo está aprobado o cerrado: reábralo para registrar nuevas observaciones.")
    titulo = (datos.get("titulo") or "").strip()
    if len(titulo) < 5:
        raise ErrorFlujo("Describa la observación (mínimo 5 caracteres).")
    h = HallazgoAnexo(empresa_id=empresa_id, anexo_id=a.id, version_id=a.version_id, origen="USUARIO",
                      huella=hashlib.sha256(f"U|{datetime.now().isoformat()}|{titulo}".encode()).hexdigest()[:40],
                      codigo="OBSERVACION_REVISOR", severidad=datos.get("severidad") or "MEDIA", titulo=titulo[:300],
                      detalle=datos.get("detalle"), importe=datos.get("importe"), clave_fila=datos.get("clave_fila"),
                      responsable=datos.get("responsable"), accion_correctiva=datos.get("accion_correctiva"), creado_por=usuario)
    db.add(h)
    db.flush()
    a.observaciones_abiertas = (a.observaciones_abiertas or 0) + (0 if h.severidad == "INFORMATIVA" else 1)
    auditar(db, empresa_id, usuario, "AGREGAR_OBSERVACION", "hallazgo", h.id, {"anexo": a.id, "titulo": titulo}, r)
    db.commit()
    return h


def actualizar_hallazgo(db: Session, empresa_id: int, hallazgo_id: int, usuario: str, datos: dict) -> HallazgoAnexo:
    h = db.get(HallazgoAnexo, hallazgo_id)
    if not h or h.empresa_id != empresa_id:
        raise LookupError("Observación no encontrada")
    a = db.get(Anexo, h.anexo_id)
    nuevo = datos.get("estado")
    r = exigir(db, empresa_id, usuario, "revisar" if nuevo == "DESCARTADO" else "elaborar")
    exigir_cuenta(db, empresa_id, usuario, a.cuenta)
    if a.estado_revision in ("APROBADO", "CERRADO"):
        raise ErrorFlujo("El anexo está aprobado o cerrado.")
    cambios = {}
    if nuevo and nuevo != h.estado:
        if nuevo not in ("ABIERTO", "SUBSANADO", "DESCARTADO"):
            raise ErrorFlujo("Estado de observación no válido")
        if nuevo == "DESCARTADO" and len((datos.get("comentario") or "").strip()) < 10:
            raise ErrorFlujo("Justifique el descarte (mínimo 10 caracteres).")
        cambios["estado"] = [h.estado, nuevo]
        h.estado = nuevo
        h.resuelto_por, h.resuelto_en = (usuario, datetime.now()) if nuevo != "ABIERTO" else (None, None)
    for k in ("responsable", "accion_correctiva"):
        if k in datos and datos[k] != getattr(h, k):
            cambios[k] = [getattr(h, k), datos[k]]
            setattr(h, k, datos[k])
    if datos.get("comentario"):
        db.add(ComentarioAnexo(anexo_id=a.id, version_id=a.version_id, clave_fila=h.clave_fila, usuario=usuario,
                               texto=f"[Observación #{h.id}] {datos['comentario']}"))
    from app.anexos.generador import abiertas
    db.flush()
    a.observaciones_abiertas = abiertas(db, a.id)
    auditar(db, empresa_id, usuario, "ACTUALIZAR_OBSERVACION", "hallazgo", h.id, cambios, r)
    db.commit()
    return h


def comentar(db: Session, empresa_id: int, anexo_id: int, usuario: str, texto: str, clave_fila: str | None = None) -> ComentarioAnexo:
    a = _cargar(db, empresa_id, anexo_id)
    exigir(db, empresa_id, usuario, "comentar")
    exigir_cuenta(db, empresa_id, usuario, a.cuenta)
    texto = (texto or "").strip()
    if not texto:
        raise ErrorFlujo("El comentario está vacío.")
    c = ComentarioAnexo(anexo_id=a.id, version_id=a.version_id, clave_fila=clave_fila, usuario=usuario, texto=texto[:4000])
    db.add(c)
    db.commit()
    return c


# ------------------------------------------------------------------ documentación sustentatoria
def _dir_adjuntos(empresa_id: int) -> Path:
    d = Path(config.DATA_DIR) / "anexos" / str(empresa_id) / "sustentos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def adjuntar(db: Session, empresa_id: int, usuario: str, nombre: str, tipo: str | None, contenido: bytes, meta: dict) -> AdjuntoAnexo:
    r = exigir(db, empresa_id, usuario, "adjuntar")
    if not contenido:
        raise ErrorFlujo("El archivo está vacío.")
    if len(contenido) > MAX_ADJUNTO:
        raise ErrorFlujo("El archivo supera el tamaño máximo (20 MB).")
    ext = Path(nombre or "").suffix.lower()
    if ext not in EXT_PERMITIDAS:
        raise ErrorFlujo(f"Tipo de archivo no permitido ({ext or 'sin extensión'}).")
    cat = (meta.get("categoria") or "OTRO").upper()
    if cat not in CATEGORIAS_ADJUNTO:
        raise ErrorFlujo("Categoría de documento no válida.")
    anexo_id = meta.get("anexo_id")
    cuenta = (meta.get("cuenta") or "").strip() or None
    if anexo_id:
        a = _cargar(db, empresa_id, int(anexo_id))
        cuenta = cuenta or a.cuenta
    if not (cuenta or meta.get("tercero") or meta.get("documento") or meta.get("clave_fila") or meta.get("item_id") or meta.get("linea_id")):
        raise ErrorFlujo("Relacione el documento con una cuenta, anexo, tercero, documento o partida.")
    if cuenta:
        exigir_cuenta(db, empresa_id, usuario, cuenta)
    h = hashlib.sha256(contenido).hexdigest()
    seguro = re.sub(r"[^A-Za-z0-9._-]", "_", Path(nombre).name)[:120]
    ruta = _dir_adjuntos(empresa_id) / f"{h[:16]}-{seguro}"
    if not ruta.exists():
        ruta.write_bytes(contenido)
    adj = AdjuntoAnexo(empresa_id=empresa_id, anexo_id=int(anexo_id) if anexo_id else None, cuenta=cuenta,
                       tercero=(meta.get("tercero") or "").strip() or None, documento=(meta.get("documento") or "").strip().upper() or None,
                       clave_fila=meta.get("clave_fila") or None, item_id=int(meta["item_id"]) if meta.get("item_id") else None,
                       linea_id=int(meta["linea_id"]) if meta.get("linea_id") else None, categoria=cat,
                       descripcion=(meta.get("descripcion") or None), nombre=Path(nombre).name[:255], tipo_contenido=tipo,
                       tamano=len(contenido), hash=h, ruta=str(ruta.relative_to(Path(config.DATA_DIR))),
                       confidencial=str(meta.get("confidencial", "")).lower() in ("1", "true", "si", "sí"), usuario=usuario)
    db.add(adj)
    db.flush()
    auditar(db, empresa_id, usuario, "ADJUNTAR_SUSTENTO", "adjunto", adj.id,
            {"nombre": adj.nombre, "categoria": cat, "cuenta": cuenta, "anexo": anexo_id, "hash": h}, r)
    db.commit()
    return adj


def ruta_adjunto(adj: AdjuntoAnexo) -> Path:
    return Path(config.DATA_DIR) / adj.ruta


# ------------------------------------------------------------------ asignaciones y configuración
def asignar(db: Session, empresa_id: int, usuario: str, datos: dict) -> AsignacionAnexo:
    r = exigir(db, empresa_id, usuario, "configurar" if datos.get("tipo") == "ACCESO" else "asignar")
    tipo = datos.get("tipo")
    if tipo not in ("ELABORACION", "REVISION", "APROBACION", "ACCESO"):
        raise ErrorFlujo("Tipo de asignación no válido")
    if not (datos.get("cuenta") or datos.get("anexo_id")):
        raise ErrorFlujo("Indique la cuenta (prefijo) o el anexo.")
    if datos.get("anexo_id"):
        _cargar(db, empresa_id, int(datos["anexo_id"]))
    fl = datos.get("fecha_limite")
    x = AsignacionAnexo(empresa_id=empresa_id, anexo_id=datos.get("anexo_id"), cuenta=(datos.get("cuenta") or None), tipo=tipo,
                        usuario=datos["usuario"].strip(), fecha_limite=date.fromisoformat(fl) if fl else None, asignado_por=usuario)
    db.add(x)
    db.flush()
    campo = {"ELABORACION": "responsable_elaboracion", "REVISION": "responsable_revision", "APROBACION": "responsable_aprobacion"}.get(tipo)
    if campo:  # propaga el responsable a los anexos abiertos de la cuenta
        q = update(Anexo).where(Anexo.empresa_id == empresa_id, Anexo.estado_revision.notin_(("APROBADO", "CERRADO")))
        q = q.where(Anexo.id == int(datos["anexo_id"])) if datos.get("anexo_id") else q.where(Anexo.cuenta.like(f"{datos['cuenta']}%"))
        valores = {campo: x.usuario}
        if x.fecha_limite and tipo == "ELABORACION":
            valores["fecha_limite"] = x.fecha_limite
        db.execute(q.values(**valores))
    auditar(db, empresa_id, usuario, "ASIGNAR", "asignacion", x.id, {k: str(v) for k, v in datos.items()}, r)
    db.commit()
    return x


def guardar_configuracion(db: Session, empresa_id: int, usuario: str, datos: dict) -> dict:
    r = exigir(db, empresa_id, usuario, "configurar")
    actual = configuracion(db, empresa_id)
    if "separacion_funciones" in datos:
        actual["separacion_funciones"] = bool(datos["separacion_funciones"])
    if "tolerancia" in datos:
        from decimal import Decimal
        t = Decimal(str(datos["tolerancia"]))
        if t < 0 or t > 1000:
            raise ErrorFlujo("Tolerancia fuera de rango (0 a 1000).")
        actual["tolerancia"] = str(t)
    if "aprobacion_automatica" in datos:
        aa = datos["aprobacion_automatica"] or {}
        activa = bool(aa.get("activa"))
        resultados = [x for x in aa.get("resultados", ["CUADRADO"]) if x in ("CUADRADO",)]
        if activa and not resultados:
            raise ErrorFlujo("La aprobación automática solo puede aplicarse a anexos CUADRADOS sin observaciones.")
        actual["aprobacion_automatica"] = {"activa": activa, "resultados": resultados or ["CUADRADO"],
                                           "autorizada_por": usuario if activa else None,
                                           "autorizada_en": datetime.now().isoformat() if activa else None}
    c = db.scalar(select(ConfiguracionAnexos).where(ConfiguracionAnexos.empresa_id == empresa_id))
    if not c:
        c = ConfiguracionAnexos(empresa_id=empresa_id)
        db.add(c)
    c.parametros, c.actualizado_por = json.dumps(actual), usuario
    auditar(db, empresa_id, usuario, "CONFIGURAR", "configuracion", None, actual, r)
    db.commit()
    return actual


# ------------------------------------------------------------------ datos personales
def enmascarar(fila: dict) -> dict:
    t = fila.get("tercero")
    if t:
        fila["tercero"] = "•" * max(len(t) - 2, 0) + t[-2:]
    if fila.get("razon_social"):
        fila["razon_social"] = f"Trabajador ···{(t or '')[-2:]}" if t else "Trabajador (reservado)"
    return fila


def requiere_mascara(fila: dict, especialidad: str) -> bool:
    return especialidad == "REMUNERACIONES" or bool(fila.get("personal"))
