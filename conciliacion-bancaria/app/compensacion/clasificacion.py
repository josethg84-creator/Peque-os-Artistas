"""Clasificación de movimientos de cuentas compensables.

Señales, en orden: origen del dato (apertura) → tipo de documento (Tabla 10 SUNAT) → glosa →
cuenta y subdiario → lado del movimiento y contrapartidas del asiento. Cuando las señales se
contradicen o no hay ninguna, la clase queda PENDIENTE DE REVISIÓN con confianza baja.

Rol: ORIGEN genera saldo según la naturaleza de la cuenta (cargo en cuentas por cobrar, abono en
cuentas por pagar); APLICACION lo cancela. Las notas de crédito, extornos, pagos, cobranzas,
detracciones y retenciones son aplicaciones; las notas de débito son origen.
"""
import re
from dataclasses import dataclass

from app.importers.normalizacion import normalizar_texto

TIPOS_DOC = {"01": "FACTURA", "03": "BOLETA", "02": "RECIBO_HONORARIOS", "07": "NOTA_CREDITO", "08": "NOTA_DEBITO",
             "20": "RETENCION", "40": "PERCEPCION", "12": "BOLETA", "14": "FACTURA"}
PALABRAS = [  # (clase, patrón) en orden de prioridad
    ("EXTORNO", r"\bEXTORNO|\bANULAC|\bANULAD|\bREVERSI"),
    ("DETRACCION", r"DETRACC|\bSPOT\b|BANCO DE LA NACION"),
    ("RETENCION", r"RETENC"),
    ("PERCEPCION", r"PERCEPC"),
    ("DIFERENCIA_CAMBIO", r"DIF(\.|ERENCIA)?\s*(DE\s*)?CAMBIO|\bDIF\s*CAMB"),
    ("RECLASIFICACION", r"RECLASIF"),
    ("NOTA_CREDITO", r"NOTA\s*(DE\s*)?CREDITO|\bN/C\b|\bNC\s"),
    ("NOTA_DEBITO", r"NOTA\s*(DE\s*)?DEBITO|\bN/D\b"),
    ("RENDICION", r"RENDICION|LIQUIDACION DE GASTOS"),
    ("ENTREGA_RENDIR", r"A RENDIR|ENTREGA[S]? A RENDIR|FONDO FIJO"),
    ("ANTICIPO", r"ANTICIPO|ADELANTO"),
    ("AMORTIZACION", r"AMORTIZ|\bCUOTA\b"),
    ("PRESTAMO", r"PRESTAMO|FINANCIAMIENTO|DESEMBOLSO"),
    ("COBRANZA", r"COBRANZA|\bCOBRO\b|ABONO DE CLIENTE"),
    ("PAGO", r"\bPAGO\b|\bPAGOS\b|CANCELACION"),
    ("FACTURA", r"\bFACTURA\b|\bFACT\b|VENTA\s|COMPRA\s"),
    ("BOLETA", r"\bBOLETA\b"),
    ("RECIBO_HONORARIOS", r"HONORARIO|\bR\.?H\.?\b"),
]
_PALABRAS = [(c, re.compile(p)) for c, p in PALABRAS]
SIEMPRE_APLICACION = {"NOTA_CREDITO", "EXTORNO", "PAGO", "COBRANZA", "DETRACCION", "RETENCION", "RENDICION", "AMORTIZACION"}
SIEMPRE_ORIGEN = {"NOTA_DEBITO", "FACTURA", "BOLETA", "RECIBO_HONORARIOS", "PRESTAMO", "ENTREGA_RENDIR"}


def naturaleza(cuenta: str) -> str:
    """D si la cuenta es de activo (saldo deudor esperado), A si es de pasivo."""
    return "D" if cuenta[:1] in "123" else "A"


@dataclass
class Clasificacion:
    clase: str
    rol: str
    confianza: int
    motivo: str
    pendiente: bool


def clasificar(*, cuenta: str, lado: str, tipo_documento: str | None, glosa: str | None, subdiario: str | None,
               contrapartidas: set[str], origen_datos: str, anticipos: list[str], subdiarios_pago: list[str]) -> Clasificacion:
    nat = naturaleza(cuenta)
    rol_lado = "ORIGEN" if (lado == "D") == (nat == "D") else "APLICACION"
    if origen_datos != "DIARIO":
        return Clasificacion("SALDO_INICIAL", rol_lado, 100, "Saldo de apertura", origen_datos == "APERTURA_CONSOLIDADA")

    g = normalizar_texto(glosa or "")
    por_tipo = TIPOS_DOC.get((tipo_documento or "").zfill(2) if tipo_documento else "")
    por_glosa = next((c for c, p in _PALABRAS if p.search(g)), None)
    contra_caja = any(c.startswith("10") for c in contrapartidas)
    es_anticipo_cta = any(cuenta.startswith(p) for p in anticipos)
    motivos = []

    clase, confianza = None, 0
    if por_glosa in ("EXTORNO", "DETRACCION", "RETENCION", "PERCEPCION", "DIFERENCIA_CAMBIO", "RECLASIFICACION"):
        clase, confianza = por_glosa, 90
        motivos.append(f"glosa: {por_glosa.lower()}")
    elif por_tipo in ("FACTURA", "BOLETA", "RECIBO_HONORARIOS") and rol_lado == "APLICACION":
        # la línea que cancela suele llevar el documento que aplica (práctica de CONCAR, Starsoft…)
        if contra_caja or por_glosa in ("PAGO", "COBRANZA"):
            clase, confianza = ("COBRANZA" if nat == "D" else "PAGO"), 90
            motivos.append("cancela el documento referenciado con " + ("caja/bancos" if contra_caja else "glosa de pago"))
        elif por_glosa in ("ANTICIPO", "NOTA_CREDITO", "RECLASIFICACION"):
            clase, confianza = por_glosa, 70
            motivos.append(f"aplica el documento referenciado; glosa: {por_glosa.lower()}")
        else:
            clase, confianza = "OTRO", 55
            motivos.append("cancela el documento referenciado sin evidencia de pago")
    elif por_tipo:
        clase, confianza = por_tipo, 95
        motivos.append(f"tipo de documento {tipo_documento}")
        if por_glosa and por_glosa not in (por_tipo, "FACTURA", "PAGO", "COBRANZA") and rol_lado == "ORIGEN" \
                and por_glosa in ("ANTICIPO", "NOTA_CREDITO"):
            confianza = 50
            motivos.append(f"la glosa sugiere {por_glosa.lower()}")
    elif es_anticipo_cta or por_glosa == "ANTICIPO":
        clase, confianza = "ANTICIPO", 85 if es_anticipo_cta else 75
        motivos.append("cuenta de anticipos" if es_anticipo_cta else "glosa: anticipo")
    elif por_glosa:
        clase, confianza = por_glosa, 75
        motivos.append(f"glosa: {por_glosa.lower()}")

    if clase is None:  # señales estructurales
        if rol_lado == "APLICACION" and (contra_caja or (subdiario or "") in subdiarios_pago):
            clase, confianza = ("COBRANZA" if nat == "D" else "PAGO"), 80
            motivos.append("contrapartida en caja/bancos" if contra_caja else f"subdiario {subdiario}")
        elif cuenta.startswith("45"):
            clase, confianza = ("PRESTAMO" if rol_lado == "ORIGEN" else "AMORTIZACION"), 70
            motivos.append("obligación financiera")
        elif cuenta.startswith("141"):
            clase, confianza = ("ENTREGA_RENDIR" if rol_lado == "ORIGEN" else "RENDICION"), 70
            motivos.append("cuenta de entregas al personal")
        else:
            clase, confianza = "OTRO", 40
            motivos.append("sin señales suficientes")
    elif clase in ("PAGO", "COBRANZA") and rol_lado == "APLICACION":
        clase = "COBRANZA" if nat == "D" else "PAGO"

    rol = rol_lado
    if clase in SIEMPRE_APLICACION and rol_lado == "ORIGEN":
        # un pago o nota de crédito en el lado que genera saldo es inusual: posible devolución o error
        confianza = min(confianza, 50)
        motivos.append("el lado del movimiento no corresponde a la clase")
    if clase in SIEMPRE_ORIGEN and rol_lado == "APLICACION" and clase != "ENTREGA_RENDIR":
        confianza = min(confianza, 50)
        motivos.append("el lado del movimiento no corresponde a la clase")
    pendiente = confianza < 60
    return Clasificacion(clase, rol, confianza, "; ".join(motivos), pendiente)
