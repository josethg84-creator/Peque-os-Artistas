"""API del generador de anexos contables (fase 5). Todo se acota a `empresa_id`, al rol del usuario
(cabecera X-Usuario) y, si corresponde, a las cuentas que tiene asignadas. Los anexos leen los asientos
originales sin modificarlos."""
import json
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.anexos import auxiliares, catalogo, comparar, consultas, expresiones, exportar, flujo, generador, render
from app.anexos import datos as datos_mod
from app.api.deps import DB, Usuario
from app.contable import trabajos
from app.core import config
from app.core.database import SessionLocal
from app.importers.lectores import ErrorImportacion
from app.models import (AdjuntoAnexo, Anexo, AprobacionAnexo, AsignacionAnexo, AuditoriaAnexo, ComentarioAnexo,
                        ConciliacionAnexo, Empresa, ExportacionAnexos, FormulaPlantilla, GeneracionAnexos, HallazgoAnexo,
                        PlantillaAnexo, RegistroAuxiliar, ReglaPlantilla, RevisionAnexo, VersionAnexo)
from app.models.anexos import CATEGORIAS_ADJUNTO, ESTADOS_REVISION, TIPOS_REGISTRO

router = APIRouter(prefix="/anexos", tags=["Anexos contables"])


# ------------------------------------------------------------------ utilitarios
def _j(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def _fila(o, excluir=()):
    return {c.key: _j(getattr(o, c.key)) for c in o.__table__.columns if c.key not in excluir}


def _empresa(db, empresa_id) -> Empresa:
    e = db.get(Empresa, empresa_id)
    if not e:
        raise HTTPException(404, "Empresa no encontrada")
    return e


def _err(exc):
    if isinstance(exc, LookupError):
        raise HTTPException(404, str(exc).strip("'"))
    raise HTTPException(getattr(exc, "status", 422), str(exc))


def _permiso(db, empresa_id, usuario, accion) -> str:
    _empresa(db, empresa_id)
    try:
        return flujo.exigir(db, empresa_id, usuario, accion)
    except flujo.SinPermiso as exc:
        raise HTTPException(403, str(exc))


def _anexo(db, empresa_id, anexo_id, usuario) -> Anexo:
    a = db.get(Anexo, anexo_id)
    if not a or a.empresa_id != empresa_id:
        raise HTTPException(404, "Anexo no encontrado")
    try:
        flujo.exigir_cuenta(db, empresa_id, usuario, a.cuenta)
    except flujo.SinPermiso as exc:
        raise HTTPException(403, str(exc))
    return a


def _corte(ejercicio: int | None, periodo: int | None, fecha_corte: date | None) -> tuple[int, int, date]:
    if fecha_corte and not ejercicio:
        ejercicio = fecha_corte.year
    if fecha_corte and not periodo:
        periodo = fecha_corte.month
    if not ejercicio or not periodo:
        raise HTTPException(422, "Indique el ejercicio y el periodo (o la fecha de corte).")
    return ejercicio, periodo, fecha_corte or datos_mod.fin_de_periodo(ejercicio, periodo)


def _mascara(db, empresa_id, usuario) -> bool:
    return not flujo.puede(db, empresa_id, usuario, "datos_personales")


# ------------------------------------------------------------------ sesión
@router.get("/mi-rol")
def mi_rol(db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    rol, abierto = flujo.rol(db, empresa_id, usuario)
    return {"usuario": usuario, "rol": rol, "modo_abierto": abierto,
            "permisos": sorted(a for a, roles in flujo.PERMISOS.items() if rol in roles),
            "cuentas_permitidas": flujo.cuentas_permitidas(db, empresa_id, usuario),
            "configuracion": generador.configuracion(db, empresa_id)}


# ------------------------------------------------------------------ plantillas y diseñador
def _plantilla_dict(db, p: PlantillaAnexo, detalle=True) -> dict:
    d = _fila(p, ("filtros", "rangos_antiguedad", "encabezado", "parametros"))
    if detalle:
        d.update(catalogo.snapshot(db, p))
    d["sistema"] = p.empresa_id is None
    return d


def _visible(p: PlantillaAnexo, empresa_id, usuario) -> bool:
    return p.empresa_id is None or (p.empresa_id == empresa_id and (p.compartida or p.creado_por == usuario or p.tipo != "PERSONALIZADA"))


@router.get("/plantillas")
def plantillas(db: DB, usuario: Usuario, empresa_id: int, especialidad: str | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    catalogo.sembrar(db)
    q = select(PlantillaAnexo).where(or_(PlantillaAnexo.empresa_id.is_(None), PlantillaAnexo.empresa_id == empresa_id))
    if especialidad:
        q = q.where(PlantillaAnexo.especialidad == especialidad)
    return [_plantilla_dict(db, p, detalle=False) for p in db.scalars(q.order_by(PlantillaAnexo.empresa_id.is_(None), PlantillaAnexo.cuentas, PlantillaAnexo.codigo))
            if _visible(p, empresa_id, usuario)]


@router.get("/plantillas/{plantilla_id}")
def plantilla(plantilla_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    p = db.get(PlantillaAnexo, plantilla_id)
    if not p or not _visible(p, empresa_id, usuario):
        raise HTTPException(404, "Plantilla no encontrada")
    return _plantilla_dict(db, p)


@router.get("/campos/{especialidad}")
def campos(especialidad: str, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    if especialidad not in catalogo.PROPIOS:
        raise HTTPException(404, "Especialidad no encontrada")
    return {"campos": [{"campo": c, "titulo": t, "tipo": tp} for c, t, tp in catalogo.campos(especialidad)],
            "funciones": sorted(expresiones.FUNCIONES), "operadores": list(render.OPERADORES),
            "especialidades": catalogo.ESPECIALIDADES}


class ColumnaIn(BaseModel):
    campo: str = Field(min_length=1, max_length=60)
    titulo: str | None = Field(default=None, max_length=80)
    visible: bool = True
    total: bool = False


class FormulaIn(BaseModel):
    campo: str = Field(min_length=1, max_length=60)
    titulo: str = Field(min_length=1, max_length=80)
    expresion: str = Field(min_length=1, max_length=500)
    tipo: str = Field(default="importe", pattern="^(importe|texto|entero|pct)$")


class ReglaIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=40)
    descripcion: str = Field(min_length=3, max_length=255)
    tipo: str = Field(pattern="^(CONDICION_FILA|UMBRAL_DIFERENCIA|SALDO_ANTIGUO)$")
    expresion: str | None = Field(default=None, max_length=500)
    parametros: dict = {}
    severidad: str = Field(default="MEDIA", pattern="^(ALTA|MEDIA|BAJA|INFORMATIVA)$")


class PlantillaIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    codigo: str | None = Field(default=None, max_length=40)
    descripcion: str | None = None
    especialidad: str
    cuentas: str = Field(default="", max_length=400)
    columnas: list[ColumnaIn] = Field(min_length=1, max_length=60)
    formulas: list[FormulaIn] = []
    reglas: list[ReglaIn] = []
    agrupar_por: list[str] = []
    subtotales: list[str] = []
    filtros: list[dict] = []
    orden: list[str] = []
    rangos_antiguedad: list[list[int | None]] | None = None
    encabezado: dict = {}
    orientacion: str = Field(default="HORIZONTAL", pattern="^(HORIZONTAL|VERTICAL)$")
    usar_logo: bool = True
    compartida: bool = False


def _validar_plantilla(d: PlantillaIn):
    if d.especialidad not in catalogo.PROPIOS:
        raise HTTPException(422, "Especialidad no válida")
    disponibles = {c for c, _, _ in catalogo.campos(d.especialidad)}
    try:
        render.validar_formulas(d.especialidad, [f.model_dump() for f in d.formulas])
        todos = disponibles | {f.campo for f in d.formulas}
        for r in d.reglas:
            if r.tipo == "CONDICION_FILA":
                if not r.expresion:
                    raise expresiones.ErrorExpresion(f"La regla {r.codigo} requiere una expresión")
                expresiones.compilar(r.expresion, todos)
    except expresiones.ErrorExpresion as exc:
        raise HTTPException(422, str(exc))
    for c in d.columnas:
        if c.campo not in todos:
            raise HTTPException(422, f"Columna desconocida: {c.campo}")
    for campo in d.agrupar_por + [x.lstrip("-") for x in d.orden] + d.subtotales:
        if campo not in todos:
            raise HTTPException(422, f"Campo desconocido: {campo}")
    for f in d.filtros:
        if f.get("campo") not in todos or f.get("op", "=") not in render.OPERADORES:
            raise HTTPException(422, f"Filtro no válido: {f}")
    if d.rangos_antiguedad:
        previo = 0
        for i, r in enumerate(d.rangos_antiguedad):
            if len(r) != 2 or r[0] != previo + 1 or (r[1] is not None and r[1] < r[0]) or (r[1] is None and i != len(d.rangos_antiguedad) - 1):
                raise HTTPException(422, "Rangos de antigüedad: deben ser consecutivos desde 1 (p. ej. 1–30, 31–60 … 366–∞).")
            previo = r[1] or 0
    for pref in [x.strip() for x in d.cuentas.split(",") if x.strip()]:
        if not pref.isdigit():
            raise HTTPException(422, "Las cuentas deben ser prefijos numéricos separados por coma")


def _guardar_plantilla(db, p: PlantillaAnexo, d: PlantillaIn, usuario: str, puede_autorizar: bool):
    p.nombre, p.descripcion, p.especialidad = d.nombre, d.descripcion, d.especialidad
    p.cuentas = ",".join(x.strip() for x in d.cuentas.split(",") if x.strip())
    p.elemento = p.cuentas[:1] or None
    p.agrupar_por, p.subtotales = ",".join(d.agrupar_por) or None, ",".join(d.subtotales) or None
    p.orden = ",".join(d.orden) or None
    p.filtros = json.dumps(d.filtros) if d.filtros else None
    p.rangos_antiguedad = json.dumps(d.rangos_antiguedad or catalogo.RANGOS_DEFECTO)
    p.encabezado = json.dumps({k: str(v)[:300] for k, v in d.encabezado.items() if k in ("titulo", "subtitulo", "nota")})
    p.orientacion, p.usar_logo, p.compartida = d.orientacion, d.usar_logo, d.compartida
    p.autorizada = puede_autorizar
    p.autorizada_por = usuario if puede_autorizar else None
    db.flush()
    catalogo.reemplazar_columnas(db, p, [c.model_dump() for c in d.columnas])
    for x in db.scalars(select(FormulaPlantilla).where(FormulaPlantilla.plantilla_id == p.id)):
        db.delete(x)
    for x in db.scalars(select(ReglaPlantilla).where(ReglaPlantilla.plantilla_id == p.id)):
        db.delete(x)
    db.flush()
    for i, f in enumerate(d.formulas):
        db.add(FormulaPlantilla(plantilla_id=p.id, campo=f.campo, titulo=f.titulo, expresion=f.expresion, tipo=f.tipo, orden=i))
    for r in d.reglas:
        db.add(ReglaPlantilla(plantilla_id=p.id, codigo=r.codigo, descripcion=r.descripcion, tipo=r.tipo, expresion=r.expresion,
                              parametros=json.dumps(r.parametros), severidad=r.severidad))


@router.post("/plantillas", status_code=201)
def crear_plantilla(datos: PlantillaIn, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "plantillas")
    _validar_plantilla(datos)
    codigo = (datos.codigo or f"P-{int(time.time() * 1000) % 10**10}").upper()
    if db.scalar(select(PlantillaAnexo).where(PlantillaAnexo.empresa_id == empresa_id, PlantillaAnexo.codigo == codigo)):
        raise HTTPException(409, "Ya existe una plantilla con ese código")
    p = PlantillaAnexo(empresa_id=empresa_id, codigo=codigo, nombre=datos.nombre, tipo="PERSONALIZADA", especialidad=datos.especialidad,
                       creado_por=usuario)
    db.add(p)
    db.flush()
    _guardar_plantilla(db, p, datos, usuario, rol in flujo.PERMISOS["autorizar_plantillas"])
    generador.auditar(db, empresa_id, usuario, "CREAR_PLANTILLA", "plantilla", p.id, datos.model_dump(), rol)
    db.commit()
    return _plantilla_dict(db, p)


@router.put("/plantillas/{plantilla_id}")
def editar_plantilla(plantilla_id: int, datos: PlantillaIn, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "plantillas")
    p = db.get(PlantillaAnexo, plantilla_id)
    if not p or p.empresa_id != empresa_id:
        raise HTTPException(404 if not p or p.empresa_id else 409,
                            "Las plantillas del catálogo no se editan: duplíquela para personalizarla." if p else "Plantilla no encontrada")
    if p.tipo == "PERSONALIZADA" and p.creado_por != usuario and rol not in flujo.PERMISOS["autorizar_plantillas"]:
        raise HTTPException(403, "Solo quien creó la plantilla o un supervisor puede modificarla")
    _validar_plantilla(datos)
    antes = catalogo.snapshot(db, p)
    _guardar_plantilla(db, p, datos, usuario, rol in flujo.PERMISOS["autorizar_plantillas"])
    p.version += 1
    generador.auditar(db, empresa_id, usuario, "EDITAR_PLANTILLA", "plantilla", p.id, {"antes": antes, "despues": datos.model_dump()}, rol)
    db.commit()
    return _plantilla_dict(db, p)


class DuplicarIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    codigo: str | None = Field(default=None, max_length=40)


@router.post("/plantillas/{plantilla_id}/duplicar", status_code=201)
def duplicar(plantilla_id: int, datos: DuplicarIn, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "plantillas")
    p = db.get(PlantillaAnexo, plantilla_id)
    if not p or not _visible(p, empresa_id, usuario):
        raise HTTPException(404, "Plantilla no encontrada")
    s = catalogo.snapshot(db, p)
    nuevo = PlantillaIn(nombre=datos.nombre, codigo=datos.codigo, especialidad=p.especialidad, cuentas=p.cuentas or "",
                        columnas=[ColumnaIn(**{k: c[k] for k in ("campo", "titulo", "visible", "total")}) for c in s["columnas"]],
                        formulas=[FormulaIn(**f) for f in s["formulas"]], reglas=[ReglaIn(**r) for r in s["reglas"]],
                        agrupar_por=s["agrupar_por"], subtotales=s["subtotales"], filtros=s["filtros"], orden=s["orden"],
                        rangos_antiguedad=s["rangos_antiguedad"], encabezado=s["encabezado"], orientacion=s["orientacion"],
                        usar_logo=s["usar_logo"])
    out = crear_plantilla(nuevo, db, usuario, empresa_id)
    q = db.get(PlantillaAnexo, out["id"])
    q.base_id, q.parametros = p.id, p.parametros
    db.commit()
    generador.auditar(db, empresa_id, usuario, "DUPLICAR_PLANTILLA", "plantilla", q.id, {"base": p.id}, rol)
    db.commit()
    return _plantilla_dict(db, q)


@router.post("/plantillas/{plantilla_id}/autorizar")
def autorizar_plantilla(plantilla_id: int, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "autorizar_plantillas")
    p = db.get(PlantillaAnexo, plantilla_id)
    if not p or p.empresa_id != empresa_id:
        raise HTTPException(404, "Plantilla no encontrada")
    p.autorizada, p.autorizada_por, p.compartida = True, usuario, True
    generador.auditar(db, empresa_id, usuario, "AUTORIZAR_PLANTILLA", "plantilla", p.id, None, rol)
    db.commit()
    return _plantilla_dict(db, p)


class ValidarIn(BaseModel):
    especialidad: str
    formulas: list[FormulaIn] = []
    expresion: str | None = None
    fila: dict | None = None


@router.post("/formulas/validar")
def validar_formula(datos: ValidarIn, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    try:
        render.validar_formulas(datos.especialidad, [f.model_dump() for f in datos.formulas])
        res = None
        if datos.expresion:
            campos_ = set(render.tipos(datos.especialidad)) | {f.campo for f in datos.formulas} | {"documento"}
            arbol = expresiones.compilar(datos.expresion, campos_)
            if datos.fila is not None:
                res = _j(expresiones.evaluar(arbol, datos.fila))
        return {"valida": True, "resultado": res}
    except expresiones.ErrorExpresion as exc:
        return {"valida": False, "error": str(exc)}


@router.post("/logo", status_code=201)
async def subir_logo(db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()]):
    rol = _permiso(db, empresa_id, usuario, "configurar")
    contenido = await archivo.read()
    if len(contenido) > 1024 * 1024:
        raise HTTPException(422, "El logotipo no debe superar 1 MB")
    ext = "png" if contenido[:8] == b"\x89PNG\r\n\x1a\n" else ("jpg" if contenido[:3] == b"\xff\xd8\xff" else None)
    if not ext:
        raise HTTPException(422, "El logotipo debe ser PNG o JPG")
    d = Path(config.DATA_DIR) / "anexos" / str(empresa_id)
    d.mkdir(parents=True, exist_ok=True)
    for viejo in d.glob("logo.*"):
        viejo.rename(d / f"logo-anterior-{int(time.time())}{viejo.suffix}")  # se conserva el anterior
    (d / f"logo.{ext}").write_bytes(contenido)
    generador.auditar(db, empresa_id, usuario, "SUBIR_LOGO", "logo", None, {"bytes": len(contenido)}, rol)
    db.commit()
    return {"ok": True}


@router.get("/logo")
def logo(db: DB, empresa_id: int):
    """Logotipo de la empresa (dato de presentación, sin información contable): lo carga la vista de impresión."""
    _empresa(db, empresa_id)
    p = exportar.ruta_logo(empresa_id)
    if not p:
        raise HTTPException(404, "Sin logotipo")
    return FileResponse(p)


# ------------------------------------------------------------------ explorador, generación
@router.get("/cuentas")
def cuentas(db: DB, usuario: Usuario, empresa_id: int, ejercicio: int | None = None, periodo: int | None = None,
            fecha_corte: date | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    ej, per, corte = _corte(ejercicio, periodo, fecha_corte)
    return consultas.explorador(db, empresa_id, ej, per, corte, flujo.cuentas_permitidas(db, empresa_id, usuario))


class GeneracionIn(BaseModel):
    ejercicio: int | None = None
    periodo: int | None = Field(default=None, ge=1, le=13)
    fecha_corte: date | None = None
    modo: str = Field(default="CUENTAS", pattern="^(CUENTAS|ELEMENTO|RANGO|BALANCE)$")
    cuentas: list[str] = []
    elemento: str | None = Field(default=None, pattern="^[0-9]$")
    desde: str | None = None
    hasta: str | None = None
    digitos: int | None = Field(default=None, ge=1, le=12)
    plantilla_id: int | None = None
    filtros: dict = {}
    motivo: str | None = Field(default=None, max_length=255)
    forzar: bool = False


def _lanzar(db, empresa_id, usuario, d: GeneracionIn) -> dict:
    ej, per, corte = _corte(d.ejercicio, d.periodo, d.fecha_corte)
    if d.modo == "CUENTAS" and not d.cuentas:
        raise HTTPException(422, "Seleccione al menos una cuenta")
    if d.modo == "RANGO" and not (d.desde and d.hasta):
        raise HTTPException(422, "Indique el rango de cuentas")
    if d.modo == "ELEMENTO" and d.elemento is None:
        raise HTTPException(422, "Indique el elemento")
    permitidas = flujo.cuentas_permitidas(db, empresa_id, usuario)
    cuentas_sel = [c.strip() for c in d.cuentas if c.strip()]
    if permitidas is not None:
        if d.modo != "CUENTAS":
            raise HTTPException(403, "Su acceso está restringido a cuentas asignadas: genere los anexos de esas cuentas.")
        for c in cuentas_sel:
            try:
                flujo.exigir_cuenta(db, empresa_id, usuario, c)
            except flujo.SinPermiso as exc:
                raise HTTPException(403, str(exc))
    if d.plantilla_id:
        p = db.get(PlantillaAnexo, d.plantilla_id)
        if not p or p.empresa_id not in (None, empresa_id) or not _visible(p, empresa_id, usuario):
            raise HTTPException(404, "Plantilla no encontrada")
        if p.tipo == "PERSONALIZADA" and not p.autorizada and p.creado_por != usuario:
            raise HTTPException(403, "La plantilla personalizada no está autorizada")
    filtros = {k: v for k, v in (d.filtros or {}).items() if k in ("centro_costo", "proyecto", "unidad_negocio", "moneda") and v}
    alcance = {"modo": d.modo, "cuentas": cuentas_sel, "elemento": d.elemento, "desde": d.desde, "hasta": d.hasta, "digitos": d.digitos,
               "plantilla_id": d.plantilla_id, "filtros": filtros, "motivo": d.motivo}
    try:
        run, nuevo = generador.crear_run(db, empresa_id, ej, per, corte, alcance, usuario, d.forzar)
    except generador.Conflicto as exc:
        _err(exc)
    if not nuevo:
        return {"run_id": run.id, "reutilizado": True, "trabajo": None}
    rid = run.id

    def tarea(avance):
        with SessionLocal() as s:
            return generador.ejecutar_run(s, rid, avance)
    return {"run_id": rid, "reutilizado": False, "trabajo": trabajos.crear("ANEXOS", tarea)}


@router.post("/generaciones", status_code=202)
def generar(datos: GeneracionIn, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "generar")
    return _lanzar(db, empresa_id, usuario, datos)


@router.get("/generaciones")
def generaciones(db: DB, usuario: Usuario, empresa_id: int, limite: int = 30):
    _permiso(db, empresa_id, usuario, "consultar")
    return [generador.run_dict(r) for r in db.scalars(select(GeneracionAnexos).where(GeneracionAnexos.empresa_id == empresa_id)
                                                      .order_by(GeneracionAnexos.id.desc()).limit(min(limite, 200)))]


def _run(db, empresa_id, run_id) -> GeneracionAnexos:
    r = db.get(GeneracionAnexos, run_id)
    if not r or r.empresa_id != empresa_id:
        raise HTTPException(404, "Generación no encontrada")
    return r


@router.get("/generaciones/{run_id}")
def generacion(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    return generador.run_dict(_run(db, empresa_id, run_id))


@router.post("/generaciones/{run_id}/cancelar")
def cancelar(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "generar")
    r = _run(db, empresa_id, run_id)
    if r.estado not in ("EN_COLA", "PROCESANDO"):
        raise HTTPException(409, "La generación ya terminó")
    generador.marcar_cancelacion(db, r)
    generador.auditar(db, empresa_id, usuario, "CANCELAR_GENERACION", "run", r.id, None, rol)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ anexos
@router.get("/anexos")
def listar(db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None, cuenta: str | None = None,
           estado: str | None = None, resultado: str | None = None, elemento: str | None = None, responsable: str | None = None,
           pagina: int = 1, por_pagina: int = 100):
    _permiso(db, empresa_id, usuario, "consultar")
    q = select(Anexo).where(Anexo.empresa_id == empresa_id, Anexo.version_id.is_not(None))
    if fecha_corte:
        q = q.where(Anexo.fecha_corte == fecha_corte)
    if cuenta:
        q = q.where(Anexo.cuenta.like(f"{cuenta}%"))
    if estado:
        q = q.where(Anexo.estado_revision == estado)
    if resultado:
        q = q.where(Anexo.resultado == resultado)
    if elemento:
        q = q.where(Anexo.elemento == elemento)
    if responsable:
        q = q.where(or_(Anexo.responsable_elaboracion == responsable, Anexo.responsable_revision == responsable,
                        Anexo.responsable_aprobacion == responsable))
    permitidas = flujo.cuentas_permitidas(db, empresa_id, usuario)
    if permitidas is not None:
        q = q.where(or_(*[Anexo.cuenta.like(f"{p}%") for p in permitidas]))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    por_pagina = max(1, min(por_pagina, 500))
    filas = db.scalars(q.order_by(Anexo.fecha_corte.desc(), Anexo.cuenta).offset((max(pagina, 1) - 1) * por_pagina).limit(por_pagina)).all()
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina,
            "items": [_fila(a, ("clave",)) | {"filtros": json.loads(a.filtros) if a.filtros else {}} for a in filas]}


def _acciones(db, empresa_id, usuario, a: Anexo) -> list[str]:
    out = []
    for nuevo, (accion, origenes) in flujo.TRANSICIONES.items():
        if a.estado_revision in origenes and flujo.puede(db, empresa_id, usuario, accion):
            out.append(nuevo)
    return out


@router.get("/anexos/{anexo_id}")
def obtener(anexo_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    a = _anexo(db, empresa_id, anexo_id, usuario)
    v = db.get(VersionAnexo, a.version_id) if a.version_id else None
    conc = db.scalar(select(ConciliacionAnexo).where(ConciliacionAnexo.version_id == a.version_id)) if a.version_id else None
    hall = db.scalars(select(HallazgoAnexo).where(HallazgoAnexo.anexo_id == a.id)
                      .order_by(HallazgoAnexo.estado, HallazgoAnexo.severidad, HallazgoAnexo.id)).all()
    adj = db.scalars(select(AdjuntoAnexo).where(AdjuntoAnexo.empresa_id == empresa_id,
                                                or_(AdjuntoAnexo.anexo_id == a.id, AdjuntoAnexo.cuenta.like(f"{a.cuenta}%")))
                     .order_by(AdjuntoAnexo.id.desc()).limit(300)).all()
    versiones = db.scalars(select(VersionAnexo).where(VersionAnexo.anexo_id == a.id).order_by(VersionAnexo.numero.desc())).all()
    snap = json.loads(v.plantilla_snapshot) if v else None
    return {
        "anexo": _fila(a, ("clave",)) | {"filtros": json.loads(a.filtros) if a.filtros else {}},
        "version": (_fila(v, ("plantilla_snapshot", "reglas_snapshot", "resumen")) if v else None),
        "resumen": json.loads(v.resumen) if v else None, "conciliacion": _fila(conc) if conc else None,
        "plantilla": {k: snap[k] for k in ("id", "codigo", "nombre", "tipo", "especialidad", "version", "columnas", "formulas",
                                           "agrupar_por", "subtotales", "filtros", "orientacion", "encabezado")} if snap else None,
        "hallazgos": [_fila(h) for h in hall],
        "revisiones": [_fila(r) for r in db.scalars(select(RevisionAnexo).where(RevisionAnexo.anexo_id == a.id).order_by(RevisionAnexo.id.desc()).limit(200))],
        "aprobaciones": [_fila(r) for r in db.scalars(select(AprobacionAnexo).where(AprobacionAnexo.anexo_id == a.id).order_by(AprobacionAnexo.id))],
        "comentarios": [_fila(c) for c in db.scalars(select(ComentarioAnexo).where(ComentarioAnexo.anexo_id == a.id).order_by(ComentarioAnexo.id))],
        "adjuntos": [_fila(x, ("ruta",)) for x in adj],
        "versiones": [{"id": x.id, "numero": x.numero, "generado_por": x.generado_por, "generado_en": _j(x.generado_en), "filas": x.filas,
                       "inmutable": x.inmutable, "estado_al_cerrar": x.estado_al_cerrar, "motivo": x.motivo,
                       "resultado": json.loads(x.resumen).get("resultado"), "diferencia": json.loads(x.resumen).get("diferencia"),
                       "version_datos": x.version_datos, "plantilla_version": json.loads(x.plantilla_snapshot).get("version")} for x in versiones],
        "acciones": _acciones(db, empresa_id, usuario, a), "puede_editar": a.estado_revision not in ("APROBADO", "CERRADO")
        and flujo.puede(db, empresa_id, usuario, "elaborar"),
        "datos_personales_ocultos": a.especialidad == "REMUNERACIONES" and _mascara(db, empresa_id, usuario),
    }


@router.get("/anexos/{anexo_id}/detalle")
def detalle(anexo_id: int, db: DB, usuario: Usuario, empresa_id: int, version_id: int | None = None, pagina: int = 1,
            por_pagina: int = 200, buscar: str | None = None, filtros: str | None = None, sin_filtros_plantilla: bool = False):
    _permiso(db, empresa_id, usuario, "consultar")
    a = _anexo(db, empresa_id, anexo_id, usuario)
    v = db.get(VersionAnexo, version_id or a.version_id) if (version_id or a.version_id) else None
    if not v or v.anexo_id != a.id:
        raise HTTPException(404, "Versión no encontrada")
    snap = json.loads(v.plantilla_snapshot)
    filas = render.filas_version(db, v.id, a.especialidad)
    if _mascara(db, empresa_id, usuario):
        filas = [flujo.enmascarar(f) if flujo.requiere_mascara(f, a.especialidad) else f for f in filas]
    try:
        extra = json.loads(filtros) if filtros else []
    except ValueError:
        raise HTTPException(422, "Filtros no válidos")
    vista = render.aplicar(snap, filas, filtros_extra=extra, buscar=buscar, ignorar_filtros_plantilla=sin_filtros_plantilla)
    por_pagina = max(1, min(por_pagina, 2000))
    ini = (max(pagina, 1) - 1) * por_pagina
    pag = vista["filas"][ini: ini + por_pagina]
    s = render.serial
    return {"version": v.numero, "version_id": v.id, "columnas": vista["columnas"], "pagina": pagina, "por_pagina": por_pagina,
            "total_filas": vista["total_filas"], "filas_filtradas": vista["filas_filtradas"],
            "filas": [{k: s(x) for k, x in f.items()} for f in pag], "totales": {k: s(x) for k, x in vista["totales"].items()},
            "grupos": [{**g, "subtotales": {k: s(x) for k, x in g["subtotales"].items()}} for g in vista["grupos"]],
            "agrupar_por": vista["agrupar_por"], "filtros_aplicados": vista["filtros_aplicados"], "errores_formulas": vista["errores_formulas"]}


class EstadoIn(BaseModel):
    estado: str = Field(pattern=f"^({'|'.join(ESTADOS_REVISION)})$")
    comentario: str | None = Field(default=None, max_length=4000)
    lock_version: int | None = None


@router.post("/anexos/{anexo_id}/estado")
def estado(anexo_id: int, datos: EstadoIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        flujo.cambiar_estado(db, empresa_id, anexo_id, usuario, datos.estado, datos.comentario, datos.lock_version)
    except (flujo.SinPermiso, flujo.ErrorFlujo, flujo.Conflicto, LookupError) as exc:
        db.rollback()
        _err(exc)
    return obtener(anexo_id, db, usuario, empresa_id)


class EdicionIn(BaseModel):
    conclusion: str | None = Field(default=None, max_length=8000)
    acciones_correctivas: str | None = Field(default=None, max_length=8000)
    responsable_elaboracion: str | None = Field(default=None, max_length=80)
    responsable_revision: str | None = Field(default=None, max_length=80)
    responsable_aprobacion: str | None = Field(default=None, max_length=80)
    fecha_limite: date | None = None
    lock_version: int | None = None


@router.patch("/anexos/{anexo_id}")
def editar(anexo_id: int, datos: EdicionIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        flujo.editar(db, empresa_id, anexo_id, usuario, datos.model_dump(exclude_unset=True, exclude={"lock_version"}), datos.lock_version)
    except (flujo.SinPermiso, flujo.ErrorFlujo, flujo.Conflicto, LookupError) as exc:
        db.rollback()
        _err(exc)
    return obtener(anexo_id, db, usuario, empresa_id)


class RegenerarIn(BaseModel):
    motivo: str | None = Field(default=None, max_length=255)
    forzar: bool = False


@router.post("/anexos/{anexo_id}/regenerar", status_code=202)
def regenerar(anexo_id: int, datos: RegenerarIn, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "generar")
    a = _anexo(db, empresa_id, anexo_id, usuario)
    if a.estado_revision in ("APROBADO", "CERRADO"):
        raise HTTPException(409, "El anexo está aprobado o cerrado: su versión es inmutable. Reábralo (con autorización) para actualizarlo.")
    return _lanzar(db, empresa_id, usuario, GeneracionIn(ejercicio=a.ejercicio, periodo=a.periodo, fecha_corte=a.fecha_corte, modo="CUENTAS",
                                                          cuentas=[a.cuenta], plantilla_id=a.plantilla_id,
                                                          filtros=json.loads(a.filtros) if a.filtros else {},
                                                          motivo=datos.motivo or "Actualización del anexo", forzar=datos.forzar))


class HallazgoIn(BaseModel):
    titulo: str = Field(min_length=5, max_length=300)
    detalle: str | None = None
    severidad: str = Field(default="MEDIA", pattern="^(ALTA|MEDIA|BAJA|INFORMATIVA)$")
    importe: Decimal | None = None
    clave_fila: str | None = None
    responsable: str | None = None
    accion_correctiva: str | None = None


@router.post("/anexos/{anexo_id}/hallazgos", status_code=201)
def agregar_hallazgo(anexo_id: int, datos: HallazgoIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        return _fila(flujo.agregar_hallazgo(db, empresa_id, anexo_id, usuario, datos.model_dump()))
    except (flujo.SinPermiso, flujo.ErrorFlujo, LookupError) as exc:
        _err(exc)


class HallazgoUpd(BaseModel):
    estado: str | None = Field(default=None, pattern="^(ABIERTO|SUBSANADO|DESCARTADO)$")
    responsable: str | None = None
    accion_correctiva: str | None = None
    comentario: str | None = None


@router.patch("/hallazgos/{hallazgo_id}")
def actualizar_hallazgo(hallazgo_id: int, datos: HallazgoUpd, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        return _fila(flujo.actualizar_hallazgo(db, empresa_id, hallazgo_id, usuario, datos.model_dump(exclude_unset=True)))
    except (flujo.SinPermiso, flujo.ErrorFlujo, LookupError) as exc:
        _err(exc)


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    clave_fila: str | None = None


@router.post("/anexos/{anexo_id}/comentarios", status_code=201)
def comentar(anexo_id: int, datos: ComentarioIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        return _fila(flujo.comentar(db, empresa_id, anexo_id, usuario, datos.texto, datos.clave_fila))
    except (flujo.SinPermiso, flujo.ErrorFlujo, LookupError) as exc:
        _err(exc)


@router.get("/anexos/{anexo_id}/comparar")
def comparar_anexo(anexo_id: int, db: DB, usuario: Usuario, empresa_id: int, contra: str = "mes_anterior"):
    _permiso(db, empresa_id, usuario, "consultar")
    a = _anexo(db, empresa_id, anexo_id, usuario)
    try:
        r = comparar.comparar(db, a, contra, usuario)
    except (LookupError, ValueError) as exc:
        _err(exc)
    s = render.serial
    mascara = _mascara(db, empresa_id, usuario) and a.especialidad == "REMUNERACIONES"

    def limpiar(x):
        if isinstance(x, list):
            return [limpiar(i) for i in x]
        if isinstance(x, dict):
            return {k: ("(reservado)" if mascara and k == "razon_social" else limpiar(v)) for k, v in x.items()}
        return s(x)
    return limpiar(r)


@router.get("/anexos/{anexo_id}/exportar.{formato}")
def exportar_anexo(anexo_id: int, formato: str, db: DB, usuario: Usuario, empresa_id: int, version_id: int | None = None):
    rol = _permiso(db, empresa_id, usuario, "exportar")
    a = _anexo(db, empresa_id, anexo_id, usuario)
    if formato not in ("xlsx", "pdf"):
        raise HTTPException(404, "Formato no disponible")
    try:
        p = exportar.preparar(db, a, version_id, mascara=_mascara(db, empresa_id, usuario))
    except LookupError as exc:
        _err(exc)
    contenido = exportar.excel_anexo(p) if formato == "xlsx" else exportar.pdf_anexo(p)
    generador.auditar(db, empresa_id, usuario, "EXPORTAR_ANEXO", "anexo", a.id, {"formato": formato, "version": p["version"].numero}, rol)
    db.commit()
    nombre = f"anexo_{a.cuenta}_{a.fecha_corte:%Y%m%d}_v{p['version'].numero}.{formato}"
    tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if formato == "xlsx" else "application/pdf"
    return Response(contenido, media_type=tipo, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


# ------------------------------------------------------------------ documentación sustentatoria
@router.post("/adjuntos", status_code=201)
async def adjuntar(db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()],
                   categoria: Annotated[str, Form()] = "OTRO", anexo_id: Annotated[int | None, Form()] = None,
                   cuenta: Annotated[str | None, Form()] = None, tercero: Annotated[str | None, Form()] = None,
                   documento: Annotated[str | None, Form()] = None, clave_fila: Annotated[str | None, Form()] = None,
                   item_id: Annotated[int | None, Form()] = None, linea_id: Annotated[int | None, Form()] = None,
                   descripcion: Annotated[str | None, Form()] = None, confidencial: Annotated[bool, Form()] = False):
    _empresa(db, empresa_id)
    meta = {"categoria": categoria, "anexo_id": anexo_id, "cuenta": cuenta, "tercero": tercero, "documento": documento,
            "clave_fila": clave_fila, "item_id": item_id, "linea_id": linea_id, "descripcion": descripcion, "confidencial": confidencial}
    try:
        adj = flujo.adjuntar(db, empresa_id, usuario, archivo.filename or "archivo", archivo.content_type, await archivo.read(), meta)
    except (flujo.SinPermiso, flujo.ErrorFlujo, LookupError) as exc:
        _err(exc)
    return _fila(adj, ("ruta",))


@router.get("/adjuntos")
def adjuntos(db: DB, usuario: Usuario, empresa_id: int, cuenta: str | None = None, anexo_id: int | None = None,
             tercero: str | None = None, categoria: str | None = None, pagina: int = 1, por_pagina: int = 100):
    _permiso(db, empresa_id, usuario, "consultar")
    q = select(AdjuntoAnexo).where(AdjuntoAnexo.empresa_id == empresa_id)
    if cuenta:
        q = q.where(AdjuntoAnexo.cuenta.like(f"{cuenta}%"))
    if anexo_id:
        q = q.where(AdjuntoAnexo.anexo_id == anexo_id)
    if tercero:
        q = q.where(AdjuntoAnexo.tercero == tercero)
    if categoria:
        q = q.where(AdjuntoAnexo.categoria == categoria)
    permitidas = flujo.cuentas_permitidas(db, empresa_id, usuario)
    if permitidas is not None:
        q = q.where(or_(*[AdjuntoAnexo.cuenta.like(f"{p}%") for p in permitidas]))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    filas = db.scalars(q.order_by(AdjuntoAnexo.id.desc()).offset((max(pagina, 1) - 1) * por_pagina).limit(min(por_pagina, 500))).all()
    return {"total": total, "categorias": list(CATEGORIAS_ADJUNTO), "items": [_fila(x, ("ruta",)) for x in filas]}


@router.get("/adjuntos/{adjunto_id}/descargar")
def descargar_adjunto(adjunto_id: int, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "consultar")
    x = db.get(AdjuntoAnexo, adjunto_id)
    if not x or x.empresa_id != empresa_id:
        raise HTTPException(404, "Documento no encontrado")
    if x.cuenta:
        try:
            flujo.exigir_cuenta(db, empresa_id, usuario, x.cuenta)
        except flujo.SinPermiso as exc:
            raise HTTPException(403, str(exc))
    if x.confidencial and _mascara(db, empresa_id, usuario):
        raise HTTPException(403, "Documento confidencial: requiere permiso de datos personales")
    generador.auditar(db, empresa_id, usuario, "DESCARGAR_SUSTENTO", "adjunto", x.id, None, rol)
    db.commit()
    return FileResponse(flujo.ruta_adjunto(x), filename=x.nombre)


# ------------------------------------------------------------------ asignaciones y configuración
class AsignacionIn(BaseModel):
    tipo: str = Field(pattern="^(ELABORACION|REVISION|APROBACION|ACCESO)$")
    usuario: str = Field(min_length=2, max_length=80)
    cuenta: str | None = Field(default=None, max_length=20)
    anexo_id: int | None = None
    fecha_limite: str | None = None


@router.get("/asignaciones")
def asignaciones(db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    return [_fila(x) for x in db.scalars(select(AsignacionAnexo).where(AsignacionAnexo.empresa_id == empresa_id, AsignacionAnexo.activa.is_(True))
                                         .order_by(AsignacionAnexo.cuenta, AsignacionAnexo.tipo))]


@router.post("/asignaciones", status_code=201)
def asignar(datos: AsignacionIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        return _fila(flujo.asignar(db, empresa_id, usuario, datos.model_dump()))
    except (flujo.SinPermiso, flujo.ErrorFlujo, LookupError, ValueError) as exc:
        _err(exc)


@router.post("/asignaciones/{asignacion_id}/desactivar")
def desactivar_asignacion(asignacion_id: int, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "asignar")
    x = db.get(AsignacionAnexo, asignacion_id)
    if not x or x.empresa_id != empresa_id:
        raise HTTPException(404, "Asignación no encontrada")
    if x.tipo == "ACCESO" and rol not in flujo.PERMISOS["configurar"]:
        raise HTTPException(403, "Solo un supervisor o administrador modifica accesos")
    x.activa = False
    generador.auditar(db, empresa_id, usuario, "DESACTIVAR_ASIGNACION", "asignacion", x.id, None, rol)
    db.commit()
    return {"ok": True}


@router.get("/configuracion")
def ver_configuracion(db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    return generador.configuracion(db, empresa_id)


@router.put("/configuracion")
def guardar_configuracion(datos: dict, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        return flujo.guardar_configuracion(db, empresa_id, usuario, datos)
    except (flujo.SinPermiso, flujo.ErrorFlujo, ArithmeticError, ValueError) as exc:
        _err(exc)


# ------------------------------------------------------------------ registros auxiliares
@router.post("/registros/importar", status_code=201)
async def importar_registro(db: DB, usuario: Usuario, empresa_id: int, tipo: Annotated[str, Form()], archivo: Annotated[UploadFile, File()]):
    _permiso(db, empresa_id, usuario, "registros")
    if tipo not in TIPOS_REGISTRO:
        raise HTTPException(422, "Tipo de registro no válido")
    try:
        return auxiliares.importar(db, empresa_id, usuario, tipo, archivo.filename or "archivo", await archivo.read())
    except ErrorImportacion as exc:
        raise HTTPException(422, str(exc))


@router.get("/registros")
def registros(db: DB, usuario: Usuario, empresa_id: int, tipo: str | None = None, pagina: int = 1, por_pagina: int = 200):
    _permiso(db, empresa_id, usuario, "consultar")
    q = select(RegistroAuxiliar).where(RegistroAuxiliar.empresa_id == empresa_id)
    if tipo:
        q = q.where(RegistroAuxiliar.tipo == tipo)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    filas = db.scalars(q.order_by(RegistroAuxiliar.tipo, RegistroAuxiliar.clave).offset((max(pagina, 1) - 1) * por_pagina).limit(min(por_pagina, 1000))).all()
    return {"total": total, "tipos": {t: auxiliares.ESPEC[t][1] for t in TIPOS_REGISTRO},
            "items": [_fila(x, ("datos",)) | {"datos": json.loads(x.datos)} for x in filas]}


@router.post("/registros/{registro_id}/anular")
def anular_registro(registro_id: int, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "registros")
    x = db.get(RegistroAuxiliar, registro_id)
    if not x or x.empresa_id != empresa_id:
        raise HTTPException(404, "Registro no encontrado")
    x.vigente = False  # se conserva para la trazabilidad de versiones anteriores
    generador.auditar(db, empresa_id, usuario, "ANULAR_REGISTRO", "registro", x.id, None, rol)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ exportaciones masivas
class ExportacionIn(BaseModel):
    tipo: str = Field(pattern="^(LIBRO_EXCEL|EXPEDIENTE_PDF)$")
    fecha_corte: date
    anexo_ids: list[int] = []
    cuenta: str | None = None
    solo_aprobados: bool = False


def _dir_export(empresa_id) -> Path:
    d = Path(config.DATA_DIR) / "anexos" / str(empresa_id) / "exportaciones"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/exportaciones", status_code=202)
def crear_exportacion(datos: ExportacionIn, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "exportar")
    permitidas = flujo.cuentas_permitidas(db, empresa_id, usuario)
    lst = consultas.anexos_al_corte(db, empresa_id, datos.fecha_corte, permitidas)
    if datos.anexo_ids:
        lst = [a for a in lst if a.id in set(datos.anexo_ids)]
    if datos.cuenta:
        lst = [a for a in lst if a.cuenta.startswith(datos.cuenta)]
    if datos.solo_aprobados:
        lst = [a for a in lst if a.estado_revision in ("APROBADO", "CERRADO")]
    if not lst:
        raise HTTPException(422, "No hay anexos generados para exportar con esos criterios")
    job = ExportacionAnexos(empresa_id=empresa_id, tipo=datos.tipo, alcance=json.dumps(datos.model_dump(), default=str), usuario=usuario,
                            anexos=len(lst))
    db.add(job)
    db.flush()
    generador.auditar(db, empresa_id, usuario, "EXPORTAR_MASIVO", "exportacion", job.id, {"tipo": datos.tipo, "anexos": len(lst)}, rol)
    db.commit()
    jid, ids, mascara = job.id, [a.id for a in lst], _mascara(db, empresa_id, usuario)

    def tarea(avance):
        t0 = time.perf_counter()
        with SessionLocal() as s:
            j = s.get(ExportacionAnexos, jid)
            j.estado = "PROCESANDO"
            s.commit()
            try:
                emp = s.get(Empresa, empresa_id)
                anexos = [s.get(Anexo, i) for i in ids]
                anexos.sort(key=lambda a: a.cuenta)

                def prog(p, e):
                    j.progreso, j.etapa = p, e
                    s.commit()
                    avance(p, e)
                mf = lambda a: mascara and a.especialidad == "REMUNERACIONES"  # noqa: E731
                if datos.tipo == "LIBRO_EXCEL":
                    prog(3, "Cargando el balance de comprobación")
                    ctx = datos_mod.crear(s, empresa_id, datos.fecha_corte.year, datos.fecha_corte.month, datos.fecha_corte)
                    contenido = exportar.excel_libro(s, emp, anexos, ctx, mf, prog)
                    nombre = f"anexos_{emp.ruc}_{datos.fecha_corte:%Y%m%d}.xlsx"
                else:
                    contenido = exportar.pdf_expediente(s, emp, anexos, mf, prog)
                    nombre = f"expediente_cierre_{emp.ruc}_{datos.fecha_corte:%Y%m%d}.pdf"
                ruta = _dir_export(empresa_id) / f"{jid}-{nombre}"
                ruta.write_bytes(contenido)
                j.estado, j.progreso, j.etapa, j.nombre_archivo = "COMPLETADO", 100, "Completado", nombre
                j.ruta, j.tamano = str(ruta.relative_to(Path(config.DATA_DIR))), len(contenido)
            except Exception as exc:
                s.rollback()
                j = s.get(ExportacionAnexos, jid)
                j.estado, j.error = "ERROR", str(exc)[:2000]
                s.commit()
                raise
            j.duracion_ms, j.finalizado_en = int((time.perf_counter() - t0) * 1000), datetime.now()
            s.commit()
            return {"exportacion_id": jid}
    return {"exportacion_id": jid, "trabajo": trabajos.crear("EXPORTACION_ANEXOS", tarea)}


@router.get("/exportaciones")
def exportaciones(db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    return [_fila(x, ("ruta",)) for x in db.scalars(select(ExportacionAnexos).where(ExportacionAnexos.empresa_id == empresa_id)
                                                     .order_by(ExportacionAnexos.id.desc()).limit(50))]


@router.get("/exportaciones/{exportacion_id}/descargar")
def descargar_exportacion(exportacion_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "exportar")
    x = db.get(ExportacionAnexos, exportacion_id)
    if not x or x.empresa_id != empresa_id:
        raise HTTPException(404, "Exportación no encontrada")
    if x.estado != "COMPLETADO":
        raise HTTPException(409, f"La exportación está {x.estado.lower()}")
    if x.usuario != usuario and not flujo.puede(db, empresa_id, usuario, "configurar"):
        raise HTTPException(403, "La exportación pertenece a otro usuario")
    return FileResponse(Path(config.DATA_DIR) / x.ruta, filename=x.nombre_archivo)


# ------------------------------------------------------------------ dashboard y auditoría
@router.get("/dashboard")
def dashboard(db: DB, usuario: Usuario, empresa_id: int, ejercicio: int | None = None, periodo: int | None = None,
              fecha_corte: date | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    ej, per, corte = _corte(ejercicio, periodo, fecha_corte)
    d = consultas.dashboard(db, empresa_id, ej, per, corte, flujo.cuentas_permitidas(db, empresa_id, usuario))
    ult = db.scalar(select(GeneracionAnexos).where(GeneracionAnexos.empresa_id == empresa_id).order_by(GeneracionAnexos.id.desc()))
    d["ultima_generacion"] = generador.run_dict(ult) if ult else None
    return d


@router.get("/auditoria")
def auditoria(db: DB, usuario: Usuario, empresa_id: int, limite: int = 300, entidad: str | None = None, entidad_id: int | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    q = select(AuditoriaAnexo).where(AuditoriaAnexo.empresa_id == empresa_id)
    if entidad:
        q = q.where(AuditoriaAnexo.entidad == entidad)
    if entidad_id:
        q = q.where(AuditoriaAnexo.entidad_id == entidad_id)
    return [_fila(a) for a in db.scalars(q.order_by(AuditoriaAnexo.id.desc()).limit(min(limite, 2000)))]



