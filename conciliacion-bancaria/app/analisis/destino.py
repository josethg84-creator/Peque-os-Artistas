"""Análisis de origen y destino: gastos por naturaleza (clase 6), cargas imputables (79), destino
(clase 9 u otro configurado) y cargas cubiertas por provisiones (78).

No se asume que toda la clase 6 deba coincidir con la clase 9: solo se comparan las cuentas
sujetas a distribución según la política de la empresa (prefijos destinables de la configuración
contable, menos las cuentas excluidas por reglas). El destino esperado se obtiene, en este orden:
  1. reglas de distribución vigentes (cuenta + centro de costo/proyecto/unidad/maquinaria + %),
  2. el destino definido en el plan de cuentas de la cuenta de origen (100 %),
  3. la cuenta de destino del centro de costo (100 %).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CentroCosto, ConfiguracionContable, CuentaContable, ReglaDistribucion

CERO = Decimal("0")
CIEN = Decimal("100")


def _lista(t):
    return [p.strip() for p in (t or "").split(",") if p.strip()]


def _empieza(c, prefijos):
    return bool(c) and any(c.startswith(p) for p in prefijos)


@dataclass
class Politica:
    usa_destino: bool
    modo: str
    destinables: list[str]
    destino: list[str]
    cargas: str
    exigir_cc: bool
    validar_78: bool
    tolerancia: Decimal


def politica(db: Session, empresa_id: int) -> Politica:
    cfg = db.scalar(select(ConfiguracionContable).where(ConfiguracionContable.empresa_id == empresa_id)) \
        or ConfiguracionContable(empresa_id=empresa_id)
    return Politica(cfg.usa_clase_9 if cfg.usa_clase_9 is not None else True, cfg.modo_destino or "MISMO_ASIENTO",
                    _lista(cfg.prefijos_destinables if cfg.prefijos_destinables is not None else "62,63,64,65,66,67,68"),
                    _lista(cfg.prefijo_destino) or ["9"], cfg.cuenta_cargas_imputables or "79",
                    bool(cfg.exigir_centro_costo_destino), cfg.validar_cuenta_78 if cfg.validar_cuenta_78 is not None else True,
                    Decimal(str(cfg.tolerancia_descuadre if cfg.tolerancia_descuadre is not None else "0.01")))


def reglas_vigentes(db: Session, empresa_id: int, fecha: date) -> list[ReglaDistribucion]:
    return [r for r in db.scalars(select(ReglaDistribucion).where(ReglaDistribucion.empresa_id == empresa_id,
                                                                   ReglaDistribucion.activa.is_(True)))
            if (r.vigente_desde is None or r.vigente_desde <= fecha) and (r.vigente_hasta is None or r.vigente_hasta >= fecha)]


def _aplicables(reglas, cuenta, cc, proyecto, unidad, maquinaria):
    """Reglas que aplican; gana la de cuenta más específica y, a igual cuenta, la más específica en dimensiones."""
    cands = []
    for r in reglas:
        if not cuenta.startswith(r.cuenta_origen):
            continue
        dims = ((r.centro_costo, cc), (r.proyecto, proyecto), (r.unidad_negocio, unidad), (r.maquinaria, maquinaria))
        if any(v and v != real for v, real in dims):
            continue
        cands.append((len(r.cuenta_origen), sum(1 for v, _ in dims if v), r))
    if not cands:
        return []
    mejor = max((c[0], c[1]) for c in cands)
    return [c[2] for c in cands if (c[0], c[1]) == mejor]


def analizar(db: Session, empresa_id: int, lineas: list, ejercicio: int, hasta: int) -> dict:
    """`lineas`: movimientos del rango (ver motor.cargar_lineas). Devuelve resumen y detalle."""
    pol = politica(db, empresa_id)
    fin = date(ejercicio, min(max(hasta, 1), 12), 28)
    reglas = reglas_vigentes(db, empresa_id, fin)
    plan = {c.codigo: c for c in db.scalars(select(CuentaContable).where(CuentaContable.empresa_id == empresa_id))}
    centros = {c.codigo: c for c in db.scalars(select(CentroCosto).where(CentroCosto.empresa_id == empresa_id))}
    excluidas_regla = [r.cuenta_origen for r in reglas if r.excluir]

    por_periodo = defaultdict(lambda: {"origen": CERO, "destino": CERO, "cargas": CERO, "excluido": CERO,
                                       "aplica48": CERO, "abono78": CERO})
    por_cc = defaultdict(lambda: {"origen": CERO, "destino": CERO})
    por_origen = defaultdict(lambda: {"origen": CERO, "esperado": CERO, "sin_regla": CERO, "excluido": False})
    esperado_destino = defaultdict(lambda: CERO)
    registrado_destino = defaultdict(lambda: CERO)
    asientos = defaultdict(lambda: {"origen": CERO, "destino": CERO, "cargas": CERO, "lineas_destino": [], "fila": None})
    sin_cc = []

    for ln in lineas:
        neto = ln.debe - ln.haber
        c = ln.cuenta
        p = ln.periodo
        unidad = centros[ln.cc].unidad_negocio if ln.cc in centros else None
        ka = (ln.lote_id, ln.periodo, ln.subdiario or "", ln.asiento) if ln.asiento else None
        if c.startswith("6") and (not _empieza(c, pol.destinables) or _empieza(c, excluidas_regla)):
            por_periodo[p]["excluido"] += neto
            por_origen[c]["origen"] += neto
            por_origen[c]["excluido"] = True
            continue
        if _empieza(c, pol.destinables):
            por_periodo[p]["origen"] += neto
            por_cc[ln.cc or "(sin centro de costo)"]["origen"] += neto
            o = por_origen[c]
            o["origen"] += neto
            aplicables = _aplicables(reglas, c, ln.cc, ln.proyecto, unidad, ln.maquinaria)
            if aplicables:
                for r in aplicables:
                    monto = (neto * r.porcentaje / CIEN).quantize(Decimal("0.01"))
                    if r.cuenta_destino:
                        esperado_destino[r.cuenta_destino] += monto
                        o["esperado"] += monto
            elif plan.get(c) and plan[c].cuenta_destino_debe:
                esperado_destino[plan[c].cuenta_destino_debe] += neto
                o["esperado"] += neto
            elif ln.cc in centros and centros[ln.cc].cuenta_destino:
                esperado_destino[centros[ln.cc].cuenta_destino] += neto
                o["esperado"] += neto
            else:
                o["sin_regla"] += neto
            if ka:
                asientos[ka]["origen"] += neto
                asientos[ka]["fila"] = asientos[ka]["fila"] or ln
        elif _empieza(c, pol.destino):
            por_periodo[p]["destino"] += neto
            por_cc[ln.cc or "(sin centro de costo)"]["destino"] += neto
            registrado_destino[c] += neto
            if pol.exigir_cc and not ln.cc:
                sin_cc.append(ln)
            if ka:
                asientos[ka]["destino"] += neto
                asientos[ka]["lineas_destino"].append(ln)
                asientos[ka]["fila"] = asientos[ka]["fila"] or ln
        elif c.startswith(pol.cargas):
            por_periodo[p]["cargas"] -= neto
            if ka:
                asientos[ka]["cargas"] -= neto
        if c.startswith("48") and ln.debe > 0:
            por_periodo[p]["aplica48"] += ln.debe
        if c.startswith("78") and ln.haber > 0:
            por_periodo[p]["abono78"] += ln.haber

    tol = pol.tolerancia
    resumen = []
    for p in sorted(por_periodo):
        x = por_periodo[p]
        estado = "CONFORME"
        if not pol.usa_destino:
            estado = "NO_APLICA"
        elif x["origen"] and not x["destino"]:
            estado = "SIN_DESTINO"
        elif x["destino"] - x["origen"] > tol:
            estado = "DESTINO_DUPLICADO"
        elif abs(x["destino"] - x["cargas"]) > tol:
            estado = "DUPLICIDAD_PRESENTACION"
        elif abs(x["origen"] - x["destino"]) > tol:
            estado = "DIFERENCIA"
        resumen.append({"periodo": p, "origen": x["origen"], "destino": x["destino"], "cargas_imputables": x["cargas"],
                        "excluido": x["excluido"], "diferencia": x["origen"] - x["destino"],
                        "diferencia_79": x["destino"] - x["cargas"], "provision_aplicada_48": x["aplica48"],
                        "abono_78": x["abono78"], "estado": estado})
    cc = [{"clave": k, "origen": v["origen"], "destino": v["destino"], "diferencia": v["origen"] - v["destino"],
           "estado": "CONFORME" if abs(v["origen"] - v["destino"]) <= tol else "DIFERENCIA"}
          for k, v in sorted(por_cc.items())]
    destinos = [{"clave": k, "esperado": esperado_destino.get(k, CERO),
                 "registrado": sum((v for c, v in registrado_destino.items() if c.startswith(k)), CERO)}
                for k in sorted(esperado_destino)]
    asignados = set(esperado_destino)
    for c, v in sorted(registrado_destino.items()):
        if not any(c.startswith(k) for k in asignados):
            destinos.append({"clave": c, "esperado": CERO, "registrado": v})
    for d in destinos:
        d["diferencia"] = d["esperado"] - d["registrado"]
        d["estado"] = "CONFORME" if abs(d["diferencia"]) <= tol else (
            "SIN_REGLA" if not d["esperado"] else "DIFERENCIA")
    origenes = []
    for c, v in sorted(por_origen.items()):
        estado = "EXCLUIDA" if v["excluido"] else ("SIN_DESTINO_CONFIGURADO" if v["sin_regla"] else "CON_DESTINO")
        origenes.append({"clave": c, "descripcion": plan[c].descripcion if c in plan else None, "origen": v["origen"],
                         "esperado": v["esperado"], "sin_regla": v["sin_regla"], "estado": estado})
    incidencias_asiento = []
    if pol.usa_destino and pol.modo == "MISMO_ASIENTO":
        for k, a in asientos.items():
            etiqueta = "-".join(p for p in (k[2], k[3]) if p)
            if a["destino"] - a["origen"] > tol:
                incidencias_asiento.append({"asiento": etiqueta, "periodo": k[1], "estado": "DESTINO_DUPLICADO",
                                            "origen": a["origen"], "destino": a["destino"], "linea_id": a["fila"].id})
            elif a["origen"] and not a["destino"]:
                incidencias_asiento.append({"asiento": etiqueta, "periodo": k[1], "estado": "SIN_DESTINO",
                                            "origen": a["origen"], "destino": CERO, "linea_id": a["fila"].id})
            vistos = set()
            for ln in a["lineas_destino"]:
                firma = (ln.cuenta, ln.cc, ln.debe, ln.haber)
                if firma in vistos:
                    incidencias_asiento.append({"asiento": etiqueta, "periodo": k[1], "estado": "LINEA_DESTINO_REPETIDA",
                                                "origen": a["origen"], "destino": a["destino"], "linea_id": ln.id})
                vistos.add(firma)
    totales = {k: sum((x[k] for x in resumen), CERO) for k in ("origen", "destino", "cargas_imputables", "excluido",
                                                                "provision_aplicada_48", "abono_78")}
    return {"politica": pol.__dict__ | {"tolerancia": str(pol.tolerancia)}, "reglas_vigentes": len(reglas),
            "resumen": resumen, "totales": totales, "centros_costo": cc, "destinos": destinos, "origenes": origenes,
            "asientos": incidencias_asiento, "destino_sin_centro_costo": [ln.id for ln in sin_cc][:200]}


def serializar(res: dict) -> dict:
    def s(v):
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, dict):
            return {k: s(x) for k, x in v.items()}
        if isinstance(v, list):
            return [s(x) for x in v]
        return v
    return s(res)
