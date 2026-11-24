"""Datos maestros: empresas, bancos, monedas, cuentas bancarias y su configuración."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, String,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ruc: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    nombre_comercial: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cuentas: Mapped[list["CuentaBancaria"]] = relationship(back_populates="empresa")


class Banco(Base):
    __tablename__ = "bancos"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)  # BCP, BBVA…
    nombre: Mapped[str] = mapped_column(String(120))
    codigo_sunat: Mapped[str | None] = mapped_column(String(4))  # Tabla 3 PLE
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Moneda(Base):
    __tablename__ = "monedas"

    codigo: Mapped[str] = mapped_column(String(3), primary_key=True)  # ISO 4217
    nombre: Mapped[str] = mapped_column(String(60))
    simbolo: Mapped[str] = mapped_column(String(5))


class CuentaBancaria(Base):
    __tablename__ = "cuentas_bancarias"
    __table_args__ = (UniqueConstraint("empresa_id", "banco_id", "numero_cuenta"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    banco_id: Mapped[int] = mapped_column(ForeignKey("bancos.id"))
    moneda: Mapped[str] = mapped_column(ForeignKey("monedas.codigo"))
    numero_cuenta: Mapped[str] = mapped_column(String(30))
    cci: Mapped[str | None] = mapped_column(String(20))
    cuenta_contable: Mapped[str] = mapped_column(String(12))  # p. ej. 104101
    descripcion: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    empresa: Mapped[Empresa] = relationship(back_populates="cuentas")
    banco: Mapped[Banco] = relationship()
    configuracion: Mapped["ConfiguracionConciliacion"] = relationship(
        back_populates="cuenta", uselist=False, cascade="all, delete-orphan")


class ConfiguracionConciliacion(Base):
    """Tolerancias y umbrales del motor de conciliación (fase 2) por cuenta."""
    __tablename__ = "configuracion_conciliacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_bancaria_id: Mapped[int] = mapped_column(
        ForeignKey("cuentas_bancarias.id"), unique=True)
    tolerancia_dias: Mapped[int] = mapped_column(Integer, default=3)
    tolerancia_importe: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    umbral_auto_confirmacion: Mapped[int] = mapped_column(Integer, default=95)
    umbral_sugerencia: Mapped[int] = mapped_column(Integer, default=60)
    max_elementos_combinacion: Mapped[int] = mapped_column(Integer, default=4)
    usar_numero_operacion: Mapped[bool] = mapped_column(Boolean, default=True)

    cuenta: Mapped[CuentaBancaria] = relationship(back_populates="configuracion")
