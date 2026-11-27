"""Pruebas de la fase 6: motor de conciliaciones contables automáticas.

Todos los datos son sintéticos. El libro se importa por el flujo real de la fase 2, los estados bancarios por el de
la fase 1 y las fuentes externas (planillas, kardex, constancias…) por el importador de la propia conciliación,
que reutiliza la homologación de columnas de la fase 2. Cada escenario verifica la clasificación de la diferencia,
su importe y que los asientos originales no se modifican.
"""
import io
import time
from datetime import date
from decimal import Decimal

import pytest

from tests.test_analisis import importar_bytes
from tests.test_compensacion import CAB
from tests.test_compensacion import fila as fila4

D = Decimal
SUNAT = "20131312955"
PROV = {"P1": "20100100101", "P2": "20100100202", "P3": "20100100303", "P4": "20100100404", "P5": "20100100505"}
W1, W2 = "45678912", "41234567"
CAB6 = CAB + ";Centro Costo;Proyecto;Maquinaria"
CONTADOR, SUPERVISOR, GERENTE = "ana.contadora", "sofia.supervisora", "gerardo.gerente"


def asiento(sub, asi, fecha, lineas):
    out = []
    for cuenta, ter, kw in lineas:
        kw = dict(kw)
        cc, proyecto, maq = kw.pop("cc", "") or "", kw.pop("proyecto", "") or "", kw.pop("maq", "") or ""
        out.append(fila4(sub, asi, fecha, cuenta, ter, **kw) + [cc, proyecto, maq])
    return out


def csv(filas):
    return (CAB6 + "\n" + "\n".join(";".join(str(x) for x in f) for f in filas) + "\n").encode()


def q(e, **k):
    return {"empresa_id": e, **k}


@pytest.fixture()
def base(cliente, monkeypatch):
    """Empresa con cuenta bancaria BCP (104101), apertura 2026 y roles separados (elabora, revisa, aprueba)."""
    monkeypatch.setenv("CONTABLE_TRABAJOS_SINCRONOS", "1")
    e = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Conciliaciones del Sur SAC"}).json()["id"]
    bancos = {b["codigo"]: b["id"] for b in cliente.get("/api/bancos").json()}
    cb = cliente.post("/api/cuentas", json={"empresa_id": e, "banco_id": bancos["BCP"], "moneda": "PEN", "numero_cuenta": "191-1234567-0-01",
                                            "cuenta_contable": "104101"}).json()
    ap = "Cuenta;RUC;Debe;Haber\n104101;;10000;\n5011;;;10000\n".encode()
    importar_bytes(cliente, e, "apertura_2026.csv", ap, "SALDOS_INICIALES", periodo=0, ejercicio=2026)
    return {"e": e, "cb": cb["id"]}


def diario(cliente, e, filas, nombre="diario.csv"):
    importar_bytes(cliente, e, nombre, csv(filas), "DIARIO", periodo=None, ejercicio=2026)


def estado_banco(cliente, cb, movs, saldo_inicial=D("10000"), nombre="estado_bcp.csv"):
    """movs: (fecha, descripción, importe, operación). Formato real del BCP (fase 1)."""
    saldo = saldo_inicial
    filas = ["Fecha;Fecha valuta;Descripción operación;Monto;Saldo;Sucursal - agencia;Operación - Número"]
    for f, desc, imp, op in movs:
        saldo += D(imp)
        filas.append(f"{f};{f};{desc};{D(imp):.2f};{saldo:.2f};191 - LIMA CENTRO;{op}")
    r = cliente.post("/api/importaciones", files={"archivo": (nombre, ("\n".join(filas) + "\n").encode())},
                     data={"cuenta_id": str(cb), "tipo": "BANCO"})
    assert r.status_code == 201, r.text
    return r.json()


def cobro(asi, fecha, op, importe, glosa="COBRANZA CLIENTE"):
    return asiento("01", asi, fecha, [("104101", "", {"num": op, "debe": importe, "glosa": glosa}),
                                      ("1212", "20555555551", {"td": "01", "serie": "F001", "num": asi, "haber": importe, "glosa": glosa,
                                                               "rs": "CLIENTE UNO"})])


def pago_b(asi, fecha, op, importe, glosa="TRANSFERENCIA A PROVEEDOR", td=""):
    return asiento("02", asi, fecha, [("4212", PROV["P1"], {"td": "01", "serie": "F100", "num": asi, "debe": importe, "glosa": glosa}),
                                      ("104101", "", {"td": td, "num": op, "haber": importe, "glosa": glosa})])


def crear(cliente, e, tipo, ambito=None, corte="2026-01-31", usuario=CONTADOR, **extra):
    r = cliente.post("/api/conciliaciones", params=q(e), json={"tipo": tipo, "fecha_corte": corte, "ambito": ambito or {}, **extra},
                     headers={"X-Usuario": usuario})
    assert r.status_code == 201, r.text
    return r.json()


def subir(cliente, e, run_id, lado, nombre, contenido, usuario=CONTADOR, **data):
    r = cliente.post(f"/api/conciliaciones/{run_id}/fuentes/{lado}/archivo", params=q(e), files={"archivo": (nombre, contenido)},
                     data={k: str(v) for k, v in data.items()}, headers={"X-Usuario": usuario})
    assert r.status_code == 200, r.text
    return r.json()


def ejecutar(cliente, e, run_id, usuario=CONTADOR, forzar=False):
    r = cliente.post(f"/api/conciliaciones/{run_id}/ejecutar", params=q(e), json={"forzar": forzar}, headers={"X-Usuario": usuario})
    assert r.status_code == 202, r.text
    assert r.json()["trabajo"]["estado"] == "COMPLETADO", r.json()["trabajo"]
    c = ver(cliente, e, run_id, usuario)
    assert c["estado_proceso"] == "COMPLETADO", c
    return c


def ver(cliente, e, run_id, usuario=CONTADOR):
    r = cliente.get(f"/api/conciliaciones/{run_id}", params=q(e), headers={"X-Usuario": usuario})
    assert r.status_code == 200, r.text
    return r.json()


def conciliar(cliente, e, tipo, ambito=None, archivos=(), **extra):
    c = crear(cliente, e, tipo, ambito, **extra)
    for lado, nombre, contenido in archivos:
        subir(cliente, e, c["id"], lado, nombre, contenido)
    return ejecutar(cliente, e, c["id"])


def difs(cliente, e, run_id, usuario=CONTADOR, **f):
    r = cliente.get("/api/conciliaciones/diferencias", params=q(e, run_id=run_id, por_pagina=500, **f), headers={"X-Usuario": usuario})
    assert r.status_code == 200, r.text
    return r.json()["items"]


def una(lst, **cond):
    m = [d for d in lst if all(d.get(k) == v for k, v in cond.items())]
    assert len(m) == 1, (cond, [(d["clasificacion"], d["subtipo"], d["importe"], d["documento"]) for d in lst])
    return m[0]


def registros(cliente, e, run_id, lado, usuario=CONTADOR, **f):
    r = cliente.get(f"/api/conciliaciones/{run_id}/registros", params=q(e, lado=lado, por_pagina=500, **f), headers={"X-Usuario": usuario})
    assert r.status_code == 200, r.text
    return r.json()


def grupos(cliente, e, run_id, **f):
    r = cliente.get(f"/api/conciliaciones/{run_id}/grupos", params=q(e, por_pagina=500, **f))
    assert r.status_code == 200, r.text
    return r.json()["items"]


def lineas_libro(cliente, e):
    """Huella de los asientos originales para verificar que la conciliación no los modifica."""
    r = cliente.get("/api/analisis/balance", params=q(e, ejercicio=2026, desde=1, hasta=12)).json()
    return sorted((n["cuenta"], n["saldo_final"]) for n in r["nodos"])


# ===================================================================== bancaria (1–4)
MOVS_OK = [("05/01/2026", "DEPOSITO CLIENTE UNO", "1500", "0451201"), ("12/01/2026", "TRANSF A PROVEEDOR P1", "-800", "0451388")]
LIBRO_OK = cobro("C1", "05/01/2026", "0451201", "1500") + pago_b("P1", "12/01/2026", "0451388", "800")


def test_01_bancaria_sin_diferencias(cliente, base):
    e = base["e"]
    diario(cliente, e, LIBRO_OK)
    estado_banco(cliente, base["cb"], MOVS_OK)
    antes = lineas_libro(cliente, e)
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    rep = c["version"]["reporte"]
    assert D(rep["saldo_banco"]) == D(rep["saldo_libros"]) == D("10700")
    assert D(rep["diferencia_final"]) == 0
    assert difs(cliente, e, c["id"]) == []
    res = c["resumen"]
    assert res["asignaciones"] == {"CONCILIADO": 4} and res["porcentaje_cantidad"]["CONCILIADO"] == 100.0
    assert all(g["estado"] == "CONFIRMADA" and g["tipo"] == "EXACTA" for g in grupos(cliente, e, c["id"]))
    assert lineas_libro(cliente, e) == antes  # analítica: no modifica asientos


def test_02_comision_no_registrada(cliente, base):
    e = base["e"]
    diario(cliente, e, LIBRO_OK)
    estado_banco(cliente, base["cb"], MOVS_OK + [("31/01/2026", "COMISION MANTENIMIENTO CUENTA", "-15", ""),
                                                 ("31/01/2026", "ITF", "-0.05", "")])
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    ds = difs(cliente, e, c["id"])
    com = una(ds, subtipo="COMISION_BANCARIA")
    assert com["clasificacion"] == "REGISTRO_FALTANTE_CONTABILIDAD" and D(com["importe"]) == D("-15")
    assert D(una(ds, subtipo="ITF")["importe"]) == D("-0.05")
    rep = c["version"]["reporte"]
    assert D(rep["saldo_banco"]) == D("10684.95") and D(rep["saldo_libros"]) == D("10700")
    assert D(rep["saldo_libros_ajustado"]) == D(rep["saldo_banco_ajustado"]) == D("10684.95")
    assert D(rep["diferencia_final"]) == 0


def test_03_deposito_en_transito(cliente, base):
    e = base["e"]
    diario(cliente, e, LIBRO_OK + cobro("C2", "31/01/2026", "0459999", "2000", "DEPOSITO CHEQUE CLIENTE"))
    estado_banco(cliente, base["cb"], MOVS_OK)
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    d = una(difs(cliente, e, c["id"]), subtipo="DEPOSITO_EN_TRANSITO")
    assert d["clasificacion"] == "DIFERENCIA_TEMPORAL" and D(d["importe"]) == D("2000") and d["prioridad"] == "BAJO"
    rep = c["version"]["reporte"]
    assert D(rep["partidas_banco"][0]["importe"]) == D("2000")
    assert D(rep["saldo_banco_ajustado"]) == D(rep["saldo_libros"]) == D("12700") and D(rep["diferencia_final"]) == 0


def test_04_transferencia_duplicada(cliente, base):
    e = base["e"]
    diario(cliente, e, LIBRO_OK + pago_b("P2", "12/01/2026", "0451388", "800"))
    estado_banco(cliente, base["cb"], MOVS_OK)
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    d = una(difs(cliente, e, c["id"]), subtipo="DUPLICADO_CONTABLE")
    assert d["clasificacion"] == "DOCUMENTO_DUPLICADO" and D(d["importe"]) == D("-800")
    assert c["resumen"]["duplicados"] == 1
    rep = c["version"]["reporte"]
    assert D(rep["saldo_libros"]) == D("9900") and D(rep["diferencia_final"]) == 0


# ===================================================================== compras (5–7)
CAB_COMPRAS = "Fecha Emision;Tipo Doc;Serie;Numero;RUC;Razon Social;Base Imponible;IGV;No Gravado;Total;Moneda;Doc Referencia"


def reg_compras(filas):
    return (CAB_COMPRAS + "\n" + "\n".join(";".join(str(x) for x in f) for f in filas) + "\n").encode()


def provision(asi, fecha, ter, serie, num, base, igv, td="01", gasto="6011", cc=""):
    total = D(base) + D(igv)
    if td == "07":  # nota de crédito: invierte la provisión
        return asiento("11", asi, fecha, [("4212", ter, {"td": td, "serie": serie, "num": num, "debe": str(total), "glosa": f"NC {serie}-{num}"}),
                                          (gasto, ter, {"haber": base, "glosa": "NC COMPRA", "cc": cc}),
                                          ("40111", ter, {"haber": igv, "glosa": "IGV NC"})])
    return asiento("11", asi, fecha, [(gasto, ter, {"debe": base, "glosa": f"COMPRA {serie}-{num}", "cc": cc}),
                                      ("40111", ter, {"debe": igv, "glosa": "IGV COMPRA"}),
                                      ("4212", ter, {"td": td, "serie": serie, "num": num, "haber": str(total), "glosa": f"FACTURA {serie}-{num}"})])


def test_05_06_07_compras(cliente, base):
    e = base["e"]
    diario(cliente, e, provision("K1", "03/01/2026", PROV["P1"], "F100", "1", "1000", "180")
           + provision("K3", "10/01/2026", PROV["P3"], "F300", "3", "2010", "350")
           + provision("K4", "20/01/2026", PROV["P4"], "FC01", "5", "500", "90", td="07"))
    reg = reg_compras([["03/01/2026", "01", "F100", "1", PROV["P1"], "PROVEEDOR UNO", "1000", "180", "0", "1180", "PEN", ""],
                       ["08/01/2026", "01", "F200", "7", PROV["P2"], "PROVEEDOR DOS", "500", "90", "0", "590", "PEN", ""],
                       ["10/01/2026", "01", "F300", "3", PROV["P3"], "PROVEEDOR TRES", "2000", "360", "0", "2360", "PEN", ""],
                       ["20/01/2026", "07", "FC01", "5", PROV["P4"], "PROVEEDOR CUATRO", "-500", "-90", "0", "-590", "PEN", "F999-9"]])
    importar_bytes(cliente, e, "compras_2026-01.csv", reg, "COMPRAS", periodo=1, ejercicio=2026)
    c = conciliar(cliente, e, "COMPRAS")
    ds = difs(cliente, e, c["id"])
    # 5 · compra registrada y no contabilizada
    d5 = una(ds, subtipo="COMPRA_NO_CONTABILIZADA")
    assert d5["clasificacion"] == "REGISTRO_FALTANTE_CONTABILIDAD" and D(d5["importe"]) == D("590") and d5["documento"] == "01 F200-7"
    # 6 · diferencia de IGV (y la base que la compensa): el total cuadra pero la composición no
    d6 = una(ds, subtipo="DIFERENCIA_IGV")
    assert D(d6["importe"]) == D("-10") and d6["clasificacion"] == "DIFERENCIA_MONETARIA" and not d6["dentro_tolerancia"]
    assert D(una(ds, subtipo="DIFERENCIA_BASE")["importe"]) == D("10")
    # 7 · nota de crédito sin comprobante relacionado
    d7 = una(ds, subtipo="NC_NO_RELACIONADA")
    assert d7["clasificacion"] == "DOCUMENTO_PENDIENTE_SUSTENTO" and "F999-9" in d7["explicacion"]
    # la factura correcta se concilia exactamente
    regs = registros(cliente, e, c["id"], "A", buscar="F100")["items"]
    assert regs[0]["asignacion"]["estado"] == "CONCILIADO"


# ===================================================================== planillas (8, 9, 28)
PLANILLA = ("Periodo;Tipo Planilla;DNI;Apellidos y Nombres;Concepto;Tipo Concepto;Importe;Centro Costo\n"
            f"2026-01;MENSUAL;{W1};TRABAJADOR UNO;REMUNERACION;INGRESO;3000;ADM\n"
            f"2026-01;MENSUAL;{W2};TRABAJADOR DOS;REMUNERACION;INGRESO;2500;ADM\n"
            f"2026-01;MENSUAL;{W1};TRABAJADOR UNO;AFP;DESCUENTO;300;ADM\n"
            f"2026-01;MENSUAL;{W2};TRABAJADOR DOS;AFP;DESCUENTO;250;ADM\n"
            f"2026-01;MENSUAL;{W1};TRABAJADOR UNO;ESSALUD;APORTE;270;ADM\n"
            f"2026-01;MENSUAL;{W2};TRABAJADOR DOS;ESSALUD;APORTE;225;ADM\n"
            f"2026-01;MENSUAL;{W1};TRABAJADOR UNO;NETO A PAGAR;NETO;2700;ADM\n"
            f"2026-01;MENSUAL;{W2};TRABAJADOR DOS;NETO A PAGAR;NETO;2250;ADM\n").encode()
# la remuneración neta de W2 no se contabilizó (8) y el aporte AFP se registró por 500 en lugar de 550 (9)
LIBRO_PLANILLA = asiento("35", "PL1", "31/01/2026", [
    ("6211", "", {"debe": "5500", "glosa": "REMUNERACIONES ENERO", "cc": "ADM"}),
    ("6271", "", {"debe": "495", "glosa": "ESSALUD ENERO", "cc": "ADM"}),
    ("4111", W1, {"haber": "2700", "glosa": "NETO PLANILLA ENERO", "rs": "TRABAJADOR UNO"}),
    ("407", "", {"haber": "500", "glosa": "AFP ENERO"}),
    ("4031", SUNAT, {"haber": "495", "glosa": "ESSALUD ENERO", "rs": "SUNAT"}),
    ("4191", "", {"haber": "2300", "glosa": "OTRAS REMUNERACIONES POR PAGAR"})])


def roles(cliente, e, asignaciones, admin="admin.general"):
    for u, rol in asignaciones:
        r = cliente.post("/api/compensacion/roles", params=q(e), json={"usuario": u, "rol": rol}, headers={"X-Usuario": admin})
        assert r.status_code == 201, r.text


def test_08_09_28_planillas_y_proteccion_de_datos(cliente, base):
    e = base["e"]
    diario(cliente, e, LIBRO_PLANILLA)
    roles(cliente, e, [("pedro.planillas", "PLANILLAS"), ("tito.tesorero", "TESORERO"), ("carlos.consulta", "CONSULTA"), (CONTADOR, "CONTADOR")])
    c = crear(cliente, e, "PLANILLAS", usuario="pedro.planillas")
    vista = subir(cliente, e, c["id"], "A", "planilla_2026-01.csv", PLANILLA, usuario="pedro.planillas")
    assert vista["registros"] >= 8
    c = ejecutar(cliente, e, c["id"], usuario="pedro.planillas")
    ds = difs(cliente, e, c["id"], usuario="pedro.planillas")
    # 8 · planilla vs 41: la remuneración neta de W2 no está contabilizada
    d8 = una(ds, subtipo="REMUNERACION_NO_CONTABILIZADA")
    assert D(d8["importe"]) == D("2250") and d8["tercero"] == W2 and d8["personal"]
    # 9 · aportes: AFP según planilla 550, contabilidad 500
    d9 = una(ds, subtipo="DIFERENCIA_APORTES")
    assert D(d9["importe"]) == D("-50") and d9["clasificacion"] == "DIFERENCIA_MONETARIA"
    # el costo por centro de costo (62) y EsSalud (4031) cuadran
    assert not [d for d in ds if d["subtipo"] == "DIFERENCIA_DISTRIBUCION"]
    # 28 · protección de datos: el tesorero no accede, el usuario de consulta ve datos enmascarados
    assert cliente.get(f"/api/conciliaciones/{c['id']}", params=q(e), headers={"X-Usuario": "tito.tesorero"}).status_code == 403
    assert cliente.get(f"/api/conciliaciones/{c['id']}/exportar", params=q(e), headers={"X-Usuario": "tito.tesorero"}).status_code == 403
    assert all(x["tipo_codigo"] != "PLANILLAS" for x in cliente.get("/api/conciliaciones", params=q(e), headers={"X-Usuario": "tito.tesorero"}).json()["items"])
    ver_c = difs(cliente, e, c["id"], usuario="carlos.consulta")
    m = next(d for d in ver_c if d["id"] == d8["id"])
    assert m["tercero"] != W2 and m["tercero"].endswith(W2[-2:]) and "reservado" in m["explicacion"]
    regs = registros(cliente, e, c["id"], "A", usuario="carlos.consulta")["items"]
    assert regs and all(r["tercero"] in (None, "TOTAL") or "•" in r["tercero"] for r in regs)
    assert all(r["razon_social"] is None or "TRABAJADOR UNO" not in r["razon_social"] for r in regs)
    assert ver(cliente, e, c["id"], "carlos.consulta")["version"]["reporte"].get("nota", "").startswith("Detalle reservado")
    # el contador opera la conciliación pero tampoco ve los datos personales
    assert "•" in registros(cliente, e, c["id"], "A", usuario=CONTADOR)["items"][0]["tercero"]
    # la exportación para un usuario no autorizado también va enmascarada
    import openpyxl
    x = cliente.get(f"/api/conciliaciones/{c['id']}/exportar", params=q(e), headers={"X-Usuario": "carlos.consulta"})
    assert x.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    texto = " ".join(str(v) for ws in wb.worksheets for row in ws.iter_rows(values_only=True) for v in row if v)
    assert W2 not in texto and "TRABAJADOR DOS" not in texto
    x = cliente.get(f"/api/conciliaciones/{c['id']}/exportar", params=q(e), headers={"X-Usuario": "pedro.planillas"})
    texto = " ".join(str(v) for ws in openpyxl.load_workbook(io.BytesIO(x.content)).worksheets for row in ws.iter_rows(values_only=True) for v in row if v)
    assert W2 in texto


# ===================================================================== activos fijos (10, 11) e inventarios (12)
ACTIVOS = ("codigo;cuenta;descripcion;categoria;fecha_adquisicion;fecha_uso;costo_inicial;adiciones;vida_util_meses;valor_residual;"
           "cuenta_depreciacion;depreciacion_acumulada_inicial;ubicacion\n"
           "AF-1;3341;CAMION VOLVO;VEHICULOS;02/01/2026;01/01/2026;12000;;120;0;3913;0;LIMA\n").encode()


def test_10_11_activos_fijos(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("21", "AF1", "02/01/2026", [("3341", "", {"debe": "12000", "glosa": "COMPRA CAMION", "maq": "AF-1"}),
                                                             ("4651", PROV["P5"], {"haber": "12000", "glosa": "COMPRA CAMION", "td": "01", "serie": "F500",
                                                                                   "num": "1"})])
           # 10 · activo comprado y contabilizado que no se registró en el auxiliar
           + asiento("21", "AF9", "15/01/2026", [("3341", "", {"debe": "5000", "glosa": "COMPRA GRUPO ELECTROGENO", "maq": "AF-9"}),
                                                  ("4651", PROV["P5"], {"haber": "5000", "glosa": "COMPRA", "td": "01", "serie": "F500", "num": "2"})])
           # 11 · depreciación contabilizada 120; según el auxiliar corresponde 100 (12 000 / 120 meses)
           + asiento("31", "DP1", "31/01/2026", [("6814", "", {"debe": "120", "glosa": "DEPRECIACION ENERO", "maq": "AF-1"}),
                                                  ("3913", "", {"haber": "120", "glosa": "DEPRECIACION ENERO", "maq": "AF-1"})]))
    r = cliente.post("/api/anexos/registros/importar", params=q(e), data={"tipo": "ACTIVO_FIJO"}, files={"archivo": ("activos.csv", ACTIVOS)})
    assert r.status_code == 201 and not r.json()["errores"], r.text
    c = conciliar(cliente, e, "ACTIVOS_FIJOS")
    ds = difs(cliente, e, c["id"])
    d10 = una(ds, subtipo="ACTIVO_SOLO_EN_CONTABILIDAD")
    assert D(d10["importe"]) == D("5000") and "AF-9" in d10["explicacion"]
    dep = [d for d in ds if d["subtipo"] == "DIFERENCIA_DEPRECIACION"]
    assert {(d["evidencia"]["valores"]["nombre"], D(d["importe"])) for d in dep} == {("Depreciación acumulada", D("20")),
                                                                                     ("Depreciación del periodo", D("20"))}
    assert not [d for d in ds if d["subtipo"] == "DIFERENCIA_COSTO"]  # el costo de AF-1 cuadra
    # un activo totalmente depreciado no se da de baja automáticamente (no hay ninguno aquí)
    assert not [d for d in ds if d["subtipo"] == "BAJA_NO_REGISTRADA"]


KARDEX = ("Codigo Producto;Descripcion;Almacen;Unidad;Cuenta;Cantidad Inicial;Cantidad Entradas;Cantidad Salidas;Cantidad Final;"
          "Costo Unitario;Valor Inicial;Valor Entradas;Valor Salidas;Valor Final\n"
          "P-1;CEMENTO;ALM1;BOL;2011;0;100;0;100;10;0;1000;0;1000\n"
          "P-2;FIERRO;ALM1;UND;2011;0;50;0;40;12.5;0;500;0;500\n").encode()


def test_12_kardex_vs_contabilidad(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("11", "IN1", "10/01/2026", [("2011", "", {"debe": "1400", "glosa": "COMPRA MERCADERIA"}),
                                                            ("4212", PROV["P1"], {"haber": "1400", "glosa": "COMPRA", "td": "01", "serie": "F100",
                                                                                  "num": "9"})]))
    c = conciliar(cliente, e, "INVENTARIOS", archivos=[("A", "kardex.csv", KARDEX)])
    ds = difs(cliente, e, c["id"])
    v = una(ds, subtipo="DIFERENCIA_VALORIZACION")
    assert D(v["importe"]) == D("-100") and v["cuenta"] == "2011"
    assert D(una(ds, subtipo="MOVIMIENTO_NO_CONTABILIZADO")["importe"]) == D("-100")
    # cantidades y valores se comparan por separado: el fierro tiene una inconsistencia física (0 + 50 − 0 ≠ 40)
    q2 = una(ds, subtipo="INCONSISTENCIA_CANTIDADES")
    assert "P-2" in q2["explicacion"] and D(q2["importe"]) == 0
    assert c["version"]["reporte"]["metodo_valorizacion"] == "PROMEDIO"


# ===================================================================== financieras (13), detracciones (14), retenciones (15)
CONTRATOS = ("contrato;cuenta;entidad;ruc_entidad;tipo;moneda;capital;tasa;fecha_desembolso\n"
             "PR-77;4511;BANCO DE CREDITO;20100047218;PRESTAMO;PEN;60000;12;02/01/2026\n").encode()
CUOTAS = ("contrato;numero;fecha_vencimiento;capital;interes;comision;pagada\n"
          "PR-77;1;31/01/2026;2500;600;;S\nPR-77;2;28/02/2026;2500;575;;N\n").encode()


def aux(cliente, e, tipo, nombre, contenido):
    r = cliente.post("/api/anexos/registros/importar", params=q(e), data={"tipo": tipo}, files={"archivo": (nombre, contenido)})
    assert r.status_code == 201 and not r.json()["errores"], r.text


def test_13_diferencia_de_capital_en_prestamo(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("21", "PR1", "02/01/2026", [("104101", "20100047218", {"debe": "60000", "glosa": "DESEMBOLSO PRESTAMO PR-77"}),
                                                            ("4511", "20100047218", {"haber": "60000", "glosa": "DESEMBOLSO PRESTAMO PR-77",
                                                                                     "ref": "PR-77"})])
           # la cuota 1 se pagó por 3 100 (2 500 de capital + 600 de interés) pero se amortizó solo 2 000 de capital
           + asiento("21", "PR2", "31/01/2026", [("4511", "20100047218", {"debe": "2000", "glosa": "CUOTA 1 PRESTAMO PR-77", "ref": "PR-77"}),
                                                  ("6731", "20100047218", {"debe": "1100", "glosa": "INTERESES CUOTA 1 PR-77"}),
                                                  ("104101", "20100047218", {"haber": "3100", "glosa": "PAGO CUOTA 1"})]))
    aux(cliente, e, "CONTRATO_FINANCIERO", "contratos.csv", CONTRATOS)
    aux(cliente, e, "CUOTA_FINANCIERA", "cuotas.csv", CUOTAS)
    c = conciliar(cliente, e, "FINANCIERAS")
    ds = difs(cliente, e, c["id"])
    cap = una(ds, subtipo="DIFERENCIA_CAPITAL")
    assert D(cap["importe"]) == D("500") and cap["documento"] == "PR-77" and cap["prioridad"] == "ALTO"
    assert D(una(ds, subtipo="CUOTA_NO_REGISTRADA")["importe"]) == D("2500")
    rep = next(x for x in c["version"]["reporte"]["contratos"] if x["contrato"] == "PR-77")
    assert D(rep["capital_pendiente_cronograma"]) == D("57500") and D(rep["saldo_libros"]) == D("58000")
    # la cuota 2 aún no vence: no se considera
    assert not [d for d in ds if "cuota 2" in (d["explicacion"] or "").lower() or "Cuota 2" in (d["explicacion"] or "")]


def regla_tributaria(cliente, e, tipo, codigo, tasa, aprobar=True):
    r = cliente.post("/api/compensacion/reglas", params=q(e), json={"tipo": tipo, "codigo": codigo, "nombre": f"{tipo} {codigo}",
                                                                    "parametros": {"tasa": tasa}, "sustento": "Norma sintética de prueba",
                                                                    "vigente_desde": "2025-01-01"}, headers={"X-Usuario": CONTADOR})
    assert r.status_code == 201, r.text
    if aprobar:
        # quien configura no aprueba (separación de funciones)
        assert cliente.post(f"/api/conciliaciones/tasas/{r.json()['id']}/aprobar", params=q(e), headers={"X-Usuario": CONTADOR}).status_code == 403
        a = cliente.post(f"/api/conciliaciones/tasas/{r.json()['id']}/aprobar", params=q(e), headers={"X-Usuario": SUPERVISOR})
        assert a.status_code == 200 and a.json()["autorizado_por"] == SUPERVISOR, a.text
    return r.json()


CAB_DET = "Fecha Emision;Tipo Doc;Serie;Numero;RUC;Razon Social;Base Imponible;IGV;No Gravado;Total;Moneda;Codigo Detraccion"
CONSTANCIAS = ("Constancia;Fecha Deposito;Tipo Doc;Serie;Numero;RUC;Razon Social;Codigo Detraccion;Importe;Periodo\n"
               f"C-0002;12/01/2026;01;F600;2;{PROV['P5']};PROVEEDOR CINCO;037;708;2026-01\n").encode()


def test_14_detraccion_sin_constancia(cliente, base):
    e = base["e"]
    regla_tributaria(cliente, e, "DETRACCION", "037", "12")
    reg = (CAB_DET + "\n" + f"05/01/2026;01;F600;1;{PROV['P5']};PROVEEDOR CINCO;10000;1800;0;11800;PEN;037\n"
           f"06/01/2026;01;F600;2;{PROV['P5']};PROVEEDOR CINCO;5000;900;0;5900;PEN;037\n").encode()
    importar_bytes(cliente, e, "compras_det.csv", reg, "COMPRAS", periodo=1, ejercicio=2026)
    diario(cliente, e, asiento("21", "DT2", "12/01/2026", [("4212", PROV["P5"], {"td": "01", "serie": "F600", "num": "2", "debe": "708",
                                                                                 "glosa": "DETRACCION F600-2", "const": "C-0002", "cod": "037"}),
                                                            ("104201", "", {"haber": "708", "glosa": "CTA DETRACCIONES BN"})]))
    c = conciliar(cliente, e, "DETRACCIONES", archivos=[("B", "constancias.csv", CONSTANCIAS)])
    ds = difs(cliente, e, c["id"])
    d = una(ds, subtipo="FACTURA_SIN_DEPOSITO")
    assert D(d["importe"]) == D("1416") and d["documento"] == "01 F600-1"  # 11 800 × 12 %
    assert "No constituye" in d["explicacion"]  # no se declara incumplimiento definitivo
    # el comprobante con constancia, y la constancia contabilizada, se concilian
    assert not [x for x in ds if x["subtipo"] in ("CONSTANCIA_NO_CONTABILIZADA", "REGISTRO_SIN_CONSTANCIA", "DEPOSITO_SIN_DOCUMENTO")]
    regs = registros(cliente, e, c["id"], "A")["items"]
    f2 = next(r for r in regs if r["numero"] == "2")
    assert f2["asignacion"]["estado"] == "CONCILIADO" and D(f2["importe"]) == D("708") and f2["datos"]["tasa"] == "12"
    assert f2["datos"]["aprobado_por"] == SUPERVISOR and f2["datos"]["fuente_normativa"] == "Norma sintética de prueba"


RETENCIONES = ("Tipo Retencion;Fecha;Tipo Doc;Serie;Numero;RUC;Razon Social;Documento Original;Importe del comprobante;Importe;Periodo\n"
               f"RETENCION IGV;20/01/2026;20;R001;5;{PROV['P1']};PROVEEDOR UNO;F100-1;1000;30;2026-01\n").encode()


def test_15_retencion_pendiente_de_sustento(cliente, base):
    e = base["e"]
    regla_tributaria(cliente, e, "RETENCION", "IGV", "3")
    diario(cliente, e, asiento("21", "RT1", "20/01/2026", [("4212", PROV["P1"], {"td": "01", "serie": "F100", "num": "1", "debe": "1000", "glosa": "PAGO F100-1"}),
                                                            ("40114", PROV["P1"], {"td": "20", "serie": "R001", "num": "5", "haber": "30",
                                                                                   "glosa": "RETENCION IGV R001-5"}),
                                                            ("104101", "", {"haber": "970", "glosa": "PAGO NETO"})])
           + asiento("21", "RT2", "25/01/2026", [("4212", PROV["P2"], {"td": "01", "serie": "F200", "num": "8", "debe": "1500", "glosa": "PAGO F200-8"}),
                                                  ("40114", PROV["P2"], {"td": "20", "serie": "R001", "num": "6", "haber": "45",
                                                                         "glosa": "RETENCION IGV R001-6"}),
                                                  ("104101", "", {"haber": "1455", "glosa": "PAGO NETO"})]))
    c = conciliar(cliente, e, "RETENCIONES", archivos=[("A", "retenciones.csv", RETENCIONES)])
    ds = difs(cliente, e, c["id"])
    d = una(ds, subtipo="RETENCION_SIN_COMPROBANTE")
    assert d["clasificacion"] == "DOCUMENTO_PENDIENTE_SUSTENTO" and D(d["importe"]) == D("45") and d["documento"] == "20 R001-6"
    # la tasa vigente y aprobada (3 %) verifica el comprobante R001-5: sin diferencia de tasa
    assert not [x for x in ds if x["subtipo"] in ("DIFERENCIA_TASA", "TASA_NO_CONFIGURADA")]


# ===================================================================== intercompañía (16) y seguridad multiempresa (27)
def test_16_27_intercompania_y_aislamiento(cliente, base):
    e = base["e"]
    b = cliente.post("/api/empresas", json={"ruc": "20100047218", "razon_social": "Relacionada Norte SAC"}).json()["id"]
    diario(cliente, e, asiento("05", "V10", "10/01/2026", [("1321", "20100047218", {"td": "01", "serie": "F001", "num": "10", "debe": "5000",
                                                                                    "glosa": "SERVICIO A RELACIONADA", "rs": "RELACIONADA NORTE"}),
                                                            ("7041", "", {"haber": "5000", "glosa": "SERVICIO"})])
           + asiento("05", "V11", "20/01/2026", [("1321", "20100047218", {"td": "01", "serie": "F001", "num": "11", "debe": "2000",
                                                                          "glosa": "SERVICIO A RELACIONADA", "rs": "RELACIONADA NORTE"}),
                                                  ("7041", "", {"haber": "2000", "glosa": "SERVICIO"})]))
    importar_bytes(cliente, b, "diario_b.csv", csv(asiento("11", "C10", "12/01/2026", [
        ("6321", "", {"debe": "5000", "glosa": "SERVICIO DE RELACIONADA"}),
        ("4321", "20609876540", {"td": "01", "serie": "F001", "num": "10", "haber": "5000", "glosa": "FACTURA RELACIONADA", "rs": "CONCILIACIONES DEL SUR"})])),
        "DIARIO", periodo=None, ejercicio=2026)
    # sin autorización recíproca de grupo económico no se concilia
    r = cliente.post("/api/conciliaciones", params=q(e), json={"tipo": "INTERCOMPANIA", "fecha_corte": "2026-01-31",
                                                               "ambito": {"empresa_relacionada_id": b}})
    assert r.status_code == 403 and "grupo económico" in r.json()["detail"]
    for x, y in ((e, b), (b, e)):
        assert cliente.post("/api/conciliaciones/asignaciones", params=q(x),
                            json={"tipo": "GRUPO_ECONOMICO", "empresa_relacionada_id": y}).status_code == 201
    c = conciliar(cliente, e, "INTERCOMPANIA", {"empresa_relacionada_id": b})
    ds = difs(cliente, e, c["id"])
    d = una(ds, subtipo="OPERACION_NO_RECIPROCA")
    assert d["documento"] == "01 F001-11" and D(d["importe"]) == D("2000") and "RELACIONADA NORTE" in d["explicacion"]
    assert "eliminaciones" in c["version"]["reporte"]["nota"]
    # 27 · aislamiento: la conciliación no se ve desde otra empresa ni por un usuario sin rol en ella
    assert cliente.get(f"/api/conciliaciones/{c['id']}", params=q(b)).status_code == 404
    assert cliente.get("/api/conciliaciones/diferencias", params=q(b, run_id=c["id"])).json()["items"] == []
    roles(cliente, e, [(CONTADOR, "CONTADOR")])
    roles(cliente, b, [("solo.b", "CONTADOR")], admin="admin.b")
    assert cliente.get(f"/api/conciliaciones/{c['id']}", params=q(e), headers={"X-Usuario": "solo.b"}).status_code == 403
    assert cliente.get("/api/conciliaciones", params=q(e), headers={"X-Usuario": "solo.b"}).status_code == 403
    # un usuario sin acceso a la relacionada no puede crear la conciliación recíproca
    r = cliente.post("/api/conciliaciones", params=q(e), json={"tipo": "INTERCOMPANIA", "fecha_corte": "2026-02-28",
                                                               "ambito": {"empresa_relacionada_id": b}}, headers={"X-Usuario": CONTADOR})
    assert r.status_code == 403 and "empresa relacionada" in r.json()["detail"]


# ===================================================================== origen-destino (17, 18)
def gasto(asi, fecha, cuenta, importe, destinos=(), cc="ADM"):
    lineas = [(cuenta, "", {"debe": importe, "glosa": f"GASTO {asi}", "cc": cc})]
    total9 = D(0)
    for c9, imp in destinos:
        lineas.append((c9, "", {"debe": imp, "glosa": f"DESTINO {asi}", "cc": cc}))
        total9 += D(imp)
    if total9:
        lineas.append(("791", "", {"haber": str(total9), "glosa": "CARGAS IMPUTABLES"}))
    lineas.append(("4212", PROV["P1"], {"td": "01", "serie": "F700", "num": asi, "haber": importe, "glosa": f"FACTURA {asi}"}))
    return asiento("31", asi, fecha, lineas)


def test_17_18_origen_destino(cliente, base):
    e = base["e"]
    diario(cliente, e, gasto("G1", "10/01/2026", "6361", "800", [("9411", "800")])
           + gasto("G2", "15/01/2026", "6351", "1200")                                  # 17 · gasto destinable sin destino
           + gasto("G3", "20/01/2026", "6371", "500", [("9411", "500"), ("9411", "500")]))  # 18 · destino registrado dos veces
    antes = lineas_libro(cliente, e)
    c = conciliar(cliente, e, "ORIGEN_DESTINO")
    ds = difs(cliente, e, c["id"])
    d17 = una(ds, subtipo="GASTO_SIN_DESTINO")
    assert D(d17["importe"]) == D("1200") and "31-G2" in d17["explicacion"].replace(" ", "") or "G2" in d17["explicacion"]
    d18 = una(ds, subtipo="DISTRIBUCION_DUPLICADA")
    assert D(d18["importe"]) == D("500") and d18["prioridad"] == "ALTO" and "líneas de destino repetidas" in d18["explicacion"]
    # el asiento G1 cuadra (origen = destino = 79) y la 79 coincide con la clase 9 en todos los asientos
    assert not [d for d in ds if d["subtipo"] in ("CONTRAPARTIDA_79", "DESTINO_SIN_ORIGEN", "DISTRIBUCION_INCOMPLETA")]
    assert "no es un gasto adicional" in c["version"]["reporte"]["nota"]
    assert lineas_libro(cliente, e) == antes  # no se generan asientos de regularización


# ===================================================================== motor: parcial (19), ambigua (20), tolerancia (21)
def manual(cliente, e, run_id, a, b, justificacion="Conciliación manual sustentada con el voucher del banco", usuario=CONTADOR, **extra):
    return cliente.post(f"/api/conciliaciones/{run_id}/manual", params=q(e), headers={"X-Usuario": usuario},
                        json={"registros_a": a, "registros_b": b, "justificacion": justificacion, **extra})


def reg_por(cliente, e, run_id, lado, **cond):
    return next(r for r in registros(cliente, e, run_id, lado)["items"] if all(str(r.get(k)) == str(v) for k, v in cond.items()))


def test_19_coincidencia_parcial_y_combinada(cliente, base):
    e = base["e"]
    # un abono del banco por 3 000 corresponde a dos depósitos del libro (2 000 + 1 000): coincidencia N:1 propuesta
    diario(cliente, e, cobro("C1", "10/01/2026", "", "2000") + cobro("C2", "10/01/2026", "", "1000")
           + pago_b("P1", "15/01/2026", "777", "1000"))
    estado_banco(cliente, base["cb"], [("10/01/2026", "DEPOSITOS VARIOS", "3000", ""), ("16/01/2026", "TRANSF PARCIAL PROVEEDOR", "-600", "888")])
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    g = una(grupos(cliente, e, c["id"]), modalidad="N:1")
    assert g["estado"] == "PROPUESTA" and D(g["importe_a"]) == D("3000") and g["detalle"]["combinacion"]
    assert cliente.post(f"/api/conciliaciones/grupos/{g['id']}/confirmar", params=q(e), json={}).status_code == 200
    # aplicación parcial manual: del pago de 1 000 se concilian 600 con el cargo del banco
    libro = reg_por(cliente, e, c["id"], "A", numero="777")
    banco = reg_por(cliente, e, c["id"], "B", operacion="888")
    r = manual(cliente, e, c["id"], [{"id": libro["id"], "importe": "600"}], [{"id": banco["id"]}])
    assert r.status_code == 201, r.text
    assert r.json()["modalidad"] == "1:1" and D(r.json()["diferencia"]) == 0
    libro = reg_por(cliente, e, c["id"], "A", numero="777")
    assert libro["asignacion"]["estado"] == "PARCIAL" and D(libro["asignacion"]["pendiente"]) == D("400")
    d = una(difs(cliente, e, c["id"]), subtipo="TRANSFERENCIA_PENDIENTE")
    assert d["estado"] == "DETECTADO" and D(d["importe_pendiente"]) == D("-400") and D(d["importe"]) == D("-1000")
    # sin saldo disponible no se puede volver a conciliar el mismo registro por más de lo pendiente
    r = manual(cliente, e, c["id"], [{"id": libro["id"], "importe": "500"}], [{"id": banco["id"]}])
    assert r.status_code in (409, 422)
    # la decisión manual se re-aplica al volver a ejecutar
    c2 = ejecutar(cliente, e, c["id"], forzar=True)
    assert c2["version"]["numero"] == 2 and c2["resumen"]["manuales_reaplicadas"] == 1
    assert reg_por(cliente, e, c["id"], "A", numero="777")["asignacion"]["estado"] == "PARCIAL"


def test_20_coincidencia_ambigua_no_se_aprueba(cliente, base):
    e = base["e"]
    diario(cliente, e, cobro("C1", "09/01/2026", "", "500") + cobro("C2", "11/01/2026", "", "500"))
    estado_banco(cliente, base["cb"], [("10/01/2026", "DEPOSITO EFECTIVO", "500", "")])
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    g = una(grupos(cliente, e, c["id"]), estado="AMBIGUA")
    assert len(g["registros"]) == 3
    d = una(difs(cliente, e, c["id"]), clasificacion="COINCIDENCIA_AMBIGUA")
    assert "no se aprueba automáticamente" in d["explicacion"]
    assert c["pendientes"]["ambiguas"] == 1
    # una coincidencia ambigua no se confirma: se resuelve eligiendo la alternativa correcta
    assert cliente.post(f"/api/conciliaciones/grupos/{g['id']}/confirmar", params=q(e), json={}).status_code == 422
    assert cliente.post(f"/api/conciliaciones/{c['id']}/estado", params=q(e), json={"estado": "EN_REVISION"}).status_code == 200
    assert cliente.post(f"/api/conciliaciones/{c['id']}/estado", params=q(e), json={"estado": "REVISADA"},
                        headers={"X-Usuario": SUPERVISOR}).status_code == 200
    r = cliente.post(f"/api/conciliaciones/{c['id']}/estado", params=q(e), json={"estado": "APROBADA"}, headers={"X-Usuario": GERENTE})
    assert r.status_code == 422 and "ambiguas" in r.json()["detail"]
    r = cliente.post(f"/api/conciliaciones/{c['id']}/estado", params=q(e), json={"estado": "OBSERVADA", "comentario": "Resolver el depósito ambiguo"},
                     headers={"X-Usuario": SUPERVISOR})
    assert r.status_code == 200
    r = cliente.post(f"/api/conciliaciones/grupos/{g['id']}/rechazar", params=q(e), json={"motivo": "Se identificó el depósito con el voucher"})
    assert r.status_code == 200 and r.json()["estado"] == "RECHAZADA"
    libro = reg_por(cliente, e, c["id"], "A", fecha="2026-01-09")
    banco = registros(cliente, e, c["id"], "B")["items"][0]
    assert manual(cliente, e, c["id"], [{"id": libro["id"]}], [{"id": banco["id"]}]).status_code == 201
    assert una(difs(cliente, e, c["id"]), clasificacion="COINCIDENCIA_AMBIGUA")["estado"] == "SUBSANADO"
    c = ejecutar(cliente, e, c["id"])  # la observada se vuelve a ejecutar: re-aplica la decisión, el otro depósito queda en tránsito
    assert c["pendientes"]["ambiguas"] == 0
    assert D(una(difs(cliente, e, c["id"], abiertas=True), subtipo="DEPOSITO_EN_TRANSITO")["importe"]) == D("500")


def test_21_dentro_de_tolerancia_visible(cliente, base):
    e = base["e"]
    r = cliente.post("/api/conciliaciones/tolerancias", params=q(e), json={"tipo_codigo": "BANCARIA", "importe_absoluto": "1.00", "dias": 3},
                     headers={"X-Usuario": SUPERVISOR})
    assert r.status_code == 201, r.text
    diario(cliente, e, LIBRO_OK)
    estado_banco(cliente, base["cb"], [("05/01/2026", "DEPOSITO CLIENTE UNO", "1500.40", "0451201"), MOVS_OK[1]])
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    g = una(grupos(cliente, e, c["id"]), tipo="TOLERANCIA")
    assert g["estado"] == "CONFIRMADA" and D(g["diferencia"]) == D("0.40")
    d = una(difs(cliente, e, c["id"]), subtipo="DENTRO_TOLERANCIA")
    assert d["dentro_tolerancia"] and d["prioridad"] == "INFORMATIVO" and D(d["importe"]) == D("0.40")  # visible y cuantificada
    rep = c["version"]["reporte"]
    assert D(rep["diferencia_final"]) == 0 and D(rep["partidas_libros"][-1]["importe"]) == D("0.40")
    assert c["resumen"]["tolerancia"]["importe_absoluto"] == "1.00"


# ===================================================================== continuidad (22)
def test_22_traslado_al_periodo_siguiente(cliente, base):
    e = base["e"]
    diario(cliente, e, LIBRO_OK + cobro("C2", "31/01/2026", "0459999", "2000", "DEPOSITO CHEQUE CLIENTE"))
    estado_banco(cliente, base["cb"], MOVS_OK + [("31/01/2026", "COMISION MANTENIMIENTO", "-15", "")])
    ene = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    com = una(difs(cliente, e, ene["id"]), subtipo="COMISION_BANCARIA")
    dep = una(difs(cliente, e, ene["id"]), subtipo="DEPOSITO_EN_TRANSITO")
    r = cliente.patch(f"/api/conciliaciones/diferencias/{com['id']}", params=q(e),
                      json={"estado": "EN_ANALISIS", "responsable": "luis.tesoreria", "fecha_limite": "2026-02-15", "comentario": "Se solicitó el voucher"})
    assert r.status_code == 200 and r.json()["estado"] == "EN_ANALISIS"
    # febrero: el depósito en tránsito ya fue abonado; la comisión sigue sin registrarse
    estado_banco(cliente, base["cb"], [("02/02/2026", "DEPOSITO CHEQUE CLIENTE", "2000", "0459999")], saldo_inicial=D("10685"), nombre="feb.csv")
    feb = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]}, corte="2026-02-28")
    ds = difs(cliente, e, feb["id"])
    t = una(ds, subtipo="COMISION_BANCARIA")
    assert t["periodo_origen"] == 202601 and t["fecha_deteccion"] == com["fecha_deteccion"] and t["origen_id"] == com["id"]
    assert t["anterior_id"] == com["id"] and t["estado"] == "EN_ANALISIS" and t["responsable"] == "luis.tesoreria"
    assert t["recurrencias"] == 1 and D(t["importe_original"]) == D("-15") and D(t["importe_pendiente"]) == D("-15")
    assert not [d for d in ds if d["subtipo"] == "DEPOSITO_EN_TRANSITO"]
    # sin duplicar: la incidencia de enero queda trasladada, la del depósito queda subsanada
    h = cliente.get(f"/api/conciliaciones/diferencias/{t['id']}", params=q(e)).json()
    assert [x["id"] for x in h["cadena"]] == [t["id"], com["id"]]
    assert cliente.get(f"/api/conciliaciones/diferencias/{dep['id']}", params=q(e)).json()["diferencia"]["estado"] == "SUBSANADO"
    assert cliente.get(f"/api/conciliaciones/diferencias/{com['id']}", params=q(e)).json()["diferencia"]["trasladada"] is True
    tr = cliente.get("/api/conciliaciones/diferencias", params=q(e, trasladadas=True)).json()["items"]
    assert [x["id"] for x in tr] == [t["id"]]  # solo vigentes: la versión de enero no se cuenta dos veces


# ===================================================================== flujo: reversión (23) e historial (24)
def test_23_24_reversion_de_aprobada_e_historial(cliente, base):
    from datetime import datetime, timedelta

    from app.core.database import SessionLocal
    from app.models import DiferenciaConciliacion, RevisionConciliacion, VersionConciliacion
    e = base["e"]
    roles(cliente, e, [(CONTADOR, "CONTADOR"), (SUPERVISOR, "SUPERVISOR"), (GERENTE, "CONTADOR"), ("aldo.auditor", "AUDITOR")])
    diario(cliente, e, LIBRO_OK + cobro("C2", "31/01/2026", "0459999", "2000"))
    estado_banco(cliente, base["cb"], MOVS_OK)
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    rid = c["id"]
    est = lambda estado, u, **k: cliente.post(f"/api/conciliaciones/{rid}/estado", params=q(e), json={"estado": estado, **k},  # noqa: E731
                                             headers={"X-Usuario": u})
    assert est("APROBADA", GERENTE).status_code == 422          # no se salta la revisión
    assert est("EN_REVISION", CONTADOR).status_code == 200
    assert est("REVISADA", CONTADOR).status_code == 403          # quien elabora no revisa
    assert est("REVISADA", "aldo.auditor").status_code == 200
    assert est("APROBADA", "aldo.auditor").status_code == 403    # el auditor no aprueba
    assert est("APROBADA", CONTADOR).status_code == 403          # ni quien elaboró
    lock = ver(cliente, e, rid)["lock_version"]
    assert est("APROBADA", GERENTE, lock_version=lock - 1).status_code == 409  # bloqueo optimista
    r = est("APROBADA", GERENTE, lock_version=lock)
    assert r.status_code == 200 and r.json()["estado"] == "APROBADA" and r.json()["version"]["inmutable"]
    # una versión aprobada es inmutable
    libro = reg_por(cliente, e, rid, "A", numero="0459999")
    assert manual(cliente, e, rid, [{"id": libro["id"]}], [{"id": libro["id"]}]).status_code == 422
    assert cliente.post(f"/api/conciliaciones/{rid}/ejecutar", params=q(e), json={}, headers={"X-Usuario": CONTADOR}).status_code == 422
    # reversión: solo supervisor o administrador, con motivo
    m = {"motivo": "Se recibió un estado de cuenta corregido por el banco"}
    assert cliente.post(f"/api/conciliaciones/{rid}/revertir", params=q(e), json=m, headers={"X-Usuario": CONTADOR}).status_code == 403
    assert cliente.post(f"/api/conciliaciones/{rid}/revertir", params=q(e), json={"motivo": "x"}, headers={"X-Usuario": SUPERVISOR}).status_code == 422
    r = cliente.post(f"/api/conciliaciones/{rid}/revertir", params=q(e), json=m, headers={"X-Usuario": SUPERVISOR})
    assert r.status_code == 200 and r.json()["estado"] == "REABIERTA"
    c2 = ejecutar(cliente, e, rid)
    assert c2["version"]["numero"] == 2 and not c2["version"]["inmutable"] and c2["estado"] == "EJECUTADA"
    assert [v["inmutable"] for v in c2["versiones"]] == [True, False]
    h = cliente.get(f"/api/conciliaciones/{rid}/historial", params=q(e), headers={"X-Usuario": "aldo.auditor"}).json()
    assert [a["accion"] for a in h["aprobaciones"]] == ["REVISAR", "APROBAR", "REABRIR"]
    assert h["reversiones"][0]["alcance"] == "CONCILIACION" and h["reversiones"][0]["usuario"] == SUPERVISOR
    assert {"CREAR", "EJECUTAR", "ESTADO_APROBADA", "REVERTIR_CONCILIACION"} <= {a["accion"] for a in h["auditoria"]}
    # la versión 1 sigue consultable y exportable tal como se aprobó
    v1 = c2["versiones"][0]["id"]
    assert registros(cliente, e, rid, "A", version_id=v1)["total"] == 3
    assert cliente.get(f"/api/conciliaciones/{rid}/exportar", params=q(e, version_id=v1), headers={"X-Usuario": "aldo.auditor"}).status_code == 200
    # 24 · historial a una fecha: simulamos que la versión 1 y su aprobación ocurrieron hace 10 días
    with SessionLocal() as s:
        antes = datetime.now() - timedelta(days=10)
        s.get(VersionConciliacion, v1).generado_en = antes
        for x in s.query(DiferenciaConciliacion).filter(DiferenciaConciliacion.version_id == v1).all():
            x.creado_en = antes
        revs = s.query(RevisionConciliacion).filter(RevisionConciliacion.run_id == rid).order_by(RevisionConciliacion.id).all()
        aprobada = max(x.id for x in revs if x.a_estado == "APROBADA")
        for x in revs:
            if x.id <= aprobada:
                x.creado_en = antes
        s.commit()
    hace5 = (date.today() - timedelta(days=5)).isoformat()
    h5 = cliente.get(f"/api/conciliaciones/{rid}/a-fecha", params=q(e, fecha=hace5), headers={"X-Usuario": "aldo.auditor"}).json()
    assert h5["existia"] and h5["version"]["numero"] == 1 and h5["estado"] == "APROBADA"
    assert [x["subtipo"] for x in h5["diferencias"]] == ["DEPOSITO_EN_TRANSITO"]
    hoy = cliente.get(f"/api/conciliaciones/{rid}/a-fecha", params=q(e, fecha=date.today().isoformat()), headers={"X-Usuario": CONTADOR}).json()
    assert hoy["version"]["numero"] == 2 and hoy["estado"] == "EJECUTADA"
    antes_de_todo = cliente.get(f"/api/conciliaciones/{rid}/a-fecha", params=q(e, fecha=(date.today() - timedelta(days=30)).isoformat()),
                                headers={"X-Usuario": CONTADOR}).json()
    assert antes_de_todo["existia"] is False


# ===================================================================== exportación (26)
def test_26_exportacion_excel_y_pdf(cliente, base):
    import openpyxl
    import pdfplumber
    e = base["e"]
    diario(cliente, e, LIBRO_OK + cobro("C2", "31/01/2026", "0459999", "2000"))
    estado_banco(cliente, base["cb"], MOVS_OK + [("31/01/2026", "COMISION MANTENIMIENTO", "-15", "")])
    c = conciliar(cliente, e, "BANCARIA", {"cuenta_bancaria_id": base["cb"]})
    x = cliente.get(f"/api/conciliaciones/{c['id']}/exportar", params=q(e, formato="xlsx"))
    assert x.status_code == 200 and "spreadsheetml" in x.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ["Resumen", "Conciliación bancaria", "Fuente contable", "Fuente externa", "Conciliados", "No conciliados",
                             "Diferencias", "Observaciones", "Control de aprobación"]
    ws = wb["Conciliación bancaria"]
    formulas = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]
    assert any("-B" in f for f in formulas) and len(formulas) >= 3  # banco ajustado, libros ajustado y diferencia final con fórmulas
    nc = wb["No conciliados"]
    filas = [r for r in nc.iter_rows(min_row=5, values_only=True) if r[0] and isinstance(r[0], int)]
    assert len(filas) == 2 and all(r[-3] for r in filas)  # referencia al registro original (tabla de origen)
    texto_dif = " ".join(str(v) for row in wb["Diferencias"].iter_rows(values_only=True) for v in row if v)
    assert "COMISION_BANCARIA" in texto_dif and "DEPOSITO_EN_TRANSITO" in texto_dif
    p = cliente.get(f"/api/conciliaciones/{c['id']}/exportar", params=q(e, formato="pdf"))
    assert p.status_code == 200 and p.content[:4] == b"%PDF"
    with pdfplumber.open(io.BytesIO(p.content)) as pdf:
        texto = " ".join(pg.extract_text() or "" for pg in pdf.pages)
    assert "Conciliación bancaria" in texto and "Diferencia final" in texto and "Página 1 de" in texto and "Depósitos en tránsito" in texto
    for tipo in ("RESUMEN", "DIFERENCIAS", "PENDIENTES", "OBSERVACIONES", "HISTORIAL"):
        for fmt in ("xlsx", "pdf"):
            r = cliente.get(f"/api/conciliaciones/reportes/{tipo}", params=q(e, formato=fmt))
            assert r.status_code == 200 and len(r.content) > 500, (tipo, fmt)
    tab = cliente.get("/api/conciliaciones/tablero", params=q(e, ejercicio=2026)).json()
    assert tab["kpi"]["diferencias_abiertas"] == 2 and tab["kpi"]["pct_conciliado_cantidad"] is not None
    assert tab["kpi"]["pct_conciliado_cantidad"] != tab["kpi"]["pct_conciliado_importe"]  # por cantidad y por importe, por separado


# ===================================================================== diseñador y procesamiento masivo (25)
DEF_MASIVA = {
    "fuentes": {"A": {"tipo": "ARCHIVO", "rol": "CONTABLE", "nombre": "Sistema de tesorería", "esquema": "CONC_GENERICO"},
                "B": {"tipo": "ARCHIVO", "rol": "EXTERNA", "nombre": "Pasarela de pagos", "esquema": "CONC_GENERICO"}},
    "pasadas": [{"a": "A", "b": "B", "modo": "PARTIDAS", "signo": "IGUAL"}],
    "duplicados": {"B": [["operacion", "importe", "fecha"]]},
    "tolerancia": {"importe_absoluto": "0", "dias": 2},
    "confirmar_automaticamente": ["EXACTA"],
    "reglas": [{"codigo": "OPERACION", "descripcion": "Número de operación", "tipo": "CLAVE", "parametros": {"campos": ["operacion"]}},
               {"codigo": "IMPORTE_FECHA", "descripcion": "Importe y fecha", "tipo": "IMPORTE_FECHA"},
               {"codigo": "EXCLUIR_PRUEBAS", "descripcion": "Excluir operaciones de prueba", "tipo": "EXCLUSION",
                "parametros": {"expresion": "importe == 0", "lado": "*"}}]}


def test_diseñador_de_plantillas(cliente, base):
    e = base["e"]
    malo = {**DEF_MASIVA, "reglas": [{"codigo": "X", "tipo": "CLAVE", "parametros": {"campos": ["importe; DROP TABLE x"]}}]}
    r = cliente.post("/api/conciliaciones/plantillas/validar", params=q(e), json={"configuracion": malo})
    assert r.status_code == 422 and "no es un nombre de campo válido" in r.json()["detail"]
    malo = {**DEF_MASIVA, "reglas": [{"codigo": "X", "tipo": "EXCLUSION", "parametros": {"expresion": "__import__('os').system('x')"}}]}
    assert cliente.post("/api/conciliaciones/plantillas/validar", params=q(e), json={"configuracion": malo}).status_code == 422
    malo = {**DEF_MASIVA, "reglas": [{"codigo": "X", "tipo": "COMBINACION", "parametros": {"max_elementos": 50}}]}
    assert "límite combinatorio" in cliente.post("/api/conciliaciones/plantillas/validar", params=q(e), json={"configuracion": malo}).json()["detail"]
    r = cliente.post("/api/conciliaciones/plantillas", params=q(e), json={"nombre": "Pasarela de pagos", "configuracion": DEF_MASIVA},
                     headers={"X-Usuario": CONTADOR})
    assert r.status_code == 201 and r.json()["autorizada"] is False, r.text
    pid = r.json()["id"]
    r = cliente.post("/api/conciliaciones", params=q(e), json={"tipo": "PERSONALIZADA", "plantilla_id": pid, "fecha_corte": "2026-01-31"})
    assert r.status_code == 422 and "no está autorizada" in r.json()["detail"]
    assert cliente.post(f"/api/conciliaciones/plantillas/{pid}/autorizar", params=q(e), headers={"X-Usuario": CONTADOR}).status_code == 422
    assert cliente.post(f"/api/conciliaciones/plantillas/{pid}/autorizar", params=q(e), headers={"X-Usuario": SUPERVISOR}).json()["autorizada"]
    cfg = cliente.get(f"/api/conciliaciones/plantillas/{pid}", params=q(e)).json()["configuracion"]
    assert [x["codigo"] for x in cfg["reglas"]] == ["OPERACION", "IMPORTE_FECHA", "EXCLUIR_PRUEBAS"]
    c = crear(cliente, e, "PERSONALIZADA", plantilla_id=pid)
    vista = subir(cliente, e, c["id"], "A", "a.csv", b"Fecha;Operacion;Glosa;Importe\n05/01/2026;1;COBRO;100\n06/01/2026;2;PRUEBA;0\n", confirmar=False)
    assert vista["mapeo"]["numero_operacion"] == 1 and vista["registros"] == 2 and "fuente_id" not in vista  # vista previa sin guardar
    subir(cliente, e, c["id"], "A", "a.csv", b"Fecha;Operacion;Glosa;Importe\n05/01/2026;1;COBRO;100\n06/01/2026;2;PRUEBA;0\n",
          guardar_mapeo="Tesorería estándar")
    subir(cliente, e, c["id"], "B", "b.csv", b"Fecha;Operacion;Glosa;Importe\n05/01/2026;X1;COBRO;100\n")
    assert cliente.get("/api/conciliaciones/mapeos", params=q(e, esquema="CONC_GENERICO")).json()[0]["nombre"] == "Tesorería estándar"
    # paso 8: prueba en memoria de una variante de la definición (sin guardar)
    r = cliente.post("/api/conciliaciones/plantillas/probar", params=q(e), json={"run_id": c["id"], "configuracion": DEF_MASIVA})
    assert r.status_code == 200 and r.json()["excluidos"] == 1 and r.json()["grupos"] == {"EXACTA:CONFIRMADA": 1}
    c = ejecutar(cliente, e, c["id"])
    assert c["resumen"]["asignaciones"].get("CONCILIADO") == 2 and c["resumen"]["excluidos"] == 1


def test_25_procesamiento_masivo(cliente, base, capsys):
    """109 000 registros (A 55 000, B 54 000): 50 000 por operación (500 con diferencia de importe), 3 000 por importe y fecha,
    2 000 solo en A y 1 000 solo en B."""
    e = base["e"]
    pid = cliente.post("/api/conciliaciones/plantillas", params=q(e), json={"nombre": "Masiva", "configuracion": DEF_MASIVA},
                       headers={"X-Usuario": CONTADOR}).json()["id"]
    cliente.post(f"/api/conciliaciones/plantillas/{pid}/autorizar", params=q(e), headers={"X-Usuario": SUPERVISOR})
    fa, fb = ["Fecha;Operacion;Glosa;Importe"], ["Fecha;Operacion;Glosa;Importe"]
    for i in range(55000):
        f = f"{(i % 28) + 1:02d}/01/2026"
        imp = f"{1000 + i * 0.01:.2f}"
        if i < 50000:
            fa.append(f"{f};OP{i};COBRO {i};{imp}")
            fb.append(f"{f};OP{i};COBRO {i};{imp if i % 100 else f'{1005 + i * 0.01:.2f}'}")
        elif i < 53000:
            fa.append(f"{f};A{i};COBRO {i};{imp}")
            fb.append(f"{f};B{i};COBRO {i};{imp}")
        elif i < 54000:
            fa.append(f"{f};A{i};SOLO A {i};{imp}")
        else:
            fb.append(f"{f};B{i};SOLO B {i};{imp}")
            fa.append(f"{f};A{i}x;SOLO A {i};{2000 + i * 0.01:.2f}")
    t0 = time.perf_counter()
    c = crear(cliente, e, "PERSONALIZADA", plantilla_id=pid)
    subir(cliente, e, c["id"], "A", "a.csv", ("\n".join(fa) + "\n").encode())
    subir(cliente, e, c["id"], "B", "b.csv", ("\n".join(fb) + "\n").encode())
    t1 = time.perf_counter()
    c = ejecutar(cliente, e, c["id"])
    t2 = time.perf_counter()
    res = c["resumen"]
    assert res["registros"] == {"A": 55000, "B": 54000}
    assert len(fa) - 1 + len(fb) - 1 == 109000
    g = res["grupos"]
    assert g["EXACTA:CONFIRMADA"] == 49500 + 3000 and g["DIFERENCIA:PROPUESTA"] == 500
    ds = cliente.get("/api/conciliaciones/diferencias", params=q(e, run_id=c["id"], por_pagina=1)).json()
    por = res["por_clasificacion"]
    assert por["DIFERENCIA_MONETARIA"] == 500 and por["REGISTRO_FALTANTE_FUENTE_EXTERNA"] == 2000 and por["REGISTRO_FALTANTE_CONTABILIDAD"] == 1000
    assert ds["total"] == 3500
    # paginación en el servidor
    p = registros(cliente, e, c["id"], "A", estado="PENDIENTE")
    assert p["total"] == 2000 and len(p["items"]) == 500
    # idempotencia: sin cambios no se genera otra versión
    t3 = time.perf_counter()
    c2 = ejecutar(cliente, e, c["id"])
    t4 = time.perf_counter()
    assert c2["version"]["numero"] == 1 and "Sin cambios" in c2["etapa"]
    with capsys.disabled():
        print(f"\n[volumen fase 6] 109 000 registros · importación {t1 - t0:.1f} s · conciliación {t2 - t1:.1f} s · "
              f"re-ejecución idempotente {t4 - t3:.1f} s · etapas {c['tiempos']}")
    assert t2 - t1 < 300


# ===================================================================== módulos adicionales: servicios en proceso y ventas
def test_servicios_en_proceso_y_cuenta_23(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("31", "SP1", "31/01/2026", [("6211", "", {"debe": "3000", "glosa": "MANO DE OBRA P-100", "proyecto": "P-100", "cc": "OPE"}),
                                                            ("6343", "", {"debe": "800", "glosa": "MANTENIMIENTO ADMINISTRATIVO", "cc": "ADM"}),
                                                            ("4111", W1, {"haber": "3800", "glosa": "PLANILLA"})])
           + asiento("31", "SP2", "31/01/2026", [("2311", "", {"debe": "3000", "glosa": "COSTO EN PROCESO P-100", "proyecto": "P-100"}),
                                                  ("7111", "", {"haber": "3000", "glosa": "VARIACION PRODUCCION", "proyecto": "P-100"})]))
    reporte = ("Proyecto;Orden de Servicio;Concepto;Importe;Periodo\nP-100;OS-1;MANO DE OBRA;3000;2026-01\nP-100;OS-1;COMBUSTIBLE;500;2026-01\n").encode()
    c = conciliar(cliente, e, "SERVICIOS_PROCESO", archivos=[("A", "costos.csv", reporte)])
    ds = difs(cliente, e, c["id"])
    solo = [d for d in ds if d["subtipo"] in ("SOLO_A", "SOLO_B")]
    assert len(solo) == 1 and solo[0]["subtipo"] == "SOLO_A" and D(solo[0]["importe"]) == D("500")  # el combustible no está contabilizado
    assert D(una(ds, subtipo="COSTO_SIN_PROYECTO")["importe"]) == D("800")  # costo administrativo: informativo, no exige proyecto
    assert c["resumen"]["excluidos"] == 1  # la cuenta 23 no se cruza dos veces contra el reporte operativo
    assert c["version"]["reporte"]["saldo_23_por_proyecto"] == {"P-100": "3000"}


def test_ventas_ingreso_sin_comprobante_no_es_error(cliente, base):
    e = base["e"]
    diario(cliente, e, asiento("05", "V1", "10/01/2026", [("1212", "20555555551", {"td": "01", "serie": "F001", "num": "20", "debe": "1180", "glosa": "VENTA",
                                                                                   "rs": "CLIENTE UNO"}),
                                                           ("40111", "", {"haber": "180", "glosa": "IGV"}), ("7041", "", {"haber": "1000", "glosa": "VENTA"})])
           + asiento("31", "DV1", "31/01/2026", [("1213", "", {"debe": "2000", "glosa": "INGRESO DEVENGADO NO FACTURADO"}),
                                                  ("7041", "", {"haber": "2000", "glosa": "SERVICIO DEVENGADO ENERO"})]))
    reg = reg_compras([["10/01/2026", "01", "F001", "20", "20555555551", "CLIENTE UNO", "1000", "180", "0", "1180", "PEN", ""],
                       ["15/01/2026", "01", "F001", "21", "20555555551", "CLIENTE UNO", "500", "90", "0", "590", "PEN", ""]])
    importar_bytes(cliente, e, "ventas.csv", reg, "VENTAS", periodo=1, ejercicio=2026)
    c = conciliar(cliente, e, "VENTAS")
    ds = difs(cliente, e, c["id"])
    assert D(una(ds, subtipo="VENTA_NO_CONTABILIZADA")["importe"]) == D("590")
    d = una(ds, subtipo="INGRESO_SIN_COMPROBANTE")
    assert d["clasificacion"] == "DIFERENCIA_TEMPORAL" and d["prioridad"] == "BAJO" and "NIIF 15" in d["recomendacion"]


def test_13b_versiones_de_cronograma(cliente, base):
    """Un cronograma reprogramado (versión 2) se compara en su última versión y se conserva el original."""
    e = base["e"]
    diario(cliente, e, asiento("21", "PR1", "02/01/2026", [("104101", "20100047218", {"debe": "60000", "glosa": "DESEMBOLSO PRESTAMO PR-77"}),
                                                            ("4511", "20100047218", {"haber": "60000", "glosa": "DESEMBOLSO PRESTAMO PR-77", "ref": "PR-77"})])
           + asiento("21", "PR2", "31/01/2026", [("4511", "20100047218", {"debe": "2000", "glosa": "CUOTA 1 PRESTAMO PR-77", "ref": "PR-77"}),
                                                  ("6731", "20100047218", {"debe": "1100", "glosa": "INTERESES CUOTA 1 PR-77"}),
                                                  ("104101", "20100047218", {"haber": "3100", "glosa": "PAGO CUOTA 1"})]))
    aux(cliente, e, "CONTRATO_FINANCIERO", "contratos.csv", CONTRATOS)
    aux(cliente, e, "CUOTA_FINANCIERA", "cuotas.csv", CUOTAS)
    c = conciliar(cliente, e, "FINANCIERAS")
    cap = una(difs(cliente, e, c["id"]), subtipo="DIFERENCIA_CAPITAL")
    v2 = ("contrato;version;numero;fecha_vencimiento;capital;interes;comision;pagada\n"
          "PR-77;2;1;31/01/2026;2000;1100;;S\nPR-77;2;2;28/02/2026;3000;575;;N\n").encode()
    aux(cliente, e, "CUOTA_FINANCIERA", "cuotas_v2.csv", v2)
    c = ejecutar(cliente, e, c["id"], forzar=True)
    ds = difs(cliente, e, c["id"])
    mod = una(ds, subtipo="CRONOGRAMA_MODIFICADO")
    assert "versión 1 → 2" in mod["explicacion"] and D(mod["importe"]) == D("500")  # intereses 1 175 → 1 675
    assert not [d for d in ds if d["subtipo"] in ("DIFERENCIA_CAPITAL", "CUOTA_NO_REGISTRADA", "PAGO_SIN_CUOTA")]
    rep = next(x for x in c["version"]["reporte"]["contratos"] if x["contrato"] == "PR-77")
    assert rep["versiones_cronograma"] == [1, 2] and D(rep["capital_pendiente_cronograma"]) == D("58000")
    assert cliente.get(f"/api/conciliaciones/diferencias/{cap['id']}", params=q(e)).json()["diferencia"]["estado"] == "DETECTADO"  # versión anterior: historia
    # el anexo de la cuenta 45 (fase 5) también usa la última versión del cronograma
    r = cliente.post("/api/anexos/generaciones", params=q(e), json={"fecha_corte": "2026-01-31", "modo": "CUENTAS", "cuentas": ["4511"]})
    assert r.status_code == 202, r.text
