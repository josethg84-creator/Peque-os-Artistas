"""Reglas de análisis configurables.

Cada regla (tabla `account_analysis_rules`) tiene un `tipo` que elige el evaluador y parámetros
editables sin tocar código: cuentas o rango, condición, operador, valor, importe mínimo,
tolerancia %, riesgo, vigencia, estado y parámetros adicionales (JSON). El tipo UMBRAL permite
definir reglas nuevas combinando condición + operador + valor.

Los hallazgos son POSIBLES incidencias: requieren revisión profesional antes de considerarse
errores. Por eso cada uno trae evidencia, explicación contable y una recomendación, y nace en
estado «Pendiente de revisión».
"""
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analisis import pcge
from app.analisis.saldos import dec
from app.models import ReglaAnalisis

CERO = Decimal("0")

# tipo: (nombre, descripción, explicación contable, recomendación)
TIPOS = {
    "SALDO_CONTRARIO": ("Saldo contrario a la naturaleza", "Cuentas cuyo saldo final es opuesto a su naturaleza (deudora/acreedora).",
                        "Un saldo contrario puede reflejar errores de imputación, cobros o pagos no aplicados, anticipos o "
                        "reclasificaciones pendientes para la presentación de los estados financieros.",
                        "Analice la composición del saldo y, si corresponde, reclasifique para la presentación."),
    "MOVIMIENTO_EXTRAORDINARIO": ("Movimiento extraordinario", "Líneas cuyo importe excede la media de la cuenta en N desviaciones estándar.",
                                  "Un importe atípico respecto del comportamiento habitual de la cuenta merece verificarse con su sustento.",
                                  "Revise el documento de sustento y la aprobación de la operación."),
    "SIN_MOVIMIENTO": ("Cuenta con saldo y sin movimiento", "Cuentas con saldo que no registran movimientos en los últimos N meses.",
                       "Un saldo inmovilizado puede corresponder a partidas antiguas pendientes de depurar o castigar.",
                       "Confirme la vigencia del saldo (confirmaciones, conciliaciones) o evalúe su depuración."),
    "SALDO_ANTIGUO": ("Saldo antiguo", "Documentos con saldo pendiente de antigüedad mayor a N días.",
                      "Las partidas antiguas pueden requerir estimación de cobranza dudosa (cuentas por cobrar) o depuración.",
                      "Evalúe la recuperabilidad o exigibilidad del documento y su tratamiento contable y tributario."),
    "DOCUMENTO_DUPLICADO": ("Documento potencialmente duplicado", "El mismo documento con igual cuenta, lado e importe en asientos distintos.",
                            "Un comprobante registrado dos veces sobreestima gastos, activos o pasivos. Un documento con varias líneas "
                            "en el mismo asiento es legítimo y no se observa.",
                            "Verifique si se trata del mismo comprobante y, de ser así, extorne el registro duplicado."),
    "VARIACION_SIGNIFICATIVA": ("Variación significativa", "Variación del saldo respecto del periodo anterior mayor al umbral.",
                                "Variaciones fuera de lo esperado deben explicarse con hechos del negocio (análisis de fluctuaciones).",
                                "Documente la causa de la variación."),
    "SIN_TERCERO": ("Movimiento sin tercero", "Líneas sin RUC o identificación del tercero en cuentas que lo requieren.",
                    "Sin tercero no es posible analizar la composición, la antigüedad ni confirmar el saldo.",
                    "Complete el auxiliar (anexo) en el ERP."),
    "SIN_CENTRO_COSTO": ("Gasto sin centro de costo", "Líneas sin centro de costo en cuentas que lo exigen.",
                         "Sin centro de costo el gasto no puede distribuirse ni analizarse por área.",
                         "Asigne el centro de costo según la política de la empresa."),
    "FUERA_DE_PERIODO": ("Movimiento fuera del periodo", "Fecha contable que no corresponde al periodo del lote o de la línea.",
                         "Los registros fuera de periodo afectan el corte contable (devengo).",
                         "Verifique la fecha y el periodo de registro."),
    "CLASIFICACION": ("Posible error de clasificación", "Gastos de importe relevante cuya glosa sugiere un activo.",
                      "Desembolsos que generan beneficios futuros podrían corresponder a activo inmovilizado (NIC 16 / NIC 38).",
                      "Evalúe si el desembolso cumple los criterios de reconocimiento como activo."),
    "CONCENTRACION_TERCERO": ("Concentración en un tercero", "Un tercero concentra más del % indicado del movimiento de la cuenta.",
                              "La concentración aumenta el riesgo de dependencia y puede requerir confirmación de saldos.",
                              "Considere solicitar confirmación de saldos y revisar condiciones contractuales."),
    "ORIGEN_DESTINO": ("Diferencia origen–destino", "Diferencias entre gasto por naturaleza destinable, destino (clase 9) y cuenta 79.",
                       "Si el destino no coincide con la 79 el gasto podría presentarse duplicado; si el gasto destinable no tiene "
                       "destino, el estado de resultados por función queda incompleto.",
                       "Revise los asientos de destino y las reglas de distribución vigentes."),
    "CUENTA_RESTRINGIDA": ("Movimiento en cuenta restringida", "Movimientos en cuentas de título, sin movimiento o restringidas.",
                           "Las cuentas de título o restringidas no deberían recibir registros directos.",
                           "Reclasifique a la subcuenta de último nivel que corresponda."),
    "SOBREGIRO": ("Saldo acreedor en caja y bancos", "Cuentas del elemento 10 con saldo acreedor.",
                  "Un saldo acreedor en bancos suele ser un sobregiro o cheques girados no cobrados; para la presentación "
                  "se reclasifica a obligaciones financieras (45).",
                  "Concilie la cuenta bancaria y evalúe la reclasificación para la presentación."),
    "SALDO_CONTRARIO_TERCERO": ("Saldo contrario por tercero", "Clientes con saldo acreedor o proveedores con saldo deudor.",
                                "Puede tratarse de anticipos, cobros/pagos no aplicados o pagos duplicados. No se compensa "
                                "automáticamente con otros documentos (fase 4).",
                                "Identifique el origen del saldo y aplíquelo o reclasifíquelo como anticipo."),
    "COSTO_EN_PROCESO": ("Costos acumulados en la cuenta 23", "Costos de servicios/productos en proceso antiguos o sin actividad reciente.",
                         "La falta de facturación no justifica por sí sola mantener costos como activo: debe evaluarse la "
                         "situación del servicio (avance, culminación, obligación de desempeño, NIIF 15 / NIC 2) y transferirse "
                         "al costo cuando corresponda.",
                         "Evalúe el estado del contrato/proyecto y la transferencia de costos a resultados o a productos terminados."),
    "DEPRECIACION_EXCEDE": ("Depreciación acumulada mayor al costo", "Depreciación/amortización acumulada que supera el costo del activo.",
                            "La depreciación acumulada no puede exceder el costo depreciable del activo.",
                            "Revise la vida útil, los retiros y la correspondencia entre activo y depreciación."),
    "CUENTAS_ORDEN": ("Cuentas de orden mezcladas", "Asientos que combinan cuentas de orden con cuentas patrimoniales o de resultados.",
                      "Las cuentas de orden registran compromisos y contingencias y no deben afectar los estados financieros.",
                      "Registre las cuentas de orden en asientos propios y con su contracuenta de orden."),
    "SALDO_INTERMEDIARIO": ("Saldos intermediarios fuera del cierre", "Cuentas del elemento 8 con saldo en periodos distintos del cierre.",
                            "Los saldos intermediarios se determinan en el cierre según el procedimiento de la empresa.",
                            "Verifique el procedimiento de cierre aplicado."),
    "MOVIMIENTO_PATRIMONIAL": ("Movimiento patrimonial", "Movimientos en capital, capital adicional, excedente de revaluación o reservas.",
                               "Los movimientos patrimoniales son inusuales y requieren acuerdo societario o sustento técnico.",
                               "Verifique el acta de junta, la escritura o el sustento de la operación."),
    "DIFERENCIA_CAMBIO": ("Posible diferencia de cambio no registrada", "Saldos en moneda extranjera no actualizados al tipo de cambio de cierre.",
                          "Las partidas monetarias en moneda extranjera se expresan al tipo de cambio de cierre (NIC 21); "
                          "activos al tipo de compra y pasivos al de venta según la práctica tributaria peruana.",
                          "Calcule y registre la diferencia de cambio del periodo."),
    "UMBRAL": ("Regla de umbral personalizada", "Compara una medida de la cuenta con un valor (condición + operador).",
               "Regla definida por la empresa.", "Revise la cuenta según el criterio definido."),
}

CONDICIONES = {"SALDO_FINAL", "SALDO_DEUDOR", "SALDO_ACREEDOR", "MOVIMIENTO_DEBE", "MOVIMIENTO_HABER", "MOVIMIENTO_NETO",
               "VARIACION", "VARIACION_PCT", "CANTIDAD_MOVIMIENTOS", "CANTIDAD_TERCEROS"}
OPERADORES = {">", ">=", "<", "<=", "=", "!=", "ENTRE", "FUERA"}

# Reglas iniciales de cada empresa (se pueden editar, desactivar o eliminar).
DEFECTO = [
    dict(codigo="NAT-01", tipo="SALDO_CONTRARIO", grupo="SALDOS", riesgo="MEDIO", importe_minimo=Decimal("1.00")),
    dict(codigo="SOB-10", tipo="SOBREGIRO", grupo="ELEMENTO 1", cuentas="10", riesgo="ALTO"),
    dict(codigo="TER-01", tipo="SALDO_CONTRARIO_TERCERO", grupo="ELEMENTO 1", cuentas="12,13,14,16,17,42,43,44,46,47",
         riesgo="MEDIO", importe_minimo=Decimal("1.00")),
    dict(codigo="ANT-01", tipo="SALDO_ANTIGUO", grupo="ANTIGÜEDAD", cuentas="12,13,14,16,17,42,43,44,46,47", riesgo="MEDIO",
         valor=Decimal("365"), parametros={"base": "VENCIMIENTO"}),
    dict(codigo="C23-01", tipo="COSTO_EN_PROCESO", grupo="ELEMENTO 2", cuentas="23", riesgo="ALTO", valor=Decimal("180"),
         parametros={"dias_inactividad": 90}),
    dict(codigo="DEP-01", tipo="DEPRECIACION_EXCEDE", grupo="ELEMENTO 3", cuentas="32,33,34,35", riesgo="ALTO",
         parametros={"depreciacion": "39"}),
    dict(codigo="PAT-01", tipo="MOVIMIENTO_PATRIMONIAL", grupo="ELEMENTO 5", cuentas="50,52,57,58", riesgo="INFORMATIVO"),
    dict(codigo="DUP-01", tipo="DOCUMENTO_DUPLICADO", grupo="DOCUMENTOS", riesgo="ALTO"),
    dict(codigo="EXT-01", tipo="MOVIMIENTO_EXTRAORDINARIO", grupo="MOVIMIENTOS", riesgo="MEDIO", valor=Decimal("3"),
         importe_minimo=Decimal("1000.00"), parametros={"min_lineas": 10}),
    dict(codigo="SMV-01", tipo="SIN_MOVIMIENTO", grupo="SALDOS", riesgo="BAJO", valor=Decimal("3"), importe_minimo=Decimal("1.00")),
    dict(codigo="VAR-01", tipo="VARIACION_SIGNIFICATIVA", grupo="VARIACIONES", riesgo="MEDIO", tolerancia_pct=Decimal("30"),
         importe_minimo=Decimal("5000.00"), parametros={"nivel": 2}),
    dict(codigo="STE-01", tipo="SIN_TERCERO", grupo="DOCUMENTOS", cuentas="12,13,14,16,17,42,43,44,46,47", riesgo="MEDIO"),
    dict(codigo="SCC-01", tipo="SIN_CENTRO_COSTO", grupo="GASTOS", cuentas="62,63,64,65,66,67,68", riesgo="BAJO",
         parametros={"solo_si_plan_lo_exige": True}),
    dict(codigo="FPE-01", tipo="FUERA_DE_PERIODO", grupo="MOVIMIENTOS", riesgo="MEDIO"),
    dict(codigo="CLA-01", tipo="CLASIFICACION", grupo="GASTOS", cuentas="6", riesgo="MEDIO", valor=Decimal("2000"),
         parametros={"palabras": ["EQUIPO", "MAQUINA", "MAQUINARIA", "VEHICULO", "COMPUTADORA", "LAPTOP", "SERVIDOR",
                                  "MOBILIARIO", "MUEBLE", "LICENCIA PERPETUA", "EDIFICACION", "CONSTRUCCION"]}),
    dict(codigo="CON-01", tipo="CONCENTRACION_TERCERO", grupo="TERCEROS", cuentas="12,42,60,63,70", riesgo="BAJO",
         tolerancia_pct=Decimal("60"), importe_minimo=Decimal("10000.00"), parametros={"min_terceros": 3}),
    dict(codigo="OD-01", tipo="ORIGEN_DESTINO", grupo="ORIGEN-DESTINO", riesgo="ALTO", importe_minimo=Decimal("1.00")),
    dict(codigo="RES-01", tipo="CUENTA_RESTRINGIDA", grupo="MOVIMIENTOS", riesgo="ALTO"),
    dict(codigo="ORD-01", tipo="CUENTAS_ORDEN", grupo="ELEMENTO 0", cuentas="0", riesgo="MEDIO"),
    dict(codigo="INT-01", tipo="SALDO_INTERMEDIARIO", grupo="ELEMENTO 8", cuentas="8", riesgo="INFORMATIVO"),
    dict(codigo="TC-01", tipo="DIFERENCIA_CAMBIO", grupo="MONEDA EXTRANJERA", riesgo="MEDIO", importe_minimo=Decimal("10.00")),
]


def sembrar(db: Session, empresa_id: int) -> None:
    existentes = set(db.scalars(select(ReglaAnalisis.codigo).where(ReglaAnalisis.empresa_id == empresa_id)))
    nuevas = False
    for d in DEFECTO:
        if d["codigo"] in existentes:
            continue
        nombre, descripcion, *_ = TIPOS[d["tipo"]]
        datos = {**d}
        params = datos.pop("parametros", None)
        db.add(ReglaAnalisis(empresa_id=empresa_id, nombre=nombre, descripcion=descripcion,
                             parametros=json.dumps(params, ensure_ascii=False) if params else None, **datos))
        nuevas = True
    if nuevas:
        db.commit()


def vigente(r: ReglaAnalisis, fecha: date) -> bool:
    return r.activa and (r.vigente_desde is None or r.vigente_desde <= fecha) and (r.vigente_hasta is None or r.vigente_hasta >= fecha)


def snapshot(r: ReglaAnalisis) -> dict:
    return {k: (str(v) if isinstance(v, Decimal) else v.isoformat() if isinstance(v, date) else v)
            for k, v in ((c.key, getattr(r, c.key)) for c in ReglaAnalisis.__table__.columns)
            if k not in ("historial", "actualizado_en")}


# ===================================================================== evaluación
@dataclass
class Hallazgo:
    regla: ReglaAnalisis
    cuenta: str
    importe: Decimal
    titulo: str
    evidencia: dict
    tercero: str | None = None
    documento: str | None = None
    asiento: str | None = None
    linea_id: int | None = None
    periodo: int | None = None
    clave_exposicion: str | None = None
    riesgo: str | None = None


@dataclass
class Contexto:
    empresa_id: int
    ejercicio: int
    desde: int
    hasta: int
    nodos: dict                       # código → Nodo (saldos.construir_arbol)
    lineas: list                      # motor.Linea del rango
    plan: dict
    restringidas: list[str]
    aging: dict | None = None         # antiguedad.calcular(...)
    destino: dict | None = None       # destino.analizar(...)
    meses_con_movimiento: dict = field(default_factory=dict)  # cuenta → set(periodos) del ejercicio hasta el corte
    saldos_me: dict = field(default_factory=dict)             # cuenta → (saldo_me, saldo_mn, moneda)
    tipo_cambio_cierre: dict = field(default_factory=dict)    # moneda → (fecha, compra, venta)
    lotes_periodo: dict = field(default_factory=dict)         # lote_id → periodo del lote
    lineas_hasta_corte: list = field(default_factory=list)    # apertura + movimientos del ejercicio hasta el corte


def _prefijos(r: ReglaAnalisis) -> list[str]:
    return [p.strip() for p in (r.cuentas or "").split(",") if p.strip()]


def en_alcance(r: ReglaAnalisis, cuenta: str) -> bool:
    pref = _prefijos(r)
    if pref and not any(cuenta.startswith(p) for p in pref):
        return False
    if r.cuenta_desde and cuenta[:len(r.cuenta_desde)] < r.cuenta_desde:
        return False
    if r.cuenta_hasta and cuenta[:len(r.cuenta_hasta)] > r.cuenta_hasta:
        return False
    return True


def _params(r) -> dict:
    return json.loads(r.parametros) if r.parametros else {}


def _hojas(ctx: Contexto):
    """Nodos que representan cuentas de movimiento (evita evaluar dos veces el mismo saldo en sus niveles superiores)."""
    return [n for n in ctx.nodos.values() if n.hijos == 0 or n.propio]


def _ok_importe(r, v: Decimal) -> bool:
    return abs(v) >= (r.importe_minimo or CERO)


def _comparar(valor: Decimal, op: str, a: Decimal, b: Decimal | None) -> bool:
    return {">": valor > a, ">=": valor >= a, "<": valor < a, "<=": valor <= a, "=": valor == a, "!=": valor != a,
            "ENTRE": b is not None and a <= valor <= b, "FUERA": b is not None and not (a <= valor <= b)}[op]


def evaluar(r: ReglaAnalisis, ctx: Contexto) -> list[Hallazgo]:
    fn = EVALUADORES.get(r.tipo)
    return fn(r, ctx) if fn else []


def ev_saldo_contrario(r, ctx):
    out = []
    for n in _hojas(ctx):
        if not en_alcance(r, n.codigo) or n.codigo[0] in "08" or pcge.perfil(n.codigo).cartera:
            continue  # la cartera se evalúa por tercero (regla SALDO_CONTRARIO_TERCERO)
        sf = dec(n.sf)
        if (n.naturaleza == "D" and sf < 0) or (n.naturaleza == "A" and sf > 0):
            if _ok_importe(r, sf):
                out.append(Hallazgo(r, n.codigo, abs(sf), f"Cuenta {n.codigo} con saldo {'acreedor' if sf < 0 else 'deudor'} "
                                    f"contrario a su naturaleza {'deudora' if n.naturaleza == 'D' else 'acreedora'}",
                                    {"saldo_final": str(sf), "naturaleza": n.naturaleza, "descripcion": n.descripcion}))
    return out


def ev_sobregiro(r, ctx):
    return [Hallazgo(r, n.codigo, abs(dec(n.sf)), f"Saldo acreedor en {n.codigo} ({n.descripcion or 'caja y bancos'})",
                     {"saldo_final": str(dec(n.sf))})
            for n in _hojas(ctx) if en_alcance(r, n.codigo) and n.sf < 0 and _ok_importe(r, dec(n.sf))]


def ev_contrario_tercero(r, ctx):
    saldo = defaultdict(lambda: CERO)
    rs = {}
    for ln in ctx.lineas_hasta_corte:
        if ln.tercero and en_alcance(r, ln.cuenta):
            saldo[(ln.cuenta, ln.tercero)] += ln.debe - ln.haber
            rs[ln.tercero] = ln.razon_social or rs.get(ln.tercero)
    out = []
    for (c, t), v in saldo.items():
        nat = pcge.naturaleza_pcge(c)
        if ((nat == "D" and v < 0) or (nat == "A" and v > 0)) and _ok_importe(r, v):
            tipo = "cliente con saldo acreedor" if c[0] == "1" else "proveedor con saldo deudor"
            out.append(Hallazgo(r, c, abs(v), f"{tipo.capitalize()}: {rs.get(t) or t}", {"saldo": str(v), "tercero": t},
                                tercero=t, clave_exposicion=f"D{c}|{t}|*"))
    return out


def ev_saldo_antiguo(r, ctx):
    if not ctx.aging:
        return []
    dias = int(r.valor or 365)
    return [Hallazgo(r, d["cuenta"], abs(Decimal(d["importe"])), f"Documento {d['documento']} con {d['dias']} días de antigüedad",
                     {"dias": d["dias"], "fecha_base": d["fecha_base"], "importe": d["importe"], "preliminar": d["preliminar"],
                      "motivos": d["motivos"], "razon_social": d["razon_social"]},
                     tercero=d["tercero"], documento=d["documento"], clave_exposicion=f"D{d['cuenta']}|{d['tercero']}|{d['documento']}")
            for d in ctx.aging["documentos"]
            if d["dias"] > dias and en_alcance(r, d["cuenta"]) and _ok_importe(r, Decimal(d["importe"]))]


def ev_duplicado(r, ctx):
    """Compara contra todo el ejercicio hasta el corte (una factura de febrero ya registrada en enero
    es el caso típico) y reporta solo las repeticiones que caen en el rango analizado."""
    vistos: dict[tuple, object] = {}
    out = []
    for ln in sorted((x for x in ctx.lineas_hasta_corte if x.id), key=lambda x: (x.periodo, x.fecha or date.min, x.id)):
        if not ln.numero or not en_alcance(r, ln.cuenta):
            continue
        clave = (ln.tercero, ln.tipo_doc, ln.serie, ln.numero, ln.cuenta, "D" if ln.debe else "H", ln.debe or ln.haber)
        previo = vistos.get(clave)
        if previo is None:
            vistos[clave] = ln
        elif (previo.lote_id, previo.periodo, previo.subdiario, previo.asiento) != (ln.lote_id, ln.periodo, ln.subdiario, ln.asiento) \
                and ctx.desde <= ln.periodo <= ctx.hasta and _ok_importe(r, ln.debe or ln.haber):
            out.append(Hallazgo(r, ln.cuenta, ln.debe or ln.haber, f"Documento {ln.doc} repetido en otro asiento",
                                {"asiento_original": previo.etiqueta_asiento, "linea_original": previo.id,
                                 "asiento_repetido": ln.etiqueta_asiento, "importe": str(ln.debe or ln.haber)},
                                tercero=ln.tercero, documento=ln.doc, asiento=ln.etiqueta_asiento, linea_id=ln.id, periodo=ln.periodo))
    return out


def ev_extraordinario(r, ctx):
    k = float(r.valor or 3)
    minimo = int(_params(r).get("min_lineas", 10))
    por_cuenta = defaultdict(list)
    for ln in ctx.lineas:
        if en_alcance(r, ln.cuenta):
            por_cuenta[ln.cuenta].append(ln)
    out = []
    for c, lns in por_cuenta.items():
        if len(lns) < minimo:
            continue
        montos = [float(ln.debe + ln.haber) for ln in lns]
        media, desv = statistics.fmean(montos), statistics.pstdev(montos)
        if desv == 0:
            continue
        for ln, m in zip(lns, montos):
            if m > media + k * desv and _ok_importe(r, ln.debe + ln.haber):
                out.append(Hallazgo(r, c, ln.debe + ln.haber, f"Movimiento de {ln.debe + ln.haber} muy superior al habitual en {c}",
                                    {"importe": str(ln.debe + ln.haber), "media": round(media, 2), "desviacion": round(desv, 2),
                                     "umbral": round(media + k * desv, 2), "glosa": ln.glosa},
                                    tercero=ln.tercero, documento=ln.doc, asiento=ln.etiqueta_asiento, linea_id=ln.id, periodo=ln.periodo))
    return out


def ev_sin_movimiento(r, ctx):
    meses = int(r.valor or 3)
    ventana = set(range(max(1, ctx.hasta - meses + 1), ctx.hasta + 1))
    out = []
    for n in _hojas(ctx):
        if not en_alcance(r, n.codigo) or n.codigo[0] in "0":
            continue
        if n.sf and not (ctx.meses_con_movimiento.get(n.codigo, set()) & ventana) and _ok_importe(r, dec(n.sf)):
            out.append(Hallazgo(r, n.codigo, abs(dec(n.sf)), f"Cuenta {n.codigo} con saldo y sin movimientos en {meses} meses",
                                {"saldo_final": str(dec(n.sf)), "meses_sin_movimiento": meses,
                                 "ultimo_mes_con_movimiento": max(ctx.meses_con_movimiento.get(n.codigo, {0}))}))
    return out


def ev_variacion(r, ctx):
    nivel = int(_params(r).get("nivel", 2))
    tol = Decimal(str(r.tolerancia_pct or 0))
    out = []
    for n in ctx.nodos.values():
        if len(n.codigo) != nivel or n.anterior is None or not en_alcance(r, n.codigo):
            continue
        var = dec(n.sf - n.anterior)
        if not _ok_importe(r, var):
            continue
        if n.anterior == 0:
            out.append(Hallazgo(r, n.codigo, abs(var), f"Cuenta {n.codigo} con saldo nuevo de {var} (base cero: % no aplicable)",
                                {"saldo_actual": str(dec(n.sf)), "saldo_anterior": "0.00", "variacion": str(var), "variacion_pct": None}))
            continue
        pct = Decimal(n.sf - n.anterior) / abs(Decimal(n.anterior)) * 100
        if abs(pct) >= tol:
            out.append(Hallazgo(r, n.codigo, abs(var), f"Variación de {pct:.1f} % en {n.codigo} respecto del periodo anterior",
                                {"saldo_actual": str(dec(n.sf)), "saldo_anterior": str(dec(n.anterior)), "variacion": str(var),
                                 "variacion_pct": round(float(pct), 2)}))
    return out


def _agrupar_lineas(r, ctx, condicion, titulo):
    grupos = defaultdict(list)
    for ln in ctx.lineas:
        if en_alcance(r, ln.cuenta) and condicion(ln):
            grupos[ln.cuenta].append(ln)
    out = []
    for c, lns in grupos.items():
        total = sum((ln.debe + ln.haber for ln in lns), CERO)
        if _ok_importe(r, total):
            out.append(Hallazgo(r, c, total, titulo(c, lns), {"lineas": len(lns), "importe": str(total),
                                                             "muestra": [ln.id for ln in lns[:25]],
                                                             "asientos": sorted({ln.etiqueta_asiento for ln in lns if ln.asiento})[:25]}))
    return out


def ev_sin_tercero(r, ctx):
    return _agrupar_lineas(r, ctx, lambda ln: not ln.tercero, lambda c, l: f"{len(l)} movimiento(s) sin tercero en {c}")


def ev_sin_cc(r, ctx):
    solo_plan = bool(_params(r).get("solo_si_plan_lo_exige", False))

    def exige(ln):
        if ln.cc:
            return False
        p = ctx.plan.get(ln.cuenta)
        return (p is not None and p.requiere_centro_costo) if solo_plan else True
    return _agrupar_lineas(r, ctx, exige, lambda c, l: f"{len(l)} gasto(s) sin centro de costo en {c}")


def ev_fuera_periodo(r, ctx):
    def fuera(ln):
        lote_p = ctx.lotes_periodo.get(ln.lote_id)
        if ln.fecha and ln.periodo and 1 <= ln.periodo <= 12 and (ln.fecha.month != ln.periodo or ln.fecha.year != ctx.ejercicio):
            return True
        return bool(lote_p and 1 <= lote_p <= 12 and ln.periodo != lote_p)
    return _agrupar_lineas(r, ctx, fuera, lambda c, l: f"{len(l)} movimiento(s) de {c} fuera del periodo del lote o de la fecha")


def ev_restringida(r, ctx):
    def restringida(ln):
        p = ctx.plan.get(ln.cuenta)
        return (p is not None and (not p.admite_movimiento or not p.activa)) or any(ln.cuenta.startswith(x) for x in ctx.restringidas)
    return _agrupar_lineas(r, ctx, restringida, lambda c, l: f"{len(l)} movimiento(s) en la cuenta restringida {c}")


def ev_clasificacion(r, ctx):
    palabras = [p.upper() for p in _params(r).get("palabras", [])]
    umbral = Decimal(str(r.valor or 0))
    out = []
    for ln in ctx.lineas:
        if ln.debe >= umbral and en_alcance(r, ln.cuenta) and ln.glosa:
            g = ln.glosa.upper()
            hit = next((p for p in palabras if p in g), None)
            if hit and _ok_importe(r, ln.debe):
                out.append(Hallazgo(r, ln.cuenta, ln.debe, f"Gasto de {ln.debe} con glosa que sugiere un activo («{hit}»)",
                                    {"glosa": ln.glosa, "palabra": hit, "importe": str(ln.debe)},
                                    tercero=ln.tercero, documento=ln.doc, asiento=ln.etiqueta_asiento, linea_id=ln.id, periodo=ln.periodo))
    return out


def ev_concentracion(r, ctx):
    minimo = int(_params(r).get("min_terceros", 3))
    tol = Decimal(str(r.tolerancia_pct or 60))
    mov = defaultdict(lambda: defaultdict(lambda: CERO))
    for ln in ctx.lineas:
        if ln.tercero and en_alcance(r, ln.cuenta):
            mov[ln.cuenta[:2]][ln.tercero] += ln.debe + ln.haber
    out = []
    for c, por_t in mov.items():
        total = sum(por_t.values(), CERO)
        if len(por_t) < minimo or not _ok_importe(r, total):
            continue
        t, v = max(por_t.items(), key=lambda x: x[1])
        pct = v / total * 100
        if pct >= tol:
            out.append(Hallazgo(r, c, v, f"El tercero {t} concentra {pct:.1f} % del movimiento de {c}",
                                {"tercero": t, "importe": str(v), "total": str(total), "participacion_pct": round(float(pct), 2),
                                 "terceros": len(por_t)}, tercero=t, clave_exposicion=f"C{c}|concentracion"))
    return out


def ev_origen_destino(r, ctx):
    if not ctx.destino or not ctx.destino["politica"]["usa_destino"]:
        return []
    out = []
    for x in ctx.destino["resumen"]:
        if x["estado"] in ("CONFORME", "NO_APLICA"):
            continue
        if x["estado"] == "DUPLICIDAD_PRESENTACION":
            imp, titulo = abs(x["diferencia_79"]), f"Periodo {x['periodo']:02d}: destino {x['destino']} ≠ cuenta 79 {x['cargas_imputables']}"
        else:
            imp, titulo = abs(x["diferencia"]), f"Periodo {x['periodo']:02d}: gasto destinable {x['origen']} vs destino {x['destino']} ({x['estado']})"
        if _ok_importe(r, imp):
            out.append(Hallazgo(r, "6/9", imp, titulo, {k: str(v) if isinstance(v, Decimal) else v for k, v in x.items()},
                                periodo=x["periodo"], clave_exposicion=f"OD|{x['periodo']}"))
    for a in ctx.destino["asientos"]:
        imp = abs(a["destino"] - a["origen"]) if a["estado"] != "SIN_DESTINO" else abs(a["origen"])
        if _ok_importe(r, imp):
            out.append(Hallazgo(r, "6/9", imp, f"Asiento {a['asiento']}: {a['estado'].replace('_', ' ').lower()}",
                                {k: str(v) if isinstance(v, Decimal) else v for k, v in a.items()}, asiento=a["asiento"],
                                linea_id=a["linea_id"], periodo=a["periodo"], clave_exposicion=f"OD|{a['periodo']}"))
    for cc in ctx.destino["centros_costo"]:
        if cc["estado"] == "DIFERENCIA" and _ok_importe(r, cc["diferencia"]):
            out.append(Hallazgo(r, "6/9", abs(cc["diferencia"]), f"Centro de costo {cc['clave']}: origen {cc['origen']} vs destino {cc['destino']}",
                                {k: str(v) if isinstance(v, Decimal) else v for k, v in cc.items()}, riesgo="MEDIO",
                                clave_exposicion=f"ODCC|{cc['clave']}"))
    return out


def ev_costo_proceso(r, ctx):
    dias = int(r.valor or 180)
    inactividad = int(_params(r).get("dias_inactividad", 90))
    from datetime import date as _d
    corte = _d(ctx.ejercicio, min(ctx.hasta, 12), 28)
    grupos = defaultdict(lambda: {"saldo": CERO, "primero": None, "ultimo": None, "transferido": CERO, "lineas": 0})
    for ln in ctx.lineas_hasta_corte:
        if not en_alcance(r, ln.cuenta):
            continue
        k = (ln.cuenta, ln.proyecto or ln.cc or ln.tercero or "(sin proyecto)")
        g = grupos[k]
        g["saldo"] += ln.debe - ln.haber
        g["lineas"] += 1
        if ln.debe and ln.fecha:
            g["primero"] = min(g["primero"] or ln.fecha, ln.fecha)
        if ln.fecha:
            g["ultimo"] = max(g["ultimo"] or ln.fecha, ln.fecha)
        g["transferido"] += ln.haber
    out = []
    for (c, proy), g in grupos.items():
        if g["saldo"] <= 0 or not g["primero"]:
            continue
        edad, quieto = (corte - g["primero"]).days, (corte - (g["ultimo"] or corte)).days
        if (edad > dias or quieto > inactividad) and _ok_importe(r, g["saldo"]):
            out.append(Hallazgo(r, c, g["saldo"], f"Costos acumulados de {proy} en {c}: {edad} días desde el primer costo",
                                {"proyecto": proy, "saldo": str(g["saldo"]), "primer_costo": g["primero"].isoformat(),
                                 "ultimo_movimiento": g["ultimo"].isoformat() if g["ultimo"] else None, "dias_antiguedad": edad,
                                 "dias_sin_movimiento": quieto, "transferido_acumulado": str(g["transferido"])},
                                documento=proy, clave_exposicion=f"D{c}|*|{proy}"))
    return out


def ev_depreciacion(r, ctx):
    dep = str(_params(r).get("depreciacion", "39"))
    costo, acum = defaultdict(lambda: CERO), defaultdict(lambda: CERO)
    for ln in ctx.lineas_hasta_corte:
        k = ln.maquinaria or "(general)"
        if en_alcance(r, ln.cuenta):
            costo[k] += ln.debe - ln.haber
        elif ln.cuenta.startswith(dep):
            acum[k] += ln.haber - ln.debe
    out = []
    for k in set(costo) | set(acum):
        if acum[k] - costo[k] > 0 and _ok_importe(r, acum[k] - costo[k]) and (k != "(general)" or not costo):
            out.append(Hallazgo(r, dep, acum[k] - costo[k], f"Depreciación acumulada mayor al costo en el activo {k}",
                                {"activo": k, "costo": str(costo[k]), "depreciacion_acumulada": str(acum[k])},
                                documento=k, clave_exposicion=f"D{dep}|*|{k}"))
    tc = sum(costo.values(), CERO)
    ta = sum(acum.values(), CERO)
    if ta > tc and _ok_importe(r, ta - tc):
        out.append(Hallazgo(r, dep, ta - tc, "Depreciación acumulada total mayor al costo total del activo inmovilizado",
                            {"costo_total": str(tc), "depreciacion_total": str(ta)}, clave_exposicion=f"C{dep}"))
    return out


def ev_cuentas_orden(r, ctx):
    asientos = defaultdict(list)
    for ln in ctx.lineas:
        if ln.asiento:
            asientos[(ln.lote_id, ln.periodo, ln.subdiario, ln.asiento)].append(ln)
    out = []
    for lns in asientos.values():
        orden = [ln for ln in lns if ln.cuenta.startswith("0")]
        if orden and len(orden) < len(lns):
            imp = sum((ln.debe for ln in orden), CERO)
            out.append(Hallazgo(r, orden[0].cuenta, imp, f"Asiento {orden[0].etiqueta_asiento} mezcla cuentas de orden y patrimoniales",
                                {"cuentas": sorted({ln.cuenta for ln in lns})}, asiento=orden[0].etiqueta_asiento,
                                linea_id=orden[0].id, periodo=orden[0].periodo))
    return out


def ev_intermediario(r, ctx):
    if ctx.hasta >= 13:
        return []
    return [Hallazgo(r, n.codigo, abs(dec(n.sf)), f"Saldo intermediario {n.codigo} con saldo antes del cierre", {"saldo_final": str(dec(n.sf))})
            for n in _hojas(ctx) if en_alcance(r, n.codigo) and n.sf and _ok_importe(r, dec(n.sf))]


def ev_patrimonial(r, ctx):
    return _agrupar_lineas(r, ctx, lambda ln: True, lambda c, l: f"{len(l)} movimiento(s) patrimonial(es) en {c} a sustentar")


def ev_diferencia_cambio(r, ctx):
    out = []
    for c, (sme, smn, moneda) in ctx.saldos_me.items():
        if not sme or moneda not in ctx.tipo_cambio_cierre:
            continue
        fecha, compra, venta = ctx.tipo_cambio_cierre[moneda]
        tc = compra if c[0] in "123" else venta  # activos al TC compra, pasivos al TC venta
        esperado = (sme * tc).quantize(Decimal("0.01"))
        dif = esperado - smn
        if _ok_importe(r, dif):
            out.append(Hallazgo(r, c, abs(dif), f"Cuenta {c} en {moneda}: saldo MN {smn} vs ME {sme} × TC {tc} = {esperado}",
                                {"saldo_me": str(sme), "saldo_mn": str(smn), "tipo_cambio_cierre": str(tc),
                                 "fecha_tipo_cambio": fecha.isoformat(), "diferencia": str(dif)}))
    return out


def ev_umbral(r, ctx):
    medida = r.condicion or "SALDO_FINAL"
    op = r.operador or ">"
    a, b = Decimal(str(r.valor or 0)), (Decimal(str(r.valor2)) if r.valor2 is not None else None)
    out = []
    for n in _hojas(ctx):
        if not en_alcance(r, n.codigo):
            continue
        valores = {"SALDO_FINAL": dec(n.sf), "SALDO_DEUDOR": max(dec(n.sf), CERO), "SALDO_ACREEDOR": max(-dec(n.sf), CERO),
                   "MOVIMIENTO_DEBE": dec(n.debe), "MOVIMIENTO_HABER": dec(n.haber), "MOVIMIENTO_NETO": dec(n.debe - n.haber),
                   "VARIACION": dec(n.sf - n.anterior) if n.anterior is not None else None,
                   "VARIACION_PCT": (Decimal(n.sf - n.anterior) / abs(Decimal(n.anterior)) * 100) if n.anterior else None,
                   "CANTIDAD_MOVIMIENTOS": Decimal(n.n), "CANTIDAD_TERCEROS": Decimal(len(n.terceros))}
        v = valores.get(medida)
        if v is None or not _comparar(v, op, a, b):
            continue
        imp = abs(dec(n.sf)) if "CANTIDAD" in medida or "PCT" in medida else abs(v)
        if _ok_importe(r, imp):
            out.append(Hallazgo(r, n.codigo, imp, f"{r.nombre}: {medida.replace('_', ' ').lower()} {op} {a}{f' y {b}' if b is not None else ''}",
                                {"medida": medida, "valor": str(v), "operador": op, "umbral": str(a), "umbral2": str(b) if b is not None else None}))
    return out


EVALUADORES = {
    "SALDO_CONTRARIO": ev_saldo_contrario, "SOBREGIRO": ev_sobregiro, "SALDO_CONTRARIO_TERCERO": ev_contrario_tercero,
    "SALDO_ANTIGUO": ev_saldo_antiguo, "DOCUMENTO_DUPLICADO": ev_duplicado, "MOVIMIENTO_EXTRAORDINARIO": ev_extraordinario,
    "SIN_MOVIMIENTO": ev_sin_movimiento, "VARIACION_SIGNIFICATIVA": ev_variacion, "SIN_TERCERO": ev_sin_tercero,
    "SIN_CENTRO_COSTO": ev_sin_cc, "FUERA_DE_PERIODO": ev_fuera_periodo, "CUENTA_RESTRINGIDA": ev_restringida,
    "CLASIFICACION": ev_clasificacion, "CONCENTRACION_TERCERO": ev_concentracion, "ORIGEN_DESTINO": ev_origen_destino,
    "COSTO_EN_PROCESO": ev_costo_proceso, "DEPRECIACION_EXCEDE": ev_depreciacion, "CUENTAS_ORDEN": ev_cuentas_orden,
    "SALDO_INTERMEDIARIO": ev_intermediario, "MOVIMIENTO_PATRIMONIAL": ev_patrimonial, "DIFERENCIA_CAMBIO": ev_diferencia_cambio,
    "UMBRAL": ev_umbral,
}


def catalogo() -> list[dict]:
    return [{"tipo": t, "nombre": n, "descripcion": d, "explicacion": e, "recomendacion": rc,
             "parametrizable": t == "UMBRAL"} for t, (n, d, e, rc) in TIPOS.items()]
