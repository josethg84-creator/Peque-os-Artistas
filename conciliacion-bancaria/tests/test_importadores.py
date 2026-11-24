import io
from decimal import Decimal

import pytest

from app.importers.analizador import analizar
from app.importers.lectores import ErrorImportacion


def leer(ejemplos, nombre):
    return (ejemplos / nombre).read_bytes()


def test_csv_bcp(ejemplos):
    r = analizar("bcp.csv", leer(ejemplos, "estado_bcp_pen_2026-10.csv"), "BANCO", "PEN")
    assert r.formato == "CSV" and not r.errores
    assert len(r.registros) == 22
    assert r.saldo_inicial == Decimal("50000.00")
    cats = [x["categoria"] for x in r.registros]
    assert cats.count("ITF") == 9 and "INTERES" in cats and "COMISION" in cats
    # la fila repetida rompe la continuidad de saldos y se informa
    assert r.saldos_consistentes is False


def test_xlsx_bbva_cargo_abono(ejemplos):
    r = analizar("bbva.xlsx", leer(ejemplos, "estado_bbva_usd_2026-10.xlsx"), "BANCO", "USD")
    assert r.formato == "XLSX" and r.saldos_consistentes is True
    assert [x["importe"] for x in r.registros][:3] == [Decimal("6500.00"), Decimal("-3120.75"), Decimal("-35.00")]
    assert r.registros[0]["numero_operacion"] == "7781001"


def test_pdf_texto_deduce_signo_por_saldo(ejemplos):
    r = analizar("ibk.pdf", leer(ejemplos, "estado_interbank_pen_2026-10.pdf"), "BANCO", "PEN")
    assert r.formato == "PDF" and r.metodo == "TEXTO_PDF"
    assert r.saldo_inicial == Decimal("20000.00") and r.saldos_consistentes is True
    assert [x["importe"] for x in r.registros] == [Decimal("3200.00"), Decimal("-845.30"), Decimal("1500.00"),
                                                   Decimal("-12.00"), Decimal("-2000.00")]
    assert r.registros[0]["numero_operacion"] == "000123456"


def test_pdf_con_tabla():
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    buf = io.BytesIO()
    datos = [["Fecha", "Descripción", "Cargo", "Abono", "Saldo"],
             ["01/10/2026", "DEPOSITO", "", "1,000.00", "1,000.00"],
             ["02/10/2026", "ITF", "0.05", "", "999.95"]]
    t = Table(datos)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, "black")]))
    SimpleDocTemplate(buf, pagesize=A4).build([t])
    r = analizar("x.pdf", buf.getvalue(), "BANCO", "PEN")
    assert r.metodo == "TABLA"
    assert [x["importe"] for x in r.registros] == [Decimal("1000.00"), Decimal("-0.05")]
    assert r.saldos_consistentes is True


def test_libro_filtra_subcuenta_y_saldo_anterior(ejemplos):
    r = analizar("mayor.xlsx", leer(ejemplos, "libro_mayor_cuenta10_2026-10.xlsx"), "LIBRO", "PEN",
                 cuenta_contable="104101")
    assert len(r.registros) == 14 and r.filas_filtradas == 7
    assert r.saldo_inicial == Decimal("50000.00")
    pago = next(x for x in r.registros if x["voucher"] == "03-0001")
    assert pago["importe"] == Decimal("-4720.00") and pago["haber"] == Decimal("4720.00")


def test_moneda_distinta_se_rechaza():
    csv = "Fecha;Descripcion;Monto;Moneda\n01/10/2026;DEP;100.00;USD\n02/10/2026;DEP;50.00;S/\n".encode()
    r = analizar("x.csv", csv, "BANCO", "PEN")
    assert len(r.registros) == 1 and len(r.errores) == 1 and "Moneda USD" in r.errores[0]["mensaje"]


def test_orden_descendente_y_signo_por_saldo():
    csv = ("Fecha,Descripcion,Importe,Saldo\n"
           "03/10/2026,PAGO,200.00,900.00\n02/10/2026,DEPOSITO,500.00,1100.00\n01/10/2026,DEPOSITO,100.00,600.00\n").encode()
    r = analizar("x.csv", csv, "BANCO", "PEN")
    # 01/10 no puede deducirse (sin saldo inicial); los demás sí
    assert r.registros[0]["importe"] == Decimal("-200.00")
    assert any("descendente" in a for a in r.advertencias)


def test_mapeo_manual():
    csv = "Col A;Col B;Col C\n01/10/2026;Algo;150.00\n".encode()
    with pytest.raises(ErrorImportacion):
        analizar("x.csv", csv, "BANCO", "PEN")
    r = analizar("x.csv", csv, "BANCO", "PEN", mapeo_manual={0: "fecha", 1: "descripcion", 2: "importe"})
    assert r.registros[0]["importe"] == Decimal("150.00")


def test_xls_antiguo_rechazado():
    with pytest.raises(ErrorImportacion, match="xls"):
        analizar("x.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 100, "BANCO", "PEN")
