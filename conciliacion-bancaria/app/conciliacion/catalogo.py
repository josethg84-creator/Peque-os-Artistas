"""Catálogo de tipos de conciliación y plantillas del sistema.

Una plantilla describe: las fuentes (A, B y opcionalmente C), su rol (contable, externa o auxiliar interno),
las pasadas de comparación (pares de fuentes, modo PARTIDAS o AGREGADO, convención de signo), las reglas
ordenadas por prioridad, la tolerancia por defecto, las claves de duplicados y los criterios de aprobación.
Las reglas se guardan en `reconciliation_rules`; la empresa puede duplicar y personalizar cualquier plantilla.
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlantillaConciliacion, ReglaConciliacion, TipoConciliacion

VERSION_CATALOGO = 2

TIPOS = [
    # código, nombre, categoría, roles adicionales, datos personales, descripción
    ("BANCARIA", "Conciliación bancaria", "TESORERIA", "TESORERO", False,
     "Estado de cuenta bancario (fase 1) contra los movimientos de la cuenta 10 del libro."),
    ("COMPRAS", "Registro de compras vs contabilidad", "TRIBUTARIA", "", False,
     "Registro auxiliar de compras contra la provisión contable (42, 40 y cuentas de destino)."),
    ("VENTAS", "Registro de ventas vs contabilidad", "TRIBUTARIA", "", False,
     "Registro auxiliar de ventas contra la contabilidad (12, 40 y 70)."),
    ("PLANILLAS", "Planillas vs contabilidad", "LABORAL", "PLANILLAS", True,
     "Planilla procesada contra las cuentas 14, 40, 41, 46 y 62, por trabajador, concepto y centro de costo."),
    ("ACTIVOS_FIJOS", "Activos fijos vs contabilidad", "ACTIVOS", "", False,
     "Registro de activos (fase 5) contra las cuentas 33, 34, 39 y 68."),
    ("INVENTARIOS", "Kardex valorizado vs existencias", "COSTOS", "", False,
     "Kardex valorizado contra las cuentas 20 a 28 (cantidades y valores por separado)."),
    ("SERVICIOS_PROCESO", "Costos por proyecto vs contabilidad", "COSTOS", "", False,
     "Reporte operativo de costos contra la clase 6 por proyecto y la cuenta 23."),
    ("FINANCIERAS", "Obligaciones financieras", "TESORERIA", "TESORERO", False,
     "Cronogramas de préstamos y arrendamientos contra la cuenta 45 y los intereses (67)."),
    ("DETRACCIONES", "Detracciones", "TRIBUTARIA", "TESORERO", False,
     "Documentos sujetos, constancias de depósito y registros contables."),
    ("RETENCIONES", "Retenciones y percepciones", "TRIBUTARIA", "", False,
     "Comprobantes de retención y percepción contra la cuenta 40."),
    ("TRIBUTOS", "Tributos y aportes", "TRIBUTARIA", "PLANILLAS", False,
     "Declaraciones y constancias de pago contra la cuenta 40 por tributo y periodo."),
    ("INTERCOMPANIA", "Empresas relacionadas", "GRUPO", "", False,
     "Operaciones recíprocas entre empresas autorizadas del mismo grupo económico."),
    ("ORIGEN_DESTINO", "Origen y destino de gastos", "COSTOS", "", False,
     "Distribución de la clase 6 hacia la clase 9 con la contrapartida 79 (y 78)."),
    ("AUXILIAR_MAYOR", "Auxiliares y anexos vs mayor", "CIERRE", "", False,
     "Saldos de anexos (fase 5) y auxiliares contra el mayor y el balance de comprobación."),
    ("PERSONALIZADA", "Conciliación personalizada", "OTRAS", "", False,
     "Definida por el contador con el diseñador (fuentes, homologación, reglas y tolerancias)."),
]


def _r(codigo, descripcion, tipo, pasada=0, **parametros):
    return {"codigo": codigo, "descripcion": descripcion, "tipo": tipo, "pasada": pasada, "parametros": parametros}


DOC = ["tercero", "tipo_documento", "serie", "numero"]
CAMPOS_ACTIVO = [{"nombre": "Costo", "campo": "costo", "subtipo": "DIFERENCIA_COSTO"},
                 {"nombre": "Depreciación acumulada", "campo": "dep_acumulada", "subtipo": "DIFERENCIA_DEPRECIACION"},
                 {"nombre": "Depreciación del periodo", "campo": "dep_periodo", "subtipo": "DIFERENCIA_DEPRECIACION"}]
PLANTILLAS = {
    "BANCARIA": {
        "fuentes": {"A": {"tipo": "LIBRO", "rol": "CONTABLE", "nombre": "Libro — cuenta 10", "parametros": {"por_cuenta_bancaria": True}},
                    "B": {"tipo": "BANCO", "rol": "EXTERNA", "nombre": "Estado de cuenta bancario", "parametros": {}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}],
        "duplicados": {"A": [["operacion", "importe", "fecha"], ["descripcion", "importe", "fecha", "referencia"]],
                       "B": [["operacion", "importe", "fecha"]]},
        "tolerancia": {"importe_absoluto": "0.00", "porcentaje": None, "dias": 3},
        "confirmar_automaticamente": ["EXACTA", "TOLERANCIA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("OPERACION", "Mismo número de operación", "CLAVE", campos=["operacion"], fecha_dias=5),
                   _r("IMPORTE_FECHA", "Mismo importe y fecha cercana", "IMPORTE_FECHA"),
                   _r("COMBINACION", "Depósitos o cargos agrupados", "COMBINACION", max_elementos=4, dias=5)],
    },
    "COMPRAS": {
        "fuentes": {"A": {"tipo": "REGISTRO", "rol": "EXTERNA", "nombre": "Registro de compras", "parametros": {"registro": "COMPRAS"}},
                    "B": {"tipo": "LIBRO_DOCUMENTOS", "rol": "CONTABLE", "nombre": "Provisiones contables",
                          "parametros": {"cuentas_documento": ["42", "43", "46", "47"], "lado_documento": "H", "cuentas_igv": ["4011"]}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}],
        "duplicados": {"A": [DOC], "B": [DOC]},
        "tolerancia": {"importe_absoluto": "0.05", "porcentaje": None, "dias": 0},
        "confirmar_automaticamente": ["EXACTA", "TOLERANCIA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "cuentas_destino_admitidas": ["60", "61", "62", "63", "64", "65", "66", "67", "68", "2", "3", "18", "16", "14", "42", "43", "46"],
        "reglas": [_r("DOCUMENTO", "Mismo proveedor y comprobante", "CLAVE", campos=DOC,
                      comparar=[["igv", "igv", "IGV", "DIFERENCIA_IGV"], ["base", "base", "Base imponible", "DIFERENCIA_BASE"]])],
    },
    "VENTAS": {
        "fuentes": {"A": {"tipo": "REGISTRO", "rol": "EXTERNA", "nombre": "Registro de ventas", "parametros": {"registro": "VENTAS"}},
                    "B": {"tipo": "LIBRO_DOCUMENTOS", "rol": "CONTABLE", "nombre": "Contabilidad (12, 40, 70)",
                          "parametros": {"cuentas_documento": ["12", "13", "16"], "lado_documento": "D", "cuentas_igv": ["4011"],
                                         "cuentas_ingreso": ["70", "75", "77"]}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}],
        "duplicados": {"A": [DOC], "B": [DOC]},
        "tolerancia": {"importe_absoluto": "0.05", "porcentaje": None, "dias": 0},
        "confirmar_automaticamente": ["EXACTA", "TOLERANCIA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("DOCUMENTO", "Mismo cliente y comprobante", "CLAVE", campos=["tipo_documento", "serie", "numero"],
                      comparar=[["igv", "igv", "IGV", "DIFERENCIA_IGV"], ["base", "base", "Base imponible", "DIFERENCIA_BASE"]])],
    },
    "PLANILLAS": {
        "fuentes": {"A": {"tipo": "ARCHIVO", "rol": "EXTERNA", "nombre": "Planilla procesada", "esquema": "CONC_PLANILLA", "parametros": {}},
                    "B": {"tipo": "PLANILLA_LIBRO", "rol": "CONTABLE", "nombre": "Contabilidad (14, 40, 41, 46, 62)", "parametros": {}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "AGREGADO", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "0.00", "porcentaje": None, "dias": 0},
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        # concepto de planilla → cuenta, lado y nivel de comparación
        "conceptos": [
            {"grupo": "NETO", "nombre": "Remuneración neta por pagar", "conceptos": ["NETO", "NETO A PAGAR"], "cuenta": "411", "lado": "H",
             "por": "trabajador", "subtipo": "DIFERENCIA_NETO"},
            {"grupo": "CTS", "nombre": "CTS", "conceptos": ["CTS"], "cuenta": "4151", "lado": "H", "por": "trabajador", "subtipo": "DIFERENCIA_PROVISION"},
            {"grupo": "GRATIFICACION", "nombre": "Gratificaciones", "conceptos": ["GRATIFICACION"], "cuenta": "4114", "lado": "H",
             "por": "trabajador", "subtipo": "DIFERENCIA_PROVISION"},
            {"grupo": "VACACIONES", "nombre": "Vacaciones", "conceptos": ["VACACIONES"], "cuenta": "4115", "lado": "H", "por": "trabajador",
             "subtipo": "DIFERENCIA_PROVISION"},
            {"grupo": "AFP", "nombre": "Aportes AFP del trabajador", "conceptos": ["AFP"], "cuenta": "407", "lado": "H", "por": "total",
             "subtipo": "DIFERENCIA_APORTES"},
            {"grupo": "ONP", "nombre": "Aportes ONP", "conceptos": ["ONP"], "cuenta": "4032", "lado": "H", "por": "total", "subtipo": "DIFERENCIA_APORTES"},
            {"grupo": "ESSALUD", "nombre": "EsSalud (empleador)", "conceptos": ["ESSALUD"], "cuenta": "4031", "lado": "H", "por": "total",
             "subtipo": "DIFERENCIA_APORTES"},
            {"grupo": "QUINTA", "nombre": "Retenciones de quinta categoría", "conceptos": ["QUINTA", "RENTA QUINTA"], "cuenta": "40174", "lado": "H",
             "por": "total", "subtipo": "DIFERENCIA_RETENCIONES"},
            {"grupo": "PRESTAMO", "nombre": "Descuento de préstamos", "conceptos": ["PRESTAMO"], "cuenta": "1411", "lado": "H", "por": "trabajador",
             "subtipo": "DESCUENTO_NO_REGISTRADO"},
            {"grupo": "ADELANTO", "nombre": "Descuento de adelantos", "conceptos": ["ADELANTO"], "cuenta": "1412", "lado": "H", "por": "trabajador",
             "subtipo": "DESCUENTO_NO_REGISTRADO"},
            {"grupo": "JUDICIAL", "nombre": "Descuentos judiciales", "conceptos": ["JUDICIAL", "RETENCION JUDICIAL"], "cuenta": "46", "lado": "H",
             "por": "trabajador", "subtipo": "DESCUENTO_NO_REGISTRADO"},
            {"grupo": "GASTO", "nombre": "Costo de personal por centro de costo", "conceptos": ["REMUNERACION", "BASICO", "ASIGNACION FAMILIAR",
                                                                                                "HORAS EXTRAS", "ESSALUD", "CTS", "GRATIFICACION",
                                                                                                "VACACIONES"],
             "cuenta": "62", "lado": "D", "por": "centro_costo", "subtipo": "DIFERENCIA_DISTRIBUCION"},
        ],
        "reglas": [_r("CONCEPTO", "Por concepto y trabajador, centro de costo o total", "AGREGADO", claves=["concepto", "clave"],
                      campos=[{"nombre": "Importe", "campo": "importe", "subtipo": None}])],
    },
    "ACTIVOS_FIJOS": {
        "fuentes": {"A": {"tipo": "ACTIVOS_REGISTRO", "rol": "AUXILIAR_INTERNO", "nombre": "Registro de activos fijos", "parametros": {}},
                    "B": {"tipo": "ACTIVOS_LIBRO", "rol": "CONTABLE", "nombre": "Contabilidad (33, 34, 39, 68)",
                          "parametros": {"costo": ["33", "34"], "depreciacion": ["39"], "gasto": ["68"]}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "AGREGADO", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "1.00", "porcentaje": None, "dias": 0},
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("ACTIVO", "Por código de activo", "AGREGADO", claves=["clave"], campos=CAMPOS_ACTIVO),
                   _r("SIN_CODIGO", "Saldos contables sin código de activo contra el resto del registro", "AGREGADO", claves=["grupo"],
                      campos=CAMPOS_ACTIVO)],
    },
    "INVENTARIOS": {
        "fuentes": {"A": {"tipo": "ARCHIVO", "rol": "AUXILIAR_INTERNO", "nombre": "Kardex valorizado", "esquema": "CONC_KARDEX", "parametros": {}},
                    "B": {"tipo": "INVENTARIO_LIBRO", "rol": "CONTABLE", "nombre": "Existencias (20–28)",
                          "parametros": {"cuentas": ["20", "21", "22", "23", "24", "25", "26", "28"]}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "AGREGADO", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "1.00", "porcentaje": None, "dias": 0},
        "metodo_valorizacion": "PROMEDIO",
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("CUENTA", "Por cuenta de existencias", "AGREGADO", claves=["cuenta"],
                      campos=[{"nombre": "Valor inicial", "campo": "valor_inicial", "subtipo": "DIFERENCIA_CORTE"},
                              {"nombre": "Entradas", "campo": "valor_entradas", "subtipo": "MOVIMIENTO_NO_CONTABILIZADO"},
                              {"nombre": "Salidas", "campo": "valor_salidas", "subtipo": "MOVIMIENTO_NO_CONTABILIZADO"},
                              {"nombre": "Valor final", "campo": "valor_final", "subtipo": "DIFERENCIA_VALORIZACION"}])],
    },
    "SERVICIOS_PROCESO": {
        "fuentes": {"A": {"tipo": "ARCHIVO", "rol": "EXTERNA", "nombre": "Reporte de costos por proyecto", "esquema": "CONC_COSTOS", "parametros": {}},
                    "B": {"tipo": "COSTOS_LIBRO", "rol": "CONTABLE", "nombre": "Clase 6 por proyecto y cuenta 23",
                          "parametros": {"cuenta_proceso": "23"}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "AGREGADO", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "1.00", "porcentaje": None, "dias": 0},
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("PROYECTO_CONCEPTO", "Por proyecto y concepto de costo", "AGREGADO", claves=["proyecto", "concepto"],
                      campos=[{"nombre": "Costo", "campo": "importe", "subtipo": "DIFERENCIA_REPORTE_OPERATIVO"}])],
    },
    "FINANCIERAS": {
        "fuentes": {"A": {"tipo": "CUOTAS", "rol": "EXTERNA", "nombre": "Cronogramas financieros", "parametros": {}},
                    "B": {"tipo": "FINANCIERAS_LIBRO", "rol": "CONTABLE", "nombre": "Cuenta 45 e intereses (67)",
                          "parametros": {"cuentas": ["45"], "intereses": ["67"]}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}],
        "duplicados": {"B": [["contrato", "concepto", "importe", "fecha"]]},
        "tolerancia": {"importe_absoluto": "1.00", "porcentaje": None, "dias": 10},
        "confirmar_automaticamente": ["EXACTA", "TOLERANCIA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("CUOTA", "Contrato, concepto e importe de la cuota", "IMPORTE_FECHA", campos_extra=["contrato", "concepto"])],
    },
    "DETRACCIONES": {
        "fuentes": {"A": {"tipo": "DETRACCION_DOCUMENTOS", "rol": "EXTERNA", "nombre": "Comprobantes sujetos a detracción",
                          "parametros": {"registro": "COMPRAS"}},
                    "B": {"tipo": "ARCHIVO", "rol": "EXTERNA", "nombre": "Constancias de depósito", "esquema": "CONC_CONSTANCIAS", "parametros": {}},
                    "C": {"tipo": "CONSTANCIAS_LIBRO", "rol": "CONTABLE", "nombre": "Registro contable de detracciones", "parametros": {}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}, {"a": "B", "b": "C", "modo": "PARTIDAS", "signo": "IGUAL"}],
        "duplicados": {"B": [["operacion"]]},
        "tolerancia": {"importe_absoluto": "1.00", "porcentaje": None, "dias": 0},
        "confirmar_automaticamente": ["EXACTA", "TOLERANCIA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": False},
        "reglas": [_r("DOCUMENTO", "Documento de la constancia", "CLAVE", pasada=0, campos=["tercero", "serie", "numero"]),
                   _r("CONSTANCIA", "Número de constancia", "CLAVE", pasada=1, campos=["operacion"])],
    },
    "RETENCIONES": {
        "fuentes": {"A": {"tipo": "ARCHIVO", "rol": "EXTERNA", "nombre": "Comprobantes de retención y percepción", "esquema": "CONC_RETENCIONES",
                          "parametros": {}},
                    "B": {"tipo": "LIBRO", "rol": "CONTABLE", "nombre": "Cuenta 40 (retenciones y percepciones)",
                          "parametros": {"cuentas": ["40113", "40114", "40173", "40174"], "naturaleza": "A"}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}],
        "duplicados": {"A": [["serie", "numero"]]},
        "tolerancia": {"importe_absoluto": "0.05", "porcentaje": None, "dias": 31},
        "confirmar_automaticamente": ["EXACTA", "TOLERANCIA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("COMPROBANTE", "Número de comprobante", "CLAVE", campos=["serie", "numero"]),
                   _r("TERCERO_IMPORTE", "Tercero e importe", "IMPORTE_FECHA", campos_extra=["tercero"])],
    },
    "TRIBUTOS": {
        "fuentes": {"A": {"tipo": "ARCHIVO", "rol": "EXTERNA", "nombre": "Declaraciones y constancias", "esquema": "CONC_DECLARACIONES", "parametros": {}},
                    "B": {"tipo": "TRIBUTOS_LIBRO", "rol": "CONTABLE", "nombre": "Cuenta 40 por tributo y periodo", "parametros": {}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "AGREGADO", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "1.00", "porcentaje": None, "dias": 0},
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("TRIBUTO_PERIODO", "Por tributo y periodo tributario", "AGREGADO", claves=["concepto", "periodo"],
                      campos=[{"nombre": "Obligación", "campo": "obligacion", "subtipo": "DIFERENCIA_OBLIGACION"},
                              {"nombre": "Pagos", "campo": "pagos", "subtipo": "DIFERENCIA_PAGOS"},
                              {"nombre": "Créditos", "campo": "creditos", "subtipo": "DIFERENCIA_CREDITOS"}])],
    },
    "INTERCOMPANIA": {
        "fuentes": {"A": {"tipo": "LIBRO", "rol": "CONTABLE", "nombre": "Empresa — operaciones con la relacionada",
                          "parametros": {"cuentas": ["13", "17", "43", "47", "16", "46", "42", "12"], "tercero_relacionada": True}},
                    "B": {"tipo": "EMPRESA_RELACIONADA", "rol": "EXTERNA", "nombre": "Empresa relacionada — operaciones recíprocas",
                          "parametros": {"cuentas": ["13", "17", "43", "47", "16", "46", "42", "12"]}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "OPUESTO"}],
        "tolerancia": {"importe_absoluto": "0.00", "porcentaje": None, "dias": 31},
        "confirmar_automaticamente": ["EXACTA", "TOLERANCIA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("DOCUMENTO", "Mismo comprobante", "CLAVE", campos=["serie", "numero"], fecha_dias=31),
                   _r("IMPORTE_FECHA", "Importe y fecha", "IMPORTE_FECHA")],
    },
    "ORIGEN_DESTINO": {
        "fuentes": {"A": {"tipo": "DESTINO_ORIGEN", "rol": "CONTABLE", "nombre": "Gastos por naturaleza destinables (clase 6)", "parametros": {}},
                    "B": {"tipo": "DESTINO_DESTINO", "rol": "CONTABLE", "nombre": "Destino (clase 9)", "parametros": {}},
                    "C": {"tipo": "DESTINO_TRANSFERENCIA", "rol": "CONTABLE", "nombre": "Cargas imputables (79)", "parametros": {}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "AGREGADO", "signo": "IGUAL"}, {"a": "B", "b": "C", "modo": "AGREGADO", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "0.01", "porcentaje": None, "dias": 0},
        "destinos_autorizados": ["9"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": False},
        "reglas": [_r("ASIENTO", "Origen y destino por asiento", "AGREGADO", pasada=0, claves=["referencia"],
                      campos=[{"nombre": "Origen vs destino", "campo": "importe", "subtipo": "DISTRIBUCION"}]),
                   _r("TRANSFERENCIA", "Destino vs 79 por asiento", "AGREGADO", pasada=1, claves=["referencia"],
                      campos=[{"nombre": "Destino vs 79", "campo": "importe", "subtipo": "CONTRAPARTIDA_79"}])],
    },
    "AUXILIAR_MAYOR": {
        "fuentes": {"A": {"tipo": "ANEXO", "rol": "AUXILIAR_INTERNO", "nombre": "Anexos (fase 5)", "parametros": {}},
                    "B": {"tipo": "MAYOR", "rol": "CONTABLE", "nombre": "Libro mayor", "parametros": {}},
                    "C": {"tipo": "BALANCE_IMPORTADO", "rol": "EXTERNA", "nombre": "Balance de comprobación importado", "parametros": {}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "AGREGADO", "signo": "IGUAL"}, {"a": "B", "b": "C", "modo": "AGREGADO", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "0.00", "porcentaje": None, "dias": 0},
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": False},
        "reglas": [_r("CUENTA", "Anexo vs mayor por cuenta", "AGREGADO", pasada=0, claves=["cuenta"],
                      campos=[{"nombre": "Saldo", "campo": "importe", "subtipo": "AUXILIAR_VS_MAYOR"}]),
                   _r("BALANCE", "Mayor vs balance importado", "AGREGADO", pasada=1, claves=["cuenta"],
                      campos=[{"nombre": "Saldo", "campo": "importe", "subtipo": "MAYOR_VS_BALANCE"}])],
    },
    "PERSONALIZADA": {
        "fuentes": {"A": {"tipo": "LIBRO", "rol": "CONTABLE", "nombre": "Libro", "parametros": {"cuentas": []}},
                    "B": {"tipo": "ARCHIVO", "rol": "EXTERNA", "nombre": "Fuente externa", "esquema": "CONC_GENERICO", "parametros": {}}},
        "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}],
        "tolerancia": {"importe_absoluto": "0.00", "porcentaje": None, "dias": 3},
        "confirmar_automaticamente": ["EXACTA"],
        "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": True},
        "reglas": [_r("DOCUMENTO", "Documento", "CLAVE", campos=["serie", "numero"]),
                   _r("IMPORTE_FECHA", "Importe y fecha", "IMPORTE_FECHA")],
    },
}


def sembrar(db: Session) -> None:
    """Crea o actualiza los tipos y las plantillas del sistema. Idempotente."""
    tipos = {t.codigo: t for t in db.scalars(select(TipoConciliacion))}
    cambios = False
    for codigo, nombre, cat, roles, personal, desc in TIPOS:
        t = tipos.get(codigo)
        if t and t.version >= VERSION_CATALOGO:
            continue
        t = t or TipoConciliacion(codigo=codigo)
        t.nombre, t.categoria, t.roles_operacion, t.datos_personales, t.descripcion = nombre, cat, roles, personal, desc
        t.especializado, t.version = codigo != "PERSONALIZADA", VERSION_CATALOGO
        db.add(t)
        cambios = True
    plantillas = {p.codigo: p for p in db.scalars(select(PlantillaConciliacion).where(PlantillaConciliacion.empresa_id.is_(None)))}
    for codigo, cfg in PLANTILLAS.items():
        p = plantillas.get(codigo)
        if p and p.version >= VERSION_CATALOGO:
            continue
        p = p or PlantillaConciliacion(empresa_id=None, codigo=codigo)
        nombre = next(t[1] for t in TIPOS if t[0] == codigo)
        p.tipo_codigo, p.nombre, p.version, p.autorizada, p.autorizada_por = codigo, nombre, VERSION_CATALOGO, True, "catálogo del sistema"
        p.configuracion = json.dumps({k: v for k, v in cfg.items() if k != "reglas"}, ensure_ascii=False)
        db.add(p)
        db.flush()
        guardar_reglas(db, p, cfg["reglas"])
        cambios = True
    if cambios:
        db.commit()


def guardar_reglas(db: Session, p: PlantillaConciliacion, reglas: list[dict]) -> None:
    for r in db.scalars(select(ReglaConciliacion).where(ReglaConciliacion.plantilla_id == p.id)):
        db.delete(r)
    db.flush()
    for i, r in enumerate(reglas):
        db.add(ReglaConciliacion(plantilla_id=p.id, pasada=r.get("pasada", 0), orden=i, codigo=r["codigo"][:40],
                                 descripcion=r.get("descripcion") or r["codigo"], tipo=r["tipo"],
                                 parametros=json.dumps(r.get("parametros", {}), ensure_ascii=False), activa=r.get("activa", True)))
    db.flush()


def configuracion(db: Session, p: PlantillaConciliacion) -> dict:
    cfg = json.loads(p.configuracion)
    cfg["reglas"] = [{"codigo": r.codigo, "descripcion": r.descripcion, "tipo": r.tipo, "pasada": r.pasada, "orden": r.orden,
                      "parametros": json.loads(r.parametros or "{}"), "activa": r.activa}
                     for r in db.scalars(select(ReglaConciliacion).where(ReglaConciliacion.plantilla_id == p.id)
                                         .order_by(ReglaConciliacion.pasada, ReglaConciliacion.orden))]
    cfg["plantilla"] = {"id": p.id, "codigo": p.codigo, "nombre": p.nombre, "version": p.version, "tipo": p.tipo_codigo}
    return cfg
