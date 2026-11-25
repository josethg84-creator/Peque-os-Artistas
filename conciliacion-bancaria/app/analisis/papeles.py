"""Papeles de trabajo preliminares por cuenta.

Congelan los saldos del momento en que se generan (para que la revisión sea reproducible) y
reúnen composición preliminar, hallazgos, comentarios, sustento, conclusión y responsable.
La generación definitiva de anexos conciliados corresponde a la fase 5.
"""
import hashlib
import json
import re
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analisis import navegacion, pcge, saldos
from app.analisis.motor import auditar
from app.core import config
from app.models import AdjuntoAnalisis, AnalisisEjecucion, Hallazgo, PapelTrabajo, RevisionAnalisis

TRANSICIONES = {
    "PENDIENTE": {"EN_REVISION"},
    "EN_REVISION": {"OBSERVADO", "REVISADO", "PENDIENTE"},
    "OBSERVADO": {"SUBSANADO", "EN_REVISION"},
    "SUBSANADO": {"EN_REVISION", "REVISADO"},
    "REVISADO": {"APROBADO", "OBSERVADO", "EN_REVISION"},
    "APROBADO": {"EN_REVISION"},  # reabrir exige comentario
}
EDITABLES = ("comentarios_analista", "documentos_sustento", "conclusion", "responsable", "fecha_revision")
MAX_ADJUNTO_MB = 15


class ErrorPapel(Exception):
    def __init__(self, msg, status=422):
        super().__init__(msg)
        self.status = status


def ultimo_run(db: Session, empresa_id, ejercicio, desde, hasta) -> AnalisisEjecucion | None:
    return db.scalar(select(AnalisisEjecucion).where(
        AnalisisEjecucion.empresa_id == empresa_id, AnalisisEjecucion.ejercicio == ejercicio,
        AnalisisEjecucion.periodo_desde == desde, AnalisisEjecucion.periodo_hasta == hasta,
        AnalisisEjecucion.estado == "COMPLETADO").order_by(AnalisisEjecucion.id.desc()))


def generar(db: Session, empresa_id: int, ejercicio: int, desde: int, hasta: int, cuenta: str, usuario: str) -> PapelTrabajo:
    bal = saldos.balance(db, empresa_id, ejercicio, desde, hasta, comparar=False)
    nodo = next((n for n in bal["nodos"] if n["cuenta"] == cuenta), None)
    if nodo is None:
        raise ErrorPapel(f"La cuenta {cuenta} no tiene saldo ni movimientos en el periodo.", 404)
    perfil = pcge.perfil(cuenta)
    filtros = navegacion.Filtros(cuenta=cuenta)
    composicion = {"criterio": None, "items": [], "nota": "Composición PRELIMINAR: no incluye compensaciones entre documentos."}
    if perfil.cartera or perfil.requiere_tercero:
        t = navegacion.terceros(db, empresa_id, ejercicio, desde, hasta, filtros)
        composicion.update(criterio="Por tercero", items=t["items"][:50])
    else:
        hijos = [n for n in bal["nodos"] if n["padre"] == cuenta]
        if hijos:
            composicion.update(criterio="Por subcuenta", items=[{k: n[k] for k in ("cuenta", "descripcion", "saldo_inicial",
                                                                                   "debe", "haber", "saldo_final")} for n in hijos])
        else:
            t = navegacion.terceros(db, empresa_id, ejercicio, desde, hasta, filtros)
            composicion.update(criterio="Por tercero", items=t["items"][:50])
    run = ultimo_run(db, empresa_id, ejercicio, desde, hasta)
    hall = []
    if run:
        hall = [{"id": h.id, "codigo": h.regla_codigo, "riesgo": h.riesgo, "titulo": h.titulo, "importe": str(h.importe),
                 "estado": h.estado} for h in db.scalars(select(Hallazgo).where(Hallazgo.run_id == run.id,
                                                                                 Hallazgo.cuenta.like(f"{cuenta}%")))]
    papel = db.scalar(select(PapelTrabajo).where(
        PapelTrabajo.empresa_id == empresa_id, PapelTrabajo.ejercicio == ejercicio, PapelTrabajo.periodo_desde == desde,
        PapelTrabajo.periodo_hasta == hasta, PapelTrabajo.cuenta == cuenta))
    if papel and papel.estado == "APROBADO":
        raise ErrorPapel("El papel de trabajo está aprobado; reábralo para actualizar sus saldos.", 409)
    nuevo = papel is None
    if nuevo:
        papel = PapelTrabajo(empresa_id=empresa_id, ejercicio=ejercicio, periodo_desde=desde, periodo_hasta=hasta,
                             cuenta=cuenta, usuario=usuario, estado="PENDIENTE", version=0)
        db.add(papel)
    papel.run_id = run.id if run else None
    papel.descripcion = nodo["descripcion"]
    papel.saldo_inicial, papel.debe = Decimal(nodo["saldo_inicial"]), Decimal(nodo["debe"])
    papel.haber, papel.saldo_final = Decimal(nodo["haber"]), Decimal(nodo["saldo_final"])
    papel.composicion = json.dumps(composicion, ensure_ascii=False, default=str)
    papel.hallazgos = json.dumps(hall, ensure_ascii=False)
    papel.version = (papel.version or 0) + 1
    db.flush()
    auditar(db, empresa_id, usuario, "GENERAR_PAPEL" if nuevo else "ACTUALIZAR_SALDOS_PAPEL", "papel", papel.id,
            {"cuenta": cuenta, "version": papel.version, "saldo_final": nodo["saldo_final"], "preliminar": bal["preliminar"]})
    db.commit()
    return papel


def actualizar(db: Session, papel: PapelTrabajo, datos: dict, usuario: str) -> PapelTrabajo:
    if papel.estado == "APROBADO":
        raise ErrorPapel("El papel de trabajo está aprobado y no admite cambios; reábralo primero.", 409)
    cambios = {}
    for k in EDITABLES:
        if k in datos:
            v = datos[k]
            if k == "fecha_revision" and isinstance(v, str):
                v = date.fromisoformat(v) if v else None
            if getattr(papel, k) != v:
                cambios[k] = {"antes": str(getattr(papel, k)), "despues": str(v)}
                setattr(papel, k, v)
    if cambios:
        auditar(db, papel.empresa_id, usuario, "EDITAR_PAPEL", "papel", papel.id, cambios)
        db.commit()
    return papel


def cambiar_estado(db: Session, papel: PapelTrabajo, nuevo: str, usuario: str, comentario: str | None) -> PapelTrabajo:
    if nuevo not in TRANSICIONES.get(papel.estado, set()):
        raise ErrorPapel(f"No se puede pasar de {papel.estado} a {nuevo}.", 409)
    if nuevo in ("REVISADO", "APROBADO") and not (papel.conclusion or "").strip():
        raise ErrorPapel("Registre la conclusión antes de marcar el papel como revisado o aprobado.")
    if nuevo == "APROBADO":
        if papel.responsable and papel.responsable == usuario:
            raise ErrorPapel("La aprobación debe hacerla una persona distinta del responsable del análisis.", 409)
        if not papel.fecha_revision:
            papel.fecha_revision = date.today()
    if papel.estado == "APROBADO" and not (comentario or "").strip():
        raise ErrorPapel("Indique el motivo para reabrir un papel aprobado.")
    db.add(RevisionAnalisis(empresa_id=papel.empresa_id, entidad="PAPEL", entidad_id=papel.id, estado_anterior=papel.estado,
                            estado_nuevo=nuevo, responsable=papel.responsable, comentario=comentario, usuario=usuario))
    auditar(db, papel.empresa_id, usuario, "ESTADO_PAPEL", "papel", papel.id, {"de": papel.estado, "a": nuevo, "comentario": comentario})
    papel.estado = nuevo
    db.commit()
    return papel


def guardar_adjunto(db: Session, papel: PapelTrabajo, nombre: str, tipo: str | None, contenido: bytes, usuario: str) -> AdjuntoAnalisis:
    if papel.estado == "APROBADO":
        raise ErrorPapel("El papel aprobado no admite nuevos adjuntos.", 409)
    if not contenido:
        raise ErrorPapel("El archivo está vacío.")
    if len(contenido) > MAX_ADJUNTO_MB * 1024 * 1024:
        raise ErrorPapel(f"El adjunto supera {MAX_ADJUNTO_MB} MB.", 413)
    limpio = re.sub(r"[^\w.\- ]", "_", nombre or "adjunto")[:120] or "adjunto"
    carpeta = config.DATA_DIR / "adjuntos" / str(int(papel.empresa_id))
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / uuid.uuid4().hex
    destino.write_bytes(contenido)
    adj = AdjuntoAnalisis(empresa_id=papel.empresa_id, papel_id=papel.id, nombre=limpio, tipo_contenido=(tipo or "")[:120] or None,
                          tamano=len(contenido), hash=hashlib.sha256(contenido).hexdigest(), ruta=str(destino.name), usuario=usuario)
    db.add(adj)
    db.flush()
    auditar(db, papel.empresa_id, usuario, "ADJUNTAR", "papel", papel.id, {"adjunto": adj.id, "nombre": limpio, "hash": adj.hash})
    db.commit()
    return adj


def ruta_adjunto(adj: AdjuntoAnalisis):
    return config.DATA_DIR / "adjuntos" / str(int(adj.empresa_id)) / adj.ruta


def papel_dict(p: PapelTrabajo, adjuntos=None, revisiones=None) -> dict:
    d = {c.key: getattr(p, c.key) for c in PapelTrabajo.__table__.columns}
    for k, v in list(d.items()):
        if isinstance(v, Decimal):
            d[k] = str(v)
        elif hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    d["composicion"] = json.loads(p.composicion) if p.composicion else None
    d["hallazgos"] = json.loads(p.hallazgos) if p.hallazgos else []
    d["transiciones"] = sorted(TRANSICIONES.get(p.estado, set()))
    if adjuntos is not None:
        d["adjuntos"] = [{"id": a.id, "nombre": a.nombre, "tamano": a.tamano, "usuario": a.usuario, "hash": a.hash,
                          "creado_en": a.creado_en.isoformat() if a.creado_en else None} for a in adjuntos]
    if revisiones is not None:
        d["revisiones"] = [{"de": r.estado_anterior, "a": r.estado_nuevo, "usuario": r.usuario, "comentario": r.comentario,
                            "fecha": r.creado_en.isoformat() if r.creado_en else None} for r in revisiones]
    return d
