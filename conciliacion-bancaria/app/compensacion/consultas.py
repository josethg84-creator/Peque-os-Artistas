"""Consultas sobre la compensación: antigüedad real, anticipos, tributos, dashboard y reportes."""
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analisis import antiguedad as ant3
from app.analisis.exportar import Reporte, Tabla
from app.compensacion import partidas
from app.compensacion.motor import CERO
from app.models import Aplicacion, ExcepcionCompensacion, GrupoCompensacion, PartidaAbierta

TIPO_CARTERA = lambda cuenta: "CXC" if cuenta[:1] == "1" else "CXP"  # noqa: E731


def _fin_mes(a: int, m: int) -> date:
    s = date(a + (m == 12), m % 12 + 1, 1)
    return date.fromordinal(s.toordinal() - 1)


def antiguedad(db: Session, empresa_id: int, corte: date, *, base="VENCIMIENTO", agrupar="tercero", cuentas=None,
               config_id=None, tercero=None) -> dict:
    """Antigüedad de los saldos REALMENTE pendientes (después de compensaciones aprobadas a la fecha de corte).
    Los documentos sin fecha de vencimiento van a su propio tramo (no se suponen vencimientos)."""
    if isinstance(cuentas, str):
        cuentas = [c.strip() for c in cuentas.split(",") if c.strip()]
    cfg = ant3.configuracion(db, empresa_id, config_id)
    rangos = json.loads(cfg.rangos)
    nombres = ant3.etiquetas(rangos) + ["Sin fecha de vencimiento determinada"]
    sin_fecha = len(nombres) - 1
    comp = partidas.composicion(db, empresa_id, corte, cuentas=cuentas, tercero=tercero, solo_pendientes=True, incluir_propuestas=False)
    grupos: dict[str, dict] = {}
    docs, a_favor = [], defaultdict(lambda: CERO)
    for e in comp:
        it = e.item
        if it["rol"] == "APLICACION":  # saldos a favor (pagos, anticipos, notas de crédito sin aplicar)
            a_favor[TIPO_CARTERA(it["cuenta"])] += e.pendiente_mn
            continue
        fb = it["fecha_vencimiento"] if base == "VENCIMIENTO" else it["fecha_documento"]
        if fb is None:
            t, dias = sin_fecha, None
        else:
            dias = (corte - fb).days
            t = ant3.tramo(dias, rangos)
        clave = {"tercero": it["tercero"] or "(sin tercero)", "cuenta": it["cuenta"], "moneda": it["moneda"],
                 "proyecto": it["proyecto"] or "(sin proyecto)", "centro_costo": it["centro_costo"] or "(sin centro de costo)",
                 "documento": f"{it['serie']}-{it['numero']}" if it["serie"] else (it["numero"] or f"partida {it['id']}")}[agrupar]
        g = grupos.setdefault(clave, {"clave": clave, "razon_social": it["razon_social"], "tramos": [CERO] * len(nombres),
                                      "total": CERO, "documentos": 0, "cartera": TIPO_CARTERA(it["cuenta"])})
        g["tramos"][t] += e.pendiente_mn
        g["total"] += e.pendiente_mn
        g["documentos"] += 1
        docs.append({"item_id": it["id"], "cuenta": it["cuenta"], "tercero": it["tercero"], "razon_social": it["razon_social"],
                     "documento": f"{it['serie']}-{it['numero']}" if it["serie"] else it["numero"], "clase": it["clase"],
                     "moneda": it["moneda"], "pendiente": str(e.pendiente), "pendiente_mn": str(e.pendiente_mn),
                     "fecha_documento": it["fecha_documento"].isoformat(), "fecha_vencimiento": it["fecha_vencimiento"].isoformat() if it["fecha_vencimiento"] else None,
                     "dias": dias, "tramo": t, "tramo_nombre": nombres[t], "estado_cancelacion": e.cancelacion,
                     "origen_datos": it["origen_datos"]})
    tot = [CERO] * len(nombres)
    for g in grupos.values():
        tot = [a + b for a, b in zip(tot, g["tramos"])]
    filas = sorted(grupos.values(), key=lambda x: -x["total"])
    for g in filas:
        g["tramos"] = [str(v) for v in g["tramos"]]
        g["total"] = str(g["total"])
    return {"fecha_corte": corte.isoformat(), "base": base, "agrupar": agrupar, "tramos": nombres, "totales": [str(v) for v in tot],
            "total": str(sum(tot, CERO)), "grupos": filas, "documentos": sorted(docs, key=lambda d: -(d["dias"] or -1)),
            "saldos_a_favor_sin_aplicar": {k: str(v) for k, v in a_favor.items()},
            "nota": "Saldos pendientes después de las compensaciones APROBADAS a la fecha de corte, en moneda nacional."}


def anticipos(db: Session, empresa_id: int, corte: date) -> list[dict]:
    comp = partidas.composicion(db, empresa_id, corte, incluir_propuestas=True)
    rel = _relacionados(db, empresa_id, corte)
    out = []
    for e in comp:
        it = e.item
        es = (it["rol"] == "APLICACION" and it["clase"] in ("ANTICIPO", "PAGO", "COBRANZA") and e.pendiente > 0) or \
             (it["clase"] in ("ENTREGA_RENDIR",))
        if not es:
            continue
        tipo = ("Entrega a rendir" if it["clase"] == "ENTREGA_RENDIR" else
                "Anticipo de cliente" if it["clase"] == "ANTICIPO" and it["cuenta"][:1] == "1" else
                "Anticipo a proveedor" if it["clase"] == "ANTICIPO" else "Fondo pendiente de aplicación")
        out.append({**partidas.estado_dict(e), "tipo_anticipo": tipo, "antiguedad_dias": (corte - it["fecha_documento"]).days,
                    "relacionados": rel.get(it["id"], []),
                    "ejercicio_anterior": it["ejercicio"] < corte.year})
    return sorted(out, key=lambda x: -x["antiguedad_dias"])


def _relacionados(db, empresa_id, corte) -> dict[int, list]:
    out = defaultdict(list)
    q = select(Aplicacion.origen_item_id, Aplicacion.aplicacion_item_id, Aplicacion.importe, Aplicacion.estado, Aplicacion.grupo_id) \
        .where(Aplicacion.empresa_id == empresa_id, Aplicacion.estado.in_(("PROPUESTA", "APROBADA")), Aplicacion.fecha_efectiva <= corte)
    for o, a, imp, est, g in db.execute(q):
        out[o].append({"item_id": a, "importe": str(imp), "estado": est, "grupo_id": g})
        out[a].append({"item_id": o, "importe": str(imp), "estado": est, "grupo_id": g})
    return out


def tributos(db: Session, empresa_id: int, corte: date) -> dict:
    comp = {e.item["id"]: e for e in partidas.composicion(db, empresa_id, corte, incluir_propuestas=True)}
    rel = _relacionados(db, empresa_id, corte)
    obs = defaultdict(list)
    for x in db.scalars(select(ExcepcionCompensacion).where(ExcepcionCompensacion.empresa_id == empresa_id,
                                                            ExcepcionCompensacion.estado.in_(("ABIERTA", "EN_REVISION")))):
        if x.item_id:
            obs[x.item_id].append(x.codigo)
    out = {"DETRACCION": [], "RETENCION": [], "PERCEPCION": []}
    for e in comp.values():
        c = e.item["clase"]
        if c not in out:
            continue
        docs = [comp[r["item_id"]].item for r in rel.get(e.item["id"], []) if r["item_id"] in comp]
        out[c].append({**partidas.estado_dict(e), "lado_tributario": "Cliente (cobro)" if e.item["cuenta"][:1] == "1" else "Proveedor (pago)",
                       "documentos_relacionados": [f"{d['serie']}-{d['numero']}" if d["serie"] else d["numero"] for d in docs],
                       "importe_documento": str(sum((d["importe"] for d in docs), CERO)) if docs else None,
                       "observaciones": obs.get(e.item["id"], []),
                       "pendiente_revision": bool(obs.get(e.item["id"])) or not rel.get(e.item["id"])})
    return out


def dashboard(db: Session, empresa_id: int, corte: date) -> dict:
    comp = partidas.composicion(db, empresa_id, corte, incluir_propuestas=True)
    k = {c: defaultdict(lambda: CERO) for c in ("CXC", "CXP")}
    conc_t = {c: defaultdict(lambda: CERO) for c in ("CXC", "CXP")}
    rs = {}
    por_moneda = defaultdict(lambda: CERO)
    for e in comp:
        it = e.item
        c = TIPO_CARTERA(it["cuenta"])
        k[c]["partidas"] += 1
        k[c]["importe_aplicado"] += it["importe_mn"] - e.pendiente_mn if e.aplicado else CERO
        if e.cancelacion == "TOTAL":
            k[c]["compensadas"] += 1
        elif e.cancelacion == "PARCIAL":
            k[c]["parciales"] += 1
        else:
            k[c]["pendientes"] += 1
        if e.pendiente > 0 and it["rol"] == "ORIGEN":
            k[c]["importe_pendiente"] += e.pendiente_mn
            conc_t[c][it["tercero"] or "(sin tercero)"] += e.pendiente_mn
            rs[it["tercero"]] = it["razon_social"] or rs.get(it["tercero"])
            por_moneda[(c, it["moneda"])] += e.pendiente
        if e.vencimiento == "VENCIDO":
            k[c]["vencidos"] += 1
        if e.cancelacion == "ANTICIPO_PENDIENTE":
            k[c]["anticipos_pendientes"] += 1
    grupos = db.execute(select(GrupoCompensacion.estado, GrupoCompensacion.origen_propuesta, GrupoCompensacion.confianza,
                               func.count(), func.sum(GrupoCompensacion.importe))
                        .where(GrupoCompensacion.empresa_id == empresa_id).group_by(GrupoCompensacion.estado, GrupoCompensacion.origen_propuesta,
                                                                                    GrupoCompensacion.confianza)).all()
    g = defaultdict(int)
    conf = defaultdict(int)
    for est, orig, cf, n, _ in grupos:
        g[f"{est}_{orig}"] += n
        if est in ("PROPUESTA", "APROBADA"):
            conf[cf] += n
    dif = db.scalar(select(func.sum(Aplicacion.diferencia_cambio)).where(Aplicacion.empresa_id == empresa_id, Aplicacion.estado == "APROBADA",
                                                                        Aplicacion.fecha_efectiva <= corte)) or 0
    obs = db.scalar(select(func.count()).select_from(ExcepcionCompensacion).where(
        ExcepcionCompensacion.empresa_id == empresa_id, ExcepcionCompensacion.estado.in_(("ABIERTA", "EN_REVISION"))))
    # evolución de pendientes (fin de cada mes de los últimos 12)
    meses = []
    a, m = corte.year, corte.month
    for _ in range(12):
        meses.append(_fin_mes(a, m) if _fin_mes(a, m) <= corte else corte)
        a, m = (a, m - 1) if m > 1 else (a - 1, 12)
    meses = sorted(set(meses))
    items = db.execute(select(PartidaAbierta.id, PartidaAbierta.cuenta, PartidaAbierta.rol, PartidaAbierta.importe_mn, PartidaAbierta.importe,
                              PartidaAbierta.fecha_contable).where(PartidaAbierta.empresa_id == empresa_id, PartidaAbierta.vigente.is_(True),
                                                                   PartidaAbierta.rol == "ORIGEN")).all()
    apl = db.execute(select(Aplicacion.origen_item_id, Aplicacion.importe_mn_origen, Aplicacion.fecha_efectiva).where(
        Aplicacion.empresa_id == empresa_id, Aplicacion.estado == "APROBADA")).all()
    cartera_item = {i.id: TIPO_CARTERA(i.cuenta) for i in items}
    evolucion = []
    for fm in meses:
        v = {"CXC": CERO, "CXP": CERO}
        for i in items:
            if i.fecha_contable and i.fecha_contable <= fm:
                v[cartera_item[i.id]] += i.importe_mn
        for oid, mn, fe in apl:
            if fe <= fm and oid in cartera_item:
                v[cartera_item[oid]] -= mn
        evolucion.append({"fecha": fm.isoformat(), "CXC": str(v["CXC"]), "CXP": str(v["CXP"])})
    por_periodo = defaultdict(lambda: {"AUTOMATICA": CERO, "MANUAL": CERO})
    for fe, orig, imp in db.execute(select(GrupoCompensacion.fecha_efectiva, GrupoCompensacion.origen_propuesta, GrupoCompensacion.importe)
                                    .where(GrupoCompensacion.empresa_id == empresa_id, GrupoCompensacion.estado == "APROBADA")):
        por_periodo[f"{fe.year}-{fe.month:02d}"][orig] += imp
    aging = antiguedad(db, empresa_id, corte)
    return {
        "fecha_corte": corte.isoformat(),
        "kpi": {c: {kk: (str(v) if kk.startswith("importe") else int(v)) for kk, v in d.items()} for c, d in k.items()},
        "grupos": {"autoaprobadas": g["APROBADA_AUTOMATICA"], "manuales_aprobadas": g["APROBADA_MANUAL"],
                   "propuestas_pendientes": g["PROPUESTA_AUTOMATICA"] + g["PROPUESTA_MANUAL"], "revertidas": g["REVERTIDA_AUTOMATICA"] + g["REVERTIDA_MANUAL"],
                   "rechazadas": g["RECHAZADA_AUTOMATICA"] + g["RECHAZADA_MANUAL"]},
        "diferencias_cambio": str(Decimal(str(dif)).quantize(Decimal("0.01"))), "observaciones_abiertas": obs,
        "graficos": {
            "antiguedad": {"tramos": aging["tramos"], "CXC": _tramos_por(aging, "CXC"), "CXP": _tramos_por(aging, "CXP")},
            "evolucion": evolucion,
            "concentracion": {c: [{"tercero": t, "razon_social": rs.get(t), "importe": str(v)} for t, v in
                                  sorted(conc_t[c].items(), key=lambda x: -x[1])[:10]] for c in conc_t},
            "por_periodo": [{"periodo": p, "automatica": str(v["AUTOMATICA"]), "manual": str(v["MANUAL"])} for p, v in sorted(por_periodo.items())],
            "confianza": {c: conf.get(c, 0) for c in ("MUY_ALTA", "ALTA", "MEDIA", "BAJA")},
            "por_moneda": [{"cartera": c, "moneda": mo, "importe": str(v)} for (c, mo), v in sorted(por_moneda.items())],
        },
    }


def _tramos_por(aging, cartera):
    t = [CERO] * len(aging["tramos"])
    for g in aging["grupos"]:
        if g["cartera"] == cartera:
            t = [a + Decimal(b) for a, b in zip(t, g["tramos"])]
    return [str(v) for v in t]


# ------------------------------------------------------------------ reportes
def _refs(empresa, corte, filtros, moneda="PEN (moneda nacional) y moneda de cada documento"):
    return [("Empresa", f"{empresa.razon_social} — RUC {empresa.ruc}"), ("Fecha de corte", corte.strftime("%d/%m/%Y")),
            ("Periodo", f"{corte.year} · hasta {corte.month:02d}"), ("Moneda", moneda),
            ("Filtros", filtros or "sin filtros"), ("Generado", datetime.now().strftime("%d/%m/%Y %H:%M"))]


COL_PARTIDA = [("id", "Partida", "entero"), ("cuenta", "Cuenta", "texto"), ("tercero", "Tercero", "texto"),
               ("razon_social", "Razón social", "texto"), ("clase", "Clase", "texto"), ("documento", "Documento", "texto"),
               ("fecha_documento", "Fecha", "texto"), ("fecha_vencimiento", "Vencimiento", "texto"), ("moneda", "Mon.", "texto"),
               ("importe", "Importe", "importe"), ("aplicado", "Aplicado", "importe"), ("pendiente", "Pendiente", "importe"),
               ("pendiente_mn", "Pendiente MN", "importe"), ("estado_cancelacion", "Cancelación", "texto"),
               ("estado_vencimiento", "Vencimiento", "texto"), ("estado_revision", "Revisión", "texto")]
COL_GRUPO = [("id", "Compensación", "entero"), ("modalidad", "Modalidad", "texto"), ("origen_propuesta", "Origen", "texto"),
             ("regla", "Regla", "texto"), ("puntuacion", "Puntuación", "entero"), ("confianza", "Confianza", "texto"),
             ("cuenta", "Cuenta", "texto"), ("tercero", "Tercero", "texto"), ("moneda", "Mon.", "texto"), ("importe", "Importe", "importe"),
             ("fecha_efectiva", "Fecha efectiva", "texto"), ("estado", "Estado", "texto"), ("propuesto_por", "Propuesto por", "texto"),
             ("aprobado_por", "Aprobado por", "texto"), ("justificacion", "Justificación", "texto")]


def reporte(db: Session, empresa, nombre: str, corte: date, filtros: dict) -> Reporte:
    e = empresa.id
    ftxt = ", ".join(f"{k}: {v}" for k, v in filtros.items() if v)
    cuentas = [filtros["cuenta"]] if filtros.get("cuenta") else None
    if nombre in ("partidas_abiertas", "partidas_compensadas", "aplicaciones_parciales", "pendientes_tercero", "saldos_historicos"):
        comp = partidas.composicion(db, e, corte, cuentas=cuentas, tercero=filtros.get("tercero"), incluir_propuestas=False)
        sel = {"partidas_abiertas": lambda x: x.pendiente > 0, "partidas_compensadas": lambda x: x.cancelacion == "TOTAL",
               "aplicaciones_parciales": lambda x: x.cancelacion == "PARCIAL", "pendientes_tercero": lambda x: x.pendiente > 0 and x.item["rol"] == "ORIGEN",
               "saldos_historicos": lambda x: True}[nombre]
        filas = [partidas.estado_dict(x) for x in comp if sel(x)]
        if nombre == "pendientes_tercero":
            filas.sort(key=lambda f: (f["tercero"] or "", f["fecha_documento"]))
        titulos = {"partidas_abiertas": "Partidas abiertas", "partidas_compensadas": "Partidas compensadas",
                   "aplicaciones_parciales": "Aplicaciones parciales", "pendientes_tercero": "Documentos pendientes por tercero",
                   "saldos_historicos": "Composición histórica del saldo"}
        return Reporte(nombre, titulos[nombre], _refs(empresa, corte, ftxt),
                       [Tabla(titulos[nombre], COL_PARTIDA, filas, totales=["importe", "aplicado", "pendiente_mn"],
                              nota="Pendiente MN: importe pendiente expresado en moneda nacional.")])
    if nombre == "antiguedad":
        a = antiguedad(db, e, corte, base=filtros.get("base") or "VENCIMIENTO", agrupar=filtros.get("agrupar") or "tercero", cuentas=cuentas)
        cols = [("clave", "Agrupación", "texto"), ("razon_social", "Razón social", "texto")] + \
            [(f"t{i}", n, "importe") for i, n in enumerate(a["tramos"])] + [("total", "Total", "importe")]
        filas = [{**g, **{f"t{i}": v for i, v in enumerate(g["tramos"])}} for g in a["grupos"]]
        return Reporte("antiguedad_compensada", "Antigüedad de saldos pendientes (después de compensaciones)", _refs(empresa, corte, ftxt),
                       [Tabla("Antigüedad", cols, filas, totales=[f"t{i}" for i in range(len(a["tramos"]))] + ["total"], nota=a["nota"])])
    if nombre in ("compensaciones_propuestas", "compensaciones_aprobadas", "compensaciones_revertidas"):
        est = {"compensaciones_propuestas": "PROPUESTA", "compensaciones_aprobadas": "APROBADA", "compensaciones_revertidas": "REVERTIDA"}[nombre]
        filas = [{c.key: (str(getattr(g, c.key)) if isinstance(getattr(g, c.key), Decimal) else
                          getattr(g, c.key).isoformat() if hasattr(getattr(g, c.key), "isoformat") else getattr(g, c.key))
                  for c in GrupoCompensacion.__table__.columns}
                 for g in db.scalars(select(GrupoCompensacion).where(GrupoCompensacion.empresa_id == e, GrupoCompensacion.estado == est)
                                     .order_by(GrupoCompensacion.id))]
        return Reporte(nombre, f"Compensaciones {est.lower()}s", _refs(empresa, corte, ftxt), [Tabla("Compensaciones", COL_GRUPO, filas, totales=["importe"])])
    if nombre == "anticipos":
        filas = anticipos(db, e, corte)
        cols = [("tipo_anticipo", "Tipo", "texto")] + COL_PARTIDA[1:4] + [("documento", "Documento", "texto"), ("importe", "Importe original", "importe"),
                                                                           ("aplicado", "Aplicado", "importe"), ("pendiente", "Pendiente", "importe"),
                                                                           ("antiguedad_dias", "Antigüedad (días)", "entero"), ("responsable", "Responsable", "texto"),
                                                                           ("estado_revision", "Revisión", "texto")]
        return Reporte("anticipos", "Anticipos y fondos pendientes de aplicación", _refs(empresa, corte, ftxt), [Tabla("Anticipos", cols, filas, totales=["importe", "aplicado", "pendiente"])])
    if nombre in ("detracciones", "retenciones"):
        t = tributos(db, e, corte)["DETRACCION" if nombre == "detracciones" else "RETENCION"]
        filas = [{**x, "documentos_relacionados": ", ".join(x["documentos_relacionados"]), "observaciones": ", ".join(x["observaciones"])}
                 for x in t if x["pendiente_revision"]]
        cols = [("lado_tributario", "Lado", "texto"), ("tercero", "Tercero", "texto"), ("documento", "Documento / constancia", "texto"),
                ("constancia_detraccion", "Constancia", "texto"), ("retencion", "Comprobante retención", "texto"),
                ("fecha_documento", "Fecha", "texto"), ("importe", "Importe", "importe"), ("documentos_relacionados", "Documentos relacionados", "texto"),
                ("importe_documento", "Importe documento", "importe"), ("observaciones", "Observaciones", "texto")]
        return Reporte(nombre, f"{nombre.capitalize()} pendientes de revisión", _refs(empresa, corte, ftxt), [Tabla(nombre.capitalize(), cols, filas, totales=["importe"])])
    if nombre == "diferencias_cambio":
        filas = []
        for a, p in db.execute(select(Aplicacion, PartidaAbierta).join(PartidaAbierta, PartidaAbierta.id == Aplicacion.origen_item_id)
                               .where(Aplicacion.empresa_id == e, Aplicacion.estado == "APROBADA", Aplicacion.moneda != "PEN",
                                      Aplicacion.fecha_efectiva <= corte)):
            filas.append({"grupo_id": a.grupo_id, "cuenta": p.cuenta, "tercero": p.tercero, "documento": f"{p.serie}-{p.numero}" if p.serie else p.numero,
                          "moneda": a.moneda, "importe": str(a.importe), "mn_emision": str(a.importe_mn_origen), "mn_cancelacion": str(a.importe_mn_aplicacion),
                          "diferencia": str(a.diferencia_cambio), "fecha": a.fecha_efectiva.isoformat()})
        cols = [("grupo_id", "Compensación", "entero"), ("cuenta", "Cuenta", "texto"), ("tercero", "Tercero", "texto"), ("documento", "Documento", "texto"),
                ("moneda", "Moneda", "texto"), ("importe", "Importe ME", "importe"), ("mn_emision", "MN a TC de emisión", "importe"),
                ("mn_cancelacion", "MN a TC de cancelación", "importe"), ("diferencia", "Diferencia de cambio", "importe"), ("fecha", "Fecha", "texto")]
        return Reporte("diferencias_cambio", "Diferencias de cambio identificadas (pendientes de evaluación)", _refs(empresa, corte, ftxt),
                       [Tabla("Diferencias de cambio", cols, filas, totales=["importe", "mn_emision", "mn_cancelacion", "diferencia"],
                              nota="No se generan asientos automáticos en esta fase.")])
    if nombre == "conciliacion":
        c = partidas.conciliacion(db, e, corte)
        cols = [("cuenta", "Cuenta", "texto"), ("saldo_contable", "Saldo contable", "importe"), ("origen", "Partidas origen pendientes", "importe"),
                ("aplicacion", "Partidas de aplicación pendientes", "importe"), ("sin_detalle", "Saldos iniciales sin detalle", "importe"),
                ("no_clasificado", "Movimientos no clasificados", "importe"), ("diferencia_cambio_aplicaciones", "Dif. de cambio de aplicaciones", "importe"),
                ("partidas_netas", "Total explicado", "importe"), ("diferencia", "Diferencia", "importe")]
        return Reporte("conciliacion_partidas", "Conciliación entre saldo contable y partidas abiertas", _refs(empresa, corte, ftxt, "PEN (moneda nacional)"),
                       [Tabla("Conciliación", cols, c["cuentas"], totales=[k for k, _, t in cols if t == "importe"], nota=c["nota"])])
    raise ValueError("Reporte no disponible")


REPORTES = ["partidas_abiertas", "partidas_compensadas", "aplicaciones_parciales", "pendientes_tercero", "antiguedad",
            "compensaciones_propuestas", "compensaciones_aprobadas", "compensaciones_revertidas", "anticipos", "detracciones",
            "retenciones", "diferencias_cambio", "saldos_historicos", "conciliacion"]
