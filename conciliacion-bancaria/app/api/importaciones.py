"""Importación de estados de cuenta y libro mayor: vista previa, confirmación, historial."""
import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import select

from app.api.deps import DB, Usuario
from app.core import config
from app.importers.columnas import sinonimos
from app.importers.lectores import ErrorImportacion
from app.models import CuentaBancaria, Importacion
from app.schemas import AnulacionIn, ImportacionOut
from app.services import importacion as svc

router = APIRouter(prefix="/importaciones", tags=["Importación"])

ETIQUETAS = {
    "fecha": "Fecha", "fecha_valuta": "Fecha valuta", "descripcion": "Descripción",
    "numero_operacion": "N.º operación / documento", "referencia": "Referencia", "importe": "Importe (con signo)",
    "cargo": "Cargo", "abono": "Abono", "saldo": "Saldo", "moneda": "Moneda", "voucher": "Voucher / CUO",
    "glosa": "Glosa", "medio_pago": "Medio de pago (Tabla 1)", "tercero": "Tercero", "cuenta": "Cuenta contable",
    "debe": "Debe", "haber": "Haber",
}


@router.get("/campos/{tipo}")
def campos(tipo: str):
    tipo = tipo.upper()
    if tipo not in ("BANCO", "LIBRO"):
        raise HTTPException(404, "Tipo inválido")
    return [{"campo": c, "etiqueta": ETIQUETAS.get(c, c)} for c in sinonimos(tipo)]


async def _leer(archivo: UploadFile) -> bytes:
    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(422, "El archivo está vacío")
    if len(contenido) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"El archivo supera {config.MAX_UPLOAD_MB} MB")
    return contenido


def _cuenta(db, cuenta_id: int) -> CuentaBancaria:
    cuenta = db.get(CuentaBancaria, cuenta_id)
    if not cuenta or not cuenta.activo:
        raise HTTPException(404, "Cuenta bancaria no encontrada o inactiva")
    return cuenta


def _mapeo(texto: str | None) -> dict[int, str] | None:
    if not texto:
        return None
    try:
        datos = json.loads(texto)
        return {int(k): str(v) for k, v in datos.items() if v}
    except (ValueError, AttributeError):
        raise HTTPException(422, "Mapeo de columnas inválido")


def _tipo(tipo: str) -> str:
    tipo = tipo.upper()
    if tipo not in ("BANCO", "LIBRO"):
        raise HTTPException(422, "El tipo debe ser BANCO o LIBRO")
    return tipo


def _serializar_registro(r: dict) -> dict:
    return {k: (str(v) if v is not None and k in ("importe", "saldo", "debe", "haber") else
                v.isoformat() if hasattr(v, "isoformat") and v is not None else v)
            for k, v in r.items() if k != "hash"}


@router.post("/vista-previa")
async def vista_previa(
    db: DB,
    archivo: Annotated[UploadFile, File()],
    cuenta_id: Annotated[int, Form()],
    tipo: Annotated[str, Form()],
    anio: Annotated[int | None, Form()] = None,
    invertir_signo: Annotated[bool, Form()] = False,
    mapeo: Annotated[str | None, Form()] = None,
    limite: Annotated[int, Form()] = 500,
):
    tipo = _tipo(tipo)
    cuenta = _cuenta(db, cuenta_id)
    contenido = await _leer(archivo)
    try:
        res = svc.analizar_para_cuenta(db, cuenta, archivo.filename or "archivo", contenido, tipo,
                                       mapeo_manual=_mapeo(mapeo), anio=anio, invertir_signo=invertir_signo)
    except ErrorImportacion as exc:
        raise HTTPException(422, str(exc))
    previa = svc.importacion_previa(db, cuenta.id, tipo, svc.hash_archivo(contenido))
    ingresos = sum(r["importe"] for r in res.registros if r["importe"] > 0)
    egresos = -sum(r["importe"] for r in res.registros if r["importe"] < 0)
    dup_archivo = sum(1 for r in res.registros if r["duplicado"] and r["duplicado"]["origen"] == "ARCHIVO")
    dup_base = sum(1 for r in res.registros if r["duplicado"] and r["duplicado"]["origen"] == "BASE")
    return {
        "formato": res.formato,
        "metodo": res.metodo,
        "fila_encabezado": res.fila_encabezado,
        "encabezados": res.encabezados,
        "mapeo": {str(k): v for k, v in res.mapeo.items()},
        "campos": campos(tipo),
        "resumen": {
            "registros": len(res.registros), "errores": len(res.errores),
            "duplicados_archivo": dup_archivo, "duplicados_base": dup_base,
            "ingresos": str(ingresos), "egresos": str(egresos), "neto": str(ingresos - egresos),
            "fecha_desde": res.fecha_desde.isoformat() if res.fecha_desde else None,
            "fecha_hasta": res.fecha_hasta.isoformat() if res.fecha_hasta else None,
            "saldo_inicial": str(res.saldo_inicial) if res.saldo_inicial is not None else None,
            "saldo_final": str(res.saldo_final) if res.saldo_final is not None else None,
            "saldos_consistentes": res.saldos_consistentes,
            "filas_filtradas": res.filas_filtradas,
        },
        "archivo_ya_importado": {"id": previa.id, "fecha": previa.creado_en.isoformat()} if previa else None,
        "advertencias": res.advertencias,
        "errores": res.errores[:200],
        "descuadres_saldo": res.descuadres_saldo,
        "registros": [_serializar_registro(r) for r in res.registros[:max(1, min(limite, 5000))]],
    }


@router.post("", response_model=ImportacionOut, status_code=201)
async def importar(
    db: DB,
    usuario: Usuario,
    archivo: Annotated[UploadFile, File()],
    cuenta_id: Annotated[int, Form()],
    tipo: Annotated[str, Form()],
    anio: Annotated[int | None, Form()] = None,
    invertir_signo: Annotated[bool, Form()] = False,
    mapeo: Annotated[str | None, Form()] = None,
    accion_duplicados: Annotated[str, Form()] = "marcar",
    forzar: Annotated[bool, Form()] = False,
):
    tipo = _tipo(tipo)
    cuenta = _cuenta(db, cuenta_id)
    contenido = await _leer(archivo)
    try:
        return svc.confirmar(db, cuenta, archivo.filename or "archivo", contenido, tipo, usuario,
                             mapeo_manual=_mapeo(mapeo), anio=anio, invertir_signo=invertir_signo,
                             accion_duplicados=accion_duplicados, forzar=forzar)
    except svc.ConflictoImportacion as exc:
        raise HTTPException(409, str(exc))
    except ErrorImportacion as exc:
        raise HTTPException(422, str(exc))


@router.get("", response_model=list[ImportacionOut])
def listar(db: DB, empresa_id: int | None = None, cuenta_id: int | None = None, tipo: str | None = None,
           limite: int = 200):
    q = select(Importacion).order_by(Importacion.id.desc()).limit(min(limite, 1000))
    if cuenta_id:
        q = q.where(Importacion.cuenta_bancaria_id == cuenta_id)
    if empresa_id:
        q = q.join(CuentaBancaria).where(CuentaBancaria.empresa_id == empresa_id)
    if tipo:
        q = q.where(Importacion.tipo == tipo.upper())
    return db.scalars(q).all()


@router.get("/{importacion_id}")
def detalle(importacion_id: int, db: DB):
    imp = db.get(Importacion, importacion_id)
    if not imp:
        raise HTTPException(404, "Importación no encontrada")
    datos = ImportacionOut.model_validate(imp).model_dump(mode="json")
    datos["mapeo"] = json.loads(imp.mapeo) if imp.mapeo else None
    datos["incidencias"] = json.loads(imp.advertencias) if imp.advertencias else None
    return datos


@router.post("/{importacion_id}/anular", response_model=ImportacionOut)
def anular(importacion_id: int, datos: AnulacionIn, db: DB, usuario: Usuario):
    imp = db.get(Importacion, importacion_id)
    if not imp:
        raise HTTPException(404, "Importación no encontrada")
    try:
        return svc.anular(db, imp, datos.motivo, usuario)
    except ErrorImportacion as exc:
        raise HTTPException(409, str(exc))
