from decimal import Decimal
import json


def subir(cliente, ruta, ejemplos, nombre, cuenta_id, tipo, **extra):
    with open(ejemplos / nombre, "rb") as fh:
        return cliente.post(ruta, files={"archivo": (nombre, fh.read())},
                            data={"cuenta_id": str(cuenta_id), "tipo": tipo, **extra})


def test_empresa_valida_ruc_y_unicidad(cliente):
    assert cliente.post("/api/empresas", json={"ruc": "20100047219", "razon_social": "X SAC"}).status_code == 422
    assert cliente.post("/api/empresas", json={"ruc": "20100047218", "razon_social": "Banco SAC"}).status_code == 201
    assert cliente.post("/api/empresas", json={"ruc": "20100047218", "razon_social": "Otro"}).status_code == 409


def test_cuenta_valida_subcuenta_y_duplicados(escenario, cliente):
    emp = escenario["empresa"]
    bcp = escenario["cuentas"]["bcp"]
    base = {"empresa_id": emp["id"], "banco_id": bcp["banco_id"], "moneda": "PEN"}
    assert cliente.post("/api/cuentas", json={**base, "numero_cuenta": "999-999", "cuenta_contable": "421201"}).status_code == 422
    assert cliente.post("/api/cuentas", json={**base, "numero_cuenta": "191-1234567-0-01", "cuenta_contable": "104109"}).status_code == 409
    assert cliente.post("/api/cuentas", json={**base, "numero_cuenta": "191-7777777-0-01", "cuenta_contable": "104101"}).status_code == 409


def test_configuracion_tolerancias(escenario, cliente):
    cid = escenario["cuentas"]["bcp"]["id"]
    cfg = cliente.get(f"/api/cuentas/{cid}/configuracion").json()
    assert cfg["tolerancia_dias"] == 3 and cfg["umbral_auto_confirmacion"] == 95
    nuevo = {**cfg, "tolerancia_dias": 5, "tolerancia_importe": "0.50"}
    r = cliente.put(f"/api/cuentas/{cid}/configuracion", json=nuevo)
    assert r.status_code == 200 and r.json()["tolerancia_dias"] == 5
    malo = {**nuevo, "umbral_sugerencia": 99, "umbral_auto_confirmacion": 90}
    assert cliente.put(f"/api/cuentas/{cid}/configuracion", json=malo).status_code == 422


def test_flujo_importacion_completo(escenario, cliente, ejemplos):
    bcp = escenario["cuentas"]["bcp"]["id"]
    nombre = "estado_bcp_pen_2026-10.csv"

    prev = subir(cliente, "/api/importaciones/vista-previa", ejemplos, nombre, bcp, "BANCO").json()
    assert prev["resumen"]["registros"] == 22
    assert prev["resumen"]["duplicados_archivo"] == 1 and prev["resumen"]["duplicados_base"] == 0
    assert prev["archivo_ya_importado"] is None

    imp = subir(cliente, "/api/importaciones", ejemplos, nombre, bcp, "BANCO")
    assert imp.status_code == 201, imp.text
    imp = imp.json()
    assert imp["total_registros"] == 22 and imp["total_duplicados"] == 1 and imp["usuario"] == "tesorero.prueba"

    # el mismo archivo no se puede volver a importar sin forzar
    assert subir(cliente, "/api/importaciones", ejemplos, nombre, bcp, "BANCO").status_code == 409

    # reimportación forzada omitiendo duplicados existentes → no ingresa nada nuevo
    r = subir(cliente, "/api/importaciones", ejemplos, nombre, bcp, "BANCO", forzar="true", accion_duplicados="omitir")
    assert r.status_code == 201 and r.json()["total_registros"] == 1 and r.json()["total_omitidos"] == 21

    movs = cliente.get("/api/movimientos/banco", params={"cuenta_id": bcp, "solo_duplicados": True}).json()
    assert movs["total"] == 2
    dup = movs["items"][0]

    r = cliente.post(f"/api/movimientos/banco/{dup['id']}/duplicado", json={"decision": "EXCLUIR", "comentario": "fila repetida"})
    assert r.status_code == 200 and r.json()["estado_conciliacion"] == "EXCLUIDO"

    itf = cliente.get("/api/movimientos/banco", params={"cuenta_id": bcp, "categoria": "ITF"}).json()
    assert itf["total"] == 9

    # anulación con motivo y auditoría
    assert cliente.post(f"/api/importaciones/{imp['id']}/anular", json={"motivo": "x"}).status_code == 422
    r = cliente.post(f"/api/importaciones/{imp['id']}/anular", json={"motivo": "Archivo de prueba"})
    assert r.status_code == 200 and r.json()["estado"] == "ANULADA"
    pend = cliente.get("/api/movimientos/banco", params={"importacion_id": imp["id"], "estado": "PENDIENTE"}).json()
    assert pend["total"] == 0

    acciones = [a["accion"] for a in cliente.get("/api/auditoria").json()]
    assert {"IMPORTAR", "ANULAR", "DUPLICADO_EXCLUIR", "CREAR"} <= set(acciones)


def test_importar_libro_y_panel(escenario, cliente, ejemplos):
    bcp = escenario["cuentas"]["bcp"]["id"]
    bbva = escenario["cuentas"]["bbva"]["id"]
    r = subir(cliente, "/api/importaciones", ejemplos, "libro_mayor_cuenta10_2026-10.xlsx", bcp, "LIBRO")
    assert r.status_code == 201 and r.json()["total_registros"] == 14
    assert r.json()["saldo_inicial"] == "50000.00"
    # el mismo mayor sirve para la subcuenta en dólares
    r = subir(cliente, "/api/importaciones", ejemplos, "libro_mayor_cuenta10_2026-10.xlsx", bbva, "LIBRO")
    assert r.status_code == 201 and r.json()["total_registros"] == 3
    det = cliente.get(f"/api/importaciones/{r.json()['id']}").json()
    assert det["mapeo"]["columnas"]["Debe"] == "debe"

    subir(cliente, "/api/importaciones", ejemplos, "estado_interbank_pen_2026-10.pdf",
          escenario["cuentas"]["ibk"]["id"], "BANCO")
    panel = cliente.get("/api/panel", params={"empresa_id": escenario["empresa"]["id"]}).json()
    por_cc = {c["cuenta_contable"]: c for c in panel["cuentas"]}
    assert por_cc["104101"]["libro_resumen"]["movimientos"] == 14
    assert por_cc["104103"]["ultimo_saldo_banco"] == "21842.70"


def test_mapeo_manual_via_api(escenario, cliente, tmp_path):
    bcp = escenario["cuentas"]["bcp"]["id"]
    contenido = "A;B;C\n05/10/2026;Pago raro;-75.00\n".encode()
    r = cliente.post("/api/importaciones/vista-previa", files={"archivo": ("x.csv", contenido)},
                     data={"cuenta_id": str(bcp), "tipo": "BANCO"})
    assert r.status_code == 422
    r = cliente.post("/api/importaciones/vista-previa", files={"archivo": ("x.csv", contenido)},
                     data={"cuenta_id": str(bcp), "tipo": "BANCO",
                           "mapeo": json.dumps({"0": "fecha", "1": "descripcion", "2": "importe"})})
    assert r.status_code == 200 and r.json()["registros"][0]["importe"] == "-75.00"


def test_neto_excluye_duplicados_excluidos(escenario, cliente, ejemplos):
    bcp = escenario["cuentas"]["bcp"]["id"]
    imp = subir(cliente, "/api/importaciones", ejemplos, "estado_bcp_pen_2026-10.csv", bcp, "BANCO").json()
    dup = cliente.get("/api/movimientos/banco", params={"cuenta_id": bcp, "solo_duplicados": True}).json()["items"][0]
    cliente.post(f"/api/movimientos/banco/{dup['id']}/duplicado", json={"decision": "EXCLUIR"})
    datos = cliente.get("/api/movimientos/banco", params={"cuenta_id": bcp}).json()
    # neto = saldo final − saldo inicial del estado de cuenta
    assert datos["total"] == 22
    assert datos["suma_importes"] == "8269.70" == str(Decimal(imp["saldo_final"]) - Decimal(imp["saldo_inicial"]))
    # restaurar y volver a excluir queda auditado
    r = cliente.post(f"/api/movimientos/banco/{dup['id']}/duplicado", json={"decision": "RESTAURAR"})
    assert r.json()["estado_conciliacion"] == "PENDIENTE"
