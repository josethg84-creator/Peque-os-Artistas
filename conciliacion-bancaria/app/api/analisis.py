"""API del motor de análisis de cuentas (fase 3).

Seguridad multiempresa: toda consulta exige `empresa_id` y cada objeto (ejecución, hallazgo, papel,
regla, excepción, línea) se verifica contra esa empresa; un identificador de otra empresa responde 404.
El módulo es de solo lectura sobre la información contable: no modifica asientos.
"""
import json
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select

from app.analisis import antiguedad as ant_mod
from app.analisis import comparativo as comp_mod
from app.analisis import destino as dest_mod
from app.analisis import exportar, motor, navegacion, papeles, pcge, reglas, saldos
from app.api.deps import DB, Usuario
from app.contable import trabajos
from app.core.database import SessionLocal
from app.models import (AdjuntoAnalisis, AnalisisEjecucion, AnalisisResultado, AuditoriaAnalisis, ComentarioAnalisis,
                        ConfiguracionAntiguedad, Empresa, ExcepcionAnalisis, Hallazgo, LineaDiario, PapelTrabajo,
                        ReglaAnalisis, ReglaDistribucion, ResultadoDestino, RevisionAnalisis)
from app.models.analisis import ESTADOS_HALLAZGO, RIESGOS

router = APIRouter(prefix="/analisis", tags=["Análisis de cuentas"])


def _empresa(db, empresa_id: int) -> Empresa:
    emp = db.get(Empresa, empresa_id)
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")
    return emp


def _propio(obj, empresa_id: int, nombre: str):
    if obj is None or getattr(obj, "empresa_id", None) != empresa_id:
        raise HTTPException(404, f"{nombre} no encontrado")
    return obj


def _rango(desde: int, hasta: int):
    if not (1 <= desde <= hasta <= 13):
        raise HTTPException(422, "Rango de periodos inválido (01–13)")


def _filtros(cuenta=None, tercero=None, documento=None, centro_costo=None, proyecto=None, maquinaria=None, moneda=None, texto=None):
    return navegacion.Filtros(cuenta=cuenta, tercero=tercero, documento=documento, centro_costo=centro_costo,
                              proyecto=proyecto, maquinaria=maquinaria, moneda=moneda, texto=texto)


def _jsonable(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _fila(obj, excluir=()):
    return {c.key: _jsonable(getattr(obj, c.key)) for c in obj.__table__.columns if c.key not in excluir}


# ------------------------------------------------------------------ catálogo y balance
@router.get("/catalogo")
def catalogo():
    return {"perfiles": [p.__dict__ for p in pcge.PERFILES.values()], "elementos": pcge.ELEMENTOS, "niveles": pcge.NIVELES,
            "tipos_regla": reglas.catalogo(), "condiciones": sorted(reglas.CONDICIONES), "operadores": sorted(reglas.OPERADORES),
            "riesgos": list(RIESGOS), "estados_hallazgo": list(ESTADOS_HALLAZGO), "estados_papel": list(papeles.TRANSICIONES)}


@router.get("/periodos/{empresa_id}")
def periodos(empresa_id: int, db: DB):
    """Ejercicios y periodos con movimientos importados (para los selectores)."""
    _empresa(db, empresa_id)
    filas = db.execute(select(LineaDiario.ejercicio, LineaDiario.periodo, func.count())
                       .where(LineaDiario.empresa_id == empresa_id).group_by(LineaDiario.ejercicio, LineaDiario.periodo)).all()
    out = {}
    for e, p, n in filas:
        out.setdefault(e, []).append({"periodo": p, "lineas": n})
    return [{"ejercicio": e, "periodos": sorted(v, key=lambda x: x["periodo"] or 0)} for e, v in sorted(out.items(), reverse=True)]


@router.get("/balance")
def balance(db: DB, empresa_id: int, ejercicio: int, desde: int, hasta: int):
    _empresa(db, empresa_id)
    _rango(desde, hasta)
    b = saldos.balance(db, empresa_id, ejercicio, desde, hasta)
    run = papeles.ultimo_run(db, empresa_id, ejercicio, desde, hasta)
    obs = {}
    if run:
        for c, n, r in db.execute(select(Hallazgo.cuenta, func.count(), func.min(case(
                (Hallazgo.riesgo == "ALTO", 0), (Hallazgo.riesgo == "MEDIO", 1), (Hallazgo.riesgo == "BAJO", 2), else_=3)))
                .where(Hallazgo.run_id == run.id).group_by(Hallazgo.cuenta)):
            obs[c] = (n, r)
    riesgos = ["ALTO", "MEDIO", "BAJO", "INFORMATIVO"]
    nodos = []
    for n in b["nodos"]:  # observaciones agregadas a cada nivel (un hallazgo de 1212 cuenta en 1, 12, 121 y 1212)
        tot, peor = 0, 9
        for c, (k, r) in obs.items():
            if c.startswith(n["cuenta"]):
                tot += k
                peor = min(peor, r)
        nodos.append({**n, "hallazgos": tot, "riesgo": riesgos[peor] if tot else None})
    return {**b, "nodos": nodos, "run": {"id": run.id, "fecha": run.finalizado_en.isoformat() if run.finalizado_en else None,
                                         "vigente": run.version_datos == b["version_datos"]} if run else None}


@router.get("/cuenta/{codigo}")
def detalle_cuenta(codigo: str, db: DB, empresa_id: int, ejercicio: int, desde: int, hasta: int):
    """Panel lateral: saldos, perfil de análisis, evolución mensual, principales terceros y hallazgos."""
    _empresa(db, empresa_id)
    _rango(desde, hasta)
    b = saldos.balance(db, empresa_id, ejercicio, desde, hasta)
    nodo = next((n for n in b["nodos"] if n["cuenta"] == codigo), None)
    if nodo is None:
        raise HTTPException(404, "La cuenta no tiene saldo ni movimientos en el periodo")
    perfil = pcge.perfil(codigo)
    serie = comp_mod._serie_mensual(db, empresa_id, ejercicio, hasta, "CUENTA", codigo, len(codigo))
    mensual = serie.get(codigo, [])
    inicio = saldos.balance(db, empresa_id, ejercicio, 1, 1, comparar=False)
    acumulado = next((int(Decimal(n["saldo_inicial"]) * 100) for n in inicio["nodos"] if n["cuenta"] == codigo), 0)
    evolucion = []
    for i, v in enumerate(mensual):  # la serie viene en céntimos enteros
        acumulado += int(v)
        evolucion.append({"periodo": i + 1, "movimiento": str(saldos.dec(int(v))), "saldo": str(saldos.dec(acumulado))})
    ter = navegacion.terceros(db, empresa_id, ejercicio, desde, hasta, navegacion.Filtros(cuenta=codigo))["items"][:10]
    run = papeles.ultimo_run(db, empresa_id, ejercicio, desde, hasta)
    hall = [_hallazgo_dict(h) for h in db.scalars(select(Hallazgo).where(Hallazgo.run_id == run.id, Hallazgo.cuenta.like(f"{codigo}%"))
                                                 .order_by(Hallazgo.riesgo))] if run else []
    papel = db.scalar(select(PapelTrabajo).where(PapelTrabajo.empresa_id == empresa_id, PapelTrabajo.ejercicio == ejercicio,
                                                 PapelTrabajo.periodo_desde == desde, PapelTrabajo.periodo_hasta == hasta,
                                                 PapelTrabajo.cuenta == codigo))
    return {"nodo": nodo, "perfil": perfil.__dict__, "evolucion": evolucion, "terceros": ter, "hallazgos": hall,
            "papel": {"id": papel.id, "estado": papel.estado} if papel else None, "preliminar": b["preliminar"]}


# ------------------------------------------------------------------ navegación
@router.get("/terceros")
def terceros(db: DB, empresa_id: int, ejercicio: int, desde: int, hasta: int, cuenta: str | None = None,
             texto: str | None = None):
    _empresa(db, empresa_id)
    _rango(desde, hasta)
    return navegacion.terceros(db, empresa_id, ejercicio, desde, hasta, _filtros(cuenta=cuenta, texto=texto))


@router.get("/documentos")
def documentos(db: DB, empresa_id: int, ejercicio: int, desde: int, hasta: int, cuenta: str | None = None,
               tercero: str | None = None):
    _empresa(db, empresa_id)
    _rango(desde, hasta)
    return navegacion.documentos(db, empresa_id, ejercicio, desde, hasta, _filtros(cuenta=cuenta, tercero=tercero))


@router.get("/movimientos")
def movimientos(db: DB, empresa_id: int, ejercicio: int, desde: int, hasta: int, cuenta: str | None = None,
                tercero: str | None = None, documento: str | None = None, centro_costo: str | None = None,
                proyecto: str | None = None, maquinaria: str | None = None, moneda: str | None = None,
                texto: str | None = None, pagina: int = 1, por_pagina: int = 100):
    _empresa(db, empresa_id)
    _rango(desde, hasta)
    return navegacion.movimientos(db, empresa_id, ejercicio, desde, hasta,
                                  _filtros(cuenta, tercero, documento, centro_costo, proyecto, maquinaria, moneda, texto),
                                  pagina, por_pagina)


@router.get("/lineas/{linea_id}/asiento")
def asiento(linea_id: int, db: DB, empresa_id: int):
    try:
        return navegacion.asiento(db, empresa_id, linea_id)
    except navegacion.NoEncontrado as exc:
        raise HTTPException(404, str(exc))


@router.get("/lineas/{linea_id}/origen")
def origen(linea_id: int, db: DB, empresa_id: int):
    try:
        return navegacion.linea_original(db, empresa_id, linea_id)
    except navegacion.NoEncontrado as exc:
        raise HTTPException(404, str(exc))


# ------------------------------------------------------------------ antigüedad, comparativos, destino
@router.get("/antiguedad")
def antiguedad(db: DB, empresa_id: int, ejercicio: int, fecha_corte: date, base: str | None = None,
               fuente: str = "LIBROS", cuentas: str | None = None, config_id: int | None = None, tercero: str | None = None):
    _empresa(db, empresa_id)
    if base not in (None, "EMISION", "VENCIMIENTO") or fuente not in ("LIBROS", "CARTERA"):
        raise HTTPException(422, "Base o fuente no válida")
    try:
        return _jsonable(ant_mod.calcular(db, empresa_id, ejercicio, fecha_corte, base=base, fuente=fuente, cuentas=cuentas,
                                          config_id=config_id, tercero=tercero))
    except ValueError as exc:
        raise HTTPException(404, str(exc))


class AntiguedadIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    rangos: list[list[int | None]]
    base: str = Field(pattern="^(VENCIMIENTO|EMISION)$")
    cuentas: str = Field(pattern=r"^[\d,\s]+$", max_length=200)
    dias_saldo_antiguo: int = Field(ge=1, le=3650)
    predeterminada: bool = False


def _validar_rangos(rangos):
    previo = 0
    for i, r in enumerate(rangos):
        if len(r) != 2 or r[0] is None or r[0] != previo + 1 or (r[1] is not None and r[1] < r[0]) or (r[1] is None and i != len(rangos) - 1):
            raise HTTPException(422, "Los rangos deben ser consecutivos desde 1 (p. ej. 1–30, 31–60 … 366–∞).")
        previo = r[1] or 0


@router.get("/antiguedad/configuraciones")
def configuraciones_antiguedad(db: DB, empresa_id: int):
    _empresa(db, empresa_id)
    ant_mod.configuracion(db, empresa_id)
    return [{**_fila(c), "rangos": json.loads(c.rangos)} for c in
            db.scalars(select(ConfiguracionAntiguedad).where(ConfiguracionAntiguedad.empresa_id == empresa_id))]


@router.post("/antiguedad/configuraciones", status_code=201)
def crear_config_antiguedad(datos: AntiguedadIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    _validar_rangos(datos.rangos)
    if datos.predeterminada:
        for c in db.scalars(select(ConfiguracionAntiguedad).where(ConfiguracionAntiguedad.empresa_id == empresa_id)):
            c.predeterminada = False
    c = ConfiguracionAntiguedad(empresa_id=empresa_id, **{**datos.model_dump(), "rangos": json.dumps(datos.rangos)})
    db.add(c)
    db.flush()
    motor.auditar(db, empresa_id, usuario, "CREAR_CONFIG_ANTIGUEDAD", "aging", c.id, datos.model_dump())
    db.commit()
    return {**_fila(c), "rangos": datos.rangos}


@router.get("/comparativo")
def comparativo(db: DB, empresa_id: int, modo: str, ejercicio: int, periodo: int, dimension: str = "CUENTA",
                medida: str = "SALDO", nivel: int = 2, cuenta: str | None = None,
                ej_a: int | None = None, desde_a: int | None = None, hasta_a: int | None = None,
                ej_b: int | None = None, desde_b: int | None = None, hasta_b: int | None = None):
    _empresa(db, empresa_id)
    try:
        pers = ((ej_a, desde_a, hasta_a), (ej_b, desde_b, hasta_b)) if modo == "PERSONALIZADO" else None
        actual, base = comp_mod.rangos(modo, ejercicio, periodo, pers)
        return comp_mod.comparar(db, empresa_id, actual, base, dimension=dimension, medida=medida, nivel=nivel, cuenta=cuenta)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))


@router.get("/destino")
def origen_destino(db: DB, empresa_id: int, ejercicio: int, desde: int, hasta: int):
    _empresa(db, empresa_id)
    _rango(desde, hasta)
    f = saldos.fuentes(db, empresa_id, ejercicio)
    return dest_mod.serializar(dest_mod.analizar(db, empresa_id, motor.cargar_lineas(db, f.filtro_lineas(desde, hasta)), ejercicio, hasta))


class DistribucionIn(BaseModel):
    nombre: str | None = Field(default=None, max_length=160)
    cuenta_origen: str = Field(pattern=r"^\d+$", max_length=20)
    centro_costo: str | None = Field(default=None, max_length=30)
    proyecto: str | None = Field(default=None, max_length=40)
    unidad_negocio: str | None = Field(default=None, max_length=60)
    maquinaria: str | None = Field(default=None, max_length=40)
    cuenta_destino: str | None = Field(default=None, pattern=r"^\d*$", max_length=20)
    porcentaje: Decimal = Field(ge=0, le=100, default=Decimal("100"))
    excluir: bool = False
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    activa: bool = True


def _validar_distribucion(db, empresa_id, d: DistribucionIn, excluir_id=None):
    if not d.excluir and not d.cuenta_destino:
        raise HTTPException(422, "Indique la cuenta de destino o marque la regla como exclusión.")
    if d.vigente_desde and d.vigente_hasta and d.vigente_hasta < d.vigente_desde:
        raise HTTPException(422, "La vigencia final es anterior a la inicial.")
    clave = (d.cuenta_origen, d.centro_costo or None, d.proyecto or None, d.unidad_negocio or None, d.maquinaria or None)
    suma = d.porcentaje if not d.excluir else Decimal("0")
    for r in db.scalars(select(ReglaDistribucion).where(ReglaDistribucion.empresa_id == empresa_id, ReglaDistribucion.activa.is_(True))):
        if r.id == excluir_id or r.excluir:
            continue
        if (r.cuenta_origen, r.centro_costo, r.proyecto, r.unidad_negocio, r.maquinaria) == clave:
            solapa = not ((d.vigente_hasta and r.vigente_desde and d.vigente_hasta < r.vigente_desde)
                          or (r.vigente_hasta and d.vigente_desde and r.vigente_hasta < d.vigente_desde))
            if solapa:
                suma += r.porcentaje
    if suma > 100:
        raise HTTPException(422, f"La distribución para esa combinación suma {suma} % (máximo 100 %).")


@router.get("/destino/reglas")
def reglas_distribucion(db: DB, empresa_id: int):
    _empresa(db, empresa_id)
    return [_fila(r) for r in db.scalars(select(ReglaDistribucion).where(ReglaDistribucion.empresa_id == empresa_id)
                                         .order_by(ReglaDistribucion.cuenta_origen, ReglaDistribucion.centro_costo))]


@router.post("/destino/reglas", status_code=201)
def crear_distribucion(datos: DistribucionIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    _validar_distribucion(db, empresa_id, datos)
    r = ReglaDistribucion(empresa_id=empresa_id, usuario=usuario, **{k: (v or None) if isinstance(v, str) else v
                                                                     for k, v in datos.model_dump().items()})
    db.add(r)
    db.flush()
    motor.auditar(db, empresa_id, usuario, "CREAR_DISTRIBUCION", "destination_rule", r.id, datos.model_dump())
    db.commit()
    return _fila(r)


@router.put("/destino/reglas/{regla_id}")
def editar_distribucion(regla_id: int, datos: DistribucionIn, db: DB, usuario: Usuario, empresa_id: int):
    r = _propio(db.get(ReglaDistribucion, regla_id), empresa_id, "Regla de distribución")
    _validar_distribucion(db, empresa_id, datos, regla_id)
    antes = _fila(r)
    for k, v in datos.model_dump().items():
        setattr(r, k, (v or None) if isinstance(v, str) else v)
    r.usuario = usuario
    motor.auditar(db, empresa_id, usuario, "EDITAR_DISTRIBUCION", "destination_rule", r.id, {"antes": antes, "despues": datos.model_dump()})
    db.commit()
    return _fila(r)


@router.delete("/destino/reglas/{regla_id}", status_code=204)
def borrar_distribucion(regla_id: int, db: DB, usuario: Usuario, empresa_id: int):
    r = _propio(db.get(ReglaDistribucion, regla_id), empresa_id, "Regla de distribución")
    motor.auditar(db, empresa_id, usuario, "ELIMINAR_DISTRIBUCION", "destination_rule", r.id, _fila(r))
    db.delete(r)
    db.commit()


# ------------------------------------------------------------------ ejecuciones
class EjecucionIn(BaseModel):
    ejercicio: int = Field(ge=1990, le=2100)
    desde: int = Field(ge=1, le=13)
    hasta: int = Field(ge=1, le=13)
    reglas: list[str] | None = None
    grupo: str | None = None


@router.post("/ejecuciones", status_code=202)
def ejecutar(datos: EjecucionIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    _rango(datos.desde, datos.hasta)
    run = motor.crear(db, empresa_id, datos.ejercicio, datos.desde, datos.hasta, usuario, datos.reglas, datos.grupo)

    def tarea(avance):
        with SessionLocal() as s:
            return motor.ejecutar(s, run.id, avance)
    t = trabajos.crear("ANALISIS", tarea)
    return {"run_id": run.id, "trabajo": t}


def _run_dict(r: AnalisisEjecucion) -> dict:
    d = _fila(r, excluir=("reglas_snapshot", "fuentes"))
    for k in ("resumen", "advertencias", "tiempos"):
        d[k] = json.loads(getattr(r, k)) if getattr(r, k) else None
    return d


@router.get("/ejecuciones")
def listar_ejecuciones(db: DB, empresa_id: int, limite: int = 50):
    _empresa(db, empresa_id)
    return [_run_dict(r) for r in db.scalars(select(AnalisisEjecucion).where(AnalisisEjecucion.empresa_id == empresa_id)
                                              .order_by(AnalisisEjecucion.id.desc()).limit(min(limite, 200)))]


@router.get("/ejecuciones/{run_id}")
def obtener_ejecucion(run_id: int, db: DB, empresa_id: int):
    r = _propio(db.get(AnalisisEjecucion, run_id), empresa_id, "Análisis")
    d = _run_dict(r)
    d["reglas"] = json.loads(r.reglas_snapshot or "{}").get("reglas", [])
    d["fuentes"] = json.loads(r.fuentes) if r.fuentes else None
    d["vigente"] = r.version_datos == saldos.version_datos(db, empresa_id)
    return d


@router.post("/ejecuciones/{run_id}/cancelar")
def cancelar(run_id: int, db: DB, usuario: Usuario, empresa_id: int):
    r = _propio(db.get(AnalisisEjecucion, run_id), empresa_id, "Análisis")
    try:
        motor.cancelar(db, r, usuario)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    return {"ok": True}


@router.get("/ejecuciones/{run_id}/destino")
def destino_ejecucion(run_id: int, db: DB, empresa_id: int):
    _propio(db.get(AnalisisEjecucion, run_id), empresa_id, "Análisis")
    return [_fila(x) for x in db.scalars(select(ResultadoDestino).where(ResultadoDestino.run_id == run_id).order_by(ResultadoDestino.id))]


# ------------------------------------------------------------------ hallazgos
def _hallazgo_dict(h: Hallazgo) -> dict:
    d = _fila(h)
    d["evidencia"] = json.loads(h.evidencia) if h.evidencia else None
    return d


def _consulta_hallazgos(run_id, riesgo=None, estado=None, regla=None, cuenta=None, texto=None, responsable=None):
    q = select(Hallazgo).where(Hallazgo.run_id == run_id)
    if riesgo:
        q = q.where(Hallazgo.riesgo == riesgo)
    if estado:
        q = q.where(Hallazgo.estado == estado)
    if regla:
        q = q.where(Hallazgo.regla_codigo == regla)
    if cuenta:
        q = q.where(Hallazgo.cuenta.like(f"{cuenta}%"))
    if responsable:
        q = q.where(Hallazgo.responsable == responsable)
    if texto:
        p = f"%{texto}%"
        q = q.where(Hallazgo.titulo.ilike(p) | Hallazgo.tercero.ilike(p) | Hallazgo.documento.ilike(p) | Hallazgo.asiento.ilike(p))
    return q


@router.get("/hallazgos")
def listar_hallazgos(db: DB, empresa_id: int, run_id: int, riesgo: str | None = None, estado: str | None = None,
                     regla: str | None = None, cuenta: str | None = None, texto: str | None = None,
                     responsable: str | None = None, pagina: int = 1, por_pagina: int = 100):
    run = _propio(db.get(AnalisisEjecucion, run_id), empresa_id, "Análisis")
    q = _consulta_hallazgos(run.id, riesgo, estado, regla, cuenta, texto, responsable)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    orden = case((Hallazgo.riesgo == "ALTO", 0), (Hallazgo.riesgo == "MEDIO", 1), (Hallazgo.riesgo == "BAJO", 2), else_=3)
    por_pagina = max(1, min(por_pagina, 500))
    items = db.scalars(q.order_by(orden, Hallazgo.importe.desc(), Hallazgo.id).offset((max(pagina, 1) - 1) * por_pagina).limit(por_pagina)).all()
    filas = db.scalars(q).all()
    expos = motor.exposicion([{"cuenta": h.cuenta, "importe": h.importe, "clave_exposicion": h.clave_exposicion} for h in filas])
    resumen = {"por_riesgo": dict(db.execute(select(Hallazgo.riesgo, func.count()).where(Hallazgo.run_id == run.id).group_by(Hallazgo.riesgo)).all()),
               "por_estado": dict(db.execute(select(Hallazgo.estado, func.count()).where(Hallazgo.run_id == run.id).group_by(Hallazgo.estado)).all()),
               "por_regla": dict(db.execute(select(Hallazgo.regla_codigo, func.count()).where(Hallazgo.run_id == run.id).group_by(Hallazgo.regla_codigo)).all())}
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina, "importe_sujeto_revision": str(expos),
            "resumen": resumen, "items": [_hallazgo_dict(h) for h in items]}


class RevisionIn(BaseModel):
    estado: str | None = Field(default=None, pattern="^(PENDIENTE|EN_REVISION|CONFIRMADO|DESCARTADO|SUBSANADO)$")
    responsable: str | None = Field(default=None, max_length=80)
    comentario: str | None = Field(default=None, max_length=2000)


@router.get("/hallazgos/{hallazgo_id}")
def obtener_hallazgo(hallazgo_id: int, db: DB, empresa_id: int):
    h = _propio(db.get(Hallazgo, hallazgo_id), empresa_id, "Hallazgo")
    comentarios = db.scalars(select(ComentarioAnalisis).where(ComentarioAnalisis.empresa_id == empresa_id,
                                                              (ComentarioAnalisis.hallazgo_id == h.id) | (ComentarioAnalisis.huella_hallazgo == h.huella))
                             .order_by(ComentarioAnalisis.id)).all()
    revisiones = db.scalars(select(RevisionAnalisis).where(RevisionAnalisis.empresa_id == empresa_id, RevisionAnalisis.entidad == "HALLAZGO",
                                                           RevisionAnalisis.entidad_id.in_(select(Hallazgo.id).where(Hallazgo.huella == h.huella)))
                            .order_by(RevisionAnalisis.id)).all()
    return {**_hallazgo_dict(h), "comentarios": [_fila(c) for c in comentarios], "revisiones": [_fila(r) for r in revisiones]}


@router.patch("/hallazgos/{hallazgo_id}")
def revisar_hallazgo(hallazgo_id: int, datos: RevisionIn, db: DB, usuario: Usuario, empresa_id: int):
    h = _propio(db.get(Hallazgo, hallazgo_id), empresa_id, "Hallazgo")
    if datos.estado in ("DESCARTADO", "CONFIRMADO") and not (datos.comentario or "").strip():
        raise HTTPException(422, "Para confirmar o descartar una observación indique el fundamento profesional.")
    anterior = h.estado
    if datos.responsable is not None:
        h.responsable = datos.responsable.strip() or None
    if datos.estado and datos.estado != h.estado:
        h.estado = datos.estado
    db.add(RevisionAnalisis(empresa_id=empresa_id, entidad="HALLAZGO", entidad_id=h.id, estado_anterior=anterior,
                            estado_nuevo=h.estado, responsable=h.responsable, comentario=datos.comentario, usuario=usuario))
    if datos.comentario:
        db.add(ComentarioAnalisis(empresa_id=empresa_id, hallazgo_id=h.id, huella_hallazgo=h.huella, usuario=usuario, texto=datos.comentario))
    motor.auditar(db, empresa_id, usuario, "REVISAR_HALLAZGO", "finding", h.id,
                  {"de": anterior, "a": h.estado, "responsable": h.responsable, "comentario": datos.comentario})
    db.commit()
    return _hallazgo_dict(h)


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


@router.post("/hallazgos/{hallazgo_id}/comentarios", status_code=201)
def comentar_hallazgo(hallazgo_id: int, datos: ComentarioIn, db: DB, usuario: Usuario, empresa_id: int):
    h = _propio(db.get(Hallazgo, hallazgo_id), empresa_id, "Hallazgo")
    c = ComentarioAnalisis(empresa_id=empresa_id, hallazgo_id=h.id, huella_hallazgo=h.huella, usuario=usuario, texto=datos.texto)
    db.add(c)
    db.commit()
    return _fila(c)


# ------------------------------------------------------------------ reglas y excepciones
class ReglaIn(BaseModel):
    codigo: str = Field(min_length=2, max_length=12, pattern=r"^[A-Z0-9\-]+$")
    nombre: str = Field(min_length=3, max_length=160)
    descripcion: str | None = Field(default=None, max_length=2000)
    tipo: str
    grupo: str = Field(default="GENERAL", max_length=60)
    cuentas: str | None = Field(default=None, pattern=r"^[\d,\s]*$", max_length=200)
    cuenta_desde: str | None = Field(default=None, pattern=r"^\d*$", max_length=20)
    cuenta_hasta: str | None = Field(default=None, pattern=r"^\d*$", max_length=20)
    condicion: str | None = None
    operador: str | None = None
    valor: Decimal | None = None
    valor2: Decimal | None = None
    importe_minimo: Decimal = Field(default=Decimal("0"), ge=0)
    tolerancia_pct: Decimal = Field(default=Decimal("0"), ge=0, le=1000)
    parametros: dict | None = None
    riesgo: str = Field(pattern="^(ALTO|MEDIO|BAJO|INFORMATIVO)$")
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    activa: bool = True


def _validar_regla(d: ReglaIn):
    if d.tipo not in reglas.TIPOS:
        raise HTTPException(422, "Tipo de regla no válido")
    if d.tipo == "UMBRAL":
        if d.condicion not in reglas.CONDICIONES or d.operador not in reglas.OPERADORES or d.valor is None:
            raise HTTPException(422, "La regla de umbral requiere condición, operador y valor válidos.")
        if d.operador in ("ENTRE", "FUERA") and d.valor2 is None:
            raise HTTPException(422, "Los operadores ENTRE y FUERA requieren un segundo valor.")
    if d.vigente_desde and d.vigente_hasta and d.vigente_hasta < d.vigente_desde:
        raise HTTPException(422, "La vigencia final es anterior a la inicial.")


def _regla_dict(r: ReglaAnalisis) -> dict:
    d = _fila(r, excluir=("historial",))
    d["parametros"] = json.loads(r.parametros) if r.parametros else None
    d["versiones_anteriores"] = len(json.loads(r.historial)) if r.historial else 0
    return d


@router.get("/reglas")
def listar_reglas(db: DB, empresa_id: int):
    _empresa(db, empresa_id)
    reglas.sembrar(db, empresa_id)
    return [_regla_dict(r) for r in db.scalars(select(ReglaAnalisis).where(ReglaAnalisis.empresa_id == empresa_id)
                                                .order_by(ReglaAnalisis.grupo, ReglaAnalisis.codigo))]


@router.post("/reglas", status_code=201)
def crear_regla(datos: ReglaIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    _validar_regla(datos)
    if db.scalar(select(ReglaAnalisis).where(ReglaAnalisis.empresa_id == empresa_id, ReglaAnalisis.codigo == datos.codigo)):
        raise HTTPException(409, "Ya existe una regla con ese código")
    valores = datos.model_dump()
    valores["parametros"] = json.dumps(valores["parametros"], ensure_ascii=False) if valores["parametros"] else None
    r = ReglaAnalisis(empresa_id=empresa_id, usuario=usuario, version=1, **valores)
    db.add(r)
    db.flush()
    motor.auditar(db, empresa_id, usuario, "CREAR_REGLA", "rule", r.id, reglas.snapshot(r))
    db.commit()
    return _regla_dict(r)


@router.get("/reglas/{regla_id}")
def obtener_regla(regla_id: int, db: DB, empresa_id: int):
    r = _propio(db.get(ReglaAnalisis, regla_id), empresa_id, "Regla")
    return {**_regla_dict(r), "historial": json.loads(r.historial) if r.historial else []}


@router.put("/reglas/{regla_id}")
def editar_regla(regla_id: int, datos: ReglaIn, db: DB, usuario: Usuario, empresa_id: int):
    """Cada modificación genera una nueva versión; la anterior queda en el historial."""
    r = _propio(db.get(ReglaAnalisis, regla_id), empresa_id, "Regla")
    _validar_regla(datos)
    if datos.codigo != r.codigo:
        raise HTTPException(422, "El código de una regla no se puede cambiar")
    historial = json.loads(r.historial) if r.historial else []
    historial.append(reglas.snapshot(r))
    valores = datos.model_dump()
    valores["parametros"] = json.dumps(valores["parametros"], ensure_ascii=False) if valores["parametros"] else None
    for k, v in valores.items():
        setattr(r, k, v)
    r.version += 1
    r.historial = json.dumps(historial, ensure_ascii=False)
    r.usuario = usuario
    motor.auditar(db, empresa_id, usuario, "EDITAR_REGLA", "rule", r.id, {"version": r.version})
    db.commit()
    return _regla_dict(r)


class ExcepcionIn(BaseModel):
    regla_id: int | None = None
    cuenta: str | None = Field(default=None, pattern=r"^[\d/]*$", max_length=20)
    tercero: str | None = Field(default=None, max_length=20)
    documento: str | None = Field(default=None, max_length=80)
    motivo: str = Field(min_length=10, max_length=255)
    vigente_hasta: date | None = None


@router.get("/excepciones")
def listar_excepciones(db: DB, empresa_id: int):
    _empresa(db, empresa_id)
    return [_fila(x) for x in db.scalars(select(ExcepcionAnalisis).where(ExcepcionAnalisis.empresa_id == empresa_id)
                                         .order_by(ExcepcionAnalisis.id.desc()))]


@router.post("/excepciones", status_code=201)
def crear_excepcion(datos: ExcepcionIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    if datos.regla_id:
        _propio(db.get(ReglaAnalisis, datos.regla_id), empresa_id, "Regla")
    if not (datos.cuenta or datos.tercero or datos.documento):
        raise HTTPException(422, "Una excepción debe acotarse a una cuenta, tercero o documento.")
    x = ExcepcionAnalisis(empresa_id=empresa_id, autorizado_por=usuario, **{k: (v or None) if isinstance(v, str) else v
                                                                            for k, v in datos.model_dump().items()})
    db.add(x)
    db.flush()
    motor.auditar(db, empresa_id, usuario, "AUTORIZAR_EXCEPCION", "exception", x.id, datos.model_dump())
    db.commit()
    return _fila(x)


@router.delete("/excepciones/{excepcion_id}", status_code=204)
def revocar_excepcion(excepcion_id: int, db: DB, usuario: Usuario, empresa_id: int):
    x = _propio(db.get(ExcepcionAnalisis, excepcion_id), empresa_id, "Excepción")
    x.activa = False
    motor.auditar(db, empresa_id, usuario, "REVOCAR_EXCEPCION", "exception", x.id)
    db.commit()


# ------------------------------------------------------------------ dashboard
@router.get("/dashboard")
def dashboard(db: DB, empresa_id: int, ejercicio: int, desde: int, hasta: int):
    _empresa(db, empresa_id)
    _rango(desde, hasta)
    b = saldos.balance(db, empresa_id, ejercicio, desde, hasta)
    run = papeles.ultimo_run(db, empresa_id, ejercicio, desde, hasta)
    f = saldos.fuentes(db, empresa_id, ejercicio)
    # evolución mensual de saldos por elemento (1–5): apertura + movimientos acumulados
    base = {}
    if f.apertura == "SALDOS_INICIALES":
        from app.models import SaldoCuenta
        for e, v in db.execute(select(func.substr(SaldoCuenta.cuenta, 1, 1), saldos.cent(SaldoCuenta.saldo_inicial_debe) - saldos.cent(SaldoCuenta.saldo_inicial_haber))
                               .where(SaldoCuenta.lote_id.in_(f.lotes_apertura)).group_by(func.substr(SaldoCuenta.cuenta, 1, 1))):
            base[e] = int(v)
    mov = {}
    for e, p, v in db.execute(select(func.substr(LineaDiario.cuenta, 1, 1), LineaDiario.periodo,
                                     saldos.cent(LineaDiario.debe_mn) - saldos.cent(LineaDiario.haber_mn))
                              .where(f.filtro_lineas(0 if f.apertura == "DIARIO_00" else 1, min(hasta, 12), f.apertura == "DIARIO_00"))
                              .group_by(func.substr(LineaDiario.cuenta, 1, 1), LineaDiario.periodo)):
        mov[(e, p)] = int(v)
    evolucion = []
    for e in "12345":
        acum = base.get(e, 0) + mov.get((e, 0), 0)
        puntos = []
        for p in range(1, min(hasta, 12) + 1):
            acum += mov.get((e, p), 0)
            puntos.append(str(saldos.dec(acum)))
        evolucion.append({"elemento": e, "nombre": pcge.ELEMENTOS[e], "saldos": puntos})
    gastos = [{"cuenta": n["cuenta"], "descripcion": n["descripcion"], "importe": n["neto"]}
              for n in b["nodos"] if n["nivel"] == 2 and n["cuenta"][0] == "6"]
    cc = comp_mod._movimiento_por(db, empresa_id, comp_mod.Rango(ejercicio, desde, hasta), "CENTRO_COSTO", "6")
    gastos_cc = sorted(({"centro_costo": k, "importe": str(saldos.dec(v["valor"]))} for k, v in cc.items()),
                       key=lambda x: -abs(Decimal(x["importe"])))
    aging = ant_mod.calcular(db, empresa_id, ejercicio, motor._fin_periodo(ejercicio, hasta))
    conc = [{"tercero": t["tercero"], "razon_social": t["razon_social"], "importe": t["total"]} for t in aging["terceros"][:10]]
    kpi = {"cuentas_analizadas": sum(1 for n in b["nodos"] if (not n["tiene_hijos"] or n["movimiento_propio"]) and n["cuenta"][0] != "0"),
           "movimientos": b["totales"]["movimientos"]}
    hallazgos_riesgo, avance, od = {}, None, []
    if run:
        res = json.loads(run.resumen or "{}")
        kpi.update({k: res.get(k) for k in ("cuentas_con_observaciones", "cuentas_sin_observaciones", "importe_sujeto_revision",
                                            "saldos_contrarios", "diferencias_origen_destino", "variaciones_significativas", "hallazgos")})
        hallazgos_riesgo = dict(db.execute(select(Hallazgo.riesgo, func.count()).where(Hallazgo.run_id == run.id).group_by(Hallazgo.riesgo)).all())
        estados = dict(db.execute(select(Hallazgo.estado, func.count()).where(Hallazgo.run_id == run.id).group_by(Hallazgo.estado)).all())
        total = sum(estados.values())
        revisados = total - estados.get("PENDIENTE", 0)
        avance = {"total": total, "revisados": revisados, "pct": round(revisados / total * 100, 1) if total else 100.0, "por_estado": estados}
        od = [{"periodo": x.periodo, "origen": str(x.origen), "destino": str(x.destino), "cargas": str(x.cargas_imputables or 0),
               "estado": x.estado} for x in db.scalars(select(ResultadoDestino).where(ResultadoDestino.run_id == run.id,
                                                                                    ResultadoDestino.tipo == "RESUMEN").order_by(ResultadoDestino.periodo))]
    kpi["saldos_antiguos"] = aging["saldo_antiguo"]
    papeles_estado = dict(db.execute(select(PapelTrabajo.estado, func.count()).where(
        PapelTrabajo.empresa_id == empresa_id, PapelTrabajo.ejercicio == ejercicio).group_by(PapelTrabajo.estado)).all())
    return {"kpi": kpi, "run": _run_dict(run) if run else None, "run_vigente": bool(run and run.version_datos == b["version_datos"]),
            "advertencias": b["advertencias"], "preliminar": b["preliminar"], "control": b["control"],
            "graficos": {"evolucion": evolucion, "distribucion_gastos": gastos, "antiguedad": {"tramos": aging["tramos"], "totales": aging["totales"]},
                         "concentracion_terceros": conc, "observaciones_riesgo": hallazgos_riesgo, "origen_destino": od,
                         "gastos_centro_costo": gastos_cc[:12]},
            "avance_revision": avance, "papeles": papeles_estado}


# ------------------------------------------------------------------ papeles de trabajo
class PapelIn(BaseModel):
    ejercicio: int
    desde: int
    hasta: int
    cuenta: str = Field(pattern=r"^\d+$", max_length=20)


class PapelEdicion(BaseModel):
    comentarios_analista: str | None = Field(default=None, max_length=20000)
    documentos_sustento: str | None = Field(default=None, max_length=5000)
    conclusion: str | None = Field(default=None, max_length=20000)
    responsable: str | None = Field(default=None, max_length=80)
    fecha_revision: date | None = None


class EstadoIn(BaseModel):
    estado: str = Field(pattern="^(PENDIENTE|EN_REVISION|OBSERVADO|SUBSANADO|REVISADO|APROBADO)$")
    comentario: str | None = Field(default=None, max_length=2000)


def _papel(db, papel_id, empresa_id) -> PapelTrabajo:
    return _propio(db.get(PapelTrabajo, papel_id), empresa_id, "Papel de trabajo")


def _papel_completo(db, p):
    adj = db.scalars(select(AdjuntoAnalisis).where(AdjuntoAnalisis.papel_id == p.id).order_by(AdjuntoAnalisis.id)).all()
    rev = db.scalars(select(RevisionAnalisis).where(RevisionAnalisis.entidad == "PAPEL", RevisionAnalisis.entidad_id == p.id)
                     .order_by(RevisionAnalisis.id)).all()
    return papeles.papel_dict(p, adj, rev)


@router.get("/papeles")
def listar_papeles(db: DB, empresa_id: int, ejercicio: int | None = None, estado: str | None = None):
    _empresa(db, empresa_id)
    q = select(PapelTrabajo).where(PapelTrabajo.empresa_id == empresa_id)
    if ejercicio:
        q = q.where(PapelTrabajo.ejercicio == ejercicio)
    if estado:
        q = q.where(PapelTrabajo.estado == estado)
    return [papeles.papel_dict(p) for p in db.scalars(q.order_by(PapelTrabajo.cuenta))]


def _error_papel(exc):
    raise HTTPException(exc.status, str(exc))


@router.post("/papeles", status_code=201)
def generar_papel(datos: PapelIn, db: DB, usuario: Usuario, empresa_id: int):
    _empresa(db, empresa_id)
    _rango(datos.desde, datos.hasta)
    try:
        return _papel_completo(db, papeles.generar(db, empresa_id, datos.ejercicio, datos.desde, datos.hasta, datos.cuenta, usuario))
    except papeles.ErrorPapel as exc:
        _error_papel(exc)


@router.get("/papeles/{papel_id}")
def obtener_papel(papel_id: int, db: DB, empresa_id: int):
    return _papel_completo(db, _papel(db, papel_id, empresa_id))


@router.put("/papeles/{papel_id}")
def editar_papel(papel_id: int, datos: PapelEdicion, db: DB, usuario: Usuario, empresa_id: int):
    try:
        return _papel_completo(db, papeles.actualizar(db, _papel(db, papel_id, empresa_id), datos.model_dump(exclude_unset=True), usuario))
    except papeles.ErrorPapel as exc:
        _error_papel(exc)


@router.post("/papeles/{papel_id}/estado")
def estado_papel(papel_id: int, datos: EstadoIn, db: DB, usuario: Usuario, empresa_id: int):
    try:
        return _papel_completo(db, papeles.cambiar_estado(db, _papel(db, papel_id, empresa_id), datos.estado, usuario, datos.comentario))
    except papeles.ErrorPapel as exc:
        _error_papel(exc)


@router.post("/papeles/{papel_id}/adjuntos", status_code=201)
async def adjuntar(papel_id: int, db: DB, usuario: Usuario, empresa_id: int, archivo: Annotated[UploadFile, File()]):
    p = _papel(db, papel_id, empresa_id)
    try:
        a = papeles.guardar_adjunto(db, p, archivo.filename, archivo.content_type, await archivo.read(), usuario)
    except papeles.ErrorPapel as exc:
        _error_papel(exc)
    return {"id": a.id, "nombre": a.nombre, "tamano": a.tamano, "hash": a.hash}


@router.get("/papeles/{papel_id}/adjuntos/{adjunto_id}")
def descargar_adjunto(papel_id: int, adjunto_id: int, db: DB, empresa_id: int):
    _papel(db, papel_id, empresa_id)
    a = db.get(AdjuntoAnalisis, adjunto_id)
    if not a or a.papel_id != papel_id or a.empresa_id != empresa_id:
        raise HTTPException(404, "Adjunto no encontrado")
    return FileResponse(papeles.ruta_adjunto(a), filename=a.nombre, media_type=a.tipo_contenido or "application/octet-stream")


# ------------------------------------------------------------------ exportaciones
REPORTES = {"balance", "cuenta", "movimientos", "antiguedad", "comparativo", "gastos", "ingresos", "destino", "observaciones", "papel"}


@router.get("/exportar/{reporte}.{formato}")
def exportar_reporte(reporte: str, formato: str, db: DB, usuario: Usuario, empresa_id: int,
                     ejercicio: int | None = None, desde: int = 1, hasta: int = 12, cuenta: str | None = None,
                     tercero: str | None = None, documento: str | None = None, centro_costo: str | None = None,
                     proyecto: str | None = None, texto: str | None = None, fecha_corte: date | None = None,
                     base: str | None = None, fuente: str = "LIBROS", modo: str = "MES_ANTERIOR", dimension: str = "CUENTA",
                     medida: str = "SALDO", nivel: int = 2, run_id: int | None = None, papel_id: int | None = None,
                     riesgo: str | None = None, estado: str | None = None):
    if reporte not in REPORTES or formato not in ("xlsx", "pdf"):
        raise HTTPException(404, "Reporte o formato no disponible")
    emp = _empresa(db, empresa_id)
    if reporte not in ("papel", "observaciones", "antiguedad") and not ejercicio:
        raise HTTPException(422, "Indique el ejercicio")
    if ejercicio:
        _rango(desde, hasta)
    try:
        if reporte == "balance":
            rep = exportar.balance(db, emp, ejercicio, desde, hasta, usuario)
        elif reporte == "cuenta":
            if not cuenta:
                raise HTTPException(422, "Indique la cuenta")
            rep = exportar.cuenta(db, emp, ejercicio, desde, hasta, usuario, cuenta)
        elif reporte == "movimientos":
            rep = exportar.movimientos(db, emp, ejercicio, desde, hasta, usuario,
                                       _filtros(cuenta, tercero, documento, centro_costo, proyecto, texto=texto))
        elif reporte == "antiguedad":
            if not (ejercicio and fecha_corte):
                raise HTTPException(422, "Indique ejercicio y fecha de corte")
            rep = exportar.antiguedad(db, emp, ejercicio, fecha_corte, usuario, base=base, fuente=fuente, cuentas=cuenta)
        elif reporte == "comparativo":
            actual, base_r = comp_mod.rangos(modo, ejercicio, hasta)
            rep = exportar.comparativo(db, emp, usuario, actual, base_r, dimension=dimension, medida=medida, nivel=nivel, cuenta=cuenta)
        elif reporte in ("gastos", "ingresos"):
            rep = exportar.por_elemento(db, emp, ejercicio, desde, hasta, usuario, "6" if reporte == "gastos" else "7")
        elif reporte == "destino":
            rep = exportar.destino(db, emp, ejercicio, desde, hasta, usuario)
        elif reporte == "observaciones":
            run = _propio(db.get(AnalisisEjecucion, run_id), empresa_id, "Análisis") if run_id else None
            if not run:
                raise HTTPException(422, "Indique el análisis (run_id)")
            filas = [{**_hallazgo_dict(h), "evidencia_txt": h.evidencia} for h in db.scalars(
                _consulta_hallazgos(run.id, riesgo, estado).order_by(Hallazgo.riesgo, Hallazgo.cuenta))]
            rep = exportar.hallazgos(emp, run, filas, usuario)
        else:
            if not papel_id:
                raise HTTPException(422, "Indique el papel de trabajo")
            rep = exportar.papel(emp, _papel_completo(db, _papel(db, papel_id, empresa_id)), usuario)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    contenido = exportar.a_excel(rep) if formato == "xlsx" else exportar.a_pdf(rep)
    motor.auditar(db, empresa_id, usuario, "EXPORTAR", "reporte", None, {"reporte": reporte, "formato": formato})
    db.commit()
    tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if formato == "xlsx" else "application/pdf"
    return Response(contenido, media_type=tipo, headers={"Content-Disposition": f'attachment; filename="{rep.nombre}.{formato}"'})


# ------------------------------------------------------------------ auditoría del módulo
@router.get("/auditoria")
def auditoria_analisis(db: DB, empresa_id: int, limite: int = 300):
    _empresa(db, empresa_id)
    return [_fila(a) for a in db.scalars(select(AuditoriaAnalisis).where(AuditoriaAnalisis.empresa_id == empresa_id)
                                         .order_by(AuditoriaAnalisis.id.desc()).limit(min(limite, 2000)))]


@router.get("/resultados")
def resultados(db: DB, empresa_id: int, run_id: int):
    _propio(db.get(AnalisisEjecucion, run_id), empresa_id, "Análisis")
    return [_fila(r) for r in db.scalars(select(AnalisisResultado).where(AnalisisResultado.run_id == run_id)
                                         .order_by(AnalisisResultado.cuenta))]
