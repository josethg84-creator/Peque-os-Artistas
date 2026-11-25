"""Estructura del Plan Contable General Empresarial (PCGE) y perfiles de análisis por cuenta.

Niveles por número de dígitos: 1 elemento · 2 cuenta · 3 subcuenta · 4 divisionaria ·
5 subdivisionaria · 6+ analítica (personalizada por la empresa).

Los nombres de las cuentas de 2 dígitos se usan solo cuando la empresa no importó su plan
de cuentas o no definió esa cuenta; el plan de la empresa siempre prevalece.
"""
from dataclasses import dataclass

NIVELES = {1: "Elemento", 2: "Cuenta", 3: "Subcuenta", 4: "Divisionaria", 5: "Subdivisionaria"}


def nombre_nivel(codigo: str) -> str:
    return NIVELES.get(len(codigo), "Analítica")


ELEMENTOS = {
    "0": "Cuentas de orden",
    "1": "Activo disponible y exigible",
    "2": "Activo realizable",
    "3": "Activo inmovilizado",
    "4": "Pasivo",
    "5": "Patrimonio neto",
    "6": "Gastos por naturaleza",
    "7": "Ingresos",
    "8": "Saldos intermediarios de gestión y determinación del resultado",
    "9": "Contabilidad analítica de explotación",
}

CUENTAS = {
    "10": "Efectivo y equivalentes de efectivo", "11": "Inversiones financieras",
    "12": "Cuentas por cobrar comerciales – terceros", "13": "Cuentas por cobrar comerciales – relacionadas",
    "14": "Cuentas por cobrar al personal, accionistas, directores y gerentes",
    "16": "Cuentas por cobrar diversas – terceros", "17": "Cuentas por cobrar diversas – relacionadas",
    "18": "Servicios y otros contratados por anticipado", "19": "Estimación de cuentas de cobranza dudosa",
    "20": "Mercaderías", "21": "Productos terminados", "22": "Subproductos, desechos y desperdicios",
    "23": "Productos en proceso", "24": "Materias primas", "25": "Materiales auxiliares, suministros y repuestos",
    "26": "Envases y embalajes", "27": "Activos no corrientes mantenidos para la venta",
    "28": "Inventarios por recibir", "29": "Desvalorización de inventarios",
    "30": "Inversiones mobiliarias", "31": "Propiedades de inversión", "32": "Activos por derecho de uso",
    "33": "Propiedades, planta y equipo", "34": "Intangibles", "35": "Activos biológicos",
    "36": "Desvalorización de activo inmovilizado", "37": "Activo diferido", "38": "Otros activos",
    "39": "Depreciación, amortización y agotamiento acumulados",
    "40": "Tributos, contraprestaciones y aportes al sistema de pensiones y de salud por pagar",
    "41": "Remuneraciones y participaciones por pagar", "42": "Cuentas por pagar comerciales – terceros",
    "43": "Cuentas por pagar comerciales – relacionadas",
    "44": "Cuentas por pagar a los accionistas, directores y gerentes", "45": "Obligaciones financieras",
    "46": "Cuentas por pagar diversas – terceros", "47": "Cuentas por pagar diversas – relacionadas",
    "48": "Provisiones", "49": "Pasivo diferido",
    "50": "Capital", "51": "Acciones de inversión", "52": "Capital adicional", "56": "Resultados no realizados",
    "57": "Excedente de revaluación", "58": "Reservas", "59": "Resultados acumulados",
    "60": "Compras", "61": "Variación de inventarios", "62": "Gastos de personal y directores",
    "63": "Gastos de servicios prestados por terceros", "64": "Gastos por tributos", "65": "Otros gastos de gestión",
    "66": "Pérdida por medición de activos no financieros al valor razonable", "67": "Gastos financieros",
    "68": "Valuación y deterioro de activos y provisiones", "69": "Costo de ventas",
    "70": "Ventas", "71": "Variación de la producción almacenada", "72": "Producción de activo inmovilizado",
    "73": "Descuentos, rebajas y bonificaciones obtenidos", "74": "Descuentos, rebajas y bonificaciones concedidos",
    "75": "Otros ingresos de gestión", "76": "Ganancia por medición de activos no financieros al valor razonable",
    "77": "Ingresos financieros", "78": "Cargas cubiertas por provisiones",
    "79": "Cargas imputables a cuentas de costos y gastos",
    "80": "Margen comercial", "81": "Producción del ejercicio", "82": "Valor agregado",
    "83": "Excedente bruto (insuficiencia bruta) de explotación", "84": "Resultado de explotación",
    "85": "Resultado antes de participaciones e impuestos", "87": "Participaciones de los trabajadores",
    "88": "Impuesto a la renta", "89": "Determinación del resultado del ejercicio",
}


def nombre_pcge(codigo: str) -> str | None:
    if len(codigo) == 1:
        return ELEMENTOS.get(codigo)
    if len(codigo) == 2:
        if codigo[0] == "9":
            return "Cuenta analítica de la empresa"
        if codigo[0] == "0":
            return "Cuenta de orden"
        return CUENTAS.get(codigo)
    return None


def naturaleza_pcge(cuenta: str) -> str | None:
    """D deudora, A acreedora, None indeterminada. 19/29/36/39 son correctoras (acreedoras)."""
    if not cuenta or not cuenta[0].isdigit():
        return None
    if cuenta[:2] in ("19", "29", "36", "39"):
        return "A"
    if cuenta[:2] in ("59", "79") or cuenta[0] in "08":
        return "A" if cuenta[:2] == "79" else None
    if cuenta[0] in "12369":
        return "D"
    if cuenta[0] in "457":
        return "A"
    return None


@dataclass(frozen=True)
class Perfil:
    clave: str
    nombre: str
    descripcion: str
    requiere_tercero: bool = False
    cartera: bool = False          # documentos con antigüedad (cobrar / pagar)
    transferencia: bool = False    # 78 / 79: no son ingresos económicos
    economico: str | None = None   # GASTO | INGRESO | None


PERFILES = {
    "DISPONIBLE": Perfil("DISPONIBLE", "Caja y bancos",
                         "Saldos acreedores en bancos (sobregiros), fondos restringidos y partidas pendientes."),
    "INVERSION_FIN": Perfil("INVERSION_FIN", "Inversiones financieras", "Valuación y vigencia de las inversiones."),
    "COBRAR": Perfil("COBRAR", "Cuentas por cobrar",
                     "Antigüedad de documentos, saldos contrarios por tercero (anticipos de clientes) y vencidos.",
                     requiere_tercero=True, cartera=True),
    "ANTICIPADO": Perfil("ANTICIPADO", "Gastos contratados por anticipado", "Devengo de servicios pagados por adelantado."),
    "ESTIMACION": Perfil("ESTIMACION", "Estimación de cobranza dudosa", "Cuenta correctora: saldo acreedor esperado."),
    "INVENTARIO": Perfil("INVENTARIO", "Existencias", "Saldos contrarios, existencias por recibir antiguas, desvalorización."),
    "EN_PROCESO": Perfil("EN_PROCESO", "Productos y servicios en proceso",
                         "Costos acumulados por proyecto/cliente, antigüedad, transferencias y culminación del servicio."),
    "DESVALORIZACION": Perfil("DESVALORIZACION", "Desvalorización", "Cuenta correctora: saldo acreedor esperado."),
    "INMOVILIZADO": Perfil("INMOVILIZADO", "Activo inmovilizado",
                           "Costo vs depreciación acumulada por activo, altas y bajas, deterioro."),
    "DEPRECIACION": Perfil("DEPRECIACION", "Depreciación y amortización acumulada",
                           "No debe exceder el costo del activo relacionado."),
    "DIFERIDO": Perfil("DIFERIDO", "Activo diferido", "Recuperabilidad y movimientos del periodo."),
    "TRIBUTOS": Perfil("TRIBUTOS", "Tributos por pagar",
                       "Saldos deudores (créditos tributarios) y obligaciones antiguas.", requiere_tercero=False),
    "REMUNERACIONES": Perfil("REMUNERACIONES", "Remuneraciones y beneficios", "Obligaciones laborales antiguas o contrarias."),
    "PAGAR": Perfil("PAGAR", "Cuentas por pagar",
                    "Obligaciones vencidas, anticipos a proveedores (saldo deudor), saldos antiguos y moneda extranjera.",
                    requiere_tercero=True, cartera=True),
    "FINANCIERA": Perfil("FINANCIERA", "Obligaciones financieras", "Vencimientos, moneda extranjera y saldos contrarios."),
    "PROVISION": Perfil("PROVISION", "Provisiones", "Aplicación de provisiones y relación con la cuenta 78."),
    "PASIVO_DIFERIDO": Perfil("PASIVO_DIFERIDO", "Pasivo diferido", "Reconocimiento de ingresos y tributos diferidos."),
    "PATRIMONIO": Perfil("PATRIMONIO", "Patrimonio neto",
                         "Movimientos inusuales que requieren acuerdo societario y diferencias entre ejercicios."),
    "GASTO": Perfil("GASTO", "Gastos por naturaleza",
                    "Por proveedor, documento, centro de costo, proyecto, maquinaria y periodo.", economico="GASTO"),
    "COSTO_VENTAS": Perfil("COSTO_VENTAS", "Costo de ventas", "Relación con ventas e inventarios.", economico="GASTO"),
    "INGRESO": Perfil("INGRESO", "Ingresos", "Ingresos económicos por cliente, documento y periodo.", economico="INGRESO"),
    "TRANSFERENCIA": Perfil("TRANSFERENCIA", "Cuentas de transferencia (78 / 79)",
                            "No son ingresos económicos: contrapartidas de provisiones aplicadas y de la distribución a destino.",
                            transferencia=True),
    "INTERMEDIARIO": Perfil("INTERMEDIARIO", "Saldos intermediarios de gestión",
                            "Deben usarse según el procedimiento de cierre de la empresa."),
    "ANALITICA": Perfil("ANALITICA", "Contabilidad analítica (destino)",
                        "Destinos definidos por la empresa: administración, ventas, producción, proyectos, maquinaria…"),
    "ORDEN": Perfil("ORDEN", "Cuentas de orden",
                    "Compromisos y contingencias: se muestran por separado y no integran los estados financieros."),
    "OTRO": Perfil("OTRO", "Otras cuentas", "Revisión general."),
}

_MAPA = {"10": "DISPONIBLE", "11": "INVERSION_FIN", "12": "COBRAR", "13": "COBRAR", "14": "COBRAR", "16": "COBRAR",
         "17": "COBRAR", "18": "ANTICIPADO", "19": "ESTIMACION", "23": "EN_PROCESO", "29": "DESVALORIZACION",
         "30": "INMOVILIZADO", "31": "INMOVILIZADO", "32": "INMOVILIZADO", "33": "INMOVILIZADO", "34": "INMOVILIZADO",
         "35": "INMOVILIZADO", "36": "DESVALORIZACION", "37": "DIFERIDO", "38": "INMOVILIZADO", "39": "DEPRECIACION",
         "40": "TRIBUTOS", "41": "REMUNERACIONES", "42": "PAGAR", "43": "PAGAR", "44": "PAGAR", "45": "FINANCIERA",
         "46": "PAGAR", "47": "PAGAR", "48": "PROVISION", "49": "PASIVO_DIFERIDO", "69": "COSTO_VENTAS",
         "78": "TRANSFERENCIA", "79": "TRANSFERENCIA"}


def perfil(cuenta: str) -> Perfil:
    if not cuenta:
        return PERFILES["OTRO"]
    dos, uno = cuenta[:2], cuenta[0]
    if dos in _MAPA:
        return PERFILES[_MAPA[dos]]
    if uno == "2":
        return PERFILES["INVENTARIO"]
    if uno == "5":
        return PERFILES["PATRIMONIO"]
    if uno == "6":
        return PERFILES["GASTO"]
    if uno == "7":
        return PERFILES["INGRESO"]
    if uno == "8":
        return PERFILES["INTERMEDIARIO"]
    if uno == "9":
        return PERFILES["ANALITICA"]
    if uno == "0":
        return PERFILES["ORDEN"]
    return PERFILES["OTRO"]


def ancestros(codigo: str, codigos_plan: set[str] | None = None) -> list[str]:
    """Prefijos del código (sin incluirlo) que forman niveles del árbol.

    Elemento, cuenta y subcuenta siempre existen; divisionaria, subdivisionaria y niveles
    analíticos intermedios solo si están definidos en el plan de la empresa (evita nodos
    artificiales con un único hijo)."""
    out = []
    for n in range(1, len(codigo)):
        pref = codigo[:n]
        if n <= 3 or (codigos_plan and pref in codigos_plan):
            out.append(pref)
    return out
