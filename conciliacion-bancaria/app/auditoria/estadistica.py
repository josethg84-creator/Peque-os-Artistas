"""Módulo ESTADISTICA: herramientas exploratorias de detección de anomalías.

Cada resultado documenta el método, la población y las limitaciones. Los resultados estadísticos son indicios para
orientar la revisión; NO son prueba de errores ni de fraude. La Ley de Benford se aplica solo con población suficiente
y a importes que no estén acotados por la naturaleza de la operación (umbrales de conformidad MAD de Nigrini, solo como
referencia exploratoria).
"""
import math
import statistics
from collections import Counter, defaultdict


from app.auditoria.base import CERO, Res, Salida, asiento_de, dec, ev_calc, ev_linea

LIMITACION = "Indicador exploratorio: no constituye evidencia de error ni de fraude."


def _cuartiles(v):
    q1, q2, q3 = statistics.quantiles(v, n=4)
    return q1, q2, q3


def atipicos(ax, r) -> Salida:
    """Líneas fuera de Q3 + k·IQR por cuenta."""
    k = float(r.p.get("k", 3))
    minimo = int(r.p.get("min_lineas", 12))
    imp_min = dec(r.p.get("importe_minimo", "0"))
    por = defaultdict(list)
    for ln in ax.lineas:
        if r.en(ln.cuenta) and (ln.debe or ln.haber):
            por[ln.cuenta].append(ln)
    out = []
    for c, ls in por.items():
        if len(ls) < minimo:
            continue
        v = [float(x.debe + x.haber) for x in ls]
        q1, q2, q3 = _cuartiles(v)
        lim = q3 + k * (q3 - q1)
        for x in ls:
            imp = x.debe + x.haber
            if float(imp) > lim and imp >= imp_min and q3 > q1:
                out.append(Res(titulo=f"Importe atípico en la cuenta {c}", condicion=f"Línea {x.id} por {imp} supera Q3 + {k}·IQR ({lim:,.2f}); mediana {q2:,.2f}.",
                               importe=imp, cuenta=c, tercero=x.tercero, linea_id=x.id, asiento=asiento_de(x), evidencia=[ev_linea(x), ev_calc(
                                   "Distribución de la cuenta", n=len(v), q1=round(q1, 2), mediana=round(q2, 2), q3=round(q3, 2), limite=round(lim, 2),
                                   media=round(statistics.mean(v), 2), desviacion=round(statistics.pstdev(v), 2), limitacion=LIMITACION)],
                               clave=f"EST|ATI|{x.id}", exposicion=f"LINEA|{x.id}", estructural=False, calidad="PARCIAL", riesgo_minimo="INFORMATIVO"))
    return Salida(out, sum(len(v) for v in por.values()), metodo=f"Rango intercuartílico por cuenta (mínimo {minimo} líneas): límite Q3 + {k}·IQR. {LIMITACION}")


def frecuencia(ax, r) -> Salida:
    """Meses con cantidad de operaciones atípica por cuenta (z-score sobre los meses anteriores)."""
    z = float(r.p.get("z", 3))
    por = defaultdict(Counter)
    for ln in ax.lineas:
        if r.en(ln.cuenta) and 1 <= (ln.periodo or 0) <= 12:
            por[ln.cuenta][ln.periodo] += 1
    out = []
    for c, m in por.items():
        hist = [m.get(p, 0) for p in range(1, ax.periodo)]
        if len(hist) < 3:
            continue
        mu, sd = statistics.mean(hist), statistics.pstdev(hist)
        act = m.get(ax.periodo, 0)
        if sd and (act - mu) / sd > z:
            out.append(Res(titulo=f"Frecuencia atípica de operaciones en la cuenta {c}", condicion=f"{act} movimientos en el periodo {ax.periodo:02d}; promedio "
                           f"{mu:.1f} (desv. {sd:.1f}).", cuenta=c, evidencia=[ev_calc("Movimientos por mes", **{f"p{p:02d}": m.get(p, 0) for p in range(1, ax.periodo + 1)},
                                                                                     limitacion=LIMITACION)],
                           clave=f"EST|FRE|{c}|{ax.periodo}", exposicion=f"FRECUENCIA|{c}", calidad="PARCIAL", riesgo_minimo="INFORMATIVO"))
    return Salida(out, len(por), metodo=f"Cantidad de movimientos del periodo frente al promedio histórico (z > {z}). {LIMITACION}")


def dimensiones(ax, r) -> Salida:
    """Comparación entre centros de costo o proyectos: gasto atípico respecto de sus pares (IQR)."""
    dim = r.p.get("dimension", "cc")
    por = defaultdict(lambda: CERO)
    for ln in ax.lineas:
        if ln.cuenta.startswith("6") and r.en(ln.cuenta):
            k = getattr(ln, dim) or "(sin asignar)"
            por[k] += ln.debe - ln.haber
    out = []
    if len(por) >= 5:
        v = [float(x) for x in por.values()]
        q1, q2, q3 = _cuartiles(v)
        lim = q3 + float(r.p.get("k", 1.5)) * (q3 - q1)
        for k, x in por.items():
            if float(x) > lim and q3 > q1:
                out.append(Res(titulo=f"Gasto atípico del {'centro de costo' if dim == 'cc' else 'proyecto'} {k}", condicion=f"Gasto {x} frente a una mediana de "
                               f"{q2:,.2f} entre {len(por)} {'centros' if dim == 'cc' else 'proyectos'}.", importe=x,
                               centro_costo=k if dim == "cc" else None, proyecto=k if dim == "proyecto" else None,
                               evidencia=[ev_calc("Comparación entre pares", mediana=round(q2, 2), limite=round(lim, 2), n=len(por), limitacion=LIMITACION)],
                               clave=f"EST|DIM|{dim}|{k}", exposicion=f"DIM|{dim}|{k}", calidad="PARCIAL", riesgo_minimo="INFORMATIVO"))
    return Salida(out, len(por), metodo=f"Gasto por {dim} frente a sus pares (Q3 + k·IQR). {LIMITACION}")


def redondos(ax, r) -> Salida:
    base = dec(r.p.get("multiplo", "1000"))
    pct = float(r.p.get("porcentaje", 30))
    por = defaultdict(lambda: [0, 0])
    for ln in ax.lineas:
        imp = ln.debe + ln.haber
        if r.en(ln.cuenta) and imp >= base:
            por[ln.cuenta][0] += 1
            por[ln.cuenta][1] += imp % base == 0
    out = []
    for c, (n, rd) in por.items():
        if n >= int(r.p.get("min_lineas", 10)) and rd * 100 / n >= pct:
            out.append(Res(titulo=f"Alta proporción de importes redondos en la cuenta {c}", condicion=f"{rd} de {n} movimientos ≥ {base} son múltiplos exactos "
                           f"de {base} ({rd * 100 / n:.1f} %).", cuenta=c, evidencia=[ev_calc("Importes redondos", n=n, redondos=rd, limitacion=LIMITACION)],
                           clave=f"EST|RED|{c}", exposicion=f"REDONDOS|{c}", calidad="PARCIAL", riesgo_minimo="INFORMATIVO",
                           causa="Pueden corresponder a estimaciones, anticipos o tarifas fijas: requiere revisión."))
    return Salida(out, len(por), metodo=f"Proporción de importes múltiplos de {base} por cuenta ≥ {pct} %. {LIMITACION}")


def cerca_de_limites(ax, r) -> Salida:
    limites = [dec(x) for x in r.p.get("limites", [])]
    if not limites:
        return Salida(estado="SIN_DATOS", mensaje="No se configuraron límites (p. ej. niveles de aprobación) para esta regla.")
    margen = dec(r.p.get("margen_pct", 5))
    minimo = int(r.p.get("min_operaciones", 3))
    g = defaultdict(list)
    for ln in ax.lineas:
        imp = ln.debe + ln.haber
        for lim in limites:
            if r.en(ln.cuenta) and lim * (100 - margen) / 100 <= imp < lim:
                g[(lim, ln.usuario_registro or ln.tercero or "(sin dato)")].append(ln)
    out = []
    for (lim, quien), ls in g.items():
        if len(ls) >= minimo:
            out.append(Res(titulo=f"Operaciones cercanas al límite de {lim}", condicion=f"{len(ls)} operaciones entre {lim * (100 - margen) / 100:.2f} y {lim} "
                           f"({quien}).", importe=sum((x.debe + x.haber for x in ls), CERO), tercero=ls[0].tercero, evidencia=[ev_linea(x) for x in ls[:15]],
                           clave=f"EST|LIM|{lim}|{quien}", exposicion=f"LIMITE|{lim}|{quien}", calidad="PARCIAL",
                           causa="Posible fraccionamiento para evitar niveles de aprobación: hipótesis a verificar."))
    return Salida(out, sum(len(v) for v in g.values()), metodo=f"Importes dentro del {margen} % por debajo de los límites configurados. {LIMITACION}")


BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def benford(ax, r) -> Salida:
    minimo = int(r.p.get("min_poblacion", 500))
    imp_min = dec(r.p.get("importe_minimo", "10"))
    digitos = [int(str(int(x.debe + x.haber))[0]) for x in ax.lineas if r.en(x.cuenta) and x.debe + x.haber >= imp_min]
    if len(digitos) < minimo:
        return Salida(estado="SIN_DATOS", mensaje=f"Población insuficiente para la Ley de Benford ({len(digitos)} < {minimo} importes ≥ {imp_min}).")
    n = len(digitos)
    obs = Counter(digitos)
    mad = sum(abs(obs.get(d, 0) / n - p) for d, p in BENFORD.items()) / 9
    conf = "conformidad cercana" if mad <= 0.006 else "conformidad aceptable" if mad <= 0.012 else "conformidad marginal" if mad <= 0.015 else "no conformidad"
    out = []
    if mad > float(r.p.get("mad_umbral", 0.015)):
        out.append(Res(titulo="La distribución del primer dígito se aparta de la Ley de Benford", condicion=f"MAD {mad:.4f} ({conf}) sobre {n} importes.",
                       evidencia=[ev_calc("Primer dígito", n=n, mad=round(mad, 5), **{f"d{d}": f"{obs.get(d, 0) / n:.3f} vs {p:.3f}" for d, p in BENFORD.items()},
                                          limitacion=LIMITACION + " Benford no aplica a importes acotados (tarifas, planillas, cuotas fijas).")],
                       clave=f"EST|BEN|{ax.periodo}", exposicion="BENFORD", calidad="PARCIAL", riesgo_minimo="INFORMATIVO",
                       causa="Exploratorio: orienta la selección de muestras, no prueba irregularidades."))
    return Salida(out, n, metodo=f"Ley de Benford del primer dígito (MAD; Nigrini: ≤0,006 cercana, ≤0,012 aceptable, ≤0,015 marginal). {LIMITACION}")


def resumen(ax, cuenta: str | None = None) -> dict:
    """Estadística descriptiva para el explorador (no genera hallazgos)."""
    v = [float(x.debe + x.haber) for x in ax.lineas if (not cuenta or x.cuenta.startswith(cuenta)) and (x.debe or x.haber)]
    if len(v) < 2:
        return {"n": len(v)}
    q1, q2, q3 = _cuartiles(v)
    mensual = defaultdict(float)
    for x in ax.lineas:
        if not cuenta or x.cuenta.startswith(cuenta):
            mensual[x.periodo] += float(x.debe - x.haber)
    return {"n": len(v), "suma": round(sum(v), 2), "media": round(statistics.mean(v), 2), "mediana": round(q2, 2), "desviacion": round(statistics.pstdev(v), 2),
            "q1": round(q1, 2), "q3": round(q3, 2), "iqr": round(q3 - q1, 2), "minimo": min(v), "maximo": max(v),
            "mensual": {str(k): round(x, 2) for k, x in sorted(mensual.items())}, "limitacion": LIMITACION}


EVALUADORES = {"atipicos": atipicos, "frecuencia": frecuencia, "dimensiones": dimensiones, "redondos": redondos, "cerca_de_limites": cerca_de_limites,
               "benford": benford}

