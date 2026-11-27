"""Muestras de auditoría y papeles de trabajo preliminares.

Muestras: aleatoria (semilla reproducible), por importe, por riesgo, por antigüedad, por tercero, por cuenta y estratificada
(aleatoria dentro de cada estrato). Solo la aleatoria y la estratificada se marcan como estadísticamente representativas;
las dirigidas (importe, riesgo, antigüedad…) NO representan a toda la población y así se indica.
Papeles de trabajo: objetivo, alcance, población, fuente, corte, regla, procedimiento, resultados, excepciones, evidencias,
conclusión preliminar, elaboración y revisión. Su contenido es JSON estable, preparado para el módulo de informes (fase 13).
"""
import json
import random
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.auditoria.base import CERO, Contexto, asiento_de, doc_de
from app.auditoria.motor import alcance_de
from app.auditoria.servicio import ErrorAuditoria, SinPermiso, _hist, cargar_encargo, evento, exigir
from app.models import (AprobacionAuditoria, EjecucionAuditoria, EvidenciaHallazgo, HallazgoAuditoria, ItemMuestra, MuestraAuditoria, PapelAuditoria,
                        ReglaAuditoria, ResultadoRegla)

METODOS = ("ALEATORIA", "IMPORTE", "RIESGO", "ANTIGUEDAD", "TERCERO", "CUENTA", "ESTRATIFICADA")


def _poblacion(db, e, tipo, crit):
    if tipo == "HALLAZGOS":
        hs = db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == e.id, HallazgoAuditoria.vigente.is_(True))).all()
        return [{"tabla": "audit_findings", "id": h.id, "importe": abs(h.importe), "fecha": h.fecha_deteccion, "tercero": h.tercero, "cuenta": h.cuenta,
                 "riesgo": h.puntuacion, "descripcion": f"{h.codigo} {h.titulo}"[:255]} for h in hs]
    if tipo != "LINEAS":
        raise ErrorAuditoria("Población no válida: LINEAS o HALLAZGOS.")
    ax = Contexto(db, e, alcance_de(db, e), None)
    pref = crit.get("cuentas")
    return [{"tabla": "lineas_diario", "id": ln.id, "importe": ln.debe + ln.haber, "fecha": ln.fecha, "tercero": ln.tercero, "cuenta": ln.cuenta, "riesgo": 0,
             "descripcion": f"{asiento_de(ln) or ''} {ln.cuenta} {doc_de(ln) or ''} {ln.glosa or ''}"[:255]}
            for ln in ax.lineas if ln.id and (ln.debe or ln.haber) and (not pref or ln.cuenta.startswith(tuple(pref)))]


def crear_muestra(db, empresa_id, eid, usuario, d: dict) -> MuestraAuditoria:
    r = exigir(db, empresa_id, usuario, "revisar")
    e = cargar_encargo(db, empresa_id, eid, usuario)
    metodo = d.get("metodo")
    if metodo not in METODOS:
        raise ErrorAuditoria(f"Método no válido: {', '.join(METODOS)}.")
    crit = d.get("criterios") or {}
    pob = _poblacion(db, e, d.get("poblacion", "LINEAS"), crit)
    if metodo == "RIESGO" and d.get("poblacion", "LINEAS") != "HALLAZGOS":
        raise ErrorAuditoria("La selección por riesgo se aplica a la población de hallazgos.")
    n = int(d.get("tamano") or 0)
    if n <= 0:
        raise ErrorAuditoria("Indique el tamaño de la muestra.")
    if crit.get("importe_minimo"):
        pob = [x for x in pob if x["importe"] >= Decimal(str(crit["importe_minimo"]))]
    semilla = None
    estratos = {}
    if metodo == "ALEATORIA":
        semilla = int(d.get("semilla") or random.SystemRandom().randrange(1, 2 ** 31))
        sel = random.Random(semilla).sample(sorted(pob, key=lambda x: (x["tabla"], x["id"])), min(n, len(pob)))
    elif metodo == "IMPORTE":
        sel = sorted(pob, key=lambda x: (-x["importe"], x["id"]))[:n]
    elif metodo == "RIESGO":
        sel = sorted(pob, key=lambda x: (-x["riesgo"], -x["importe"], x["id"]))[:n]
    elif metodo == "ANTIGUEDAD":
        sel = sorted([x for x in pob if x["fecha"]], key=lambda x: (x["fecha"], x["id"]))[:n]
    elif metodo == "TERCERO":
        if not crit.get("tercero"):
            raise ErrorAuditoria("Indique el tercero.")
        sel = sorted([x for x in pob if x["tercero"] == crit["tercero"]], key=lambda x: (-x["importe"], x["id"]))[:n]
    elif metodo == "CUENTA":
        if not crit.get("cuenta"):
            raise ErrorAuditoria("Indique la cuenta.")
        sel = sorted([x for x in pob if (x["cuenta"] or "").startswith(crit["cuenta"])], key=lambda x: (-x["importe"], x["id"]))[:n]
    else:  # ESTRATIFICADA: estratos por importe, aleatoria dentro de cada uno
        limites = sorted(Decimal(str(v)) for v in (crit.get("limites") or []))
        if not limites:
            raise ErrorAuditoria("Indique los límites de los estratos (importes).")
        semilla = int(d.get("semilla") or random.SystemRandom().randrange(1, 2 ** 31))
        rnd = random.Random(semilla)
        por = {}
        for x in sorted(pob, key=lambda x: (x["tabla"], x["id"])):
            i = sum(1 for lim in limites if x["importe"] >= lim)
            por.setdefault(i, []).append(x)
        total = len(pob) or 1
        sel = []
        for i, xs in sorted(por.items()):
            k = max(1, round(n * len(xs) / total)) if xs else 0
            elegidos = rnd.sample(xs, min(k, len(xs)))
            nombre = f"≥ {limites[i - 1]}" if i else f"< {limites[0]}"
            estratos[nombre] = {"poblacion": len(xs), "muestra": len(elegidos)}
            for x in elegidos:
                x["estrato"] = nombre
            sel += elegidos
    representativa = metodo in ("ALEATORIA", "ESTRATIFICADA")
    m = MuestraAuditoria(engagement_id=e.id, workpaper_id=d.get("workpaper_id"), nombre=(d.get("nombre") or f"Muestra {metodo.lower()}")[:160],
                         poblacion=d.get("poblacion", "LINEAS"), metodo=metodo, criterios=json.dumps({**crit, "estratos": estratos}, default=str),
                         semilla=semilla, poblacion_cantidad=len(pob), poblacion_importe=sum((x["importe"] for x in pob), CERO), tamano=len(sel),
                         estadisticamente_representativa=representativa, usuario=usuario,
                         nota=None if representativa else "Muestra dirigida (selección por criterio): no es estadísticamente representativa de toda "
                                                          "la población; sus resultados no se extrapolan.")
    db.add(m)
    db.flush()
    for x in sel:
        db.add(ItemMuestra(sample_id=m.id, tabla=x["tabla"], registro_id=x["id"], descripcion=x["descripcion"], importe=x["importe"], estrato=x.get("estrato"),
                           resultado="PENDIENTE"))
    evento(db, empresa_id, usuario, "CREAR_MUESTRA", "muestra", m.id, {"metodo": metodo, "semilla": semilla, "tamano": len(sel), "criterios": crit}, r, e.id)
    db.commit()
    return m


def evaluar_item(db, empresa_id, usuario, item_id, resultado, comentario=None) -> ItemMuestra:
    it = db.get(ItemMuestra, item_id)
    if not it:
        raise LookupError("Elemento de muestra no encontrado")
    m = db.get(MuestraAuditoria, it.sample_id)
    e = cargar_encargo(db, empresa_id, m.engagement_id, usuario)
    r = exigir(db, empresa_id, usuario, "revisar")
    if resultado not in ("CONFORME", "EXCEPCION", "PENDIENTE"):
        raise ErrorAuditoria("Resultado no válido.")
    it.resultado, it.comentario = resultado, comentario
    evento(db, empresa_id, usuario, "EVALUAR_MUESTRA", "muestra_item", it.id, {"resultado": resultado}, r, e.id)
    db.commit()
    return it


def generar_papel(db, empresa_id, eid, usuario, codigo_regla: str) -> PapelAuditoria:
    r_ = exigir(db, empresa_id, usuario, "ejecutar")
    e = cargar_encargo(db, empresa_id, eid, usuario)
    rr = db.scalar(select(ResultadoRegla).join(EjecucionAuditoria, EjecucionAuditoria.id == ResultadoRegla.run_id)
                   .where(EjecucionAuditoria.engagement_id == e.id, ResultadoRegla.codigo == codigo_regla).order_by(ResultadoRegla.id.desc()))
    if not rr:
        raise ErrorAuditoria("La regla no se ha ejecutado en este encargo.")
    if rr.estado == "REUTILIZADA":
        rr = db.scalar(select(ResultadoRegla).join(EjecucionAuditoria, EjecucionAuditoria.id == ResultadoRegla.run_id)
                       .where(EjecucionAuditoria.engagement_id == e.id, ResultadoRegla.codigo == codigo_regla,
                              ResultadoRegla.estado != "REUTILIZADA").order_by(ResultadoRegla.id.desc())) or rr
    regla = db.get(ReglaAuditoria, rr.rule_id)
    run = db.get(EjecucionAuditoria, rr.run_id)
    hs = db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id == e.id, HallazgoAuditoria.rule_id == regla.id)
                    .order_by(HallazgoAuditoria.puntuacion.desc(), HallazgoAuditoria.id)).all()
    n_ev = db.scalar(select(func.count()).select_from(EvidenciaHallazgo).where(EvidenciaHallazgo.finding_id.in_([h.id for h in hs] or [0]))) or 0
    muestras = db.scalars(select(MuestraAuditoria).where(MuestraAuditoria.engagement_id == e.id)).all()
    excep = [h for h in hs if h.tipo != "FALSO_POSITIVO"]
    conclusion = ("Sin excepciones en la población evaluada." if rr.estado == "SIN_EXCEPCIONES" else
                  f"Procedimiento no ejecutado: {rr.mensaje}" if rr.estado in ("NO_VALIDADA", "FUERA_DE_VIGENCIA", "SIN_DATOS", "PENDIENTE_EVALUACION", "ERROR") else
                  f"Se identificaron {len(excep)} excepciones potenciales por {sum((abs(h.importe) for h in excep), CERO)}, pendientes de revisión profesional "
                  "(conclusión preliminar).")
    contenido = {
        "objetivo": regla.descripcion or regla.nombre, "criterio": regla.criterio, "alcance": {"encargo": e.nombre, "corte": e.fecha_corte.isoformat(),
                                                                                                 "alcance": alcance_de(db, e)},
        "poblacion": {"registros": rr.poblacion, "importe": str(rr.importe_poblacion)}, "fuente": rr.metodo, "fecha_corte": e.fecha_corte.isoformat(),
        "regla": {"codigo": regla.codigo, "nombre": regla.nombre, "version": rr.version, "modulo": rr.modulo},
        "procedimiento": rr.metodo, "ejecucion": {"run": run.numero, "fecha": run.creado_en.isoformat() if run.creado_en else None, "usuario": run.usuario,
                                                  "estado": rr.estado, "duracion_ms": rr.duracion_ms, "version_datos": run.version_datos},
        "resultados": {"excepciones": len(excep), "importe_excepciones": str(sum((abs(h.importe) for h in excep), CERO)),
                       "falsos_positivos": sum(1 for h in hs if h.tipo == "FALSO_POSITIVO")},
        "excepciones": [{"codigo": h.codigo, "titulo": h.titulo, "cuenta": h.cuenta, "documento": h.documento, "asiento": h.asiento, "linea_id": h.linea_id,
                         "importe": str(h.importe), "riesgo": h.riesgo, "estado": h.estado} for h in excep[:300]],
        "evidencias": {"registros": n_ev, "nota": "Cada hallazgo conserva sus referencias a los registros originales (tabla e id)."},
        "muestras": [{"id": m.id, "metodo": m.metodo, "semilla": m.semilla, "tamano": m.tamano, "representativa": m.estadisticamente_representativa,
                      "nota": m.nota} for m in muestras],
        "conclusion_preliminar": conclusion,
        "integracion": {"fase_13": "papel de trabajo preliminar exportable", "formato": "audit_workpaper/v1"}}
    n = (db.scalar(select(func.count()).select_from(PapelAuditoria).where(PapelAuditoria.engagement_id == e.id)) or 0) + 1
    p = PapelAuditoria(engagement_id=e.id, run_id=run.id, rule_id=regla.id, referencia=f"PT-{regla.codigo}-{n:02d}", titulo=f"{regla.codigo} · {regla.nombre}"[:255],
                       contenido=json.dumps(contenido, ensure_ascii=False, default=str), conclusion=conclusion, elaborado_por=usuario)
    db.add(p)
    db.flush()
    evento(db, empresa_id, usuario, "GENERAR_PAPEL", "papel", p.id, {"regla": regla.codigo, "run": run.numero}, r_, e.id)
    db.commit()
    return p


def cambiar_estado_papel(db, empresa_id, pid, usuario, estado, conclusion=None) -> PapelAuditoria:
    p = db.get(PapelAuditoria, pid)
    if not p:
        raise LookupError("Papel de trabajo no encontrado")
    e = cargar_encargo(db, empresa_id, p.engagement_id, usuario)
    trans = {"EN_REVISION": ("ejecutar", {"PRELIMINAR"}), "REVISADO": ("revisar", {"EN_REVISION"}), "APROBADO": ("aprobar", {"REVISADO"}),
             "PRELIMINAR": ("revisar", {"EN_REVISION", "REVISADO"})}
    if estado not in trans:
        raise ErrorAuditoria("Estado no válido.")
    r = exigir(db, empresa_id, usuario, trans[estado][0])
    if p.estado not in trans[estado][1]:
        raise ErrorAuditoria(f"No se puede pasar de {p.estado} a {estado}.")
    if estado == "REVISADO":
        if usuario.lower() == p.elaborado_por.lower():
            raise SinPermiso("Separación de funciones: quien elabora el papel no lo revisa.")
        p.revisado_por, p.revisado_en = usuario, datetime.now()
    if conclusion:
        p.conclusion = conclusion
        c = json.loads(p.contenido)
        c["conclusion_preliminar"] = conclusion
        p.contenido = json.dumps(c, ensure_ascii=False)
        p.version += 1
    previo = p.estado
    p.estado = estado
    if estado == "APROBADO":
        db.add(AprobacionAuditoria(empresa_id=empresa_id, entidad="PAPEL", entidad_id=p.id, accion="APROBAR", usuario=usuario, rol=r))
    _hist(db, empresa_id, "PAPEL", p.id, usuario, r, previo, estado, conclusion)
    evento(db, empresa_id, usuario, f"PAPEL_{estado}", "papel", p.id, None, r, e.id)
    db.commit()
    return p
