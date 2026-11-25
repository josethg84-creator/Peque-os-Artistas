"""Pruebas de la fase 3: motor de análisis de cuentas.

Los datos se importan por el flujo real de la fase 2 (archivos CSV → asistente) y los saldos
esperados se calculan de forma independiente, en Python, desde las mismas filas de origen.
"""
import io
import json
import time
from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import insert

from tests.test_contable import confirmar, validar

D = Decimal
R1, R2 = "20100047218", "20609876540"   # clientes
P1, P2 = "20555123451", "20601234561"   # proveedores

PLAN = [("10", "EFECTIVO", "D", "N"), ("104", "CTAS CTES", "D", "N"), ("104101", "BCP MN", "D", "S"), ("104102", "BBVA USD", "D", "S"),
        ("12", "CXC", "D", "N"), ("1212", "FACTURAS POR COBRAR", "D", "S"), ("23", "PRODUCTOS EN PROCESO", "D", "N"),
        ("2311", "SERVICIOS EN PROCESO", "D", "S"), ("41", "REMUNERACIONES", "A", "N"), ("4111", "SUELDOS POR PAGAR", "A", "S"),
        ("42", "CXP", "A", "N"), ("4212", "FACTURAS POR PAGAR", "A", "S"), ("50", "CAPITAL", "A", "N"), ("5011", "ACCIONES", "A", "S"),
        ("62", "PERSONAL", "D", "N"), ("6211", "SUELDOS", "D", "S"), ("63", "SERVICIOS", "D", "N"), ("6311", "TRANSPORTE", "D", "S"),
        ("70", "VENTAS", "A", "N"), ("7011", "MERCADERIAS", "A", "S"), ("79", "CARGAS IMPUTABLES", "A", "N"),
        ("791", "CARGAS IMPUTABLES", "A", "S"), ("94", "GASTOS ADMINISTRATIVOS", "D", "N"), ("9411", "GASTOS ADM", "D", "S"),
        ("95", "GASTOS DE VENTAS", "D", "N"), ("9511", "GASTOS VENTAS", "D", "S"), ("0111", "BIENES EN CUSTODIA", None, "S"),
        ("0211", "CONTRACUENTA", None, "S")]
APERTURA = [("104101", None, "10000", ""), ("1212", R1, "2000", ""), ("4212", P2, "", "3000"), ("5011", None, "", "9000")]
# (subdiario, asiento, fecha, cuenta, ruc, glosa, td, serie, numero, venc, moneda, tc, debe, haber, debe_me, haber_me, cc, proyecto)
L = lambda *a: a  # noqa: E731
DIARIO = [
    L("05", "A1", "05/01/2026", "1212", R1, "VENTA F001-1", "01", "F001", "1", "31/01/2026", "PEN", "", "1180", "", "", "", "", ""),
    L("05", "A1", "05/01/2026", "7011", R1, "VENTA F001-1", "01", "F001", "1", "", "PEN", "", "", "1180", "", "", "", ""),
    L("03", "A2", "10/01/2026", "6311", P1, "FLETE E001-10", "01", "E001", "10", "", "PEN", "", "500", "", "", "", "ADM", ""),
    L("03", "A2", "10/01/2026", "4212", P1, "FLETE E001-10", "01", "E001", "10", "09/02/2026", "PEN", "", "", "500", "", "", "", ""),
    L("03", "A2", "10/01/2026", "9411", "", "DESTINO FLETE", "", "", "", "", "PEN", "", "500", "", "", "", "ADM", ""),
    L("03", "A2", "10/01/2026", "791", "", "DESTINO FLETE", "", "", "", "", "PEN", "", "", "500", "", "", "", ""),
    L("01", "A3", "20/01/2026", "104101", R1, "COBRANZA F001-1", "01", "F001", "1", "", "PEN", "", "1180", "", "", "", "", ""),
    L("01", "A3", "20/01/2026", "1212", R1, "COBRANZA F001-1", "01", "F001", "1", "", "PEN", "", "", "1180", "", "", "", ""),
    L("01", "A4", "25/01/2026", "104102", R2, "COBRANZA USD", "", "", "", "", "USD", "3.72", "3720", "", "1000", "", "", ""),
    L("01", "A4", "25/01/2026", "1212", R2, "COBRANZA USD", "", "", "", "", "USD", "3.72", "", "3720", "", "1000", "", ""),
    L("03", "A5", "03/01/2026", "2311", P2, "COSTO PROYECTO ANTIGUO", "01", "F010", "1", "", "PEN", "", "1200", "", "", "", "", "PRJ-OLD"),
    L("03", "A5", "03/01/2026", "4212", P2, "COSTO PROYECTO ANTIGUO", "01", "F010", "1", "02/02/2026", "PEN", "", "", "1200", "", "", "", ""),
    L("35", "B1", "27/02/2026", "6211", "", "PLANILLA FEBRERO", "", "", "", "", "PEN", "", "2000", "", "", "", "VEN", ""),
    L("35", "B1", "27/02/2026", "4111", "", "PLANILLA FEBRERO", "", "", "", "", "PEN", "", "", "2000", "", "", "", ""),
    L("35", "B1", "27/02/2026", "9511", "", "DESTINO PLANILLA", "", "", "", "", "PEN", "", "2000", "", "", "", "VEN", ""),
    L("35", "B1", "27/02/2026", "791", "", "DESTINO PLANILLA", "", "", "", "", "PEN", "", "", "1500", "", "", "", ""),
    L("35", "B1", "27/02/2026", "4111", "", "AJUSTE", "", "", "", "", "PEN", "", "", "500", "", "", "", ""),
    L("03", "B2", "05/02/2026", "6311", P1, "FLETE E001-11", "01", "E001", "11", "", "PEN", "", "300", "", "", "", "ADM", ""),
    L("03", "B2", "05/02/2026", "4212", P1, "FLETE E001-11", "01", "E001", "11", "15/02/2026", "PEN", "", "", "300", "", "", "", ""),
    L("01", "B3", "12/02/2026", "4212", P1, "PAGO E001-10", "01", "E001", "10", "", "PEN", "", "12000", "", "", "", "", ""),
    L("01", "B3", "12/02/2026", "104101", P1, "PAGO E001-10", "01", "E001", "10", "", "PEN", "", "", "12000", "", "", "", ""),
    L("03", "B4", "14/02/2026", "6311", P1, "FLETE E001-10", "01", "E001", "10", "", "PEN", "", "500", "", "", "", "ADM", ""),
    L("03", "B4", "14/02/2026", "4212", P1, "FLETE E001-10", "01", "E001", "10", "", "PEN", "", "", "500", "", "", "", ""),
    L("03", "B5", "16/02/2026", "6311", P2, "COMPRA LAPTOP DELL", "01", "F010", "5", "", "PEN", "", "3500", "", "", "", "ADM", ""),
    L("03", "B5", "16/02/2026", "4212", P2, "COMPRA LAPTOP DELL", "01", "F010", "5", "", "PEN", "", "", "3500", "", "", "", ""),
    L("01", "B6", "18/02/2026", "1212", R1, "APORTE POR COBRAR", "", "", "", "", "PEN", "", "1000", "", "", "", "", ""),
    L("01", "B6", "18/02/2026", "5011", "", "APORTE DE CAPITAL", "", "", "", "", "PEN", "", "", "1000", "", "", "", ""),
    L("09", "B7", "20/02/2026", "0111", "", "BIENES EN CUSTODIA", "", "", "", "", "PEN", "", "100", "", "", "", "", ""),
    L("09", "B7", "20/02/2026", "4212", "", "CUSTODIA MAL REGISTRADA", "", "", "", "", "PEN", "", "", "100", "", "", "", ""),
]
ENCAB_DIARIO = "Subdiario;Asiento;Fecha;Cuenta;RUC;Glosa;Tipo Doc;Serie;Numero;F. Vencimiento;Moneda;T.C.;Debe MN;Haber MN;Debe ME;Haber ME;Centro Costo;Proyecto"


def csv_diario(filas):
    return (ENCAB_DIARIO + "\n" + "\n".join(";".join(f) for f in filas) + "\n").encode()


def importar_bytes(cliente, empresa, nombre, contenido, tipo, **extra):
    r = cliente.post("/api/contable/archivos", files={"archivo": (nombre, contenido)}, data={"empresa_id": str(empresa)})
    assert r.status_code == 201, r.text
    token = r.json()["token"]
    sug = cliente.get(f"/api/contable/archivos/{token}/vista-previa", params={"tipo": tipo}).json()["sugerencia_encabezado"]
    params = {"empresa_id": empresa, "tipo": tipo, "ejercicio": 2026, "periodo": extra.pop("periodo", 1),
              "fila_encabezado": sug["fila"], "filas_encabezado": sug["filas"], **extra}
    hom = cliente.post(f"/api/contable/archivos/{token}/homologacion", json=params).json()
    params["mapeo"] = {c: v["columna"] for c, v in hom["mapeo_sugerido"].items()}
    validar(cliente, token, params)
    t = confirmar(cliente, token, params, confirmar_criticos=True, motivo_criticos="Datos de prueba de la fase 3")
    assert t["estado"] == "COMPLETADO", t
    return t["resultado"]


@pytest.fixture()
def emp(cliente, monkeypatch):
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    e = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Empresa Análisis SAC"}).json()["id"]
    plan = "Codigo;Descripcion;Naturaleza;Movimiento\n" + "\n".join(f"{c};{d};{n or ''};{m}" for c, d, n, m in PLAN) + "\n"
    importar_bytes(cliente, e, "plan.csv", plan.encode(), "PLAN_CUENTAS")
    cc = "Codigo;Descripcion;Cuenta destino;Unidad de negocio\nADM;ADMINISTRACION;9411;CORPORATIVO\nVEN;VENTAS;9511;COMERCIAL\n"
    importar_bytes(cliente, e, "cc.csv", cc.encode(), "CENTROS_COSTO")
    tc = "Fecha;Moneda;Compra;Venta\n31/01/2026;USD;3.700;3.710\n27/02/2026;USD;3.800;3.810\n"
    importar_bytes(cliente, e, "tc.csv", tc.encode(), "TIPOS_CAMBIO")
    ape = "Cuenta;RUC;Debe;Haber\n" + "\n".join(";".join(x or "" for x in f) for f in APERTURA) + "\n"
    importar_bytes(cliente, e, "apertura.csv", ape.encode(), "SALDOS_INICIALES", periodo=0)
    importar_bytes(cliente, e, "diario.csv", csv_diario(DIARIO), "DIARIO", periodo=None)
    return e


def esperado(hasta_periodo: int, desde_periodo: int = 1):
    """Saldos esperados calculados directamente desde las filas de origen."""
    si, mov = defaultdict(lambda: D(0)), defaultdict(lambda: [D(0), D(0)])
    for c, _t, d, h in APERTURA:
        si[c] += D(d or 0) - D(h or 0)
    for f in DIARIO:
        p = int(f[2][3:5])
        d, h = D(f[12] or 0), D(f[13] or 0)
        if p < desde_periodo:
            si[f[3]] += d - h
        elif p <= hasta_periodo:
            mov[f[3]][0] += d
            mov[f[3]][1] += h
    return si, mov


def balance(cliente, e, desde, hasta):
    r = cliente.get("/api/analisis/balance", params={"empresa_id": e, "ejercicio": 2026, "desde": desde, "hasta": hasta})
    assert r.status_code == 200, r.text
    return r.json(), {n["cuenta"]: n for n in r.json()["nodos"]}


def correr(cliente, e, desde=2, hasta=2, **extra):
    r = cliente.post("/api/analisis/ejecuciones", params={"empresa_id": e},
                     json={"ejercicio": 2026, "desde": desde, "hasta": hasta, **extra})
    assert r.status_code == 202, r.text
    run = cliente.get(f"/api/analisis/ejecuciones/{r.json()['run_id']}", params={"empresa_id": e}).json()
    assert run["estado"] == "COMPLETADO", run
    return run


def hallazgos(cliente, e, run_id, **f):
    return cliente.get("/api/analisis/hallazgos", params={"empresa_id": e, "run_id": run_id, "por_pagina": 500, **f}).json()


# ===================================================================== saldos y jerarquía
def test_saldos_iniciales_y_finales_coinciden_con_origen(cliente, emp):
    b, nodos = balance(cliente, emp, 2, 2)
    si, mov = esperado(2, 2)
    for cuenta in set(si) | set(mov):
        n = nodos[cuenta]
        assert D(n["saldo_inicial"]) == si[cuenta], cuenta
        assert D(n["debe"]) == mov[cuenta][0] and D(n["haber"]) == mov[cuenta][1], cuenta
        assert D(n["saldo_final"]) == si[cuenta] + mov[cuenta][0] - mov[cuenta][1], cuenta
    assert b["control"]["conciliado"] is True and b["apertura"] == "SALDOS_INICIALES" and not b["preliminar"]


def test_consolidacion_jerarquica_sin_duplicar(cliente, emp):
    b, nodos = balance(cliente, emp, 1, 2)
    # cada nivel es la suma exacta de sus hijos directos (más su movimiento propio)
    for c, n in nodos.items():
        hijos = [x for x in nodos.values() if x["padre"] == c]
        if hijos and not n["movimiento_propio"]:
            for k in ("saldo_inicial", "debe", "haber", "saldo_final"):
                assert D(n[k]) == sum(D(x[k]) for x in hijos), (c, k)
    assert nodos["1"]["nivel_nombre"] == "Elemento" and nodos["12"]["nivel_nombre"] == "Cuenta"
    assert nodos["104101"]["padre"] == "104" and nodos["104"]["padre"] == "10" and nodos["10"]["padre"] == "1"
    # la suma de los elementos 1–9 es igual a la suma directa de las líneas: no hay doble conteo
    total_debe = sum(D(x[12] or 0) for x in DIARIO if x[3][0] != "0")
    assert D(b["totales"]["debe"]) == total_debe
    assert b["totales"]["cuentas_orden"]["debe"] == "100.00"  # elemento 0 fuera de los totales
    assert nodos["1212"]["terceros"] == 2 and nodos["12"]["terceros"] == 2


def test_no_duplica_mayor_ni_asiento_de_apertura(cliente, emp):
    antes, nodos_antes = balance(cliente, emp, 2, 2)
    mayor = [f for f in DIARIO if f[2][3:5] == "02"]
    importar_bytes(cliente, emp, "mayor.csv", csv_diario(mayor), "MAYOR", periodo=2, importacion_completa=False)
    apertura = [L("00", "AP", "01/01/2026", c, t or "", "APERTURA", "", "", "", "", "PEN", "", d, h, "", "", "", "")
                for c, t, d, h in APERTURA]
    importar_bytes(cliente, emp, "apertura_diario.csv", csv_diario(apertura), "DIARIO", periodo=0)
    despues, nodos = balance(cliente, emp, 2, 2)
    assert despues["version_datos"] != antes["version_datos"]  # la caché se invalida al importar
    for c in nodos_antes:
        assert nodos[c]["saldo_final"] == nodos_antes[c]["saldo_final"], c
    avisos = " ".join(despues["advertencias"])
    assert "diario y mayor" in avisos and "periodo 00" in avisos


def test_cache_se_invalida_al_anular_lote(cliente, emp):
    _, n1 = balance(cliente, emp, 1, 1)
    lote = next(l for l in cliente.get("/api/contable/lotes", params={"empresa_id": emp, "tipo": "SALDOS_INICIALES"}).json())
    cliente.post(f"/api/contable/lotes/{lote['id']}/anular", json={"motivo": "Prueba de invalidación"})
    b, n2 = balance(cliente, emp, 1, 1)
    assert n2["104101"]["saldo_inicial"] == "0.00" and n1["104101"]["saldo_inicial"] == "10000.00"
    assert b["preliminar"] is True and any("PRELIMINARES" in a for a in b["advertencias"])


# ===================================================================== naturaleza, moneda extranjera
def test_cuentas_deudoras_acreedoras_y_moneda_extranjera(cliente, emp):
    run = correr(cliente, emp)
    hs = hallazgos(cliente, emp, run["id"])["items"]
    por = defaultdict(list)
    for h in hs:
        por[h["regla_codigo"]].append(h)
    # 104101 queda en −820 (acreedor): sobregiro; no se repite como «saldo contrario» genérico
    assert [h["cuenta"] for h in por["SOB-10"]] == ["104101"] and D(por["SOB-10"][0]["importe"]) == D("820")
    # proveedor P1 con saldo deudor por pago en exceso (anticipo / pago no aplicado)
    ter = {(h["cuenta"], h["tercero"]): D(h["importe"]) for h in por["TER-01"]}
    assert ter[("4212", P1)] == D("10700.00") and ("1212", R2) in ter  # 12 000 − (500 + 300 + 500)
    # 104102 se lleva íntegramente en USD: 1000 × 3.80 (TC compra de cierre) = 3800 vs 3720 → 80 de diferencia
    tc = [h for h in por["TC-01"]]
    assert [h["cuenta"] for h in tc] == ["104102"] and D(tc[0]["importe"]) == D("80.00")
    # 1212 mezcla soles y dólares: no se evalúa (evita diferencias de cambio ficticias)
    assert all(h["cuenta"] != "1212" for h in tc)


# ===================================================================== comparación
def test_comparacion_entre_periodos(cliente, emp):
    r = cliente.get("/api/analisis/comparativo", params={"empresa_id": emp, "modo": "MES_ANTERIOR", "ejercicio": 2026, "periodo": 2,
                                                         "dimension": "CUENTA", "medida": "MOVIMIENTO", "nivel": 2, "cuenta": "6"}).json()
    f = {x["clave"]: x for x in r["filas"]}
    assert D(f["63"]["actual"]) == D("4300") and D(f["63"]["base"]) == D("500") and f["63"]["variacion_pct"] == 760.0
    assert f["62"]["variacion_pct"] is None and f["62"]["variacion_pct_aplica"] is False  # base cero → no aplica
    assert len(f["63"]["tendencia"]) == 2 and D(f["63"]["tendencia"][1]) == D("4300")
    # mismo mes del año anterior sin información → advertencia de periodo incompleto
    r2 = cliente.get("/api/analisis/comparativo", params={"empresa_id": emp, "modo": "MISMO_MES_ANTERIOR", "ejercicio": 2026, "periodo": 2}).json()
    assert any("2025" in a and "sin información" in a for a in r2["advertencias"])
    # por centro de costo y por unidad de negocio (derivada del maestro de centros de costo)
    r3 = cliente.get("/api/analisis/comparativo", params={"empresa_id": emp, "modo": "ACUMULADO", "ejercicio": 2026, "periodo": 2,
                                                          "dimension": "UNIDAD_NEGOCIO", "cuenta": "6"}).json()
    un = {x["clave"]: D(x["actual"]) for x in r3["filas"]}
    assert un == {"CORPORATIVO": D("4800"), "COMERCIAL": D("2000")}


# ===================================================================== antigüedad
def test_antiguedad_de_saldos(cliente, emp):
    p = {"empresa_id": emp, "ejercicio": 2026, "fecha_corte": "2026-04-30", "cuentas": "42"}
    venc = cliente.get("/api/analisis/antiguedad", params={**p, "base": "VENCIMIENTO"}).json()
    docs = {(d["tercero"], d["documento"]): d for d in venc["documentos"]}
    e11 = docs[(P1, "E001-11")]
    assert e11["dias"] == 74 and e11["tramo_nombre"] == "De 61 a 90 días" and not e11["preliminar"]
    emi = cliente.get("/api/analisis/antiguedad", params={**p, "base": "EMISION"}).json()
    assert {(d["tercero"], d["documento"]): d for d in emi["documentos"]}[(P1, "E001-11")]["dias"] == 84
    # el documento pagado en exceso queda con saldo contrario y marcado como PRELIMINAR (sin compensar)
    e10 = docs[(P1, "E001-10")]
    assert D(e10["importe"]) == D("-11000.00") and e10["preliminar"] and any("anticipo" in m for m in e10["motivos"])
    # la apertura sin detalle por documento también es preliminar
    assert docs[(P2, "(saldo de apertura)")]["preliminar"]
    assert D(venc["total"]) == sum(D(x) for x in venc["totales"])


# ===================================================================== origen y destino
def test_reglas_de_origen_y_destino(cliente, emp):
    od = cliente.get("/api/analisis/destino", params={"empresa_id": emp, "ejercicio": 2026, "desde": 2, "hasta": 2}).json()
    feb = od["resumen"][0]
    # gasto destinable feb: 6211 2000 + 6311 300 + 500 + 3500 = 6300; destino 2000; 79 = 1500
    assert D(feb["origen"]) == D("6300") and D(feb["destino"]) == D("2000") and D(feb["cargas_imputables"]) == D("1500")
    asientos = {a["asiento"]: a["estado"] for a in od["asientos"]}
    assert asientos["03-B2"] == "SIN_DESTINO"
    cc = {c["clave"]: c for c in od["centros_costo"]}
    assert D(cc["ADM"]["origen"]) == D("4300") and D(cc["ADM"]["destino"]) == 0
    # regla con porcentaje y vigencia: 6311 de ADM → 70 % a 9411 y 30 % a 9511
    for destino, pct in (("9411", 70), ("9511", 30)):
        r = cliente.post("/api/analisis/destino/reglas", params={"empresa_id": emp},
                         json={"cuenta_origen": "6311", "centro_costo": "ADM", "cuenta_destino": destino, "porcentaje": pct,
                               "vigente_desde": "2026-01-01"})
        assert r.status_code == 201, r.text
    exceso = cliente.post("/api/analisis/destino/reglas", params={"empresa_id": emp},
                          json={"cuenta_origen": "6311", "centro_costo": "ADM", "cuenta_destino": "9411", "porcentaje": 10})
    assert exceso.status_code == 422  # superaría el 100 %
    cliente.post("/api/analisis/destino/reglas", params={"empresa_id": emp}, json={"cuenta_origen": "6211", "excluir": True})
    od = cliente.get("/api/analisis/destino", params={"empresa_id": emp, "ejercicio": 2026, "desde": 2, "hasta": 2}).json()
    destinos = {d["clave"]: d for d in od["destinos"]}
    # 6311/ADM en febrero: 300 + 500 + 3 500 = 4 300 → 70 % = 3 010 y 30 % = 1 290; 6211 queda excluida
    assert D(destinos["9411"]["esperado"]) == D("3010.00") and D(destinos["9511"]["esperado"]) == D("1290.00")
    origenes = {o["clave"]: o["estado"] for o in od["origenes"]}
    assert origenes["6211"] == "EXCLUIDA"
    assert D(od["resumen"][0]["excluido"]) == D("2000")
    # regla vencida no se aplica
    cliente.post("/api/analisis/destino/reglas", params={"empresa_id": emp},
                 json={"cuenta_origen": "6311", "centro_costo": "VEN", "cuenta_destino": "9511", "vigente_hasta": "2025-12-31"})
    assert od["reglas_vigentes"] == 3


# ===================================================================== detección de inconsistencias
def test_deteccion_de_inconsistencias_y_reglas_configurables(cliente, emp):
    reglas = {r["codigo"]: r for r in cliente.get("/api/analisis/reglas", params={"empresa_id": emp}).json()}
    c23 = reglas["C23-01"]
    c23_in = {k: c23[k] for k in ("codigo", "nombre", "descripcion", "tipo", "grupo", "cuentas", "cuenta_desde", "cuenta_hasta",
                                   "condicion", "operador", "valor", "valor2", "importe_minimo", "tolerancia_pct", "parametros",
                                   "riesgo", "vigente_desde", "vigente_hasta", "activa")}
    r = cliente.put(f"/api/analisis/reglas/{c23['id']}", params={"empresa_id": emp}, json={**c23_in, "valor": "30"})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["versiones_anteriores"] == 1
    nueva = cliente.post("/api/analisis/reglas", params={"empresa_id": emp}, json={
        "codigo": "U-CAP", "nombre": "Capital acreedor mayor a 9 500", "tipo": "UMBRAL", "grupo": "PROPIAS", "cuentas": "50",
        "condicion": "SALDO_ACREEDOR", "operador": ">", "valor": "9500", "riesgo": "BAJO"})
    assert nueva.status_code == 201, nueva.text
    run = correr(cliente, emp)
    hs = hallazgos(cliente, emp, run["id"])
    codigos = {h["regla_codigo"] for h in hs["items"]}
    for esperado_codigo in ("SOB-10", "TER-01", "DUP-01", "CLA-01", "PAT-01", "ORD-01", "OD-01", "TC-01", "C23-01", "STE-01", "U-CAP"):
        assert esperado_codigo in codigos, esperado_codigo
    dup = [h for h in hs["items"] if h["regla_codigo"] == "DUP-01"]
    assert {h["cuenta"] for h in dup} == {"6311", "4212"} and all(h["asiento"] == "03-B4" for h in dup)
    c23h = next(h for h in hs["items"] if h["regla_codigo"] == "C23-01")
    assert c23h["regla_version"] == 2 and c23h["documento"] == "PRJ-OLD" and "NIIF 15" in c23h["explicacion"]
    assert all(h["estado"] == "PENDIENTE" for h in hs["items"])  # nada se presenta como error confirmado
    snap = {x["codigo"]: x["version"] for x in run["reglas"]}
    assert snap["C23-01"] == 2  # versión registrada en el análisis
    # exposición: nunca mayor que la suma simple de importes
    assert D(hs["importe_sujeto_revision"]) <= sum(D(h["importe"]) for h in hs["items"])


def test_excepciones_revision_y_arrastre_entre_ejecuciones(cliente, emp):
    run = correr(cliente, emp)
    hs = hallazgos(cliente, emp, run["id"])["items"]
    sob = next(h for h in hs if h["regla_codigo"] == "SOB-10")
    r = cliente.patch(f"/api/analisis/hallazgos/{sob['id']}", params={"empresa_id": emp}, json={"estado": "DESCARTADO"})
    assert r.status_code == 422  # descartar exige fundamento
    r = cliente.patch(f"/api/analisis/hallazgos/{sob['id']}", params={"empresa_id": emp},
                      json={"estado": "CONFIRMADO", "responsable": "ana.tesoreria", "comentario": "Sobregiro autorizado; reclasificar a 45."})
    assert r.status_code == 200 and r.json()["estado"] == "CONFIRMADO"
    reglas = {x["codigo"]: x for x in cliente.get("/api/analisis/reglas", params={"empresa_id": emp}).json()}
    x = cliente.post("/api/analisis/excepciones", params={"empresa_id": emp},
                     json={"regla_id": reglas["CLA-01"]["id"], "cuenta": "6311", "motivo": "Laptops bajo política de gasto menor"})
    assert x.status_code == 201
    run2 = correr(cliente, emp)
    hs2 = hallazgos(cliente, emp, run2["id"])["items"]
    sob2 = next(h for h in hs2 if h["regla_codigo"] == "SOB-10")
    assert sob2["estado"] == "CONFIRMADO" and sob2["responsable"] == "ana.tesoreria"  # el estado se arrastra
    det = cliente.get(f"/api/analisis/hallazgos/{sob2['id']}", params={"empresa_id": emp}).json()
    assert det["comentarios"][0]["texto"].startswith("Sobregiro autorizado")
    assert not any(h["regla_codigo"] == "CLA-01" for h in hs2) and run2["resumen"]["exceptuados"] >= 1
    # ejecución por grupo de reglas
    run3 = correr(cliente, emp, grupo="ELEMENTO 1")
    assert {h["regla_codigo"] for h in hallazgos(cliente, emp, run3["id"])["items"]} <= {"SOB-10", "TER-01"}


def test_dashboard_y_avance(cliente, emp):
    correr(cliente, emp)
    d = cliente.get("/api/analisis/dashboard", params={"empresa_id": emp, "ejercicio": 2026, "desde": 2, "hasta": 2}).json()
    k = d["kpi"]
    assert k["cuentas_analizadas"] > 0 and k["movimientos"] == sum(1 for f in DIARIO if f[2][3:5] == "02" and f[3][0] != "0")
    assert k["cuentas_con_observaciones"] + k["cuentas_sin_observaciones"] == k["cuentas_analizadas"]
    assert d["avance_revision"]["pct"] == 0 and d["run_vigente"] is True
    g = d["graficos"]
    assert [e["elemento"] for e in g["evolucion"]] == list("12345") and len(g["evolucion"][0]["saldos"]) == 2
    assert {x["cuenta"] for x in g["distribucion_gastos"]} == {"62", "63"}
    assert g["origen_destino"][0]["estado"] in ("SIN_DESTINO", "DIFERENCIA", "DESTINO_DUPLICADO", "DUPLICIDAD_PRESENTACION")


# ===================================================================== navegación
def test_navegacion_hasta_asiento_y_linea_original(cliente, emp):
    q = {"empresa_id": emp, "ejercicio": 2026, "desde": 1, "hasta": 2}
    ter = cliente.get("/api/analisis/terceros", params={**q, "cuenta": "42"}).json()["items"]
    p1 = next(t for t in ter if t["tercero"] == P1)
    assert D(p1["saldo_final"]) == D("12000") - (D("500") + D("300") + D("500"))  # deudor: pago en exceso
    docs = cliente.get("/api/analisis/documentos", params={**q, "cuenta": "42", "tercero": P1}).json()["items"]
    e10 = next(x for x in docs if x["documento"] == "E001-10")
    assert D(e10["saldo_final"]) == D("11000.00")  # deudor (debe − haber)
    movs = cliente.get("/api/analisis/movimientos", params={**q, "cuenta": "4212", "tercero": P1, "documento": "E001-10"}).json()
    assert movs["total"] == 3 and D(movs["items"][-1]["saldo_acumulado"]) == D("11000.00")
    linea = movs["items"][0]
    asi = cliente.get(f"/api/analisis/lineas/{linea['id']}/asiento", params={"empresa_id": emp}).json()
    assert asi["asiento"] == "03-A2" and len(asi["lineas"]) == 4 and asi["cuadra"]
    assert {x["cuenta"] for x in asi["lineas"]} == {"6311", "4212", "9411", "791"}  # con contrapartidas
    org = cliente.get(f"/api/analisis/lineas/{linea['id']}/origen", params={"empresa_id": emp}).json()
    original = {c["columna"]: c["valor"] for c in org["original"]}
    assert original["Asiento"] == "A2" and original["Cuenta"] == "4212" and original["Haber MN"] == "500"
    assert org["lote"]["archivo"] == "diario.csv" and org["fila"] == 5


# ===================================================================== papeles de trabajo y exportación
def test_papeles_de_trabajo(cliente, emp):
    correr(cliente, emp)
    r = cliente.post("/api/analisis/papeles", params={"empresa_id": emp}, json={"ejercicio": 2026, "desde": 2, "hasta": 2, "cuenta": "4212"})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["estado"] == "PENDIENTE" and p["composicion"]["criterio"] == "Por tercero" and p["hallazgos"]
    pid = p["id"]
    e = lambda est, com=None: cliente.post(f"/api/analisis/papeles/{pid}/estado", params={"empresa_id": emp},  # noqa: E731
                                           json={"estado": est, "comentario": com})
    assert e("APROBADO").status_code == 409  # transición no permitida
    assert e("EN_REVISION").status_code == 200
    assert e("REVISADO").status_code == 422  # falta conclusión
    cliente.put(f"/api/analisis/papeles/{pid}", params={"empresa_id": emp},
                json={"conclusion": "Saldo deudor de P1 por pago en exceso: solicitar devolución.", "responsable": "tesorero.prueba"})
    adj = cliente.post(f"/api/analisis/papeles/{pid}/adjuntos", params={"empresa_id": emp},
                       files={"archivo": ("confirmacion.pdf", b"%PDF-1.4 sustento")})
    assert adj.status_code == 201
    assert e("REVISADO").status_code == 200
    assert e("APROBADO").status_code == 409  # el responsable no puede aprobar su propio papel
    r = cliente.post(f"/api/analisis/papeles/{pid}/estado", params={"empresa_id": emp}, json={"estado": "APROBADO"},
                     headers={"X-Usuario": "gerente.contable"})
    assert r.status_code == 200 and r.json()["estado"] == "APROBADO" and r.json()["fecha_revision"]
    assert cliente.put(f"/api/analisis/papeles/{pid}", params={"empresa_id": emp}, json={"conclusion": "x"}).status_code == 409
    det = cliente.get(f"/api/analisis/papeles/{pid}", params={"empresa_id": emp}).json()
    assert [x["a"] for x in det["revisiones"]] == ["EN_REVISION", "REVISADO", "APROBADO"] and det["adjuntos"][0]["nombre"] == "confirmacion.pdf"
    descarga = cliente.get(f"/api/analisis/papeles/{pid}/adjuntos/{det['adjuntos'][0]['id']}", params={"empresa_id": emp})
    assert descarga.content == b"%PDF-1.4 sustento"


def test_exportaciones_excel_y_pdf(cliente, emp):
    from openpyxl import load_workbook
    run = correr(cliente, emp)
    base = {"empresa_id": emp, "ejercicio": 2026, "desde": 1, "hasta": 2}
    xl = cliente.get("/api/analisis/exportar/balance.xlsx", params=base)
    assert xl.status_code == 200
    wb = load_workbook(io.BytesIO(xl.content))
    ws = wb["Totales por elemento"]
    assert "Empresa Análisis SAC".upper() in str(ws["B2"].value).upper() and "2026" in str(ws["B3"].value)
    assert ws.auto_filter.ref and ws.freeze_panes
    fila_total = next(r for r in ws.iter_rows() if r[0].value == "TOTAL")
    # importes numéricos; debe y haber difieren exactamente en los 100 del asiento B7, que mezcla la cuenta
    # de orden 0111 con la 4212 (error sembrado): el reporte lo refleja sin «corregirlo»
    assert isinstance(fila_total[3].value, (int, float)) and round(fila_total[4].value - fila_total[3].value, 2) == 100
    pedidos = [("cuenta", {"cuenta": "4212"}), ("movimientos", {"cuenta": "42"}), ("comparativo", {}), ("gastos", {}),
               ("ingresos", {}), ("destino", {}), ("observaciones", {"run_id": run["id"]}),
               ("antiguedad", {"fecha_corte": "2026-02-28"})]
    for rep, extra in pedidos:
        for fmt in ("xlsx", "pdf"):
            r = cliente.get(f"/api/analisis/exportar/{rep}.{fmt}", params={**base, **extra})
            assert r.status_code == 200, (rep, fmt, r.text[:200])
            assert r.content[:4] == (b"PK\x03\x04" if fmt == "xlsx" else b"%PDF"), (rep, fmt)
    mov = load_workbook(io.BytesIO(cliente.get("/api/analisis/exportar/movimientos.xlsx", params={**base, "cuenta": "4212"}).content))["Movimientos"]
    encabezado = next(r for r in mov.iter_rows() if r[0].value == "Fecha")
    col_debe = [c.value for c in encabezado].index("Debe")
    valores = [r[col_debe].value for r in mov.iter_rows(min_row=encabezado[0].row + 1) if r[0].value not in (None, "TOTAL")]
    assert all(isinstance(v, (int, float)) for v in valores)


# ===================================================================== seguridad multiempresa
def test_seguridad_multiempresa(cliente, emp):
    run = correr(cliente, emp)
    otra = cliente.post("/api/empresas", json={"ruc": "20100047218", "razon_social": "Otra Empresa SAC"}).json()["id"]
    h = hallazgos(cliente, emp, run["id"])["items"][0]
    linea = cliente.get("/api/analisis/movimientos", params={"empresa_id": emp, "ejercicio": 2026, "desde": 1, "hasta": 1}).json()["items"][0]
    p = cliente.post("/api/analisis/papeles", params={"empresa_id": emp}, json={"ejercicio": 2026, "desde": 2, "hasta": 2, "cuenta": "4212"}).json()
    q = {"empresa_id": otra}
    assert cliente.get(f"/api/analisis/ejecuciones/{run['id']}", params=q).status_code == 404
    assert cliente.get("/api/analisis/hallazgos", params={**q, "run_id": run["id"]}).status_code == 404
    assert cliente.get(f"/api/analisis/hallazgos/{h['id']}", params=q).status_code == 404
    assert cliente.patch(f"/api/analisis/hallazgos/{h['id']}", params=q, json={"estado": "EN_REVISION"}).status_code == 404
    assert cliente.get(f"/api/analisis/lineas/{linea['id']}/asiento", params=q).status_code == 404
    assert cliente.get(f"/api/analisis/lineas/{linea['id']}/origen", params=q).status_code == 404
    assert cliente.get(f"/api/analisis/papeles/{p['id']}", params=q).status_code == 404
    assert cliente.get("/api/analisis/exportar/papel.pdf", params={**q, "papel_id": p["id"]}).status_code == 404
    b = cliente.get("/api/analisis/balance", params={**q, "ejercicio": 2026, "desde": 1, "hasta": 2}).json()
    assert b["nodos"] == [] and b["totales"]["movimientos"] == 0


def test_cancelacion_de_analisis(cliente, emp):
    from app.analisis import motor
    from app.core.database import SessionLocal
    with SessionLocal() as db:
        run = motor.crear(db, emp, 2026, 2, 2, "prueba")
        motor.cancelar(db, run, "prueba")
        with pytest.raises(motor.Cancelado):
            motor.ejecutar(db, run.id)
    r = cliente.get(f"/api/analisis/ejecuciones/{run.id}", params={"empresa_id": emp}).json()
    assert r["estado"] == "CANCELADO"


# ===================================================================== volumen
def test_mas_de_100000_movimientos(cliente, monkeypatch):
    """Rendimiento con 100 200 líneas: los saldos del árbol concilian con la suma directa y el análisis completo termina."""
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    from app.core.database import SessionLocal
    from app.models import LineaDiario, LoteContable
    e = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Volumen SAC"}).json()["id"]
    cuentas_d = ["1212", "6311", "6211", "6561", "104101", "2011"]
    cuentas_h = ["7011", "4212", "4111", "104102", "4011", "791"]
    with SessionLocal() as db:
        lote = LoteContable(empresa_id=e, tipo_informacion="DIARIO", ejercicio=2026, periodo=None, nombre_archivo="volumen.csv",
                            hash_archivo="x" * 64, usuario="prueba", registros_importados=100200)
        db.add(lote)
        db.flush()
        filas, total = [], D(0)
        for i in range(50100):  # 50 100 asientos de 2 líneas
            imp = D(i % 997 + 1) + D(i % 100) / 100
            p = i % 12 + 1
            base = dict(lote_id=lote.id, empresa_id=e, ejercicio=2026, periodo=p, fecha_contable=date(2026, p, i % 28 + 1),
                        subdiario="01", numero_asiento=str(i), documento_tercero=f"20{i % 300:09d}", numero_documento=str(i % 5000),
                        serie="F001", moneda="PEN", debe_me=D(0), haber_me=D(0), centro_costo=["ADM", "VEN", "PRD"][i % 3])
            filas.append({**base, "numero_linea": 1, "cuenta": cuentas_d[i % 6], "debe_mn": imp, "haber_mn": D(0)})
            filas.append({**base, "numero_linea": 2, "cuenta": cuentas_h[i % 6], "debe_mn": D(0), "haber_mn": imp})
            total += imp
        for i in range(0, len(filas), 10000):
            db.execute(insert(LineaDiario), filas[i:i + 10000])
        db.commit()
    t0 = time.perf_counter()
    b, nodos = balance(cliente, e, 1, 12)
    t_balance = time.perf_counter() - t0
    assert b["control"]["conciliado"] and b["control"]["origen_lineas"] == 100200
    assert D(b["totales"]["debe"]) == total == D(b["totales"]["haber"])
    t1 = time.perf_counter()
    run = correr(cliente, e, desde=1, hasta=12)
    t_run = time.perf_counter() - t1
    assert run["resumen"]["movimientos"] == 100200
    movs = cliente.get("/api/analisis/movimientos", params={"empresa_id": e, "ejercicio": 2026, "desde": 1, "hasta": 12,
                                                            "cuenta": "6311", "pagina": 50, "por_pagina": 100}).json()
    assert movs["total"] == 8350 and len(movs["items"]) == 100
    print(f"\n100 200 líneas: balance {t_balance:.2f}s · análisis completo {t_run:.2f}s · tiempos {json.dumps(run['tiempos'])}")
    assert t_balance < 30 and t_run < 180


def test_panel_de_cuenta_evolucion_coincide_con_saldos(cliente, emp):
    d = cliente.get("/api/analisis/cuenta/4212", params={"empresa_id": emp, "ejercicio": 2026, "desde": 2, "hasta": 2}).json()
    _, n1 = balance(cliente, emp, 1, 1)
    _, n2 = balance(cliente, emp, 2, 2)
    assert [D(x["saldo"]) for x in d["evolucion"]] == [D(n1["4212"]["saldo_final"]), D(n2["4212"]["saldo_final"])]
    assert d["perfil"]["clave"] == "PAGAR" and d["nodo"]["saldo_final"] == n2["4212"]["saldo_final"]
