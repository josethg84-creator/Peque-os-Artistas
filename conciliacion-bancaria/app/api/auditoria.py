"""API del Auditor contable inteligente 360 (fase 7). Todo se acota a `empresa_id` y al rol del usuario (cabecera X-Usuario).
Herramienta de apoyo: no emite dictámenes, no modifica asientos, no genera ajustes ni declara fraude o infracciones."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.api.deps import DB, Usuario
from app.auditoria import catalogo, configurables, consultas, estadistica, informes, motor, papeles, riesgo, servicio
from app.auditoria.base import Contexto
from app.contable import trabajos
from app.core import config
from app.core.database import SessionLocal
from app.models import (Empresa, EjecucionAuditoria, EvidenciaHallazgo, InformeAuditoria, Materialidad, MuestraAuditoria, PapelAuditoria,
                        ReglaAuditoria, VersionInforme)

router = APIRouter(prefix="/auditoria360", tags=["Auditor contable 360"])
ERRORES = (servicio.SinPermiso, servicio.ErrorAuditoria, servicio.Conflicto, LookupError)


def _empresa(db, e) -> Empresa:
    x = db.get(Empresa, e)
    if not x:
        raise HTTPException(404, "Empresa no encontrada")
    return x


def _ok(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ERRORES as exc:
        if isinstance(exc, LookupError):
            raise HTTPException(404, str(exc).strip("'"))
        raise HTTPException(exc.status, str(exc))


def _consultar(db, empresa_id, usuario):
    _empresa(db, empresa_id)
    return _ok(servicio.exigir, db, empresa_id, usuario, "consultar")


def _archivo(contenido, nombre, formato):
    if formato == "pdf":
        return Response(contenido, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{nombre}.pdf"'})
    return Response(contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.xlsx"'})


# ------------------------------------------------------------------ catálogo
@router.get("/catalogo")
def catalogo_(db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    catalogo.sembrar(db)
    db.commit()
    return {"categorias": [{"codigo": c, "nombre": n, "descripcion": d} for c, n, d in catalogo.CATEGORIAS],
            "tipos_auditoria": list(servicio.TIPOS_AUDITORIA), "estados": list(servicio.TRANS), "riesgos": list(riesgo.NIVELES)[::-1],
            "regularizacion": list(servicio.REGULARIZACION), "bases_materialidad": list(riesgo.BASES), "metodos_muestra": list(papeles.METODOS),
            "informes": informes.TIPOS, "exportaciones": informes.EXPORTS, "sistemas_erp": list(consultas.SISTEMAS),
            "fuentes_configurables": {k: list(v) for k, v in configurables.CAMPOS.items()}, "operadores": sorted(configurables.OPERADORES),
            "rol": servicio.rol(db, empresa_id, usuario), "permisos": {k: servicio.puede(db, empresa_id, usuario, k) for k in servicio.PERMISOS},
            "matriz": riesgo.matriz_vigente(db, empresa_id), "aviso": informes.AVISO}


@router.get("/reglas")
def reglas(db: DB, usuario: Usuario, empresa_id: int, modulo: str | None = None, buscar: str | None = None):
    _consultar(db, empresa_id, usuario)
    return consultas.reglas(db, empresa_id, {"modulo": modulo, "buscar": buscar})


class ReglaIn(BaseModel):
    codigo: str | None = None
    categoria: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    definicion: dict | None = None
    cuentas: str | None = None
    fuente: str | None = None
    parametros: dict | None = None
    riesgo: str | None = None
    probabilidad: int | None = Field(None, ge=1, le=5)
    criterio: str | None = None
    recomendacion: str | None = None
    evidencia_requerida: str | None = None
    excepciones: dict | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    normativa: bool | None = None
    norma_referencia: str | None = None
    fuente_oficial: str | None = None
    fecha_publicacion: date | None = None
    condiciones_aplicacion: str | None = None
    excepciones_normativas: str | None = None
    responsable_validacion: str | None = None
    motivo: str | None = None


@router.post("/reglas", status_code=201)
def crear_regla(d: ReglaIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    r = _ok(servicio.guardar_regla, db, empresa_id, usuario, d.model_dump(exclude_unset=True))
    return consultas.fila(r)


@router.put("/reglas/{rule_id}")
def editar_regla(rule_id: int, d: ReglaIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    r = _ok(servicio.guardar_regla, db, empresa_id, usuario, d.model_dump(exclude_unset=True), rule_id)
    return consultas.fila(r)


class ActivarIn(BaseModel):
    activa: bool


@router.post("/reglas/{rule_id}/activar")
def activar(rule_id: int, d: ActivarIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(servicio.activar_regla, db, empresa_id, usuario, rule_id, d.activa))


class ValidarIn(BaseModel):
    aprobar: bool = True
    comentario: str | None = None


@router.post("/reglas/{rule_id}/validar")
def validar(rule_id: int, d: ValidarIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(servicio.validar_regla, db, empresa_id, usuario, rule_id, d.aprobar, d.comentario))


@router.get("/reglas/{rule_id}/versiones")
def versiones(rule_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    r = db.get(ReglaAuditoria, rule_id)
    if not r or r.empresa_id not in (None, empresa_id):
        raise HTTPException(404, "Regla no encontrada")
    return consultas.versiones_regla(db, rule_id)


class VistaIn(BaseModel):
    engagement_id: int
    definicion: dict
    limite: int = Field(50, ge=1, le=500)


@router.post("/reglas/vista-previa")
def vista_previa(d: VistaIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    return _ok(servicio.vista_previa, db, empresa_id, usuario, d.engagement_id, d.definicion, d.limite)


# ------------------------------------------------------------------ materialidad, matriz, configuración del ERP
class MaterialidadIn(BaseModel):
    ejercicio: int
    periodo: int = 12
    base: str
    importe_base: str | None = None
    descripcion_base: str | None = None
    porcentaje_global: str
    porcentaje_ejecucion: str
    porcentaje_insignificante: str
    por_cuenta: dict | None = None
    por_tipo: dict | None = None
    cualitativos: dict | None = None
    justificacion: str


@router.get("/materialidad")
def materialidades(db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    from sqlalchemy import select
    return [consultas.fila(m) for m in db.scalars(select(Materialidad).where(Materialidad.empresa_id == empresa_id).order_by(Materialidad.id.desc()))]


@router.post("/materialidad", status_code=201)
def crear_materialidad(d: MaterialidadIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    return consultas.fila(_ok(servicio.crear_materialidad, db, empresa_id, usuario, d.model_dump()))


@router.post("/materialidad/{mid}/aprobar")
def aprobar_materialidad(mid: int, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(servicio.aprobar_materialidad, db, empresa_id, usuario, mid))


class MatrizIn(BaseModel):
    nombre: str | None = None
    matriz: list
    factores: dict | None = None


@router.post("/matriz", status_code=201)
def matriz(d: MatrizIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    return consultas.fila(_ok(servicio.guardar_matriz, db, empresa_id, usuario, d.model_dump()))


@router.post("/configuraciones", status_code=201)
def importar_configuracion(db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()], tipo: Annotated[str, Form()],
                           sistema: Annotated[str, Form()] = "OTRO", sustento: Annotated[str | None, Form()] = None,
                           vigente_desde: Annotated[date | None, Form()] = None):
    _empresa(db, empresa_id)
    c = _ok(consultas.importar_configuracion, db, empresa_id, usuario, tipo, sistema, archivo.filename or "config.csv", archivo.file.read(), sustento,
            vigente_desde)
    return consultas.fila(c, ("items",))


@router.get("/configuraciones")
def configuraciones(db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    from sqlalchemy import select
    from app.models import ConfiguracionImportada
    return [consultas.fila(c, ("items",)) for c in db.scalars(select(ConfiguracionImportada).where(ConfiguracionImportada.empresa_id == empresa_id)
                                                               .order_by(ConfiguracionImportada.tipo, ConfiguracionImportada.version))]


# ------------------------------------------------------------------ encargos
class EncargoIn(BaseModel):
    tipo: str = "INTEGRAL"
    nombre: str | None = None
    ejercicio: int | None = None
    periodo: int | None = Field(None, ge=1, le=12)
    fecha_corte: date | None = None
    objetivo: str | None = None
    responsable: str | None = None
    materialidad_id: int | None = None
    recurrencia: str | None = Field(None, pattern="^(MENSUAL|TRIMESTRAL|ANUAL)$")
    alcance: dict = {}


@router.get("/encargos")
def encargos(db: DB, usuario: Usuario, empresa_id: int, estado: str | None = None, ejercicio: int | None = None, pagina: int = 1, por_pagina: int = 50):
    _consultar(db, empresa_id, usuario)
    from app.models import EncargoAuditoria
    q = consultas.encargos_visibles(db, empresa_id, usuario)
    if estado:
        q = q.where(EncargoAuditoria.estado == estado)
    if ejercicio:
        q = q.where(EncargoAuditoria.ejercicio == ejercicio)
    total, qp, pagina, pp = consultas.paginar(db, q.order_by(EncargoAuditoria.fecha_corte.desc(), EncargoAuditoria.id.desc()), pagina, por_pagina)
    return {"total": total, "pagina": pagina, "por_pagina": pp, "items": [consultas.fila(e) for e in db.scalars(qp)]}


@router.post("/encargos", status_code=201)
def crear_encargo(d: EncargoIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    if not d.fecha_corte and not (d.ejercicio and d.periodo):
        raise HTTPException(422, "Indique la fecha de corte o el ejercicio y periodo")
    e = _ok(servicio.crear_encargo, db, empresa_id, usuario, d.model_dump())
    return consultas.encargo_dict(db, e)


@router.get("/encargos/{eid}")
def encargo(eid: int, db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    return consultas.encargo_dict(db, _ok(servicio.cargar_encargo, db, empresa_id, eid, usuario))


class AlcanceIn(BaseModel):
    alcance: dict


@router.put("/encargos/{eid}/alcance")
def alcance(eid: int, d: AlcanceIn, db: DB, usuario: Usuario, empresa_id: int):
    r = _ok(servicio.exigir, db, empresa_id, usuario, "crear_encargo")
    e = _ok(servicio.cargar_encargo, db, empresa_id, eid, usuario)
    _ok(servicio.guardar_alcance, db, e, d.alcance)
    servicio.evento(db, empresa_id, usuario, "ALCANCE", "encargo", e.id, d.alcance, r, e.id)
    db.commit()
    return consultas.encargo_dict(db, e)


class EstadoEncIn(BaseModel):
    estado: str
    conclusion: str | None = None
    lock_version: int | None = None


@router.post("/encargos/{eid}/estado")
def estado_encargo(eid: int, d: EstadoEncIn, db: DB, usuario: Usuario, empresa_id: int):
    e = _ok(servicio.cambiar_estado_encargo, db, empresa_id, eid, usuario, d.estado, d.conclusion, d.lock_version)
    return consultas.encargo_dict(db, e)


@router.post("/encargos/{eid}/programar-siguiente", status_code=201)
def programar(eid: int, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.encargo_dict(db, _ok(servicio.programar_siguiente, db, empresa_id, eid, usuario))


class EjecutarIn(BaseModel):
    tipo: str = Field("COMPLETA", pattern="^(COMPLETA|MODULO|CUENTA|REGLAS)$")
    modulos: list[str] | None = None
    cuentas: list[str] | None = None
    reglas: list[str] | None = None
    forzar: bool = False


@router.post("/encargos/{eid}/ejecutar", status_code=202)
def ejecutar(eid: int, d: EjecutarIn, db: DB, usuario: Usuario, empresa_id: int):
    r = _ok(servicio.exigir, db, empresa_id, usuario, "ejecutar")
    e = _ok(servicio.cargar_encargo, db, empresa_id, eid, usuario)
    if e.estado in ("CONCLUIDO", "CERRADO"):
        raise HTTPException(422, "El encargo está concluido o cerrado.")
    from sqlalchemy import select
    if db.scalar(select(EjecucionAuditoria.id).where(EjecucionAuditoria.engagement_id == e.id, EjecucionAuditoria.estado_proceso.in_(("EN_COLA", "PROCESANDO")))):
        raise HTTPException(409, "Ya hay una ejecución en curso para este encargo.")
    params = {k: v for k, v in d.model_dump().items() if k != "tipo" and v}
    run = motor.crear_run(db, e, usuario, d.tipo, params)
    servicio.evento(db, empresa_id, usuario, "EJECUTAR_AUDITORIA", "ejecucion", run.id, {"tipo": d.tipo, **params}, r, e.id, run.id)
    db.commit()
    rid = run.id

    def tarea(avance):
        with SessionLocal() as s:
            return {"run_id": rid, "resumen": motor.ejecutar(s, rid, avance).get("resumen", {}).get("totales")}
    return {"run_id": rid, "trabajo": trabajos.crear("AUDITORIA", tarea)}


@router.post("/ejecuciones/{rid}/cancelar")
def cancelar(rid: int, db: DB, usuario: Usuario, empresa_id: int):
    _ok(servicio.exigir, db, empresa_id, usuario, "ejecutar")
    run = db.get(EjecucionAuditoria, rid)
    if not run or run.empresa_id != empresa_id:
        raise HTTPException(404, "Ejecución no encontrada")
    if run.estado_proceso not in ("EN_COLA", "PROCESANDO"):
        raise HTTPException(409, "La ejecución no está en curso")
    run.cancelar = True
    db.commit()
    return {"ok": True}


@router.get("/ejecuciones/{rid}")
def ejecucion(rid: int, db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    run = db.get(EjecucionAuditoria, rid)
    if not run or run.empresa_id != empresa_id:
        raise HTTPException(404, "Ejecución no encontrada")
    _ok(servicio.cargar_encargo, db, empresa_id, run.engagement_id, usuario)
    import json
    return {**consultas.fila(run, ("reglas_snapshot",)), "resumen": json.loads(run.resumen) if run.resumen else None,
            "tiempos": json.loads(run.tiempos) if run.tiempos else None, "resultados": consultas.resultados_run(db, rid)}


@router.get("/trabajos/{tid}")
def trabajo(tid: str):
    t = trabajos.obtener(tid)
    if not t:
        raise HTTPException(404, "Trabajo no encontrado")
    return t


# ------------------------------------------------------------------ hallazgos
@router.get("/hallazgos")
def hallazgos(db: DB, usuario: Usuario, empresa_id: int, engagement_id: int | None = None, modulo: str | None = None, estado: str | None = None, tipo: str | None = None, regla_codigo: str | None = None, responsable: str | None = None, cuenta: str | None = None,
              tercero: str | None = None, centro_costo: str | None = None, grupo_id: int | None = None, regularizacion: str | None = None,
              solo_vigentes: bool = False, bandeja: bool = False, vencidos: bool = False, buscar: str | None = None, orden: str | None = None,
              pagina: int = 1, por_pagina: int = 50, riesgo: str | None = None):
    _consultar(db, empresa_id, usuario)
    f = dict(engagement_id=engagement_id, modulo=modulo, riesgo=riesgo, estado=estado, tipo=tipo, regla_codigo=regla_codigo, responsable=responsable,
             cuenta=cuenta, tercero=tercero, centro_costo=centro_costo, grupo_id=grupo_id, regularizacion=regularizacion, solo_vigentes=solo_vigentes,
             bandeja=bandeja, vencidos=vencidos, buscar=buscar, orden=orden, pagina=pagina, por_pagina=por_pagina)
    return consultas.hallazgos(db, empresa_id, usuario, f)


@router.get("/hallazgos/{hid}")
def hallazgo(hid: int, db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    h = _ok(servicio.cargar_hallazgo, db, empresa_id, hid, usuario)
    return consultas.hallazgo_detalle(db, empresa_id, usuario, h)


class EstadoIn(BaseModel):
    estado: str
    comentario: str | None = None
    lock_version: int | None = None
    regularizacion: str | None = None
    importe_confirmado: str | None = None


@router.post("/hallazgos/{hid}/estado")
def estado_hallazgo(hid: int, d: EstadoIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    h = _ok(servicio.cambiar_estado, db, empresa_id, hid, usuario, d.estado, d.comentario, d.lock_version,
            {k: v for k, v in (("regularizacion", d.regularizacion), ("importe_confirmado", d.importe_confirmado)) if v})
    return consultas.hallazgo_detalle(db, empresa_id, usuario, h)


class HallazgoIn(BaseModel):
    responsable: str | None = None
    fecha_limite: str | None = None
    causa: str | None = None
    efecto: str | None = None
    recomendacion: str | None = None
    riesgo: str | None = None
    justificacion_riesgo: str | None = None
    regularizacion: str | None = None
    comentario: str | None = None
    lock_version: int | None = None


@router.patch("/hallazgos/{hid}")
def actualizar(hid: int, d: HallazgoIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    h = _ok(servicio.actualizar_hallazgo, db, empresa_id, hid, usuario, d.model_dump(exclude_unset=True))
    return consultas.hallazgo_detalle(db, empresa_id, usuario, h)


class ComentarioIn(BaseModel):
    texto: str


@router.post("/hallazgos/{hid}/comentarios", status_code=201)
def comentar(hid: int, d: ComentarioIn, db: DB, usuario: Usuario, empresa_id: int):
    _ok(servicio.comentar, db, empresa_id, hid, usuario, d.texto)
    return {"ok": True}


@router.post("/hallazgos/{hid}/evidencias", status_code=201)
def evidencia(hid: int, db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()],
              descripcion: Annotated[str | None, Form()] = None, confidencial: Annotated[bool, Form()] = False):
    _empresa(db, empresa_id)
    e = _ok(servicio.adjuntar_evidencia, db, empresa_id, hid, usuario, archivo.filename or "evidencia", archivo.content_type, archivo.file.read(),
            descripcion, confidencial)
    return consultas.fila(e, ("ruta",))


@router.get("/evidencias/{evid}")
def descargar(evid: int, db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    e = db.get(EvidenciaHallazgo, evid)
    if not e or not e.ruta:
        raise HTTPException(404, "Evidencia no encontrada")
    h = _ok(servicio.cargar_hallazgo, db, empresa_id, e.finding_id, usuario)
    if e.confidencial and not servicio.puede(db, empresa_id, usuario, "datos_personales" if h.personal else "confidencial"):
        raise HTTPException(403, "Evidencia confidencial")
    from pathlib import Path
    return FileResponse(Path(config.DATA_DIR) / e.ruta, filename=e.nombre_archivo)


class PlanIn(BaseModel):
    descripcion: str
    responsable: str
    fecha_compromiso: date


@router.post("/hallazgos/{hid}/planes", status_code=201)
def plan(hid: int, d: PlanIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(servicio.crear_plan, db, empresa_id, hid, usuario, d.model_dump()))


class PlanUpdIn(BaseModel):
    estado: str | None = None
    avance: int | None = Field(None, ge=0, le=100)
    comentario_cierre: str | None = None


@router.patch("/planes/{pid}")
def plan_upd(pid: int, d: PlanUpdIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(servicio.actualizar_plan, db, empresa_id, pid, usuario, d.model_dump(exclude_unset=True)))


@router.post("/hallazgos/{hid}/regularizacion")
def regularizacion(hid: int, db: DB, usuario: Usuario, empresa_id: int):
    h = _ok(servicio.enviar_regularizacion, db, empresa_id, hid, usuario)
    return consultas.hallazgo_detalle(db, empresa_id, usuario, h)


class GrupoIn(BaseModel):
    engagement_id: int
    hallazgos: list[int]
    titulo: str | None = None


@router.post("/grupos", status_code=201)
def grupo(d: GrupoIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(servicio.agrupar, db, empresa_id, usuario, d.engagement_id, d.hallazgos, d.titulo))


class AsignacionIn(BaseModel):
    tipo: str
    usuario: str
    engagement_id: int | None = None
    funcion: str | None = None
    vigente_hasta: str | None = None


@router.post("/asignaciones", status_code=201)
def asignacion(d: AsignacionIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(servicio.asignar, db, empresa_id, usuario, d.model_dump()))


# ------------------------------------------------------------------ muestras y papeles
class MuestraIn(BaseModel):
    nombre: str | None = None
    poblacion: str = "LINEAS"
    metodo: str
    tamano: int = Field(ge=1, le=5000)
    semilla: int | None = None
    criterios: dict = {}
    workpaper_id: int | None = None


@router.post("/encargos/{eid}/muestras", status_code=201)
def muestra(eid: int, d: MuestraIn, db: DB, usuario: Usuario, empresa_id: int):
    m = _ok(papeles.crear_muestra, db, empresa_id, eid, usuario, d.model_dump())
    return consultas.muestra_dict(db, m)


@router.get("/muestras/{mid}")
def ver_muestra(mid: int, db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    m = db.get(MuestraAuditoria, mid)
    if not m:
        raise HTTPException(404, "Muestra no encontrada")
    _ok(servicio.cargar_encargo, db, empresa_id, m.engagement_id, usuario)
    return consultas.muestra_dict(db, m)


class ItemIn(BaseModel):
    resultado: str
    comentario: str | None = None


@router.post("/muestras/items/{iid}")
def evaluar_item(iid: int, d: ItemIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.fila(_ok(papeles.evaluar_item, db, empresa_id, usuario, iid, d.resultado, d.comentario))


class PapelIn(BaseModel):
    regla: str


@router.post("/encargos/{eid}/papeles", status_code=201)
def papel(eid: int, d: PapelIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.papel_dict(_ok(papeles.generar_papel, db, empresa_id, eid, usuario, d.regla))


@router.get("/encargos/{eid}/papeles")
def papeles_(eid: int, db: DB, usuario: Usuario, empresa_id: int):
    _consultar(db, empresa_id, usuario)
    e = _ok(servicio.cargar_encargo, db, empresa_id, eid, usuario)
    from sqlalchemy import select
    return [consultas.papel_dict(p) for p in db.scalars(select(PapelAuditoria).where(PapelAuditoria.engagement_id == e.id).order_by(PapelAuditoria.id))]


class PapelEstadoIn(BaseModel):
    estado: str
    conclusion: str | None = None


@router.post("/papeles/{pid}/estado")
def papel_estado(pid: int, d: PapelEstadoIn, db: DB, usuario: Usuario, empresa_id: int):
    return consultas.papel_dict(_ok(papeles.cambiar_estado_papel, db, empresa_id, pid, usuario, d.estado, d.conclusion))


# ------------------------------------------------------------------ tablero, informes, exportación, bitácora
@router.get("/tablero")
def tablero(db: DB, usuario: Usuario, empresa_id: int, engagement_id: int | None = None, ejercicio: int | None = None):
    _consultar(db, empresa_id, usuario)
    return consultas.tablero(db, empresa_id, usuario, engagement_id, ejercicio)


@router.get("/encargos/{eid}/estadistica")
def estadistica_(eid: int, db: DB, usuario: Usuario, empresa_id: int, cuenta: str | None = None):
    _consultar(db, empresa_id, usuario)
    e = _ok(servicio.cargar_encargo, db, empresa_id, eid, usuario)
    return estadistica.resumen(Contexto(db, e, motor.alcance_de(db, e), None), cuenta)


class InformeIn(BaseModel):
    tipo: str
    cuenta: str | None = None


@router.post("/encargos/{eid}/informes", status_code=201)
def informe(eid: int, d: InformeIn, db: DB, usuario: Usuario, empresa_id: int):
    inf = _ok(informes.generar_informe, db, empresa_id, eid, usuario, d.tipo, d.cuenta)
    import json
    from sqlalchemy import select
    v = db.scalar(select(VersionInforme).where(VersionInforme.report_id == inf.id, VersionInforme.numero == inf.version_actual))
    return {**consultas.fila(inf), "contenido": json.loads(v.contenido), "hash": v.hash}


@router.get("/informes/{iid}/exportar")
def exportar_informe(iid: int, db: DB, usuario: Usuario, empresa_id: int, formato: str = "pdf", version: int | None = None):
    _ok(servicio.exigir, db, empresa_id, usuario, "exportar")
    inf = db.get(InformeAuditoria, iid)
    if not inf:
        raise HTTPException(404, "Informe no encontrado")
    _ok(servicio.cargar_encargo, db, empresa_id, inf.engagement_id, usuario)
    contenido = informes.informe_pdf(db, inf, empresa_id, version) if formato == "pdf" else informes.informe_excel(db, inf, version)
    return _archivo(contenido, f"informe_{inf.tipo.lower()}_v{version or inf.version_actual}", formato)


@router.get("/encargos/{eid}/exportar/{tipo}")
def exportar(eid: int, tipo: str, db: DB, usuario: Usuario, empresa_id: int, formato: str = "xlsx"):
    _empresa(db, empresa_id)
    contenido = _ok(informes.exportar, db, empresa_id, eid, usuario, tipo.upper(), formato)
    return _archivo(contenido, f"auditoria_{tipo.lower()}", formato)


@router.get("/bitacora")
def bitacora(db: DB, usuario: Usuario, empresa_id: int, engagement_id: int | None = None, pagina: int = 1, por_pagina: int = 100):
    _empresa(db, empresa_id)
    _ok(servicio.exigir, db, empresa_id, usuario, "revisar")
    from sqlalchemy import select
    from app.models import EventoAuditoria
    q = select(EventoAuditoria).where(EventoAuditoria.empresa_id == empresa_id)
    if engagement_id:
        q = q.where(EventoAuditoria.engagement_id == engagement_id)
    total, qp, pagina, pp = consultas.paginar(db, q.order_by(EventoAuditoria.id.desc()), pagina, por_pagina)
    return {"total": total, "pagina": pagina, "por_pagina": pp, "items": [consultas.fila(e) for e in db.scalars(qp)],
            "verificacion": riesgo.verificar_bitacora(db, empresa_id)}
