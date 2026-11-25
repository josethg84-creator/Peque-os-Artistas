"""API del motor de compensación de partidas (fase 4). Toda operación se acota a `empresa_id`
y verifica el rol del usuario (cabecera X-Usuario). La compensación es analítica: no modifica asientos."""
import json
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import OperationalError

from app.analisis import exportar
from app.api.deps import DB, Usuario
from app.compensacion import consultas, motor, partidas, servicio
from app.contable import trabajos
from app.core.database import SessionLocal
from app.models import (AdjuntoCompensacion, Aplicacion, AprobacionCompensacion, AuditoriaCompensacion, CandidatoCompensacion,
                        ComentarioCompensacion, EjecucionCompensacion, Empresa, ExcepcionCompensacion, GrupoCompensacion,
                        PartidaAbierta, PartidaFuente, ReglaCompensacion, ReversionCompensacion, RolUsuario)
from app.models.compensacion import ROLES

router = APIRouter(prefix="/compensacion", tags=["Compensación de partidas"])


def _empresa(db, empresa_id) -> Empresa:
    e = db.get(Empresa, empresa_id)
    if not e:
        raise HTTPException(404, "Empresa no encontrada")
    return e


def _permiso(db, empresa_id, usuario, accion) -> str:
    _empresa(db, empresa_id)
    try:
        return servicio.exigir(db, empresa_id, usuario, accion)
    except servicio.SinPermiso as exc:
        raise HTTPException(403, str(exc))


def _err(exc):
    raise HTTPException(getattr(exc, "status", 422), str(exc))


def _j(v):
    if isinstance(v, Decimal):
        return str(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _fila(o, excluir=()):
    return {c.key: _j(getattr(o, c.key)) for c in o.__table__.columns if c.key not in excluir}


def _corte(fecha_corte: date | None) -> date:
    return fecha_corte or date.today()


# ------------------------------------------------------------------ sesión, roles y configuración
@router.get("/mi-rol")
def mi_rol(db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    rol, abierto = servicio.rol_de(db, empresa_id, usuario)
    return {"usuario": usuario, "rol": rol, "modo_abierto": abierto,
            "permisos": sorted(a for a, roles in servicio.PERMISOS.items() if rol in roles)}


class RolIn(BaseModel):
    usuario: str = Field(min_length=2, max_length=80)
    rol: str


@router.get("/roles")
def listar_roles(db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    return [_fila(r) for r in db.scalars(select(RolUsuario).where(RolUsuario.empresa_id == empresa_id).order_by(RolUsuario.usuario))]


@router.post("/roles", status_code=201)
def asignar_rol(datos: RolIn, db: DB, usuario: Usuario, empresa_id: int):
    rol_actual = _permiso(db, empresa_id, usuario, "roles")
    if datos.rol not in ROLES:
        raise HTTPException(422, "Rol no válido")
    existentes = db.scalars(select(RolUsuario).where(RolUsuario.empresa_id == empresa_id)).all()
    if not existentes and datos.rol != "ADMINISTRADOR" and datos.usuario.lower() != usuario.lower():
        # al salir del modo abierto, quien configura queda como administrador para no perder el acceso
        db.add(RolUsuario(empresa_id=empresa_id, usuario=usuario, rol="ADMINISTRADOR", asignado_por=usuario))
    r = next((x for x in existentes if x.usuario.lower() == datos.usuario.lower()), None)
    if r:
        r.rol = datos.rol
    else:
        r = RolUsuario(empresa_id=empresa_id, usuario=datos.usuario.strip(), rol=datos.rol, asignado_por=usuario)
        db.add(r)
    motor.auditar(db, empresa_id, usuario, "ASIGNAR_ROL", "rol", None, datos.model_dump(), rol_actual)
    db.commit()
    return _fila(r)


@router.delete("/roles/{rol_id}", status_code=204)
def quitar_rol(rol_id: int, db: DB, usuario: Usuario, empresa_id: int):
    rol_actual = _permiso(db, empresa_id, usuario, "roles")
    r = db.get(RolUsuario, rol_id)
    if not r or r.empresa_id != empresa_id:
        raise HTTPException(404, "Rol no encontrado")
    admins = db.scalar(select(func.count()).select_from(RolUsuario).where(RolUsuario.empresa_id == empresa_id, RolUsuario.rol == "ADMINISTRADOR"))
    if r.rol == "ADMINISTRADOR" and admins <= 1 and db.scalar(select(func.count()).select_from(RolUsuario).where(RolUsuario.empresa_id == empresa_id)) > 1:
        raise HTTPException(409, "No se puede quitar el último administrador mientras haya otros usuarios")
    motor.auditar(db, empresa_id, usuario, "QUITAR_ROL", "rol", r.id, _fila(r), rol_actual)
    db.delete(r)
    db.commit()


@router.get("/reglas")
def reglas(db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    partidas.sembrar(db, empresa_id)
    return [{**_fila(r, ("historial",)), "parametros": json.loads(r.parametros or "{}")}
            for r in db.scalars(select(ReglaCompensacion).where(ReglaCompensacion.empresa_id == empresa_id)
                                .order_by(ReglaCompensacion.tipo, ReglaCompensacion.codigo))]


class ReglaIn(BaseModel):
    tipo: str = Field(pattern="^(CUENTA|GENERAL|ENTRE_CUENTAS|CONVERSION_MONEDA|DETRACCION|RETENCION|PERCEPCION)$")
    codigo: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=3, max_length=160)
    parametros: dict = {}
    sustento: str | None = Field(default=None, max_length=4000)
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    activa: bool = True


def _validar_regla(d: ReglaIn):
    p = d.parametros
    if d.tipo == "ENTRE_CUENTAS":
        if len(p.get("cuentas", [])) < 2 or len((d.sustento or "").strip()) < 20:
            raise HTTPException(422, "Una regla entre cuentas requiere al menos dos cuentas y un sustento contable (≥ 20 caracteres).")
    if d.tipo == "CONVERSION_MONEDA" and len(p.get("monedas", [])) < 2:
        raise HTTPException(422, "Indique las monedas que la regla permite convertir.")
    if d.tipo in ("DETRACCION", "RETENCION", "PERCEPCION"):
        try:
            t = Decimal(str(p.get("tasa")))
        except Exception:
            raise HTTPException(422, "Indique la tasa (%) vigente según la norma aplicable.")
        if not (0 < t < 100):
            raise HTTPException(422, "Tasa fuera de rango.")
    if d.tipo == "CUENTA":
        if not d.codigo.isdigit():
            raise HTTPException(422, "El código de una regla de cuenta es el prefijo contable.")
        if int(p.get("max_combinacion", 4)) > 8 or int(p.get("max_candidatos", 20)) > 60 or int(p.get("max_nodos", 20000)) > 500000:
            raise HTTPException(422, "Límites de búsqueda combinatoria demasiado altos (máx. 8 partidas, 60 candidatos, 500 000 nodos).")
        if int(p.get("umbral_auto", 95)) < 95 and p.get("autoaprobar"):
            raise HTTPException(422, "La aprobación automática solo admite umbrales de confianza muy alta (≥ 95).")


@router.post("/reglas", status_code=201)
def crear_regla(datos: ReglaIn, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "configurar")
    _validar_regla(datos)
    if db.scalar(select(ReglaCompensacion).where(ReglaCompensacion.empresa_id == empresa_id, ReglaCompensacion.tipo == datos.tipo,
                                                  ReglaCompensacion.codigo == datos.codigo)):
        raise HTTPException(409, "Ya existe una regla con ese tipo y código")
    base = partidas.PARAMETROS_CUENTA if datos.tipo == "CUENTA" else {}
    r = ReglaCompensacion(empresa_id=empresa_id, tipo=datos.tipo, codigo=datos.codigo, nombre=datos.nombre,
                          parametros=json.dumps({**base, **datos.parametros}), sustento=datos.sustento,
                          autorizado_por=usuario if datos.tipo in ("ENTRE_CUENTAS", "CONVERSION_MONEDA") else None,
                          vigente_desde=datos.vigente_desde, vigente_hasta=datos.vigente_hasta, activa=datos.activa, usuario=usuario)
    db.add(r)
    db.flush()
    motor.auditar(db, empresa_id, usuario, "CREAR_REGLA", "regla", r.id, datos.model_dump(mode="json"), rol)
    db.commit()
    return {**_fila(r, ("historial",)), "parametros": json.loads(r.parametros)}


@router.put("/reglas/{regla_id}")
def editar_regla(regla_id: int, datos: ReglaIn, db: DB, usuario: Usuario, empresa_id: int):
    rol = _permiso(db, empresa_id, usuario, "configurar")
    r = db.get(ReglaCompensacion, regla_id)
    if not r or r.empresa_id != empresa_id:
        raise HTTPException(404, "Regla no encontrada")
    if (datos.tipo, datos.codigo) != (r.tipo, r.codigo):
        raise HTTPException(422, "El tipo y el código de una regla no se modifican")
    _validar_regla(datos)
    hist = json.loads(r.historial or "[]")
    hist.append({**_fila(r, ("historial",))})
    r.nombre, r.sustento, r.vigente_desde, r.vigente_hasta, r.activa = datos.nombre, datos.sustento, datos.vigente_desde, datos.vigente_hasta, datos.activa
    r.parametros = json.dumps({**json.loads(r.parametros or "{}"), **datos.parametros})
    r.version += 1
    r.historial, r.usuario = json.dumps(hist), usuario
    if r.tipo in ("ENTRE_CUENTAS", "CONVERSION_MONEDA"):
        r.autorizado_por = usuario
    motor.auditar(db, empresa_id, usuario, "EDITAR_REGLA", "regla", r.id, {"version": r.version, **datos.model_dump(mode="json")}, rol)
    db.commit()
    return {**_fila(r, ("historial",)), "parametros": json.loads(r.parametros)}


# ------------------------------------------------------------------ ejecuciones
class EjecucionIn(BaseModel):
    fecha_corte: date
    cuentas: list[str] | None = None
    forzar: bool = False


@router.post("/ejecuciones", status_code=202)
def ejecutar(datos: EjecucionIn, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "ejecutar")
    try:
        run, nuevo = motor.crear(db, empresa_id, datos.fecha_corte, usuario, datos.cuentas, datos.forzar)
    except motor.Conflicto as exc:
        _err(exc)
    if not nuevo:
        return {"run_id": run.id, "reutilizado": True, "trabajo": None}
    rid = run.id

    def tarea(avance):
        # reintentos controlados ante bloqueos transitorios de la base de datos
        for intento in range(3):
            try:
                with SessionLocal() as s:
                    return motor.ejecutar(s, rid, avance)
            except OperationalError:
                if intento == 2:
                    raise
                import time
                time.sleep(0.5 * (intento + 1))
                with SessionLocal() as s:
                    r = s.get(EjecucionCompensacion, rid)
                    r.estado, r.error = "EN_COLA", None
                    s.commit()
    return {"run_id": rid, "reutilizado": False, "trabajo": trabajos.crear("COMPENSACION", tarea)}


def _run(db, run_id, empresa_id) -> EjecucionCompensacion:
    r = db.get(EjecucionCompensacion, run_id)
    if not r or r.empresa_id != empresa_id:
        raise HTTPException(404, "Ejecución no encontrada")
    return r


@router.get("/ejecuciones")
def listar_ejecuciones(db: DB, usuario: Usuario, empresa_id: int, limite: int = 30):
    _permiso(db, empresa_id, usuario, "consultar")
    return [{**_fila(r, ("reglas_snapshot",)), "resumen": json.loads(r.resumen) if r.resumen else None,
             "tiempos": json.loads(r.tiempos) if r.tiempos else None}
            for r in db.scalars(select(EjecucionCompensacion).where(EjecucionCompensacion.empresa_id == empresa_id)
                                .order_by(EjecucionCompensacion.id.desc()).limit(min(limite, 200)))]


@router.get("/ejecuciones/{run_id}")
def obtener_ejecucion(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    r = _run(db, run_id, empresa_id)
    return {**_fila(r), "resumen": json.loads(r.resumen) if r.resumen else None, "tiempos": json.loads(r.tiempos) if r.tiempos else None,
            "reglas_snapshot": json.loads(r.reglas_snapshot) if r.reglas_snapshot else None}


@router.post("/ejecuciones/{run_id}/cancelar")
def cancelar(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "ejecutar")
    r = _run(db, run_id, empresa_id)
    if r.estado not in ("EN_COLA", "PROCESANDO"):
        raise HTTPException(409, "La ejecución ya terminó")
    r.cancelar = True
    motor.auditar(db, empresa_id, usuario, "CANCELAR", "run", r.id)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ partidas
@router.get("/partidas")
def listar_partidas(db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None, cuenta: str | None = None,
                    tercero: str | None = None, rol: str | None = None, clase: str | None = None, moneda: str | None = None,
                    estado_cancelacion: str | None = None, estado_vencimiento: str | None = None, texto: str | None = None,
                    solo_disponibles: bool = False, solo_pendientes: bool = False, pagina: int = 1, por_pagina: int = 100,
                    orden: str = "fecha"):
    _permiso(db, empresa_id, usuario, "consultar")
    corte = _corte(fecha_corte)
    extra = None
    if texto:
        t = f"%{texto}%"
        extra = or_(PartidaAbierta.numero.ilike(t), PartidaAbierta.serie.ilike(t), PartidaAbierta.glosa.ilike(t),
                    PartidaAbierta.razon_social.ilike(t), PartidaAbierta.tercero.ilike(t), PartidaAbierta.documento_referencia.ilike(t))
    comp = partidas.composicion(db, empresa_id, corte, cuentas=[cuenta] if cuenta else None, tercero=tercero, rol=rol, moneda=moneda,
                                solo_pendientes=solo_pendientes, filtros_extra=extra)
    if clase:
        comp = [x for x in comp if x.item["clase"] == clase]
    if estado_cancelacion:
        comp = [x for x in comp if x.cancelacion == estado_cancelacion]
    if estado_vencimiento:
        comp = [x for x in comp if x.vencimiento == estado_vencimiento]
    if solo_disponibles:
        comp = [x for x in comp if x.item["importe"] - x.item["importe_comprometido"] > 0]
    if orden == "importe":
        comp.sort(key=lambda x: -x.pendiente)
    total = len(comp)
    por_pagina = max(1, min(por_pagina, 1000))
    pag = comp[(max(pagina, 1) - 1) * por_pagina: max(pagina, 1) * por_pagina]
    tot = {"importe_mn": str(sum((x.item["importe_mn"] for x in comp), Decimal("0"))),
           "pendiente_mn": str(sum((partidas.firmado(x, x.pendiente_mn) for x in comp), Decimal("0")))}
    return {"fecha_corte": corte.isoformat(), "total": total, "pagina": pagina, "por_pagina": por_pagina, "totales": tot,
            "items": [partidas.estado_dict(x) for x in pag]}


@router.get("/partidas/{item_id}")
def obtener_partida(item_id: int, db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    p = db.get(PartidaAbierta, item_id)
    if not p or p.empresa_id != empresa_id:
        raise HTTPException(404, "Partida no encontrada")
    corte = _corte(fecha_corte)
    e = next((x for x in partidas.composicion(db, empresa_id, corte, filtros_extra=PartidaAbierta.id == item_id)), None)
    apl = []
    for a in db.scalars(select(Aplicacion).where(or_(Aplicacion.origen_item_id == item_id, Aplicacion.aplicacion_item_id == item_id))
                        .order_by(Aplicacion.id)):
        otra = db.get(PartidaAbierta, a.aplicacion_item_id if a.origen_item_id == item_id else a.origen_item_id)
        apl.append({**_fila(a), "contraparte": {"id": otra.id, "documento": f"{otra.serie}-{otra.numero}" if otra.serie else otra.numero,
                                                "clase": otra.clase, "fecha": _j(otra.fecha_contable), "cuenta": otra.cuenta}})
    fuentes = [_fila(f) for f in db.scalars(select(PartidaFuente).where(PartidaFuente.item_id == item_id))]
    obs = [_fila(x) for x in db.scalars(select(ExcepcionCompensacion).where(ExcepcionCompensacion.item_id == item_id))]
    return {"partida": partidas.estado_dict(e) if e else _fila(p), "posterior_al_corte": e is None,
            "aplicaciones": apl, "fuentes": fuentes, "observaciones": obs}


# ------------------------------------------------------------------ compensación manual
class Linea(BaseModel):
    item_id: int
    importe: Decimal = Field(gt=0)


class ManualIn(BaseModel):
    izquierda: list[Linea]
    derecha: list[Linea]
    justificacion: str = Field(default="", max_length=4000)
    autorizar_terceros: bool = False
    tipo_cambio: Decimal | None = Field(default=None, gt=0)
    fecha_corte: date | None = None


def _lineas(l):
    return [x.model_dump() for x in l]


@router.post("/vista-previa")
def vista_previa(datos: ManualIn, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    try:
        v = servicio.validar_manual(db, empresa_id, usuario, _lineas(datos.izquierda), _lineas(datos.derecha),
                                    justificacion=datos.justificacion, autorizar_terceros=datos.autorizar_terceros,
                                    tipo_cambio=datos.tipo_cambio, fecha_corte=datos.fecha_corte)
    except (servicio.ErrorValidacion, servicio.SinPermiso, motor.Conflicto) as exc:
        _err(exc)
    return {k: v[k] for k in ("vista", "total", "moneda", "entre_cuentas", "entre_terceros")}


@router.post("/grupos", status_code=201)
def compensar(datos: ManualIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        g = servicio.compensar_manual(db, empresa_id, usuario, _lineas(datos.izquierda), _lineas(datos.derecha),
                                      justificacion=datos.justificacion, autorizar_terceros=datos.autorizar_terceros,
                                      tipo_cambio=datos.tipo_cambio, fecha_corte=datos.fecha_corte)
    except (servicio.ErrorValidacion, servicio.SinPermiso, motor.Conflicto) as exc:
        db.rollback()
        _err(exc)
    return _grupo_dict(db, g)


def _grupo_dict(db, g: GrupoCompensacion, detalle=False) -> dict:
    d = {**_fila(g), "componentes": json.loads(g.componentes) if g.componentes else None}
    if detalle:
        aps = db.scalars(select(Aplicacion).where(Aplicacion.grupo_id == g.id).order_by(Aplicacion.id)).all()
        ids = {a.origen_item_id for a in aps} | {a.aplicacion_item_id for a in aps}
        items = {p.id: p for p in db.scalars(select(PartidaAbierta).where(PartidaAbierta.id.in_(ids)))} if ids else {}

        def p_dict(p):
            return {"id": p.id, "cuenta": p.cuenta, "tercero": p.tercero, "razon_social": p.razon_social, "clase": p.clase,
                    "documento": f"{p.serie}-{p.numero}" if p.serie else p.numero, "fecha": _j(p.fecha_contable), "moneda": p.moneda,
                    "importe": str(p.importe), "linea_id": p.linea_id, "rol": p.rol}
        d["aplicaciones"] = [{**_fila(a), "origen": p_dict(items[a.origen_item_id]), "aplicacion": p_dict(items[a.aplicacion_item_id])} for a in aps]
        d["aprobaciones"] = [_fila(x) for x in db.scalars(select(AprobacionCompensacion).where(AprobacionCompensacion.grupo_id == g.id))]
        d["reversiones"] = [_fila(x) for x in db.scalars(select(ReversionCompensacion).where(ReversionCompensacion.grupo_id == g.id))]
        d["comentarios"] = [_fila(x) for x in db.scalars(select(ComentarioCompensacion).where(ComentarioCompensacion.grupo_id == g.id))]
        d["adjuntos"] = [_fila(x, ("ruta",)) for x in db.scalars(select(AdjuntoCompensacion).where(AdjuntoCompensacion.grupo_id == g.id))]
    return d


@router.get("/grupos")
def listar_grupos(db: DB, usuario: Usuario, empresa_id: int, estado: str | None = None, origen: str | None = None,
                  confianza: str | None = None, tercero: str | None = None, cuenta: str | None = None, pagina: int = 1, por_pagina: int = 100):
    _permiso(db, empresa_id, usuario, "consultar")
    q = select(GrupoCompensacion).where(GrupoCompensacion.empresa_id == empresa_id)
    for col, v in ((GrupoCompensacion.estado, estado), (GrupoCompensacion.origen_propuesta, origen), (GrupoCompensacion.confianza, confianza)):
        if v:
            q = q.where(col == v)
    if tercero:
        q = q.where(GrupoCompensacion.tercero.like(f"%{tercero}%"))
    if cuenta:
        q = q.where(GrupoCompensacion.cuenta.like(f"{cuenta}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    por_pagina = max(1, min(por_pagina, 500))
    items = db.scalars(q.order_by(GrupoCompensacion.id.desc()).offset((max(pagina, 1) - 1) * por_pagina).limit(por_pagina)).all()
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina, "items": [_grupo_dict(db, g) for g in items]}


@router.get("/grupos/{grupo_id}")
def obtener_grupo(grupo_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    g = db.get(GrupoCompensacion, grupo_id)
    if not g or g.empresa_id != empresa_id:
        raise HTTPException(404, "Compensación no encontrada")
    return _grupo_dict(db, g, detalle=True)


class DecisionIn(BaseModel):
    comentario: str | None = Field(default=None, max_length=4000)


def _accion(fn, db, empresa_id, grupo_id, usuario, *args):
    _empresa(db, empresa_id)
    g = db.get(GrupoCompensacion, grupo_id)
    if not g or g.empresa_id != empresa_id:
        raise HTTPException(404, "Compensación no encontrada")
    try:
        return _grupo_dict(db, fn(db, empresa_id, grupo_id, usuario, *args), detalle=True)
    except (servicio.ErrorValidacion, servicio.SinPermiso, motor.Conflicto) as exc:
        db.rollback()
        _err(exc)


@router.post("/grupos/{grupo_id}/aprobar")
def aprobar(grupo_id: int, datos: DecisionIn, db: DB, usuario: Usuario, empresa_id: int):
    return _accion(servicio.aprobar, db, empresa_id, grupo_id, usuario, datos.comentario)


@router.post("/grupos/{grupo_id}/rechazar")
def rechazar(grupo_id: int, datos: DecisionIn, db: DB, usuario: Usuario, empresa_id: int):
    return _accion(servicio.rechazar, db, empresa_id, grupo_id, usuario, datos.comentario or "")


@router.post("/grupos/{grupo_id}/revertir")
def revertir(grupo_id: int, datos: DecisionIn, db: DB, usuario: Usuario, empresa_id: int):
    return _accion(servicio.revertir, db, empresa_id, grupo_id, usuario, datos.comentario or "")


class LoteIn(BaseModel):
    grupos: list[int] = Field(min_length=1, max_length=500)
    comentario: str | None = None


@router.post("/grupos/aprobar-lote")
def aprobar_lote(datos: LoteIn, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "aprobar")
    ok, errores = [], []
    for gid in datos.grupos:
        try:
            g = db.get(GrupoCompensacion, gid)
            if not g or g.empresa_id != empresa_id:
                raise servicio.ErrorValidacion("no encontrada")
            servicio.aprobar(db, empresa_id, gid, usuario, datos.comentario)
            ok.append(gid)
        except (servicio.ErrorValidacion, servicio.SinPermiso, motor.Conflicto) as exc:
            db.rollback()
            errores.append({"grupo": gid, "error": str(exc)})
    return {"aprobadas": ok, "errores": errores}


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


@router.post("/grupos/{grupo_id}/comentarios", status_code=201)
def comentar(grupo_id: int, datos: ComentarioIn, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "revisar")
    g = db.get(GrupoCompensacion, grupo_id)
    if not g or g.empresa_id != empresa_id:
        raise HTTPException(404, "Compensación no encontrada")
    c = ComentarioCompensacion(empresa_id=empresa_id, grupo_id=g.id, usuario=usuario, texto=datos.texto)
    db.add(c)
    db.commit()
    return _fila(c)


@router.post("/grupos/{grupo_id}/adjuntos", status_code=201)
async def adjuntar(grupo_id: int, db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()]):
    _empresa(db, empresa_id)
    try:
        a = servicio.adjuntar(db, empresa_id, grupo_id, usuario, archivo.filename, archivo.content_type, await archivo.read())
    except (servicio.ErrorValidacion, servicio.SinPermiso) as exc:
        _err(exc)
    return _fila(a, ("ruta",))


@router.get("/grupos/{grupo_id}/adjuntos/{adjunto_id}")
def descargar(grupo_id: int, adjunto_id: int, db: DB, usuario: Usuario, empresa_id: int):
    _permiso(db, empresa_id, usuario, "consultar")
    a = db.get(AdjuntoCompensacion, adjunto_id)
    if not a or a.empresa_id != empresa_id or a.grupo_id != grupo_id:
        raise HTTPException(404, "Adjunto no encontrado")
    return FileResponse(servicio.ruta_adjunto(a), filename=a.nombre)


# ------------------------------------------------------------------ candidatos ambiguos y observaciones
@router.get("/candidatos")
def candidatos(db: DB, usuario: Usuario, empresa_id: int, run_id: int | None = None, decision: str | None = "REQUIERE_DECISION",
               pagina: int = 1, por_pagina: int = 100):
    _permiso(db, empresa_id, usuario, "consultar")
    q = select(CandidatoCompensacion).where(CandidatoCompensacion.empresa_id == empresa_id)
    if run_id:
        q = q.where(CandidatoCompensacion.run_id == run_id)
    if decision:
        q = q.where(CandidatoCompensacion.decision == decision)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    filas = db.scalars(q.order_by(CandidatoCompensacion.id.desc()).offset((max(pagina, 1) - 1) * por_pagina).limit(min(por_pagina, 500))).all()
    out = []
    for c in filas:
        d = {**_fila(c), "origenes": json.loads(c.origenes), "aplicaciones": json.loads(c.aplicaciones), "componentes": json.loads(c.componentes)}
        ids = {x["item_id"] for x in d["origenes"] + d["aplicaciones"]} | {i for alt in d["componentes"].get("alternativas", []) for i in alt["origenes"]}
        d["partidas"] = {p.id: {"documento": f"{p.serie}-{p.numero}" if p.serie else p.numero, "fecha": _j(p.fecha_contable), "importe": str(p.importe),
                                "clase": p.clase, "tercero": p.tercero}
                         for p in db.scalars(select(PartidaAbierta).where(PartidaAbierta.id.in_(ids)))}
        out.append(d)
    return {"total": total, "items": out}


class ResolverIn(BaseModel):
    opcion: int = Field(ge=0)
    justificacion: str = Field(default="", max_length=4000)


@router.post("/candidatos/{candidato_id}/resolver")
def resolver(candidato_id: int, datos: ResolverIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        g = servicio.resolver_candidato(db, empresa_id, candidato_id, usuario, datos.opcion, datos.justificacion)
    except (servicio.ErrorValidacion, servicio.SinPermiso, motor.Conflicto) as exc:
        db.rollback()
        _err(exc)
    return _grupo_dict(db, g, detalle=True)


@router.get("/observaciones")
def observaciones(db: DB, usuario: Usuario, empresa_id: int, estado: str | None = None, codigo: str | None = None,
                  pagina: int = 1, por_pagina: int = 200):
    _permiso(db, empresa_id, usuario, "consultar")
    q = select(ExcepcionCompensacion).where(ExcepcionCompensacion.empresa_id == empresa_id)
    if estado:
        q = q.where(ExcepcionCompensacion.estado == estado)
    if codigo:
        q = q.where(ExcepcionCompensacion.codigo == codigo)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    por_codigo = dict(db.execute(select(ExcepcionCompensacion.codigo, func.count()).where(ExcepcionCompensacion.empresa_id == empresa_id)
                                 .group_by(ExcepcionCompensacion.codigo)).all())
    filas = db.scalars(q.order_by(ExcepcionCompensacion.id.desc()).offset((max(pagina, 1) - 1) * por_pagina).limit(min(por_pagina, 500))).all()
    return {"total": total, "por_codigo": por_codigo, "items": [_fila(x) for x in filas]}


class RevisionIn(BaseModel):
    estado: str | None = Field(default=None, pattern="^(ABIERTA|EN_REVISION|RESUELTA|DESCARTADA)$")
    responsable: str | None = None
    comentario: str | None = None


@router.patch("/observaciones/{obs_id}")
def revisar_observacion(obs_id: int, datos: RevisionIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    try:
        return _fila(servicio.revisar_observacion(db, empresa_id, obs_id, usuario, datos.estado, datos.responsable, datos.comentario))
    except (servicio.ErrorValidacion, servicio.SinPermiso) as exc:
        _err(exc)


# ------------------------------------------------------------------ consultas
@router.get("/antiguedad")
def antiguedad(db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None, base: str = "VENCIMIENTO",
               agrupar: str = "tercero", cuenta: str | None = None, tercero: str | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    if agrupar not in ("tercero", "cuenta", "documento", "moneda", "proyecto", "centro_costo") or base not in ("VENCIMIENTO", "EMISION"):
        raise HTTPException(422, "Agrupación o base no válida")
    return consultas.antiguedad(db, empresa_id, _corte(fecha_corte), base=base, agrupar=agrupar,
                                cuentas=[cuenta] if cuenta else None, tercero=tercero)


@router.get("/anticipos")
def anticipos(db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    return consultas.anticipos(db, empresa_id, _corte(fecha_corte))


@router.get("/tributos")
def tributos(db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    return consultas.tributos(db, empresa_id, _corte(fecha_corte))


@router.get("/conciliacion")
def conciliacion(db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    return partidas.conciliacion(db, empresa_id, _corte(fecha_corte))


@router.get("/dashboard")
def dashboard(db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    d = consultas.dashboard(db, empresa_id, _corte(fecha_corte))
    ult = db.scalar(select(EjecucionCompensacion).where(EjecucionCompensacion.empresa_id == empresa_id)
                    .order_by(EjecucionCompensacion.id.desc()))
    d["ultima_ejecucion"] = {**_fila(ult, ("reglas_snapshot",)), "resumen": json.loads(ult.resumen) if ult.resumen else None} if ult else None
    rol, abierto = servicio.rol_de(db, empresa_id, usuario)
    d["sesion"] = {"rol": rol, "modo_abierto": abierto}
    return d


@router.get("/exportar/{reporte}.{formato}")
def exportar_reporte(reporte: str, formato: str, db: DB, usuario: Usuario, empresa_id: int, fecha_corte: date | None = None,
                     cuenta: str | None = None, tercero: str | None = None, base: str | None = None, agrupar: str | None = None):
    _permiso(db, empresa_id, usuario, "consultar")
    if reporte not in consultas.REPORTES or formato not in ("xlsx", "pdf"):
        raise HTTPException(404, "Reporte o formato no disponible")
    emp = _empresa(db, empresa_id)
    rep = consultas.reporte(db, emp, reporte, _corte(fecha_corte), {"cuenta": cuenta, "tercero": tercero, "base": base, "agrupar": agrupar})
    contenido = exportar.a_excel(rep) if formato == "xlsx" else exportar.a_pdf(rep)
    motor.auditar(db, empresa_id, usuario, "EXPORTAR", "reporte", None, {"reporte": reporte, "formato": formato})
    db.commit()
    tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if formato == "xlsx" else "application/pdf"
    return Response(contenido, media_type=tipo, headers={"Content-Disposition": f'attachment; filename="{rep.nombre}.{formato}"'})


@router.get("/auditoria")
def auditoria(db: DB, usuario: Usuario, empresa_id: int, limite: int = 300):
    _permiso(db, empresa_id, usuario, "consultar")
    return [_fila(a) for a in db.scalars(select(AuditoriaCompensacion).where(AuditoriaCompensacion.empresa_id == empresa_id)
                                         .order_by(AuditoriaCompensacion.id.desc()).limit(min(limite, 2000)))]
