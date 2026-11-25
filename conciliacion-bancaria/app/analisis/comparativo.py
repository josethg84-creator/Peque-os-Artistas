"""Análisis comparativo entre periodos y dimensiones.

Modos: MES_ANTERIOR · MISMO_MES_ANTERIOR (mismo mes del ejercicio anterior) · ACUMULADO (enero–mes
contra el mismo acumulado del ejercicio anterior) · PERSONALIZADO (dos rangos cualesquiera).
Dimensiones: CUENTA (a un nivel del árbol) · CENTRO_COSTO · PROYECTO · UNIDAD_NEGOCIO · MONEDA · TERCERO.
Medidas: SALDO (saldo final; solo dimensión CUENTA) o MOVIMIENTO (debe − haber del rango).

Variación porcentual NO APLICABLE cuando la base es cero. Se advierte cuando alguno de los periodos
comparados no tiene información importada o solo tiene un mayor parcial.
"""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.analisis import pcge
from app.analisis.saldos import cent, construir_arbol, dec, fuentes, plan_de, saldos_hoja
from app.models import CentroCosto, LineaDiario

CERO = Decimal("0")
DIMENSIONES = {"CUENTA", "CENTRO_COSTO", "PROYECTO", "UNIDAD_NEGOCIO", "MONEDA", "TERCERO"}


@dataclass
class Rango:
    ejercicio: int
    desde: int
    hasta: int

    @property
    def etiqueta(self) -> str:
        return f"{self.ejercicio} · {self.desde:02d}" if self.desde == self.hasta else f"{self.ejercicio} · {self.desde:02d}–{self.hasta:02d}"

    @property
    def meses(self) -> int:
        return max(1, min(self.hasta, 12) - max(self.desde, 1) + 1)


def rangos(modo: str, ejercicio: int, periodo: int, personalizado: tuple | None = None) -> tuple[Rango, Rango]:
    if modo == "MES_ANTERIOR":
        base = Rango(ejercicio, periodo - 1, periodo - 1) if periodo > 1 else Rango(ejercicio - 1, 12, 12)
        return Rango(ejercicio, periodo, periodo), base
    if modo == "MISMO_MES_ANTERIOR":
        return Rango(ejercicio, periodo, periodo), Rango(ejercicio - 1, periodo, periodo)
    if modo == "ACUMULADO":
        return Rango(ejercicio, 1, periodo), Rango(ejercicio - 1, 1, periodo)
    if modo == "PERSONALIZADO" and personalizado:
        (e1, d1, h1), (e2, d2, h2) = personalizado
        return Rango(e1, d1, h1), Rango(e2, d2, h2)
    raise ValueError("Modo de comparación no válido")


def _cobertura(db, empresa_id, r: Rango) -> list[str]:
    f = fuentes(db, empresa_id, r.ejercicio)
    avisos = []
    faltan = [p for p in range(max(r.desde, 1), min(r.hasta, 12) + 1) if p not in f.por_periodo]
    if faltan:
        avisos.append(f"{r.etiqueta}: periodos sin información importada ({', '.join(f'{p:02d}' for p in faltan)}).")
    parciales = [p for p in range(r.desde, r.hasta + 1) if f.por_periodo.get(p, {}).get("tipo") == "MAYOR"]
    if parciales:
        avisos.append(f"{r.etiqueta}: periodos con solo libro mayor ({', '.join(f'{p:02d}' for p in parciales)}).")
    return avisos


def _movimiento_por(db, empresa_id, r: Rango, dim: str, cuenta: str | None) -> dict[str, dict]:
    f = fuentes(db, empresa_id, r.ejercicio)
    col = {"CENTRO_COSTO": LineaDiario.centro_costo, "PROYECTO": LineaDiario.proyecto,
           "MONEDA": LineaDiario.moneda, "TERCERO": LineaDiario.documento_tercero,
           "UNIDAD_NEGOCIO": LineaDiario.centro_costo}[dim]
    clave = func.coalesce(col, "(sin informar)")
    q = select(clave, cent(LineaDiario.debe_mn), cent(LineaDiario.haber_mn), cent(LineaDiario.debe_me),
               cent(LineaDiario.haber_me), func.count()).where(f.filtro_lineas(r.desde, r.hasta))
    if cuenta:
        q = q.where(or_(*[LineaDiario.cuenta.like(f"{c.strip()}%") for c in cuenta.split(",") if c.strip()]))
    out: dict[str, dict] = defaultdict(lambda: {"valor": 0, "me": 0, "n": 0})
    unidades = {}
    if dim == "UNIDAD_NEGOCIO":
        unidades = dict(db.execute(select(CentroCosto.codigo, CentroCosto.unidad_negocio).where(CentroCosto.empresa_id == empresa_id)).all())
    for k, d, h, dme, hme, n in db.execute(q.group_by(clave)):
        if dim == "UNIDAD_NEGOCIO":
            k = unidades.get(k) or "(sin unidad de negocio)"
        x = out[k]
        x["valor"] += int(d) - int(h)
        x["me"] += int(dme) - int(hme)
        x["n"] += n
    return out


def _serie_mensual(db, empresa_id, ejercicio: int, hasta: int, dim: str, cuenta: str | None, nivel: int) -> dict[str, list]:
    """Tendencia: movimiento neto mensual del ejercicio (enero → mes analizado) por clave."""
    f = fuentes(db, empresa_id, ejercicio)
    if dim == "CUENTA":
        clave = LineaDiario.cuenta if nivel == 0 else func.substr(LineaDiario.cuenta, 1, nivel)
    else:
        clave = func.coalesce({"CENTRO_COSTO": LineaDiario.centro_costo, "PROYECTO": LineaDiario.proyecto,
                               "MONEDA": LineaDiario.moneda, "TERCERO": LineaDiario.documento_tercero,
                               "UNIDAD_NEGOCIO": LineaDiario.centro_costo}[dim], "(sin informar)")
    q = select(clave, LineaDiario.periodo, cent(LineaDiario.debe_mn) - cent(LineaDiario.haber_mn)) \
        .where(f.filtro_lineas(1, min(hasta, 12))).group_by(clave, LineaDiario.periodo)
    if cuenta:
        q = q.where(or_(*[LineaDiario.cuenta.like(f"{c.strip()}%") for c in cuenta.split(",") if c.strip()]))
    series: dict[str, list] = defaultdict(lambda: [0] * min(hasta, 12))
    for k, p, v in db.execute(q):
        if p and 1 <= p <= 12 and p <= hasta:
            series[k][p - 1] += int(v)
    return series


def comparar(db: Session, empresa_id: int, actual: Rango, base: Rango, *, dimension="CUENTA", medida="SALDO",
             nivel=2, cuenta: str | None = None, limite=500) -> dict:
    if dimension not in DIMENSIONES:
        raise ValueError("Dimensión no válida")
    if dimension != "CUENTA":
        medida = "MOVIMIENTO"
    avisos = _cobertura(db, empresa_id, actual) + _cobertura(db, empresa_id, base)
    if actual.meses != base.meses:
        avisos.append(f"Los periodos comparados tienen distinta duración ({actual.meses} y {base.meses} meses).")
    nombres = {}
    if dimension == "CUENTA":
        plan = plan_de(db, empresa_id)
        valores = []
        for r in (actual, base):
            nodos = construir_arbol(saldos_hoja(db, fuentes(db, empresa_id, r.ejercicio), r.desde, r.hasta), plan)
            vals = {}
            for c, nd in nodos.items():
                incluir = nd.propio if nivel == 0 else (len(c) == nivel or (len(c) < nivel and nd.hijos == 0))
                if not incluir:  # nivel 0 = cuentas de movimiento
                    continue
                if cuenta and not any(c.startswith(p.strip()) for p in cuenta.split(",")):
                    continue
                vals[c] = {"valor": nd.sf if medida == "SALDO" else nd.debe - nd.haber, "me": 0, "n": nd.n}
                nombres[c] = nd.descripcion
            valores.append(vals)
        act, bas = valores
    else:
        act = _movimiento_por(db, empresa_id, actual, dimension, cuenta)
        bas = _movimiento_por(db, empresa_id, base, dimension, cuenta)
    claves = sorted(set(act) | set(bas))
    total_act = sum(abs(act[k]["valor"]) for k in act) or 0
    series = _serie_mensual(db, empresa_id, actual.ejercicio, actual.hasta, dimension, cuenta, nivel)
    filas = []
    for k in claves:
        a, b = act.get(k, {"valor": 0, "me": 0, "n": 0}), bas.get(k, {"valor": 0, "me": 0, "n": 0})
        var = a["valor"] - b["valor"]
        pct = None if b["valor"] == 0 else round(float(Decimal(var) / abs(Decimal(b["valor"])) * 100), 2)
        filas.append({
            "clave": k, "descripcion": nombres.get(k) or (pcge.nombre_pcge(k) if dimension == "CUENTA" else None),
            "actual": str(dec(a["valor"])), "base": str(dec(b["valor"])), "variacion": str(dec(var)),
            "variacion_pct": pct, "variacion_pct_aplica": b["valor"] != 0,
            "participacion_pct": round(float(Decimal(abs(a["valor"])) / Decimal(total_act) * 100), 2) if total_act else None,
            "promedio_mensual": str(dec(round(a["valor"] / actual.meses))) if medida == "MOVIMIENTO" else None,
            "importe_me": str(dec(a["me"])) if dimension == "MONEDA" else None,
            "movimientos": a["n"], "tendencia": [str(dec(v)) for v in series.get(k, [])],
        })
    filas.sort(key=lambda x: -abs(Decimal(x["actual"])))
    # concentración: participación acumulada de las 5 claves principales
    top = sorted((abs(act[k]["valor"]) for k in act), reverse=True)
    concentracion = round(float(Decimal(sum(top[:5])) / Decimal(total_act) * 100), 2) if total_act else None
    return {"actual": actual.__dict__ | {"etiqueta": actual.etiqueta}, "base": base.__dict__ | {"etiqueta": base.etiqueta},
            "dimension": dimension, "medida": medida, "nivel": nivel, "cuenta": cuenta, "advertencias": avisos,
            "total_actual": str(dec(sum(act[k]["valor"] for k in act))), "total_base": str(dec(sum(bas[k]["valor"] for k in bas))),
            "concentracion_top5_pct": concentracion, "filas": filas[:limite], "total_filas": len(filas)}
