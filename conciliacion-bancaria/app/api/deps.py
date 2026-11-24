from typing import Annotated
from urllib.parse import unquote

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db

DB = Annotated[Session, Depends(get_db)]


def usuario_actual(x_usuario: Annotated[str | None, Header()] = None) -> str:
    """Usuario que opera (fase 6 lo reemplaza por autenticación real)."""
    nombre = unquote(x_usuario or "").strip()
    return nombre[:80] or "sistema"


Usuario = Annotated[str, Depends(usuario_actual)]
