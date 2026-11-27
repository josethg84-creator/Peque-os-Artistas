"""API del motor de conciliaciones contables (fase 6). Todo se acota a `empresa_id` y al rol del usuario
(cabecera X-Usuario). Las conciliaciones son analíticas: no modifican asientos, no generan ajustes, no realizan
operaciones bancarias ni presentan declaraciones."""
import json
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB, Usuario
from app.conciliacion import catalogo, consultas, disenador, exportar, fuentes, servicio
from app.contable import trabajos
from app.core.database import SessionLocal
from app.models import (AdjuntoConciliacion, AsignacionConciliacion, AuditoriaConciliacion, Conciliacion, DiferenciaConciliacion, Empresa,
                        GrupoConciliacion, MapeoColumnas, PlantillaConciliacion, TipoConciliacion, ToleranciaConciliacion)
from app.models.conciliacion import CLASIFICACIONES, ESTADOS_DIFERENCIA, PRIORIDADES

router = APIRouter(prefix="/conciliaciones", tags=["Conciliaciones"])
ERRORES = (servicio.SinPermiso, servicio.ErrorConciliacion, servicio.Conflicto, LookupError)


def _empresa(db, empresa_id) -> Empresa:
    e = db.get(Empresa, empresa_id)
    if not e:
        raise HTTPException(404, "Empresa no encontrada")
    return e


def _err(exc):
    if isinstance(exc, LookupError):
        raise HTTPException(404, str(exc).strip("'"))
    raise HTTPException(getattr(exc, "status", 422), str(exc))


def _ok(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ERRORES as exc:
        _err(exc)
    except Exception as exc:
        if getattr(exc, "status", None):
            _err(exc)
        raise


def _ver(db, empresa_id, usuario, run_id) -> tuple[Conciliacion, bool]:
    _empresa(db, empresa_id)
    c = _ok(servicio.cargar, db, empresa_id, run_id)
    _ok(servicio.exigir, db, empresa_id, usuario, "consultar")
    r, _ = servicio.rol(db, empresa_id, usuario)
    if r in ("TESORERO", "PLANILLAS") and not servicio.puede(db, empresa_id, usuario, "operar", c.tipo_codigo):
        raise HTTPException(403, "La conciliación no corresponde a su función.")
    return c, servicio.ve_datos_personales(db, empresa_id, usuario)


# ------------------------------------------------------------------ catálogo y configuración
@router.get("/catalogo")
def catalogo_(db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    catalogo.sembrar(db)
    r, _ = servicio.rol(db, empresa_id, usuario)
    tipos = [{"codigo": t.codigo, "nombre": t.nombre, "categoria": t.categoria, "descripcion": t.descripcion, "datos_personales": t.datos_personales,
              "puede_operar": servicio.puede(db, empresa_id, usuario, "operar", t.codigo)}
             for t in db.scalars(select(TipoConciliacion).where(TipoConciliacion.activo.is_(True)).order_by(TipoConciliacion.id))]
    plantillas = [{"id": p.id, "codigo": p.codigo, "nombre": p.nombre, "tipo": p.tipo_codigo, "personalizada": p.personalizada,
                   "autorizada": p.autorizada, "autorizada_por": p.autorizada_por, "version": p.version, "creado_por": p.creado_por,
                   "empresa_id": p.empresa_id}
                  for p in db.scalars(select(PlantillaConciliacion).where(PlantillaConciliacion.activa.is_(True),
                                                                          (PlantillaConciliacion.empresa_id.is_(None)) | (PlantillaConciliacion.empresa_id == empresa_id))
                                      .order_by(PlantillaConciliacion.empresa_id.is_not(None), PlantillaConciliacion.id))]
    return {"tipos": tipos, "plantillas": plantillas, "clasificaciones": CLASIFICACIONES, "prioridades": PRIORIDADES,
            "estados_diferencia": ESTADOS_DIFERENCIA, "estados": list(exportar.ESTADOS), "reportes": exportar.REPORTES,
            "pasos_disenador": disenador.PASOS, "rol": r,
            "permisos": {k: servicio.puede(db, empresa_id, usuario, k) for k in servicio.PERMISOS},
            "tipos_fuente": fuentes.TIPOS_FUENTE}


@router.get("/plantillas/{plantilla_id}")
def plantilla(plantilla_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    p = db.get(PlantillaConciliacion, plantilla_id)
    if not p or p.empresa_id not in (None, empresa_id):
        raise HTTPException(404, "Plantilla no encontrada")
    return {"id": p.id, "codigo": p.codigo, "nombre": p.nombre, "descripcion": p.descripcion, "tipo": p.tipo_codigo, "personalizada": p.personalizada,
            "autorizada": p.autorizada, "version": p.version, "configuracion": catalogo.configuracion(db, p)}


class PlantillaIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    codigo: str | None = None
    descripcion: str | None = None
    tipo_codigo: str = "PERSONALIZADA"
    configuracion: dict


@router.post("/plantillas", status_code=201)
def crear_plantilla(d: PlantillaIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    p = _ok(disenador.guardar, db, empresa_id, usuario, d.model_dump())
    return {"id": p.id, "codigo": p.codigo, "autorizada": p.autorizada, "version": p.version}


@router.put("/plantillas/{plantilla_id}")
def editar_plantilla(plantilla_id: int, d: PlantillaIn, db: DB, usuario: Usuario, empresa_id: int):
    p = _ok(disenador.guardar, db, empresa_id, usuario, d.model_dump(), plantilla_id)
    return {"id": p.id, "codigo": p.codigo, "autorizada": p.autorizada, "version": p.version}


@router.post("/plantillas/{plantilla_id}/autorizar")
def autorizar_plantilla(plantilla_id: int, db: DB, usuario: Usuario, empresa_id: int):
    p = _ok(disenador.autorizar, db, empresa_id, usuario, plantilla_id)
    return {"id": p.id, "autorizada": p.autorizada, "autorizada_por": p.autorizada_por}


@router.post("/plantillas/validar")
def validar_plantilla(d: dict, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    return _ok(disenador.validar, d.get("configuracion") or d)


class PruebaIn(BaseModel):
    run_id: int
    configuracion: dict


@router.post("/plantillas/probar")
def probar_plantilla(d: PruebaIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    return _ok(disenador.probar, db, empresa_id, usuario, d.run_id, d.configuracion)


class ToleranciaIn(BaseModel):
    tipo_codigo: str | None = None
    cuenta: str | None = None
    moneda: str | None = None
    importe_absoluto: str = "0"
    porcentaje: str | None = None
    dias: int = Field(0, ge=0, le=366)


@router.get("/tolerancias")
def tolerancias(db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    return [consultas.fila(t) for t in db.scalars(select(ToleranciaConciliacion).where(ToleranciaConciliacion.empresa_id == empresa_id,
                                                                                         ToleranciaConciliacion.activa.is_(True)))]


@router.post("/tolerancias", status_code=201)
def crear_tolerancia(d: ToleranciaIn, db: DB, usuario: Usuario, empresa_id: int):
    from decimal import Decimal, InvalidOperation
    _empresa(db, empresa_id)
    r = _ok(servicio.exigir, db, empresa_id, usuario, "configurar")
    try:
        ia, pc = Decimal(d.importe_absoluto), Decimal(d.porcentaje) if d.porcentaje not in (None, "") else None
    except InvalidOperation:
        raise HTTPException(422, "Importe o porcentaje no válido")
    if ia < 0 or (pc is not None and not 0 <= pc <= 100):
        raise HTTPException(422, "Las tolerancias deben ser positivas")
    t = ToleranciaConciliacion(empresa_id=empresa_id, tipo_codigo=d.tipo_codigo or None, cuenta=d.cuenta or None, moneda=d.moneda or None,
                               importe_absoluto=ia, porcentaje=pc, dias=d.dias, creado_por=usuario)
    db.add(t)
    db.flush()
    servicio.auditar(db, empresa_id, usuario, "CREAR_TOLERANCIA", "tolerancia", t.id, d.model_dump(), r)
    db.commit()
    return consultas.fila(t)


@router.delete("/tolerancias/{tid}")
def borrar_tolerancia(tid: int, db: DB, usuario: Usuario, empresa_id: int):
    r = _ok(servicio.exigir, db, empresa_id, usuario, "configurar")
    t = db.get(ToleranciaConciliacion, tid)
    if not t or t.empresa_id != empresa_id:
        raise HTTPException(404, "Tolerancia no encontrada")
    t.activa = False  # se desactiva (no se elimina) para conservar la trazabilidad
    servicio.auditar(db, empresa_id, usuario, "DESACTIVAR_TOLERANCIA", "tolerancia", t.id, None, r)
    db.commit()
    return {"ok": True}


class AsignacionIn(BaseModel):
    tipo: str = Field(pattern="^(ELABORACION|REVISION|APROBACION|PROGRAMADA|GRUPO_ECONOMICO)$")
    tipo_conciliacion: str | None = None
    plantilla_id: int | None = None
    ambito: dict | None = None
    usuario: str | None = None
    empresa_relacionada_id: int | None = None
    fecha_limite: date | None = None
    dia_programado: int | None = Field(None, ge=1, le=31)


@router.get("/asignaciones")
def asignaciones(db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    return [consultas.fila(a) for a in db.scalars(select(AsignacionConciliacion).where(AsignacionConciliacion.empresa_id == empresa_id,
                                                                                         AsignacionConciliacion.activa.is_(True)))]


@router.post("/asignaciones", status_code=201)
def crear_asignacion(d: AsignacionIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    r = _ok(servicio.exigir, db, empresa_id, usuario, "configurar")
    if d.tipo == "GRUPO_ECONOMICO" and (not d.empresa_relacionada_id or not db.get(Empresa, d.empresa_relacionada_id)
                                         or d.empresa_relacionada_id == empresa_id):
        raise HTTPException(422, "Indique la empresa relacionada del grupo económico")
    a = AsignacionConciliacion(empresa_id=empresa_id, tipo=d.tipo, tipo_conciliacion=d.tipo_conciliacion, plantilla_id=d.plantilla_id,
                               ambito=json.dumps(d.ambito) if d.ambito else None, usuario=d.usuario, empresa_relacionada_id=d.empresa_relacionada_id,
                               fecha_limite=d.fecha_limite, dia_programado=d.dia_programado, asignado_por=usuario)
    db.add(a)
    db.flush()
    servicio.auditar(db, empresa_id, usuario, "ASIGNAR", "asignacion", a.id, d.model_dump(), r)
    db.commit()
    return consultas.fila(a)


@router.delete("/asignaciones/{aid}")
def borrar_asignacion(aid: int, db: DB, usuario: Usuario, empresa_id: int):
    r = _ok(servicio.exigir, db, empresa_id, usuario, "configurar")
    a = db.get(AsignacionConciliacion, aid)
    if not a or a.empresa_id != empresa_id:
        raise HTTPException(404, "Asignación no encontrada")
    a.activa = False
    servicio.auditar(db, empresa_id, usuario, "DESACTIVAR_ASIGNACION", "asignacion", a.id, None, r)
    db.commit()
    return {"ok": True}


@router.get("/mapeos")
def mapeos(db: DB, usuario: Usuario, empresa_id: int, esquema: str | None = None):
    _empresa(db, empresa_id)
    q = select(MapeoColumnas).where(MapeoColumnas.empresa_id == empresa_id)
    if esquema:
        q = q.where(MapeoColumnas.esquema == esquema)
    return [{**consultas.fila(m), "mapeo": json.loads(m.mapeo or "{}")} for m in db.scalars(q.order_by(MapeoColumnas.nombre))]


# ------------------------------------------------------------------ tablero, diferencias, reportes
@router.get("/tablero")
def tablero(db: DB, usuario: Usuario, empresa_id: int, ejercicio: int | None = None, periodo: int | None = None):
    _empresa(db, empresa_id)
    _ok(servicio.exigir, db, empresa_id, usuario, "consultar")
    return consultas.tablero(db, empresa_id, ejercicio, periodo, usuario)


@router.get("/diferencias")
def diferencias(db: DB, usuario: Usuario, empresa_id: int, clasificacion: str | None = None, prioridad: str | None = None,
                estado: str | None = None, tipo_conciliacion: str | None = None, responsable: str | None = None, run_id: int | None = None,
                version_id: int | None = None, abiertas: bool = False, trasladadas: bool = False, dentro_tolerancia: str | None = None,
                cuenta: str | None = None, tercero: str | None = None, buscar: str | None = None, orden: str | None = None,
                pagina: int = 1, por_pagina: int = 50):
    _empresa(db, empresa_id)
    _ok(servicio.exigir, db, empresa_id, usuario, "consultar")
    f = dict(clasificacion=clasificacion, prioridad=prioridad, estado=estado, tipo_conciliacion=tipo_conciliacion, responsable=responsable,
             run_id=run_id, version_id=version_id, abiertas=abiertas, trasladadas=trasladadas, dentro_tolerancia=dentro_tolerancia,
             cuenta=cuenta, tercero=tercero, buscar=buscar, orden=orden, pagina=pagina, por_pagina=por_pagina)
    return consultas.diferencias(db, empresa_id, f, servicio.ve_datos_personales(db, empresa_id, usuario), usuario)


def _dif(db, empresa_id, usuario, dif_id) -> tuple[DiferenciaConciliacion, bool]:
    d = db.get(DiferenciaConciliacion, dif_id)
    if not d or d.empresa_id != empresa_id:
        raise HTTPException(404, "Diferencia no encontrada")
    _, ve = _ver(db, empresa_id, usuario, d.run_id)
    return d, ve


@router.get("/diferencias/{dif_id}")
def diferencia(dif_id: int, db: DB, usuario: Usuario, empresa_id: int):
    d, ve = _dif(db, empresa_id, usuario, dif_id)
    return consultas.historial_diferencia(db, d, ve)


class DiferenciaIn(BaseModel):
    estado: str | None = None
    responsable: str | None = None
    fecha_limite: date | None = None
    causa: str | None = None
    accion_correctiva: str | None = None
    comentario: str | None = None
    lock_version: int | None = None


@router.patch("/diferencias/{dif_id}")
def actualizar_diferencia(dif_id: int, d: DiferenciaIn, db: DB, usuario: Usuario, empresa_id: int):
    _, ve = _dif(db, empresa_id, usuario, dif_id)
    if d.estado and d.estado not in servicio.TRANS_DIF:
        raise HTTPException(422, "Estado no válido")
    x = _ok(servicio.actualizar_diferencia, db, empresa_id, dif_id, usuario, d.model_dump(exclude_unset=True))
    return consultas.diferencia_dict(x, ve)


@router.post("/adjuntos", status_code=201)
def adjuntar(db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()],
             run_id: Annotated[int | None, Form()] = None, diferencia_id: Annotated[int | None, Form()] = None,
             grupo_id: Annotated[int | None, Form()] = None, registro_id: Annotated[int | None, Form()] = None,
             categoria: Annotated[str | None, Form()] = None, descripcion: Annotated[str | None, Form()] = None,
             confidencial: Annotated[bool, Form()] = False):
    _empresa(db, empresa_id)
    a = _ok(servicio.adjuntar, db, empresa_id, usuario, archivo.filename, archivo.content_type, archivo.file.read(),
            {"run_id": run_id, "diferencia_id": diferencia_id, "grupo_id": grupo_id, "registro_id": registro_id, "categoria": categoria,
             "descripcion": descripcion, "confidencial": confidencial})
    return consultas.fila(a, ("ruta",))


@router.get("/adjuntos/{aid}")
def descargar_adjunto(aid: int, db: DB, usuario: Usuario, empresa_id: int):
    a = db.get(AdjuntoConciliacion, aid)
    if not a or a.empresa_id != empresa_id:
        raise HTTPException(404, "Documento no encontrado")
    _, ve = _ver(db, empresa_id, usuario, a.run_id)
    if a.confidencial and not ve:
        raise HTTPException(403, "Documento confidencial")
    return FileResponse(servicio.ruta_adjunto(a), filename=a.nombre, media_type=a.tipo_contenido or "application/octet-stream")


@router.get("/reportes/{tipo}")
def reporte(tipo: str, db: DB, usuario: Usuario, empresa_id: int, formato: str = "xlsx", ejercicio: int | None = None, periodo: int | None = None,
            tipo_codigo: str | None = None, clasificacion: str | None = None, prioridad: str | None = None, estado: str | None = None):
    e = _empresa(db, empresa_id)
    r = _ok(servicio.exigir, db, empresa_id, usuario, "exportar")
    f = {"ejercicio": ejercicio, "periodo": periodo, "tipo_codigo": tipo_codigo, "clasificacion": clasificacion, "prioridad": prioridad, "estado": estado}
    contenido = _ok(exportar.reporte_global, db, e, tipo.upper(), f, servicio.ve_datos_personales(db, empresa_id, usuario), formato)
    servicio.auditar(db, empresa_id, usuario, "EXPORTAR_REPORTE", "reporte", None, {"tipo": tipo, "formato": formato, **f}, r)
    db.commit()
    return _archivo(contenido, f"conciliaciones_{tipo.lower()}", formato)


def _archivo(contenido: bytes, nombre: str, formato: str) -> Response:
    if formato == "pdf":
        return Response(contenido, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{nombre}.pdf"'})
    return Response(contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.xlsx"'})


@router.get("/auditoria")
def auditoria(db: DB, usuario: Usuario, empresa_id: int, run_id: int | None = None, pagina: int = 1, por_pagina: int = 100):
    _empresa(db, empresa_id)
    _ok(servicio.exigir, db, empresa_id, usuario, "revisar")
    q = select(AuditoriaConciliacion).where(AuditoriaConciliacion.empresa_id == empresa_id)
    if run_id:
        q = q.where(AuditoriaConciliacion.run_id == run_id)
    total, qp, pagina, pp = consultas.paginar(db, q.order_by(AuditoriaConciliacion.id.desc()), pagina, por_pagina)
    return {"total": total, "pagina": pagina, "por_pagina": pp, "items": [consultas.fila(a) for a in db.scalars(qp)]}


@router.get("/trabajos/{tid}")
def trabajo(tid: str):
    t = trabajos.obtener(tid)
    if not t:
        raise HTTPException(404, "Trabajo no encontrado")
    return t


# ------------------------------------------------------------------ conciliaciones
@router.get("")
def listar(db: DB, usuario: Usuario, empresa_id: int, tipo_codigo: str | None = None, estado: str | None = None, ejercicio: int | None = None,
           periodo: int | None = None, responsable: str | None = None, plantilla_id: int | None = None, fecha_corte: date | None = None,
           cuenta: str | None = None, moneda: str | None = None, centro_costo: str | None = None, proyecto: str | None = None,
           cuenta_bancaria_id: int | None = None, buscar: str | None = None, pagina: int = 1, por_pagina: int = 50):
    _empresa(db, empresa_id)
    _ok(servicio.exigir, db, empresa_id, usuario, "consultar")
    f = dict(tipo_codigo=tipo_codigo, estado=estado, ejercicio=ejercicio, periodo=periodo, responsable=responsable, plantilla_id=plantilla_id,
             fecha_corte=fecha_corte, cuenta=cuenta, moneda=moneda, centro_costo=centro_costo, proyecto=proyecto,
             cuenta_bancaria_id=cuenta_bancaria_id, buscar=buscar, pagina=pagina, por_pagina=por_pagina)
    return consultas.listar(db, empresa_id, f, usuario)


class CrearIn(BaseModel):
    tipo: str
    plantilla_id: int | None = None
    ejercicio: int | None = None
    periodo: int | None = Field(None, ge=1, le=12)
    fecha_corte: date | None = None
    ambito: dict = {}
    nombre: str | None = None
    responsable: str | None = None
    fecha_limite: date | None = None


@router.post("", status_code=201)
def crear(d: CrearIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    if not d.fecha_corte and not (d.ejercicio and d.periodo):
        raise HTTPException(422, "Indique la fecha de corte o el ejercicio y periodo")
    c = _ok(servicio.crear, db, empresa_id, usuario, d.model_dump())
    return consultas.conciliacion(db, c, servicio.ve_datos_personales(db, empresa_id, usuario))


@router.get("/{run_id}")
def ver(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    c, ve = _ver(db, empresa_id, usuario, run_id)
    return consultas.conciliacion(db, c, ve)


@router.post("/{run_id}/fuentes/{lado}/archivo")
def importar_fuente(run_id: int, lado: str, db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()],
                    confirmar: Annotated[bool, Form()] = True, mapeo: Annotated[str | None, Form()] = None,
                    fila_encabezado: Annotated[int | None, Form()] = None, guardar_mapeo: Annotated[str | None, Form()] = None):
    _ver(db, empresa_id, usuario, run_id)
    try:
        mm = json.loads(mapeo) if mapeo else None
    except ValueError:
        raise HTTPException(422, "Homologación no válida")
    return _ok(servicio.cargar_archivo, db, empresa_id, run_id, lado.upper(), usuario, archivo.filename or "archivo", archivo.file.read(),
               mapeo_manual=mm, fila_encabezado=fila_encabezado, guardar_mapeo=guardar_mapeo, confirmar=confirmar)


class EjecutarIn(BaseModel):
    forzar: bool = False


@router.post("/{run_id}/ejecutar", status_code=202)
def ejecutar(run_id: int, db: DB, usuario: Usuario, empresa_id: int, d: EjecutarIn | None = None):
    _ver(db, empresa_id, usuario, run_id)
    forzar = bool(d and d.forzar)
    _ok(servicio.preparar, db, empresa_id, run_id, usuario, forzar)

    def tarea(avance):
        with SessionLocal() as s:
            return servicio.ejecutar(s, run_id, avance, forzar)
    return {"run_id": run_id, "trabajo": trabajos.crear("CONCILIACION", tarea)}


@router.post("/{run_id}/cancelar")
def cancelar(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    c, _ = _ver(db, empresa_id, usuario, run_id)
    _ok(servicio.exigir, db, empresa_id, usuario, "operar", c.tipo_codigo)
    if c.estado_proceso not in ("EN_COLA", "PROCESANDO"):
        raise HTTPException(409, "La conciliación no se está ejecutando")
    c.cancelar = True
    db.commit()
    return {"ok": True}


@router.get("/{run_id}/registros")
def registros(run_id: int, db: DB, usuario: Usuario, empresa_id: int, lado: str = "A", pasada: str | None = None, estado: str | None = None,
              buscar: str | None = None, cuenta: str | None = None, tercero: str | None = None, moneda: str | None = None,
              concepto: str | None = None, centro_costo: str | None = None, proyecto: str | None = None, desde: date | None = None,
              hasta: date | None = None, importe: str | None = None, version_id: int | None = None, pagina: int = 1, por_pagina: int = 50):
    c, ve = _ver(db, empresa_id, usuario, run_id)
    f = dict(lado=lado.upper(), pasada=pasada, estado=estado, buscar=buscar, cuenta=cuenta, tercero=tercero, moneda=moneda, concepto=concepto,
             centro_costo=centro_costo, proyecto=proyecto, desde=desde, hasta=hasta, importe=importe, pagina=pagina, por_pagina=por_pagina)
    return consultas.registros(db, c, f, ve, version_id)


@router.get("/{run_id}/grupos")
def grupos(run_id: int, db: DB, usuario: Usuario, empresa_id: int, estado: str | None = None, tipo: str | None = None, pasada: str | None = None,
           origen: str | None = None, version_id: int | None = None, pagina: int = 1, por_pagina: int = 50):
    c, ve = _ver(db, empresa_id, usuario, run_id)
    return consultas.grupos(db, c, dict(estado=estado, tipo=tipo, pasada=pasada, origen=origen, pagina=pagina, por_pagina=por_pagina), ve, version_id)


class Seleccion(BaseModel):
    id: int
    importe: str | None = None


class ManualIn(BaseModel):
    pasada: str = "A-B"
    registros_a: list[Seleccion]
    registros_b: list[Seleccion]
    justificacion: str
    aceptar_diferencia: bool = False


@router.post("/{run_id}/manual", status_code=201)
def manual(run_id: int, d: ManualIn, db: DB, usuario: Usuario, empresa_id: int):
    _ver(db, empresa_id, usuario, run_id)
    datos = d.model_dump()
    g = _ok(servicio.conciliar_manual, db, empresa_id, run_id, usuario, datos)
    return consultas.fila(g, ("huellas",))


class DecisionIn(BaseModel):
    motivo: str | None = None


@router.post("/grupos/{grupo_id}/{accion}")
def decidir(grupo_id: int, accion: str, db: DB, usuario: Usuario, empresa_id: int, d: DecisionIn | None = None):
    g = db.get(GrupoConciliacion, grupo_id)
    if not g:
        raise HTTPException(404, "Coincidencia no encontrada")
    _ver(db, empresa_id, usuario, g.run_id)
    if accion not in ("confirmar", "rechazar", "revertir"):
        raise HTTPException(404, "Acción no válida")
    g = _ok(servicio.decidir_grupo, db, empresa_id, grupo_id, usuario, accion, d.motivo if d else None)
    return consultas.fila(g, ("huellas",))


class EstadoIn(BaseModel):
    estado: str
    comentario: str | None = None
    lock_version: int | None = None


@router.post("/{run_id}/estado")
def estado(run_id: int, d: EstadoIn, db: DB, usuario: Usuario, empresa_id: int):
    _, ve = _ver(db, empresa_id, usuario, run_id)
    c = _ok(servicio.cambiar_estado, db, empresa_id, run_id, usuario, d.estado, d.comentario, d.lock_version)
    return consultas.conciliacion(db, c, ve)


class MotivoIn(BaseModel):
    motivo: str


@router.post("/{run_id}/revertir")
def revertir(run_id: int, d: MotivoIn, db: DB, usuario: Usuario, empresa_id: int):
    _, ve = _ver(db, empresa_id, usuario, run_id)
    c = _ok(servicio.revertir_conciliacion, db, empresa_id, run_id, usuario, d.motivo)
    return consultas.conciliacion(db, c, ve)


@router.get("/{run_id}/historial")
def historial(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    c, _ = _ver(db, empresa_id, usuario, run_id)
    return consultas.historial(db, c)


@router.get("/{run_id}/a-fecha")
def a_fecha(run_id: int, fecha: date, db: DB, usuario: Usuario, empresa_id: int):
    c, ve = _ver(db, empresa_id, usuario, run_id)
    return consultas.a_fecha(db, c, fecha, ve)


@router.get("/{run_id}/exportar")
def exportar_run(run_id: int, db: DB, usuario: Usuario, empresa_id: int, formato: str = "xlsx", version_id: int | None = None):
    c, ve = _ver(db, empresa_id, usuario, run_id)
    r = _ok(servicio.exigir, db, empresa_id, usuario, "exportar")
    p = _ok(exportar.preparar, db, c, version_id, ve)
    contenido = exportar.pdf(p) if formato == "pdf" else exportar.excel(p)
    servicio.auditar(db, empresa_id, usuario, "EXPORTAR", "conciliacion", c.id, {"formato": formato, "version": p["v"].numero}, r, c)
    db.commit()
    return _archivo(contenido, f"conciliacion_{c.tipo_codigo.lower()}_{c.fecha_corte:%Y%m%d}_v{p['v'].numero}", formato)


@router.post("/tasas/{regla_id}/aprobar")
def aprobar_tasa(regla_id: int, db: DB, usuario: Usuario, empresa_id: int, d: DecisionIn | None = None):
    _empresa(db, empresa_id)
    x = _ok(servicio.aprobar_regla_tributaria, db, empresa_id, usuario, regla_id, d.motivo if d else None)
    return {"id": x.id, "tipo": x.tipo, "codigo": x.codigo, "autorizado_por": x.autorizado_por}
