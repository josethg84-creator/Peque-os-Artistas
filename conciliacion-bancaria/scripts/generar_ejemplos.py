"""Genera archivos de ejemplo (ficticios) en ./ejemplos para probar la importación.

Escenario: COMERCIAL ANDINA S.A.C. (RUC ficticio 20609876540), octubre 2026.
  - 104101 BCP soles        → estado_bcp_pen_2026-10.csv     (CSV, importe con signo)
  - 104102 BBVA dólares     → estado_bbva_usd_2026-10.xlsx   (Excel, cargo/abono, títulos arriba)
  - 104103 Interbank soles  → estado_interbank_pen_2026-10.pdf (PDF de texto, sin signo)
  - libro_mayor_cuenta10_2026-10.xlsx con las tres subcuentas.

Incluye a propósito: ITF, comisiones, portes e intereses no registrados en libros,
un cheque no cobrado, un depósito en tránsito, un depósito que agrupa dos
cobranzas (1 a varios), una planilla pagada en un solo cargo (varios a 1),
diferencias de fecha y una fila duplicada en el estado de cuenta.

Uso:  python scripts/generar_ejemplos.py
"""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "ejemplos"
D = Decimal


def itf(monto: Decimal) -> Decimal:
    """ITF 0.005 % truncado a múltiplos de S/ 0.05 (criterio usado para el ejemplo)."""
    bruto = abs(monto) * D("0.00005")
    return (bruto / D("0.05")).to_integral_value(rounding="ROUND_FLOOR") * D("0.05")


# ---------------------------------------------------------------- BCP (PEN)
BCP_SALDO_INICIAL = D("50000.00")
BCP = [  # fecha, descripción, importe, n.º operación
    (date(2026, 10, 1), "DEPOSITO EN EFECTIVO VENTANILLA", D("12500.00"), "0451201"),
    (date(2026, 10, 3), "TRANSF.BCO.OTROS CLIENTE NORTE SAC", D("8850.00"), "0451388"),
    (date(2026, 10, 5), "PAGO PROVEEDOR TEXTILES LIMA SRL", D("-4720.00"), "0451502"),
    (date(2026, 10, 8), "CHEQUE 00012345 PAGADO", D("-3000.00"), "00012345"),
    (date(2026, 10, 10), "DEPOSITO CHEQUE OTRO BANCO", D("2360.00"), "0451777"),
    (date(2026, 10, 12), "PAGO SUNAT NPS 1029384756", D("-1850.00"), "0451890"),
    (date(2026, 10, 15), "TRANSF RECIBIDA COMERCIAL SUR EIRL", D("5900.00"), "0452001"),
    (date(2026, 10, 20), "PAGO DE HABERES PLANILLA", D("-15300.00"), "0452120"),
    (date(2026, 10, 25), "COMISION MANTENIMIENTO CUENTA", D("-15.00"), None),
    (date(2026, 10, 28), "TRANSF RECIBIDA DISTRIB. CENTRO SAC", D("3540.00"), "0452300"),
    (date(2026, 10, 31), "INTERESES GANADOS", D("12.35"), None),
    (date(2026, 10, 31), "PORTES ENVIO ESTADO DE CUENTA", D("-5.00"), None),
]


def generar_bcp():
    filas, saldo = [], BCP_SALDO_INICIAL
    for f, desc, imp, op in BCP:
        saldo += imp
        filas.append([f, desc, imp, saldo, op])
        if desc.startswith(("DEPOSITO", "TRANSF", "PAGO", "CHEQUE")):
            t = itf(imp)
            if t:
                saldo -= t
                filas.append([f, "ITF", -t, saldo, None])
        if op == "0452001":  # exportación con la fila repetida
            filas.append(list(filas[-2]))
    with open(DESTINO / "estado_bcp_pen_2026-10.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Fecha", "Fecha valuta", "Descripción operación", "Monto", "Saldo",
                    "Sucursal - agencia", "Operación - Número"])
        for f, desc, imp, saldo_f, op in filas:
            w.writerow([f.strftime("%d/%m/%Y"), f.strftime("%d/%m/%Y"), desc, f"{imp:,.2f}",
                        f"{saldo_f:,.2f}", "191 - LIMA CENTRO", op or ""])


# --------------------------------------------------------------- BBVA (USD)
BBVA_SALDO_INICIAL = D("18250.40")
BBVA = [
    (date(2026, 10, 2), "ABONO TRANSFERENCIA EXTERIOR ACME CORP", D("6500.00"), "7781001"),
    (date(2026, 10, 9), "PAGO FACTURA IMPORTACION LOGISTIC INC", D("-3120.75"), "7781054"),
    (date(2026, 10, 16), "COMISION TRANSFERENCIA EXTERIOR", D("-35.00"), "7781090"),
    (date(2026, 10, 22), "ABONO TRANSFERENCIA CLIENTE DELTA", D("2480.00"), "7781123"),
    (date(2026, 10, 30), "INTERES ACREDITADO", D("4.18"), None),
]


def generar_bbva():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"
    ws.append(["BBVA Perú - Consulta de movimientos"])
    ws.append(["Cuenta:", "0011-0123-0100012345"])
    ws.append(["Moneda:", "USD"])
    ws.append([])
    ws.append(["F. Operación", "F. Valor", "Concepto", "Nº Doc.", "Cargo", "Abono", "Saldo"])
    saldo = BBVA_SALDO_INICIAL
    for f, desc, imp, op in BBVA:
        saldo += imp
        ws.append([f, f, desc, op, float(-imp) if imp < 0 else None,
                   float(imp) if imp > 0 else None, float(saldo)])
    for fila in ws.iter_rows(min_row=6, max_col=2):
        for c in fila:
            c.number_format = "DD/MM/YYYY"
    wb.save(DESTINO / "estado_bbva_usd_2026-10.xlsx")


# ------------------------------------------------------- Interbank (PEN, PDF)
IBK_SALDO_INICIAL = D("20000.00")
IBK = [
    (date(2026, 10, 2), "ABONO TRANSF INTERBANCARIA OP 000123456", D("3200.00")),
    (date(2026, 10, 7), "PAGO SERVICIO LUZ DEL SUR OP 000123480", D("-845.30")),
    (date(2026, 10, 14), "DEPOSITO EFECTIVO AGENCIA OP 000123511", D("1500.00")),
    (date(2026, 10, 21), "COMISION POR MANTENIMIENTO", D("-12.00")),
    (date(2026, 10, 29), "TRANSF A TERCEROS OP 000123590", D("-2000.00")),
]


def generar_interbank():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(DESTINO / "estado_interbank_pen_2026-10.pdf"), pagesize=A4)
    y = 800
    for linea in ["INTERBANK - ESTADO DE CUENTA CORRIENTE", "COMERCIAL ANDINA S.A.C.",
                  "Cuenta: 200-3001234567  Moneda: SOLES  Periodo: 01/10/2026 al 31/10/2026", "",
                  "Fecha  Fecha valor  Descripción  Importe  Saldo",
                  f"SALDO ANTERIOR {IBK_SALDO_INICIAL:,.2f}"]:
        c.drawString(40, y, linea)
        y -= 16
    saldo = IBK_SALDO_INICIAL
    for f, desc, imp in IBK:
        saldo += imp
        c.drawString(40, y, f"{f:%d/%m/%Y} {f:%d/%m/%Y} {desc} {abs(imp):,.2f} {saldo:,.2f}")
        y -= 16
    c.drawString(40, y - 10, f"SALDO FINAL {saldo:,.2f}")
    c.save()


# ------------------------------------------------------------ Libro mayor
def generar_libro():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Mayor"
    ws.append(["COMERCIAL ANDINA S.A.C.  RUC 20609876540"])
    ws.append(["LIBRO MAYOR - CUENTA 10 EFECTIVO Y EQUIVALENTES DE EFECTIVO - OCTUBRE 2026"])
    ws.append([])
    ws.append(["Cuenta", "Fecha", "Voucher", "Glosa", "Medio de pago", "Nro Operación",
               "Razón social", "Debe", "Haber"])
    filas = [
        ("104101", None, None, "SALDO ANTERIOR", None, None, None, 50000.00, None),
        ("104101", date(2026, 10, 1), "02-0001", "DEPOSITO VENTAS EN EFECTIVO", "001", "0451201", None, 12500.00, None),
        ("104101", date(2026, 10, 3), "02-0002", "COBRANZA F001-245", "003", "0451388", "CLIENTE NORTE SAC", 8850.00, None),
        ("104101", date(2026, 10, 4), "03-0001", "PAGO F/ E001-889", "003", "0451502", "TEXTILES LIMA SRL", None, 4720.00),
        ("104101", date(2026, 10, 6), "03-0002", "CHEQUE 00012345 SERVICIOS GENERALES", "007", "00012345", "SERVICIOS GENERALES EIRL", None, 3000.00),
        ("104101", date(2026, 10, 10), "02-0003", "COBRANZA F001-250", "001", None, "INVERSIONES ROJAS SAC", 1180.00, None),
        ("104101", date(2026, 10, 10), "02-0004", "COBRANZA F001-251", "001", None, "INVERSIONES ROJAS SAC", 1180.00, None),
        ("104101", date(2026, 10, 12), "03-0003", "PAGO IGV SETIEMBRE 2026", "003", None, "SUNAT", None, 1850.00),
        ("104101", date(2026, 10, 15), "02-0005", "COBRANZA F001-260", "003", "0452001", "COMERCIAL SUR EIRL", 5900.00, None),
        ("104101", date(2026, 10, 20), "03-0004", "PLANILLA OCT - J. PEREZ", "003", None, "PEREZ JUAN", None, 5100.00),
        ("104101", date(2026, 10, 20), "03-0005", "PLANILLA OCT - M. QUISPE", "003", None, "QUISPE MARIA", None, 5100.00),
        ("104101", date(2026, 10, 20), "03-0006", "PLANILLA OCT - L. TORRES", "003", None, "TORRES LUIS", None, 5100.00),
        ("104101", date(2026, 10, 27), "02-0006", "COBRANZA F001-270", "003", "0452300", "DISTRIB. CENTRO SAC", 3540.00, None),
        ("104101", date(2026, 10, 29), "03-0007", "CHEQUE 00012346 PROVEEDOR ANDES", "007", "00012346", "PROVEEDOR ANDES SAC", None, 2200.00),
        ("104101", date(2026, 10, 31), "02-0007", "DEPOSITO VENTAS 31/10", "001", None, None, 4000.00, None),
        ("104102", None, None, "SALDO ANTERIOR", None, None, None, 18250.40, None),
        ("104102", date(2026, 10, 2), "02-0101", "COBRANZA EXPORTACION E001-55", "003", "7781001", "ACME CORP", 6500.00, None),
        ("104102", date(2026, 10, 9), "03-0101", "PAGO IMPORTACION INV-9921", "003", "7781054", "LOGISTIC INC", None, 3120.75),
        ("104102", date(2026, 10, 23), "02-0102", "COBRANZA CLIENTE DELTA", "003", "7781123", "DELTA SRL", 2480.00, None),
        ("104103", None, None, "SALDO ANTERIOR", None, None, None, 20000.00, None),
        ("104103", date(2026, 10, 2), "02-0201", "COBRANZA F002-010", "003", "000123456", "CLIENTE OESTE SAC", 3200.00, None),
        ("104103", date(2026, 10, 7), "03-0201", "PAGO LUZ DEL SUR SETIEMBRE", "003", "000123480", "LUZ DEL SUR", None, 845.30),
        ("104103", date(2026, 10, 14), "02-0202", "DEPOSITO VENTAS", "001", "000123511", None, 1500.00, None),
        ("104103", date(2026, 10, 29), "03-0202", "TRANSFERENCIA A PROVEEDOR", "003", "000123590", "PROVEEDOR CUSCO", None, 2000.00),
    ]
    for f in filas:
        ws.append(list(f))
    for fila in ws.iter_rows(min_row=5, min_col=2, max_col=2):
        for c in fila:
            c.number_format = "DD/MM/YYYY"
    wb.save(DESTINO / "libro_mayor_cuenta10_2026-10.xlsx")


if __name__ == "__main__":
    DESTINO.mkdir(exist_ok=True)
    generar_bcp()
    generar_bbva()
    generar_interbank()
    generar_libro()
    for p in sorted(DESTINO.iterdir()):
        print("✔", p.relative_to(DESTINO.parent))
