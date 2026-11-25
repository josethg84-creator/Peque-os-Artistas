"""Pruebas de la fase 4: motor de compensación de partidas.

Los movimientos se importan por el flujo real de la fase 2 (CSV → asistente) y cada escenario usa
un proveedor (o cliente) distinto para poder verificar saldo original, importe aplicado, saldo
pendiente y trazabilidad de forma independiente.
"""
import threading
import time
from datetime import date
from decimal import Decimal

import pytest

from tests.test_analisis import importar_bytes

D = Decimal
CAB = ("Subdiario;Asiento;Fecha;F. Vencimiento;Cuenta;RUC;Razon Social;Glosa;Tipo Doc;Serie;Numero;Doc Referencia;"
       "Cod Detraccion;Constancia;Moneda;T.C.;Debe MN;Haber MN;Debe ME;Haber ME")
T = {k: f"20{n:09d}" for n, k in enumerate(["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11A", "T11B", "T12",
                                             "T13", "T17", "C1"], start=100000001)}


def fila(sub, asi, fecha, cuenta, ter, glosa, td="", serie="", num="", ref="", venc="", debe="", haber="", mon="PEN", tc="",
         dme="", hme="", cod="", const="", rs=None):
    return [sub, asi, fecha, venc, cuenta, T.get(ter, ter), rs or (f"PROVEEDOR {ter}" if ter else ""), glosa, td, serie, num, ref,
            cod, const, mon, tc, debe, haber, dme, hme]


def asiento(sub, asi, fecha, lineas):
    return [fila(sub, asi, fecha, *l[:2], **l[2]) for l in lineas]


def compra(asi, fecha, ter, serie, num, importe, venc="", mon="PEN", tc="", me=""):
    """Factura de proveedor: gasto al debe y 4212 al haber."""
    gasto = {"debe": importe, "mon": mon, "tc": tc, "dme": me}
    prov = {"td": "01", "serie": serie, "num": num, "venc": venc, "haber": importe, "mon": mon, "tc": tc, "hme": me}
    return asiento("11", asi, fecha, [("6311", ter, gasto | {"glosa": f"COMPRA {serie}-{num}"}),
                                      ("4212", ter, prov | {"glosa": f"FACTURA {serie}-{num}"})])


def pago(asi, fecha, ter, importe, serie="", num="", glosa=None, cuenta="4212", mon="PEN", tc="", me="", **extra):
    doc = {"td": "01" if num else "", "serie": serie, "num": num}
    return asiento("21", asi, fecha, [(cuenta, ter, {**doc, "debe": importe, "mon": mon, "tc": tc, "dme": me,
                                                     "glosa": glosa or f"PAGO {serie}-{num}".strip(" -"), **extra}),
                                      ("104101", ter, {"haber": importe, "mon": mon, "tc": tc, "hme": me, "glosa": "BANCO"})])


DIARIO_2025 = compra("A10", "15/12/2025", "T10", "F001", "10", "2000", venc="14/01/2026")
DIARIO_2026 = (
    compra("A1", "05/01/2026", "T1", "F001", "1", "10000", venc="04/02/2026") + pago("P1", "15/01/2026", "T1", "10000", "F001", "1") +
    compra("A2", "05/01/2026", "T2", "F001", "2", "10000", venc="04/02/2026") + pago("P2a", "10/01/2026", "T2", "4000", "F001", "2") +
    pago("P2b", "20/01/2026", "T2", "6000", "F001", "2") +
    compra("A3", "05/01/2026", "T3", "F001", "3", "10000", venc="20/01/2026") + pago("P3", "15/01/2026", "T3", "3000", "F001", "3") +
    compra("A41", "02/01/2026", "T4", "F001", "41", "1000") + compra("A42", "03/01/2026", "T4", "F001", "42", "2000") +
    compra("A43", "04/01/2026", "T4", "F001", "43", "3000") + pago("P4", "25/01/2026", "T4", "6000", glosa="PAGO VARIAS FACTURAS") +
    compra("A5", "05/01/2026", "T5", "F001", "5", "5000") +
    asiento("11", "NC5", "12/01/2026", [("4212", "T5", {"td": "07", "serie": "FC01", "num": "1", "ref": "F001-5", "debe": "1000", "glosa": "NOTA DE CREDITO DESCUENTO"}),
                                        ("6311", "T5", {"haber": "1000", "glosa": "NOTA DE CREDITO"})]) +
    pago("P6a", "10/01/2026", "T6", "2000", glosa="ANTICIPO A PROVEEDOR", cuenta="4221") +
    compra("A6", "20/01/2026", "T6", "F001", "6", "5000") +
    asiento("31", "AP6", "25/01/2026", [("4212", "T6", {"td": "01", "serie": "F001", "num": "6", "debe": "2000", "glosa": "APLICACION ANTICIPO"}),
                                        ("4221", "T6", {"haber": "2000", "glosa": "APLICACION ANTICIPO F001-6"})]) +
    pago("P6b", "30/01/2026", "T6", "3000", "F001", "6") +
    compra("A7", "05/01/2026", "T7", "F001", "7", "1180") + pago("P7", "15/01/2026", "T7", "1038", "F001", "7") +
    asiento("21", "DT7", "15/01/2026", [("4212", "T7", {"td": "01", "serie": "F001", "num": "7", "debe": "142", "glosa": "DETRACCION F001-7",
                                                        "cod": "037", "const": "45678901"}),
                                        ("104201", "T7", {"haber": "142", "glosa": "BANCO DE LA NACION"})]) +
    compra("A8", "05/01/2026", "T8", "F001", "8", "1000") + pago("P8", "15/01/2026", "T8", "970", "F001", "8") +
    asiento("21", "RT8", "15/01/2026", [("4212", "T8", {"td": "20", "serie": "R001", "num": "55", "ref": "F001-8", "debe": "30", "glosa": "RETENCION IGV"}),
                                        ("40114", "T8", {"haber": "30", "glosa": "RETENCION POR PAGAR"})]) +
    compra("A9", "05/01/2026", "T9", "F001", "9", "3700", mon="USD", tc="3.70", me="1000") +
    pago("P9", "20/01/2026", "T9", "3800", "F001", "9", mon="USD", tc="3.80", me="1000") +
    pago("P10", "10/01/2026", "T10", "2000", "F001", "10") +
    compra("A11", "05/01/2026", "T11A", "F001", "11", "1500") + compra("B11", "06/01/2026", "T11B", "F001", "11", "1500") +
    pago("P11", "15/01/2026", "T11A", "1500", "F001", "11") +
    compra("A121", "05/01/2026", "T12", "F001", "121", "800") + compra("A122", "06/01/2026", "T12", "F001", "122", "800") +
    pago("P12", "15/01/2026", "T12", "800", glosa="PAGO PROVEEDOR") +
    compra("A17", "05/01/2026", "T17", "F001", "17", "1000") + pago("P17a", "10/01/2026", "T17", "600", glosa="PAGO") +
    pago("P17b", "11/01/2026", "T17", "600", glosa="PAGO") +
    pago("P13", "20/01/2026", "T13", "300", glosa="PAGO SALDO ANTERIOR") +
    asiento("05", "V1", "05/01/2026", [("1212", "C1", {"td": "01", "serie": "F002", "num": "1", "debe": "2360", "venc": "04/02/2026", "glosa": "VENTA"}),
                                      ("7011", "C1", {"haber": "2360", "glosa": "VENTA"})]) +
    asiento("01", "CB1", "25/01/2026", [("104101", "C1", {"debe": "2360", "glosa": "COBRANZA F002-1"}),
                                        ("1212", "C1", {"td": "01", "serie": "F002", "num": "1", "haber": "2360", "glosa": "COBRANZA F002-1"})])
)


def csv(filas):
    return (CAB + "\n" + "\n".join(";".join(str(x) for x in f) for f in filas) + "\n").encode()


@pytest.fixture()
def emp(cliente, monkeypatch):
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    e = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Compensa SAC"}).json()["id"]
    # apertura 2025 (ejercicio de inicio): saldo de T13 sin detalle documental
    ap = f"Cuenta;RUC;Debe;Haber\n4212;{T['T13']};;500\n104101;;50000;\n5011;;;49500\n".encode()
    importar_bytes(cliente, e, "apertura_2025.csv", ap, "SALDOS_INICIALES", periodo=0, ejercicio=2025)
    importar_bytes(cliente, e, "diario_2025.csv", csv(DIARIO_2025), "DIARIO", periodo=None, ejercicio=2025)
    # apertura 2026: debe ignorarse (la continuidad viene de los movimientos de 2025)
    ap26 = f"Cuenta;RUC;Debe;Haber\n4212;{T['T10']};;2000\n4212;{T['T13']};;500\n".encode()
    importar_bytes(cliente, e, "apertura_2026.csv", ap26, "SALDOS_INICIALES", periodo=0, ejercicio=2026)
    importar_bytes(cliente, e, "diario_2026.csv", csv(DIARIO_2026), "DIARIO", periodo=None, ejercicio=2026)
    return e


def q(e, **k):
    return {"empresa_id": e, **k}


def ejecutar(cliente, e, corte="2026-01-31", **k):
    r = cliente.post("/api/compensacion/ejecuciones", params=q(e), json={"fecha_corte": corte, **k})
    assert r.status_code == 202, r.text
    run = cliente.get(f"/api/compensacion/ejecuciones/{r.json()['run_id']}", params=q(e)).json()
    assert run["estado"] == "COMPLETADO", run
    return run


def partidas(cliente, e, corte="2026-01-31", **f):
    r = cliente.get("/api/compensacion/partidas", params=q(e, fecha_corte=corte, por_pagina=1000, **f))
    assert r.status_code == 200, r.text
    return r.json()["items"]


def factura(cliente, e, ter, num, corte="2026-01-31", serie="F001"):
    return next(p for p in partidas(cliente, e, corte, tercero=T[ter]) if p["rol"] == "ORIGEN" and p["numero"] == num and p["serie"] == serie)


def grupos_de(cliente, e, item_id, corte="2026-01-31"):
    det = cliente.get(f"/api/compensacion/partidas/{item_id}", params=q(e, fecha_corte=corte)).json()
    return {a["grupo_id"] for a in det["aplicaciones"] if a["estado"] in ("PROPUESTA", "APROBADA")}, det


def aprobar(cliente, e, gid, usuario="supervisor.uno"):
    r = cliente.post(f"/api/compensacion/grupos/{gid}/aprobar", params=q(e), json={"comentario": "Verificado"}, headers={"X-Usuario": usuario})
    assert r.status_code == 200, r.text
    return r.json()


def aprobar_de(cliente, e, item):
    gids, _ = grupos_de(cliente, e, item["id"])
    for g in gids:
        if cliente.get(f"/api/compensacion/grupos/{g}", params=q(e)).json()["estado"] == "PROPUESTA":
            aprobar(cliente, e, g)
    return gids


def configurar(cliente, e, codigo, **params):
    regla = next(r for r in cliente.get("/api/compensacion/reglas", params=q(e)).json() if r["codigo"] == codigo)
    r = cliente.put(f"/api/compensacion/reglas/{regla['id']}", params=q(e), json={
        "tipo": regla["tipo"], "codigo": regla["codigo"], "nombre": regla["nombre"], "parametros": params, "activa": True})
    assert r.status_code == 200, r.text


def nueva_regla(cliente, e, **d):
    r = cliente.post("/api/compensacion/reglas", params=q(e), json=d)
    assert r.status_code == 201, r.text
    return r.json()


# ===================================================================== escenarios 1–4
def test_01_factura_y_pago_total(cliente, emp):
    ejecutar(cliente, emp)
    f = factura(cliente, emp, "T1", "1")
    assert f["clase"] == "FACTURA" and D(f["importe"]) == D("10000")
    gids, det = grupos_de(cliente, emp, f["id"])
    g = cliente.get(f"/api/compensacion/grupos/{gids.pop()}", params=q(emp)).json()
    assert g["modalidad"] == "UNO_A_UNO" and g["nivel"] == 1 and g["puntuacion"] >= 95 and g["confianza"] == "MUY_ALTA"
    assert g["estado"] == "PROPUESTA"  # sin política de aprobación automática
    aprobar(cliente, emp, g["id"])
    f = factura(cliente, emp, "T1", "1")
    assert (D(f["aplicado"]), D(f["pendiente"]), f["estado_cancelacion"]) == (D("10000"), D("0"), "TOTAL")
    a = cliente.get(f"/api/compensacion/grupos/{g['id']}", params=q(emp)).json()["aplicaciones"][0]
    assert a["regla"] and a["puntuacion"] >= 95 and a["usuario"] == "motor" and a["estado"] == "APROBADA"
    assert a["fecha_efectiva"] == "2026-01-15" and a["origen"]["linea_id"] and a["aplicacion"]["clase"] == "PAGO"


def test_02_factura_con_dos_pagos(cliente, emp):
    ejecutar(cliente, emp)
    f = factura(cliente, emp, "T2", "2")
    gids = aprobar_de(cliente, emp, f)
    g = cliente.get(f"/api/compensacion/grupos/{list(gids)[0]}", params=q(emp)).json()
    assert g["modalidad"] == "UNO_A_VARIOS" and sorted(D(a["importe"]) for a in g["aplicaciones"]) == [D("4000"), D("6000")]
    f = factura(cliente, emp, "T2", "2")
    assert D(f["pendiente"]) == 0 and f["estado_cancelacion"] == "TOTAL"


def test_03_pago_parcial(cliente, emp):
    ejecutar(cliente, emp)
    f = factura(cliente, emp, "T3", "3")
    aprobar_de(cliente, emp, f)
    f = factura(cliente, emp, "T3", "3")
    assert (D(f["importe"]), D(f["aplicado"]), D(f["pendiente"])) == (D("10000"), D("3000"), D("7000"))
    assert f["estado_cancelacion"] == "PARCIAL" and f["estado_vencimiento"] == "VENCIDO" and f["dias_vencido"] == 11


def test_04_tres_facturas_un_pago(cliente, emp):
    ejecutar(cliente, emp)
    pago4 = next(p for p in partidas(cliente, emp, tercero=T["T4"]) if p["rol"] == "APLICACION")
    gids, _ = grupos_de(cliente, emp, pago4["id"])
    g = cliente.get(f"/api/compensacion/grupos/{gids.pop()}", params=q(emp)).json()
    assert g["modalidad"] == "VARIOS_A_UNO" and g["nivel"] == 3 and g["confianza"] in ("MEDIA", "BAJA")
    aprobar(cliente, emp, g["id"])
    assert all(D(factura(cliente, emp, "T4", n)["pendiente"]) == 0 for n in ("41", "42", "43"))


# ===================================================================== 5–9
def test_05_nota_de_credito_parcial(cliente, emp):
    ejecutar(cliente, emp)
    nc = next(p for p in partidas(cliente, emp, tercero=T["T5"]) if p["rol"] == "APLICACION")
    assert nc["clase"] == "NOTA_CREDITO" and nc["documento_referencia"] == "F001-5"
    f = factura(cliente, emp, "T5", "5")
    gids = aprobar_de(cliente, emp, f)
    g = cliente.get(f"/api/compensacion/grupos/{gids.pop()}", params=q(emp)).json()
    assert g["nivel"] == 2
    f = factura(cliente, emp, "T5", "5")
    assert (D(f["aplicado"]), D(f["pendiente"])) == (D("1000"), D("4000"))
    # la nota de crédito no puede aplicarse otra vez
    r = cliente.post("/api/compensacion/grupos", params=q(emp), json={
        "izquierda": [{"item_id": f["id"], "importe": "100"}], "derecha": [{"item_id": nc["id"], "importe": "100"}], "justificacion": "otra vez"})
    assert r.status_code == 422 and "disponible" in r.json()["detail"]


def test_06_anticipo_aplicado(cliente, emp):
    nueva_regla(cliente, emp, tipo="ENTRE_CUENTAS", codigo="ANT-PROV", nombre="Anticipos a proveedores contra facturas",
                parametros={"cuentas": ["4212", "4221"]}, sustento="Política contable: los anticipos a proveedores se aplican a sus facturas.")
    ejecutar(cliente, emp)
    ant = next(p for p in partidas(cliente, emp, tercero=T["T6"]) if p["cuenta"] == "4221" and p["rol"] == "APLICACION")
    assert ant["clase"] == "ANTICIPO"
    lista = cliente.get("/api/compensacion/anticipos", params=q(emp, fecha_corte="2026-01-31")).json()
    assert any(x["id"] == ant["id"] and x["tipo_anticipo"] == "Anticipo a proveedor" for x in lista)
    for p in partidas(cliente, emp, tercero=T["T6"]):
        aprobar_de(cliente, emp, p)
    f = factura(cliente, emp, "T6", "6")
    assert D(f["pendiente"]) == 0
    ant = next(p for p in partidas(cliente, emp, tercero=T["T6"]) if p["id"] == ant["id"])
    assert (D(ant["importe"]), D(ant["aplicado"]), D(ant["pendiente"])) == (D("2000"), D("2000"), D("0"))


def test_07_detraccion_sustentada(cliente, emp):
    nueva_regla(cliente, emp, tipo="DETRACCION", codigo="037", nombre="Demás servicios gravados con IGV",
                parametros={"tasa": "12", "tolerancia": "1"})
    configurar(cliente, emp, "42", autoaprobar=True, umbral_auto=95)
    ejecutar(cliente, emp)
    det = next(p for p in partidas(cliente, emp, tercero=T["T7"]) if p["clase"] == "DETRACCION")
    assert det["constancia_detraccion"] == "45678901"
    f = factura(cliente, emp, "T7", "7")
    assert D(f["pendiente"]) == 0  # pago neto + detracción con constancia y tasa verificada (aprobación automática por política)
    trib = cliente.get("/api/compensacion/tributos", params=q(emp, fecha_corte="2026-01-31")).json()["DETRACCION"]
    assert trib[0]["documentos_relacionados"] == ["F001-7"] and not trib[0]["observaciones"]


def test_07b_detraccion_sin_tasa_no_se_aprueba_sola(cliente, emp):
    configurar(cliente, emp, "42", autoaprobar=True, umbral_auto=95)
    ejecutar(cliente, emp)
    det = next(p for p in partidas(cliente, emp, tercero=T["T7"]) if p["clase"] == "DETRACCION")
    gids, _ = grupos_de(cliente, emp, det["id"])
    g = cliente.get(f"/api/compensacion/grupos/{gids.pop()}", params=q(emp)).json()
    assert g["estado"] == "PROPUESTA" and "sin tasa de detracción" in " ".join(g["componentes"]["bloqueos"])


def test_08_retencion_sustentada(cliente, emp):
    nueva_regla(cliente, emp, tipo="RETENCION", codigo="IGV", nombre="Retención del IGV", parametros={"tasa": "3"})
    ejecutar(cliente, emp)
    f = factura(cliente, emp, "T8", "8")
    for g in aprobar_de(cliente, emp, f):
        pass
    f = factura(cliente, emp, "T8", "8")
    assert (D(f["aplicado"]), D(f["pendiente"])) == (D("1000"), D("0"))
    ret = next(p for p in partidas(cliente, emp, tercero=T["T8"]) if p["clase"] == "RETENCION")
    assert ret["serie"] == "R001" and ret["documento_referencia"] == "F001-8"


def test_09_moneda_extranjera(cliente, emp):
    ejecutar(cliente, emp)
    f = factura(cliente, emp, "T9", "9")
    assert f["moneda"] == "USD" and D(f["importe"]) == D("1000") and D(f["importe_mn"]) == D("3700")
    gids = aprobar_de(cliente, emp, f)
    f = factura(cliente, emp, "T9", "9")
    assert D(f["pendiente"]) == 0 and f["estado_cancelacion"] == "TOTAL"  # cancelada en USD aunque el MN difiera
    a = cliente.get(f"/api/compensacion/grupos/{gids.pop()}", params=q(emp)).json()["aplicaciones"][0]
    assert (D(a["importe_mn_origen"]), D(a["importe_mn_aplicacion"]), D(a["diferencia_cambio"])) == (D("3700"), D("3800"), D("100"))
    conc = cliente.get("/api/compensacion/conciliacion", params=q(emp, fecha_corte="2026-01-31")).json()
    c42 = next(c for c in conc["cuentas"] if c["cuenta"] == "4212")
    assert D(c42["diferencia_cambio_aplicaciones"]) == D("100") and c42["conciliado"]


# ===================================================================== 10–14
def test_10_y_16_ejercicio_anterior_y_saldos_historicos(cliente, emp):
    ejecutar(cliente, emp)
    f25 = factura(cliente, emp, "T10", "10", corte="2025-12-31")
    assert D(f25["pendiente"]) == D("2000") and f25["ejercicio"] == 2025
    aprobar_de(cliente, emp, factura(cliente, emp, "T10", "10"))
    assert D(factura(cliente, emp, "T10", "10")["pendiente"]) == 0
    # la aplicación de enero 2026 no altera la composición al 31/12/2025
    assert D(factura(cliente, emp, "T10", "10", corte="2025-12-31")["pendiente"]) == D("2000")
    # la apertura 2026 no duplica: el saldo de T10 viene del diario 2025
    assert not [p for p in partidas(cliente, emp, tercero=T["T10"]) if p["origen_datos"].startswith("APERTURA")]
    sin_detalle = [p for p in partidas(cliente, emp, corte="2025-12-31", tercero=T["T13"]) if p["origen_datos"] == "APERTURA_CONSOLIDADA"]
    assert len(sin_detalle) == 1 and D(sin_detalle[0]["importe"]) == D("500") and sin_detalle[0]["clasificacion_pendiente"]


def test_11_proveedores_con_mismo_numero(cliente, emp):
    ejecutar(cliente, emp)
    aprobar_de(cliente, emp, factura(cliente, emp, "T11A", "11"))
    assert D(factura(cliente, emp, "T11A", "11")["pendiente"]) == 0
    b = factura(cliente, emp, "T11B", "11")
    assert D(b["pendiente"]) == D("1500") and b["estado_revision"] == "NINGUNA"


def test_12_coincidencia_ambigua(cliente, emp):
    configurar(cliente, emp, "42", autoaprobar=True, umbral_auto=95)
    run = ejecutar(cliente, emp)
    pago12 = next(p for p in partidas(cliente, emp, tercero=T["T12"]) if p["rol"] == "APLICACION")
    assert pago12["estado_revision"] == "NINGUNA" and D(pago12["disponible"]) == D("800")  # no se aplicó solo
    cands = cliente.get("/api/compensacion/candidatos", params=q(emp, run_id=run["id"])).json()["items"]
    c = next(x for x in cands if x["aplicaciones"][0]["item_id"] == pago12["id"])
    assert c["ambiguo"] and c["alternativas"] == 2 and c["decision"] == "REQUIERE_DECISION"
    r = cliente.post(f"/api/compensacion/candidatos/{c['id']}/resolver", params=q(emp), json={"opcion": 1, "justificacion": "Según voucher del banco"})
    assert r.status_code == 200 and r.json()["estado"] == "PROPUESTA" and r.json()["origen_propuesta"] == "MANUAL"
    aprobar(cliente, emp, r.json()["id"])
    assert D(factura(cliente, emp, "T12", "122")["pendiente"]) == 0 and D(factura(cliente, emp, "T12", "121")["pendiente"]) == D("800")


def test_13_y_14_aplicacion_duplicada_y_exceso(cliente, emp):
    ejecutar(cliente, emp)
    f = factura(cliente, emp, "T17", "17")
    p1, p2 = [p for p in partidas(cliente, emp, tercero=T["T17"]) if p["rol"] == "APLICACION"]
    body = {"izquierda": [{"item_id": f["id"], "importe": "100"}], "derecha": [{"item_id": p1["id"], "importe": "100"}], "justificacion": "Pago parcial"}
    assert cliente.post("/api/compensacion/grupos", params=q(emp), json=body).status_code == 201
    dup = cliente.post("/api/compensacion/grupos", params=q(emp), json=body)
    assert dup.status_code == 409 and "duplicada" in dup.json()["detail"]
    exceso = {"izquierda": [{"item_id": f["id"], "importe": "1200"}], "derecha": [{"item_id": p2["id"], "importe": "1200"}], "justificacion": "Exceso"}
    r = cliente.post("/api/compensacion/grupos", params=q(emp), json=exceso)
    assert r.status_code == 422 and "disponible" in r.json()["detail"]
    descuadre = {"izquierda": [{"item_id": f["id"], "importe": "300"}], "derecha": [{"item_id": p2["id"], "importe": "200"}], "justificacion": "x" * 10}
    assert cliente.post("/api/compensacion/grupos", params=q(emp), json=descuadre).status_code == 422
    f = factura(cliente, emp, "T17", "17")
    assert D(f["disponible"]) == D("900") and D(f["aplicado"]) == 0  # propuesta reserva, aún no aplica


def test_15_reversion_de_compensacion_aprobada(cliente, emp):
    run1 = ejecutar(cliente, emp)
    f = factura(cliente, emp, "T1", "1")
    gid = aprobar_de(cliente, emp, f).pop()
    r = cliente.post(f"/api/compensacion/grupos/{gid}/revertir", params=q(emp), json={"comentario": "corto"})
    assert r.status_code == 422
    r = cliente.post(f"/api/compensacion/grupos/{gid}/revertir", params=q(emp), json={"comentario": "Pago aplicado a factura equivocada"})
    assert r.status_code == 200 and r.json()["estado"] == "REVERTIDA" and r.json()["reversiones"]
    assert all(a["estado"] == "REVERTIDA" and a["reversion_id"] for a in r.json()["aplicaciones"])
    f = factura(cliente, emp, "T1", "1")
    assert D(f["pendiente"]) == D("10000") and f["estado_revision"] == "REVERTIDA"
    # nada se elimina: el historial conserva la aplicación revertida y el snapshot de la ejecución anterior
    _, det = grupos_de(cliente, emp, f["id"])
    assert any(a["estado"] == "REVERTIDA" for a in det["aplicaciones"])
    from app.core.database import SessionLocal
    from app.models import SnapshotCompensacion
    with SessionLocal() as db:
        snap = db.query(SnapshotCompensacion).filter_by(run_id=run1["id"], item_id=f["id"]).one()
        assert snap.estado_cancelacion == "PENDIENTE"  # al momento del run estaba propuesto, no aplicado
    assert cliente.post(f"/api/compensacion/grupos/{gid}/aprobar", params=q(emp), json={}).status_code == 409


# ===================================================================== 17–18 y seguridad
def test_17_procesamiento_simultaneo(cliente, emp):
    ejecutar(cliente, emp)
    f = factura(cliente, emp, "T17", "17")
    p1, p2 = [p for p in partidas(cliente, emp, tercero=T["T17"]) if p["rol"] == "APLICACION"]
    from app.compensacion import servicio
    from app.core.database import SessionLocal
    resultados = []

    def usuario(nombre, a, b):
        with SessionLocal() as db:
            try:
                servicio.compensar_manual(db, emp, nombre, [{"item_id": f["id"], "importe": "1000"}],
                                          [{"item_id": a, "importe": "600"}, {"item_id": b, "importe": "400"}], justificacion="Concurrencia")
                resultados.append("ok")
            except Exception as exc:  # conflicto de saldo disponible
                db.rollback()
                resultados.append(type(exc).__name__)
    hilos = [threading.Thread(target=usuario, args=("ana", p1["id"], p2["id"])), threading.Thread(target=usuario, args=("luis", p2["id"], p1["id"]))]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert sorted(resultados)[-1] == "ok" and resultados.count("ok") == 1, resultados
    f = factura(cliente, emp, "T17", "17")
    assert D(f["disponible"]) == 0  # nunca por encima de su importe


def test_18_acceso_entre_empresas_y_roles(cliente, emp):
    ejecutar(cliente, emp)
    otra = cliente.post("/api/empresas", json={"ruc": "20100047218", "razon_social": "Otra SAC"}).json()["id"]
    f = factura(cliente, emp, "T1", "1")
    gid = grupos_de(cliente, emp, f["id"])[0].pop()
    assert cliente.get(f"/api/compensacion/partidas/{f['id']}", params=q(otra)).status_code == 404
    assert cliente.get(f"/api/compensacion/grupos/{gid}", params=q(otra)).status_code == 404
    assert cliente.post(f"/api/compensacion/grupos/{gid}/aprobar", params=q(otra), json={}).status_code == 404
    r = cliente.post("/api/compensacion/grupos", params=q(otra), json={"izquierda": [{"item_id": f["id"], "importe": "1"}],
                                                                       "derecha": [{"item_id": f["id"] + 1, "importe": "1"}], "justificacion": "intento"})
    assert r.status_code == 422 and "no existe en la empresa" in r.json()["detail"]
    assert partidas(cliente, otra) == []
    # roles: al asignar el primero se sale del modo abierto
    assert cliente.get("/api/compensacion/mi-rol", params=q(emp)).json()["modo_abierto"] is True
    for u, rol in (("ana.analista", "ANALISTA"), ("sofia.super", "SUPERVISOR"), ("aldo.auditor", "AUDITOR"), ("carla.contadora", "CONTADOR")):
        assert cliente.post("/api/compensacion/roles", params=q(emp), json={"usuario": u, "rol": rol}).status_code == 201
    H = lambda u: {"X-Usuario": u}  # noqa: E731
    assert cliente.get("/api/compensacion/partidas", params=q(emp), headers=H("intruso")).status_code == 403
    assert cliente.get("/api/compensacion/partidas", params=q(emp, por_pagina=1), headers=H("aldo.auditor")).status_code == 200
    assert cliente.post(f"/api/compensacion/grupos/{gid}/aprobar", params=q(emp), json={}, headers=H("aldo.auditor")).status_code == 403
    assert cliente.post(f"/api/compensacion/grupos/{gid}/aprobar", params=q(emp), json={}, headers=H("ana.analista")).status_code == 403
    # separación de funciones: quien propone no aprueba
    p1, p2 = [p for p in partidas(cliente, emp, tercero=T["T17"]) if p["rol"] == "APLICACION"]
    f17 = factura(cliente, emp, "T17", "17")
    g = cliente.post("/api/compensacion/grupos", params=q(emp), headers=H("carla.contadora"), json={
        "izquierda": [{"item_id": f17["id"], "importe": "600"}], "derecha": [{"item_id": p1["id"], "importe": "600"}], "justificacion": "Pago parcial"}).json()
    assert cliente.post(f"/api/compensacion/grupos/{g['id']}/aprobar", params=q(emp), json={}, headers=H("carla.contadora")).status_code == 403
    assert cliente.post(f"/api/compensacion/grupos/{g['id']}/aprobar", params=q(emp), json={}, headers=H("sofia.super")).status_code == 200
    # revertir requiere supervisor
    assert cliente.post(f"/api/compensacion/grupos/{g['id']}/revertir", params=q(emp), json={"comentario": "Error de aplicación detectado"},
                        headers=H("carla.contadora")).status_code == 403
    acciones = {a["accion"] for a in cliente.get("/api/compensacion/auditoria", params=q(emp), headers=H("aldo.auditor")).json()}
    assert {"EJECUTAR", "PROPONER_MANUAL", "APROBAR", "ASIGNAR_ROL"} <= acciones


def test_compensacion_entre_terceros_y_cuentas_requiere_autorizacion(cliente, emp):
    ejecutar(cliente, emp)
    a, b = factura(cliente, emp, "T11A", "11"), factura(cliente, emp, "T11B", "11")
    pago13 = next(p for p in partidas(cliente, emp, tercero=T["T13"]) if p["rol"] == "APLICACION")  # pago sin documento
    body = {"izquierda": [{"item_id": b["id"], "importe": "100"}], "derecha": [{"item_id": pago13["id"], "importe": "100"}], "justificacion": "cruce"}
    r = cliente.post("/api/compensacion/grupos", params=q(emp), json=body)
    assert r.status_code == 422 and "terceros distintos" in r.json()["detail"]
    body.update(autorizar_terceros=True, justificacion="Cesión de derechos según contrato del 10/01/2026 firmado por ambas partes")
    assert cliente.post("/api/compensacion/grupos", params=q(emp), json=body).status_code == 201
    cobro = next(p for p in partidas(cliente, emp, tercero=T["C1"]) if p["rol"] == "ORIGEN")
    r = cliente.post("/api/compensacion/grupos", params=q(emp), json={
        "izquierda": [{"item_id": a["id"], "importe": "50"}], "derecha": [{"item_id": cobro["id"], "importe": "50"}], "justificacion": "neteo"})
    assert r.status_code == 422


# ===================================================================== políticas, idempotencia, conciliación, reportes
def test_autoaprobacion_idempotencia_y_reejecucion(cliente, emp):
    configurar(cliente, emp, "42", autoaprobar=True, umbral_auto=95)
    run = ejecutar(cliente, emp)
    f = factura(cliente, emp, "T1", "1")
    assert D(f["pendiente"]) == 0 and f["estado_revision"] == "APROBADA"
    assert run["resumen"]["autoaprobadas"] >= 1 and run["resumen"]["ambiguas"] >= 1
    r = cliente.post("/api/compensacion/ejecuciones", params=q(emp), json={"fecha_corte": "2026-01-31"}).json()
    assert r["reutilizado"] is True and r["run_id"] == run["id"]  # mismos datos y reglas → mismo resultado
    run2 = ejecutar(cliente, emp, forzar=True)
    gids = cliente.get("/api/compensacion/grupos", params=q(emp, estado="APROBADA")).json()["items"]
    assert len({g["id"] for g in gids}) == len(gids)
    assert D(factura(cliente, emp, "T1", "1")["aplicado"]) == D("10000")  # nunca se aplica dos veces
    assert run2["resumen"]["propuestas_retiradas"] >= 0


def test_conciliacion_con_saldo_contable(cliente, emp):
    ejecutar(cliente, emp)
    for ter in ("T1", "T2", "T3", "T9"):
        for p in partidas(cliente, emp, tercero=T[ter]):
            if p["rol"] == "ORIGEN":
                aprobar_de(cliente, emp, p)
    for corte in ("2025-12-31", "2026-01-31"):
        c = cliente.get("/api/compensacion/conciliacion", params=q(emp, fecha_corte=corte)).json()
        assert c["conciliado"] is True and D(c["totales"]["diferencia"]) == 0, c
    c42 = next(c for c in cliente.get("/api/compensacion/conciliacion", params=q(emp, fecha_corte="2026-01-31")).json()["cuentas"] if c["cuenta"] == "4212")
    assert D(c42["sin_detalle"]) == D("-500")  # saldo inicial de T13 sin detalle, mostrado aparte
    # el saldo contable se calcula de forma independiente desde el libro
    from tests.test_analisis import balance
    _, n = balance(cliente, emp, 1, 1)
    assert D(n["4212"]["saldo_final"]) == D(c42["saldo_contable"])


def test_antiguedad_real_y_dashboard(cliente, emp):
    ejecutar(cliente, emp)
    aprobar_de(cliente, emp, factura(cliente, emp, "T3", "3"))
    a = cliente.get("/api/compensacion/antiguedad", params=q(emp, fecha_corte="2026-01-31")).json()
    assert a["tramos"][-1] == "Sin fecha de vencimiento determinada"
    t3 = next(g for g in a["grupos"] if g["clave"] == T["T3"])
    assert D(t3["total"]) == D("7000") and D(t3["tramos"][1]) == D("7000")  # 11 días vencido
    assert not any(d["documento"] == "F001-1" and d["tramo"] == 0 for d in a["documentos"] if D(d["pendiente"]) == 0)
    via3 = cliente.get("/api/analisis/antiguedad", params=q(emp, ejercicio=2026, fecha_corte="2026-01-31", fuente="COMPENSACION")).json()
    assert via3["totales"] == a["totales"]  # el módulo de antigüedad de la fase 3 usa la composición real
    d = cliente.get("/api/compensacion/dashboard", params=q(emp, fecha_corte="2026-01-31")).json()
    assert d["kpi"]["CXP"]["partidas"] > 0 and "CXC" in d["kpi"] and d["graficos"]["confianza"]["MUY_ALTA"] >= 1
    assert d["observaciones_abiertas"] >= 1


def test_exportaciones_de_reportes(cliente, emp):
    ejecutar(cliente, emp)
    from app.compensacion.consultas import REPORTES
    from openpyxl import load_workbook
    import io
    for rep in REPORTES:
        for fmt in ("xlsx", "pdf"):
            r = cliente.get(f"/api/compensacion/exportar/{rep}.{fmt}", params=q(emp, fecha_corte="2026-01-31"))
            assert r.status_code == 200, (rep, fmt, r.text[:300])
            assert r.content[:4] == (b"PK\x03\x04" if fmt == "xlsx" else b"%PDF")
    ws = load_workbook(io.BytesIO(cliente.get("/api/compensacion/exportar/partidas_abiertas.xlsx", params=q(emp, fecha_corte="2026-01-31")).content)).active
    textos = " ".join(str(c.value) for row in ws.iter_rows(max_row=8) for c in row if c.value)
    for clave in ("Empresa", "Fecha de corte", "Moneda", "Filtros", "Generado"):
        assert clave in textos


# ===================================================================== volumen
def test_mas_de_100000_movimientos(cliente, monkeypatch):
    """100 000 líneas en cuentas compensables (50 000 facturas y pagos) más sus contrapartidas."""
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    from sqlalchemy import insert
    from app.core.database import SessionLocal
    from app.models import LineaDiario, LoteContable
    e = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Volumen SAC"}).json()["id"]
    with SessionLocal() as db:
        lote = LoteContable(empresa_id=e, tipo_informacion="DIARIO", ejercicio=2026, periodo=None, nombre_archivo="volumen.csv",
                            hash_archivo="v" * 64, usuario="prueba", registros_importados=200000)
        db.add(lote)
        db.flush()
        filas = []
        n = 50000
        for i in range(n):
            ter = f"20{i % 2000:09d}"
            imp = D(i % 900 + 100)
            mf, mp = i % 6 + 1, i % 6 + 2
            base = dict(lote_id=lote.id, empresa_id=e, ejercicio=2026, moneda="PEN", debe_me=D(0), haber_me=D(0), documento_tercero=ter)
            fac = dict(base, periodo=mf, fecha_contable=date(2026, mf, i % 28 + 1), subdiario="11", numero_asiento=f"F{i}",
                       tipo_documento="01", serie="F001", numero_documento=str(i))
            filas.append({**fac, "numero_linea": 1, "cuenta": "4212", "debe_mn": D(0), "haber_mn": imp, "glosa": "FACTURA"})
            filas.append({**fac, "numero_linea": 2, "cuenta": "6311", "debe_mn": imp, "haber_mn": D(0), "glosa": "GASTO"})
            if i % 5:  # 80 % pagadas (algunas en forma parcial)
                pag = dict(base, periodo=mp, fecha_contable=date(2026, mp, i % 28 + 1), subdiario="21", numero_asiento=f"P{i}",
                           tipo_documento="01", serie="F001", numero_documento=str(i))
                monto = imp if i % 7 else imp - 50
                filas.append({**pag, "numero_linea": 1, "cuenta": "4212", "debe_mn": monto, "haber_mn": D(0), "glosa": "PAGO"})
                filas.append({**pag, "numero_linea": 2, "cuenta": "104101", "debe_mn": D(0), "haber_mn": monto, "glosa": "BANCO"})
        for i in range(0, len(filas), 20000):
            db.execute(insert(LineaDiario), filas[i:i + 20000])
        db.commit()
        total_lineas = len(filas)
    t0 = time.perf_counter()
    run = ejecutar(cliente, e, corte="2026-12-31")
    t_run = time.perf_counter() - t0
    res = run["resumen"]
    assert res["construccion"]["nuevas"] == 90000 and res["propuestas"] == 40000
    t1 = time.perf_counter()
    c = cliente.get("/api/compensacion/conciliacion", params=q(e, fecha_corte="2026-12-31")).json()
    t_conc = time.perf_counter() - t1
    assert c["conciliado"] is True
    t2 = time.perf_counter()
    pag = cliente.get("/api/compensacion/partidas", params=q(e, fecha_corte="2026-12-31", pagina=10, por_pagina=100, solo_pendientes=True)).json()
    t_pag = time.perf_counter() - t2
    assert len(pag["items"]) == 100
    print(f"\nCompensación con {total_lineas} líneas ({res['construccion']['nuevas']} partidas): ejecución {t_run:.1f}s · "
          f"conciliación {t_conc:.1f}s · página de partidas {t_pag:.1f}s · etapas {run['tiempos']}")
    assert t_run < 300
