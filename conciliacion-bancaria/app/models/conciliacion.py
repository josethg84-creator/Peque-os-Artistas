"""Fase 6 — Motor universal de conciliaciones.

Una conciliación compara dos o más fuentes (libro, estados bancarios, registros auxiliares, archivos externos,
anexos, otra empresa del grupo…). Las fuentes se «congelan» en registros normalizados con referencia al
origen; las coincidencias, asignaciones y diferencias pertenecen a una VERSIÓN. Nada modifica los asientos
originales; las versiones aprobadas son inmutables y no se eliminan.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

Importe = Numeric(18, 2)
Cantidad = Numeric(18, 4)
TasaCambio = Numeric(12, 6)

ESTADOS_RUN = ("BORRADOR", "EJECUTADA", "EN_REVISION", "OBSERVADA", "REVISADA", "APROBADA", "CERRADA", "REABIERTA")
ESTADOS_PROCESO = ("PENDIENTE", "EN_COLA", "PROCESANDO", "COMPLETADO", "CANCELADO", "ERROR")
TIPOS_GRUPO = ("EXACTA", "TOLERANCIA", "PARCIAL", "AMBIGUA", "DIFERENCIA", "AGREGADO", "MANUAL")
ESTADOS_GRUPO = ("PROPUESTA", "CONFIRMADA", "AMBIGUA", "RECHAZADA", "REVERTIDA")
CLASIFICACIONES = ("REGISTRO_FALTANTE_CONTABILIDAD", "REGISTRO_FALTANTE_FUENTE_EXTERNA", "DIFERENCIA_MONETARIA",
                   "DIFERENCIA_TEMPORAL", "DIFERENCIA_TIPO_CAMBIO", "DIFERENCIA_CLASIFICACION", "DOCUMENTO_DUPLICADO",
                   "DOCUMENTO_PENDIENTE_SUSTENTO", "DIFERENCIA_CORTE", "DIFERENCIA_PARAMETRIZACION", "DIFERENCIA_NO_IDENTIFICADA",
                   "COINCIDENCIA_AMBIGUA")
PRIORIDADES = ("CRITICO", "ALTO", "MEDIO", "BAJO", "INFORMATIVO")
ESTADOS_DIFERENCIA = ("DETECTADO", "PENDIENTE_REVISION", "EN_ANALISIS", "JUSTIFICADO", "PENDIENTE_REGULARIZACION", "SUBSANADO",
                      "APROBADO", "CERRADO", "REABIERTO")
ROLES_FUENTE = ("CONTABLE", "EXTERNA", "AUXILIAR_INTERNO")


def _l(v):
    return ", ".join(f"'{x}'" for x in v)


class TipoConciliacion(Base):
    __tablename__ = "reconciliation_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(30))
    especializado: Mapped[bool] = mapped_column(Boolean, default=True)
    roles_operacion: Mapped[str | None] = mapped_column(String(200))  # roles adicionales que pueden operarla
    datos_personales: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class PlantillaConciliacion(Base):
    __tablename__ = "reconciliation_templates"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_rec_template_codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo_codigo: Mapped[str] = mapped_column(String(30))
    codigo: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str | None] = mapped_column(Text)
    configuracion: Mapped[str] = mapped_column(Text)  # JSON: fuentes, pasadas, duplicados, criterios de aprobación
    personalizada: Mapped[bool] = mapped_column(Boolean, default=False)
    autorizada: Mapped[bool] = mapped_column(Boolean, default=True)
    autorizada_por: Mapped[str | None] = mapped_column(String(80))
    compartida: Mapped[bool] = mapped_column(Boolean, default=True)
    base_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_templates.id"))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    creado_por: Mapped[str] = mapped_column(String(80), default="sistema")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ReglaConciliacion(Base):
    __tablename__ = "reconciliation_rules"
    __table_args__ = (CheckConstraint("tipo IN ('CLAVE', 'IMPORTE_FECHA', 'COMBINACION', 'AGREGADO', 'EXCLUSION', 'CLASIFICACION')",
                                      name="ck_rec_rule_tipo"),
                      Index("ix_rec_rule_plantilla", "plantilla_id", "pasada", "orden"))

    id: Mapped[int] = mapped_column(primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_templates.id", ondelete="CASCADE"))
    pasada: Mapped[int] = mapped_column(Integer, default=0)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    codigo: Mapped[str] = mapped_column(String(40))
    descripcion: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(15))
    parametros: Mapped[str] = mapped_column(Text, default="{}")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class ToleranciaConciliacion(Base):
    """Tolerancia por empresa, tipo de conciliación, cuenta y moneda (gana la más específica)."""
    __tablename__ = "reconciliation_tolerances"
    __table_args__ = (CheckConstraint("importe_absoluto >= 0 AND (porcentaje IS NULL OR porcentaje >= 0) AND dias >= 0",
                                      name="ck_rec_tolerance_positiva"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo_codigo: Mapped[str | None] = mapped_column(String(30))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    moneda: Mapped[str | None] = mapped_column(String(3))
    importe_absoluto: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    porcentaje: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    dias: Mapped[int] = mapped_column(Integer, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Conciliacion(Base):
    """La conciliación (una por ámbito y fecha de corte). Cada ejecución genera una versión."""
    __tablename__ = "reconciliation_runs"
    __table_args__ = (CheckConstraint(f"estado IN ({_l(ESTADOS_RUN)})", name="ck_rec_run_estado"),
                      CheckConstraint(f"estado_proceso IN ({_l(ESTADOS_PROCESO)})", name="ck_rec_run_proceso"),
                      Index("ix_rec_run_ambito", "empresa_id", "ambito_clave", "fecha_corte"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_templates.id"))
    tipo_codigo: Mapped[str] = mapped_column(String(30))
    nombre: Mapped[str] = mapped_column(String(200))
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int] = mapped_column(Integer)
    fecha_corte: Mapped[date] = mapped_column(Date)
    ambito: Mapped[str] = mapped_column(Text, default="{}")  # cuenta, cuenta bancaria, moneda, CC, proyecto, empresa relacionada
    ambito_clave: Mapped[str] = mapped_column(String(64))   # continuidad mensual
    responsable: Mapped[str | None] = mapped_column(String(80))
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(12), default="BORRADOR")
    estado_proceso: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    etapa: Mapped[str | None] = mapped_column(String(160))
    cancelar: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    clave_idempotencia: Mapped[str | None] = mapped_column(String(64))
    version_actual: Mapped[int] = mapped_column(Integer, default=0)
    version_id: Mapped[int | None] = mapped_column(Integer)
    resumen: Mapped[str | None] = mapped_column(Text)
    tiempos: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    creado_por: Mapped[str] = mapped_column(String(80))
    ejecutado_por: Mapped[str | None] = mapped_column(String(80))
    revisado_por: Mapped[str | None] = mapped_column(String(80))
    aprobado_por: Mapped[str | None] = mapped_column(String(80))
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime)
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime)
    lock_version: Mapped[int] = mapped_column(Integer, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class FuenteConciliacion(Base):
    __tablename__ = "reconciliation_sources"
    __table_args__ = (CheckConstraint(f"rol IN ({_l(ROLES_FUENTE)})", name="ck_rec_source_rol"),
                      Index("ix_rec_source_run", "run_id", "lado", "vigente"))

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    lado: Mapped[str] = mapped_column(String(1))      # A | B | C
    rol: Mapped[str] = mapped_column(String(16))
    tipo_fuente: Mapped[str] = mapped_column(String(24))
    nombre: Mapped[str] = mapped_column(String(200))
    parametros: Mapped[str] = mapped_column(Text, default="{}")
    esquema: Mapped[str | None] = mapped_column(String(30))
    nombre_archivo: Mapped[str | None] = mapped_column(String(255))
    hash_archivo: Mapped[str | None] = mapped_column(String(64))
    ruta_archivo: Mapped[str | None] = mapped_column(String(400))
    mapeo_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_column_mappings.id"))
    version_datos: Mapped[str | None] = mapped_column(String(64))
    registros: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo: Mapped[Decimal | None] = mapped_column(Importe)   # saldo informado por la fuente (p. ej. estado bancario)
    observaciones: Mapped[str | None] = mapped_column(Text)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RegistroFuente(Base):
    """Registro normalizado de una fuente, con referencia verificable a su origen (tabla e id, o archivo y fila)."""
    __tablename__ = "reconciliation_source_records"
    __table_args__ = (Index("ix_rec_record_fuente", "fuente_id", "orden"), Index("ix_rec_record_run", "run_id", "lado"))

    id: Mapped[int] = mapped_column(primary_key=True)
    fuente_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_sources.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"))
    lado: Mapped[str] = mapped_column(String(1))
    orden: Mapped[int] = mapped_column(Integer)
    clave_registro: Mapped[str] = mapped_column(String(160))   # identidad estable entre periodos
    origen_tabla: Mapped[str | None] = mapped_column(String(40))
    origen_id: Mapped[int | None] = mapped_column(Integer)
    fila_origen: Mapped[int | None] = mapped_column(Integer)
    fecha: Mapped[date | None] = mapped_column(Date)
    fecha_valor: Mapped[date | None] = mapped_column(Date)
    periodo: Mapped[int | None] = mapped_column(Integer)       # AAAAMM
    tipo_documento: Mapped[str | None] = mapped_column(String(4))
    serie: Mapped[str | None] = mapped_column(String(20))
    numero: Mapped[str | None] = mapped_column(String(40))
    tercero: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(255))
    referencia: Mapped[str | None] = mapped_column(String(120))
    operacion: Mapped[str | None] = mapped_column(String(60))
    descripcion: Mapped[str | None] = mapped_column(String(255))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    centro_costo: Mapped[str | None] = mapped_column(String(30))
    proyecto: Mapped[str | None] = mapped_column(String(40))
    concepto: Mapped[str | None] = mapped_column(String(60))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    tipo_cambio: Mapped[Decimal | None] = mapped_column(TasaCambio)
    importe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    importe_me: Mapped[Decimal | None] = mapped_column(Importe)
    cantidad: Mapped[Decimal | None] = mapped_column(Cantidad)
    datos: Mapped[str | None] = mapped_column(Text)
    personal: Mapped[bool] = mapped_column(Boolean, default=False)
    excluido: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_exclusion: Mapped[str | None] = mapped_column(String(255))


class MapeoColumnas(Base):
    """Homologación de columnas guardada (fase 2) para un esquema de fuente: perfiles bancarios, planillas, kardex…"""
    __tablename__ = "reconciliation_column_mappings"
    __table_args__ = (UniqueConstraint("empresa_id", "esquema", "nombre", name="uq_rec_mapping"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    esquema: Mapped[str] = mapped_column(String(30))
    nombre: Mapped[str] = mapped_column(String(120))
    ambito: Mapped[str | None] = mapped_column(String(80))  # p. ej. «BANCO:3» (cuenta bancaria) o un tipo de conciliación
    mapeo: Mapped[str] = mapped_column(Text)               # {campo: encabezado normalizado | "#n"}
    opciones: Mapped[str | None] = mapped_column(Text)
    fila_encabezado: Mapped[int] = mapped_column(Integer, default=1)
    usos: Mapped[int] = mapped_column(Integer, default=0)
    creado_por: Mapped[str] = mapped_column(String(80))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VersionConciliacion(Base):
    __tablename__ = "reconciliation_versions"
    __table_args__ = (UniqueConstraint("run_id", "numero", name="uq_rec_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    numero: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str | None] = mapped_column(String(255))
    configuracion: Mapped[str] = mapped_column(Text)   # plantilla, reglas y tolerancias usadas
    fuentes: Mapped[str] = mapped_column(Text)         # fuentes, archivos y versiones de datos
    resumen: Mapped[str] = mapped_column(Text)
    reporte: Mapped[str | None] = mapped_column(Text)  # p. ej. reporte de conciliación bancaria
    hash_contenido: Mapped[str] = mapped_column(String(64))
    inmutable: Mapped[bool] = mapped_column(Boolean, default=False)
    estado_al_cerrar: Mapped[str | None] = mapped_column(String(12))
    generado_por: Mapped[str] = mapped_column(String(80))
    generado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GrupoConciliacion(Base):
    __tablename__ = "reconciliation_match_groups"
    __table_args__ = (CheckConstraint(f"tipo IN ({_l(TIPOS_GRUPO)})", name="ck_rec_group_tipo"),
                      CheckConstraint(f"estado IN ({_l(ESTADOS_GRUPO)})", name="ck_rec_group_estado"),
                      Index("ix_rec_group_version", "version_id", "estado"))

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"))
    version_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_versions.id"))
    pasada: Mapped[str] = mapped_column(String(5))        # «A-B»
    tipo: Mapped[str] = mapped_column(String(12))
    modalidad: Mapped[str] = mapped_column(String(5))     # 1:1 · 1:N · N:1 · N:N
    nivel: Mapped[int] = mapped_column(Integer, default=0)
    regla: Mapped[str | None] = mapped_column(String(80))
    clave: Mapped[str | None] = mapped_column(String(200))
    puntuacion: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(12), default="PROPUESTA")
    origen: Mapped[str] = mapped_column(String(10), default="AUTOMATICO")
    importe_a: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    importe_b: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    diferencia: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    dias: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(Text)     # diferencias por campo, alternativas
    huellas: Mapped[str | None] = mapped_column(Text)     # claves de registro (para re-aplicar decisiones manuales)
    justificacion: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80), default="motor")
    confirmado_por: Mapped[str | None] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MatchConciliacion(Base):
    __tablename__ = "reconciliation_matches"
    __table_args__ = (Index("ix_rec_match_grupo", "grupo_id"), Index("ix_rec_match_registro", "registro_id"),
                      CheckConstraint("importe >= 0", name="ck_rec_match_importe"))

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_match_groups.id"))
    registro_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_source_records.id"))
    lado: Mapped[str] = mapped_column(String(1))
    importe: Mapped[Decimal] = mapped_column(Importe)    # parte del registro asignada (valor absoluto)


class AsignacionRegistro(Base):
    """Estado de cada registro en una versión y pasada: conciliado, parcial o pendiente (control de sobreasignación)."""
    __tablename__ = "reconciliation_allocations"
    __table_args__ = (UniqueConstraint("version_id", "registro_id", "pasada", name="uq_rec_allocation"),
                      CheckConstraint("conciliado >= 0 AND conciliado <= total", name="ck_rec_allocation_limite"),
                      Index("ix_rec_allocation_estado", "version_id", "estado"))

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_versions.id"))
    registro_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_source_records.id"))
    pasada: Mapped[str] = mapped_column(String(5))
    lado: Mapped[str] = mapped_column(String(1))
    total: Mapped[Decimal] = mapped_column(Importe)        # valor absoluto del registro
    conciliado: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    estado: Mapped[str] = mapped_column(String(12), default="PENDIENTE")  # CONCILIADO | PARCIAL | PENDIENTE | EXCLUIDO | DUPLICADO | AMBIGUO
    lock: Mapped[int] = mapped_column(Integer, default=0)


class DiferenciaConciliacion(Base):
    __tablename__ = "reconciliation_differences"
    __table_args__ = (CheckConstraint(f"clasificacion IN ({_l(CLASIFICACIONES)})", name="ck_rec_diff_clasificacion"),
                      CheckConstraint(f"prioridad IN ({_l(PRIORIDADES)})", name="ck_rec_diff_prioridad"),
                      CheckConstraint(f"estado IN ({_l(ESTADOS_DIFERENCIA)})", name="ck_rec_diff_estado"),
                      Index("ix_rec_diff_run", "run_id", "version_id"), Index("ix_rec_diff_huella", "empresa_id", "huella"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"))
    version_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_versions.id"))
    codigo: Mapped[str] = mapped_column(String(30))
    tipo_conciliacion: Mapped[str] = mapped_column(String(30))
    clasificacion: Mapped[str] = mapped_column(String(34))
    subtipo: Mapped[str | None] = mapped_column(String(50))
    prioridad: Mapped[str] = mapped_column(String(12))
    fuente: Mapped[str | None] = mapped_column(String(60))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    documento: Mapped[str | None] = mapped_column(String(80))
    tercero: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(255))
    importe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    fecha: Mapped[date | None] = mapped_column(Date)
    evidencia: Mapped[str | None] = mapped_column(Text)   # registros, grupo, valores comparados
    regla: Mapped[str | None] = mapped_column(String(80))
    explicacion: Mapped[str] = mapped_column(Text)
    recomendacion: Mapped[str | None] = mapped_column(Text)
    dentro_tolerancia: Mapped[bool] = mapped_column(Boolean, default=False)
    responsable: Mapped[str | None] = mapped_column(String(80))
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(26), default="DETECTADO")
    causa: Mapped[str | None] = mapped_column(String(255))
    accion_correctiva: Mapped[str | None] = mapped_column(Text)
    huella: Mapped[str] = mapped_column(String(64))
    origen_id: Mapped[int | None] = mapped_column(Integer)        # primera detección (continuidad mensual)
    anterior_id: Mapped[int | None] = mapped_column(Integer)      # incidencia del periodo anterior
    periodo_origen: Mapped[int | None] = mapped_column(Integer)   # AAAAMM
    fecha_deteccion: Mapped[date] = mapped_column(Date)
    importe_original: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    importe_pendiente: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    recurrencias: Mapped[int] = mapped_column(Integer, default=0)
    trasladada: Mapped[bool] = mapped_column(Boolean, default=False)
    personal: Mapped[bool] = mapped_column(Boolean, default=False)
    lock_version: Mapped[int] = mapped_column(Integer, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RevisionConciliacion(Base):
    __tablename__ = "reconciliation_reviews"
    __table_args__ = (Index("ix_rec_review_entidad", "entidad", "entidad_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"))
    entidad: Mapped[str] = mapped_column(String(12))   # CONCILIACION | DIFERENCIA | GRUPO
    entidad_id: Mapped[int] = mapped_column(Integer)
    de_estado: Mapped[str | None] = mapped_column(String(26))
    a_estado: Mapped[str | None] = mapped_column(String(26))
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    cambios: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AprobacionConciliacion(Base):
    __tablename__ = "reconciliation_approvals"
    __table_args__ = (CheckConstraint("accion IN ('REVISAR', 'APROBAR', 'CERRAR', 'REABRIR')", name="ck_rec_approval_accion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_versions.id"))
    accion: Mapped[str] = mapped_column(String(10))
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReversionConciliacion(Base):
    __tablename__ = "reconciliation_reversals"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_versions.id"))
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_match_groups.id"))
    alcance: Mapped[str] = mapped_column(String(12))   # COINCIDENCIA | CONCILIACION
    motivo: Mapped[str] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdjuntoConciliacion(Base):
    __tablename__ = "reconciliation_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_runs.id"))
    diferencia_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_differences.id"))
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_match_groups.id"))
    registro_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_source_records.id"))
    categoria: Mapped[str] = mapped_column(String(30), default="OTRO")
    descripcion: Mapped[str | None] = mapped_column(String(255))
    nombre: Mapped[str] = mapped_column(String(255))
    tipo_contenido: Mapped[str | None] = mapped_column(String(100))
    tamano: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(64))
    ruta: Mapped[str] = mapped_column(String(400))
    confidencial: Mapped[bool] = mapped_column(Boolean, default=False)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AsignacionConciliacion(Base):
    """Responsables, programación y autorizaciones (p. ej. grupo económico para conciliaciones intercompañías)."""
    __tablename__ = "reconciliation_assignments"
    __table_args__ = (CheckConstraint("tipo IN ('ELABORACION', 'REVISION', 'APROBACION', 'PROGRAMADA', 'GRUPO_ECONOMICO')",
                                      name="ck_rec_assignment_tipo"),
                      Index("ix_rec_assignment", "empresa_id", "tipo", "activa"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    tipo: Mapped[str] = mapped_column(String(16))
    tipo_conciliacion: Mapped[str | None] = mapped_column(String(30))
    plantilla_id: Mapped[int | None] = mapped_column(ForeignKey("reconciliation_templates.id"))
    ambito: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str | None] = mapped_column(String(80))
    empresa_relacionada_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"))
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    dia_programado: Mapped[int | None] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    asignado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditoriaConciliacion(Base):
    __tablename__ = "reconciliation_audit_logs"
    __table_args__ = (Index("ix_rec_audit_empresa", "empresa_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(30))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    run_id: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(Text)
