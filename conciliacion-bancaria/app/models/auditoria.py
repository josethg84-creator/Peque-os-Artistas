"""Bitácora de auditoría (inmutable)."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    usuario: Mapped[str] = mapped_column(String(80))
    empresa_id: Mapped[int | None] = mapped_column(Integer, index=True)
    entidad: Mapped[str] = mapped_column(String(40), index=True)
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    accion: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[str | None] = mapped_column(String(500))
    datos: Mapped[str | None] = mapped_column(Text)
