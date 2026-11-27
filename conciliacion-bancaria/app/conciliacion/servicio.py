"""Ciclo de vida de una conciliación: creación, fuentes, ejecución, versiones, conciliación manual, reversiones,
flujo de revisión y aprobación, incidencias y continuidad mensual. Todo es analítico: no se modifican asientos."""
import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, insert, select, update

from app.anexos import datos as datos5
from app.compensacion.servicio import rol_de
from app.conciliacion import catalogo, clasificar, fuentes
from app.conciliacion.motor import CERO, Comparador, Tolerancia
from app.core import config
from app.importers.lectores import ErrorImportacion
from app.models import (AdjuntoConciliacion, AprobacionConciliacion, AsignacionConciliacion, AsignacionRegistro, AuditoriaConciliacion,
                        Conciliacion, DiferenciaConciliacion, Empresa, FuenteConciliacion, GrupoConciliacion, MapeoColumnas,
                        MatchConciliacion, PlantillaConciliacion, RegistroFuente, ReversionConciliacion, RevisionConciliacion,
                        TipoConciliacion, ToleranciaConciliacion, VersionConciliacion)

TODOS = {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA", "AUDITOR", "CONSULTA", "TESORERO", "PLANILLAS", "AUDITOR_EXTERNO", "GERENCIA"}
BASE_OPERAR = {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "ANALISTA"}
PERMISOS = {"consultar": TODOS, "exportar": TODOS, "operar": BASE_OPERAR, "incidencias": BASE_OPERAR,
            "revisar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR", "AUDITOR"}, "aprobar": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR"},
            "revertir": {"ADMINISTRADOR", "SUPERVISOR"}, "plantillas": {"ADMINISTRADOR", "SUPERVISOR", "CONTADOR"},
            "configurar": {"ADMINISTRADOR", "SUPERVISOR"}, "datos_personales": {"ADMINISTRADOR", "SUPERVISOR", "PLANILLAS"}}
EDITABLES = ("EJECUTADA", "OBSERVADA", "REABIERTA", "BORRADOR")
FINALES_DIF = ("SUBSANADO", "APROBADO", "CERRADO")
GRAVEDAD = ("EXCLUIDO", "CONCILIADO", "PROPUESTO", "PARCIAL", "PENDIENTE", "AMBIGUO", "DUPLICADO")
TRANSICIONES = {"EN_REVISION": ("operar", {"EJECUTADA", "OBSERVADA"}), "OBSERVADA": ("revisar", {"EN_REVISION", "REVISADA"}),
                "REVISADA": ("revisar", {"EN_REVISION"}), "APROBADA": ("aprobar", {"REVISADA"}), "CERRADA": ("revertir", {"APROBADA"})}
TRANS_DIF = {"PENDIENTE_REVISION": ("incidencias", None), "EN_ANALISIS": ("incidencias", None), "JUSTIFICADO": ("incidencias", None),
             "PENDIENTE_REGULARIZACION": ("incidencias", None), "SUBSANADO": ("incidencias", None),
             "APROBADO": ("revisar", {"JUSTIFICADO", "SUBSANADO", "PENDIENTE_REGULARIZACION"}),
             "CERRADO": ("aprobar", {"APROBADO", "SUBSANADO", "JUSTIFICADO"}), "REABIERTO": ("revisar", {"SUBSANADO", "APROBADO", "CERRADO", "JUSTIFICADO"})}


class SinPermiso(Exception):
    status = 403


class ErrorConciliacion(Exception):
    status = 422


class Conflicto(Exception):
    status = 409


def _j(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, set):
        return sorted(v)
    return v


def auditar(db, empresa_id, usuario, accion, entidad, entidad_id=None, detalle=None, rol=None, run=None):
    db.add(AuditoriaConciliacion(empresa_id=empresa_id, usuario=usuario or "sistema", rol=rol, accion=accion, entidad=entidad, entidad_id=entidad_id,
                                 run_id=run.id if run else None, version=run.version_actual if run else None,
                                 detalle=None if detalle is None else json.dumps(detalle, default=_j, ensure_ascii=False)))


# ------------------------------------------------------------------ permisos
def rol(db, empresa_id, usuario):
    return rol_de(db, empresa_id, usuario)


def puede(db, empresa_id, usuario, accion, tipo: str | None = None) -> bool:
    r, _ = rol(db, empresa_id, usuario)
    if r in PERMISOS[accion]:
        return True
    if tipo and accion in ("operar", "incidencias"):
        t = db.scalar(select(TipoConciliacion).where(TipoConciliacion.codigo == tipo))
        if t is None:
            catalogo.sembrar(db)
            t = db.scalar(select(TipoConciliacion).where(TipoConciliacion.codigo == tipo))
        return bool(t and r and r in (t.roles_operacion or "").split(","))
    return False


def exigir(db, empresa_id, usuario, accion, tipo=None) -> str:
    if not puede(db, empresa_id, usuario, accion, tipo):
        r, _ = rol(db, empresa_id, usuario)
        raise SinPermiso(f"El usuario «{usuario}» ({r or 'sin rol en la empresa'}) no puede {accion} conciliaciones"
                         + (f" de tipo {tipo}" if tipo else "") + ".")
    return rol(db, empresa_id, usuario)[0]


def ve_datos_personales(db, empresa_id, usuario) -> bool:
    return puede(db, empresa_id, usuario, "datos_personales")


def cargar(db, empresa_id, run_id) -> Conciliacion:
    c = db.get(Conciliacion, run_id)
    if not c or c.empresa_id != empresa_id:
        raise LookupError("Conciliación no encontrada")
    return c


def _lock(db, c: Conciliacion, lock_version):
    if lock_version is None:
        return
    r = db.execute(update(Conciliacion).where(Conciliacion.id == c.id, Conciliacion.lock_version == lock_version)
                   .values(lock_version=lock_version + 1))
    if r.rowcount != 1:
        db.rollback()
        raise Conflicto("La conciliación fue modificada por otro usuario: actualice la pantalla.")
    db.refresh(c)


# ------------------------------------------------------------------ tolerancias y plantillas
def tolerancia(db, empresa_id, tipo, ambito: dict, cfg: dict) -> Tolerancia:
    t = cfg.get("tolerancia") or {}
    base = Tolerancia(Decimal(str(t.get("importe_absoluto") or "0")), Decimal(str(t["porcentaje"])) if t.get("porcentaje") not in (None, "") else None,
                      int(t.get("dias") or 0))
    mejor, puntos = None, -1
    cuenta, moneda = ambito.get("cuenta") or "", ambito.get("moneda")
    for x in db.scalars(select(ToleranciaConciliacion).where(ToleranciaConciliacion.empresa_id == empresa_id, ToleranciaConciliacion.activa.is_(True))):
        if (x.tipo_codigo and x.tipo_codigo != tipo) or (x.cuenta and not cuenta.startswith(x.cuenta)) or (x.moneda and x.moneda != moneda):
            continue
        p = (1 if x.tipo_codigo else 0) + (len(x.cuenta) if x.cuenta else 0) + (1 if x.moneda else 0)
        if p > puntos:
            mejor, puntos = x, p
    if mejor:
        return Tolerancia(Decimal(mejor.importe_absoluto), Decimal(mejor.porcentaje) if mejor.porcentaje is not None else None, mejor.dias)
    return base


def plantilla_para(db, empresa_id, tipo, plantilla_id=None) -> PlantillaConciliacion:
    catalogo.sembrar(db)
    if plantilla_id:
        p = db.get(PlantillaConciliacion, plantilla_id)
        if not p or p.empresa_id not in (None, empresa_id) or not p.activa:
            raise LookupError("Plantilla no encontrada")
        if p.empresa_id and not p.autorizada:
            raise ErrorConciliacion("La plantilla personalizada no está autorizada.")
        return p
    p = db.scalar(select(PlantillaConciliacion).where(PlantillaConciliacion.empresa_id == empresa_id, PlantillaConciliacion.tipo_codigo == tipo,
                                                       PlantillaConciliacion.activa.is_(True), PlantillaConciliacion.autorizada.is_(True),
                                                       PlantillaConciliacion.personalizada.is_(False)).order_by(PlantillaConciliacion.id.desc())) \
        or db.scalar(select(PlantillaConciliacion).where(PlantillaConciliacion.empresa_id.is_(None), PlantillaConciliacion.codigo == tipo))
    if not p:
        raise LookupError("Tipo de conciliación no disponible")
    return p


def ambito_clave(empresa_id, plantilla_id, tipo, ambito: dict) -> str:
    base = {k: ambito.get(k) for k in ("cuenta", "cuenta_bancaria_id", "moneda", "centro_costo", "proyecto", "empresa_relacionada_id")}
    return hashlib.sha256(json.dumps([empresa_id, tipo, plantilla_id, base], sort_keys=True).encode()).hexdigest()[:40]


# ------------------------------------------------------------------ creación
def crear(db, empresa_id, usuario, datos: dict) -> Conciliacion:
    tipo = datos["tipo"]
    r = exigir(db, empresa_id, usuario, "operar", tipo)
    p = plantilla_para(db, empresa_id, tipo, datos.get("plantilla_id"))
    tipo = p.tipo_codigo
    corte = datos.get("fecha_corte") or datos5.fin_de_periodo(datos["ejercicio"], datos["periodo"])
    ejercicio = datos.get("ejercicio") or corte.year
    periodo = datos.get("periodo") or corte.month
    ambito = {k: v for k, v in (datos.get("ambito") or {}).items() if v not in (None, "")}
    if tipo == "BANCARIA" and not ambito.get("cuenta_bancaria_id"):
        raise ErrorConciliacion("Seleccione la cuenta bancaria.")
    if tipo == "INTERCOMPANIA":
        verificar_grupo(db, empresa_id, ambito.get("empresa_relacionada_id"), usuario)
    clave = ambito_clave(empresa_id, p.id, tipo, ambito)
    existente = db.scalar(select(Conciliacion).where(Conciliacion.empresa_id == empresa_id, Conciliacion.ambito_clave == clave,
                                                     Conciliacion.fecha_corte == corte))
    if existente:
        return existente
    nombre = datos.get("nombre") or f"{p.nombre} al {corte:%d/%m/%Y}"
    c = Conciliacion(empresa_id=empresa_id, plantilla_id=p.id, tipo_codigo=tipo, nombre=nombre[:200], ejercicio=ejercicio, periodo=periodo,
                     fecha_corte=corte, ambito=json.dumps(ambito), ambito_clave=clave, responsable=datos.get("responsable"),
                     fecha_limite=datos.get("fecha_limite"), creado_por=usuario)
    db.add(c)
    db.flush()
    auditar(db, empresa_id, usuario, "CREAR", "conciliacion", c.id, {"tipo": tipo, "corte": corte, "ambito": ambito}, r, c)
    db.commit()
    return c


def verificar_grupo(db, empresa_id, relacionada_id, usuario):
    if not relacionada_id or relacionada_id == empresa_id or not db.get(Empresa, relacionada_id):
        raise ErrorConciliacion("Seleccione una empresa relacionada válida.")
    for a, b in ((empresa_id, relacionada_id), (relacionada_id, empresa_id)):
        ok = db.scalar(select(AsignacionConciliacion).where(AsignacionConciliacion.empresa_id == a, AsignacionConciliacion.tipo == "GRUPO_ECONOMICO",
                                                             AsignacionConciliacion.empresa_relacionada_id == b, AsignacionConciliacion.activa.is_(True)))
        if not ok:
            raise SinPermiso("Ambas empresas deben autorizar su pertenencia al mismo grupo económico para conciliar operaciones recíprocas.")
    if not puede(db, relacionada_id, usuario, "consultar"):
        raise SinPermiso("Su usuario no tiene acceso a la empresa relacionada.")


# ------------------------------------------------------------------ fuentes
def _dir(empresa_id) -> Path:
    d = Path(config.DATA_DIR) / "conciliaciones" / str(empresa_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _hash_registros(regs: list[dict]) -> str:
    return hashlib.sha256(json.dumps([[r["clave_registro"], str(r["importe"]), r.get("fecha"), r.get("concepto"), r["datos"]] for r in regs],
                                     default=_j, sort_keys=True).encode()).hexdigest()


def _guardar_fuente(db, c: Conciliacion, lado, spec, regs, meta, usuario, *, archivo=None) -> FuenteConciliacion:
    for f in db.scalars(select(FuenteConciliacion).where(FuenteConciliacion.run_id == c.id, FuenteConciliacion.lado == lado,
                                                         FuenteConciliacion.vigente.is_(True))):
        f.vigente = False  # se conserva para las versiones anteriores
    f = FuenteConciliacion(run_id=c.id, empresa_id=c.empresa_id, lado=lado, rol=spec.get("rol", "EXTERNA"), tipo_fuente=spec["tipo"],
                           nombre=spec.get("nombre") or spec["tipo"], parametros=json.dumps(spec.get("parametros", {})), esquema=spec.get("esquema"),
                           registros=len(regs), total=sum((r["importe"] for r in regs), CERO), saldo=meta.get("saldo"),
                           observaciones=meta.get("observaciones"), version_datos=_hash_registros(regs), creado_por=usuario, **(archivo or {}))
    db.add(f)
    db.flush()
    filas = []
    for i, r in enumerate(regs):
        x = {k: r.get(k) for k in fuentes.CAMPOS_FIJOS}
        x.update(fuente_id=f.id, run_id=c.id, lado=lado, orden=i, clave_registro=str(r["clave_registro"])[:160],
                 datos=json.dumps(r["datos"], default=_j, ensure_ascii=False) if r["datos"] else None,
                 excluido=bool(r.get("excluido")), motivo_exclusion=r.get("motivo_exclusion"))
        for k, n in (("descripcion", 255), ("razon_social", 255), ("referencia", 120), ("operacion", 60), ("concepto", 60), ("numero", 40),
                     ("serie", 20), ("tercero", 20), ("cuenta", 20), ("centro_costo", 30), ("proyecto", 40), ("tipo_documento", 4)):
            x[k] = (str(x[k])[:n] if x[k] not in (None, "") else None)
        filas.append(x)
    for i in range(0, len(filas), 5000):
        db.execute(insert(RegistroFuente), filas[i:i + 5000])
    return f


def construir_fuentes(db, c: Conciliacion, cfg: dict, usuario: str, avance=lambda p, e: None) -> dict:
    ambito = json.loads(c.ambito or "{}")
    cx = fuentes.Contexto(db, c.empresa_id, c.ejercicio, c.periodo, c.fecha_corte, ambito)
    vigentes = {f.lado: f for f in db.scalars(select(FuenteConciliacion).where(FuenteConciliacion.run_id == c.id, FuenteConciliacion.vigente.is_(True)))}
    info = {}
    for i, (lado, spec) in enumerate(sorted(cfg["fuentes"].items())):
        avance(5 + 20 * i // max(len(cfg["fuentes"]), 1), f"Preparando la fuente {lado}: {spec.get('nombre')}")
        if spec["tipo"] == "ARCHIVO":
            f = vigentes.get(lado)
            if not f:
                raise ErrorConciliacion(f"Importe el archivo de la fuente {lado} ({spec.get('nombre')}) antes de ejecutar.")
        else:
            fn = fuentes.CONSTRUCTORES.get(spec["tipo"])
            if spec["tipo"] == "PLANILLA_LIBRO":
                regs, meta = fuentes.planilla_libro(cx, spec.get("parametros", {}), cfg.get("conceptos", []))
            elif fn:
                regs, meta = fn(cx, spec.get("parametros", {}))
            else:
                raise ErrorConciliacion(f"Tipo de fuente no admitido: {spec['tipo']}")
            f = vigentes.get(lado)
            if not f or f.version_datos != _hash_registros(regs) or f.tipo_fuente != spec["tipo"]:
                f = _guardar_fuente(db, c, lado, spec, regs, meta, usuario)
            else:
                f.saldo, f.observaciones = meta.get("saldo"), meta.get("observaciones")
        info[lado] = {"id": f.id, "rol": f.rol, "nombre": f.nombre, "tipo": f.tipo_fuente, "saldo": f.saldo, "registros": f.registros,
                      "hash": f.version_datos, "archivo": f.nombre_archivo, "observaciones": f.observaciones}
    db.flush()
    return {"info": info, "cx": cx}


def cargar_archivo(db, empresa_id, run_id, lado, usuario, nombre, contenido, *, mapeo_manual=None, fila_encabezado=None, guardar_mapeo=None,
                   confirmar=True) -> dict:
    c = cargar(db, empresa_id, run_id)
    r = exigir(db, empresa_id, usuario, "operar", c.tipo_codigo)
    if c.estado not in EDITABLES:
        raise ErrorConciliacion("La conciliación no admite cambios en su estado actual.")
    p = db.get(PlantillaConciliacion, c.plantilla_id)
    cfg = catalogo.configuracion(db, p)
    spec = cfg["fuentes"].get(lado)
    if not spec or spec["tipo"] != "ARCHIVO":
        raise ErrorConciliacion(f"La fuente {lado} de esta plantilla no se importa desde un archivo.")
    esquema = spec.get("esquema") or "CONC_GENERICO"
    guardado = db.scalar(select(MapeoColumnas).where(MapeoColumnas.empresa_id == empresa_id, MapeoColumnas.esquema == esquema)
                         .order_by(MapeoColumnas.actualizado_en.desc()))
    try:
        lect = fuentes.leer_archivo(nombre, contenido, esquema, json.loads(guardado.mapeo) if guardado else None, fila_encabezado, mapeo_manual)
    except ErrorImportacion as exc:
        raise ErrorConciliacion(str(exc))
    regs = fuentes.normalizar_archivo(esquema, lect["registros"], nombre, cfg.get("conceptos"))
    vista = {k: lect[k] for k in ("formato", "fila_encabezado", "encabezados", "mapeo", "observaciones", "excluidos", "filas_subtotal")}
    vista["sugerencia"] = {k: v for k, v in lect["sugerencia"].items()}
    vista["registros"] = len(regs)
    vista["muestra"] = [{k: _j(v) for k, v in x.items() if k != "datos"} for x in regs[:20]]
    vista["campos"] = fuentes_campos(esquema)
    if not confirmar:
        return vista
    if not regs:
        raise ErrorConciliacion("El archivo no tiene registros válidos con la homologación indicada.")
    h = hashlib.sha256(contenido).hexdigest()
    ruta = _dir(empresa_id) / f"{h[:16]}-{Path(nombre).name[-120:]}"
    if not ruta.exists():
        ruta.write_bytes(contenido)
    f = _guardar_fuente(db, c, lado, spec, regs, {"observaciones": "; ".join(lect["observaciones"][:20]) or None}, usuario,
                        archivo={"nombre_archivo": Path(nombre).name[:255], "hash_archivo": h,
                                 "ruta_archivo": str(ruta.relative_to(Path(config.DATA_DIR)))})
    if guardar_mapeo:
        m = db.scalar(select(MapeoColumnas).where(MapeoColumnas.empresa_id == empresa_id, MapeoColumnas.esquema == esquema,
                                                  MapeoColumnas.nombre == guardar_mapeo))
        if not m:
            m = MapeoColumnas(empresa_id=empresa_id, esquema=esquema, nombre=guardar_mapeo[:120], creado_por=usuario, ambito=c.tipo_codigo)
            db.add(m)
        m.mapeo, m.fila_encabezado, m.usos = json.dumps(lect["mapeo_plantilla"]), lect["fila_encabezado"], (m.usos or 0) + 1
        db.flush()
        f.mapeo_id = m.id
    auditar(db, empresa_id, usuario, "IMPORTAR_FUENTE", "fuente", f.id, {"lado": lado, "archivo": nombre, "hash": h, "registros": len(regs)}, r, c)
    db.commit()
    vista["fuente_id"] = f.id
    return vista


def fuentes_campos(esquema):
    from app.contable.campos import describir_tipo
    return describir_tipo(esquema)["campos"]


# ------------------------------------------------------------------ ejecución
def _registros_vigentes(db, c: Conciliacion) -> tuple[dict, dict]:
    fs = {f.id: f for f in db.scalars(select(FuenteConciliacion).where(FuenteConciliacion.run_id == c.id, FuenteConciliacion.vigente.is_(True)))}
    cols = [x for x in RegistroFuente.__table__.columns]
    por = defaultdict(list)
    for row in db.execute(select(*cols).where(RegistroFuente.fuente_id.in_(list(fs) or [0])).order_by(RegistroFuente.lado, RegistroFuente.orden)):
        r = dict(zip([x.key for x in cols], row))
        r["datos"] = json.loads(r["datos"]) if r["datos"] else {}
        r["_id"], r["_lado"], r["_val"] = r["id"], r["lado"], Decimal(r["importe"] or 0)
        por[r["lado"]].append(r)
    return por, fs


def preparar(db, empresa_id, run_id, usuario, forzar=False) -> tuple[Conciliacion, bool]:
    c = cargar(db, empresa_id, run_id)
    r = exigir(db, empresa_id, usuario, "operar", c.tipo_codigo)
    if c.estado not in EDITABLES:
        raise ErrorConciliacion(f"La conciliación está {c.estado.lower()}: no se puede volver a ejecutar sin reabrirla.")
    if c.estado_proceso in ("EN_COLA", "PROCESANDO"):
        raise Conflicto("La conciliación ya se está ejecutando.")
    c.estado_proceso, c.progreso, c.etapa, c.cancelar, c.error = "EN_COLA", 0, "En cola", False, None
    c.ejecutado_por = usuario
    auditar(db, empresa_id, usuario, "EJECUTAR", "conciliacion", c.id, {"forzar": forzar}, r, c)
    db.commit()
    return c, True


def ejecutar(db, run_id, avance=lambda p, e: None, forzar=False) -> dict:
    c = db.get(Conciliacion, run_id)
    t0 = time.perf_counter()
    tiempos, marca = {}, [time.perf_counter(), "Inicio"]

    def etapa(n, pct):
        ahora = time.perf_counter()
        tiempos[marca[1]] = int((ahora - marca[0]) * 1000)
        marca[0], marca[1] = ahora, n
        c.etapa, c.progreso = n, pct
        avance(pct, n)
    c.estado_proceso = "PROCESANDO"
    db.commit()
    try:
        p = db.get(PlantillaConciliacion, c.plantilla_id)
        cfg = catalogo.configuracion(db, p)
        ambito = json.loads(c.ambito or "{}")
        tol = tolerancia(db, c.empresa_id, c.tipo_codigo, ambito, cfg)
        etapa("Preparación de fuentes", 3)
        prep = construir_fuentes(db, c, cfg, c.ejecutado_por or c.creado_por, avance)
        db.commit()
        etapa("Lectura de registros normalizados", 25)
        por, fs = _registros_vigentes(db, c)
        anterior = db.get(VersionConciliacion, c.version_id) if c.version_id else None
        manuales, rechazadas = [], set()
        if anterior:
            for g in db.scalars(select(GrupoConciliacion).where(GrupoConciliacion.version_id == anterior.id,
                                                                GrupoConciliacion.estado.in_(("CONFIRMADA", "RECHAZADA")))):
                h = json.loads(g.huellas or "{}")
                if g.estado == "RECHAZADA" and g.origen == "AUTOMATICO":
                    rechazadas.add(frozenset(h.get("todas", [])))
                elif g.origen == "MANUAL" and g.estado == "CONFIRMADA":
                    manuales.append({"pasada": g.pasada, "a": h.get("a", []), "b": h.get("b", []), "justificacion": g.justificacion,
                                     "usuario": g.usuario, "regla": g.regla, "detalle": json.loads(g.detalle or "{}")})
        huella = hashlib.sha256(json.dumps([cfg, tol.como_dict(), sorted(f.version_datos for f in fs.values()), manuales,
                                            sorted(sorted(x) for x in rechazadas)], default=_j, sort_keys=True).encode()).hexdigest()
        if anterior and anterior.hash_contenido == huella and not forzar and c.estado != "REABIERTA":
            c.estado_proceso, c.progreso, c.etapa = "COMPLETADO", 100, "Sin cambios: se conserva la versión vigente"
            c.duracion_ms = int((time.perf_counter() - t0) * 1000)
            db.commit()
            return {"run_id": c.id, "version": c.version_actual, "sin_cambios": True}
        etapa("Comparación de fuentes", 30)
        auto = set(cfg.get("confirmar_automaticamente") or [])
        comp = Comparador(por, cfg, tol, auto, rechazadas, avance, cancelar=lambda: _cancelado(db, c.id))
        comp.ejecutar(cfg["pasadas"], cfg["reglas"], manuales)
        etapa("Clasificación de diferencias", 72)
        R = clasificar.Resultado(comp, prep["info"], c.tipo_codigo, cfg, prep["cx"], c, tol)
        clasificar.clasificar(R, cfg["reglas"])
        etapa("Registro de la versión", 82)
        v = guardar_version(db, c, comp, R, cfg, tol, prep["info"], huella, manuales)
        etapa("Completado", 99)
        c.estado_proceso, c.progreso = "COMPLETADO", 100
        if c.estado in ("BORRADOR", "REABIERTA", "OBSERVADA"):
            previo = c.estado
            c.estado = "EJECUTADA"
            db.add(RevisionConciliacion(run_id=c.id, entidad="CONCILIACION", entidad_id=c.id, de_estado=previo, a_estado="EJECUTADA",
                                        usuario=c.ejecutado_por or "sistema", comentario=f"Versión {v.numero} generada"))
    except InterruptedError:
        db.rollback()
        c = db.get(Conciliacion, run_id)
        c.estado_proceso, c.etapa = "CANCELADO", "Cancelado por el usuario"
    except Exception as exc:
        db.rollback()
        c = db.get(Conciliacion, run_id)
        c.estado_proceso, c.error = "ERROR", str(exc)[:2000]
        c.intentos = (c.intentos or 0) + 1
        db.commit()
        raise
    c.tiempos = json.dumps(tiempos)
    c.duracion_ms = int((time.perf_counter() - t0) * 1000)
    db.commit()
    return {"run_id": c.id, "version": c.version_actual, "estado": c.estado_proceso}


def _cancelado(db, run_id) -> bool:
    return bool(db.scalar(select(Conciliacion.cancelar).where(Conciliacion.id == run_id)))


def _huella_dif(c: Conciliacion, d: dict) -> str:
    base = d.get("clave") or "|".join(d["claves"])
    extra = d["subtipo"] if d.get("clave") or d["grupo"] else ""
    return hashlib.sha256(f"{c.tipo_codigo}|{c.ambito_clave}|{base}|{extra}".encode()).hexdigest()[:48]


def guardar_version(db, c: Conciliacion, comp: Comparador, R, cfg, tol, info, huella, manuales) -> VersionConciliacion:
    numero = (c.version_actual or 0) + 1
    v = VersionConciliacion(run_id=c.id, empresa_id=c.empresa_id, numero=numero, configuracion=json.dumps({**cfg, "tolerancia_aplicada": tol.como_dict()},
                                                                                                          default=_j, ensure_ascii=False),
                            fuentes=json.dumps(info, default=_j, ensure_ascii=False), resumen="{}", reporte=json.dumps(R.reporte, default=_j, ensure_ascii=False),
                            hash_contenido=huella, generado_por=c.ejecutado_por or c.creado_por,
                            motivo="Re-ejecución" if numero > 1 else "Primera ejecución")
    db.add(v)
    db.flush()
    # grupos y coincidencias
    filas_g, ref_grupo = [], {}
    for p in comp.pasadas:
        for gi, g in enumerate(p.grupos):
            ref_grupo[(p.nombre, gi)] = len(filas_g)
            filas_g.append({"run_id": c.id, "version_id": v.id, "pasada": p.nombre, "tipo": g.tipo, "modalidad": g.modalidad, "nivel": g.nivel,
                            "regla": (g.regla or "")[:80], "clave": (g.clave or "")[:200] or None, "puntuacion": g.puntuacion, "estado": g.estado,
                            "origen": g.origen, "importe_a": g.importe_a, "importe_b": g.importe_b,
                            "diferencia": Decimal(g.detalle.get("diferencia") or (g.importe_b - g.importe_a)), "dias": g.dias,
                            "detalle": json.dumps(g.detalle, default=_j, ensure_ascii=False), "justificacion": g.justificacion, "usuario": g.usuario,
                            "huellas": json.dumps({"a": [[r["clave_registro"], str(m)] for r, m in g.a], "b": [[r["clave_registro"], str(m)] for r, m in g.b],
                                                   "todas": sorted([r["clave_registro"] for r, _ in g.a + g.b])})})
    ids = []
    for i in range(0, len(filas_g), 5000):
        ids += list(db.scalars(insert(GrupoConciliacion).returning(GrupoConciliacion.id, sort_by_parameter_order=True), filas_g[i:i + 5000]))
    matches = []
    for p in comp.pasadas:
        for gi, g in enumerate(p.grupos):
            gid = ids[ref_grupo[(p.nombre, gi)]]
            for lado, ms in ((p.a, g.a), (p.b, g.b)):
                for r, m in ms:
                    matches.append({"grupo_id": gid, "registro_id": r["_id"], "lado": lado, "importe": m})
    for i in range(0, len(matches), 10000):
        db.execute(insert(MatchConciliacion), matches[i:i + 10000])
    # asignaciones por registro y pasada
    estado_grupo = {}
    for p in comp.pasadas:
        for g in p.grupos:
            for r, _ in g.a + g.b:
                estado_grupo.setdefault((p.nombre, r["_id"]), set()).add(g.estado)
    asign = []
    cont = Counter()
    importes = Counter()
    por_registro = {}
    for p in comp.pasadas:
        for lado in (p.a, p.b):
            for r in comp.reg.get(lado, []):
                total = abs(r["_val"])
                if r["_id"] in comp.duplicados:
                    est, conc = "DUPLICADO", CERO
                elif r["_id"] in comp.excluidos:
                    est, conc = "EXCLUIDO", CERO
                else:
                    pend = p.dispo.get(r["_id"], total)
                    conc = total - pend
                    eg = estado_grupo.get((p.nombre, r["_id"]), set())
                    if r["_id"] in p.ambiguos:
                        est = "AMBIGUO"
                    elif pend == 0 and total and eg <= {"CONFIRMADA"}:
                        est = "CONCILIADO"
                    elif pend == 0 and total:
                        est = "PROPUESTO"
                    elif conc > 0:
                        est = "PARCIAL"
                    elif not total and eg:
                        est = "CONCILIADO"
                    else:
                        est = "PENDIENTE"
                asign.append({"version_id": v.id, "registro_id": r["_id"], "pasada": p.nombre, "lado": lado, "total": total, "conciliado": conc, "estado": est})
                previo = por_registro.get(r["_id"])
                if previo is None or GRAVEDAD.index(est) > GRAVEDAD.index(previo[0]):
                    por_registro[r["_id"]] = (est, total)
    for est, total in por_registro.values():  # cada registro se cuenta una sola vez (su estado menos favorable entre comparaciones)
        cont[est] += 1
        importes[est] += total
    for i in range(0, len(asign), 10000):
        db.execute(insert(AsignacionRegistro), asign[i:i + 10000])
    # diferencias con continuidad
    previas = {}
    if c.version_id:
        for d in db.scalars(select(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id == c.version_id)):
            previas[d.huella] = d
    prev_run = db.scalar(select(Conciliacion).where(Conciliacion.empresa_id == c.empresa_id, Conciliacion.ambito_clave == c.ambito_clave,
                                                    Conciliacion.fecha_corte < c.fecha_corte, Conciliacion.version_id.is_not(None))
                         .order_by(Conciliacion.fecha_corte.desc()))
    prev_periodo = {}
    if prev_run:
        for d in db.scalars(select(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id == prev_run.version_id)):
            prev_periodo[d.huella] = d
    periodo = c.ejercicio * 100 + c.periodo
    vistas = set()
    filas_d = []
    n = 0
    for d in R.difs:
        h = _huella_dif(c, d)
        if h in vistas:
            continue
        vistas.add(h)
        n += 1
        ant = previas.get(h)
        prev = prev_periodo.get(h) if not ant else None
        origen = ant or prev
        imp = Decimal(d["importe"] or 0).quantize(Decimal("0.01"))
        estado_dif = "DETECTADO"
        if ant:
            estado_dif = ant.estado
        elif prev and prev.estado not in FINALES_DIF:
            estado_dif = prev.estado if prev.estado != "DETECTADO" else "PENDIENTE_REVISION"
        regs = [R.registros[i] for i in d["registros"]]
        filas_d.append({
            "empresa_id": c.empresa_id, "run_id": c.id, "version_id": v.id, "codigo": f"D{c.id}-{numero}-{n:05d}", "tipo_conciliacion": c.tipo_codigo,
            "clasificacion": d["clasificacion"], "subtipo": (d["subtipo"] or "")[:50] or None, "prioridad": d["prioridad"],
            "fuente": (d["fuente"] or "")[:60] or None, "cuenta": (d["cuenta"] or "")[:20] or None, "documento": (d["documento"] or "")[:80] or None,
            "tercero": (d["tercero"] or "")[:20] or None, "razon_social": (d["razon_social"] or "")[:255] or None, "importe": imp,
            "moneda": d["moneda"] or "PEN", "fecha": d["fecha"],
            "evidencia": json.dumps({"registros": d["registros"][:200], "claves": d["claves"][:200], "grupo": d["grupo"], "valores": d["valores"],
                                     "pasada": d.get("_pasada"), "lados": sorted({r["_lado"] for r in regs})}, default=_j, ensure_ascii=False),
            "regla": (d["regla"] or "")[:80] or None, "explicacion": d["explicacion"], "recomendacion": d["recomendacion"],
            "dentro_tolerancia": bool(d["dentro_tolerancia"]), "responsable": (origen.responsable if origen else None) or c.responsable,
            "fecha_limite": origen.fecha_limite if origen else c.fecha_limite, "estado": estado_dif,
            "causa": origen.causa if origen else None, "accion_correctiva": origen.accion_correctiva if origen else None, "huella": h,
            "origen_id": (origen.origen_id or origen.id) if origen else None, "anterior_id": origen.id if origen else None,
            "periodo_origen": origen.periodo_origen if origen else periodo,
            "fecha_deteccion": origen.fecha_deteccion if origen else date.today(),
            "importe_original": origen.importe_original if origen else imp, "importe_pendiente": imp,
            "recurrencias": (origen.recurrencias + (1 if prev else 0)) if origen else 0, "personal": bool(d["personal"])})
        if prev:
            prev.trasladada = True
    for i in range(0, len(filas_d), 5000):
        db.execute(insert(DiferenciaConciliacion), filas_d[i:i + 5000])
    # incidencias del periodo anterior que ya no se reproducen
    for h, d in prev_periodo.items():
        if h not in vistas and d.estado not in FINALES_DIF and not d.trasladada:
            db.add(RevisionConciliacion(run_id=d.run_id, entidad="DIFERENCIA", entidad_id=d.id, de_estado=d.estado, a_estado="SUBSANADO",
                                        usuario="sistema", comentario=f"No se reproduce en la conciliación al {c.fecha_corte:%d/%m/%Y}"))
            d.estado = "SUBSANADO"
    por_clas = Counter(x["clasificacion"] for x in filas_d)
    por_prio = Counter(x["prioridad"] for x in filas_d)
    total_reg = sum(cont.values())
    total_imp = sum(importes.values(), CERO)
    resumen = {
        "version": numero, "registros": {lado: len(lst) for lado, lst in comp.reg.items()}, "asignaciones": dict(cont),
        "importes": {k: str(v) for k, v in importes.items()},
        "porcentaje_cantidad": {k: round(100 * v / total_reg, 2) for k, v in cont.items()} if total_reg else {},
        "porcentaje_importe": {k: float(round(100 * v / total_imp, 2)) for k, v in importes.items()} if total_imp else {},
        "grupos": dict(Counter(f"{g['tipo']}:{g['estado']}" for g in filas_g)), "diferencias": len(filas_d),
        "por_clasificacion": dict(por_clas), "por_prioridad": dict(por_prio),
        "importe_diferencias": str(sum((abs(x["importe"]) for x in filas_d), CERO)),
        "dentro_tolerancia": sum(1 for x in filas_d if x["dentro_tolerancia"]),
        "manuales_reaplicadas": sum(1 for m in manuales if m.get("_reaplicada")), "manuales_no_reaplicadas": sum(1 for m in manuales if not m.get("_reaplicada")),
        "duplicados": len(comp.duplicados), "excluidos": len(comp.excluidos), "pasadas": [{"nombre": p.nombre, "modo": p.modo, "omitida": p.omitida,
                                                                                              "grupos": len(p.grupos)} for p in comp.pasadas],
        "tolerancia": tol.como_dict(), "trasladadas": sum(1 for x in filas_d if x["anterior_id"] and x["periodo_origen"] != periodo)}
    v.resumen = json.dumps(resumen, default=_j, ensure_ascii=False)
    c.version_actual, c.version_id = numero, v.id
    c.resumen = v.resumen
    c.lock_version = (c.lock_version or 0) + 1
    db.flush()
    return v


# ------------------------------------------------------------------ flujo de la conciliación
def cambiar_estado(db, empresa_id, run_id, usuario, nuevo, comentario=None, lock_version=None) -> Conciliacion:
    c = cargar(db, empresa_id, run_id)
    if nuevo not in TRANSICIONES:
        raise ErrorConciliacion("Estado no válido")
    accion, origenes = TRANSICIONES[nuevo]
    r = exigir(db, empresa_id, usuario, accion, c.tipo_codigo if accion == "operar" else None)
    if c.estado not in origenes:
        raise ErrorConciliacion(f"No se puede pasar de {c.estado} a {nuevo}.")
    if not c.version_id:
        raise ErrorConciliacion("La conciliación no tiene una versión ejecutada.")
    comentario = (comentario or "").strip() or None
    if nuevo == "OBSERVADA" and (not comentario or len(comentario) < 10):
        raise ErrorConciliacion("Indique la observación (mínimo 10 caracteres).")
    cfg = catalogo.configuracion(db, db.get(PlantillaConciliacion, c.plantilla_id))
    preparador = (c.ejecutado_por or c.creado_por or "").lower()
    if nuevo == "REVISADA" and usuario.lower() == preparador:
        raise SinPermiso("Separación de funciones: quien elabora la conciliación no puede revisarla.")
    if nuevo == "APROBADA":
        if usuario.lower() in {preparador, (c.revisado_por or "").lower()}:
            raise SinPermiso("Separación de funciones: quien elabora o revisa no puede aprobar.")
        crit = cfg.get("criterios_aprobacion") or {}
        if crit.get("sin_ambiguas") and db.scalar(select(func.count()).select_from(GrupoConciliacion).where(
                GrupoConciliacion.version_id == c.version_id, GrupoConciliacion.estado == "AMBIGUA")):
            raise ErrorConciliacion("Hay coincidencias ambiguas sin resolver: resuélvalas antes de aprobar.")
        if crit.get("sin_criticas_abiertas") and db.scalar(select(func.count()).select_from(DiferenciaConciliacion).where(
                DiferenciaConciliacion.version_id == c.version_id, DiferenciaConciliacion.prioridad == "CRITICO",
                DiferenciaConciliacion.estado.in_(("DETECTADO", "REABIERTO", "PENDIENTE_REVISION")))):
            raise ErrorConciliacion("Hay diferencias críticas sin analizar: justifíquelas o regístrelas como pendientes de regularización.")
    _lock(db, c, lock_version)
    v = db.get(VersionConciliacion, c.version_id)
    ahora = datetime.now()
    if nuevo == "REVISADA":
        c.revisado_por, c.revisado_en = usuario, ahora
        db.add(AprobacionConciliacion(run_id=c.id, version_id=v.id, accion="REVISAR", usuario=usuario, rol=r, comentario=comentario))
    elif nuevo == "APROBADA":
        c.aprobado_por, c.aprobado_en = usuario, ahora
        v.inmutable, v.estado_al_cerrar = True, "APROBADA"
        db.add(AprobacionConciliacion(run_id=c.id, version_id=v.id, accion="APROBAR", usuario=usuario, rol=r, comentario=comentario))
    elif nuevo == "CERRADA":
        v.inmutable, v.estado_al_cerrar = True, "CERRADA"
        db.add(AprobacionConciliacion(run_id=c.id, version_id=v.id, accion="CERRAR", usuario=usuario, rol=r, comentario=comentario))
    previo = c.estado
    c.estado = nuevo
    c.lock_version = (c.lock_version or 0) + 1
    db.add(RevisionConciliacion(run_id=c.id, entidad="CONCILIACION", entidad_id=c.id, de_estado=previo, a_estado=nuevo, usuario=usuario, rol=r,
                                comentario=comentario))
    auditar(db, empresa_id, usuario, f"ESTADO_{nuevo}", "conciliacion", c.id, {"de": previo, "a": nuevo, "comentario": comentario}, r, c)
    db.commit()
    return c


def revertir_conciliacion(db, empresa_id, run_id, usuario, motivo) -> Conciliacion:
    c = cargar(db, empresa_id, run_id)
    r = exigir(db, empresa_id, usuario, "revertir")
    if c.estado not in ("APROBADA", "CERRADA"):
        raise ErrorConciliacion("Solo se revierte una conciliación aprobada o cerrada.")
    if not motivo or len(motivo.strip()) < 10:
        raise ErrorConciliacion("Indique el motivo de la reversión (mínimo 10 caracteres).")
    db.add(ReversionConciliacion(run_id=c.id, version_id=c.version_id, alcance="CONCILIACION", motivo=motivo.strip(), usuario=usuario, rol=r))
    db.add(AprobacionConciliacion(run_id=c.id, version_id=c.version_id, accion="REABRIR", usuario=usuario, rol=r, comentario=motivo.strip()))
    db.add(RevisionConciliacion(run_id=c.id, entidad="CONCILIACION", entidad_id=c.id, de_estado=c.estado, a_estado="REABIERTA", usuario=usuario,
                                rol=r, comentario=motivo.strip()))
    previo = c.estado
    c.estado, c.aprobado_por, c.aprobado_en = "REABIERTA", None, None
    c.lock_version = (c.lock_version or 0) + 1
    auditar(db, empresa_id, usuario, "REVERTIR_CONCILIACION", "conciliacion", c.id, {"de": previo, "motivo": motivo}, r, c)
    db.commit()
    return c


# ------------------------------------------------------------------ conciliación manual
def _editable(db, c: Conciliacion):
    v = db.get(VersionConciliacion, c.version_id) if c.version_id else None
    if not v:
        raise ErrorConciliacion("Ejecute la conciliación antes de conciliar manualmente.")
    if v.inmutable or c.estado not in ("EJECUTADA", "OBSERVADA"):
        raise ErrorConciliacion("La versión vigente está aprobada o en revisión: no admite cambios (reabra la conciliación con autorización).")
    return v


def _consumir(db, v, pasada, reg_id, importe):
    a = db.scalar(select(AsignacionRegistro).where(AsignacionRegistro.version_id == v.id, AsignacionRegistro.registro_id == reg_id,
                                                   AsignacionRegistro.pasada == pasada))
    if not a:
        raise ErrorConciliacion(f"El registro {reg_id} no participa en la comparación {pasada}.")
    if a.estado in ("DUPLICADO", "EXCLUIDO"):
        raise ErrorConciliacion(f"El registro {reg_id} está marcado como {a.estado.lower()}.")
    r = db.execute(update(AsignacionRegistro).where(AsignacionRegistro.id == a.id, AsignacionRegistro.lock == a.lock,
                                                    AsignacionRegistro.conciliado + importe <= AsignacionRegistro.total)
                   .values(conciliado=AsignacionRegistro.conciliado + importe, lock=AsignacionRegistro.lock + 1))
    if r.rowcount != 1:
        raise Conflicto(f"El registro {reg_id} ya no tiene saldo disponible (otro usuario lo concilió o el importe excede su saldo).")
    db.refresh(a)
    a.estado = "CONCILIADO" if a.conciliado == a.total else "PARCIAL"
    return a


def conciliar_manual(db, empresa_id, run_id, usuario, datos: dict) -> GrupoConciliacion:
    c = cargar(db, empresa_id, run_id)
    r = exigir(db, empresa_id, usuario, "operar", c.tipo_codigo)
    v = _editable(db, c)
    pasada = datos.get("pasada") or "A-B"
    la, lb = pasada.split("-")
    just = (datos.get("justificacion") or "").strip()
    if len(just) < 10:
        raise ErrorConciliacion("Registre la justificación de la conciliación manual (mínimo 10 caracteres).")
    sel_a, sel_b = datos.get("registros_a") or [], datos.get("registros_b") or []
    if not sel_a or not sel_b:
        raise ErrorConciliacion("Seleccione registros en ambos paneles.")
    regs = {x.id: x for x in db.scalars(select(RegistroFuente).where(RegistroFuente.id.in_([s["id"] for s in sel_a + sel_b]),
                                                                     RegistroFuente.run_id == c.id))}
    total_a = total_b = CERO
    for lado, sel in ((la, sel_a), (lb, sel_b)):
        for s in sel:
            x = regs.get(s["id"])
            if not x or x.lado != lado:
                raise ErrorConciliacion(f"El registro {s['id']} no pertenece a la fuente {lado} de esta conciliación.")
            imp = Decimal(str(s.get("importe") or abs(x.importe)))
            if imp <= 0:
                raise ErrorConciliacion("Los importes a conciliar deben ser positivos.")
            s["_imp"] = imp
            firmado = imp if x.importe >= 0 else -imp
            if lado == la:
                total_a += firmado
            else:
                total_b += firmado
    cfg = catalogo.configuracion(db, db.get(PlantillaConciliacion, c.plantilla_id))
    pc = next((p for p in cfg["pasadas"] if f"{p['a']}-{p['b']}" == pasada), {"signo": "IGUAL"})
    if pc.get("signo") == "OPUESTO":
        total_b = -total_b
    tol = tolerancia(db, empresa_id, c.tipo_codigo, json.loads(c.ambito or "{}"), cfg)
    dif = total_b - total_a
    if dif and not tol.dentro(dif, total_a) and not datos.get("aceptar_diferencia"):
        raise ErrorConciliacion(f"Los totales seleccionados difieren en {dif}. Ajuste los importes (aplicación parcial) o acepte la diferencia "
                                "para registrarla como diferencia monetaria.")
    for lado, sel in ((la, sel_a), (lb, sel_b)):
        for s in sel:
            _consumir(db, v, pasada, s["id"], s["_imp"])
    tipo = "MANUAL"
    g = GrupoConciliacion(run_id=c.id, version_id=v.id, pasada=pasada, tipo=tipo, modalidad=f"{'1' if len(sel_a) == 1 else 'N'}:{'1' if len(sel_b) == 1 else 'N'}",
                          regla="MANUAL", estado="CONFIRMADA", origen="MANUAL", importe_a=total_a, importe_b=total_b, diferencia=dif,
                          detalle=json.dumps({"diferencia": str(dif)}), justificacion=just, usuario=usuario, confirmado_por=usuario,
                          huellas=json.dumps({"a": [[regs[s["id"]].clave_registro, str(s["_imp"])] for s in sel_a],
                                              "b": [[regs[s["id"]].clave_registro, str(s["_imp"])] for s in sel_b],
                                              "todas": sorted(regs[s["id"]].clave_registro for s in sel_a + sel_b)}))
    db.add(g)
    db.flush()
    for lado, sel in ((la, sel_a), (lb, sel_b)):
        for s in sel:
            db.add(MatchConciliacion(grupo_id=g.id, registro_id=s["id"], lado=lado, importe=s["_imp"]))
    ids = {s["id"] for s in sel_a + sel_b}
    restante = {a.registro_id: a.total - a.conciliado for a in db.scalars(select(AsignacionRegistro).where(
        AsignacionRegistro.version_id == v.id, AsignacionRegistro.pasada == pasada, AsignacionRegistro.registro_id.in_(ids)))}
    for d in db.scalars(select(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id == v.id,
                                                             DiferenciaConciliacion.estado.notin_(FINALES_DIF))):
        ev = json.loads(d.evidencia or "{}")
        afectados = ids & set(ev.get("registros", []))
        if not afectados or d.clasificacion not in ("REGISTRO_FALTANTE_CONTABILIDAD", "REGISTRO_FALTANTE_FUENTE_EXTERNA", "COINCIDENCIA_AMBIGUA",
                                                    "DIFERENCIA_NO_IDENTIFICADA", "DIFERENCIA_TEMPORAL"):
            continue
        if d.clasificacion != "COINCIDENCIA_AMBIGUA" and len(ev.get("registros", [])) == 1 and restante.get(next(iter(afectados)), 0) > 0:
            # aplicación parcial: la diferencia sigue abierta por el saldo no conciliado (visible y cuantificado)
            pend = restante[next(iter(afectados))]
            pend = pend if d.importe >= 0 else -pend
            db.add(RevisionConciliacion(run_id=c.id, entidad="DIFERENCIA", entidad_id=d.id, de_estado=d.estado, a_estado=d.estado, usuario=usuario,
                                        rol=r, comentario=f"Conciliada parcialmente (grupo #{g.id}); pendiente {pend}",
                                        cambios=json.dumps({"importe_pendiente": [str(d.importe_pendiente), str(pend)]})))
            d.importe_pendiente = pend
            continue
        db.add(RevisionConciliacion(run_id=c.id, entidad="DIFERENCIA", entidad_id=d.id, de_estado=d.estado, a_estado="SUBSANADO", usuario=usuario,
                                    rol=r, comentario=f"Conciliada manualmente (grupo #{g.id})"))
        d.estado = "SUBSANADO"
    if dif:
        n = db.scalar(select(func.count()).select_from(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id == v.id)) + 1
        r0 = regs[sel_a[0]["id"]]
        db.add(DiferenciaConciliacion(empresa_id=empresa_id, run_id=c.id, version_id=v.id, codigo=f"D{c.id}-{v.numero}-{n:05d}M",
                                      tipo_conciliacion=c.tipo_codigo, clasificacion="DIFERENCIA_MONETARIA",
                                      subtipo="DIFERENCIA_CONCILIACION_MANUAL", prioridad="INFORMATIVO" if tol.dentro(dif, total_a) else "MEDIO",
                                      cuenta=r0.cuenta, documento=r0.numero or r0.operacion, tercero=r0.tercero, razon_social=r0.razon_social,
                                      importe=dif, moneda=r0.moneda, fecha=r0.fecha, dentro_tolerancia=tol.dentro(dif, total_a),
                                      evidencia=json.dumps({"registros": sorted(ids), "grupo": g.id}), regla="MANUAL",
                                      explicacion=f"Conciliación manual con diferencia de {dif}: {just}", huella=f"M{g.id}",
                                      fecha_deteccion=date.today(), importe_original=dif, importe_pendiente=dif, periodo_origen=c.ejercicio * 100 + c.periodo,
                                      responsable=c.responsable, personal=False))
    c.lock_version = (c.lock_version or 0) + 1
    auditar(db, empresa_id, usuario, "CONCILIAR_MANUAL", "grupo", g.id, {"a": sel_a, "b": sel_b, "diferencia": dif, "justificacion": just}, r, c)
    db.commit()
    return g


def _grupo(db, empresa_id, grupo_id):
    g = db.get(GrupoConciliacion, grupo_id)
    c = db.get(Conciliacion, g.run_id) if g else None
    if not g or not c or c.empresa_id != empresa_id:
        raise LookupError("Coincidencia no encontrada")
    if g.version_id != c.version_id:
        raise ErrorConciliacion("La coincidencia pertenece a una versión anterior (histórica).")
    return g, c


def decidir_grupo(db, empresa_id, grupo_id, usuario, accion, motivo=None) -> GrupoConciliacion:
    """confirmar · rechazar (propuestas o ambiguas) · revertir (confirmadas)."""
    g, c = _grupo(db, empresa_id, grupo_id)
    v = _editable(db, c)
    r = exigir(db, empresa_id, usuario, "revertir" if accion == "revertir" else "operar", None if accion == "revertir" else c.tipo_codigo)
    previo = g.estado
    if accion == "confirmar":
        if g.estado != "PROPUESTA":
            raise ErrorConciliacion("Solo se confirman coincidencias propuestas (las ambiguas se resuelven manualmente).")
        g.estado, g.confirmado_por = "CONFIRMADA", usuario
        for m in db.scalars(select(MatchConciliacion).where(MatchConciliacion.grupo_id == g.id)):
            a = db.scalar(select(AsignacionRegistro).where(AsignacionRegistro.version_id == v.id, AsignacionRegistro.registro_id == m.registro_id,
                                                           AsignacionRegistro.pasada == g.pasada))
            if a and a.estado == "PROPUESTO":
                a.estado = "CONCILIADO"
    elif accion in ("rechazar", "revertir"):
        if accion == "rechazar" and g.estado not in ("PROPUESTA", "AMBIGUA"):
            raise ErrorConciliacion("Solo se rechazan propuestas o coincidencias ambiguas.")
        if accion == "revertir" and g.estado != "CONFIRMADA":
            raise ErrorConciliacion("Solo se revierten coincidencias confirmadas.")
        if not motivo or len(motivo.strip()) < 10:
            raise ErrorConciliacion("Indique el motivo (mínimo 10 caracteres).")
        if g.estado != "AMBIGUA":
            for m in db.scalars(select(MatchConciliacion).where(MatchConciliacion.grupo_id == g.id)):
                db.execute(update(AsignacionRegistro).where(AsignacionRegistro.version_id == v.id, AsignacionRegistro.registro_id == m.registro_id,
                                                            AsignacionRegistro.pasada == g.pasada)
                           .values(conciliado=AsignacionRegistro.conciliado - m.importe, estado="PENDIENTE", lock=AsignacionRegistro.lock + 1))
        g.estado = "RECHAZADA" if accion == "rechazar" else "REVERTIDA"
        if accion == "revertir":
            db.add(ReversionConciliacion(run_id=c.id, version_id=v.id, grupo_id=g.id, alcance="COINCIDENCIA", motivo=motivo.strip(), usuario=usuario, rol=r))
        if previo != "AMBIGUA":
            regs = db.scalars(select(RegistroFuente).join(MatchConciliacion, MatchConciliacion.registro_id == RegistroFuente.id)
                              .where(MatchConciliacion.grupo_id == g.id)).all()
            n = db.scalar(select(func.count()).select_from(DiferenciaConciliacion).where(DiferenciaConciliacion.version_id == v.id))
            for x in regs:
                n += 1
                db.add(DiferenciaConciliacion(empresa_id=empresa_id, run_id=c.id, version_id=v.id, codigo=f"D{c.id}-{v.numero}-{n:05d}R",
                                              tipo_conciliacion=c.tipo_codigo, clasificacion="DIFERENCIA_NO_IDENTIFICADA", subtipo="LIBERADO_POR_DECISION",
                                              prioridad="MEDIO", cuenta=x.cuenta, documento=x.numero or x.operacion, tercero=x.tercero,
                                              razon_social=x.razon_social, importe=x.importe, moneda=x.moneda, fecha=x.fecha,
                                              evidencia=json.dumps({"registros": [x.id], "grupo": g.id}), regla=g.regla,
                                              explicacion=f"Registro pendiente tras {'rechazar' if accion == 'rechazar' else 'revertir'} la coincidencia #{g.id}: "
                                              f"{motivo.strip()}", huella=f"L{g.id}|{x.id}", fecha_deteccion=date.today(), importe_original=x.importe,
                                              importe_pendiente=x.importe, periodo_origen=c.ejercicio * 100 + c.periodo, responsable=c.responsable,
                                              personal=x.personal))
    else:
        raise ErrorConciliacion("Acción no válida")
    g.justificacion = (g.justificacion or "") + (f"\n[{accion}] {motivo}" if motivo else "")
    db.add(RevisionConciliacion(run_id=c.id, entidad="GRUPO", entidad_id=g.id, de_estado=previo, a_estado=g.estado, usuario=usuario, rol=r, comentario=motivo))
    c.lock_version = (c.lock_version or 0) + 1
    auditar(db, empresa_id, usuario, f"GRUPO_{accion.upper()}", "grupo", g.id, {"de": previo, "a": g.estado, "motivo": motivo}, r, c)
    db.commit()
    return g


# ------------------------------------------------------------------ incidencias (diferencias)
def actualizar_diferencia(db, empresa_id, dif_id, usuario, datos: dict) -> DiferenciaConciliacion:
    d = db.get(DiferenciaConciliacion, dif_id)
    if not d or d.empresa_id != empresa_id:
        raise LookupError("Diferencia no encontrada")
    c = db.get(Conciliacion, d.run_id)
    nuevo = datos.get("estado")
    accion = TRANS_DIF[nuevo][0] if nuevo else "incidencias"
    r = exigir(db, empresa_id, usuario, accion, c.tipo_codigo if accion == "incidencias" else None)
    if datos.get("lock_version") is not None:
        res = db.execute(update(DiferenciaConciliacion).where(DiferenciaConciliacion.id == d.id,
                                                              DiferenciaConciliacion.lock_version == datos["lock_version"])
                         .values(lock_version=datos["lock_version"] + 1))
        if res.rowcount != 1:
            db.rollback()
            raise Conflicto("La diferencia fue modificada por otro usuario.")
        db.refresh(d)
    cambios = {}
    for k in ("responsable", "causa", "accion_correctiva"):
        if k in datos and datos[k] != getattr(d, k):
            cambios[k] = [getattr(d, k), datos[k]]
            setattr(d, k, datos[k])
    if "fecha_limite" in datos:
        fl = date.fromisoformat(datos["fecha_limite"]) if isinstance(datos["fecha_limite"], str) and datos["fecha_limite"] else datos["fecha_limite"]
        if fl != d.fecha_limite:
            cambios["fecha_limite"] = [_j(d.fecha_limite), _j(fl)]
            d.fecha_limite = fl
    comentario = (datos.get("comentario") or "").strip() or None
    if nuevo and nuevo != d.estado:
        origenes = TRANS_DIF[nuevo][1]
        if origenes and d.estado not in origenes:
            raise ErrorConciliacion(f"No se puede pasar de {d.estado} a {nuevo}.")
        if nuevo == "JUSTIFICADO" and not (d.causa or "").strip():
            raise ErrorConciliacion("Registre la causa para justificar la diferencia.")
        if nuevo == "PENDIENTE_REGULARIZACION" and not (d.accion_correctiva or "").strip():
            raise ErrorConciliacion("Registre la acción correctiva (se preparará para el módulo de asientos de regularización).")
        if nuevo == "REABIERTO" and (not comentario or len(comentario) < 10):
            raise ErrorConciliacion("Indique el motivo de la reapertura (mínimo 10 caracteres).")
        cambios["estado"] = [d.estado, nuevo]
        db.add(RevisionConciliacion(run_id=d.run_id, entidad="DIFERENCIA", entidad_id=d.id, de_estado=d.estado, a_estado=nuevo, usuario=usuario,
                                    rol=r, comentario=comentario, cambios=json.dumps(cambios, default=_j, ensure_ascii=False)))
        d.estado = nuevo
    elif cambios or comentario:
        db.add(RevisionConciliacion(run_id=d.run_id, entidad="DIFERENCIA", entidad_id=d.id, de_estado=d.estado, a_estado=d.estado, usuario=usuario,
                                    rol=r, comentario=comentario, cambios=json.dumps(cambios, default=_j, ensure_ascii=False) if cambios else None))
    d.lock_version = (d.lock_version or 0) + 1
    auditar(db, empresa_id, usuario, "ACTUALIZAR_DIFERENCIA", "diferencia", d.id, {**cambios, "comentario": comentario}, r, c)
    db.commit()
    return d


def adjuntar(db, empresa_id, usuario, nombre, tipo, contenido, meta: dict) -> AdjuntoConciliacion:
    run_id = meta.get("run_id")
    c = cargar(db, empresa_id, int(run_id)) if run_id else None
    if meta.get("diferencia_id"):
        d = db.get(DiferenciaConciliacion, int(meta["diferencia_id"]))
        if not d or d.empresa_id != empresa_id:
            raise LookupError("Diferencia no encontrada")
        c = c or db.get(Conciliacion, d.run_id)
    if not c:
        raise ErrorConciliacion("Relacione el documento con una conciliación o diferencia.")
    r = exigir(db, empresa_id, usuario, "incidencias", c.tipo_codigo)
    if not contenido or len(contenido) > 20 * 1024 * 1024:
        raise ErrorConciliacion("El archivo está vacío o supera 20 MB.")
    ext = Path(nombre or "").suffix.lower()
    if ext not in {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".csv", ".txt", ".docx", ".xml", ".zip"}:
        raise ErrorConciliacion(f"Tipo de archivo no permitido ({ext or 'sin extensión'}).")
    h = hashlib.sha256(contenido).hexdigest()
    ruta = _dir(empresa_id) / "sustentos"
    ruta.mkdir(exist_ok=True)
    ruta = ruta / f"{h[:16]}{ext}"
    if not ruta.exists():
        ruta.write_bytes(contenido)
    a = AdjuntoConciliacion(empresa_id=empresa_id, run_id=c.id, diferencia_id=int(meta["diferencia_id"]) if meta.get("diferencia_id") else None,
                            grupo_id=int(meta["grupo_id"]) if meta.get("grupo_id") else None,
                            registro_id=int(meta["registro_id"]) if meta.get("registro_id") else None, categoria=(meta.get("categoria") or "OTRO")[:30],
                            descripcion=meta.get("descripcion"), nombre=Path(nombre).name[:255], tipo_contenido=tipo, tamano=len(contenido), hash=h,
                            ruta=str(ruta.relative_to(Path(config.DATA_DIR))), confidencial=bool(meta.get("confidencial")), usuario=usuario)
    db.add(a)
    db.flush()
    auditar(db, empresa_id, usuario, "ADJUNTAR", "adjunto", a.id, {"nombre": a.nombre, "hash": h, "diferencia": a.diferencia_id}, r, c)
    db.commit()
    return a


def ruta_adjunto(a: AdjuntoConciliacion) -> Path:
    return Path(config.DATA_DIR) / a.ruta


# ------------------------------------------------------------------ tasas tributarias (reglas de la fase 4)
def aprobar_regla_tributaria(db, empresa_id, usuario, regla_id, comentario=None):
    """El responsable tributario aprueba una tasa de detracción, retención o percepción (con vigencia y fuente normativa).
    Sin esta aprobación la conciliación no calcula importes esperados (no se usan tasas fijas)."""
    from app.models import ReglaCompensacion
    r = exigir(db, empresa_id, usuario, "configurar")
    x = db.get(ReglaCompensacion, regla_id)
    if not x or x.empresa_id != empresa_id or x.tipo not in ("DETRACCION", "RETENCION", "PERCEPCION"):
        raise LookupError("Regla tributaria no encontrada")
    par = json.loads(x.parametros or "{}")
    if par.get("tasa") in (None, ""):
        raise ErrorConciliacion("La regla no tiene tasa.")
    if not (x.sustento or "").strip() or not x.vigente_desde:
        raise ErrorConciliacion("Registre la fuente normativa (sustento) y la fecha de inicio de vigencia antes de aprobar la tasa.")
    if (x.usuario or "").lower() == usuario.lower():
        raise SinPermiso("Separación de funciones: quien configura la tasa no puede aprobarla.")
    x.autorizado_por = usuario
    auditar(db, empresa_id, usuario, "APROBAR_TASA", "regla_tributaria", x.id, {"tipo": x.tipo, "codigo": x.codigo, "tasa": par["tasa"],
                                                                                "vigente_desde": x.vigente_desde, "sustento": x.sustento,
                                                                                "comentario": comentario}, r)
    db.commit()
    return x
