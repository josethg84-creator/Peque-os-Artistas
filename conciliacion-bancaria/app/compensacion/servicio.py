"""Operaciones del contador sobre la compensación: permisos, compensación manual, aprobación,
rechazo, reversión, decisiones sobre coincidencias ambiguas y observaciones.

Permisos (por empresa). Mientras la empresa no tenga roles asignados se opera en «modo abierto»
(todos con permisos de administrador) y la interfaz lo advierte. La identidad del usuario proviene
de la cabecera X-Usuario hasta que exista autenticación (fase 6).
"""
import hashlib
import json
import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.compensacion import motor, partidas
from app.compensacion.motor import CERO, C2, Conflicto, It
from app.core import config
from app.models import (AdjuntoCompensacion, Aplicacion, AprobacionCompensacion, CandidatoCompensacion,
                        ComentarioCompensacion, ExcepcionCompensacion, GrupoCompensacion, PartidaAbierta,
                        ReversionCompensacion, RolUsuario)

PERMISOS = {
    "consultar": {"ADMINISTRADOR", "CONTADOR", "ANALISTA", "AUDITOR", "SUPERVISOR", "CONSULTA", "TESORERO", "PLANILLAS"},
    "ejecutar": {"ADMINISTRADOR", "CONTADOR", "ANALISTA", "SUPERVISOR"},
    "proponer": {"ADMINISTRADOR", "CONTADOR", "ANALISTA", "SUPERVISOR"},
    "aprobar": {"ADMINISTRADOR", "CONTADOR", "SUPERVISOR"},
    "revertir": {"ADMINISTRADOR", "SUPERVISOR"},
    "autorizar_terceros": {"ADMINISTRADOR", "SUPERVISOR"},
    "configurar": {"ADMINISTRADOR", "SUPERVISOR"},
    "roles": {"ADMINISTRADOR"},
    "revisar": {"ADMINISTRADOR", "CONTADOR", "ANALISTA", "SUPERVISOR", "AUDITOR"},
}


class SinPermiso(Exception):
    status = 403


class ErrorValidacion(Exception):
    status = 422


def rol_de(db: Session, empresa_id: int, usuario: str) -> tuple[str | None, bool]:
    """(rol, modo_abierto)."""
    roles = db.scalars(select(RolUsuario).where(RolUsuario.empresa_id == empresa_id)).all()
    if not roles:
        return "ADMINISTRADOR", True
    r = next((x for x in roles if x.usuario.lower() == (usuario or "").lower()), None)
    return (r.rol if r else None), False


def exigir(db: Session, empresa_id: int, usuario: str, accion: str) -> str:
    rol, _ = rol_de(db, empresa_id, usuario)
    if rol is None or rol not in PERMISOS[accion]:
        raise SinPermiso(f"El usuario «{usuario}» ({rol or 'sin rol en la empresa'}) no puede {accion.replace('_', ' ')}.")
    return rol


def _it(p: PartidaAbierta) -> It:
    return It(p.id, p.cuenta, p.tercero, p.moneda, p.rol, p.clase, p.serie, p.numero, p.documento_referencia,
              p.orden_compra_servicio, p.proyecto, p.glosa or "", None, p.fecha_contable,
              (p.importe - p.importe_comprometido).quantize(C2), p.importe, p.importe_mn, p.clasificacion_pendiente,
              p.origen_datos, p.constancia_detraccion, p.retencion, p.codigo_detraccion, p.tipo_documento)


def _cargar(db, empresa_id, filas: list[dict]) -> list[tuple[PartidaAbierta, Decimal]]:
    out = []
    vistos = set()
    for f in filas:
        p = db.get(PartidaAbierta, int(f["item_id"]))
        if p is None or p.empresa_id != empresa_id:  # aislamiento: nunca entre empresas
            raise ErrorValidacion(f"La partida {f['item_id']} no existe en la empresa.")
        if p.id in vistos:
            raise ErrorValidacion(f"La partida {p.id} figura dos veces.")
        vistos.add(p.id)
        if not p.vigente:
            raise ErrorValidacion(f"La partida {p.id} proviene de un lote anulado.")
        m = Decimal(str(f["importe"])).quantize(C2)
        if m <= 0:
            raise ErrorValidacion("Los importes a aplicar deben ser mayores que cero.")
        disp = (p.importe - p.importe_comprometido).quantize(C2)
        if m > disp:
            raise ErrorValidacion(f"La partida {p.id} solo tiene {disp} disponible; se intentó aplicar {m}.")
        out.append((p, m))
    return out


def validar_manual(db: Session, empresa_id: int, usuario: str, izquierda: list[dict], derecha: list[dict], *,
                   justificacion: str | None, autorizar_terceros=False, tipo_cambio: Decimal | None = None,
                   fecha_corte: date | None = None) -> dict:
    """Valida todas las restricciones obligatorias y devuelve la vista previa (antes / después)."""
    if not izquierda or not derecha:
        raise ErrorValidacion("Seleccione al menos una partida en cada panel.")
    izq, der = _cargar(db, empresa_id, izquierda), _cargar(db, empresa_id, derecha)
    if {p.id for p, _ in izq} & {p.id for p, _ in der}:
        raise ErrorValidacion("Una misma partida no puede estar en ambos paneles.")
    lados_i, lados_d = {p.lado for p, _ in izq}, {p.lado for p, _ in der}
    if len(lados_i) != 1 or len(lados_d) != 1 or lados_i == lados_d:
        raise ErrorValidacion("Un panel debe contener movimientos deudores y el otro acreedores.")
    if fecha_corte:
        tardias = [p.id for p, _ in izq + der if p.fecha_contable and p.fecha_contable > fecha_corte]
        if tardias:
            raise ErrorValidacion(f"Partidas posteriores a la fecha de corte: {tardias}.")
    cfg = partidas.configuracion(db, empresa_id)
    cuentas = {p.cuenta for p, _ in izq + der}
    entre_cuentas = len(cuentas) > 1
    regla_ec = None
    if entre_cuentas:
        regla_ec = next((r for r in cfg.entre_cuentas
                         if all(any(c.startswith(x) for x in r.get("cuentas", [])) for c in cuentas)), None)
        if regla_ec is None:
            raise ErrorValidacion(f"Compensar entre las cuentas {sorted(cuentas)} requiere una regla autorizada «entre cuentas».")
    terceros = {p.tercero for p, _ in izq + der}
    entre_terceros = len(terceros) > 1
    if entre_terceros:
        if not autorizar_terceros:
            raise ErrorValidacion("Las partidas pertenecen a terceros distintos: requiere autorización expresa y sustento.")
        exigir(db, empresa_id, usuario, "autorizar_terceros")
        if len((justificacion or "").strip()) < 20:
            raise ErrorValidacion("Documente el sustento de la compensación entre terceros (mínimo 20 caracteres).")
    monedas = {p.moneda for p, _ in izq + der}
    moneda = izq[0][0].moneda
    conv = None
    if len(monedas) > 1:
        conv = next((r for r in cfg.conversion if set(r.get("monedas", [])) >= monedas), None)
        if conv is None or not tipo_cambio:
            raise ErrorValidacion("Compensar monedas distintas requiere una regla de conversión autorizada y el tipo de cambio.")
        if len({p.moneda for p, _ in izq}) > 1 or len({p.moneda for p, _ in der}) > 1:
            raise ErrorValidacion("Cada panel debe estar en una sola moneda.")

    def a_moneda_izq(p, m):
        if p.moneda == moneda:
            return m
        return (m / tipo_cambio if p.moneda == "PEN" else m * tipo_cambio).quantize(C2)
    total_i = sum((m for _, m in izq), CERO)
    total_d = sum((a_moneda_izq(p, m) for p, m in der), CERO)
    if total_i != total_d:
        raise ErrorValidacion(f"Los importes no cuadran: {total_i} contra {total_d} ({moneda}).")
    if any(p.clasificacion_pendiente for p, _ in izq + der) and len((justificacion or "").strip()) < 10:
        raise ErrorValidacion("Hay partidas con clasificación pendiente de revisión: indique la justificación.")
    vista = []
    for panel, lista in (("izquierda", izq), ("derecha", der)):
        for p, m in lista:
            disp = (p.importe - p.importe_comprometido).quantize(C2)
            vista.append({"panel": panel, "item_id": p.id, "documento": f"{p.serie}-{p.numero}" if p.serie else p.numero,
                          "cuenta": p.cuenta, "tercero": p.tercero, "moneda": p.moneda, "importe": str(p.importe),
                          "disponible_antes": str(disp), "aplicar": str(m), "disponible_despues": str(disp - m),
                          "estado_despues": "TOTAL" if disp - m == 0 else "PARCIAL"})
    return {"vista": vista, "total": str(total_i), "moneda": moneda, "entre_cuentas": entre_cuentas, "entre_terceros": entre_terceros,
            "regla_entre_cuentas": regla_ec, "conversion": conv, "izq": izq, "der": der, "a_moneda_izq": a_moneda_izq}


def compensar_manual(db: Session, empresa_id: int, usuario: str, izquierda, derecha, *, justificacion: str,
                     autorizar_terceros=False, tipo_cambio=None, fecha_corte=None) -> GrupoCompensacion:
    rol = exigir(db, empresa_id, usuario, "proponer")
    if len((justificacion or "").strip()) < 5:
        raise ErrorValidacion("Indique la justificación de la compensación manual.")
    v = validar_manual(db, empresa_id, usuario, izquierda, derecha, justificacion=justificacion,
                       autorizar_terceros=autorizar_terceros, tipo_cambio=tipo_cambio, fecha_corte=fecha_corte)
    origen_es_izq = v["izq"][0][0].rol == "ORIGEN" or v["der"][0][0].rol != "ORIGEN"
    if not origen_es_izq and tipo_cambio and v["izq"][0][0].moneda != v["der"][0][0].moneda:
        raise ErrorValidacion("Con conversión de moneda coloque los documentos de origen en el panel izquierdo.")
    a, b = (v["izq"], v["der"]) if origen_es_izq else (v["der"], v["izq"])
    conv = v["a_moneda_izq"]
    try:
        with db.begin_nested():
            g = motor.crear_grupo(
                db, empresa_id=empresa_id, run_id=None,
                origenes=[(_it(p), m if origen_es_izq else conv(p, m)) for p, m in a],
                aplicaciones=[(_it(p), conv(p, m) if origen_es_izq else m) for p, m in b],
                regla="Compensación manual" + (" entre cuentas" if v["entre_cuentas"] else "") + (" entre terceros" if v["entre_terceros"] else ""),
                version=(v["regla_entre_cuentas"] or {}).get("version"), nivel=None, puntuacion=100, componentes={"manual": True},
                ambiguo=False, propuesto_por=usuario, origen_propuesta="MANUAL", aprobar=False, justificacion=justificacion.strip(),
                entre_cuentas=v["entre_cuentas"], entre_terceros=v["entre_terceros"], tipo_cambio=tipo_cambio)
    except IntegrityError:
        db.rollback()
        raise Conflicto("Ya existe una aplicación vigente entre esas partidas (aplicación duplicada).")
    db.add(ComentarioCompensacion(empresa_id=empresa_id, grupo_id=g.id, usuario=usuario, texto=justificacion.strip()))
    motor.auditar(db, empresa_id, usuario, "PROPONER_MANUAL", "grupo", g.id,
                  {"izquierda": izquierda, "derecha": derecha, "entre_cuentas": v["entre_cuentas"],
                   "entre_terceros": v["entre_terceros"], "tipo_cambio": str(tipo_cambio) if tipo_cambio else None}, rol)
    db.commit()
    return g


def _grupo(db, empresa_id, grupo_id) -> GrupoCompensacion:
    g = db.get(GrupoCompensacion, grupo_id)
    if g is None or g.empresa_id != empresa_id:
        raise ErrorValidacion("Compensación no encontrada.") if g is None else SinPermiso("Compensación de otra empresa.")
    return g


def aprobar(db: Session, empresa_id: int, grupo_id: int, usuario: str, comentario: str | None = None) -> GrupoCompensacion:
    rol = exigir(db, empresa_id, usuario, "aprobar")
    g = _grupo(db, empresa_id, grupo_id)
    if g.estado != "PROPUESTA":
        raise Conflicto(f"La compensación está {g.estado.lower()}; solo se aprueban propuestas.")
    cfg = partidas.configuracion(db, empresa_id)
    if cfg.general.get("separar_proponer_aprobar", True) and g.propuesto_por.lower() == (usuario or "").lower():
        raise SinPermiso("Separación de funciones: quien propone no puede aprobar la misma compensación.")
    if g.ambiguo:
        raise Conflicto("Coincidencia ambigua: resuélvala eligiendo una alternativa.")
    if g.entre_terceros:
        exigir(db, empresa_id, usuario, "autorizar_terceros")
    for a in db.scalars(select(Aplicacion).where(Aplicacion.grupo_id == g.id, Aplicacion.estado == "PROPUESTA")):
        motor._ajustar(db, a.origen_item_id, empresa_id, CERO, a.importe)
        motor._ajustar(db, a.aplicacion_item_id, empresa_id, CERO, a.importe)
        a.estado = "APROBADA"
    g.estado, g.aprobado_por, g.aprobado_en = "APROBADA", usuario, datetime.now()
    db.add(AprobacionCompensacion(empresa_id=empresa_id, grupo_id=g.id, accion="APROBAR", usuario=usuario, rol=rol, comentario=comentario))
    motor.auditar(db, empresa_id, usuario, "APROBAR", "grupo", g.id, {"comentario": comentario}, rol)
    db.commit()
    return g


def rechazar(db: Session, empresa_id: int, grupo_id: int, usuario: str, comentario: str) -> GrupoCompensacion:
    rol = exigir(db, empresa_id, usuario, "aprobar")
    g = _grupo(db, empresa_id, grupo_id)
    if g.estado != "PROPUESTA":
        raise Conflicto("Solo se rechazan propuestas.")
    if len((comentario or "").strip()) < 5:
        raise ErrorValidacion("Indique el motivo del rechazo.")
    motor._liberar(db, g, "RECHAZADA", aplicado=False)
    g.estado = "RECHAZADA"
    db.add(AprobacionCompensacion(empresa_id=empresa_id, grupo_id=g.id, accion="RECHAZAR", usuario=usuario, rol=rol, comentario=comentario))
    motor.auditar(db, empresa_id, usuario, "RECHAZAR", "grupo", g.id, {"comentario": comentario}, rol)
    db.commit()
    return g


def revertir(db: Session, empresa_id: int, grupo_id: int, usuario: str, motivo: str) -> GrupoCompensacion:
    """Las compensaciones aprobadas no se eliminan: se revierten con motivo y quedan en el historial."""
    rol = exigir(db, empresa_id, usuario, "revertir")
    g = _grupo(db, empresa_id, grupo_id)
    if g.estado != "APROBADA":
        raise Conflicto("Solo se revierten compensaciones aprobadas.")
    if len((motivo or "").strip()) < 10:
        raise ErrorValidacion("Indique el motivo de la reversión (mínimo 10 caracteres).")
    rev = ReversionCompensacion(empresa_id=empresa_id, grupo_id=g.id, motivo=motivo.strip(), usuario=usuario, rol=rol)
    db.add(rev)
    db.flush()
    motor._liberar(db, g, "REVERTIDA", aplicado=True, reversion_id=rev.id)
    g.estado = "REVERTIDA"
    motor.auditar(db, empresa_id, usuario, "REVERTIR", "grupo", g.id, {"motivo": motivo, "reversion_id": rev.id}, rol)
    db.commit()
    return g


def resolver_candidato(db: Session, empresa_id: int, candidato_id: int, usuario: str, opcion: int, justificacion: str) -> GrupoCompensacion:
    """El contador elige una alternativa de una coincidencia ambigua; se crea una propuesta manual."""
    c = db.get(CandidatoCompensacion, candidato_id)
    if c is None or c.empresa_id != empresa_id:
        raise ErrorValidacion("Candidato no encontrado.")
    if c.decision != "REQUIERE_DECISION":
        raise Conflicto("El candidato ya fue resuelto.")
    alternativas = json.loads(c.componentes).get("alternativas", [])
    if not 0 <= opcion < len(alternativas):
        raise ErrorValidacion("Alternativa no válida.")
    aplic = json.loads(c.aplicaciones)[0]
    origenes = alternativas[opcion]["origenes"]
    disp_a = Decimal(aplic["importe"])
    izq, resto = [], disp_a
    for oid in origenes:
        p = db.get(PartidaAbierta, oid)
        d = min((p.importe - p.importe_comprometido).quantize(C2), resto)
        if d > 0:
            izq.append({"item_id": oid, "importe": str(d)})
            resto -= d
    total = sum(Decimal(x["importe"]) for x in izq)
    g = compensar_manual(db, empresa_id, usuario, izq, [{"item_id": aplic["item_id"], "importe": str(total)}],
                         justificacion=justificacion or f"Resolución de coincidencia ambigua #{c.id}")
    c.decision, c.grupo_id = "RESUELTO", g.id
    db.commit()
    return g


def revisar_observacion(db, empresa_id, obs_id, usuario, estado, responsable, comentario):
    exigir(db, empresa_id, usuario, "revisar")
    x = db.get(ExcepcionCompensacion, obs_id)
    if x is None or x.empresa_id != empresa_id:
        raise ErrorValidacion("Observación no encontrada.")
    if estado in ("RESUELTA", "DESCARTADA") and len((comentario or "").strip()) < 5:
        raise ErrorValidacion("Indique el fundamento para resolver o descartar la observación.")
    antes = x.estado
    if estado:
        x.estado = estado
    if responsable is not None:
        x.responsable = responsable or None
    if comentario:
        db.add(ComentarioCompensacion(empresa_id=empresa_id, excepcion_id=x.id, item_id=x.item_id, usuario=usuario, texto=comentario))
    motor.auditar(db, empresa_id, usuario, "REVISAR_OBSERVACION", "excepcion", x.id, {"de": antes, "a": x.estado, "comentario": comentario})
    db.commit()
    return x


def adjuntar(db, empresa_id, grupo_id, usuario, nombre, tipo, contenido: bytes) -> AdjuntoCompensacion:
    exigir(db, empresa_id, usuario, "proponer")
    _grupo(db, empresa_id, grupo_id)
    if not contenido or len(contenido) > 15 * 1024 * 1024:
        raise ErrorValidacion("Adjunto vacío o mayor a 15 MB.")
    carpeta = config.DATA_DIR / "adjuntos_compensacion" / str(int(empresa_id))
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = uuid.uuid4().hex
    (carpeta / ruta).write_bytes(contenido)
    a = AdjuntoCompensacion(empresa_id=empresa_id, grupo_id=grupo_id, nombre=re.sub(r"[^\w.\- ]", "_", nombre or "adjunto")[:120],
                            tipo_contenido=(tipo or "")[:120] or None, tamano=len(contenido),
                            hash=hashlib.sha256(contenido).hexdigest(), ruta=ruta, usuario=usuario)
    db.add(a)
    db.flush()
    motor.auditar(db, empresa_id, usuario, "ADJUNTAR", "grupo", grupo_id, {"adjunto": a.id, "hash": a.hash})
    db.commit()
    return a


def ruta_adjunto(a: AdjuntoCompensacion):
    return config.DATA_DIR / "adjuntos_compensacion" / str(int(a.empresa_id)) / a.ruta
