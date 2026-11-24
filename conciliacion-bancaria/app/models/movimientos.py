"""Lotes de importación y movimientos de banco y de libro (cuenta 10)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String,
                        Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoOrigen:
    BANCO = "BANCO"
    LIBRO = "LIBRO"


class EstadoImportacion:
    ACTIVA = "ACTIVA"
    ANULADA = "ANULADA"


class EstadoConciliacion:
    PENDIENTE = "PENDIENTE"
    PROPUESTO = "PROPUESTO"      # fase 2
    CONCILIADO = "CONCILIADO"    # fase 2
    EXCLUIDO = "EXCLUIDO"        # duplicado confirmado / anulado


class Importacion(Base):
    __tablename__ = "importaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_bancaria_id: Mapped[int] = mapped_column(ForeignKey("cuentas_bancarias.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))  # BANCO | LIBRO
    nombre_archivo: Mapped[str] = mapped_column(String(255))
    formato: Mapped[str] = mapped_column(String(10))  # CSV | XLSX | PDF
    hash_archivo: Mapped[str] = mapped_column(String(64), index=True)
    fecha_desde: Mapped[date | None] = mapped_column(Date)
    fecha_hasta: Mapped[date | None] = mapped_column(Date)
    total_registros: Mapped[int] = mapped_column(Integer, default=0)
    total_duplicados: Mapped[int] = mapped_column(Integer, default=0)
    total_omitidos: Mapped[int] = mapped_column(Integer, default=0)
    total_ingresos: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    total_egresos: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    saldo_inicial: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    saldo_final: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    mapeo: Mapped[str | None] = mapped_column(Text)  # JSON columna→campo
    advertencias: Mapped[str | None] = mapped_column(Text)  # JSON
    estado: Mapped[str] = mapped_column(String(10), default=EstadoImportacion.ACTIVA)
    usuario: Mapped[str] = mapped_column(String(80))
    motivo_anulacion: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cuenta = relationship("CuentaBancaria")


class _MovimientoBase:
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    importe: Mapped[Decimal] = mapped_column(Numeric(18, 2), index=True)  # + ingreso / - egreso
    moneda: Mapped[str] = mapped_column(String(3))
    numero_operacion: Mapped[str | None] = mapped_column(String(40), index=True)
    hash_registro: Mapped[str] = mapped_column(String(64), index=True)
    posible_duplicado: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_duplicado: Mapped[str | None] = mapped_column(String(255))
    estado_conciliacion: Mapped[str] = mapped_column(
        String(12), default=EstadoConciliacion.PENDIENTE, index=True)
    fila_origen: Mapped[int | None] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MovimientoBanco(_MovimientoBase, Base):
    __tablename__ = "movimientos_banco"

    cuenta_bancaria_id: Mapped[int] = mapped_column(ForeignKey("cuentas_bancarias.id"), index=True)
    importacion_id: Mapped[int] = mapped_column(ForeignKey("importaciones.id"), index=True)
    fecha_valuta: Mapped[date | None] = mapped_column(Date)
    descripcion: Mapped[str] = mapped_column(String(255))
    referencia: Mapped[str | None] = mapped_column(String(120))
    saldo: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    categoria: Mapped[str] = mapped_column(String(20), default="OTRO")
    duplicado_de_id: Mapped[int | None] = mapped_column(ForeignKey("movimientos_banco.id"))


class MovimientoLibro(_MovimientoBase, Base):
    __tablename__ = "movimientos_libro"

    cuenta_bancaria_id: Mapped[int] = mapped_column(ForeignKey("cuentas_bancarias.id"), index=True)
    importacion_id: Mapped[int] = mapped_column(ForeignKey("importaciones.id"), index=True)
    cuenta_contable: Mapped[str | None] = mapped_column(String(12))
    voucher: Mapped[str | None] = mapped_column(String(40))  # CUO / n.º de asiento
    glosa: Mapped[str] = mapped_column(String(255))
    medio_pago: Mapped[str | None] = mapped_column(String(4))  # Tabla 1 SUNAT
    tercero: Mapped[str | None] = mapped_column(String(200))
    debe: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    haber: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    duplicado_de_id: Mapped[int | None] = mapped_column(ForeignKey("movimientos_libro.id"))
