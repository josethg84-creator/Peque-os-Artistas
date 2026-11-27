"""Informes de auditoría (16 secciones, 6 versiones) y exportaciones profesionales a Excel y PDF.

Los informes son documentos de apoyo para la gestión: NO son dictámenes de auditoría independiente ni garantizan el
cumplimiento normativo. Cada versión guarda una instantánea inmutable con su hash. Las exportaciones conservan referencias
verificables (tabla e id del registro original) y enmascaran datos personales y evidencias confidenciales según el rol.
"""
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.anexos.exportar import FORMATO, _celda, _documento, _Estilos, _estilos_pdf, _fmt, ruta_logo
from app.auditoria import riesgo
from app.auditoria.motor import alcance_de
from app.auditoria.servicio import ErrorAuditoria, cargar_encargo, evento, exigir, puede
from app.models import (Empresa, EjecucionAuditoria, EvidenciaHallazgo, GrupoHallazgos, HallazgoAuditoria, InformeAuditoria, Materialidad, PapelAuditoria,
                        PlanAccion, ResultadoRegla, RevisionAuditoria, VersionInforme)

AVISO = ("Documento de apoyo elaborado con información importada y reglas automatizadas. No constituye un dictamen de auditoría "
         "independiente ni garantiza el cumplimiento normativo; los hallazgos potenciales requieren evaluación profesional.")
TIPOS = {"GERENCIA": "Informe para gerencia", "CONTADOR": "Informe para el contador", "AUDITORIA_INTERNA": "Informe para auditoría interna",
         "TRIBUTARIO": "Informe tributario preventivo", "PARAMETRIZACION": "Informe de parametrización", "DETALLE_CUENTA": "Informe detallado por cuenta"}
ORDEN_R = {k: i for i, k in enumerate(("CRITICO", "ALTO", "MEDIO", "BAJO", "INFORMATIVO"))}


def _mask(h: dict, ve: bool) -> dict:
    if h.get("personal") and not ve:
        t = h.get("tercero") or ""
        h["tercero"] = ("•" * max(len(t) - 2, 0) + t[-2:]) if t else None
        h["razon_social"] = "Trabajador (reservado)"
    return h


def _h(h: HallazgoAuditoria) -> dict:
    return {"id": h.id, "codigo": h.codigo, "titulo": h.titulo, "modulo": h.modulo, "regla": h.regla_codigo, "cuenta": h.cuenta, "tercero": h.tercero,
            "razon_social": h.razon_social, "documento": h.documento, "asiento": h.asiento, "linea_id": h.linea_id, "importe": str(h.importe),
            "importe_confirmado": str(h.importe_confirmado) if h.importe_confirmado is not None else None, "riesgo": h.riesgo, "impacto": h.impacto,
            "probabilidad": h.probabilidad, "puntuacion": h.puntuacion, "tipo": h.tipo, "estado": h.estado, "condicion": h.condicion, "criterio": h.criterio,
            "causa": h.causa, "efecto": h.efecto, "impacto_potencial": h.impacto_potencial, "recomendacion": h.recomendacion, "responsable": h.responsable,
            "fecha_deteccion": h.fecha_deteccion.isoformat(), "fecha_limite": h.fecha_limite.isoformat() if h.fecha_limite else None,
            "regularizacion": h.regularizacion, "tratamiento_tributario": h.tratamiento_tributario, "reincidencias": h.reincidencias,
            "grupo_id": h.grupo_id, "personal": h.personal, "vigente": h.vigente, "calidad_evidencia": h.calidad_evidencia}


def contenido_informe(db, e, tipo, cuenta, ve_personal) -> dict:
    q = select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == e.id, HallazgoAuditoria.vigente.is_(True),
                                        HallazgoAuditoria.tipo != "FALSO_POSITIVO")
    hs = db.scalars(q).all()
    if tipo == "TRIBUTARIO":
        hs = [h for h in hs if h.modulo == "TRIBUTARIA" or h.tratamiento_tributario]
    elif tipo == "PARAMETRIZACION":
        hs = [h for h in hs if h.modulo in ("PARAMETRIZACION", "ORIGEN_DESTINO")]
    elif tipo == "DETALLE_CUENTA":
        if not cuenta:
            raise ErrorAuditoria("Indique la cuenta del informe detallado.")
        hs = [h for h in hs if (h.cuenta or "").startswith(cuenta)]
    elif tipo == "GERENCIA":
        hs = [h for h in hs if h.riesgo in ("CRITICO", "ALTO", "MEDIO")]
    hs.sort(key=lambda h: (ORDEN_R[h.riesgo], -h.puntuacion, -abs(h.importe)))
    ids = [h.id for h in hs]
    grupos = {g.id: g for g in db.scalars(select(GrupoHallazgos).where(GrupoHallazgos.engagement_id == e.id))}
    usados = {h.grupo_id for h in hs}
    expo = sum((grupos[g].exposicion for g in usados if g in grupos), Decimal(0))
    expo_c = sum((grupos[g].exposicion_confirmada for g in usados if g in grupos), Decimal(0))
    run = db.scalar(select(EjecucionAuditoria).where(EjecucionAuditoria.engagement_id == e.id, EjecucionAuditoria.estado_proceso == "COMPLETADO")
                    .order_by(EjecucionAuditoria.id.desc()))
    rr = db.scalars(select(ResultadoRegla).where(ResultadoRegla.run_id == run.id)).all() if run else []
    planes = db.scalars(select(PlanAccion).where(PlanAccion.finding_id.in_(ids or [0]))).all()
    mat = db.get(Materialidad, json.loads(run.materialidad_snapshot)["id"]) if run and run.materialidad_snapshot else None
    matriz = defaultdict(int)
    for h in hs:
        matriz[f"{h.impacto}x{h.probabilidad}"] += 1
    emp = db.get(Empresa, e.empresa_id)
    principales = [_mask(_h(h), ve_personal) for h in hs[:60 if tipo != "GERENCIA" else 20]]
    nev = db.scalar(select(func.count()).select_from(EvidenciaHallazgo).where(EvidenciaHallazgo.finding_id.in_(ids or [0]))) or 0
    lim = [f"Regla {r.codigo}: {r.mensaje}" for r in rr if r.estado in ("SIN_DATOS", "NO_VALIDADA", "FUERA_DE_VIGENCIA", "PENDIENTE_EVALUACION", "ERROR")]
    return {
        "portada": {"titulo": TIPOS[tipo], "empresa": emp.razon_social, "ruc": emp.ruc, "encargo": e.nombre, "codigo": e.codigo,
                    "fecha_corte": e.fecha_corte.isoformat(), "fecha_emision": datetime.now().isoformat(timespec="minutes"), "aviso": AVISO},
        "resumen_ejecutivo": {"hallazgos": len(hs), "por_riesgo": dict(Counter(h.riesgo for h in hs)), "confirmados": sum(1 for h in hs if h.tipo == "CONFIRMADO"),
                              "exposicion_potencial": str(expo), "exposicion_confirmada": str(expo_c),
                              "nota": "Las exposiciones superpuestas se cuentan una sola vez (grupos de exposición)."},
        "objetivo": e.objetivo or "Evaluar la integridad, consistencia, razonabilidad y trazabilidad de la información contable.",
        "alcance": {"tipo": e.tipo, "ejercicio": e.ejercicio, "periodo": e.periodo, "corte": e.fecha_corte.isoformat(), "alcance": alcance_de(db, e),
                    "cuenta": cuenta},
        "metodologia": {"reglas_ejecutadas": len(rr), "estados": dict(Counter(r.estado for r in rr)), "matriz": "Impacto (materialidad) × probabilidad, "
                        "5 niveles; la puntuación es una priorización interna, no una probabilidad estadística validada.",
                        "estadistica": "Las herramientas estadísticas son exploratorias y no prueban errores ni fraude."},
        "fuentes": ["Libro diario y saldos importados (fase 2)", "Análisis de cuentas (fase 3)", "Compensación de partidas (fase 4)",
                    "Anexos y registros auxiliares (fase 5)", "Conciliaciones (fase 6)"],
        "limitaciones": lim + [AVISO],
        "matriz_riesgos": {"celdas": dict(matriz), "por_riesgo": dict(Counter(h.riesgo for h in hs))},
        "principales_hallazgos": principales,
        "impacto_economico": {"potencial": str(expo), "confirmado": str(expo_c), "grupos": len(usados),
                              "materialidad": riesgo.materialidad_dict(mat)},
        "evidencias": {"registros_de_evidencia": nev, "nota": "Cada hallazgo referencia el registro original (tabla e id) y su asiento."},
        "recomendaciones": [{"codigo": h["codigo"], "recomendacion": h["recomendacion"]} for h in principales if h["recomendacion"]],
        "plan_accion": [{"hallazgo": p.finding_id, "descripcion": p.descripcion, "responsable": p.responsable, "fecha": p.fecha_compromiso.isoformat(),
                         "estado": p.estado} for p in planes],
        "responsables": sorted({h.responsable for h in hs if h.responsable} | {p.responsable for p in planes}),
        "conclusiones_preliminares": e.conclusion or "Pendiente de la revisión y aprobación de conclusiones por la supervisión.",
        "anexos": [{"regla": r.codigo, "modulo": r.modulo, "estado": r.estado, "poblacion": r.poblacion, "excepciones": r.excepciones} for r in rr],
    }


def generar_informe(db, empresa_id, eid, usuario, tipo, cuenta=None) -> InformeAuditoria:
    r = exigir(db, empresa_id, usuario, "exportar")
    if tipo not in TIPOS:
        raise ErrorAuditoria("Tipo de informe no válido.")
    e = cargar_encargo(db, empresa_id, eid, usuario)
    inf = db.scalar(select(InformeAuditoria).where(InformeAuditoria.engagement_id == e.id, InformeAuditoria.tipo == tipo,
                                                   InformeAuditoria.cuenta.is_(cuenta) if cuenta is None else InformeAuditoria.cuenta == cuenta))
    if not inf:
        inf = InformeAuditoria(engagement_id=e.id, tipo=tipo, titulo=f"{TIPOS[tipo]} — {e.nombre}"[:255], cuenta=cuenta, creado_por=usuario)
        db.add(inf)
        db.flush()
    c = contenido_informe(db, e, tipo, cuenta, puede(db, empresa_id, usuario, "datos_personales"))
    txt = json.dumps(c, ensure_ascii=False, sort_keys=True, default=str)
    inf.version_actual += 1
    run = db.scalar(select(func.max(EjecucionAuditoria.id)).where(EjecucionAuditoria.engagement_id == e.id))
    db.add(VersionInforme(report_id=inf.id, numero=inf.version_actual, run_id=run, contenido=txt, hash=hashlib.sha256(txt.encode()).hexdigest(),
                          generado_por=usuario))
    evento(db, empresa_id, usuario, "GENERAR_INFORME", "informe", inf.id, {"tipo": tipo, "version": inf.version_actual}, r, e.id)
    db.commit()
    return inf


# ------------------------------------------------------------------ Excel / PDF
def _tabla_excel(wb, nombre, titulo, emp, cab, filas, importes=()):
    est = _Estilos()
    ws = wb.create_sheet(nombre[:31])
    ws.freeze_panes = "A5"
    ws.append([_celda(ws, titulo, fuente=est.titulo)])
    ws.append([f"{emp.razon_social} · RUC {emp.ruc}", f"Generado {datetime.now():%d/%m/%Y %H:%M}", AVISO])
    ws.append([])
    ws.append([_celda(ws, h, fuente=est.blanco, relleno=est.cab) for h in cab])
    for f in filas:
        ws.append([_celda(ws, float(Decimal(str(v))), formato=FORMATO) if i in importes and v not in (None, "") else v for i, v in enumerate(f)])
    return ws


def informe_excel(db, inf: InformeAuditoria, version=None) -> bytes:
    from openpyxl import Workbook
    v = db.scalar(select(VersionInforme).where(VersionInforme.report_id == inf.id, VersionInforme.numero == (version or inf.version_actual)))
    c = json.loads(v.contenido)
    emp_nombre = c["portada"]["empresa"]
    wb = Workbook(write_only=True)
    est = _Estilos()
    ws = wb.create_sheet("Informe")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 34, 110
    ws.append([_celda(ws, c["portada"]["titulo"], fuente=est.titulo)])
    for k, x in [("Empresa", emp_nombre), ("RUC", c["portada"]["ruc"]), ("Encargo", f"{c['portada']['codigo']} · {c['portada']['encargo']}"),
                 ("Fecha de corte", c["portada"]["fecha_corte"]), ("Versión", f"{v.numero} · hash {v.hash[:16]}"), ("Aviso", AVISO)]:
        ws.append([_celda(ws, k, fuente=est.negrita), _celda(ws, x, alinear=est.wrap)])
    secciones = [("1. Portada", c["portada"]), ("2. Resumen ejecutivo", c["resumen_ejecutivo"]), ("3. Objetivo", c["objetivo"]), ("4. Alcance", c["alcance"]),
                 ("5. Metodología", c["metodologia"]), ("6. Fuentes de información", c["fuentes"]), ("7. Limitaciones", c["limitaciones"]),
                 ("8. Matriz de riesgos", c["matriz_riesgos"]), ("10. Impacto económico potencial", c["impacto_economico"]), ("11. Evidencias", c["evidencias"]),
                 ("14. Responsables", c["responsables"]), ("15. Conclusiones preliminares", c["conclusiones_preliminares"])]
    for titulo, val in secciones:
        ws.append([])
        ws.append([_celda(ws, titulo, fuente=est.negrita, relleno=est.sub)])
        if isinstance(val, dict):
            for k, x in val.items():
                ws.append([k, _celda(ws, json.dumps(x, ensure_ascii=False, default=str) if isinstance(x, (dict, list)) else x, alinear=est.wrap)])
        elif isinstance(val, list):
            for x in val:
                ws.append(["", _celda(ws, x, alinear=est.wrap)])
        else:
            ws.append(["", _celda(ws, val, alinear=est.wrap)])
    cab = ["Código", "Título", "Módulo", "Regla", "Cuenta", "Tercero", "Documento", "Asiento", "Línea (id)", "Importe", "Riesgo", "Tipo", "Estado",
           "Condición", "Criterio", "Causa", "Efecto", "Recomendación", "Responsable", "Fecha límite"]
    filas = [[h["codigo"], h["titulo"], h["modulo"], h["regla"], h["cuenta"], h["tercero"], h["documento"], h["asiento"], h["linea_id"], h["importe"],
              h["riesgo"], h["tipo"], h["estado"], h["condicion"], h["criterio"], h["causa"], h["efecto"], h["recomendacion"], h["responsable"],
              h["fecha_limite"]] for h in c["principales_hallazgos"]]
    emp = type("E", (), {"razon_social": emp_nombre, "ruc": c["portada"]["ruc"]})
    _tabla_excel(wb, "9. Principales hallazgos", "Principales hallazgos", emp, cab, filas, importes={9})
    _tabla_excel(wb, "12. Recomendaciones", "Recomendaciones", emp, ["Hallazgo", "Recomendación"], [[x["codigo"], x["recomendacion"]] for x in c["recomendaciones"]])
    _tabla_excel(wb, "13. Plan de acción", "Plan de acción", emp, ["Hallazgo (id)", "Acción", "Responsable", "Fecha", "Estado"],
                 [[p["hallazgo"], p["descripcion"], p["responsable"], p["fecha"], p["estado"]] for p in c["plan_accion"]])
    _tabla_excel(wb, "16. Anexos", "Reglas ejecutadas", emp, ["Regla", "Módulo", "Estado", "Población", "Excepciones"],
                 [[a["regla"], a["modulo"], a["estado"], a["poblacion"], a["excepciones"]] for a in c["anexos"]])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def informe_pdf(db, inf: InformeAuditoria, empresa_id, version=None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, PageBreak, Paragraph, Spacer, Table, TableStyle
    v = db.scalar(select(VersionInforme).where(VersionInforme.report_id == inf.id, VersionInforme.numero == (version or inf.version_actual)))
    c = json.loads(v.contenido)
    st = _estilos_pdf()
    ancho = landscape(A4)[0] - 20 * mm
    estilo = TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0")),
                         ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2742")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP")])
    P = lambda t, s="texto": Paragraph(_fmt(t, None), st[s])  # noqa: E731
    h = []
    logo = ruta_logo(empresa_id)
    if logo:
        h.append(Image(str(logo), width=30 * mm, height=12 * mm, kind="proportional"))
    p = c["portada"]
    h += [Spacer(1, 30 * mm), Paragraph(_fmt(p["titulo"], None), st["titulo"]), P(f"{p['empresa']} · RUC {p['ruc']}"), P(f"{p['codigo']} · {p['encargo']}"),
          P(f"Fecha de corte: {p['fecha_corte']} · versión {v.numero} · emitido {p['fecha_emision']}"), Spacer(1, 10 * mm), P(AVISO, "nota"), PageBreak()]

    def seccion(t, val):
        h.append(Paragraph(_fmt(t, None), st["h2"]))
        if isinstance(val, dict):
            for k, x in val.items():
                h.append(P(f"{k}: {json.dumps(x, ensure_ascii=False, default=str) if isinstance(x, (dict, list)) else x}"))
        elif isinstance(val, list):
            for x in val:
                h.append(P(f"• {x}"))
        else:
            h.append(P(val))
    seccion("2. Resumen ejecutivo", c["resumen_ejecutivo"])
    seccion("3. Objetivo", c["objetivo"])
    seccion("4. Alcance", c["alcance"])
    seccion("5. Metodología", c["metodologia"])
    seccion("6. Fuentes de información", c["fuentes"])
    seccion("7. Limitaciones", c["limitaciones"])
    h.append(Paragraph("8. Matriz de riesgos (impacto × probabilidad)", st["h2"]))
    celdas = c["matriz_riesgos"]["celdas"]
    filas = [["Impacto \\ Probabilidad"] + [str(x) for x in range(1, 6)]] + [[str(i)] + [str(celdas.get(f"{i}x{pp}", "")) for pp in range(1, 6)] for i in range(5, 0, -1)]
    t = Table(filas, colWidths=[40 * mm] + [20 * mm] * 5)
    t.setStyle(estilo)
    h.append(t)
    h.append(Paragraph("9. Principales hallazgos", st["h2"]))
    filas = [["Código", "Riesgo", "Título", "Cuenta", "Documento", "Importe", "Estado"]] + [
        [P(x["codigo"], "celda"), x["riesgo"], P(x["titulo"], "celda"), x["cuenta"] or "", P(x["documento"] or "", "celda"), _fmt(x["importe"], "importe"), x["estado"]]
        for x in c["principales_hallazgos"]]
    t = Table(filas, colWidths=[30 * mm, 20 * mm, ancho - 160 * mm, 20 * mm, 35 * mm, 25 * mm, 30 * mm], repeatRows=1)
    t.setStyle(estilo)
    h.append(t)
    seccion("10. Impacto económico potencial", c["impacto_economico"])
    seccion("11. Evidencias", c["evidencias"])
    seccion("12. Recomendaciones", [f"{x['codigo']}: {x['recomendacion']}" for x in c["recomendaciones"]])
    seccion("13. Plan de acción", [f"{x['descripcion']} — {x['responsable']} ({x['fecha']}, {x['estado']})" for x in c["plan_accion"]] or ["Sin planes registrados."])
    seccion("14. Responsables", c["responsables"] or ["—"])
    seccion("15. Conclusiones preliminares", c["conclusiones_preliminares"])
    seccion("16. Anexos — reglas ejecutadas", [f"{a['regla']} ({a['modulo']}): {a['estado']} · población {a['poblacion']} · excepciones {a['excepciones']}"
                                                for a in c["anexos"]])
    return _documento(h, p["titulo"], f"{p['empresa']} · {p['titulo']} · v{v.numero} · {AVISO[:70]}…", True)


# ------------------------------------------------------------------ exportaciones
EXPORTS = {"INFORME_DETALLADO": "Informe detallado de hallazgos", "MATRIZ_RIESGOS": "Matriz de riesgos", "POR_CUENTA": "Hallazgos por cuenta",
           "POR_TERCERO": "Hallazgos por tercero", "TRIBUTARIOS": "Hallazgos tributarios", "PARAMETRIZACION": "Hallazgos de parametrización",
           "DUPLICIDADES": "Reporte de duplicidades", "PAPELES": "Papeles de trabajo", "PLANES": "Planes de acción",
           "SEGUIMIENTO": "Seguimiento de observaciones", "RECURRENTES": "Hallazgos recurrentes", "ORIGEN_DESTINO": "Reporte de origen y destino"}


def datos_export(db, empresa_id, e, tipo, usuario) -> tuple[str, list, list, set]:
    ve = puede(db, empresa_id, usuario, "datos_personales")
    hs = db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == e.id).order_by(HallazgoAuditoria.id)).all()
    cab = ["Código", "Título", "Módulo", "Regla", "Cuenta", "Tercero", "Razón social", "Documento", "Asiento", "Línea original (lineas_diario.id)",
           "Importe", "Importe confirmado", "Riesgo", "Impacto", "Probabilidad", "Tipo", "Estado", "Grupo de exposición", "Condición", "Criterio", "Causa",
           "Efecto", "Recomendación", "Responsable", "Fecha límite", "Regularización", "Tratamiento tributario", "Reincidencias", "Vigente"]

    def fila(h):
        x = _mask(_h(h), ve)
        return [x["codigo"], x["titulo"], x["modulo"], x["regla"], x["cuenta"], x["tercero"], x["razon_social"], x["documento"], x["asiento"], x["linea_id"],
                x["importe"], x["importe_confirmado"], x["riesgo"], x["impacto"], x["probabilidad"], x["tipo"], x["estado"], x["grupo_id"], x["condicion"],
                x["criterio"], x["causa"], x["efecto"], x["recomendacion"], x["responsable"], x["fecha_limite"], x["regularizacion"],
                x["tratamiento_tributario"], x["reincidencias"], "Sí" if x["vigente"] else "No"]
    imp = {10, 11}
    if tipo == "INFORME_DETALLADO":
        return EXPORTS[tipo], cab, [fila(h) for h in hs], imp
    if tipo == "TRIBUTARIOS":
        return EXPORTS[tipo], cab, [fila(h) for h in hs if h.modulo == "TRIBUTARIA" or h.tratamiento_tributario], imp
    if tipo == "PARAMETRIZACION":
        return EXPORTS[tipo], cab, [fila(h) for h in hs if h.modulo in ("PARAMETRIZACION", "ORIGEN_DESTINO")], imp
    if tipo == "DUPLICIDADES":
        return EXPORTS[tipo], cab, [fila(h) for h in hs if h.modulo == "DUPLICIDADES" or "duplic" in h.titulo.lower()], imp
    if tipo == "RECURRENTES":
        return EXPORTS[tipo], cab, [fila(h) for h in hs if h.reincidencias > 0], imp
    if tipo in ("POR_CUENTA", "POR_TERCERO"):
        k = "cuenta" if tipo == "POR_CUENTA" else "tercero"
        por = defaultdict(list)
        for h in hs:
            if h.tipo != "FALSO_POSITIVO" and h.vigente:
                por[getattr(h, k) or "(sin dato)"].append(h)
        filas = []
        for v, xs in sorted(por.items()):
            grupos = {}
            for h in xs:
                grupos[h.grupo_id] = max(grupos.get(h.grupo_id, Decimal(0)), abs(h.importe))
            m = _mask({"tercero": v, "personal": any(h.personal for h in xs)}, ve)["tercero"] if k == "tercero" else v
            filas.append([m, len(xs), str(sum(grupos.values(), Decimal(0))), str(sum((abs(h.importe) for h in xs), Decimal(0))),
                          dict(Counter(h.riesgo for h in xs)).__repr__(), ", ".join(h.codigo for h in xs[:30])])
        return EXPORTS[tipo], [k.capitalize(), "Hallazgos", "Exposición (sin superposición)", "Suma bruta", "Por riesgo", "Códigos"], filas, {2, 3}
    if tipo == "MATRIZ_RIESGOS":
        cel = defaultdict(lambda: [0, Decimal(0)])
        for h in hs:
            if h.vigente and h.tipo != "FALSO_POSITIVO":
                cel[(h.impacto, h.probabilidad, h.riesgo)][0] += 1
                cel[(h.impacto, h.probabilidad, h.riesgo)][1] += abs(h.importe)
        return EXPORTS[tipo], ["Impacto", "Probabilidad", "Puntuación", "Nivel", "Hallazgos", "Importe bruto"], \
            [[i, p, i * p, nv, n, str(v)] for (i, p, nv), (n, v) in sorted(cel.items(), key=lambda x: -x[0][0] * x[0][1])], {5}
    if tipo == "PLANES":
        ps = db.scalars(select(PlanAccion).where(PlanAccion.finding_id.in_([h.id for h in hs] or [0]))).all()
        cod = {h.id: h.codigo for h in hs}
        hoy = date.today()
        return EXPORTS[tipo], ["Hallazgo", "Acción", "Responsable", "Fecha compromiso", "Estado", "Avance %", "Vencido", "Comentario de cierre"], \
            [[cod[p.finding_id], p.descripcion, p.responsable, p.fecha_compromiso.isoformat(), p.estado, p.avance,
              "Sí" if p.fecha_compromiso < hoy and p.estado not in ("COMPLETADO", "CANCELADO") else "No", p.comentario_cierre] for p in ps], set()
    if tipo == "SEGUIMIENTO":
        cod = {h.id: h.codigo for h in hs}
        revs = db.scalars(select(RevisionAuditoria).where(RevisionAuditoria.entidad == "HALLAZGO", RevisionAuditoria.entidad_id.in_(list(cod) or [0]))
                          .order_by(RevisionAuditoria.id)).all()
        return EXPORTS[tipo], ["Hallazgo", "Fecha", "Usuario", "Rol", "De", "A", "Comentario", "Cambios"], \
            [[cod[r.entidad_id], r.creado_en.strftime("%d/%m/%Y %H:%M") if r.creado_en else None, r.usuario, r.rol, r.de_estado, r.a_estado, r.comentario,
              r.cambios] for r in revs], set()
    if tipo == "PAPELES":
        ps = db.scalars(select(PapelAuditoria).where(PapelAuditoria.engagement_id == e.id).order_by(PapelAuditoria.id)).all()
        filas = []
        for p in ps:
            c = json.loads(p.contenido)
            filas.append([p.referencia, p.titulo, c["objetivo"], json.dumps(c["alcance"], ensure_ascii=False), c["poblacion"]["registros"], c["poblacion"]["importe"],
                          c["fuente"], c["fecha_corte"], f"{c['regla']['codigo']} v{c['regla']['version']}", c["procedimiento"], c["resultados"]["excepciones"],
                          c["resultados"]["importe_excepciones"], p.conclusion, p.elaborado_por, p.revisado_por, p.revisado_en.isoformat() if p.revisado_en else None,
                          p.estado])
        return EXPORTS[tipo], ["Referencia", "Título", "Objetivo", "Alcance", "Población", "Importe población", "Fuente", "Corte", "Regla", "Procedimiento",
                               "Excepciones", "Importe excepciones", "Conclusión preliminar", "Elaboró", "Revisó", "Fecha revisión", "Estado"], filas, {5, 11}
    if tipo == "ORIGEN_DESTINO":
        from app.auditoria.base import Contexto
        from app.auditoria.r_especiales import reporte_destino
        ax = Contexto(db, e, alcance_de(db, e), None)
        filas = []
        for f in reporte_destino(ax):
            esp = ", ".join(f"{c} {v}" for c, v in f["destino_esperado"].items()) or ("sin regla" if f["sin_regla"] else "")
            reg = ", ".join(f"{c} {v}" for c, v in f["destino_registrado"].items())
            estado = ("CONFORME" if abs(f["diferencia"]) < Decimal("0.01") and abs(f["diferencia_79"]) < Decimal("0.01") else "DIFERENCIA")
            filas.append([", ".join(f["cuentas_origen"]), str(f["importe_original"]), str(f["sujeto"]), esp, reg, f"{f['cuenta_transferencia']} {f['transferencia']}",
                          str(f["diferencia"]), f["asiento"], ("Gastos por función " + ("sobreestimados" if f["diferencia"] < 0 else "subestimados") if estado != "CONFORME"
                                                               else "Sin impacto"), estado,
                          "Revise el asiento de destino" if estado != "CONFORME" else "", ", ".join(str(x.id) for x in f["lineas"][:10])])
        return EXPORTS[tipo], ["Cuenta de origen", "Importe original", "Importe sujeto a distribución", "Destino esperado", "Destino registrado",
                               "Cuenta de transferencia", "Diferencia", "Asiento", "Impacto potencial en resultados", "Estado", "Recomendación",
                               "Líneas originales (id)"], filas, {1, 2, 6}
    raise ErrorAuditoria("Exportación no disponible.")


def exportar(db, empresa_id, eid, usuario, tipo, formato="xlsx") -> bytes:
    r = exigir(db, empresa_id, usuario, "exportar")
    if tipo not in EXPORTS:
        raise ErrorAuditoria("Exportación no disponible.")
    e = cargar_encargo(db, empresa_id, eid, usuario)
    emp = db.get(Empresa, empresa_id)
    titulo, cab, filas, imp = datos_export(db, empresa_id, e, tipo, usuario)
    titulo = f"{titulo} — {e.codigo} {e.nombre}"
    evento(db, empresa_id, usuario, "EXPORTAR", "encargo", e.id, {"tipo": tipo, "formato": formato, "filas": len(filas)}, r, e.id)
    db.commit()
    if formato == "pdf":
        return _pdf_tabla(emp, titulo, cab, filas, imp)
    from openpyxl import Workbook
    wb = Workbook(write_only=True)
    _tabla_excel(wb, EXPORTS[tipo], titulo, emp, cab, filas, imp)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pdf_tabla(emp, titulo, cab, filas, imp) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle
    st = _estilos_pdf()
    sel = list(range(min(len(cab), 11)))
    ancho = landscape(A4)[0] - 20 * mm
    datos = [[Paragraph(f"<b>{_fmt(cab[i], None)}</b>", st["celda"]) for i in sel]]
    for f in filas[:4000]:
        datos.append([Paragraph(_fmt(f[i], "importe" if i in imp and f[i] not in (None, "") else None), st["celda_d" if i in imp else "celda"]) for i in sel])
    t = Table(datos, colWidths=[ancho / len(sel)] * len(sel), repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2E0")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF5")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    h = [Paragraph(_fmt(titulo, None), st["titulo"]), Paragraph(_fmt(AVISO, None), st["nota"]), t]
    if len(filas) > 4000:
        h.append(Paragraph("Se muestran las primeras 4 000 filas; use Excel para el detalle completo.", st["nota"]))
    return _documento(h, titulo, f"{emp.razon_social} · {titulo[:80]} · {datetime.now():%d/%m/%Y %H:%M}", True)

