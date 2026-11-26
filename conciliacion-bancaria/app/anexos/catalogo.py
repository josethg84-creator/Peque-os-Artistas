"""Catálogo de plantillas de anexos (PCGE) y campos disponibles por especialidad.

Cada plantilla del catálogo (empresa_id NULL) indica la ESPECIALIDAD que construye los datos y los
prefijos de cuenta a los que aplica. Para una cuenta se usa la plantilla con el prefijo más largo; la
empresa puede crear sus propias plantillas (personalizadas o duplicadas) que tienen prioridad.
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ColumnaPlantilla, PlantillaAnexo

# campos comunes de una fila de anexo: (campo, título, tipo)
COMUNES = [
    ("cuenta", "Cuenta", "texto"), ("categoria", "Categoría", "texto"), ("fecha", "Fecha", "fecha"),
    ("fecha_vencimiento", "Vencimiento", "fecha"), ("tipo_documento", "T.D.", "texto"), ("serie", "Serie", "texto"),
    ("numero", "Número", "texto"), ("documento", "Documento", "texto"), ("tercero", "RUC / Doc.", "texto"),
    ("razon_social", "Razón social", "texto"), ("glosa", "Glosa", "texto"), ("moneda", "Mon.", "texto"),
    ("tipo_cambio", "T.C.", "tasa"), ("importe_original", "Importe original", "importe"),
    ("importe_aplicado", "Importe aplicado", "importe"), ("saldo_me", "Saldo ME", "importe"),
    ("saldo", "Saldo MN", "importe"), ("dias", "Días", "entero"), ("tramo", "Antigüedad", "texto"),
    ("centro_costo", "C. costo", "texto"), ("proyecto", "Proyecto", "texto"), ("referencia", "Ref. contable", "texto"),
    ("estado_sustento", "Sustento", "texto"), ("observacion", "Observaciones", "texto"),
]
_T = {c: (t, tp) for c, t, tp in COMUNES}

# campos propios de cada especialidad (se guardan en `datos`)
PROPIOS = {
    "EFECTIVO": [("entidad", "Entidad financiera", "texto"), ("numero_cuenta", "N.º de cuenta", "texto"),
                 ("saldo_banco", "Saldo según banco", "importe"), ("fecha_estado", "Estado al", "fecha"),
                 ("diferencia_banco", "Diferencia libro–banco", "importe"), ("pendientes_banco", "Mov. bancarios pendientes", "entero"),
                 ("estado_banco", "Información bancaria", "texto")],
    "CARTERA": [("cobros_pagos", "Cobros / pagos", "importe"), ("notas_credito", "Notas de crédito", "importe"),
                ("anticipos", "Anticipos aplicados", "importe"), ("detracciones", "Detracciones", "importe"),
                ("retenciones", "Retenciones / percepciones", "importe"), ("otros_aplicados", "Otras aplicaciones", "importe"),
                ("clase", "Clase", "texto"), ("rol", "Rol", "texto")],
    "PERSONAL": [("entregado", "Importe entregado", "importe"), ("rendiciones", "Rendiciones", "importe"),
                 ("descuentos", "Descuentos", "importe"), ("devoluciones", "Devoluciones", "importe")],
    "ESTIMACION": [("cartera_total", "Cartera del tercero", "importe"), ("cartera_vencida", "Cartera vencida", "importe"),
                   ("vencida_365", "Vencida > 365 días", "importe"), ("cobertura", "Cobertura %", "pct")],
    "DIFERIDO": [("tipo", "Tipo", "texto"), ("fecha_inicio", "Inicio", "fecha"), ("fecha_fin", "Término", "fecha"),
                 ("contratado", "Importe contratado", "importe"), ("devengado", "Devengado al corte", "importe"),
                 ("pendiente", "Pendiente de devengo", "importe")],
    "EXISTENCIAS": [("codigo", "Código", "texto"), ("descripcion", "Descripción", "texto"), ("unidad", "Unidad", "texto"),
                    ("cantidad", "Cantidad", "importe"), ("costo_unitario", "Costo unitario", "tasa"), ("almacen", "Almacén", "texto")],
    "SERVICIOS_PROCESO": [("cliente", "Cliente", "texto"), ("contrato", "Contrato", "texto"), ("orden_servicio", "O.S.", "texto"),
                          ("maquinaria", "Maquinaria", "texto"), ("fecha_inicio", "Inicio", "fecha"),
                          ("fecha_estimada", "Culminación estimada", "fecha"), ("fecha_real", "Culminación real", "fecha"),
                          ("estado_operativo", "Estado operativo", "texto"), ("estado_facturacion", "Facturación", "texto"),
                          ("estado_contable", "Reconocimiento contable", "texto"),
                          ("costo_anterior", "Costos ejercicios anteriores", "importe"), ("costo_ejercicio", "Costos del ejercicio", "importe"),
                          ("mano_obra", "Mano de obra directa", "importe"), ("materiales", "Materiales", "importe"),
                          ("combustible", "Combustible", "importe"), ("servicios_terceros", "Servicios de terceros", "importe"),
                          ("depreciacion", "Depreciación", "importe"), ("indirectos", "Costos indirectos", "importe"),
                          ("transferencias", "Transferencias", "importe"), ("reconocido", "Reconocido en resultados", "importe"),
                          ("pendiente_evaluacion", "Pendiente de evaluación", "importe")],
    "PPE": [("codigo_activo", "Código", "texto"), ("descripcion", "Descripción", "texto"), ("categoria_activo", "Categoría", "texto"),
            ("fecha_adquisicion", "Adquisición", "fecha"), ("fecha_uso", "Disponible para uso", "fecha"),
            ("costo_inicial", "Costo inicial", "importe"), ("adiciones", "Adiciones", "importe"), ("mejoras", "Mejoras", "importe"),
            ("transferencias", "Transferencias", "importe"), ("bajas", "Bajas", "importe"), ("costo_final", "Costo final", "importe"),
            ("vida_util_meses", "Vida útil (meses)", "entero"), ("valor_residual", "Valor residual", "importe"),
            ("ubicacion", "Ubicación", "texto"), ("maquinaria", "Maquinaria", "texto")],
    "DEPRECIACION": [("codigo_activo", "Código", "texto"), ("descripcion", "Descripción", "texto"), ("costo_final", "Costo", "importe"),
                     ("dep_inicial", "Dep. acumulada inicial", "importe"), ("dep_periodo", "Dep. del periodo", "importe"),
                     ("ajustes", "Ajustes", "importe"), ("bajas", "Bajas", "importe"), ("dep_final", "Dep. acumulada final", "importe"),
                     ("valor_neto", "Valor neto contable", "importe"), ("vida_util_meses", "Vida útil financiera (meses)", "entero"),
                     ("dep_tributaria", "Dep. tributaria del periodo", "importe"),
                     ("diferencia_tributaria", "Diferencia financiera–tributaria", "importe")],
    "TRIBUTOS": [("tributo", "Tributo", "texto"), ("periodo_tributario", "Periodo tributario", "texto"),
                 ("determinado", "Obligación determinada", "importe"), ("pagos", "Pagos", "importe"),
                 ("compensaciones", "Compensaciones", "importe"), ("creditos", "Créditos aplicados", "importe"),
                 ("concepto", "Concepto", "texto"), ("exigible", "Exigible", "texto")],
    "REMUNERACIONES": [("concepto", "Concepto", "texto"), ("saldo_inicial", "Saldo inicial", "importe"),
                       ("provisiones", "Provisiones", "importe"), ("pagos", "Pagos", "importe"), ("ajustes", "Ajustes", "importe")],
    "FINANCIERAS": [("entidad", "Entidad", "texto"), ("contrato", "Contrato", "texto"), ("tipo", "Tipo", "texto"),
                    ("capital_original", "Capital original", "importe"), ("amortizado_libros", "Amortizado (libros)", "importe"),
                    ("capital_pendiente", "Capital pendiente (cronograma)", "importe"),
                    ("intereses", "Intereses (cronograma al corte)", "importe"), ("comisiones", "Comisiones y otros", "importe"),
                    ("cuotas_vencidas", "Cuotas vencidas", "entero"), ("importe_vencido", "Capital vencido", "importe"),
                    ("proximo_vencimiento", "Próximo vencimiento", "fecha"), ("proxima_cuota", "Próxima cuota", "importe"),
                    ("porcion_corriente", "Porción corriente", "importe"), ("porcion_no_corriente", "Porción no corriente", "importe"),
                    ("garantias", "Garantías", "texto")],
    "PATRIMONIO": [("saldo_inicial", "Saldo inicial", "importe"), ("aportes", "Aportes", "importe"),
                   ("distribuciones", "Distribuciones", "importe"), ("capitalizaciones", "Capitalizaciones", "importe"),
                   ("reclasificaciones", "Reclasificaciones", "importe"), ("ajustes", "Ajustes", "importe"),
                   ("resultado", "Resultado del ejercicio", "importe")],
    "GASTOS": [("mes", "Mes", "texto"), ("tipo_gasto", "Tipo de gasto", "texto"), ("maquinaria", "Maquinaria", "texto"),
               ("unidad_negocio", "Unidad de negocio", "texto")],
    "INGRESOS": [("mes", "Mes", "texto"), ("ingresos", "Ingresos registrados", "importe"), ("descuentos", "Descuentos", "importe"),
                 ("notas_credito", "Notas de crédito / devoluciones", "importe"), ("ajustes", "Ajustes", "importe"),
                 ("unidad_negocio", "Unidad de negocio", "texto"), ("transferencia", "Cuenta de transferencia", "texto")],
    "ORIGEN_DESTINO": [("mes", "Mes", "texto"), ("porcentaje", "% del total", "pct"), ("unidad_negocio", "Unidad de negocio", "texto")],
    "GENERICO": [], "ORDEN": [], "CIERRE": [],
}
ESPECIALIDADES = list(PROPIOS)


def campos(especialidad: str) -> list[tuple[str, str, str]]:
    return COMUNES + PROPIOS.get(especialidad, [])


def _c(*nombres, totales=()):
    """Columnas por nombre de campo; los importes listados en `totales` llevan total."""
    out = []
    for n in nombres:
        campo, _, titulo = n.partition(":")
        out.append((campo, titulo or None, campo in totales))
    return out


GEN = _c("cuenta", "razon_social", "tercero", "documento", "fecha", "glosa", "moneda", "saldo_me", "saldo", "dias", "tramo",
         "referencia", "estado_sustento", "observacion", totales=("saldo",))
COLS = {
    "EFECTIVO": _c("cuenta", "categoria:Tipo", "entidad", "numero_cuenta", "moneda", "saldo_me:Saldo ME (libros)",
                   "saldo:Saldo contable MN", "saldo_banco", "fecha_estado", "diferencia_banco", "pendientes_banco",
                   "estado_banco", "estado_sustento", totales=("saldo",)),
    "CARTERA": _c("razon_social", "tercero", "documento", "categoria:Clase", "fecha:Emisión", "fecha_vencimiento", "moneda",
                  "importe_original", "cobros_pagos", "notas_credito", "anticipos", "detracciones", "retenciones",
                  "saldo_me:Saldo pendiente ME", "saldo:Saldo pendiente MN", "dias:Días vencido", "tramo", "estado_sustento",
                  "observacion", totales=("saldo",)),
    "PERSONAL": _c("razon_social:Trabajador / accionista", "tercero", "categoria:Concepto", "documento", "fecha", "moneda",
                   "entregado", "rendiciones", "devoluciones", "descuentos", "saldo:Saldo pendiente", "dias", "tramo",
                   "estado_sustento", "observacion", totales=("saldo",)),
    "ESTIMACION": _c("razon_social", "tercero", "cartera_total", "cartera_vencida", "vencida_365", "saldo:Estimación registrada",
                     "cobertura", "estado_sustento", "observacion", totales=("saldo", "cartera_total", "cartera_vencida")),
    "DIFERIDO": _c("tipo", "glosa:Concepto", "razon_social:Proveedor", "documento", "fecha_inicio", "fecha_fin", "contratado",
                   "devengado", "saldo:Pendiente de devengo", "estado_sustento", "observacion", totales=("saldo", "contratado", "devengado")),
    "EXISTENCIAS": _c("cuenta", "codigo", "descripcion", "unidad", "almacen", "cantidad", "costo_unitario", "saldo:Valor",
                      "estado_sustento", "observacion", totales=("saldo",)),
    "SERVICIOS_PROCESO": _c("proyecto", "cliente", "contrato", "orden_servicio", "centro_costo", "maquinaria", "fecha_inicio",
                            "fecha_estimada", "fecha_real", "estado_operativo", "estado_facturacion", "estado_contable",
                            "costo_anterior", "costo_ejercicio", "mano_obra", "materiales", "combustible", "servicios_terceros",
                            "depreciacion", "indirectos", "transferencias", "reconocido", "saldo:Saldo contable",
                            "pendiente_evaluacion", "estado_sustento", "observacion",
                            totales=("saldo", "costo_anterior", "costo_ejercicio", "reconocido")),
    "PPE": _c("codigo_activo", "descripcion", "categoria_activo", "fecha_adquisicion", "fecha_uso", "costo_inicial", "adiciones",
              "mejoras", "transferencias", "bajas", "saldo:Costo final", "vida_util_meses", "valor_residual", "ubicacion",
              "centro_costo", "maquinaria", "estado_sustento", "observacion",
              totales=("saldo", "costo_inicial", "adiciones", "mejoras", "transferencias", "bajas")),
    "DEPRECIACION": _c("codigo_activo", "descripcion", "costo_final", "dep_inicial", "dep_periodo", "ajustes", "bajas",
                       "saldo:Dep. acumulada final", "valor_neto", "vida_util_meses", "dep_tributaria", "diferencia_tributaria",
                       "estado_sustento", "observacion", totales=("saldo", "dep_inicial", "dep_periodo", "valor_neto")),
    "TRIBUTOS": _c("tributo", "periodo_tributario", "concepto", "documento", "fecha", "fecha_vencimiento", "determinado", "pagos",
                   "compensaciones", "creditos", "saldo:Saldo pendiente", "exigible", "estado_sustento", "observacion",
                   totales=("saldo",)),
    "REMUNERACIONES": _c("razon_social:Trabajador", "tercero:Documento de identidad", "concepto", "saldo_inicial", "provisiones",
                         "pagos", "ajustes", "saldo:Saldo pendiente", "estado_sustento", "observacion",
                         totales=("saldo", "provisiones", "pagos")),
    "FINANCIERAS": _c("entidad", "contrato", "tipo", "moneda", "capital_original", "amortizado_libros", "capital_pendiente",
                      "intereses", "comisiones", "cuotas_vencidas", "importe_vencido", "proximo_vencimiento", "proxima_cuota",
                      "porcion_corriente", "porcion_no_corriente", "garantias", "saldo:Saldo contable MN", "estado_sustento",
                      "observacion", totales=("saldo",)),
    "PATRIMONIO": _c("cuenta", "categoria:Concepto", "saldo_inicial", "aportes", "distribuciones", "capitalizaciones",
                     "reclasificaciones", "ajustes", "resultado", "saldo:Saldo final", "estado_sustento", "observacion",
                     totales=("saldo", "saldo_inicial")),
    "GASTOS": _c("cuenta", "tipo_gasto", "razon_social:Proveedor", "tercero", "documento", "fecha", "mes", "centro_costo",
                 "proyecto", "maquinaria", "glosa", "saldo:Importe", "estado_sustento", "observacion", totales=("saldo",)),
    "INGRESOS": _c("cuenta", "categoria", "razon_social:Cliente", "tercero", "documento", "fecha", "mes", "proyecto", "ingresos",
                   "descuentos", "notas_credito", "ajustes", "saldo:Ingreso neto", "transferencia", "estado_sustento",
                   totales=("saldo", "ingresos", "descuentos", "notas_credito")),
    "ORIGEN_DESTINO": _c("cuenta:Cuenta", "centro_costo", "proyecto", "unidad_negocio", "mes", "saldo:Importe distribuido",
                         "porcentaje", "estado_sustento", totales=("saldo",)),
    "GENERICO": GEN, "ORDEN": GEN, "CIERRE": GEN,
}

# (código, nombre, especialidad, prefijos, parámetros)
PLANTILLAS = [
    ("EF-10", "Efectivo y equivalentes de efectivo", "EFECTIVO", "10", {}),
    ("EF-101", "Caja", "EFECTIVO", "101", {}),
    ("EF-102", "Fondos fijos", "EFECTIVO", "102", {}),
    ("EF-104", "Cuentas corrientes en instituciones financieras", "EFECTIVO", "104", {}),
    ("EF-105", "Otros equivalentes de efectivo", "EFECTIVO", "105", {}),
    ("EF-106", "Depósitos en instituciones financieras (ahorro y plazo)", "EFECTIVO", "106", {}),
    ("EF-107", "Fondos sujetos a restricción", "EFECTIVO", "107", {}),
    ("CC-12", "Cuentas por cobrar comerciales – terceros", "CARTERA", "12", {"lado": "CXC"}),
    ("CC-13", "Cuentas por cobrar comerciales – relacionadas", "CARTERA", "13", {"lado": "CXC"}),
    ("CC-14", "Cuentas por cobrar al personal, accionistas y directores", "PERSONAL", "14", {}),
    ("CC-1413", "Entregas a rendir cuenta", "PERSONAL", "1413", {}),
    ("CC-16", "Cuentas por cobrar diversas – terceros", "CARTERA", "16", {"lado": "CXC"}),
    ("CC-17", "Cuentas por cobrar diversas – relacionadas", "CARTERA", "17", {"lado": "CXC"}),
    ("SA-18", "Servicios y otros contratados por anticipado", "DIFERIDO", "18", {}),
    ("ES-19", "Estimación de cuentas de cobranza dudosa", "ESTIMACION", "19", {"cartera": ["12", "13", "16", "17"]}),
    ("EX-20", "Mercaderías", "EXISTENCIAS", "20", {}),
    ("EX-21", "Productos terminados", "EXISTENCIAS", "21", {}),
    ("EX-22", "Subproductos, desechos y desperdicios", "EXISTENCIAS", "22", {}),
    ("SP-23", "Productos en proceso / servicios en proceso (costos acumulados)", "SERVICIOS_PROCESO", "23", {}),
    ("EX-24", "Materias primas", "EXISTENCIAS", "24", {}),
    ("EX-25", "Materiales auxiliares, suministros y repuestos", "EXISTENCIAS", "25", {}),
    ("EX-26", "Envases y embalajes", "EXISTENCIAS", "26", {}),
    ("EX-28", "Existencias por recibir", "EXISTENCIAS", "28", {}),
    ("EX-29", "Desvalorización de existencias", "GENERICO", "29", {"nota": "La desvalorización requiere evaluación del valor neto realizable (NIC 2)."}),
    ("AI-30", "Inversiones mobiliarias", "GENERICO", "30", {}),
    ("AI-31", "Propiedades de inversión", "PPE", "31", {}),
    ("AI-32", "Activos por derecho de uso", "PPE", "32", {}),
    ("AI-33", "Propiedad, planta y equipo", "PPE", "33", {}),
    ("AI-34", "Intangibles", "PPE", "34", {}),
    ("AI-35", "Activos biológicos", "PPE", "35", {}),
    ("AI-36", "Desvalorización (deterioro) de activo inmovilizado", "GENERICO", "36", {"nota": "El deterioro requiere evaluación según NIC 36."}),
    ("AI-37", "Activo diferido", "GENERICO", "37", {}),
    ("AI-38", "Otros activos", "GENERICO", "38", {}),
    ("AI-39", "Depreciación, amortización y agotamiento acumulados", "DEPRECIACION", "39", {}),
    ("PA-40", "Tributos, contraprestaciones y aportes por pagar", "TRIBUTOS", "40", {}),
    ("PA-41", "Remuneraciones y participaciones por pagar", "REMUNERACIONES", "41", {}),
    ("PA-42", "Cuentas por pagar comerciales – terceros", "CARTERA", "42", {"lado": "CXP"}),
    ("PA-43", "Cuentas por pagar comerciales – relacionadas", "CARTERA", "43", {"lado": "CXP"}),
    ("PA-44", "Cuentas por pagar a accionistas, directores y gerentes", "CARTERA", "44", {"lado": "CXP"}),
    ("PA-45", "Obligaciones financieras", "FINANCIERAS", "45", {}),
    ("PA-46", "Cuentas por pagar diversas – terceros", "CARTERA", "46", {"lado": "CXP"}),
    ("PA-47", "Cuentas por pagar diversas – relacionadas", "CARTERA", "47", {"lado": "CXP"}),
    ("PA-48", "Provisiones", "GENERICO", "48", {}),
    ("PA-49", "Pasivo diferido", "GENERICO", "49", {}),
    ("PN-50", "Capital", "PATRIMONIO", "50", {}),
    ("PN-51", "Acciones de inversión", "PATRIMONIO", "51", {}),
    ("PN-52", "Capital adicional", "PATRIMONIO", "52", {}),
    ("PN-56", "Resultados no realizados", "PATRIMONIO", "56", {}),
    ("PN-57", "Excedente de revaluación", "PATRIMONIO", "57", {}),
    ("PN-58", "Reservas", "PATRIMONIO", "58", {}),
    ("PN-59", "Resultados acumulados", "PATRIMONIO", "59", {}),
    ("GA-6", "Gastos por naturaleza", "GASTOS", "6", {}),
    ("GA-60", "Compras", "GASTOS", "60", {}),
    ("GA-62", "Gastos de personal", "GASTOS", "62", {}),
    ("GA-63", "Servicios prestados por terceros", "GASTOS", "63", {}),
    ("GA-634", "Mantenimiento y reparaciones", "GASTOS", "634", {}),
    ("GA-635", "Alquileres", "GASTOS", "635", {}),
    ("GA-64", "Gastos por tributos", "GASTOS", "64", {}),
    ("GA-651", "Seguros", "GASTOS", "651", {}),
    ("GA-67", "Gastos financieros", "GASTOS", "67", {}),
    ("GA-68", "Valuación y deterioro de activos y provisiones (depreciación)", "GASTOS", "68", {}),
    ("GA-69", "Costo de ventas", "GASTOS", "69", {}),
    ("IN-7", "Ingresos y cuentas de gestión", "INGRESOS", "7", {}),
    ("IN-70", "Ventas", "INGRESOS", "70", {}),
    ("IN-71", "Variación de la producción almacenada (transferencia)", "INGRESOS", "71", {"transferencia": True}),
    ("IN-72", "Producción de activo inmovilizado (transferencia)", "INGRESOS", "72", {"transferencia": True}),
    ("IN-78", "Cargas cubiertas por provisiones (transferencia)", "INGRESOS", "78", {"transferencia": True}),
    ("OD-79", "Cargas imputables a cuentas de costos y gastos (origen–destino)", "ORIGEN_DESTINO", "79", {}),
    ("OD-9", "Contabilidad analítica de explotación (destino)", "ORIGEN_DESTINO", "9", {}),
    ("CI-8", "Saldos intermediarios de gestión y cuentas de cierre", "CIERRE", "8", {}),
    ("CO-0", "Cuentas de orden (control, garantías, compromisos y contingencias)", "ORDEN", "0", {}),
    ("GEN", "Anexo genérico por tercero y documento", "GENERICO", "", {}),
]
# plantilla de reporte especializado con filtro (no por cuenta)
REPORTES_FILTRADOS = [
    ("GA-COMB", "Combustible", "GASTOS", "6", [{"campo": "glosa", "op": "contiene", "valor": "COMBUST"}]),
]
RANGOS_DEFECTO = [[1, 30], [31, 60], [61, 90], [91, 180], [181, 365], [366, None]]
VERSION_CATALOGO = 3


def sembrar(db: Session) -> None:
    """Crea (o actualiza) el catálogo global. Idempotente."""
    existentes = {p.codigo: p for p in db.scalars(select(PlantillaAnexo).where(PlantillaAnexo.empresa_id.is_(None)))}
    todos = [(c, n, e, pref, par, None) for c, n, e, pref, par in PLANTILLAS] + \
            [(c, n, e, pref, {}, filtros) for c, n, e, pref, filtros in REPORTES_FILTRADOS]
    cambios = False
    for codigo, nombre, esp, prefijo, par, filtros in todos:
        p = existentes.get(codigo)
        if p and p.version >= VERSION_CATALOGO:
            continue
        if not p:
            p = PlantillaAnexo(empresa_id=None, codigo=codigo)
            db.add(p)
        p.nombre, p.especialidad, p.cuentas = nombre, esp, prefijo
        p.tipo = "GENERICA" if esp in ("GENERICO",) else "ESPECIALIZADA"
        p.elemento = prefijo[:1] or None
        p.parametros = json.dumps(par)
        p.filtros = json.dumps(filtros) if filtros else None
        p.rangos_antiguedad = json.dumps(RANGOS_DEFECTO)
        p.encabezado = json.dumps({"titulo": f"Anexo — {nombre}"})
        p.orientacion = "HORIZONTAL"
        p.compartida, p.autorizada, p.autorizada_por, p.version = True, True, "catálogo del sistema", VERSION_CATALOGO
        p.agrupar_por = "razon_social" if esp in ("CARTERA", "PERSONAL", "REMUNERACIONES") else (
            "tributo" if esp == "TRIBUTOS" else ("tipo_gasto" if esp == "GASTOS" else None))
        p.subtotales = "saldo" if p.agrupar_por else None
        db.flush()
        reemplazar_columnas(db, p, COLS[esp])
        cambios = True
    if cambios:
        db.commit()


def reemplazar_columnas(db: Session, p: PlantillaAnexo, columnas) -> None:
    for c in db.scalars(select(ColumnaPlantilla).where(ColumnaPlantilla.plantilla_id == p.id)):
        db.delete(c)
    db.flush()
    disponibles = {c: (t, tp) for c, t, tp in campos(p.especialidad)}
    for i, col in enumerate(columnas):
        if isinstance(col, dict):
            campo, titulo, total, visible = col["campo"], col.get("titulo"), col.get("total", False), col.get("visible", True)
            tipo = col.get("tipo")
        else:
            (campo, titulo, total), visible, tipo = col, True, None
        if campo not in disponibles and not tipo:
            continue
        t_def, tp_def = disponibles.get(campo, (campo, "texto"))
        db.add(ColumnaPlantilla(plantilla_id=p.id, orden=i, campo=campo, titulo=(titulo or t_def)[:80], tipo=tipo or tp_def,
                                visible=visible, total=bool(total)))
    db.flush()


def para_cuenta(db: Session, empresa_id: int, cuenta: str, plantilla_id: int | None = None) -> PlantillaAnexo:
    """Plantilla explícita o la de prefijo más largo (las de la empresa tienen prioridad sobre el catálogo)."""
    if plantilla_id:
        p = db.get(PlantillaAnexo, plantilla_id)
        if p and p.empresa_id in (None, empresa_id) and p.activa:
            return p
        raise ValueError("Plantilla no disponible para la empresa")
    candidatas = db.scalars(select(PlantillaAnexo).where(
        PlantillaAnexo.activa.is_(True), PlantillaAnexo.filtros.is_(None),
        (PlantillaAnexo.empresa_id.is_(None)) | ((PlantillaAnexo.empresa_id == empresa_id) & PlantillaAnexo.autorizada.is_(True)
                                                  & (PlantillaAnexo.tipo != "PERSONALIZADA")))).all()
    mejor, largo = None, -1
    for p in candidatas:
        for pref in [x.strip() for x in (p.cuentas or "").split(",")] or [""]:
            if cuenta.startswith(pref) and (len(pref) > largo or (len(pref) == largo and p.empresa_id)):
                mejor, largo = p, len(pref)
    return mejor


def snapshot(db: Session, p: PlantillaAnexo) -> dict:
    from app.models import FormulaPlantilla, ReglaPlantilla
    cols = db.scalars(select(ColumnaPlantilla).where(ColumnaPlantilla.plantilla_id == p.id).order_by(ColumnaPlantilla.orden)).all()
    forms = db.scalars(select(FormulaPlantilla).where(FormulaPlantilla.plantilla_id == p.id).order_by(FormulaPlantilla.orden)).all()
    reglas = db.scalars(select(ReglaPlantilla).where(ReglaPlantilla.plantilla_id == p.id, ReglaPlantilla.activa.is_(True))).all()
    j = lambda v, d: json.loads(v) if v else d  # noqa: E731
    return {
        "id": p.id, "codigo": p.codigo, "nombre": p.nombre, "tipo": p.tipo, "especialidad": p.especialidad, "version": p.version,
        "empresa_id": p.empresa_id, "cuentas": p.cuentas, "orientacion": p.orientacion, "usar_logo": p.usar_logo,
        "agrupar_por": [x for x in (p.agrupar_por or "").split(",") if x], "subtotales": [x for x in (p.subtotales or "").split(",") if x],
        "orden": [x for x in (p.orden or "").split(",") if x], "filtros": j(p.filtros, []), "parametros": j(p.parametros, {}),
        "rangos_antiguedad": j(p.rangos_antiguedad, RANGOS_DEFECTO), "encabezado": j(p.encabezado, {}),
        "columnas": [{"campo": c.campo, "titulo": c.titulo, "tipo": c.tipo, "visible": c.visible, "total": c.total} for c in cols],
        "formulas": [{"campo": f.campo, "titulo": f.titulo, "expresion": f.expresion, "tipo": f.tipo} for f in forms],
        "reglas": [{"codigo": r.codigo, "descripcion": r.descripcion, "tipo": r.tipo, "expresion": r.expresion,
                    "parametros": j(r.parametros, {}), "severidad": r.severidad} for r in reglas],
    }
