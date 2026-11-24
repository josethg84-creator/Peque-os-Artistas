"""Bitácora de auditoría: toda alta, cambio, anulación o decisión queda registrada."""
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def _serializable(v: Any) -> Any:
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def instantanea(obj: Any, campos: list[str] | None = None) -> dict:
    cols = campos or [c.key for c in obj.__table__.columns]
    return {c: _serializable(getattr(obj, c)) for c in cols}


def registrar(
    db: Session,
    *,
    usuario: str,
    entidad: str,
    entidad_id: int | None,
    accion: str,
    antes: dict | None = None,
    despues: dict | None = None,
    detalle: str | None = None,
    empresa_id: int | None = None,
) -> AuditLog:
    cambios = None
    if antes is not None and despues is not None:
        cambios = {k: {"antes": antes.get(k), "despues": despues.get(k)}
                   for k in despues if antes.get(k) != despues.get(k)}
    log = AuditLog(
        usuario=usuario or "sistema",
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        empresa_id=empresa_id,
        detalle=detalle,
        datos=json.dumps(
            {"antes": antes, "despues": despues, "cambios": cambios},
            ensure_ascii=False, default=_serializable,
        ) if (antes or despues) else None,
    )
    db.add(log)
    return log
