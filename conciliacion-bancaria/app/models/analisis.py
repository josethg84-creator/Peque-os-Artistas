"""Entidades del motor de análisis de cuentas (fase 3).

Principio: el análisis NO modifica ni duplica los movimientos contables. Lee `lineas_diario`,
`saldos_cuenta`, `cuentas_contables`, etc., y guarda únicamente resultados versionados por
ejecución (snapshots de saldos, hallazgos, resultados de origen-destino) y el trabajo del
analista (revisiones, comentarios, papeles de trabajo, adjuntos). Todo está acotado por empresa.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

Importe = Numeric(18, 2)

RIESGOS = ("ALTO", "MEDIO", "BAJO", "INFORMATIVO")
ESTADOS_HALLAZGO = ("PENDIENTE", "EN_REVISION", "CONFIRMADO", "DESCARTADO", "SUBSANADO")
ESTADOS_PAPEL = ("PENDIENTE", "EN_REVISION", "OBSERVADO", "SUBSANADO", "REVISADO", "APROBADO")


class AnalisisEjecucion(Base):
    __tablename__ = "account_analysis_runs"
    __table_args__ = (Index("ix_runs_empresa_periodo", "empresa_id", "ejercicio", "periodo_desde", "periodo_hasta"),
                      CheckConstraint("periodo_desde <= periodo_hasta", name="ck_run_rango"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo_desde: Mapped[int] = mapped_column(Integer)
    periodo_hasta: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(12), default="EN_COLA")  # EN_COLA PROCESANDO COMPLETADO ERROR CANCELADO
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    etapa: Mapped[str | None] = mapped_column(String(120))
    version_datos: Mapped[str] = mapped_column(String(64))     # huella de los lotes usados (invalida caché)
    fuentes: Mapped[str | None] = mapped_column(Text)          # JSON lotes por periodo
    reglas_snapshot: Mapped[str | None] = mapped_column(Text)  # JSON: código → versión y parámetros usados
    grupo_reglas: Mapped[str | None] = mapped_column(String(60))
    resumen: Mapped[str | None] = mapped_column(Text)          # JSON indicadores
    advertencias: Mapped[str | None] = mapped_column(Text)     # JSON
    error: Mapped[str | None] = mapped_column(Text)
    cancelar: Mapped[bool] = mapped_column(Boolean, default=False)
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    tiempos: Mapped[str | None] = mapped_column(Text)          # JSON tiempo por etapa
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime)


class SaldoSnapshot(Base):
    """Saldos de cada nodo del árbol (elemento → analítica) calculados en una ejecución."""
    __tablename__ = "account_balance_snapshots"
    __table_args__ = (UniqueConstraint("run_id", "cuenta"), Index("ix_snap_run_nivel", "run_id", "nivel"))

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("account_analysis_runs.id", ondelete="CASCADE"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    cuenta: Mapped[str] = mapped_column(String(20))
    padre: Mapped[str | None] = mapped_column(String(20))
    nivel: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    naturaleza: Mapped[str | None] = mapped_column(String(1))
    saldo_inicial: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    debe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    haber: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_final: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_anterior: Mapped[Decimal | None] = mapped_column(Importe)  # saldo final del periodo comparable anterior
    movimientos: Mapped[int] = mapped_column(Integer, default=0)
    terceros: Mapped[int] = mapped_column(Integer, default=0)


class AnalisisResultado(Base):
    """Resultado del análisis por cuenta con movimiento: perfil, riesgo e indicadores."""
    __tablename__ = "account_analysis_results"
    __table_args__ = (UniqueConstraint("run_id", "cuenta"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("account_analysis_runs.id", ondelete="CASCADE"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    cuenta: Mapped[str] = mapped_column(String(20))
    perfil: Mapped[str] = mapped_column(String(20))
    hallazgos: Mapped[int] = mapped_column(Integer, default=0)
    riesgo_maximo: Mapped[str | None] = mapped_column(String(12))
    importe_revision: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    indicadores: Mapped[str | None] = mapped_column(Text)  # JSON


class ReglaAnalisis(Base):
    """Regla configurable sin tocar código. `tipo` elige el evaluador; el resto son parámetros."""
    __tablename__ = "account_analysis_rules"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),
                      CheckConstraint("riesgo IN ('ALTO','MEDIO','BAJO','INFORMATIVO')", name="ck_regla_riesgo"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(12))
    nombre: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(30))
    grupo: Mapped[str] = mapped_column(String(60), default="GENERAL")
    cuentas: Mapped[str | None] = mapped_column(String(200))   # prefijos separados por coma
    cuenta_desde: Mapped[str | None] = mapped_column(String(20))
    cuenta_hasta: Mapped[str | None] = mapped_column(String(20))
    condicion: Mapped[str | None] = mapped_column(String(30))
    operador: Mapped[str | None] = mapped_column(String(10))
    valor: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    valor2: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    importe_minimo: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    tolerancia_pct: Mapped[Decimal] = mapped_column(Numeric(9, 4), default=Decimal("0"))
    parametros: Mapped[str | None] = mapped_column(Text)        # JSON adicional (palabras clave, días…)
    riesgo: Mapped[str] = mapped_column(String(12), default="MEDIO")
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    historial: Mapped[str | None] = mapped_column(Text)         # JSON versiones anteriores
    usuario: Mapped[str] = mapped_column(String(80), default="sistema")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Hallazgo(Base):
    __tablename__ = "account_analysis_findings"
    __table_args__ = (Index("ix_hallazgos_run_riesgo", "run_id", "riesgo"), Index("ix_hallazgos_huella", "empresa_id", "huella"),
                      CheckConstraint("estado IN ('PENDIENTE','EN_REVISION','CONFIRMADO','DESCARTADO','SUBSANADO')",
                                      name="ck_hallazgo_estado"))

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("account_analysis_runs.id", ondelete="CASCADE"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    regla_id: Mapped[int | None] = mapped_column(ForeignKey("account_analysis_rules.id", ondelete="SET NULL"))
    regla_codigo: Mapped[str] = mapped_column(String(12))
    regla_version: Mapped[int] = mapped_column(Integer)
    regla_nombre: Mapped[str] = mapped_column(String(160))
    cuenta: Mapped[str] = mapped_column(String(20), index=True)
    tercero: Mapped[str | None] = mapped_column(String(20))
    documento: Mapped[str | None] = mapped_column(String(80))
    asiento: Mapped[str | None] = mapped_column(String(80))
    linea_id: Mapped[int | None] = mapped_column(Integer)  # referencia blanda: la línea puede pertenecer a un lote anulado
    periodo: Mapped[int | None] = mapped_column(Integer)
    importe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    clave_exposicion: Mapped[str] = mapped_column(String(160))  # evita sumar dos veces la misma exposición
    riesgo: Mapped[str] = mapped_column(String(12))
    titulo: Mapped[str] = mapped_column(String(255))
    evidencia: Mapped[str | None] = mapped_column(Text)        # JSON
    explicacion: Mapped[str | None] = mapped_column(Text)
    recomendacion: Mapped[str | None] = mapped_column(Text)
    huella: Mapped[str] = mapped_column(String(64))            # identifica el mismo hallazgo entre ejecuciones
    estado: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    responsable: Mapped[str | None] = mapped_column(String(80))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ExcepcionAnalisis(Base):
    """Excepción autorizada: suprime hallazgos de una regla para una cuenta/tercero/documento."""
    __tablename__ = "account_analysis_exceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    regla_id: Mapped[int | None] = mapped_column(ForeignKey("account_analysis_rules.id", ondelete="CASCADE"))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    tercero: Mapped[str | None] = mapped_column(String(20))
    documento: Mapped[str | None] = mapped_column(String(80))
    motivo: Mapped[str] = mapped_column(String(255))
    autorizado_por: Mapped[str] = mapped_column(String(80))
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ComentarioAnalisis(Base):
    __tablename__ = "account_analysis_comments"
    __table_args__ = (CheckConstraint("hallazgo_id IS NOT NULL OR papel_id IS NOT NULL", name="ck_comentario_destino"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    hallazgo_id: Mapped[int | None] = mapped_column(ForeignKey("account_analysis_findings.id", ondelete="CASCADE"), index=True)
    papel_id: Mapped[int | None] = mapped_column(ForeignKey("accounting_workpapers.id", ondelete="CASCADE"), index=True)
    huella_hallazgo: Mapped[str | None] = mapped_column(String(64))  # el comentario sigue al hallazgo entre ejecuciones
    usuario: Mapped[str] = mapped_column(String(80))
    texto: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RevisionAnalisis(Base):
    """Historial de cambios de estado (hallazgos y papeles de trabajo)."""
    __tablename__ = "account_analysis_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    entidad: Mapped[str] = mapped_column(String(12))  # HALLAZGO | PAPEL
    entidad_id: Mapped[int] = mapped_column(Integer, index=True)
    estado_anterior: Mapped[str | None] = mapped_column(String(12))
    estado_nuevo: Mapped[str] = mapped_column(String(12))
    responsable: Mapped[str | None] = mapped_column(String(80))
    comentario: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdjuntoAnalisis(Base):
    __tablename__ = "account_analysis_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    papel_id: Mapped[int | None] = mapped_column(ForeignKey("accounting_workpapers.id", ondelete="CASCADE"), index=True)
    hallazgo_id: Mapped[int | None] = mapped_column(ForeignKey("account_analysis_findings.id", ondelete="SET NULL"))
    nombre: Mapped[str] = mapped_column(String(255))
    tipo_contenido: Mapped[str | None] = mapped_column(String(120))
    tamano: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(64))
    ruta: Mapped[str] = mapped_column(String(255))
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReglaDistribucion(Base):
    """Regla de distribución origen → destino (cuenta, centro de costo, proyecto, unidad, maquinaria, %)."""
    __tablename__ = "destination_mapping_rules"
    __table_args__ = (CheckConstraint("porcentaje >= 0 AND porcentaje <= 100", name="ck_distribucion_pct"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    nombre: Mapped[str | None] = mapped_column(String(160))
    cuenta_origen: Mapped[str] = mapped_column(String(20))       # prefijo
    centro_costo: Mapped[str | None] = mapped_column(String(30))
    proyecto: Mapped[str | None] = mapped_column(String(40))
    unidad_negocio: Mapped[str | None] = mapped_column(String(60))
    maquinaria: Mapped[str | None] = mapped_column(String(40))
    cuenta_destino: Mapped[str | None] = mapped_column(String(20))  # vacío si la regla excluye
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("100"))
    excluir: Mapped[bool] = mapped_column(Boolean, default=False)  # cuenta excluida de la distribución
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    usuario: Mapped[str] = mapped_column(String(80), default="sistema")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ResultadoDestino(Base):
    __tablename__ = "destination_analysis_results"
    __table_args__ = (Index("ix_destino_run", "run_id", "tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("account_analysis_runs.id", ondelete="CASCADE"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))  # RESUMEN | CENTRO_COSTO | DESTINO | ORIGEN | ASIENTO
    periodo: Mapped[int | None] = mapped_column(Integer)
    clave: Mapped[str] = mapped_column(String(120))  # cuenta, centro de costo o asiento
    descripcion: Mapped[str | None] = mapped_column(String(255))
    origen: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    destino_esperado: Mapped[Decimal | None] = mapped_column(Importe)
    destino: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    cargas_imputables: Mapped[Decimal | None] = mapped_column(Importe)
    diferencia: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    estado: Mapped[str] = mapped_column(String(20))  # CONFORME | DIFERENCIA | SIN_DESTINO | EXCLUIDA | DESTINO_DUPLICADO …


class ConfiguracionAntiguedad(Base):
    __tablename__ = "aging_configurations"
    __table_args__ = (UniqueConstraint("empresa_id", "nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    rangos: Mapped[str] = mapped_column(Text)  # JSON [[1,30],[31,60],…,[366,null]]
    base: Mapped[str] = mapped_column(String(12), default="VENCIMIENTO")  # VENCIMIENTO | EMISION
    cuentas: Mapped[str] = mapped_column(String(200), default="12,13,14,16,17,42,43,44,46,47")
    dias_saldo_antiguo: Mapped[int] = mapped_column(Integer, default=365)
    predeterminada: Mapped[bool] = mapped_column(Boolean, default=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PapelTrabajo(Base):
    """Hoja de análisis preliminar por cuenta. Congela los saldos del análisis que la generó."""
    __tablename__ = "accounting_workpapers"
    __table_args__ = (UniqueConstraint("empresa_id", "ejercicio", "periodo_desde", "periodo_hasta", "cuenta"),
                      CheckConstraint("estado IN ('PENDIENTE','EN_REVISION','OBSERVADO','SUBSANADO','REVISADO','APROBADO')",
                                      name="ck_papel_estado"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("account_analysis_runs.id", ondelete="SET NULL"))
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo_desde: Mapped[int] = mapped_column(Integer)
    periodo_hasta: Mapped[int] = mapped_column(Integer)
    cuenta: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str | None] = mapped_column(String(255))
    saldo_inicial: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    debe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    haber: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_final: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    composicion: Mapped[str | None] = mapped_column(Text)  # JSON composición preliminar
    hallazgos: Mapped[str | None] = mapped_column(Text)    # JSON resumen de hallazgos vinculados
    comentarios_analista: Mapped[str | None] = mapped_column(Text)
    documentos_sustento: Mapped[str | None] = mapped_column(Text)
    conclusion: Mapped[str | None] = mapped_column(Text)
    responsable: Mapped[str | None] = mapped_column(String(80))
    fecha_revision: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    version: Mapped[int] = mapped_column(Integer, default=1)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditoriaAnalisis(Base):
    __tablename__ = "analysis_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    usuario: Mapped[str] = mapped_column(String(80))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(Text)
