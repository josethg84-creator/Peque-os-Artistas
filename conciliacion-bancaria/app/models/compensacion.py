"""Entidades del motor de compensación de partidas (fase 4).

La compensación es ANALÍTICA: relaciona movimientos deudores y acreedores para conocer la
composición real de los saldos; nunca modifica `lineas_diario`. No es la compensación legal de
activos y pasivos para presentación financiera (NIC 32), que no se realiza aquí.

Integridad:
  * `open_items.importe_comprometido` (propuesto + aprobado) nunca supera `importe`: se actualiza
    con un UPDATE condicional y un número de versión (control optimista de concurrencia).
  * Un índice único parcial impide dos aplicaciones vigentes entre el mismo par de partidas.
  * Nada se borra: rechazos y reversiones cambian el estado y dejan registro.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint, func, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

Importe = Numeric(18, 2)
Tasa = Numeric(12, 6)

CLASES = ("FACTURA", "BOLETA", "RECIBO_HONORARIOS", "NOTA_CREDITO", "NOTA_DEBITO", "PAGO", "COBRANZA", "ANTICIPO",
          "ENTREGA_RENDIR", "RENDICION", "PRESTAMO", "AMORTIZACION", "DETRACCION", "RETENCION", "PERCEPCION",
          "DIFERENCIA_CAMBIO", "RECLASIFICACION", "EXTORNO", "SALDO_INICIAL", "OTRO")
ROLES = ("ADMINISTRADOR", "CONTADOR", "ANALISTA", "AUDITOR", "SUPERVISOR", "CONSULTA", "TESORERO", "PLANILLAS")


class PartidaAbierta(Base):
    """Partida (documento o movimiento) de una cuenta sujeta a compensación."""
    __tablename__ = "open_items"
    __table_args__ = (
        UniqueConstraint("empresa_id", "clave_fuente"),
        Index("ix_items_particion", "empresa_id", "cuenta", "tercero", "moneda"),
        Index("ix_items_documento", "empresa_id", "serie", "numero"),
        CheckConstraint("importe > 0", name="ck_item_importe_positivo"),
        CheckConstraint("importe_comprometido >= 0 AND importe_comprometido <= importe", name="ck_item_comprometido"),
        CheckConstraint("importe_aplicado >= 0 AND importe_aplicado <= importe_comprometido", name="ck_item_aplicado"),
        CheckConstraint("rol IN ('ORIGEN','APLICACION')", name="ck_item_rol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    clave_fuente: Mapped[str] = mapped_column(String(80))        # estable entre ejecuciones (idempotencia)
    origen_datos: Mapped[str] = mapped_column(String(20))        # DIARIO | APERTURA_DETALLE | APERTURA_CONSOLIDADA
    cuenta: Mapped[str] = mapped_column(String(20))
    tercero: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(255))
    tipo_documento: Mapped[str | None] = mapped_column(String(4))
    serie: Mapped[str | None] = mapped_column(String(20))
    numero: Mapped[str | None] = mapped_column(String(30))
    documento_referencia: Mapped[str | None] = mapped_column(String(60))
    orden_compra_servicio: Mapped[str | None] = mapped_column(String(40))
    proyecto: Mapped[str | None] = mapped_column(String(40))
    centro_costo: Mapped[str | None] = mapped_column(String(30))
    glosa: Mapped[str | None] = mapped_column(String(255))
    subdiario: Mapped[str | None] = mapped_column(String(20))
    numero_asiento: Mapped[str | None] = mapped_column(String(40))
    lote_id: Mapped[int | None] = mapped_column(Integer)
    linea_id: Mapped[int | None] = mapped_column(Integer)        # primera línea (navegación al asiento)
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int | None] = mapped_column(Integer)
    fecha_documento: Mapped[date] = mapped_column(Date, index=True)  # emisión o, en su defecto, contable
    fecha_contable: Mapped[date | None] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    lado: Mapped[str] = mapped_column(String(1))                 # D | H (en el libro)
    rol: Mapped[str] = mapped_column(String(10))                 # ORIGEN (genera saldo) | APLICACION (lo cancela)
    clase: Mapped[str] = mapped_column(String(20))
    clase_confianza: Mapped[int] = mapped_column(Integer, default=100)
    clase_motivo: Mapped[str | None] = mapped_column(String(255))
    clasificacion_pendiente: Mapped[bool] = mapped_column(Boolean, default=False)
    moneda: Mapped[str] = mapped_column(String(3))
    tipo_cambio: Mapped[Decimal | None] = mapped_column(Tasa)
    importe: Mapped[Decimal] = mapped_column(Importe)            # en la moneda de la partida
    importe_mn: Mapped[Decimal] = mapped_column(Importe)
    importe_original: Mapped[Decimal | None] = mapped_column(Importe)  # para aperturas con detalle
    importe_comprometido: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    importe_aplicado: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    codigo_detraccion: Mapped[str | None] = mapped_column(String(10))
    constancia_detraccion: Mapped[str | None] = mapped_column(String(30))
    retencion: Mapped[str | None] = mapped_column(String(60))
    referencia_historica: Mapped[str | None] = mapped_column(String(120))
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)  # False si su lote se anuló
    estado_revision: Mapped[str] = mapped_column(String(14), default="NINGUNA")  # NINGUNA OBSERVADO EN_REVISION
    responsable: Mapped[str | None] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer, default=1)      # control optimista
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PartidaFuente(Base):
    """Líneas del libro (o registros de apertura) que componen una partida."""
    __tablename__ = "open_item_sources"
    __table_args__ = (UniqueConstraint("item_id", "tipo_fuente", "fuente_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("open_items.id", ondelete="CASCADE"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo_fuente: Mapped[str] = mapped_column(String(20))  # LINEA_DIARIO | SALDO_CUENTA | DOCUMENTO_REGISTRO
    fuente_id: Mapped[int] = mapped_column(Integer, index=True)
    importe_mn: Mapped[Decimal] = mapped_column(Importe)
    importe_me: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))


class EjecucionCompensacion(Base):
    __tablename__ = "settlement_runs"
    __table_args__ = (Index("ix_srun_clave", "empresa_id", "clave_idempotencia"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    fecha_corte: Mapped[date] = mapped_column(Date)
    ejercicio_inicio: Mapped[int] = mapped_column(Integer)
    cuentas: Mapped[str] = mapped_column(String(200))
    clave_idempotencia: Mapped[str] = mapped_column(String(64))
    version_datos: Mapped[str] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(String(12), default="EN_COLA")
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    etapa: Mapped[str | None] = mapped_column(String(160))
    cancelar: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    reglas_snapshot: Mapped[str | None] = mapped_column(Text)
    resumen: Mapped[str | None] = mapped_column(Text)
    tiempos: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime)


class ReglaCompensacion(Base):
    """CUENTA (configuración por cuenta) · ENTRE_CUENTAS · CONVERSION_MONEDA · DETRACCION · RETENCION · PERCEPCION."""
    __tablename__ = "settlement_rules"
    __table_args__ = (UniqueConstraint("empresa_id", "tipo", "codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    codigo: Mapped[str] = mapped_column(String(40))  # p. ej. prefijo de cuenta «12» o código de detracción «037»
    nombre: Mapped[str] = mapped_column(String(160))
    parametros: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    sustento: Mapped[str | None] = mapped_column(Text)
    autorizado_por: Mapped[str | None] = mapped_column(String(80))
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    historial: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80), default="sistema")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class GrupoCompensacion(Base):
    __tablename__ = "settlement_groups"
    __table_args__ = (Index("ix_sgrupo_estado", "empresa_id", "estado"),
                      CheckConstraint("estado IN ('PROPUESTA','APROBADA','RECHAZADA','REVERTIDA')", name="ck_grupo_estado"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_runs.id", ondelete="SET NULL"), index=True)
    modalidad: Mapped[str] = mapped_column(String(20))  # UNO_A_UNO UNO_A_VARIOS VARIOS_A_UNO VARIOS_A_VARIOS + _PARCIAL
    origen_propuesta: Mapped[str] = mapped_column(String(12))  # AUTOMATICA | MANUAL
    nivel: Mapped[int | None] = mapped_column(Integer)
    regla: Mapped[str] = mapped_column(String(80))
    regla_version: Mapped[int | None] = mapped_column(Integer)
    puntuacion: Mapped[int] = mapped_column(Integer, default=0)
    confianza: Mapped[str] = mapped_column(String(10))
    componentes: Mapped[str | None] = mapped_column(Text)  # JSON desglose de la puntuación
    ambiguo: Mapped[bool] = mapped_column(Boolean, default=False)
    cuenta: Mapped[str] = mapped_column(String(60))
    tercero: Mapped[str | None] = mapped_column(String(80))
    moneda: Mapped[str] = mapped_column(String(3))
    importe: Mapped[Decimal] = mapped_column(Importe)
    fecha_efectiva: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(10), default="PROPUESTA")
    justificacion: Mapped[str | None] = mapped_column(Text)
    propuesto_por: Mapped[str] = mapped_column(String(80))
    aprobado_por: Mapped[str | None] = mapped_column(String(80))
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime)
    entre_cuentas: Mapped[bool] = mapped_column(Boolean, default=False)
    entre_terceros: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Aplicacion(Base):
    __tablename__ = "settlement_allocations"
    __table_args__ = (
        Index("ux_aplicacion_vigente", "origen_item_id", "aplicacion_item_id", unique=True,
              sqlite_where=text("estado IN ('PROPUESTA','APROBADA')"),
              postgresql_where=text("estado IN ('PROPUESTA','APROBADA')")),
        Index("ix_aplic_origen", "origen_item_id", "estado"), Index("ix_aplic_aplicacion", "aplicacion_item_id", "estado"),
        CheckConstraint("importe > 0", name="ck_aplicacion_importe"),
        CheckConstraint("origen_item_id <> aplicacion_item_id", name="ck_aplicacion_distintos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("settlement_groups.id"), index=True)
    origen_item_id: Mapped[int] = mapped_column(ForeignKey("open_items.id"))
    aplicacion_item_id: Mapped[int] = mapped_column(ForeignKey("open_items.id"))
    importe: Mapped[Decimal] = mapped_column(Importe)          # en la moneda de las partidas
    moneda: Mapped[str] = mapped_column(String(3))
    tipo_cambio: Mapped[Decimal | None] = mapped_column(Tasa)  # cuando hay conversión autorizada
    importe_mn_origen: Mapped[Decimal] = mapped_column(Importe)
    importe_mn_aplicacion: Mapped[Decimal] = mapped_column(Importe)
    diferencia_cambio: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    fecha_efectiva: Mapped[date] = mapped_column(Date, index=True)
    regla: Mapped[str] = mapped_column(String(80))
    puntuacion: Mapped[int] = mapped_column(Integer)
    usuario: Mapped[str] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(10))  # PROPUESTA APROBADA RECHAZADA REVERTIDA
    reversion_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_reversals.id"))
    registrado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AprobacionCompensacion(Base):
    __tablename__ = "settlement_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("settlement_groups.id"), index=True)
    accion: Mapped[str] = mapped_column(String(12))  # APROBAR | RECHAZAR | AUTOAPROBAR
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReversionCompensacion(Base):
    __tablename__ = "settlement_reversals"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("settlement_groups.id"), index=True)
    motivo: Mapped[str] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ExcepcionCompensacion(Base):
    """Observaciones del motor (no son errores confirmados): clasificación ambigua, NC sin referencia,
    detracción sin constancia, excedentes, diferencias de cambio por evaluar, saldos sin detalle…"""
    __tablename__ = "settlement_exceptions"
    __table_args__ = (UniqueConstraint("empresa_id", "huella"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_runs.id", ondelete="SET NULL"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("open_items.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_groups.id"))
    codigo: Mapped[str] = mapped_column(String(20), index=True)
    titulo: Mapped[str] = mapped_column(String(255))
    detalle: Mapped[str | None] = mapped_column(Text)
    importe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    huella: Mapped[str] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(String(12), default="ABIERTA")  # ABIERTA EN_REVISION RESUELTA DESCARTADA
    responsable: Mapped[str | None] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CandidatoCompensacion(Base):
    """Coincidencias evaluadas por el motor (incluye las ambiguas que requieren decisión)."""
    __tablename__ = "settlement_candidates"
    __table_args__ = (Index("ix_scand_run", "run_id", "ambiguo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("settlement_runs.id", ondelete="CASCADE"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    nivel: Mapped[int] = mapped_column(Integer)
    origenes: Mapped[str] = mapped_column(Text)       # JSON [{item_id, importe}]
    aplicaciones: Mapped[str] = mapped_column(Text)   # JSON [{item_id, importe}]
    importe: Mapped[Decimal] = mapped_column(Importe)
    puntuacion: Mapped[int] = mapped_column(Integer)
    componentes: Mapped[str] = mapped_column(Text)
    ambiguo: Mapped[bool] = mapped_column(Boolean, default=False)
    alternativas: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[str] = mapped_column(String(14))  # AUTOAPROBADO PROPUESTO REQUIERE_DECISION DESCARTADO RESUELTO
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_groups.id"))
    cuenta: Mapped[str] = mapped_column(String(20))
    tercero: Mapped[str | None] = mapped_column(String(20))
    moneda: Mapped[str] = mapped_column(String(3))


class ComentarioCompensacion(Base):
    __tablename__ = "settlement_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_groups.id"), index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("open_items.id"), index=True)
    excepcion_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_exceptions.id"))
    usuario: Mapped[str] = mapped_column(String(80))
    texto: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdjuntoCompensacion(Base):
    __tablename__ = "settlement_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("settlement_groups.id"), index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("open_items.id"))
    nombre: Mapped[str] = mapped_column(String(255))
    tipo_contenido: Mapped[str | None] = mapped_column(String(120))
    tamano: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(64))
    ruta: Mapped[str] = mapped_column(String(255))
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SnapshotCompensacion(Base):
    """Composición del saldo por partida a la fecha de corte de una ejecución (resultado reproducible)."""
    __tablename__ = "settlement_balance_snapshots"
    __table_args__ = (UniqueConstraint("run_id", "item_id"), Index("ix_ssnap_run_cuenta", "run_id", "cuenta"))

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("settlement_runs.id", ondelete="CASCADE"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("open_items.id"))
    fecha_corte: Mapped[date] = mapped_column(Date)
    cuenta: Mapped[str] = mapped_column(String(20))
    tercero: Mapped[str | None] = mapped_column(String(20))
    rol: Mapped[str] = mapped_column(String(10))
    moneda: Mapped[str] = mapped_column(String(3))
    importe: Mapped[Decimal] = mapped_column(Importe)
    aplicado: Mapped[Decimal] = mapped_column(Importe)
    pendiente: Mapped[Decimal] = mapped_column(Importe)
    pendiente_mn: Mapped[Decimal] = mapped_column(Importe)
    estado_cancelacion: Mapped[str] = mapped_column(String(20))
    estado_vencimiento: Mapped[str] = mapped_column(String(16))
    dias_vencido: Mapped[int | None] = mapped_column(Integer)


class AuditoriaCompensacion(Base):
    __tablename__ = "settlement_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(Text)


class RolUsuario(Base):
    """Rol de un usuario en una empresa. Mientras una empresa no tenga roles asignados, el módulo
    opera en «modo abierto» (todos administradores) y lo advierte en pantalla."""
    __tablename__ = "roles_usuario"
    __table_args__ = (UniqueConstraint("empresa_id", "usuario"),
                      CheckConstraint("rol IN ('ADMINISTRADOR','CONTADOR','ANALISTA','AUDITOR','SUPERVISOR','CONSULTA','TESORERO','PLANILLAS')",
                                      name="ck_rol_valido"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str] = mapped_column(String(20))
    asignado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
