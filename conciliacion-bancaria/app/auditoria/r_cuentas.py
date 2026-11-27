"""Módulos CXC, CXP, TESORERIA, GASTOS, INGRESOS y DEVENGOS.

Los saldos pendientes por documento salen de la compensación de la fase 4 cuando existe (saldos realmente pendientes
tras compensaciones aprobadas) y, si no, del libro (antigüedad de la fase 3). Ninguna regla determina pérdidas por
deterioro, recomienda dar de baja pasivos, califica operaciones como fraudulentas ni decide la deducibilidad tributaria:
todo resultado es un hallazgo potencial pendiente de evaluación profesional.
"""
import statistics
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from app.analisis import antiguedad
from app.auditoria.base import (CERO, Res, Salida, asiento_de, dec, doc_de, ev_calc, ev_linea, ev_reg, fase3, res_de_h3)
from app.importers.normalizacion import normalizar_texto
from app.models import Anexo, CuentaBancaria

CXC = ("12", "13", "14", "16", "17")
CXP = ("42", "43", "44", "45", "46", "47")


# ===================================================================== saldos pendientes por documento
def pendientes(ax, prefijos) -> tuple[list[dict], str]:
    clave = ("pend",) + tuple(prefijos)
    cache = ax.__dict__.setdefault("_pend", {})
    if clave in cache:
        return cache[clave]
    out = []
    if ax.partidas is not None:
        for e in ax.partidas:
            it = e.item
            if not it["cuenta"].startswith(tuple(prefijos)) or e.pendiente_mn <= 0:
                continue
            out.append({"cuenta": it["cuenta"], "tercero": it["tercero"], "razon_social": it["razon_social"],
                        "documento": f"{it['serie']}-{it['numero']}" if it["serie"] else it["numero"], "clase": it["clase"], "rol": it["rol"],
                        "fecha": it["fecha_documento"], "vencimiento": it["fecha_vencimiento"], "importe": e.pendiente_mn,
                        "signo": 1 if it["lado"] == "D" else -1, "linea_id": it["linea_id"], "tabla": "open_items", "id": it["id"]})
        fuente = "Partidas abiertas después de las compensaciones aprobadas (fase 4)."
    else:
        ag = antiguedad.calcular(ax.db, ax.empresa_id, ax.ejercicio, ax.corte, cuentas=",".join(prefijos))
        for d in ag["documentos"]:
            imp = dec(d["importe"])
            out.append({"cuenta": d["cuenta"], "tercero": d["tercero"], "razon_social": d["razon_social"], "documento": d["documento"],
                        "clase": "NOTA_CREDITO" if (d.get("tipo_documento") or "").lstrip("0") == "7" else None,
                        "rol": "ORIGEN" if imp > 0 else "APLICACION", "fecha": _f(d["fecha_emision"]) or _f(d["fecha_contable"]),
                        "vencimiento": _f(d["fecha_vencimiento"]), "importe": abs(imp), "signo": 1 if imp > 0 else -1, "linea_id": None,
                        "tabla": "lineas_diario", "id": None})
        fuente = "Saldos por documento según el libro (fase 3: la compensación de la fase 4 no se ha ejecutado)."
    cache[clave] = (out, fuente)
    return out, fuente


def _f(v):
    from datetime import date
    return date.fromisoformat(v) if isinstance(v, str) else v


def _res_doc(d, titulo, condicion, prefijo, **kw) -> Res:
    ev = [ev_reg(d["tabla"], d["id"], f"{d['documento'] or '(sin documento)'} · {d['razon_social'] or d['tercero'] or ''}",
                 cuenta=d["cuenta"], fecha=d["fecha"], vencimiento=d["vencimiento"], pendiente=d["importe"])]
    return Res(titulo=titulo, condicion=condicion, importe=d["importe"], cuenta=d["cuenta"], tercero=d["tercero"], razon_social=d["razon_social"],
               documento=d["documento"], linea_id=d["linea_id"], evidencia=ev, clave=f"{prefijo}|{d['cuenta']}|{d['tercero']}|{d['documento']}",
               exposicion=f"DOC|{d['tercero']}|{d['documento']}|{d['cuenta'][:2]}", **kw)


def vencidos(ax, r) -> Salida:
    pref = tuple(r.cuentas) or CXC
    dias = int(r.p.get("dias", 30))
    docs, fuente = pendientes(ax, pref)
    pagar = pref[0].startswith("4")
    por = defaultdict(list)
    for d in docs:
        if d["rol"] == "ORIGEN" and d["vencimiento"] and (ax.corte - d["vencimiento"]).days > dias:
            por[(d["cuenta"][:2], d["tercero"])].append(d)
    out = []
    for (c, t), ds in por.items():
        tot = sum((d["importe"] for d in ds), CERO)
        mx = max((ax.corte - d["vencimiento"]).days for d in ds)
        out.append(Res(titulo=f"{'Obligaciones' if pagar else 'Documentos'} vencidos de {ds[0]['razon_social'] or t or 'tercero sin identificar'}",
                       condicion=f"{len(ds)} documentos vencidos hace más de {dias} días (máximo {mx}) por {tot}.", importe=tot, cuenta=ds[0]["cuenta"],
                       tercero=t, razon_social=ds[0]["razon_social"], evidencia=[ev_reg(d["tabla"], d["id"], d["documento"] or "", vencimiento=d["vencimiento"],
                                                                                    pendiente=d["importe"]) for d in ds[:30]],
                       clave=f"VENC|{c}|{t}", exposicion=f"TERCERO|{c}|{t}", detalle={"dias_max": mx, "fuente": fuente},
                       recomendacion=("Verifique la exigibilidad, el sustento y el tratamiento contable y legal; no se recomienda dar de baja pasivos "
                                      "antiguos sin esa evaluación." if pagar else
                                      "Gestione la cobranza y evalúe la recuperabilidad con evidencia (no se determina deterioro solo por antigüedad).")))
    return Salida(out, len(docs), sum((d["importe"] for d in docs), CERO), f"Vencimiento mayor a {dias} días. {fuente}")


def antiguos(ax, r) -> Salida:
    pref = tuple(r.cuentas) or CXC
    dias = int(r.p.get("dias", 365))
    docs, fuente = pendientes(ax, pref)
    pagar = pref[0].startswith("4")
    out = []
    for d in docs:
        if d["rol"] == "ORIGEN" and d["fecha"] and (ax.corte - d["fecha"]).days > dias:
            out.append(_res_doc(d, f"Saldo antiguo: {d['documento'] or 'sin documento'} de {d['razon_social'] or d['tercero'] or 'tercero sin identificar'}",
                                f"Documento con {(ax.corte - d['fecha']).days} días de antigüedad y saldo pendiente {d['importe']}.", "ANT",
                                recomendacion=("Evalúe la exigibilidad, sustento y tratamiento contable y legal antes de cualquier depuración." if pagar else
                                               "Evalúe la recuperabilidad con evidencia; la antigüedad no determina por sí sola un deterioro."),
                                detalle={"dias": (ax.corte - d["fecha"]).days, "fuente": fuente}))
    return Salida(out, len(docs), sum((d["importe"] for d in docs), CERO), f"Antigüedad desde la emisión mayor a {dias} días. {fuente}")


def concentracion(ax, r) -> Salida:
    pref = tuple(r.cuentas) or ("12",)
    pct = Decimal(str(r.p.get("porcentaje", 30)))
    docs, fuente = pendientes(ax, pref)
    tot = sum((d["importe"] * d["signo"] for d in docs), CERO)
    por = defaultdict(lambda: CERO)
    rs = {}
    for d in docs:
        por[d["tercero"]] += d["importe"] * d["signo"]
        rs[d["tercero"]] = d["razon_social"]
    out = []
    if tot and len(por) >= int(r.p.get("min_terceros", 3)):
        for t, v in por.items():
            if v * 100 / abs(tot) >= pct and v >= dec(r.p.get("importe_minimo", 0)):
                out.append(Res(titulo=f"Concentración de saldo en {rs[t] or t}", condicion=f"{rs[t] or t} concentra {(v * 100 / abs(tot)).quantize(Decimal('0.1'))} % "
                               f"del saldo de las cuentas {', '.join(pref)} ({v} de {tot}).", importe=v, cuenta=pref[0], tercero=t, razon_social=rs[t],
                               evidencia=[ev_calc("Participación del tercero", saldo_tercero=v, saldo_total=tot, umbral_pct=pct)],
                               clave=f"CONC|{','.join(pref)}|{t}", exposicion=f"TERCERO|{pref[0]}|{t}", estructural=False,
                               recomendacion="Considere solicitar confirmación de saldos y revisar las condiciones contractuales."))
    return Salida(out, len(por), abs(tot), f"Participación de cada tercero en el saldo pendiente ≥ {pct} %. {fuente}")


def contrario_tercero(ax, r) -> Salida:
    hs = fase3(ax, "SALDO_CONTRARIO_TERCERO", r.codigo, cuentas=r.cuentas or list(CXC), importe_minimo=r.p.get("importe_minimo", "1"))
    out = [res_de_h3(h, "CONTR") for h in hs if not r.excluido(h.cuenta, h.tercero)]
    return Salida(out, len(hs), metodo="Evaluador SALDO_CONTRARIO_TERCERO de la fase 3 (saldo por tercero opuesto a la naturaleza de la cuenta).")


def aplicaciones_pendientes(ax, r) -> Salida:
    """Cobranzas, pagos, anticipos o notas de crédito pendientes de aplicación (fase 4; sin ella, saldos contrarios por documento)."""
    pref = tuple(r.cuentas) or CXC
    clases = set(r.p.get("clases", ["COBRANZA", "PAGO"]))
    docs, fuente = pendientes(ax, pref)
    out = []
    for d in docs:
        es = d["rol"] == "APLICACION" and (d["clase"] in clases if ax.partidas is not None else
                                            (d["clase"] == "NOTA_CREDITO") == ("NOTA_CREDITO" in clases))
        if es and d["importe"] >= dec(r.p.get("importe_minimo", "0.01")):
            nombre = {"COBRANZA": "Cobranza", "PAGO": "Pago", "ANTICIPO": "Anticipo", "NOTA_CREDITO": "Nota de crédito"}.get(d["clase"], "Saldo a favor")
            out.append(_res_doc(d, f"{nombre} pendiente de aplicación: {d['documento'] or ''} de {d['razon_social'] or d['tercero'] or ''}",
                                f"{nombre} por {d['importe']} sin documento al cual aplicarse al {ax.corte:%d/%m/%Y}"
                                f"{' (' + str((ax.corte - d['fecha']).days) + ' días)' if d['fecha'] else ''}.", "APL",
                                detalle={"clase": d["clase"], "fuente": fuente}, regularizacion="REQUIERE_CONCILIACION"))
    return Salida(out, len(docs), metodo=f"Partidas de aplicación con saldo pendiente ({', '.join(sorted(clases))}). {fuente}")


def anticipos(ax, r) -> Salida:
    pref = tuple(r.cuentas)
    dias = int(r.p.get("dias", 90))
    out, n = [], 0
    saldos = defaultdict(lambda: [CERO, None, None, []])
    for ln in ax.ctx3.lineas_hasta_corte:
        if ln.cuenta.startswith(pref):
            n += 1
            s = saldos[(ln.cuenta, ln.tercero)]
            s[0] += ln.debe - ln.haber
            s[1] = ln.razon_social or s[1]
            s[2] = max(s[2] or ln.fecha, ln.fecha) if ln.fecha else s[2]
            s[3].append(ln)
    for (c, t), (v, rs, ult, ls) in saldos.items():
        if v and ult and (ax.corte - ult).days > dias:
            out.append(Res(titulo=f"Anticipo pendiente de aplicación en la cuenta {c}: {rs or t or 'sin tercero'}",
                           condicion=f"Saldo {abs(v)} sin movimiento desde el {ult:%d/%m/%Y} ({(ax.corte - ult).days} días).", importe=abs(v), cuenta=c,
                           tercero=t, razon_social=rs, evidencia=[ev_linea(x) for x in ls[-10:] if x.id], clave=f"ANTIC|{c}|{t}",
                           exposicion=f"TERCERO|{c[:2]}|{t}", regularizacion="REQUIERE_CONCILIACION",
                           recomendacion="Verifique si el bien o servicio ya se recibió/entregó para aplicar el anticipo al comprobante."))
    return Salida(out, n, metodo=f"Saldos por tercero de las cuentas {', '.join(pref)} sin movimiento en más de {dias} días.")


def personal(ax, r) -> Salida:
    """Préstamos, adelantos o entregas a rendir (14) con saldo antiguo por trabajador."""
    dias = int(r.p.get("dias", 60))
    s = anticipos(ax, r)
    for x in s.res:
        x.personal = True
        x.titulo = x.titulo.replace("Anticipo pendiente de aplicación", r.p.get("nombre", "Saldo del personal pendiente"))
    s.metodo = f"Saldos por trabajador de las cuentas {', '.join(r.cuentas)} sin movimiento en más de {dias} días."
    return s


def diferencia_cambio(ax, r) -> Salida:
    hs = fase3(ax, "DIFERENCIA_CAMBIO", r.codigo, cuentas=r.cuentas, importe_minimo=r.p.get("importe_minimo", "1"))
    out = [res_de_h3(h, "DCAM", calidad="PARCIAL", recomendacion="Evalúe y registre la diferencia de cambio al tipo de cierre (NIC 21).") for h in hs]
    return Salida(out, len(hs), metodo="Evaluador DIFERENCIA_CAMBIO de la fase 3 con el tipo de cambio de cierre importado.")


def deterioro(ax, r) -> Salida:
    dias = int(r.p.get("dias", 365))
    docs, fuente = pendientes(ax, tuple(r.cuentas) or ("12", "13", "16"))
    estimacion = defaultdict(lambda: CERO)
    for ln in ax.ctx3.lineas_hasta_corte:
        if ln.cuenta.startswith("19"):
            estimacion[ln.tercero] += ln.haber - ln.debe
    por = defaultdict(list)
    for d in docs:
        if d["rol"] == "ORIGEN" and d["fecha"] and (ax.corte - d["fecha"]).days > dias and estimacion[d["tercero"]] <= 0:
            por[d["tercero"]].append(d)
    out = []
    for t, ds in por.items():
        tot = sum((d["importe"] for d in ds), CERO)
        out.append(Res(titulo=f"Evaluar posible deterioro de la cartera de {ds[0]['razon_social'] or t}",
                       condicion=f"{len(ds)} documentos con más de {dias} días por {tot} sin estimación de cobranza dudosa (19) registrada.",
                       importe=tot, cuenta=ds[0]["cuenta"], tercero=t, razon_social=ds[0]["razon_social"],
                       evidencia=[ev_reg(d["tabla"], d["id"], d["documento"] or "", fecha=d["fecha"], pendiente=d["importe"]) for d in ds[:20]],
                       clave=f"DET|{t}", exposicion=f"TERCERO|{ds[0]['cuenta'][:2]}|{t}", calidad="PARCIAL",
                       tributario="PENDIENTE_EVALUACION", causa="La antigüedad es un indicio, no una pérdida determinada.",
                       recomendacion="Evalúe la recuperabilidad (pérdidas crediticias esperadas, NIIF 9 o la política de la empresa); el sistema no "
                                     "determina deterioros automáticamente."))
    return Salida(out, len(docs), metodo=f"Documentos de más de {dias} días sin estimación en la cuenta 19 del mismo tercero. {fuente}")


def anexos_vs_balance(ax, r) -> Salida:
    pref = tuple(r.cuentas) or CXC
    q = select(Anexo).where(Anexo.empresa_id == ax.empresa_id, Anexo.fecha_corte == ax.corte, Anexo.version_id.is_not(None))
    anexos = [a for a in ax.db.scalars(q) if a.cuenta.startswith(pref)]
    if not anexos:
        return Salida(estado="SIN_DATOS", mensaje="No hay anexos generados (fase 5) de estas cuentas a la fecha de corte.")
    out = [Res(titulo=f"Anexo de la cuenta {a.cuenta} no cuadra con el balance", condicion=f"Saldo contable {a.saldo_contable}, detalle del anexo "
               f"{a.saldo_detalle}: diferencia {a.diferencia}.", importe=abs(a.diferencia), cuenta=a.cuenta,
               evidencia=[ev_reg("accounting_annexes", a.id, f"Anexo {a.cuenta} versión {a.version_actual}", resultado=a.resultado,
                                 saldo_contable=a.saldo_contable, saldo_detalle=a.saldo_detalle)],
               clave=f"ANX|{a.cuenta}", exposicion=f"CUENTA|{a.cuenta}", regularizacion="REQUIERE_CONCILIACION")
           for a in anexos if a.diferencia]
    return Salida(out, len(anexos), metodo="Diferencia entre el saldo contable y el detalle de los anexos de la fase 5 al corte.")


def pagos_sin_documento(ax, r) -> Salida:
    minimo = dec(r.p.get("importe_minimo", "0"))
    out = []
    for k, ls in ax.asientos.items():
        if not any(x.cuenta.startswith("10") and x.haber for x in ls):
            continue
        sin = [x for x in ls if x.cuenta.startswith(tuple(r.cuentas) or CXP) and x.debe >= minimo and not x.numero]
        if sin and ax.asiento_en_alcance(sin):
            x = sin[0]
            out.append(Res(titulo=f"Pago sin documento asociado en el asiento {asiento_de(x)}", condicion=f"Pago de {sum((y.debe for y in sin), CERO)} "
                           f"en {', '.join(sorted({y.cuenta for y in sin}))} sin número de documento.", importe=sum((y.debe for y in sin), CERO),
                           cuenta=x.cuenta, tercero=x.tercero, razon_social=x.razon_social, asiento=asiento_de(x), linea_id=x.id,
                           evidencia=[ev_linea(y) for y in ls[:10]], clave=f"PSD|{k}", exposicion=f"ASIENTO|{k[0]}|{k[1]}|{asiento_de(x)}",
                           calidad="PARCIAL", regularizacion="REQUIERE_DOCUMENTACION"))
    return Salida(out, len(ax.asientos), metodo="Asientos con salida de caja/bancos y cargos a cuentas por pagar sin número de documento.")


def sin_tercero(ax, r) -> Salida:
    hs = fase3(ax, "SIN_TERCERO", r.codigo, cuentas=r.cuentas or list(CXP), lineas=ax.lineas)
    return Salida([res_de_h3(h, "STER") for h in hs], len(ax.lineas), metodo="Evaluador SIN_TERCERO de la fase 3.")


def conciliacion_memoria(ax, r) -> Salida:
    """Diferencias de una plantilla de la fase 6 ejecutada en memoria (o, si existe, de la conciliación vigente)."""
    tipo = r.p["tipo"]
    subtipos = set(r.p.get("subtipos", []))
    guardadas = ax.diferencias_conciliacion((tipo,))
    if guardadas:
        out = []
        for d in guardadas:
            if subtipos and d.subtipo not in subtipos:
                continue
            out.append(Res(titulo=f"{d.subtipo or d.clasificacion}: {d.documento or d.cuenta or ''}".replace("_", " ").capitalize(),
                           condicion=d.explicacion or "", importe=abs(d.importe), cuenta=d.cuenta, tercero=d.tercero, razon_social=d.razon_social,
                           documento=d.documento, evidencia=[ev_reg("reconciliation_differences", d.id, f"Diferencia {d.codigo} (fase 6)",
                                                                     clasificacion=d.clasificacion, estado=d.estado)],
                           clave=f"C6|{d.huella}", exposicion=f"C6|{d.huella}", personal=d.personal,
                           recomendacion=d.recomendacion, detalle={"conciliacion_id": d.run_id, "subtipo": d.subtipo}))
        return Salida(out, len(guardadas), metodo=f"Diferencias abiertas de la conciliación {tipo} vigente (fase 6).")
    difs = ax.conciliar_en_memoria(tipo)
    if not difs and tipo in ("PLANILLAS", "INVENTARIOS", "TRIBUTOS", "DETRACCIONES", "RETENCIONES", "SERVICIOS_PROCESO"):
        return Salida(estado="SIN_DATOS", mensaje=f"No hay una conciliación {tipo} ejecutada en la fase 6 (requiere la fuente externa).")
    out = []
    for d in difs:
        if subtipos and d["subtipo"] not in subtipos:
            continue
        regs = d.get("_registros", [])
        ev = [ev_reg(x.get("origen_tabla"), x.get("origen_id"), f"{x.get('descripcion') or ''}", importe=x.get("importe"), documento=x.get("numero"))
              for x in regs[:10]]
        out.append(Res(titulo=f"{(d['subtipo'] or d['clasificacion']).replace('_', ' ').capitalize()}: {d['documento'] or d['cuenta'] or ''}",
                       condicion=d["explicacion"], importe=abs(dec(d["importe"])), cuenta=d["cuenta"], tercero=d["tercero"],
                       razon_social=d["razon_social"], documento=d["documento"], evidencia=ev + [ev_calc("Conciliación en memoria (fase 6)", tipo=tipo,
                                                                                                      clasificacion=d["clasificacion"])],
                       clave=f"C6M|{tipo}|{d['subtipo']}|{d.get('clave') or '|'.join(d['claves'][:10])}",
                       exposicion=f"DOC|{d['tercero']}|{d['documento']}" if d["documento"] else f"C6M|{tipo}|{d.get('clave') or d['claves'][:3]}",
                       recomendacion=d["recomendacion"], personal=d.get("personal", False),
                       riesgo_minimo="INFORMATIVO" if d["prioridad"] == "INFORMATIVO" else None,
                       detalle={"subtipo": d["subtipo"], "prioridad_fase6": d["prioridad"]}))
    return Salida(out, len(difs), metodo=f"Plantilla {tipo} de la fase 6 ejecutada en memoria (sin guardar) con las fuentes internas.")


# ===================================================================== TESORERÍA
BANCO_SUBTIPOS = {"COMISION_BANCARIA", "ITF", "ABONO_NO_IDENTIFICADO", "CARGO_NO_REGISTRADO", "INTERES_BANCARIO", "DEPOSITO_EN_TRANSITO",
                  "CHEQUE_PENDIENTE_COBRO", "TRANSFERENCIA_PENDIENTE", "DUPLICADO_CONTABLE", "DUPLICADO_EXTERNA", "DIFERENCIA_FINAL",
                  "DIFERENCIA_IMPORTE", "PERIODO_DIFERENTE"}


def bancaria(ax, r) -> Salida:
    subtipos = set(r.p.get("subtipos") or BANCO_SUBTIPOS)
    dias = int(r.p.get("dias_antiguedad", 0))
    minimo = dec(r.p.get("importe_minimo", "0"))
    cuentas = ax.db.scalars(select(CuentaBancaria).where(CuentaBancaria.empresa_id == ax.empresa_id)).all()
    if not cuentas:
        return Salida(estado="SIN_DATOS", mensaje="La empresa no tiene cuentas bancarias registradas (fase 1).")
    out, n = [], 0
    frecuencia = defaultdict(list)
    for cb in cuentas:
        difs = ax.conciliar_en_memoria("BANCARIA", {"cuenta_bancaria_id": cb.id})
        n += len(difs)
        rep = ax.reporte_en_memoria("BANCARIA", {"cuenta_bancaria_id": cb.id})
        for d in difs:
            st = d["subtipo"]
            if st not in subtipos or abs(dec(d["importe"])) < minimo:
                continue
            antig = (ax.corte - d["fecha"]).days if d.get("fecha") else None
            if dias and (antig is None or antig <= dias):
                continue
            frecuencia[(cb.id, st)].append(d)
            out.append(Res(titulo=f"{st.replace('_', ' ').capitalize()} · {cb.cuenta_contable} {cb.numero_cuenta}",
                           condicion=d["explicacion"] + (f" Antigüedad: {antig} días." if antig is not None else ""), importe=abs(dec(d["importe"])),
                           cuenta=cb.cuenta_contable, documento=d["documento"], tercero=d["tercero"],
                           evidencia=[ev_reg(x.get("origen_tabla"), x.get("origen_id"), x.get("descripcion") or "", fecha=x.get("fecha"),
                                             importe=x.get("importe")) for x in d.get("_registros", [])[:6]]
                           + [ev_calc("Conciliación bancaria en memoria (fase 6)", saldo_banco=rep.get("saldo_banco"), saldo_libros=rep.get("saldo_libros"),
                                      diferencia_final=rep.get("diferencia_final"))],
                           clave=f"BAN|{cb.id}|{st}|{d.get('clave') or '|'.join(d['claves'][:5])}",
                           exposicion=f"BAN|{cb.id}|{'|'.join(d['claves'][:5]) or st}", detalle={"subtipo": st, "antiguedad": antig},
                           recomendacion=d["recomendacion"], regularizacion="REQUIERE_CONCILIACION",
                           causa="Diferencia de conciliación; no se califica la operación como irregular."))
    alerta = int(r.p.get("alerta_frecuencia", 0))
    if alerta:
        out = [x for x in out if len(frecuencia[(int(x.clave.split("|")[1]), x.detalle["subtipo"])]) >= alerta]
    return Salida(out, n, metodo="Conciliación bancaria de la fase 6 ejecutada en memoria por cada cuenta bancaria (estado de cuenta importado "
                                 f"vs libro); filtros: importe ≥ {minimo}, antigüedad > {dias} días, frecuencia ≥ {alerta or 1}.")


def transferencias_internas(ax, r) -> Salida:
    puente = tuple(r.p.get("cuentas_puente", ["103"]))
    out = []
    saldo = defaultdict(lambda: CERO)
    for ln in ax.ctx3.lineas_hasta_corte:
        if ln.cuenta.startswith(puente):
            saldo[ln.cuenta] += ln.debe - ln.haber
    for c, v in saldo.items():
        if v:
            out.append(Res(titulo=f"Transferencias entre cuentas pendientes en {c}", condicion=f"La cuenta puente {c} mantiene saldo {v} al corte: "
                           "transferencias sin contrapartida identificada.", importe=abs(v), cuenta=c, clave=f"TRI|{c}", exposicion=f"CUENTA|{c}",
                           evidencia=[ev_calc("Saldo de la cuenta puente", saldo=v)], regularizacion="REQUIERE_CONCILIACION"))
    for k, ls in ax.asientos.items():
        g = " ".join(normalizar_texto(x.glosa or "") for x in ls)
        bancos = [x for x in ls if x.cuenta.startswith("10")]
        if ("TRASPASO" in g or "ENTRE CUENTAS" in g) and len({x.cuenta for x in bancos}) == 1 and not any(x.cuenta.startswith(puente) for x in ls):
            x = bancos[0]
            out.append(Res(titulo=f"Transferencia entre cuentas sin contrapartida en el asiento {asiento_de(x)}",
                           condicion="Asiento de traspaso entre cuentas propias que afecta una sola cuenta de bancos.", importe=x.debe + x.haber,
                           cuenta=x.cuenta, asiento=asiento_de(x), linea_id=x.id, evidencia=[ev_linea(y) for y in ls],
                           clave=f"TRA|{k}", exposicion=f"ASIENTO|{k[0]}|{k[1]}|{asiento_de(x)}", calidad="PARCIAL"))
    return Salida(out, len(saldo), metodo="Saldo de cuentas puente (efectivo en tránsito) y traspasos que afectan una sola cuenta de bancos.")


def movimientos_sin_documento(ax, r) -> Salida:
    minimo = dec(r.p.get("importe_minimo", "0"))
    out = []
    for ln in ax.lineas:
        if ln.cuenta.startswith("10") and ln.debe + ln.haber >= minimo and not ln.numero and not ln.referencia and len((ln.glosa or "").strip()) < 4:
            out.append(Res(titulo=f"Movimiento de tesorería sin documentación en la cuenta {ln.cuenta}", condicion=f"Línea {ln.id} por {ln.debe + ln.haber} "
                           "sin operación, referencia ni glosa descriptiva.", importe=ln.debe + ln.haber, cuenta=ln.cuenta, linea_id=ln.id,
                           asiento=asiento_de(ln), evidencia=[ev_linea(ln)], clave=f"MSD|{ln.id}", exposicion=f"LINEA|{ln.id}", calidad="INSUFICIENTE",
                           regularizacion="REQUIERE_DOCUMENTACION"))
    return Salida(out, len(ax.lineas), metodo=f"Líneas de caja y bancos ≥ {minimo} sin número de operación, referencia ni glosa.")


# ===================================================================== GASTOS
def _terceros_asiento(ls):
    return next((x for x in ls if x.tercero and x.cuenta[:1] == "4"), None) or next((x for x in ls if x.tercero), None)


def gastos_sin_documento(ax, r) -> Salida:
    minimo = dec(r.p.get("importe_minimo", "0"))
    excl = tuple(r.p.get("excluir", ["62", "68", "69", "79", "9"]))
    exige_tercero = r.p.get("modo") == "TERCERO"
    out = []
    for k, ls in ax.asientos.items():
        gastos = [x for x in ls if x.cuenta.startswith("6") and not x.cuenta.startswith(excl) and x.debe >= minimo]
        if not gastos or not ax.asiento_en_alcance(gastos):
            continue
        falta = (not _terceros_asiento(ls)) if exige_tercero else not any(x.numero for x in ls)
        if falta:
            x = max(gastos, key=lambda y: y.debe)
            que = "proveedor identificado" if exige_tercero else "documento asociado"
            out.append(Res(titulo=f"Gasto sin {que} en el asiento {asiento_de(x)}", condicion=f"Gasto de {sum((y.debe for y in gastos), CERO)} en "
                           f"{', '.join(sorted({y.cuenta for y in gastos}))} sin {que}.", importe=sum((y.debe for y in gastos), CERO), cuenta=x.cuenta,
                           asiento=asiento_de(x), linea_id=x.id, centro_costo=x.cc, evidencia=[ev_linea(y) for y in ls[:10]],
                           clave=f"{'GSP' if exige_tercero else 'GSD'}|{k}", exposicion=f"ASIENTO|{k[0]}|{k[1]}|{asiento_de(x)}", calidad="PARCIAL",
                           tributario="PENDIENTE_EVALUACION", regularizacion="REQUIERE_DOCUMENTACION",
                           recomendacion="Obtenga el comprobante; la deducibilidad tributaria se evalúa con el sustento, no por la cuenta contable."))
    return Salida(out, len(ax.asientos), metodo=f"Asientos con gastos ≥ {minimo} (excluye {', '.join(excl)}) sin {'tercero' if exige_tercero else 'número de documento'}.")


def gastos_sin_cc(ax, r) -> Salida:
    hs = fase3(ax, "SIN_CENTRO_COSTO", r.codigo, cuentas=r.cuentas or ["6"], parametros={"solo_si_plan_lo_exige": True}, lineas=ax.lineas)
    return Salida([res_de_h3(h, "SCC") for h in hs], len(ax.lineas), metodo="Evaluador SIN_CENTRO_COSTO de la fase 3 (solo cuentas que lo exigen en el plan).")


def gastos_fuera_periodo(ax, r) -> Salida:
    meses = int(r.p.get("meses", 1))
    pref = tuple(r.cuentas) or ("6",)
    out = []
    for ln in ax.lineas:
        if ln.cuenta.startswith(pref) and ln.fecha_emision and ln.fecha and \
                (ln.fecha.year - ln.fecha_emision.year) * 12 + ln.fecha.month - ln.fecha_emision.month > meses:
            out.append(Res(titulo=f"Registro de {'ingreso' if pref[0] == '7' else 'gasto'} fuera del periodo del comprobante", condicion=
                           f"Comprobante {doc_de(ln)} emitido el {ln.fecha_emision:%d/%m/%Y} y contabilizado el {ln.fecha:%d/%m/%Y}.",
                           importe=ln.debe + ln.haber, cuenta=ln.cuenta, tercero=ln.tercero, documento=doc_de(ln), linea_id=ln.id, asiento=asiento_de(ln),
                           evidencia=[ev_linea(ln)], clave=f"GFP|{ln.id}", exposicion=f"LINEA|{ln.id}", tributario="POSIBLE_DIFERENCIA_TEMPORAL",
                           recomendacion="Verifique el periodo de devengo y el corte contable."))
    return Salida(out, len(ax.lineas), metodo=f"Meses entre la emisión del comprobante y su registro contable mayores a {meses}.")


def palabras(ax, r) -> Salida:
    """Gastos por palabras clave configurables: capitalización, posibles gastos personales, mejoras o mantenimiento capitalizado."""
    pal = [normalizar_texto(x) for x in r.p.get("palabras", [])]
    minimo = dec(r.p.get("importe_minimo", "0"))
    pref = tuple(r.cuentas) or ("6",)
    lado = r.p.get("lado", "D")
    out = []
    for ln in ax.lineas:
        imp = ln.debe if lado == "D" else ln.haber
        if not ln.cuenta.startswith(pref) or imp < minimo:
            continue
        g = normalizar_texto(ln.glosa or "")
        hit = next((p for p in pal if p and p in g), None)
        if hit:
            out.append(Res(titulo=r.p.get("titulo", "Gasto que requiere evaluación") + f" ({ln.cuenta})", condicion=f"Línea {ln.id} por {imp}: glosa "
                           f"«{ln.glosa}» contiene «{hit}».", importe=imp, cuenta=ln.cuenta, tercero=ln.tercero, documento=doc_de(ln), linea_id=ln.id,
                           asiento=asiento_de(ln), centro_costo=ln.cc, evidencia=[ev_linea(ln)], clave=f"{r.codigo}|{ln.id}", exposicion=f"LINEA|{ln.id}",
                           calidad="PARCIAL", tributario=r.p.get("tributario"), regularizacion=r.p.get("regularizacion"),
                           causa="Indicio por palabra clave: requiere evaluación profesional con el sustento."))
    return Salida(out, len(ax.lineas), metodo=f"Glosas de las cuentas {', '.join(pref)} ≥ {minimo} con palabras clave configuradas: {', '.join(pal)}.")


def _mensual(ax, pref, por="cuenta"):
    m = defaultdict(lambda: defaultdict(lambda: CERO))
    for ln in ax.lineas:
        if ln.cuenta.startswith(pref) and 1 <= (ln.periodo or 0) <= 12:
            k = {"cuenta": ln.cuenta, "cc": ln.cc or "(sin CC)", "proyecto": ln.proyecto or "(sin proyecto)"}[por]
            m[k][ln.periodo] += (ln.debe - ln.haber) if pref[0] != "7" else (ln.haber - ln.debe)
    return m


def recurrentes_omitidos(ax, r) -> Salida:
    min_meses = int(r.p.get("min_meses", 3))
    pref = tuple(r.cuentas) or ("63", "65")
    serie = defaultdict(dict)
    for k, ls in ax.asientos.items():
        ter = _terceros_asiento(ls)
        for x in ls:
            if x.cuenta.startswith(pref) and x.debe and 1 <= x.periodo <= 12:
                serie[(x.cuenta, ter.tercero if ter else None)][x.periodo] = serie[(x.cuenta, ter.tercero if ter else None)].get(x.periodo, CERO) + x.debe
    out = []
    p = ax.periodo
    for (c, t), meses in serie.items():
        previos = [m for m in range(p - min_meses, p) if m >= 1]
        if len(previos) == min_meses and all(m in meses for m in previos) and p not in meses and t:
            prom = sum((meses[m] for m in previos), CERO) / len(previos)
            out.append(Res(titulo=f"Posible gasto recurrente omitido en {c} ({t})", condicion=f"Registrado en los {min_meses} meses anteriores "
                           f"(promedio {prom.quantize(Decimal('0.01'))}) y sin registro en el periodo {p:02d}.", importe=prom.quantize(Decimal("0.01")),
                           cuenta=c, tercero=t, evidencia=[ev_calc("Serie mensual", **{f"p{m:02d}": meses.get(m, CERO) for m in range(1, p + 1)})],
                           clave=f"REC|{c}|{t}|{p}", exposicion=f"OMITIDO|{c}|{t}|{p}", calidad="PARCIAL", tributario="POSIBLE_DIFERENCIA_TEMPORAL",
                           causa="Hipótesis: el comprobante del mes aún no se registró (servicio recibido pendiente de facturación) o el servicio terminó.",
                           recomendacion="Verifique el contrato y los movimientos posteriores al cierre antes de provisionar."))
    return Salida(out, len(serie), metodo=f"Gastos por cuenta y proveedor presentes en los {min_meses} meses previos y ausentes en el periodo.")


def variaciones(ax, r) -> Salida:
    pref = tuple(r.cuentas) or ("6",)
    pct = Decimal(str(r.p.get("porcentaje", 50)))
    minimo = dec(r.p.get("importe_minimo", "1000"))
    m = _mensual(ax, pref)
    p = ax.periodo
    out = []
    for c, meses in m.items():
        hist = [meses.get(x, CERO) for x in range(1, p)]
        if len(hist) < int(r.p.get("min_meses", 3)) or not any(hist):
            continue
        actual = meses.get(p, CERO)
        prom = Decimal(statistics.mean(hist)).quantize(Decimal("0.01"))
        med = Decimal(statistics.median(hist)).quantize(Decimal("0.01"))
        var = actual - prom
        if prom and abs(var) >= minimo and abs(var) * 100 / abs(prom) >= pct:
            out.append(Res(titulo=f"Variación significativa en la cuenta {c}", condicion=f"Periodo {p:02d}: {actual}; promedio de los meses anteriores "
                           f"{prom} (mediana {med}); variación {var} ({(var * 100 / prom).quantize(Decimal('0.1'))} %).", importe=abs(var), cuenta=c,
                           evidencia=[ev_calc("Serie mensual", promedio=prom, mediana=med, **{f"p{x:02d}": meses.get(x, CERO) for x in range(1, p + 1)})],
                           clave=f"VAR|{c}|{p}", exposicion=f"VARIACION|{c}|{p}", estructural=False, calidad="PARCIAL",
                           causa="Indicador analítico: requiere explicación del negocio, no implica un error."))
    return Salida(out, len(m), metodo=f"Variación del periodo frente al promedio de los meses anteriores ≥ {pct} % y ≥ {minimo}.")


def concentracion_flujo(ax, r) -> Salida:
    """Concentración de gastos por proveedor o de ingresos por cliente (tercero de la contrapartida del asiento)."""
    pref = tuple(r.cuentas) or ("6",)
    pct = Decimal(str(r.p.get("porcentaje", 40)))
    por, rs, tot = defaultdict(lambda: CERO), {}, CERO
    for k, ls in ax.asientos.items():
        ter = _terceros_asiento(ls)
        imp = sum(((x.debe if pref[0] == "6" else x.haber) for x in ls if x.cuenta.startswith(pref)), CERO)
        if imp and ter:
            por[ter.tercero] += imp
            rs[ter.tercero] = ter.razon_social
            tot += imp
    out = []
    if tot and len(por) >= int(r.p.get("min_terceros", 3)):
        for t, v in por.items():
            if v * 100 / tot >= pct:
                out.append(Res(titulo=f"Concentración {'de gastos en el proveedor' if pref[0] == '6' else 'de ingresos en el cliente'} {rs[t] or t}",
                               condicion=f"{(v * 100 / tot).quantize(Decimal('0.1'))} % del total ({v} de {tot}).", importe=v, cuenta=pref[0], tercero=t,
                               razon_social=rs[t], evidencia=[ev_calc("Participación", importe_tercero=v, total=tot)], clave=f"CFL|{pref[0]}|{t}",
                               exposicion=f"CONC|{pref[0]}|{t}", estructural=False, calidad="PARCIAL"))
    return Salida(out, len(por), tot, f"Participación de cada tercero (contrapartida del asiento) ≥ {pct} %.")


def dup_cuenta(ax, r) -> Salida:
    """Mismo comprobante del mismo tercero cargado en asientos distintos de las cuentas indicadas (6 o 70)."""
    from app.auditoria.r_duplicados import _exactos_y_aproximados, _grupo_doc
    pref = tuple(r.cuentas) or ("6",)
    docs = []
    for k, ls in ax.asientos.items():
        cargos = [x for x in ls if x.cuenta.startswith(pref) and ((x.debe if pref[0] == "6" else x.haber) > 0)]
        if not cargos:
            continue
        doc = next((x for x in ls if x.numero and x.cuenta.startswith(pref)), None) or next((x for x in ls if x.numero and x.cuenta[:1] in "14"), None)
        if not doc:
            continue
        ter = _terceros_asiento(ls)
        g = _grupo_doc(cargos)
        g.update(tercero=doc.tercero or (ter.tercero if ter else ""), td=(doc.tipo_doc or "").lstrip("0"), serie=doc.serie or "", numero=doc.numero,
                 lineas=[doc] + cargos, importe=sum(((x.debe if pref[0] == "6" else x.haber) for x in cargos), CERO))
        docs.append(g)
    out = _exactos_y_aproximados(ax, r, f"CTA{pref[0]}", docs, "Comprobante")
    return Salida(out, len(docs), metodo="Mismo tercero y comprobante normalizado en asientos distintos (exacta) o mismo tercero e importe en pocos días.")


# ===================================================================== INGRESOS
def anticipos_como_ingreso(ax, r) -> Salida:
    r.p.setdefault("palabras", ["ANTICIPO", "ADELANTO", "A CUENTA"])
    r.p.setdefault("titulo", "Anticipo registrado como ingreso: requiere evaluación")
    r.p["lado"] = "H"
    r.cuentas = r.cuentas or ["70"]
    return palabras(ax, r)


def valorizaciones(ax, r) -> Salida:
    regs = [x for x in ax.registros("SERVICIO_PROCESO") if x.get("valorizacion_acumulada") not in (None, "")]
    if not regs:
        return Salida(estado="SIN_DATOS", mensaje="El registro de servicios en proceso no incluye valorizaciones (campo valorizacion_acumulada).")
    ingresos = defaultdict(lambda: CERO)
    for ln in ax.lineas:
        if ln.cuenta.startswith("70") and ln.proyecto:
            ingresos[ln.proyecto] += ln.haber - ln.debe
    tol = Decimal(str(r.p.get("tolerancia_pct", 5)))
    out = []
    for x in regs:
        v = dec(x["valorizacion_acumulada"]) - dec(x.get("valorizacion_anterior", 0))
        i = ingresos.get(str(x["_clave"]), CERO)
        if v and abs(v - i) * 100 / abs(v) > tol:
            out.append(Res(titulo=f"Valorizaciones e ingresos del proyecto {x['_clave']} difieren", condicion=f"Valorizado en el ejercicio {v}; ingreso "
                           f"reconocido {i}.", importe=abs(v - i), proyecto=str(x["_clave"]), cuenta="70",
                           evidencia=[ev_reg("annex_support_records", x["_id"], f"Proyecto {x['_clave']}", valorizacion=v, ingreso=i)],
                           clave=f"VALO|{x['_clave']}", exposicion=f"PROY|{x['_clave']}", calidad="PARCIAL",
                           causa="Puede corresponder a ingresos devengados no facturados o facturación anticipada: no es un error por sí mismo.",
                           recomendacion="Evalúe la obligación de desempeño y el grado de avance (NIIF 15)."))
    return Salida(out, len(regs), metodo=f"Valorización del ejercicio frente a ingresos de la cuenta 70 por proyecto (tolerancia {tol} %).")


# ===================================================================== DEVENGOS Y CORTE
def gastos_anticipados(ax, r) -> Salida:
    regs = ax.registros("GASTO_ANTICIPADO")
    if not regs:
        return Salida(estado="SIN_DATOS", mensaje="No se importó el registro de gastos contratados por anticipado (fase 5).")
    esperado = defaultdict(lambda: CERO)
    detalle = defaultdict(list)
    for x in regs:
        ini, fin = _f(x.get("fecha_inicio")), _f(x.get("fecha_fin"))
        imp = dec(x.get("importe"))
        if not ini or not fin or fin <= ini:
            continue
        total = (fin - ini).days + 1
        resto = max(min((fin - ax.corte).days, total), 0)
        e = (imp * resto / total).quantize(Decimal("0.01"))
        c = x.get("_cuenta") or "18"
        esperado[c] += e
        detalle[c].append((x, e))
    libro = defaultdict(lambda: CERO)
    for ln in ax.ctx3.lineas_hasta_corte:
        for c in esperado:
            if ln.cuenta.startswith(c):
                libro[c] += ln.debe - ln.haber
    out = []
    for c, e in esperado.items():
        dif = libro[c] - e
        if abs(dif) > dec(r.p.get("tolerancia", "1")):
            out.append(Res(titulo=f"Devengo del gasto anticipado en la cuenta {c} no coincide", condicion=f"Saldo por devengar según contratos {e}; saldo "
                           f"contable {libro[c]}: diferencia {dif}.", importe=abs(dif), cuenta=c,
                           evidencia=[ev_reg("annex_support_records", x["_id"], f"{x['_clave']} {x.get('concepto') or ''}", por_devengar=v) for x, v in detalle[c]],
                           clave=f"DEVA|{c}", exposicion=f"CUENTA|{c}", tributario="POSIBLE_DIFERENCIA_TEMPORAL",
                           regularizacion="REQUIERE_AJUSTE" if dif > 0 else "REQUIERE_EVALUACION_TRIBUTARIA",
                           causa="Devengo mensual no registrado o registrado en exceso." if dif > 0 else "Gasto reconocido por encima del devengo."))
    return Salida(out, len(regs), metodo="Saldo por devengar de cada contrato (días restantes / días de vigencia) frente al saldo contable.")


def corte_posterior(ax, r) -> Salida:
    """Comprobantes emitidos hasta el corte y registrados después (movimientos posteriores como evidencia complementaria)."""
    pref = tuple(r.cuentas) or ("42",)
    lado = r.p.get("lado", "H")
    minimo = dec(r.p.get("importe_minimo", "0"))
    out = []
    for ln in ax.posteriores:
        imp = ln.haber if lado == "H" else ln.debe
        if ln.cuenta.startswith(pref) and imp >= minimo and ln.fecha_emision and ln.fecha_emision <= ax.corte < (ln.fecha or ax.corte):
            ingreso = pref[0] in "17"
            out.append(Res(titulo=f"{'Ingreso' if ingreso else 'Obligación'} del periodo registrado después del corte: {doc_de(ln) or ''}",
                           condicion=f"Comprobante emitido el {ln.fecha_emision:%d/%m/%Y} y contabilizado el {ln.fecha:%d/%m/%Y} (posterior al corte "
                                     f"{ax.corte:%d/%m/%Y}) por {imp}.", importe=imp, cuenta=ln.cuenta, tercero=ln.tercero, razon_social=ln.razon_social,
                           documento=doc_de(ln), linea_id=ln.id, asiento=asiento_de(ln), evidencia=[ev_linea(ln, f"Evento posterior (no integra el saldo "
                                                                                                                 f"histórico): {ln.glosa or ''}")],
                           clave=f"CORTE|{ln.id}", exposicion=f"DOC|{ln.tercero}|{doc_de(ln)}", tributario="POSIBLE_DIFERENCIA_TEMPORAL",
                           regularizacion="REQUIERE_AJUSTE",
                           causa="Diferencia de corte: el hecho económico corresponde al periodo auditado.",
                           recomendacion="Evalúe si corresponde reconocer la obligación o el ingreso al corte; el saldo histórico no se modifica."))
    return Salida(out, len(ax.posteriores), metodo="Movimientos posteriores al corte (evidencia complementaria) con fecha de emisión hasta el corte.")


def ingresos_anticipados(ax, r) -> Salida:
    out = []
    for ln in ax.lineas:
        if ln.cuenta.startswith(tuple(r.cuentas) or ("70",)) and ln.haber and ln.fecha_emision and ln.fecha_emision > ax.corte:
            out.append(Res(titulo=f"Ingreso con comprobante posterior al corte: {doc_de(ln) or ''}", condicion=f"Comprobante emitido el "
                           f"{ln.fecha_emision:%d/%m/%Y} reconocido en el periodo.", importe=ln.haber, cuenta=ln.cuenta, tercero=ln.tercero, documento=doc_de(ln),
                           linea_id=ln.id, asiento=asiento_de(ln), evidencia=[ev_linea(ln)], clave=f"INGA|{ln.id}", exposicion=f"LINEA|{ln.id}",
                           tributario="POSIBLE_DIFERENCIA_TEMPORAL"))
    return Salida(out, len(ax.lineas), metodo="Ingresos del periodo con comprobante emitido después de la fecha de corte.")


def provisiones_antiguas(ax, r) -> Salida:
    hs = fase3(ax, "SIN_MOVIMIENTO", r.codigo, cuentas=r.cuentas or ["48"], valor=r.p.get("meses", 6), importe_minimo=r.p.get("importe_minimo", "1"))
    return Salida([res_de_h3(h, "PROVA", recomendacion="Revise si la provisión sigue vigente (NIC 37).") for h in hs], len(hs),
                  metodo="Evaluador SIN_MOVIMIENTO de la fase 3: provisiones con saldo y sin movimiento en los últimos meses.")


EVALUADORES = {"vencidos": vencidos, "antiguos": antiguos, "concentracion": concentracion, "contrario_tercero": contrario_tercero,
               "aplicaciones_pendientes": aplicaciones_pendientes, "anticipos": anticipos, "personal": personal, "diferencia_cambio": diferencia_cambio,
               "deterioro": deterioro, "anexos_vs_balance": anexos_vs_balance, "pagos_sin_documento": pagos_sin_documento, "sin_tercero": sin_tercero,
               "conciliacion_memoria": conciliacion_memoria, "bancaria": bancaria, "transferencias_internas": transferencias_internas,
               "movimientos_sin_documento": movimientos_sin_documento, "gastos_sin_documento": gastos_sin_documento, "gastos_sin_cc": gastos_sin_cc,
               "gastos_fuera_periodo": gastos_fuera_periodo, "palabras": palabras, "recurrentes_omitidos": recurrentes_omitidos,
               "variaciones": variaciones, "concentracion_flujo": concentracion_flujo, "dup_cuenta": dup_cuenta,
               "anticipos_como_ingreso": anticipos_como_ingreso, "valorizaciones": valorizaciones, "gastos_anticipados": gastos_anticipados,
               "corte_posterior": corte_posterior, "ingresos_anticipados": ingresos_anticipados, "provisiones_antiguas": provisiones_antiguas}
