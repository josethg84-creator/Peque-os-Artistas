"""Panel resumen y bitácora de auditoría."""
from fastapi import APIRouter
from sqlalchemy import case, func, select

from app.api.deps import DB
from app.models import (AuditLog, CuentaBancaria, EstadoConciliacion, EstadoImportacion, Importacion,
                        MovimientoBanco, MovimientoLibro)
from app.schemas import AuditOut

router = APIRouter(tags=["Panel"])


def _resumen_movs(db, Modelo, cuenta_id):
    vigente = Modelo.estado_conciliacion != EstadoConciliacion.EXCLUIDO
    fila = db.execute(select(
        func.count().filter(vigente),
        func.count().filter(Modelo.estado_conciliacion == EstadoConciliacion.PENDIENTE),
        func.count().filter(Modelo.posible_duplicado.is_(True), vigente),
        func.coalesce(func.sum(case((vigente, Modelo.importe), else_=0)), 0),
        func.min(Modelo.fecha), func.max(Modelo.fecha),
    ).where(Modelo.cuenta_bancaria_id == cuenta_id)).one()
    return {"movimientos": fila[0], "pendientes": fila[1], "posibles_duplicados": fila[2],
            "neto": str(fila[3]), "desde": fila[4].isoformat() if fila[4] else None,
            "hasta": fila[5].isoformat() if fila[5] else None}


@router.get("/panel")
def panel(db: DB, empresa_id: int | None = None):
    q = select(CuentaBancaria).where(CuentaBancaria.activo.is_(True)).order_by(CuentaBancaria.cuenta_contable)
    if empresa_id:
        q = q.where(CuentaBancaria.empresa_id == empresa_id)
    cuentas = []
    for c in db.scalars(q):
        ult = db.scalar(select(Importacion).where(
            Importacion.cuenta_bancaria_id == c.id, Importacion.tipo == "BANCO",
            Importacion.estado == EstadoImportacion.ACTIVA).order_by(Importacion.fecha_hasta.desc(), Importacion.id.desc()))
        cuentas.append({
            "id": c.id, "banco": c.banco.nombre, "banco_codigo": c.banco.codigo, "numero_cuenta": c.numero_cuenta,
            "moneda": c.moneda, "cuenta_contable": c.cuenta_contable, "descripcion": c.descripcion,
            "banco_resumen": _resumen_movs(db, MovimientoBanco, c.id),
            "libro_resumen": _resumen_movs(db, MovimientoLibro, c.id),
            "ultimo_saldo_banco": str(ult.saldo_final) if ult and ult.saldo_final is not None else None,
            "ultimo_corte_banco": ult.fecha_hasta.isoformat() if ult and ult.fecha_hasta else None,
        })
    return {"cuentas": cuentas}


@router.get("/auditoria", response_model=list[AuditOut])
def bitacora(db: DB, empresa_id: int | None = None, entidad: str | None = None, usuario: str | None = None,
             limite: int = 300):
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limite, 2000))
    if empresa_id:
        q = q.where(AuditLog.empresa_id == empresa_id)
    if entidad:
        q = q.where(AuditLog.entidad == entidad)
    if usuario:
        q = q.where(AuditLog.usuario.ilike(f"%{usuario}%"))
    return db.scalars(q).all()
