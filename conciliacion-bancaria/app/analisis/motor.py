"""Ejecución del análisis de cuentas (asíncrona, cancelable, con tiempos y resultados versionados).

Etapas: fuentes y saldos → carga de movimientos → antigüedad → origen-destino → reglas →
persistencia de snapshots, resultados y hallazgos → indicadores.

Exposición sin duplicar: varios hallazgos pueden referirse al mismo importe (p. ej. un documento
antiguo que además es saldo contrario). El «importe sujeto a revisión» se calcula por cuenta de 2
dígitos como el máximo entre (a) la suma, por clave de exposición distinta (línea, documento o
cuenta), del mayor importe observado y (b) el mayor hallazgo a nivel de cuenta del mismo grupo.
"""
import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.analisis import antiguedad, destino, pcge, reglas, saldos
from app.models import (AnalisisEjecucion, AnalisisResultado, AuditoriaAnalisis, ConfiguracionContable, ExcepcionAnalisis,
                        Hallazgo, LineaDiario, LoteContable, ReglaAnalisis, ResultadoDestino, SaldoCuenta, SaldoSnapshot,
                        TipoCambio)

CERO = Decimal("0")
ORDEN_RIESGO = {"ALTO": 0, "MEDIO": 1, "BAJO": 2, "INFORMATIVO": 3}


class Cancelado(Exception):
    pass


@dataclass(slots=True)
class Linea:
    id: int
    lote_id: int
    periodo: int
    fecha: date | None
    subdiario: str | None
    asiento: str | None
    cuenta: str
    tercero: str | None
    razon_social: str | None
    tipo_doc: str | None
    serie: str | None
    numero: str | None
    debe: Decimal
    haber: Decimal
    debe_me: Decimal
    haber_me: Decimal
    moneda: str
    cc: str | None
    proyecto: str | None
    maquinaria: str | None
    glosa: str | None
    # campos complementarios (fase 7: auditoría); opcionales para las pseudo-líneas de apertura
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None
    tipo_cambio: Decimal | None = None
    referencia: str | None = None
    codigo_detraccion: str | None = None
    constancia: str | None = None
    usuario_registro: str | None = None
    fecha_registro: date | None = None
    origen_asiento: str | None = None

    @property
    def doc(self) -> str | None:
        if not self.numero:
            return None
        return f"{self.serie}-{self.numero}" if self.serie else self.numero

    @property
    def etiqueta_asiento(self) -> str | None:
        return "-".join(p for p in (self.subdiario, self.asiento) if p) or None


_COLS = (LineaDiario.id, LineaDiario.lote_id, LineaDiario.periodo, LineaDiario.fecha_contable, LineaDiario.subdiario,
         LineaDiario.numero_asiento, LineaDiario.cuenta, LineaDiario.documento_tercero, LineaDiario.razon_social,
         LineaDiario.tipo_documento, LineaDiario.serie, LineaDiario.numero_documento, LineaDiario.debe_mn,
         LineaDiario.haber_mn, LineaDiario.debe_me, LineaDiario.haber_me, LineaDiario.moneda, LineaDiario.centro_costo,
         LineaDiario.proyecto, LineaDiario.activo_maquinaria, LineaDiario.glosa, LineaDiario.fecha_emision,
         LineaDiario.fecha_vencimiento, LineaDiario.tipo_cambio, LineaDiario.documento_referencia, LineaDiario.codigo_detraccion,
         LineaDiario.constancia_detraccion, LineaDiario.usuario_registro, LineaDiario.fecha_registro, LineaDiario.origen_asiento)


def _d(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v or 0)).quantize(Decimal("0.01"))


def cargar_lineas(db: Session, filtro) -> list[Linea]:
    out = []
    for r in db.execute(select(*_COLS).where(filtro).order_by(LineaDiario.id)).yield_per(5000):
        out.append(Linea(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], _d(r[12]), _d(r[13]),
                         _d(r[14]), _d(r[15]), r[16] or "PEN", r[17], r[18], r[19], r[20], *r[21:]))
    return out


def auditar(db: Session, empresa_id: int, usuario: str, accion: str, entidad: str, entidad_id=None, detalle=None):
    db.add(AuditoriaAnalisis(empresa_id=empresa_id, usuario=usuario or "sistema", accion=accion, entidad=entidad,
                             entidad_id=entidad_id, detalle=detalle if isinstance(detalle, str) or detalle is None
                             else json.dumps(detalle, ensure_ascii=False, default=str)))


# ------------------------------------------------------------------ creación
def crear(db: Session, empresa_id: int, ejercicio: int, desde: int, hasta: int, usuario: str,
          codigos: list[str] | None = None, grupo: str | None = None) -> AnalisisEjecucion:
    if not (1 <= desde <= hasta <= 13):
        raise ValueError("Rango de periodos inválido (01–13).")
    reglas.sembrar(db, empresa_id)
    run = AnalisisEjecucion(empresa_id=empresa_id, ejercicio=ejercicio, periodo_desde=desde, periodo_hasta=hasta,
                            version_datos=saldos.version_datos(db, empresa_id), usuario=usuario, grupo_reglas=grupo,
                            reglas_snapshot=json.dumps({"filtro_codigos": codigos or [], "grupo": grupo}))
    db.add(run)
    db.flush()
    auditar(db, empresa_id, usuario, "EJECUTAR_ANALISIS", "run", run.id,
            {"ejercicio": ejercicio, "desde": desde, "hasta": hasta, "codigos": codigos, "grupo": grupo})
    db.commit()
    return run


def cancelar(db: Session, run: AnalisisEjecucion, usuario: str):
    if run.estado in ("COMPLETADO", "ERROR", "CANCELADO"):
        raise ValueError("El análisis ya terminó.")
    run.cancelar = True
    auditar(db, run.empresa_id, usuario, "CANCELAR_ANALISIS", "run", run.id)
    db.commit()


# ------------------------------------------------------------------ ejecución
def ejecutar(db: Session, run_id: int, avance=lambda p, e: None) -> dict:
    run = db.get(AnalisisEjecucion, run_id)
    tiempos: dict[str, int] = {}
    t0 = time.perf_counter()
    marca = [t0]

    def paso(pct: int, etapa: str):
        ahora = time.perf_counter()
        tiempos[etapa_actual[0]] = int((ahora - marca[0]) * 1000)
        marca[0] = ahora
        etapa_actual[0] = etapa
        db.expire(run, ["cancelar"])
        if db.scalar(select(AnalisisEjecucion.cancelar).where(AnalisisEjecucion.id == run_id)):
            raise Cancelado()
        run.progreso, run.etapa, run.estado = pct, etapa, "PROCESANDO"
        db.commit()
        avance(pct, etapa)

    etapa_actual = ["Inicio"]
    try:
        resultado = _ejecutar(db, run, paso)
        tiempos[etapa_actual[0]] = int((time.perf_counter() - marca[0]) * 1000)
        run.estado, run.progreso, run.etapa = "COMPLETADO", 100, "Completado"
        run.duracion_ms = int((time.perf_counter() - t0) * 1000)
        run.tiempos = json.dumps(tiempos)
        run.finalizado_en = datetime.now()
        db.commit()
        return resultado
    except Cancelado:
        db.rollback()
        _limpiar(db, run_id)
        run = db.get(AnalisisEjecucion, run_id)
        run.estado, run.etapa, run.finalizado_en = "CANCELADO", "Cancelado por el usuario", datetime.now()
        run.duracion_ms = int((time.perf_counter() - t0) * 1000)
        db.commit()
        raise
    except Exception as exc:
        db.rollback()
        _limpiar(db, run_id)
        run = db.get(AnalisisEjecucion, run_id)
        run.estado, run.error, run.finalizado_en = "ERROR", str(exc)[:2000], datetime.now()
        db.commit()
        raise


def _limpiar(db, run_id):
    for modelo in (Hallazgo, AnalisisResultado, SaldoSnapshot, ResultadoDestino):
        db.execute(delete(modelo).where(modelo.run_id == run_id))
    db.commit()


def preparar_contexto(db: Session, e: int, ej: int, desde: int, hasta: int, paso=lambda p, t: None) -> tuple:
    """Fuentes, árbol de saldos, movimientos, antigüedad y origen-destino listos para evaluar reglas.
    Lo usan el análisis de cuentas (fase 3) y el auditor contable (fase 7). Devuelve (ctx, fuentes, control)."""
    paso(5, "Identificando fuentes y saldos")
    f = saldos.fuentes(db, e, ej)
    plan = saldos.plan_de(db, e)
    hojas_rango = saldos.saldos_hoja(db, f, desde, hasta)
    nodos = saldos.construir_arbol(hojas_rango, plan)
    ant = saldos.periodo_anterior(ej, desde, hasta)
    if ant:
        fa = saldos.fuentes(db, e, ant[0])
        if any(ant[1] <= p <= ant[2] for p in fa.por_periodo) or fa.apertura != "NINGUNA":
            previo = saldos.construir_arbol(saldos.saldos_hoja(db, fa, ant[1], ant[2]), plan)
            for c, nd in nodos.items():
                nd.anterior = previo[c].sf if c in previo else 0
    control = saldos.control_cuadre(db, f, desde, hasta, nodos)

    paso(20, "Cargando movimientos")
    lineas = cargar_lineas(db, f.filtro_lineas(desde, hasta))
    previas = cargar_lineas(db, f.filtro_lineas(0 if f.apertura == "DIARIO_00" else 1, desde - 1,
                                                incluir_apertura_diario=f.apertura == "DIARIO_00")) if desde > 1 or f.apertura == "DIARIO_00" else []
    hasta_corte = previas + lineas
    if f.apertura == "SALDOS_INICIALES":  # apertura como pseudo-líneas (sin documento) para saldos por tercero
        for c, t, mon, d, h, dme, hme in db.execute(
                select(SaldoCuenta.cuenta, SaldoCuenta.documento_tercero, SaldoCuenta.moneda,
                       func.sum(SaldoCuenta.saldo_inicial_debe), func.sum(SaldoCuenta.saldo_inicial_haber),
                       func.sum(SaldoCuenta.saldo_me_debe), func.sum(SaldoCuenta.saldo_me_haber))
                .where(SaldoCuenta.lote_id.in_(f.lotes_apertura))
                .group_by(SaldoCuenta.cuenta, SaldoCuenta.documento_tercero, SaldoCuenta.moneda)):
            hasta_corte.append(Linea(0, 0, 0, date(ej, 1, 1), None, None, c, t, None, None, None, None, _d(d), _d(h),
                                     _d(dme), _d(hme), mon or "PEN", None, None, None, "Saldo de apertura"))
    meses = defaultdict(set)
    for c, hj in saldos.saldos_hoja(db, f, 1, hasta).items():
        meses[c] = {p for p, (d, h) in hj.por_periodo.items() if d or h}

    paso(35, "Antigüedad de saldos")
    corte = _fin_periodo(ej, hasta)
    aging = antiguedad.calcular(db, e, ej, corte)

    paso(45, "Análisis de origen y destino")
    od = destino.analizar(db, e, lineas, ej, hasta)

    cfg = db.scalar(select(ConfiguracionContable).where(ConfiguracionContable.empresa_id == e))
    restringidas = [p.strip() for p in ((cfg.prefijos_sin_movimiento if cfg else "") or "").split(",") if p.strip()]
    ctx = reglas.Contexto(e, ej, desde, hasta, nodos, lineas, plan, restringidas, aging=aging, destino=od,
                          meses_con_movimiento=meses,
                          lotes_periodo=dict(db.execute(select(LoteContable.id, LoteContable.periodo)
                                                        .where(LoteContable.empresa_id == e)).all()))
    ctx.lineas_hasta_corte = hasta_corte
    ctx.saldos_me, ctx.tipo_cambio_cierre = _moneda_extranjera(db, e, hasta_corte, corte)
    return ctx, f, control


def _ejecutar(db: Session, run: AnalisisEjecucion, paso) -> dict:
    e, ej, desde, hasta = run.empresa_id, run.ejercicio, run.periodo_desde, run.periodo_hasta
    ctx, f, control = preparar_contexto(db, e, ej, desde, hasta, paso)
    nodos, lineas, aging, od = ctx.nodos, ctx.lineas, ctx.aging, ctx.destino
    corte = _fin_periodo(ej, hasta)
    run.fuentes = json.dumps({"por_periodo": {str(k): v for k, v in f.por_periodo.items()}, "apertura": f.apertura,
                              "lotes_apertura": f.lotes_apertura})
    paso(55, "Aplicando reglas")
    filtro = json.loads(run.reglas_snapshot or "{}")
    lista = [r for r in db.scalars(select(ReglaAnalisis).where(ReglaAnalisis.empresa_id == e).order_by(ReglaAnalisis.codigo))
             if reglas.vigente(r, corte)
             and (not filtro.get("filtro_codigos") or r.codigo in filtro["filtro_codigos"])
             and (not filtro.get("grupo") or r.grupo == filtro["grupo"])]
    excepciones = [x for x in db.scalars(select(ExcepcionAnalisis).where(ExcepcionAnalisis.empresa_id == e,
                                                                          ExcepcionAnalisis.activa.is_(True)))
                   if x.vigente_hasta is None or x.vigente_hasta >= corte]
    hallados, exceptuados = [], 0
    for i, r in enumerate(lista):
        paso(55 + int(25 * i / max(len(lista), 1)), f"Regla {r.codigo}: {r.nombre}")
        for h in reglas.evaluar(r, ctx):
            if any(_coincide(x, h) for x in excepciones):
                exceptuados += 1
                continue
            hallados.append(h)
    run.reglas_snapshot = json.dumps({**filtro, "reglas": [reglas.snapshot(r) for r in lista]}, ensure_ascii=False)

    paso(82, "Guardando resultados")
    _guardar_snapshots(db, run, nodos)
    _guardar_destino(db, run, od)
    filas_h = _guardar_hallazgos(db, run, hallados)
    _guardar_resultados(db, run, nodos, filas_h)

    paso(95, "Calculando indicadores")
    advertencias = list(f.advertencias)
    if not control["conciliado"]:
        advertencias.append("El árbol de saldos no concilia con la suma directa de las líneas fuente.")
    resumen = indicadores(run, nodos, lineas, filas_h, aging, od, control, exceptuados, len(lista))
    run.resumen = json.dumps(resumen, ensure_ascii=False, default=str)
    run.advertencias = json.dumps(advertencias, ensure_ascii=False)
    db.commit()
    return {"run_id": run.id, "resumen": resumen}


def _fin_periodo(ejercicio: int, periodo: int) -> date:
    p = min(max(periodo, 1), 12)
    siguiente = date(ejercicio + (p == 12), p % 12 + 1, 1)
    return date.fromordinal(siguiente.toordinal() - 1)


def _moneda_extranjera(db, empresa_id, lineas, corte):
    """Saldos de cuentas llevadas íntegramente en una moneda extranjera.

    Solo se evalúa una cuenta si TODAS sus líneas (incluida la apertura) tienen la misma moneda
    extranjera e importe en ME; las cuentas mixtas o con apertura sin detalle en ME se omiten
    para no generar diferencias de cambio ficticias."""
    acumulado = defaultdict(lambda: {"me": CERO, "mn": CERO, "monedas": set(), "sin_me": False})
    for ln in lineas:
        a = acumulado[ln.cuenta]
        a["me"] += ln.debe_me - ln.haber_me
        a["mn"] += ln.debe - ln.haber
        a["monedas"].add(ln.moneda or "PEN")
        if (ln.debe or ln.haber) and not (ln.debe_me or ln.haber_me):
            a["sin_me"] = True
    saldos_me = {c: (a["me"], a["mn"], next(iter(a["monedas"]))) for c, a in acumulado.items()
                 if len(a["monedas"]) == 1 and "PEN" not in a["monedas"] and not a["sin_me"]}
    tc = {}
    for moneda in {v[2] for v in saldos_me.values()}:
        t = db.scalar(select(TipoCambio).where(TipoCambio.empresa_id == empresa_id, TipoCambio.moneda == moneda,
                                               TipoCambio.fecha <= corte).order_by(TipoCambio.fecha.desc()))
        if t:
            tc[moneda] = (t.fecha, t.compra, t.venta)
    return saldos_me, tc


def _coincide(x: ExcepcionAnalisis, h) -> bool:
    return ((x.regla_id is None or x.regla_id == h.regla.id) and (not x.cuenta or h.cuenta.startswith(x.cuenta))
            and (not x.tercero or x.tercero == h.tercero) and (not x.documento or x.documento == h.documento))


def huella(empresa_id, ejercicio, h) -> str:
    base = f"{empresa_id}|{ejercicio}|{h.regla.codigo}|{h.cuenta}|{h.tercero}|{h.documento}|{h.asiento}|{h.linea_id}|{h.periodo}|{h.titulo if not (h.linea_id or h.documento or h.tercero) else ''}"
    return hashlib.sha256(base.encode()).hexdigest()


def _guardar_snapshots(db, run, nodos):
    filas = [{"run_id": run.id, "empresa_id": run.empresa_id, "cuenta": n.codigo, "padre": n.padre, "nivel": len(n.codigo),
              "descripcion": (n.descripcion or "")[:255] or None, "naturaleza": n.naturaleza,
              "saldo_inicial": saldos.dec(n.si), "debe": saldos.dec(n.debe), "haber": saldos.dec(n.haber),
              "saldo_final": saldos.dec(n.sf), "saldo_anterior": saldos.dec(n.anterior) if n.anterior is not None else None,
              "movimientos": n.n, "terceros": len(n.terceros)} for n in nodos.values()]
    for i in range(0, len(filas), 2000):
        db.execute(insert(SaldoSnapshot), filas[i:i + 2000])


def _guardar_destino(db, run, od):
    filas = []
    for x in od["resumen"]:
        filas.append(dict(tipo="RESUMEN", periodo=x["periodo"], clave=f"{x['periodo']:02d}", origen=x["origen"],
                          destino=x["destino"], cargas_imputables=x["cargas_imputables"], diferencia=x["diferencia"],
                          estado=x["estado"], descripcion=f"Excluido de la distribución: {x['excluido']}"))
    for x in od["centros_costo"]:
        filas.append(dict(tipo="CENTRO_COSTO", clave=x["clave"][:120], origen=x["origen"], destino=x["destino"],
                          diferencia=x["diferencia"], estado=x["estado"]))
    for x in od["destinos"]:
        filas.append(dict(tipo="DESTINO", clave=x["clave"], origen=CERO, destino_esperado=x["esperado"], destino=x["registrado"],
                          diferencia=x["diferencia"], estado=x["estado"]))
    for x in od["origenes"]:
        filas.append(dict(tipo="ORIGEN", clave=x["clave"], descripcion=(x["descripcion"] or "")[:255] or None,
                          origen=x["origen"], destino_esperado=x["esperado"], destino=CERO,
                          diferencia=x["sin_regla"], estado=x["estado"]))
    for x in od["asientos"]:
        filas.append(dict(tipo="ASIENTO", periodo=x["periodo"], clave=x["asiento"][:120], origen=x["origen"], destino=x["destino"],
                          diferencia=x["origen"] - x["destino"], estado=x["estado"]))
    for f in filas:
        f.update(run_id=run.id, empresa_id=run.empresa_id)
        f.setdefault("destino_esperado", None)
        f.setdefault("cargas_imputables", None)
        f.setdefault("periodo", None)
        f.setdefault("descripcion", None)
    if filas:
        db.execute(insert(ResultadoDestino), filas)


def _guardar_hallazgos(db, run, hallados) -> list[dict]:
    # Estado de revisión arrastrado desde la ejecución anterior (misma huella).
    previos = {}
    huellas = {huella(run.empresa_id, run.ejercicio, h) for h in hallados}
    lista_h = list(huellas)
    for i in range(0, len(lista_h), 500):
        for hf, est, resp, rid in db.execute(select(Hallazgo.huella, Hallazgo.estado, Hallazgo.responsable, Hallazgo.run_id)
                                             .where(Hallazgo.empresa_id == run.empresa_id, Hallazgo.huella.in_(lista_h[i:i + 500]),
                                                    Hallazgo.run_id != run.id)):
            if hf not in previos or rid > previos[hf][2]:
                previos[hf] = (est, resp, rid)
    filas = []
    vistos = set()
    for h in hallados:
        hf = huella(run.empresa_id, run.ejercicio, h)
        if hf in vistos:
            continue
        vistos.add(hf)
        nombre, _d1, explicacion, recomendacion = reglas.TIPOS[h.regla.tipo]
        clave = h.clave_exposicion or (f"L{h.linea_id}" if h.linea_id else f"D{h.cuenta}|{h.tercero}|{h.documento}"
                                       if (h.documento or h.tercero) else f"C{h.cuenta}")
        est, resp, _ = previos.get(hf, ("PENDIENTE", None, None))
        filas.append({"run_id": run.id, "empresa_id": run.empresa_id, "regla_id": h.regla.id, "regla_codigo": h.regla.codigo,
                      "regla_version": h.regla.version, "regla_nombre": h.regla.nombre, "cuenta": h.cuenta[:20],
                      "tercero": h.tercero, "documento": (h.documento or None) and h.documento[:80],
                      "asiento": (h.asiento or None) and h.asiento[:80], "linea_id": h.linea_id or None, "periodo": h.periodo,
                      "importe": Decimal(h.importe).quantize(Decimal("0.01")), "clave_exposicion": clave[:160],
                      "riesgo": h.riesgo or h.regla.riesgo, "titulo": h.titulo[:255],
                      "evidencia": json.dumps(h.evidencia, ensure_ascii=False, default=str),
                      "explicacion": explicacion, "recomendacion": recomendacion, "huella": hf, "estado": est, "responsable": resp})
    for i in range(0, len(filas), 2000):
        db.execute(insert(Hallazgo), filas[i:i + 2000])
    return filas


def exposicion(filas: list[dict]) -> Decimal:
    """Importe sujeto a revisión sin sumar dos veces exposiciones superpuestas (ver docstring del módulo)."""
    por_grupo = defaultdict(lambda: {"claves": defaultdict(lambda: CERO), "cuenta": CERO})
    for f in filas:
        grupo = f["cuenta"][:2]
        imp = Decimal(f["importe"])
        clave = f["clave_exposicion"]
        g = por_grupo[grupo]
        if clave.startswith("C") and "|" not in clave:  # hallazgo sobre el saldo de toda la cuenta
            g["cuenta"] = max(g["cuenta"], imp)
        else:
            g["claves"][clave] = max(g["claves"][clave], imp)
    return sum((max(sum(g["claves"].values(), CERO), g["cuenta"]) for g in por_grupo.values()), CERO)


def _guardar_resultados(db, run, nodos, filas_h):
    por_cuenta = defaultdict(list)
    for f in filas_h:
        por_cuenta[f["cuenta"]].append(f)
    filas = []
    for c, n in nodos.items():
        if not (n.hijos == 0 or n.propio) and c not in por_cuenta:
            continue
        hs = por_cuenta.get(c, [])
        filas.append({"run_id": run.id, "empresa_id": run.empresa_id, "cuenta": c, "perfil": pcge.perfil(c).clave,
                      "hallazgos": len(hs), "riesgo_maximo": min((h["riesgo"] for h in hs), key=ORDEN_RIESGO.get) if hs else None,
                      "importe_revision": exposicion(hs) if hs else CERO,
                      "indicadores": json.dumps({"saldo_final": str(saldos.dec(n.sf)), "movimientos": n.n,
                                                 "terceros": len(n.terceros)})})
    for c in set(por_cuenta) - set(nodos):  # hallazgos agregados (p. ej. «6/9» de origen-destino)
        hs = por_cuenta[c]
        filas.append({"run_id": run.id, "empresa_id": run.empresa_id, "cuenta": c, "perfil": "ANALITICA",
                      "hallazgos": len(hs), "riesgo_maximo": min((h["riesgo"] for h in hs), key=ORDEN_RIESGO.get),
                      "importe_revision": exposicion(hs), "indicadores": None})
    if filas:
        db.execute(insert(AnalisisResultado), filas)


def indicadores(run, nodos, lineas, filas_h, aging, od, control, exceptuados, n_reglas) -> dict:
    hojas = [n for n in nodos.values() if (n.hijos == 0 or n.propio) and n.codigo[0] != "0"]
    con_obs = {f["cuenta"] for f in filas_h if f["cuenta"] in nodos}
    por_riesgo = defaultdict(int)
    for f in filas_h:
        por_riesgo[f["riesgo"]] += 1
    contrarios = [f for f in filas_h if f["regla_codigo"] and f["riesgo"] and
                  f["regla_nombre"] in (reglas.TIPOS["SALDO_CONTRARIO"][0], reglas.TIPOS["SALDO_CONTRARIO_TERCERO"][0],
                                        reglas.TIPOS["SOBREGIRO"][0])]
    variaciones = [f for f in filas_h if f["regla_nombre"] == reglas.TIPOS["VARIACION_SIGNIFICATIVA"][0]]
    dif_od = sum((abs(x["diferencia"]) for x in od["resumen"] if x["estado"] not in ("CONFORME", "NO_APLICA")), CERO) + \
        sum((abs(x["diferencia_79"]) for x in od["resumen"] if x["estado"] == "DUPLICIDAD_PRESENTACION"), CERO)
    return {
        "cuentas_analizadas": len(hojas), "movimientos": len(lineas),
        "cuentas_con_observaciones": len(con_obs & {n.codigo for n in hojas}),
        "cuentas_sin_observaciones": len({n.codigo for n in hojas} - con_obs),
        "hallazgos": len(filas_h), "hallazgos_por_riesgo": dict(por_riesgo), "exceptuados": exceptuados, "reglas_aplicadas": n_reglas,
        "importe_sujeto_revision": str(exposicion(filas_h)),
        "saldos_antiguos": aging["saldo_antiguo"], "documentos_preliminares": aging["documentos_preliminares"],
        "saldos_contrarios": {"cantidad": len(contrarios), "importe": str(exposicion(contrarios))},
        "diferencias_origen_destino": str(dif_od),
        "variaciones_significativas": len(variaciones), "control_cuadre": control,
    }
