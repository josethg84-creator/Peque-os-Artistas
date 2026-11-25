"""Exportación de análisis a Excel y PDF.

Excel: una hoja por sección con referencias (empresa, RUC, reporte, periodo, fecha y usuario),
encabezados con estilo, importes NUMÉRICOS con formato contable, autofiltro, encabezado fijo y
fila de totales. PDF: horizontal, encabezado repetido en cada página y numeración.
"""
import io
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.analisis import antiguedad as ant_mod
from app.analisis import comparativo as comp_mod
from app.analisis import destino as dest_mod
from app.analisis import navegacion, pcge, saldos

FORMATO_IMPORTE = '#,##0.00;[Red]-#,##0.00'
MAX_FILAS_PDF = 3000


@dataclass
class Tabla:
    titulo: str
    columnas: list[tuple[str, str, str]]  # (clave, etiqueta, tipo: texto|importe|entero|pct)
    filas: list[dict]
    totales: list[str] = field(default_factory=list)
    nota: str | None = None


@dataclass
class Reporte:
    nombre: str
    titulo: str
    referencias: list[tuple[str, str]]
    tablas: list[Tabla]


def _num(v, tipo):
    if v is None or v == "":
        return None
    if tipo in ("importe", "pct"):
        return Decimal(str(v))
    if tipo == "entero":
        return int(v)
    return v


def a_excel(rep: Reporte) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    wb.remove(wb.active)
    cab = PatternFill("solid", fgColor="0F2742")
    borde = Border(bottom=Side(style="thin", color="C9D2E0"))
    for i, t in enumerate(rep.tablas):
        ws = wb.create_sheet((t.titulo or f"Hoja {i + 1}")[:31].replace("/", "-").replace(":", " "))
        ws["A1"] = rep.titulo
        ws["A1"].font = Font(bold=True, size=14, color="0F2742")
        fila = 2
        for k, v in rep.referencias:
            ws.cell(fila, 1, k).font = Font(bold=True, color="667085")
            ws.cell(fila, 2, v)
            fila += 1
        ws.cell(fila, 1, t.titulo).font = Font(bold=True, size=12)
        if t.nota:
            ws.cell(fila, 3, t.nota).font = Font(italic=True, color="B25E09")
        fila += 2
        enc = fila
        for j, (_, etiqueta, tipo) in enumerate(t.columnas, 1):
            c = ws.cell(enc, j, etiqueta)
            c.font, c.fill = Font(bold=True, color="FFFFFF"), cab
            c.alignment = Alignment(horizontal="right" if tipo in ("importe", "entero", "pct") else "left", vertical="center",
                                    wrap_text=True)
        for f in t.filas:
            fila += 1
            for j, (clave, _, tipo) in enumerate(t.columnas, 1):
                c = ws.cell(fila, j, _num(f.get(clave), tipo))
                if tipo == "importe":
                    c.number_format = FORMATO_IMPORTE
                elif tipo == "pct":
                    c.number_format = '0.00"%"'
                c.border = borde
        if t.filas:
            ws.auto_filter.ref = f"A{enc}:{get_column_letter(len(t.columnas))}{fila}"
        if t.totales and t.filas:
            fila += 1
            ws.cell(fila, 1, "TOTAL").font = Font(bold=True)
            for j, (clave, _, tipo) in enumerate(t.columnas, 1):
                if clave in t.totales:
                    total = sum((Decimal(str(f.get(clave) or 0)) for f in t.filas), Decimal("0"))
                    c = ws.cell(fila, j, total)
                    c.font, c.number_format = Font(bold=True), FORMATO_IMPORTE
        ws.freeze_panes = ws.cell(enc + 1, 1)
        for j, (clave, etiqueta, tipo) in enumerate(t.columnas, 1):
            largo = max([len(str(etiqueta))] + [len(str(f.get(clave) or "")) for f in t.filas[:500]])
            ws.column_dimensions[get_column_letter(j)].width = min(max(10, largo + 2), 60)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def a_pdf(rep: Reporte) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    buf = io.BytesIO()
    estilos = getSampleStyleSheet()
    celda = estilos["BodyText"].clone("celda", fontSize=7, leading=8.5)
    celda_d = celda.clone("celda_d", alignment=2)
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=12 * mm,
                            bottomMargin=12 * mm, title=rep.titulo)
    historia = [Paragraph(rep.titulo, estilos["Title"]),
                Paragraph(" · ".join(f"<b>{k}:</b> {v}" for k, v in rep.referencias), estilos["BodyText"]), Spacer(1, 4 * mm)]
    for t in rep.tablas:
        historia.append(Paragraph(t.titulo, estilos["Heading3"]))
        if t.nota:
            historia.append(Paragraph(f"<i>{t.nota}</i>", celda))
        filas = t.filas[:MAX_FILAS_PDF]
        datos = [[Paragraph(f"<b>{e}</b>", celda_d if tp in ("importe", "entero", "pct") else celda) for _, e, tp in t.columnas]]
        for f in filas:
            datos.append([Paragraph(_fmt(f.get(k), tp), celda_d if tp in ("importe", "entero", "pct") else celda)
                          for k, _, tp in t.columnas])
        if t.totales and filas:
            datos.append([Paragraph("<b>TOTAL</b>", celda)] + [
                Paragraph(f"<b>{_fmt(sum((Decimal(str(x.get(k) or 0)) for x in t.filas), Decimal('0')), 'importe')}</b>", celda_d)
                if k in t.totales else "" for k, _, _ in t.columnas[1:]])
        ancho = (landscape(A4)[0] - 20 * mm) / max(len(t.columnas), 1)
        tabla = Table(datos, repeatRows=1, colWidths=[ancho] * len(t.columnas))
        tabla.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF5")),
                                   ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        historia += [tabla, Spacer(1, 4 * mm)]
        if len(t.filas) > MAX_FILAS_PDF:
            historia.append(Paragraph(f"Se muestran {MAX_FILAS_PDF} de {len(t.filas)} filas; use la exportación a Excel para el detalle completo.", celda))

    def pie(canvas, documento):
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(landscape(A4)[0] - 10 * mm, 6 * mm, f"Página {documento.page} · {rep.titulo}")
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return buf.getvalue()


def _fmt(v, tipo):
    if v is None or v == "":
        return ""
    if tipo == "importe":
        return f"{Decimal(str(v)):,.2f}"
    if tipo == "pct":
        return f"{Decimal(str(v)):.2f} %"
    from xml.sax.saxutils import escape
    return escape(str(v))


# ------------------------------------------------------------------ constructores
def referencias(empresa, ejercicio, desde, hasta, usuario, extra=None):
    refs = [("Empresa", f"{empresa.razon_social} — RUC {empresa.ruc}"),
            ("Periodo analizado", f"{ejercicio} · {desde:02d}" + (f" a {hasta:02d}" if hasta != desde else "")),
            ("Generado", f"{datetime.now():%d/%m/%Y %H:%M} por {usuario}")]
    return refs + (extra or [])


COL_SALDOS = [("saldo_inicial", "Saldo inicial", "importe"), ("debe", "Debe", "importe"), ("haber", "Haber", "importe"),
              ("saldo_final", "Saldo final", "importe")]


def balance(db, empresa, ej, d, h, usuario, nivel_max: int | None = None) -> Reporte:
    b = saldos.balance(db, empresa.id, ej, d, h)
    nodos = [n for n in b["nodos"] if nivel_max is None or n["nivel"] <= nivel_max or not n["tiene_hijos"]]
    for n in nodos:
        n["sangria"] = "   " * (n["nivel"] - 1) + n["cuenta"]
    tabla = Tabla("Balance analítico", [("sangria", "Cuenta", "texto"), ("descripcion", "Descripción", "texto"),
                                        ("nivel_nombre", "Nivel", "texto"), ("naturaleza", "Nat.", "texto"), *COL_SALDOS,
                                        ("variacion", "Variación vs anterior", "importe"), ("variacion_pct", "Var. %", "pct"),
                                        ("movimientos", "Movimientos", "entero"), ("terceros", "Terceros", "entero")],
                  nodos, nota="Los totales de cada nivel ya incluyen a sus subcuentas: sume solo un nivel." if b["preliminar"] is False else
                  "PRELIMINAR: sin saldos iniciales importados.")
    elementos = Tabla("Totales por elemento", [("cuenta", "Elemento", "texto"), ("descripcion", "Descripción", "texto"), *COL_SALDOS],
                      [n for n in b["nodos"] if n["nivel"] == 1 and n["cuenta"] != "0"], totales=["saldo_inicial", "debe", "haber", "saldo_final"])
    return Reporte("balance_analitico", "Balance analítico", referencias(empresa, ej, d, h, usuario,
                   [("Cuadre con origen", "Conciliado" if b["control"]["conciliado"] else "NO conciliado")]), [elementos, tabla])


def movimientos(db, empresa, ej, d, h, usuario, filtros: navegacion.Filtros) -> Reporte:
    m = navegacion.movimientos(db, empresa.id, ej, d, h, filtros, 1, 1000000)
    cols = [("fecha_contable", "Fecha", "texto"), ("subdiario", "Subdiario", "texto"), ("numero_asiento", "Asiento", "texto"),
            ("glosa", "Glosa", "texto"), ("cuenta", "Cuenta", "texto"), ("tipo_documento", "TD", "texto"), ("serie", "Serie", "texto"),
            ("numero_documento", "Número", "texto"), ("documento_tercero", "RUC", "texto"), ("razon_social", "Razón social", "texto"),
            ("moneda", "Moneda", "texto"), ("tipo_cambio", "TC", "importe"), ("debe_mn", "Debe", "importe"),
            ("haber_mn", "Haber", "importe"), ("saldo_acumulado", "Saldo acumulado", "importe"), ("centro_costo", "C. costo", "texto"),
            ("proyecto", "Proyecto", "texto"), ("archivo", "Archivo de origen", "texto"), ("fila_origen", "Fila", "entero")]
    filtro_txt = ", ".join(f"{k}: {v}" for k, v in filtros.__dict__.items() if v) or "sin filtros"
    return Reporte("movimientos", "Movimientos detallados", referencias(empresa, ej, d, h, usuario,
                   [("Filtros", filtro_txt), ("Saldo inicial", m["saldo_inicial"]), ("Saldo final", m["saldo_final"])]),
                   [Tabla("Movimientos", cols, m["items"], totales=["debe_mn", "haber_mn"])])


def cuenta(db, empresa, ej, d, h, usuario, codigo: str) -> Reporte:
    b = saldos.balance(db, empresa.id, ej, d, h)
    nodo = next((n for n in b["nodos"] if n["cuenta"] == codigo), None)
    resumen = [{"concepto": k, "importe": nodo[c] if nodo else None} for k, c in
               (("Saldo inicial", "saldo_inicial"), ("Movimiento debe", "debe"), ("Movimiento haber", "haber"),
                ("Movimiento neto", "neto"), ("Saldo final", "saldo_final"), ("Saldo periodo anterior", "saldo_anterior"),
                ("Variación", "variacion"))]
    f = navegacion.Filtros(cuenta=codigo)
    ter = navegacion.terceros(db, empresa.id, ej, d, h, f)["items"]
    mov = movimientos(db, empresa, ej, d, h, usuario, f).tablas[0]
    return Reporte(f"cuenta_{codigo}", f"Análisis de la cuenta {codigo} — {nodo['descripcion'] if nodo else ''}",
                   referencias(empresa, ej, d, h, usuario, [("Perfil", pcge.perfil(codigo).nombre)]),
                   [Tabla("Resumen", [("concepto", "Concepto", "texto"), ("importe", "Importe", "importe")], resumen),
                    Tabla("Composición por tercero", [("tercero", "Tercero", "texto"), ("razon_social", "Razón social", "texto"),
                                                      ("si", "Saldo inicial", "importe"), ("debe", "Debe", "importe"),
                                                      ("haber", "Haber", "importe"), ("saldo_final", "Saldo final", "importe"),
                                                      ("movimientos", "Movs.", "entero")], ter,
                          totales=["si", "debe", "haber", "saldo_final"], nota="Composición preliminar."), mov])


def antiguedad(db, empresa, ej, corte, usuario, **kw) -> Reporte:
    a = ant_mod.calcular(db, empresa.id, ej, corte, **kw)
    cols_t = [("tercero", "Tercero", "texto"), ("razon_social", "Razón social", "texto")] + \
        [(f"t{i}", n, "importe") for i, n in enumerate(a["tramos"])] + [("total", "Total", "importe"), ("documentos", "Docs.", "entero")]
    terceros = [{**t, **{f"t{i}": v for i, v in enumerate(t["tramos"])}} for t in a["terceros"]]
    docs = [{**x, "preliminar": "Sí" if x["preliminar"] else "", "motivos": "; ".join(x["motivos"])} for x in a["documentos"]]
    return Reporte("antiguedad", "Antigüedad de saldos", [("Empresa", f"{empresa.razon_social} — RUC {empresa.ruc}"),
                   ("Fecha de corte", corte.strftime("%d/%m/%Y")), ("Base", a["base"]), ("Fuente", a["fuente"]),
                   ("Cuentas", ", ".join(a["cuentas"])), ("Generado", f"{datetime.now():%d/%m/%Y %H:%M} por {usuario}")],
                   [Tabla("Por tercero", cols_t, terceros, totales=[f"t{i}" for i in range(len(a["tramos"]))] + ["total"], nota=a["nota"]),
                    Tabla("Por documento", [("cuenta", "Cuenta", "texto"), ("tercero", "Tercero", "texto"), ("documento", "Documento", "texto"),
                                            ("fecha_emision", "Emisión", "texto"), ("fecha_vencimiento", "Vencimiento", "texto"),
                                            ("dias", "Días", "entero"), ("tramo_nombre", "Tramo", "texto"), ("importe", "Importe", "importe"),
                                            ("preliminar", "Preliminar", "texto"), ("motivos", "Motivo", "texto")], docs, totales=["importe"])])


def comparativo(db, empresa, usuario, actual, base, titulo="Comparación entre periodos", **kw) -> Reporte:
    c = comp_mod.comparar(db, empresa.id, actual, base, **kw)
    cols = [("clave", "Clave", "texto"), ("descripcion", "Descripción", "texto"), ("actual", c["actual"]["etiqueta"], "importe"),
            ("base", c["base"]["etiqueta"], "importe"), ("variacion", "Variación", "importe"), ("variacion_pct", "Var. %", "pct"),
            ("participacion_pct", "Participación %", "pct"), ("promedio_mensual", "Promedio mensual", "importe"),
            ("movimientos", "Movs.", "entero")]
    return Reporte("comparativo", titulo, [("Empresa", f"{empresa.razon_social} — RUC {empresa.ruc}"),
                   ("Actual", c["actual"]["etiqueta"]), ("Base", c["base"]["etiqueta"]), ("Dimensión", c["dimension"]),
                   ("Medida", c["medida"]), ("Advertencias", " ".join(c["advertencias"]) or "Ninguna"),
                   ("Generado", f"{datetime.now():%d/%m/%Y %H:%M} por {usuario}")],
                   [Tabla(c["dimension"].replace("_", " ").title(), cols, c["filas"], totales=["actual", "base", "variacion"],
                          nota="Var. % vacía = no aplicable (base cero).")])


def destino(db, empresa, ej, d, h, usuario) -> Reporte:
    from app.analisis.motor import cargar_lineas
    f = saldos.fuentes(db, empresa.id, ej)
    od = dest_mod.serializar(dest_mod.analizar(db, empresa.id, cargar_lineas(db, f.filtro_lineas(d, h)), ej, h))
    imp = lambda k, e: (k, e, "importe")  # noqa: E731
    return Reporte("origen_destino", "Comparación de origen y destino", referencias(empresa, ej, d, h, usuario,
                   [("Política", f"Destino {'sí' if od['politica']['usa_destino'] else 'no'} · {od['politica']['modo']} · "
                                 f"destinables {', '.join(od['politica']['destinables'])}")]),
                   [Tabla("Resumen por periodo", [("periodo", "Periodo", "entero"), imp("origen", "Gasto destinable"),
                                                  imp("destino", "Destino"), imp("cargas_imputables", "Cuenta 79"), imp("excluido", "Excluido"),
                                                  imp("diferencia", "Origen − destino"), imp("diferencia_79", "Destino − 79"),
                                                  imp("provision_aplicada_48", "48 aplicada"), imp("abono_78", "Abono 78"),
                                                  ("estado", "Estado", "texto")], od["resumen"],
                          totales=["origen", "destino", "cargas_imputables", "excluido"]),
                    Tabla("Por centro de costo", [("clave", "Centro de costo", "texto"), imp("origen", "Origen"), imp("destino", "Destino"),
                                                  imp("diferencia", "Diferencia"), ("estado", "Estado", "texto")], od["centros_costo"],
                          totales=["origen", "destino", "diferencia"]),
                    Tabla("Por cuenta de destino", [("clave", "Destino", "texto"), imp("esperado", "Esperado"), imp("registrado", "Registrado"),
                                                    imp("diferencia", "Diferencia"), ("estado", "Estado", "texto")], od["destinos"],
                          totales=["esperado", "registrado"]),
                    Tabla("Por cuenta de origen", [("clave", "Cuenta", "texto"), ("descripcion", "Descripción", "texto"), imp("origen", "Gasto"),
                                                   imp("esperado", "Destino esperado"), imp("sin_regla", "Sin destino configurado"),
                                                   ("estado", "Estado", "texto")], od["origenes"], totales=["origen", "esperado"])])


def por_elemento(db, empresa, ej, d, h, usuario, elemento: str) -> Reporte:
    """Análisis de gastos (6) o ingresos (7): por cuenta, por centro de costo y por tercero."""
    from app.analisis.comparativo import Rango
    actual, base = (Rango(ej, d, h), Rango(ej - 1, d, h))
    titulo = "Análisis de gastos por naturaleza" if elemento == "6" else "Análisis de ingresos"
    rep = comparativo(db, empresa, usuario, actual, base, titulo=titulo, dimension="CUENTA", medida="MOVIMIENTO", nivel=0, cuenta=elemento)
    rep.nombre = "gastos" if elemento == "6" else "ingresos"
    tablas = rep.tablas
    if elemento == "7":
        for f in tablas[0].filas:
            f["descripcion"] = f"{f['descripcion'] or ''}{' (transferencia, no es ingreso económico)' if f['clave'][:2] in ('78', '79') else ''}"
    for dim in ("CENTRO_COSTO", "TERCERO"):
        c = comparativo(db, empresa, usuario, actual, base, dimension=dim, cuenta=elemento if elemento == "6" else "70,71,72,73,74,75,76,77")
        tablas.append(c.tablas[0])
    return rep


def hallazgos(empresa, run, filas, usuario) -> Reporte:
    datos = [{**f, "evidencia": f.get("evidencia_txt", "")} for f in filas]
    return Reporte("observaciones", "Reporte de observaciones del análisis", [
        ("Empresa", f"{empresa.razon_social} — RUC {empresa.ruc}"),
        ("Análisis", f"#{run.id} · {run.ejercicio} {run.periodo_desde:02d}–{run.periodo_hasta:02d}"),
        ("Advertencia", "Observaciones automáticas: requieren revisión profesional y no constituyen conclusiones."),
        ("Generado", f"{datetime.now():%d/%m/%Y %H:%M} por {usuario}")],
        [Tabla("Observaciones", [("regla_codigo", "Código", "texto"), ("regla_nombre", "Regla", "texto"), ("regla_version", "Versión", "entero"),
                                 ("riesgo", "Riesgo", "texto"), ("cuenta", "Cuenta", "texto"), ("tercero", "Tercero", "texto"),
                                 ("documento", "Documento", "texto"), ("asiento", "Asiento", "texto"), ("importe", "Importe", "importe"),
                                 ("titulo", "Observación", "texto"), ("explicacion", "Explicación contable", "texto"),
                                 ("recomendacion", "Recomendación", "texto"), ("estado", "Estado de revisión", "texto"),
                                 ("responsable", "Responsable", "texto")], datos,
               nota="El total de importes puede superponer exposiciones; ver «importe sujeto a revisión» en el dashboard.")])


def papel(empresa, p: dict, usuario) -> Reporte:
    comp = p.get("composicion") or {}
    items = comp.get("items") or []
    cols = [(k, k.replace("_", " ").capitalize(), "importe" if k in ("si", "debe", "haber", "saldo_final", "saldo_inicial") else
             ("entero" if k in ("movimientos", "documentos") else "texto")) for k in (items[0].keys() if items else [])]
    ficha = [{"campo": k, "valor": v} for k, v in (
        ("Cuenta", f"{p['cuenta']} — {p.get('descripcion') or ''}"), ("Estado", p["estado"]), ("Versión", p["version"]),
        ("Saldo inicial", p["saldo_inicial"]), ("Debe", p["debe"]), ("Haber", p["haber"]), ("Saldo final", p["saldo_final"]),
        ("Comentarios del analista", p.get("comentarios_analista") or ""), ("Documentos de sustento", p.get("documentos_sustento") or ""),
        ("Conclusión", p.get("conclusion") or ""), ("Responsable", p.get("responsable") or ""),
        ("Fecha de revisión", p.get("fecha_revision") or ""))]
    return Reporte(f"papel_{p['cuenta']}", f"Papel de trabajo preliminar — cuenta {p['cuenta']}",
                   [("Empresa", f"{empresa.razon_social} — RUC {empresa.ruc}"),
                    ("Periodo", f"{p['ejercicio']} · {p['periodo_desde']:02d}–{p['periodo_hasta']:02d}"),
                    ("Generado", f"{datetime.now():%d/%m/%Y %H:%M} por {usuario}"),
                    ("Nota", "Documento preliminar: los anexos conciliados definitivos se generan en la fase 5.")],
                   [Tabla("Ficha", [("campo", "Campo", "texto"), ("valor", "Valor", "texto")], ficha),
                    Tabla(f"Composición preliminar ({comp.get('criterio') or '—'})", cols, items, nota=comp.get("nota")),
                    Tabla("Observaciones vinculadas", [("codigo", "Código", "texto"), ("riesgo", "Riesgo", "texto"), ("titulo", "Observación", "texto"),
                                                       ("importe", "Importe", "importe"), ("estado", "Estado", "texto")], p.get("hallazgos") or [])])
