"""Catálogo de tipos de información contable, sus campos y el diccionario de homologación.

Cada tipo define:
  - `campos`: campos internos admitidos, en orden de presentación.
  - `requeridos`: grupos de campos; cada grupo se cumple si al menos uno está mapeado
    (p. ej. el importe puede venir como Debe/Haber o como un importe con signo).
  - `extra`: sinónimos adicionales solo válidos para ese tipo (p. ej. «Código» es la
    cuenta en un plan de cuentas pero el centro de costo en un maestro de centros).

Los sinónimos recogen encabezados habituales de SAP, Starsoft, Proficont, CONCAR, PLE y
Excel genéricos. Son una ayuda: el usuario siempre confirma o corrige la homologación.
"""
import re
from dataclasses import dataclass, field

from app.importers.normalizacion import normalizar_texto

SISTEMAS_ORIGEN = {
    "GENERICO": "Excel genérico",
    "SAP": "SAP",
    "STARSOFT": "Starsoft",
    "PROFICONT": "Proficont",
    "CONCAR": "CONCAR",
    "PERSONALIZADO": "Sistema personalizado",
}


@dataclass(frozen=True)
class Campo:
    clave: str
    etiqueta: str
    tipo: str  # texto | codigo | fecha | importe | tasa | entero | booleano | moneda | dh
    sinonimos: tuple[str, ...] = ()


def _c(clave, etiqueta, tipo, *sinonimos):
    return Campo(clave, etiqueta, tipo, tuple(sinonimos))


CAMPOS: dict[str, Campo] = {c.clave: c for c in [
    _c("ejercicio", "Ejercicio", "entero", "EJERCICIO", "AÑO", "ANIO", "YEAR", "FISCAL YEAR", "AÑO FISCAL"),
    _c("periodo", "Periodo", "entero", "PERIODO", "MES", "PERIOD", "PERIODO CONTABLE", "PER"),
    _c("fecha_contable", "Fecha contable", "fecha", "FECHA", "FECHA CONTABLE", "FEC CONTABLE", "FECHA ASIENTO",
       "FECHA DE CONTABILIZACION", "FECHA CONTABILIZACION", "FE CONTABILIZACION", "POSTING DATE",
       "FECHA OPERACION", "FECHA VOUCHER", "F CONTABLE", "FECHA REGISTRO", "FECHA COMPROBANTE CONTABLE"),
    _c("fecha_emision", "Fecha de emisión", "fecha", "FECHA EMISION", "FECHA DE EMISION", "F EMISION",
       "FEC EMISION", "FECHA DOCUMENTO", "FECHA DOC", "FECHA DE DOCUMENTO", "DOCUMENT DATE", "FECHA COMPROBANTE",
       "FECHA DE EMISION DEL COMPROBANTE"),
    _c("fecha_vencimiento", "Fecha de vencimiento", "fecha", "FECHA VENCIMIENTO", "FECHA DE VENCIMIENTO",
       "F VENCIMIENTO", "FEC VENC", "FECHA VENC", "VENCIMIENTO", "DUE DATE", "FEC VENCIMIENTO"),
    _c("subdiario", "Subdiario", "codigo", "SUBDIARIO", "SUB DIARIO", "SUBDIARIO CODIGO", "LIBRO", "CLASE DOCUMENTO",
       "CLASE DE DOCUMENTO", "CL DOC", "ORIGEN", "TIPO ASIENTO", "JOURNAL", "DIARIO"),
    _c("numero_asiento", "Número de asiento", "codigo", "ASIENTO", "NRO ASIENTO", "NUMERO ASIENTO", "VOUCHER",
       "NRO VOUCHER", "NRO COMPROBANTE", "COMPROBANTE", "NRO COMPROBANTE CONTABLE", "NUMERO DE COMPROBANTE",
       "CUO", "DOCUMENTO CONTABLE", "NRO DOC CONTABLE", "JOURNAL ENTRY", "ENTRY NO", "NRO MOVIMIENTO"),
    _c("numero_linea", "Número de línea", "entero", "LINEA", "NRO LINEA", "ITEM", "POSICION", "POS", "SECUENCIA",
       "LINE ITEM", "CORRELATIVO LINEA", "NRO ITEM"),
    _c("cuenta", "Código de cuenta contable", "codigo", "CUENTA", "CUENTA CONTABLE", "CTA", "CTA CONTABLE",
       "CODIGO CUENTA", "COD CUENTA", "CODIGO DE CUENTA", "CUENTA MAYOR", "CUENTA DE MAYOR", "ACCOUNT",
       "GL ACCOUNT", "G L ACCOUNT", "NRO CUENTA", "CTA CTBLE", "CUENTA CTBLE"),
    _c("descripcion_cuenta", "Descripción de cuenta", "texto", "DESCRIPCION CUENTA", "DESCRIPCION DE LA CUENTA",
       "NOMBRE CUENTA", "NOMBRE DE LA CUENTA", "DENOMINACION", "DENOMINACION DE LA CUENTA", "ACCOUNT NAME",
       "DESC CUENTA", "TEXTO CUENTA"),
    _c("glosa", "Glosa", "texto", "GLOSA", "GLOSA DETALLE", "GLOSA ASIENTO", "DESCRIPCION", "CONCEPTO", "DETALLE",
       "TEXTO", "TEXT", "DESCRIPTION", "GLOSA PRINCIPAL", "DESCRIPCION OPERACION"),
    _c("tipo_documento", "Tipo de documento", "codigo", "TIPO DOCUMENTO", "TIPO DOC", "TD", "T DOC",
       "TIPO COMPROBANTE", "TIPO DE COMPROBANTE", "COD COMPROBANTE", "TIPO DE DOCUMENTO", "TIPO COMPROBANTE PAGO",
       "TIPO CP"),
    _c("serie", "Serie", "codigo", "SERIE", "SERIE DOCUMENTO", "SERIE COMPROBANTE", "NRO SERIE", "SERIE CP",
       "SERIE DEL COMPROBANTE"),
    _c("numero_documento", "Número de documento", "codigo", "NUMERO", "NRO DOCUMENTO", "NUMERO DOCUMENTO",
       "NUM DOC", "NRO DOC", "NUMERO COMPROBANTE", "NRO COMPROBANTE PAGO", "NUMERO DEL COMPROBANTE", "REFERENCIA",
       "DOCUMENTO", "NRO CP", "NUMERO CP", "NRO DE DOCUMENTO"),
    _c("tipo_documento_identidad", "Tipo de documento de identidad", "codigo", "TIPO DOC IDENTIDAD",
       "TIPO DOCUMENTO IDENTIDAD", "TIPO DE DOCUMENTO DE IDENTIDAD", "TDI", "T DOC IDENT", "TIPO IDENTIDAD",
       "TIPO DOC ID", "TIPO DE DOC"),
    _c("documento_tercero", "RUC o identificación del tercero", "codigo", "RUC", "NRO RUC", "RUC DNI",
       "DOCUMENTO IDENTIDAD", "NRO DOC IDENTIDAD", "NUMERO DOCUMENTO IDENTIDAD", "NUMERO DE DOCUMENTO DE IDENTIDAD",
       "TAX ID", "IDENTIFICACION", "ANEXO", "CODIGO ANEXO", "COD ANEXO", "AUXILIAR", "COD AUXILIAR", "NIT",
       "DNI", "RUC PROVEEDOR", "RUC CLIENTE", "NRO DOCUMENTO IDENTIDAD"),
    _c("razon_social", "Razón social", "texto", "RAZON SOCIAL", "NOMBRE O RAZON SOCIAL", "APELLIDOS Y NOMBRES",
       "APELLIDOS NOMBRES DENOMINACION O RAZON SOCIAL", "PROVEEDOR", "CLIENTE", "BENEFICIARIO", "NAME",
       "NOMBRE ANEXO", "DESCRIPCION ANEXO", "NOMBRE AUXILIAR", "NOMBRE TERCERO"),
    _c("moneda", "Moneda", "moneda", "MONEDA", "MON", "DIVISA", "CURRENCY", "COD MONEDA", "MONEDA DOCUMENTO",
       "MONEDA DEL DOCUMENTO", "MND"),
    _c("tipo_cambio", "Tipo de cambio", "tasa", "TIPO DE CAMBIO", "TIPO CAMBIO", "T C", "TC", "CAMBIO",
       "EXCHANGE RATE", "TIPO CAMBIO VENTA", "TCAMBIO", "T CAMBIO"),
    _c("debe_mn", "Debe moneda nacional", "importe", "DEBE", "DEBE MN", "DEBE S", "DEBE SOLES", "DEBE M N",
       "DEBE NACIONAL", "CARGO", "CARGO MN", "CARGOS", "DEBITO", "DEBIT", "IMPORTE DEBE", "MONTO DEBE",
       "DEBE MONEDA NACIONAL", "DEBE ML"),
    _c("haber_mn", "Haber moneda nacional", "importe", "HABER", "HABER MN", "HABER S", "HABER SOLES", "HABER M N",
       "HABER NACIONAL", "ABONO", "ABONO MN", "ABONOS", "CREDITO", "CREDIT", "IMPORTE HABER", "MONTO HABER",
       "HABER MONEDA NACIONAL", "HABER ML"),
    _c("debe_me", "Debe moneda extranjera", "importe", "DEBE ME", "DEBE US$", "DEBE US", "DEBE DOLARES",
       "DEBE M E", "CARGO ME", "DEBE EXTRANJERA", "DEBE MONEDA EXTRANJERA", "DEBE MD"),
    _c("haber_me", "Haber moneda extranjera", "importe", "HABER ME", "HABER US$", "HABER US", "HABER DOLARES",
       "HABER M E", "ABONO ME", "HABER EXTRANJERA", "HABER MONEDA EXTRANJERA", "HABER MD"),
    _c("importe_mn", "Importe MN con signo (+ debe / − haber)", "importe", "IMPORTE", "IMPORTE MN",
       "IMPORTE EN MONEDA LOCAL", "IMPORTE ML", "IMPORTE MONEDA LOCAL", "AMOUNT IN LOCAL CURRENCY", "AMOUNT LC",
       "IMPORTE SOLES", "MONTO MN", "VALOR"),
    _c("importe_me", "Importe ME con signo", "importe", "IMPORTE ME", "IMPORTE EN MONEDA DEL DOCUMENTO",
       "IMPORTE MD", "IMPORTE MONEDA DOCUMENTO", "AMOUNT IN DOC CURR", "IMPORTE DOLARES", "MONTO ME"),
    _c("indicador_dh", "Indicador debe/haber", "dh", "D H", "DEBE HABER", "INDICADOR DEBE HABER", "IND D H",
       "CLAVE CONTABILIZACION", "CLAVE CONTABILIZ", "CLAVE CONTAB", "CLV CONT", "CL CONT", "POSTING KEY", "PSTNG KEY", "D C",
       "DEBIT CREDIT", "CARGO ABONO", "C A", "TIPO MOVIMIENTO"),
    _c("centro_costo", "Centro de costo", "codigo", "CENTRO COSTO", "CENTRO DE COSTO", "CENTRO DE COSTOS",
       "CENTRO COSTE", "CENTRO DE COSTE", "CECO", "CC", "C COSTO", "COST CENTER", "COST CENTRE",
       "COD CENTRO COSTO", "CODIGO CENTRO COSTO", "C COSTOS", "CENTRO COSTOS"),
    _c("proyecto", "Proyecto", "codigo", "PROYECTO", "PROJECT", "OBRA", "ELEMENTO PEP", "WBS", "COD PROYECTO"),
    _c("activo_maquinaria", "Código de maquinaria o activo", "codigo", "MAQUINARIA", "COD MAQUINARIA", "ACTIVO FIJO",
       "COD ACTIVO", "CODIGO ACTIVO", "EQUIPO", "ASSET", "ACTIVO"),
    _c("documento_referencia", "Documento de referencia", "codigo", "DOCUMENTO REFERENCIA", "DOC REFERENCIA",
       "REFERENCIA DOC", "DOC REF", "NRO REFERENCIA", "DOCUMENTO MODIFICADO", "DOC ORIGEN"),
    _c("orden_compra_servicio", "Orden de compra o servicio", "codigo", "ORDEN COMPRA", "ORDEN DE COMPRA", "OC",
       "O C", "OS", "O S", "ORDEN SERVICIO", "ORDEN DE SERVICIO", "PEDIDO", "PURCHASE ORDER", "NRO OC"),
    _c("codigo_detraccion", "Código de detracción", "codigo", "CODIGO DETRACCION", "COD DETRACCION",
       "TIPO DETRACCION", "BIEN SERVICIO DETRACCION", "CODIGO BIEN SERVICIO"),
    _c("constancia_detraccion", "N.º constancia de detracción", "codigo", "CONSTANCIA DETRACCION",
       "NRO CONSTANCIA", "CONSTANCIA DE DEPOSITO", "NUMERO CONSTANCIA DETRACCION", "NRO DETRACCION",
       "NRO CONSTANCIA DETRACCION", "CONSTANCIA"),
    _c("retencion", "Información de retención", "texto", "RETENCION", "IMPORTE RETENCION", "COMPROBANTE RETENCION",
       "NRO RETENCION", "RETENCION IGV", "MARCA RETENCION"),
    # Trazabilidad del registro en el ERP (fase 7): solo si el sistema de origen la exporta
    _c("usuario_registro", "Usuario que registró", "texto", "USUARIO", "USUARIO REGISTRO", "REGISTRADO POR", "DIGITADOR",
       "USUARIO CREACION", "CREADO POR"),
    _c("fecha_registro", "Fecha real de registro", "fecha", "FECHA REGISTRO", "FECHA DE REGISTRO", "FECHA DIGITACION",
       "FECHA CREACION", "FECHA SISTEMA"),
    _c("origen_asiento", "Origen del asiento (manual / automático)", "codigo", "ORIGEN", "ORIGEN ASIENTO", "TIPO REGISTRO",
       "MANUAL AUTOMATICO", "MODULO ORIGEN"),
    # Registros de compras y ventas / cuentas por cobrar y pagar
    _c("cuo", "CUO / n.º de registro", "codigo", "CUO", "CODIGO UNICO DE OPERACION", "NRO REGISTRO",
       "CORRELATIVO", "VOUCHER", "NRO VOUCHER", "ASIENTO"),
    _c("base_imponible", "Base imponible", "importe", "BASE IMPONIBLE", "BASE IMP", "VALOR VENTA", "VALOR COMPRA",
       "BI", "BASE GRAVADA", "BI GRAVADA", "VALOR FACTURADO", "AFECTO", "OPERACION GRAVADA",
       "BASE IMPONIBLE GRAVADA", "VALOR DE VENTA"),
    _c("igv", "IGV / IPM", "importe", "IGV", "IGV IPM", "IGV Y O IPM", "IMPUESTO", "IGV 18%", "IGV 18"),
    _c("no_gravado", "No gravado / exonerado / inafecto", "importe", "NO GRAVADO", "INAFECTO", "EXONERADO",
       "VALOR NO GRAVADO", "NO AFECTO", "OPERACION INAFECTA", "OPERACION EXONERADA", "ADQUISICIONES NO GRAVADAS"),
    _c("otros_tributos", "Otros tributos y cargos", "importe", "OTROS TRIBUTOS", "ISC", "ICBPER", "OTROS CARGOS",
       "OTROS TRIBUTOS Y CARGOS"),
    _c("total", "Importe total", "importe", "TOTAL", "IMPORTE TOTAL", "TOTAL COMPROBANTE", "PRECIO VENTA",
       "MONTO TOTAL", "IMPORTE ORIGINAL", "MONTO ORIGINAL", "IMPORTE DOCUMENTO", "TOTAL DOCUMENTO"),
    _c("saldo_pendiente", "Saldo pendiente MN", "importe", "SALDO PENDIENTE", "SALDO", "SALDO MN", "SALDO S",
       "SALDO POR COBRAR", "SALDO POR PAGAR", "PENDIENTE", "IMPORTE PENDIENTE", "SALDO SOLES"),
    _c("saldo_pendiente_me", "Saldo pendiente ME", "importe", "SALDO ME", "SALDO US$", "SALDO US",
       "SALDO DOLARES", "SALDO PENDIENTE ME"),
    # Plan de cuentas
    _c("nivel", "Nivel", "entero", "NIVEL", "LEVEL", "GRADO", "DIGITOS"),
    _c("naturaleza", "Naturaleza (D/A)", "texto", "NATURALEZA", "TIPO SALDO", "NAT", "SALDO NATURAL"),
    _c("admite_movimiento", "Admite movimiento", "booleano", "ADMITE MOVIMIENTO", "MOVIMIENTO", "IMPUTABLE",
       "REGISTRA MOVIMIENTO", "TRANSACCIONAL", "AFECTABLE", "DE MOVIMIENTO", "ULTIMO NIVEL"),
    _c("activa", "Activa", "booleano", "ACTIVA", "ACTIVO", "ESTADO", "VIGENTE", "HABILITADA"),
    _c("requiere_centro_costo", "Requiere centro de costo", "booleano", "REQUIERE CC", "REQUIERE CENTRO COSTO",
       "CENTRO COSTO OBLIGATORIO", "PIDE CC", "PIDE CENTRO COSTO"),
    _c("cuenta_destino_debe", "Cuenta destino (debe)", "codigo", "DESTINO DEBE", "CTA DESTINO DEBE",
       "CUENTA DESTINO DEBE", "DESTINO CARGO", "AMARRE DEBE", "DESTINO", "CUENTA DESTINO"),
    _c("cuenta_destino_haber", "Cuenta destino (haber)", "codigo", "DESTINO HABER", "CTA DESTINO HABER",
       "CUENTA DESTINO HABER", "DESTINO ABONO", "AMARRE HABER", "CONTRA DESTINO"),
    # Maestros
    _c("descripcion", "Descripción", "texto", "DESCRIPCION", "NOMBRE", "DENOMINACION", "DESCRIPTION"),
    _c("cuenta_destino", "Cuenta de destino (clase 9)", "codigo", "CUENTA DESTINO", "CTA DESTINO",
       "CUENTA CLASE 9", "DESTINO"),
    _c("unidad_negocio", "Unidad de negocio", "codigo", "UNIDAD NEGOCIO", "UNIDAD DE NEGOCIO", "UN", "LINEA DE NEGOCIO",
       "DIVISION", "SEGMENTO", "BUSINESS UNIT"),
    _c("direccion", "Dirección", "texto", "DIRECCION", "DOMICILIO FISCAL", "DOMICILIO", "ADDRESS"),
    _c("estado_contribuyente", "Estado del contribuyente", "texto", "ESTADO CONTRIBUYENTE", "ESTADO SUNAT", "ESTADO"),
    _c("condicion_domicilio", "Condición de domicilio", "texto", "CONDICION", "CONDICION DOMICILIO", "HABIDO",
       "CONDICION DE DOMICILIO"),
    # Balance de comprobación
    _c("saldo_inicial_debe", "Saldo inicial deudor", "importe", "SALDO INICIAL DEUDOR", "SALDOS INICIALES DEUDOR",
       "SALDO ANTERIOR DEUDOR", "SI DEBE", "SALDO INICIAL DEBE", "INICIAL DEUDOR", "SALDO ANTERIOR DEBE"),
    _c("saldo_inicial_haber", "Saldo inicial acreedor", "importe", "SALDO INICIAL ACREEDOR",
       "SALDOS INICIALES ACREEDOR", "SALDO ANTERIOR ACREEDOR", "SI HABER", "SALDO INICIAL HABER",
       "INICIAL ACREEDOR", "SALDO ANTERIOR HABER"),
    _c("movimiento_debe", "Movimiento debe", "importe", "MOVIMIENTO DEBE", "MOVIMIENTOS DEBE", "DEBE", "CARGOS",
       "SUMAS DEBE", "MOVIMIENTOS DEL PERIODO DEBE", "MOV DEBE", "DEBITOS", "SUMAS DEL MAYOR DEBE"),
    _c("movimiento_haber", "Movimiento haber", "importe", "MOVIMIENTO HABER", "MOVIMIENTOS HABER", "HABER", "ABONOS",
       "SUMAS HABER", "MOVIMIENTOS DEL PERIODO HABER", "MOV HABER", "CREDITOS", "SUMAS DEL MAYOR HABER"),
    _c("saldo_final_debe", "Saldo final deudor", "importe", "SALDO FINAL DEUDOR", "SALDOS FINALES DEUDOR",
       "SALDO DEUDOR", "DEUDOR", "SALDOS DEUDOR", "SF DEBE", "SALDO FINAL DEBE", "SALDOS DEUDOR"),
    _c("saldo_final_haber", "Saldo final acreedor", "importe", "SALDO FINAL ACREEDOR", "SALDOS FINALES ACREEDOR",
       "SALDO ACREEDOR", "ACREEDOR", "SALDOS ACREEDOR", "SF HABER", "SALDO FINAL HABER"),
    _c("saldo_inicial", "Saldo inicial con signo", "importe", "SALDO INICIAL", "SALDO ANTERIOR"),
    _c("saldo_final", "Saldo final con signo", "importe", "SALDO FINAL", "SALDO ACTUAL"),
    # Tipos de cambio
    _c("fecha", "Fecha", "fecha", "FECHA", "FECHA PUBLICACION", "DATE", "DIA"),
    _c("compra", "Tipo de cambio compra", "tasa", "COMPRA", "TC COMPRA", "TIPO CAMBIO COMPRA", "BUY", "T C COMPRA"),
    _c("venta", "Tipo de cambio venta", "tasa", "VENTA", "TC VENTA", "TIPO CAMBIO VENTA", "SELL", "T C VENTA"),
]}


@dataclass(frozen=True)
class TipoDef:
    clave: str
    nombre: str
    descripcion: str
    campos: tuple[str, ...]
    requeridos: tuple[frozenset, ...]
    extra: dict = field(default_factory=dict)
    transaccional: bool = True       # requiere periodo; se puede anular
    admite_completa: bool = False    # partida doble verificable


_LINEA = ("ejercicio", "periodo", "fecha_contable", "fecha_emision", "fecha_vencimiento", "subdiario",
          "numero_asiento", "numero_linea", "cuenta", "descripcion_cuenta", "glosa", "tipo_documento", "serie",
          "numero_documento", "tipo_documento_identidad", "documento_tercero", "razon_social", "moneda",
          "tipo_cambio", "debe_mn", "haber_mn", "debe_me", "haber_me", "importe_mn", "importe_me", "indicador_dh",
          "centro_costo", "proyecto", "activo_maquinaria", "documento_referencia", "orden_compra_servicio",
          "codigo_detraccion", "constancia_detraccion", "retencion", "usuario_registro", "fecha_registro", "origen_asiento")
_REGISTRO = ("periodo", "cuo", "fecha_emision", "fecha_vencimiento", "tipo_documento", "serie", "numero_documento",
             "tipo_documento_identidad", "documento_tercero", "razon_social", "base_imponible", "igv", "no_gravado",
             "otros_tributos", "total", "moneda", "tipo_cambio", "cuenta", "glosa", "documento_referencia",
             "codigo_detraccion", "constancia_detraccion", "retencion")
_CARTERA = ("documento_tercero", "razon_social", "tipo_documento_identidad", "tipo_documento", "serie",
            "numero_documento", "fecha_emision", "fecha_vencimiento", "moneda", "tipo_cambio", "total",
            "saldo_pendiente", "saldo_pendiente_me", "cuenta", "glosa")
_TERCERO = ("tipo_documento_identidad", "documento_tercero", "razon_social", "direccion", "estado_contribuyente",
            "condicion_domicilio")
_IMPORTE_LINEA = frozenset({"debe_mn", "haber_mn", "importe_mn"})
_CODIGO_ES_CUENTA = {"cuenta": ("CODIGO", "COD"), "descripcion_cuenta": ("DESCRIPCION", "NOMBRE")}

TIPOS: dict[str, TipoDef] = {t.clave: t for t in [
    TipoDef("DIARIO", "Libro diario", "Asientos con todas sus líneas (debe y haber).", _LINEA,
            (frozenset({"fecha_contable"}), frozenset({"numero_asiento"}), frozenset({"cuenta"}), _IMPORTE_LINEA),
            admite_completa=True),
    TipoDef("MAYOR", "Libro mayor", "Movimientos agrupados por cuenta.", _LINEA,
            (frozenset({"fecha_contable"}), frozenset({"cuenta"}), _IMPORTE_LINEA), admite_completa=True),
    TipoDef("BALANCE", "Balance de comprobación", "Saldos iniciales, movimientos y saldos finales por cuenta.",
            ("cuenta", "descripcion_cuenta", "saldo_inicial_debe", "saldo_inicial_haber", "saldo_inicial",
             "movimiento_debe", "movimiento_haber", "saldo_final_debe", "saldo_final_haber", "saldo_final"),
            (frozenset({"cuenta"}), frozenset({"movimiento_debe", "movimiento_haber", "saldo_final_debe",
                                               "saldo_final_haber", "saldo_final"})),
            extra=_CODIGO_ES_CUENTA, admite_completa=True),
    TipoDef("COMPRAS", "Registro de compras", "Comprobantes de compra (formato 8.1 o propio del ERP).", _REGISTRO,
            (frozenset({"fecha_emision"}), frozenset({"tipo_documento"}), frozenset({"numero_documento"}),
             frozenset({"documento_tercero"}), frozenset({"total"}))),
    TipoDef("VENTAS", "Registro de ventas", "Comprobantes de venta (formato 14.1 o propio del ERP).", _REGISTRO,
            (frozenset({"fecha_emision"}), frozenset({"tipo_documento"}), frozenset({"numero_documento"}),
             frozenset({"total"}))),
    TipoDef("PLAN_CUENTAS", "Plan de cuentas", "Cuentas con naturaleza, movimiento y destinos.",
            ("cuenta", "descripcion_cuenta", "nivel", "naturaleza", "admite_movimiento", "activa",
             "requiere_centro_costo", "cuenta_destino_debe", "cuenta_destino_haber"),
            (frozenset({"cuenta"}), frozenset({"descripcion_cuenta"})), extra=_CODIGO_ES_CUENTA, transaccional=False),
    TipoDef("CLIENTES", "Maestro de clientes", "Clientes con su documento de identidad.", _TERCERO,
            (frozenset({"documento_tercero"}), frozenset({"razon_social"})),
            extra={"razon_social": ("NOMBRE", "DESCRIPCION")}, transaccional=False),
    TipoDef("PROVEEDORES", "Maestro de proveedores", "Proveedores con su documento de identidad.", _TERCERO,
            (frozenset({"documento_tercero"}), frozenset({"razon_social"})),
            extra={"razon_social": ("NOMBRE", "DESCRIPCION")}, transaccional=False),
    TipoDef("CENTROS_COSTO", "Centros de costo", "Centros de costo y su cuenta de destino.",
            ("centro_costo", "descripcion", "cuenta_destino", "unidad_negocio", "activa"),
            (frozenset({"centro_costo"}), frozenset({"descripcion"})),
            extra={"centro_costo": ("CODIGO", "COD")}, transaccional=False),
    TipoDef("SALDOS_INICIALES", "Saldos iniciales", "Saldos de apertura por cuenta (y tercero).",
            ("cuenta", "descripcion_cuenta", "documento_tercero", "moneda", "debe_mn", "haber_mn", "debe_me",
             "haber_me", "importe_mn"),
            (frozenset({"cuenta"}), _IMPORTE_LINEA),
            extra={"importe_mn": ("SALDO", "SALDO INICIAL"), "descripcion_cuenta": ("DESCRIPCION", "NOMBRE")},
            admite_completa=True),
    TipoDef("TIPOS_CAMBIO", "Tipos de cambio", "Tipo de cambio compra y venta por fecha.",
            ("fecha", "moneda", "compra", "venta"), (frozenset({"fecha"}), frozenset({"compra", "venta"})),
            transaccional=False),
    TipoDef("CXC", "Cuentas por cobrar", "Documentos pendientes de cobro al cierre.", _CARTERA,
            (frozenset({"documento_tercero"}), frozenset({"numero_documento"}), frozenset({"saldo_pendiente"}))),
    TipoDef("CXP", "Cuentas por pagar", "Documentos pendientes de pago al cierre.", _CARTERA,
            (frozenset({"documento_tercero"}), frozenset({"numero_documento"}), frozenset({"saldo_pendiente"}))),
]}

# Diseños adicionales registrados por otros módulos (p. ej. fuentes de conciliación de la fase 6). No se
# muestran en el asistente de importación contable, pero reutilizan la homologación, la detección de
# encabezados y la conversión de valores de esta fase.
TIPOS_EXTRA: dict[str, TipoDef] = {}


def tipo_def(tipo: str) -> TipoDef:
    return TIPOS[tipo] if tipo in TIPOS else TIPOS_EXTRA[tipo]


def registrar_tipo(tdef: TipoDef, campos: list[Campo]) -> None:
    for c in campos:
        if c.clave in CAMPOS and CAMPOS[c.clave].tipo != c.tipo:
            raise ValueError(f"El campo {c.clave} ya existe con otro tipo")
        CAMPOS.setdefault(c.clave, c)
    TIPOS_EXTRA[tdef.clave] = tdef


_ABREV_NUMERO = {"NUMERO", "NUM", "NRO", "NO", "N", "NÚMERO"}


def clave_encabezado(texto) -> str:
    """Encabezado comparable: sin tildes, sin puntuación; N°/Nº/No./Núm. → NRO."""
    s = normalizar_texto(texto).replace("°", "O").replace("º", "O")
    s = re.sub(r"[.:_\-/()\\\[\]]+", " ", s)
    return " ".join("NRO" if t in _ABREV_NUMERO else t for t in s.split())


def sinonimos_de(tipo: str, campo: str) -> list[str]:
    t = tipo_def(tipo)
    return [clave_encabezado(s) for s in (*t.extra.get(campo, ()), *CAMPOS[campo].sinonimos)]


def es_obligatorio(tipo: str, campo: str) -> bool:
    return any(campo in g and len(g) == 1 for g in tipo_def(tipo).requeridos)


def grupos_faltantes(tipo: str, mapeados: set[str]) -> list[frozenset]:
    return [g for g in tipo_def(tipo).requeridos if not (g & mapeados)]


def describir_tipo(tipo: str) -> dict:
    t = tipo_def(tipo)
    alternativos = {c for g in t.requeridos if len(g) > 1 for c in g}
    return {
        "clave": t.clave, "nombre": t.nombre, "descripcion": t.descripcion,
        "transaccional": t.transaccional, "admite_completa": t.admite_completa,
        "campos": [{
            "clave": c, "etiqueta": CAMPOS[c].etiqueta, "tipo": CAMPOS[c].tipo,
            "obligatorio": es_obligatorio(tipo, c),
            "alternativo": c in alternativos,
        } for c in t.campos],
        "requeridos": [sorted(g) for g in t.requeridos],
    }
