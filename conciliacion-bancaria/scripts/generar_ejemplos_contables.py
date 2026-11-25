"""Genera archivos contables de ejemplo (ficticios) en ./ejemplos/contable.

Empresa: COMERCIAL ANDINA S.A.C. (RUC ficticio 20609876540), octubre 2026.
Cada archivo imita un origen distinto y trae errores sembrados a propósito para
demostrar el motor de validación (ver README de la fase 2):

  plan_cuentas_concar.xlsx        Plan con naturaleza, movimiento, estado y destinos (CONCAR-like)
  centros_costo.csv               Maestro de centros de costo (separador «;»)
  tipos_cambio_2026-10.csv        Tipos de cambio USD (con un salto atípico)
  proveedores.xlsx                Maestro de proveedores (un RUC inválido)
  saldos_iniciales_2026.xlsx      Apertura del ejercicio
  diario_concar_2026-10.xlsx      Diario con títulos, subtotales por asiento, total general y errores
  diario_sap_2026-10.csv          Diario estilo SAP: «;», decimales con coma, fechas dd.mm.aaaa, claves 40/50
  compras_2026-10.txt             Registro de compras en TXT con «|» y SIN encabezado (estilo PLE)
  balance_comprobacion_2026-10.xls  Balance en Excel 97-2003 con encabezado en dos filas y niveles

Uso:  python scripts/generar_ejemplos_contables.py
"""
import csv
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

D = Decimal
DESTINO = Path(__file__).resolve().parent.parent / "ejemplos" / "contable"

PLAN = [  # código, descripción, nivel, naturaleza, movimiento, estado, requiere CC, destino debe, destino haber
    ("10", "EFECTIVO Y EQUIVALENTES DE EFECTIVO", 2, "D", "N", "Activo", "N", "", ""),
    ("104", "CUENTAS CORRIENTES EN INSTITUCIONES FINANCIERAS", 3, "D", "N", "Activo", "N", "", ""),
    ("104101", "BCP CTA CTE MN", 6, "D", "S", "Activo", "N", "", ""),
    ("104102", "BBVA CTA CTE ME", 6, "D", "S", "Activo", "N", "", ""),
    ("12", "CUENTAS POR COBRAR COMERCIALES - TERCEROS", 2, "D", "N", "Activo", "N", "", ""),
    ("1212", "EMITIDAS EN CARTERA", 4, "D", "S", "Activo", "N", "", ""),
    ("20", "MERCADERÍAS", 2, "D", "N", "Activo", "N", "", ""),
    ("2011", "MERCADERÍAS MANUFACTURADAS", 4, "D", "S", "Activo", "N", "", ""),
    ("40", "TRIBUTOS POR PAGAR", 2, "A", "N", "Activo", "N", "", ""),
    ("40111", "IGV - CUENTA PROPIA", 5, "A", "S", "Activo", "N", "", ""),
    ("41", "REMUNERACIONES POR PAGAR", 2, "A", "N", "Activo", "N", "", ""),
    ("4111", "SUELDOS Y SALARIOS POR PAGAR", 4, "A", "S", "Activo", "N", "", ""),
    ("42", "CUENTAS POR PAGAR COMERCIALES - TERCEROS", 2, "A", "N", "Activo", "N", "", ""),
    ("4212", "EMITIDAS", 4, "A", "S", "Activo", "N", "", ""),
    ("46", "CUENTAS POR PAGAR DIVERSAS", 2, "A", "N", "Activo", "N", "", ""),
    ("4699", "OTRAS CUENTAS POR PAGAR (EN DESUSO)", 4, "A", "S", "Inactivo", "N", "", ""),
    ("48", "PROVISIONES", 2, "A", "N", "Activo", "N", "", ""),
    ("4811", "PROVISIÓN PARA LITIGIOS", 4, "A", "S", "Activo", "N", "", ""),
    ("50", "CAPITAL", 2, "A", "N", "Activo", "N", "", ""),
    ("5011", "ACCIONES", 4, "A", "S", "Activo", "N", "", ""),
    ("62", "GASTOS DE PERSONAL", 2, "D", "N", "Activo", "N", "", ""),
    ("6211", "SUELDOS Y SALARIOS", 4, "D", "S", "Activo", "S", "9411", "791"),
    ("63", "GASTOS DE SERVICIOS PRESTADOS POR TERCEROS", 2, "D", "N", "Activo", "N", "", ""),
    ("6311", "TRANSPORTE DE CARGA", 4, "D", "S", "Activo", "S", "9511", "791"),
    ("6361", "ENERGÍA ELÉCTRICA", 4, "D", "S", "Activo", "S", "9411", "791"),
    ("70", "VENTAS", 2, "A", "N", "Activo", "N", "", ""),
    ("7011", "MERCADERÍAS MANUFACTURADAS - TERCEROS", 4, "A", "S", "Activo", "N", "", ""),
    ("78", "CARGAS CUBIERTAS POR PROVISIONES", 2, "A", "S", "Activo", "N", "", ""),
    ("79", "CARGAS IMPUTABLES A CUENTAS DE COSTOS Y GASTOS", 2, "A", "N", "Activo", "N", "", ""),
    ("791", "CARGAS IMPUTABLES A CUENTAS DE COSTOS Y GASTOS", 3, "A", "S", "Activo", "N", "", ""),
    ("94", "GASTOS ADMINISTRATIVOS", 2, "D", "N", "Activo", "N", "", ""),
    ("9411", "GASTOS ADMINISTRATIVOS", 4, "D", "S", "Activo", "N", "", ""),
    ("95", "GASTOS DE VENTAS", 2, "D", "N", "Activo", "N", "", ""),
    ("9511", "GASTOS DE VENTAS", 4, "D", "S", "Activo", "N", "", ""),
]

SALDOS_INICIALES = [("104101", D("50000.00"), D("0")), ("104102", D("68000.00"), D("0")),
                    ("1212", D("12000.00"), D("0")), ("2011", D("30000.00"), D("0")),
                    ("4212", D("0"), D("10000.00")), ("5011", D("0"), D("150000.00"))]

# Diario CONCAR: (subdiario, número, fecha, cuenta, anexo, glosa, CC, moneda, TC, debe, haber, debe ME, haber ME, TD, serie, número)
R, P = "20100047218", "20555123451"
F = date(2026, 10, 1)
CONCAR = [
    ("05", "0001", F + timedelta(4), [("1212", R, "VENTA F001-245", "", "PEN", None, "1180.00", "", "01", "F001", "245"),
                                      ("40111", R, "VENTA F001-245", "", "PEN", None, "", "180.00", "01", "F001", "245"),
                                      ("7011", R, "VENTA F001-245", "", "PEN", None, "", "1000.00", "01", "F001", "245")]),
    ("03", "0002", F + timedelta(6), [("6361", P, "LUZ OCTUBRE", "ADM", "PEN", None, "500.00", "", "01", "E001", "889"),
                                      ("40111", P, "LUZ OCTUBRE", "", "PEN", None, "90.00", "", "01", "E001", "889"),
                                      ("4212", P, "LUZ OCTUBRE", "", "PEN", None, "", "590.00", "01", "E001", "889"),
                                      ("9411", "", "DESTINO LUZ", "ADM", "PEN", None, "500.00", "", "", "", ""),
                                      ("791", "", "DESTINO LUZ", "", "PEN", None, "", "500.00", "", "", "")]),
    # Sin destino → DES001; centro de costo inexistente → CC001
    ("03", "0003", F + timedelta(7), [("6311", P, "FLETE LIMA-AREQUIPA", "PRD", "PEN", None, "300.00", "", "01", "E001", "901"),
                                      ("40111", P, "FLETE LIMA-AREQUIPA", "", "PEN", None, "54.00", "", "01", "E001", "901"),
                                      ("4212", P, "FLETE LIMA-AREQUIPA", "", "PEN", None, "", "354.00", "01", "E001", "901")]),
    # Destino 9 = 5,000 pero 79 = 4,500 → DES002 (posible duplicidad)
    ("35", "0004", F + timedelta(29), [("6211", "", "PLANILLA OCTUBRE", "ADM", "PEN", None, "5000.00", "", "", "", ""),
                                       ("4111", "", "PLANILLA OCTUBRE", "", "PEN", None, "", "5000.00", "", "", ""),
                                       ("9411", "", "DESTINO PLANILLA", "ADM", "PEN", None, "5000.00", "", "", "", ""),
                                       ("791", "", "DESTINO PLANILLA", "", "PEN", None, "", "4500.00", "", "", ""),
                                       ("2011", "", "AJUSTE DESTINO", "", "PEN", None, "", "500.00", "", "", "")]),
    # Cobranza en dólares: TC 3.72 distinto al publicado (3.745) → TC002
    ("01", "0005", F + timedelta(9), [("104102", R, "COBRANZA USD", "", "USD", "3.72", "3720.00", "", "", "", ""),
                                      ("1212", R, "COBRANZA USD", "", "USD", "3.72", "", "3720.00", "", "", "")]),
    # Descuadrado → PD001
    ("01", "0006", F + timedelta(11), [("104101", R, "COBRANZA F001-230", "", "PEN", None, "1000.00", "", "01", "F001", "230"),
                                       ("1212", R, "COBRANZA F001-230", "", "PEN", None, "", "990.00", "01", "F001", "230")]),
    # Cuenta inexistente → CTA001
    ("01", "0007", F + timedelta(12), [("109999", "", "FONDO FIJO", "", "PEN", None, "200.00", "", "", "", ""),
                                       ("104101", "", "FONDO FIJO", "", "PEN", None, "", "200.00", "", "", "")]),
    # Cuenta de título (104) e inactiva (4699) → CTA003 / CTA002
    ("01", "0008", F + timedelta(13), [("104", "", "COMISION", "", "PEN", None, "50.00", "", "", "", ""),
                                       ("4699", "", "COMISION", "", "PEN", None, "", "50.00", "", "", "")]),
    # Fecha fuera del periodo → FEC002
    ("05", "0009", date(2026, 9, 15), [("1212", R, "VENTA F001-199", "", "PEN", None, "236.00", "", "01", "F001", "199"),
                                       ("40111", R, "VENTA F001-199", "", "PEN", None, "", "36.00", "01", "F001", "199"),
                                       ("7011", R, "VENTA F001-199", "", "PEN", None, "", "200.00", "01", "F001", "199")]),
    # Misma factura en otro asiento con igual cuenta e importe → DUP001
    ("05", "0010", F + timedelta(20), [("1212", R, "VENTA F001-245", "", "PEN", None, "1180.00", "", "01", "F001", "245"),
                                       ("40111", R, "VENTA F001-245", "", "PEN", None, "", "180.00", "01", "F001", "245"),
                                       ("7011", R, "VENTA F001-245", "", "PEN", None, "", "1000.00", "01", "F001", "245")]),
    # Aplicación de provisión sin abono a 78 → DES006
    ("01", "0011", F + timedelta(25), [("4811", "", "PAGO LITIGIO PROVISIONADO", "", "PEN", None, "800.00", "", "", "", ""),
                                       ("104101", "", "PAGO LITIGIO PROVISIONADO", "", "PEN", None, "", "800.00", "", "", "")]),
    # Importe con formato inválido → IMP001 (crítico) y diferencia contra el total del archivo → TOT001
    ("01", "0012", F + timedelta(26), [("104101", "", "DEPOSITO", "", "PEN", None, "1,2a0.00", "", "", "", ""),
                                       ("5011", "", "DEPOSITO", "", "PEN", None, "", "1200.00", "", "", "")]),
]


def _d(v):
    return D(v) if v and v.replace(".", "").isdigit() else D("0")


def generar_plan():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Plan"
    ws.append(["COMERCIAL ANDINA S.A.C."])
    ws.append(["PLAN DE CUENTAS 2026"])
    ws.append([])
    ws.append(["Código", "Descripción", "Nivel", "Naturaleza", "Movimiento", "Estado", "Pide CC", "Destino Debe",
               "Destino Haber"])
    for f in PLAN:
        ws.append(list(f))
    wb.save(DESTINO / "plan_cuentas_concar.xlsx")


def generar_maestros():
    with open(DESTINO / "centros_costo.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Código", "Descripción", "Cuenta destino", "Estado"])
        w.writerow(["ADM", "ADMINISTRACIÓN", "9411", "Activo"])
        w.writerow(["VEN", "VENTAS", "9511", "Activo"])
    with open(DESTINO / "tipos_cambio_2026-10.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Fecha", "Moneda", "Compra", "Venta"])
        base = D("3.738")
        for i in range(31):
            dia = F + timedelta(i)
            compra = base + D(i) / 1000
            venta = compra + D("0.007")
            if dia.day == 20:
                compra, venta = D("3.950"), D("3.958")  # salto atípico → TC004
            w.writerow([f"{dia:%d/%m/%Y}", "USD", f"{compra:.3f}", f"{venta:.3f}"])
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Tipo Doc Identidad", "RUC", "Razón Social", "Dirección", "Estado", "Condición"])
    ws.append(["6", P, "ENERGIA DEL SUR S.A.", "AV. LOS PROCERES 123, LIMA", "ACTIVO", "HABIDO"])
    ws.append(["6", "20100047218", "TRANSPORTES ANDINOS S.A.C.", "JR. PUNO 456, LIMA", "ACTIVO", "HABIDO"])
    ws.append(["6", "20123456789", "PROVEEDOR CON RUC ERRADO", "CALLE 1", "ACTIVO", "HABIDO"])  # TER001
    wb.save(DESTINO / "proveedores.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(["Cuenta", "Descripción", "Debe", "Haber"])
    for c, d_, h in SALDOS_INICIALES:
        ws.append([c, dict((p[0], p[1]) for p in PLAN)[c], float(d_) or None, float(h) or None])
    wb.save(DESTINO / "saldos_iniciales_2026.xlsx")


def generar_concar():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Diario"
    ws.append(["COMERCIAL ANDINA S.A.C.", None, None, "RUC 20609876540"])
    ws.append(["LIBRO DIARIO - OCTUBRE 2026"])
    ws.append([])
    ws.append(["Sub Diario", "Nro Comprobante", "Fecha", "Cuenta", "Anexo", "Glosa", "Centro Costo", "Moneda", "T.C.",
               "Debe MN", "Haber MN", "Debe ME", "Haber ME", "Tipo Doc", "Serie", "Número"])
    total_d = total_h = D("0")
    for sub, num, fecha, lineas in CONCAR:
        sd = sh = D("0")
        for cta, anexo, glosa, cc, mon, tc, debe, haber, td, serie, numero in lineas:
            me_d = me_h = None
            if mon == "USD":
                me_d = float(_d(debe) / D(tc)) if debe else None
                me_h = float(_d(haber) / D(tc)) if haber else None
            ws.append([sub, num, fecha, cta, anexo or None, glosa, cc or None, mon, float(tc) if tc else None,
                       float(_d(debe)) if debe and _d(debe) else (debe or None), float(_d(haber)) if haber else None,
                       me_d, me_h, td or None, serie or None, numero or None])
            sd += _d(debe)
            sh += _d(haber)
        if num == "0012":
            sd += D("1200.00")  # el reporte original sí sumó el importe que llegó mal formateado
        ws.append([None, None, None, None, None, f"Total comprobante {sub}-{num}", None, None, None, float(sd), float(sh)])
        ws.append([])
        total_d += sd
        total_h += sh
    ws.append([None, None, None, None, None, "TOTAL GENERAL", None, None, None, float(total_d), float(total_h)])
    for fila in ws.iter_rows(min_row=5, min_col=3, max_col=3):
        for c in fila:
            c.number_format = "DD/MM/YYYY"
    wb.save(DESTINO / "diario_concar_2026-10.xlsx")


def generar_sap():
    """SAP: «Nº documento» es el número de asiento y «Referencia» el comprobante; importes positivos con clave 40/50."""
    asientos = [
        ("SA", "100000201", date(2026, 10, 3), [("40", "6311", "VEN", "FLETE DESPACHO", "E001-950", "300,00"),
                                                ("40", "40111", "", "IGV FLETE", "E001-950", "54,00"),
                                                ("50", "4212", "", "TRANSPORTES ANDINOS", "E001-950", "354,00"),
                                                ("40", "9511", "VEN", "DESTINO FLETE", "", "300,00"),
                                                ("50", "791", "", "DESTINO FLETE", "", "300,00")]),
        ("SA", "100000202", date(2026, 10, 18), [("40", "104101", "", "COBRANZA F001-245", "F001-245", "1.180,00"),
                                                 ("50", "1212", "", "COBRANZA F001-245", "F001-245", "1.180,00")]),
        ("KR", "100000203", date(2026, 10, 22), [("40", "2011", "", "COMPRA MERCADERIA", "F002-5521", "10.000,00"),
                                                 ("40", "40111", "", "IGV COMPRA", "F002-5521", "1.800,00"),
                                                 ("50", "4212", "", "TEXTILES LIMA", "F002-5521", "11.800,00")]),
    ]
    with open(DESTINO / "diario_sap_2026-10.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Clase de documento", "Nº documento", "Fecha de contabilización", "Pos.", "Clave contabiliz.",
                    "Cuenta", "Centro de coste", "Texto", "Referencia", "Importe en moneda local", "Moneda"])
        for clase, num, fecha, lineas in asientos:
            for i, (clave, cta, ceco, texto, ref, imp) in enumerate(lineas, 1):
                w.writerow([clase, num, f"{fecha:%d.%m.%Y}", i, clave, cta, ceco, texto, ref, imp, "PEN"])


def generar_compras():
    """Registro de compras sin encabezado, separado por «|» (columnas: periodo|CUO|emisión|vencimiento|TD|serie|número|
    TDI|RUC|razón social|base|IGV|no gravado|total|moneda|TC)."""
    filas = [
        ("20261000", "M0001", "07/10/2026", "06/11/2026", "01", "E001", "889", "6", P, "ENERGIA DEL SUR S.A.",
         "500.00", "90.00", "0.00", "590.00", "PEN", ""),
        ("20261000", "M0002", "08/10/2026", "07/11/2026", "01", "E001", "901", "6", "20100047218",
         "TRANSPORTES ANDINOS S.A.C.", "300.00", "54.00", "0.00", "354.00", "PEN", ""),
        # IGV mal calculado y total que no cuadra → REG002 / REG001
        ("20261000", "M0003", "12/10/2026", "11/11/2026", "01", "F002", "5521", "6", "20100047218",
         "TRANSPORTES ANDINOS S.A.C.", "1000.00", "150.00", "0.00", "1200.00", "PEN", ""),
        # RUC inválido → TER001 ; proveedor no registrado → TER002
        ("20261000", "M0004", "15/10/2026", "14/11/2026", "01", "F010", "77", "6", "20123456788",
         "PROVEEDOR DESCONOCIDO", "100.00", "18.00", "0.00", "118.00", "PEN", ""),
        # Comprobante de agosto anotado en octubre → FEC002 informativo
        ("20261000", "M0005", "20/08/2026", "19/09/2026", "01", "E001", "850", "6", P, "ENERGIA DEL SUR S.A.",
         "400.00", "72.00", "0.00", "472.00", "PEN", ""),
        # Duplicado → DUP001
        ("20261000", "M0006", "07/10/2026", "06/11/2026", "01", "E001", "889", "6", P, "ENERGIA DEL SUR S.A.",
         "500.00", "90.00", "0.00", "590.00", "PEN", ""),
    ]
    with open(DESTINO / "compras_2026-10.txt", "w", encoding="utf-8", newline="") as fh:
        for f in filas:
            fh.write("|".join(f) + "|\r\n")


def generar_balance():
    """Balance construido a partir de los saldos iniciales y del diario CONCAR válido, con niveles de resumen."""
    import xlwt
    mov = defaultdict(lambda: [D("0"), D("0")])
    for _, num, fecha, lineas in CONCAR:
        if num == "0012":
            continue  # la línea con importe inválido no llega a procesarse
        for linea in lineas:
            cta, debe, haber = linea[0], linea[6], linea[7]
            mov[cta][0] += _d(debe)
            mov[cta][1] += _d(haber)
    ini = {c: d_ - h for c, d_, h in SALDOS_INICIALES}
    cuentas = sorted(set(mov) | set(ini))
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Balance")
    ws.write(0, 0, "BALANCE DE COMPROBACIÓN AL 31/10/2026")
    grupos = ["", "", "Saldos iniciales", "", "Movimientos", "", "Saldos finales", ""]
    for i, g in enumerate(grupos):
        if g:
            ws.write(2, i, g)
    for i, h in enumerate(["Cuenta", "Descripción", "Deudor", "Acreedor", "Debe", "Haber", "Deudor", "Acreedor"]):
        ws.write(3, i, h)
    nombres = {p[0]: p[1] for p in PLAN}
    fila = 4
    resumen = defaultdict(lambda: [D("0")] * 6)
    detalle = []
    for c in cuentas:
        si = ini.get(c, D("0"))
        d_, h = mov[c]
        sf = si + d_ - h
        valores = [max(si, D(0)), max(-si, D(0)), d_, h, max(sf, D(0)), max(-sf, D(0))]
        if c == "7011":
            valores[5] += D("100")  # saldo final mal calculado → SAL001
        detalle.append((c, valores))
        resumen[c[:2]] = [a + b for a, b in zip(resumen[c[:2]], valores)]
    for c, valores in sorted(detalle + [(k, v) for k, v in resumen.items() if k not in dict(detalle)]):
        ws.write(fila, 0, c)
        ws.write(fila, 1, nombres.get(c, ""))
        for i, v in enumerate(valores):
            ws.write(fila, 2 + i, float(v))
        fila += 1
    wb.save(str(DESTINO / "balance_comprobacion_2026-10.xls"))


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    generar_plan()
    generar_maestros()
    generar_concar()
    generar_sap()
    generar_compras()
    generar_balance()
    for p in sorted(DESTINO.iterdir()):
        print("✔", p.relative_to(DESTINO.parent.parent))
