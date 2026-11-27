"""Módulos INTEGRIDAD y ASIENTOS.

Integridad: errores estructurales confirmables (descuadres, cuentas inexistentes, importes inválidos…) separados de
observaciones que requieren interpretación (glosas, fechas, tipos de cambio).
Asientos: indicadores de riesgo. Un asiento manual o registrado al cierre NO es irregular por sí mismo: estas reglas
exigen al menos un factor adicional (importe significativo, falta de documento, glosa genérica, cuenta poco frecuente,
combinación atípica). Los campos de usuario, fecha real de registro y origen solo se analizan si el ERP los exportó.
"""
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.analisis import saldos
from app.auditoria.base import CERO, Res, Salida, asiento_de, dec, doc_de, ev_calc, ev_linea, fin_mes
from app.importers.normalizacion import normalizar_texto
from app.models import ConfiguracionContable, LineaDiario, LoteContable, SaldoCuenta, TipoCambio

GLOSAS_GENERICAS = {"AJUSTE", "AJUSTES", "VARIOS", "OTROS", "REGULARIZACION", "CORRECCION", "ASIENTO", "S G", "SG", "XXX", "X",
                    "PROVISION", "RECLASIFICACION", "ASIENTO DE AJUSTE", "AJUSTE CONTABLE", "VARIOS GASTOS", "-", "."}


def _total(lineas) -> Decimal:
    return sum((ln.debe for ln in lineas), CERO)


def _etiqueta(k) -> str:
    return "-".join(p for p in (k[2], k[3]) if p)


def _res_asiento(k, lineas, titulo, condicion, importe=None, **kw) -> Res:
    ln0 = max(lineas, key=lambda x: x.debe + x.haber)
    return Res(titulo=titulo, condicion=condicion, importe=_total(lineas) if importe is None else importe, cuenta=ln0.cuenta,
               asiento=_etiqueta(k), linea_id=ln0.id, documento=doc_de(ln0), tercero=ln0.tercero, razon_social=ln0.razon_social,
               centro_costo=ln0.cc, proyecto=ln0.proyecto, evidencia=[ev_linea(x) for x in lineas[:20]],
               clave=f"ASI|{k[0]}|{k[1]}|{_etiqueta(k)}", exposicion=f"ASIENTO|{k[0]}|{k[1]}|{_etiqueta(k)}", **kw)


# ===================================================================== INTEGRIDAD
def descuadre(ax, r) -> Salida:
    cfg = ax.db.scalar(select(ConfiguracionContable).where(ConfiguracionContable.empresa_id == ax.empresa_id))
    tol = dec(r.p.get("tolerancia", cfg.tolerancia_descuadre if cfg else "0.01"))
    out = []
    for k, ls in ax.asientos.items():
        d, h = sum((x.debe for x in ls), CERO), sum((x.haber for x in ls), CERO)
        if abs(d - h) > tol and ax.asiento_en_alcance(ls):
            out.append(_res_asiento(k, ls, f"Asiento {_etiqueta(k)} descuadrado", f"El asiento {_etiqueta(k)} del periodo {k[1]:02d} suma "
                                    f"debe {d} y haber {h}: diferencia {d - h}.", importe=abs(d - h), estructural=True,
                                    efecto="Los saldos del mayor y del balance de comprobación quedan distorsionados.",
                                    detalle={"debe": str(d), "haber": str(h), "diferencia": str(d - h)}))
            out[-1].evidencia.insert(0, ev_calc("Suma del asiento", debe=d, haber=h, diferencia=d - h, tolerancia=tol))
    return Salida(out, len(ax.asientos), sum((_total(x) for x in ax.asientos.values()), CERO),
                  f"Suma de debe y haber por asiento (lote, periodo, subdiario, número); tolerancia {tol}.")


def _por_cuenta(ax, pred, titulo, condicion, estructural=True, **kw):
    malas = defaultdict(list)
    for ln in ax.lineas:
        if pred(ln):
            malas[ln.cuenta].append(ln)
    out = []
    for c, ls in sorted(malas.items()):
        out.append(Res(titulo=titulo.format(c=c), condicion=condicion.format(c=c, n=len(ls)), importe=sum((x.debe + x.haber for x in ls), CERO),
                       cuenta=c, linea_id=ls[0].id, asiento=asiento_de(ls[0]), evidencia=[ev_linea(x) for x in ls[:20]],
                       clave=f"{titulo[:20]}|{c}", exposicion=f"CUENTA|{c}", estructural=estructural, detalle={"lineas": len(ls)}, **kw))
    return out


def cuentas_inexistentes(ax, r) -> Salida:
    if not ax.plan:
        return Salida(estado="SIN_DATOS", mensaje="No se importó el plan de cuentas: no puede verificarse la existencia de las cuentas.")
    out = _por_cuenta(ax, lambda ln: ln.cuenta not in ax.plan, "Cuenta {c} inexistente en el plan de cuentas",
                      "La cuenta {c} tiene {n} movimientos pero no figura en el plan de cuentas importado.",
                      efecto="Saldos que no se presentan o se agrupan incorrectamente en los estados financieros.")
    return Salida(out, len(ax.lineas), metodo="Cruce de cada cuenta movida contra el plan de cuentas importado (fase 2).")


def cuentas_inactivas(ax, r) -> Salida:
    if not ax.plan:
        return Salida(estado="SIN_DATOS", mensaje="No se importó el plan de cuentas.")
    out = _por_cuenta(ax, lambda ln: ln.cuenta in ax.plan and ax.plan[ln.cuenta].activa is False, "Movimientos en la cuenta inactiva {c}",
                      "La cuenta {c} está marcada como inactiva en el plan y registra {n} movimientos en el periodo.")
    return Salida(out, len(ax.lineas), metodo="Estado «activa» del plan de cuentas.")


def cuentas_no_autorizadas(ax, r) -> Salida:
    if not ax.plan:
        return Salida(estado="SIN_DATOS", mensaje="No se importó el plan de cuentas.")
    codigos = set(ax.plan)
    restr = tuple(ax.ctx3.restringidas)

    def mala(ln):
        c = ax.plan.get(ln.cuenta)
        return bool((c and c.admite_movimiento is False) or (restr and ln.cuenta.startswith(restr))
                    or any(x != ln.cuenta and x.startswith(ln.cuenta) for x in codigos if len(x) > len(ln.cuenta)))
    out = _por_cuenta(ax, mala, "Movimientos en la cuenta {c} que no admite registros directos",
                      "La cuenta {c} es de título, no admite movimiento o está restringida y registra {n} movimientos.")
    return Salida(out, len(ax.lineas), metodo="Plan de cuentas: «admite movimiento», cuentas con subcuentas y prefijos restringidos.")


def fuera_de_periodo(ax, r) -> Salida:
    out = []
    for ln in ax.lineas:
        if ln.fecha and 1 <= (ln.periodo or 0) <= 12 and (ln.fecha.year != ax.ejercicio or ln.fecha.month != ln.periodo):
            out.append(Res(titulo=f"Asiento {asiento_de(ln) or ''} con fecha fuera de su periodo", condicion=
                           f"La línea {ln.id} tiene fecha {ln.fecha:%d/%m/%Y} y se registró en el periodo {ln.periodo:02d}/{ax.ejercicio}.",
                           importe=ln.debe + ln.haber, cuenta=ln.cuenta, linea_id=ln.id, asiento=asiento_de(ln), documento=doc_de(ln),
                           tercero=ln.tercero, evidencia=[ev_linea(ln)], clave=f"FPE|{ln.id}", exposicion=f"LINEA|{ln.id}", estructural=True,
                           efecto="Afecta el corte contable y la comparación entre periodos."))
    return Salida(out, len(ax.lineas), metodo="Mes y año de la fecha contable frente al periodo de registro de la línea.")


def incompletos(ax, r) -> Salida:
    out = []
    for ln in ax.lineas:
        falta = [n for n, ok in (("fecha", ln.fecha), ("número de asiento", ln.asiento), ("importe", ln.debe or ln.haber)) if not ok]
        if falta:
            out.append(Res(titulo=f"Registro incompleto en la cuenta {ln.cuenta}", condicion=f"La línea {ln.id} no tiene {', '.join(falta)}.",
                           importe=ln.debe + ln.haber, cuenta=ln.cuenta, linea_id=ln.id, asiento=asiento_de(ln), evidencia=[ev_linea(ln)],
                           clave=f"INC|{ln.id}", exposicion=f"LINEA|{ln.id}", estructural=True))
    return Salida(out, len(ax.lineas), metodo="Campos mínimos de cada línea: fecha, asiento e importe.")


def fechas_inconsistentes(ax, r) -> Salida:
    out = []
    holgura = int(r.p.get("dias_tolerancia", 0))
    for ln in ax.lineas:
        motivos = []
        if ln.fecha_emision and ln.fecha and ln.fecha_emision > ln.fecha + timedelta(days=holgura):
            motivos.append(f"emisión {ln.fecha_emision:%d/%m/%Y} posterior a la fecha contable {ln.fecha:%d/%m/%Y}")
        if ln.fecha_emision and ln.fecha_vencimiento and ln.fecha_vencimiento < ln.fecha_emision:
            motivos.append(f"vencimiento {ln.fecha_vencimiento:%d/%m/%Y} anterior a la emisión")
        if motivos:
            out.append(Res(titulo=f"Fechas inconsistentes en el documento {doc_de(ln) or ''}", condicion=f"Línea {ln.id}: " + "; ".join(motivos) + ".",
                           importe=ln.debe + ln.haber, cuenta=ln.cuenta, linea_id=ln.id, asiento=asiento_de(ln), documento=doc_de(ln),
                           tercero=ln.tercero, evidencia=[ev_linea(ln)], clave=f"FEC|{ln.id}", exposicion=f"LINEA|{ln.id}", estructural=False,
                           causa="Posible error de digitación de fechas o registro anticipado del documento."))
    return Salida(out, len(ax.lineas), metodo="Coherencia entre fecha de emisión, contable y de vencimiento.")


def importes_invalidos(ax, r) -> Salida:
    out = []
    for ln in ax.lineas:
        if ln.debe < 0 or ln.haber < 0 or (ln.debe > 0 and ln.haber > 0):
            out.append(Res(titulo=f"Importe inválido en la cuenta {ln.cuenta}", condicion=f"La línea {ln.id} registra debe {ln.debe} y haber {ln.haber}.",
                           importe=abs(ln.debe) + abs(ln.haber), cuenta=ln.cuenta, linea_id=ln.id, asiento=asiento_de(ln), evidencia=[ev_linea(ln)],
                           clave=f"IMP|{ln.id}", exposicion=f"LINEA|{ln.id}", estructural=True))
    return Salida(out, len(ax.lineas), metodo="Importes negativos o línea con debe y haber simultáneos.")


def sin_glosa(ax, r) -> Salida:
    minimo = dec(r.p.get("importe_minimo", 0))
    out = []
    for k, ls in ax.asientos.items():
        vacias = [x for x in ls if not (x.glosa or "").strip()]
        if vacias and _total(ls) >= minimo and ax.asiento_en_alcance(ls):
            out.append(_res_asiento(k, vacias, f"Asiento {_etiqueta(k)} sin glosa", f"{len(vacias)} de {len(ls)} líneas del asiento no tienen glosa.",
                                    importe=_total(ls), estructural=False,
                                    efecto="Dificulta entender y sustentar la operación."))
    return Salida(out, len(ax.asientos), metodo="Líneas con glosa vacía, agrupadas por asiento.")


def sin_identificacion(ax, r) -> Salida:
    out = []
    for k, ls in ax.asientos.items():
        malas = [x for x in ls if r.en(x.cuenta, ("12", "13", "14", "16", "17", "42", "43", "44", "46", "47")) and not x.numero and x.periodo]
        if malas and ax.asiento_en_alcance(malas):
            out.append(_res_asiento(k, malas, f"Documento sin identificación en el asiento {_etiqueta(k)}",
                                    f"{len(malas)} líneas en cuentas de terceros sin número de documento "
                                    f"({', '.join(sorted({x.cuenta for x in malas}))}).", importe=sum((x.debe + x.haber for x in malas), CERO),
                                    estructural=False, efecto="No es posible analizar la composición, antigüedad ni compensación del saldo."))
    return Salida(out, len(ax.asientos), metodo="Líneas de cuentas por cobrar y por pagar sin número de documento.")


def tipo_cambio(ax, r) -> Salida:
    tol_conv = dec(r.p.get("tolerancia_conversion", "0.05"))
    tol_tc = dec(r.p.get("tolerancia_tc", "0.005"))
    tcs = defaultdict(dict)
    for t in ax.db.scalars(select(TipoCambio).where(TipoCambio.empresa_id == ax.empresa_id, TipoCambio.fecha <= ax.corte)):
        tcs[t.moneda][t.fecha] = t
    out, n = [], 0
    for ln in ax.lineas:
        if (ln.moneda or "PEN") == "PEN" or not (ln.debe_me or ln.haber_me):
            continue
        n += 1
        me, mn = ln.debe_me + ln.haber_me, ln.debe + ln.haber
        motivos = []
        if ln.tipo_cambio and abs(me * ln.tipo_cambio - mn) > tol_conv:
            motivos.append(f"ME {me} × TC {ln.tipo_cambio} = {(me * ln.tipo_cambio).quantize(Decimal('0.01'))} y MN registrado {mn}")
        t = tcs.get(ln.moneda, {}).get(ln.fecha)
        if t and ln.tipo_cambio and min(abs(ln.tipo_cambio - t.compra), abs(ln.tipo_cambio - t.venta)) > tol_tc:
            motivos.append(f"TC usado {ln.tipo_cambio} y TC publicado del {ln.fecha:%d/%m/%Y} {t.compra}/{t.venta}")
        if motivos:
            out.append(Res(titulo=f"Tipo de cambio inconsistente en la cuenta {ln.cuenta}", condicion=f"Línea {ln.id}: " + "; ".join(motivos) + ".",
                           importe=abs(me * (ln.tipo_cambio or 0) - mn) if ln.tipo_cambio else mn, cuenta=ln.cuenta, linea_id=ln.id,
                           asiento=asiento_de(ln), documento=doc_de(ln), tercero=ln.tercero, evidencia=[ev_linea(ln)], clave=f"TC|{ln.id}",
                           exposicion=f"LINEA|{ln.id}", estructural=False, causa="Tipo de cambio digitado o tabla de tipos de cambio desactualizada."))
    return Salida(out, n, metodo=f"Conversión ME × TC frente al importe en MN (tolerancia {tol_conv}) y TC de la tabla importada (±{tol_tc}).")


def _sumas_por_lote_tipo(ax, tipo):
    q = (select(LineaDiario.cuenta, func.sum(LineaDiario.debe_mn), func.sum(LineaDiario.haber_mn))
         .join(LoteContable, LoteContable.id == LineaDiario.lote_id)
         .where(LineaDiario.empresa_id == ax.empresa_id, LineaDiario.ejercicio == ax.ejercicio, LoteContable.estado == "ACTIVO",
                LoteContable.tipo_informacion == tipo, LineaDiario.periodo.between(1, ax.periodo)).group_by(LineaDiario.cuenta))
    return {c: (dec(d), dec(h)) for c, d, h in ax.db.execute(q)}


def diario_vs_mayor(ax, r) -> Salida:
    mayor = _sumas_por_lote_tipo(ax, "MAYOR")
    if not mayor:
        return Salida(estado="SIN_DATOS", mensaje="No se importó un libro mayor independiente del diario para el ejercicio.")
    diario = _sumas_por_lote_tipo(ax, "DIARIO")
    out = []
    for c in sorted(set(mayor) | set(diario)):
        a, b = diario.get(c, (CERO, CERO)), mayor.get(c, (CERO, CERO))
        if a != b:
            out.append(Res(titulo=f"Diario y mayor difieren en la cuenta {c}", condicion=f"Diario: debe {a[0]} haber {a[1]}; mayor: debe {b[0]} haber {b[1]}.",
                           importe=abs((a[0] - a[1]) - (b[0] - b[1])) or abs(a[0] - b[0]), cuenta=c, clave=f"DXM|{c}", exposicion=f"CUENTA|{c}",
                           estructural=True, evidencia=[ev_calc("Sumas por cuenta", diario_debe=a[0], diario_haber=a[1], mayor_debe=b[0], mayor_haber=b[1])]))
    return Salida(out, len(set(mayor) | set(diario)), metodo="Sumas del debe y del haber por cuenta en el diario y en el mayor importados.")


def mayor_vs_balance(ax, r) -> Salida:
    lote = ax.db.scalar(select(LoteContable).where(LoteContable.empresa_id == ax.empresa_id, LoteContable.tipo_informacion == "BALANCE",
                                                   LoteContable.estado == "ACTIVO", LoteContable.ejercicio == ax.ejercicio)
                        .order_by(LoteContable.periodo.desc().nulls_last(), LoteContable.id.desc()))
    if not lote:
        return Salida(estado="SIN_DATOS", mensaje="No se importó un balance de comprobación del ejercicio.")
    bal = defaultdict(lambda: CERO)
    for c, d, h in ax.db.execute(select(SaldoCuenta.cuenta, SaldoCuenta.saldo_final_debe, SaldoCuenta.saldo_final_haber)
                                 .where(SaldoCuenta.lote_id == lote.id)):
        bal[c] += dec(d) - dec(h)
    hasta = lote.periodo or ax.periodo
    f = saldos.fuentes(ax.db, ax.empresa_id, ax.ejercicio)
    hojas = saldos.saldos_hoja(ax.db, f, 1, hasta)
    nodos = saldos.construir_arbol(hojas, ax.plan)
    out = []
    for c, v in sorted(bal.items()):
        calc = saldos.dec(nodos[c].sf) if c in nodos else CERO
        if abs(calc - v) > Decimal("0.01"):
            out.append(Res(titulo=f"Mayor y balance de comprobación difieren en la cuenta {c}", condicion=f"Saldo según mayor {calc}; según el "
                           f"balance importado (lote {lote.id}, periodo {hasta}) {v}.", importe=abs(calc - v), cuenta=c, clave=f"MXB|{c}",
                           exposicion=f"CUENTA|{c}", estructural=True,
                           evidencia=[ev_calc("Saldo calculado vs balance importado", mayor=calc, balance=v, lote_balance=lote.id)]))
    return Salida(out, len(bal), metodo="Saldo final por cuenta del árbol de saldos (fase 3) frente al balance de comprobación importado.")


def apertura_vs_cierre(ax, r) -> Salida:
    fa = saldos.fuentes(ax.db, ax.empresa_id, ax.ejercicio - 1)
    if not fa.por_periodo and fa.apertura == "NINGUNA":
        return Salida(estado="SIN_DATOS", mensaje=f"No hay información del ejercicio {ax.ejercicio - 1} para comparar el cierre con la apertura.")
    f = saldos.fuentes(ax.db, ax.empresa_id, ax.ejercicio)
    if f.apertura == "NINGUNA":
        return Salida(estado="SIN_DATOS", mensaje="El ejercicio no tiene saldos iniciales ni asiento de apertura.")
    cierre = {c: h.si + h.debe - h.haber for c, h in saldos.saldos_hoja(ax.db, fa, 1, 13).items()}
    apertura = {c: h.si for c, h in saldos.saldos_hoja(ax.db, f, 1, 0).items()}
    out = []
    for c in sorted(set(cierre) | set(apertura)):
        if c[:1] not in "12345":
            continue  # las cuentas de resultados se cierran al final del ejercicio
        a, b = saldos.dec(cierre.get(c, 0)), saldos.dec(apertura.get(c, 0))
        if a != b:
            out.append(Res(titulo=f"Saldo inicial de la cuenta {c} distinto al cierre anterior", condicion=f"Cierre {ax.ejercicio - 1}: {a}; "
                           f"apertura {ax.ejercicio}: {b}.", importe=abs(a - b), cuenta=c, clave=f"APE|{c}", exposicion=f"CUENTA|{c}", estructural=True,
                           evidencia=[ev_calc("Cierre anterior vs apertura", cierre_anterior=a, apertura=b)]))
    return Salida(out, len(set(cierre) | set(apertura)), metodo="Saldos finales del ejercicio anterior (incluye periodo 13) frente a la apertura (cuentas 1–5).")


# ===================================================================== ASIENTOS
class Factores:
    """Factores de riesgo por asiento (para no calificar un asiento por un solo indicio)."""

    def __init__(self, ax, r):
        self.ax, self.r = ax, r
        self.usos = Counter()
        self.redondas = Counter()
        self.lineas_cta = Counter()
        for k, ls in ax.asientos.items():
            for c in {x.cuenta for x in ls}:
                self.usos[c] += 1
            for x in ls:
                self.lineas_cta[x.cuenta] += 1
                if (x.debe + x.haber) % 1000 == 0:
                    self.redondas[x.cuenta] += 1

    def de(self, k, ls) -> dict:
        p = self.r.p
        fin = fin_mes(ls[0].fecha) if ls[0].fecha else None
        tot = _total(ls)
        return {"importe_significativo": self.ax.significativo(tot) or tot >= dec(p.get("importe_significativo", "1e18")),
                "sin_documento": not any(x.numero for x in ls),
                "glosa_generica": any(normalizar_texto(x.glosa or "") in GLOSAS_GENERICAS for x in ls) or all(len((x.glosa or "").strip()) < 4 for x in ls),
                "cuenta_poco_frecuente": any(self.usos[x.cuenta] <= int(p.get("max_usos_cuenta", 2)) for x in ls),
                "importe_redondo": tot >= dec(p.get("minimo_redondo", "1000")) and tot % 1000 == 0,
                "al_cierre": bool(fin and ls[0].fecha and (fin - ls[0].fecha).days < int(p.get("dias_cierre", 3))),
                "manual": any(normalizar_texto(x.origen_asiento or "").startswith("MANUAL") for x in ls)}


def _con_factores(ax, r, condicion_principal, titulo, texto, minimo_extra=1, requiere=None, principal=""):
    f = Factores(ax, r)
    out = []
    for k, ls in ax.asientos.items():
        if not ax.asiento_en_alcance(ls) or not condicion_principal(k, ls):
            continue
        fs = f.de(k, ls)
        if requiere and not fs.get(requiere):
            continue
        extra = [n for n, v in fs.items() if v and n != requiere and n != principal]
        if len(extra) < minimo_extra:
            continue
        out.append(_res_asiento(k, ls, titulo.format(a=_etiqueta(k)), texto.format(a=_etiqueta(k)) + " Factores: " + ", ".join(extra).replace("_", " ") + ".",
                                estructural=False, detalle={"factores": fs},
                                causa="Hipótesis: requiere revisión del sustento; ningún factor aislado indica una irregularidad."))
        out[-1].evidencia.insert(0, ev_calc("Factores de riesgo del asiento", **{k2: v for k2, v in fs.items()}))
    return out


def manuales_significativos(ax, r) -> Salida:
    if not any(ln.origen_asiento for ln in ax.lineas_todas):
        return Salida(estado="SIN_DATOS", mensaje="El ERP de origen no exportó el origen del asiento (manual / automático): no se infiere.")

    def manual(k, ls):
        return any(normalizar_texto(x.origen_asiento or "").startswith("MANUAL") for x in ls)
    out = _con_factores(ax, r, manual, "Asiento manual {a} con factores de riesgo", "Asiento manual {a} de importe significativo.",
                        minimo_extra=int(r.p.get("factores_adicionales", 1)), requiere="importe_significativo", principal="manual")
    return Salida(out, len(ax.asientos), metodo="Asientos con origen MANUAL según el ERP, importe significativo y al menos un factor adicional.")


def al_cierre(ax, r) -> Salida:
    def cierre(k, ls):
        fin = fin_mes(ls[0].fecha) if ls[0].fecha else None
        return bool(fin and (fin - ls[0].fecha).days < int(r.p.get("dias_cierre", 3)))
    out = _con_factores(ax, r, cierre, "Asiento {a} al cierre del periodo con factores de riesgo", "Asiento {a} registrado en los últimos días del mes.",
                        minimo_extra=int(r.p.get("factores_adicionales", 2)), requiere="importe_significativo", principal="al_cierre")
    return Salida(out, len(ax.asientos), metodo="Asientos de los últimos días del periodo con importe significativo y otros factores de riesgo.")


def _con_registro(ax):
    return any(ln.fecha_registro for ln in ax.lineas_todas)


def despues_del_cierre(ax, r) -> Salida:
    if not _con_registro(ax):
        return Salida(estado="SIN_DATOS", mensaje="El ERP no exportó la fecha real de registro: no se evalúa (no se inventan datos).")
    gracia = int(r.p.get("dias_gracia", 10))
    out = []
    for k, ls in ax.asientos.items():
        x = ls[0]
        if x.fecha_registro and x.fecha and x.fecha_registro > fin_mes(x.fecha) + timedelta(days=gracia) and ax.asiento_en_alcance(ls):
            out.append(_res_asiento(k, ls, f"Asiento {_etiqueta(k)} registrado después del cierre del periodo",
                                    f"Fecha contable {x.fecha:%d/%m/%Y}; registrado el {x.fecha_registro:%d/%m/%Y}"
                                    f"{' por ' + x.usuario_registro if x.usuario_registro else ''} (más de {gracia} días después del cierre).",
                                    estructural=False, detalle={"usuario": x.usuario_registro, "fecha_registro": x.fecha_registro.isoformat()}))
    return Salida(out, len(ax.asientos), metodo=f"Fecha real de registro del ERP posterior al cierre del mes + {gracia} días.")


def retroactivos(ax, r) -> Salida:
    if not _con_registro(ax):
        return Salida(estado="SIN_DATOS", mensaje="El ERP no exportó la fecha real de registro.")
    dias = int(r.p.get("dias", 30))
    out = []
    for k, ls in ax.asientos.items():
        x = ls[0]
        if x.fecha_registro and x.fecha and (x.fecha_registro - x.fecha).days > dias and ax.asiento_en_alcance(ls):
            out.append(_res_asiento(k, ls, f"Asiento {_etiqueta(k)} con fecha retroactiva", f"Registrado {(x.fecha_registro - x.fecha).days} días después "
                                    f"de su fecha contable ({x.fecha:%d/%m/%Y} → {x.fecha_registro:%d/%m/%Y}).", estructural=False))
    return Salida(out, len(ax.asientos), metodo=f"Diferencia entre la fecha real de registro y la fecha contable mayor a {dias} días.")


def importes_redondos(ax, r) -> Salida:
    f = Factores(ax, r)
    minimo = dec(r.p.get("minimo_redondo", "1000"))
    pct_raro = Decimal(str(r.p.get("pct_habitual", 20)))
    out = []
    for k, ls in ax.asientos.items():
        tot = _total(ls)
        if tot < minimo or tot % 1000 or not ax.asiento_en_alcance(ls):
            continue
        raras = [x for x in ls if (x.debe + x.haber) % 1000 == 0 and f.lineas_cta[x.cuenta] >= 5
                 and Decimal(f.redondas[x.cuenta]) * 100 / f.lineas_cta[x.cuenta] < pct_raro]
        if raras:
            out.append(_res_asiento(k, ls, f"Importe redondo inusual en el asiento {_etiqueta(k)}", f"Importe {tot} múltiplo de 1 000 en cuentas donde "
                                    f"los importes redondos son poco habituales ({', '.join(sorted({x.cuenta for x in raras}))}).", estructural=False))
    return Salida(out, len(ax.asientos), metodo=f"Asientos ≥ {minimo} múltiplos de 1 000 en cuentas con menos de {pct_raro} % de líneas redondas.")


def cuentas_poco_frecuentes(ax, r) -> Salida:
    f = Factores(ax, r)
    maximo = int(r.p.get("max_usos_cuenta", 2))
    minimo = dec(r.p.get("importe_minimo", "0"))
    out = []
    for k, ls in ax.asientos.items():
        raras = [x for x in ls if f.usos[x.cuenta] <= maximo and x.debe + x.haber >= minimo and (x.cuenta[:1] not in "0")]
        if raras and len(ax.asientos) >= int(r.p.get("min_asientos", 20)) and ax.asiento_en_alcance(raras):
            out.append(_res_asiento(k, ls, f"Cuenta poco frecuente en el asiento {_etiqueta(k)}",
                                    f"Cuentas usadas en {maximo} asientos o menos durante el ejercicio: {', '.join(sorted({x.cuenta for x in raras}))}.",
                                    importe=sum((x.debe + x.haber for x in raras), CERO), estructural=False))
    return Salida(out, len(ax.asientos), metodo=f"Frecuencia de uso de cada cuenta en el ejercicio (≤ {maximo} asientos).")


def _pares(ls):
    deb = {x.cuenta[:2] for x in ls if x.debe > 0}
    hab = {x.cuenta[:2] for x in ls if x.haber > 0}
    return {(d, h) for d in deb for h in hab if d != h}


def combinaciones_atipicas(ax, r) -> Salida:
    freq = Counter()
    pares = {}
    for k, ls in ax.asientos.items():
        pares[k] = _pares(ls)
        freq.update(pares[k])
    if len(ax.asientos) < int(r.p.get("min_asientos", 50)):
        return Salida(estado="SIN_DATOS", mensaje=f"Población insuficiente ({len(ax.asientos)} asientos) para identificar combinaciones atípicas.")
    minimo = dec(r.p.get("importe_minimo", "0"))
    out = []
    for k, ps in pares.items():
        raros = [p for p in ps if freq[p] == 1]
        ls = ax.asientos[k]
        if raros and _total(ls) >= minimo and ax.asiento_en_alcance(ls):
            out.append(_res_asiento(k, ls, f"Combinación contable atípica en el asiento {_etiqueta(k)}",
                                    "Pares debe/haber usados una sola vez en el ejercicio: " + ", ".join(f"{d}↔{h}" for d, h in sorted(raros)) + ".",
                                    estructural=False))
    return Salida(out, len(ax.asientos), metodo="Frecuencia de pares cuenta debe / cuenta haber (2 dígitos) en el ejercicio.")


def glosas_genericas(ax, r) -> Salida:
    minimo = dec(r.p.get("importe_minimo", "0"))
    extra = {normalizar_texto(x) for x in r.p.get("glosas", [])}
    out = []
    for k, ls in ax.asientos.items():
        g = [x for x in ls if normalizar_texto(x.glosa or "") in GLOSAS_GENERICAS | extra]
        if g and _total(ls) >= minimo and ax.asiento_en_alcance(ls):
            out.append(_res_asiento(k, ls, f"Glosa genérica en el asiento {_etiqueta(k)}", f"Glosa «{g[0].glosa}» no describe la operación.", estructural=False))
    return Salida(out, len(ax.asientos), metodo="Glosas de una lista de textos genéricos (configurable).")


ESPERADAS = {"70": ["10", "12", "13", "14", "16", "17", "19", "40", "46", "48", "49", "70"]}


def contrapartidas(ax, r) -> Salida:
    esperadas = r.p.get("esperadas") or ESPERADAS
    out = []
    for k, ls in ax.asientos.items():
        for pref, permitidas in esperadas.items():
            hab = [x for x in ls if x.cuenta.startswith(pref) and x.haber > 0]
            if not hab:
                continue
            otras = sorted({x.cuenta for x in ls if x.debe > 0 and not x.cuenta.startswith(tuple(permitidas))})
            if otras and ax.asiento_en_alcance(ls):
                out.append(_res_asiento(k, ls, f"Contrapartida inesperada de la cuenta {pref} en el asiento {_etiqueta(k)}",
                                        f"La cuenta {hab[0].cuenta} se abona contra {', '.join(otras)} (esperadas: {', '.join(permitidas)}).",
                                        estructural=False))
    return Salida(out, len(ax.asientos), metodo="Contrapartidas esperadas por cuenta (configurables en la regla).")


def reclasificaciones(ax, r) -> Salida:
    veces = int(r.p.get("veces", 3))
    por_par = defaultdict(list)
    for k, ls in ax.asientos.items():
        cuentas = {x.cuenta for x in ls}
        if len(cuentas) == 2 and len({c[:2] for c in cuentas}) == 1 or "RECLASIF" in " ".join(normalizar_texto(x.glosa or "") for x in ls):
            por_par[tuple(sorted(cuentas))].append(k)
    out = []
    for par, ks in por_par.items():
        if len(ks) >= veces:
            ls = [x for k in ks for x in ax.asientos[k]]
            out.append(Res(titulo=f"Reclasificaciones frecuentes entre {' y '.join(par)}", condicion=f"{len(ks)} asientos de reclasificación entre "
                           f"las mismas cuentas en el ejercicio.", importe=max(_total(ax.asientos[k]) for k in ks), cuenta=par[0],
                           evidencia=[ev_linea(x) for x in ls[:20]], clave=f"RCL|{'|'.join(par)}", exposicion=f"RECLAS|{'|'.join(par)}",
                           estructural=False, causa="Posible deficiencia en la imputación inicial o en la parametrización."))
    return Salida(out, len(ax.asientos), metodo=f"Asientos entre dos cuentas del mismo grupo o glosa de reclasificación repetidos ≥ {veces} veces.")


def extornos(ax, r) -> Salida:
    veces = int(r.p.get("veces", 2))
    firmas = {}
    for k, ls in ax.asientos.items():
        firmas[k] = frozenset((x.cuenta, x.debe, x.haber) for x in ls)
    inversas = defaultdict(list)
    idx = defaultdict(list)
    for k, f in firmas.items():
        idx[f].append(k)
    for k, f in firmas.items():
        inv = frozenset((c, h, d) for c, d, h in f)
        for k2 in idx.get(inv, []):
            if k2 != k and k < k2:
                cuentas = tuple(sorted({c for c, _, _ in f}))
                inversas[cuentas].append((k, k2))
    out = []
    for cuentas, pares in inversas.items():
        if len(pares) >= veces:
            ls = [x for a, b in pares for x in ax.asientos[a] + ax.asientos[b]]
            out.append(Res(titulo=f"Extornos repetitivos en las cuentas {', '.join(cuentas)}", condicion=f"{len(pares)} pares de asientos registrados y "
                           f"luego revertidos con los mismos importes.", importe=max(_total(ax.asientos[a]) for a, _ in pares), cuenta=cuentas[0],
                           evidencia=[ev_linea(x) for x in ls[:20]], clave=f"EXT|{'|'.join(cuentas)}", exposicion=f"EXTORNO|{'|'.join(cuentas)}",
                           estructural=False, causa="Posibles errores recurrentes de registro o ajustes temporales al cierre."))
    return Salida(out, len(ax.asientos), metodo=f"Pares de asientos con las mismas cuentas e importes invertidos, repetidos ≥ {veces} veces.")


def extraordinarios(ax, r) -> Salida:
    from app.analisis import reglas as r3
    from app.models import ReglaAnalisis
    reg = ReglaAnalisis(id=None, codigo=r.codigo[:12], nombre=r.nombre, tipo="MOVIMIENTO_EXTRAORDINARIO", cuentas=",".join(r.cuentas) or None,
                        valor=Decimal(str(r.p.get("desviaciones", 3))), importe_minimo=dec(r.p.get("importe_minimo", "1000")),
                        parametros=f'{{"min_lineas": {int(r.p.get("min_lineas", 10))}}}', riesgo="MEDIO")
    ctx = ax.ctx3
    original = ctx.lineas
    ctx.lineas = ax.lineas
    try:
        hs = r3.evaluar(reg, ctx)
    finally:
        ctx.lineas = original
    out = [Res(titulo=h.titulo, condicion=h.titulo, importe=h.importe, cuenta=h.cuenta, tercero=h.tercero, documento=h.documento, asiento=h.asiento,
               linea_id=h.linea_id, evidencia=[ev_calc("Estadística de la cuenta (fase 3)", **{k: v for k, v in h.evidencia.items() if not isinstance(v, (list, dict))})],
               clave=f"EXO|{h.linea_id}", exposicion=f"LINEA|{h.linea_id}", estructural=False) for h in hs]
    return Salida(out, len(ax.lineas), metodo="Evaluador MOVIMIENTO_EXTRAORDINARIO de la fase 3: media ± N desviaciones estándar por cuenta.")


def ajustes_sin_documentacion(ax, r) -> Salida:
    palabras = tuple(r.p.get("palabras", ["AJUSTE", "REGULARIZ", "CORRECCION", "PROVISION"]))
    minimo = dec(r.p.get("importe_minimo", "0"))
    out = []
    for k, ls in ax.asientos.items():
        if any(any(p in normalizar_texto(x.glosa or "") for p in palabras) for x in ls) and not any(x.numero for x in ls) \
                and _total(ls) >= minimo and ax.asiento_en_alcance(ls):
            out.append(_res_asiento(k, ls, f"Ajuste {_etiqueta(k)} sin documentación disponible", "Asiento de ajuste sin documento de sustento "
                                    "identificado en la información importada.", estructural=False, calidad="PARCIAL",
                                    causa="El sustento puede existir fuera del ERP: solicitarlo antes de concluir."))
    return Salida(out, len(ax.asientos), metodo="Asientos con glosa de ajuste sin número de documento en ninguna línea.")


EVALUADORES = {"descuadre": descuadre, "cuentas_inexistentes": cuentas_inexistentes, "cuentas_inactivas": cuentas_inactivas,
               "cuentas_no_autorizadas": cuentas_no_autorizadas, "fuera_de_periodo": fuera_de_periodo, "incompletos": incompletos,
               "fechas_inconsistentes": fechas_inconsistentes, "importes_invalidos": importes_invalidos, "sin_glosa": sin_glosa,
               "sin_identificacion": sin_identificacion, "tipo_cambio": tipo_cambio, "diario_vs_mayor": diario_vs_mayor,
               "mayor_vs_balance": mayor_vs_balance, "apertura_vs_cierre": apertura_vs_cierre,
               "manuales_significativos": manuales_significativos, "al_cierre": al_cierre, "despues_del_cierre": despues_del_cierre,
               "retroactivos": retroactivos, "importes_redondos": importes_redondos, "cuentas_poco_frecuentes": cuentas_poco_frecuentes,
               "combinaciones_atipicas": combinaciones_atipicas, "glosas_genericas": glosas_genericas, "contrapartidas": contrapartidas,
               "reclasificaciones": reclasificaciones, "extornos": extornos, "extraordinarios": extraordinarios,
               "ajustes_sin_documentacion": ajustes_sin_documentacion}
