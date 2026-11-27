"""Pruebas de la fase 7: Auditor contable inteligente 360 (datos sintéticos).

Cada escenario verifica el caso positivo (la regla lo detecta con evidencia) y el negativo (un caso legítimo parecido no
se observa). El libro se importa por el flujo real de la fase 2 y las fuentes auxiliares por los flujos de las fases 1, 5 y 6.
"""
import io
import time
from datetime import date
from decimal import Decimal

import pytest

from tests.test_analisis import importar_bytes
from tests.test_conciliaciones import (CAB6, CONTADOR, GERENTE, PLANILLA, PROV, SUPERVISOR, W1, asiento, aux, base, cobro, conciliar, crear, diario,  # noqa: F401
                                       ejecutar as ejecutar_conc, estado_banco, gasto, pago_b, provision, q, reg_compras, roles, subir)

D = Decimal
AUDITOR = "aldo.auditor"


def enc(cliente, e, usuario=CONTADOR, **kw):
    body = {"tipo": "INTEGRAL", "ejercicio": 2026, "periodo": 1, **kw}
    r = cliente.post("/api/auditoria360/encargos", params=q(e), json=body, headers={"X-Usuario": usuario})
    assert r.status_code == 201, r.text
    return r.json()


def correr(cliente, e, eid, usuario=CONTADOR, reglas=None, **kw):
    body = {"tipo": "REGLAS" if reglas else kw.pop("tipo", "COMPLETA"), **({"reglas": reglas} if reglas else {}), **kw}
    r = cliente.post(f"/api/auditoria360/encargos/{eid}/ejecutar", params=q(e), json=body, headers={"X-Usuario": usuario})
    assert r.status_code == 202, r.text
    assert r.json()["trabajo"]["estado"] == "COMPLETADO", r.json()["trabajo"]
    run = cliente.get(f"/api/auditoria360/ejecuciones/{r.json()['run_id']}", params=q(e), headers={"X-Usuario": usuario}).json()
    assert run["estado_proceso"] == "COMPLETADO", run
    return run


def hz(cliente, e, eid, usuario=CONTADOR, **f):
    r = cliente.get("/api/auditoria360/hallazgos", params=q(e, engagement_id=eid, por_pagina=500, **f), headers={"X-Usuario": usuario})
    assert r.status_code == 200, r.text
    return r.json()["items"]


def de(hs, regla, **cond):
    return [h for h in hs if h["regla"] == regla and all(h.get(k) == v for k, v in cond.items())]


def estado_regla(run, codigo):
    return next(x for x in run["resultados"] if x["codigo"] == codigo)


def regla_id(cliente, e, codigo):
    return next(x["id"] for x in cliente.get("/api/auditoria360/reglas", params=q(e), headers={"X-Usuario": SUPERVISOR}).json() if x["codigo"] == codigo)


def personalizar(cliente, e, codigo, usuario=SUPERVISOR, **d):
    r = cliente.put(f"/api/auditoria360/reglas/{regla_id(cliente, e, codigo)}", params=q(e), json=d, headers={"X-Usuario": usuario})
    assert r.status_code == 200, r.text
    return r.json()


def estado(cliente, e, hid, nuevo, usuario, comentario=None, **extra):
    return cliente.post(f"/api/auditoria360/hallazgos/{hid}/estado", params=q(e), json={"estado": nuevo, "comentario": comentario, **extra},
                        headers={"X-Usuario": usuario})


def csv_emision(filas):
    """Diario con columna de fecha de emisión (última columna de cada fila)."""
    return (CAB6 + ";Fecha Emision\n" + "\n".join(";".join(str(x) for x in f) for f in filas) + "\n").encode()


# ===================================================================== 1 · asiento descuadrado
def test_01_asiento_descuadrado(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("31", "DQ1", "10/01/2026", [("6361", "", {"debe": "1000", "glosa": "ENERGIA"}),
                                                            ("4699", PROV["P1"], {"haber": "900", "glosa": "PROVISION ENERGIA"})])
           + asiento("31", "OK1", "11/01/2026", [("6361", "", {"debe": "500", "glosa": "ENERGIA"}), ("4699", PROV["P1"], {"haber": "500", "glosa": "PROV"})]))
    a = enc(cliente, e)
    run = correr(cliente, e, a["id"], reglas=["INT-01"])
    hs = hz(cliente, e, a["id"])
    assert len(hs) == 1  # solo el asiento descuadrado
    h = hs[0]
    assert h["asiento"] == "31-DQ1" and D(h["importe"]) == D("100") and h["riesgo"] in ("ALTO", "MEDIO", "CRITICO")
    det = cliente.get(f"/api/auditoria360/hallazgos/{h['id']}", params=q(e)).json()
    assert det["estructural"] is True and det["tipo"] == "POTENCIAL"
    assert any(ev["tabla"] == "lineas_diario" and ev["registro_id"] for ev in det["evidencias"])  # trazable al registro original
    assert estado_regla(run, "INT-01")["estado"] == "CON_EXCEPCIONES" and estado_regla(run, "INT-01")["poblacion"] == 2


# ===================================================================== 2–5 · duplicidades
def test_02_03_04_05_duplicidades_y_pagos(cliente, base):
    e = base["e"]
    diario(cliente, e,
           provision("K1", "03/01/2026", PROV["P1"], "F100", "1", "1000", "180")
           + provision("K1B", "20/01/2026", PROV["P1"], "F100", "00001", "1000", "180")          # 2 · misma factura (numeración con ceros)
           + asiento("11", "K2", "05/01/2026", [("6011", PROV["P2"], {"debe": "600", "glosa": "COMPRA A"}),   # 3 · varias líneas legítimas
                                                 ("6311", PROV["P2"], {"debe": "400", "glosa": "FLETE"}),
                                                 ("40111", PROV["P2"], {"debe": "180", "glosa": "IGV"}),
                                                 ("4212", PROV["P2"], {"td": "01", "serie": "F200", "num": "2", "haber": "700", "glosa": "FACTURA F200-2 PARTE 1"}),
                                                 ("4212", PROV["P2"], {"td": "01", "serie": "F200", "num": "2", "haber": "480", "glosa": "FACTURA F200-2 PARTE 2"})])
           + provision("K3", "06/01/2026", PROV["P3"], "F300", "3", "1000", "180")
           + asiento("21", "PG3A", "15/01/2026", [("4212", PROV["P3"], {"td": "01", "serie": "F300", "num": "3", "debe": "1180", "glosa": "PAGO F300-3"}),
                                                   ("104101", "", {"num": "0451388", "haber": "1180", "glosa": "TRANSF"})])
           + asiento("21", "PG3B", "18/01/2026", [("4212", PROV["P3"], {"td": "01", "serie": "F300", "num": "3", "debe": "1180", "glosa": "PAGO F300-3"}),
                                                   ("104101", "", {"num": "0451399", "haber": "1180", "glosa": "TRANSF"})])          # 4 · pago duplicado
           + provision("K4", "07/01/2026", PROV["P4"], "F400", "4", "1000", "180")
           + asiento("21", "PG4A", "15/01/2026", [("4212", PROV["P4"], {"td": "01", "serie": "F400", "num": "4", "debe": "500", "glosa": "PAGO PARCIAL"}),
                                                   ("104101", "", {"num": "0451400", "haber": "500", "glosa": "TRANSF"})])
           + asiento("21", "PG4B", "25/01/2026", [("4212", PROV["P4"], {"td": "01", "serie": "F400", "num": "4", "debe": "680", "glosa": "PAGO SALDO"}),
                                                   ("104101", "", {"num": "0451401", "haber": "680", "glosa": "TRANSF"})]))     # 5 · pago parcial correcto
    a = enc(cliente, e)
    correr(cliente, e, a["id"], reglas=["DUP-01", "DUP-05", "GAS-01"])
    hs = hz(cliente, e, a["id"])
    d2 = de(hs, "DUP-01")
    assert len(d2) == 1 and "F100" in d2[0]["titulo"] and D(d2[0]["importe"]) == D("1180")   # 2 · duplicado exacto pese a la numeración
    assert not [h for h in hs if "F200" in (h["titulo"] + (h["documento"] or ""))]            # 3 · las líneas del mismo asiento son legítimas
    d4 = de(hs, "DUP-05")
    assert len(d4) == 1 and D(d4[0]["importe"]) == D("1180") and "F300" in d4[0]["documento"]   # 4 · exceso sobre el documento
    assert not [h for h in hs if (h["documento"] or "").startswith("F400")]                   # 5 · pagos parciales que no exceden: sin hallazgo
    # 23 · superposición: el mismo duplicado lo detectan DUP-01 (compras) y GAS-01 (gasto) → una sola exposición
    g = de(hs, "GAS-01")
    assert g and g[0]["grupo_id"] == d2[0]["grupo_id"]
    tab = cliente.get("/api/auditoria360/tablero", params=q(e, engagement_id=a["id"])).json()["kpi"]
    assert D(tab["exposicion_potencial"]) < D(tab["exposicion_bruta"])
    assert D(tab["exposicion_potencial"]) == D("1180") + D("1180")   # el duplicado F100-1 cuenta una vez aunque lo vean dos reglas


# ===================================================================== 6–7 · cuentas por cobrar y por pagar
def test_06_07_saldo_antiguo_y_anticipo(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("05", "V1", "02/01/2026", [("1212", "20555555551", {"td": "01", "serie": "F001", "num": "1", "debe": "2360", "rs": "CLIENTE UNO",
                                                                                   "glosa": "VENTA"}), ("7011", "", {"haber": "2360", "glosa": "VENTA"})])
           + asiento("05", "V2", "28/01/2026", [("1212", "20555555552", {"td": "01", "serie": "F001", "num": "2", "debe": "1180", "rs": "CLIENTE DOS",
                                                                         "glosa": "VENTA"}), ("7011", "", {"haber": "1180", "glosa": "VENTA"})])
           + asiento("21", "AN1", "03/01/2026", [("4221", PROV["P5"], {"debe": "3000", "glosa": "ANTICIPO A PROVEEDOR"}),
                                                  ("104101", "", {"num": "0459000", "haber": "3000", "glosa": "TRANSF"})])
           + asiento("21", "AN2", "29/01/2026", [("4221", PROV["P4"], {"debe": "800", "glosa": "ANTICIPO RECIENTE"}),
                                                  ("104101", "", {"num": "0459001", "haber": "800", "glosa": "TRANSF"})]))
    # parámetros de la empresa (personalización versionada de reglas del catálogo)
    personalizar(cliente, e, "CXC-02", parametros={"dias": 20}, usuario=AUDITOR)
    r = personalizar(cliente, e, "CXP-04", parametros={"dias": 10}, usuario=AUDITOR)
    assert r["empresa_id"] == e
    a = enc(cliente, e)
    correr(cliente, e, a["id"], reglas=["CXC-02", "CXP-04"])
    hs = hz(cliente, e, a["id"])
    d6 = de(hs, "CXC-02")
    assert [h["documento"] for h in d6] == ["F001-1"] and D(d6[0]["importe"]) == D("2360")        # 29 días > 20; F001-2 (3 días) no
    assert "no determina" in d6[0]["recomendacion"] or "no se determina" in d6[0]["recomendacion"].lower() or "antigüedad no" in d6[0]["recomendacion"]
    d7 = de(hs, "CXP-04")
    assert len(d7) == 1 and D(d7[0]["importe"]) == D("3000") and d7[0]["tercero"] == PROV["P5"]   # el anticipo reciente no se observa
    assert d7[0]["tipo"] == "POTENCIAL"


# ===================================================================== 8–10 · origen y destino
def test_08_09_10_origen_destino(cliente, base):
    e = base["e"]
    diario(cliente, e, gasto("G1", "10/01/2026", "6361", "800", [("9411", "800")])
           + gasto("G2", "15/01/2026", "6351", "1200")                                  # 8 · sin destino
           + gasto("G3", "20/01/2026", "6371", "500", [("9411", "500"), ("9411", "500")]))  # 9 · destino dos veces
    rubros = ("Cuenta;Rubro;Estado Financiero\n6351;Gastos de administración;RESULTADOS\n6361;Gastos de administración;RESULTADOS\n"
              "9411;Gastos administrativos;RESULTADOS\n1041;Efectivo;BALANCE\n").encode()
    r = cliente.post("/api/auditoria360/configuraciones", params=q(e), data={"tipo": "RUBROS_UTILIZADOS", "sistema": "CONCAR"},
                     files={"archivo": ("rubros.csv", rubros)})
    assert r.status_code == 201 and r.json()["registros"] == 4, r.text
    a = enc(cliente, e, tipo="PARAMETRIZACION")
    run = correr(cliente, e, a["id"])
    assert all(x["modulo"] in ("PARAMETRIZACION", "ORIGEN_DESTINO") for x in run["resultados"])
    hs = hz(cliente, e, a["id"])
    d8 = de(hs, "ODE-01")
    assert [h["asiento"] for h in d8] == ["31-G2"] and D(d8[0]["importe"]) == D("1200")
    d9 = de(hs, "ODE-03")
    assert [h["asiento"] for h in d9] == ["31-G3"] and D(d9[0]["importe"]) == D("500")
    d10 = de(hs, "ODE-08")
    assert len(d10) == 1 and "9411" in d10[0]["condicion"] and "dos veces" in d10[0]["impacto_potencial"]
    # reporte de origen y destino (sección 11)
    x = cliente.get(f"/api/auditoria360/encargos/{a['id']}/exportar/ORIGEN_DESTINO", params=q(e))
    import openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(x.content)).worksheets[0]
    cab = [c.value for c in next(ws.iter_rows(min_row=4, max_row=4))]
    assert cab[:8] == ["Cuenta de origen", "Importe original", "Importe sujeto a distribución", "Destino esperado", "Destino registrado",
                       "Cuenta de transferencia", "Diferencia", "Asiento"]


# ===================================================================== 11 · parametrización
def test_11_diferencia_de_parametrizacion(cliente, base):
    e = base["e"]
    aprobado = "Cuenta;Descripcion;Naturaleza;Admite Movimiento\n1212;Facturas emitidas;D;S\n4212;Facturas por pagar;A;S\n".encode()
    utilizado = "Cuenta;Descripcion;Naturaleza;Admite Movimiento\n1212;Facturas emitidas;A;S\n4212;Facturas por pagar;A;S\n".encode()
    for tipo, cont in (("PLAN_APROBADO", aprobado), ("PLAN_UTILIZADO", utilizado)):
        assert cliente.post("/api/auditoria360/configuraciones", params=q(e), data={"tipo": tipo, "sistema": "SAP"},
                            files={"archivo": (f"{tipo}.csv", cont)}).status_code == 201
    # nueva versión del plan utilizado sin sustento (cambio de configuración)
    utilizado2 = utilizado.replace(b"4212;Facturas por pagar;A", b"4212;Facturas por pagar;D")
    assert cliente.post("/api/auditoria360/configuraciones", params=q(e), data={"tipo": "PLAN_UTILIZADO", "sistema": "SAP"},
                        files={"archivo": ("v2.csv", utilizado2)}).json()["version"] == 2
    a = enc(cliente, e, tipo="PARAMETRIZACION")
    correr(cliente, e, a["id"], reglas=["PAR-01", "PAR-06", "PAR-07"])
    hs = hz(cliente, e, a["id"])
    assert {h["cuenta"] for h in de(hs, "PAR-07")} == {"1212", "4212"}
    assert {h["cuenta"] for h in de(hs, "PAR-01")} == {"1212", "4212"}   # naturaleza distinta a la del PCGE
    assert len(de(hs, "PAR-06")) == 1 and "sin sustento" in de(hs, "PAR-06")[0]["titulo"]
    # 11b · sin configuración de reportes: la regla no concluye (limitada a datos observables)
    run = correr(cliente, e, a["id"], reglas=["PAR-03"])
    assert estado_regla(run, "PAR-03")["estado"] == "SIN_DATOS"


# ===================================================================== 12–14 · servicios en proceso y activos fijos
SERV = ("proyecto;cuenta;cliente;contrato;estado_operativo;estado_facturacion\n"
        "P-100;2311;MINERA ANDINA;CT-55;CULMINADO;PENDIENTE DE FACTURAR\nP-200;2311;MINERA ANDINA;CT-56;EN EJECUCION;PENDIENTE\n").encode()
ACT = ("codigo;cuenta;descripcion;categoria;fecha_adquisicion;fecha_uso;costo_inicial;vida_util_meses;valor_residual;cuenta_depreciacion;"
       "depreciacion_acumulada_inicial\nAF-1;3341;CAMION;VEHICULOS;02/01/2026;01/01/2026;12000;120;0;3913;0\n"
       "AF-2;3341;COMPRESORA;MAQUINARIA;01/01/2020;01/01/2020;6000;60;0;3913;6000\n").encode()


def test_12_13_14_servicios_y_activos(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("31", "SP1", "31/01/2026", [("2311", "", {"debe": "6000", "glosa": "COSTO P-100", "proyecto": "P-100"}),
                                                            ("7111", "", {"haber": "6000", "glosa": "VARIACION", "proyecto": "P-100"})])
           + asiento("31", "SP2", "31/01/2026", [("2311", "", {"debe": "2000", "glosa": "COSTO P-200", "proyecto": "P-200"}),
                                                  ("7111", "", {"haber": "2000", "glosa": "VARIACION", "proyecto": "P-200"})])
           + asiento("21", "AF1", "02/01/2026", [("3341", "", {"debe": "12000", "glosa": "CAMION", "maq": "AF-1"}),
                                                  ("4651", PROV["P5"], {"haber": "12000", "glosa": "COMPRA", "td": "01", "serie": "F500", "num": "1"})])
           + asiento("31", "DP1", "31/01/2026", [("6814", "", {"debe": "13000", "glosa": "DEPRECIACION AF-1", "maq": "AF-1"}),
                                                  ("3913", "", {"haber": "13000", "glosa": "DEPRECIACION AF-1", "maq": "AF-1"})])     # 13 · excede el costo
           + asiento("21", "AF2", "05/01/2026", [("3341", "", {"debe": "6000", "glosa": "COMPRESORA", "maq": "AF-2"}),
                                                  ("3913", "", {"haber": "6000", "glosa": "DEP ACUMULADA COMPRESORA", "maq": "AF-2"})]))  # 14 · totalmente depreciado
    aux(cliente, e, "SERVICIO_PROCESO", "servicios.csv", SERV)
    aux(cliente, e, "ACTIVO_FIJO", "activos.csv", ACT)
    a = enc(cliente, e)
    correr(cliente, e, a["id"], reglas=["SPR-01", "ACT-04", "ACT-08"])
    hs = hz(cliente, e, a["id"])
    d12 = de(hs, "SPR-01")
    assert len(d12) == 1 and "P-100" in d12[0]["titulo"] and D(d12[0]["importe"]) == D("6000")   # P-200 en ejecución no se observa
    assert "fecha de facturación no es el único criterio" in d12[0]["recomendacion"]
    d13 = de(hs, "ACT-04")
    assert d13 and all("AF-1" in h["titulo"] or "AF-1" in h["condicion"] for h in d13)
    d14 = de(hs, "ACT-08")
    assert len(d14) == 1 and d14[0]["riesgo"] == "INFORMATIVO" and "no se recomienda su baja automática" in d14[0]["recomendacion"]


# ===================================================================== 15–16 · planillas
def test_15_16_planillas(cliente, base):
    from tests.test_conciliaciones import LIBRO_PLANILLA
    e = base["e"]
    diario(cliente, e, LIBRO_PLANILLA
           + asiento("35", "JU1", "05/01/2026", [("6211", "", {"debe": "300", "glosa": "REMUNERACION", "cc": "ADM"}),
                                                  ("4699", W1, {"haber": "300", "glosa": "RETENCION JUDICIAL ALIMENTOS", "rs": "TRABAJADOR UNO"})]))
    roles(cliente, e, [("pedro.planillas", "PLANILLAS"), (CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), (AUDITOR, "AUDITOR"),
                       ("carlos.consulta", "CONSULTA")])
    c = crear(cliente, e, "PLANILLAS", usuario="pedro.planillas")
    subir(cliente, e, c["id"], "A", "planilla.csv", PLANILLA, usuario="pedro.planillas")
    ejecutar_conc(cliente, e, c["id"], usuario="pedro.planillas")
    a = enc(cliente, e, ejercicio=2026, periodo=2)
    run = correr(cliente, e, a["id"], reglas=["PLA-01", "PLA-04"])
    assert estado_regla(run, "PLA-01")["estado"] == "CON_EXCEPCIONES"
    hs = hz(cliente, e, a["id"], usuario=AUDITOR)
    d15 = de(hs, "PLA-01")
    assert any(h["tercero"] == "41234567" and D(h["importe"]) == D("2250") for h in d15)         # remuneración neta no contabilizada (fase 6)
    d16 = de(hs, "PLA-04")
    assert len(d16) == 1 and D(d16[0]["importe"]) == D("300") and d16[0]["personal"]
    # datos personales protegidos para el usuario de consulta
    ver = hz(cliente, e, a["id"], usuario="carlos.consulta")
    x = next(h for h in ver if h["id"] == d16[0]["id"])
    assert x["tercero"] != W1 and x["razon_social"] == "Trabajador (reservado)"


# ===================================================================== 17–18, 24 · tributaria preventiva
def test_17_18_24_tributaria(cliente, base):
    e = base["e"]
    from tests.test_conciliaciones import CAB_DET
    reg = (CAB_DET + "\n" + f"05/01/2026;01;F600;1;{PROV['P5']};PROVEEDOR CINCO;10000;1800;0;11800;PEN;037\n"
           f"06/01/2026;01;F600;2;{PROV['P5']};PROVEEDOR CINCO;5000;900;0;5900;PEN;037\n").encode()
    importar_bytes(cliente, e, "compras.csv", reg, "COMPRAS", periodo=1, ejercicio=2026)
    diario(cliente, e, asiento("21", "DT2", "12/01/2026", [("4212", PROV["P5"], {"td": "01", "serie": "F600", "num": "2", "debe": "708",
                                                                                 "glosa": "DETRACCION", "const": "C-0002", "cod": "037"}),
                                                            ("104201", "", {"haber": "708", "glosa": "BN"})])
           + asiento("31", "RP1", "20/01/2026", [("6592", "", {"debe": "450", "glosa": "MULTA MUNICIPAL"}), ("4699", PROV["P1"], {"haber": "450", "glosa": "MULTA"})]))
    roles(cliente, e, [(CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), (AUDITOR, "AUDITOR")])
    a = enc(cliente, e, tipo="TRIBUTARIA_PREVENTIVA")
    run = correr(cliente, e, a["id"], reglas=["TRI-03", "TRI-07"])
    assert estado_regla(run, "TRI-07")["estado"] == "NO_VALIDADA"           # regla normativa sin validar: no se ejecuta
    hs = hz(cliente, e, a["id"])
    d17 = de(hs, "TRI-03")
    assert [h["documento"] for h in d17] == ["F600-1"] and d17[0]["tratamiento_tributario"] == "PENDIENTE_EVALUACION"
    assert not de(hs, "TRI-07")
    # 18 · el auditor completa la norma (datos sintéticos) y el supervisor la valida
    rid = regla_id(cliente, e, "TRI-07")
    r = cliente.put(f"/api/auditoria360/reglas/{rid}", params=q(e), headers={"X-Usuario": AUDITOR},
                    json={"cuentas": "6592", "norma_referencia": "Norma sintética de prueba art. 1", "fuente_oficial": "Fuente sintética",
                          "fecha_publicacion": "2025-01-01", "vigente_desde": "2025-01-01", "condiciones_aplicacion": "Gastos de la cuenta indicada",
                          "responsable_validacion": SUPERVISOR})
    assert r.status_code == 200 and r.json()["estado_validacion"] == "PENDIENTE" and r.json()["activa"] is True
    nueva = r.json()["id"]
    assert cliente.post(f"/api/auditoria360/reglas/{nueva}/validar", params=q(e), json={}, headers={"X-Usuario": AUDITOR}).status_code == 403
    v = cliente.post(f"/api/auditoria360/reglas/{nueva}/validar", params=q(e), json={"comentario": "Revisada"}, headers={"X-Usuario": SUPERVISOR})
    assert v.status_code == 200 and v.json()["estado_validacion"] == "VALIDADA"
    correr(cliente, e, a["id"], reglas=["TRI-07"])
    d18 = de(hz(cliente, e, a["id"]), "TRI-07")
    assert len(d18) == 1 and D(d18[0]["importe"]) == D("450") and d18[0]["tratamiento_tributario"] == "POSIBLE_DIFERENCIA_PERMANENTE"
    assert "potencialmente" in d18[0]["titulo"]
    # 24 · fuera de vigencia: la misma regla no se aplica a un corte posterior a su vigencia
    r = cliente.put(f"/api/auditoria360/reglas/{nueva}", params=q(e), headers={"X-Usuario": AUDITOR}, json={"vigente_hasta": "2025-12-31"})
    assert r.json()["estado_validacion"] == "PENDIENTE"  # todo cambio normativo exige nueva validación
    cliente.post(f"/api/auditoria360/reglas/{nueva}/validar", params=q(e), json={}, headers={"X-Usuario": SUPERVISOR})
    b = enc(cliente, e, tipo="TRIBUTARIA_PREVENTIVA")
    run = correr(cliente, e, b["id"], reglas=["TRI-07"])
    assert estado_regla(run, "TRI-07")["estado"] == "FUERA_DE_VIGENCIA" and not hz(cliente, e, b["id"])
    vers = cliente.get(f"/api/auditoria360/reglas/{nueva}/versiones", params=q(e)).json()
    assert len(vers) >= 1


# ===================================================================== 19–20 · devengos y corte
def test_19_20_provision_duplicada_y_corte(cliente, base):
    e = base["e"]
    luz = lambda asi, f, imp: asiento("31", asi, f, [("6361", "", {"debe": imp, "glosa": "PROVISION ENERGIA ENERO"}),  # noqa: E731
                                                     ("4699", PROV["P1"], {"haber": imp, "glosa": "PROVISION ENERGIA ENERO"})])
    filas = luz("PR1", "31/01/2026", "500") + luz("PR2", "31/01/2026", "500") + luz("PR3", "31/01/2026", "320")
    filas = [f + ["31/01/2026"] for f in filas]
    # 20 · factura emitida en enero y contabilizada en febrero (evento posterior al corte)
    filas += [f + ["28/01/2026"] for f in asiento("11", "FB1", "05/02/2026", [("6311", PROV["P2"], {"debe": "2000", "glosa": "SERVICIO ENERO"}),
                                                                             ("4212", PROV["P2"], {"td": "01", "serie": "F777", "num": "9", "haber": "2000",
                                                                                                   "glosa": "FACTURA SERVICIO ENERO"})])]
    filas += [f + ["03/02/2026"] for f in asiento("11", "FB2", "06/02/2026", [("6311", PROV["P3"], {"debe": "900", "glosa": "SERVICIO FEBRERO"}),
                                                                             ("4212", PROV["P3"], {"td": "01", "serie": "F777", "num": "10", "haber": "900",
                                                                                                   "glosa": "FACTURA FEBRERO"})])]
    importar_bytes(cliente, e, "diario.csv", csv_emision(filas), "DIARIO", periodo=None, ejercicio=2026)
    a = enc(cliente, e)
    correr(cliente, e, a["id"], reglas=["DEV-06", "DEV-03"])
    hs = hz(cliente, e, a["id"])
    d19 = de(hs, "DEV-06")
    assert len(d19) == 1 and D(d19[0]["importe"]) == D("500")      # la provisión de 320 (importe distinto) no se observa
    d20 = de(hs, "DEV-03")
    assert [h["documento"] for h in d20] == ["F777-9"] and D(d20[0]["importe"]) == D("2000")  # la de febrero no
    det = cliente.get(f"/api/auditoria360/hallazgos/{d20[0]['id']}", params=q(e)).json()
    assert "no integra el saldo histórico" in det["evidencias"][0]["descripcion"]
    # el saldo histórico al corte no cambia
    bal = {n["cuenta"]: n["saldo_final"] for n in cliente.get("/api/analisis/balance", params=q(e, ejercicio=2026, desde=1, hasta=1)).json()["nodos"]}
    assert D(bal.get("4212", "0")) == 0


# ===================================================================== 21, 22, 25 · flujo de hallazgos
def test_21_22_25_evidencia_falso_positivo_y_reapertura(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("21", "MS1", "10/01/2026", [("104101", "", {"debe": "5000", "glosa": "X"}), ("7591", "", {"haber": "5000", "glosa": "X"})])
           + asiento("21", "MS2", "12/01/2026", [("104101", "", {"haber": "3000", "glosa": "."}), ("6591", "", {"debe": "3000", "glosa": "."})]))
    roles(cliente, e, [(CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), (AUDITOR, "AUDITOR"), (GERENTE, "GERENCIA")])
    a = enc(cliente, e)
    correr(cliente, e, a["id"], reglas=["BAN-09"])
    hs = sorted(de(hz(cliente, e, a["id"]), "BAN-09"), key=lambda h: h["asiento"])
    assert len(hs) == 2
    h1, h2 = hs
    det = cliente.get(f"/api/auditoria360/hallazgos/{h1['id']}", params=q(e), headers={"X-Usuario": AUDITOR}).json()
    assert det["calidad_evidencia"] == "INSUFICIENTE"
    # separación de funciones: quien ejecutó no confirma
    assert estado(cliente, e, h1["id"], "CONFIRMADO", CONTADOR).status_code == 403
    # 21 · evidencia insuficiente: no se confirma sin evidencia de revisión
    r = estado(cliente, e, h1["id"], "CONFIRMADO", AUDITOR)
    assert r.status_code == 422 and "Evidencia insuficiente" in r.json()["detail"]
    up = cliente.post(f"/api/auditoria360/hallazgos/{h1['id']}/evidencias", params=q(e), files={"archivo": ("voucher.pdf", b"%PDF-1.4 sintetico")},
                      data={"descripcion": "Voucher del depósito sin sustento de origen"}, headers={"X-Usuario": AUDITOR})
    assert up.status_code == 201 and up.json()["origen"] == "USUARIO"
    r = estado(cliente, e, h1["id"], "CONFIRMADO", AUDITOR, "Confirmado con el voucher", regularizacion="REQUIERE_DOCUMENTACION")
    assert r.status_code == 200 and r.json()["tipo"] == "CONFIRMADO"
    # 22 · falso positivo con justificación; no se duplica ni reaparece al volver a ejecutar
    assert estado(cliente, e, h2["id"], "FALSO_POSITIVO", AUDITOR, "corto").status_code == 422
    r = estado(cliente, e, h2["id"], "FALSO_POSITIVO", AUDITOR, "Pago de multa con resolución adjunta en el ERP")
    assert r.status_code == 200 and r.json()["tipo"] == "FALSO_POSITIVO" and r.json()["estado"] == "CERRADO"
    correr(cliente, e, a["id"], reglas=["BAN-09"], forzar=True)
    otra = de(hz(cliente, e, a["id"]), "BAN-09")
    assert len(otra) == 2 and next(h for h in otra if h["id"] == h2["id"])["tipo"] == "FALSO_POSITIVO"
    # 25 · ciclo de subsanación, cierre y reapertura
    assert estado(cliente, e, h1["id"], "EN_SUBSANACION", CONTADOR).status_code == 422   # exige plan de acción
    p = cliente.post(f"/api/auditoria360/hallazgos/{h1['id']}/planes", params=q(e), headers={"X-Usuario": CONTADOR},
                     json={"descripcion": "Obtener el sustento del depósito", "responsable": CONTADOR, "fecha_compromiso": "2026-02-15"})
    assert p.status_code == 201
    assert estado(cliente, e, h1["id"], "EN_SUBSANACION", CONTADOR).status_code == 200
    assert estado(cliente, e, h1["id"], "CERRADO", SUPERVISOR, "Cierre sin verificación previa").status_code == 422   # confirmado sin verificación
    assert estado(cliente, e, h1["id"], "SUBSANADO", CONTADOR, "Se obtuvo el contrato de préstamo").status_code == 200
    assert estado(cliente, e, h1["id"], "VERIFICADO", CONTADOR, "Yo mismo").status_code in (403,)                     # quien subsana no verifica
    assert estado(cliente, e, h1["id"], "VERIFICADO", AUDITOR, "Contrato revisado y conforme").status_code == 200
    assert estado(cliente, e, h1["id"], "CERRADO", AUDITOR, "El verificador no cierra su verificación").status_code == 403
    r = estado(cliente, e, h1["id"], "CERRADO", SUPERVISOR, "Cierre aprobado con la verificación del auditor")
    assert r.status_code == 200 and r.json()["estado"] == "CERRADO" and r.json()["tipo"] == "SUBSANADO"
    assert estado(cliente, e, h1["id"], "REABIERTO", GERENTE, "La gerencia no reabre").status_code == 403
    r = estado(cliente, e, h1["id"], "REABIERTO", AUDITOR, "Nueva información: el contrato no corresponde")
    assert r.status_code == 200 and r.json()["estado"] == "REABIERTO"
    hist = [x["a_estado"] for x in r.json()["historial"] if x["de_estado"] != x["a_estado"]]
    assert hist == ["CONFIRMADO", "EN_SUBSANACION", "SUBSANADO", "VERIFICADO", "CERRADO", "REABIERTO"]
    # bandeja de regularizaciones (fase 8): solo confirmados clasificados; no se generan asientos
    r = estado(cliente, e, h1["id"], "CONFIRMADO", AUDITOR, "Reconfirmado", regularizacion="REQUIERE_AJUSTE")
    assert r.status_code == 200
    r = cliente.post(f"/api/auditoria360/hallazgos/{h1['id']}/regularizacion", params=q(e), headers={"X-Usuario": CONTADOR})
    assert r.status_code == 200 and r.json()["en_bandeja_regularizacion"] is True
    assert cliente.get("/api/auditoria360/hallazgos", params=q(e, bandeja=True), headers={"X-Usuario": CONTADOR}).json()["total"] == 1


# ===================================================================== materialidad y riesgo
def test_materialidad_y_ajuste_de_riesgo(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("31", "DQ1", "10/01/2026", [("6361", "", {"debe": "1000", "glosa": "ENERGIA"}),
                                                            ("4699", PROV["P1"], {"haber": "990", "glosa": "PROV"})]))
    roles(cliente, e, [(CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), (AUDITOR, "AUDITOR")])
    sin = cliente.post("/api/auditoria360/materialidad", params=q(e), json={"ejercicio": 2026, "base": "ACTIVOS", "justificacion": "x"},
                       headers={"X-Usuario": AUDITOR})
    assert sin.status_code == 422  # sin porcentajes por defecto
    m = cliente.post("/api/auditoria360/materialidad", params=q(e), headers={"X-Usuario": AUDITOR},
                     json={"ejercicio": 2026, "base": "OTRA", "importe_base": "100000", "porcentaje_global": "2", "porcentaje_ejecucion": "75",
                           "porcentaje_insignificante": "5", "justificacion": "Base sintética de prueba",
                           "cualitativos": {"reglas": ["INT-01"]}}).json()
    assert (D(m["materialidad_global"]), D(m["materialidad_ejecucion"]), D(m["umbral_insignificante"])) == (D("2000"), D("1500"), D("100"))
    assert cliente.post(f"/api/auditoria360/materialidad/{m['id']}/aprobar", params=q(e), headers={"X-Usuario": AUDITOR}).status_code == 403
    assert cliente.post(f"/api/auditoria360/materialidad/{m['id']}/aprobar", params=q(e), headers={"X-Usuario": SUPERVISOR}).json()["estado"] == "APROBADA"
    a = enc(cliente, e)
    correr(cliente, e, a["id"], reglas=["INT-01"])
    h = de(hz(cliente, e, a["id"]), "INT-01")[0]
    det = cliente.get(f"/api/auditoria360/hallazgos/{h['id']}", params=q(e), headers={"X-Usuario": AUDITOR}).json()
    # importe 10 claramente insignificante, pero cualitativamente relevante: no se excluye y su impacto no baja de 3
    assert det["claramente_insignificante"] and det["impacto"] >= 3
    r = cliente.patch(f"/api/auditoria360/hallazgos/{h['id']}", params=q(e), headers={"X-Usuario": AUDITOR}, json={"riesgo": "BAJO"})
    assert r.status_code == 422
    r = cliente.patch(f"/api/auditoria360/hallazgos/{h['id']}", params=q(e), headers={"X-Usuario": AUDITOR},
                      json={"riesgo": "BAJO", "justificacion_riesgo": "Diferencia de redondeo documentada en el ERP"})
    assert r.status_code == 200 and r.json()["riesgo"] == "BAJO" and r.json()["riesgo_ajustado_por"] == AUDITOR
    assert r.json()["riesgo_calculado"] != "BAJO" and "redondeo" in r.json()["justificacion_riesgo"]


# ===================================================================== reglas configurables
def test_regla_configurable_con_vista_previa(cliente, base):
    e = base["e"]
    diario(cliente, e, gasto("G1", "10/01/2026", "6361", "800") + gasto("G2", "15/01/2026", "6351", "12000") + gasto("G3", "20/01/2026", "6371", "15000"))
    roles(cliente, e, [(CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), (AUDITOR, "AUDITOR")])
    a = enc(cliente, e)
    defi = {"fuente": "LINEAS", "condiciones": {"y": [{"campo": "cuenta", "op": "empieza", "valor": "63"}, {"o": [
        {"campo": "importe", "op": ">", "valor": 10000}, {"campo": "glosa", "op": "contiene", "valor": "URGENTE"}]}]}, "titulo": "Gasto de servicios alto {cuenta}"}
    mal = cliente.post("/api/auditoria360/reglas/vista-previa", params=q(e), headers={"X-Usuario": AUDITOR},
                       json={"engagement_id": a["id"], "definicion": {"fuente": "LINEAS", "condiciones": {"campo": "cuenta; DROP TABLE x", "op": "=", "valor": "1"}}})
    assert mal.status_code == 422
    vp = cliente.post("/api/auditoria360/reglas/vista-previa", params=q(e), headers={"X-Usuario": AUDITOR},
                      json={"engagement_id": a["id"], "definicion": defi}).json()
    assert vp["coincidencias"] == 2 and {x["cuenta"] for x in vp["muestra"]} == {"6351", "6371"}
    assert not hz(cliente, e, a["id"])  # la vista previa no genera hallazgos
    r = cliente.post("/api/auditoria360/reglas", params=q(e), headers={"X-Usuario": AUDITOR},
                     json={"codigo": "EMP-01", "nombre": "Servicios de importe alto", "definicion": defi, "riesgo": "MEDIO"})
    assert r.status_code == 201 and r.json()["activa"] is False
    rid = r.json()["id"]
    assert cliente.post(f"/api/auditoria360/reglas/{rid}/activar", params=q(e), json={"activa": True}, headers={"X-Usuario": AUDITOR}).status_code == 200
    correr(cliente, e, a["id"], reglas=["EMP-01"])
    hs = de(hz(cliente, e, a["id"]), "EMP-01")
    assert len(hs) == 2 and hs[0]["titulo"].startswith("Gasto de servicios alto 63")


# ===================================================================== 26 · exportación de informes
def test_26_informes_y_exportaciones(cliente, base):
    import openpyxl
    import pdfplumber
    e = base["e"]
    diario(cliente, e, provision("K1", "03/01/2026", PROV["P1"], "F100", "1", "1000", "180") + provision("K1B", "20/01/2026", PROV["P1"], "F100", "1", "1000", "180")
           + gasto("G2", "15/01/2026", "6351", "1200") + gasto("G1", "10/01/2026", "6361", "800", [("9411", "800")]))
    a = enc(cliente, e)
    correr(cliente, e, a["id"])
    for tipo in ("GERENCIA", "CONTADOR", "AUDITORIA_INTERNA", "TRIBUTARIO", "PARAMETRIZACION"):
        r = cliente.post(f"/api/auditoria360/encargos/{a['id']}/informes", params=q(e), json={"tipo": tipo})
        assert r.status_code == 201, r.text
        assert len(r.json()["contenido"]) == 16
    r = cliente.post(f"/api/auditoria360/encargos/{a['id']}/informes", params=q(e), json={"tipo": "DETALLE_CUENTA", "cuenta": "42"})
    inf = cliente.post(f"/api/auditoria360/encargos/{a['id']}/informes", params=q(e), json={"tipo": "GERENCIA"}).json()
    assert inf["version_actual"] == 2 and len(inf["hash"]) == 64
    pdf = cliente.get(f"/api/auditoria360/informes/{inf['id']}/exportar", params=q(e, formato="pdf"))
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    with pdfplumber.open(io.BytesIO(pdf.content)) as p:
        texto = " ".join(pg.extract_text() or "" for pg in p.pages)
    assert "No constituye un dictamen" in texto and "Matriz de riesgos" in texto and "Plan de acción" in texto and "Página 1 de" in texto
    x = cliente.get(f"/api/auditoria360/informes/{inf['id']}/exportar", params=q(e, formato="xlsx"))
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert "9. Principales hallazgos" in wb.sheetnames
    for tipo in ("INFORME_DETALLADO", "MATRIZ_RIESGOS", "POR_CUENTA", "POR_TERCERO", "TRIBUTARIOS", "PARAMETRIZACION", "DUPLICIDADES", "PAPELES",
                 "PLANES", "SEGUIMIENTO", "RECURRENTES", "ORIGEN_DESTINO"):
        for fmt in ("xlsx", "pdf"):
            r = cliente.get(f"/api/auditoria360/encargos/{a['id']}/exportar/{tipo}", params=q(e, formato=fmt))
            assert r.status_code == 200 and len(r.content) > 500, (tipo, fmt, r.text[:200])
    det = openpyxl.load_workbook(io.BytesIO(cliente.get(f"/api/auditoria360/encargos/{a['id']}/exportar/INFORME_DETALLADO", params=q(e)).content)).worksheets[0]
    cab = [c.value for c in next(det.iter_rows(min_row=4, max_row=4))]
    assert "Línea original (lineas_diario.id)" in cab
    # papel de trabajo y muestra reproducible
    p = cliente.post(f"/api/auditoria360/encargos/{a['id']}/papeles", params=q(e), json={"regla": "DUP-01"}, headers={"X-Usuario": CONTADOR}).json()
    assert p["contenido"]["regla"]["codigo"] == "DUP-01" and "conclusion_preliminar" in p["contenido"] and p["estado"] == "PRELIMINAR"
    m1 = cliente.post(f"/api/auditoria360/encargos/{a['id']}/muestras", params=q(e), json={"metodo": "ALEATORIA", "tamano": 3, "semilla": 42}).json()
    m2 = cliente.post(f"/api/auditoria360/encargos/{a['id']}/muestras", params=q(e), json={"metodo": "ALEATORIA", "tamano": 3, "semilla": 42}).json()
    assert [i["registro_id"] for i in m1["items"]] == [i["registro_id"] for i in m2["items"]] and m1["estadisticamente_representativa"]
    m3 = cliente.post(f"/api/auditoria360/encargos/{a['id']}/muestras", params=q(e), json={"metodo": "RIESGO", "poblacion": "HALLAZGOS", "tamano": 2}).json()
    assert m3["estadisticamente_representativa"] is False and "no es estadísticamente representativa" in m3["nota"]


# ===================================================================== 27 · procesamiento masivo
def test_27_procesamiento_masivo(cliente, base, capsys):
    """100 000 movimientos (50 000 asientos de dos líneas) importados por el flujo real y auditados con todas las reglas."""
    e = base["e"]
    filas = []
    for i in range(50000):
        f = f"{(i % 28) + 1:02d}/01/2026"
        imp = f"{100 + (i % 997) + (i % 7) * 0.01:.2f}"
        filas += asiento("11", f"M{i}", f, [("6361" if i % 3 else "6351", "", {"debe": imp, "glosa": f"SERVICIO {i % 50}", "cc": f"CC{i % 12}"}),
                                             ("4212", f"20{100000000 + i % 300:09d}", {"td": "01", "serie": f"F{i % 40:03d}", "num": str(i), "haber": imp,
                                                                                    "glosa": "FACTURA"})])
    t0 = time.perf_counter()
    diario(cliente, e, filas, nombre="masivo.csv")
    t1 = time.perf_counter()
    a = enc(cliente, e)
    run = correr(cliente, e, a["id"])
    t2 = time.perf_counter()
    run2 = correr(cliente, e, a["id"])
    t3 = time.perf_counter()
    ej = run["resumen"]["ejecucion"]
    assert ej["movimientos_evaluados"] == 100000 and ej["reglas"] >= 160
    assert all(x["estado"] != "ERROR" for x in run["resultados"]), [x for x in run["resultados"] if x["estado"] == "ERROR"]
    assert all(x["estado"] in ("REUTILIZADA", "NO_VALIDADA") for x in run2["resultados"])  # incremental: sin cambios no se recalcula
    lentas = sorted(run["tiempos"].items(), key=lambda x: -x[1])[:5]
    with capsys.disabled():
        print(f"\n[volumen fase 7] 100 000 movimientos · importación {t1 - t0:.1f} s · auditoría completa {t2 - t1:.1f} s "
              f"({run['duracion_ms']} ms en el motor, {ej['reglas']} reglas, {run['resumen']['totales']['hallazgos']} hallazgos) · "
              f"re-ejecución incremental {t3 - t2:.1f} s · reglas más lentas {lentas}")
    assert t2 - t1 < 600


# ===================================================================== 28 · seguridad multiempresa y bitácora
def test_28_seguridad_multiempresa_y_bitacora(cliente, base):
    from sqlalchemy import text

    from app.core.database import SessionLocal
    e = base["e"]
    b = cliente.post("/api/empresas", json={"ruc": "20100047218", "razon_social": "Otra Empresa SAC"}).json()["id"]
    diario(cliente, e, asiento("31", "DQ1", "10/01/2026", [("6361", "", {"debe": "1000", "glosa": "X"}), ("4699", PROV["P1"], {"haber": "900", "glosa": "X"})]))
    roles(cliente, e, [(CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), ("ext.auditor", "AUDITOR_EXTERNO"), ("carlos.consulta", "CONSULTA")])
    roles(cliente, b, [("solo.b", "ADMINISTRADOR")], admin="admin.b")
    a = enc(cliente, e)
    correr(cliente, e, a["id"], reglas=["INT-01"])
    h = hz(cliente, e, a["id"])[0]
    # otra empresa: no ve ni el encargo ni sus hallazgos
    assert cliente.get(f"/api/auditoria360/encargos/{a['id']}", params=q(b), headers={"X-Usuario": "solo.b"}).status_code == 404
    assert cliente.get(f"/api/auditoria360/hallazgos/{h['id']}", params=q(b), headers={"X-Usuario": "solo.b"}).status_code == 404
    assert cliente.get("/api/auditoria360/hallazgos", params=q(b), headers={"X-Usuario": "solo.b"}).json()["total"] == 0
    assert cliente.get("/api/auditoria360/hallazgos", params=q(e), headers={"X-Usuario": "solo.b"}).status_code == 403
    # auditor externo: solo con acceso asignado y vigente
    assert cliente.get(f"/api/auditoria360/encargos/{a['id']}", params=q(e), headers={"X-Usuario": "ext.auditor"}).status_code == 403
    assert cliente.post("/api/auditoria360/asignaciones", params=q(e), headers={"X-Usuario": SUPERVISOR},
                        json={"tipo": "AUDITOR_EXTERNO", "usuario": "ext.auditor", "engagement_id": a["id"], "vigente_hasta": "2099-12-31"}).status_code == 201
    assert cliente.get(f"/api/auditoria360/encargos/{a['id']}", params=q(e), headers={"X-Usuario": "ext.auditor"}).status_code == 200
    # consulta: lee pero no modifica
    assert estado(cliente, e, h["id"], "EN_ANALISIS", "carlos.consulta").status_code == 403
    assert cliente.post(f"/api/auditoria360/encargos/{a['id']}/ejecutar", params=q(e), json={}, headers={"X-Usuario": "carlos.consulta"}).status_code == 403
    # bitácora encadenada e inmutable
    bit = cliente.get("/api/auditoria360/bitacora", params=q(e), headers={"X-Usuario": SUPERVISOR}).json()
    assert bit["verificacion"]["integra"] and bit["total"] >= 3
    with SessionLocal() as s:
        with pytest.raises(Exception):
            s.execute(text("UPDATE audit_event_logs SET usuario = 'otro' WHERE empresa_id = :e"), {"e": e})
            s.commit()
        s.rollback()
        with pytest.raises(Exception):
            s.execute(text("DELETE FROM audit_event_logs WHERE empresa_id = :e"), {"e": e})
            s.commit()
    assert cliente.get("/api/auditoria360/bitacora", params=q(e), headers={"X-Usuario": SUPERVISOR}).json()["verificacion"]["integra"]


# ===================================================================== auditoría completa, encargo y conclusión
def test_auditoria_completa_y_conclusion(cliente, base):
    e = base["e"]
    diario(cliente, e, provision("K1", "03/01/2026", PROV["P1"], "F100", "1", "1000", "180") + cobro("C1", "05/01/2026", "0451201", "1500"))
    estado_banco(cliente, base["cb"], [("05/01/2026", "DEPOSITO", "1500", "0451201"), ("31/01/2026", "COMISION MANTENIMIENTO", "-15", "")])
    roles(cliente, e, [(CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), (AUDITOR, "AUDITOR")])
    a = enc(cliente, e, recurrencia="MENSUAL", alcance={"modulos": ["TESORERIA", "INTEGRIDAD", "DUPLICIDADES", "TRIBUTARIA"]})
    run = correr(cliente, e, a["id"])
    mods = {x["modulo"] for x in run["resultados"]}
    assert mods == {"TESORERIA", "INTEGRIDAD", "DUPLICIDADES", "TRIBUTARIA"}
    hs = hz(cliente, e, a["id"])
    assert any(h["regla"] == "BAN-02" and "Comision" in h["titulo"] for h in hs)   # comisión no registrada (fase 6 en memoria)
    # ejecución por cuenta
    run = correr(cliente, e, a["id"], tipo="CUENTA", cuentas=["42"])
    assert run["tipo"] == "CUENTA"
    # conclusión: quien ejecutó no la aprueba
    assert cliente.post(f"/api/auditoria360/encargos/{a['id']}/estado", params=q(e), json={"estado": "EN_REVISION"}, headers={"X-Usuario": CONTADOR}).status_code == 200
    c = {"estado": "CONCLUIDO", "conclusion": "Conclusión preliminar: hallazgos de tesorería pendientes de regularización."}
    assert cliente.post(f"/api/auditoria360/encargos/{a['id']}/estado", params=q(e), json=c, headers={"X-Usuario": CONTADOR}).status_code == 403
    r = cliente.post(f"/api/auditoria360/encargos/{a['id']}/estado", params=q(e), json=c, headers={"X-Usuario": SUPERVISOR})
    assert r.status_code == 200 and r.json()["conclusion_aprobada_por"] == SUPERVISOR
    # auditoría recurrente: encargo del periodo siguiente con el mismo alcance
    sig = cliente.post(f"/api/auditoria360/encargos/{a['id']}/programar-siguiente", params=q(e), headers={"X-Usuario": CONTADOR}).json()
    assert sig["fecha_corte"] == "2026-02-28" and sig["alcance"]["modulos"] == sorted(["TESORERIA", "INTEGRIDAD", "DUPLICIDADES", "TRIBUTARIA"])
    assert date.fromisoformat(sig["fecha_corte"]) > date.fromisoformat(a["fecha_corte"])
