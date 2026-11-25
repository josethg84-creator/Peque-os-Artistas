"""API del analizador contable: asistente de importación, lotes, plantillas y reglas."""
import csv
import io
import json
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import DB, Usuario
from app.contable import archivos, servicio, trabajos
from app.contable.campos import SISTEMAS_ORIGEN, TIPOS, describir_tipo
from app.contable.observaciones import catalogo_publico
from app.core import auditoria, config
from app.core.database import SessionLocal
from app.importers.lectores import ErrorImportacion
from app.models import (CentroCosto, ConfiguracionContable, CuentaContable, DocumentoRegistro, Empresa, LineaDiario,
                        LoteContable, ObservacionImportacion, PlantillaImportacion, ReglaDestino, SaldoCuenta,
                        Severidad, Tercero, TipoCambio)

router = APIRouter(prefix="/contable", tags=["Analizador contable"])


def _error(exc: Exception):
    status = getattr(exc, "status", 422)
    raise HTTPException(status, str(exc))


# ------------------------------------------------------------------ catálogo
@router.get("/catalogo")
def catalogo():
    return {
        "tipos": [describir_tipo(t) for t in TIPOS],
        "sistemas": [{"clave": k, "nombre": v} for k, v in SISTEMAS_ORIGEN.items()],
        "observaciones": catalogo_publico(),
        "periodos": [{"valor": 0, "nombre": "00 · Apertura"}] + [{"valor": m, "nombre": f"{m:02d}"} for m in range(1, 13)]
                    + [{"valor": 13, "nombre": "13 · Cierre"}],
    }


# ------------------------------------------------------------------ asistente
class ParametrosIn(BaseModel):
    empresa_id: int
    tipo: str
    ejercicio: int | None = Field(default=None, ge=1990, le=2100)
    periodo: int | None = Field(default=None, ge=0, le=13)
    sistema_origen: str = "GENERICO"
    hoja: str | None = None
    fila_encabezado: int = Field(default=1, ge=0)
    filas_encabezado: int = Field(default=1, ge=1, le=2)
    delimitador: str = "AUTO"
    separador_decimal: str = "AUTO"
    formato_fecha: str = "AUTO"
    mapeo: dict[str, int] = {}
    importacion_completa: bool = True
    plantilla_id: int | None = None


class ConfirmacionIn(ParametrosIn):
    confirmar_criticos: bool = False
    motivo_criticos: str | None = Field(default=None, max_length=255)
    reemplazar_previos: bool = False
    guardar_plantilla: str | None = Field(default=None, max_length=120)


def _parametros(token: str, datos: ParametrosIn) -> servicio.Parametros:
    campos = {k: v for k, v in datos.model_dump().items() if k in servicio.Parametros.__dataclass_fields__}
    return servicio.Parametros(token=token, **campos)


def _verificar_token(token: str, empresa_id: int | None = None) -> dict:
    try:
        m = archivos.meta(token)
    except ErrorImportacion as exc:
        raise HTTPException(404, str(exc))
    if empresa_id is not None and m["empresa_id"] != empresa_id:
        raise HTTPException(403, "El archivo pertenece a otra empresa.")
    return m


@router.post("/archivos", status_code=201)
async def subir(db: DB, usuario: Usuario, archivo: Annotated[UploadFile, File()],
                empresa_id: Annotated[int, Form()]):
    if not db.get(Empresa, empresa_id):
        raise HTTPException(404, "Empresa no encontrada")
    contenido = await archivo.read()
    if len(contenido) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"El archivo supera {config.MAX_UPLOAD_MB} MB")
    try:
        return archivos.guardar(contenido, archivo.filename or "archivo", empresa_id, usuario)
    except ErrorImportacion as exc:
        raise HTTPException(422, str(exc))


@router.get("/archivos/{token}/vista-previa")
def vista_previa(token: str, tipo: str, hoja: str | None = None, delimitador: str = "AUTO"):
    _verificar_token(token)
    try:
        return servicio.vista_previa(token, tipo, hoja, delimitador)
    except (ErrorImportacion, servicio.ErrorContable) as exc:
        _error(exc)


@router.post("/archivos/{token}/homologacion")
def homologacion(token: str, datos: ParametrosIn, db: DB):
    _verificar_token(token, datos.empresa_id)
    if datos.tipo not in TIPOS:
        raise HTTPException(422, "Tipo de información no válido")
    try:
        return servicio.homologar(db, _parametros(token, datos))
    except (ErrorImportacion, servicio.ErrorContable) as exc:
        _error(exc)


def _lanzar(tipo: str, fn):
    def ejecutar(avance):
        with SessionLocal() as db:
            return fn(db, avance)
    return trabajos.crear(tipo, ejecutar)


@router.post("/archivos/{token}/validacion", status_code=202)
def validacion(token: str, datos: ParametrosIn):
    _verificar_token(token, datos.empresa_id)
    p = _parametros(token, datos)
    try:
        p.verificar()
    except servicio.ErrorContable as exc:
        _error(exc)
    return _lanzar("VALIDACION", lambda db, avance: servicio.validar_y_guardar(db, p, avance))


@router.post("/archivos/{token}/confirmacion", status_code=202)
def confirmacion(token: str, datos: ConfirmacionIn, usuario: Usuario):
    _verificar_token(token, datos.empresa_id)
    p = _parametros(token, datos)
    try:
        p.verificar()
    except servicio.ErrorContable as exc:
        _error(exc)
    return _lanzar("CONFIRMACION", lambda db, avance: servicio.confirmar(
        db, p, usuario, avance, confirmar_criticos=datos.confirmar_criticos, motivo_criticos=datos.motivo_criticos,
        reemplazar_previos=datos.reemplazar_previos, guardar_plantilla=datos.guardar_plantilla))


@router.get("/trabajos/{trabajo_id}")
def trabajo(trabajo_id: str):
    t = trabajos.obtener(trabajo_id)
    if not t:
        raise HTTPException(404, "Trabajo no encontrado o expirado")
    return t


def _paginar_obs(lista: list[dict], severidad, codigo, texto, pagina, por_pagina):
    if severidad:
        lista = [o for o in lista if o["severidad"] == severidad.upper()]
    if codigo:
        lista = [o for o in lista if o["codigo"] == codigo.upper()]
    if texto:
        t = texto.lower()
        lista = [o for o in lista if t in " ".join(str(o.get(k) or "") for k in ("mensaje", "cuenta", "asiento",
                                                                                  "documento", "valor")).lower()]
    por_pagina = max(1, min(por_pagina, 500))
    inicio = (max(pagina, 1) - 1) * por_pagina
    return {"total": len(lista), "pagina": pagina, "por_pagina": por_pagina, "items": lista[inicio:inicio + por_pagina]}


@router.get("/archivos/{token}/observaciones")
def observaciones_previas(token: str, severidad: str | None = None, codigo: str | None = None,
                         texto: str | None = None, pagina: int = 1, por_pagina: int = 100):
    _verificar_token(token)
    try:
        return _paginar_obs(servicio.observaciones_validadas(token), severidad, codigo, texto, pagina, por_pagina)
    except servicio.ErrorContable as exc:
        _error(exc)


@router.delete("/archivos/{token}", status_code=204)
def descartar(token: str):
    archivos.descartar(token)


# ------------------------------------------------------------------ lotes
@router.get("/lotes")
def listar_lotes(db: DB, empresa_id: int, tipo: str | None = None, ejercicio: int | None = None,
                 estado: str | None = None, limite: int = 300):
    q = select(LoteContable).where(LoteContable.empresa_id == empresa_id).order_by(LoteContable.id.desc())
    if tipo:
        q = q.where(LoteContable.tipo_informacion == tipo)
    if ejercicio:
        q = q.where(LoteContable.ejercicio == ejercicio)
    if estado:
        q = q.where(LoteContable.estado == estado)
    return [servicio.lote_dict(x) for x in db.scalars(q.limit(min(limite, 1000)))]


def _lote(db, lote_id) -> LoteContable:
    lote = db.get(LoteContable, lote_id)
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    return lote


@router.get("/lotes/{lote_id}")
def obtener_lote(lote_id: int, db: DB):
    return servicio.lote_dict(_lote(db, lote_id))


def _consulta_obs(lote_id, severidad, codigo, texto):
    q = select(ObservacionImportacion).where(ObservacionImportacion.lote_id == lote_id)
    if severidad:
        q = q.where(ObservacionImportacion.severidad == severidad.upper())
    if codigo:
        q = q.where(ObservacionImportacion.codigo == codigo.upper())
    if texto:
        patron = f"%{texto}%"
        q = q.where(ObservacionImportacion.mensaje.ilike(patron) | ObservacionImportacion.cuenta.ilike(patron)
                    | ObservacionImportacion.asiento.ilike(patron) | ObservacionImportacion.documento.ilike(patron))
    return q


def _obs_dict(o: ObservacionImportacion) -> dict:
    return {c.key: getattr(o, c.key) for c in ObservacionImportacion.__table__.columns}


@router.get("/lotes/{lote_id}/observaciones")
def observaciones_lote(lote_id: int, db: DB, severidad: str | None = None, codigo: str | None = None,
                       texto: str | None = None, pagina: int = 1, por_pagina: int = 100):
    _lote(db, lote_id)
    q = _consulta_obs(lote_id, severidad, codigo, texto)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    por_pagina = max(1, min(por_pagina, 500))
    orden = {s: i for s, i in Severidad.ORDEN.items()}
    from sqlalchemy import case
    items = db.scalars(q.order_by(case(orden, value=ObservacionImportacion.severidad), ObservacionImportacion.codigo,
                                  ObservacionImportacion.fila)
                       .offset((max(pagina, 1) - 1) * por_pagina).limit(por_pagina)).all()
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina, "items": [_obs_dict(o) for o in items]}


@router.get("/lotes/{lote_id}/observaciones.csv")
def exportar_observaciones(lote_id: int, db: DB):
    lote = _lote(db, lote_id)
    buf = io.StringIO()
    buf.write("﻿")  # BOM para que Excel reconozca UTF-8
    w = csv.writer(buf, delimiter=";")
    cols = ["severidad", "codigo", "archivo", "hoja", "fila", "cuenta", "asiento", "documento", "campo", "valor",
            "mensaje", "recomendacion"]
    w.writerow([c.capitalize() for c in cols])
    for o in db.scalars(select(ObservacionImportacion).where(ObservacionImportacion.lote_id == lote_id)
                        .order_by(ObservacionImportacion.id)):
        w.writerow([getattr(o, c) if getattr(o, c) is not None else "" for c in cols])
    nombre = f"observaciones_lote_{lote.id}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


_TABLA_REGISTROS = {"DIARIO": LineaDiario, "MAYOR": LineaDiario, "BALANCE": SaldoCuenta,
                    "SALDOS_INICIALES": SaldoCuenta, "COMPRAS": DocumentoRegistro, "VENTAS": DocumentoRegistro,
                    "CXC": DocumentoRegistro, "CXP": DocumentoRegistro, "PLAN_CUENTAS": CuentaContable,
                    "CLIENTES": Tercero, "PROVEEDORES": Tercero, "CENTROS_COSTO": CentroCosto,
                    "TIPOS_CAMBIO": TipoCambio}


def _fila_json(obj) -> dict:
    out = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.key)
        out[c.key] = str(v) if isinstance(v, Decimal) else v.isoformat() if isinstance(v, date) else v
    return out


@router.get("/lotes/{lote_id}/registros")
def registros_lote(lote_id: int, db: DB, pagina: int = 1, por_pagina: int = 100):
    lote = _lote(db, lote_id)
    Modelo = _TABLA_REGISTROS[lote.tipo_informacion]
    q = select(Modelo).where(Modelo.lote_id == lote_id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    por_pagina = max(1, min(por_pagina, 500))
    items = db.scalars(q.order_by(Modelo.id).offset((max(pagina, 1) - 1) * por_pagina).limit(por_pagina)).all()
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina, "items": [_fila_json(x) for x in items]}


class AnulacionIn(BaseModel):
    motivo: str = Field(min_length=5, max_length=255)


@router.post("/lotes/{lote_id}/anular")
def anular_lote(lote_id: int, datos: AnulacionIn, db: DB, usuario: Usuario):
    try:
        return servicio.anular(db, _lote(db, lote_id), datos.motivo, usuario)
    except servicio.ErrorContable as exc:
        _error(exc)


# ------------------------------------------------------------------ plantillas
@router.get("/plantillas")
def listar_plantillas(db: DB, empresa_id: int, tipo: str | None = None):
    q = select(PlantillaImportacion).where((PlantillaImportacion.empresa_id == empresa_id)
                                           | (PlantillaImportacion.empresa_id.is_(None)))
    if tipo:
        q = q.where(PlantillaImportacion.tipo_informacion == tipo)
    return [servicio._plantilla_dict(x) for x in db.scalars(q.order_by(PlantillaImportacion.tipo_informacion,
                                                                       PlantillaImportacion.nombre))]


class PlantillaIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    mapeo: dict[str, str] | None = None
    opciones: dict | None = None


@router.put("/plantillas/{plantilla_id}")
def actualizar_plantilla(plantilla_id: int, datos: PlantillaIn, db: DB, usuario: Usuario):
    pl = db.get(PlantillaImportacion, plantilla_id)
    if not pl:
        raise HTTPException(404, "Plantilla no encontrada")
    antes = auditoria.instantanea(pl, ["nombre", "mapeo", "opciones"])
    pl.nombre = datos.nombre.strip()
    if datos.mapeo is not None:
        invalidos = set(datos.mapeo) - set(TIPOS[pl.tipo_informacion].campos)
        if invalidos:
            raise HTTPException(422, f"Campos no válidos: {', '.join(sorted(invalidos))}")
        pl.mapeo = json.dumps(datos.mapeo, ensure_ascii=False)
    if datos.opciones is not None:
        pl.opciones = json.dumps(datos.opciones)
    pl.usuario = usuario
    auditoria.registrar(db, usuario=usuario, entidad="plantilla_importacion", entidad_id=pl.id, accion="MODIFICAR",
                        antes=antes, despues=auditoria.instantanea(pl, ["nombre", "mapeo", "opciones"]),
                        empresa_id=pl.empresa_id)
    db.commit()
    return servicio._plantilla_dict(pl)


@router.delete("/plantillas/{plantilla_id}", status_code=204)
def eliminar_plantilla(plantilla_id: int, db: DB, usuario: Usuario):
    pl = db.get(PlantillaImportacion, plantilla_id)
    if not pl:
        raise HTTPException(404, "Plantilla no encontrada")
    for lote in db.scalars(select(LoteContable).where(LoteContable.plantilla_id == plantilla_id)):
        lote.plantilla_id = None  # el lote conserva su propio mapeo
    auditoria.registrar(db, usuario=usuario, entidad="plantilla_importacion", entidad_id=pl.id, accion="ELIMINAR",
                        antes=auditoria.instantanea(pl, ["nombre", "sistema_origen", "tipo_informacion", "mapeo"]),
                        empresa_id=pl.empresa_id)
    db.delete(pl)
    db.commit()


# ------------------------------------------------------------------ configuración y reglas
class ConfiguracionContableIn(BaseModel):
    tolerancia_descuadre: Decimal = Field(ge=0, le=1000)
    materialidad: Decimal = Field(ge=0)
    tolerancia_tipo_cambio: Decimal = Field(ge=0, le=1)
    tolerancia_conversion: Decimal = Field(ge=0, le=1000)
    usa_clase_9: bool = True
    modo_destino: str = Field(pattern="^(MISMO_ASIENTO|PERIODO|NO_APLICA)$")
    prefijos_destinables: str = Field(max_length=120, pattern=r"^[\d,\s]*$")
    prefijo_destino: str = Field(max_length=60, pattern=r"^[\d,\s]+$")
    cuenta_cargas_imputables: str = Field(max_length=20, pattern=r"^\d+$")
    exigir_centro_costo_destino: bool = False
    validar_cuenta_78: bool = True
    prefijos_sin_movimiento: str = Field(default="", max_length=120, pattern=r"^[\d,\s]*$")


def _config(db, empresa_id) -> ConfiguracionContable:
    if not db.get(Empresa, empresa_id):
        raise HTTPException(404, "Empresa no encontrada")
    cfg = db.scalar(select(ConfiguracionContable).where(ConfiguracionContable.empresa_id == empresa_id))
    if cfg is None:
        cfg = ConfiguracionContable(empresa_id=empresa_id)
        db.add(cfg)
        db.commit()
    return cfg


@router.get("/configuracion/{empresa_id}")
def obtener_configuracion(empresa_id: int, db: DB):
    return _fila_json(_config(db, empresa_id))


@router.put("/configuracion/{empresa_id}")
def actualizar_configuracion(empresa_id: int, datos: ConfiguracionContableIn, db: DB, usuario: Usuario):
    cfg = _config(db, empresa_id)
    antes = auditoria.instantanea(cfg)
    valores = datos.model_dump()
    for k in ("prefijos_destinables", "prefijo_destino", "prefijos_sin_movimiento"):
        valores[k] = ",".join(p.strip() for p in valores[k].split(",") if p.strip())
    for k, v in valores.items():
        setattr(cfg, k, v)
    auditoria.registrar(db, usuario=usuario, entidad="configuracion_contable", entidad_id=cfg.id, accion="MODIFICAR",
                        antes=antes, despues=auditoria.instantanea(cfg), empresa_id=empresa_id)
    db.commit()
    return _fila_json(cfg)


class ReglaIn(BaseModel):
    empresa_id: int
    prefijo_origen: str = Field(min_length=1, max_length=20, pattern=r"^\d+$")
    destino_debe: str = Field(default="", max_length=60, pattern=r"^[\d,\s]*$")
    destino_haber: str = Field(default="", max_length=60, pattern=r"^[\d,\s]*$")
    requiere_centro_costo: bool = False
    activa: bool = True
    descripcion: str | None = Field(default=None, max_length=200)


@router.get("/reglas-destino")
def listar_reglas(db: DB, empresa_id: int):
    return [_fila_json(r) for r in db.scalars(select(ReglaDestino).where(ReglaDestino.empresa_id == empresa_id)
                                              .order_by(ReglaDestino.prefijo_origen))]


@router.post("/reglas-destino", status_code=201)
def crear_regla(datos: ReglaIn, db: DB, usuario: Usuario):
    _config(db, datos.empresa_id)
    if not (datos.destino_debe.strip() or datos.destino_haber.strip()):
        raise HTTPException(422, "Indique al menos un destino (debe o haber)")
    r = ReglaDestino(**datos.model_dump())
    db.add(r)
    db.flush()
    auditoria.registrar(db, usuario=usuario, entidad="regla_destino", entidad_id=r.id, accion="CREAR",
                        despues=auditoria.instantanea(r), empresa_id=datos.empresa_id)
    db.commit()
    return _fila_json(r)


@router.put("/reglas-destino/{regla_id}")
def actualizar_regla(regla_id: int, datos: ReglaIn, db: DB, usuario: Usuario):
    r = db.get(ReglaDestino, regla_id)
    if not r:
        raise HTTPException(404, "Regla no encontrada")
    antes = auditoria.instantanea(r)
    for k, v in datos.model_dump().items():
        setattr(r, k, v)
    auditoria.registrar(db, usuario=usuario, entidad="regla_destino", entidad_id=r.id, accion="MODIFICAR",
                        antes=antes, despues=auditoria.instantanea(r), empresa_id=r.empresa_id)
    db.commit()
    return _fila_json(r)


@router.delete("/reglas-destino/{regla_id}", status_code=204)
def eliminar_regla(regla_id: int, db: DB, usuario: Usuario):
    r = db.get(ReglaDestino, regla_id)
    if not r:
        raise HTTPException(404, "Regla no encontrada")
    auditoria.registrar(db, usuario=usuario, entidad="regla_destino", entidad_id=r.id, accion="ELIMINAR",
                        antes=auditoria.instantanea(r), empresa_id=r.empresa_id)
    db.delete(r)
    db.commit()


# ------------------------------------------------------------------ resumen de datos cargados
@router.get("/resumen/{empresa_id}")
def resumen_empresa(empresa_id: int, db: DB):
    """Qué información contable tiene cargada la empresa (para el panel del analizador)."""
    maestros = {
        "PLAN_CUENTAS": db.scalar(select(func.count()).select_from(CuentaContable).where(CuentaContable.empresa_id == empresa_id)),
        "CENTROS_COSTO": db.scalar(select(func.count()).select_from(CentroCosto).where(CentroCosto.empresa_id == empresa_id)),
        "CLIENTES": db.scalar(select(func.count()).select_from(Tercero).where(Tercero.empresa_id == empresa_id, Tercero.rol == "CLIENTE")),
        "PROVEEDORES": db.scalar(select(func.count()).select_from(Tercero).where(Tercero.empresa_id == empresa_id, Tercero.rol == "PROVEEDOR")),
        "TIPOS_CAMBIO": db.scalar(select(func.count()).select_from(TipoCambio).where(TipoCambio.empresa_id == empresa_id)),
    }
    filas = db.execute(select(LoteContable.tipo_informacion, LoteContable.ejercicio, LoteContable.periodo,
                              func.count(), func.sum(LoteContable.registros_importados), func.sum(LoteContable.obs_critico),
                              func.sum(LoteContable.obs_alto))
                       .where(LoteContable.empresa_id == empresa_id, LoteContable.estado == "ACTIVO")
                       .group_by(LoteContable.tipo_informacion, LoteContable.ejercicio, LoteContable.periodo)).all()
    return {"maestros": maestros, "transaccional": [
        {"tipo": t, "tipo_nombre": TIPOS[t].nombre, "ejercicio": e, "periodo": p, "lotes": n, "registros": r or 0,
         "criticos": c or 0, "altos": a or 0} for t, e, p, n, r, c, a in filas if TIPOS[t].transaccional]}


@router.get("/maestros/{tipo}")
def consultar_maestro(tipo: str, db: DB, empresa_id: int, texto: str | None = None, limite: int = 500):
    modelos = {"PLAN_CUENTAS": (CuentaContable, CuentaContable.codigo, [CuentaContable.codigo, CuentaContable.descripcion]),
               "CENTROS_COSTO": (CentroCosto, CentroCosto.codigo, [CentroCosto.codigo, CentroCosto.descripcion]),
               "CLIENTES": (Tercero, Tercero.razon_social, [Tercero.numero_documento, Tercero.razon_social]),
               "PROVEEDORES": (Tercero, Tercero.razon_social, [Tercero.numero_documento, Tercero.razon_social]),
               "TIPOS_CAMBIO": (TipoCambio, TipoCambio.fecha.desc(), [TipoCambio.moneda])}
    if tipo not in modelos:
        raise HTTPException(404, "Maestro no válido")
    Modelo, orden, buscables = modelos[tipo]
    q = select(Modelo).where(Modelo.empresa_id == empresa_id)
    if tipo in ("CLIENTES", "PROVEEDORES"):
        q = q.where(Tercero.rol == ("CLIENTE" if tipo == "CLIENTES" else "PROVEEDOR"))
    if texto:
        patron = f"%{texto}%"
        cond = buscables[0].ilike(patron)
        for b in buscables[1:]:
            cond = cond | b.ilike(patron)
        q = q.where(cond)
    return [_fila_json(x) for x in db.scalars(q.order_by(orden).limit(min(limite, 5000)))]
