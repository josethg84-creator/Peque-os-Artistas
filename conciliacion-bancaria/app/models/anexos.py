"""Fase 5 — Generador de anexos contables.

Los anexos se calculan a partir de las líneas del libro (fase 2), los saldos y el análisis (fase 3) y las
compensaciones aprobadas (fase 4). Nunca modifican los asientos originales. Cada generación produce
una VERSIÓN con su detalle; las versiones aprobadas son inmutables y ninguna versión se elimina.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

Importe = Numeric(18, 2)
TasaCambio = Numeric(12, 6)

ESTADOS_REVISION = ("PENDIENTE_GENERACION", "GENERADO", "EN_ELABORACION", "EN_REVISION", "OBSERVADO", "SUBSANADO",
                    "REVISADO", "APROBADO", "CERRADO", "REABIERTO")
RESULTADOS_CONCILIACION = ("CUADRADO", "CUADRADO_CON_OBSERVACIONES", "PARCIALMENTE_SUSTENTADO", "DESCUADRADO",
                           "INFORMACION_INSUFICIENTE")
ESTADOS_SUSTENTO = ("DOCUMENTADO", "SIN_DOCUMENTO", "SIN_DETALLE", "POR_CLASIFICAR")
TIPOS_REGISTRO = ("ACTIVO_FIJO", "CONTRATO_FINANCIERO", "CUOTA_FINANCIERA", "GASTO_ANTICIPADO", "SERVICIO_PROCESO",
                  "INVENTARIO")
CATEGORIAS_ADJUNTO = ("FACTURA", "CONTRATO", "ESTADO_BANCARIO", "CONSTANCIA_DETRACCION", "COMPROBANTE_RETENCION",
                      "CRONOGRAMA_FINANCIERO", "VALORIZACION", "ORDEN_SERVICIO", "INFORME_TECNICO", "LIQUIDACION",
                      "DECLARACION_TRIBUTARIA", "ACTA", "ARQUEO", "OTRO")


def _lista(valores):
    return ", ".join(f"'{v}'" for v in valores)


# ------------------------------------------------------------------ plantillas
class PlantillaAnexo(Base):
    """Plantilla del catálogo (empresa_id NULL) o propia de la empresa (personalizada o duplicada)."""
    __tablename__ = "annex_templates"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_annex_template_codigo"),
                      CheckConstraint("tipo IN ('ESPECIALIZADA', 'GENERICA', 'PERSONALIZADA')", name="ck_annex_template_tipo"),
                      CheckConstraint("orientacion IN ('VERTICAL', 'HORIZONTAL')", name="ck_annex_template_orientacion"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(14), default="ESPECIALIZADA")
    especialidad: Mapped[str] = mapped_column(String(30))  # constructor de datos (EFECTIVO, CARTERA, PPE…)
    elemento: Mapped[str | None] = mapped_column(String(2))
    cuentas: Mapped[str] = mapped_column(String(400), default="")  # prefijos separados por coma
    agrupar_por: Mapped[str | None] = mapped_column(String(200))   # campos separados por coma
    subtotales: Mapped[str | None] = mapped_column(String(400))    # campos importe a subtotalizar
    filtros: Mapped[str | None] = mapped_column(Text)              # JSON [{campo, op, valor}]
    orden: Mapped[str | None] = mapped_column(String(200))         # "campo" o "-campo", separados por coma
    rangos_antiguedad: Mapped[str | None] = mapped_column(Text)    # JSON [[1,30],[31,60]…]
    encabezado: Mapped[str | None] = mapped_column(Text)           # JSON {titulo, subtitulo, nota}
    parametros: Mapped[str | None] = mapped_column(Text)           # JSON propio de la especialidad
    orientacion: Mapped[str] = mapped_column(String(10), default="HORIZONTAL")
    usar_logo: Mapped[bool] = mapped_column(Boolean, default=True)
    compartida: Mapped[bool] = mapped_column(Boolean, default=False)
    autorizada: Mapped[bool] = mapped_column(Boolean, default=True)
    autorizada_por: Mapped[str | None] = mapped_column(String(80))
    base_id: Mapped[int | None] = mapped_column(ForeignKey("annex_templates.id"))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    creado_por: Mapped[str] = mapped_column(String(80), default="sistema")
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ColumnaPlantilla(Base):
    __tablename__ = "annex_template_columns"
    __table_args__ = (UniqueConstraint("plantilla_id", "campo", name="uq_annex_col_campo"),
                      CheckConstraint("tipo IN ('texto', 'importe', 'entero', 'fecha', 'pct', 'tasa')", name="ck_annex_col_tipo"))

    id: Mapped[int] = mapped_column(primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("annex_templates.id", ondelete="CASCADE"), index=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    campo: Mapped[str] = mapped_column(String(60))
    titulo: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(10), default="texto")
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    total: Mapped[bool] = mapped_column(Boolean, default=False)
    ancho: Mapped[int | None] = mapped_column(Integer)


class ReglaPlantilla(Base):
    """Validaciones adicionales que la plantilla ejecuta sobre el anexo generado."""
    __tablename__ = "annex_template_rules"
    __table_args__ = (UniqueConstraint("plantilla_id", "codigo", name="uq_annex_rule_codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("annex_templates.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(40))
    descripcion: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(20))  # CONDICION_FILA | UMBRAL_DIFERENCIA | SALDO_ANTIGUO
    expresion: Mapped[str | None] = mapped_column(Text)
    parametros: Mapped[str | None] = mapped_column(Text)
    severidad: Mapped[str] = mapped_column(String(12), default="MEDIA")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class FormulaPlantilla(Base):
    """Campo calculado con el motor seguro de expresiones (sin código ni SQL arbitrario)."""
    __tablename__ = "annex_template_formulas"
    __table_args__ = (UniqueConstraint("plantilla_id", "campo", name="uq_annex_formula_campo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("annex_templates.id", ondelete="CASCADE"), index=True)
    campo: Mapped[str] = mapped_column(String(60))
    titulo: Mapped[str] = mapped_column(String(80))
    expresion: Mapped[str] = mapped_column(String(500))
    tipo: Mapped[str] = mapped_column(String(10), default="importe")
    orden: Mapped[int] = mapped_column(Integer, default=0)


# ------------------------------------------------------------------ generación y anexos
class GeneracionAnexos(Base):
    __tablename__ = "annex_generation_runs"
    __table_args__ = (CheckConstraint("estado IN ('EN_COLA', 'PROCESANDO', 'COMPLETADO', 'CANCELADO', 'ERROR')",
                                      name="ck_annex_run_estado"),
                      Index("ix_annex_run_clave", "empresa_id", "clave_idempotencia"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int] = mapped_column(Integer)
    fecha_corte: Mapped[date] = mapped_column(Date)
    alcance: Mapped[str] = mapped_column(Text)  # JSON {modo, cuentas, elemento, desde, hasta, filtros}
    clave_idempotencia: Mapped[str] = mapped_column(String(64))
    version_datos: Mapped[str] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(String(12), default="EN_COLA")
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    etapa: Mapped[str | None] = mapped_column(String(160))
    cancelar: Mapped[bool] = mapped_column(Boolean, default=False)
    total_cuentas: Mapped[int] = mapped_column(Integer, default=0)
    resumen: Mapped[str | None] = mapped_column(Text)
    tiempos: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime)


class Anexo(Base):
    """Un anexo por (empresa, cuenta, fecha de corte, plantilla, filtros). Sus resultados viven en versiones."""
    __tablename__ = "accounting_annexes"
    __table_args__ = (UniqueConstraint("empresa_id", "clave", name="uq_annex_clave"),
                      CheckConstraint(f"estado_revision IN ({_lista(ESTADOS_REVISION)})", name="ck_annex_estado"),
                      CheckConstraint(f"resultado IS NULL OR resultado IN ({_lista(RESULTADOS_CONCILIACION)})",
                                      name="ck_annex_resultado"),
                      Index("ix_annex_corte", "empresa_id", "fecha_corte", "cuenta"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    clave: Mapped[str] = mapped_column(String(64))
    cuenta: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str | None] = mapped_column(String(255))
    elemento: Mapped[str] = mapped_column(String(1))
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int] = mapped_column(Integer)
    fecha_corte: Mapped[date] = mapped_column(Date)
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    filtros: Mapped[str | None] = mapped_column(Text)  # JSON {centro_costo, proyecto, unidad_negocio, moneda}
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("annex_templates.id"))
    especialidad: Mapped[str] = mapped_column(String(30))
    version_actual: Mapped[int] = mapped_column(Integer, default=0)
    version_id: Mapped[int | None] = mapped_column(Integer)
    estado_revision: Mapped[str] = mapped_column(String(22), default="PENDIENTE_GENERACION")
    resultado: Mapped[str | None] = mapped_column(String(28))
    naturaleza: Mapped[str] = mapped_column(String(1), default="D")
    saldo_inicial: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    debe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    haber: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_contable: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_detalle: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_sustentado: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    saldo_pendiente_sustento: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    diferencia: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    observaciones_abiertas: Mapped[int] = mapped_column(Integer, default=0)
    responsable_elaboracion: Mapped[str | None] = mapped_column(String(80))
    responsable_revision: Mapped[str | None] = mapped_column(String(80))
    responsable_aprobacion: Mapped[str | None] = mapped_column(String(80))
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    conclusion: Mapped[str | None] = mapped_column(Text)
    acciones_correctivas: Mapped[str | None] = mapped_column(Text)
    elaborado_por: Mapped[str | None] = mapped_column(String(80))
    revisado_por: Mapped[str | None] = mapped_column(String(80))
    aprobado_por: Mapped[str | None] = mapped_column(String(80))
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime)
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime)
    lock_version: Mapped[int] = mapped_column(Integer, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VersionAnexo(Base):
    """Fotografía de un anexo: referencia a datos, plantilla y reglas usadas. Nunca se elimina."""
    __tablename__ = "annex_versions"
    __table_args__ = (UniqueConstraint("anexo_id", "numero", name="uq_annex_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    anexo_id: Mapped[int] = mapped_column(ForeignKey("accounting_annexes.id"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("annex_generation_runs.id"))
    motivo: Mapped[str | None] = mapped_column(String(255))
    version_datos: Mapped[str] = mapped_column(String(64))
    version_compensacion: Mapped[str | None] = mapped_column(String(64))
    plantilla_snapshot: Mapped[str] = mapped_column(Text)
    reglas_snapshot: Mapped[str | None] = mapped_column(Text)
    resumen: Mapped[str] = mapped_column(Text)        # JSON resumen contable + conciliación + extras
    hash_contenido: Mapped[str] = mapped_column(String(64))
    filas: Mapped[int] = mapped_column(Integer, default=0)
    inmutable: Mapped[bool] = mapped_column(Boolean, default=False)
    estado_al_cerrar: Mapped[str | None] = mapped_column(String(22))
    generado_por: Mapped[str] = mapped_column(String(80))
    generado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DetalleAnexo(Base):
    __tablename__ = "accounting_annex_details"
    __table_args__ = (Index("ix_annex_detail_version", "version_id", "orden"),
                      CheckConstraint(f"estado_sustento IN ({_lista(ESTADOS_SUSTENTO)})", name="ck_annex_detail_sustento"))

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("annex_versions.id"))
    anexo_id: Mapped[int] = mapped_column(ForeignKey("accounting_annexes.id"), index=True)
    orden: Mapped[int] = mapped_column(Integer)
    clave: Mapped[str] = mapped_column(String(160))
    cuenta: Mapped[str] = mapped_column(String(20))
    categoria: Mapped[str | None] = mapped_column(String(80))
    fecha: Mapped[date | None] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    tipo_documento: Mapped[str | None] = mapped_column(String(4))
    serie: Mapped[str | None] = mapped_column(String(20))
    numero: Mapped[str | None] = mapped_column(String(40))
    tercero: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(255))
    glosa: Mapped[str | None] = mapped_column(String(255))
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    tipo_cambio: Mapped[Decimal | None] = mapped_column(TasaCambio)
    importe_original: Mapped[Decimal | None] = mapped_column(Importe)
    importe_aplicado: Mapped[Decimal | None] = mapped_column(Importe)
    saldo_me: Mapped[Decimal | None] = mapped_column(Importe)
    saldo: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))  # MN, con el signo natural de la cuenta
    dias: Mapped[int | None] = mapped_column(Integer)
    tramo: Mapped[str | None] = mapped_column(String(60))
    centro_costo: Mapped[str | None] = mapped_column(String(30))
    proyecto: Mapped[str | None] = mapped_column(String(40))
    referencia: Mapped[str | None] = mapped_column(String(80))
    linea_id: Mapped[int | None] = mapped_column(Integer)
    item_id: Mapped[int | None] = mapped_column(Integer)
    estado_sustento: Mapped[str] = mapped_column(String(14), default="DOCUMENTADO")
    observacion: Mapped[str | None] = mapped_column(String(500))
    datos: Mapped[str | None] = mapped_column(Text)  # JSON campos propios de la especialidad


class ConciliacionAnexo(Base):
    __tablename__ = "annex_reconciliations"
    __table_args__ = (UniqueConstraint("version_id", name="uq_annex_reconciliation_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    anexo_id: Mapped[int] = mapped_column(ForeignKey("accounting_annexes.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("annex_versions.id"))
    saldo_inicial: Mapped[Decimal] = mapped_column(Importe)
    debe: Mapped[Decimal] = mapped_column(Importe)
    haber: Mapped[Decimal] = mapped_column(Importe)
    saldo_contable: Mapped[Decimal] = mapped_column(Importe)
    saldo_balance_importado: Mapped[Decimal | None] = mapped_column(Importe)
    diferencia_balance_importado: Mapped[Decimal | None] = mapped_column(Importe)
    saldo_detalle: Mapped[Decimal] = mapped_column(Importe)
    sustentado: Mapped[Decimal] = mapped_column(Importe)
    sin_documento: Mapped[Decimal] = mapped_column(Importe)
    sin_detalle: Mapped[Decimal] = mapped_column(Importe)
    por_clasificar: Mapped[Decimal] = mapped_column(Importe)
    diferencia: Mapped[Decimal] = mapped_column(Importe)
    resultado: Mapped[str] = mapped_column(String(28))
    cuadra: Mapped[bool] = mapped_column(Boolean)
    explicacion: Mapped[str | None] = mapped_column(Text)


class HallazgoAnexo(Base):
    __tablename__ = "annex_findings"
    __table_args__ = (CheckConstraint("estado IN ('ABIERTO', 'SUBSANADO', 'DESCARTADO')", name="ck_annex_finding_estado"),
                      Index("ix_annex_finding_anexo", "anexo_id", "estado"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    anexo_id: Mapped[int] = mapped_column(ForeignKey("accounting_annexes.id"))
    version_id: Mapped[int | None] = mapped_column(ForeignKey("annex_versions.id"))
    origen: Mapped[str] = mapped_column(String(10), default="SISTEMA")  # SISTEMA | USUARIO
    huella: Mapped[str] = mapped_column(String(64))
    codigo: Mapped[str] = mapped_column(String(40))
    severidad: Mapped[str] = mapped_column(String(12), default="MEDIA")  # ALTA | MEDIA | BAJA | INFORMATIVA
    titulo: Mapped[str] = mapped_column(String(300))
    detalle: Mapped[str | None] = mapped_column(Text)
    importe: Mapped[Decimal | None] = mapped_column(Importe)
    clave_fila: Mapped[str | None] = mapped_column(String(160))
    estado: Mapped[str] = mapped_column(String(10), default="ABIERTO")
    responsable: Mapped[str | None] = mapped_column(String(80))
    accion_correctiva: Mapped[str | None] = mapped_column(Text)
    creado_por: Mapped[str] = mapped_column(String(80), default="sistema")
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resuelto_por: Mapped[str | None] = mapped_column(String(80))
    resuelto_en: Mapped[datetime | None] = mapped_column(DateTime)


class RevisionAnexo(Base):
    """Bitácora del flujo: cada cambio de estado o de campos de revisión."""
    __tablename__ = "annex_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    anexo_id: Mapped[int] = mapped_column(ForeignKey("accounting_annexes.id"), index=True)
    version_id: Mapped[int | None] = mapped_column(ForeignKey("annex_versions.id"))
    de_estado: Mapped[str | None] = mapped_column(String(22))
    a_estado: Mapped[str | None] = mapped_column(String(22))
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    cambios: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AprobacionAnexo(Base):
    __tablename__ = "annex_approvals"
    __table_args__ = (CheckConstraint("accion IN ('APROBAR', 'APROBAR_POLITICA', 'CERRAR', 'REABRIR')", name="ck_annex_approval_accion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    anexo_id: Mapped[int] = mapped_column(ForeignKey("accounting_annexes.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("annex_versions.id"))
    accion: Mapped[str] = mapped_column(String(18))
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ComentarioAnexo(Base):
    __tablename__ = "annex_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    anexo_id: Mapped[int] = mapped_column(ForeignKey("accounting_annexes.id"), index=True)
    version_id: Mapped[int | None] = mapped_column(ForeignKey("annex_versions.id"))
    clave_fila: Mapped[str | None] = mapped_column(String(160))
    usuario: Mapped[str] = mapped_column(String(80))
    texto: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdjuntoAnexo(Base):
    """Documento sustentatorio relacionado con la cuenta, el anexo, el tercero, el documento o la partida."""
    __tablename__ = "annex_attachments"
    __table_args__ = (CheckConstraint(f"categoria IN ({_lista(CATEGORIAS_ADJUNTO)})", name="ck_annex_attachment_categoria"),
                      Index("ix_annex_attachment_rel", "empresa_id", "cuenta", "tercero"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    anexo_id: Mapped[int | None] = mapped_column(ForeignKey("accounting_annexes.id"))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    tercero: Mapped[str | None] = mapped_column(String(20))
    documento: Mapped[str | None] = mapped_column(String(60))
    clave_fila: Mapped[str | None] = mapped_column(String(160))
    item_id: Mapped[int | None] = mapped_column(Integer)
    linea_id: Mapped[int | None] = mapped_column(Integer)
    categoria: Mapped[str] = mapped_column(String(24), default="OTRO")
    descripcion: Mapped[str | None] = mapped_column(String(255))
    nombre: Mapped[str] = mapped_column(String(255))
    tipo_contenido: Mapped[str | None] = mapped_column(String(100))
    tamano: Mapped[int] = mapped_column(Integer)
    hash: Mapped[str] = mapped_column(String(64))
    ruta: Mapped[str] = mapped_column(String(400))
    confidencial: Mapped[bool] = mapped_column(Boolean, default=False)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AsignacionAnexo(Base):
    """Responsables y fechas límite por cuenta (prefijo) o por anexo; tipo ACCESO restringe cuentas visibles."""
    __tablename__ = "annex_assignments"
    __table_args__ = (CheckConstraint("tipo IN ('ELABORACION', 'REVISION', 'APROBACION', 'ACCESO')", name="ck_annex_assignment_tipo"),
                      Index("ix_annex_assignment_usuario", "empresa_id", "usuario"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    anexo_id: Mapped[int | None] = mapped_column(ForeignKey("accounting_annexes.id"))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    tipo: Mapped[str] = mapped_column(String(12))
    usuario: Mapped[str] = mapped_column(String(80))
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    asignado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ExportacionAnexos(Base):
    __tablename__ = "annex_export_jobs"
    __table_args__ = (CheckConstraint("estado IN ('EN_COLA', 'PROCESANDO', 'COMPLETADO', 'ERROR')", name="ck_annex_export_estado"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))  # LIBRO_EXCEL | EXPEDIENTE_PDF | ANEXO_EXCEL | ANEXO_PDF
    alcance: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), default="EN_COLA")
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    etapa: Mapped[str | None] = mapped_column(String(160))
    nombre_archivo: Mapped[str | None] = mapped_column(String(255))
    ruta: Mapped[str | None] = mapped_column(String(400))
    tamano: Mapped[int | None] = mapped_column(Integer)
    anexos: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime)


class AuditoriaAnexo(Base):
    __tablename__ = "annex_audit_logs"
    __table_args__ = (Index("ix_annex_audit_empresa", "empresa_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(30))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(Text)


# ------------------------------------------------------------------ soporte (adaptación)
class RegistroAuxiliar(Base):
    """Información de soporte importada por el usuario: registro de activos fijos, cronogramas financieros,
    contratos de gastos anticipados, servicios en proceso e inventarios. Nunca se genera de forma automática."""
    __tablename__ = "annex_support_records"
    __table_args__ = (CheckConstraint(f"tipo IN ({_lista(TIPOS_REGISTRO)})", name="ck_annex_support_tipo"),
                      UniqueConstraint("empresa_id", "tipo", "clave", "fecha_referencia", name="uq_annex_support_clave"),
                      Index("ix_annex_support_tipo", "empresa_id", "tipo", "vigente"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    tipo: Mapped[str] = mapped_column(String(22))
    clave: Mapped[str] = mapped_column(String(80))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    fecha_referencia: Mapped[date | None] = mapped_column(Date)
    datos: Mapped[str] = mapped_column(Text)
    archivo: Mapped[str | None] = mapped_column(String(255))
    fila: Mapped[int | None] = mapped_column(Integer)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ConfiguracionAnexos(Base):
    """Políticas por empresa: separación de funciones, aprobación automática autorizada, tolerancia, logo."""
    __tablename__ = "annex_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), unique=True)
    parametros: Mapped[str] = mapped_column(Text, default="{}")
    actualizado_por: Mapped[str | None] = mapped_column(String(80))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


__all__ = ["PlantillaAnexo", "ColumnaPlantilla", "ReglaPlantilla", "FormulaPlantilla", "GeneracionAnexos", "Anexo",
           "VersionAnexo", "DetalleAnexo", "ConciliacionAnexo", "HallazgoAnexo", "RevisionAnexo", "AprobacionAnexo",
           "ComentarioAnexo", "AdjuntoAnexo", "AsignacionAnexo", "ExportacionAnexos", "AuditoriaAnexo",
           "RegistroAuxiliar", "ConfiguracionAnexos", "ESTADOS_REVISION", "RESULTADOS_CONCILIACION",
           "ESTADOS_SUSTENTO", "TIPOS_REGISTRO", "CATEGORIAS_ADJUNTO"]
