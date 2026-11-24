"""Consulta de movimientos de banco y libro, y resolución de duplicados."""
from datetime import date

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, or_, select

from app.api.deps import DB, Usuario
from app.importers.lectores import ErrorImportacion
from app.models import CuentaBancaria, EstadoConciliacion, MovimientoBanco, MovimientoLibro
from app.schemas import DecisionDuplicado, MovimientoBancoOut, MovimientoLibroOut
from app.services import importacion as svc

router = APIRouter(prefix="/movimientos", tags=["Movimientos"])


def _filtrar(q, Modelo, *, cuenta_id, empresa_id, desde, hasta, estado, solo_duplicados, texto, importacion_id,
             campos_texto):
    if cuenta_id:
        q = q.where(Modelo.cuenta_bancaria_id == cuenta_id)
    if empresa_id:
        q = q.join(CuentaBancaria, CuentaBancaria.id == Modelo.cuenta_bancaria_id).where(
            CuentaBancaria.empresa_id == empresa_id)
    if importacion_id:
        q = q.where(Modelo.importacion_id == importacion_id)
    if desde:
        q = q.where(Modelo.fecha >= desde)
    if hasta:
        q = q.where(Modelo.fecha <= hasta)
    if estado:
        q = q.where(Modelo.estado_conciliacion == estado.upper())
    if solo_duplicados:
        q = q.where(Modelo.posible_duplicado.is_(True))
    if texto:
        patron = f"%{texto.strip()}%"
        q = q.where(or_(*[c.ilike(patron) for c in campos_texto]))
    return q


def _suma_vigente(db, base):
    """Suma de importes sin movimientos excluidos (salvo que se filtre justamente por EXCLUIDO)."""
    sub = base.subquery()
    q = select(func.coalesce(func.sum(sub.c.importe), 0))
    excl = select(func.count()).select_from(sub).where(sub.c.estado_conciliacion != EstadoConciliacion.EXCLUIDO)
    if db.scalar(excl):
        q = q.where(sub.c.estado_conciliacion != EstadoConciliacion.EXCLUIDO)
    return db.scalar(q)


def _listar(db, Modelo, campos_texto, pagina, por_pagina, **filtros):
    base = _filtrar(select(Modelo), Modelo, campos_texto=campos_texto, **filtros)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    suma = _suma_vigente(db, base)
    items = db.scalars(base.order_by(Modelo.fecha, Modelo.id)
                       .offset((pagina - 1) * por_pagina).limit(por_pagina)).all()
    return total, suma, items


@router.get("/banco")
def movimientos_banco(db: DB, cuenta_id: int | None = None, empresa_id: int | None = None,
                      desde: date | None = None, hasta: date | None = None, estado: str | None = None,
                      categoria: str | None = None, solo_duplicados: bool = False, texto: str | None = None,
                      importacion_id: int | None = None, pagina: int = 1, por_pagina: int = 100):
    por_pagina = max(1, min(por_pagina, 1000))
    filtros = dict(cuenta_id=cuenta_id, empresa_id=empresa_id, desde=desde, hasta=hasta, estado=estado,
                   solo_duplicados=solo_duplicados, texto=texto, importacion_id=importacion_id)
    campos_texto = [MovimientoBanco.descripcion, MovimientoBanco.numero_operacion, MovimientoBanco.referencia]
    base = _filtrar(select(MovimientoBanco), MovimientoBanco, campos_texto=campos_texto, **filtros)
    if categoria:
        base = base.where(MovimientoBanco.categoria == categoria.upper())
    sub = base.subquery()
    total = db.scalar(select(func.count()).select_from(sub))
    suma = _suma_vigente(db, base)
    items = db.scalars(base.order_by(MovimientoBanco.fecha, MovimientoBanco.id)
                       .offset((max(pagina, 1) - 1) * por_pagina).limit(por_pagina)).all()
    return {"total": total, "suma_importes": str(suma), "pagina": pagina, "por_pagina": por_pagina,
            "items": [MovimientoBancoOut.model_validate(m).model_dump(mode="json") for m in items]}


@router.get("/libro")
def movimientos_libro(db: DB, cuenta_id: int | None = None, empresa_id: int | None = None,
                      desde: date | None = None, hasta: date | None = None, estado: str | None = None,
                      solo_duplicados: bool = False, texto: str | None = None,
                      importacion_id: int | None = None, pagina: int = 1, por_pagina: int = 100):
    por_pagina = max(1, min(por_pagina, 1000))
    total, suma, items = _listar(
        db, MovimientoLibro,
        [MovimientoLibro.glosa, MovimientoLibro.numero_operacion, MovimientoLibro.voucher, MovimientoLibro.tercero],
        max(pagina, 1), por_pagina, cuenta_id=cuenta_id, empresa_id=empresa_id, desde=desde, hasta=hasta,
        estado=estado, solo_duplicados=solo_duplicados, texto=texto, importacion_id=importacion_id)
    return {"total": total, "suma_importes": str(suma), "pagina": pagina, "por_pagina": por_pagina,
            "items": [MovimientoLibroOut.model_validate(m).model_dump(mode="json") for m in items]}


@router.post("/{tipo}/{mov_id}/duplicado")
def resolver_duplicado(tipo: str, mov_id: int, datos: DecisionDuplicado, db: DB, usuario: Usuario):
    tipo = tipo.upper()
    Modelo = {"BANCO": MovimientoBanco, "LIBRO": MovimientoLibro}.get(tipo)
    if not Modelo:
        raise HTTPException(404, "Tipo inválido")
    mov = db.get(Modelo, mov_id)
    if not mov:
        raise HTTPException(404, "Movimiento no encontrado")
    try:
        svc.resolver_duplicado(db, tipo, mov, datos.decision, usuario, datos.comentario)
    except ErrorImportacion as exc:
        raise HTTPException(409, str(exc))
    Out = MovimientoBancoOut if tipo == "BANCO" else MovimientoLibroOut
    return Out.model_validate(mov).model_dump(mode="json")
