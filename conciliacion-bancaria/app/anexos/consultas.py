"""Consultas del centro de anexos: explorador jerárquico de cuentas y dashboard del cierre."""
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analisis import saldos
from app.anexos import catalogo
from app.anexos.exportar import ESTADOS, RESULTADOS
from app.models import Anexo, DetalleAnexo, HallazgoAnexo, PlantillaAnexo

CERO = Decimal("0")
APROBADOS = ("APROBADO", "CERRADO")


def _permitida(cuenta: str, permitidas: list[str] | None) -> bool:
    return permitidas is None or any(cuenta.startswith(p) or p.startswith(cuenta) for p in permitidas)


def sin_duplicar(anexos: list[Anexo]) -> list[Anexo]:
    """Evita sumar una cuenta y sus subcuentas: se conserva la cuenta de mayor nivel presente."""
    codigos = {a.cuenta for a in anexos}
    return [a for a in anexos if not any(o != a.cuenta and a.cuenta.startswith(o) for o in codigos)]


def anexos_al_corte(db: Session, empresa_id: int, corte: date, permitidas=None) -> list[Anexo]:
    lst = db.scalars(select(Anexo).where(Anexo.empresa_id == empresa_id, Anexo.fecha_corte == corte, Anexo.version_id.is_not(None))
                     .order_by(Anexo.cuenta)).all()
    return [a for a in lst if _permitida(a.cuenta, permitidas)]


def explorador(db: Session, empresa_id: int, ejercicio: int, periodo: int, corte: date, permitidas=None) -> dict:
    catalogo.sembrar(db)
    bal = saldos.balance(db, empresa_id, ejercicio, 1, min(periodo, 13), comparar=False)
    anexos = defaultdict(list)
    for a in anexos_al_corte(db, empresa_id, corte, permitidas):
        anexos[a.cuenta].append(a)
    candidatas = db.scalars(select(PlantillaAnexo).where(PlantillaAnexo.activa.is_(True), PlantillaAnexo.filtros.is_(None),
                                                         (PlantillaAnexo.empresa_id.is_(None)) | (PlantillaAnexo.empresa_id == empresa_id))).all()

    def sugerida(c):
        mejor, largo = None, -1
        for p in candidatas:
            if p.tipo == "PERSONALIZADA":
                continue
            for pref in [x.strip() for x in (p.cuentas or "").split(",")] or [""]:
                if c.startswith(pref) and (len(pref) > largo or (len(pref) == largo and p.empresa_id)):
                    mejor, largo = p, len(pref)
        return mejor
    nodos = []
    for n in bal["nodos"]:
        if not _permitida(n["cuenta"], permitidas):
            continue
        p = sugerida(n["cuenta"])
        lst = anexos.get(n["cuenta"], [])
        a = max(lst, key=lambda x: x.id) if lst else None
        nodos.append({**{k: n[k] for k in ("cuenta", "padre", "nivel", "descripcion", "naturaleza", "saldo_inicial", "debe", "haber",
                                           "saldo_final", "movimientos", "tiene_hijos", "movimiento_propio")},
                      "plantilla": {"id": p.id, "codigo": p.codigo, "nombre": p.nombre, "especialidad": p.especialidad} if p else None,
                      "anexo": {"id": a.id, "estado": a.estado_revision, "resultado": a.resultado, "diferencia": str(a.diferencia),
                                "version": a.version_actual, "observaciones": a.observaciones_abiertas,
                                "responsable": a.responsable_elaboracion} if a else None,
                      "anexos": len(lst)})
    return {"ejercicio": ejercicio, "periodo": periodo, "fecha_corte": corte.isoformat(), "advertencias": bal["advertencias"],
            "preliminar": bal["preliminar"], "nodos": nodos}


def dashboard(db: Session, empresa_id: int, ejercicio: int, periodo: int, corte: date, permitidas=None) -> dict:
    bal = saldos.balance(db, empresa_id, ejercicio, 1, min(periodo, 13), comparar=False)
    sujetas = [n["cuenta"] for n in bal["nodos"] if not n["tiene_hijos"] and (Decimal(n["saldo_final"]) or n["movimientos"])
               and _permitida(n["cuenta"], permitidas)]
    anexos = anexos_al_corte(db, empresa_id, corte, permitidas)
    cubiertas = {c for c in sujetas if any(c.startswith(a.cuenta) for a in anexos)}
    unicos = sin_duplicar(anexos)
    res = Counter(a.resultado for a in anexos)
    est = Counter(a.estado_revision for a in anexos)
    aprobados = sum(est[x] for x in APROBADOS)
    hoy = date.today()
    pendientes_resp = defaultdict(lambda: {"pendientes": 0, "vencidos": 0, "anexos": []})
    for a in anexos:
        if a.estado_revision in APROBADOS:
            continue
        quien = (a.responsable_revision if a.estado_revision in ("EN_REVISION", "SUBSANADO") else
                 a.responsable_aprobacion if a.estado_revision == "REVISADO" else a.responsable_elaboracion) or "(sin asignar)"
        x = pendientes_resp[quien]
        x["pendientes"] += 1
        x["vencidos"] += 1 if a.fecha_limite and a.fecha_limite < hoy else 0
        if len(x["anexos"]) < 20:
            x["anexos"].append({"id": a.id, "cuenta": a.cuenta, "estado": a.estado_revision, "fecha_limite": a.fecha_limite.isoformat() if a.fecha_limite else None})
    por_elemento = defaultdict(lambda: {"aprobados": 0, "en_proceso": 0, "sin_generar": 0})
    for a in anexos:
        el = a.elemento
        por_elemento[el]["aprobados" if a.estado_revision in APROBADOS else "en_proceso"] += 1
    for c in sujetas:
        if c not in cubiertas:
            por_elemento[c[:1]]["sin_generar"] += 1
    difs = sorted((a for a in unicos if a.diferencia), key=lambda a: -abs(a.diferencia))[:12]
    # evolución por fecha de corte (últimos 12 cortes con anexos)
    evol = []
    cortes = [c for (c,) in db.execute(select(Anexo.fecha_corte).where(Anexo.empresa_id == empresa_id, Anexo.version_id.is_not(None))
                                       .group_by(Anexo.fecha_corte).order_by(Anexo.fecha_corte.desc()).limit(12))]
    for c in sorted(cortes):
        lst = anexos_al_corte(db, empresa_id, c, permitidas)
        u = sin_duplicar(lst)
        evol.append({"fecha_corte": c.isoformat(), "anexos": len(lst), "aprobados": sum(1 for a in lst if a.estado_revision in APROBADOS),
                     "diferencia": str(sum((abs(a.diferencia) for a in u), CERO)),
                     "descuadrados": sum(1 for a in lst if a.resultado == "DESCUADRADO")})
    # antigüedad de los saldos de cartera (versiones vigentes, sin duplicar cuentas)
    carteras = [a.version_id for a in unicos if a.especialidad in ("CARTERA", "PERSONAL")]
    antig = defaultdict(lambda: CERO)
    for k in range(0, len(carteras), 500):
        for tramo, s in db.execute(select(DetalleAnexo.tramo, func.sum(DetalleAnexo.saldo)).where(DetalleAnexo.version_id.in_(carteras[k:k + 500]))
                                   .group_by(DetalleAnexo.tramo)):
            antig[tramo or "—"] += s or CERO
    obs = defaultdict(int)
    ids = [a.id for a in anexos]
    resp_anexo = {a.id: a.responsable_elaboracion for a in anexos}
    for k in range(0, len(ids), 500):
        for aid, resp, n in db.execute(select(HallazgoAnexo.anexo_id, HallazgoAnexo.responsable, func.count())
                                       .where(HallazgoAnexo.anexo_id.in_(ids[k:k + 500]), HallazgoAnexo.estado == "ABIERTO",
                                              HallazgoAnexo.severidad != "INFORMATIVA")
                                       .group_by(HallazgoAnexo.anexo_id, HallazgoAnexo.responsable)):
            obs[resp or resp_anexo.get(aid) or "(sin asignar)"] += n
    return {
        "fecha_corte": corte.isoformat(), "ejercicio": ejercicio, "periodo": periodo,
        "kpi": {"cuentas_sujetas": len(sujetas), "anexos_generados": len(anexos), "cuentas_sin_anexo": len(sujetas) - len(cubiertas),
                "cuadrados": res["CUADRADO"], "cuadrados_con_observaciones": res["CUADRADO_CON_OBSERVACIONES"],
                "descuadrados": res["DESCUADRADO"], "parcialmente_sustentados": res["PARCIALMENTE_SUSTENTADO"],
                "informacion_insuficiente": res["INFORMACION_INSUFICIENTE"], "observados": est["OBSERVADO"], "aprobados": aprobados,
                "avance_cierre": round(100 * aprobados / len(anexos), 1) if anexos else 0.0,
                "diferencia_total": str(sum((abs(a.diferencia) for a in unicos), CERO)),
                "pendiente_sustento_total": str(sum((a.saldo_pendiente_sustento for a in unicos), CERO))},
        "nota_duplicados": "Los importes agregados consideran solo la cuenta de mayor nivel cuando existen anexos de una cuenta y de sus subcuentas.",
        "graficos": {
            "avance_elemento": [{"elemento": e, **v} for e, v in sorted(por_elemento.items())],
            "estado_revision": [{"estado": k, "nombre": ESTADOS.get(k, k), "cantidad": est[k]} for k in ESTADOS if est[k]],
            "resultado": [{"resultado": k, "nombre": RESULTADOS[k], "cantidad": res[k]} for k in RESULTADOS if res[k]],
            "diferencias": [{"anexo_id": a.id, "cuenta": a.cuenta, "descripcion": a.descripcion, "diferencia": str(a.diferencia)} for a in difs],
            "evolucion": evol,
            "antiguedad": [{"tramo": t, "saldo": str(v)} for t, v in antig.items()],
            "observaciones_responsable": [{"responsable": r, "cantidad": n} for r, n in sorted(obs.items(), key=lambda x: -x[1])],
        },
        "pendientes_responsable": [{"responsable": r, **v} for r, v in sorted(pendientes_resp.items(), key=lambda x: -x[1]["pendientes"])],
    }
