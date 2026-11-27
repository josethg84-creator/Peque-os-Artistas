"""Información contable normalizada importada desde ERP (fase 2).

Todos los importes son NUMERIC (Decimal). Los tipos de cambio usan 6 decimales.
Cada registro guarda el lote de origen, la hoja y la fila del archivo para trazabilidad.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String,
                        Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

Importe = Numeric(18, 2)
TasaCambio = Numeric(12, 6)


class TipoInformacion:
    DIARIO = "DIARIO"
    MAYOR = "MAYOR"
    BALANCE = "BALANCE"
    COMPRAS = "COMPRAS"
    VENTAS = "VENTAS"
    PLAN_CUENTAS = "PLAN_CUENTAS"
    CLIENTES = "CLIENTES"
    PROVEEDORES = "PROVEEDORES"
    CENTROS_COSTO = "CENTROS_COSTO"
    SALDOS_INICIALES = "SALDOS_INICIALES"
    TIPOS_CAMBIO = "TIPOS_CAMBIO"
    CXC = "CXC"
    CXP = "CXP"


class Severidad:
    CRITICO = "CRITICO"
    ALTO = "ALTO"
    MEDIO = "MEDIO"
    INFORMATIVO = "INFORMATIVO"
    ORDEN = {"CRITICO": 0, "ALTO": 1, "MEDIO": 2, "INFORMATIVO": 3}


class LoteContable(Base):
    """Una importación confirmada de información contable."""
    __tablename__ = "lotes_contables"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo_informacion: Mapped[str] = mapped_column(String(20), index=True)
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int | None] = mapped_column(Integer)  # 0 apertura · 1–12 · 13 cierre · None anual
    sistema_origen: Mapped[str] = mapped_column(String(20), default="GENERICO")
    nombre_archivo: Mapped[str] = mapped_column(String(255))
    hoja: Mapped[str | None] = mapped_column(String(120))
    fila_encabezado: Mapped[int] = mapped_column(Integer, default=1)
    hash_archivo: Mapped[str] = mapped_column(String(64), index=True)
    plantilla_id: Mapped[int | None] = mapped_column(ForeignKey("plantillas_importacion.id"))
    mapeo: Mapped[str | None] = mapped_column(Text)       # JSON campo → encabezado
    opciones: Mapped[str | None] = mapped_column(Text)    # JSON separador, formato fecha…
    importacion_completa: Mapped[bool] = mapped_column(Boolean, default=True)
    filas_leidas: Mapped[int] = mapped_column(Integer, default=0)
    filas_vacias: Mapped[int] = mapped_column(Integer, default=0)
    filas_subtotal: Mapped[int] = mapped_column(Integer, default=0)
    registros_importados: Mapped[int] = mapped_column(Integer, default=0)
    registros_excluidos: Mapped[int] = mapped_column(Integer, default=0)
    total_debe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    total_haber: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    total_archivo_debe: Mapped[Decimal | None] = mapped_column(Importe)
    total_archivo_haber: Mapped[Decimal | None] = mapped_column(Importe)
    obs_critico: Mapped[int] = mapped_column(Integer, default=0)
    obs_alto: Mapped[int] = mapped_column(Integer, default=0)
    obs_medio: Mapped[int] = mapped_column(Integer, default=0)
    obs_informativo: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(10), default="ACTIVO")  # ACTIVO | ANULADO
    motivo_criticos: Mapped[str | None] = mapped_column(String(255))
    motivo_anulacion: Mapped[str | None] = mapped_column(String(255))
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlantillaImportacion(Base):
    """Homologación reutilizable por empresa (o global), sistema contable y tipo de archivo."""
    __tablename__ = "plantillas_importacion"
    __table_args__ = (UniqueConstraint("empresa_id", "sistema_origen", "tipo_informacion", "nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), index=True)  # None = global
    sistema_origen: Mapped[str] = mapped_column(String(20))
    tipo_informacion: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(120))
    hoja: Mapped[str | None] = mapped_column(String(120))
    fila_encabezado: Mapped[int] = mapped_column(Integer, default=1)  # 0 = sin encabezado
    mapeo: Mapped[str] = mapped_column(Text)     # JSON {campo: encabezado normalizado | "#n"}
    opciones: Mapped[str | None] = mapped_column(Text)
    usos: Mapped[int] = mapped_column(Integer, default=0)
    usuario: Mapped[str] = mapped_column(String(80))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CuentaContable(Base):
    __tablename__ = "cuentas_contables"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(255))
    nivel: Mapped[int | None] = mapped_column(Integer)
    naturaleza: Mapped[str | None] = mapped_column(String(1))  # D | A
    admite_movimiento: Mapped[bool] = mapped_column(Boolean, default=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    requiere_centro_costo: Mapped[bool] = mapped_column(Boolean, default=False)
    cuenta_destino_debe: Mapped[str | None] = mapped_column(String(20))
    cuenta_destino_haber: Mapped[str | None] = mapped_column(String(20))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes_contables.id"))


class Tercero(Base):
    __tablename__ = "terceros"
    __table_args__ = (UniqueConstraint("empresa_id", "rol", "numero_documento"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    rol: Mapped[str] = mapped_column(String(10))  # CLIENTE | PROVEEDOR
    tipo_documento_identidad: Mapped[str | None] = mapped_column(String(2))  # Tabla 2 SUNAT
    numero_documento: Mapped[str] = mapped_column(String(20))
    razon_social: Mapped[str] = mapped_column(String(255))
    direccion: Mapped[str | None] = mapped_column(String(255))
    estado_contribuyente: Mapped[str | None] = mapped_column(String(30))
    condicion_domicilio: Mapped[str | None] = mapped_column(String(30))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes_contables.id"))


class CentroCosto(Base):
    __tablename__ = "centros_costo"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(30))
    descripcion: Mapped[str] = mapped_column(String(255))
    cuenta_destino: Mapped[str | None] = mapped_column(String(20))
    unidad_negocio: Mapped[str | None] = mapped_column(String(60))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes_contables.id"))


class TipoCambio(Base):
    __tablename__ = "tipos_cambio"
    __table_args__ = (UniqueConstraint("empresa_id", "fecha", "moneda"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3))
    compra: Mapped[Decimal] = mapped_column(TasaCambio)
    venta: Mapped[Decimal] = mapped_column(TasaCambio)
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes_contables.id"))


class LineaDiario(Base):
    """Línea contable normalizada (libro diario o libro mayor)."""
    __tablename__ = "lineas_diario"
    __table_args__ = (
        Index("ix_lineas_asiento", "empresa_id", "ejercicio", "periodo", "subdiario", "numero_asiento"),
        Index("ix_lineas_cuenta", "empresa_id", "ejercicio", "periodo", "cuenta"),
        Index("ix_lineas_documento", "empresa_id", "serie", "numero_documento"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes_contables.id"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int | None] = mapped_column(Integer)
    fecha_contable: Mapped[date | None] = mapped_column(Date)
    fecha_emision: Mapped[date | None] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    subdiario: Mapped[str | None] = mapped_column(String(20))
    numero_asiento: Mapped[str | None] = mapped_column(String(40))
    numero_linea: Mapped[int | None] = mapped_column(Integer)
    cuenta: Mapped[str] = mapped_column(String(20))
    descripcion_cuenta: Mapped[str | None] = mapped_column(String(255))
    glosa: Mapped[str | None] = mapped_column(String(255))
    tipo_documento: Mapped[str | None] = mapped_column(String(4))  # Tabla 10 SUNAT
    serie: Mapped[str | None] = mapped_column(String(20))
    numero_documento: Mapped[str | None] = mapped_column(String(30))
    tipo_documento_identidad: Mapped[str | None] = mapped_column(String(2))
    documento_tercero: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(255))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    tipo_cambio: Mapped[Decimal | None] = mapped_column(TasaCambio)
    debe_mn: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    haber_mn: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    debe_me: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    haber_me: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    centro_costo: Mapped[str | None] = mapped_column(String(30))
    proyecto: Mapped[str | None] = mapped_column(String(40))
    activo_maquinaria: Mapped[str | None] = mapped_column(String(40))
    documento_referencia: Mapped[str | None] = mapped_column(String(60))
    orden_compra_servicio: Mapped[str | None] = mapped_column(String(40))
    codigo_detraccion: Mapped[str | None] = mapped_column(String(10))
    constancia_detraccion: Mapped[str | None] = mapped_column(String(30))
    retencion: Mapped[str | None] = mapped_column(String(60))
    usuario_registro: Mapped[str | None] = mapped_column(String(80))   # fase 7: solo si el ERP lo exporta
    fecha_registro: Mapped[date | None] = mapped_column(Date)
    origen_asiento: Mapped[str | None] = mapped_column(String(20))      # MANUAL | AUTOMATICO | módulo de origen
    hoja: Mapped[str | None] = mapped_column(String(120))
    fila_origen: Mapped[int | None] = mapped_column(Integer)


class DocumentoRegistro(Base):
    """Comprobantes de los registros de compras/ventas y saldos de cuentas por cobrar/pagar."""
    __tablename__ = "documentos_registro"
    __table_args__ = (Index("ix_doc_registro", "empresa_id", "tipo", "serie", "numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes_contables.id"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    tipo: Mapped[str] = mapped_column(String(10))  # COMPRAS | VENTAS | CXC | CXP
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int | None] = mapped_column(Integer)
    cuo: Mapped[str | None] = mapped_column(String(40))
    fecha_emision: Mapped[date | None] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    tipo_documento: Mapped[str | None] = mapped_column(String(4))
    serie: Mapped[str | None] = mapped_column(String(20))
    numero: Mapped[str | None] = mapped_column(String(30))
    tipo_documento_identidad: Mapped[str | None] = mapped_column(String(2))
    documento_tercero: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(255))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    tipo_cambio: Mapped[Decimal | None] = mapped_column(TasaCambio)
    base_imponible: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    igv: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    no_gravado: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    otros_tributos: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    importe_me: Mapped[Decimal | None] = mapped_column(Importe)
    saldo_pendiente: Mapped[Decimal | None] = mapped_column(Importe)
    cuenta: Mapped[str | None] = mapped_column(String(20))
    glosa: Mapped[str | None] = mapped_column(String(255))
    codigo_detraccion: Mapped[str | None] = mapped_column(String(10))
    constancia_detraccion: Mapped[str | None] = mapped_column(String(30))
    retencion: Mapped[str | None] = mapped_column(String(60))
    documento_referencia: Mapped[str | None] = mapped_column(String(60))  # NC/ND: comprobante que modifica (fase 6)
    hoja: Mapped[str | None] = mapped_column(String(120))
    fila_origen: Mapped[int | None] = mapped_column(Integer)


class SaldoCuenta(Base):
    """Filas del balance de comprobación y de los saldos iniciales."""
    __tablename__ = "saldos_cuenta"
    __table_args__ = (Index("ix_saldos", "empresa_id", "tipo", "ejercicio", "periodo", "cuenta"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes_contables.id"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    tipo: Mapped[str] = mapped_column(String(20))  # BALANCE | SALDOS_INICIALES
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int | None] = mapped_column(Integer)
    cuenta: Mapped[str] = mapped_column(String(20))
    descripcion_cuenta: Mapped[str | None] = mapped_column(String(255))
    documento_tercero: Mapped[str | None] = mapped_column(String(20))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    saldo_inicial_debe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_inicial_haber: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    movimiento_debe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    movimiento_haber: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_final_debe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_final_haber: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_me_debe: Mapped[Decimal | None] = mapped_column(Importe)
    saldo_me_haber: Mapped[Decimal | None] = mapped_column(Importe)
    hoja: Mapped[str | None] = mapped_column(String(120))
    fila_origen: Mapped[int | None] = mapped_column(Integer)


class ObservacionImportacion(Base):
    __tablename__ = "observaciones_importacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("lotes_contables.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(10), index=True)
    severidad: Mapped[str] = mapped_column(String(12), index=True)
    archivo: Mapped[str] = mapped_column(String(255))
    hoja: Mapped[str | None] = mapped_column(String(120))
    fila: Mapped[int | None] = mapped_column(Integer)
    cuenta: Mapped[str | None] = mapped_column(String(20))
    asiento: Mapped[str | None] = mapped_column(String(80))
    documento: Mapped[str | None] = mapped_column(String(80))
    campo: Mapped[str | None] = mapped_column(String(40))
    valor: Mapped[str | None] = mapped_column(String(120))
    mensaje: Mapped[str] = mapped_column(String(500))
    recomendacion: Mapped[str | None] = mapped_column(String(500))


class ConfiguracionContable(Base):
    """Tolerancias y políticas contables de cada empresa para el motor de validación."""
    __tablename__ = "configuracion_contable"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), unique=True)
    tolerancia_descuadre: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0.01"))
    materialidad: Mapped[Decimal] = mapped_column(Importe, default=Decimal("100.00"))
    tolerancia_tipo_cambio: Mapped[Decimal] = mapped_column(TasaCambio, default=Decimal("0.005"))
    tolerancia_conversion: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0.05"))
    # Contabilidad analítica (clases 6, 7 y 9)
    usa_clase_9: Mapped[bool] = mapped_column(Boolean, default=True)
    modo_destino: Mapped[str] = mapped_column(String(15), default="MISMO_ASIENTO")  # | PERIODO | NO_APLICA
    prefijos_destinables: Mapped[str] = mapped_column(String(120), default="62,63,64,65,66,67,68")
    prefijo_destino: Mapped[str] = mapped_column(String(60), default="9")
    cuenta_cargas_imputables: Mapped[str] = mapped_column(String(20), default="79")
    exigir_centro_costo_destino: Mapped[bool] = mapped_column(Boolean, default=False)
    validar_cuenta_78: Mapped[bool] = mapped_column(Boolean, default=True)
    prefijos_sin_movimiento: Mapped[str] = mapped_column(String(120), default="")  # p. ej. cuentas título


class ReglaDestino(Base):
    """Regla analítica configurable: cuentas de origen → destino esperado (debe/haber)."""
    __tablename__ = "reglas_destino"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    prefijo_origen: Mapped[str] = mapped_column(String(20))
    destino_debe: Mapped[str] = mapped_column(String(60))   # prefijos separados por coma
    destino_haber: Mapped[str] = mapped_column(String(60))
    requiere_centro_costo: Mapped[bool] = mapped_column(Boolean, default=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    descripcion: Mapped[str | None] = mapped_column(String(200))
