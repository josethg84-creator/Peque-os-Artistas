from datetime import date
from decimal import Decimal

import pytest

from app.core.utils import ruc_valido
from app.importers.columnas import detectar_encabezado, mapear_columnas
from app.importers.normalizacion import clasificar_movimiento, limpiar_codigo, parse_fecha, parse_importe


@pytest.mark.parametrize("texto,esperado", [
    ("1,234.56", "1234.56"), ("1.234,56", "1234.56"), ("S/ 1,234.56", "1234.56"),
    ("US$ 10", "10.00"), ("(500.00)", "-500.00"), ("500.00-", "-500.00"), ("-500", "-500.00"),
    ("500.00 CR", "500.00"), ("500.00 DB", "-500.00"), ("1 234,56", "1234.56"), ("1234,5", "1234.50"),
    ("1,234", "1234.00"), ("1.234.567", "1234567.00"), (1500.255, "1500.26"), (0, "0.00"),
    ("S/ -1,200.00", "-1200.00"), ("USD 1,500.00", "1500.00"), ("S/. 99.90", "99.90"), ("PEN 10", "10.00"),
])
def test_parse_importe(texto, esperado):
    assert parse_importe(texto) == Decimal(esperado)


@pytest.mark.parametrize("vacio", [None, "", "-", "  ", float("nan"), "abc", "1,2a0.00", "12O.00", "N/A"])
def test_parse_importe_vacio(vacio):
    assert parse_importe(vacio) is None


@pytest.mark.parametrize("texto,esperado", [
    ("15/10/2026", date(2026, 10, 15)), ("15-10-26", date(2026, 10, 15)), ("2026-10-15", date(2026, 10, 15)),
    ("2026-10-15 00:00:00", date(2026, 10, 15)), ("15/10", date(2026, 10, 15)),
    ("15-OCT-2026", date(2026, 10, 15)), ("15OCT", date(2026, 10, 15)), ("01-Set-2026", date(2026, 9, 1)),
    (46310, date(2026, 10, 15)), (date(2026, 10, 15), date(2026, 10, 15)),
])
def test_parse_fecha(texto, esperado):
    assert parse_fecha(texto, 2026) == esperado


@pytest.mark.parametrize("texto", ["31/02/2026", "SALDO ANTERIOR", None, "", 12])
def test_parse_fecha_invalida(texto):
    assert parse_fecha(texto, 2026) is None


def test_limpiar_codigo():
    assert limpiar_codigo(451201.0) == "451201"
    assert limpiar_codigo(" 00012345 ") == "00012345"
    assert limpiar_codigo(None) is None


@pytest.mark.parametrize("desc,cat", [
    ("ITF", "ITF"), ("IMPUESTO A LAS TRANSACCIONES FINANCIERAS", "ITF"), ("COMISION MANTENIMIENTO", "COMISION"),
    ("PORTES ENVIO", "COMISION"), ("INTERESES GANADOS", "INTERES"), ("TRANSF.BCO.OTROS CLIENTE", "TRANSFERENCIA"),
    ("DEPOSITO EN EFECTIVO", "DEPOSITO"), ("DEPOSITO CHEQUE OTRO BANCO", "DEPOSITO"),
    ("ABONO TRANSF INTERBANCARIA", "TRANSFERENCIA"), ("CHEQUE 00012345 PAGADO", "CHEQUE"), ("PAGO SUNAT", "PAGO"),
    ("XYZ", "OTRO"),
])
def test_clasificar(desc, cat):
    assert clasificar_movimiento(desc) == cat


def test_ruc():
    assert ruc_valido("20100047218")  # BCP
    assert ruc_valido("20609876540")
    assert not ruc_valido("20100047219")
    assert not ruc_valido("30100047218")
    assert not ruc_valido("2010004721")


def test_mapeo_columnas_bancos():
    m = mapear_columnas(["Fecha", "Fecha valuta", "Descripción operación", "Monto", "Saldo",
                         "Sucursal - agencia", "Operación - Número"], "BANCO")
    assert m[0] == "fecha" and m[1] == "fecha_valuta" and m[2] == "descripcion"
    assert m[3] == "importe" and m[4] == "saldo" and m[6] == "numero_operacion"
    m = mapear_columnas(["F. Operación", "F. Valor", "Concepto", "Nº Doc.", "Cargo", "Abono", "Saldo"], "BANCO")
    assert set(m.values()) >= {"fecha", "fecha_valuta", "descripcion", "numero_operacion", "cargo", "abono", "saldo"}


def test_detecta_encabezado_tras_titulos():
    filas = [["BANCO X"], ["Cuenta:", "123"], [], ["Fecha", "Concepto", "Cargo", "Abono"], ["01/10/2026", "x", "", "5"]]
    idx, _ = detectar_encabezado(filas, "BANCO")
    assert idx == 3
