"""Encargos, permisos, materialidad, matriz, reglas configurables y flujo de hallazgos.

Separación de funciones: quien crea una regla no la valida; quien ejecuta la auditoría no confirma sus hallazgos; quien
marca un hallazgo como subsanado no lo verifica; el cierre y la aprobación de conclusiones corresponden a supervisión.
Un hallazgo confirmado no se cierra sin la verificación (evidencia de revisión) y un comentario de cierre. Todo cambio
queda en el historial (audit_reviews) y en la bitácora encadenada (audit_event_logs). No se elimina nada.
"""
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import func, select, update

from app.auditoria import catalogo, configurables, riesgo
from app.auditoria.base import Contexto, Regla
from app.compensacion.servicio import rol_de
from app.core import config
from app.models import (AlcanceAuditoria, AprobacionAuditoria, AsignacionAuditoria, CategoriaRegla, EjecucionAuditoria, EncargoAuditoria,
                        EvidenciaHallazgo, GrupoHallazgos, HallazgoAuditoria, Materialidad, MatrizRiesgo, PlanAccion, ReglaAuditoria,
                        RevisionAuditoria, VersionRegla)
from app.models.auditoria360 import REGULARIZACION, TIPOS_AUDITORIA

TODOS = {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA", "AUDITOR", "AUDITOR_EXTERNO", "GERENCIA", "CONSULTA", "TESORERO", "PLANILLAS"}
PERMISOS = {
    "consultar": TODOS, "exportar": TODOS - {"TESORERO", "PLANILLAS"},
    "crear_encargo": {"ADMINISTRADOR", "SUPERVISOR", "AUDITOR", "CONTADOR"},
    "ejecutar": {"ADMINISTRADOR", "SUPERVISOR", "AUDITOR", "CONTADOR", "ANALISTA"},
    "reglas": {"ADMINISTRADOR", "SUPERVISOR", "AUDITOR"},
    "validar_reglas": {"ADMINISTRADOR", "SUPERVISOR"},
    "revisar": {"ADMINISTRADOR", "SUPERVISOR", "AUDITOR", "AUDITOR_EXTERNO"},
    "gestionar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA", "AUDITOR"},
    "aprobar": {"ADMINISTRADOR", "SUPERVISOR"},
    "materialidad": {"ADMINISTRADOR", "SUPERVISOR", "AUDITOR"},
    "regularizacion": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR"},
    "confidencial": {"ADMINISTRADOR", "SUPERVISOR", "AUDITOR"},
    "datos_personales": {"ADMINISTRADOR", "SUPERVISOR", "PLANILLAS", "AUDITOR"},
}
ABIERTOS = ("DETECTADO", "PENDIENTE_REVISION", "EN_ANALISIS", "CONFIRMADO", "PENDIENTE_REGULARIZACION", "EN_SUBSANACION", "REABIERTO")
# nuevo estado: (permiso, estados de origen)
TRANS = {
    "PENDIENTE_REVISION": ("gestionar", {"DETECTADO", "REABIERTO"}),
    "EN_ANALISIS": ("gestionar", {"DETECTADO", "PENDIENTE_REVISION", "REABIERTO"}),
    "CONFIRMADO": ("revisar", {"DETECTADO", "PENDIENTE_REVISION", "EN_ANALISIS", "REABIERTO"}),
    "JUSTIFICADO": ("revisar", {"DETECTADO", "PENDIENTE_REVISION", "EN_ANALISIS", "REABIERTO", "CONFIRMADO"}),
    "FALSO_POSITIVO": ("revisar", {"DETECTADO", "PENDIENTE_REVISION", "EN_ANALISIS", "REABIERTO"}),
    "PENDIENTE_REGULARIZACION": ("gestionar", {"CONFIRMADO"}),
    "EN_SUBSANACION": ("gestionar", {"CONFIRMADO", "PENDIENTE_REGULARIZACION"}),
    "SUBSANADO": ("gestionar", {"CONFIRMADO", "PENDIENTE_REGULARIZACION", "EN_SUBSANACION"}),
    "VERIFICADO": ("revisar", {"SUBSANADO"}),
    "CERRADO": ("aprobar", {"VERIFICADO", "JUSTIFICADO"}),
    "REABIERTO": ("revisar", {"CERRADO", "VERIFICADO", "SUBSANADO", "JUSTIFICADO"}),
}


class SinPermiso(Exception):
    status = 403


class ErrorAuditoria(Exception):
    status = 422


class Conflicto(Exception):
    status = 409


def rol(db, empresa_id, usuario):
    return rol_de(db, empresa_id, usuario)[0]


def puede(db, empresa_id, usuario, accion) -> bool:
    return rol(db, empresa_id, usuario) in PERMISOS[accion]


def exigir(db, empresa_id, usuario, accion) -> str:
    r = rol(db, empresa_id, usuario)
    if r not in PERMISOS[accion]:
        raise SinPermiso(f"El usuario «{usuario}» ({r or 'sin rol en la empresa'}) no tiene permiso para: {accion.replace('_', ' ')}.")
    return r


def evento(db, empresa_id, usuario, accion, entidad, entidad_id=None, detalle=None, rol_=None, engagement_id=None, run_id=None):
    riesgo.registrar(db, empresa_id, usuario, accion, entidad, entidad_id, detalle, rol_, engagement_id, run_id)


def _hist(db, empresa_id, entidad, entidad_id, usuario, rol_, de=None, a=None, comentario=None, cambios=None):
    db.add(RevisionAuditoria(empresa_id=empresa_id, entidad=entidad, entidad_id=entidad_id, de_estado=de, a_estado=a, comentario=comentario,
                             cambios=json.dumps(cambios, default=str, ensure_ascii=False) if cambios else None, usuario=usuario, rol=rol_))


# ------------------------------------------------------------------ encargos
def cargar_encargo(db, empresa_id, eid, usuario=None) -> EncargoAuditoria:
    e = db.get(EncargoAuditoria, eid)
    if not e or e.empresa_id != empresa_id:
        raise LookupError("Encargo no encontrado")
    if usuario and rol(db, empresa_id, usuario) == "AUDITOR_EXTERNO":
        ok = db.scalar(select(AsignacionAuditoria).where(AsignacionAuditoria.empresa_id == empresa_id, AsignacionAuditoria.tipo == "AUDITOR_EXTERNO",
                                                         AsignacionAuditoria.usuario == usuario, AsignacionAuditoria.activa.is_(True),
                                                         AsignacionAuditoria.engagement_id == eid))
        if not ok or (ok.vigente_hasta and ok.vigente_hasta < date.today()):
            raise SinPermiso("El auditor externo no tiene un acceso vigente a este encargo.")
    return e


def crear_encargo(db, empresa_id, usuario, d: dict) -> EncargoAuditoria:
    r = exigir(db, empresa_id, usuario, "crear_encargo")
    if d.get("tipo", "INTEGRAL") not in TIPOS_AUDITORIA:
        raise ErrorAuditoria("Tipo de auditoría no válido.")
    from app.anexos.datos import fin_de_periodo
    corte = d.get("fecha_corte") or fin_de_periodo(d["ejercicio"], d["periodo"])
    n = (db.scalar(select(func.count()).select_from(EncargoAuditoria).where(EncargoAuditoria.empresa_id == empresa_id)) or 0) + 1
    e = EncargoAuditoria(empresa_id=empresa_id, codigo=f"A{corte:%Y%m}-{n:03d}", nombre=(d.get("nombre") or f"Auditoría {d.get('tipo', 'INTEGRAL').lower()} al {corte:%d/%m/%Y}")[:200],
                         tipo=d.get("tipo", "INTEGRAL"), ejercicio=d.get("ejercicio") or corte.year, periodo=d.get("periodo") or corte.month, fecha_corte=corte,
                         objetivo=d.get("objetivo"), responsable=d.get("responsable"), materialidad_id=d.get("materialidad_id"),
                         recurrencia=d.get("recurrencia"), proxima_ejecucion=d.get("proxima_ejecucion"), creado_por=usuario)
    db.add(e)
    db.flush()
    guardar_alcance(db, e, d.get("alcance") or {})
    evento(db, empresa_id, usuario, "CREAR_ENCARGO", "encargo", e.id, {"tipo": e.tipo, "corte": corte, "alcance": d.get("alcance")}, r, e.id)
    db.commit()
    return e


ALCANCE = {"modulos": "MODULO", "cuentas": "CUENTA", "centros_costo": "CENTRO_COSTO", "proyectos": "PROYECTO", "unidades_negocio": "UNIDAD_NEGOCIO",
           "reglas": "REGLA", "terceros": "TERCERO"}


def guardar_alcance(db, e, alcance: dict):
    for a in db.scalars(select(AlcanceAuditoria).where(AlcanceAuditoria.engagement_id == e.id)):
        db.delete(a)
    db.flush()
    mods = {c for c, _, _ in catalogo.CATEGORIAS}
    for k, tipo in ALCANCE.items():
        for v in sorted(set(alcance.get(k) or [])):
            if k == "modulos" and v not in mods:
                raise ErrorAuditoria(f"Módulo no válido: {v}")
            db.add(AlcanceAuditoria(engagement_id=e.id, tipo=tipo, valor=str(v)[:60]))
    db.flush()


def programar_siguiente(db, empresa_id, eid, usuario) -> EncargoAuditoria:
    """Auditoría recurrente: crea el encargo del periodo siguiente con el mismo alcance (no se ejecuta solo: sin planificador)."""
    e = cargar_encargo(db, empresa_id, eid)
    if not e.recurrencia:
        raise ErrorAuditoria("El encargo no es recurrente.")
    meses = {"MENSUAL": 1, "TRIMESTRAL": 3, "ANUAL": 12}[e.recurrencia]
    m = e.fecha_corte.month + meses
    ej, per = e.fecha_corte.year + (m - 1) // 12, (m - 1) % 12 + 1
    from app.auditoria.motor import alcance_de
    nuevo = crear_encargo(db, empresa_id, usuario, {"tipo": e.tipo, "ejercicio": ej, "periodo": per, "responsable": e.responsable,
                                                    "objetivo": e.objetivo, "recurrencia": e.recurrencia, "alcance": alcance_de(db, e)})
    nuevo.origen_id = e.id
    db.commit()
    return nuevo


def cambiar_estado_encargo(db, empresa_id, eid, usuario, estado, conclusion=None, lock_version=None) -> EncargoAuditoria:
    e = cargar_encargo(db, empresa_id, eid, usuario)
    validos = {"EN_REVISION": ("ejecutar", {"EN_EJECUCION"}), "CONCLUIDO": ("aprobar", {"EN_REVISION"}), "CERRADO": ("aprobar", {"CONCLUIDO"}),
               "EN_EJECUCION": ("ejecutar", {"PLANIFICADO", "EN_REVISION"})}
    if estado not in validos:
        raise ErrorAuditoria("Estado no válido.")
    perm, origenes = validos[estado]
    r = exigir(db, empresa_id, usuario, perm)
    if e.estado not in origenes:
        raise ErrorAuditoria(f"No se puede pasar de {e.estado} a {estado}.")
    if lock_version is not None:
        if db.execute(update(EncargoAuditoria).where(EncargoAuditoria.id == e.id, EncargoAuditoria.lock_version == lock_version)
                      .values(lock_version=lock_version + 1)).rowcount != 1:
            db.rollback()
            raise Conflicto("El encargo fue modificado por otro usuario.")
        db.refresh(e)
    if estado == "CONCLUIDO":
        if not conclusion or len(conclusion.strip()) < 20:
            raise ErrorAuditoria("Registre la conclusión preliminar (mínimo 20 caracteres).")
        ejecutores = {x.lower() for x in db.scalars(select(EjecucionAuditoria.usuario).where(EjecucionAuditoria.engagement_id == e.id))}
        if usuario.lower() in ejecutores:
            raise SinPermiso("Separación de funciones: quien ejecutó la auditoría no aprueba sus conclusiones.")
        e.conclusion, e.conclusion_aprobada_por = conclusion.strip(), usuario
        db.add(AprobacionAuditoria(empresa_id=empresa_id, entidad="CONCLUSION", entidad_id=e.id, accion="APROBAR", usuario=usuario, rol=r, comentario=conclusion))
    previo = e.estado
    e.estado = estado
    e.lock_version += 1
    _hist(db, empresa_id, "ENCARGO", e.id, usuario, r, previo, estado, conclusion)
    evento(db, empresa_id, usuario, f"ENCARGO_{estado}", "encargo", e.id, {"de": previo}, r, e.id)
    db.commit()
    return e


# ------------------------------------------------------------------ materialidad y matriz
def crear_materialidad(db, empresa_id, usuario, d: dict) -> Materialidad:
    r = exigir(db, empresa_id, usuario, "materialidad")
    try:
        pg, pe, pi = (Decimal(str(d[k])) for k in ("porcentaje_global", "porcentaje_ejecucion", "porcentaje_insignificante"))
    except (KeyError, InvalidOperation):
        raise ErrorAuditoria("Indique los porcentajes de materialidad global, de ejecución y de diferencias claramente insignificantes "
                             "(no hay porcentajes por defecto).")
    if not (0 < pg <= 100 and 0 < pe <= 100 and 0 <= pi <= 100):
        raise ErrorAuditoria("Porcentajes fuera de rango.")
    base = d.get("base")
    if base not in riesgo.BASES:
        raise ErrorAuditoria(f"Base no válida: use {', '.join(riesgo.BASES)}.")
    importe = Decimal(str(d["importe_base"])) if d.get("importe_base") not in (None, "") else riesgo.importe_base(db, empresa_id, d["ejercicio"],
                                                                                                                  d.get("periodo", 12), base)
    if not (d.get("justificacion") or "").strip():
        raise ErrorAuditoria("Registre la justificación de la base y los porcentajes elegidos.")
    glob = (abs(importe) * pg / 100).quantize(Decimal("0.01"))
    ejec = (glob * pe / 100).quantize(Decimal("0.01"))
    ins = (glob * pi / 100).quantize(Decimal("0.01"))
    m = Materialidad(empresa_id=empresa_id, ejercicio=d["ejercicio"], base=base, descripcion_base=d.get("descripcion_base"), importe_base=abs(importe),
                     porcentaje_global=pg, materialidad_global=glob, porcentaje_ejecucion=pe, materialidad_ejecucion=ejec, porcentaje_insignificante=pi,
                     umbral_insignificante=ins, por_cuenta=json.dumps(d.get("por_cuenta") or {}), por_tipo=json.dumps(d.get("por_tipo") or {}),
                     cualitativos=json.dumps(d.get("cualitativos") or {}), justificacion=d["justificacion"].strip(), definido_por=usuario)
    db.add(m)
    db.flush()
    evento(db, empresa_id, usuario, "DEFINIR_MATERIALIDAD", "materialidad", m.id, riesgo.materialidad_dict(m), r)
    db.commit()
    return m


def aprobar_materialidad(db, empresa_id, usuario, mid) -> Materialidad:
    r = exigir(db, empresa_id, usuario, "aprobar")
    m = db.get(Materialidad, mid)
    if not m or m.empresa_id != empresa_id:
        raise LookupError("Materialidad no encontrada")
    if m.definido_por.lower() == usuario.lower():
        raise SinPermiso("Separación de funciones: quien define la materialidad no la aprueba.")
    for x in db.scalars(select(Materialidad).where(Materialidad.empresa_id == empresa_id, Materialidad.ejercicio == m.ejercicio,
                                                   Materialidad.estado == "APROBADA")):
        x.estado = "REEMPLAZADA"
    m.estado, m.aprobado_por, m.aprobado_en = "APROBADA", usuario, datetime.now()
    db.add(AprobacionAuditoria(empresa_id=empresa_id, entidad="MATERIALIDAD", entidad_id=m.id, accion="APROBAR", usuario=usuario, rol=r))
    evento(db, empresa_id, usuario, "APROBAR_MATERIALIDAD", "materialidad", m.id, None, r)
    db.commit()
    return m


def guardar_matriz(db, empresa_id, usuario, d: dict) -> MatrizRiesgo:
    r = exigir(db, empresa_id, usuario, "aprobar")
    try:
        riesgo.validar_matriz(d["matriz"])
    except (KeyError, ValueError) as exc:
        raise ErrorAuditoria(str(exc))
    v = (db.scalar(select(func.max(MatrizRiesgo.version)).where(MatrizRiesgo.empresa_id == empresa_id)) or 0) + 1
    for x in db.scalars(select(MatrizRiesgo).where(MatrizRiesgo.empresa_id == empresa_id, MatrizRiesgo.activa.is_(True))):
        x.activa = False
    m = MatrizRiesgo(empresa_id=empresa_id, nombre=d.get("nombre") or f"Matriz v{v}", version=v, matriz=json.dumps(d["matriz"]),
                     factores=json.dumps(d.get("factores") or {}), creado_por=usuario, aprobado_por=usuario)
    db.add(m)
    db.flush()
    db.add(AprobacionAuditoria(empresa_id=empresa_id, entidad="MATRIZ", entidad_id=m.id, accion="APROBAR", usuario=usuario, rol=r))
    evento(db, empresa_id, usuario, "GUARDAR_MATRIZ", "matriz", m.id, d, r)
    db.commit()
    return m


# ------------------------------------------------------------------ reglas
CAMPOS_REGLA = ("nombre", "descripcion", "cuentas", "fuente", "riesgo", "probabilidad", "criterio", "recomendacion", "evidencia_requerida",
                "vigente_desde", "vigente_hasta", "norma_referencia", "fuente_oficial", "fecha_publicacion", "condiciones_aplicacion",
                "excepciones_normativas", "responsable_validacion")


def _version(db, r: ReglaAuditoria, usuario, motivo):
    from app.auditoria.motor import snapshot_regla
    db.add(VersionRegla(rule_id=r.id, version=r.version, snapshot=json.dumps(snapshot_regla(r), ensure_ascii=False), usuario=usuario, motivo=motivo))


def guardar_regla(db, empresa_id, usuario, d: dict, rule_id=None) -> ReglaAuditoria:
    """Crea una regla configurable o una versión de empresa de una regla del catálogo (nunca se edita el catálogo global)."""
    r_ = exigir(db, empresa_id, usuario, "reglas")
    catalogo.sembrar(db)
    if rule_id:
        r = db.get(ReglaAuditoria, rule_id)
        if not r or r.empresa_id not in (None, empresa_id):
            raise LookupError("Regla no encontrada")
        if r.empresa_id is None:  # personalización de una regla del sistema: copia de la empresa
            existente = db.scalar(select(ReglaAuditoria).where(ReglaAuditoria.empresa_id == empresa_id, ReglaAuditoria.codigo == r.codigo))
            if existente:
                r = existente
            else:
                base = r
                r = ReglaAuditoria(empresa_id=empresa_id, **{c.key: getattr(base, c.key) for c in ReglaAuditoria.__table__.columns
                                                              if c.key not in ("id", "empresa_id", "actualizado_en", "validada_por", "validada_en")})
                r.version = base.version
                r.creado_por = usuario
                if base.normativa:
                    r.estado_validacion = "PENDIENTE"
                db.add(r)
                db.flush()
        else:
            _version(db, r, usuario, d.get("motivo") or "Modificación")
            r.version += 1
    else:
        cat = db.scalar(select(CategoriaRegla).where(CategoriaRegla.codigo == (d.get("categoria") or "CONFIGURABLE")))
        if not cat:
            raise ErrorAuditoria("Categoría no válida.")
        codigo = (d.get("codigo") or "").upper().strip()
        if not codigo or not codigo.replace("-", "").replace("_", "").isalnum() or len(codigo) > 20:
            raise ErrorAuditoria("Código de regla no válido.")
        if db.scalar(select(ReglaAuditoria).where(ReglaAuditoria.codigo == codigo, (ReglaAuditoria.empresa_id == empresa_id) | ReglaAuditoria.empresa_id.is_(None))):
            raise ErrorAuditoria("Ya existe una regla con ese código.")
        r = ReglaAuditoria(empresa_id=empresa_id, categoria_id=cat.id, codigo=codigo, nombre=d.get("nombre") or codigo, origen="CONFIGURABLE",
                           evaluador="configurable", creado_por=usuario, activa=False, normativa=bool(d.get("normativa")),
                           estado_validacion="PENDIENTE" if d.get("normativa") else "NO_REQUIERE")
        db.add(r)
    if "definicion" in d and d["definicion"] is not None:
        if r.origen != "CONFIGURABLE":
            raise ErrorAuditoria("Las reglas del sistema no admiten definición declarativa; modifique sus parámetros.")
        try:
            configurables.validar(d["definicion"])
        except configurables.ErrorDefinicion as exc:
            raise ErrorAuditoria(str(exc))
        r.definicion = json.dumps(d["definicion"], ensure_ascii=False)
    for k in CAMPOS_REGLA:
        if k in d:
            v = d[k]
            if k in ("vigente_desde", "vigente_hasta", "fecha_publicacion") and isinstance(v, str):
                v = date.fromisoformat(v) if v else None
            setattr(r, k, v)
    if "parametros" in d:
        if not isinstance(d["parametros"], dict):
            raise ErrorAuditoria("Parámetros no válidos.")
        r.parametros = json.dumps({**json.loads(r.parametros or "{}"), **d["parametros"]}, ensure_ascii=False)
    if "excepciones" in d:
        r.excepciones = json.dumps(d["excepciones"] or {}, ensure_ascii=False)
    if r.riesgo not in riesgo.NIVELES:
        raise ErrorAuditoria("Nivel de riesgo no válido.")
    if r.normativa and rule_id:
        r.estado_validacion, r.validada_por, r.validada_en = "PENDIENTE", None, None  # todo cambio normativo requiere nueva validación
    db.flush()
    evento(db, empresa_id, usuario, "GUARDAR_REGLA", "regla", r.id, {"codigo": r.codigo, "version": r.version, "cambios": {k: d.get(k) for k in d}}, r_)
    db.commit()
    return r


def activar_regla(db, empresa_id, usuario, rule_id, activa: bool) -> ReglaAuditoria:
    r_ = exigir(db, empresa_id, usuario, "reglas")
    r = db.get(ReglaAuditoria, rule_id)
    if not r or r.empresa_id != empresa_id:
        raise LookupError("Regla de la empresa no encontrada (personalice primero la regla del catálogo).")
    if activa and r.normativa and r.estado_validacion != "VALIDADA":
        raise ErrorAuditoria("Una regla normativa no se activa sin validar su contenido y vigencia.")
    r.activa = activa
    evento(db, empresa_id, usuario, "ACTIVAR_REGLA" if activa else "DESACTIVAR_REGLA", "regla", r.id, None, r_)
    db.commit()
    return r


def validar_regla(db, empresa_id, usuario, rule_id, aprobar=True, comentario=None) -> ReglaAuditoria:
    r_ = exigir(db, empresa_id, usuario, "validar_reglas")
    r = db.get(ReglaAuditoria, rule_id)
    if not r or r.empresa_id != empresa_id:
        raise LookupError("Regla de la empresa no encontrada")
    if (r.creado_por or "").lower() == usuario.lower():
        raise SinPermiso("Separación de funciones: quien crea o modifica la regla no la valida.")
    if r.normativa and aprobar:
        faltan = [n for n, v in (("norma de referencia", r.norma_referencia), ("fuente oficial", r.fuente_oficial),
                                 ("fecha de publicación", r.fecha_publicacion), ("inicio de vigencia", r.vigente_desde),
                                 ("condiciones de aplicación", r.condiciones_aplicacion), ("responsable de validación", r.responsable_validacion)) if not v]
        if faltan:
            raise ErrorAuditoria(f"No se valida una regla normativa incompleta: falta {', '.join(faltan)}.")
    r.estado_validacion = "VALIDADA" if aprobar else "RECHAZADA"
    r.validada_por, r.validada_en = usuario, datetime.now()
    if aprobar and r.normativa:
        r.activa = True
    db.add(AprobacionAuditoria(empresa_id=empresa_id, entidad="REGLA", entidad_id=r.id, accion="VALIDAR" if aprobar else "RECHAZAR", usuario=usuario,
                               rol=r_, comentario=comentario))
    _hist(db, empresa_id, "REGLA", r.id, usuario, r_, None, r.estado_validacion, comentario)
    evento(db, empresa_id, usuario, "VALIDAR_REGLA", "regla", r.id, {"resultado": r.estado_validacion, "version": r.version}, r_)
    db.commit()
    return r


def vista_previa(db, empresa_id, usuario, eid, definicion: dict, limite=50) -> dict:
    """Resultados de una regla configurable antes de activarla (no guarda nada)."""
    exigir(db, empresa_id, usuario, "reglas")
    e = cargar_encargo(db, empresa_id, eid)
    try:
        configurables.validar(definicion)
    except configurables.ErrorDefinicion as exc:
        raise ErrorAuditoria(str(exc))
    from app.auditoria.motor import alcance_de
    ax = Contexto(db, e, alcance_de(db, e), None)
    fake = ReglaAuditoria(id=0, codigo="VISTA", nombre="Vista previa", riesgo="MEDIO", parametros="{}", definicion=json.dumps(definicion))
    s = configurables.evaluar(ax, Regla(fake), limite=limite)
    return {"poblacion": s.poblacion, "coincidencias": len(s.res), "limite": limite,
            "muestra": [{"titulo": x.titulo, "condicion": x.condicion, "importe": str(x.importe), "cuenta": x.cuenta, "tercero": x.tercero,
                         "documento": x.documento, "asiento": x.asiento, "linea_id": x.linea_id} for x in s.res],
            "nota": "Vista previa: no se generan hallazgos hasta activar la regla y ejecutar la auditoría."}


# ------------------------------------------------------------------ hallazgos
def cargar_hallazgo(db, empresa_id, hid, usuario=None) -> HallazgoAuditoria:
    h = db.get(HallazgoAuditoria, hid)
    if not h or h.empresa_id != empresa_id:
        raise LookupError("Hallazgo no encontrado")
    if usuario:
        cargar_encargo(db, empresa_id, h.engagement_id, usuario)
    return h


def _lock(db, h, lock_version):
    if lock_version is None:
        return
    if db.execute(update(HallazgoAuditoria).where(HallazgoAuditoria.id == h.id, HallazgoAuditoria.lock_version == lock_version)
                  .values(lock_version=lock_version + 1)).rowcount != 1:
        db.rollback()
        raise Conflicto("El hallazgo fue modificado por otro usuario.")
    db.refresh(h)


def cambiar_estado(db, empresa_id, hid, usuario, nuevo, comentario=None, lock_version=None, datos=None) -> HallazgoAuditoria:
    h = cargar_hallazgo(db, empresa_id, hid, usuario)
    if nuevo not in TRANS:
        raise ErrorAuditoria("Estado no válido.")
    perm, origenes = TRANS[nuevo]
    r = exigir(db, empresa_id, usuario, perm)
    if h.estado not in origenes:
        raise ErrorAuditoria(f"No se puede pasar de {h.estado} a {nuevo}.")
    comentario = (comentario or "").strip() or None
    datos = datos or {}
    _lock(db, h, lock_version)
    ejecutor = db.get(EjecucionAuditoria, h.run_id).usuario
    if nuevo in ("CONFIRMADO", "FALSO_POSITIVO", "JUSTIFICADO") and usuario.lower() == ejecutor.lower():
        raise SinPermiso("Separación de funciones: quien ejecutó la auditoría no revisa sus hallazgos.")
    if nuevo == "CONFIRMADO" and h.calidad_evidencia == "INSUFICIENTE" and not _evidencia_usuario(db, h):
        raise ErrorAuditoria("Evidencia insuficiente: adjunte evidencia de revisión antes de confirmar el hallazgo.")
    if nuevo in ("FALSO_POSITIVO", "JUSTIFICADO", "REABIERTO", "CERRADO") and (not comentario or len(comentario) < 15):
        raise ErrorAuditoria("Registre la justificación (mínimo 15 caracteres).")
    if nuevo == "PENDIENTE_REGULARIZACION" and not (datos.get("regularizacion") or h.regularizacion):
        raise ErrorAuditoria("Clasifique el tipo de regularización requerida.")
    if nuevo == "EN_SUBSANACION" and not db.scalar(select(PlanAccion.id).where(PlanAccion.finding_id == h.id)):
        raise ErrorAuditoria("Registre un plan de acción antes de iniciar la subsanación.")
    if nuevo == "SUBSANADO" and not comentario:
        raise ErrorAuditoria("Describa la subsanación realizada.")
    if nuevo == "VERIFICADO":
        quien = db.scalar(select(RevisionAuditoria.usuario).where(RevisionAuditoria.entidad == "HALLAZGO", RevisionAuditoria.entidad_id == h.id,
                                                                  RevisionAuditoria.a_estado == "SUBSANADO").order_by(RevisionAuditoria.id.desc()))
        if quien and quien.lower() == usuario.lower():
            raise SinPermiso("Separación de funciones: quien subsana no verifica la subsanación.")
        if not comentario:
            raise ErrorAuditoria("Registre la evidencia de revisión de la subsanación.")
    if nuevo == "CERRADO":
        revisores = {x.lower() for x in db.scalars(select(RevisionAuditoria.usuario).where(
            RevisionAuditoria.entidad == "HALLAZGO", RevisionAuditoria.entidad_id == h.id, RevisionAuditoria.a_estado.in_(("VERIFICADO", "JUSTIFICADO"))))}
        if usuario.lower() in revisores:
            raise SinPermiso("Separación de funciones: el cierre lo aprueba un usuario distinto de quien verificó o justificó.")
    previo = h.estado
    if nuevo == "FALSO_POSITIVO":
        h.estado, h.tipo = "CERRADO", "FALSO_POSITIVO"
    else:
        h.estado = nuevo
        h.tipo = {"CONFIRMADO": "CONFIRMADO", "JUSTIFICADO": "JUSTIFICADO", "VERIFICADO": "SUBSANADO", "REABIERTO": "POTENCIAL"}.get(nuevo, h.tipo)
    if datos.get("regularizacion"):
        if datos["regularizacion"] not in REGULARIZACION:
            raise ErrorAuditoria("Clasificación de regularización no válida.")
        h.regularizacion = datos["regularizacion"]
    if datos.get("importe_confirmado") not in (None, ""):
        h.importe_confirmado = Decimal(str(datos["importe_confirmado"]))
    h.lock_version += 1
    _hist(db, empresa_id, "HALLAZGO", h.id, usuario, r, previo, h.estado if nuevo != "FALSO_POSITIVO" else "FALSO_POSITIVO", comentario, datos or None)
    if nuevo in ("CONFIRMADO", "CERRADO", "VERIFICADO"):
        db.add(AprobacionAuditoria(empresa_id=empresa_id, entidad="HALLAZGO", entidad_id=h.id, accion=nuevo, usuario=usuario, rol=r, comentario=comentario))
    evento(db, empresa_id, usuario, f"HALLAZGO_{nuevo}", "hallazgo", h.id, {"de": previo, "comentario": comentario}, r, h.engagement_id)
    from app.auditoria.motor import recalcular_grupos
    recalcular_grupos(db, h.engagement_id)
    db.commit()
    return h


def _evidencia_usuario(db, h) -> bool:
    return bool(db.scalar(select(EvidenciaHallazgo.id).where(EvidenciaHallazgo.finding_id == h.id, EvidenciaHallazgo.origen == "USUARIO")))


def actualizar_hallazgo(db, empresa_id, hid, usuario, d: dict) -> HallazgoAuditoria:
    h = cargar_hallazgo(db, empresa_id, hid, usuario)
    r = exigir(db, empresa_id, usuario, "gestionar" if not d.get("riesgo") else "revisar")
    _lock(db, h, d.get("lock_version"))
    cambios = {}
    for k in ("responsable", "causa", "efecto", "recomendacion"):
        if k in d and d[k] != getattr(h, k):
            cambios[k] = [getattr(h, k), d[k]]
            setattr(h, k, d[k])
    if "fecha_limite" in d:
        fl = date.fromisoformat(d["fecha_limite"]) if d["fecha_limite"] else None
        cambios["fecha_limite"] = [str(h.fecha_limite), str(fl)]
        h.fecha_limite = fl
    if d.get("riesgo") and d["riesgo"] != h.riesgo:  # ajuste del auditor con justificación documentada
        if d["riesgo"] not in riesgo.NIVELES:
            raise ErrorAuditoria("Nivel de riesgo no válido.")
        if not d.get("justificacion_riesgo") or len(d["justificacion_riesgo"].strip()) < 15:
            raise ErrorAuditoria("Justifique el ajuste de la clasificación de riesgo (mínimo 15 caracteres).")
        cambios["riesgo"] = [h.riesgo, d["riesgo"]]
        h.riesgo, h.riesgo_ajustado_por, h.justificacion_riesgo = d["riesgo"], usuario, d["justificacion_riesgo"].strip()
    if d.get("regularizacion"):
        if d["regularizacion"] not in REGULARIZACION:
            raise ErrorAuditoria("Clasificación de regularización no válida.")
        cambios["regularizacion"] = [h.regularizacion, d["regularizacion"]]
        h.regularizacion = d["regularizacion"]
    if d.get("responsable"):
        db.add(AsignacionAuditoria(empresa_id=empresa_id, engagement_id=h.engagement_id, finding_id=h.id, tipo="RESPONSABLE_HALLAZGO",
                                   usuario=d["responsable"], asignado_por=usuario))
    h.lock_version += 1
    _hist(db, empresa_id, "HALLAZGO", h.id, usuario, r, h.estado, h.estado, d.get("comentario"), cambios)
    evento(db, empresa_id, usuario, "ACTUALIZAR_HALLAZGO", "hallazgo", h.id, cambios, r, h.engagement_id)
    db.commit()
    return h


def comentar(db, empresa_id, hid, usuario, texto) -> None:
    h = cargar_hallazgo(db, empresa_id, hid, usuario)
    r = exigir(db, empresa_id, usuario, "consultar")
    if not texto or not texto.strip():
        raise ErrorAuditoria("Comentario vacío.")
    _hist(db, empresa_id, "HALLAZGO", h.id, usuario, r, h.estado, h.estado, texto.strip())
    evento(db, empresa_id, usuario, "COMENTAR", "hallazgo", h.id, {"texto": texto.strip()[:500]}, r, h.engagement_id)
    db.commit()


def adjuntar_evidencia(db, empresa_id, hid, usuario, nombre, tipo, contenido: bytes, descripcion, confidencial=False) -> EvidenciaHallazgo:
    h = cargar_hallazgo(db, empresa_id, hid, usuario)
    r = exigir(db, empresa_id, usuario, "gestionar" if rol(db, empresa_id, usuario) not in PERMISOS["revisar"] else "revisar")
    if not contenido or len(contenido) > 20 * 1024 * 1024:
        raise ErrorAuditoria("Archivo vacío o mayor a 20 MB.")
    ext = Path(nombre or "").suffix.lower()
    if ext not in {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".csv", ".txt", ".docx", ".xml", ".zip", ".msg", ".eml"}:
        raise ErrorAuditoria(f"Tipo de archivo no permitido ({ext or 'sin extensión'}).")
    hs = hashlib.sha256(contenido).hexdigest()
    carpeta = Path(config.DATA_DIR) / "auditoria" / str(empresa_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{hs[:16]}{ext}"
    if not ruta.exists():
        ruta.write_bytes(contenido)
    e = EvidenciaHallazgo(finding_id=h.id, origen="USUARIO", tipo="ARCHIVO", descripcion=(descripcion or Path(nombre).name)[:2000],
                          nombre_archivo=Path(nombre).name[:255], ruta=str(ruta.relative_to(Path(config.DATA_DIR))), hash=hs,
                          confidencial=bool(confidencial) or h.personal, usuario=usuario,
                          datos=json.dumps({"tipo_contenido": tipo, "tamano": len(contenido)}))
    db.add(e)
    db.flush()
    evento(db, empresa_id, usuario, "ADJUNTAR_EVIDENCIA", "evidencia", e.id, {"hallazgo": h.id, "hash": hs, "nombre": e.nombre_archivo}, r, h.engagement_id)
    db.commit()
    return e


def crear_plan(db, empresa_id, hid, usuario, d: dict) -> PlanAccion:
    h = cargar_hallazgo(db, empresa_id, hid, usuario)
    r = exigir(db, empresa_id, usuario, "gestionar")
    if not d.get("descripcion") or not d.get("responsable") or not d.get("fecha_compromiso"):
        raise ErrorAuditoria("Indique descripción, responsable y fecha de compromiso del plan de acción.")
    p = PlanAccion(finding_id=h.id, descripcion=d["descripcion"], responsable=d["responsable"],
                   fecha_compromiso=date.fromisoformat(d["fecha_compromiso"]) if isinstance(d["fecha_compromiso"], str) else d["fecha_compromiso"], usuario=usuario)
    db.add(p)
    db.flush()
    if not h.fecha_limite or p.fecha_compromiso < h.fecha_limite:
        h.fecha_limite = p.fecha_compromiso
    _hist(db, empresa_id, "HALLAZGO", h.id, usuario, r, h.estado, h.estado, f"Plan de acción: {p.descripcion}")
    evento(db, empresa_id, usuario, "CREAR_PLAN", "plan", p.id, d, r, h.engagement_id)
    db.commit()
    return p


def actualizar_plan(db, empresa_id, pid, usuario, d: dict) -> PlanAccion:
    p = db.get(PlanAccion, pid)
    if not p:
        raise LookupError("Plan no encontrado")
    h = cargar_hallazgo(db, empresa_id, p.finding_id, usuario)
    r = exigir(db, empresa_id, usuario, "gestionar")
    if d.get("estado") and d["estado"] not in ("PENDIENTE", "EN_PROCESO", "COMPLETADO", "CANCELADO"):
        raise ErrorAuditoria("Estado de plan no válido.")
    for k in ("estado", "avance", "comentario_cierre"):
        if k in d:
            setattr(p, k, d[k])
    _hist(db, empresa_id, "PLAN", p.id, usuario, r, None, p.estado, d.get("comentario_cierre"), d)
    evento(db, empresa_id, usuario, "ACTUALIZAR_PLAN", "plan", p.id, d, r, h.engagement_id)
    db.commit()
    return p


def enviar_regularizacion(db, empresa_id, hid, usuario) -> HallazgoAuditoria:
    """Bandeja de regularizaciones pendientes (fase 8). No genera ni contabiliza asientos."""
    h = cargar_hallazgo(db, empresa_id, hid, usuario)
    r = exigir(db, empresa_id, usuario, "regularizacion")
    if h.tipo != "CONFIRMADO" and h.estado not in ("CONFIRMADO", "PENDIENTE_REGULARIZACION"):
        raise ErrorAuditoria("Solo los hallazgos confirmados se envían a la bandeja de regularizaciones.")
    if not h.regularizacion or h.regularizacion == "NO_REQUIERE_AJUSTE":
        raise ErrorAuditoria("Clasifique el hallazgo con el tipo de regularización requerida.")
    h.en_bandeja_regularizacion, h.enviado_regularizacion_por, h.enviado_regularizacion_en = True, usuario, datetime.now()
    _hist(db, empresa_id, "HALLAZGO", h.id, usuario, r, h.estado, h.estado, "Enviado a la bandeja de regularizaciones (fase 8: no se generan asientos).")
    evento(db, empresa_id, usuario, "ENVIAR_REGULARIZACION", "hallazgo", h.id, {"regularizacion": h.regularizacion}, r, h.engagement_id)
    db.commit()
    return h


def agrupar(db, empresa_id, usuario, eid, hallazgos: list[int], titulo) -> GrupoHallazgos:
    """Agrupación manual de hallazgos relacionados que comparten la misma exposición."""
    e = cargar_encargo(db, empresa_id, eid, usuario)
    r = exigir(db, empresa_id, usuario, "revisar")
    hs = [cargar_hallazgo(db, empresa_id, i) for i in hallazgos]
    if len(hs) < 2 or any(h.engagement_id != e.id for h in hs):
        raise ErrorAuditoria("Seleccione dos o más hallazgos del encargo.")
    clave = f"MANUAL|{'|'.join(str(h.id) for h in sorted(hs, key=lambda x: x.id))}"
    for h in hs:
        h.clave_exposicion = clave
    db.flush()
    from app.auditoria.motor import recalcular_grupos
    recalcular_grupos(db, e.id)
    g = db.scalar(select(GrupoHallazgos).where(GrupoHallazgos.engagement_id == e.id, GrupoHallazgos.clave == clave))
    g.manual, g.titulo, g.creado_por = True, (titulo or g.titulo)[:255], usuario
    evento(db, empresa_id, usuario, "AGRUPAR_HALLAZGOS", "grupo", g.id, {"hallazgos": hallazgos}, r, e.id)
    db.commit()
    return g


def asignar(db, empresa_id, usuario, d: dict) -> AsignacionAuditoria:
    r = exigir(db, empresa_id, usuario, "aprobar")
    if d["tipo"] not in ("EQUIPO", "AUDITOR_EXTERNO"):
        raise ErrorAuditoria("Tipo de asignación no válido.")
    if d.get("engagement_id"):
        cargar_encargo(db, empresa_id, d["engagement_id"])
    a = AsignacionAuditoria(empresa_id=empresa_id, engagement_id=d.get("engagement_id"), tipo=d["tipo"], usuario=d["usuario"], funcion=d.get("funcion"),
                            vigente_hasta=date.fromisoformat(d["vigente_hasta"]) if d.get("vigente_hasta") else None, asignado_por=usuario)
    db.add(a)
    db.flush()
    evento(db, empresa_id, usuario, "ASIGNAR", "asignacion", a.id, d, r, d.get("engagement_id"))
    db.commit()
    return a
