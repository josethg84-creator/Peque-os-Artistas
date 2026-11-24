"""Carga inicial de catálogos (idempotente)."""
from sqlalchemy.orm import Session

from app.models import Banco, Moneda

MONEDAS = [("PEN", "Sol peruano", "S/"), ("USD", "Dólar estadounidense", "US$"), ("EUR", "Euro", "€")]

# Código SUNAT según Tabla 3 del PLE (entidades del sistema financiero).
BANCOS = [
    ("BCP", "Banco de Crédito del Perú", "02"),
    ("INTERBANK", "Interbank", "03"),
    ("CITI", "Citibank del Perú", "07"),
    ("SCOTIABANK", "Scotiabank Perú", "09"),
    ("BBVA", "BBVA Perú", "11"),
    ("BN", "Banco de la Nación", "18"),
    ("COMERCIO", "Banco de Comercio", "23"),
    ("PICHINCHA", "Banco Pichincha", "35"),
    ("BANBIF", "BanBif - Banco Interamericano de Finanzas", "38"),
    ("GNB", "Banco GNB Perú", "53"),
    ("FALABELLA", "Banco Falabella", "54"),
    ("SANTANDER", "Banco Santander Perú", "56"),
]


def sembrar(db: Session) -> None:
    for codigo, nombre, simbolo in MONEDAS:
        if not db.get(Moneda, codigo):
            db.add(Moneda(codigo=codigo, nombre=nombre, simbolo=simbolo))
    existentes = {b.codigo for b in db.query(Banco).all()}
    for codigo, nombre, sunat in BANCOS:
        if codigo not in existentes:
            db.add(Banco(codigo=codigo, nombre=nombre, codigo_sunat=sunat))
    db.commit()
