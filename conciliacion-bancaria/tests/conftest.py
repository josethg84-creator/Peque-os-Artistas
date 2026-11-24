import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "ejemplos"


@pytest.fixture(scope="session", autouse=True)
def ejemplos():
    if not (EJEMPLOS / "libro_mayor_cuenta10_2026-10.xlsx").exists():
        subprocess.run([sys.executable, str(RAIZ / "scripts" / "generar_ejemplos.py")], check=True)
    return EJEMPLOS


@pytest.fixture()
def cliente(tmp_path):
    from app.core import database
    database.configurar(f"sqlite:///{tmp_path / 'prueba.db'}")
    from app.main import crear_app
    with TestClient(crear_app(), headers={"X-Usuario": "tesorero.prueba"}) as c:
        yield c


@pytest.fixture()
def escenario(cliente):
    """Empresa con cuentas BCP (PEN), BBVA (USD) e Interbank (PEN)."""
    emp = cliente.post("/api/empresas", json={"ruc": "20609876540", "razon_social": "Comercial Andina S.A.C."}).json()
    bancos = {b["codigo"]: b["id"] for b in cliente.get("/api/bancos").json()}
    cuentas = {}
    for clave, banco, moneda, numero, cc in [
        ("bcp", "BCP", "PEN", "191-1234567-0-01", "104101"),
        ("bbva", "BBVA", "USD", "0011-0123-0100012345", "104102"),
        ("ibk", "INTERBANK", "PEN", "200-3001234567", "104103"),
    ]:
        r = cliente.post("/api/cuentas", json={"empresa_id": emp["id"], "banco_id": bancos[banco],
                                               "moneda": moneda, "numero_cuenta": numero, "cuenta_contable": cc})
        assert r.status_code == 201, r.text
        cuentas[clave] = r.json()
    return {"empresa": emp, "cuentas": cuentas}
