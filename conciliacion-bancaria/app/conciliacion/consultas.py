"""Consultas de lectura: listados paginados en servidor, paneles de registros, coincidencias, diferencias,
tablero, historial y reconstrucción del estado a una fecha. No modifica datos."""
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, or_, select

from app.conciliacion import servicio
from app.models import (AdjuntoConciliacion, AprobacionConciliacion, AsignacionConciliacion, AsignacionRegistro, AuditoriaConciliacion,
                        Conciliacion, DiferenciaConciliacion, FuenteConciliacion, GrupoConciliacion, MatchConciliacion,
                        RegistroFuente, ReversionConciliacion, RevisionConciliacion, TipoConciliacion, VersionConciliacion)

CERO = Decimal(0)
TRAMOS = ((30, "0-30 días"), (60, "31-60 días"), (90, "61-90 días"), (180, "91-180 días"), (None, "Más de 180 días"))
ABIERTAS = ("DETECTADO", "PENDIENTE_REVISION", "EN_ANALISIS", "JUSTIFICADO", "PENDIENTE_REGULARIZACION", "REABIERTO")


def _j(v):
    return servicio._j(v)


def fila(o, excluir=()) -> dict:
    return {c.key: _j(getattr(o, c.key)) for c in o.__table__.columns if c.key not in excluir}


def mascara(x: dict) -> dict:
    """Oculta datos personales (planillas) a usuarios no autorizados: se conservan importes y conceptos."""
    t = x.get("tercero")
    if t:
        x["tercero"] = "•" * max(len(t) - 2, 0) + t[-2:]
    if x.get("razon_social"):
        x["razon_social"] = f"Trabajador ···{(t or '')[-2:]}" if t else "Trabajador (reservado)"
    if isinstance(x.get("datos"), dict):
        x["datos"] = {k: v for k, v in x["datos"].items() if k not in ("documento_identidad", "nombre", "cuenta_sueldo", "dni")}
    if "descripcion" in x and x.get("descripcion"):
        x["descripcion"] = "(reservado)"
    return x


def paginar(db, q, pagina, por_pagina, cnt=None):
    por_pagina = max(1, min(int(por_pagina or 50), 2000))
    pagina = max(1, int(pagina or 1))
    total = db.scalar(cnt if cnt is not None else select(func.count()).select_from(q.order_by(None).subquery()))
    return total, q.limit(por_pagina).offset((pagina - 1) * por_pagina), pagina, por_pagina


def conciliacion(db, c: Conciliacion, ve_personal: bool) -> dict:
    d = fila(c)
    d["ambito"] = json.loads(c.ambito or "{}")
    d["resumen"] = json.loads(c.resumen) if c.resumen else None
    d["tiempos"] = json.loads(c.tiempos) if c.tiempos else None
    t = db.scalar(select(TipoConciliacion).where(TipoConciliacion.codigo == c.tipo_codigo))
    d["tipo_nombre"] = t.nombre if t else c.tipo_codigo
    d["datos_personales"] = bool(t and t.datos_personales)
    d["ve_datos_personales"] = ve_personal
    v = db.get(VersionConciliacion, c.version_id) if c.version_id else None
    d["version"] = None
    if v:
        d["version"] = {"id": v.id, "numero": v.numero, "inmutable": v.inmutable, "generado_en": _j(v.generado_en), "generado_por": v.generado_por,
                        "hash": v.hash_contenido, "fuentes": json.loads(v.fuentes or "{}"), "reporte": json.loads(v.reporte or "{}"),
                        "configuracion": json.loads(v.configuracion or "{}")}
        if not ve_personal and d["datos_personales"]:
            d["version"]["reporte"] = {"tipo": c.tipo_codigo, "nota": "Detalle reservado al responsable de planillas."}
    d["fuentes"] = [fila(f, ("ruta_archivo",)) for f in db.scalars(select(FuenteConciliacion).where(FuenteConciliacion.run_id == c.id)
                                                                   .order_by(FuenteConciliacion.lado, FuenteConciliacion.id.desc()))]
    d["versiones"] = [{"id": x.id, "numero": x.numero, "generado_en": _j(x.generado_en), "generado_por": x.generado_por, "inmutable": x.inmutable,
                       "motivo": x.motivo, "estado_al_cerrar": x.estado_al_cerrar}
                      for x in db.scalars(select(VersionConciliacion).where(VersionConciliacion.run_id == c.id).order_by(VersionConciliacion.numero))]
    d["pendientes"] = {"ambiguas": 0, "propuestas": 0, "criticas_abiertas": 0, "diferencias_abiertas": 0}
    if v:
        d["pendientes"]["ambiguas"] = db.scalar(select(func.count()).select_from(GrupoConciliacion)
                                                .where(GrupoConciliacion.version_id == v.id, GrupoConciliacion.estado == "AMBIGUA"))
        d["pendientes"]["propuestas"] = db.scalar(select(func.count()).select_from(GrupoConciliacion)
                                                  .where(GrupoConciliacion.version_id == v.id, GrupoConciliacion.estado == "PROPUESTA"))
        base = select(func.count()).select_from(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id == v.id,
                                                                              DiferenciaConciliacion.estado.in_(ABIERTAS))
        d["pendientes"]["diferencias_abiertas"] = db.scalar(base)
        d["pendientes"]["criticas_abiertas"] = db.scalar(base.where(DiferenciaConciliacion.prioridad == "CRITICO"))
    return d


def listar(db, empresa_id, f: dict, usuario) -> dict:
    q = select(Conciliacion).where(Conciliacion.empresa_id == empresa_id)
    for k in ("tipo_codigo", "estado", "ejercicio", "periodo", "responsable", "plantilla_id", "fecha_corte"):
        if f.get(k) not in (None, ""):
            q = q.where(getattr(Conciliacion, k) == f[k])
    if f.get("buscar"):
        q = q.where(Conciliacion.nombre.ilike(f"%{f['buscar']}%"))
    for k in ("cuenta", "moneda", "centro_costo", "proyecto", "cuenta_bancaria_id"):
        if f.get(k):
            q = q.where(Conciliacion.ambito.like(f'%"{k}": {json.dumps(f[k])}%'))
    r, _ = servicio.rol(db, empresa_id, usuario)
    if r in ("TESORERO", "PLANILLAS"):  # roles operativos ven solo sus tipos
        tipos = [t.codigo for t in db.scalars(select(TipoConciliacion)) if r in (t.roles_operacion or "").split(",")]
        q = q.where(Conciliacion.tipo_codigo.in_(tipos))
    total, q, pagina, pp = paginar(db, q.order_by(Conciliacion.fecha_corte.desc(), Conciliacion.id.desc()), f.get("pagina"), f.get("por_pagina"))
    items = []
    for c in db.scalars(q):
        x = fila(c, ("tiempos",))
        x["ambito"] = json.loads(c.ambito or "{}")
        x["resumen"] = json.loads(c.resumen) if c.resumen else None
        items.append(x)
    return {"total": total, "pagina": pagina, "por_pagina": pp, "items": items}


def registros(db, c: Conciliacion, f: dict, ve_personal: bool, version_id=None) -> dict:
    vid = version_id or c.version_id
    lado = f.get("lado") or "A"
    q = select(RegistroFuente, AsignacionRegistro).outerjoin(
        AsignacionRegistro, and_(AsignacionRegistro.registro_id == RegistroFuente.id, AsignacionRegistro.version_id == vid,
                                 *([AsignacionRegistro.pasada == f["pasada"]] if f.get("pasada") else [])))
    fuentes_ids = select(FuenteConciliacion.id).where(FuenteConciliacion.run_id == c.id, FuenteConciliacion.lado == lado)
    if version_id and version_id != c.version_id:
        v = db.get(VersionConciliacion, version_id)
        fuentes_ids = [x["id"] for x in json.loads(v.fuentes or "{}").values()]
    else:
        fuentes_ids = fuentes_ids.where(FuenteConciliacion.vigente.is_(True))
    q = q.where(RegistroFuente.run_id == c.id, RegistroFuente.lado == lado, RegistroFuente.fuente_id.in_(fuentes_ids))
    if f.get("estado"):
        q = q.where(AsignacionRegistro.estado.in_(f["estado"].split(",")))
    if f.get("buscar"):
        b = f"%{f['buscar']}%"
        doc = f["buscar"].strip().split("-", 1)
        por_doc = [and_(RegistroFuente.serie.ilike(doc[0]), RegistroFuente.numero.ilike(doc[1].lstrip("0") or "0"))] if len(doc) == 2 else []
        q = q.where(or_(*por_doc, RegistroFuente.serie.ilike(b), RegistroFuente.numero.ilike(b), RegistroFuente.descripcion.ilike(b),
                        RegistroFuente.referencia.ilike(b),
                        RegistroFuente.operacion.ilike(b), RegistroFuente.tercero.ilike(b), RegistroFuente.razon_social.ilike(b),
                        RegistroFuente.clave_registro.ilike(b)))
    for k in ("cuenta", "tercero", "moneda", "concepto", "centro_costo", "proyecto"):
        if f.get(k):
            q = q.where(getattr(RegistroFuente, k).like(f"{f[k]}%"))
    if f.get("desde"):
        q = q.where(RegistroFuente.fecha >= f["desde"])
    if f.get("hasta"):
        q = q.where(RegistroFuente.fecha <= f["hasta"])
    if f.get("importe"):
        imp = Decimal(str(f["importe"]))
        q = q.where(func.abs(RegistroFuente.importe) == abs(imp))
    total, qp, pagina, pp = paginar(db, q.order_by(RegistroFuente.orden), f.get("pagina"), f.get("por_pagina"))
    items = []
    for r, a in db.execute(qp):
        x = fila(r)
        x["datos"] = json.loads(r.datos) if r.datos else {}
        x["asignacion"] = {"estado": a.estado, "total": _j(a.total), "conciliado": _j(a.conciliado), "pendiente": _j(a.total - a.conciliado),
                           "pasada": a.pasada, "lock": a.lock} if a else None
        if r.personal and not ve_personal:
            x = mascara(x)
        items.append(x)
    sub = q.with_only_columns(RegistroFuente.importe, AsignacionRegistro.total, AsignacionRegistro.conciliado).order_by(None).subquery()
    s = db.execute(select(func.coalesce(func.sum(sub.c.importe), 0), func.coalesce(func.sum(sub.c.total), 0),
                          func.coalesce(func.sum(sub.c.conciliado), 0))).one()
    return {"total": total, "pagina": pagina, "por_pagina": pp, "items": items,
            "totales": {"importe": _j(Decimal(str(s[0]))), "absoluto": _j(Decimal(str(s[1]))), "conciliado": _j(Decimal(str(s[2]))),
                        "pendiente": _j(Decimal(str(s[1])) - Decimal(str(s[2])))}}


def grupos(db, c: Conciliacion, f: dict, ve_personal: bool, version_id=None) -> dict:
    vid = version_id or c.version_id
    q = select(GrupoConciliacion).where(GrupoConciliacion.version_id == vid)
    for k in ("estado", "tipo", "pasada", "origen"):
        if f.get(k):
            q = q.where(getattr(GrupoConciliacion, k).in_(f[k].split(",")))
    total, qp, pagina, pp = paginar(db, q.order_by(GrupoConciliacion.estado == "CONFIRMADA", GrupoConciliacion.id), f.get("pagina"), f.get("por_pagina"))
    gs = db.scalars(qp).all()
    ms = defaultdict(list)
    if gs:
        for m, r in db.execute(select(MatchConciliacion, RegistroFuente).join(RegistroFuente, RegistroFuente.id == MatchConciliacion.registro_id)
                               .where(MatchConciliacion.grupo_id.in_([g.id for g in gs]))):
            x = {"registro_id": r.id, "lado": m.lado, "importe_aplicado": _j(m.importe), "importe": _j(r.importe), "fecha": _j(r.fecha),
                 "documento": "-".join(p for p in (r.serie, r.numero) if p) or r.operacion or r.referencia, "descripcion": r.descripcion,
                 "tercero": r.tercero, "razon_social": r.razon_social, "moneda": r.moneda, "personal": r.personal}
            ms[m.grupo_id].append(mascara(x) if r.personal and not ve_personal else x)
    items = []
    for g in gs:
        x = fila(g, ("huellas",))
        x["detalle"] = json.loads(g.detalle or "{}")
        x["registros"] = ms[g.id]
        items.append(x)
    return {"total": total, "pagina": pagina, "por_pagina": pp, "items": items}


def _tramo(dias):
    for lim, n in TRAMOS:
        if lim is None or dias <= lim:
            return n


def diferencia_dict(d: DiferenciaConciliacion, ve_personal: bool, hoy: date | None = None) -> dict:
    x = fila(d)
    x["evidencia"] = json.loads(d.evidencia or "{}")
    hoy = hoy or date.today()
    x["antiguedad_dias"] = (hoy - d.fecha_deteccion).days if d.fecha_deteccion else None
    x["tramo"] = _tramo(x["antiguedad_dias"] or 0)
    x["vencida"] = bool(d.fecha_limite and d.fecha_limite < hoy and d.estado in ABIERTAS)
    if d.personal and not ve_personal:
        x = mascara(x)
        x["explicacion"] = "Diferencia de planilla (detalle reservado)."
        x["evidencia"] = {"registros": [], "reservado": True}
    return x


def filtro_diferencias(q, f: dict):
    for k in ("clasificacion", "prioridad", "estado", "tipo_conciliacion", "responsable"):
        if f.get(k):
            q = q.where(getattr(DiferenciaConciliacion, k).in_(str(f[k]).split(",")))
    if f.get("run_id"):
        q = q.where(DiferenciaConciliacion.run_id == int(f["run_id"]))
    if f.get("abiertas"):
        q = q.where(DiferenciaConciliacion.estado.in_(ABIERTAS))
    if f.get("trasladadas"):
        q = q.where(DiferenciaConciliacion.anterior_id.is_not(None))
    if f.get("dentro_tolerancia") not in (None, ""):
        q = q.where(DiferenciaConciliacion.dentro_tolerancia.is_(str(f["dentro_tolerancia"]).lower() in ("1", "true", "si")))
    for k in ("cuenta", "tercero"):
        if f.get(k):
            q = q.where(getattr(DiferenciaConciliacion, k).like(f"{f[k]}%"))
    if f.get("buscar"):
        b = f"%{f['buscar']}%"
        q = q.where(or_(DiferenciaConciliacion.codigo.ilike(b), DiferenciaConciliacion.documento.ilike(b), DiferenciaConciliacion.explicacion.ilike(b),
                        DiferenciaConciliacion.razon_social.ilike(b)))
    return q


def vigentes(db, empresa_id):
    """Ids de las versiones vigentes (las diferencias de versiones anteriores son historia)."""
    return select(Conciliacion.version_id).where(Conciliacion.empresa_id == empresa_id, Conciliacion.version_id.is_not(None))


def diferencias(db, empresa_id, f: dict, ve_personal: bool, usuario=None) -> dict:
    q = select(DiferenciaConciliacion).where(DiferenciaConciliacion.empresa_id == empresa_id)
    q = q.where(DiferenciaConciliacion.version_id == int(f["version_id"])) if f.get("version_id") else \
        q.where(DiferenciaConciliacion.version_id.in_(vigentes(db, empresa_id)))
    q = filtro_diferencias(q, f)
    if usuario:
        r, _ = servicio.rol(db, empresa_id, usuario)
        if r in ("TESORERO", "PLANILLAS"):
            tipos = [t.codigo for t in db.scalars(select(TipoConciliacion)) if r in (t.roles_operacion or "").split(",")]
            q = q.where(DiferenciaConciliacion.tipo_conciliacion.in_(tipos))
    orden = {"importe": func.abs(DiferenciaConciliacion.importe).desc(), "antiguedad": DiferenciaConciliacion.fecha_deteccion}.get(
        f.get("orden"), DiferenciaConciliacion.id)
    total, qp, pagina, pp = paginar(db, q.order_by(orden, DiferenciaConciliacion.id), f.get("pagina"), f.get("por_pagina"))
    sub = q.with_only_columns(DiferenciaConciliacion.importe).order_by(None).subquery()
    imp = db.scalar(select(func.coalesce(func.sum(func.abs(sub.c.importe)), 0)))
    return {"total": total, "pagina": pagina, "por_pagina": pp, "importe_total": _j(Decimal(str(imp))),
            "items": [diferencia_dict(d, ve_personal) for d in db.scalars(qp)]}


def historial_diferencia(db, d: DiferenciaConciliacion, ve_personal) -> dict:
    cadena, x = [], d
    vistos = set()
    while x and x.id not in vistos:  # versiones y periodos anteriores de la misma incidencia
        vistos.add(x.id)
        c = db.get(Conciliacion, x.run_id)
        cadena.append({"id": x.id, "codigo": x.codigo, "conciliacion": c.nombre, "fecha_corte": _j(c.fecha_corte), "importe": _j(x.importe),
                       "estado": x.estado, "version_id": x.version_id})
        x = db.get(DiferenciaConciliacion, x.anterior_id) if x.anterior_id else None
    revs = [fila(r) for r in db.scalars(select(RevisionConciliacion).where(RevisionConciliacion.entidad == "DIFERENCIA",
                                                                           RevisionConciliacion.entidad_id.in_([c["id"] for c in cadena]))
                                        .order_by(RevisionConciliacion.id))]
    adj = [fila(a, ("ruta",)) for a in db.scalars(select(AdjuntoConciliacion).where(AdjuntoConciliacion.diferencia_id.in_([c["id"] for c in cadena])))]
    if d.personal and not ve_personal:
        adj = [a for a in adj if not a["confidencial"]]
    return {"diferencia": diferencia_dict(d, ve_personal), "cadena": cadena, "revisiones": revs, "adjuntos": adj}


def historial(db, c: Conciliacion) -> dict:
    return {"revisiones": [fila(r) for r in db.scalars(select(RevisionConciliacion).where(RevisionConciliacion.run_id == c.id,
                                                                                           RevisionConciliacion.entidad != "DIFERENCIA")
                                                       .order_by(RevisionConciliacion.id))],
            "aprobaciones": [fila(a) for a in db.scalars(select(AprobacionConciliacion).where(AprobacionConciliacion.run_id == c.id)
                                                         .order_by(AprobacionConciliacion.id))],
            "reversiones": [fila(r) for r in db.scalars(select(ReversionConciliacion).where(ReversionConciliacion.run_id == c.id)
                                                        .order_by(ReversionConciliacion.id))],
            "auditoria": [fila(a) for a in db.scalars(select(AuditoriaConciliacion).where(AuditoriaConciliacion.run_id == c.id)
                                                      .order_by(AuditoriaConciliacion.id.desc()).limit(500))]}


def a_fecha(db, c: Conciliacion, fecha: date, ve_personal: bool) -> dict:
    """Reconstruye cómo estaba la conciliación al final de `fecha`: versión vigente, estado y estado de cada diferencia."""
    hasta = datetime.combine(fecha + timedelta(days=1), datetime.min.time())
    v = db.scalar(select(VersionConciliacion).where(VersionConciliacion.run_id == c.id, VersionConciliacion.generado_en < hasta)
                  .order_by(VersionConciliacion.numero.desc()))
    if not v:
        return {"fecha": _j(fecha), "existia": False, "nota": "La conciliación no tenía versiones generadas a esa fecha."}
    ult = db.scalar(select(RevisionConciliacion).where(RevisionConciliacion.run_id == c.id, RevisionConciliacion.entidad == "CONCILIACION",
                                                        RevisionConciliacion.creado_en < hasta).order_by(RevisionConciliacion.id.desc()))
    estado = ult.a_estado if ult else "EJECUTADA"
    difs = db.scalars(select(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id == v.id, DiferenciaConciliacion.creado_en < hasta)).all()
    revs = defaultdict(list)
    if difs:
        for r in db.scalars(select(RevisionConciliacion).where(RevisionConciliacion.entidad == "DIFERENCIA",
                                                               RevisionConciliacion.entidad_id.in_([d.id for d in difs]),
                                                               RevisionConciliacion.creado_en < hasta).order_by(RevisionConciliacion.id)):
            revs[r.entidad_id].append(r)
    items, cont = [], Counter()
    for d in difs:
        x = diferencia_dict(d, ve_personal, fecha)
        hist = revs.get(d.id)
        if hist:
            x["estado"] = hist[-1].a_estado
        else:  # estado heredado al crearse (continuidad) o DETECTADO; los cambios posteriores a la fecha no se consideran
            primero = db.scalar(select(RevisionConciliacion.de_estado).where(RevisionConciliacion.entidad == "DIFERENCIA",
                                                                             RevisionConciliacion.entidad_id == d.id).order_by(RevisionConciliacion.id))
            x["estado"] = primero or d.estado
        cont[x["estado"]] += 1
        items.append(x)
    return {"fecha": _j(fecha), "existia": True, "version": {"numero": v.numero, "generado_en": _j(v.generado_en), "inmutable_hoy": v.inmutable},
            "estado": estado, "resumen": json.loads(v.resumen or "{}"), "diferencias": items, "estados": dict(cont)}


def tablero(db, empresa_id, ejercicio: int | None, periodo: int | None, usuario) -> dict:
    q = select(Conciliacion).where(Conciliacion.empresa_id == empresa_id)
    if ejercicio:
        q = q.where(Conciliacion.ejercicio == ejercicio)
    if periodo:
        q = q.where(Conciliacion.periodo == periodo)
    r, _ = servicio.rol(db, empresa_id, usuario)
    ve_personal = servicio.ve_datos_personales(db, empresa_id, usuario)
    runs = db.scalars(q).all()
    progs = db.scalars(select(AsignacionConciliacion).where(AsignacionConciliacion.empresa_id == empresa_id, AsignacionConciliacion.tipo == "PROGRAMADA",
                                                            AsignacionConciliacion.activa.is_(True))).all()
    est = Counter(c.estado for c in runs)
    kpi = {"programadas": len(progs), "creadas": len(runs), "ejecutadas": sum(1 for c in runs if c.version_id),
           "aprobadas": est["APROBADA"] + est["CERRADA"], "pendientes": sum(1 for c in runs if c.estado not in ("APROBADA", "CERRADA")),
           "en_revision": est["EN_REVISION"] + est["REVISADA"], "observadas": est["OBSERVADA"], "con_error": sum(1 for c in runs if c.estado_proceso == "ERROR")}
    reg, imp = Counter(), Counter()
    por_tipo = defaultdict(lambda: {"conciliaciones": 0, "registros": 0, "conciliados": 0, "diferencias": 0, "importe_pendiente": CERO})
    for c in runs:
        res = json.loads(c.resumen) if c.resumen else {}
        t = por_tipo[c.tipo_codigo]
        t["conciliaciones"] += 1
        for k, n in (res.get("asignaciones") or {}).items():
            reg[k] += n
            t["registros"] += n
            if k == "CONCILIADO":
                t["conciliados"] += n
        for k, v in (res.get("importes") or {}).items():
            imp[k] += Decimal(v)
        t["diferencias"] += res.get("diferencias", 0)
    total_reg, total_imp = sum(reg.values()), sum(imp.values(), CERO)
    vids = [c.version_id for c in runs if c.version_id]
    difs = db.scalars(select(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id.in_(vids or [0]))).all()
    abiertas = [d for d in difs if d.estado in ABIERTAS]
    # una misma partida puede aparecer en conciliaciones relacionadas (p. ej. compras y detracciones): el importe neto no la duplica
    unicas = {}
    for d in abiertas:
        k = (d.documento or d.huella, d.tercero or "", abs(d.importe))
        unicas.setdefault(k, d)
    hoy = date.today()
    aging = Counter()
    aging_imp = Counter()
    for d in abiertas:
        n = _tramo((hoy - d.fecha_deteccion).days if d.fecha_deteccion else 0)
        aging[n] += 1
        aging_imp[n] += abs(d.importe)
    for d in abiertas:
        por_tipo[d.tipo_conciliacion]["importe_pendiente"] += abs(d.importe)
    por_cuenta = Counter()
    for d in abiertas:
        por_cuenta[(d.cuenta or "(sin cuenta)")[:4]] += abs(d.importe)
    recurrentes = sorted([d for d in abiertas if d.recurrencias > 0], key=lambda d: -d.recurrencias)[:10]
    por_resp = defaultdict(lambda: {"asignadas": 0, "aprobadas": 0, "diferencias_abiertas": 0})
    for c in runs:
        x = por_resp[c.responsable or "(sin asignar)"]
        x["asignadas"] += 1
        x["aprobadas"] += c.estado in ("APROBADA", "CERRADA")
    for d in abiertas:
        por_resp[d.responsable or "(sin asignar)"]["diferencias_abiertas"] += 1
    mensual = defaultdict(lambda: {"conciliaciones": 0, "aprobadas": 0, "diferencias": 0})
    for c in db.scalars(select(Conciliacion).where(Conciliacion.empresa_id == empresa_id, *( [Conciliacion.ejercicio == ejercicio] if ejercicio else []))):
        m = mensual[f"{c.ejercicio}-{c.periodo:02d}"]
        m["conciliaciones"] += 1
        m["aprobadas"] += c.estado in ("APROBADA", "CERRADA")
        m["diferencias"] += (json.loads(c.resumen).get("diferencias", 0) if c.resumen else 0)
    tipos_vis = None
    if r in ("TESORERO", "PLANILLAS"):
        tipos_vis = {t.codigo for t in db.scalars(select(TipoConciliacion)) if r in (t.roles_operacion or "").split(",")}
    return {
        "kpi": {**kpi, "registros_comparados": total_reg, "registros_conciliados": reg["CONCILIADO"], "registros_parciales": reg["PARCIAL"],
                "registros_pendientes": reg["PENDIENTE"] + reg["AMBIGUO"] + reg["PROPUESTO"], "duplicados": reg["DUPLICADO"],
                "pct_conciliado_cantidad": round(100 * reg["CONCILIADO"] / total_reg, 2) if total_reg else None,
                "pct_conciliado_importe": float(round(100 * imp["CONCILIADO"] / total_imp, 2)) if total_imp else None,
                "importe_pendiente_bruto": _j(sum((abs(d.importe) for d in abiertas), CERO)),
                "importe_pendiente_neto": _j(sum((abs(d.importe) for d in unicas.values()), CERO)),
                "diferencias_abiertas": len(abiertas), "diferencias_duplicadas_entre_conciliaciones": len(abiertas) - len(unicas),
                "diferencias_criticas": sum(1 for d in abiertas if d.prioridad == "CRITICO"),
                "dentro_tolerancia": sum(1 for d in abiertas if d.dentro_tolerancia),
                "avance_cierre": round(100 * kpi["aprobadas"] / len(runs), 2) if runs else None},
        "nota": "Los porcentajes por cantidad de registros y por importe se calculan por separado; el importe neto no duplica una misma partida "
                "observada en conciliaciones relacionadas.",
        "por_tipo": [{"tipo": k, **{kk: _j(vv) for kk, vv in v.items()}} for k, v in sorted(por_tipo.items()) if tipos_vis is None or k in tipos_vis],
        "por_estado": dict(est), "por_prioridad": dict(Counter(d.prioridad for d in abiertas)),
        "por_clasificacion": dict(Counter(d.clasificacion for d in abiertas)),
        "por_estado_diferencia": dict(Counter(d.estado for d in difs)),
        "antiguedad": [{"tramo": n, "cantidad": aging[n], "importe": _j(aging_imp[n])} for _, n in TRAMOS],
        "por_cuenta": [{"cuenta": k, "importe": _j(v)} for k, v in por_cuenta.most_common(12)],
        "mensual": [{"periodo": k, **v} for k, v in sorted(mensual.items())],
        "por_responsable": [{"responsable": k, **v} for k, v in sorted(por_resp.items())],
        "recurrentes": [diferencia_dict(d, ve_personal) for d in recurrentes]}
