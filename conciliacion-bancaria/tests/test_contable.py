"""Pruebas end-to-end del analizador contable (fase 2) con los archivos de ejemplo."""
import subprocess
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
EJ = RAIZ / "ejemplos" / "contable"


@pytest.fixture(scope="module", autouse=True)
def ejemplos_contables():
    if not (EJ / "balance_comprobacion_2026-10.xls").exists():
        subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_ejemplos_contables.py")], check=True)


@pytest.fixture()
def empresa(cliente, monkeypatch):
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    return cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Comercial Andina"}).json()["id"]


def subir(cliente, empresa, nombre):
    r = cliente.post("/api/contable/archivos", files={"archivo": (nombre, (EJ / nombre).read_bytes())},
                     data={"empresa_id": str(empresa)})
    assert r.status_code == 201, r.text
    return r.json()


def preparar(cliente, empresa, nombre, tipo, **extra):
    """Pasos 3–5 del asistente: subir, detectar encabezado y aceptar la homologación sugerida."""
    meta = subir(cliente, empresa, nombre)
    prev = cliente.get(f"/api/contable/archivos/{meta['token']}/vista-previa", params={"tipo": tipo}).json()
    sug = prev["sugerencia_encabezado"]
    params = {"empresa_id": empresa, "tipo": tipo, "ejercicio": 2026, "periodo": 10,
              "fila_encabezado": sug["fila"], "filas_encabezado": sug["filas"], **extra}
    hom = cliente.post(f"/api/contable/archivos/{meta['token']}/homologacion", json=params).json()
    params["mapeo"] = {c: v["columna"] for c, v in hom["mapeo_sugerido"].items()}
    params.update(extra)
    return meta["token"], params, hom


def validar(cliente, token, params):
    r = cliente.post(f"/api/contable/archivos/{token}/validacion", json=params)
    assert r.status_code == 202, r.text
    t = r.json()
    assert t["estado"] == "COMPLETADO", t
    return t["resultado"]


def confirmar(cliente, token, params, **extra):
    r = cliente.post(f"/api/contable/archivos/{token}/confirmacion", json={**params, **extra})
    assert r.status_code == 202, r.text
    return r.json()


def obs(cliente, token, **filtros):
    return cliente.get(f"/api/contable/archivos/{token}/observaciones", params={"por_pagina": 500, **filtros}).json()["items"]


def importar(cliente, empresa, nombre, tipo, **extra):
    token, params, _ = preparar(cliente, empresa, nombre, tipo, **extra)
    validar(cliente, token, params)
    t = confirmar(cliente, token, params, confirmar_criticos=True, motivo_criticos="Carga de datos de prueba")
    assert t["estado"] == "COMPLETADO", t
    return t["resultado"]


def cargar_maestros(cliente, empresa):
    importar(cliente, empresa, "plan_cuentas_concar.xlsx", "PLAN_CUENTAS")
    importar(cliente, empresa, "centros_costo.csv", "CENTROS_COSTO")
    importar(cliente, empresa, "tipos_cambio_2026-10.csv", "TIPOS_CAMBIO")
    importar(cliente, empresa, "proveedores.xlsx", "PROVEEDORES")


def test_catalogo(cliente):
    c = cliente.get("/api/contable/catalogo").json()
    assert len(c["tipos"]) == 13
    diario = next(t for t in c["tipos"] if t["clave"] == "DIARIO")
    obligatorios = {x["clave"] for x in diario["campos"] if x["obligatorio"]}
    assert {"fecha_contable", "numero_asiento", "cuenta"} <= obligatorios
    assert {"debe_mn", "haber_mn", "importe_mn"} <= {x["clave"] for x in diario["campos"] if x["alternativo"]}
    assert {o["severidad"] for o in c["observaciones"]} == {"CRITICO", "ALTO", "MEDIO", "INFORMATIVO"}


def test_maestros_y_validaciones(cliente, empresa):
    cargar_maestros(cliente, empresa)
    res = cliente.get(f"/api/contable/resumen/{empresa}").json()["maestros"]
    assert res == {"PLAN_CUENTAS": 34, "CENTROS_COSTO": 2, "CLIENTES": 0, "PROVEEDORES": 3, "TIPOS_CAMBIO": 31}
    plan = {c["codigo"]: c for c in cliente.get("/api/contable/maestros/PLAN_CUENTAS", params={"empresa_id": empresa}).json()}
    assert plan["4699"]["activa"] is False and plan["104"]["admite_movimiento"] is False
    assert plan["6211"]["cuenta_destino_debe"] == "9411" and plan["6211"]["naturaleza"] == "D"
    # observaciones guardadas del maestro de proveedores (RUC inválido) y de tipos de cambio (salto atípico)
    lotes = {l["tipo_informacion"]: l for l in cliente.get("/api/contable/lotes", params={"empresa_id": empresa}).json()}
    codigos_prov = {o["codigo"] for o in cliente.get(f"/api/contable/lotes/{lotes['PROVEEDORES']['id']}/observaciones").json()["items"]}
    assert "TER001" in codigos_prov
    codigos_tc = {o["codigo"] for o in cliente.get(f"/api/contable/lotes/{lotes['TIPOS_CAMBIO']['id']}/observaciones").json()["items"]}
    assert "TC004" in codigos_tc


def test_diario_concar_reglas(cliente, empresa):
    cargar_maestros(cliente, empresa)
    token, params, hom = preparar(cliente, empresa, "diario_concar_2026-10.xlsx", "DIARIO", sistema_origen="CONCAR")
    assert hom["faltantes"] == []
    res = validar(cliente, token, params)
    r = res["resumen"]
    assert r["filas_subtotal"] == 13 and r["filas_vacias"] >= 12   # 12 subtotales + total general
    assert r["registros_excluidos"] == 1                            # la línea con importe inválido
    assert r["asientos"] == 12
    o = obs(cliente, token)
    cod = {x["codigo"] for x in o}
    esperados = {"IMP001", "PD001", "CTA001", "CTA002", "CTA003", "FEC002", "DUP001", "CC001", "TC002",
                 "DES001", "DES002", "DES006", "TOT001", "EST003", "EST002"}
    assert esperados <= cod, esperados - cod
    pd = next(x for x in o if x["codigo"] == "PD001" and x["asiento"] == "01-0006")
    assert pd["severidad"] == "CRITICO" and pd["archivo"] == "diario_concar_2026-10.xlsx" and pd["hoja"] == "Diario"
    assert pd["fila"] is not None and "diferencia 10.00" in pd["mensaje"]
    # el asiento 0012 queda descuadrado porque su línea con importe inválido se excluye
    assert any(x["codigo"] == "PD001" and x["asiento"] == "01-0012" for x in o)
    cta = next(x for x in o if x["codigo"] == "CTA001")
    assert cta["cuenta"] == "109999" and cta["recomendacion"]
    # una factura con varias líneas en el MISMO asiento no es duplicado
    assert all(x["asiento"] == "05-0010" for x in o if x["codigo"] == "DUP001")

    # sin confirmar críticos no se importa
    r = cliente.post(f"/api/contable/archivos/{token}/confirmacion", json=params).json()
    assert r["estado"] == "ERROR" and r["status"] == 409
    lote = confirmar(cliente, token, params, confirmar_criticos=True, motivo_criticos="Se corregirá en noviembre")["resultado"]
    assert lote["registros_importados"] == 33 and lote["obs_critico"] >= 3 and lote["total_archivo_debe"]
    regs = cliente.get(f"/api/contable/lotes/{lote['id']}/registros", params={"por_pagina": 500}).json()
    usd = next(x for x in regs["items"] if x["cuenta"] == "104102")
    assert usd["moneda"] == "USD" and usd["tipo_cambio"] == "3.720000" and usd["debe_me"] == "1000.00"
    assert usd["fila_origen"] and usd["hoja"] == "Diario"
    csv = cliente.get(f"/api/contable/lotes/{lote['id']}/observaciones.csv")
    assert csv.status_code == 200 and "PD001" in csv.text


def test_sap_homologacion_manual_y_plantilla(cliente, empresa):
    token, params, hom = preparar(cliente, empresa, "diario_sap_2026-10.csv", "DIARIO", sistema_origen="SAP",
                                  separador_decimal="COMA")
    enc = hom["encabezados"]
    assert hom["faltantes"] == [["numero_asiento"]]
    # En SAP «Nº documento» es el asiento y «Referencia» el comprobante: el usuario corrige
    params["mapeo"]["numero_asiento"] = enc.index("Nº documento")
    params["mapeo"]["numero_documento"] = enc.index("Referencia")
    params["mapeo"]["indicador_dh"] = enc.index("Clave contabiliz.")
    res = validar(cliente, token, params)
    assert res["resumen"]["severidades"]["CRITICO"] == 0
    assert res["resumen"]["total_debe"] == res["resumen"]["total_haber"] == "13634.00"
    lote = confirmar(cliente, token, params, guardar_plantilla="SAP FBL3N diario")["resultado"]
    assert lote["plantilla_id"]

    # segundo archivo SAP: la plantilla se aplica sola
    token2, params2, hom2 = preparar(cliente, empresa, "diario_sap_2026-10.csv", "DIARIO", sistema_origen="SAP")
    assert hom2["plantilla_aplicada"]["nombre"] == "SAP FBL3N diario"
    assert hom2["mapeo_sugerido"]["numero_asiento"]["origen"] == "PLANTILLA"
    assert hom2["opciones_plantilla"]["separador_decimal"] == "COMA"
    params2["separador_decimal"] = "COMA"
    res2 = validar(cliente, token2, params2)
    cod = res2["resumen"]["codigos"]
    assert "DUP003" in cod and "DUP002" in cod  # mismo archivo y mismos documentos ya importados


def test_compras_txt_sin_encabezado(cliente, empresa):
    cargar_maestros(cliente, empresa)
    meta = subir(cliente, empresa, "compras_2026-10.txt")
    assert meta["formato"] == "TXT"
    prev = cliente.get(f"/api/contable/archivos/{meta['token']}/vista-previa", params={"tipo": "COMPRAS"}).json()
    assert prev["sugerencia_encabezado"]["fila"] == 0 and len(prev["filas"][0]) == 16
    columnas = ["periodo", "cuo", "fecha_emision", "fecha_vencimiento", "tipo_documento", "serie", "numero_documento",
                "tipo_documento_identidad", "documento_tercero", "razon_social", "base_imponible", "igv", "no_gravado",
                "total", "moneda", "tipo_cambio"]
    params = {"empresa_id": empresa, "tipo": "COMPRAS", "ejercicio": 2026, "periodo": 10, "fila_encabezado": 0,
              "mapeo": {c: i for i, c in enumerate(columnas) if c != "periodo"}}
    res = validar(cliente, meta["token"], params)
    assert res["resumen"]["registros_validos"] == 6
    o = obs(cliente, meta["token"])
    cod = {x["codigo"] for x in o}
    assert {"REG001", "REG002", "TER001", "TER002", "DUP001", "FEC002"} <= cod
    assert next(x for x in o if x["codigo"] == "FEC002")["severidad"] == "INFORMATIVO"
    lote = confirmar(cliente, meta["token"], params, guardar_plantilla="Compras TXT")["resultado"]
    assert lote["registros_importados"] == 6


def test_balance_xls_dos_filas_y_cruces(cliente, empresa):
    cargar_maestros(cliente, empresa)
    importar(cliente, empresa, "saldos_iniciales_2026.xlsx", "SALDOS_INICIALES", periodo=0)
    importar(cliente, empresa, "diario_concar_2026-10.xlsx", "DIARIO")
    token, params, hom = preparar(cliente, empresa, "balance_comprobacion_2026-10.xls", "BALANCE")
    assert params["filas_encabezado"] == 2 and hom["faltantes"] == []
    params["periodo"] = None  # balance acumulado del ejercicio
    res = validar(cliente, token, params)
    o = obs(cliente, token)
    cod = {x["codigo"] for x in o}
    assert "SAL001" in cod and any(x["cuenta"] == "7011" for x in o if x["codigo"] == "SAL001")
    assert "PD003" in cod          # el error en 7011 descuadra los saldos finales
    # Los movimientos coinciden con el diario salvo en la 5011: el diario se importó con la línea de
    # importe inválido excluida (asiento 0012 a medias) y el cruce lo detecta.
    assert {x["cuenta"] for x in o if x["codigo"] == "SAL002"} == {"5011"}
    assert "SAL003" not in cod     # saldos iniciales coinciden con la apertura importada
    # Los movimientos descuadran exactamente por el asiento 0006 (10.00). Si las filas de resumen
    # (cuentas de 2 dígitos) se sumaran junto a las de detalle, la diferencia sería 20.00.
    pd_mov = next(x for x in o if x["codigo"] == "PD003" and "movimientos" in x["mensaje"])
    assert "diferencia 10.00" in pd_mov["mensaje"]


def test_anulacion_y_reemplazo(cliente, empresa):
    importar(cliente, empresa, "saldos_iniciales_2026.xlsx", "SALDOS_INICIALES", periodo=0)
    lote = importar(cliente, empresa, "saldos_iniciales_2026.xlsx", "SALDOS_INICIALES", periodo=0, reemplazar_previos=True)
    lotes = cliente.get("/api/contable/lotes", params={"empresa_id": empresa, "tipo": "SALDOS_INICIALES"}).json()
    assert [l["estado"] for l in lotes] == ["ACTIVO", "ANULADO"]
    r = cliente.post(f"/api/contable/lotes/{lote['id']}/anular", json={"motivo": "Archivo incorrecto"})
    assert r.status_code == 200 and r.json()["estado"] == "ANULADO"
    maestro = cliente.get("/api/contable/lotes", params={"empresa_id": empresa}).json()
    plan = importar(cliente, empresa, "plan_cuentas_concar.xlsx", "PLAN_CUENTAS")
    assert cliente.post(f"/api/contable/lotes/{plan['id']}/anular", json={"motivo": "no"*3}).status_code == 409
    acciones = {a["accion"] for a in cliente.get("/api/auditoria").json() if a["entidad"] == "lote_contable"}
    assert {"IMPORTAR", "ANULAR"} <= acciones and maestro


def test_configuracion_analitica(cliente, empresa):
    cargar_maestros(cliente, empresa)
    cfg = cliente.get(f"/api/contable/configuracion/{empresa}").json()
    cfg.update(usa_clase_9=False)
    assert cliente.put(f"/api/contable/configuracion/{empresa}", json=cfg).status_code == 200
    token, params, _ = preparar(cliente, empresa, "diario_concar_2026-10.xlsx", "DIARIO")
    cod = validar(cliente, token, params)["resumen"]["codigos"]
    assert "DES001" not in cod and "DES002" not in cod and "DES007" in cod
    # regla específica configurable: 63 exige destino 95 en el mismo asiento
    cfg.update(usa_clase_9=True)
    cliente.put(f"/api/contable/configuracion/{empresa}", json=cfg)
    r = cliente.post("/api/contable/reglas-destino", json={"empresa_id": empresa, "prefijo_origen": "63",
                                                           "destino_debe": "95", "destino_haber": "79",
                                                           "descripcion": "Servicios a gastos de ventas"})
    assert r.status_code == 201
    cod = validar(cliente, token, params)["resumen"]["codigos"]
    assert "DES005" in cod


def test_trabajo_asincrono_con_progreso(cliente, monkeypatch):
    monkeypatch.delenv("CONTABLE_TRABAJOS_SINCRONOS", raising=False)
    emp = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "X SAC"}).json()["id"]
    token, params, _ = preparar(cliente, emp, "diario_concar_2026-10.xlsx", "DIARIO")
    t = cliente.post(f"/api/contable/archivos/{token}/validacion", json=params).json()
    for _ in range(100):
        t = cliente.get(f"/api/contable/trabajos/{t['id']}").json()
        if t["estado"] in ("COMPLETADO", "ERROR"):
            break
        time.sleep(0.05)
    assert t["estado"] == "COMPLETADO" and t["progreso"] == 100


def test_archivos_invalidos(cliente, empresa):
    r = cliente.post("/api/contable/archivos", files={"archivo": ("x.xlsx", b"no es excel")},
                     data={"empresa_id": str(empresa)})
    assert r.status_code == 422 and "estructuralmente" in r.json()["detail"] or "válido" in r.json()["detail"]
    r = cliente.post("/api/contable/archivos", files={"archivo": ("x.pdf", b"%PDF-1.4 ...")},
                     data={"empresa_id": str(empresa)})
    assert r.status_code == 422
    # columnas obligatorias faltantes → EST001 crítico y no se puede confirmar
    meta = subir(cliente, empresa, "centros_costo.csv")
    params = {"empresa_id": empresa, "tipo": "DIARIO", "ejercicio": 2026, "periodo": 10, "mapeo": {"cuenta": 0}}
    res = validar(cliente, meta["token"], params)
    assert res["resumen"]["estructura_valida"] is False
    t = confirmar(cliente, meta["token"], params, confirmar_criticos=True, motivo_criticos="forzar import")
    assert t["estado"] == "ERROR"
