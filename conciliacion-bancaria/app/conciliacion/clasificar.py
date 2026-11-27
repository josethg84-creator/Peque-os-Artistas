"""Clasificación de diferencias y reportes especializados.

Clasificaciones: faltante en contabilidad, faltante en la fuente externa, monetaria, temporal, tipo de cambio,
clasificación, duplicado potencial, pendiente de sustento, corte, parametrización, no identificada y coincidencia
ambigua. Prioridades: crítico, alto, medio, bajo, informativo. Las diferencias dentro de tolerancia se mantienen
visibles y cuantificadas. Ninguna diferencia se considera, por sí sola, un error contable: la explicación y la
recomendación orientan la revisión.
"""
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.anexos import expresiones
from app.conciliacion.motor import CERO, Comparador, Tolerancia, _num
from app.importers.normalizacion import normalizar_texto

DESCRIPCION_ROL = {"CONTABLE": "contabilidad", "EXTERNA": "fuente externa", "AUXILIAR_INTERNO": "auxiliar interno"}


class Resultado:
    def __init__(self, comp: Comparador, fuentes: dict, tipo: str, cfg: dict, cx, run, tol: Tolerancia):
        self.comp, self.fuentes, self.tipo, self.cfg, self.cx, self.run, self.tol = comp, fuentes, tipo, cfg, cx, run, tol
        self.registros = {r["_id"]: r for lst in comp.reg.values() for r in lst}
        self.difs: list[dict] = []
        self.reporte: dict = {}

    def doc(self, r) -> str | None:
        if r.get("numero"):
            return f"{r.get('tipo_documento') + ' ' if r.get('tipo_documento') else ''}{r['serie'] + '-' if r.get('serie') else ''}{r['numero']}"
        return r.get("operacion") or r.get("referencia") or r.get("concepto")

    def dif(self, clasificacion, prioridad, explicacion, *, subtipo=None, registros=(), grupo=None, importe=None, recomendacion=None,
            fuente=None, dentro_tolerancia=False, regla=None, valores=None, clave=None):
        regs = [r for r in registros if r]
        r0 = regs[0] if regs else {}
        d = {"clasificacion": clasificacion, "prioridad": prioridad, "explicacion": explicacion, "subtipo": subtipo,
             "registros": [r["_id"] for r in regs], "claves": sorted(r["clave_registro"] for r in regs), "grupo": grupo,
             "importe": (importe if importe is not None else sum((r["_val"] for r in regs), CERO)), "recomendacion": recomendacion,
             "fuente": fuente or (self.fuentes.get(r0.get("_lado"), {}).get("nombre") if r0 else None), "dentro_tolerancia": dentro_tolerancia,
             "regla": regla, "valores": valores or {}, "cuenta": r0.get("cuenta"), "documento": self.doc(r0) if r0 else None,
             "tercero": r0.get("tercero"), "razon_social": r0.get("razon_social"), "moneda": r0.get("moneda") or "PEN",
             "fecha": r0.get("fecha"), "personal": any(r.get("personal") for r in regs), "clave": clave}
        self.difs.append(d)
        return d

    def rol(self, lado):
        return self.fuentes.get(lado, {}).get("rol", "EXTERNA")

    def nombre(self, lado):
        return self.fuentes.get(lado, {}).get("nombre", lado)


# ------------------------------------------------------------------ clasificación genérica
def generica(R: Resultado):
    comp = R.comp
    for did, oid in comp.duplicados.items():
        r, o = R.registros[did], R.registros[oid]
        R.dif("DOCUMENTO_DUPLICADO", "ALTO", f"Registro posiblemente duplicado en {R.nombre(r['_lado'])}: coincide con otro registro de la "
              f"misma fuente ({R.doc(o) or o.get('descripcion') or ''}).", subtipo=f"DUPLICADO_{R.rol(r['_lado'])}", registros=[r, o],
              importe=r["_val"], recomendacion="Verifique si la operación se registró dos veces antes de regularizar.")
    for p in comp.pasadas:
        if p.omitida:
            R.dif("DIFERENCIA_PARAMETRIZACION", "INFORMATIVO", f"Pasada {p.nombre} no ejecutada: {p.omitida}.", subtipo="FUENTE_SIN_DATOS",
                  importe=CERO, clave=f"OMITIDA|{p.nombre}")
            continue
        for gi, g in enumerate(p.grupos):
            regs = [r for r, _ in g.a + g.b]
            ref = (p.nombre, gi)
            dif_total = Decimal(g.detalle.get("diferencia") or "0")
            if g.tipo == "AMBIGUA":
                R.dif("COINCIDENCIA_AMBIGUA", "MEDIO", f"{g.detalle.get('motivo', 'Coincidencia ambigua')}: se requiere decisión del "
                      "usuario (no se aprueba automáticamente).", subtipo="AMBIGUA", registros=regs, grupo=ref, importe=g.a[0][1] if g.a else CERO,
                      regla=g.regla, recomendacion="Elija la alternativa correcta en la pantalla de conciliación manual.")
                continue
            if g.tipo == "DIFERENCIA" and dif_total:
                cl = "DIFERENCIA_TIPO_CAMBIO" if g.detalle.get("monedas") else "DIFERENCIA_MONETARIA"
                R.dif(cl, "ALTO", f"Coincide por {g.regla} ({g.clave or ''}) pero el importe difiere en {dif_total}.", subtipo="DIFERENCIA_IMPORTE",
                      registros=regs, grupo=ref, importe=dif_total, regla=g.regla, valores={"a": str(g.importe_a), "b": str(g.importe_b)},
                      recomendacion="Revise el comprobante y el registro; corrija la fuente que corresponda.")
            elif g.tipo == "TOLERANCIA" and dif_total:
                R.dif("DIFERENCIA_MONETARIA", "INFORMATIVO", f"Coincidencia dentro de tolerancia: diferencia de {dif_total} (visible, no eliminada).",
                      subtipo="DENTRO_TOLERANCIA", registros=regs, grupo=ref, importe=dif_total, regla=g.regla, dentro_tolerancia=True)
            for c in g.detalle.get("campos", []):
                dentro = c.get("dentro_tolerancia")
                R.dif("DIFERENCIA_MONETARIA", "INFORMATIVO" if dentro else "MEDIO",
                      f"{c['nombre']}: {R.nombre(p.a)} {c['a']} y {R.nombre(p.b)} {c['b']} (diferencia {c['diferencia']})"
                      + (" — dentro de tolerancia" if dentro else "") + ".", subtipo=c.get("subtipo") or "DIFERENCIA_CAMPO", registros=regs,
                      grupo=ref, importe=Decimal(c["diferencia"]), regla=g.regla, dentro_tolerancia=bool(dentro), valores=c,
                      clave=f"{p.nombre}|{g.clave or ''}|{c.get('subtipo') or ''}|{c['nombre']}")
            if g.detalle.get("fuera_de_plazo"):
                R.dif("DIFERENCIA_TEMPORAL", "BAJO", f"Las fechas difieren en {g.detalle['fuera_de_plazo']} días.", subtipo="FECHA_FUERA_DE_PLAZO",
                      registros=regs, grupo=ref, importe=CERO, regla=g.regla)
            if g.detalle.get("periodos"):
                R.dif("DIFERENCIA_CORTE", "MEDIO", f"Registrado en periodos diferentes: {g.detalle['periodos'][0]} y {g.detalle['periodos'][1]}.",
                      subtipo="PERIODO_DIFERENTE", registros=regs, grupo=ref, importe=g.importe_a, regla=g.regla,
                      recomendacion="Verifique el periodo de registro (corte contable).")
        # pendientes
        if p.modo == "AGREGADO":
            claves = p.claves_reporte or ["clave"]
            from app.conciliacion.motor import clave_de
            for lado, otro in ((p.a, p.b), (p.b, p.a)):
                acum = defaultdict(list)
                for r in comp.reg.get(lado, []):
                    if comp_dispo(p, r) > 0:
                        acum[clave_de(r, claves) or ("(sin clave)",)].append(r)
                for k, regs in acum.items():
                    faltante(R, p, lado, otro, regs, " · ".join(k), sum((r["_val"] for r in regs), CERO))
        else:
            for lado, otro in ((p.a, p.b), (p.b, p.a)):
                for r in comp.reg.get(lado, []):
                    pend = comp_dispo(p, r)
                    if pend > 0 and r["_id"] not in p.ambiguos:
                        imp = pend if r["_val"] >= 0 else -pend
                        if r["_id"] in p.parciales:
                            R.dif("DIFERENCIA_MONETARIA", "MEDIO", f"Coincidencia parcial: queda {imp} pendiente de conciliar.",
                                  subtipo="SALDO_PARCIAL", registros=[r], importe=imp,
                                  recomendacion="Identifique el resto de la operación o confirme el saldo pendiente.")
                        else:
                            faltante(R, p, lado, otro, [r], None, imp)


def comp_dispo(p, r):
    return p.dispo.get(r["_id"], CERO)


def faltante(R: Resultado, p, lado, otro, regs, clave, importe):
    rol, rol_otro = R.rol(lado), R.rol(otro)
    if rol_otro == "CONTABLE" and rol != "CONTABLE":
        cl, prio = "REGISTRO_FALTANTE_CONTABILIDAD", "ALTO"
        txt = f"Figura en {R.nombre(lado)} y no se encontró en {R.nombre(otro)}."
    elif rol == "CONTABLE" and rol_otro != "CONTABLE":
        cl, prio = "REGISTRO_FALTANTE_FUENTE_EXTERNA", "MEDIO"
        txt = f"Registrado en {R.nombre(lado)} y no figura en {R.nombre(otro)}."
    else:
        cl, prio = "DIFERENCIA_NO_IDENTIFICADA", "MEDIO"
        txt = f"Figura en {R.nombre(lado)} y no en {R.nombre(otro)}."
    if rol == "AUXILIAR_INTERNO" or rol_otro == "AUXILIAR_INTERNO":
        txt += " (comparación con un auxiliar interno)"
    d = R.dif(cl, prio, txt, subtipo=f"SOLO_{lado}", registros=regs, importe=importe, clave=clave and f"{p.nombre}|{lado}|{clave}",
              recomendacion="Investigue el origen de la partida; no se generan ajustes automáticos.")
    d["_pasada"] = p.nombre


def reglas_clasificacion(R: Resultado, reglas: list[dict]):
    """Reglas de la plantilla que reclasifican partidas pendientes (motor seguro de expresiones)."""
    for rg in reglas:
        if rg["tipo"] != "CLASIFICACION" or not rg["activa"]:
            continue
        par = rg["parametros"]
        arbol = expresiones.compilar(par["expresion"])
        for d in R.difs:
            if not d["registros"] or d["clasificacion"] not in ("REGISTRO_FALTANTE_CONTABILIDAD", "REGISTRO_FALTANTE_FUENTE_EXTERNA",
                                                                  "DIFERENCIA_NO_IDENTIFICADA"):
                continue
            r = R.registros[d["registros"][0]]
            try:
                if expresiones.evaluar(arbol, {**r, **r["datos"]}):
                    d.update(subtipo=par.get("subtipo") or d["subtipo"], clasificacion=par.get("clasificacion") or d["clasificacion"],
                             prioridad=par.get("prioridad") or d["prioridad"], regla=rg["codigo"],
                             explicacion=par.get("explicacion") or d["explicacion"])
            except expresiones.ErrorExpresion:
                continue


# ------------------------------------------------------------------ bancaria
RE_COMISION = re.compile(r"COMISION|COM\b|COM\.|MANTENIMIENTO|MANT\b|PORTES|CARGO POR|GASTOS? BANC|MEMBRESIA|TARIFA")
RE_ITF = re.compile(r"\bITF\b|IMP\.? ?TRANS|IMPUESTO A LAS TRANSACCIONES")
RE_INTERES = re.compile(r"INTERES")
RE_CHEQUE = re.compile(r"CHEQUE|\bCHQ\b|\bCH\b")


def bancaria(R: Resultado):
    libro, banco = "A", "B"
    for d in R.difs:
        if not d["registros"]:
            continue
        r = R.registros[d["registros"][0]]
        texto = normalizar_texto(r.get("descripcion") or "")
        if d["subtipo"] == f"SOLO_{banco}":
            if r["_val"] < 0:
                st = "COMISION_BANCARIA" if RE_COMISION.search(texto) else ("ITF" if RE_ITF.search(texto) else "CARGO_NO_REGISTRADO")
                d.update(subtipo=st, prioridad="MEDIO" if st != "CARGO_NO_REGISTRADO" else "ALTO",
                         explicacion={"COMISION_BANCARIA": "Comisión bancaria cargada por el banco y no registrada en libros.",
                                      "ITF": "ITF cargado por el banco y no registrado en libros.",
                                      "CARGO_NO_REGISTRADO": "Cargo del banco no registrado en libros."}[st],
                         recomendacion="Registre el cargo con su sustento (los asientos de regularización se generan en una fase posterior).")
            else:
                st = "INTERES_BANCARIO" if RE_INTERES.search(texto) else "ABONO_NO_IDENTIFICADO"
                d.update(subtipo=st, prioridad="MEDIO" if st == "INTERES_BANCARIO" else "ALTO",
                         explicacion="Intereses abonados por el banco no registrados en libros." if st == "INTERES_BANCARIO"
                         else "Abono del banco no identificado en libros.",
                         recomendacion="Identifique al ordenante y registre el abono.")
        elif d["subtipo"] == f"SOLO_{libro}":
            antig = (R.run.fecha_corte - r["fecha"]).days if r.get("fecha") else 0
            if r["_val"] > 0:
                d.update(clasificacion="DIFERENCIA_TEMPORAL", subtipo="DEPOSITO_EN_TRANSITO", prioridad="BAJO" if antig <= 30 else "ALTO",
                         explicacion="Depósito registrado en libros que el banco aún no abona (en tránsito)." if antig <= 30
                         else f"Depósito registrado hace {antig} días y no abonado por el banco.",
                         recomendacion="Verifique su abono en el siguiente estado de cuenta.")
            else:
                st = "CHEQUE_PENDIENTE_COBRO" if (r.get("tipo_documento") in ("CH",) or RE_CHEQUE.search(texto)) else "TRANSFERENCIA_PENDIENTE"
                d.update(clasificacion="DIFERENCIA_TEMPORAL", subtipo=st, prioridad="BAJO" if antig <= 60 else "MEDIO",
                         explicacion="Cheque girado pendiente de cobro." if st == "CHEQUE_PENDIENTE_COBRO" else "Transferencia o cargo registrado en libros, pendiente en el banco.",
                         recomendacion="Verifique su cargo en el siguiente estado de cuenta.")
        elif d["subtipo"] == "PERIODO_DIFERENTE":
            d.update(explicacion="Operación registrada por el banco y por la empresa en periodos diferentes.")
        elif d["subtipo"] == "DUPLICADO_CONTABLE":
            d.update(explicacion="Movimiento registrado dos veces en libros (el banco lo muestra una sola vez).",
                     recomendacion="Verifique y anule el registro duplicado.")
        elif d["subtipo"] == "DUPLICADO_EXTERNA":
            d.update(explicacion="Movimiento duplicado en el estado bancario.", recomendacion="Solicite al banco la regularización o confirme la operación.")
    # reporte de conciliación (convención: + aumenta el efectivo)
    comp = R.comp
    p = comp.pasadas[0]
    pend = lambda lado: [r for r in comp.reg.get(lado, []) if p.dispo.get(r["_id"], CERO) > 0 and r["_id"] not in comp.duplicados]  # noqa: E731
    firm = lambda r: p.dispo[r["_id"]] if r["_val"] >= 0 else -p.dispo[r["_id"]]  # noqa: E731
    sb, sl = R.fuentes.get(banco, {}).get("saldo"), R.fuentes.get(libro, {}).get("saldo")
    dep = [r for r in pend(libro) if r["_val"] > 0]
    che = [r for r in pend(libro) if r["_val"] < 0]
    abn = [r for r in pend(banco) if r["_val"] > 0]
    car = [r for r in pend(banco) if r["_val"] < 0]
    dup_l = [R.registros[i] for i in comp.duplicados if R.registros[i]["_lado"] == libro]
    dup_b = [R.registros[i] for i in comp.duplicados if R.registros[i]["_lado"] == banco]
    dif_grupos = sum((Decimal(g.detalle.get("diferencia") or 0) for g in p.grupos if g.tipo in ("DIFERENCIA", "TOLERANCIA")), CERO)
    s = lambda lst: sum((firm(r) if r["_id"] in p.dispo else r["_val"] for r in lst), CERO)  # noqa: E731
    banco_aj = (sb + s(dep) + s(che)) if sb is not None else None
    libros_aj = (sl + s(abn) + s(car) - sum((r["_val"] for r in dup_l), CERO) + sum((r["_val"] for r in dup_b), CERO) + dif_grupos) if sl is not None else None

    def filas(lst):
        return [{"fecha": r.get("fecha"), "documento": R.doc(r), "descripcion": r.get("descripcion"), "importe": str(firm(r) if r["_id"] in p.dispo else r["_val"]),
                 "registro_id": r["_id"]} for r in lst]
    R.reporte = {"tipo": "BANCARIA", "convencion": "Importes positivos aumentan el efectivo; negativos lo disminuyen.",
                 "saldo_banco": str(sb) if sb is not None else None,
                 "partidas_banco": [{"concepto": "(+) Depósitos en tránsito", "importe": str(s(dep)), "detalle": filas(dep)},
                                    {"concepto": "(−) Cheques y transferencias pendientes", "importe": str(s(che)), "detalle": filas(che)}],
                 "saldo_banco_ajustado": str(banco_aj) if banco_aj is not None else None,
                 "saldo_libros": str(sl) if sl is not None else None,
                 "partidas_libros": [{"concepto": "(+) Abonos del banco no registrados (intereses, abonos no identificados)", "importe": str(s(abn)), "detalle": filas(abn)},
                                     {"concepto": "(−) Cargos del banco no registrados (comisiones, ITF, otros)", "importe": str(s(car)), "detalle": filas(car)},
                                     {"concepto": "(−/+) Movimientos duplicados en libros", "importe": str(-sum((r["_val"] for r in dup_l), CERO)), "detalle": filas(dup_l)},
                                     {"concepto": "(+/−) Movimientos duplicados en el banco", "importe": str(sum((r["_val"] for r in dup_b), CERO)), "detalle": filas(dup_b)},
                                     {"concepto": "(+/−) Diferencias de importe en partidas conciliadas", "importe": str(dif_grupos), "detalle": []}],
                 "saldo_libros_ajustado": str(libros_aj) if libros_aj is not None else None,
                 "diferencia_final": str(banco_aj - libros_aj) if banco_aj is not None and libros_aj is not None else None,
                 "nota": "No hay saldo del estado bancario a la fecha de corte: la conciliación no puede cerrarse." if sb is None else
                 (f"{len(p.ambiguos)} registro(s) en coincidencias ambiguas figuran como partidas pendientes hasta que se resuelvan." if p.ambiguos else None)}
    if R.reporte["diferencia_final"] not in (None, "0", "0.00") and Decimal(R.reporte["diferencia_final"]):
        R.dif("DIFERENCIA_NO_IDENTIFICADA", "CRITICO", f"La conciliación bancaria no cierra: diferencia final {R.reporte['diferencia_final']}.",
              subtipo="DIFERENCIA_FINAL", importe=Decimal(R.reporte["diferencia_final"]), clave="BANCARIA|FINAL",
              recomendacion="Revise partidas de periodos anteriores, saldos iniciales y movimientos fuera del rango del estado.")
    if sb is None:
        R.dif("DIFERENCIA_PARAMETRIZACION", "ALTO", "No hay estado bancario con saldo a la fecha de corte: no se declara conciliada.",
              subtipo="SIN_ESTADO_BANCARIO", importe=CERO, clave="BANCARIA|SIN_SALDO")


# ------------------------------------------------------------------ compras y ventas
def registros_tributarios(R: Resultado, venta=False):
    periodo = R.run.ejercicio * 100 + R.run.periodo
    docs = {(r.get("tercero") or "", r.get("serie") or "", r.get("numero") or "") for r in R.registros.values()}
    admitidas = tuple(R.cfg.get("cuentas_destino_admitidas") or [])
    nuevas = []
    for d in R.difs:
        if not d["registros"]:
            nuevas.append(d)
            continue
        r = R.registros[d["registros"][0]]
        if d["subtipo"] == "SOLO_A":
            if r["datos"].get("anulado"):
                d.update(clasificacion="DIFERENCIA_NO_IDENTIFICADA", prioridad="INFORMATIVO", subtipo="COMPROBANTE_ANULADO",
                         explicacion="Comprobante anulado en el registro: no requiere contabilización.")
            else:
                d.update(subtipo="VENTA_NO_CONTABILIZADA" if venta else "COMPRA_NO_CONTABILIZADA",
                         explicacion=("Factura emitida no contabilizada." if venta else "Compra registrada y no contabilizada."))
        elif d["subtipo"] == "SOLO_B":
            if r.get("periodo") and r["periodo"] != periodo:
                continue  # documento contable de otro periodo: fuera del alcance de este registro mensual
            if r["datos"].get("sin_comprobante"):
                d.update(clasificacion="DIFERENCIA_TEMPORAL", prioridad="BAJO", subtipo="INGRESO_SIN_COMPROBANTE",
                         explicacion="Ingreso reconocido sin comprobante asociado: puede corresponder a un ingreso devengado no facturado.",
                         recomendacion="Evalúe la naturaleza de la operación y la política de reconocimiento de ingresos (NIIF 15); no es error por sí mismo.")
            else:
                d.update(subtipo="CONTABILIZADA_SIN_REGISTRO", explicacion=("Ingreso contabilizado sin comprobante en el registro de ventas." if venta
                                                                            else "Compra contabilizada que no figura en el registro de compras."))
        elif d["subtipo"] == "PERIODO_DIFERENTE":
            d.update(subtipo="ERROR_PERIODO", explicacion="El comprobante figura en el registro de un periodo y se contabilizó en otro.")
        nuevas.append(d)
    R.difs = nuevas
    for r in R.registros.values():
        if r["_lado"] == "A" and r.get("tipo_documento") == "07":
            ref = r.get("referencia") or ""
            partes = re.split(r"[-\s]", ref.strip())
            ok = ref and any((x[1] or "").upper() == (partes[0] if len(partes) > 1 else "").upper() and (x[2] or "").lstrip("0") == partes[-1].lstrip("0")
                             for x in docs)
            if not ok:
                R.dif("DOCUMENTO_PENDIENTE_SUSTENTO", "MEDIO", f"Nota de crédito {R.doc(r)} sin comprobante relacionado identificable"
                      + (f" (referencia «{ref}»)" if ref else "") + ".", subtipo="NC_NO_RELACIONADA", registros=[r],
                      recomendacion="Registre el comprobante que modifica la nota de crédito y verifique que no se aplique dos veces.")
    if not venta:
        for p in R.comp.pasadas:
            for g in p.grupos:
                for b, _ in g.b:
                    fuera = [c for c in b["datos"].get("cuentas_destino") or [] if not c.startswith(admitidas)]
                    if admitidas and fuera:
                        R.dif("DIFERENCIA_CLASIFICACION", "INFORMATIVO", f"Comprobante registrado en cuentas no habituales para compras ({', '.join(fuera)}).",
                              subtipo="CLASIFICACION_REVISAR", registros=[b] + [a for a, _ in g.a],
                              recomendacion="No toda compra es gasto: confirme si corresponde a activo, existencias, anticipo u otro tratamiento.")
                    for a, _ in g.a:
                        if a.get("cuenta") and b["datos"].get("cuentas_destino") and not any(c.startswith(a["cuenta"]) or a["cuenta"].startswith(c)
                                                                                              for c in b["datos"]["cuentas_destino"]):
                            R.dif("DIFERENCIA_CLASIFICACION", "BAJO", f"El registro indica la cuenta {a['cuenta']} y la contabilidad usó "
                                  f"{', '.join(b['datos']['cuentas_destino'])}.", subtipo="CUENTA_DISTINTA", registros=[a, b])
                    if a_me := [a for a, _ in g.a if a["moneda"] != "PEN" and a.get("tipo_cambio") and b.get("tipo_cambio")
                                and Decimal(a["tipo_cambio"]) != Decimal(b["tipo_cambio"])]:
                        R.dif("DIFERENCIA_TIPO_CAMBIO", "BAJO", f"Tipo de cambio del registro {a_me[0]['tipo_cambio']} y contable {b['tipo_cambio']}.",
                              subtipo="TIPO_CAMBIO", registros=a_me + [b], importe=CERO)


# ------------------------------------------------------------------ planillas
def planillas(R: Resultado):
    conceptos = {c["grupo"]: c for c in R.cfg.get("conceptos", [])}
    for d in R.difs:
        d["personal"] = True
        regs = [R.registros[i] for i in d["registros"]]
        grupo = regs[0].get("concepto") if regs else None
        m = conceptos.get(grupo, {})
        if d["subtipo"] == "SOLO_A":
            d.update(subtipo="REMUNERACION_NO_CONTABILIZADA" if grupo == "NETO" else (m.get("subtipo") or "CONCEPTO_NO_CONTABILIZADO"),
                     explicacion=f"{m.get('nombre', grupo)}: figura en la planilla y no en la contabilidad ({m.get('cuenta', '')}).")
        elif d["subtipo"] == "SOLO_B":
            d.update(explicacion=f"{m.get('nombre', grupo)}: registrado en la contabilidad ({m.get('cuenta', '')}) y no figura en la planilla.")
        elif d["clasificacion"] == "DIFERENCIA_MONETARIA" and d["subtipo"] in ("DIFERENCIA_CAMPO", None):
            d.update(subtipo=m.get("subtipo") or "DIFERENCIA_PLANILLA", explicacion=f"{m.get('nombre', grupo)}: {d['explicacion']}")
    # préstamos al personal con saldo y sin descuento en la planilla
    ctx = R.cx.libro()
    con_descuento = {r.get("tercero") for r in R.registros.values() if r["_lado"] == "A" and r.get("concepto") == "PRESTAMO"}
    saldo = defaultdict(int)
    for (c, t), v in ctx.apertura_ter.items():
        if c.startswith("1411") and t:
            saldo[t] += v
    for ln in ctx.de("1411"):
        if ln.tercero:
            saldo[ln.tercero] += ln.neto
    trabajadores = {r.get("tercero") for r in R.registros.values() if r["_lado"] == "A"}
    for t, v in saldo.items():
        if v > 0 and t in trabajadores and t not in con_descuento:
            R.dif("DOCUMENTO_PENDIENTE_SUSTENTO", "INFORMATIVO", "Préstamo al personal con saldo y sin descuento en la planilla del periodo.",
                  subtipo="PRESTAMO_NO_DESCONTADO", importe=Decimal(v) / 100, clave=f"PRESTAMO|{t}",
                  recomendacion="Verifique el cronograma de descuentos acordado con el trabajador.")
            R.difs[-1].update(tercero=t, personal=True)


# ------------------------------------------------------------------ activos fijos
def activos(R: Resultado):
    for d in R.difs:
        regs = [R.registros[i] for i in d["registros"]]
        if d["subtipo"] == "SOLO_A":
            d.update(subtipo="ACTIVO_SOLO_EN_AUXILIAR", explicacion=f"Activo {d['documento'] or ''} registrado únicamente en el auxiliar.")
        elif d["subtipo"] == "SOLO_B":
            cod = regs[0]["datos"].get("clave") if regs else None
            d.update(subtipo="ACTIVO_SOLO_EN_CONTABILIDAD" if cod else "SALDO_SIN_CODIGO",
                     explicacion=f"Activo {cod} registrado únicamente en contabilidad (no figura en el registro auxiliar)." if cod
                     else "Saldo contable de activos sin código y sin contrapartida en el registro.")
    for p in R.comp.pasadas:
        for g in p.grupos:
            for a, _ in g.a:
                da = a["datos"]
                costo = _num(da.get("costo"))
                dep = _num(da.get("dep_acumulada"))
                residual = _num(da.get("valor_residual"))
                b_costo = sum((_num(b["datos"].get("costo")) for b, _ in g.b), CERO)
                b_dep = sum((_num(b["datos"].get("dep_acumulada")) for b, _ in g.b), CERO)
                ult = max((b["datos"].get("ultima_depreciacion") or "" for b, _ in g.b), default="")
                baja = da.get("fecha_baja")
                if baja and baja <= R.run.fecha_corte.isoformat() and b_costo > 0:
                    R.dif("REGISTRO_FALTANTE_CONTABILIDAD", "ALTO", f"El activo {da.get('clave')} tiene baja el {baja} y su costo sigue en libros.",
                          subtipo="BAJA_NO_REGISTRADA", registros=[a], importe=b_costo)
                if baja and ult and ult > baja:
                    R.dif("DIFERENCIA_MONETARIA", "ALTO", f"Depreciación registrada después de la baja del activo {da.get('clave')} ({ult} > {baja}).",
                          subtipo="DEPRECIACION_POSTERIOR_BAJA", registros=[a], importe=CERO)
                if dep > costo - residual or (b_dep and b_costo and b_dep > b_costo):
                    R.dif("DIFERENCIA_MONETARIA", "ALTO", f"La depreciación acumulada del activo {da.get('clave')} supera su importe depreciable.",
                          subtipo="DEPRECIACION_EXCEDE_DEPRECIABLE", registros=[a], importe=max(dep - (costo - residual), b_dep - b_costo))
                if costo and dep == costo - residual:
                    R.dif("DIFERENCIA_NO_IDENTIFICADA", "INFORMATIVO", f"El activo {da.get('clave')} está totalmente depreciado; no se da de baja "
                          "automáticamente (verifique si sigue en uso).", subtipo="TOTALMENTE_DEPRECIADO", registros=[a], importe=CERO)
                if da.get("dep_tributaria") not in (None, "None") and _num(da.get("dep_tributaria")) != _num(da.get("dep_periodo")):
                    R.dif("DIFERENCIA_PARAMETRIZACION", "INFORMATIVO", f"Activo {da.get('clave')}: depreciación financiera {da.get('dep_periodo')} y "
                          f"tributaria {da.get('dep_tributaria')} (diferencia temporal, no error).", subtipo="FINANCIERA_VS_TRIBUTARIA", registros=[a],
                          importe=_num(da.get("dep_periodo")) - _num(da.get("dep_tributaria")))


# ------------------------------------------------------------------ inventarios
def inventarios(R: Resultado):
    metodo = R.cfg.get("metodo_valorizacion", "PROMEDIO")
    unidades = defaultdict(set)
    vistos = {}
    for r in [x for x in R.registros.values() if x["_lado"] == "A"]:
        d = r["datos"]
        q = {k: _num(d.get(k)) for k in ("cantidad_inicial", "cantidad_entradas", "cantidad_salidas", "cantidad_final")}
        v = {k: _num(d.get(k)) for k in ("valor_inicial", "valor_entradas", "valor_salidas", "valor_final")}
        prod = f"{d.get('producto')} ({d.get('almacen') or 'sin almacén'})"
        if d.get("unidad"):
            unidades[d.get("producto")].add(d["unidad"])
        k = (d.get("producto"), d.get("almacen"))
        if k in vistos:
            R.dif("DOCUMENTO_DUPLICADO", "ALTO", f"El producto {prod} figura dos veces en el kardex.", subtipo="MOVIMIENTO_DUPLICADO", registros=[r, vistos[k]])
        vistos[k] = r
        if q["cantidad_final"] < 0:
            R.dif("DIFERENCIA_NO_IDENTIFICADA", "ALTO", f"Existencia negativa: {prod} con {q['cantidad_final']} unidades.", subtipo="EXISTENCIA_NEGATIVA",
                  registros=[r], importe=v["valor_final"])
        if d.get("cantidad_inicial") is not None and q["cantidad_inicial"] + q["cantidad_entradas"] - q["cantidad_salidas"] != q["cantidad_final"]:
            R.dif("DIFERENCIA_NO_IDENTIFICADA", "MEDIO", f"{prod}: cantidad inicial + entradas − salidas no coincide con la cantidad final "
                  "(cantidades físicas, no valores).", subtipo="INCONSISTENCIA_CANTIDADES", registros=[r], importe=CERO)
        if d.get("valor_inicial") is not None and v["valor_inicial"] + v["valor_entradas"] - v["valor_salidas"] != v["valor_final"]:
            R.dif("DIFERENCIA_MONETARIA", "MEDIO", f"{prod}: valor inicial + entradas − salidas no coincide con el valor final.",
                  subtipo="INCONSISTENCIA_VALORES", registros=[r],
                  importe=v["valor_inicial"] + v["valor_entradas"] - v["valor_salidas"] - v["valor_final"])
        cu = _num(d.get("costo_unitario"))
        if metodo == "PROMEDIO" and cu and q["cantidad_final"] > 0:
            implicito = v["valor_final"] / q["cantidad_final"]
            if abs(implicito - cu) > cu * Decimal("0.01"):
                R.dif("DIFERENCIA_MONETARIA", "MEDIO", f"{prod}: costo unitario {cu} y costo implícito {implicito.quantize(Decimal('0.0001'))} "
                      f"(método {metodo.lower()}).", subtipo="INCONSISTENCIA_COSTO", registros=[r], importe=(cu - implicito) * q["cantidad_final"])
        if not d.get("cuenta"):
            R.dif("DIFERENCIA_PARAMETRIZACION", "MEDIO", f"{prod} sin cuenta contable en el kardex: no puede compararse con existencias.",
                  subtipo="SIN_CUENTA", registros=[r], importe=v["valor_final"])
    for prod, us in unidades.items():
        if len(us) > 1:
            R.dif("DIFERENCIA_PARAMETRIZACION", "MEDIO", f"El producto {prod} usa unidades de medida distintas: {', '.join(sorted(us))}.",
                  subtipo="DIFERENCIA_UNIDAD_MEDIDA", importe=CERO, clave=f"UM|{prod}")
    R.reporte = {"tipo": "INVENTARIOS", "metodo_valorizacion": metodo, "nota": "Las cantidades físicas y los valores monetarios se comparan por separado."}


# ------------------------------------------------------------------ servicios y costos en proceso
def servicios(R: Resultado):
    ctx = R.cx.libro()
    sin_proy = defaultdict(lambda: [CERO, []])
    for d in list(R.difs):
        regs = [R.registros[i] for i in d["registros"]]
        if regs and regs[0].get("concepto") == "SIN_PROYECTO":
            R.difs.remove(d)
            for r in regs:
                sin_proy[r["cuenta"]][0] += r["_val"]
                sin_proy[r["cuenta"]][1].append(r)
        elif d["subtipo"] == "SOLO_A":
            d.update(explicacion=f"Costo del reporte operativo ({d['documento'] or ''}) no encontrado en contabilidad para el proyecto.")
        elif d["subtipo"] == "SOLO_B":
            d.update(explicacion=f"Costo contable del proyecto ({d['documento'] or ''}) que no figura en el reporte operativo.")
    operativos = tuple(R.cfg.get("centros_operativos") or [])
    for c, (v, regs) in sin_proy.items():
        oper = [r for r in regs if r.get("centro_costo") and r["centro_costo"].startswith(operativos)] if operativos else []
        R.dif("DIFERENCIA_CLASIFICACION", "MEDIO" if oper else "INFORMATIVO", f"Costos de la cuenta {c} sin proyecto asignado.",
              subtipo="COSTO_SIN_PROYECTO", registros=regs[:20], importe=v, clave=f"SIN_PROYECTO|{c}",
              recomendacion="Verifique si corresponden a un proyecto (costos indirectos o administrativos no requieren proyecto).")
    vistos = {}
    for r in R.registros.values():
        if r["_lado"] == "B" and r.get("numero") and r.get("proyecto"):
            k = (r["proyecto"], r.get("tercero"), r.get("serie"), r["numero"], r["_val"], r.get("cuenta"))
            if k in vistos:
                R.dif("DOCUMENTO_DUPLICADO", "ALTO", f"Costo duplicado en el proyecto {r['proyecto']} ({R.doc(r)}).", subtipo="COSTO_DUPLICADO",
                      registros=[r, vistos[k]])
            vistos[k] = r
    estados = {str(x["_clave"]): x for x in ctx.registros("SERVICIO_PROCESO")}
    saldo23 = defaultdict(int)
    for ln in ctx.de(R.cfg.get("fuentes", {}).get("B", {}).get("parametros", {}).get("cuenta_proceso", "23")):
        saldo23[ln.proyecto or ""] += ln.neto
    for proy, v in saldo23.items():
        e = estados.get(proy, {})
        op = (e.get("estado_operativo") or "").upper()
        fac = (e.get("estado_facturacion") or "").upper()
        if v and op in ("CULMINADO", "VALORIZADO", "FACTURADO"):
            R.dif("DIFERENCIA_CLASIFICACION", "MEDIO", f"El servicio {proy} está {op.lower()} ({fac.lower() or 'sin dato de facturación'}) y mantiene "
                  f"costos en la cuenta 23 por {Decimal(v) / 100}.", subtipo="SERVICIO_CULMINADO_CON_COSTOS", importe=Decimal(v) / 100,
                  clave=f"23|{proy}", recomendacion="Evalúe el reconocimiento en resultados o como activo por contrato (NIIF 15). La conciliación de "
                  "costos es independiente del reconocimiento de ingresos; no se mantienen costos como activo por la sola falta de facturación.")
    R.reporte = {"tipo": "SERVICIOS_PROCESO", "saldo_23_por_proyecto": {k or "(sin proyecto)": str(Decimal(v) / 100) for k, v in saldo23.items()}}


# ------------------------------------------------------------------ obligaciones financieras
def financieras(R: Resultado):
    from app.anexos.constructores import _d, _f
    from app.conciliacion.fuentes import contratos
    conts = contratos(R.cx)
    for d in R.difs:
        regs = [R.registros[i] for i in d["registros"]]
        if not regs:
            continue
        r = regs[0]
        if d["subtipo"] == "SOLO_A":
            pagada = r["datos"].get("pagada") in ("S", "SI", "SÍ")
            nombre = {"CAPITAL": "Cuota", "INTERES": "Intereses de la cuota", "COMISION": "Comisión de la cuota"}.get(r.get("concepto"), "Cuota")
            if pagada:
                d.update(subtipo="CUOTA_NO_REGISTRADA" if r.get("concepto") == "CAPITAL" else "INTERESES_PENDIENTES_REGISTRO",
                         explicacion=f"{nombre} {r.get('numero')} del contrato {r['datos'].get('contrato')} figura pagada en el cronograma y no se encontró "
                         "en contabilidad.")
            else:
                d.update(clasificacion="DIFERENCIA_TEMPORAL", prioridad="INFORMATIVO", subtipo="CUOTA_VENCIDA_IMPAGA",
                         explicacion=f"{nombre} {r.get('numero')} vencida e impaga según el cronograma (no es un error de registro).")
        elif d["subtipo"] == "SOLO_B":
            cont = r["datos"].get("contrato")
            if not cont:
                d.update(clasificacion="DIFERENCIA_CLASIFICACION", subtipo="PAGO_SIN_CONTRATO",
                         explicacion="Movimiento de obligaciones financieras sin contrato identificado.")
            else:
                iguales = [g for p in R.comp.pasadas for g in p.grupos for b, _ in g.b
                           if b["datos"].get("contrato") == cont and b["_val"] == r["_val"] and b.get("concepto") == r.get("concepto")]
                if iguales:
                    d.update(clasificacion="DOCUMENTO_DUPLICADO", prioridad="ALTO", subtipo="PAGO_DUPLICADO_POTENCIAL",
                             explicacion=f"Pago del contrato {cont} por el mismo importe que otra cuota ya conciliada: posible pago duplicado.")
                else:
                    d.update(subtipo="PAGO_SIN_CUOTA", explicacion=f"Pago del contrato {cont} sin cuota del cronograma que lo explique.")
    ctx = R.cx.libro()
    resumen = []
    for cod, k in conts.items():
        todas = [q for q in ctx.registros("CUOTA_FINANCIERA") if str(q.get("contrato")).upper() == cod]
        if not todas:
            continue
        versiones = sorted({int(q.get("version") or 1) for q in todas})
        ultima = [q for q in todas if int(q.get("version") or 1) == versiones[-1]]
        capital = _d(k.get("capital")) or CERO
        vencido = sum(((_d(q.get("capital")) or CERO) for q in ultima if (_f(q.get("fecha_vencimiento")) or date.max) <= R.run.fecha_corte
                       and str(q.get("pagada") or "").upper() in ("S", "SI", "SÍ")), CERO)
        pend_cron = capital - vencido
        me = (k.get("moneda") or "PEN").upper() != "PEN"
        neto = 0
        for ln in ctx.de(k.get("_cuenta") or "45"):
            texto = " ".join(normalizar_texto(x or "") for x in (ln.referencia, ln.numero, ln.glosa))
            if cod in texto:
                neto += ln.neto_me if me else ln.neto
        ap = sum(v for (c, t), v in ctx.apertura_ter.items() if c.startswith(k.get("_cuenta") or "45") and t and t == k.get("ruc_entidad"))
        libros = Decimal(-(neto + ap)) / 100
        resumen.append({"contrato": cod, "capital_original": str(capital), "capital_pendiente_cronograma": str(pend_cron), "saldo_libros": str(libros),
                        "diferencia": str(libros - pend_cron), "versiones_cronograma": versiones})
        if abs(libros - pend_cron) > R.tol.permitido(pend_cron):
            R.dif("DIFERENCIA_MONETARIA", "ALTO", f"Contrato {cod}: capital pendiente según cronograma {pend_cron} y saldo contable {libros}.",
                  subtipo="DIFERENCIA_CAPITAL", importe=libros - pend_cron, clave=f"CAPITAL|{cod}",
                  recomendacion="Revise amortizaciones no registradas, pagos duplicados o reclasificaciones de porción corriente.")
            R.difs[-1]["documento"] = cod
        if len(versiones) > 1:
            original = [q for q in todas if int(q.get("version") or 1) == versiones[0]]
            ta, tb = sum(((_d(q.get("capital")) or CERO) for q in original), CERO), sum(((_d(q.get("capital")) or CERO) for q in ultima), CERO)
            ia, ib = sum(((_d(q.get("interes")) or CERO) for q in original), CERO), sum(((_d(q.get("interes")) or CERO) for q in ultima), CERO)
            R.dif("DIFERENCIA_PARAMETRIZACION", "INFORMATIVO", f"Contrato {cod}: cronograma modificado (versión {versiones[0]} → {versiones[-1]}). "
                  f"Capital {ta} → {tb}; intereses {ia} → {ib}.", subtipo="CRONOGRAMA_MODIFICADO", importe=ib - ia, clave=f"CRONOGRAMA|{cod}")
    R.reporte = {"tipo": "FINANCIERAS", "contratos": resumen}


# ------------------------------------------------------------------ detracciones
def detracciones(R: Resultado):
    for d in R.difs:
        regs = [R.registros[i] for i in d["registros"]]
        if not regs:
            continue
        r = regs[0]
        pas = d.get("_pasada")
        if r["_lado"] == "A" and r["datos"].get("sin_tasa"):
            d.update(clasificacion="DIFERENCIA_PARAMETRIZACION", prioridad="MEDIO", subtipo="TASA_NO_CONFIGURADA",
                     explicacion=f"No se calcula la detracción esperada de {R.doc(r)}: {r['datos']['sin_tasa']}.",
                     recomendacion="Configure la tasa con su vigencia, fuente normativa y aprobación del responsable tributario.")
        elif pas == "A-B" and d["subtipo"] == "SOLO_A":
            d.update(clasificacion="DOCUMENTO_PENDIENTE_SUSTENTO", subtipo="FACTURA_SIN_DEPOSITO",
                     explicacion=f"Comprobante {R.doc(r)} sujeto a detracción sin constancia de depósito identificada "
                                 f"(esperado {r['_val']}). No constituye, por sí solo, un incumplimiento tributario.")
        elif pas == "A-B" and d["subtipo"] == "SOLO_B":
            d.update(clasificacion="DOCUMENTO_PENDIENTE_SUSTENTO", subtipo="DEPOSITO_SIN_DOCUMENTO",
                     explicacion=f"Constancia {r.get('operacion')} sin comprobante sujeto a detracción identificado.")
        elif pas == "B-C" and d["subtipo"] == "SOLO_B":
            d.update(clasificacion="REGISTRO_FALTANTE_CONTABILIDAD", subtipo="CONSTANCIA_NO_CONTABILIZADA",
                     explicacion=f"Constancia {r.get('operacion')} no registrada en contabilidad.")
        elif pas == "B-C" and d["subtipo"] == "SOLO_C":
            d.update(clasificacion="DOCUMENTO_PENDIENTE_SUSTENTO", subtipo="REGISTRO_SIN_CONSTANCIA",
                     explicacion=f"Registro contable de detracción ({r.get('operacion') or R.doc(r)}) sin constancia en el archivo.")
        elif d["subtipo"] == "DIFERENCIA_IMPORTE":
            d.update(subtipo="DIFERENCIA_IMPORTE_DETRACCION", explicacion=f"Importe depositado distinto al esperado: {d['explicacion']}")
        elif d["subtipo"] == "DUPLICADO_EXTERNA":
            d.update(subtipo="DEPOSITO_DUPLICADO", explicacion="Constancia de depósito duplicada.")
    # oportunidad del depósito (solo con plazo configurado en la regla aprobada)
    for p in R.comp.pasadas:
        if p.nombre != "A-B":
            continue
        for g in p.grupos:
            for a, _ in g.a:
                plazo = a["datos"].get("plazo_dias")
                for b, _ in g.b:
                    if plazo and a.get("fecha") and b.get("fecha") and (b["fecha"] - a["fecha"]).days > int(plazo):
                        R.dif("DIFERENCIA_TEMPORAL", "INFORMATIVO", f"Depósito de {R.doc(a)} realizado {(b['fecha'] - a['fecha']).days} días después de la "
                              f"emisión (plazo configurado {plazo}). Posible diferencia de oportunidad: requiere evaluación, no es una determinación definitiva.",
                              subtipo="POSIBLE_DEPOSITO_EXTEMPORANEO", registros=[a, b], importe=CERO)
    # aplicaciones de la fase 4 inconsistentes con la constancia
    from sqlalchemy import func, select
    from app.models import Aplicacion, PartidaAbierta
    for p in R.comp.pasadas:
        if p.nombre != "A-B":
            continue
        for g in p.grupos:
            for a, _ in g.a:
                aplicado = R.cx.db.scalar(select(func.sum(Aplicacion.importe)).join(PartidaAbierta, PartidaAbierta.id == Aplicacion.aplicacion_item_id)
                                          .where(Aplicacion.empresa_id == R.run.empresa_id, Aplicacion.estado == "APROBADA",
                                                 PartidaAbierta.clase == "DETRACCION", PartidaAbierta.serie == a.get("serie"),
                                                 PartidaAbierta.numero == a.get("numero"), PartidaAbierta.tercero == a.get("tercero")))
                depositado = sum((b["_val"] for b, _ in g.b), CERO)
                if aplicado is not None and Decimal(aplicado) != depositado:
                    R.dif("DIFERENCIA_MONETARIA", "MEDIO", f"La compensación aplicada como detracción a {R.doc(a)} ({aplicado}) difiere de la constancia "
                          f"({depositado}).", subtipo="APLICACION_INCONSISTENTE", registros=[a], importe=Decimal(aplicado) - depositado)


# ------------------------------------------------------------------ retenciones y percepciones
def retenciones(R: Resultado):
    from app.conciliacion.fuentes import _tasa
    for d in R.difs:
        regs = [R.registros[i] for i in d["registros"]]
        if not regs:
            continue
        r = regs[0]
        if d["subtipo"] == "SOLO_B":
            d.update(clasificacion="DOCUMENTO_PENDIENTE_SUSTENTO", subtipo="RETENCION_SIN_COMPROBANTE",
                     explicacion=f"Retención o percepción registrada en la cuenta {r.get('cuenta')} sin comprobante identificado.",
                     recomendacion="Obtenga el comprobante de retención o percepción que sustenta el registro.")
        elif d["subtipo"] == "SOLO_A":
            d.update(subtipo="RETENCION_NO_CONTABILIZADA", explicacion=f"Comprobante {R.doc(r)} no contabilizado.")
    for r in R.registros.values():
        if r["_lado"] != "A" or r["datos"].get("base") in (None, "None"):
            continue
        tipo = "PERCEPCION" if "PERCEP" in (r.get("concepto") or "") else "RETENCION"
        codigo = "IGV" if "IGV" in (r.get("concepto") or "") or r.get("concepto") in ("RETENCION", "PERCEPCION") else r.get("concepto")
        info, error = _tasa(R.cx.db, R.run.empresa_id, tipo, codigo, r.get("fecha"))
        if not info:
            R.dif("DIFERENCIA_PARAMETRIZACION", "INFORMATIVO", f"No se verifica la tasa de {R.doc(r)}: {error}. No se usan tasas fijas.",
                  subtipo="TASA_NO_CONFIGURADA", registros=[r], importe=CERO)
            continue
        esperado = (_num(r["datos"]["base"]) * info["tasa"] / 100).quantize(Decimal("0.01"))
        if abs(esperado - r["_val"]) > R.tol.permitido(esperado):
            R.dif("DIFERENCIA_MONETARIA", "MEDIO", f"{R.doc(r)}: importe {r['_val']} distinto del esperado {esperado} según la tasa vigente "
                  f"({info['tasa']} %).", subtipo="DIFERENCIA_TASA", registros=[r], importe=r["_val"] - esperado)


# ------------------------------------------------------------------ tributos
def tributos(R: Resultado):
    for d in R.difs:
        if d["subtipo"] == "SOLO_A":
            d.update(subtipo="DECLARADO_NO_CONTABILIZADO", explicacion=f"Obligación declarada ({d['documento'] or ''}) sin registro contable.")
        elif d["subtipo"] == "SOLO_B":
            d.update(subtipo="CONTABILIZADO_NO_DECLARADO", explicacion=f"Obligación contabilizada ({d['documento'] or ''}) sin declaración importada.",
                     recomendacion="Verifique la declaración; el sistema no presenta declaraciones ni realiza pagos.")
    R.reporte = {"tipo": "TRIBUTOS", "nota": "Comparación analítica: no se presentan declaraciones ni se realizan pagos."}


# ------------------------------------------------------------------ intercompañías
PARES = {"13": "43", "43": "13", "17": "47", "47": "17", "16": "46", "46": "16", "12": "42", "42": "12"}


def intercompania(R: Resultado):
    from app.models import Empresa
    rel = R.cx.db.get(Empresa, R.cx.ambito.get("empresa_relacionada_id"))
    for d in R.difs:
        if d["subtipo"] == "SOLO_A":
            d.update(subtipo="OPERACION_NO_RECIPROCA", explicacion=f"Operación registrada solo en {R.cx.empresa.razon_social}; "
                     f"{rel.razon_social if rel else 'la relacionada'} no la registra.")
        elif d["subtipo"] == "SOLO_B":
            d.update(subtipo="OPERACION_NO_RECIPROCA", explicacion=f"Operación registrada solo en {rel.razon_social if rel else 'la relacionada'}.")
        elif d["clasificacion"] == "DIFERENCIA_TIPO_CAMBIO":
            d.update(subtipo="DIFERENCIA_MONEDA")
    for p in R.comp.pasadas:
        for g in p.grupos:
            for a, _ in g.a:
                for b, _ in g.b:
                    esperado = PARES.get((a.get("cuenta") or "")[:2])
                    if esperado and not (b.get("cuenta") or "").startswith(esperado):
                        R.dif("DIFERENCIA_CLASIFICACION", "MEDIO", f"Clasificación no recíproca: {a.get('cuenta')} en la empresa y {b.get('cuenta')} "
                              f"en la relacionada (se esperaba {esperado}).", subtipo="CLASIFICACION_NO_RECIPROCA", registros=[a, b], importe=CERO)
    R.reporte = {"tipo": "INTERCOMPANIA", "empresa_relacionada": rel.razon_social if rel else None,
                 "nota": "No se realizan eliminaciones de consolidación ni compensaciones legales."}


# ------------------------------------------------------------------ origen y destino
def destino(R: Resultado):
    from app.analisis import destino as d3
    from app.models import CentroCosto
    pol = d3.politica(R.cx.db, R.run.empresa_id)
    autorizados = tuple(R.cfg.get("destinos_autorizados") or pol.destino)
    from sqlalchemy import select
    centros = {c.codigo: c.cuenta_destino for c in R.cx.db.scalars(select(CentroCosto).where(CentroCosto.empresa_id == R.run.empresa_id))}
    for d in list(R.difs):
        regs = [R.registros[i] for i in d["registros"]]
        pas = d.get("_pasada")
        if pas == "A-B" and d["subtipo"] == "SOLO_A":
            if not pol.usa_destino:
                R.difs.remove(d)
                continue
            d.update(clasificacion="REGISTRO_FALTANTE_FUENTE_EXTERNA", subtipo="GASTO_SIN_DESTINO", prioridad="MEDIO",
                     explicacion="Gasto por naturaleza destinable sin su destino en la clase 9 (asiento " + (regs[0]["datos"].get("asiento") or "") + ").")
        elif pas == "A-B" and d["subtipo"] == "SOLO_B":
            d.update(clasificacion="DIFERENCIA_NO_IDENTIFICADA", subtipo="DESTINO_SIN_ORIGEN",
                     explicacion="Destino en la clase 9 sin gasto de origen identificado en el asiento.")
        elif pas == "A-B" and d["clasificacion"] == "DIFERENCIA_MONETARIA" and d["subtipo"] in ("DISTRIBUCION", "DIFERENCIA_CAMPO"):
            dif = d["importe"]
            rep = sum((r["datos"].get("repetidas", 0) for r in regs if r["_lado"] == "B"), 0)
            if dif > 0:
                d.update(prioridad="ALTO", subtipo="DISTRIBUCION_DUPLICADA",
                         explicacion=f"El destino supera al origen en {dif}" + (" (líneas de destino repetidas)" if rep else "") +
                         ": posible distribución duplicada.", recomendacion="La clase 9 distribuye gastos ya registrados en la 6; no debe sumarse dos veces.")
            else:
                d.update(subtipo="DISTRIBUCION_INCOMPLETA", explicacion=f"El destino es menor que el origen en {abs(dif)}: distribución incompleta.")
        elif pas == "B-C" and d["subtipo"] in ("SOLO_B", "SOLO_C", "CONTRAPARTIDA_79", "DIFERENCIA_CAMPO"):
            d.update(subtipo="CONTRAPARTIDA_79", explicacion="El destino de la clase 9 no coincide con la contrapartida de la cuenta 79: " + d["explicacion"])
    for r in R.registros.values():
        if r["_lado"] != "B":
            continue
        for x in r["datos"].get("detalle", []):
            esperado = centros.get(x["centro_costo"])
            if not x["cuenta"].startswith(autorizados) or (esperado and not x["cuenta"].startswith(esperado)):
                R.dif("DIFERENCIA_CLASIFICACION", "MEDIO", f"Destino {x['cuenta']} no autorizado" + (f" para el centro de costo {x['centro_costo']} "
                      f"(destino configurado {esperado})" if esperado else "") + ".", subtipo="DESTINO_INCORRECTO", registros=[r],
                      importe=Decimal(x["importe"]), clave=f"DEST|{r['clave_registro']}|{x['cuenta']}|{x['centro_costo']}")
    R.reporte = {"tipo": "ORIGEN_DESTINO", "politica": {"modo": pol.modo, "destinables": pol.destinables, "destino": pol.destino, "cargas": pol.cargas,
                                                        "usa_destino": pol.usa_destino},
                 "nota": "La clase 9 distribuye gastos ya registrados por naturaleza: no es un gasto adicional. No se exige que toda la clase 6 "
                         "coincida con la clase 9 (cuentas no destinables o excluidas)."}


# ------------------------------------------------------------------ auxiliares vs mayor
def auxiliar_mayor(R: Resultado):
    for d in R.difs:
        pas = d.get("_pasada")
        if pas == "A-B":
            d.update(explicacion=d["explicacion"] + " Conciliación INTERNA: el anexo proviene del mismo libro y no es evidencia independiente.")
        elif pas == "B-C":
            d.update(prioridad="ALTO" if d["prioridad"] not in ("INFORMATIVO",) else d["prioridad"],
                     explicacion=d["explicacion"] + " Comparación con el balance de comprobación importado (fuente independiente del cálculo).")
    R.reporte = {"tipo": "AUXILIAR_MAYOR", "nota": "Los anexos generados desde el libro mayor no constituyen evidencia independiente de su exactitud; "
                                                    "las fuentes externas (balance importado, auxiliares de otros sistemas) sí lo son."}


ESPECIALIZADOS = {"BANCARIA": bancaria, "COMPRAS": lambda R: registros_tributarios(R, False), "VENTAS": lambda R: registros_tributarios(R, True),
                  "PLANILLAS": planillas, "ACTIVOS_FIJOS": activos, "INVENTARIOS": inventarios, "SERVICIOS_PROCESO": servicios,
                  "FINANCIERAS": financieras, "DETRACCIONES": detracciones, "RETENCIONES": retenciones, "TRIBUTOS": tributos,
                  "INTERCOMPANIA": intercompania, "ORIGEN_DESTINO": destino, "AUXILIAR_MAYOR": auxiliar_mayor}


def clasificar(R: Resultado, reglas: list[dict]) -> None:
    generica(R)
    # pasada de cada diferencia (para los clasificadores de varias fuentes)
    for d in R.difs:
        if d.get("_pasada"):
            continue
        if d["grupo"]:
            d["_pasada"] = d["grupo"][0]
        elif d["registros"]:
            lado = R.registros[d["registros"][0]]["_lado"]
            d["_pasada"] = next((p.nombre for p in R.comp.pasadas if lado in (p.a, p.b) and p.dispo.get(d["registros"][0], CERO) > 0),
                                next((p.nombre for p in R.comp.pasadas if lado in (p.a, p.b)), None))
    fn = ESPECIALIZADOS.get(R.tipo)
    if fn:
        fn(R)
    reglas_clasificacion(R, reglas)
