"""Ejecución de auditorías (asíncrona, cancelable, incremental y sin hallazgos duplicados).

Etapas: selección de reglas → contexto (fases 3–6, carga perezosa) → evaluación regla por regla con su población y tiempos
→ consolidación de hallazgos por huella (un mismo hecho nunca se duplica; las reincidencias se identifican) → riesgo según
la matriz y la materialidad → grupos de exposición (montos superpuestos no se suman) → resumen.

Reglas normativas sin validación: NO_VALIDADA. Fuera de vigencia: FUERA_DE_VIGENCIA. Sin datos: SIN_DATOS. Faltan
parámetros normativos: PENDIENTE_EVALUACION. Si la huella de entrada (datos + versión de la regla + materialidad + alcance)
no cambió desde la última ejecución del encargo, la regla se REUTILIZA sin recalcular (procesamiento incremental).
"""
import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.analisis import saldos
from app.auditoria import catalogo, riesgo
from app.auditoria.base import CERO, Contexto, Regla
from app.models import (AlcanceAuditoria, EjecucionAuditoria, EncargoAuditoria, EvidenciaHallazgo, GrupoHallazgos, HallazgoAuditoria, Materialidad,
                        ResultadoRegla, RevisionAuditoria, ReglaAuditoria)


class Cancelado(Exception):
    pass


def _j(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def snapshot_regla(r: ReglaAuditoria) -> dict:
    return {c.key: _j(getattr(r, c.key)) for c in ReglaAuditoria.__table__.columns if c.key not in ("actualizado_en",)}


def alcance_de(db, encargo) -> dict:
    a = defaultdict(list)
    for s in db.scalars(select(AlcanceAuditoria).where(AlcanceAuditoria.engagement_id == encargo.id)):
        a[{"MODULO": "modulos", "CUENTA": "cuentas", "CENTRO_COSTO": "centros_costo", "PROYECTO": "proyectos", "UNIDAD_NEGOCIO": "unidades_negocio",
           "REGLA": "reglas", "TERCERO": "terceros"}[s.tipo]].append(s.valor)
    return dict(a)


TIPO_MODULOS = {"TRIBUTARIA_PREVENTIVA": ["TRIBUTARIA", "DEVENGOS"], "PARAMETRIZACION": ["PARAMETRIZACION", "ORIGEN_DESTINO"],
                "CONTROL_INTERNO": ["INTEGRIDAD", "ASIENTOS", "DUPLICIDADES", "TESORERIA"]}


def reglas_aplicables(db, encargo, tipo_run: str, parametros: dict, alcance: dict) -> list[ReglaAuditoria]:
    catalogo.sembrar(db)
    todas = {}
    for r in db.scalars(select(ReglaAuditoria).where((ReglaAuditoria.empresa_id.is_(None)) | (ReglaAuditoria.empresa_id == encargo.empresa_id))
                        .order_by(ReglaAuditoria.empresa_id.is_not(None), ReglaAuditoria.codigo)):
        todas[r.codigo] = r  # la versión de la empresa reemplaza a la del catálogo
    cats = {c: m for c, m in ((r.categoria_id, catalogo.modulo_de(db, r)) for r in todas.values())}
    modulos = parametros.get("modulos") or alcance.get("modulos") or TIPO_MODULOS.get(encargo.tipo)
    codigos = parametros.get("reglas") or alcance.get("reglas")
    out = []
    for r in todas.values():
        if not r.activa:
            continue
        if codigos and r.codigo not in codigos:
            continue
        if modulos and cats[r.categoria_id] not in modulos:
            continue
        out.append(r)
    return out


def materialidad_aprobada(db, encargo) -> Materialidad | None:
    if encargo.materialidad_id:
        m = db.get(Materialidad, encargo.materialidad_id)
        if m and m.estado == "APROBADA":
            return m
    return db.scalar(select(Materialidad).where(Materialidad.empresa_id == encargo.empresa_id, Materialidad.ejercicio == encargo.ejercicio,
                                                Materialidad.estado == "APROBADA").order_by(Materialidad.id.desc()))


def huella(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


def crear_run(db, encargo, usuario, tipo="COMPLETA", parametros=None) -> EjecucionAuditoria:
    numero = (db.scalar(select(func.max(EjecucionAuditoria.numero)).where(EjecucionAuditoria.engagement_id == encargo.id)) or 0) + 1
    run = EjecucionAuditoria(engagement_id=encargo.id, empresa_id=encargo.empresa_id, numero=numero, tipo=tipo,
                             parametros=json.dumps(parametros or {}, ensure_ascii=False), estado_proceso="EN_COLA", usuario=usuario,
                             version_datos=saldos.version_datos(db, encargo.empresa_id))
    db.add(run)
    db.flush()
    return run


def ejecutar(db, run_id: int, avance=lambda p, e: None) -> dict:
    run = db.get(EjecucionAuditoria, run_id)
    enc = db.get(EncargoAuditoria, run.engagement_id)
    t0 = time.perf_counter()
    run.estado_proceso = "PROCESANDO"
    db.commit()
    try:
        res = _ejecutar(db, run, enc, avance)
        run.estado_proceso, run.progreso, run.etapa = "COMPLETADO", 100, "Completado"
        run.duracion_ms = int((time.perf_counter() - t0) * 1000)
        run.finalizado_en = datetime.now()
        if enc.estado == "PLANIFICADO":
            enc.estado = "EN_EJECUCION"
        riesgo.registrar(db, enc.empresa_id, run.usuario, "EJECUCION_COMPLETADA", "ejecucion", run.id, run.resumen and json.loads(run.resumen).get("totales"),
                         engagement_id=enc.id, run_id=run.id)
        db.commit()
        return res
    except Cancelado:
        db.rollback()
        run = db.get(EjecucionAuditoria, run_id)
        run.estado_proceso, run.etapa, run.finalizado_en = "CANCELADO", "Cancelado por el usuario (los hallazgos ya consolidados se conservan)", datetime.now()
        run.duracion_ms = int((time.perf_counter() - t0) * 1000)
        db.commit()
        return {"run_id": run_id, "estado": "CANCELADO"}
    except Exception as exc:
        db.rollback()
        run = db.get(EjecucionAuditoria, run_id)
        run.estado_proceso, run.error, run.finalizado_en = "ERROR", str(exc)[:2000], datetime.now()
        run.intentos = (run.intentos or 0) + 1
        db.commit()
        raise


def _ejecutar(db, run, enc, avance) -> dict:
    params = json.loads(run.parametros or "{}")
    alcance = alcance_de(db, enc)
    if run.tipo == "CUENTA" and params.get("cuentas"):
        alcance["cuentas"] = params["cuentas"]
    mat_obj = materialidad_aprobada(db, enc)
    mat = riesgo.materialidad_dict(mat_obj)
    matriz = riesgo.matriz_vigente(db, enc.empresa_id)
    reglas = reglas_aplicables(db, enc, run.tipo, params, alcance)
    run.reglas_snapshot = json.dumps([snapshot_regla(r) for r in reglas], ensure_ascii=False)
    run.hash_reglas = huella(run.reglas_snapshot)
    run.materialidad_snapshot = json.dumps(mat, ensure_ascii=False) if mat else None
    db.commit()
    ax = Contexto(db, enc, alcance, mat, avance)
    previos = {}
    for rr in db.scalars(select(ResultadoRegla).join(EjecucionAuditoria, EjecucionAuditoria.id == ResultadoRegla.run_id)
                         .where(EjecucionAuditoria.engagement_id == enc.id, ResultadoRegla.estado.notin_(("ERROR", "REUTILIZADA")))
                         .order_by(ResultadoRegla.id)):
        previos[(rr.rule_id, rr.huella_entrada)] = rr
    existentes = {h.huella: h for h in db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == enc.id))}
    anteriores = _hallazgos_encargo_anterior(db, enc)
    n_codigo = db.scalar(select(func.count()).select_from(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == enc.id)) or 0
    tiempos, estados, vistos_run, reglas_evaluadas = {}, Counter(), set(), set()
    pob_total, pob_importe = 0, CERO
    entrada_base = json.dumps([run.version_datos, mat, alcance, enc.fecha_corte.isoformat()], default=str, sort_keys=True)
    for i, r in enumerate(reglas):
        if db.scalar(select(EjecucionAuditoria.cancelar).where(EjecucionAuditoria.id == run.id)):
            raise Cancelado()
        pct = 5 + int(85 * i / max(len(reglas), 1))
        run.progreso, run.etapa = pct, f"Regla {r.codigo}: {r.nombre}"[:160]
        avance(pct, run.etapa)
        modulo = catalogo.modulo_de(db, r)
        t = time.perf_counter()
        entrada = huella(entrada_base + json.dumps(snapshot_regla(r), sort_keys=True, default=str))
        rr = ResultadoRegla(run_id=run.id, rule_id=r.id, codigo=r.codigo, version=r.version, modulo=modulo, huella_entrada=entrada)
        if r.vigente_desde and r.vigente_desde > enc.fecha_corte or r.vigente_hasta and r.vigente_hasta < enc.fecha_corte:
            rr.estado, rr.mensaje = "FUERA_DE_VIGENCIA", f"Vigencia {r.vigente_desde or '…'} – {r.vigente_hasta or '…'}; corte {enc.fecha_corte}."
        elif r.normativa and r.estado_validacion != "VALIDADA":
            rr.estado, rr.mensaje = "NO_VALIDADA", "Regla normativa sin validación de su contenido y vigencia: no se ejecuta."
        elif (r.id, entrada) in previos and not params.get("forzar"):
            p = previos[(r.id, entrada)]
            rr.estado, rr.poblacion, rr.importe_poblacion, rr.excepciones = "REUTILIZADA", p.poblacion, p.importe_poblacion, p.excepciones
            rr.importe_excepciones, rr.metodo, rr.mensaje = p.importe_excepciones, p.metodo, f"Sin cambios en datos, regla ni materialidad (resultado #{p.id})."
            for h in existentes.values():
                if h.rule_id == r.id and h.vigente:
                    vistos_run.add(h.huella)
                    h.ultima_run_id = run.id
        else:
            try:
                fn = catalogo.EVALUADORES[r.evaluador or "configurable"]
                salida = fn(ax, Regla(r))
            except Exception as exc:  # una regla con error no detiene la auditoría (la evaluación solo lee datos)
                rr = ResultadoRegla(run_id=run.id, rule_id=r.id, codigo=r.codigo, version=r.version, modulo=modulo, huella_entrada=entrada,
                                    estado="ERROR", mensaje=f"{type(exc).__name__}: {exc}"[:1000])
                db.add(rr)
                estados["ERROR"] += 1
                db.commit()
                continue
            reglas_evaluadas.add(r.id)
            if salida.estado:
                rr.estado, rr.mensaje = salida.estado, salida.mensaje
            else:
                rr.estado = "CON_EXCEPCIONES" if salida.res else "SIN_EXCEPCIONES"
            rr.poblacion, rr.importe_poblacion, rr.metodo = salida.poblacion, salida.importe, salida.metodo
            rr.excepciones = len(salida.res)
            rr.importe_excepciones = sum((abs(x.importe or 0) for x in salida.res), CERO)
            with db.begin_nested():
                for x in salida.res:
                    n_codigo = _consolidar(db, run, enc, r, modulo, x, existentes, anteriores, mat, matriz, vistos_run, n_codigo)
        rr.duracion_ms = int((time.perf_counter() - t) * 1000)
        tiempos[r.codigo] = rr.duracion_ms
        estados[rr.estado] += 1
        pob_total += rr.poblacion or 0
        pob_importe += rr.importe_poblacion or CERO
        db.add(rr)
        db.flush()
        if i % 10 == 9:
            db.commit()
    # hallazgos de reglas evaluadas que ya no se reproducen: se conservan (no se ocultan ni eliminan) y se marcan
    for h in existentes.values():
        if h.rule_id in reglas_evaluadas and h.huella not in vistos_run and h.vigente:
            h.vigente = False
            db.add(RevisionAuditoria(empresa_id=enc.empresa_id, entidad="HALLAZGO", entidad_id=h.id, de_estado=h.estado, a_estado=h.estado,
                                     usuario="sistema", comentario=f"No se reproduce en la ejecución #{run.numero} (datos o regla modificados)."))
    db.flush()
    recalcular_grupos(db, enc.id)
    resumen = resumen_encargo(db, enc.id)
    resumen["ejecucion"] = {"reglas": len(reglas), "estados_reglas": dict(estados), "poblacion": pob_total, "importe_poblacion": str(pob_importe),
                            "cuentas_auditadas": len({ln.cuenta for ln in ax.lineas}) if "ctx3" in ax.__dict__ else 0,
                            "movimientos_evaluados": len(ax.lineas) if "ctx3" in ax.__dict__ else 0, "materialidad": mat}
    run.resumen = json.dumps(resumen, default=_j, ensure_ascii=False)
    run.tiempos = json.dumps(tiempos)
    db.flush()
    return {"run_id": run.id, "resumen": resumen}


def _hallazgos_encargo_anterior(db, enc) -> dict:
    """Hallazgos del encargo anterior de la empresa (mismo tipo) para identificar reincidencias."""
    prev = db.scalar(select(EncargoAuditoria).where(EncargoAuditoria.empresa_id == enc.empresa_id, EncargoAuditoria.tipo == enc.tipo,
                                                    EncargoAuditoria.fecha_corte < enc.fecha_corte).order_by(EncargoAuditoria.fecha_corte.desc()))
    if not prev:
        return {}
    return {h.huella: h for h in db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == prev.id))}


def _consolidar(db, run, enc, r, modulo, x, existentes, anteriores, mat, matriz, vistos_run, n_codigo) -> int:
    clave = x.clave or f"{r.codigo}|{x.titulo}"
    hu = huella(f"{enc.empresa_id}|{clave}")
    if hu in vistos_run:  # el mismo hecho detectado por otra regla en esta ejecución: no se duplica
        h = existentes.get(hu)
        if h and r.codigo not in (h.detalle or ""):
            det = json.loads(h.detalle or "{}")
            det.setdefault("otras_reglas", []).append(r.codigo)
            h.detalle = json.dumps(det, default=_j, ensure_ascii=False)
        return n_codigo
    vistos_run.add(hu)
    prev = anteriores.get(hu)
    ev = riesgo.evaluar(x, r, modulo, mat, matriz, reincidente=bool(prev))
    h = existentes.get(hu)
    if h:
        h.ultima_run_id, h.vigente = run.id, True
        if abs(h.importe - Decimal(x.importe or 0)) > Decimal("0.005"):
            db.add(EvidenciaHallazgo(finding_id=h.id, tipo="CALCULO", descripcion=f"Ejecución #{run.numero}: importe actualizado de {h.importe} a {x.importe}.",
                                     datos=json.dumps({"anterior": str(h.importe), "nuevo": str(x.importe)})))
            h.importe = Decimal(x.importe or 0)
        if not h.riesgo_ajustado_por:
            h.riesgo, h.riesgo_calculado, h.impacto, h.probabilidad, h.puntuacion = ev["riesgo"], ev["riesgo"], ev["impacto"], ev["probabilidad"], ev["puntuacion"]
        if h.estado in ("SUBSANADO", "VERIFICADO") or (h.estado == "CERRADO" and h.tipo == "SUBSANADO"):
            # subsanado pero vuelve a detectarse: reincidencia (los falsos positivos y justificados cerrados se respetan)
            db.add(RevisionAuditoria(empresa_id=enc.empresa_id, entidad="HALLAZGO", entidad_id=h.id, de_estado=h.estado, a_estado="REABIERTO",
                                     usuario="sistema", comentario=f"Reincidencia: se detecta nuevamente en la ejecución #{run.numero}."))
            h.estado, h.tipo, h.reincidencias = "REABIERTO", "POTENCIAL", h.reincidencias + 1
        return n_codigo
    n_codigo += 1
    h = HallazgoAuditoria(empresa_id=enc.empresa_id, engagement_id=enc.id, run_id=run.id, ultima_run_id=run.id, rule_id=r.id, regla_codigo=r.codigo,
                          regla_version=r.version, codigo=f"H-{enc.codigo}-{n_codigo:04d}", titulo=x.titulo[:255], periodo=enc.ejercicio * 100 + enc.periodo,
                          modulo=modulo, cuenta=(x.cuenta or None) and str(x.cuenta)[:20], tercero=(x.tercero or None) and str(x.tercero)[:20],
                          razon_social=(x.razon_social or None) and x.razon_social[:255], documento=(x.documento or None) and str(x.documento)[:80],
                          asiento=(x.asiento or None) and str(x.asiento)[:80], linea_id=x.linea_id, centro_costo=(x.centro_costo or None) and x.centro_costo[:30],
                          proyecto=(x.proyecto or None) and x.proyecto[:40], importe=Decimal(x.importe or 0).quantize(Decimal("0.01")),
                          impacto_potencial=x.impacto_potencial or _impacto_texto(x, ev), clave_exposicion=(x.exposicion or clave)[:200],
                          riesgo=ev["riesgo"], riesgo_calculado=ev["riesgo"], impacto=ev["impacto"], probabilidad=ev["probabilidad"],
                          puntuacion=ev["puntuacion"], sobre_materialidad=ev["sobre_materialidad"], claramente_insignificante=ev["claramente_insignificante"],
                          calidad_evidencia=x.calidad, estructural=bool(x.estructural if x.estructural is not None else r.estructural), condicion=x.condicion,
                          criterio=x.criterio or r.criterio, causa=x.causa, efecto=x.efecto, recomendacion=x.recomendacion or r.recomendacion,
                          tratamiento_tributario=x.tributario, tipo="POTENCIAL", estado="DETECTADO", regularizacion=x.regularizacion,
                          responsable=enc.responsable, fecha_deteccion=date.today(), reincidencias=(prev.reincidencias + 1) if prev else 0,
                          anterior_id=prev.id if prev else None, personal=x.personal, huella=hu,
                          detalle=json.dumps({**x.detalle, "clave": clave}, default=_j, ensure_ascii=False))
    db.add(h)
    db.flush()
    existentes[hu] = h
    for e in x.evidencia:
        db.add(EvidenciaHallazgo(finding_id=h.id, origen="SISTEMA", tipo=e["tipo"], tabla=e.get("tabla"), registro_id=e.get("id"),
                                 descripcion=e["descripcion"][:2000], datos=json.dumps(e.get("datos"), default=_j, ensure_ascii=False),
                                 confidencial=x.personal))
    if prev:
        db.add(EvidenciaHallazgo(finding_id=h.id, tipo="REINCIDENCIA", tabla="audit_findings", registro_id=prev.id,
                                 descripcion=f"Reincidencia del hallazgo {prev.codigo} del encargo anterior (estado {prev.estado})."))
    return n_codigo


def _impacto_texto(x, ev) -> str:
    base = f"Exposición potencial {x.importe}" if x.importe else "Sin exposición monetaria directa"
    if ev["sobre_materialidad"]:
        base += " (supera la materialidad de ejecución)"
    elif ev["claramente_insignificante"]:
        base += " (claramente insignificante: se mantiene visible por su naturaleza)"
    return base + ". Impacto potencial: requiere evaluación; no es un error confirmado."


def recalcular_grupos(db, engagement_id) -> None:
    hs = db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == engagement_id)).all()
    por = defaultdict(list)
    for h in hs:
        por[h.clave_exposicion].append(h)
    grupos = {g.clave: g for g in db.scalars(select(GrupoHallazgos).where(GrupoHallazgos.engagement_id == engagement_id))}
    for clave, xs in por.items():
        activos = [h for h in xs if h.tipo not in ("FALSO_POSITIVO",) and h.vigente]
        g = grupos.get(clave[:200])
        if not g:
            g = GrupoHallazgos(engagement_id=engagement_id, clave=clave[:200], titulo=xs[0].titulo[:255])
            db.add(g)
            db.flush()
        g.hallazgos = len(xs)
        g.exposicion = max((abs(h.importe) for h in activos), default=CERO)          # superpuestos: el mayor, no la suma
        g.exposicion_confirmada = max((abs(h.importe_confirmado if h.importe_confirmado is not None else h.importe) for h in activos
                                       if h.tipo == "CONFIRMADO" or h.estado in ("CONFIRMADO", "PENDIENTE_REGULARIZACION", "EN_SUBSANACION")), default=CERO)
        for h in xs:
            h.grupo_id = g.id
    db.flush()


def resumen_encargo(db, engagement_id) -> dict:
    hs = db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == engagement_id)).all()
    grupos = db.scalars(select(GrupoHallazgos).where(GrupoHallazgos.engagement_id == engagement_id)).all()
    vig = [h for h in hs if h.vigente and h.tipo != "FALSO_POSITIVO"]
    hoy = date.today()
    return {"totales": {"hallazgos": len(hs), "vigentes": len(vig), "confirmados": sum(1 for h in hs if h.tipo == "CONFIRMADO" or h.estado == "CONFIRMADO"),
                        "criticos": sum(1 for h in vig if h.riesgo == "CRITICO"), "altos": sum(1 for h in vig if h.riesgo == "ALTO"),
                        "pendientes": sum(1 for h in vig if h.estado not in ("CERRADO", "VERIFICADO", "SUBSANADO")),
                        "subsanados": sum(1 for h in hs if h.estado in ("SUBSANADO", "VERIFICADO") or h.tipo == "SUBSANADO"),
                        "falsos_positivos": sum(1 for h in hs if h.tipo == "FALSO_POSITIVO"),
                        "vencidos": sum(1 for h in vig if h.fecha_limite and h.fecha_limite < hoy and h.estado not in ("CERRADO", "VERIFICADO")),
                        "exposicion_potencial": str(sum((g.exposicion for g in grupos), CERO)),
                        "exposicion_confirmada": str(sum((g.exposicion_confirmada for g in grupos), CERO)),
                        "exposicion_bruta_sin_agrupar": str(sum((abs(h.importe) for h in vig), CERO)),
                        "grupos_exposicion": len(grupos)},
            "por_modulo": dict(Counter(h.modulo for h in vig)), "por_riesgo": dict(Counter(h.riesgo for h in vig)),
            "por_estado": dict(Counter(h.estado for h in hs)), "por_tipo": dict(Counter(h.tipo for h in hs))}

