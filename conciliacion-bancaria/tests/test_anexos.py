"""Pruebas de la fase 5: generador de anexos contables.

El libro se importa por el flujo real (fase 2); las compensaciones se proponen y aprueban con el motor
de la fase 4; los registros auxiliares (activos, cronogramas, contratos, servicios) se importan como
CSV. Cada prueba verifica que los importes del anexo coincidan con la información contable original.
"""
import io
import json
import time
from datetime import date
from decimal import Decimal

import pytest

from tests.test_analisis import importar_bytes
from tests.test_compensacion import CAB, DIARIO_2025, DIARIO_2026, T
from tests.test_compensacion import compra as compra4
from tests.test_compensacion import fila as fila4

D = Decimal
SUNAT = "20131312955"
W1, W2, E1, BCP = "45678912", "41234567", "40111222", "20100047218"
CAB5 = CAB + ";Centro Costo;Proyecto"


def asiento(sub, asi, fecha, lineas):
    """Como en la fase 4, con centro de costo y proyecto."""
    out = []
    for cuenta, ter, kw in lineas:
        kw = dict(kw)
        cc, proyecto = kw.pop("cc", "") or "", kw.pop("proyecto", "") or ""
        out.append(fila4(sub, asi, fecha, cuenta, ter, **kw) + [cc, proyecto])
    return out


def compra(*a, **k):
    return [f + ["", ""] for f in compra4(*a, **k)]


def csv(filas):
    filas = [f if len(f) == len(CAB5.split(";")) else f + ["", ""] for f in filas]
    return (CAB5 + "\n" + "\n".join(";".join(str(x) for x in f) for f in filas) + "\n").encode()

EXTRA_2026 = (
    # 1 · cuentas por cobrar con cobro parcial (cliente C2)
    asiento("05", "V2", "05/01/2026", [("1212", "C2", {"td": "01", "serie": "F002", "num": "2", "debe": "5000", "venc": "04/02/2026",
                                                        "glosa": "VENTA SERVICIO", "rs": "CLIENTE C2"}),
                                      ("7041", "C2", {"td": "01", "serie": "F002", "num": "2", "haber": "5000", "glosa": "VENTA SERVICIO",
                                                      "rs": "CLIENTE C2", "proyecto": None})]) +
    asiento("01", "CB2", "20/01/2026", [("104101", "C2", {"debe": "2000", "glosa": "COBRANZA PARCIAL F002-2", "rs": "CLIENTE C2"}),
                                        ("1212", "C2", {"td": "01", "serie": "F002", "num": "2", "haber": "2000", "glosa": "COBRANZA F002-2",
                                                        "rs": "CLIENTE C2"})]) +
    # 3 · entrega a rendir con rendición parcial
    asiento("21", "ER1", "05/01/2026", [("1413", E1, {"serie": "ER", "num": "1", "debe": "1500", "glosa": "ENTREGA A RENDIR VIATICOS", "rs": "TRABAJADOR E1"}),
                                        ("104101", E1, {"haber": "1500", "glosa": "BANCO", "rs": "TRABAJADOR E1"})]) +
    asiento("31", "RE1", "20/01/2026", [("6311", E1, {"debe": "1000", "glosa": "GASTOS DE VIAJE", "rs": "TRABAJADOR E1", "cc": "ADM"}),
                                        ("1413", E1, {"serie": "ER", "num": "1", "haber": "1000", "glosa": "RENDICION DE GASTOS ER-1", "rs": "TRABAJADOR E1"})]) +
    # 5 · servicio en proceso (cuenta 23) con costos del ejercicio por proyecto
    asiento("31", "SP1", "31/01/2026", [("6211", "", {"debe": "3000", "glosa": "MANO DE OBRA P-100", "proyecto": "P-100", "cc": "OPE"}),
                                        ("6343", "", {"debe": "2000", "glosa": "SERVICIO DE TERCEROS P-100", "proyecto": "P-100", "cc": "OPE"}),
                                        ("6561", "", {"debe": "1000", "glosa": "COMBUSTIBLE P-100", "proyecto": "P-100", "cc": "OPE"}),
                                        ("4111", W2, {"haber": "3000", "glosa": "PLANILLA ENERO", "rs": "TRABAJADOR W2"}),
                                        ("4212", "T1", {"td": "01", "serie": "F009", "num": "50", "haber": "3000", "glosa": "SERVICIOS Y COMBUSTIBLE"}),
                                        ("9211", "", {"debe": "6000", "glosa": "DESTINO COSTO SERVICIO P-100", "cc": "OPE"}),
                                        ("791", "", {"haber": "6000", "glosa": "CARGAS IMPUTABLES"})]) +
    asiento("31", "SP2", "31/01/2026", [("2311", "", {"debe": "6000", "glosa": "COSTO DEL SERVICIO EN PROCESO P-100", "proyecto": "P-100"}),
                                        ("7111", "", {"haber": "6000", "glosa": "VARIACION DE LA PRODUCCION", "proyecto": "P-100"})]) +
    # 4 · gastos administrativos por centro de costo con su destino
    asiento("31", "GA1", "31/01/2026", [("6361", "", {"debe": "800", "glosa": "ENERGIA ELECTRICA", "cc": "ADM", "td": "14", "serie": "S001", "num": "77"}),
                                        ("6351", "", {"debe": "1200", "glosa": "ALQUILER OFICINA", "cc": "ADM", "td": "01", "serie": "F010", "num": "5"}),
                                        ("4212", "T1", {"td": "01", "serie": "F010", "num": "5", "haber": "2000", "glosa": "GASTOS ADM"}),
                                        ("9411", "", {"debe": "2000", "glosa": "DESTINO GASTOS ADMINISTRATIVOS", "cc": "ADM"}),
                                        ("791", "", {"haber": "2000", "glosa": "CARGAS IMPUTABLES"})]) +
    # 6–7 · activo fijo: adición y depreciación del mes
    asiento("21", "AF1", "15/01/2026", [("3341", "", {"debe": "30000", "glosa": "COMPRA CAMION AF-2", "td": "01", "serie": "F020", "num": "9"}),
                                        ("104101", "", {"haber": "30000", "glosa": "BANCO"})]) +
    asiento("31", "DP1", "31/01/2026", [("6814", "", {"debe": "1000", "glosa": "DEPRECIACION ENERO", "cc": "OPE"}),
                                        ("3913", "", {"haber": "1000", "glosa": "DEPRECIACION ENERO"})]) +
    # 8 · obligación financiera (préstamo PR-001) y pago de la primera cuota
    asiento("21", "PR1", "02/01/2026", [("104101", BCP, {"debe": "60000", "glosa": "DESEMBOLSO PRESTAMO PR-001", "rs": "BANCO DE CREDITO"}),
                                        ("4511", BCP, {"haber": "60000", "glosa": "DESEMBOLSO PRESTAMO PR-001", "ref": "PR-001", "rs": "BANCO DE CREDITO"})]) +
    asiento("21", "PR2", "31/01/2026", [("4511", BCP, {"debe": "2500", "glosa": "CUOTA 1 PRESTAMO PR-001", "ref": "PR-001", "rs": "BANCO DE CREDITO"}),
                                        ("6731", BCP, {"debe": "600", "glosa": "INTERESES CUOTA 1 PR-001", "rs": "BANCO DE CREDITO"}),
                                        ("104101", BCP, {"haber": "3100", "glosa": "BANCO", "rs": "BANCO DE CREDITO"})]) +
    # 9 · tributos: IGV del periodo (y un crédito), EsSalud declarado y pagado
    asiento("31", "TR1", "31/01/2026", [("6271", "", {"debe": "900", "glosa": "ESSALUD ENERO", "cc": "ADM"}),
                                        ("4031", SUNAT, {"serie": "PDT", "num": "202601", "haber": "900", "glosa": "ESSALUD ENERO", "rs": "SUNAT"}),
                                        ("40111", SUNAT, {"serie": "IGV", "num": "202601", "haber": "900", "glosa": "IGV VENTAS ENERO", "rs": "SUNAT"}),
                                        ("1212", "C2", {"debe": "900", "glosa": "IGV F002-2", "rs": "CLIENTE C2", "td": "01", "serie": "F002", "num": "2B"}),
                                        ("9411", "", {"debe": "900", "glosa": "DESTINO ESSALUD", "cc": "ADM"}),
                                        ("791", "", {"haber": "900", "glosa": "CARGAS IMPUTABLES"})]) +
    asiento("21", "TR2", "28/01/2026", [("4031", SUNAT, {"serie": "PDT", "num": "202601", "debe": "900", "glosa": "PAGO ESSALUD ENERO", "rs": "SUNAT"}),
                                        ("104101", SUNAT, {"haber": "900", "glosa": "BANCO", "rs": "SUNAT"})]) +
    # 10 · remuneraciones: planilla, pago parcial y CTS
    asiento("35", "PL1", "31/01/2026", [("6211", "", {"debe": "2500", "glosa": "PLANILLA ENERO W1", "cc": "ADM"}),
                                        ("6291", "", {"debe": "500", "glosa": "CTS ENERO W1", "cc": "ADM"}),
                                        ("4111", W1, {"haber": "2500", "glosa": "PLANILLA ENERO", "rs": "TRABAJADOR W1"}),
                                        ("4151", W1, {"haber": "500", "glosa": "CTS ENERO", "rs": "TRABAJADOR W1"}),
                                        ("9411", "", {"debe": "3000", "glosa": "DESTINO PLANILLA", "cc": "ADM"}),
                                        ("791", "", {"haber": "3000", "glosa": "CARGAS IMPUTABLES"})]) +
    asiento("21", "PL2", "31/01/2026", [("4111", W1, {"debe": "2000", "glosa": "PAGO PLANILLA ENERO", "rs": "TRABAJADOR W1"}),
                                        ("4111", W2, {"debe": "3000", "glosa": "PAGO PLANILLA ENERO", "rs": "TRABAJADOR W2"}),
                                        ("104101", "", {"haber": "5000", "glosa": "BANCO"})]) +
    # 14 · seguro pagado por anticipado sin devengo registrado (genera una diferencia real)
    asiento("21", "SG1", "01/01/2026", [("1821", "20100041953", {"td": "01", "serie": "F777", "num": "12", "debe": "12000", "glosa": "POLIZA SEGURO 2026",
                                                                 "rs": "ASEGURADORA"}),
                                        ("104101", "20100041953", {"haber": "12000", "glosa": "BANCO", "rs": "ASEGURADORA"})]) +
    # 15 · factura en moneda extranjera pendiente
    compra("A9B", "10/01/2026", "T9", "F001", "91", "1875", venc="09/02/2026", mon="USD", tc="3.75", me="500")
)
APERTURA_EXTRA_2026 = ("Cuenta;RUC;Debe;Haber\n3341;;120000;\n3913;;;24000\n2311;;5000;\n5011;;;101000\n").encode()

ACTIVOS = ("codigo;cuenta;descripcion;categoria;fecha_adquisicion;fecha_uso;costo_inicial;adiciones;vida_util_meses;valor_residual;"
           "cuenta_depreciacion;depreciacion_acumulada_inicial;tasa_tributaria;ubicacion\n"
           "AF-1;3341;CAMION VOLVO FH;VEHICULOS;01/01/2024;01/01/2024;120000;;120;0;3913;24000;20;LIMA\n"
           "AF-2;3341;CAMION ISUZU;VEHICULOS;15/01/2026;01/02/2026;30000;;60;0;3913;0;20;AREQUIPA\n").encode()
CONTRATOS = ("contrato;cuenta;entidad;ruc_entidad;tipo;moneda;capital;tasa;fecha_desembolso;garantias\n"
             f"PR-001;4511;BANCO DE CREDITO;{BCP};PRESTAMO;PEN;60000;12;02/01/2026;HIPOTECA INMUEBLE LIMA\n").encode()
CUOTAS = ("contrato;numero;fecha_vencimiento;capital;interes;comision;pagada\n" + "".join(
    f"PR-001;{n};{date(2026 + (n - 1) // 12, (n - 1) % 12 + 1, 28).strftime('%d/%m/%Y') if n > 1 else '31/01/2026'};2500;{600 - 20 * n};10;{'S' if n == 1 else 'N'}\n"
    for n in range(1, 25))).encode()
SEGUROS = ("codigo;cuenta;tipo;concepto;proveedor;ruc;serie;numero;importe;fecha_documento;fecha_inicio;fecha_fin\n"
           "POL-2026;1821;SEGURO;POLIZA VEHICULAR 2026;ASEGURADORA;20100041953;F777;12;12000;01/01/2026;01/01/2026;31/12/2026\n").encode()
SERVICIOS = ("proyecto;cuenta;cliente;contrato;orden_servicio;maquinaria;centro_costo;fecha_inicio;fecha_estimada;fecha_real;"
             "estado_operativo;estado_facturacion;costo_acumulado_anterior\n"
             "P-100;2311;MINERA ANDINA;CT-55;OS-901;CAMION AF-1;OPE;01/11/2025;15/01/2026;20/01/2026;CULMINADO;PENDIENTE DE FACTURAR;5000\n").encode()


def q(e, **k):
    return {"empresa_id": e, **k}


def subir_registro(cliente, e, tipo, nombre, contenido):
    r = cliente.post("/api/anexos/registros/importar", params=q(e), data={"tipo": tipo}, files={"archivo": (nombre, contenido)})
    assert r.status_code == 201, r.text
    assert not r.json()["errores"], r.json()
    return r.json()


@pytest.fixture()
def emp(cliente, monkeypatch):
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    e = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Anexos del Sur SAC"}).json()["id"]
    ap = f"Cuenta;RUC;Debe;Haber\n4212;{T['T13']};;500\n104101;;50000;\n5011;;;49500\n".encode()
    importar_bytes(cliente, e, "apertura_2025.csv", ap, "SALDOS_INICIALES", periodo=0, ejercicio=2025)
    importar_bytes(cliente, e, "diario_2025.csv", csv(DIARIO_2025), "DIARIO", periodo=None, ejercicio=2025)
    ap26 = f"Cuenta;RUC;Debe;Haber\n4212;{T['T10']};;2000\n4212;{T['T13']};;500\n104101;;50000;\n5011;;;47500\n".encode()
    importar_bytes(cliente, e, "apertura_2026.csv", ap26, "SALDOS_INICIALES", periodo=0, ejercicio=2026)
    importar_bytes(cliente, e, "apertura_2026_b.csv", APERTURA_EXTRA_2026, "SALDOS_INICIALES", periodo=0, ejercicio=2026)
    importar_bytes(cliente, e, "diario_2026.csv", csv(DIARIO_2026 + EXTRA_2026), "DIARIO", periodo=None, ejercicio=2026)
    subir_registro(cliente, e, "ACTIVO_FIJO", "activos.csv", ACTIVOS)
    subir_registro(cliente, e, "CONTRATO_FINANCIERO", "contratos.csv", CONTRATOS)
    subir_registro(cliente, e, "CUOTA_FINANCIERA", "cuotas.csv", CUOTAS)
    subir_registro(cliente, e, "GASTO_ANTICIPADO", "seguros.csv", SEGUROS)
    subir_registro(cliente, e, "SERVICIO_PROCESO", "servicios.csv", SERVICIOS)
    # fase 4: el motor propone y un supervisor aprueba las coincidencias inequívocas
    r = cliente.post("/api/compensacion/ejecuciones", params=q(e), json={"fecha_corte": "2026-01-31"})
    assert r.status_code == 202, r.text
    grupos = cliente.get("/api/compensacion/grupos", params=q(e, estado="PROPUESTA", por_pagina=500)).json()["items"]
    ids = [g["id"] for g in grupos if g["confianza"] in ("MUY_ALTA", "ALTA")]
    r = cliente.post("/api/compensacion/grupos/aprobar-lote", params=q(e), json={"grupos": ids}, headers={"X-Usuario": "supervisor.f4"})
    assert r.status_code == 200 and not r.json()["errores"], r.text
    return e


def generar(cliente, e, cuentas=None, corte="2026-01-31", modo="CUENTAS", usuario="ana.contadora", **extra):
    body = {"fecha_corte": corte, "modo": modo, **extra}
    if cuentas:
        body["cuentas"] = cuentas
    r = cliente.post("/api/anexos/generaciones", params=q(e), json=body, headers={"X-Usuario": usuario})
    assert r.status_code == 202, r.text
    run = cliente.get(f"/api/anexos/generaciones/{r.json()['run_id']}", params=q(e)).json()
    assert run["estado"] == "COMPLETADO", run
    return run


def anexo(cliente, e, cuenta, corte="2026-01-31", **extra):
    lst = cliente.get("/api/anexos/anexos", params=q(e, cuenta=cuenta, fecha_corte=corte, por_pagina=500)).json()["items"]
    a = next(x for x in lst if x["cuenta"] == cuenta and all(x.get(k) == v for k, v in extra.items()))
    return cliente.get(f"/api/anexos/anexos/{a['id']}", params=q(e)).json()


def detalle(cliente, e, anexo_id, **params):
    r = cliente.get(f"/api/anexos/anexos/{anexo_id}/detalle", params=q(e, por_pagina=2000, **params))
    assert r.status_code == 200, r.text
    return r.json()


def libro(cliente, e, cuenta, ejercicio=2026, hasta=1):
    """Saldo final del balance de la fase 3 (deudor positivo), calculado de forma independiente."""
    nodos = {n["cuenta"]: n for n in cliente.get("/api/analisis/balance", params=q(e, ejercicio=ejercicio, desde=1, hasta=hasta)).json()["nodos"]}
    return D(nodos[cuenta]["saldo_final"]) if cuenta in nodos else D(0)


def fila_de(det, **cond):
    return next(f for f in det["filas"] if all(f.get(k) == v for k, v in cond.items()))


# ===================================================================== 1–4
def test_01_cuentas_por_cobrar_con_pagos_parciales(cliente, emp):
    generar(cliente, emp, ["1212"])
    a = anexo(cliente, emp, "1212")
    r = a["resumen"]
    assert D(r["saldo_final_contable"]) == libro(cliente, emp, "1212") == D("2360") - D("2360") + D("5000") - D("2000") + D("900")
    det = detalle(cliente, emp, a["anexo"]["id"])
    f = fila_de(det, documento="F002-2")
    assert (D(f["importe_original"]), D(f["cobros_pagos"]), D(f["saldo"])) == (D("5000"), D("2000"), D("3000"))
    assert f["linea_id"] and f["item_id"] and f["tramo"] == "No vencido" and f["estado_sustento"] == "DOCUMENTADO"
    assert D(r["diferencia"]) == 0 and D(r["saldo_detalle"]) == D("3900")
    assert a["anexo"]["estado_revision"] == "GENERADO" and a["anexo"]["resultado"] in ("CUADRADO", "CUADRADO_CON_OBSERVACIONES")
    # trazabilidad hasta el asiento original (fase 3)
    asi = cliente.get(f"/api/analisis/lineas/{f['linea_id']}/asiento", params=q(emp)).json()
    assert any(x["cuenta"] == "1212" for x in asi["lineas"])


def test_02_cuentas_por_pagar_con_nota_de_credito(cliente, emp):
    generar(cliente, emp, ["4212"])
    a = anexo(cliente, emp, "4212")
    det = detalle(cliente, emp, a["anexo"]["id"])
    f = fila_de(det, documento="F001-5", tercero=T["T5"])
    assert (D(f["importe_original"]), D(f["notas_credito"]), D(f["saldo"])) == (D("5000"), D("1000"), D("4000"))
    assert D(a["resumen"]["saldo_final_contable"]) == -libro(cliente, emp, "4212")  # cuenta acreedora: signo natural
    assert D(a["resumen"]["diferencia"]) == 0


def test_03_entregas_a_rendir(cliente, emp):
    generar(cliente, emp, ["1413"])
    a = anexo(cliente, emp, "1413")
    assert a["plantilla"]["especialidad"] == "PERSONAL"
    f = fila_de(detalle(cliente, emp, a["anexo"]["id"]), documento="ER-1")
    assert (D(f["entregado"]), D(f["rendiciones"]), D(f["saldo"])) == (D("1500"), D("1000"), D("500"))
    assert f["categoria"] == "Entrega a rendir"
    assert D(a["resumen"]["saldo_final_contable"]) == libro(cliente, emp, "1413") == D("500") and D(a["resumen"]["diferencia"]) == 0


def test_04_anticipos_a_proveedores(cliente, emp):
    generar(cliente, emp, ["4221"])
    a = anexo(cliente, emp, "4221")
    # el anticipo de T6 se aplicó (con una regla entre cuentas): sin regla queda pendiente y así se muestra
    assert D(a["resumen"]["saldo_final_contable"]) == -libro(cliente, emp, "4221")
    assert D(a["resumen"]["diferencia"]) == 0
    det = detalle(cliente, emp, a["anexo"]["id"])
    assert sum(D(f["saldo"]) for f in det["filas"]) == D(a["resumen"]["saldo_final_contable"])


# ===================================================================== 5–8
def test_05_servicios_en_proceso_entre_ejercicios(cliente, emp):
    generar(cliente, emp, ["2311"])
    a = anexo(cliente, emp, "2311")
    r = a["resumen"]
    assert D(r["saldo_final_contable"]) == libro(cliente, emp, "2311") == D("11000")
    f = fila_de(detalle(cliente, emp, a["anexo"]["id"]), proyecto="P-100")
    assert (D(f["costo_anterior"]), D(f["costo_ejercicio"]), D(f["saldo"])) == (D("5000"), D("6000"), D("11000"))
    assert (D(f["mano_obra"]), D(f["servicios_terceros"]), D(f["combustible"])) == (D("3000"), D("2000"), D("1000"))
    assert f["estado_operativo"] == "CULMINADO" and f["estado_contable"] == "PENDIENTE DE EVALUACIÓN"
    assert f["estado_facturacion"] == "PENDIENTE DE FACTURAR"
    codigos = {h["codigo"] for h in a["hallazgos"]}
    assert "SERVICIO_CULMINADO_EN_23" in codigos and D(r["diferencia"]) == 0


def test_06_y_07_activos_fijos_y_depreciacion(cliente, emp):
    generar(cliente, emp, ["3341", "3913"])
    a = anexo(cliente, emp, "3341")
    assert D(a["resumen"]["saldo_final_contable"]) == libro(cliente, emp, "3341") == D("150000")
    det = detalle(cliente, emp, a["anexo"]["id"])
    assert {f["codigo_activo"]: D(f["saldo"]) for f in det["filas"]} == {"AF-1": D("120000"), "AF-2": D("30000")}
    assert a["anexo"]["resultado"] == "CUADRADO"
    d = anexo(cliente, emp, "3913")
    assert D(d["resumen"]["saldo_final_contable"]) == -libro(cliente, emp, "3913") == D("25000")
    det = detalle(cliente, emp, d["anexo"]["id"])
    af1 = fila_de(det, codigo_activo="AF-1")
    assert (D(af1["dep_inicial"]), D(af1["dep_periodo"]), D(af1["saldo"]), D(af1["valor_neto"])) == (D("24000"), D("1000"), D("25000"), D("95000"))
    assert D(af1["dep_tributaria"]) == D("2000") and D(af1["diferencia_tributaria"]) == D("-1000")  # financiera ≠ tributaria
    af2 = fila_de(det, codigo_activo="AF-2")
    assert D(af2["dep_periodo"]) == 0  # disponible para su uso desde febrero
    assert D(d["resumen"]["diferencia"]) == 0


def test_08_obligaciones_financieras(cliente, emp):
    generar(cliente, emp, ["4511"])
    a = anexo(cliente, emp, "4511")
    f = fila_de(detalle(cliente, emp, a["anexo"]["id"]), contrato="PR-001")
    assert D(f["saldo"]) == D("57500") == -libro(cliente, emp, "4511")
    assert (D(f["capital_original"]), D(f["amortizado_libros"]), D(f["capital_pendiente"])) == (D("60000"), D("2500"), D("57500"))
    assert (D(f["porcion_corriente"]), D(f["porcion_no_corriente"])) == (D("30000"), D("27500"))
    assert f["cuotas_vencidas"] == 0 and f["proximo_vencimiento"] == "2026-02-28" and f["garantias"].startswith("HIPOTECA")
    assert D(f["intereses"]) == D("580") and D(f["comisiones"]) == D("10")  # capital, intereses y comisiones separados
    assert D(a["resumen"]["diferencia"]) == 0


# ===================================================================== 9–12
def test_09_tributos_por_pagar(cliente, emp):
    generar(cliente, emp, ["40", "4031", "40111"])
    a = anexo(cliente, emp, "40")
    assert D(a["resumen"]["saldo_final_contable"]) == -libro(cliente, emp, "40")
    det = detalle(cliente, emp, a["anexo"]["id"])
    igv = [f for f in det["filas"] if f["tributo"] and f["tributo"].startswith("IGV – cuenta propia")]
    assert igv and D(igv[0]["determinado"]) == D("900") and igv[0]["exigible"] == "Sí" and igv[0]["periodo_tributario"] == "2026-01"
    assert not [f for f in det["filas"] if f["tributo"] == "EsSalud"]  # declarado y pagado: sin saldo
    essalud = anexo(cliente, emp, "4031")
    assert D(essalud["resumen"]["saldo_final_contable"]) == 0 and D(essalud["resumen"]["haber"]) == D("900")
    assert D(a["resumen"]["diferencia"]) == 0


def test_10_remuneraciones_y_datos_personales(cliente, emp):
    generar(cliente, emp, ["41"])
    a = anexo(cliente, emp, "41")
    det = detalle(cliente, emp, a["anexo"]["id"])
    w1 = fila_de(det, tercero=W1, cuenta="4111")
    assert (D(w1["provisiones"]), D(w1["pagos"]), D(w1["saldo"])) == (D("2500"), D("2000"), D("500"))
    cts = fila_de(det, tercero=W1, cuenta="4151")
    assert cts["concepto"].startswith("Compensación por tiempo") and D(cts["saldo"]) == D("500")
    assert D(a["resumen"]["saldo_final_contable"]) == -libro(cliente, emp, "41") == D("1000") and D(a["resumen"]["diferencia"]) == 0
    # protección de datos personales: un analista ve los datos enmascarados
    for u, rol in (("ana.contadora", "CONTADOR"), ("luis.analista", "ANALISTA")):
        assert cliente.post("/api/compensacion/roles", params=q(emp), json={"usuario": u, "rol": rol}).status_code == 201
    oculto = cliente.get(f"/api/anexos/anexos/{a['anexo']['id']}/detalle", params=q(emp), headers={"X-Usuario": "luis.analista"}).json()
    assert all(W1 not in (f["tercero"] or "") and "TRABAJADOR W1" != f["razon_social"] for f in oculto["filas"])
    visible = cliente.get(f"/api/anexos/anexos/{a['anexo']['id']}/detalle", params=q(emp), headers={"X-Usuario": "ana.contadora"}).json()
    assert any(f["tercero"] == W1 for f in visible["filas"])


def test_11_gastos_por_centro_de_costo_con_plantilla_personalizada(cliente, emp):
    base = next(p for p in cliente.get("/api/anexos/plantillas", params=q(emp)).json() if p["codigo"] == "GA-6")
    r = cliente.post("/api/anexos/plantillas", params=q(emp), json={
        "nombre": "Gastos por centro de costo", "codigo": "GCC", "especialidad": "GASTOS", "cuentas": "6",
        "columnas": [{"campo": "centro_costo", "titulo": "Centro"}, {"campo": "cuenta"}, {"campo": "glosa"},
                     {"campo": "saldo", "titulo": "Gasto", "total": True}],
        "formulas": [{"campo": "igv_estimado", "titulo": "IGV 18 %", "expresion": "REDONDEAR(saldo * 0.18, 2)", "tipo": "importe"},
                     {"campo": "alerta", "titulo": "Alerta", "expresion": "SI(saldo > 2000, 'REVISAR', 'OK')", "tipo": "texto"}],
        "reglas": [{"codigo": "GASTO-ALTO", "descripcion": "Gasto superior a 2 500", "tipo": "CONDICION_FILA", "expresion": "saldo > 2500",
                    "severidad": "BAJA"}],
        "agrupar_por": ["centro_costo"], "subtotales": ["saldo"], "orden": ["centro_costo", "-saldo"],
        "encabezado": {"titulo": "Gastos por centro de costo"}, "orientacion": "VERTICAL", "compartida": True})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["tipo"] == "PERSONALIZADA" and base["id"] != p["id"]
    generar(cliente, emp, ["6"], plantilla_id=p["id"])
    a = anexo(cliente, emp, "6")
    det = detalle(cliente, emp, a["anexo"]["id"])
    sub = {g["clave"]: D(g["subtotales"]["saldo"]) for g in det["grupos"]}
    assert sub["OPE"] == D("7000") and sub["ADM"] == D("1000") + D("800") + D("1200") + D("900") + D("2500") + D("500")
    assert sum(sub.values()) == D(det["totales"]["saldo"]) == libro(cliente, emp, "6") == D(a["resumen"]["saldo_final_contable"])
    f = fila_de(det, glosa="MANO DE OBRA P-100")
    assert D(f["igv_estimado"]) == D("540.00") and f["alerta"] == "REVISAR"
    assert any(h["codigo"] == "GASTO-ALTO" for h in a["hallazgos"])
    # el motor de fórmulas no ejecuta código arbitrario
    for mala in ("__import__('os').system('ls')", "saldo.__class__", "[x for x in range(3)]", "open('x')", "lambda: 1"):
        v = cliente.post("/api/anexos/formulas/validar", params=q(emp), json={"especialidad": "GASTOS", "expresion": mala}).json()
        assert v["valida"] is False, mala
    v = cliente.post("/api/anexos/formulas/validar", params=q(emp), json={"especialidad": "GASTOS", "expresion": "saldo * 2", "fila": {"saldo": "10.5"}}).json()
    assert v == {"valida": True, "resultado": "21.0"}


def test_12_origen_y_destino(cliente, emp):
    generar(cliente, emp, ["79", "9"])
    a = anexo(cliente, emp, "79")
    od = a["resumen"]["extras"]["origen_destino"]
    assert D(a["resumen"]["saldo_final_contable"]) == -libro(cliente, emp, "79") == D("11900")
    # parte de la clase 6 no tiene destino configurado (compras 6311, depreciación): se informa, no se exige distribuirla
    assert {x["periodo"] for x in od["por_periodo"]} == {1} and any(o["estado"] == "SIN_DESTINO_CONFIGURADO" for o in od["origenes"])
    assert D(a["resumen"]["diferencia"]) == 0
    assert not [h for h in a["hallazgos"] if h["codigo"] in ("DESTINO_DUPLICADO", "DUPLICIDAD_PRESENTACION")]
    nueve = anexo(cliente, emp, "9")
    det = detalle(cliente, emp, nueve["anexo"]["id"])
    assert D(det["totales"]["saldo"]) == libro(cliente, emp, "9") == D("11900")
    assert sum(D(f["porcentaje"]) for f in det["filas"]) == D("100.00")


# ===================================================================== 13–16
def test_13_saldo_inicial_sin_detalle(cliente, emp):
    generar(cliente, emp, ["4212"])
    a = anexo(cliente, emp, "4212")
    r = a["resumen"]
    assert D(r["sin_detalle"]) == D("500") and a["anexo"]["resultado"] == "PARCIALMENTE_SUSTENTADO"
    assert D(r["diferencia"]) == 0  # cuadrado matemáticamente pero no sustentado en su totalidad
    sd = [f for f in detalle(cliente, emp, a["anexo"]["id"])["filas"] if f["estado_sustento"] == "SIN_DETALLE"]
    assert len(sd) == 1 and sd[0]["numero"] is None  # no se inventa un documento
    assert any(h["codigo"] == "SALDO_SIN_DETALLE" for h in a["hallazgos"])


def test_14_diferencias_contables_explicitas(cliente, emp):
    generar(cliente, emp, ["1821"])
    a = anexo(cliente, emp, "1821")
    r = a["resumen"]
    assert D(r["saldo_final_contable"]) == libro(cliente, emp, "1821") == D("12000")
    f = fila_de(detalle(cliente, emp, a["anexo"]["id"]), glosa="POLIZA VEHICULAR 2026")
    devengado = (D("12000") * 31 / 365).quantize(D("0.01"))
    assert D(f["devengado"]) == devengado and D(f["saldo"]) == D("12000") - devengado
    assert D(r["diferencia"]) == devengado and a["anexo"]["resultado"] == "DESCUADRADO"
    assert any(h["codigo"] == "DIFERENCIA_CONCILIACION" for h in a["hallazgos"])
    # la diferencia no se ajusta: el libro sigue intacto
    assert libro(cliente, emp, "1821") == D("12000")


def test_15_moneda_extranjera(cliente, emp):
    generar(cliente, emp, ["4212"])
    a = anexo(cliente, emp, "4212")
    f = fila_de(detalle(cliente, emp, a["anexo"]["id"]), documento="F001-91")
    assert f["moneda"] == "USD" and (D(f["saldo_me"]), D(f["saldo"]), D(f["importe_original"])) == (D("500"), D("1875"), D("500"))
    pagada = [x for x in detalle(cliente, emp, a["anexo"]["id"])["filas"] if x["documento"] == "F001-9" and x["tercero"] == T["T9"]]
    assert not pagada  # factura de US$ 1 000 cancelada en su moneda: no aparece pendiente
    # efectivo: sin estado bancario no se declara conciliada
    generar(cliente, emp, ["104101"])
    b = anexo(cliente, emp, "104101")
    fb = detalle(cliente, emp, b["anexo"]["id"])["filas"][0]
    assert fb["estado_banco"].startswith("Sin cuenta bancaria") or "insuficiente" in fb["estado_banco"]
    assert fb["estado_sustento"] == "SIN_DOCUMENTO" and D(fb["saldo"]) == libro(cliente, emp, "104101")


def test_16_fecha_de_corte_historica(cliente, emp):
    generar(cliente, emp, ["4212"], corte="2025-12-31")
    a = anexo(cliente, emp, "4212", corte="2025-12-31")
    assert (a["anexo"]["ejercicio"], a["anexo"]["periodo"]) == (2025, 12)
    assert D(a["resumen"]["saldo_final_contable"]) == -libro(cliente, emp, "4212", ejercicio=2025, hasta=12) == D("2500")
    det = detalle(cliente, emp, a["anexo"]["id"])
    assert D(fila_de(det, documento="F001-10")["saldo"]) == D("2000")  # pagada en enero 2026: pendiente al 31/12/2025
    generar(cliente, emp, ["1212"], corte="2026-01-15")
    m = anexo(cliente, emp, "1212", corte="2026-01-15")
    f = fila_de(detalle(cliente, emp, m["anexo"]["id"]), documento="F002-2")
    assert D(f["saldo"]) == D("5000")  # la cobranza del 20/01 es posterior al corte
    comp = cliente.get(f"/api/anexos/anexos/{anexo(cliente, emp, '1212', corte='2026-01-15')['anexo']['id']}/comparar",
                       params=q(emp, contra="corte:2025-12-31")).json()
    assert comp["calculado_al_vuelo"] is True and any(x["documento"] == "F002-2" for x in comp["partidas_nuevas"])


# ===================================================================== 17–21
def test_17_generacion_masiva_concilia_todo_el_balance(cliente, emp):
    run = generar(cliente, emp, modo="BALANCE")
    res = run["resumen"]
    bal = cliente.get("/api/analisis/balance", params=q(emp, ejercicio=2026, desde=1, hasta=1)).json()
    hojas = [n for n in bal["nodos"] if not n["tiene_hijos"] and (D(n["saldo_final"]) or n["movimientos"])]
    assert res["cuentas"] == len(hojas) and res["nuevas_versiones"] == len(hojas) and not res["errores"]
    lst = cliente.get("/api/anexos/anexos", params=q(emp, fecha_corte="2026-01-31", por_pagina=500)).json()["items"]
    por = {a["cuenta"]: a for a in lst}
    for n in hojas:  # el saldo contable de cada anexo coincide con el libro
        a = por[n["cuenta"]]
        sg = 1 if a["naturaleza"] == "D" else -1
        assert D(a["saldo_contable"]) == D(n["saldo_final"]) * sg, n["cuenta"]
        assert D(a["saldo_contable"]) - D(a["saldo_detalle"]) == D(a["diferencia"])
    assert {a["resultado"] for a in lst} <= {"CUADRADO", "CUADRADO_CON_OBSERVACIONES", "PARCIALMENTE_SUSTENTADO", "DESCUADRADO", "INFORMACION_INSUFICIENTE"}
    # idempotencia: misma información y reglas → misma ejecución; forzar no crea versiones sin cambios
    r = cliente.post("/api/anexos/generaciones", params=q(emp), json={"fecha_corte": "2026-01-31", "modo": "BALANCE"}).json()
    assert r["reutilizado"] is True and r["run_id"] == run["id"]
    run2 = generar(cliente, emp, modo="BALANCE", forzar=True)
    assert run2["resumen"]["nuevas_versiones"] == 0 and run2["resumen"]["sin_cambios"] == len(hojas)
    d = cliente.get("/api/anexos/dashboard", params=q(emp, fecha_corte="2026-01-31")).json()
    assert d["kpi"]["anexos_generados"] == len(hojas) and d["kpi"]["cuentas_sin_anexo"] == 0
    assert d["graficos"]["avance_elemento"] and d["graficos"]["diferencias"]
    # generación por elemento y por rango
    assert generar(cliente, emp, modo="ELEMENTO", elemento="4", digitos=2)["resumen"]["cuentas"] == 4  # 40, 41, 42 y 45
    assert generar(cliente, emp, modo="RANGO", desde="10", hasta="14")["resumen"]["cuentas"] >= 3


def test_18_exportacion_a_excel(cliente, emp):
    from openpyxl import load_workbook
    generar(cliente, emp, ["1212", "4212", "3341"])
    a = anexo(cliente, emp, "1212")
    r = cliente.get(f"/api/anexos/anexos/{a['anexo']['id']}/exportar.xlsx", params=q(emp))
    assert r.status_code == 200 and r.content[:2] == b"PK"
    ws = load_workbook(io.BytesIO(r.content)).active
    celdas = {(c.row, c.column): c.value for fila in ws.iter_rows() for c in fila}
    textos = " ".join(str(v) for v in celdas.values() if v is not None)
    for clave in ("Razón social", "RUC", "Fecha de corte", "Saldo final contable", "Diferencia de conciliación", "Elaborado por",
                  "Aprobado por", "No constituyen firma digital"):
        assert clave in textos, clave
    formulas = [v for v in celdas.values() if isinstance(v, str) and v.startswith("=")]
    assert any("SUBTOTAL(9" in f for f in formulas) and any(f.startswith("=B") for f in formulas)
    importes = [v for v in celdas.values() if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)]
    assert D("3000") in [D(str(x)) for x in importes]  # importes numéricos reales, no texto
    assert ws.freeze_panes and ws.auto_filter.ref
    # libro masivo
    r = cliente.post("/api/anexos/exportaciones", params=q(emp), json={"tipo": "LIBRO_EXCEL", "fecha_corte": "2026-01-31"})
    assert r.status_code == 202, r.text
    x = cliente.get(f"/api/anexos/exportaciones/{r.json()['exportacion_id']}/descargar", params=q(emp))
    assert x.status_code == 200
    wb = load_workbook(io.BytesIO(x.content))
    for hoja in ("Índice", "Resumen general", "Balance de comprobación", "Diferencias", "Observaciones", "Control de revisión"):
        assert hoja in wb.sheetnames
    assert len(wb.sheetnames) == 6 + 3
    enlaces = [c.value for fila in wb["Índice"].iter_rows() for c in fila if isinstance(c.value, str) and c.value.startswith("=HYPERLINK(\"#")]
    assert len(enlaces) >= 3 + 5


def test_19_exportacion_a_pdf(cliente, emp):
    import pdfplumber
    generar(cliente, emp, ["4212", "3913"])
    a = anexo(cliente, emp, "4212")
    r = cliente.get(f"/api/anexos/anexos/{a['anexo']['id']}/exportar.pdf", params=q(emp))
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        texto = " ".join(p.extract_text() or "" for p in pdf.pages)
        n = len(pdf.pages)
    for clave in ("ANEXOS DEL SUR SAC", "RUC 20609876540", f"Página 1 de {n}", "versión 1", "Elaborado por", "No constituyen firma digital"):
        assert clave in texto, clave
    r = cliente.post("/api/anexos/exportaciones", params=q(emp), json={"tipo": "EXPEDIENTE_PDF", "fecha_corte": "2026-01-31"})
    exp = cliente.get(f"/api/anexos/exportaciones/{r.json()['exportacion_id']}/descargar", params=q(emp))
    with pdfplumber.open(io.BytesIO(exp.content)) as pdf:
        primera = pdf.pages[0].extract_text()
        assert "EXPEDIENTE DE CIERRE CONTABLE" in primera and len(pdf.pages) >= 3


def test_20_aprobacion_y_versionamiento(cliente, emp):
    for u, rol in (("ana.contadora", "CONTADOR"), ("sofia.super", "SUPERVISOR"), ("aldo.auditor", "AUDITOR")):
        assert cliente.post("/api/compensacion/roles", params=q(emp), json={"usuario": u, "rol": rol}).status_code == 201
    H = lambda u: {"X-Usuario": u}  # noqa: E731
    generar(cliente, emp, ["3341"], usuario="ana.contadora")
    a = anexo(cliente, emp, "3341")
    aid, lock = a["anexo"]["id"], a["anexo"]["lock_version"]

    def estado(nuevo, usuario, comentario=None, lock_version=None):
        return cliente.post(f"/api/anexos/anexos/{aid}/estado", params=q(emp), headers=H(usuario),
                            json={"estado": nuevo, "comentario": comentario, "lock_version": lock_version})
    r = cliente.patch(f"/api/anexos/anexos/{aid}", params=q(emp), headers=H("ana.contadora"),
                      json={"conclusion": "Saldo conforme con el registro de activos", "lock_version": lock})
    assert r.status_code == 200 and r.json()["anexo"]["estado_revision"] == "EN_ELABORACION"
    assert cliente.patch(f"/api/anexos/anexos/{aid}", params=q(emp), headers=H("ana.contadora"),
                         json={"conclusion": "otra", "lock_version": lock}).status_code == 409  # concurrencia optimista
    assert estado("APROBADO", "sofia.super").status_code == 422  # no se salta la revisión
    assert estado("EN_REVISION", "ana.contadora").status_code == 200
    assert estado("OBSERVADO", "aldo.auditor", "corto").status_code == 422
    assert estado("OBSERVADO", "aldo.auditor", "Adjuntar la factura de compra del camión AF-2").status_code == 200
    adj = cliente.post("/api/anexos/adjuntos", params=q(emp), headers=H("ana.contadora"),
                       data={"categoria": "FACTURA", "anexo_id": str(aid), "documento": "F020-9", "descripcion": "Factura camión"},
                       files={"archivo": ("factura.pdf", b"%PDF-1.4 prueba")})
    assert adj.status_code == 201, adj.text
    assert estado("SUBSANADO", "ana.contadora").status_code == 200
    assert estado("REVISADO", "aldo.auditor").status_code == 200
    assert estado("APROBADO", "ana.contadora").status_code == 403  # separación de funciones
    assert estado("APROBADO", "aldo.auditor").status_code == 403  # el auditor no aprueba
    r = estado("APROBADO", "sofia.super", "Conforme")
    assert r.status_code == 200 and r.json()["anexo"]["estado_revision"] == "APROBADO"
    v1 = r.json()["version"]
    assert v1["inmutable"] is True and v1["numero"] == 1
    # versión aprobada inmutable: no se edita ni se regenera sin reapertura
    assert cliente.patch(f"/api/anexos/anexos/{aid}", params=q(emp), headers=H("ana.contadora"), json={"conclusion": "x"}).status_code == 422
    assert cliente.post(f"/api/anexos/anexos/{aid}/regenerar", params=q(emp), headers=H("ana.contadora"), json={}).status_code == 409
    masivo = generar(cliente, emp, ["3341"], usuario="ana.contadora", forzar=True)
    assert masivo["resumen"]["protegidos"] == 1 and masivo["resumen"]["nuevas_versiones"] == 0
    assert estado("REABIERTO", "ana.contadora", "Reapertura para incluir la baja").status_code == 403
    assert estado("REABIERTO", "sofia.super", "corto").status_code == 422
    assert estado("REABIERTO", "sofia.super", "Se registró una mejora al activo AF-1").status_code == 200
    # nueva información → nueva versión; la aprobada se conserva
    mejora = "codigo;cuenta;descripcion;categoria;fecha_adquisicion;fecha_uso;costo_inicial;mejoras;vida_util_meses;valor_residual;cuenta_depreciacion;depreciacion_acumulada_inicial\n" \
             "AF-1;3341;CAMION VOLVO FH;VEHICULOS;01/01/2024;01/01/2024;120000;5000;120;0;3913;24000\n"
    subir_registro(cliente, emp, "ACTIVO_FIJO", "mejora.csv", mejora.encode())
    r = cliente.post(f"/api/anexos/anexos/{aid}/regenerar", params=q(emp), headers=H("ana.contadora"), json={"motivo": "Mejora AF-1"})
    assert r.status_code == 202
    a = anexo(cliente, emp, "3341")
    assert a["anexo"]["version_actual"] == 2 and a["anexo"]["estado_revision"] == "EN_ELABORACION"
    assert [v["numero"] for v in a["versiones"]] == [2, 1] and a["versiones"][1]["inmutable"] is True
    assert D(a["resumen"]["diferencia"]) == D("-5000") and a["anexo"]["resultado"] == "DESCUADRADO"  # la mejora no está en libros
    v1_det = detalle(cliente, emp, aid, version_id=v1["id"])
    assert D(fila_de(v1_det, codigo_activo="AF-1")["saldo"]) == D("120000")  # la versión aprobada no cambia
    cmp = cliente.get(f"/api/anexos/anexos/{aid}/comparar", params=q(emp, contra="aprobada")).json()
    assert cmp["conteo"]["cambios_importe"] == 1 and D(cmp["cambios_importe"][0]["variacion"]) == D("5000")
    assert any(o["codigo"] == "DIFERENCIA_CONCILIACION" for o in cmp["observaciones_nuevas"])
    hist = {(x["de_estado"], x["a_estado"]) for x in a["revisiones"]}
    assert ("REVISADO", "APROBADO") in hist and ("APROBADO", "REABIERTO") in hist
    acciones = {x["accion"] for x in cliente.get("/api/anexos/auditoria", params=q(emp), headers=H("aldo.auditor")).json()}
    assert {"GENERAR_ANEXOS", "ESTADO_APROBADO", "ESTADO_REABIERTO", "ADJUNTAR_SUSTENTO", "EDITAR_ANEXO"} <= acciones


def test_21_seguridad_multiempresa_y_permisos(cliente, emp):
    generar(cliente, emp, ["1212", "4212"])
    a = anexo(cliente, emp, "1212")
    aid = a["anexo"]["id"]
    otra = cliente.post("/api/empresas", json={"ruc": "20100047218", "razon_social": "Otra SAC"}).json()["id"]
    assert cliente.get(f"/api/anexos/anexos/{aid}", params=q(otra)).status_code == 404
    assert cliente.get(f"/api/anexos/anexos/{aid}/detalle", params=q(otra)).status_code == 404
    assert cliente.get(f"/api/anexos/anexos/{aid}/exportar.xlsx", params=q(otra)).status_code == 404
    assert cliente.post(f"/api/anexos/anexos/{aid}/estado", params=q(otra), json={"estado": "EN_REVISION"}).status_code == 404
    assert cliente.get("/api/anexos/anexos", params=q(otra)).json()["total"] == 0
    for u, rol in (("ana.contadora", "CONTADOR"), ("carlos.consulta", "CONSULTA"), ("luis.analista", "ANALISTA"), ("sofia.super", "SUPERVISOR")):
        assert cliente.post("/api/compensacion/roles", params=q(emp), json={"usuario": u, "rol": rol}).status_code == 201
    H = lambda u: {"X-Usuario": u}  # noqa: E731
    assert cliente.post("/api/anexos/generaciones", params=q(emp), headers=H("carlos.consulta"),
                        json={"fecha_corte": "2026-01-31", "cuentas": ["1212"]}).status_code == 403
    assert cliente.get(f"/api/anexos/anexos/{aid}", params=q(emp), headers=H("intruso")).status_code == 403
    # acceso por cuenta: el analista solo ve la 42
    r = cliente.post("/api/anexos/asignaciones", params=q(emp), headers=H("sofia.super"), json={"tipo": "ACCESO", "usuario": "luis.analista", "cuenta": "42"})
    assert r.status_code == 201, r.text
    assert cliente.get(f"/api/anexos/anexos/{aid}", params=q(emp), headers=H("luis.analista")).status_code == 403
    vis = cliente.get("/api/anexos/anexos", params=q(emp), headers=H("luis.analista")).json()["items"]
    assert vis and all(x["cuenta"].startswith("42") for x in vis)
    assert cliente.post("/api/anexos/generaciones", params=q(emp), headers=H("luis.analista"),
                        json={"fecha_corte": "2026-01-31", "modo": "BALANCE"}).status_code == 403
    # responsables y fecha límite por cuenta
    r = cliente.post("/api/anexos/asignaciones", params=q(emp), headers=H("ana.contadora"),
                     json={"tipo": "ELABORACION", "usuario": "luis.analista", "cuenta": "42", "fecha_limite": "2026-02-05"})
    assert r.status_code == 201
    b = anexo(cliente, emp, "4212")
    assert b["anexo"]["responsable_elaboracion"] == "luis.analista" and b["anexo"]["fecha_limite"] == "2026-02-05"
    # el catálogo del sistema no se modifica: se duplica
    gen = next(p for p in cliente.get("/api/anexos/plantillas", params=q(emp)).json() if p["codigo"] == "PA-42")
    body = cliente.get(f"/api/anexos/plantillas/{gen['id']}", params=q(emp)).json()
    upd = {k: body[k] for k in ("nombre", "especialidad", "cuentas", "agrupar_por", "subtotales", "filtros", "orden", "orientacion")}
    upd["columnas"] = [{"campo": c["campo"]} for c in body["columnas"]]
    assert cliente.put(f"/api/anexos/plantillas/{gen['id']}", params=q(emp), headers=H("ana.contadora"), json=upd).status_code == 409
    dup = cliente.post(f"/api/anexos/plantillas/{gen['id']}/duplicar", params=q(emp), headers=H("ana.contadora"), json={"nombre": "CxP propia"})
    assert dup.status_code == 201 and dup.json()["base_id"] == gen["id"]
    # aprobación automática: solo con política autorizada
    assert cliente.put("/api/anexos/configuracion", params=q(emp), headers=H("ana.contadora"),
                       json={"aprobacion_automatica": {"activa": True}}).status_code == 403
    cfg = cliente.put("/api/anexos/configuracion", params=q(emp), headers=H("sofia.super"), json={"aprobacion_automatica": {"activa": True}}).json()
    assert cfg["aprobacion_automatica"]["autorizada_por"] == "sofia.super"
    generar(cliente, emp, ["3341"], usuario="ana.contadora")
    c = anexo(cliente, emp, "3341")
    assert c["anexo"]["estado_revision"] == "APROBADO" and c["aprobaciones"][0]["accion"] == "APROBAR_POLITICA"
    generar(cliente, emp, ["1821"], usuario="ana.contadora")
    assert anexo(cliente, emp, "1821")["anexo"]["estado_revision"] == "GENERADO"  # descuadrado: nunca se aprueba solo


def test_catalogo_cubre_todos_los_elementos(cliente, emp):
    pl = cliente.get("/api/anexos/plantillas", params=q(emp)).json()
    esp = {p["especialidad"] for p in pl}
    assert {"EFECTIVO", "CARTERA", "PERSONAL", "ESTIMACION", "DIFERIDO", "EXISTENCIAS", "SERVICIOS_PROCESO", "PPE", "DEPRECIACION",
            "TRIBUTOS", "REMUNERACIONES", "FINANCIERAS", "PATRIMONIO", "GASTOS", "INGRESOS", "ORIGEN_DESTINO", "CIERRE", "ORDEN",
            "GENERICO"} <= esp
    prefijos = {p["cuentas"] for p in pl}
    for e in "0123456789":
        assert any(x.startswith(e) for x in prefijos), e
    exp = cliente.get("/api/anexos/cuentas", params=q(emp, fecha_corte="2026-01-31")).json()
    n = {x["cuenta"]: x for x in exp["nodos"]}
    assert n["1413"]["plantilla"]["codigo"] == "CC-1413" and n["3913"]["plantilla"]["especialidad"] == "DEPRECIACION"
    assert n["7041"]["plantilla"]["especialidad"] == "INGRESOS"


def test_volumen_1000_cuentas_y_100000_movimientos(cliente, monkeypatch):
    """Balance con 1 200 cuentas analíticas y 100 000 líneas: generación masiva, exportación y consulta."""
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    from sqlalchemy import insert
    from app.core.database import SessionLocal
    from app.models import CuentaContable, LineaDiario, LoteContable
    e = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Volumen Anexos SAC"}).json()["id"]
    gastos = [f"63{i:04d}" for i in range(400)]
    ingresos = [f"70{i:04d}" for i in range(200)]
    clientes_ = [f"12{i:04d}" for i in range(300)]
    proveedores = [f"42{i:04d}" for i in range(300)]
    with SessionLocal() as db:
        db.execute(insert(CuentaContable), [{"empresa_id": e, "codigo": c, "descripcion": f"Cuenta {c}", "naturaleza": "D" if c[0] in "16" else "A"}
                                            for c in gastos + ingresos + clientes_ + proveedores + ["104101"]])
        lote = LoteContable(empresa_id=e, tipo_informacion="DIARIO", ejercicio=2026, periodo=None, nombre_archivo="volumen.csv",
                            hash_archivo="w" * 64, usuario="prueba", registros_importados=100000)
        db.add(lote)
        db.flush()
        filas = []
        for i in range(25000):  # 4 líneas por operación → 100 000 líneas
            mes = i % 12 + 1
            f = date(2026, mes, i % 28 + 1)
            base = dict(lote_id=lote.id, empresa_id=e, ejercicio=2026, periodo=mes, fecha_contable=f, moneda="PEN", debe_me=D(0), haber_me=D(0))
            imp = D(i % 500 + 50)
            pv, cl = proveedores[i % 300], clientes_[i % 300]
            filas += [{**base, "numero_asiento": f"C{i}", "cuenta": gastos[i % 400], "debe_mn": imp, "haber_mn": D(0), "glosa": "SERVICIO",
                       "centro_costo": f"CC{i % 20}", "documento_tercero": f"20{i % 900:09d}", "tipo_documento": "01", "serie": "F001", "numero_documento": str(i)},
                      {**base, "numero_asiento": f"C{i}", "cuenta": pv, "debe_mn": D(0), "haber_mn": imp, "glosa": "FACTURA",
                       "documento_tercero": f"20{i % 900:09d}", "tipo_documento": "01", "serie": "F001", "numero_documento": str(i)},
                      {**base, "numero_asiento": f"V{i}", "cuenta": cl, "debe_mn": imp * 2, "haber_mn": D(0), "glosa": "VENTA",
                       "documento_tercero": f"10{i % 700:09d}", "tipo_documento": "01", "serie": "E001", "numero_documento": str(i)},
                      {**base, "numero_asiento": f"V{i}", "cuenta": ingresos[i % 200], "debe_mn": D(0), "haber_mn": imp * 2, "glosa": "VENTA",
                       "documento_tercero": f"10{i % 700:09d}", "tipo_documento": "01", "serie": "E001", "numero_documento": str(i)}]
        for k in range(0, len(filas), 20000):
            db.execute(insert(LineaDiario), filas[k:k + 20000])
        db.commit()
    t0 = time.perf_counter()
    run = generar(cliente, e, modo="BALANCE", corte="2026-12-31")
    t_gen = time.perf_counter() - t0
    assert run["resumen"]["cuentas"] == 1200 and run["resumen"]["nuevas_versiones"] == 1200 and not run["resumen"]["errores"]
    lst = cliente.get("/api/anexos/anexos", params=q(e, fecha_corte="2026-12-31", por_pagina=500, cuenta="63")).json()["items"]
    assert all(D(a["diferencia"]) == 0 for a in lst)
    t1 = time.perf_counter()
    d = cliente.get("/api/anexos/dashboard", params=q(e, fecha_corte="2026-12-31")).json()
    t_dash = time.perf_counter() - t1
    assert d["kpi"]["anexos_generados"] == 1200
    t2 = time.perf_counter()
    det = detalle(cliente, e, lst[0]["id"], pagina=1)
    t_det = time.perf_counter() - t2
    assert det["total_filas"] > 0
    t3 = time.perf_counter()
    r = cliente.post("/api/anexos/exportaciones", params=q(e), json={"tipo": "LIBRO_EXCEL", "fecha_corte": "2026-12-31"})
    assert r.status_code == 202
    exp = cliente.get("/api/anexos/exportaciones", params=q(e)).json()[0]
    t_xls = time.perf_counter() - t3
    assert exp["estado"] == "COMPLETADO", exp
    print(f"\nAnexos: 1 200 cuentas, 100 000 líneas → generación masiva {t_gen:.1f}s · dashboard {t_dash:.1f}s · "
          f"detalle de un anexo {t_det:.2f}s · libro Excel ({exp['tamano'] // 1024} KB, 1 206 hojas) {t_xls:.1f}s · etapas {run['tiempos']}")
    assert t_gen < 300
