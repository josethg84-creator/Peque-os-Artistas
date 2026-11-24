"""Detección de la fila de encabezados y mapeo de columnas a campos canónicos.

Los sinónimos cubren las denominaciones habituales de los estados de cuenta de
BCP, BBVA, Interbank, Scotiabank, BanBif y Banco de la Nación, y de los reportes
de libro mayor de los ERP más usados en Perú (Concar, Siscont, SAP, Starsoft…).
Siempre puede corregirse el mapeo manualmente en la vista previa.
"""
import re

from app.importers.normalizacion import normalizar_texto

# campo → lista de sinónimos (normalizados: mayúsculas sin tildes). El orden importa:
# el primero que coincide de forma exacta gana; luego se prueban coincidencias parciales.
SINONIMOS_BANCO: dict[str, list[str]] = {
    "fecha": ["FECHA", "FECHA OPERACION", "FECHA DE OPERACION", "F. OPERACION", "FEC. OPERACION",
              "FECHA PROCESO", "FECHA DE PROCESO", "FECHA MOV", "FECHA MOVIMIENTO", "FEC.",
              "F. PROCESO", "FECHA TRANSACCION", "DATE"],
    "fecha_valuta": ["FECHA VALUTA", "F. VALOR", "FECHA VALOR", "VALUTA", "FEC. VALUTA", "F. VALUTA"],
    "descripcion": ["DESCRIPCION", "DESCRIPCION OPERACION", "DESCRIPCION DE LA OPERACION",
                    "CONCEPTO", "DETALLE", "GLOSA", "MOVIMIENTO", "DESCRIPCION MOVIMIENTO",
                    "TRANSACCION", "NARRATIVA"],
    "numero_operacion": ["OPERACION - NUMERO", "NRO OPERACION", "N° OPERACION", "NO OPERACION",
                         "NUMERO DE OPERACION", "NUM. OPERACION", "NRO. OPERACION", "N OPERACION",
                         "NRO. OP.", "OPERACION", "NRO DOC", "NUMERO DOCUMENTO", "N° DOC.",
                         "DOCUMENTO", "NRO. MOV", "CODIGO OPERACION", "SECUENCIA"],
    "referencia": ["REFERENCIA", "REFERENCIA 2", "REF.", "REFERENCIA ADICIONAL", "OBSERVACION",
                   "BENEFICIARIO", "ORDENANTE", "CANAL", "SUCURSAL - AGENCIA", "AGENCIA", "OFICINA"],
    "importe": ["MONTO", "IMPORTE", "MONTO OPERACION", "IMPORTE (S/)", "IMPORTE S/", "VALOR",
                "MONTO S/", "MONTO US$", "AMOUNT"],
    "cargo": ["CARGO", "CARGOS", "CARGOS / DEBE", "DEBITO", "DEBITOS", "RETIROS", "EGRESOS",
              "CARGO S/", "CARGO US$", "SALIDAS"],
    "abono": ["ABONO", "ABONOS", "ABONOS / HABER", "CREDITO", "CREDITOS", "DEPOSITOS", "INGRESOS",
              "ABONO S/", "ABONO US$", "ENTRADAS"],
    "saldo": ["SALDO", "SALDO CONTABLE", "SALDO DISPONIBLE", "SALDO FINAL", "BALANCE", "SALDO S/",
              "SALDO US$"],
    "moneda": ["MONEDA", "MON.", "DIVISA", "CURRENCY"],
}

SINONIMOS_LIBRO: dict[str, list[str]] = {
    "fecha": ["FECHA", "FECHA OPERACION", "FECHA CONTABLE", "FEC. CONTABLE", "FECHA ASIENTO",
              "FECHA DE LA OPERACION", "FEC.", "F. EMISION", "FECHA DOC", "FECHA DOCUMENTO"],
    "voucher": ["VOUCHER", "NRO VOUCHER", "N° VOUCHER", "CUO", "NUMERO CORRELATIVO", "ASIENTO",
                "NRO ASIENTO", "N° ASIENTO", "COMPROBANTE", "SUBDIARIO - NUMERO", "REGISTRO",
                "CORRELATIVO"],
    "glosa": ["GLOSA", "DESCRIPCION", "DESCRIPCION DE LA OPERACION", "CONCEPTO", "DETALLE",
              "GLOSA DEL ASIENTO", "REFERENCIA"],
    "numero_operacion": ["NRO OPERACION", "N° OPERACION", "NUMERO DE OPERACION", "NRO. OPERACION",
                         "OPERACION BANCARIA", "NRO DOCUMENTO", "N° DOCUMENTO", "NUMERO DOCUMENTO",
                         "NRO. DOC", "DOCUMENTO", "NRO CHEQUE", "N° CHEQUE", "CHEQUE",
                         "NUM. DOC.", "MEDIO PAGO - NUMERO"],
    "medio_pago": ["MEDIO DE PAGO", "MEDIO PAGO", "COD. MEDIO PAGO", "TIPO MEDIO PAGO"],
    "tercero": ["RAZON SOCIAL", "AUXILIAR", "ANEXO", "PROVEEDOR / CLIENTE", "NOMBRE",
                "BENEFICIARIO", "GIRADO A", "CLIENTE", "PROVEEDOR"],
    "cuenta": ["CUENTA", "CUENTA CONTABLE", "CTA", "CTA. CONTABLE", "CODIGO CUENTA", "NRO CUENTA"],
    "debe": ["DEBE", "CARGO", "DEUDOR", "DEBITO", "DEBE S/", "DEBE MN", "DEBE ME", "DEBE US$"],
    "haber": ["HABER", "ABONO", "ACREEDOR", "CREDITO", "HABER S/", "HABER MN", "HABER ME",
              "HABER US$"],
    "importe": ["IMPORTE", "MONTO", "SALDO MOVIMIENTO"],
    "moneda": ["MONEDA", "MON.", "DIVISA"],
}

# Requisitos mínimos para aceptar una fila como encabezado.
REQUERIDOS = {
    "BANCO": [{"fecha"}, {"importe", "cargo", "abono"}],
    "LIBRO": [{"fecha"}, {"importe", "debe", "haber"}],
}


def sinonimos(tipo: str) -> dict[str, list[str]]:
    return SINONIMOS_BANCO if tipo == "BANCO" else SINONIMOS_LIBRO


_ABREV_NUMERO = {"NUMERO", "NUM", "NRO", "NO", "N", "NUMERO"}


def _clave(texto) -> str:
    """Clave comparable: sin tildes ni puntos; N°/Nº/No./Num./Número → NRO."""
    s = normalizar_texto(texto).replace("°", "O").replace("º", "O")
    s = re.sub(r"[.:_\-/()]+", " ", s)
    tokens = ["NRO" if t in _ABREV_NUMERO else t for t in s.split()]
    return " ".join(tokens)


def mapear_columnas(encabezados: list, tipo: str) -> dict[int, str]:
    """Devuelve {índice de columna: campo canónico}. Cada campo se asigna una sola vez."""
    tabla = sinonimos(tipo)
    claves = [_clave(h) for h in encabezados]
    asignado: dict[int, str] = {}
    usados: set[str] = set()

    # 1) coincidencia exacta
    for campo, sins in tabla.items():
        objetivos = {_clave(s) for s in sins}
        for i, c in enumerate(claves):
            if i not in asignado and c and c in objetivos:
                asignado[i] = campo
                usados.add(campo)
                break
    # 2) coincidencia parcial (el encabezado empieza por el sinónimo o lo contiene como palabra)
    for campo, sins in tabla.items():
        if campo in usados:
            continue
        for i, c in enumerate(claves):
            if i in asignado or not c:
                continue
            if any(re.search(rf"(^|\s){re.escape(_clave(s))}(\s|$)", c) for s in sins):
                asignado[i] = campo
                usados.add(campo)
                break
    return asignado


def cumple_requeridos(campos: set[str], tipo: str) -> bool:
    return all(campos & grupo for grupo in REQUERIDOS[tipo])


def detectar_encabezado(filas: list[list], tipo: str, max_filas: int = 40) -> tuple[int, dict[int, str]] | None:
    """Busca, entre las primeras filas, la que mejor funciona como encabezado."""
    mejor: tuple[int, dict[int, str]] | None = None
    for idx, fila in enumerate(filas[:max_filas]):
        textos = [c for c in fila if isinstance(c, str) and c.strip()]
        if len(textos) < 2:
            continue
        mapeo = mapear_columnas(list(fila), tipo)
        if cumple_requeridos(set(mapeo.values()), tipo):
            if mejor is None or len(mapeo) > len(mejor[1]):
                mejor = (idx, mapeo)
    return mejor
