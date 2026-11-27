"""Fase 7 — Auditor contable inteligente 360.

Un ENCARGO (audit_engagement) define empresa, periodo, corte, tipo, alcance, materialidad y responsable. Cada EJECUCIÓN
(audit_run) conserva la versión de los datos y de las reglas usadas; sus resultados por regla (audit_rule_results)
documentan la población evaluada. Los HALLAZGOS (audit_findings) son potenciales hasta que un revisor los confirma;
llevan evidencia verificable (audit_finding_evidence) con referencias a los registros originales y se agrupan para no
duplicar exposiciones monetarias. La bitácora (audit_event_logs) es encadenada por hash y no admite modificaciones.
Nada modifica los asientos originales ni genera ajustes."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

Importe = Numeric(18, 2)
Pct = Numeric(9, 4)

RIESGOS = ("CRITICO", "ALTO", "MEDIO", "BAJO", "INFORMATIVO")
TIPOS_HALLAZGO = ("POTENCIAL", "CONFIRMADO", "FALSO_POSITIVO", "JUSTIFICADO", "SUBSANADO")
ESTADOS_HALLAZGO = ("DETECTADO", "PENDIENTE_REVISION", "EN_ANALISIS", "CONFIRMADO", "JUSTIFICADO", "PENDIENTE_REGULARIZACION",
                    "EN_SUBSANACION", "SUBSANADO", "VERIFICADO", "CERRADO", "REABIERTO")
REGULARIZACION = ("REQUIERE_AJUSTE", "REQUIERE_RECLASIFICACION", "REQUIERE_DOCUMENTACION", "REQUIERE_PARAMETRIZACION",
                  "REQUIERE_CONCILIACION", "REQUIERE_EVALUACION_TRIBUTARIA", "REQUIERE_EVALUACION_LEGAL", "NO_REQUIERE_AJUSTE")
ESTADOS_ENCARGO = ("PLANIFICADO", "EN_EJECUCION", "EN_REVISION", "CONCLUIDO", "CERRADO")
ESTADOS_PROCESO = ("PENDIENTE", "EN_COLA", "PROCESANDO", "COMPLETADO", "CANCELADO", "ERROR")
TIPOS_AUDITORIA = ("INTEGRAL", "FINANCIERA", "TRIBUTARIA_PREVENTIVA", "CONTROL_INTERNO", "PARAMETRIZACION", "CUENTA", "ESPECIAL")


def _l(v):
    return ", ".join(f"'{x}'" for x in v)


class EncargoAuditoria(Base):
    __tablename__ = "audit_engagements"
    __table_args__ = (CheckConstraint(f"estado IN ({_l(ESTADOS_ENCARGO)})", name="ck_audit_eng_estado"),
                      CheckConstraint(f"tipo IN ({_l(TIPOS_AUDITORIA)})", name="ck_audit_eng_tipo"),
                      Index("ix_audit_eng_empresa", "empresa_id", "ejercicio", "periodo"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(30))
    nombre: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(25), default="INTEGRAL")
    ejercicio: Mapped[int] = mapped_column(Integer)
    periodo: Mapped[int] = mapped_column(Integer)
    fecha_corte: Mapped[date] = mapped_column(Date)
    objetivo: Mapped[str | None] = mapped_column(Text)
    responsable: Mapped[str | None] = mapped_column(String(80))
    materialidad_id: Mapped[int | None] = mapped_column(ForeignKey("audit_materiality_settings.id"))
    matriz_id: Mapped[int | None] = mapped_column(ForeignKey("audit_risk_matrix.id"))
    estado: Mapped[str] = mapped_column(String(15), default="PLANIFICADO")
    recurrencia: Mapped[str | None] = mapped_column(String(12))   # MENSUAL | TRIMESTRAL | ANUAL
    proxima_ejecucion: Mapped[date | None] = mapped_column(Date)
    origen_id: Mapped[int | None] = mapped_column(Integer)       # encargo recurrente del que deriva
    conclusion: Mapped[str | None] = mapped_column(Text)
    conclusion_aprobada_por: Mapped[str | None] = mapped_column(String(80))
    lock_version: Mapped[int] = mapped_column(Integer, default=0)
    creado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AlcanceAuditoria(Base):
    __tablename__ = "audit_scopes"
    __table_args__ = (CheckConstraint("tipo IN ('MODULO','CUENTA','CENTRO_COSTO','PROYECTO','UNIDAD_NEGOCIO','REGLA','TERCERO')",
                                      name="ck_audit_scope_tipo"),
                      UniqueConstraint("engagement_id", "tipo", "valor", name="uq_audit_scope"))

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("audit_engagements.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(15))
    valor: Mapped[str] = mapped_column(String(60))


class CategoriaRegla(Base):
    __tablename__ = "audit_rule_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[str | None] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(Integer, default=0)


class ReglaAuditoria(Base):
    """Regla del catálogo (empresa_id nulo) o de la empresa. Las normativas (tributarias) no se ejecutan sin validación."""
    __tablename__ = "audit_rules"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_audit_rule_codigo"),
                      CheckConstraint(f"riesgo IN ({_l(RIESGOS)})", name="ck_audit_rule_riesgo"),
                      CheckConstraint("origen IN ('SISTEMA','CONFIGURABLE')", name="ck_audit_rule_origen"),
                      CheckConstraint("estado_validacion IN ('NO_REQUIERE','PENDIENTE','VALIDADA','RECHAZADA')", name="ck_audit_rule_val"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), index=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("audit_rule_categories.id"))
    codigo: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text)
    origen: Mapped[str] = mapped_column(String(12), default="SISTEMA")
    evaluador: Mapped[str | None] = mapped_column(String(40))      # función del catálogo (reglas del sistema)
    definicion: Mapped[str | None] = mapped_column(Text)           # JSON declarativo (reglas configurables)
    cuentas: Mapped[str | None] = mapped_column(String(200))
    fuente: Mapped[str | None] = mapped_column(String(40))
    parametros: Mapped[str] = mapped_column(Text, default="{}")    # umbrales, tolerancias
    riesgo: Mapped[str] = mapped_column(String(12), default="MEDIO")
    probabilidad: Mapped[int] = mapped_column(Integer, default=3)  # 1–5: probabilidad base estimada (priorización interna)
    estructural: Mapped[bool] = mapped_column(Boolean, default=False)  # error estructural confirmable vs interpretación
    excepciones: Mapped[str | None] = mapped_column(Text)          # JSON: cuentas, terceros, documentos excluidos
    evidencia_requerida: Mapped[str | None] = mapped_column(Text)
    criterio: Mapped[str | None] = mapped_column(Text)
    recomendacion: Mapped[str | None] = mapped_column(Text)
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    normativa: Mapped[bool] = mapped_column(Boolean, default=False)
    norma_referencia: Mapped[str | None] = mapped_column(String(255))
    fuente_oficial: Mapped[str | None] = mapped_column(String(255))
    fecha_publicacion: Mapped[date | None] = mapped_column(Date)
    condiciones_aplicacion: Mapped[str | None] = mapped_column(Text)
    excepciones_normativas: Mapped[str | None] = mapped_column(Text)
    responsable_validacion: Mapped[str | None] = mapped_column(String(80))
    estado_validacion: Mapped[str] = mapped_column(String(12), default="NO_REQUIERE")
    validada_por: Mapped[str | None] = mapped_column(String(80))
    validada_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_por: Mapped[str] = mapped_column(String(80), default="sistema")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VersionRegla(Base):
    __tablename__ = "audit_rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version", name="uq_audit_rule_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("audit_rules.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[str] = mapped_column(Text)
    motivo: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EjecucionAuditoria(Base):
    __tablename__ = "audit_runs"
    __table_args__ = (CheckConstraint(f"estado_proceso IN ({_l(ESTADOS_PROCESO)})", name="ck_audit_run_estado"),
                      CheckConstraint("tipo IN ('COMPLETA','MODULO','CUENTA','REGLAS')", name="ck_audit_run_tipo"),
                      Index("ix_audit_run_eng", "engagement_id", "id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("audit_engagements.id"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(10), default="COMPLETA")
    parametros: Mapped[str] = mapped_column(Text, default="{}")   # módulos, cuentas, reglas
    estado_proceso: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    progreso: Mapped[int] = mapped_column(Integer, default=0)
    etapa: Mapped[str | None] = mapped_column(String(160))
    cancelar: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    version_datos: Mapped[str | None] = mapped_column(String(64))
    hash_reglas: Mapped[str | None] = mapped_column(String(64))
    reglas_snapshot: Mapped[str | None] = mapped_column(Text)
    materialidad_snapshot: Mapped[str | None] = mapped_column(Text)
    resumen: Mapped[str | None] = mapped_column(Text)
    tiempos: Mapped[str | None] = mapped_column(Text)
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime)


class ResultadoRegla(Base):
    __tablename__ = "audit_rule_results"
    __table_args__ = (CheckConstraint("estado IN ('EJECUTADA','SIN_EXCEPCIONES','CON_EXCEPCIONES','PENDIENTE_EVALUACION',"
                                      "'NO_VALIDADA','FUERA_DE_VIGENCIA','SIN_DATOS','REUTILIZADA','ERROR')", name="ck_audit_rr_estado"),
                      Index("ix_audit_rr_run", "run_id", "rule_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("audit_runs.id"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("audit_rules.id"))
    codigo: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer)
    modulo: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20))
    poblacion: Mapped[int] = mapped_column(Integer, default=0)
    importe_poblacion: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    excepciones: Mapped[int] = mapped_column(Integer, default=0)
    importe_excepciones: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    metodo: Mapped[str | None] = mapped_column(Text)              # descripción del procedimiento y limitaciones
    mensaje: Mapped[str | None] = mapped_column(Text)
    huella_entrada: Mapped[str | None] = mapped_column(String(64))  # datos + versión de regla (procesamiento incremental)
    duracion_ms: Mapped[int] = mapped_column(Integer, default=0)


class GrupoHallazgos(Base):
    """Hallazgos que comparten la misma exposición monetaria (no se suman dos veces)."""
    __tablename__ = "audit_finding_groups"
    __table_args__ = (UniqueConstraint("engagement_id", "clave", name="uq_audit_group_clave"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("audit_engagements.id"), index=True)
    clave: Mapped[str] = mapped_column(String(200))
    titulo: Mapped[str] = mapped_column(String(255))
    exposicion: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    exposicion_confirmada: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    hallazgos: Mapped[int] = mapped_column(Integer, default=0)
    manual: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_por: Mapped[str] = mapped_column(String(80), default="sistema")


class HallazgoAuditoria(Base):
    __tablename__ = "audit_findings"
    __table_args__ = (CheckConstraint(f"riesgo IN ({_l(RIESGOS)})", name="ck_audit_f_riesgo"),
                      CheckConstraint(f"tipo IN ({_l(TIPOS_HALLAZGO)})", name="ck_audit_f_tipo"),
                      CheckConstraint(f"estado IN ({_l(ESTADOS_HALLAZGO)})", name="ck_audit_f_estado"),
                      CheckConstraint(f"regularizacion IS NULL OR regularizacion IN ({_l(REGULARIZACION)})", name="ck_audit_f_reg"),
                      CheckConstraint("impacto BETWEEN 1 AND 5 AND probabilidad BETWEEN 1 AND 5", name="ck_audit_f_matriz"),
                      UniqueConstraint("engagement_id", "huella", name="uq_audit_f_huella"),
                      UniqueConstraint("empresa_id", "codigo", name="uq_audit_f_codigo"),
                      Index("ix_audit_f_eng", "engagement_id", "estado", "riesgo"), Index("ix_audit_f_cuenta", "empresa_id", "cuenta"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("audit_engagements.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("audit_runs.id"))           # ejecución que lo detectó
    ultima_run_id: Mapped[int] = mapped_column(Integer)                        # última ejecución que lo reprodujo
    rule_id: Mapped[int] = mapped_column(ForeignKey("audit_rules.id"))
    regla_codigo: Mapped[str] = mapped_column(String(20))
    regla_version: Mapped[int] = mapped_column(Integer)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("audit_finding_groups.id"))
    codigo: Mapped[str] = mapped_column(String(30))
    titulo: Mapped[str] = mapped_column(String(255))
    periodo: Mapped[int] = mapped_column(Integer)                              # AAAAMM del encargo
    modulo: Mapped[str] = mapped_column(String(20))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    tercero: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(255))
    documento: Mapped[str | None] = mapped_column(String(80))
    asiento: Mapped[str | None] = mapped_column(String(80))
    linea_id: Mapped[int | None] = mapped_column(Integer)
    centro_costo: Mapped[str | None] = mapped_column(String(30))
    proyecto: Mapped[str | None] = mapped_column(String(40))
    importe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    importe_confirmado: Mapped[Decimal | None] = mapped_column(Importe)
    impacto_potencial: Mapped[str | None] = mapped_column(Text)
    clave_exposicion: Mapped[str] = mapped_column(String(200))
    riesgo: Mapped[str] = mapped_column(String(12))
    riesgo_calculado: Mapped[str] = mapped_column(String(12))
    impacto: Mapped[int] = mapped_column(Integer, default=3)
    probabilidad: Mapped[int] = mapped_column(Integer, default=3)
    puntuacion: Mapped[int] = mapped_column(Integer, default=9)                # impacto × probabilidad (priorización interna)
    riesgo_ajustado_por: Mapped[str | None] = mapped_column(String(80))
    justificacion_riesgo: Mapped[str | None] = mapped_column(Text)
    sobre_materialidad: Mapped[bool] = mapped_column(Boolean, default=False)
    claramente_insignificante: Mapped[bool] = mapped_column(Boolean, default=False)
    calidad_evidencia: Mapped[str] = mapped_column(String(12), default="SUFICIENTE")  # SUFICIENTE | PARCIAL | INSUFICIENTE
    estructural: Mapped[bool] = mapped_column(Boolean, default=False)
    condicion: Mapped[str] = mapped_column(Text)
    criterio: Mapped[str | None] = mapped_column(Text)
    causa: Mapped[str | None] = mapped_column(Text)
    efecto: Mapped[str | None] = mapped_column(Text)
    recomendacion: Mapped[str | None] = mapped_column(Text)
    tratamiento_tributario: Mapped[str | None] = mapped_column(String(30))     # PENDIENTE_EVALUACION, POSIBLE_DIFERENCIA_TEMPORAL…
    tipo: Mapped[str] = mapped_column(String(15), default="POTENCIAL")
    estado: Mapped[str] = mapped_column(String(25), default="DETECTADO")
    regularizacion: Mapped[str | None] = mapped_column(String(32))
    en_bandeja_regularizacion: Mapped[bool] = mapped_column(Boolean, default=False)
    enviado_regularizacion_por: Mapped[str | None] = mapped_column(String(80))
    enviado_regularizacion_en: Mapped[datetime | None] = mapped_column(DateTime)
    responsable: Mapped[str | None] = mapped_column(String(80))
    fecha_deteccion: Mapped[date] = mapped_column(Date)
    fecha_limite: Mapped[date | None] = mapped_column(Date)
    reincidencias: Mapped[int] = mapped_column(Integer, default=0)
    anterior_id: Mapped[int | None] = mapped_column(Integer)                   # hallazgo del encargo anterior (reincidencia)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)               # falso si la última ejecución ya no lo reproduce
    personal: Mapped[bool] = mapped_column(Boolean, default=False)
    huella: Mapped[str] = mapped_column(String(64))
    detalle: Mapped[str | None] = mapped_column(Text)                          # JSON (valores calculados)
    lock_version: Mapped[int] = mapped_column(Integer, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class EvidenciaHallazgo(Base):
    __tablename__ = "audit_finding_evidence"
    __table_args__ = (CheckConstraint("origen IN ('SISTEMA','USUARIO')", name="ck_audit_ev_origen"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("audit_findings.id"), index=True)
    origen: Mapped[str] = mapped_column(String(8), default="SISTEMA")
    tipo: Mapped[str] = mapped_column(String(20))           # LINEA, ASIENTO, DOCUMENTO, CONCILIACION, ANEXO, CALCULO, ARCHIVO…
    tabla: Mapped[str | None] = mapped_column(String(60))   # referencia verificable al registro original
    registro_id: Mapped[int | None] = mapped_column(Integer)
    descripcion: Mapped[str] = mapped_column(Text)
    datos: Mapped[str | None] = mapped_column(Text)
    nombre_archivo: Mapped[str | None] = mapped_column(String(255))
    ruta: Mapped[str | None] = mapped_column(String(400))
    hash: Mapped[str | None] = mapped_column(String(64))
    confidencial: Mapped[bool] = mapped_column(Boolean, default=False)
    usuario: Mapped[str] = mapped_column(String(80), default="sistema")
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MatrizRiesgo(Base):
    __tablename__ = "audit_risk_matrix"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1)
    matriz: Mapped[str] = mapped_column(Text)        # JSON 5×5: [impacto-1][probabilidad-1] → nivel
    factores: Mapped[str] = mapped_column(Text)      # JSON: ajustes por recurrencia, evidencia, controles, naturaleza
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    aprobado_por: Mapped[str | None] = mapped_column(String(80))
    creado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Materialidad(Base):
    __tablename__ = "audit_materiality_settings"
    __table_args__ = (CheckConstraint("estado IN ('BORRADOR','APROBADA','REEMPLAZADA')", name="ck_audit_mat_estado"),
                      CheckConstraint("materialidad_global >= 0 AND materialidad_ejecucion >= 0 AND umbral_insignificante >= 0",
                                      name="ck_audit_mat_positiva"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    ejercicio: Mapped[int] = mapped_column(Integer)
    base: Mapped[str] = mapped_column(String(30))                   # INGRESOS | ACTIVOS | PATRIMONIO | RESULTADO_ANTES_IMPUESTOS | GASTOS | OTRA
    descripcion_base: Mapped[str | None] = mapped_column(String(255))
    importe_base: Mapped[Decimal] = mapped_column(Importe)
    porcentaje_global: Mapped[Decimal] = mapped_column(Pct)
    materialidad_global: Mapped[Decimal] = mapped_column(Importe)
    porcentaje_ejecucion: Mapped[Decimal] = mapped_column(Pct)
    materialidad_ejecucion: Mapped[Decimal] = mapped_column(Importe)
    porcentaje_insignificante: Mapped[Decimal] = mapped_column(Pct)
    umbral_insignificante: Mapped[Decimal] = mapped_column(Importe)
    por_cuenta: Mapped[str | None] = mapped_column(Text)            # JSON {prefijo: importe}
    por_tipo: Mapped[str | None] = mapped_column(Text)              # JSON {módulo: importe}
    cualitativos: Mapped[str | None] = mapped_column(Text)          # JSON: reglas o módulos siempre relevantes
    justificacion: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), default="BORRADOR")
    definido_por: Mapped[str] = mapped_column(String(80))
    aprobado_por: Mapped[str | None] = mapped_column(String(80))
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MuestraAuditoria(Base):
    __tablename__ = "audit_samples"
    __table_args__ = (CheckConstraint("metodo IN ('ALEATORIA','IMPORTE','RIESGO','ANTIGUEDAD','TERCERO','CUENTA','ESTRATIFICADA')",
                                      name="ck_audit_sample_metodo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("audit_engagements.id"), index=True)
    workpaper_id: Mapped[int | None] = mapped_column(ForeignKey("audit_workpapers.id"))
    nombre: Mapped[str] = mapped_column(String(160))
    poblacion: Mapped[str] = mapped_column(String(30))              # LINEAS | HALLAZGOS | DOCUMENTOS
    metodo: Mapped[str] = mapped_column(String(15))
    criterios: Mapped[str] = mapped_column(Text)
    semilla: Mapped[int | None] = mapped_column(Integer)
    poblacion_cantidad: Mapped[int] = mapped_column(Integer)
    poblacion_importe: Mapped[Decimal] = mapped_column(Importe)
    tamano: Mapped[int] = mapped_column(Integer)
    estadisticamente_representativa: Mapped[bool] = mapped_column(Boolean, default=False)
    nota: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ItemMuestra(Base):
    __tablename__ = "audit_sample_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey("audit_samples.id"), index=True)
    tabla: Mapped[str] = mapped_column(String(60))
    registro_id: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    importe: Mapped[Decimal] = mapped_column(Importe, default=Decimal("0"))
    estrato: Mapped[str | None] = mapped_column(String(40))
    resultado: Mapped[str | None] = mapped_column(String(20))       # CONFORME | EXCEPCION | PENDIENTE
    comentario: Mapped[str | None] = mapped_column(Text)


class PapelAuditoria(Base):
    __tablename__ = "audit_workpapers"
    __table_args__ = (CheckConstraint("estado IN ('PRELIMINAR','EN_REVISION','REVISADO','APROBADO')", name="ck_audit_wp_estado"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("audit_engagements.id"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("audit_runs.id"))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("audit_rules.id"))
    referencia: Mapped[str] = mapped_column(String(30))
    titulo: Mapped[str] = mapped_column(String(255))
    contenido: Mapped[str] = mapped_column(Text)      # JSON: objetivo, alcance, población, fuente, procedimiento, resultados…
    conclusion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), default="PRELIMINAR")
    version: Mapped[int] = mapped_column(Integer, default=1)
    elaborado_por: Mapped[str] = mapped_column(String(80))
    revisado_por: Mapped[str | None] = mapped_column(String(80))
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlanAccion(Base):
    __tablename__ = "audit_action_plans"
    __table_args__ = (CheckConstraint("estado IN ('PENDIENTE','EN_PROCESO','COMPLETADO','VENCIDO','CANCELADO')", name="ck_audit_ap_estado"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("audit_findings.id"), index=True)
    descripcion: Mapped[str] = mapped_column(Text)
    responsable: Mapped[str] = mapped_column(String(80))
    fecha_compromiso: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    avance: Mapped[int] = mapped_column(Integer, default=0)
    comentario_cierre: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AsignacionAuditoria(Base):
    __tablename__ = "audit_assignments"
    __table_args__ = (CheckConstraint("tipo IN ('EQUIPO','RESPONSABLE_HALLAZGO','AUDITOR_EXTERNO')", name="ck_audit_asig_tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    engagement_id: Mapped[int | None] = mapped_column(ForeignKey("audit_engagements.id"))
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("audit_findings.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    usuario: Mapped[str] = mapped_column(String(80))
    funcion: Mapped[str | None] = mapped_column(String(40))       # elabora, revisa, aprueba…
    vigente_hasta: Mapped[date | None] = mapped_column(Date)       # acceso temporal del auditor externo
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    asignado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RevisionAuditoria(Base):
    """Historial completo de cambios (estado, campos, comentarios) de hallazgos, encargos, papeles y reglas."""
    __tablename__ = "audit_reviews"
    __table_args__ = (Index("ix_audit_rev_entidad", "entidad", "entidad_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    entidad: Mapped[str] = mapped_column(String(20))
    entidad_id: Mapped[int] = mapped_column(Integer)
    de_estado: Mapped[str | None] = mapped_column(String(25))
    a_estado: Mapped[str | None] = mapped_column(String(25))
    comentario: Mapped[str | None] = mapped_column(Text)
    cambios: Mapped[str | None] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AprobacionAuditoria(Base):
    __tablename__ = "audit_approvals"
    __table_args__ = (CheckConstraint("entidad IN ('HALLAZGO','CONCLUSION','REGLA','MATERIALIDAD','MATRIZ','PAPEL','INFORME','CIERRE')",
                                      name="ck_audit_apr_entidad"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    entidad: Mapped[str] = mapped_column(String(15))
    entidad_id: Mapped[int] = mapped_column(Integer)
    accion: Mapped[str] = mapped_column(String(20))
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    comentario: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InformeAuditoria(Base):
    __tablename__ = "audit_reports"
    __table_args__ = (CheckConstraint("tipo IN ('GERENCIA','CONTADOR','AUDITORIA_INTERNA','TRIBUTARIO','PARAMETRIZACION','DETALLE_CUENTA')",
                                      name="ck_audit_rep_tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("audit_engagements.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    titulo: Mapped[str] = mapped_column(String(255))
    cuenta: Mapped[str | None] = mapped_column(String(20))
    version_actual: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(12), default="BORRADOR")
    creado_por: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VersionInforme(Base):
    __tablename__ = "audit_report_versions"
    __table_args__ = (UniqueConstraint("report_id", "numero", name="uq_audit_report_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("audit_reports.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[int | None] = mapped_column(Integer)
    contenido: Mapped[str] = mapped_column(Text)      # instantánea de las 16 secciones
    hash: Mapped[str] = mapped_column(String(64))
    generado_por: Mapped[str] = mapped_column(String(80))
    generado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EventoAuditoria(Base):
    """Bitácora protegida: cada evento encadena el hash del anterior; triggers impiden modificarla o borrarla."""
    __tablename__ = "audit_event_logs"
    __table_args__ = (Index("ix_audit_evt_empresa", "empresa_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    usuario: Mapped[str] = mapped_column(String(80))
    rol: Mapped[str | None] = mapped_column(String(20))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(30))
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    engagement_id: Mapped[int | None] = mapped_column(Integer)
    run_id: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(Text)
    hash_anterior: Mapped[str | None] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class ConfiguracionImportada(Base):
    """Parametrización del ERP importada (plan aprobado o utilizado, rubros de reportes, destinos, distribución…)."""
    __tablename__ = "audit_configurations"
    __table_args__ = (CheckConstraint("tipo IN ('PLAN_APROBADO','PLAN_UTILIZADO','RUBROS_APROBADOS','RUBROS_UTILIZADOS',"
                                      "'DISTRIBUCION_APROBADA','DISTRIBUCION_UTILIZADA')", name="ck_audit_conf_tipo"),
                      UniqueConstraint("empresa_id", "tipo", "version", name="uq_audit_conf_version"))

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(25))
    sistema: Mapped[str] = mapped_column(String(30))     # SAP, PROFICONT, STARSOFT, CONCAR, OTRO
    version: Mapped[int] = mapped_column(Integer)
    vigente_desde: Mapped[date | None] = mapped_column(Date)
    items: Mapped[str] = mapped_column(Text)              # JSON normalizado
    registros: Mapped[int] = mapped_column(Integer)
    nombre_archivo: Mapped[str | None] = mapped_column(String(255))
    hash_archivo: Mapped[str | None] = mapped_column(String(64))
    sustento: Mapped[str | None] = mapped_column(Text)
    aprobado_por: Mapped[str | None] = mapped_column(String(80))
    usuario: Mapped[str] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
