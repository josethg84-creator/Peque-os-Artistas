"""Matriz de riesgos (impacto × probabilidad, 5 niveles), materialidad y bitácora protegida.

La puntuación (impacto × probabilidad) es una PRIORIZACIÓN INTERNA, no una probabilidad estadística validada. El impacto
se mide contra la materialidad aprobada; sin materialidad se usa el nivel de riesgo configurado en la regla. Los hallazgos
cualitativamente relevantes (estructurales o de módulos/reglas marcados como cualitativos) no bajan de impacto medio
aunque su importe sea pequeño. Los porcentajes de materialidad los define y aprueba el responsable de auditoría: no hay
porcentajes por defecto.
"""
import hashlib
import json
from decimal import Decimal

from sqlalchemy import select

from app.analisis import saldos
from app.models import EventoAuditoria, Materialidad, MatrizRiesgo

NIVELES = ("INFORMATIVO", "BAJO", "MEDIO", "ALTO", "CRITICO")
BASE_IMPACTO = {"INFORMATIVO": 1, "BAJO": 2, "MEDIO": 3, "ALTO": 4, "CRITICO": 5}
# matriz por defecto: [impacto 1..5][probabilidad 1..5] → nivel (editable por empresa)
MATRIZ = [["INFORMATIVO", "INFORMATIVO", "BAJO", "BAJO", "BAJO"],
          ["INFORMATIVO", "BAJO", "BAJO", "MEDIO", "MEDIO"],
          ["BAJO", "BAJO", "MEDIO", "MEDIO", "ALTO"],
          ["BAJO", "MEDIO", "ALTO", "ALTO", "CRITICO"],
          ["MEDIO", "ALTO", "ALTO", "CRITICO", "CRITICO"]]
FACTORES = {"recurrencia": 1, "evidencia_parcial": -1, "evidencia_insuficiente": -1, "controles": "NO_EVALUADOS",
            "ajuste_controles": {"EFECTIVOS": -1, "NO_EVALUADOS": 0, "INEFECTIVOS": 1}}


def matriz_vigente(db, empresa_id):
    m = db.scalar(select(MatrizRiesgo).where(MatrizRiesgo.empresa_id == empresa_id, MatrizRiesgo.activa.is_(True)).order_by(MatrizRiesgo.version.desc()))
    if m:
        return {"id": m.id, "version": m.version, "matriz": json.loads(m.matriz), "factores": {**FACTORES, **json.loads(m.factores or "{}")}}
    return {"id": None, "version": 0, "matriz": MATRIZ, "factores": FACTORES}


def validar_matriz(matriz) -> None:
    if not isinstance(matriz, list) or len(matriz) != 5 or any(not isinstance(f, list) or len(f) != 5 or any(x not in NIVELES for x in f) for f in matriz):
        raise ValueError("La matriz debe ser de 5 × 5 con niveles CRITICO, ALTO, MEDIO, BAJO o INFORMATIVO.")


def impacto(importe: Decimal, mat: dict | None, riesgo_regla: str, cualitativo: bool) -> int:
    if not mat:
        i = BASE_IMPACTO.get(riesgo_regla, 3)
    else:
        imp = abs(Decimal(importe or 0))
        g, e, ins = Decimal(mat["materialidad_global"]), Decimal(mat["materialidad_ejecucion"]), Decimal(mat["umbral_insignificante"])
        i = 5 if imp >= g else 4 if imp >= e else 3 if imp >= e / 2 else 2 if imp > ins else 1
    return max(i, 3) if cualitativo else i


def evaluar(res, regla, modulo: str, mat: dict | None, matriz: dict, reincidente: bool) -> dict:
    cualitativo = bool(res.estructural if res.estructural is not None else regla.estructural)
    if mat:
        cual = mat.get("cualitativos") or {}
        cualitativo |= regla.codigo in cual.get("reglas", []) or modulo in cual.get("modulos", [])
    i = res.impacto_forzado or impacto(res.importe, mat, regla.riesgo, cualitativo)
    f = matriz["factores"]
    p = res.probabilidad or regla.probabilidad or 3
    if reincidente:
        p += int(f.get("recurrencia", 1))
    if res.calidad == "PARCIAL":
        p += int(f.get("evidencia_parcial", -1))
    elif res.calidad == "INSUFICIENTE":
        p += int(f.get("evidencia_insuficiente", -1))
    p += int(f.get("ajuste_controles", {}).get(f.get("controles", "NO_EVALUADOS"), 0))
    p = min(max(p, 1), 5)
    nivel = matriz["matriz"][i - 1][p - 1]
    if res.riesgo_minimo == "INFORMATIVO":  # herramientas exploratorias: solo informativas
        nivel = "INFORMATIVO"
    elif res.riesgo_minimo:
        nivel = max(nivel, res.riesgo_minimo, key=NIVELES.index)
    return {"impacto": i, "probabilidad": p, "puntuacion": i * p, "riesgo": nivel,
            "sobre_materialidad": bool(mat and abs(Decimal(res.importe or 0)) >= Decimal(mat["materialidad_ejecucion"])),
            "claramente_insignificante": bool(mat and abs(Decimal(res.importe or 0)) <= Decimal(mat["umbral_insignificante"]))}


# ------------------------------------------------------------------ materialidad
BASES = ("INGRESOS", "ACTIVOS", "PATRIMONIO", "RESULTADO_ANTES_IMPUESTOS", "GASTOS", "OTRA")


def importe_base(db, empresa_id, ejercicio, periodo, base) -> Decimal:
    f = saldos.fuentes(db, empresa_id, ejercicio)
    hojas = saldos.saldos_hoja(db, f, 1, periodo)
    sf = {c: h.si + h.debe - h.haber for c, h in hojas.items()}
    mov = {c: h.debe - h.haber for c, h in hojas.items()}
    d = saldos.dec
    if base == "INGRESOS":
        return d(-sum(v for c, v in mov.items() if c[:2] in ("70", "71", "72", "73", "74", "75", "76", "77")))
    if base == "ACTIVOS":
        return d(sum(v for c, v in sf.items() if c[:1] in "123"))
    if base == "PATRIMONIO":
        return d(-sum(v for c, v in sf.items() if c[:1] == "5"))
    if base == "GASTOS":
        return d(sum(v for c, v in mov.items() if c[:1] == "6" and not c.startswith(("69",))))
    if base == "RESULTADO_ANTES_IMPUESTOS":
        return d(-sum(v for c, v in mov.items() if c[:1] in "67" and not c.startswith(("88", "79", "78"))))
    raise ValueError("Para otra base indique el importe base manualmente.")


def materialidad_dict(m: Materialidad | None) -> dict | None:
    if not m:
        return None
    return {"id": m.id, "base": m.base, "importe_base": str(m.importe_base), "materialidad_global": str(m.materialidad_global),
            "materialidad_ejecucion": str(m.materialidad_ejecucion), "umbral_insignificante": str(m.umbral_insignificante),
            "por_cuenta": json.loads(m.por_cuenta or "{}"), "por_tipo": json.loads(m.por_tipo or "{}"), "cualitativos": json.loads(m.cualitativos or "{}"),
            "aprobado_por": m.aprobado_por, "estado": m.estado}


# ------------------------------------------------------------------ bitácora encadenada
def registrar(db, empresa_id, usuario, accion, entidad, entidad_id=None, detalle=None, rol=None, engagement_id=None, run_id=None) -> None:
    previo = db.scalar(select(EventoAuditoria.hash).where(EventoAuditoria.empresa_id == empresa_id).order_by(EventoAuditoria.id.desc()).limit(1))
    det = json.dumps(detalle, default=str, ensure_ascii=False, sort_keys=True) if detalle is not None else None
    base = f"{previo}|{empresa_id}|{usuario}|{rol}|{accion}|{entidad}|{entidad_id}|{engagement_id}|{run_id}|{det}"
    db.add(EventoAuditoria(empresa_id=empresa_id, usuario=usuario or "sistema", rol=rol, accion=accion, entidad=entidad, entidad_id=entidad_id,
                           engagement_id=engagement_id, run_id=run_id, detalle=det, hash_anterior=previo, hash=hashlib.sha256(base.encode()).hexdigest()))
    db.flush()


def verificar_bitacora(db, empresa_id) -> dict:
    previo, n = None, 0
    for e in db.scalars(select(EventoAuditoria).where(EventoAuditoria.empresa_id == empresa_id).order_by(EventoAuditoria.id)):
        base = f"{previo}|{e.empresa_id}|{e.usuario}|{e.rol}|{e.accion}|{e.entidad}|{e.entidad_id}|{e.engagement_id}|{e.run_id}|{e.detalle}"
        if e.hash_anterior != previo or hashlib.sha256(base.encode()).hexdigest() != e.hash:
            return {"integra": False, "eventos": n, "primer_evento_alterado": e.id}
        previo, n = e.hash, n + 1
    return {"integra": True, "eventos": n, "ultimo_hash": previo}
