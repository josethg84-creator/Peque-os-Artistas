"""Módulo TRIBUTARIA (preventiva).

Dos tipos de reglas:
- Analíticas (no normativas): comparan registros y contabilidad, identifican documentación faltante o detracciones y
  retenciones pendientes de identificación. No aplican tasas ni umbrales legales.
- Normativas: dependen de una norma (bancarización, gastos sujetos a reparo o a límites, plazos de anotación, cuarta
  categoría). El catálogo NO incluye normas, tasas ni umbrales: el responsable tributario registra la norma de referencia,
  la fuente oficial, las fechas de publicación y vigencia, las condiciones, excepciones y parámetros, y la valida. Sin esa
  validación la regla no se ejecuta; si faltan datos, el resultado queda «pendiente de evaluación».
Ningún resultado es una infracción confirmada ni una determinación de deuda tributaria.
"""


from app.auditoria.base import CERO, Res, Salida, asiento_de, dec, doc_de, ev_calc, ev_linea, ev_reg, norm_doc
from app.importers.normalizacion import normalizar_texto

PENDIENTE = "PENDIENTE_EVALUACION"


def _faltan(r, claves):
    faltan = [k for k in claves if r.p.get(k) in (None, "", [])]
    if faltan:
        return Salida(estado="PENDIENTE_EVALUACION", mensaje=f"Faltan parámetros normativos validados: {', '.join(faltan)}. No se asumen valores.")
    return None


def credito_fiscal(ax, r) -> Salida:
    docs = ax.documentos("COMPRAS")
    if not docs:
        return Salida(estado="SIN_DATOS", mensaje="No se importó el registro de compras del periodo.")
    reg = {(d.documento_tercero or "", norm_doc(d.serie), norm_doc(d.numero)) for d in docs}
    out = []
    for k, ls in ax.asientos.items():
        igv = [x for x in ls if x.cuenta.startswith(tuple(r.cuentas) or ("40111",)) and x.debe]
        if not igv:
            continue
        doc = next((x for x in ls if x.numero and x.cuenta.startswith(("42", "43", "46"))), None)
        clave = (doc.tercero or "", norm_doc(doc.serie), norm_doc(doc.numero)) if doc else None
        if not doc or clave not in reg:
            x = igv[0]
            out.append(Res(titulo=f"Crédito fiscal pendiente de evaluación en el asiento {asiento_de(x)}", condicion=f"IGV de {sum((y.debe for y in igv), CERO)} "
                           + (f"del comprobante {doc_de(doc)} que no figura en el registro de compras." if doc else "sin comprobante identificado."),
                           importe=sum((y.debe for y in igv), CERO), cuenta=x.cuenta, tercero=doc.tercero if doc else None, documento=doc_de(doc) if doc else None,
                           asiento=asiento_de(x), linea_id=x.id, evidencia=[ev_linea(y) for y in ls[:10]], clave=f"TRI|CF|{k}",
                           exposicion=f"DOC|{doc.tercero}|{doc_de(doc)}" if doc else f"ASIENTO|{k}", tributario=PENDIENTE, calidad="PARCIAL",
                           regularizacion="REQUIERE_EVALUACION_TRIBUTARIA",
                           recomendacion="Verifique la anotación del comprobante en el registro de compras y los requisitos del crédito fiscal."))
    return Salida(out, len(docs), metodo="IGV de compras contabilizado frente a los comprobantes del registro de compras importado.")


def detracciones_pendientes(ax, r) -> Salida:
    docs = [d for d in ax.documentos("COMPRAS") if d.codigo_detraccion]
    if not docs:
        return Salida(estado="SIN_DATOS", mensaje="No hay comprobantes con código de detracción en el registro de compras.")
    constancias = {(ln.tercero or "", norm_doc(ln.serie), norm_doc(ln.numero)) for ln in ax.ctx3.lineas_hasta_corte + ax.posteriores if ln.constancia}
    out = []
    for d in docs:
        k = (d.documento_tercero or "", norm_doc(d.serie), norm_doc(d.numero))
        if not d.constancia_detraccion and k not in constancias:
            out.append(Res(titulo=f"Detracción sin sustento identificado: {d.serie}-{d.numero}", condicion=f"Comprobante {d.serie}-{d.numero} de "
                           f"{d.razon_social or d.documento_tercero} por {d.total} con código {d.codigo_detraccion} sin constancia de depósito en el registro "
                           "ni en la contabilidad.", importe=dec(d.total), tercero=d.documento_tercero, razon_social=d.razon_social, documento=f"{d.serie}-{d.numero}",
                           evidencia=[ev_reg("documentos_registro", d.id, f"Registro de compras {d.serie}-{d.numero}", total=d.total,
                                             codigo=d.codigo_detraccion)], clave=f"TRI|DET|{d.id}", exposicion=f"DOC|{d.documento_tercero}|{d.serie}-{d.numero}",
                           tributario=PENDIENTE, calidad="PARCIAL", regularizacion="REQUIERE_DOCUMENTACION",
                           recomendacion="Identifique la constancia de depósito; el sistema no declara incumplimientos."))
    return Salida(out, len(docs), metodo="Comprobantes con código de detracción frente a constancias del registro y del libro (incluye movimientos posteriores).")


def retenciones_sustento(ax, r) -> Salida:
    out = []
    for ln in ax.lineas:
        if ln.cuenta.startswith(tuple(r.cuentas) or ("40113", "40114", "40172")) and ln.haber and not ln.numero:
            out.append(Res(titulo=f"Retención o percepción pendiente de sustento ({ln.cuenta})", condicion=f"Línea {ln.id} por {ln.haber} sin comprobante "
                           "de retención o percepción identificado.", importe=ln.haber, cuenta=ln.cuenta, tercero=ln.tercero, linea_id=ln.id,
                           asiento=asiento_de(ln), evidencia=[ev_linea(ln)], clave=f"TRI|RET|{ln.id}", exposicion=f"LINEA|{ln.id}", tributario=PENDIENTE,
                           calidad="INSUFICIENTE", regularizacion="REQUIERE_DOCUMENTACION"))
    return Salida(out, len(ax.lineas), metodo="Retenciones y percepciones registradas sin número de comprobante.")


def bancarizacion(ax, r) -> Salida:
    f = _faltan(r, ["umbral_pen"])
    if f:
        return f
    caja = tuple(r.p.get("cuentas_efectivo", ["101"]))
    umbral = {"PEN": dec(r.p["umbral_pen"]), "USD": dec(r.p.get("umbral_usd") or "0")}
    out = []
    for k, ls in ax.asientos.items():
        pagos = [x for x in ls if x.cuenta.startswith(("42", "43", "46")) and x.debe]
        efectivo = [x for x in ls if x.cuenta.startswith(caja) and x.haber]
        if pagos and efectivo:
            x = pagos[0]
            mon = x.moneda or "PEN"
            imp = (x.debe_me or x.debe) if mon != "PEN" else x.debe
            if umbral.get(mon) and imp >= umbral[mon]:
                out.append(Res(titulo=f"Operación que requiere evaluar el medio de pago ({doc_de(x) or asiento_de(x)})", condicion=f"Pago de {imp} {mon} "
                               f"con cargo a efectivo ({efectivo[0].cuenta}) igual o mayor al umbral validado ({umbral[mon]}).", importe=x.debe, cuenta=x.cuenta,
                               tercero=x.tercero, documento=doc_de(x), asiento=asiento_de(x), linea_id=x.id, evidencia=[ev_linea(y) for y in ls[:10]],
                               clave=f"TRI|BAN|{k}", exposicion=f"DOC|{x.tercero}|{doc_de(x)}", tributario=PENDIENTE, calidad="PARCIAL",
                               regularizacion="REQUIERE_EVALUACION_TRIBUTARIA"))
    return Salida(out, len(ax.asientos), metodo=f"Pagos con efectivo ({', '.join(caja)}) ≥ umbral de la norma validada ({r.p['umbral_pen']} PEN).")


def reparos(ax, r) -> Salida:
    f = _faltan(r, ["cuentas"] if not r.cuentas else [])
    if f and not r.p.get("palabras"):
        return f
    pal = [normalizar_texto(x) for x in r.p.get("palabras", [])]
    out = []
    for ln in ax.lineas:
        if not ln.debe or not ln.cuenta.startswith("6"):
            continue
        por_cuenta = r.cuentas and ln.cuenta.startswith(tuple(r.cuentas))
        hit = next((p for p in pal if p and p in normalizar_texto(ln.glosa or "")), None)
        if por_cuenta or hit:
            out.append(Res(titulo=f"Gasto potencialmente sujeto a reparo tributario ({ln.cuenta})", condicion=f"Línea {ln.id} por {ln.debe}: "
                           + (f"cuenta {ln.cuenta} incluida en la regla" if por_cuenta else f"glosa «{ln.glosa}» contiene «{hit}»") + ".",
                           importe=ln.debe, cuenta=ln.cuenta, tercero=ln.tercero, documento=doc_de(ln), linea_id=ln.id, asiento=asiento_de(ln),
                           evidencia=[ev_linea(ln)], clave=f"TRI|REP|{ln.id}", exposicion=f"LINEA|{ln.id}", tributario="POSIBLE_DIFERENCIA_PERMANENTE",
                           calidad="PARCIAL", regularizacion="REQUIERE_EVALUACION_TRIBUTARIA",
                           causa="Potencial: la deducibilidad depende del sustento y de las condiciones de la norma, no solo de la cuenta.",
                           recomendacion="Evalúe el tratamiento tributario con el sustento; puede generar una adición en la determinación del impuesto."))
    return Salida(out, len(ax.lineas), metodo="Gastos en cuentas o con palabras definidas por la regla normativa validada.")


def periodo_tributario(ax, r) -> Salida:
    f = _faltan(r, ["plazo_meses"])
    if f:
        return f
    plazo = int(r.p["plazo_meses"])
    out = []
    for d in ax.documentos("COMPRAS"):
        if d.fecha_emision and d.periodo:
            meses = (d.ejercicio - d.fecha_emision.year) * 12 + d.periodo - d.fecha_emision.month
            if meses > plazo:
                out.append(Res(titulo=f"Comprobante anotado fuera del plazo validado: {d.serie}-{d.numero}", condicion=f"Emitido el {d.fecha_emision:%d/%m/%Y} "
                               f"y anotado en el periodo {d.ejercicio}-{d.periodo:02d} ({meses} meses; plazo validado {plazo}).", importe=dec(d.igv),
                               tercero=d.documento_tercero, documento=f"{d.serie}-{d.numero}",
                               evidencia=[ev_reg("documentos_registro", d.id, f"{d.serie}-{d.numero}", igv=d.igv, total=d.total)],
                               clave=f"TRI|PER|{d.id}", exposicion=f"DOC|{d.documento_tercero}|{d.serie}-{d.numero}", tributario=PENDIENTE,
                               regularizacion="REQUIERE_EVALUACION_TRIBUTARIA"))
    return Salida(out, len(ax.documentos("COMPRAS")), metodo=f"Meses entre emisión y periodo de anotación frente al plazo de la norma validada ({plazo}).")


def limites(ax, r) -> Salida:
    f = _faltan(r, ["limite_importe"] if not r.p.get("limite_pct_ingresos") else [])
    if f or not r.cuentas:
        return f or Salida(estado="PENDIENTE_EVALUACION", mensaje="Indique las cuentas sujetas al límite en la regla validada.")
    gasto = sum((ln.debe - ln.haber for ln in ax.lineas if ln.cuenta.startswith(tuple(r.cuentas))), CERO)
    limite = dec(r.p.get("limite_importe"))
    if r.p.get("limite_pct_ingresos"):
        ingresos = sum((ln.haber - ln.debe for ln in ax.lineas if ln.cuenta.startswith("70")), CERO)
        limite = (ingresos * dec(r.p["limite_pct_ingresos"]) / 100).quantize(dec("0.01"))
    out = []
    if gasto > limite:
        out.append(Res(titulo=f"Gastos sujetos a límite exceden el límite validado ({', '.join(r.cuentas)})", condicion=f"Gasto {gasto}; límite {limite}: "
                       f"exceso {gasto - limite}.", importe=gasto - limite, cuenta=r.cuentas[0], clave=f"TRI|LIM|{r.codigo}", exposicion=f"LIMITE|{r.codigo}",
                       evidencia=[ev_calc("Límite tributario", gasto=gasto, limite=limite)], tributario="POSIBLE_DIFERENCIA_PERMANENTE",
                       regularizacion="REQUIERE_EVALUACION_TRIBUTARIA"))
    return Salida(out, 1, gasto, "Suma de gastos de las cuentas sujetas frente al límite de la norma validada.")


def cuarta(ax, r) -> Salida:
    f = _faltan(r, ["umbral"])
    if f:
        return f
    ret = tuple(r.p.get("cuentas_retencion", ["40172"]))
    out = []
    for k, ls in ax.asientos.items():
        rh = [x for x in ls if (x.tipo_doc or "").lstrip("0") == "2" and x.haber and x.cuenta.startswith("4")]
        if rh and not any(x.cuenta.startswith(ret) for x in ls):
            x = rh[0]
            bruto = x.haber
            if bruto >= dec(r.p["umbral"]):
                out.append(Res(titulo=f"Recibo por honorarios sin retención registrada: {doc_de(x)}", condicion=f"Recibo de {bruto} igual o mayor al umbral "
                               f"validado ({r.p['umbral']}) sin línea de retención en {', '.join(ret)}.", importe=bruto, cuenta=x.cuenta, tercero=x.tercero,
                               documento=doc_de(x), asiento=asiento_de(x), linea_id=x.id, evidencia=[ev_linea(y) for y in ls[:8]],
                               clave=f"TRI|4TA|{k}", exposicion=f"DOC|{x.tercero}|{doc_de(x)}", tributario=PENDIENTE, calidad="PARCIAL",
                               regularizacion="REQUIERE_EVALUACION_TRIBUTARIA",
                               causa="Puede existir suspensión de retenciones u otra excepción: verificar antes de concluir."))
    return Salida(out, len(ax.asientos), metodo="Recibos por honorarios (tipo 02) ≥ umbral validado sin retención de cuarta categoría en el asiento.")


EVALUADORES = {"credito_fiscal": credito_fiscal, "detracciones_pendientes": detracciones_pendientes, "retenciones_sustento": retenciones_sustento,
               "bancarizacion": bancarizacion, "reparos": reparos, "periodo_tributario": periodo_tributario, "limites": limites, "cuarta": cuarta}

