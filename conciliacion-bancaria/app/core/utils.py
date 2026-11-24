"""Utilidades generales: validación de RUC, montos."""
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)


def ruc_valido(ruc: str) -> bool:
    """Valida un RUC peruano (11 dígitos, prefijo y dígito verificador módulo 11)."""
    if not ruc or len(ruc) != 11 or not ruc.isdigit():
        return False
    if ruc[:2] not in {"10", "15", "16", "17", "20"}:
        return False
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(d) * p for d, p in zip(ruc[:10], pesos))
    digito = 11 - (suma % 11)
    if digito == 10:
        digito = 0
    elif digito == 11:
        digito = 1
    return digito == int(ruc[10])
