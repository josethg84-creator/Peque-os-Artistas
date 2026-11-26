"""Exportación profesional de anexos.

Excel: encabezado empresarial, resumen con FÓRMULAS verificables (saldo final = inicial + debe − haber;
diferencia = contable − detalle), importes numéricos con formato, encabezados fijos, filtros, subtotales
con SUBTOTAL() y totales, observaciones y espacios de elaboración / revisión / aprobación. El libro
masivo agrega índice con enlaces internos, resumen, balance de comprobación, diferencias, observaciones
y control de revisión. PDF: logotipo, datos de la empresa, encabezados repetidos, «Página x de y»,
versión, responsables y fecha de generación. Los espacios de visto bueno NO son firmas digitales.
"""
import io
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.anexos import render
from app.anexos.flujo import enmascarar, requiere_mascara
from app.core import config
from app.models import Anexo, Empresa, HallazgoAnexo, VersionAnexo

FORMATO = '#,##0.00;[Red]-#,##0.00'
MAX_FILAS_PDF = 3000
NOTA_FIRMAS = "Espacios de visto bueno para el flujo interno. No constituyen firma digital certificada."
ESTADOS = {"PENDIENTE_GENERACION": "Pendiente de generación", "GENERADO": "Generado", "EN_ELABORACION": "En elaboración",
           "EN_REVISION": "En revisión", "OBSERVADO": "Observado", "SUBSANADO": "Subsanado", "REVISADO": "Revisado",
           "APROBADO": "Aprobado", "CERRADO": "Cerrado", "REABIERTO": "Reabierto"}
RESULTADOS = {"CUADRADO": "Cuadrado", "CUADRADO_CON_OBSERVACIONES": "Cuadrado con observaciones",
              "PARCIALMENTE_SUSTENTADO": "Parcialmente sustentado", "DESCUADRADO": "Descuadrado",
              "INFORMACION_INSUFICIENTE": "Información insuficiente"}
PERIODOS = ["Apertura", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre",
            "Noviembre", "Diciembre", "Cierre"]


def ruta_logo(empresa_id: int) -> Path | None:
    for ext in ("png", "jpg"):
        p = Path(config.DATA_DIR) / "anexos" / str(empresa_id) / f"logo.{ext}"
        if p.exists():
            return p
    return None


def preparar(db: Session, a: Anexo, version_id: int | None = None, mascara: bool = False) -> dict:
    v = db.get(VersionAnexo, version_id or a.version_id)
    if not v or v.anexo_id != a.id:
        raise LookupError("Versión no encontrada")
    snap = json.loads(v.plantilla_snapshot)
    filas = render.filas_version(db, v.id, a.especialidad)
    if mascara:
        filas = [enmascarar(f) if requiere_mascara(f, a.especialidad) else f for f in filas]
    vista = render.aplicar(snap, filas)
    hall = db.scalars(select(HallazgoAnexo).where(HallazgoAnexo.anexo_id == a.id, HallazgoAnexo.estado == "ABIERTO")
                      .order_by(HallazgoAnexo.severidad, HallazgoAnexo.id)).all()
    return {"anexo": a, "version": v, "resumen": json.loads(v.resumen), "snap": snap, "vista": vista, "hallazgos": hall,
            "empresa": db.get(Empresa, a.empresa_id)}


def _titulo(p: dict) -> str:
    enc = p["snap"].get("encabezado") or {}
    a = p["anexo"]
    t = enc.get("titulo") or f"Anexo — {p['snap']['nombre']}"
    return f"{t} · Cuenta {a.cuenta} {a.descripcion or ''}".strip()


def _ref(p: dict) -> list[tuple[str, str]]:
    a, v, e = p["anexo"], p["version"], p["empresa"]
    return [("Razón social", e.razon_social), ("RUC", e.ruc), ("Ejercicio", str(a.ejercicio)),
            ("Periodo", f"{a.periodo:02d} · {PERIODOS[min(a.periodo, 13)]}"), ("Fecha de corte", a.fecha_corte.strftime("%d/%m/%Y")),
            ("Cuenta", f"{a.cuenta} — {a.descripcion or ''}"), ("Moneda", "Soles (PEN) — importes en moneda nacional"),
            ("Versión", f"{v.numero}" + (" (aprobada, inmutable)" if v.inmutable else "")),
            ("Generado", f"{v.generado_en:%d/%m/%Y %H:%M} por {v.generado_por}"),
            ("Estado de revisión", ESTADOS.get(a.estado_revision, a.estado_revision)),
            ("Resultado de conciliación", RESULTADOS.get(p["resumen"].get("resultado"), "—")),
            ("Elaboró / revisó / aprobó", " / ".join(x or "—" for x in (a.responsable_elaboracion or a.elaborado_por,
                                                                        a.responsable_revision or a.revisado_por,
                                                                        a.responsable_aprobacion or a.aprobado_por))),
            ("Fecha de exportación", datetime.now().strftime("%d/%m/%Y %H:%M"))]


def _valor(v, tipo):
    if v is None or v == "":
        return None
    if tipo in ("importe", "pct", "tasa"):
        return float(v) if isinstance(v, Decimal) and tipo == "tasa" else (v if isinstance(v, Decimal) else Decimal(str(v)))
    if tipo == "entero":
        return int(v)
    if tipo == "fecha":
        return v if isinstance(v, date) else v
    return str(v)


# ------------------------------------------------------------------ Excel
class _Estilos:
    def __init__(self):
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        self.titulo = Font(bold=True, size=13, color="0F2742")
        self.negrita = Font(bold=True)
        self.gris = Font(bold=True, color="667085")
        self.blanco = Font(bold=True, color="FFFFFF")
        self.cab = PatternFill("solid", fgColor="0F2742")
        self.sub = PatternFill("solid", fgColor="E8EDF5")
        self.tot = PatternFill("solid", fgColor="D5DEEC")
        self.alerta = Font(bold=True, color="B42318")
        self.borde = Border(bottom=Side(style="thin", color="C9D2E0"))
        self.der = Alignment(horizontal="right")
        self.wrap = Alignment(wrap_text=True, vertical="top")


def _celda(ws, valor, *, fuente=None, relleno=None, formato=None, alinear=None):
    from openpyxl.cell import WriteOnlyCell
    c = WriteOnlyCell(ws, value=valor)
    if fuente:
        c.font = fuente
    if relleno:
        c.fill = relleno
    if formato:
        c.number_format = formato
    if alinear:
        c.alignment = alinear
    return c


def _hoja_anexo(wb, nombre: str, p: dict, est: _Estilos, indice: str | None = None):
    from openpyxl.utils import get_column_letter
    ws = wb.create_sheet(nombre)
    a, r = p["anexo"], p["resumen"]
    vista = p["vista"]
    cols = vista["columnas"]
    refs = _ref(p)
    fila_det = 1 + 1 + len(refs) + 1 + 10 + 1  # título, refs, separación, resumen (10), separación
    ws.freeze_panes = f"A{fila_det + 1}"
    for j, c in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(j)].width = 14 if c["tipo"] in ("importe", "fecha", "entero", "pct", "tasa") else (
            34 if c["campo"] in ("razon_social", "glosa", "observacion", "descripcion") else 16)
    ws.column_dimensions["A"].width = max(ws.column_dimensions["A"].width or 0, 30)
    ws.append([_celda(ws, _titulo(p), fuente=est.titulo)] + ([_celda(ws, '=HYPERLINK("#\'Índice\'!A1","← Índice")')] if indice else []))
    for k, v in refs:
        ws.append([_celda(ws, k, fuente=est.gris), v])
    ws.append([])
    base = 1 + len(refs) + 2  # fila de «RESUMEN CONTABLE»
    sg_formula = "+" if r["naturaleza"] == "D" else "-"
    letra_saldo = None
    for j, c in enumerate(cols, 1):
        if c["campo"] == "saldo":
            letra_saldo = get_column_letter(j)
    filas_res = [
        ("RESUMEN CONTABLE (signo natural de la cuenta)", None, est.negrita),
        ("Saldo inicial", Decimal(r["saldo_inicial"]), None),
        ("Movimientos del debe", Decimal(r["debe"]), None),
        ("Movimientos del haber", Decimal(r["haber"]), None),
        ("Saldo final contable", f"=B{base + 1}{sg_formula}B{base + 2}{'-' if sg_formula == '+' else '+'}B{base + 3}", est.negrita),
        ("Saldo detallado en el anexo", "__DET__", None),
        ("Saldo sustentado documentalmente", Decimal(r["saldo_sustentado"]), None),
        ("Saldo pendiente de sustento", f"=B{base + 5}-B{base + 6}", None),
        ("Diferencia de conciliación (contable − detalle)", f"=B{base + 4}-B{base + 5}", est.alerta),
        ("Resultado", RESULTADOS.get(r.get("resultado"), "—") + f" — {r.get('explicacion') or ''}", est.negrita),
    ]
    n_filas = len(vista["filas"]) + len(vista["grupos"])
    fin = fila_det + n_filas
    for etiqueta, valor, fuente in filas_res:
        if valor == "__DET__":
            valor = f"=SUBTOTAL(9,{letra_saldo}{fila_det + 1}:{letra_saldo}{max(fin, fila_det + 1)})" if letra_saldo else Decimal(r["saldo_detalle"])
        celdas = [_celda(ws, etiqueta, fuente=fuente or est.gris)]
        if valor is not None:
            celdas.append(_celda(ws, valor, formato=FORMATO if not isinstance(valor, str) or valor.startswith("=") else None, fuente=fuente))
        ws.append(celdas)
    ws.append([])
    ws.append([_celda(ws, c["titulo"], fuente=est.blanco, relleno=est.cab) for c in cols])
    filas = vista["filas"]
    grupos = vista["grupos"]
    sumables = {c["campo"] for c in cols if c["tipo"] == "importe" and (c.get("total") or c["campo"] == "saldo")}
    fila_actual = fila_det
    idx = 0

    def escribir(rw):
        nonlocal fila_actual
        celdas = []
        for c in cols:
            v = _valor(rw.get(c["campo"]), c["tipo"])
            fmt = FORMATO if c["tipo"] == "importe" else ("0.00" if c["tipo"] == "pct" else ("0.000000" if c["tipo"] == "tasa" else
                                                                                             ("dd/mm/yyyy" if c["tipo"] == "fecha" else None)))
            celdas.append(_celda(ws, v, formato=fmt) if fmt else v)
        ws.append(celdas)
        fila_actual += 1
    if grupos:
        for g in grupos:
            ini = fila_actual + 1
            for rw in filas[idx: idx + g["filas"]]:
                escribir(rw)
            idx += g["filas"]
            celdas = []
            for j, c in enumerate(cols, 1):
                if j == 1:
                    celdas.append(_celda(ws, f"Subtotal {g['clave']}", fuente=est.negrita, relleno=est.sub))
                elif c["campo"] in sumables:
                    L = get_column_letter(j)
                    celdas.append(_celda(ws, f"=SUBTOTAL(9,{L}{ini}:{L}{fila_actual})", fuente=est.negrita, relleno=est.sub, formato=FORMATO))
                else:
                    celdas.append(_celda(ws, None, relleno=est.sub))
            ws.append(celdas)
            fila_actual += 1
    else:
        for rw in filas:
            escribir(rw)
    if cols:
        ws.auto_filter.ref = f"A{fila_det}:{get_column_letter(len(cols))}{max(fila_actual, fila_det + 1)}"
    tot = []
    for j, c in enumerate(cols, 1):
        if j == 1:
            tot.append(_celda(ws, "TOTAL", fuente=est.negrita, relleno=est.tot))
        elif c["campo"] in sumables:
            L = get_column_letter(j)
            tot.append(_celda(ws, f"=SUBTOTAL(9,{L}{fila_det + 1}:{L}{max(fila_actual, fila_det + 1)})", fuente=est.negrita, relleno=est.tot, formato=FORMATO))
        else:
            tot.append(_celda(ws, None, relleno=est.tot))
    ws.append(tot)
    if vista["filtros_aplicados"]:
        ws.append([_celda(ws, f"Vista filtrada: {vista['filas_filtradas']} de {vista['total_filas']} filas. La conciliación considera el detalle completo.",
                          fuente=est.alerta)])
    ws.append([])
    ws.append([_celda(ws, "OBSERVACIONES ABIERTAS", fuente=est.negrita)])
    for h in p["hallazgos"][:300]:
        ws.append([h.severidad, h.titulo, _celda(ws, h.importe, formato=FORMATO) if h.importe is not None else None, h.responsable or ""])
    if not p["hallazgos"]:
        ws.append(["Sin observaciones abiertas"])
    ws.append([])
    ws.append([_celda(ws, "Conclusión del contador", fuente=est.gris), a.conclusion or ""])
    ws.append([_celda(ws, "Acciones correctivas", fuente=est.gris), a.acciones_correctivas or ""])
    ws.append([])
    for rol, quien, cuando in (("Elaborado por", a.responsable_elaboracion or a.elaborado_por, None),
                               ("Revisado por", a.responsable_revision or a.revisado_por, a.revisado_en),
                               ("Aprobado por", a.responsable_aprobacion or a.aprobado_por, a.aprobado_en)):
        ws.append([_celda(ws, rol, fuente=est.gris), quien or "______________________", "Fecha:",
                   cuando.strftime("%d/%m/%Y %H:%M") if cuando else "____/____/______"])
    ws.append([_celda(ws, NOTA_FIRMAS, fuente=est.gris)])
    return ws


def _nombre_hoja(base: str, usados: set) -> str:
    n = "".join(ch for ch in base if ch not in "[]:*?/\\")[:31] or "Hoja"
    k, cand = 2, n
    while cand in usados:
        cand = f"{n[:28]}~{k}"
        k += 1
    usados.add(cand)
    return cand


def excel_anexo(p: dict) -> bytes:
    from openpyxl import Workbook
    wb = Workbook(write_only=True)
    _hoja_anexo(wb, _nombre_hoja(f"Anexo {p['anexo'].cuenta}", set()), p, _Estilos())
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def excel_libro(db: Session, empresa: Empresa, anexos: list[Anexo], ctx, mascara_fn, avance=lambda p, e: None) -> bytes:
    """Libro masivo: índice, resumen general, balance de comprobación, una hoja por anexo, diferencias,
    observaciones y control de revisión."""
    from openpyxl import Workbook
    est = _Estilos()
    wb = Workbook(write_only=True)
    usados = {"Índice", "Resumen general", "Balance de comprobación", "Diferencias", "Observaciones", "Control de revisión"}
    nombres = [(a, _nombre_hoja(f"{a.cuenta} {a.descripcion or ''}", usados)) for a in anexos]
    corte = anexos[0].fecha_corte if anexos else date.today()
    cab = [("Razón social", empresa.razon_social), ("RUC", empresa.ruc), ("Fecha de corte", corte.strftime("%d/%m/%Y")),
           ("Moneda", "Soles (PEN)"), ("Generado", datetime.now().strftime("%d/%m/%Y %H:%M"))]

    def encabezado(ws, titulo):
        ws.append([_celda(ws, titulo, fuente=est.titulo)])
        for k, v in cab:
            ws.append([_celda(ws, k, fuente=est.gris), v])
        ws.append([])

    def cabecera(ws, titulos):
        ws.append([_celda(ws, t, fuente=est.blanco, relleno=est.cab) for t in titulos])
    # Índice
    ws = wb.create_sheet("Índice")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 16, 60
    encabezado(ws, "Expediente de anexos contables — Índice")
    cabecera(ws, ["Cuenta", "Anexo", "Resultado", "Estado de revisión", "Versión"])
    for a, n in nombres:
        ws.append([a.cuenta, _celda(ws, f'=HYPERLINK("#\'{n}\'!A1","{(a.descripcion or a.cuenta).replace(chr(34), "")}")'),
                   RESULTADOS.get(a.resultado, "—"), ESTADOS.get(a.estado_revision), a.version_actual])
    for t in ("Resumen general", "Balance de comprobación", "Diferencias", "Observaciones", "Control de revisión"):
        ws.append(["", _celda(ws, f'=HYPERLINK("#\'{t}\'!A1","{t}")')])
    # Resumen general
    ws = wb.create_sheet("Resumen general")
    encabezado(ws, "Resumen general de anexos")
    cabecera(ws, ["Cuenta", "Descripción", "Saldo contable", "Saldo detallado", "Sustentado", "Diferencia", "Resultado", "Estado", "Ir"])
    ini = len(cab) + 4
    for i, (a, n) in enumerate(nombres):
        f = ini + i
        ws.append([a.cuenta, a.descripcion, _celda(ws, a.saldo_contable, formato=FORMATO), _celda(ws, a.saldo_detalle, formato=FORMATO),
                   _celda(ws, a.saldo_sustentado, formato=FORMATO), _celda(ws, f"=C{f}-D{f}", formato=FORMATO),
                   RESULTADOS.get(a.resultado, "—"), ESTADOS.get(a.estado_revision), _celda(ws, f'=HYPERLINK("#\'{n}\'!A1","Ver")')])
    # Balance de comprobación (desde el libro)
    ws = wb.create_sheet("Balance de comprobación")
    encabezado(ws, "Balance de comprobación (hojas con información, desde el libro)")
    cabecera(ws, ["Cuenta", "Descripción", "Saldo inicial (D+/A−)", "Debe", "Haber", "Saldo final (D+/A−)"])
    ini = len(cab) + 4
    hojas = ctx.hojas() if ctx else []
    for i, c in enumerate(hojas):
        s = ctx.saldos_de(c)
        f = ini + i
        ws.append([c, ctx.descripcion(c), _celda(ws, Decimal(s["si"]) / 100, formato=FORMATO), _celda(ws, Decimal(s["debe"]) / 100, formato=FORMATO),
                   _celda(ws, Decimal(s["haber"]) / 100, formato=FORMATO), _celda(ws, f"=C{f}+D{f}-E{f}", formato=FORMATO)])
    if hojas:
        fin = ini + len(hojas) - 1
        ws.append([_celda(ws, "TOTAL", fuente=est.negrita), None] + [_celda(ws, f"=SUM({L}{ini}:{L}{fin})", fuente=est.negrita, formato=FORMATO)
                                                                      for L in "CDEF"])
    # una hoja por anexo
    for i, (a, n) in enumerate(nombres):
        if i % 20 == 0:
            avance(10 + int(70 * i / max(len(nombres), 1)), f"Escribiendo hojas ({i}/{len(nombres)})")
        p = preparar(db, a, mascara=mascara_fn(a))
        _hoja_anexo(wb, n, p, est, indice="Índice")
    # diferencias
    ws = wb.create_sheet("Diferencias")
    encabezado(ws, "Anexos con diferencias de conciliación (sin ajustes)")
    cabecera(ws, ["Cuenta", "Descripción", "Saldo contable", "Saldo detallado", "Diferencia", "Explicación"])
    for a, n in nombres:
        if a.diferencia:
            ws.append([a.cuenta, a.descripcion, _celda(ws, a.saldo_contable, formato=FORMATO), _celda(ws, a.saldo_detalle, formato=FORMATO),
                       _celda(ws, a.diferencia, formato=FORMATO), RESULTADOS.get(a.resultado)])
    # observaciones
    ws = wb.create_sheet("Observaciones")
    encabezado(ws, "Observaciones abiertas")
    cabecera(ws, ["Cuenta", "Código", "Severidad", "Observación", "Importe", "Responsable", "Acción correctiva"])
    ids = [a.id for a, _ in nombres]
    cuentas = {a.id: a.cuenta for a, _ in nombres}
    for k in range(0, len(ids), 500):
        for h in db.scalars(select(HallazgoAnexo).where(HallazgoAnexo.anexo_id.in_(ids[k:k + 500]), HallazgoAnexo.estado == "ABIERTO")
                            .order_by(HallazgoAnexo.anexo_id, HallazgoAnexo.id)):
            ws.append([cuentas[h.anexo_id], h.codigo, h.severidad, h.titulo, _celda(ws, h.importe, formato=FORMATO) if h.importe is not None else None,
                       h.responsable, h.accion_correctiva])
    # control de revisión
    ws = wb.create_sheet("Control de revisión")
    encabezado(ws, "Control de revisión")
    cabecera(ws, ["Cuenta", "Estado", "Versión", "Elaboró", "Revisó", "Fecha revisión", "Aprobó", "Fecha aprobación", "Fecha límite", "Conclusión"])
    for a, n in nombres:
        ws.append([a.cuenta, ESTADOS.get(a.estado_revision), a.version_actual, a.responsable_elaboracion or a.elaborado_por,
                   a.responsable_revision or a.revisado_por, _celda(ws, a.revisado_en, formato="dd/mm/yyyy hh:mm") if a.revisado_en else None,
                   a.aprobado_por, _celda(ws, a.aprobado_en, formato="dd/mm/yyyy hh:mm") if a.aprobado_en else None,
                   _celda(ws, a.fecha_limite, formato="dd/mm/yyyy") if a.fecha_limite else None, a.conclusion])
    ws.append([])
    ws.append([NOTA_FIRMAS])
    avance(90, "Guardando el libro")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ PDF
def _estilos_pdf():
    from reportlab.lib.styles import getSampleStyleSheet
    e = getSampleStyleSheet()
    celda = e["BodyText"].clone("celda", fontSize=6.8, leading=8.2)
    return {"titulo": e["Title"].clone("t", fontSize=14, leading=17), "h2": e["Heading2"].clone("h2", fontSize=11, spaceBefore=6),
            "h3": e["Heading3"].clone("h3", fontSize=9.5), "texto": e["BodyText"].clone("x", fontSize=8.5, leading=11),
            "celda": celda, "celda_d": celda.clone("cd", alignment=2), "nota": celda.clone("n", textColor="#667085")}


def _fmt(v, tipo):
    from xml.sax.saxutils import escape
    if v is None or v == "":
        return ""
    if tipo == "importe":
        return f"{Decimal(str(v)):,.2f}"
    if tipo == "pct":
        return f"{Decimal(str(v)):.2f} %"
    if tipo == "fecha" and isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return escape(str(v))


def _bloque_anexo(p: dict, st: dict, logo: Path | None, ancho: float) -> list:
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle
    a, r, vista = p["anexo"], p["resumen"], p["vista"]
    out = []
    cab = [Paragraph(f"<b>{_fmt(p['empresa'].razon_social, 'texto')}</b><br/>RUC {p['empresa'].ruc}", st["texto"])]
    if logo and p["snap"].get("usar_logo", True):
        try:
            cab.insert(0, Image(str(logo), width=28 * mm, height=14 * mm, kind="proportional"))
        except Exception:
            pass
    out.append(Table([cab], colWidths=[32 * mm, ancho - 32 * mm] if len(cab) == 2 else [ancho], style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    out.append(Paragraph(_fmt(_titulo(p), "texto"), st["titulo"]))
    refs = _ref(p)
    out.append(Paragraph(" · ".join(f"<b>{k}:</b> {_fmt(v, 'texto')}" for k, v in refs[2:]), st["texto"]))
    out.append(Spacer(1, 3 * mm))
    filas_res = [("Saldo inicial", r["saldo_inicial"]), ("Movimientos del debe", r["debe"]), ("Movimientos del haber", r["haber"]),
                 ("Saldo final contable", r["saldo_final_contable"]), ("Saldo detallado en el anexo", r["saldo_detalle"]),
                 ("Saldo sustentado documentalmente", r["saldo_sustentado"]), ("Saldo pendiente de sustento", r["saldo_pendiente_sustento"]),
                 ("   · sin documento", r["sin_documento"]), ("   · sin detalle (saldos iniciales)", r["sin_detalle"]),
                 ("   · por clasificar", r["por_clasificar"]), ("Diferencia de conciliación", r["diferencia"])]
    if r.get("saldo_balance_importado") is not None:
        filas_res.append(("Saldo según balance de comprobación importado", r["saldo_balance_importado"]))
    t = Table([[Paragraph(k, st["celda"]), Paragraph(_fmt(v, "importe"), st["celda_d"])] for k, v in filas_res], colWidths=[70 * mm, 35 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0")),
                           ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#E8EDF5")),
                           ("BACKGROUND", (0, 10), (-1, 10), colors.HexColor("#FDECEC" if Decimal(r["diferencia"]) else "#E6F6EC"))]))
    out += [Paragraph("Resumen contable y conciliación", st["h3"]), t,
            Paragraph(f"<b>{RESULTADOS.get(r.get('resultado'), '—')}</b> — {_fmt(r.get('explicacion'), 'texto')} "
                      "<i>(un saldo cuadrado no implica, por sí solo, que esté correctamente sustentado)</i>", st["texto"]),
            Spacer(1, 3 * mm), Paragraph("Detalle", st["h3"])]
    cols = vista["columnas"]
    num = lambda c: c["tipo"] in ("importe", "entero", "pct", "tasa")  # noqa: E731
    datos = [[Paragraph(f"<font color='white'><b>{_fmt(c['titulo'], 'texto')}</b></font>", st["celda_d"] if num(c) else st["celda"])
              for c in cols]]
    estilos = []
    filas = vista["filas"]
    sumables = [c["campo"] for c in cols if c["tipo"] == "importe" and (c.get("total") or c["campo"] == "saldo")]

    def fila_pdf(rw):
        return [Paragraph(_fmt(rw.get(c["campo"]), c["tipo"]), st["celda_d"] if num(c) else st["celda"]) for c in cols]
    escritas = 0
    if vista["grupos"]:
        idx = 0
        for g in vista["grupos"]:
            for rw in filas[idx: idx + g["filas"]]:
                if escritas < MAX_FILAS_PDF:
                    datos.append(fila_pdf(rw))
                    escritas += 1
            idx += g["filas"]
            datos.append([Paragraph(f"<b>Subtotal {_fmt(g['clave'], 'texto')}</b>", st["celda"]) if j == 0 else
                          (Paragraph(f"<b>{_fmt(g['subtotales'].get(c['campo']), 'importe')}</b>", st["celda_d"]) if c["campo"] in sumables else "")
                          for j, c in enumerate(cols)])
            estilos.append(("BACKGROUND", (0, len(datos) - 1), (-1, len(datos) - 1), colors.HexColor("#E8EDF5")))
    else:
        for rw in filas[:MAX_FILAS_PDF]:
            datos.append(fila_pdf(rw))
            escritas += 1
    datos.append([Paragraph("<b>TOTAL</b>", st["celda"]) if j == 0 else
                  (Paragraph(f"<b>{_fmt(vista['totales'].get(c['campo']), 'importe')}</b>", st["celda_d"]) if c["campo"] in sumables else "")
                  for j, c in enumerate(cols)])
    estilos.append(("BACKGROUND", (0, len(datos) - 1), (-1, len(datos) - 1), colors.HexColor("#D5DEEC")))
    pesos = [2.2 if c["campo"] in ("razon_social", "glosa", "observacion", "descripcion") else 1 for c in cols]
    anchos = [ancho * w / sum(pesos) for w in pesos]
    tabla = Table(datos, repeatRows=1, colWidths=anchos)
    tabla.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2742")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0")), ("VALIGN", (0, 0), (-1, -1), "TOP")] + estilos))
    out.append(tabla)
    if len(filas) > escritas:
        out.append(Paragraph(f"Se muestran {escritas} de {len(filas)} filas; el detalle completo está en la exportación a Excel. "
                             "Los totales consideran todas las filas.", st["nota"]))
    if vista["filtros_aplicados"]:
        out.append(Paragraph(f"Vista filtrada: {vista['filas_filtradas']} de {vista['total_filas']} filas. La conciliación considera el detalle completo.", st["nota"]))
    nota = (r.get("extras") or {}).get("nota")
    if nota:
        out.append(Paragraph(_fmt(nota, "texto"), st["nota"]))
    out.append(Spacer(1, 3 * mm))
    out.append(Paragraph("Observaciones abiertas", st["h3"]))
    if p["hallazgos"]:
        for h in p["hallazgos"][:200]:
            out.append(Paragraph(f"<b>[{h.severidad}]</b> {_fmt(h.titulo, 'texto')}" + (f" — {_fmt(h.importe, 'importe')}" if h.importe is not None else ""),
                                 st["texto"]))
    else:
        out.append(Paragraph("Sin observaciones abiertas.", st["texto"]))
    out.append(Paragraph(f"<b>Conclusión del contador:</b> {_fmt(a.conclusion, 'texto') or '—'}", st["texto"]))
    out.append(Paragraph(f"<b>Acciones correctivas:</b> {_fmt(a.acciones_correctivas, 'texto') or '—'}", st["texto"]))
    out.append(Spacer(1, 6 * mm))
    firmas = [[Paragraph(f"<b>{t}</b><br/>{_fmt(q, 'texto') or '______________________'}<br/>"
                         f"{(c.strftime('%d/%m/%Y %H:%M') if c else 'Fecha: ____/____/______')}", st["texto"])
               for t, q, c in (("Elaborado por", a.responsable_elaboracion or a.elaborado_por, None),
                               ("Revisado por", a.responsable_revision or a.revisado_por, a.revisado_en),
                               ("Aprobado por", a.responsable_aprobacion or a.aprobado_por, a.aprobado_en))]]
    out.append(Table(firmas, colWidths=[ancho / 3] * 3, style=[("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#98A2B3"))]))
    out.append(Paragraph(NOTA_FIRMAS, st["nota"]))
    return out


def _documento(historia: list, titulo: str, pie: str, horizontal=True) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import SimpleDocTemplate
    tam = landscape(A4) if horizontal else A4

    class Numerado(canvas.Canvas):  # «Página x de y»
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._paginas = []

        def showPage(self):
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._paginas)
            for estado in self._paginas:
                self.__dict__.update(estado)
                self.setFont("Helvetica", 7)
                self.setFillGray(0.4)
                self.drawString(10 * mm, 6 * mm, pie[:150])
                self.drawRightString(tam[0] - 10 * mm, 6 * mm, f"Página {self._pageNumber} de {total}")
                super().showPage()
            super().save()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=tam, leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=12 * mm, title=titulo)
    doc.build(historia, canvasmaker=Numerado)
    return buf.getvalue()


def pdf_anexo(p: dict) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    horizontal = p["snap"].get("orientacion", "HORIZONTAL") == "HORIZONTAL"
    ancho = (landscape(A4)[0] if horizontal else A4[0]) - 20 * mm
    st = _estilos_pdf()
    a, v = p["anexo"], p["version"]
    historia = _bloque_anexo(p, st, ruta_logo(a.empresa_id), ancho)
    pie = (f"{p['empresa'].razon_social} · Anexo {a.cuenta} al {a.fecha_corte:%d/%m/%Y} · versión {v.numero} · "
           f"generado {datetime.now():%d/%m/%Y %H:%M}")
    return _documento(historia, _titulo(p), pie, horizontal)


def pdf_expediente(db: Session, empresa: Empresa, anexos: list[Anexo], mascara_fn, avance=lambda p, e: None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, PageBreak, Paragraph, Spacer, Table, TableStyle
    st = _estilos_pdf()
    ancho = landscape(A4)[0] - 20 * mm
    logo = ruta_logo(empresa.id)
    corte = anexos[0].fecha_corte if anexos else date.today()
    h = []
    if logo:
        try:
            h.append(Image(str(logo), width=40 * mm, height=20 * mm, kind="proportional"))
        except Exception:
            pass
    h += [Spacer(1, 20 * mm), Paragraph("EXPEDIENTE DE CIERRE CONTABLE — ANEXOS", st["titulo"]),
          Paragraph(f"{_fmt(empresa.razon_social, 'texto')} · RUC {empresa.ruc}", st["h2"]),
          Paragraph(f"Fecha de corte: {corte:%d/%m/%Y} · Anexos: {len(anexos)} · Generado: {datetime.now():%d/%m/%Y %H:%M}", st["texto"]),
          Paragraph(NOTA_FIRMAS, st["nota"]), PageBreak(), Paragraph("Índice y resumen general", st["h2"])]
    datos = [[Paragraph(f"<b>{t}</b>", st["celda"]) for t in ("Cuenta", "Descripción", "Saldo contable", "Detalle", "Diferencia",
                                                             "Resultado", "Estado", "Versión")]]
    for a in anexos:
        datos.append([a.cuenta, Paragraph(_fmt(a.descripcion, "texto"), st["celda"]), Paragraph(_fmt(a.saldo_contable, "importe"), st["celda_d"]),
                      Paragraph(_fmt(a.saldo_detalle, "importe"), st["celda_d"]), Paragraph(_fmt(a.diferencia, "importe"), st["celda_d"]),
                      Paragraph(RESULTADOS.get(a.resultado, "—"), st["celda"]), Paragraph(ESTADOS.get(a.estado_revision, ""), st["celda"]),
                      str(a.version_actual)])
    t = Table(datos, repeatRows=1, colWidths=[22 * mm, 90 * mm, 28 * mm, 28 * mm, 28 * mm, 35 * mm, 25 * mm, 15 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF5")), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0"))]))
    h.append(t)
    difs = [a for a in anexos if a.diferencia]
    h += [Spacer(1, 4 * mm), Paragraph(f"Anexos con diferencias: {len(difs)}", st["h3"])]
    for a in difs[:300]:
        h.append(Paragraph(f"{a.cuenta} {_fmt(a.descripcion, 'texto')}: diferencia {_fmt(a.diferencia, 'importe')} (sin ajustes)", st["texto"]))
    for i, a in enumerate(anexos):
        if i % 10 == 0:
            avance(10 + int(80 * i / max(len(anexos), 1)), f"Componiendo anexos ({i}/{len(anexos)})")
        h.append(PageBreak())
        h += _bloque_anexo(preparar(db, a, mascara=mascara_fn(a)), st, logo, ancho)
    avance(92, "Paginando el expediente")
    return _documento(h, "Expediente de cierre contable", f"{empresa.razon_social} · Expediente de anexos al {corte:%d/%m/%Y}")
