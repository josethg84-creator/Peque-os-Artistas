"""Catálogo de reglas de auditoría del sistema (empresa_id nulo) y su siembra idempotente.

Las reglas NORMATIVAS (tributarias) se siembran sin norma, fuente ni parámetros: quedan «pendientes de validación» y no se
ejecutan hasta que el responsable tributario registra su contenido, vigencia y parámetros y las valida.
"""
import json

from sqlalchemy import select

from app.auditoria import configurables, estadistica, r_cuentas, r_duplicados, r_especiales, r_integridad, r_tributaria
from app.models import CategoriaRegla, ReglaAuditoria

VERSION = 1
EVALUADORES = {**r_integridad.EVALUADORES, **r_duplicados.EVALUADORES, **r_cuentas.EVALUADORES, **r_especiales.EVALUADORES,
               **r_tributaria.EVALUADORES, **estadistica.EVALUADORES, **configurables.EVALUADORES}

CATEGORIAS = [
    ("INTEGRIDAD", "Integridad contable", "Cuadre, cuentas, periodos, importes, fechas, tipos de cambio y cruces entre libros."),
    ("ASIENTOS", "Auditoría de asientos", "Indicadores de riesgo por asiento y contrapartidas."),
    ("DUPLICIDADES", "Duplicidades", "Coincidencias exactas y aproximadas en documentos, pagos y registros."),
    ("CXC", "Cuentas por cobrar", "Cuentas 12, 13, 14, 16, 17."),
    ("CXP", "Cuentas por pagar", "Cuentas 42, 43, 44, 45, 46, 47."),
    ("TESORERIA", "Bancos y tesorería", "Conciliaciones bancarias de la fase 6 y movimientos de caja y bancos."),
    ("GASTOS", "Gastos por naturaleza", "Elemento 6."),
    ("ORIGEN_DESTINO", "Origen y destino", "Clase 6, 79, 78 y 9; reglas de distribución."),
    ("PARAMETRIZACION", "Parametrización del ERP", "Plan de cuentas, rubros financieros, destinos y distribución."),
    ("INGRESOS", "Ingresos", "Cuentas de ingresos y registro de ventas."),
    ("SERVICIOS", "Servicios en proceso", "Cuenta 23, proyectos y estados operativos."),
    ("ACTIVOS", "Activos fijos", "Propiedad, planta y equipo, intangibles, derecho de uso y depreciación."),
    ("INVENTARIOS", "Inventarios", "Existencias, kardex y costos unitarios."),
    ("PLANILLAS", "Planillas", "Remuneraciones, beneficios, aportes y retenciones (datos personales protegidos)."),
    ("TRIBUTARIA", "Tributaria preventiva", "Potenciales contingencias tributarias (sin determinar infracciones)."),
    ("DEVENGOS", "Devengos y corte", "Gastos anticipados, provisiones y operaciones entre periodos."),
    ("ESTADISTICA", "Análisis estadístico", "Herramientas exploratorias de anomalías."),
    ("CONFIGURABLE", "Reglas configurables", "Controles definidos por la empresa con el diseñador."),
]


def R(codigo, modulo, nombre, evaluador, riesgo="MEDIO", prob=3, estructural=False, cuentas=None, p=None, criterio=None, recomendacion=None,
      normativa=False, descripcion=None, evidencia=None):
    return dict(codigo=codigo, modulo=modulo, nombre=nombre, evaluador=evaluador, riesgo=riesgo, probabilidad=prob, estructural=estructural,
                cuentas=",".join(cuentas) if cuentas else None, parametros=p or {}, criterio=criterio, recomendacion=recomendacion,
                normativa=normativa, descripcion=descripcion or nombre, evidencia_requerida=evidencia)


CRIT_PCGE = "Plan Contable General Empresarial y políticas contables de la empresa."
REGLAS = [
    # ---- integridad
    R("INT-01", "INTEGRIDAD", "Igualdad entre debe y haber por asiento", "descuadre", "ALTO", 5, True, criterio="Partida doble: cada asiento debe cuadrar.",
      recomendacion="Corrija el asiento en el ERP y reimporte; no se generan ajustes automáticos."),
    R("INT-02", "INTEGRIDAD", "Cuentas inexistentes en el plan", "cuentas_inexistentes", "ALTO", 5, True, criterio=CRIT_PCGE),
    R("INT-03", "INTEGRIDAD", "Movimientos en cuentas inactivas", "cuentas_inactivas", "MEDIO", 4, True, criterio=CRIT_PCGE),
    R("INT-04", "INTEGRIDAD", "Cuentas no autorizadas para movimientos", "cuentas_no_autorizadas", "MEDIO", 4, True, criterio=CRIT_PCGE),
    R("INT-05", "INTEGRIDAD", "Asientos fuera del periodo", "fuera_de_periodo", "MEDIO", 4, True, criterio="Principio de devengo y corte contable."),
    R("INT-06", "INTEGRIDAD", "Registros incompletos", "incompletos", "MEDIO", 4, True),
    R("INT-07", "INTEGRIDAD", "Fechas inconsistentes", "fechas_inconsistentes", "BAJO", 3),
    R("INT-08", "INTEGRIDAD", "Importes inválidos", "importes_invalidos", "ALTO", 5, True),
    R("INT-09", "INTEGRIDAD", "Movimientos sin glosa", "sin_glosa", "BAJO", 2, p={"importe_minimo": "0"}),
    R("INT-10", "INTEGRIDAD", "Documentos sin identificación en cuentas de terceros", "sin_identificacion", "MEDIO", 3),
    R("INT-11", "INTEGRIDAD", "Tipos de cambio inconsistentes", "tipo_cambio", "MEDIO", 3, p={"tolerancia_conversion": "0.05", "tolerancia_tc": "0.005"},
      criterio="NIC 21: conversión al tipo de cambio de la fecha de la transacción."),
    R("INT-12", "INTEGRIDAD", "Diferencias entre libro diario y libro mayor", "diario_vs_mayor", "ALTO", 4, True),
    R("INT-13", "INTEGRIDAD", "Diferencias entre mayor y balance de comprobación", "mayor_vs_balance", "ALTO", 4, True),
    R("INT-14", "INTEGRIDAD", "Saldos iniciales frente al cierre anterior", "apertura_vs_cierre", "ALTO", 4, True),
    # ---- asientos
    R("ASI-01", "ASIENTOS", "Asientos manuales por importes significativos", "manuales_significativos", "MEDIO", 2, p={"factores_adicionales": 1},
      descripcion="Solo con origen exportado por el ERP; exige importe significativo y otro factor de riesgo."),
    R("ASI-02", "ASIENTOS", "Asientos al cierre del periodo con factores de riesgo", "al_cierre", "MEDIO", 2, p={"dias_cierre": 3, "factores_adicionales": 2}),
    R("ASI-03", "ASIENTOS", "Asientos registrados después del cierre", "despues_del_cierre", "BAJO", 2, p={"dias_gracia": 10}),
    R("ASI-04", "ASIENTOS", "Asientos con fechas retroactivas", "retroactivos", "BAJO", 2, p={"dias": 30}),
    R("ASI-05", "ASIENTOS", "Importes redondos inusuales", "importes_redondos", "BAJO", 2, p={"minimo_redondo": "10000", "pct_habitual": 20}),
    R("ASI-06", "ASIENTOS", "Cuentas poco frecuentes", "cuentas_poco_frecuentes", "BAJO", 2, p={"max_usos_cuenta": 1, "importe_minimo": "5000", "min_asientos": 50}),
    R("ASI-07", "ASIENTOS", "Combinaciones contables atípicas", "combinaciones_atipicas", "BAJO", 2, p={"min_asientos": 100, "importe_minimo": "5000"}),
    R("ASI-08", "ASIENTOS", "Glosas genéricas", "glosas_genericas", "BAJO", 2, p={"importe_minimo": "1000"}),
    R("ASI-09", "ASIENTOS", "Contrapartidas inesperadas", "contrapartidas", "MEDIO", 3),
    R("ASI-10", "ASIENTOS", "Reclasificaciones frecuentes", "reclasificaciones", "BAJO", 2, p={"veces": 3}),
    R("ASI-11", "ASIENTOS", "Extornos repetitivos", "extornos", "MEDIO", 3, p={"veces": 2}),
    R("ASI-12", "ASIENTOS", "Movimientos extraordinarios", "extraordinarios", "MEDIO", 2, p={"desviaciones": 3, "importe_minimo": "1000", "min_lineas": 10}),
    R("ASI-13", "ASIENTOS", "Ajustes sin documentación disponible", "ajustes_sin_documentacion", "MEDIO", 3, p={"importe_minimo": "1000"}),
    # ---- duplicidades
    R("DUP-01", "DUPLICIDADES", "Facturas de compra duplicadas", "dup_documentos", "ALTO", 4, p={"clase": "COMPRAS"}),
    R("DUP-02", "DUPLICIDADES", "Facturas de venta duplicadas", "dup_documentos", "ALTO", 4, p={"clase": "VENTAS"}),
    R("DUP-03", "DUPLICIDADES", "Recibos por honorarios duplicados", "dup_documentos", "ALTO", 4, p={"clase": "HONORARIOS"}),
    R("DUP-04", "DUPLICIDADES", "Notas de crédito duplicadas", "dup_documentos", "MEDIO", 4, p={"clase": "NOTAS_CREDITO"}),
    R("DUP-05", "DUPLICIDADES", "Pagos a proveedores duplicados", "dup_aplicaciones", "ALTO", 4, p={"clase": "PAGOS"}),
    R("DUP-06", "DUPLICIDADES", "Cobranzas duplicadas", "dup_aplicaciones", "MEDIO", 4, p={"clase": "COBRANZAS"}),
    R("DUP-07", "DUPLICIDADES", "Transferencias bancarias duplicadas", "dup_transferencias", "ALTO", 4),
    R("DUP-08", "DUPLICIDADES", "Asientos contables duplicados", "dup_asientos", "ALTO", 4, p={"importe_minimo": "1"}),
    R("DUP-09", "DUPLICIDADES", "Registros de planilla duplicados", "dup_documentos", "ALTO", 4, p={"clase": "PLANILLAS"}),
    R("DUP-10", "DUPLICIDADES", "Activos fijos duplicados", "dup_documentos", "MEDIO", 3, p={"clase": "ACTIVOS"}),
    R("DUP-11", "DUPLICIDADES", "Depreciaciones duplicadas", "dup_documentos", "ALTO", 4, p={"clase": "DEPRECIACIONES"}),
    R("DUP-12", "DUPLICIDADES", "Detracciones duplicadas", "dup_detracciones", "MEDIO", 4),
    R("DUP-13", "DUPLICIDADES", "Retenciones duplicadas", "dup_documentos", "MEDIO", 4, p={"clase": "RETENCIONES"}),
    # ---- cuentas por cobrar
    R("CXC-01", "CXC", "Documentos por cobrar vencidos", "vencidos", "MEDIO", 3, cuentas=["12", "13", "16"], p={"dias": 90}),
    R("CXC-02", "CXC", "Saldos antiguos por cobrar", "antiguos", "MEDIO", 3, cuentas=["12", "13", "16"], p={"dias": 365}),
    R("CXC-03", "CXC", "Concentración de la deuda en un cliente", "concentracion", "BAJO", 2, cuentas=["12"], p={"porcentaje": 40}),
    R("CXC-04", "CXC", "Saldos acreedores inesperados de clientes", "contrario_tercero", "MEDIO", 3, cuentas=["12", "13", "16"]),
    R("CXC-05", "CXC", "Cobranzas sin aplicación", "aplicaciones_pendientes", "MEDIO", 3, cuentas=["12", "13"], p={"clases": ["COBRANZA"]}),
    R("CXC-06", "CXC", "Anticipos de clientes pendientes", "anticipos", "MEDIO", 3, cuentas=["122"], p={"dias": 90}),
    R("CXC-07", "CXC", "Notas de crédito por aplicar a clientes", "aplicaciones_pendientes", "MEDIO", 3, cuentas=["12"], p={"clases": ["NOTA_CREDITO"]}),
    R("CXC-08", "CXC", "Préstamos al personal pendientes", "personal", "MEDIO", 3, cuentas=["1411", "1412"], p={"dias": 90, "nombre": "Préstamo al personal pendiente"}),
    R("CXC-09", "CXC", "Entregas a rendir antiguas", "personal", "MEDIO", 3, cuentas=["1413"], p={"dias": 30, "nombre": "Entrega a rendir antigua"}),
    R("CXC-10", "CXC", "Diferencias de cambio pendientes de evaluación (por cobrar)", "diferencia_cambio", "MEDIO", 3, cuentas=["12", "13", "14", "16", "17"]),
    R("CXC-11", "CXC", "Posible necesidad de evaluar deterioro", "deterioro", "MEDIO", 2, cuentas=["12", "13", "16"], p={"dias": 365}),
    R("CXC-12", "CXC", "Diferencias entre anexos y balance (por cobrar)", "anexos_vs_balance", "MEDIO", 4, cuentas=["12", "13", "14", "16", "17"]),
    # ---- cuentas por pagar
    R("CXP-01", "CXP", "Facturas por pagar vencidas", "vencidos", "MEDIO", 3, cuentas=["42", "43", "46"], p={"dias": 90}),
    R("CXP-02", "CXP", "Obligaciones antiguas", "antiguos", "MEDIO", 3, cuentas=["42", "43", "46", "47"], p={"dias": 365}),
    R("CXP-03", "CXP", "Pagos sin documento asociado", "pagos_sin_documento", "MEDIO", 3, cuentas=["42", "43", "46"]),
    R("CXP-04", "CXP", "Anticipos a proveedores pendientes de aplicación", "anticipos", "MEDIO", 3, cuentas=["422"], p={"dias": 90}),
    R("CXP-05", "CXP", "Notas de crédito de proveedores pendientes", "aplicaciones_pendientes", "MEDIO", 3, cuentas=["42", "43"], p={"clases": ["NOTA_CREDITO"]}),
    R("CXP-06", "CXP", "Saldos deudores inesperados de proveedores", "contrario_tercero", "MEDIO", 3, cuentas=["421", "423", "43", "46", "47"]),
    R("CXP-07", "CXP", "Obligaciones sin tercero identificado", "sin_tercero", "MEDIO", 3, cuentas=["42", "43", "44", "46", "47"]),
    R("CXP-08", "CXP", "Diferencias entre cronogramas y contabilidad", "conciliacion_memoria", "ALTO", 4,
      p={"tipo": "FINANCIERAS", "subtipos": ["DIFERENCIA_CAPITAL", "CUOTA_NO_REGISTRADA", "PAGO_SIN_CUOTA", "PAGO_DUPLICADO_POTENCIAL"]}),
    R("CXP-09", "CXP", "Diferencias entre anexos y balance (por pagar)", "anexos_vs_balance", "MEDIO", 4, cuentas=["42", "43", "44", "45", "46", "47"]),
    R("CXP-10", "CXP", "Obligaciones potencialmente omitidas (registro de compras)", "conciliacion_memoria", "ALTO", 3,
      p={"tipo": "COMPRAS", "subtipos": ["COMPRA_NO_CONTABILIZADA"]}),
    # ---- tesorería
    R("BAN-01", "TESORERIA", "Partidas conciliatorias antiguas", "bancaria", "MEDIO", 3,
      p={"subtipos": ["DEPOSITO_EN_TRANSITO", "CHEQUE_PENDIENTE_COBRO", "TRANSFERENCIA_PENDIENTE"], "dias_antiguedad": 60}),
    R("BAN-02", "TESORERIA", "Comisiones e ITF no registrados", "bancaria", "BAJO", 4, p={"subtipos": ["COMISION_BANCARIA", "ITF"]}),
    R("BAN-03", "TESORERIA", "Abonos y cargos no identificados", "bancaria", "ALTO", 3, p={"subtipos": ["ABONO_NO_IDENTIFICADO", "CARGO_NO_REGISTRADO"]}),
    R("BAN-04", "TESORERIA", "Transferencias duplicadas en la conciliación", "bancaria", "ALTO", 3, p={"subtipos": ["DUPLICADO_CONTABLE", "DUPLICADO_EXTERNA"]}),
    R("BAN-05", "TESORERIA", "Cheques pendientes de cobro y depósitos en tránsito", "bancaria", "BAJO", 2,
      p={"subtipos": ["CHEQUE_PENDIENTE_COBRO", "DEPOSITO_EN_TRANSITO"]}),
    R("BAN-06", "TESORERIA", "Saldos bancarios inconsistentes", "bancaria", "CRITICO", 4, p={"subtipos": ["DIFERENCIA_FINAL"]}),
    R("BAN-07", "TESORERIA", "Diferencias de importe, moneda o periodo", "bancaria", "MEDIO", 3, p={"subtipos": ["DIFERENCIA_IMPORTE", "PERIODO_DIFERENTE"]}),
    R("BAN-08", "TESORERIA", "Transferencias entre cuentas sin contrapartida", "transferencias_internas", "MEDIO", 3, p={"cuentas_puente": ["103"]}),
    R("BAN-09", "TESORERIA", "Movimientos sin documentación disponible", "movimientos_sin_documento", "MEDIO", 3, p={"importe_minimo": "1000"}),
    # ---- gastos
    R("GAS-01", "GASTOS", "Gastos duplicados potenciales", "dup_cuenta", "ALTO", 3, cuentas=["6"]),
    R("GAS-02", "GASTOS", "Gastos sin documento asociado", "gastos_sin_documento", "MEDIO", 3, p={"importe_minimo": "500"}),
    R("GAS-03", "GASTOS", "Gastos sin proveedor identificado", "gastos_sin_documento", "MEDIO", 3, p={"importe_minimo": "500", "modo": "TERCERO"}),
    R("GAS-04", "GASTOS", "Gastos sin centro de costo obligatorio", "gastos_sin_cc", "BAJO", 3, cuentas=["6"]),
    R("GAS-05", "GASTOS", "Gastos fuera del periodo del comprobante", "gastos_fuera_periodo", "MEDIO", 3, cuentas=["6"], p={"meses": 1}),
    R("GAS-06", "GASTOS", "Gastos que requieren evaluación de capitalización", "palabras", "MEDIO", 3, cuentas=["6"],
      p={"palabras": ["EQUIPO", "MAQUINARIA", "VEHICULO", "COMPUTADORA", "LAPTOP", "SERVIDOR", "MOBILIARIO", "EDIFICACION", "CONSTRUCCION",
                      "MEJORA", "AMPLIACION", "OVERHAUL", "REPOTENCIACION"], "importe_minimo": "2000",
         "titulo": "Gasto que requiere evaluación de capitalización", "regularizacion": "REQUIERE_RECLASIFICACION"},
      criterio="NIC 16 / NIC 38: reconocimiento de activos."),
    R("GAS-07", "GASTOS", "Gastos potencialmente personales", "palabras", "MEDIO", 2, cuentas=["6"],
      p={"palabras": ["SUPERMERCADO", "COLEGIO", "PENSION ESCOLAR", "CINE", "JUGUETERIA", "GIMNASIO", "SPA", "LICORERIA", "VIAJE FAMILIAR",
                      "REGALO PERSONAL"], "importe_minimo": "0", "titulo": "Gasto potencialmente personal", "tributario": "PENDIENTE_EVALUACION"}),
    R("GAS-08", "GASTOS", "Gastos que requieren evaluación tributaria", "palabras", "MEDIO", 2, cuentas=["659"],
      p={"palabras": ["DONACION", "MULTA", "SANCION", "INTERES MORATORIO", "GASTO NO SUSTENTADO", "OTROS"], "importe_minimo": "0",
         "titulo": "Gasto que requiere evaluación tributaria", "tributario": "PENDIENTE_EVALUACION", "regularizacion": "REQUIERE_EVALUACION_TRIBUTARIA"}),
    R("GAS-09", "GASTOS", "Gastos recurrentes omitidos", "recurrentes_omitidos", "MEDIO", 2, cuentas=["63", "65"], p={"min_meses": 3}),
    R("GAS-10", "GASTOS", "Variaciones significativas de gastos", "variaciones", "BAJO", 2, cuentas=["6"], p={"porcentaje": 50, "importe_minimo": "5000"}),
    R("GAS-11", "GASTOS", "Concentración de gastos por proveedor", "concentracion_flujo", "BAJO", 2, cuentas=["6"], p={"porcentaje": 50}),
    # ---- origen y destino
    R("ODE-01", "ORIGEN_DESTINO", "Gastos sin destino", "destino", "ALTO", 4, p={"caso": "SIN_DESTINO"}),
    R("ODE-02", "ORIGEN_DESTINO", "Destinos sin origen identificado", "destino", "MEDIO", 3, p={"caso": "SIN_ORIGEN"}),
    R("ODE-03", "ORIGEN_DESTINO", "Gastos distribuidos más de una vez", "destino", "ALTO", 4, p={"caso": "DUPLICADO"}),
    R("ODE-04", "ORIGEN_DESTINO", "Distribuciones incompletas", "destino", "MEDIO", 3, p={"caso": "INCOMPLETO"}),
    R("ODE-05", "ORIGEN_DESTINO", "Destinos incorrectos", "destino", "MEDIO", 3, p={"caso": "INCORRECTO"}),
    R("ODE-06", "ORIGEN_DESTINO", "Contrapartidas de transferencia incorrectas", "destino", "ALTO", 4, p={"caso": "TRANSFERENCIA"}),
    R("ODE-07", "ORIGEN_DESTINO", "Porcentajes de distribución inconsistentes", "porcentajes", "MEDIO", 4, True),
    R("ODE-08", "ORIGEN_DESTINO", "Clase 9 incluida como gasto adicional (duplicidad en resultados)", "clase9_en_resultados", "ALTO", 4, True),
    R("ODE-09", "ORIGEN_DESTINO", "Configuración de distribución distinta a la aprobada", "distribucion_aprobada", "MEDIO", 3, True),
    # ---- parametrización
    R("PAR-01", "PARAMETRIZACION", "Cuentas con naturaleza incorrecta", "naturaleza", "MEDIO", 4, True),
    R("PAR-02", "PARAMETRIZACION", "Cuentas en rubros financieros incorrectos", "rubros", "MEDIO", 4, True, p={"caso": "RUBRO_INCORRECTO"}),
    R("PAR-03", "PARAMETRIZACION", "Cuentas de balance presentadas como resultados", "rubros", "ALTO", 4, True, p={"caso": "BALANCE_EN_RESULTADOS"}),
    R("PAR-04", "PARAMETRIZACION", "Cuentas de resultados presentadas como balance", "rubros", "ALTO", 4, True, p={"caso": "RESULTADOS_EN_BALANCE"}),
    R("PAR-05", "PARAMETRIZACION", "Duplicidad en agrupaciones financieras", "rubros", "ALTO", 4, True, p={"caso": "DUPLICIDAD"}),
    R("PAR-06", "PARAMETRIZACION", "Cambios de configuración sin sustento", "cambios_sin_sustento", "MEDIO", 3),
    R("PAR-07", "PARAMETRIZACION", "Diferencias respecto de las políticas aprobadas", "politicas", "MEDIO", 4, True),
    R("PAR-08", "PARAMETRIZACION", "Cuentas con saldo omitidas en reportes", "rubros", "ALTO", 4, True, p={"caso": "OMITIDAS"}),
    R("PAR-09", "PARAMETRIZACION", "Cuentas incluidas más de una vez en reportes", "rubros", "ALTO", 4, True, p={"caso": "INCLUIDA_DOS_VECES"}),
    # ---- ingresos
    R("ING-01", "INGRESOS", "Facturas emitidas no contabilizadas", "conciliacion_memoria", "ALTO", 4, p={"tipo": "VENTAS", "subtipos": ["VENTA_NO_CONTABILIZADA"]}),
    R("ING-02", "INGRESOS", "Ingresos duplicados potenciales", "dup_cuenta", "ALTO", 3, cuentas=["70"]),
    R("ING-03", "INGRESOS", "Ingresos en periodos distintos al comprobante", "gastos_fuera_periodo", "MEDIO", 3, cuentas=["70"], p={"meses": 0}),
    R("ING-04", "INGRESOS", "Notas de crédito no relacionadas", "conciliacion_memoria", "MEDIO", 3, p={"tipo": "VENTAS", "subtipos": ["NC_NO_RELACIONADA"]}),
    R("ING-05", "INGRESOS", "Diferencias entre facturación y contabilidad", "conciliacion_memoria", "MEDIO", 3,
      p={"tipo": "VENTAS", "subtipos": ["DIFERENCIA_IGV", "DIFERENCIA_BASE", "DIFERENCIA_IMPORTE", "CONTABILIZADA_SIN_REGISTRO", "INGRESO_SIN_COMPROBANTE"]},
      descripcion="Un ingreso devengado pendiente de facturación no es un error por sí mismo (NIIF 15)."),
    R("ING-06", "INGRESOS", "Valorizaciones frente a ingresos reconocidos", "valorizaciones", "MEDIO", 3, p={"tolerancia_pct": 5}),
    R("ING-07", "INGRESOS", "Anticipos registrados como ingresos", "anticipos_como_ingreso", "MEDIO", 3, cuentas=["70"]),
    R("ING-08", "INGRESOS", "Variaciones significativas de ingresos", "variaciones", "BAJO", 2, cuentas=["70"], p={"porcentaje": 50, "importe_minimo": "5000"}),
    R("ING-09", "INGRESOS", "Concentración de ingresos por cliente", "concentracion_flujo", "BAJO", 2, cuentas=["70"], p={"porcentaje": 50}),
    # ---- servicios en proceso
    R("SPR-01", "SERVICIOS", "Servicios culminados con costos pendientes de evaluación", "servicios", "ALTO", 4, p={"caso": "CULMINADO"},
      criterio="NIIF 15 y NIC 2; la fecha de facturación no es el único criterio de reconocimiento."),
    R("SPR-02", "SERVICIOS", "Costos de ejercicios anteriores sin movimiento", "servicios", "MEDIO", 3, p={"caso": "ANTERIORES", "dias": 180}),
    R("SPR-03", "SERVICIOS", "Costos sin proyecto asignado", "servicios", "MEDIO", 3, p={"caso": "SIN_PROYECTO"}),
    R("SPR-04", "SERVICIOS", "Costos de proyectos suspendidos", "servicios", "MEDIO", 3, p={"caso": "SUSPENDIDO"}),
    R("SPR-05", "SERVICIOS", "Costos sin sustento disponible", "servicios", "MEDIO", 3, p={"caso": "SIN_SUSTENTO"}),
    R("SPR-06", "SERVICIOS", "Transferencias de costos inconsistentes", "servicios", "MEDIO", 3, p={"caso": "TRANSFERENCIAS"}),
    R("SPR-07", "SERVICIOS", "Avance operativo frente al reconocimiento contable", "servicios", "MEDIO", 2, p={"caso": "AVANCE", "tolerancia_pct": 10}),
    R("SPR-08", "SERVICIOS", "Posibles activos mantenidos indebidamente", "servicios", "ALTO", 3, p={"caso": "FACTURADO"}),
    # ---- activos
    R("ACT-01", "ACTIVOS", "Activos sin código", "activos", "BAJO", 3, p={"caso": "SIN_CODIGO"}),
    R("ACT-02", "ACTIVOS", "Activos sin fecha disponible para su uso", "activos", "BAJO", 3, p={"caso": "SIN_FECHA_USO"}),
    R("ACT-03", "ACTIVOS", "Activos sin depreciación cuando corresponde", "activos", "MEDIO", 3, p={"caso": "SIN_DEPRECIACION"}),
    R("ACT-04", "ACTIVOS", "Depreciación superior al importe depreciable", "activos", "ALTO", 4, True, p={"caso": "DEPRECIACION_EXCEDE"},
      criterio="NIC 16: la depreciación no excede el importe depreciable."),
    R("ACT-05", "ACTIVOS", "Depreciación posterior a una baja", "activos", "ALTO", 4, True, p={"caso": "POSTERIOR_BAJA"}),
    R("ACT-06", "ACTIVOS", "Diferencias entre auxiliar y contabilidad", "activos", "MEDIO", 4, p={"caso": "DIFERENCIAS"}),
    R("ACT-07", "ACTIVOS", "Bajas no registradas", "activos", "ALTO", 4, p={"caso": "BAJA"}),
    R("ACT-08", "ACTIVOS", "Activos totalmente depreciados en uso", "activos", "INFORMATIVO", 2, p={"caso": "TOTALMENTE_DEPRECIADO"},
      recomendacion="Revise la vida útil; no se recomienda la baja automática."),
    R("ACT-09", "ACTIVOS", "Depreciación financiera frente a tributaria", "activos", "INFORMATIVO", 2, p={"caso": "FINANCIERA_TRIBUTARIA"},
      descripcion="Las tasas tributarias no son criterio de depreciación financiera."),
    R("ACT-10", "ACTIVOS", "Mantenimiento capitalizado que requiere evaluación", "palabras", "MEDIO", 2, cuentas=["33"],
      p={"palabras": ["MANTENIMIENTO", "REPARACION", "SERVICIO TECNICO"], "titulo": "Mantenimiento capitalizado que requiere evaluación",
         "regularizacion": "REQUIERE_RECLASIFICACION"}),
    # ---- inventarios
    R("INV-01", "INVENTARIOS", "Existencias negativas", "inventarios", "ALTO", 4, True, p={"caso": "NEGATIVAS"}),
    R("INV-02", "INVENTARIOS", "Diferencias de valorización", "inventarios", "MEDIO", 3, p={"caso": "VALORIZACION"}),
    R("INV-03", "INVENTARIOS", "Movimientos duplicados", "inventarios", "MEDIO", 3, p={"caso": "DUPLICADOS"}),
    R("INV-04", "INVENTARIOS", "Inventarios sin movimiento (posible obsolescencia)", "inventarios", "MEDIO", 2, p={"caso": "SIN_MOVIMIENTO", "dias": 365}),
    R("INV-05", "INVENTARIOS", "Diferencias entre kardex y balance", "inventarios", "ALTO", 4, p={"caso": "KARDEX_BALANCE"}),
    R("INV-06", "INVENTARIOS", "Inventario valorizado fuera del periodo", "inventarios", "BAJO", 2, p={"caso": "FUERA_PERIODO"}),
    R("INV-07", "INVENTARIOS", "Costos unitarios atípicos", "inventarios", "BAJO", 2, p={"caso": "COSTO_ATIPICO"}),
    R("INV-08", "INVENTARIOS", "Diferencias de costo entre almacenes", "inventarios", "BAJO", 2, p={"caso": "ALMACENES", "porcentaje": 20}),
    # ---- planillas
    R("PLA-01", "PLANILLAS", "Diferencias entre planilla y contabilidad", "conciliacion_memoria", "ALTO", 4, p={"tipo": "PLANILLAS"}),
    R("PLA-02", "PLANILLAS", "Pagos de planilla duplicados", "pagos_planilla", "ALTO", 4),
    R("PLA-03", "PLANILLAS", "Provisiones de beneficios pendientes", "planilla_libro", "MEDIO", 3, cuentas=["4114", "4115", "4151"],
      p={"dias": 180, "titulo": "Beneficio social pendiente de evaluación"}),
    R("PLA-04", "PLANILLAS", "Retenciones judiciales pendientes de evaluación", "planilla_libro", "MEDIO", 3, cuentas=["41", "46"],
      p={"dias": 30, "palabras": ["JUDICIAL", "ALIMENT"], "titulo": "Retención judicial pendiente de entrega o evaluación"}),
    R("PLA-05", "PLANILLAS", "Remuneraciones pendientes antiguas por trabajador", "planilla_libro", "MEDIO", 3, cuentas=["411"],
      p={"dias": 60, "titulo": "Remuneración pendiente antigua"}),
    R("PLA-06", "PLANILLAS", "Liquidaciones pendientes", "planilla_libro", "MEDIO", 3, cuentas=["41"],
      p={"dias": 30, "palabras": ["LIQUIDACION"], "titulo": "Liquidación pendiente de pago"}),
    R("PLA-07", "PLANILLAS", "Aportes retenidos pendientes de entrega", "planilla_libro", "MEDIO", 3, cuentas=["403", "407"],
      p={"dias": 60, "titulo": "Aporte retenido pendiente de entrega"}),
    # ---- tributaria
    R("TRI-01", "TRIBUTARIA", "Diferencias entre registro de compras y contabilidad", "conciliacion_memoria", "MEDIO", 3,
      p={"tipo": "COMPRAS", "subtipos": ["DIFERENCIA_IGV", "DIFERENCIA_BASE", "DIFERENCIA_IMPORTE", "CONTABILIZADA_SIN_REGISTRO", "ERROR_PERIODO"]}),
    R("TRI-02", "TRIBUTARIA", "Crédito fiscal pendiente de evaluación", "credito_fiscal", "MEDIO", 3),
    R("TRI-03", "TRIBUTARIA", "Detracciones pendientes de identificación", "detracciones_pendientes", "MEDIO", 3),
    R("TRI-04", "TRIBUTARIA", "Retenciones y percepciones pendientes de sustento", "retenciones_sustento", "MEDIO", 3),
    R("TRI-05", "TRIBUTARIA", "Diferencias entre declaraciones importadas y registros", "conciliacion_memoria", "MEDIO", 3, p={"tipo": "TRIBUTOS"}),
    R("TRI-06", "TRIBUTARIA", "Operaciones que requieren evaluar medios de pago (bancarización)", "bancarizacion", "MEDIO", 3, normativa=True,
      descripcion="Requiere norma validada con el umbral vigente (parámetros umbral_pen / umbral_usd)."),
    R("TRI-07", "TRIBUTARIA", "Gastos potencialmente sujetos a reparo tributario", "reparos", "MEDIO", 3, normativa=True,
      descripcion="Requiere norma validada con las cuentas o conceptos sujetos."),
    R("TRI-08", "TRIBUTARIA", "Diferencias de periodo tributario (anotación de comprobantes)", "periodo_tributario", "MEDIO", 3, normativa=True,
      descripcion="Requiere norma validada con el plazo de anotación (parámetro plazo_meses)."),
    R("TRI-09", "TRIBUTARIA", "Gastos sujetos a límites tributarios", "limites", "MEDIO", 3, normativa=True,
      descripcion="Requiere norma validada con las cuentas y el límite (limite_importe o limite_pct_ingresos)."),
    R("TRI-10", "TRIBUTARIA", "Recibos por honorarios sin retención de cuarta categoría", "cuarta", "MEDIO", 3, normativa=True,
      descripcion="Requiere norma validada con el umbral de retención (parámetro umbral)."),
    # ---- devengos y corte
    R("DEV-01", "DEVENGOS", "Gastos anticipados no devengados correctamente", "gastos_anticipados", "MEDIO", 3),
    R("DEV-02", "DEVENGOS", "Gastos reconocidos anticipadamente", "palabras", "MEDIO", 2, cuentas=["6"],
      p={"palabras": ["ANUAL", "ADELANTADO", "POR ADELANTADO", "PRIMA ANUAL", "ALQUILER ANUAL", "SUSCRIPCION ANUAL"], "importe_minimo": "1000",
         "titulo": "Gasto posiblemente reconocido anticipadamente", "tributario": "POSIBLE_DIFERENCIA_TEMPORAL"}),
    R("DEV-03", "DEVENGOS", "Servicios recibidos pendientes de registro (corte)", "corte_posterior", "MEDIO", 3, cuentas=["42", "46"], p={"lado": "H"},
      descripcion="Movimientos posteriores al corte como evidencia complementaria."),
    R("DEV-04", "DEVENGOS", "Ingresos registrados en periodos incorrectos", "corte_posterior", "MEDIO", 3, cuentas=["70"], p={"lado": "H"}),
    R("DEV-05", "DEVENGOS", "Ingresos con comprobante posterior al corte", "ingresos_anticipados", "MEDIO", 3, cuentas=["70"]),
    R("DEV-06", "DEVENGOS", "Provisiones duplicadas", "dup_documentos", "ALTO", 4, p={"clase": "PROVISIONES"}),
    R("DEV-07", "DEVENGOS", "Provisiones antiguas pendientes de revisión", "provisiones_antiguas", "MEDIO", 3, cuentas=["48"], p={"meses": 6}),
    R("DEV-08", "DEVENGOS", "Intereses pendientes de registro", "conciliacion_memoria", "MEDIO", 3,
      p={"tipo": "FINANCIERAS", "subtipos": ["INTERESES_PENDIENTES_REGISTRO"]}),
    # ---- estadística
    R("EST-01", "ESTADISTICA", "Importes atípicos por cuenta (rango intercuartílico)", "atipicos", "INFORMATIVO", 2, p={"k": 3, "min_lineas": 12}),
    R("EST-02", "ESTADISTICA", "Frecuencia atípica de operaciones", "frecuencia", "INFORMATIVO", 2, p={"z": 3}),
    R("EST-03", "ESTADISTICA", "Comparación de gastos por centro de costo", "dimensiones", "INFORMATIVO", 2, p={"dimension": "cc"}),
    R("EST-04", "ESTADISTICA", "Comparación de gastos por proyecto", "dimensiones", "INFORMATIVO", 2, p={"dimension": "proyecto"}),
    R("EST-05", "ESTADISTICA", "Proporción de importes redondos", "redondos", "INFORMATIVO", 2, p={"multiplo": "1000", "porcentaje": 30}),
    R("EST-06", "ESTADISTICA", "Operaciones cercanas a límites configurados", "cerca_de_limites", "BAJO", 2, p={"limites": [], "margen_pct": 5}),
    R("EST-07", "ESTADISTICA", "Ley de Benford (exploratoria)", "benford", "INFORMATIVO", 1, p={"min_poblacion": 500, "importe_minimo": "10"}),
]


def sembrar(db) -> None:
    cats = {c.codigo: c for c in db.scalars(select(CategoriaRegla))}
    for i, (codigo, nombre, desc) in enumerate(CATEGORIAS):
        if codigo not in cats:
            cats[codigo] = CategoriaRegla(codigo=codigo, nombre=nombre, descripcion=desc, orden=i)
            db.add(cats[codigo])
    db.flush()
    existentes = {r.codigo: r for r in db.scalars(select(ReglaAuditoria).where(ReglaAuditoria.empresa_id.is_(None)))}
    for x in REGLAS:
        r = existentes.get(x["codigo"])
        if r:
            continue
        db.add(ReglaAuditoria(empresa_id=None, categoria_id=cats[x["modulo"]].id, codigo=x["codigo"], nombre=x["nombre"], descripcion=x["descripcion"],
                              origen="SISTEMA", evaluador=x["evaluador"], cuentas=x["cuentas"], parametros=json.dumps(x["parametros"], ensure_ascii=False),
                              riesgo=x["riesgo"], probabilidad=x["probabilidad"], estructural=x["estructural"], criterio=x["criterio"],
                              recomendacion=x["recomendacion"], normativa=x["normativa"], evidencia_requerida=x["evidencia_requerida"],
                              estado_validacion="PENDIENTE" if x["normativa"] else "NO_REQUIERE", activa=True, version=VERSION))
    db.flush()


def modulo_de(db, r) -> str:
    return db.get(CategoriaRegla, r.categoria_id).codigo
