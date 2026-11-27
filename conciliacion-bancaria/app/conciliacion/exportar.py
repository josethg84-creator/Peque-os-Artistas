"""Exportación de conciliaciones a Excel y PDF (reutiliza estilos, numeración de páginas y logotipo de la fase 5).

Libro Excel por conciliación: Resumen (con fórmulas), Reporte especializado (p. ej. conciliación bancaria con fórmulas
saldo banco → banco ajustado / saldo libros → libros ajustado → diferencia final), Fuente contable, Fuente externa,
Conciliados, No conciliados, Diferencias, Observaciones y Control de aprobación. Cada fila conserva la referencia
al registro original (tabla e id de origen, fila del archivo). Los vistos buenos NO son firmas digitales."""
import io
import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.anexos.exportar import FORMATO, NOTA_FIRMAS, _celda, _documento, _Estilos, _estilos_pdf, _fmt, ruta_logo
from app.conciliacion import consultas
from app.conciliacion.servicio import GRAVEDAD
from app.models import (AprobacionConciliacion, AsignacionRegistro, Conciliacion, DiferenciaConciliacion, Empresa, FuenteConciliacion,
                        GrupoConciliacion, MatchConciliacion, RegistroFuente, RevisionConciliacion, VersionConciliacion)

ESTADOS = {"BORRADOR": "Borrador", "EJECUTADA": "Ejecutada", "EN_REVISION": "En revisión", "OBSERVADA": "Observada", "REVISADA": "Revisada",
           "APROBADA": "Aprobada", "CERRADA": "Cerrada", "REABIERTA": "Reabierta"}
COLS_REG = [("Id registro", "id", None), ("Fuente", "lado", None), ("Fecha", "fecha", None), ("Periodo", "periodo", None), ("Cuenta", "cuenta", None),
            ("Tipo doc.", "tipo_documento", None), ("Serie", "serie", None), ("Número", "numero", None), ("Operación", "operacion", None),
            ("Referencia", "referencia", None), ("Tercero", "tercero", None), ("Razón social", "razon_social", None), ("Descripción", "descripcion", None),
            ("Concepto", "concepto", None), ("Moneda", "moneda", None), ("Importe", "importe", "importe"), ("Importe ME", "importe_me", "importe"),
            ("Cantidad", "cantidad", "cantidad"), ("CC", "centro_costo", None), ("Proyecto", "proyecto", None),
            ("Estado", "estado", None), ("Conciliado", "conciliado", "importe"), ("Pendiente", "pendiente", "importe"),
            ("Origen (tabla)", "origen_tabla", None), ("Origen (id)", "origen_id", None), ("Fila archivo", "fila_origen", None)]
COLS_DIF = [("Código", "codigo"), ("Tipo", "clasificacion"), ("Subtipo", "subtipo"), ("Prioridad", "prioridad"), ("Fuente", "fuente"), ("Cuenta", "cuenta"),
            ("Documento", "documento"), ("Tercero", "tercero"), ("Razón social", "razon_social"), ("Importe", "importe"), ("Moneda", "moneda"),
            ("Fecha", "fecha"), ("Dentro de tolerancia", "dentro_tolerancia"), ("Regla", "regla"), ("Explicación", "explicacion"),
            ("Recomendación", "recomendacion"), ("Responsable", "responsable"), ("Estado", "estado"), ("Detectada", "fecha_deteccion"),
            ("Periodo origen", "periodo_origen"), ("Importe original", "importe_original"), ("Importe pendiente", "importe_pendiente"),
            ("Recurrencias", "recurrencias"), ("Causa", "causa"), ("Acción correctiva", "accion_correctiva"), ("Registros", "registros")]
MONEDA = {"importe", "importe_me", "conciliado", "pendiente", "importe_original", "importe_pendiente"}


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(Decimal(str(v)))
    except Exception:
        return v


def preparar(db, c: Conciliacion, version_id=None, ve_personal=True) -> dict:
    v = db.get(VersionConciliacion, version_id or c.version_id)
    if not v or v.run_id != c.id:
        raise LookupError("La conciliación no tiene una versión generada.")
    fuentes = json.loads(v.fuentes or "{}")
    ids_fuente = [x["id"] for x in fuentes.values()]
    regs = []
    q = (select(RegistroFuente, AsignacionRegistro).outerjoin(AsignacionRegistro, (AsignacionRegistro.registro_id == RegistroFuente.id)
                                                              & (AsignacionRegistro.version_id == v.id))
         .where(RegistroFuente.fuente_id.in_(ids_fuente or [0])).order_by(RegistroFuente.lado, RegistroFuente.orden))
    vistos = {}
    for r, a in db.execute(q):
        x = vistos.get(r.id)
        if x is None:
            x = {c_.key: getattr(r, c_.key) for c_ in RegistroFuente.__table__.columns}
            x.update(estado=a.estado if a else "SIN_COMPARAR", conciliado=a.conciliado if a else Decimal(0),
                     pendiente=(a.total - a.conciliado) if a else abs(r.importe or 0))
            if r.personal and not ve_personal:
                x = consultas.mascara(x)
            vistos[r.id] = x
            regs.append(x)
        elif a and x["estado"] in GRAVEDAD and GRAVEDAD.index(a.estado) > GRAVEDAD.index(x["estado"]):
            x.update(estado=a.estado, conciliado=a.conciliado, pendiente=a.total - a.conciliado)  # estado menos favorable entre comparaciones
    difs = [consultas.diferencia_dict(d, ve_personal) for d in db.scalars(select(DiferenciaConciliacion)
                                                                           .where(DiferenciaConciliacion.version_id == v.id).order_by(DiferenciaConciliacion.id))]
    grupos = db.scalars(select(GrupoConciliacion).where(GrupoConciliacion.version_id == v.id).order_by(GrupoConciliacion.id)).all()
    por_grupo = {}
    if grupos:
        for m in db.scalars(select(MatchConciliacion).where(MatchConciliacion.grupo_id.in_([g.id for g in grupos]))):
            por_grupo.setdefault(m.grupo_id, []).append(m)
    reporte = json.loads(v.reporte or "{}")
    if c.tipo_codigo == "PLANILLAS" and not ve_personal:
        reporte = {"tipo": "PLANILLAS", "nota": "Detalle reservado al responsable de planillas."}
    return {"c": c, "v": v, "empresa": db.get(Empresa, c.empresa_id), "fuentes": fuentes, "registros": regs, "diferencias": difs, "grupos": grupos,
            "matches": por_grupo, "reporte": reporte, "resumen": json.loads(v.resumen or "{}"), "ambito": json.loads(c.ambito or "{}"),
            "aprobaciones": db.scalars(select(AprobacionConciliacion).where(AprobacionConciliacion.run_id == c.id).order_by(AprobacionConciliacion.id)).all(),
            "revisiones": db.scalars(select(RevisionConciliacion).where(RevisionConciliacion.run_id == c.id).order_by(RevisionConciliacion.id)).all(),
            "fuentes_db": {f.id: f for f in db.scalars(select(FuenteConciliacion).where(FuenteConciliacion.id.in_(ids_fuente or [0])))}}


def _ref(p) -> list[tuple[str, str]]:
    c, v, e = p["c"], p["v"], p["empresa"]
    amb = ", ".join(f"{k}: {x}" for k, x in p["ambito"].items()) or "Todos"
    return [("Razón social", e.razon_social), ("RUC", e.ruc), ("Conciliación", c.nombre), ("Tipo", c.tipo_codigo), ("Ámbito", amb),
            ("Ejercicio / periodo", f"{c.ejercicio} / {c.periodo:02d}"), ("Fecha de corte", c.fecha_corte.strftime("%d/%m/%Y")),
            ("Versión", f"{v.numero}" + (" (aprobada, inmutable)" if v.inmutable else "")),
            ("Generada", f"{v.generado_en:%d/%m/%Y %H:%M} por {v.generado_por}"), ("Estado", ESTADOS.get(c.estado, c.estado)),
            ("Tolerancia aplicada", json.dumps(p["resumen"].get("tolerancia") or {}, ensure_ascii=False)),
            ("Elaboró / revisó / aprobó", " / ".join(x or "—" for x in (c.ejecutado_por or c.creado_por, c.revisado_por, c.aprobado_por))),
            ("Fecha de exportación", datetime.now().strftime("%d/%m/%Y %H:%M"))]


def _encabezado(ws, p, est, titulo):
    ws.append([_celda(ws, titulo, fuente=est.titulo)])
    ws.append([_celda(ws, p["empresa"].razon_social, fuente=est.gris), f"RUC {p['empresa'].ruc}"])
    ws.append([])


def _tabla(ws, est, cab, filas, tipos):
    ws.append([_celda(ws, h, fuente=est.blanco, relleno=est.cab) for h in cab])
    inicio = 4 + 1
    n = 0
    for f in filas:
        ws.append([_celda(ws, _num(x), formato=FORMATO) if t == "importe" and x not in (None, "") else x for x, t in zip(f, tipos)])
        n += 1
    return inicio, n


def excel(p: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    wb = Workbook(write_only=True)
    est = _Estilos()
    c, res = p["c"], p["resumen"]
    # --- Resumen (con fórmulas verificables)
    ws = wb.create_sheet("Resumen")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width, ws.column_dimensions["C"].width = 38, 22, 22
    _encabezado(ws, p, est, f"Conciliación — {c.nombre}")
    for k, x in _ref(p):
        ws.append([_celda(ws, k, fuente=est.negrita), x])
    ws.append([])
    ws.append([_celda(ws, h, fuente=est.blanco, relleno=est.cab) for h in ("Fuente", "Registros", "Total", "Saldo informado")])
    for lado, f in sorted(p["fuentes"].items()):
        ws.append([f"{lado} · {f['nombre']} ({f.get('rol')})", f.get("registros"),
                   _celda(ws, _num(sum((r["importe"] or 0 for r in p["registros"] if r["lado"] == lado), Decimal(0))), formato=FORMATO),
                   _celda(ws, _num(f.get("saldo")), formato=FORMATO) if f.get("saldo") not in (None, "") else "—"])
    ws.append([])
    ws.append([_celda(ws, h, fuente=est.blanco, relleno=est.cab) for h in ("Estado de los registros", "Cantidad", "Importe", "% cantidad", "% importe")])
    estados = sorted(res.get("asignaciones", {}))
    n0 = len(_ref(p)) + len(p["fuentes"]) + 8  # fila de la primera línea de estados (encabezado 3 + ficha + 2 tablas)
    for i, k in enumerate(estados):
        r = n0 + i
        ws.append([k, res["asignaciones"][k], _celda(ws, _num(res.get("importes", {}).get(k)), formato=FORMATO),
                   _celda(ws, f"=IFERROR(B{r}/B{n0 + len(estados)},0)", formato="0.00%"),
                   _celda(ws, f"=IFERROR(C{r}/C{n0 + len(estados)},0)", formato="0.00%")])
    ws.append([_celda(ws, "Total", fuente=est.negrita, relleno=est.tot), _celda(ws, f"=SUM(B{n0}:B{n0 + len(estados) - 1})" if estados else 0, relleno=est.tot),
               _celda(ws, f"=SUM(C{n0}:C{n0 + len(estados) - 1})" if estados else 0, formato=FORMATO, relleno=est.tot)])
    ws.append([])
    ws.append([_celda(ws, "Diferencias por clasificación", fuente=est.blanco, relleno=est.cab), _celda(ws, "Cantidad", fuente=est.blanco, relleno=est.cab)])
    for k, n in sorted((res.get("por_clasificacion") or {}).items()):
        ws.append([k, n])
    ws.append(["Diferencias dentro de tolerancia (visibles y cuantificadas)", res.get("dentro_tolerancia", 0)])
    ws.append([])
    ws.append([_celda(ws, "Nota: conciliación analítica. No modifica asientos ni genera ajustes; toda diferencia se muestra aunque esté dentro de "
                          "la tolerancia, y no toda diferencia es un error contable.", alinear=est.wrap)])
    # --- Reporte especializado
    rep = p["reporte"]
    if rep.get("tipo") == "BANCARIA":
        _hoja_bancaria(wb, p, est)
    elif rep:
        ws = wb.create_sheet("Reporte")
        _encabezado(ws, p, est, f"Reporte {rep.get('tipo', '')}")
        _aplanar(ws, est, rep)
    # --- Fuentes, conciliados y no conciliados
    tipos = [t for _, _, t in COLS_REG]
    for titulo, filtro in (("Fuente contable", lambda r: p["fuentes"].get(r["lado"], {}).get("rol") == "CONTABLE"),
                           ("Fuente externa", lambda r: p["fuentes"].get(r["lado"], {}).get("rol") != "CONTABLE"),
                           ("Conciliados", lambda r: r["estado"] in ("CONCILIADO", "PROPUESTO")),
                           ("No conciliados", lambda r: r["estado"] not in ("CONCILIADO", "PROPUESTO", "EXCLUIDO"))):
        ws = wb.create_sheet(titulo)
        ws.freeze_panes = "A5"
        for i, (h, _, _) in enumerate(COLS_REG, 1):
            ws.column_dimensions[get_column_letter(i)].width = 14 if h not in ("Descripción", "Razón social") else 36
        _encabezado(ws, p, est, f"{titulo} — {c.nombre}")
        filas = [[r.get(k) if k not in ("fecha",) else (r[k].strftime("%d/%m/%Y") if r.get(k) else None) for _, k, _ in COLS_REG]
                 for r in p["registros"] if filtro(r)]
        ini, n = _tabla(ws, est, [h for h, _, _ in COLS_REG], filas, tipos)
        col = get_column_letter(COLS_REG.index(("Importe", "importe", "importe")) + 1)
        ws.append([_celda(ws, "Total", fuente=est.negrita, relleno=est.tot)] + [None] * (COLS_REG.index(("Importe", "importe", "importe")) - 1)
                  + [_celda(ws, f"=SUBTOTAL(9,{col}{ini}:{col}{ini + n - 1})" if n else 0, formato=FORMATO, relleno=est.tot)])
        ws.auto_filter.ref = f"A4:{get_column_letter(len(COLS_REG))}{max(ini + n - 1, 4)}"
    # --- Diferencias
    ws = wb.create_sheet("Diferencias")
    ws.freeze_panes = "A5"
    _encabezado(ws, p, est, f"Diferencias — {c.nombre}")
    filas = [[(", ".join(str(i) for i in d["evidencia"].get("registros", [])[:30]) if k == "registros" else
               ("Sí" if d[k] else "No") if k == "dentro_tolerancia" else d.get(k)) for _, k in COLS_DIF] for d in p["diferencias"]]
    ini, n = _tabla(ws, est, [h for h, _ in COLS_DIF], filas, ["importe" if k in MONEDA else None for _, k in COLS_DIF])
    ws.append([_celda(ws, "Total", fuente=est.negrita, relleno=est.tot)] + [None] * 8 +
              [_celda(ws, f"=SUBTOTAL(9,J{ini}:J{ini + n - 1})" if n else 0, formato=FORMATO, relleno=est.tot)])
    # --- Observaciones
    ws = wb.create_sheet("Observaciones")
    _encabezado(ws, p, est, "Observaciones")
    ws.append([_celda(ws, h, fuente=est.blanco, relleno=est.cab) for h in ("Fecha", "Entidad", "De", "A", "Usuario", "Rol", "Comentario")])
    for r in p["revisiones"]:
        if r.comentario:
            ws.append([r.creado_en.strftime("%d/%m/%Y %H:%M") if r.creado_en else None, f"{r.entidad} #{r.entidad_id}", r.de_estado, r.a_estado,
                       r.usuario, r.rol, r.comentario])
    for f in p["fuentes"].values():
        if f.get("observaciones"):
            ws.append([None, f"Fuente {f['nombre']}", None, None, None, None, f["observaciones"]])
    # --- Control de aprobación
    ws = wb.create_sheet("Control de aprobación")
    _encabezado(ws, p, est, "Control de elaboración, revisión y aprobación")
    ws.append([_celda(ws, h, fuente=est.blanco, relleno=est.cab) for h in ("Acción", "Usuario", "Rol", "Fecha", "Versión", "Comentario")])
    ws.append(["Elaboración / ejecución", c.ejecutado_por or c.creado_por, None, p["v"].generado_en.strftime("%d/%m/%Y %H:%M"), p["v"].numero, None])
    for a in p["aprobaciones"]:
        ws.append([a.accion, a.usuario, a.rol, a.creado_en.strftime("%d/%m/%Y %H:%M") if a.creado_en else None, a.version_id, a.comentario])
    ws.append([])
    for k in ("Elaborado por", "Revisado por", "Aprobado por"):
        ws.append([_celda(ws, k, fuente=est.negrita), "______________________", "Fecha: ____/____/______"])
    ws.append([NOTA_FIRMAS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _aplanar(ws, est, rep, nivel=0):
    for k, v in rep.items():
        if isinstance(v, dict):
            ws.append([_celda(ws, ("  " * nivel) + str(k), fuente=est.negrita)])
            _aplanar(ws, est, v, nivel + 1)
        elif isinstance(v, list):
            ws.append([_celda(ws, ("  " * nivel) + str(k), fuente=est.negrita)])
            for x in v[:5000]:
                if isinstance(x, dict):
                    ws.append([("  " * (nivel + 1))] + [(_celda(ws, _num(y), formato=FORMATO) if _es_importe(kk, y) else
                                                         (json.dumps(y, ensure_ascii=False) if isinstance(y, (dict, list)) else y))
                                                        for kk, y in x.items()])
                else:
                    ws.append([("  " * (nivel + 1)), x])
        else:
            ws.append([("  " * nivel) + str(k), _celda(ws, _num(v), formato=FORMATO) if _es_importe(k, v) else v])


def _es_importe(k, v):
    return isinstance(v, (str, int, float, Decimal)) and any(x in str(k) for x in ("importe", "saldo", "diferencia", "capital", "interes", "monto", "total",
                                                                                  "esperado", "depositado", "valor", "costo")) \
        and _num(v) is not None and not isinstance(_num(v), str)


def _hoja_bancaria(wb, p, est):
    rep = p["reporte"]
    ws = wb.create_sheet("Conciliación bancaria")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width, ws.column_dimensions["C"].width = 58, 20, 40
    _encabezado(ws, p, est, f"Conciliación bancaria al {p['c'].fecha_corte:%d/%m/%Y}")
    ws.append([rep.get("convencion")])
    fila = 5

    def linea(texto, valor, negrita=False, rel=None):
        nonlocal fila
        fila += 1
        ws.append([_celda(ws, texto, fuente=est.negrita if negrita else None, relleno=rel),
                   _celda(ws, valor if isinstance(valor, str) and valor.startswith("=") else _num(valor), formato=FORMATO,
                          fuente=est.negrita if negrita else None, relleno=rel)])
        return fila
    f_sb = linea("Saldo según estado bancario", rep.get("saldo_banco"), True)
    fb = [linea(x["concepto"], x["importe"]) for x in rep.get("partidas_banco", [])]
    f_ba = linea("Saldo bancario ajustado", f"=B{f_sb}" + "".join(f"+B{x}" for x in fb), True, est.sub)
    linea("", None)
    f_sl = linea("Saldo según libros", rep.get("saldo_libros"), True)
    fl = [linea(x["concepto"], x["importe"]) for x in rep.get("partidas_libros", [])]
    f_la = linea("Saldo en libros ajustado", f"=B{f_sl}" + "".join(f"+B{x}" for x in fl), True, est.sub)
    linea("", None)
    linea("Diferencia final (banco ajustado − libros ajustado)", f"=B{f_ba}-B{f_la}", True, est.tot)
    if rep.get("nota"):
        ws.append([_celda(ws, rep["nota"], fuente=est.alerta)])
    ws.append([])
    ws.append([_celda(ws, h, fuente=est.blanco, relleno=est.cab) for h in ("Partida", "Fecha", "Documento", "Descripción", "Importe", "Id registro")])
    for x in rep.get("partidas_banco", []) + rep.get("partidas_libros", []):
        for d in x.get("detalle", []):
            ws.append([x["concepto"], d.get("fecha"), d.get("documento"), d.get("descripcion"), _celda(ws, _num(d.get("importe")), formato=FORMATO),
                       d.get("registro_id")])


# ------------------------------------------------------------------ PDF
def pdf(p: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle
    st = _estilos_pdf()
    ancho = landscape(A4)[0] - 20 * mm
    c, res, rep = p["c"], p["resumen"], p["reporte"]
    h = []
    logo = ruta_logo(c.empresa_id)
    if logo:
        h.append(Image(str(logo), width=30 * mm, height=12 * mm, kind="proportional"))
    h.append(Paragraph(_fmt(f"Conciliación — {c.nombre}", None), st["titulo"]))
    estilo = TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0")),
                         ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2742")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                         ("VALIGN", (0, 0), (-1, -1), "TOP"), ("REPEATROWS", (0, 0), (-1, 0))])
    t = Table([[Paragraph(f"<b>{_fmt(k, None)}</b>", st["celda"]), Paragraph(_fmt(v, None), st["celda"])] for k, v in _ref(p)],
              colWidths=[50 * mm, ancho - 50 * mm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0"))]))
    h += [t, Spacer(1, 4 * mm), Paragraph("Resumen", st["h2"])]
    filas = [["Estado", "Cantidad", "Importe", "% cantidad", "% importe"]]
    for k, n in sorted((res.get("asignaciones") or {}).items()):
        filas.append([k, str(n), _fmt(res.get("importes", {}).get(k), "importe"), f"{res.get('porcentaje_cantidad', {}).get(k, 0):.2f} %",
                      f"{res.get('porcentaje_importe', {}).get(k, 0):.2f} %"])
    t = Table(filas, colWidths=[60 * mm, 25 * mm, 40 * mm, 30 * mm, 30 * mm], repeatRows=1)
    t.setStyle(estilo)
    h.append(t)
    if rep.get("tipo") == "BANCARIA":
        h += [Spacer(1, 4 * mm), Paragraph("Conciliación bancaria", st["h2"]), Paragraph(_fmt(rep.get("convencion"), None), st["nota"])]
        filas = [["Concepto", "Importe"], ["Saldo según estado bancario", _fmt(rep.get("saldo_banco"), "importe")]]
        filas += [[x["concepto"], _fmt(x["importe"], "importe")] for x in rep.get("partidas_banco", [])]
        filas += [["Saldo bancario ajustado", _fmt(rep.get("saldo_banco_ajustado"), "importe")], ["Saldo según libros", _fmt(rep.get("saldo_libros"), "importe")]]
        filas += [[x["concepto"], _fmt(x["importe"], "importe")] for x in rep.get("partidas_libros", [])]
        filas += [["Saldo en libros ajustado", _fmt(rep.get("saldo_libros_ajustado"), "importe")],
                  ["Diferencia final", _fmt(rep.get("diferencia_final"), "importe")]]
        t = Table([[Paragraph(str(a), st["celda"]), Paragraph(str(b), st["celda_d"])] for a, b in filas], colWidths=[120 * mm, 40 * mm], repeatRows=1)
        t.setStyle(estilo)
        h.append(t)
        if rep.get("nota"):
            h.append(Paragraph(_fmt(rep["nota"], None), st["nota"]))
    h += [Spacer(1, 4 * mm), Paragraph(f"Diferencias ({len(p['diferencias'])})", st["h2"])]
    cab = ["Código", "Clasificación", "Prioridad", "Documento", "Tercero", "Importe", "Estado", "Explicación"]
    filas = [cab] + [[Paragraph(_fmt(d.get(k), "importe" if k == "importe" else None), st["celda_d" if k == "importe" else "celda"])
                      for k in ("codigo", "clasificacion", "prioridad", "documento", "tercero", "importe", "estado", "explicacion")]
                     for d in p["diferencias"][:2000]]
    t = Table(filas, colWidths=[24 * mm, 38 * mm, 18 * mm, 26 * mm, 22 * mm, 22 * mm, 26 * mm, ancho - 176 * mm], repeatRows=1)
    t.setStyle(estilo)
    h.append(t)
    if len(p["diferencias"]) > 2000:
        h.append(Paragraph("Se muestran las primeras 2 000 diferencias; el detalle completo está en la exportación Excel.", st["nota"]))
    pend = [r for r in p["registros"] if r["estado"] not in ("CONCILIADO", "PROPUESTO", "EXCLUIDO")]
    h += [Spacer(1, 4 * mm), Paragraph(f"Partidas no conciliadas ({len(pend)})", st["h2"])]
    filas = [["Fuente", "Fecha", "Documento", "Descripción", "Tercero", "Importe", "Pendiente", "Estado"]]
    for r in pend[:2000]:
        filas.append([r["lado"], _fmt(r.get("fecha"), "fecha"), _fmt("-".join(x for x in (r.get("serie"), r.get("numero")) if x) or r.get("operacion"), None),
                      Paragraph(_fmt(r.get("descripcion"), None), st["celda"]), _fmt(r.get("tercero"), None), _fmt(r.get("importe"), "importe"),
                      _fmt(r.get("pendiente"), "importe"), r["estado"]])
    t = Table(filas, colWidths=[12 * mm, 20 * mm, 30 * mm, ancho - 164 * mm, 24 * mm, 26 * mm, 26 * mm, 26 * mm], repeatRows=1)
    t.setStyle(estilo)
    h.append(t)
    h += [Spacer(1, 6 * mm), Paragraph("Control de aprobación", st["h2"])]
    filas = [["Acción", "Usuario", "Fecha", "Comentario"], ["Elaboración", c.ejecutado_por or c.creado_por or "", f"{p['v'].generado_en:%d/%m/%Y %H:%M}", ""]]
    filas += [[a.accion, a.usuario, f"{a.creado_en:%d/%m/%Y %H:%M}" if a.creado_en else "", Paragraph(_fmt(a.comentario, None), st["celda"])]
              for a in p["aprobaciones"]]
    t = Table(filas, colWidths=[30 * mm, 40 * mm, 30 * mm, ancho - 100 * mm], repeatRows=1)
    t.setStyle(estilo)
    h += [t, Spacer(1, 8 * mm), Paragraph("Elaborado por: ____________________  Revisado por: ____________________  "
                                          "Aprobado por: ____________________", st["texto"]), Paragraph(NOTA_FIRMAS, st["nota"])]
    pie = f"{p['empresa'].razon_social} · {c.nombre} · versión {p['v'].numero} · generado {datetime.now():%d/%m/%Y %H:%M}"
    return _documento(h, c.nombre, pie, True)


# ------------------------------------------------------------------ reportes globales
REPORTES = {"RESUMEN": "Resumen de conciliaciones", "DIFERENCIAS": "Diferencias detectadas", "PENDIENTES": "Partidas pendientes (incidencias abiertas)",
            "OBSERVACIONES": "Observaciones de revisión", "HISTORIAL": "Historial de conciliaciones"}


def reporte_global(db, empresa: Empresa, tipo: str, f: dict, ve_personal: bool, formato="xlsx") -> bytes:
    if tipo not in REPORTES:
        raise LookupError("Reporte no disponible")
    q = select(Conciliacion).where(Conciliacion.empresa_id == empresa.id)
    for k in ("ejercicio", "periodo", "tipo_codigo"):
        if f.get(k):
            q = q.where(getattr(Conciliacion, k) == f[k])
    runs = db.scalars(q.order_by(Conciliacion.fecha_corte, Conciliacion.id)).all()
    if tipo == "RESUMEN":
        cab = ["Id", "Conciliación", "Tipo", "Corte", "Estado", "Versión", "Registros", "Conciliados", "Diferencias", "Importe diferencias", "Responsable",
               "Aprobado por"]
        filas = []
        for c in runs:
            r = json.loads(c.resumen) if c.resumen else {}
            filas.append([c.id, c.nombre, c.tipo_codigo, c.fecha_corte.strftime("%d/%m/%Y"), c.estado, c.version_actual,
                          sum((r.get("asignaciones") or {}).values()), (r.get("asignaciones") or {}).get("CONCILIADO", 0), r.get("diferencias", 0),
                          r.get("importe_diferencias"), c.responsable, c.aprobado_por])
        tipos = [None] * 9 + ["importe", None, None]
    elif tipo in ("DIFERENCIAS", "PENDIENTES"):
        vids = [c.version_id for c in runs if c.version_id]
        q = select(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id.in_(vids or [0]))
        if tipo == "PENDIENTES":
            q = q.where(DiferenciaConciliacion.estado.in_(consultas.ABIERTAS))
        q = consultas.filtro_diferencias(q, f)
        cab = [h for h, _ in COLS_DIF] + ["Antigüedad (días)"]
        filas = []
        for d in db.scalars(q.order_by(DiferenciaConciliacion.run_id, DiferenciaConciliacion.id)):
            x = consultas.diferencia_dict(d, ve_personal)
            filas.append([(", ".join(str(i) for i in x["evidencia"].get("registros", [])[:30]) if k == "registros" else
                           ("Sí" if x[k] else "No") if k == "dentro_tolerancia" else x.get(k)) for _, k in COLS_DIF] + [x["antiguedad_dias"]])
        tipos = ["importe" if k in MONEDA else None for _, k in COLS_DIF] + [None]
    elif tipo == "OBSERVACIONES":
        cab = ["Conciliación", "Fecha", "Entidad", "De", "A", "Usuario", "Rol", "Comentario"]
        nombres = {c.id: c.nombre for c in runs}
        filas = [[nombres.get(r.run_id), r.creado_en.strftime("%d/%m/%Y %H:%M") if r.creado_en else None, f"{r.entidad} #{r.entidad_id}", r.de_estado,
                  r.a_estado, r.usuario, r.rol, r.comentario]
                 for r in db.scalars(select(RevisionConciliacion).where(RevisionConciliacion.run_id.in_(list(nombres) or [0]),
                                                                        RevisionConciliacion.comentario.is_not(None)).order_by(RevisionConciliacion.id))]
        tipos = [None] * 8
    else:
        cab = ["Conciliación", "Versión", "Generada", "Por", "Inmutable", "Motivo", "Registros", "Diferencias", "Hash"]
        nombres = {c.id: c.nombre for c in runs}
        filas = []
        for v in db.scalars(select(VersionConciliacion).where(VersionConciliacion.run_id.in_(list(nombres) or [0])).order_by(VersionConciliacion.run_id,
                                                                                                                           VersionConciliacion.numero)):
            r = json.loads(v.resumen or "{}")
            filas.append([nombres[v.run_id], v.numero, v.generado_en.strftime("%d/%m/%Y %H:%M"), v.generado_por, "Sí" if v.inmutable else "No", v.motivo,
                          sum((r.get("registros") or {}).values()), r.get("diferencias", 0), v.hash_contenido[:16]])
        tipos = [None] * 9
    titulo = f"{REPORTES[tipo]} — {empresa.razon_social}"
    if formato == "pdf":
        return _pdf_tabla(empresa, titulo, cab, filas, tipos)
    from openpyxl import Workbook
    wb = Workbook(write_only=True)
    est = _Estilos()
    ws = wb.create_sheet(REPORTES[tipo][:31])
    ws.freeze_panes = "A5"
    ws.append([_celda(ws, titulo, fuente=est.titulo)])
    ws.append([f"RUC {empresa.ruc}", f"Generado {datetime.now():%d/%m/%Y %H:%M}", json.dumps({k: v for k, v in f.items() if v}, default=str)])
    ws.append([])
    _tabla(ws, est, cab, filas, tipos)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pdf_tabla(empresa, titulo, cab, filas, tipos) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle
    st = _estilos_pdf()
    ancho = landscape(A4)[0] - 20 * mm
    sel = list(range(min(len(cab), 12)))
    datos = [[Paragraph(f"<b>{_fmt(cab[i], None)}</b>", st["celda"]) for i in sel]]
    for f in filas[:5000]:
        datos.append([Paragraph(_fmt(f[i], tipos[i]), st["celda_d" if tipos[i] == "importe" else "celda"]) for i in sel])
    t = Table(datos, colWidths=[ancho / len(sel)] * len(sel), repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF5")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    h = [Paragraph(_fmt(titulo, None), st["titulo"]), t]
    if len(filas) > 5000:
        h.append(Paragraph("Se muestran las primeras 5 000 filas; use la exportación Excel para el detalle completo.", st["nota"]))
    return _documento(h, titulo, f"{empresa.razon_social} · {titulo} · {datetime.now():%d/%m/%Y %H:%M}", True)
