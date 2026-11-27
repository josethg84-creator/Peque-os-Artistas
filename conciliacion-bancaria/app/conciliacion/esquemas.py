"""Diseños de fuentes externas para conciliar (planillas, kardex, constancias, declaraciones…).

Se registran en el registro de la fase 2 para reutilizar su homologación de columnas (sinónimos, sugerencias,
plantillas), la detección de encabezados, la exclusión de subtotales y la conversión de fechas e importes.
Los registros de compras y ventas se importan con el propio flujo de la fase 2 y los estados bancarios con
el de la fase 1 (que incluye PDF con revisión manual).
"""
from app.contable.campos import Campo, TipoDef, registrar_tipo


def _c(clave, etiqueta, tipo, *sin):
    return Campo(clave, etiqueta, tipo, tuple(sin))


NUEVOS = [
    _c("numero_operacion", "Número de operación", "codigo", "NRO OPERACION", "NUMERO DE OPERACION", "OPERACION", "NRO OP",
       "N OPERACION", "CODIGO OPERACION", "NRO MOVIMIENTO BANCARIO"),
    _c("referencia", "Referencia", "texto", "REFERENCIA", "REF", "REFERENCIA BANCARIA", "DOCUMENTO RELACIONADO", "OBSERVACION"),
    _c("importe", "Importe", "importe", "IMPORTE", "MONTO", "VALOR", "AMOUNT", "IMPORTE TOTAL", "MONTO TOTAL"),
    _c("concepto", "Concepto", "texto", "CONCEPTO", "CONCEPTO PLANILLA", "RUBRO", "PARTIDA", "TIPO DE COSTO", "ELEMENTO DE COSTO"),
    _c("tipo_concepto", "Tipo de concepto", "codigo", "TIPO CONCEPTO", "TIPO", "CLASE CONCEPTO", "NATURALEZA CONCEPTO"),
    _c("tipo_planilla", "Tipo de planilla", "codigo", "PLANILLA", "TIPO PLANILLA", "TIPO DE PLANILLA"),
    _c("periodo_texto", "Periodo (AAAA-MM)", "texto", "PERIODO", "MES", "PERIODO PLANILLA", "PERIODO TRIBUTARIO", "PERIODO DECLARADO"),
    _c("producto", "Código de producto", "codigo", "CODIGO PRODUCTO", "PRODUCTO", "COD PRODUCTO", "CODIGO ARTICULO", "ARTICULO", "ITEM", "SKU",
       "CODIGO"),
    _c("almacen", "Almacén", "codigo", "ALMACEN", "COD ALMACEN", "BODEGA", "DEPOSITO"),
    _c("unidad", "Unidad de medida", "codigo", "UNIDAD", "UM", "U M", "UNIDAD MEDIDA", "UNIDAD DE MEDIDA"),
    _c("cantidad_inicial", "Cantidad inicial", "tasa", "CANTIDAD INICIAL", "CANT INICIAL", "STOCK INICIAL", "SALDO INICIAL CANTIDAD"),
    _c("cantidad_entradas", "Cantidad de entradas", "tasa", "CANTIDAD ENTRADAS", "ENTRADAS CANTIDAD", "CANT ENTRADAS", "INGRESOS CANTIDAD"),
    _c("cantidad_salidas", "Cantidad de salidas", "tasa", "CANTIDAD SALIDAS", "SALIDAS CANTIDAD", "CANT SALIDAS", "EGRESOS CANTIDAD"),
    _c("cantidad_final", "Cantidad final", "tasa", "CANTIDAD FINAL", "CANT FINAL", "STOCK FINAL", "SALDO FINAL CANTIDAD", "STOCK"),
    _c("costo_unitario", "Costo unitario", "tasa", "COSTO UNITARIO", "C UNITARIO", "COSTO PROMEDIO", "PRECIO UNITARIO", "CU"),
    _c("valor_inicial", "Valor inicial", "importe", "VALOR INICIAL", "SALDO INICIAL VALOR", "COSTO INICIAL", "IMPORTE INICIAL"),
    _c("valor_entradas", "Valor de entradas", "importe", "VALOR ENTRADAS", "ENTRADAS VALOR", "COSTO ENTRADAS", "IMPORTE ENTRADAS"),
    _c("valor_salidas", "Valor de salidas", "importe", "VALOR SALIDAS", "SALIDAS VALOR", "COSTO SALIDAS", "IMPORTE SALIDAS"),
    _c("valor_final", "Valor final", "importe", "VALOR FINAL", "SALDO FINAL VALOR", "COSTO FINAL", "IMPORTE FINAL", "VALORIZADO"),
    _c("orden_servicio", "Orden de servicio", "codigo", "ORDEN SERVICIO", "ORDEN DE SERVICIO", "OS", "OT", "ORDEN DE TRABAJO"),
    _c("numero_constancia", "Número de constancia", "codigo", "CONSTANCIA", "NRO CONSTANCIA", "NUMERO CONSTANCIA", "N CONSTANCIA",
       "CONSTANCIA DE DEPOSITO"),
    _c("tipo_retencion", "Tipo de retención", "codigo", "TIPO RETENCION", "REGIMEN", "TIPO", "CLASE"),
    _c("tributo", "Tributo", "texto", "TRIBUTO", "IMPUESTO", "CONCEPTO TRIBUTARIO", "CODIGO TRIBUTO", "FORMULARIO"),
    _c("obligacion", "Obligación declarada", "importe", "OBLIGACION", "IMPORTE DECLARADO", "TRIBUTO RESULTANTE", "DEUDA TRIBUTARIA",
       "DETERMINADO", "IMPUESTO RESULTANTE"),
    _c("pagos", "Pagos", "importe", "PAGOS", "PAGADO", "IMPORTE PAGADO", "PAGO"),
    _c("creditos", "Créditos aplicados", "importe", "CREDITOS", "CREDITOS APLICADOS", "SALDO A FAVOR APLICADO", "PAGOS A CUENTA"),
    _c("compensaciones", "Compensaciones", "importe", "COMPENSACIONES", "COMPENSACION"),
    _c("numero_orden", "Número de orden", "codigo", "NRO ORDEN", "NUMERO DE ORDEN", "ORDEN", "N ORDEN"),
    _c("saldo", "Saldo", "importe", "SALDO", "SALDO PENDIENTE", "SALDO FINAL", "SALDO AUXILIAR"),
    _c("contrato", "Contrato", "codigo", "CONTRATO", "NRO CONTRATO", "NUMERO DE CONTRATO"),
]
_BASE_DOC = ("tipo_documento", "serie", "numero_documento", "documento_tercero", "razon_social")
ESQUEMAS = {
    "CONC_GENERICO": TipoDef("CONC_GENERICO", "Fuente genérica", "Cualquier listado con fecha, documento, tercero e importe.",
                             ("fecha", *_BASE_DOC, "numero_operacion", "referencia", "glosa", "cuenta", "centro_costo", "proyecto",
                              "concepto", "moneda", "tipo_cambio", "importe", "importe_me", "periodo_texto", "contrato"),
                             (frozenset({"importe"}),)),
    "CONC_PLANILLA": TipoDef("CONC_PLANILLA", "Planilla procesada", "Conceptos por trabajador (remuneraciones, descuentos, aportes, neto).",
                             ("periodo_texto", "tipo_planilla", "documento_tercero", "razon_social", "concepto", "tipo_concepto",
                              "importe", "centro_costo"),
                             (frozenset({"documento_tercero"}), frozenset({"concepto"}), frozenset({"importe"})),
                             extra={"documento_tercero": ("DNI", "DOCUMENTO", "NRO DOCUMENTO", "TRABAJADOR", "CODIGO TRABAJADOR"),
                                    "razon_social": ("NOMBRE", "APELLIDOS Y NOMBRES", "NOMBRES")}),
    "CONC_KARDEX": TipoDef("CONC_KARDEX", "Kardex valorizado", "Saldos y movimientos por producto y almacén.",
                           ("producto", "glosa", "almacen", "unidad", "cuenta", "cantidad_inicial", "cantidad_entradas",
                            "cantidad_salidas", "cantidad_final", "costo_unitario", "valor_inicial", "valor_entradas", "valor_salidas",
                            "valor_final"),
                           (frozenset({"producto"}), frozenset({"valor_final"})), extra={"glosa": ("DESCRIPCION", "NOMBRE PRODUCTO")}),
    "CONC_COSTOS": TipoDef("CONC_COSTOS", "Reporte de costos por proyecto", "Costos operativos por proyecto, orden y concepto.",
                           ("proyecto", "orden_servicio", "concepto", "importe", "periodo_texto", "centro_costo", "glosa"),
                           (frozenset({"proyecto"}), frozenset({"importe"}))),
    "CONC_CONSTANCIAS": TipoDef("CONC_CONSTANCIAS", "Constancias de detracción", "Depósitos en el Banco de la Nación.",
                                ("numero_constancia", "fecha", *_BASE_DOC, "codigo_detraccion", "importe", "periodo_texto"),
                                (frozenset({"numero_constancia"}), frozenset({"importe"})),
                                extra={"fecha": ("FECHA DEPOSITO", "FECHA DE DEPOSITO", "FECHA PAGO")}),
    "CONC_RETENCIONES": TipoDef("CONC_RETENCIONES", "Comprobantes de retención y percepción", "Retenciones y percepciones con su documento.",
                                ("tipo_retencion", "fecha", *_BASE_DOC, "documento_referencia", "base_imponible", "importe", "periodo_texto"),
                                (frozenset({"numero_documento"}), frozenset({"importe"})),
                                extra={"documento_referencia": ("DOCUMENTO ORIGINAL", "COMPROBANTE RELACIONADO", "DOC RELACIONADO"),
                                       "base_imponible": ("IMPORTE DEL COMPROBANTE", "IMPORTE ORIGINAL", "BASE", "MONTO PAGADO")}),
    "CONC_DECLARACIONES": TipoDef("CONC_DECLARACIONES", "Declaraciones y aportes", "Obligación declarada, pagos y créditos por tributo y periodo.",
                                  ("tributo", "periodo_texto", "obligacion", "pagos", "creditos", "compensaciones", "numero_orden", "fecha"),
                                  (frozenset({"tributo"}), frozenset({"periodo_texto"}), frozenset({"obligacion", "pagos"}))),
    "CONC_SALDOS": TipoDef("CONC_SALDOS", "Saldos de un auxiliar", "Saldos por cuenta, tercero o documento según el sistema auxiliar.",
                           ("cuenta", "documento_tercero", "razon_social", "serie", "numero_documento", "saldo", "moneda"),
                           (frozenset({"cuenta"}), frozenset({"saldo"}))),
}


def registrar() -> None:
    for t in ESQUEMAS.values():
        registrar_tipo(t, NUEVOS)


registrar()
