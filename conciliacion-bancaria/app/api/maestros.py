"""Empresas, bancos, monedas, cuentas bancarias y tolerancias."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, Usuario
from app.core import auditoria
from app.models import Banco, ConfiguracionConciliacion, CuentaBancaria, Empresa, Moneda
from app.schemas import (BancoIn, BancoOut, ConfiguracionIn, ConfiguracionOut, CuentaIn, CuentaOut,
                         EmpresaIn, EmpresaOut, MonedaOut)

router = APIRouter(tags=["Datos maestros"])


def _obtener(db, modelo, id_, nombre):
    obj = db.get(modelo, id_)
    if not obj:
        raise HTTPException(404, f"{nombre} no encontrada" if nombre.endswith("a") else f"{nombre} no encontrado")
    return obj


# --- Empresas ---------------------------------------------------------------
@router.get("/empresas", response_model=list[EmpresaOut])
def listar_empresas(db: DB, incluir_inactivas: bool = False):
    q = select(Empresa).order_by(Empresa.razon_social)
    if not incluir_inactivas:
        q = q.where(Empresa.activo.is_(True))
    return db.scalars(q).all()


@router.post("/empresas", response_model=EmpresaOut, status_code=201)
def crear_empresa(datos: EmpresaIn, db: DB, usuario: Usuario):
    if db.scalar(select(Empresa).where(Empresa.ruc == datos.ruc)):
        raise HTTPException(409, "Ya existe una empresa con ese RUC")
    emp = Empresa(**datos.model_dump())
    db.add(emp)
    db.flush()
    auditoria.registrar(db, usuario=usuario, entidad="empresa", entidad_id=emp.id, accion="CREAR",
                        despues=auditoria.instantanea(emp), empresa_id=emp.id)
    db.commit()
    return emp


@router.put("/empresas/{empresa_id}", response_model=EmpresaOut)
def actualizar_empresa(empresa_id: int, datos: EmpresaIn, db: DB, usuario: Usuario):
    emp = _obtener(db, Empresa, empresa_id, "Empresa")
    otra = db.scalar(select(Empresa).where(Empresa.ruc == datos.ruc, Empresa.id != empresa_id))
    if otra:
        raise HTTPException(409, "Ya existe otra empresa con ese RUC")
    antes = auditoria.instantanea(emp)
    for k, v in datos.model_dump().items():
        setattr(emp, k, v)
    auditoria.registrar(db, usuario=usuario, entidad="empresa", entidad_id=emp.id, accion="MODIFICAR",
                        antes=antes, despues=auditoria.instantanea(emp), empresa_id=emp.id)
    db.commit()
    return emp


# --- Catálogos --------------------------------------------------------------
@router.get("/monedas", response_model=list[MonedaOut])
def listar_monedas(db: DB):
    return db.scalars(select(Moneda).order_by(Moneda.codigo)).all()


@router.get("/bancos", response_model=list[BancoOut])
def listar_bancos(db: DB):
    return db.scalars(select(Banco).where(Banco.activo.is_(True)).order_by(Banco.nombre)).all()


@router.post("/bancos", response_model=BancoOut, status_code=201)
def crear_banco(datos: BancoIn, db: DB, usuario: Usuario):
    banco = Banco(codigo=datos.codigo.strip().upper(), nombre=datos.nombre.strip(),
                  codigo_sunat=datos.codigo_sunat)
    db.add(banco)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe un banco con ese código")
    auditoria.registrar(db, usuario=usuario, entidad="banco", entidad_id=banco.id, accion="CREAR",
                        despues=auditoria.instantanea(banco))
    db.commit()
    return banco


# --- Cuentas bancarias ------------------------------------------------------
@router.get("/cuentas", response_model=list[CuentaOut])
def listar_cuentas(db: DB, empresa_id: int | None = None, incluir_inactivas: bool = False):
    q = select(CuentaBancaria).order_by(CuentaBancaria.cuenta_contable)
    if empresa_id:
        q = q.where(CuentaBancaria.empresa_id == empresa_id)
    if not incluir_inactivas:
        q = q.where(CuentaBancaria.activo.is_(True))
    return db.scalars(q).all()


@router.get("/cuentas/{cuenta_id}", response_model=CuentaOut)
def obtener_cuenta(cuenta_id: int, db: DB):
    return _obtener(db, CuentaBancaria, cuenta_id, "Cuenta")


def _validar_cuenta(db, datos: CuentaIn, cuenta_id: int | None = None):
    _obtener(db, Empresa, datos.empresa_id, "Empresa")
    _obtener(db, Banco, datos.banco_id, "Banco")
    if not db.get(Moneda, datos.moneda.upper()):
        raise HTTPException(422, "Moneda no registrada")
    q = select(CuentaBancaria).where(
        CuentaBancaria.empresa_id == datos.empresa_id, CuentaBancaria.banco_id == datos.banco_id,
        CuentaBancaria.numero_cuenta == datos.numero_cuenta.strip())
    if cuenta_id:
        q = q.where(CuentaBancaria.id != cuenta_id)
    if db.scalar(q):
        raise HTTPException(409, "La cuenta ya está registrada para esta empresa y banco")
    q2 = select(CuentaBancaria).where(CuentaBancaria.empresa_id == datos.empresa_id,
                                      CuentaBancaria.cuenta_contable == datos.cuenta_contable,
                                      CuentaBancaria.activo.is_(True))
    if cuenta_id:
        q2 = q2.where(CuentaBancaria.id != cuenta_id)
    if db.scalar(q2):
        raise HTTPException(409, f"La subcuenta contable {datos.cuenta_contable} ya está asignada a otra cuenta bancaria")


@router.post("/cuentas", response_model=CuentaOut, status_code=201)
def crear_cuenta(datos: CuentaIn, db: DB, usuario: Usuario):
    _validar_cuenta(db, datos)
    valores = datos.model_dump()
    valores["moneda"] = valores["moneda"].upper()
    valores["numero_cuenta"] = valores["numero_cuenta"].strip()
    cuenta = CuentaBancaria(**valores)
    cuenta.configuracion = ConfiguracionConciliacion()
    db.add(cuenta)
    db.flush()
    auditoria.registrar(db, usuario=usuario, entidad="cuenta_bancaria", entidad_id=cuenta.id,
                        accion="CREAR", despues=auditoria.instantanea(cuenta), empresa_id=cuenta.empresa_id)
    db.commit()
    return cuenta


@router.put("/cuentas/{cuenta_id}", response_model=CuentaOut)
def actualizar_cuenta(cuenta_id: int, datos: CuentaIn, db: DB, usuario: Usuario):
    cuenta = _obtener(db, CuentaBancaria, cuenta_id, "Cuenta")
    _validar_cuenta(db, datos, cuenta_id)
    if datos.moneda.upper() != cuenta.moneda and _tiene_movimientos(db, cuenta_id):
        raise HTTPException(409, "No se puede cambiar la moneda de una cuenta con movimientos importados")
    antes = auditoria.instantanea(cuenta)
    for k, v in datos.model_dump().items():
        setattr(cuenta, k, v.upper() if k == "moneda" else v)
    auditoria.registrar(db, usuario=usuario, entidad="cuenta_bancaria", entidad_id=cuenta.id,
                        accion="MODIFICAR", antes=antes, despues=auditoria.instantanea(cuenta),
                        empresa_id=cuenta.empresa_id)
    db.commit()
    return cuenta


def _tiene_movimientos(db, cuenta_id: int) -> bool:
    from app.models import Importacion
    return db.scalar(select(Importacion.id).where(Importacion.cuenta_bancaria_id == cuenta_id).limit(1)) is not None


@router.get("/cuentas/{cuenta_id}/configuracion", response_model=ConfiguracionOut)
def obtener_configuracion(cuenta_id: int, db: DB):
    cuenta = _obtener(db, CuentaBancaria, cuenta_id, "Cuenta")
    if not cuenta.configuracion:
        cuenta.configuracion = ConfiguracionConciliacion()
        db.commit()
    return cuenta.configuracion


@router.put("/cuentas/{cuenta_id}/configuracion", response_model=ConfiguracionOut)
def actualizar_configuracion(cuenta_id: int, datos: ConfiguracionIn, db: DB, usuario: Usuario):
    if datos.umbral_sugerencia > datos.umbral_auto_confirmacion:
        raise HTTPException(422, "El umbral de sugerencia no puede superar al de auto-confirmación")
    cuenta = _obtener(db, CuentaBancaria, cuenta_id, "Cuenta")
    cfg = cuenta.configuracion or ConfiguracionConciliacion(cuenta_bancaria_id=cuenta.id)
    if cfg.id is None:
        db.add(cfg)
        db.flush()
    antes = auditoria.instantanea(cfg)
    for k, v in datos.model_dump().items():
        setattr(cfg, k, v)
    auditoria.registrar(db, usuario=usuario, entidad="configuracion_conciliacion", entidad_id=cfg.id,
                        accion="MODIFICAR", antes=antes, despues=auditoria.instantanea(cfg),
                        empresa_id=cuenta.empresa_id)
    db.commit()
    return cfg
