"""Contratos de la API."""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.utils import ruc_valido


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Empresas -------------------------------------------------------------
class EmpresaIn(BaseModel):
    ruc: str = Field(min_length=11, max_length=11)
    razon_social: str = Field(min_length=3, max_length=200)
    nombre_comercial: str | None = Field(default=None, max_length=200)
    activo: bool = True

    @field_validator("ruc")
    @classmethod
    def _ruc(cls, v: str) -> str:
        v = v.strip()
        if not ruc_valido(v):
            raise ValueError("RUC inválido (11 dígitos con dígito verificador correcto)")
        return v

    @field_validator("razon_social")
    @classmethod
    def _rs(cls, v: str) -> str:
        return v.strip().upper()


class EmpresaOut(_ORM):
    id: int
    ruc: str
    razon_social: str
    nombre_comercial: str | None
    activo: bool
    creado_en: datetime | None


# --- Catálogos ------------------------------------------------------------
class BancoIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=20)
    nombre: str = Field(min_length=3, max_length=120)
    codigo_sunat: str | None = Field(default=None, max_length=4)


class BancoOut(_ORM):
    id: int
    codigo: str
    nombre: str
    codigo_sunat: str | None
    activo: bool


class MonedaOut(_ORM):
    codigo: str
    nombre: str
    simbolo: str


# --- Cuentas bancarias -----------------------------------------------------
class CuentaIn(BaseModel):
    empresa_id: int
    banco_id: int
    moneda: str = Field(min_length=3, max_length=3)
    numero_cuenta: str = Field(min_length=5, max_length=30)
    cci: str | None = Field(default=None, max_length=20)
    cuenta_contable: str = Field(min_length=3, max_length=12, pattern=r"^10\d+$")
    descripcion: str | None = Field(default=None, max_length=200)
    activo: bool = True

    @field_validator("cci")
    @classmethod
    def _cci(cls, v: str | None) -> str | None:
        if v:
            v = v.replace("-", "").replace(" ", "")
            if not (v.isdigit() and len(v) == 20):
                raise ValueError("El CCI debe tener 20 dígitos")
        return v or None


class ConfiguracionIn(BaseModel):
    tolerancia_dias: int = Field(ge=0, le=60)
    tolerancia_importe: Decimal = Field(ge=0, le=Decimal("1000"))
    umbral_auto_confirmacion: int = Field(ge=50, le=100)
    umbral_sugerencia: int = Field(ge=10, le=100)
    max_elementos_combinacion: int = Field(ge=1, le=8)
    usar_numero_operacion: bool = True


class ConfiguracionOut(ConfiguracionIn, _ORM):
    id: int
    cuenta_bancaria_id: int


class CuentaOut(_ORM):
    id: int
    empresa_id: int
    banco_id: int
    banco: BancoOut
    moneda: str
    numero_cuenta: str
    cci: str | None
    cuenta_contable: str
    descripcion: str | None
    activo: bool


# --- Importaciones y movimientos -------------------------------------------
class ImportacionOut(_ORM):
    id: int
    cuenta_bancaria_id: int
    tipo: str
    nombre_archivo: str
    formato: str
    fecha_desde: date | None
    fecha_hasta: date | None
    total_registros: int
    total_duplicados: int
    total_omitidos: int
    total_ingresos: Decimal
    total_egresos: Decimal
    saldo_inicial: Decimal | None
    saldo_final: Decimal | None
    estado: str
    usuario: str
    motivo_anulacion: str | None
    creado_en: datetime | None


class MovimientoBancoOut(_ORM):
    id: int
    cuenta_bancaria_id: int
    importacion_id: int
    fecha: date
    fecha_valuta: date | None
    descripcion: str
    numero_operacion: str | None
    referencia: str | None
    importe: Decimal
    moneda: str
    saldo: Decimal | None
    categoria: str
    posible_duplicado: bool
    motivo_duplicado: str | None
    duplicado_de_id: int | None
    estado_conciliacion: str
    fila_origen: int | None


class MovimientoLibroOut(_ORM):
    id: int
    cuenta_bancaria_id: int
    importacion_id: int
    fecha: date
    voucher: str | None
    glosa: str
    numero_operacion: str | None
    medio_pago: str | None
    tercero: str | None
    cuenta_contable: str | None
    debe: Decimal
    haber: Decimal
    importe: Decimal
    moneda: str
    posible_duplicado: bool
    motivo_duplicado: str | None
    duplicado_de_id: int | None
    estado_conciliacion: str
    fila_origen: int | None


class DecisionDuplicado(BaseModel):
    decision: str = Field(pattern="^(EXCLUIR|MANTENER|RESTAURAR)$")
    comentario: str | None = Field(default=None, max_length=200)


class AnulacionIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=255)


class AuditOut(_ORM):
    id: int
    fecha: datetime
    usuario: str
    empresa_id: int | None
    entidad: str
    entidad_id: int | None
    accion: str
    detalle: str | None
    datos: str | None
