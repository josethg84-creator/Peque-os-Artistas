"""Módulos ORIGEN_DESTINO, PARAMETRIZACION, SERVICIOS, ACTIVOS, INVENTARIOS y PLANILLAS.

Origen y destino: se reutiliza la política y las reglas de distribución de la fase 3. No se asume que toda la clase 6
se distribuya: solo las cuentas destinables según la política, menos las excluidas. La clase 9 distribuye el mismo hecho
económico ya registrado en la 6: nunca se suman como gastos independientes.
Parametrización: sin la configuración real del ERP, las conclusiones se limitan a lo observable en los datos importados.
"""
import json
import statistics
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from app.analisis import destino as d3
from app.analisis import pcge
from app.auditoria.base import CERO, Res, Salida, asiento_de, dec, ev_calc, ev_linea, ev_reg, fase3, res_de_h3
from app.auditoria.r_cuentas import _f, conciliacion_memoria
from app.importers.normalizacion import normalizar_texto
from app.models import ConfiguracionImportada

CIEN = Decimal("100")


# ===================================================================== ORIGEN Y DESTINO
def reporte_destino(ax) -> list[dict]:
    """Filas del reporte de origen y destino por asiento (sección 11): una fila por cuenta de origen destinable."""
    if "_rep_destino" in ax.__dict__:
        return ax._rep_destino
    pol = d3.politica(ax.db, ax.empresa_id)
    reglas = d3.reglas_vigentes(ax.db, ax.empresa_id, ax.corte)
    excl = [r.cuenta_origen for r in reglas if r.excluir]
    filas = []
    for k, ls in ax.asientos.items():
        origen = [x for x in ls if x.cuenta.startswith("6") and d3._empieza(x.cuenta, pol.destinables) and not d3._empieza(x.cuenta, excl)]
        dest = [x for x in ls if d3._empieza(x.cuenta, pol.destino)]
        trans = [x for x in ls if x.cuenta.startswith(pol.cargas)]
        if not origen and not dest:
            continue
        reg_dest = defaultdict(lambda: CERO)
        for x in dest:
            reg_dest[x.cuenta] += x.debe - x.haber
        esp = defaultdict(lambda: CERO)
        sin_regla = CERO
        for x in origen:
            neto = x.debe - x.haber
            unidad = ax.centros[x.cc].unidad_negocio if x.cc in ax.centros else None
            apl = d3._aplicables(reglas, x.cuenta, x.cc, x.proyecto, unidad, x.maquinaria)
            if apl:
                for r in apl:
                    if r.cuenta_destino:
                        esp[r.cuenta_destino] += (neto * r.porcentaje / CIEN).quantize(Decimal("0.01"))
            elif x.cuenta in ax.plan and ax.plan[x.cuenta].cuenta_destino_debe:
                esp[ax.plan[x.cuenta].cuenta_destino_debe] += neto
            elif x.cc in ax.centros and ax.centros[x.cc].cuenta_destino:
                esp[ax.centros[x.cc].cuenta_destino] += neto
            else:
                sin_regla += neto
        o = sum((x.debe - x.haber for x in origen), CERO)
        dd = sum(reg_dest.values(), CERO)
        t = sum((x.haber - x.debe for x in trans), CERO)
        repetidas = len(dest) - len({(x.cuenta, x.cc, x.debe, x.haber) for x in dest})
        filas.append({"k": k, "asiento": "-".join(p for p in (k[2], k[3]) if p), "periodo": k[1], "lineas": ls,
                      "cuentas_origen": sorted({x.cuenta for x in origen}), "importe_original": sum((x.debe - x.haber for x in ls if x.cuenta.startswith("6")), CERO),
                      "sujeto": o, "destino_esperado": {c: v for c, v in esp.items()}, "sin_regla": sin_regla,
                      "destino_registrado": dict(reg_dest), "transferencia": t, "cuenta_transferencia": pol.cargas,
                      "diferencia": o - dd, "diferencia_79": dd - t, "repetidas": repetidas})
    ax._rep_destino = filas
    return filas


def _res_dest(f, titulo, condicion, importe, sufijo, impacto, **kw) -> Res:
    x = max(f["lineas"], key=lambda y: y.debe + y.haber)
    return Res(titulo=titulo, condicion=condicion, importe=abs(importe), cuenta=(f["cuentas_origen"] or [x.cuenta])[0], asiento=f["asiento"],
               linea_id=x.id, centro_costo=x.cc, evidencia=[ev_linea(y) for y in f["lineas"][:15]] + [ev_calc(
                   "Reporte de origen y destino", sujeto=f["sujeto"], destino_esperado=json.dumps({c: str(v) for c, v in f["destino_esperado"].items()}),
                   destino_registrado=json.dumps({c: str(v) for c, v in f["destino_registrado"].items()}), transferencia=f["transferencia"],
                   diferencia=f["diferencia"])], clave=f"ODE|{sufijo}|{f['k']}", exposicion=f"DESTINO|{f['k'][0]}|{f['periodo']}|{f['asiento']}",
               impacto_potencial=impacto, regularizacion="REQUIERE_AJUSTE", **kw)


def destino(ax, r) -> Salida:
    caso = r.p["caso"]
    pol = d3.politica(ax.db, ax.empresa_id)
    if not pol.usa_destino:
        return Salida(estado="SIN_DATOS", mensaje="La política contable indica que la empresa no usa la clase 9 (destino).")
    tol = pol.tolerancia
    out = []
    filas = reporte_destino(ax)
    if caso == "SIN_DESTINO" and not any(d3._empieza(ln.cuenta, pol.destino) for ln in ax.lineas_todas):
        sujeto = sum((f["sujeto"] for f in filas), CERO)
        if sujeto > tol:
            out.append(Res(titulo="La política indica destino (clase 9) pero el periodo no registra ningún asiento de destino",
                           condicion=f"Gastos destinables por {sujeto} en {len(filas)} asientos sin ninguna línea de las cuentas {', '.join(pol.destino)}.",
                           importe=sujeto, clave="ODE|SIN_DESTINO_GLOBAL", exposicion="DESTINO|GLOBAL", estructural=False,
                           evidencia=[ev_calc("Política de destino (fase 3)", destinables=", ".join(pol.destinables), destino=", ".join(pol.destino),
                                              modo=pol.modo, asientos=len(filas))],
                           impacto_potencial="Estado de resultados por función incompleto; el resultado por naturaleza no cambia.",
                           regularizacion="REQUIERE_PARAMETRIZACION",
                           recomendacion="Confirme si la empresa usa la clase 9; si no, actualice la política contable (no aplica destino)."))
        return Salida(out, len(filas), sujeto, "Política de destino sin asientos de destino en el periodo: un único hallazgo de configuración.")
    for f in filas:
        if not ax.asiento_en_alcance(f["lineas"]):
            continue
        if caso == "SIN_DESTINO" and f["sujeto"] > tol and not f["destino_registrado"] and pol.modo == "MISMO_ASIENTO":
            out.append(_res_dest(f, f"Gasto sin destino en el asiento {f['asiento']}", f"Gasto destinable de {f['sujeto']} "
                                 f"({', '.join(f['cuentas_origen'])}) sin su destino en la clase 9.", f["sujeto"], "SD",
                                 "El estado de resultados por función queda incompleto; no altera el resultado por naturaleza."))
        elif caso == "SIN_ORIGEN" and not f["sujeto"] and sum(f["destino_registrado"].values(), CERO) > tol:
            v = sum(f["destino_registrado"].values(), CERO)
            out.append(_res_dest(f, f"Destino sin origen identificado en el asiento {f['asiento']}", f"Destino de {v} en "
                                 f"{', '.join(f['destino_registrado'])} sin gasto de origen destinable en el asiento.", v, "SO",
                                 "Posible gasto por función sin respaldo por naturaleza o distribución de otro asiento."))
        elif caso == "DUPLICADO" and f["sujeto"] > tol and (f["repetidas"] or -f["diferencia"] > tol):
            exceso = -f["diferencia"] if -f["diferencia"] > tol else f["sujeto"]
            out.append(_res_dest(f, f"Gasto distribuido más de una vez en el asiento {f['asiento']}", f"Origen {f['sujeto']}; destino registrado "
                                 f"{sum(f['destino_registrado'].values(), CERO)}" + (" (líneas de destino repetidas)." if f["repetidas"] else "."),
                                 exceso, "DUP", "Gastos por función sobreestimados; la clase 9 no debe sumarse como gasto adicional.", probabilidad=4))
        elif caso == "INCOMPLETO" and f["destino_registrado"] and f["diferencia"] > tol:
            out.append(_res_dest(f, f"Distribución incompleta en el asiento {f['asiento']}", f"Origen {f['sujeto']}; destino "
                                 f"{sum(f['destino_registrado'].values(), CERO)}: falta distribuir {f['diferencia']}.", f["diferencia"], "INC",
                                 "Gastos por función subestimados."))
        elif caso == "INCORRECTO" and f["destino_esperado"] and f["destino_registrado"]:
            malos = {c: v for c, v in f["destino_registrado"].items() if not any(c.startswith(e) for e in f["destino_esperado"])}
            if malos:
                out.append(_res_dest(f, f"Destino incorrecto en el asiento {f['asiento']}", f"Se registró en {', '.join(malos)}; según las reglas "
                                     f"vigentes corresponde {', '.join(f['destino_esperado'])}.", sum(malos.values(), CERO), "MAL",
                                     "Gasto presentado en una función distinta a la configurada.", regularizacion="REQUIERE_RECLASIFICACION"))
        elif caso == "TRANSFERENCIA" and abs(f["diferencia_79"]) > tol and (f["destino_registrado"] or f["transferencia"]):
            out.append(_res_dest(f, f"Contrapartida de transferencia incorrecta en el asiento {f['asiento']}", f"Destino "
                                 f"{sum(f['destino_registrado'].values(), CERO)} y cuenta {f['cuenta_transferencia']} {f['transferencia']}: diferencia "
                                 f"{f['diferencia_79']}.", f["diferencia_79"], "79",
                                 "Posible duplicidad o falta en la presentación del estado de resultados."))
    return Salida(out, len(filas), sum((f["sujeto"] for f in filas), CERO),
                  f"Por asiento: origen destinable (política fase 3: {', '.join(pol.destinables)}; excluidas por regla), destino ({', '.join(pol.destino)}) "
                  f"y transferencia ({pol.cargas}); destino esperado por reglas de distribución, plan de cuentas o centro de costo.")


def porcentajes(ax, r) -> Salida:
    reglas = d3.reglas_vigentes(ax.db, ax.empresa_id, ax.corte)
    g = defaultdict(list)
    for x in reglas:
        if not x.excluir:
            g[(x.cuenta_origen, x.centro_costo, x.proyecto, x.unidad_negocio, x.maquinaria)].append(x)
    out = []
    for k, xs in g.items():
        tot = sum((x.porcentaje for x in xs), CERO)
        if tot != CIEN:
            out.append(Res(titulo=f"Porcentajes de distribución de {k[0]} suman {tot} %", condicion=f"Reglas vigentes para la cuenta {k[0]} "
                           f"(CC {k[1] or 'todos'}, proyecto {k[2] or 'todos'}) suman {tot} % en lugar de 100 %.", importe=CERO, cuenta=k[0],
                           evidencia=[ev_reg("destination_mapping_rules", x.id, f"{x.cuenta_origen} → {x.cuenta_destino} {x.porcentaje} %") for x in xs],
                           clave=f"PCT|{k}", exposicion=f"REGLA_DIST|{k}", estructural=True, regularizacion="REQUIERE_PARAMETRIZACION"))
    return Salida(out, len(reglas), metodo="Suma de porcentajes de las reglas de distribución vigentes por combinación de dimensiones.")


def _config(ax, tipo):
    c = ax.db.scalar(select(ConfiguracionImportada).where(ConfiguracionImportada.empresa_id == ax.empresa_id, ConfiguracionImportada.tipo == tipo)
                     .order_by(ConfiguracionImportada.version.desc()))
    return c, (json.loads(c.items) if c else [])


def clase9_en_resultados(ax, r) -> Salida:
    conf, items = _config(ax, "RUBROS_UTILIZADOS")
    if not conf:
        return Salida(estado="SIN_DATOS", mensaje="No se importó la configuración de rubros de los reportes: no puede verificarse la presentación.")
    res = [i for i in items if (i.get("estado_financiero") or "").upper().startswith("RESULT")]
    nueve = [i for i in res if str(i["cuenta"]).startswith("9")]
    seis = [i for i in res if str(i["cuenta"]).startswith("6")]
    out = []
    if nueve and seis:
        saldo = sum((dec(ax.ctx3.nodos[i["cuenta"]].sf) / 100 for i in nueve if i["cuenta"] in ax.ctx3.nodos), CERO) if ax.ctx3.nodos else CERO
        out.append(Res(titulo="Cuentas de la clase 9 incluidas como gasto adicional en el estado de resultados",
                       condicion=f"El reporte {conf.sistema} v{conf.version} suma en resultados las cuentas analíticas "
                                 f"{', '.join(sorted(str(i['cuenta']) for i in nueve))} junto con los gastos por naturaleza (clase 6).",
                       importe=abs(saldo), cuenta=str(nueve[0]["cuenta"]), clave="ODE|CLASE9_GASTO", exposicion="PRESENTACION|CLASE9",
                       evidencia=[ev_reg("audit_configurations", conf.id, f"Rubro «{i.get('rubro')}» incluye {i['cuenta']}") for i in nueve[:20]],
                       estructural=True, impacto_potencial="El mismo hecho económico se presentaría dos veces: gastos sobreestimados en el estado de resultados.",
                       regularizacion="REQUIERE_PARAMETRIZACION", probabilidad=4))
    return Salida(out, len(items), metodo="Rubros del estado de resultados importados: cuentas 9 sumadas junto con la clase 6.")


def distribucion_aprobada(ax, r) -> Salida:
    conf, items = _config(ax, "DISTRIBUCION_APROBADA")
    if not conf:
        return Salida(estado="SIN_DATOS", mensaje="No se importó la configuración aprobada de distribución.")
    usadas = {(x.cuenta_origen, x.centro_costo or "", x.cuenta_destino or ""): x.porcentaje
              for x in d3.reglas_vigentes(ax.db, ax.empresa_id, ax.corte) if not x.excluir}
    aprob = {(str(i.get("cuenta_origen")), i.get("centro_costo") or "", str(i.get("cuenta_destino") or "")): dec(i.get("porcentaje", 100)) for i in items}
    out = []
    for k in sorted(set(usadas) | set(aprob)):
        if usadas.get(k) != aprob.get(k):
            out.append(Res(titulo=f"Distribución de {k[0]} difiere de la configuración aprobada", condicion=f"{k[0]} (CC {k[1] or 'todos'}) → {k[2]}: "
                           f"aprobado {aprob.get(k, 'no existe')} %, utilizado {usadas.get(k, 'no existe')} %.", cuenta=k[0], clave=f"DAP|{k}",
                           exposicion=f"REGLA_DIST|{k}", estructural=True, regularizacion="REQUIERE_PARAMETRIZACION",
                           evidencia=[ev_reg("audit_configurations", conf.id, f"Configuración aprobada {conf.sistema} v{conf.version}")]))
    return Salida(out, len(set(usadas) | set(aprob)), metodo="Reglas de distribución vigentes (fase 3) frente a la configuración aprobada importada.")


# ===================================================================== PARAMETRIZACIÓN DEL ERP
CATEGORIA = {"1": "ACTIVO", "2": "ACTIVO", "3": "ACTIVO", "4": "PASIVO", "5": "PATRIMONIO", "6": "GASTO", "7": "INGRESO"}
PALABRAS_RUBRO = [("ACTIVO", ("ACTIVO", "EFECTIVO", "CAJA", "BANCO", "COBRAR", "INVENTARIO", "EXISTENCIA", "INMUEBLE", "MAQUINARIA", "INTANGIBLE")),
                  ("PASIVO", ("PASIVO", "PAGAR", "OBLIGACION", "TRIBUTO", "PROVISION", "REMUNERACIONES POR")),
                  ("PATRIMONIO", ("PATRIMONIO", "CAPITAL", "RESERVA", "RESULTADOS ACUMULADOS")),
                  ("INGRESO", ("INGRESO", "VENTA")), ("GASTO", ("GASTO", "COSTO", "CARGA"))]


def _categoria_rubro(i) -> str | None:
    if i.get("clase_rubro"):
        return str(i["clase_rubro"]).upper()
    t = normalizar_texto(i.get("rubro") or "")
    return next((c for c, ps in PALABRAS_RUBRO if any(p in t for p in ps)), None)


def _plan_utilizado(ax):
    conf, items = _config(ax, "PLAN_UTILIZADO")
    if conf:
        return conf, {str(i["cuenta"]): i for i in items}
    return None, {c: {"cuenta": c, "descripcion": x.descripcion, "naturaleza": x.naturaleza, "admite_movimiento": x.admite_movimiento,
                      "cuenta_destino_debe": x.cuenta_destino_debe} for c, x in ax.plan.items()}


def naturaleza(ax, r) -> Salida:
    conf, plan = _plan_utilizado(ax)
    if not plan:
        return Salida(estado="SIN_DATOS", mensaje="No hay plan de cuentas importado ni configuración del ERP.")
    out = []
    for c, i in plan.items():
        esperada = pcge.naturaleza_pcge(c)
        nat = (i.get("naturaleza") or "").upper()[:1]
        if esperada and nat and nat != esperada and c[:2] not in ("39", "29", "19", "36"):
            out.append(Res(titulo=f"Naturaleza de la cuenta {c} distinta a la del PCGE", condicion=f"La cuenta {c} ({i.get('descripcion') or ''}) está "
                           f"configurada como {'deudora' if nat == 'D' else 'acreedora'}; en el PCGE es {'deudora' if esperada == 'D' else 'acreedora'}.",
                           cuenta=c, clave=f"NAT|{c}", exposicion=f"PARAM|{c}", estructural=True, regularizacion="REQUIERE_PARAMETRIZACION",
                           evidencia=[ev_calc("Naturaleza", configurada=nat, pcge=esperada, origen="configuración importada" if conf else "plan de cuentas (fase 2)")]))
    return Salida(out, len(plan), metodo="Naturaleza configurada frente a la del PCGE (se exceptúan cuentas correctoras 19, 29, 36, 39).")


def rubros(ax, r) -> Salida:
    caso = r.p["caso"]
    conf, items = _config(ax, "RUBROS_UTILIZADOS")
    if not conf:
        return Salida(estado="SIN_DATOS", mensaje="No se importó la configuración de reportes financieros: las conclusiones se limitan a los datos.")
    out = []
    if caso in ("RUBRO_INCORRECTO", "BALANCE_EN_RESULTADOS", "RESULTADOS_EN_BALANCE"):
        for i in items:
            c = str(i["cuenta"])
            estado = (i.get("estado_financiero") or "").upper()
            cat, catr = CATEGORIA.get(c[:1]), _categoria_rubro(i)
            if caso == "BALANCE_EN_RESULTADOS" and c[:1] in "12345" and estado.startswith("RESULT"):
                txt = f"La cuenta de balance {c} se presenta en el estado de resultados (rubro «{i.get('rubro')}»)."
            elif caso == "RESULTADOS_EN_BALANCE" and c[:1] in "67" and estado.startswith("BALANCE") or (caso == "RESULTADOS_EN_BALANCE" and c[:1] in "67" and estado.startswith("SITUACION")):
                txt = f"La cuenta de resultados {c} se presenta en el estado de situación financiera (rubro «{i.get('rubro')}»)."
            elif caso == "RUBRO_INCORRECTO" and cat and catr and cat != catr and c[:2] not in ("39", "29", "19", "36"):
                txt = f"La cuenta {c} ({cat.lower()}) está agrupada en el rubro «{i.get('rubro')}» ({catr.lower()})."
            else:
                continue
            out.append(Res(titulo=txt.split(" (")[0] if caso != "RUBRO_INCORRECTO" else f"Cuenta {c} en un rubro financiero incorrecto", condicion=txt,
                           cuenta=c, clave=f"{caso}|{c}", exposicion=f"PARAM|{c}", estructural=True, regularizacion="REQUIERE_PARAMETRIZACION",
                           evidencia=[ev_reg("audit_configurations", conf.id, f"{conf.sistema} v{conf.version}: {c} → {i.get('rubro')} ({estado})")]))
    elif caso in ("DUPLICIDAD", "INCLUIDA_DOS_VECES"):
        por = defaultdict(list)
        for i in items:
            por[str(i["cuenta"])].append(i)
        codigos = sorted(por)
        for c in codigos:
            rubros_c = {i.get("rubro") for i in por[c]}
            ancestros = [a for a in codigos if a != c and c.startswith(a)]
            if caso == "DUPLICIDAD" and len(rubros_c) > 1:
                txt = f"La cuenta {c} está agrupada en {len(rubros_c)} rubros: {', '.join(sorted(map(str, rubros_c)))}."
            elif caso == "INCLUIDA_DOS_VECES" and ancestros:
                txt = f"La cuenta {c} se incluye explícitamente y también a través de {', '.join(ancestros)}: se sumaría dos veces."
            else:
                continue
            out.append(Res(titulo=f"Cuenta {c} incluida más de una vez en los reportes" if caso != "DUPLICIDAD" else f"Duplicidad en la agrupación de la cuenta {c}",
                           condicion=txt, cuenta=c, clave=f"{caso}|{c}", exposicion=f"PARAM|{c}", estructural=True, regularizacion="REQUIERE_PARAMETRIZACION",
                           evidencia=[ev_reg("audit_configurations", conf.id, f"{conf.sistema} v{conf.version}")]))
    elif caso == "OMITIDAS":
        pref = [str(i["cuenta"]) for i in items]
        for c, n in ax.ctx3.nodos.items():
            if (n.hijos == 0 or n.propio) and c[:1] in "1234567" and n.sf and not any(c.startswith(p) for p in pref):
                out.append(Res(titulo=f"Cuenta {c} con saldo omitida en los reportes", condicion=f"La cuenta {c} tiene saldo {dec(n.sf) / 100} y no está "
                               "incluida en ningún rubro de la configuración de reportes.", importe=abs(dec(n.sf) / 100), cuenta=c, clave=f"OMI|{c}",
                               exposicion=f"CUENTA|{c}", estructural=True, regularizacion="REQUIERE_PARAMETRIZACION",
                               evidencia=[ev_reg("audit_configurations", conf.id, f"{conf.sistema} v{conf.version}")]))
    return Salida(out, len(items), metodo=f"Configuración de rubros importada ({conf.sistema} v{conf.version}): {caso.lower().replace('_', ' ')}.")


def politicas(ax, r) -> Salida:
    aprob, items = _config(ax, "PLAN_APROBADO")
    if not aprob:
        return Salida(estado="SIN_DATOS", mensaje="No se importó el plan de cuentas aprobado: no puede compararse con el utilizado.")
    conf, usado = _plan_utilizado(ax)
    out = []
    for i in items:
        c = str(i["cuenta"])
        u = usado.get(c)
        if not u:
            continue
        difs = [f"{campo}: aprobado {i.get(campo)} / utilizado {u.get(campo)}" for campo in ("naturaleza", "admite_movimiento", "cuenta_destino_debe")
                if i.get(campo) not in (None, "") and str(i.get(campo)).upper()[:1] != str(u.get(campo)).upper()[:1]]
        if difs:
            out.append(Res(titulo=f"Configuración de la cuenta {c} distinta a la aprobada", condicion="; ".join(difs) + ".", cuenta=c, clave=f"POL|{c}",
                           exposicion=f"PARAM|{c}", estructural=True, regularizacion="REQUIERE_PARAMETRIZACION",
                           evidencia=[ev_reg("audit_configurations", aprob.id, f"Plan aprobado {aprob.sistema} v{aprob.version}")]))
    return Salida(out, len(items), metodo="Plan de cuentas aprobado frente al utilizado (naturaleza, movimiento y destino).")


def cambios_sin_sustento(ax, r) -> Salida:
    out, n = [], 0
    confs = ax.db.scalars(select(ConfiguracionImportada).where(ConfiguracionImportada.empresa_id == ax.empresa_id)
                          .order_by(ConfiguracionImportada.tipo, ConfiguracionImportada.version)).all()
    previo = {}
    for c in confs:
        n += 1
        p = previo.get(c.tipo)
        if p and json.loads(p.items) != json.loads(c.items) and not (c.sustento or "").strip():
            a, b = {str(i.get("cuenta")): i for i in json.loads(p.items)}, {str(i.get("cuenta")): i for i in json.loads(c.items)}
            cambios = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            out.append(Res(titulo=f"Cambio de configuración {c.tipo.lower().replace('_', ' ')} sin sustento", condicion=f"Versión {p.version} → {c.version}: "
                           f"{len(cambios)} cuentas modificadas ({', '.join(cambios[:10])}) sin sustento registrado.", clave=f"CSS|{c.tipo}|{c.version}",
                           exposicion=f"CONFIG|{c.tipo}|{c.version}", calidad="INSUFICIENTE", regularizacion="REQUIERE_DOCUMENTACION",
                           evidencia=[ev_reg("audit_configurations", p.id, f"Versión {p.version}"), ev_reg("audit_configurations", c.id, f"Versión {c.version}")]))
        previo[c.tipo] = c
    return Salida(out, n, metodo="Versiones sucesivas de cada configuración importada con cambios y sin sustento.")


# ===================================================================== SERVICIOS EN PROCESO
def _saldo23(ax, cuenta="23"):
    s = defaultdict(lambda: CERO)
    mov = defaultdict(lambda: None)
    for ln in ax.ctx3.lineas_hasta_corte:
        if ln.cuenta.startswith(cuenta):
            s[ln.proyecto or ""] += ln.debe - ln.haber
            if ln.periodo:
                mov[ln.proyecto or ""] = max(mov[ln.proyecto or ""] or ln.fecha, ln.fecha) if ln.fecha else mov[ln.proyecto or ""]
    return s, mov


def servicios(ax, r) -> Salida:
    caso = r.p["caso"]
    saldo, ultimo = _saldo23(ax)
    estados = {str(x["_clave"]): x for x in ax.registros("SERVICIO_PROCESO")}
    out = []
    if caso in ("CULMINADO", "SUSPENDIDO", "FACTURADO", "AVANCE"):
        if not estados:
            return Salida(estado="SIN_DATOS", mensaje="No se importó el registro de servicios en proceso (estado operativo y de facturación).")
        for p, e in estados.items():
            v = saldo.get(p, CERO)
            op, fac = normalizar_texto(e.get("estado_operativo") or ""), normalizar_texto(e.get("estado_facturacion") or "")
            ev = [ev_reg("annex_support_records", e["_id"], f"Servicio {p}", estado_operativo=op, estado_facturacion=fac, saldo_23=v)]
            if caso == "CULMINADO" and v > 0 and op in ("CULMINADO", "TERMINADO", "CONCLUIDO", "VALORIZADO"):
                out.append(Res(titulo=f"Servicio {p} culminado con costos pendientes de evaluación", condicion=f"El servicio está {op.lower()} "
                               f"({fac.lower() or 'sin dato de facturación'}) y mantiene {v} en la cuenta 23.", importe=v, cuenta="23", proyecto=p,
                               evidencia=ev, clave=f"SPR|CUL|{p}", exposicion=f"PROY23|{p}", regularizacion="REQUIERE_AJUSTE",
                               recomendacion="Evalúe la transferencia del costo a resultados o a un activo por contrato según la obligación de desempeño "
                                             "(NIIF 15) y la naturaleza del costo; la fecha de facturación no es el único criterio."))
            elif caso == "SUSPENDIDO" and v > 0 and op in ("SUSPENDIDO", "PARALIZADO", "CANCELADO"):
                out.append(Res(titulo=f"Costos acumulados de un proyecto {op.lower()}: {p}", condicion=f"Saldo {v} en la cuenta 23 de un proyecto {op.lower()}.",
                               importe=v, cuenta="23", proyecto=p, evidencia=ev, clave=f"SPR|SUS|{p}", exposicion=f"PROY23|{p}",
                               recomendacion="Evalúe la recuperabilidad de los costos acumulados."))
            elif caso == "FACTURADO" and v > 0 and fac in ("FACTURADO", "FACTURADO TOTAL", "COBRADO"):
                out.append(Res(titulo=f"Posible activo mantenido indebidamente: servicio {p} facturado con costos en la 23",
                               condicion=f"El servicio figura {fac.lower()} y mantiene {v} como costo en proceso.", importe=v, cuenta="23", proyecto=p,
                               evidencia=ev, clave=f"SPR|FAC|{p}", exposicion=f"PROY23|{p}", regularizacion="REQUIERE_AJUSTE"))
            elif caso == "AVANCE" and e.get("avance_operativo") not in (None, "") and e.get("presupuesto_costo") not in (None, ""):
                esperado = dec(e["presupuesto_costo"]) * dec(e["avance_operativo"]) / CIEN
                real = v + dec(e.get("costo_reconocido") or 0)
                tol = Decimal(str(r.p.get("tolerancia_pct", 10)))
                if esperado and abs(real - esperado) * 100 / esperado > tol:
                    out.append(Res(titulo=f"Avance operativo y costo contable del proyecto {p} difieren", condicion=f"Avance {e['avance_operativo']} % sobre "
                                   f"un presupuesto de {e['presupuesto_costo']} sugiere {esperado.quantize(Decimal('0.01'))}; costo contable {real}.",
                                   importe=abs(real - esperado), cuenta="23", proyecto=p, evidencia=ev, clave=f"SPR|AVA|{p}", exposicion=f"PROY23|{p}",
                                   calidad="PARCIAL"))
    elif caso == "SIN_PROYECTO":
        operativos = tuple(r.p.get("centros_operativos", []))
        for ln in ax.lineas:
            if (ln.cuenta.startswith("23") or (operativos and ln.cuenta.startswith("6") and (ln.cc or "").startswith(operativos))) and not ln.proyecto \
                    and ln.debe:
                out.append(Res(titulo=f"Costo sin proyecto asignado en la cuenta {ln.cuenta}", condicion=f"Línea {ln.id} por {ln.debe} sin proyecto.",
                               importe=ln.debe, cuenta=ln.cuenta, linea_id=ln.id, asiento=asiento_de(ln), centro_costo=ln.cc, evidencia=[ev_linea(ln)],
                               clave=f"SPR|SP|{ln.id}", exposicion=f"LINEA|{ln.id}", regularizacion="REQUIERE_RECLASIFICACION"))
    elif caso == "ANTERIORES":
        hs = fase3(ax, "COSTO_EN_PROCESO", r.codigo, cuentas=["23"], valor=r.p.get("dias", 180), parametros={"dias_inactividad": r.p.get("dias_inactividad", 90)})
        out = [res_de_h3(h, "SPR|ANT") for h in hs]
    elif caso == "TRANSFERENCIAS":
        costos, transf = defaultdict(lambda: CERO), defaultdict(lambda: CERO)
        for ln in ax.lineas:
            if ln.proyecto and ln.cuenta.startswith("6"):
                costos[ln.proyecto] += ln.debe - ln.haber
            if ln.proyecto and ln.cuenta.startswith("23"):
                transf[ln.proyecto] += ln.debe - ln.haber
        for p, t in transf.items():
            if t > costos.get(p, CERO) + dec(r.p.get("tolerancia", "1")):
                out.append(Res(titulo=f"Transferencia a la cuenta 23 mayor que los costos del proyecto {p}", condicion=f"Transferido a la 23: {t}; costos "
                               f"del ejercicio con proyecto: {costos.get(p, CERO)}.", importe=t - costos.get(p, CERO), cuenta="23", proyecto=p,
                               evidencia=[ev_calc("Costos vs transferencia", costos=costos.get(p, CERO), transferido=t)], clave=f"SPR|TRF|{p}",
                               exposicion=f"PROY23|{p}"))
    elif caso == "SIN_SUSTENTO":
        for k, ls in ax.asientos.items():
            c23 = [x for x in ls if x.cuenta.startswith("23") and x.debe]
            if c23 and not any(x.cuenta.startswith("71") for x in ls) and not any(x.numero for x in ls):
                x = c23[0]
                out.append(Res(titulo=f"Costo en proceso sin sustento en el asiento {asiento_de(x)}", condicion="Cargo a la 23 que no proviene de la "
                               "variación de la producción (71) ni tiene documento.", importe=sum((y.debe for y in c23), CERO), cuenta=x.cuenta,
                               proyecto=x.proyecto, asiento=asiento_de(x), linea_id=x.id, evidencia=[ev_linea(y) for y in ls[:10]],
                               clave=f"SPR|SS|{k}", exposicion=f"ASIENTO|{k[0]}|{k[1]}|{asiento_de(x)}", calidad="INSUFICIENTE",
                               regularizacion="REQUIERE_DOCUMENTACION"))
    return Salida(out, len(saldo) or len(ax.lineas), sum(saldo.values(), CERO), f"Servicios en proceso — {caso.lower().replace('_', ' ')}: cuenta 23 por "
                  "proyecto, registro de servicios (fase 5) y costos de la clase 6.")


# ===================================================================== ACTIVOS FIJOS
MAPA_ACTIVOS = {"DEPRECIACION_EXCEDE": {"DEPRECIACION_EXCEDE_DEPRECIABLE"}, "POSTERIOR_BAJA": {"DEPRECIACION_POSTERIOR_BAJA"},
                "BAJA": {"BAJA_NO_REGISTRADA"}, "DIFERENCIAS": {"ACTIVO_SOLO_EN_CONTABILIDAD", "ACTIVO_SOLO_EN_AUXILIAR", "DIFERENCIA_COSTO",
                                                               "DIFERENCIA_DEPRECIACION", "SALDO_SIN_CODIGO"},
                "TOTALMENTE_DEPRECIADO": {"TOTALMENTE_DEPRECIADO"}, "FINANCIERA_TRIBUTARIA": {"FINANCIERA_VS_TRIBUTARIA"}}


def activos(ax, r) -> Salida:
    caso = r.p["caso"]
    regs = ax.registros("ACTIVO_FIJO")
    if caso in MAPA_ACTIVOS:
        if not regs:
            return Salida(estado="SIN_DATOS", mensaje="No se importó el registro de activos fijos (fase 5).")
        r.p["tipo"], r.p["subtipos"] = "ACTIVOS_FIJOS", sorted(MAPA_ACTIVOS[caso])
        s = conciliacion_memoria(ax, r)
        for x in s.res:
            if caso == "TOTALMENTE_DEPRECIADO":
                x.riesgo_minimo = "INFORMATIVO"
                x.recomendacion = "Verifique si el activo sigue en uso y revise su vida útil; no se recomienda su baja automática."
            if caso == "FINANCIERA_TRIBUTARIA":
                x.tributario = "POSIBLE_DIFERENCIA_TEMPORAL"
                x.recomendacion = "La depreciación financiera se basa en la vida útil (NIC 16); la tributaria puede generar diferencias temporales."
        s.metodo = "Conciliación de activos fijos de la fase 6 (registro de la fase 5 vs 33/34/39/68) ejecutada en memoria."
        return s
    out = []
    if caso == "SIN_FECHA_USO":
        for a in regs:
            if not a.get("fecha_uso"):
                out.append(Res(titulo=f"Activo {a['_clave']} sin fecha disponible para su uso", condicion="El registro no indica la fecha de inicio de uso: no "
                               "puede verificarse el inicio de la depreciación.", importe=dec(a.get("costo_inicial")), cuenta=a.get("_cuenta"),
                               documento=str(a["_clave"]), evidencia=[ev_reg("annex_support_records", a["_id"], f"Activo {a['_clave']}")],
                               clave=f"ACT|SFU|{a['_clave']}", exposicion=f"ACTIVO|{a['_clave']}", calidad="PARCIAL", regularizacion="REQUIERE_DOCUMENTACION"))
    elif caso == "SIN_DEPRECIACION":
        con_dep = {(ln.maquinaria or "").upper() for ln in ax.lineas if ln.cuenta.startswith(("68", "39")) and ln.maquinaria}
        for a in regs:
            uso = _f(a.get("fecha_uso"))
            if uso and uso <= ax.corte and a.get("vida_util_meses") and str(a["_clave"]).upper() not in con_dep and con_dep:
                out.append(Res(titulo=f"Activo {a['_clave']} sin depreciación registrada en el periodo", condicion=f"En uso desde {uso:%d/%m/%Y} con vida útil de "
                               f"{a.get('vida_util_meses')} meses y sin líneas de depreciación con su código.", importe=dec(a.get("costo_inicial")),
                               cuenta=a.get("_cuenta"), documento=str(a["_clave"]), evidencia=[ev_reg("annex_support_records", a["_id"], f"Activo {a['_clave']}")],
                               clave=f"ACT|SDP|{a['_clave']}", exposicion=f"ACTIVO|{a['_clave']}", calidad="PARCIAL"))
    elif caso == "SIN_CODIGO":
        if regs:
            for ln in ax.lineas:
                if ln.cuenta.startswith(("32", "33", "34")) and ln.debe and not ln.maquinaria:
                    out.append(Res(titulo=f"Adquisición de activo sin código en la cuenta {ln.cuenta}", condicion=f"Línea {ln.id} por {ln.debe} sin código de "
                                   "activo: no puede vincularse con el registro auxiliar.", importe=ln.debe, cuenta=ln.cuenta, linea_id=ln.id,
                                   asiento=asiento_de(ln), evidencia=[ev_linea(ln)], clave=f"ACT|SC|{ln.id}", exposicion=f"LINEA|{ln.id}",
                                   regularizacion="REQUIERE_DOCUMENTACION"))
    return Salida(out, len(regs), metodo=f"Activos fijos — {caso.lower().replace('_', ' ')}: registro de la fase 5 y libro.")


# ===================================================================== INVENTARIOS
def inventarios(ax, r) -> Salida:
    caso = r.p["caso"]
    regs = ax.registros("INVENTARIO")
    guardadas = {"NEGATIVAS": {"EXISTENCIA_NEGATIVA"}, "VALORIZACION": {"DIFERENCIA_VALORIZACION", "INCONSISTENCIA_VALORES", "INCONSISTENCIA_COSTO"},
                 "DUPLICADOS": {"MOVIMIENTO_DUPLICADO"}, "KARDEX_BALANCE": {"DIFERENCIA_VALORIZACION", "MOVIMIENTO_NO_CONTABILIZADO"}}.get(caso)
    out = []
    if guardadas:
        r.p["tipo"], r.p["subtipos"] = "INVENTARIOS", sorted(guardadas)
        s = conciliacion_memoria(ax, r)
        if s.estado != "SIN_DATOS":
            out += s.res
    if not regs and not out:
        return Salida(estado="SIN_DATOS", mensaje="No hay inventario valorizado (fase 5) ni conciliación de kardex (fase 6).")
    cu = defaultdict(list)
    for x in regs:
        q, v = dec(x.get("cantidad")), dec(x.get("valor"))
        ev = [ev_reg("annex_support_records", x["_id"], f"{x['_clave']} {x.get('descripcion') or ''}", cantidad=q, valor=v, almacen=x.get("almacen"))]
        if caso == "NEGATIVAS" and (q < 0 or v < 0):
            out.append(Res(titulo=f"Existencia negativa: {x['_clave']}", condicion=f"Cantidad {q}, valor {v} en el almacén {x.get('almacen') or '—'}.",
                           importe=abs(v), cuenta=x.get("_cuenta"), documento=str(x["_clave"]), evidencia=ev, clave=f"INV|NEG|{x['_clave']}",
                           exposicion=f"ITEM|{x['_clave']}", estructural=True))
        elif caso == "VALORIZACION" and x.get("costo_unitario") not in (None, "") and q and abs(q * dec(x["costo_unitario"]) - v) > dec(r.p.get("tolerancia", "1")):
            out.append(Res(titulo=f"Diferencia de valorización: {x['_clave']}", condicion=f"{q} × {x['costo_unitario']} = "
                           f"{(q * dec(x['costo_unitario'])).quantize(Decimal('0.01'))} y valor registrado {v}.", importe=abs(q * dec(x["costo_unitario"]) - v),
                           cuenta=x.get("_cuenta"), documento=str(x["_clave"]), evidencia=ev, clave=f"INV|VAL|{x['_clave']}", exposicion=f"ITEM|{x['_clave']}"))
        elif caso == "SIN_MOVIMIENTO" and x.get("fecha_ultimo_movimiento") and (ax.corte - _f(x["fecha_ultimo_movimiento"])).days > int(r.p.get("dias", 365)) and v:
            out.append(Res(titulo=f"Inventario sin movimiento: posible obsolescencia de {x['_clave']}", condicion=f"Sin movimiento desde "
                           f"{_f(x['fecha_ultimo_movimiento']):%d/%m/%Y} con valor {v}.", importe=v, cuenta=x.get("_cuenta"), documento=str(x["_clave"]),
                           evidencia=ev, clave=f"INV|OBS|{x['_clave']}", exposicion=f"ITEM|{x['_clave']}", calidad="PARCIAL",
                           recomendacion="Evalúe el valor neto realizable con evidencia (NIC 2); no se determinan desvalorizaciones automáticamente."))
        elif caso == "FUERA_PERIODO" and x.get("_fecha") and x["_fecha"] != ax.corte:
            out.append(Res(titulo=f"Inventario valorizado a una fecha distinta del corte: {x['_clave']}", condicion=f"Inventario al {x['_fecha']:%d/%m/%Y}; "
                           f"corte {ax.corte:%d/%m/%Y}.", importe=v, cuenta=x.get("_cuenta"), documento=str(x["_clave"]), evidencia=ev,
                           clave=f"INV|FP|{x['_clave']}", exposicion=f"ITEM|{x['_clave']}", calidad="PARCIAL"))
        if q > 0:
            cu[str(x["_clave"])].append((v / q, x))
    if caso == "KARDEX_BALANCE" and regs:
        por = defaultdict(lambda: CERO)
        for x in regs:
            por[x.get("_cuenta") or "20"] += dec(x.get("valor"))
        for c, v in por.items():
            sf = dec(ax.ctx3.nodos[c].sf) / 100 if c in ax.ctx3.nodos else CERO
            if abs(sf - v) > dec(r.p.get("tolerancia", "1")):
                out.append(Res(titulo=f"Inventario valorizado y balance difieren en la cuenta {c}", condicion=f"Inventario {v}; saldo contable {sf}.",
                               importe=abs(sf - v), cuenta=c, clave=f"INV|KB|{c}", exposicion=f"CUENTA|{c}",
                               evidencia=[ev_calc("Inventario vs balance", inventario=v, balance=sf)]))
    if caso in ("COSTO_ATIPICO", "ALMACENES"):
        pct = Decimal(str(r.p.get("porcentaje", 20)))
        for cod, xs in cu.items():
            if caso == "ALMACENES" and len(xs) > 1:
                mn, mx = min(c for c, _ in xs), max(c for c, _ in xs)
                if mn and (mx - mn) * 100 / mn > pct:
                    out.append(Res(titulo=f"Costo unitario distinto entre almacenes: {cod}", condicion=f"Costos unitarios entre {mn.quantize(Decimal('0.01'))} y "
                                   f"{mx.quantize(Decimal('0.01'))} según el almacén.", importe=CERO, cuenta=xs[0][1].get("_cuenta"), documento=cod,
                                   evidencia=[ev_reg("annex_support_records", x["_id"], f"{x.get('almacen')}: {c.quantize(Decimal('0.0001'))}") for c, x in xs],
                                   clave=f"INV|ALM|{cod}", exposicion=f"ITEM|{cod}", calidad="PARCIAL"))
        if caso == "COSTO_ATIPICO":
            costos = [c for xs in cu.values() for c, _ in xs]
            if len(costos) >= 8:
                q1, _, q3 = statistics.quantiles([float(c) for c in costos], n=4)
                lim = Decimal(str(q3 + 3 * (q3 - q1)))
                for cod, xs in cu.items():
                    for c, x in xs:
                        if c > lim:
                            out.append(Res(titulo=f"Costo unitario atípico: {cod}", condicion=f"Costo unitario {c.quantize(Decimal('0.01'))} supera el límite "
                                           f"Q3 + 3·IQR ({lim.quantize(Decimal('0.01'))}).", importe=CERO, documento=cod, cuenta=x.get("_cuenta"),
                                           evidencia=[ev_reg("annex_support_records", x["_id"], cod)], clave=f"INV|CA|{cod}|{x.get('almacen')}",
                                           exposicion=f"ITEM|{cod}", calidad="PARCIAL"))
    return Salida(out, len(regs), metodo=f"Inventarios — {caso.lower().replace('_', ' ')}: inventario valorizado (fase 5) y conciliación de kardex (fase 6).")


# ===================================================================== PLANILLAS
def planilla_libro(ax, r) -> Salida:
    """Saldos por trabajador de cuentas de remuneraciones y retenciones con antigüedad (datos personales protegidos)."""
    pref = tuple(r.cuentas) or ("41",)
    dias = int(r.p.get("dias", 90))
    pal = [normalizar_texto(x) for x in r.p.get("palabras", [])]
    saldo = defaultdict(lambda: [CERO, None, None, []])
    for ln in ax.ctx3.lineas_hasta_corte:
        if not ln.cuenta.startswith(pref):
            continue
        if pal and not any(p in normalizar_texto(ln.glosa or "") for p in pal):
            continue
        s = saldo[(ln.cuenta, ln.tercero)]
        s[0] += ln.haber - ln.debe
        s[1] = ln.razon_social or s[1]
        if ln.haber and ln.fecha:
            s[2] = min(s[2] or ln.fecha, ln.fecha)
        s[3].append(ln)
    out = []
    for (c, t), (v, rs, desde, ls) in saldo.items():
        if v > dec(r.p.get("importe_minimo", "0.01")) and desde and (ax.corte - desde).days > dias:
            out.append(Res(titulo=r.p.get("titulo", "Saldo antiguo por trabajador") + f" ({c})", condicion=f"Saldo {v} pendiente desde el {desde:%d/%m/%Y} "
                           f"({(ax.corte - desde).days} días).", importe=v, cuenta=c, tercero=t, razon_social=rs, personal=True,
                           evidencia=[ev_linea(x) for x in ls[-10:] if x.id], clave=f"{r.codigo}|{c}|{t}", exposicion=f"TRAB|{c}|{t}",
                           tributario=r.p.get("tributario"), calidad="PARCIAL",
                           causa="Requiere evaluación: no se determinan infracciones laborales ni prescripción de obligaciones."))
    return Salida(out, len(saldo), metodo=f"Saldos acreedores por trabajador de {', '.join(pref)}{' con glosa ' + '/'.join(pal) if pal else ''} "
                                          f"con más de {dias} días.")


def pagos_planilla(ax, r) -> Salida:
    g = defaultdict(list)
    for k, ls in ax.asientos.items():
        if any(x.cuenta.startswith("10") and x.haber for x in ls):
            for x in ls:
                if x.cuenta.startswith("41") and x.debe and x.tercero:
                    g[(x.tercero, x.periodo, x.cuenta, x.debe)].append((k, x))
    out = []
    for (t, p, c, imp), xs in g.items():
        if len({k for k, _ in xs}) > 1:
            out.append(Res(titulo=f"Pago de planilla posiblemente duplicado ({c})", condicion=f"{len(xs)} pagos de {imp} al mismo trabajador en el periodo {p:02d}.",
                           importe=imp * (len(xs) - 1), cuenta=c, tercero=t, razon_social=xs[0][1].razon_social, personal=True,
                           evidencia=[ev_linea(x) for _, x in xs], clave=f"PLA|DUP|{t}|{p}|{c}|{imp}", exposicion=f"TRAB|{c}|{t}|{p}", probabilidad=4))
    return Salida(out, len(g), metodo="Pagos (con salida de caja/bancos) al mismo trabajador, periodo, cuenta e importe en asientos distintos.")


EVALUADORES = {"destino": destino, "porcentajes": porcentajes, "clase9_en_resultados": clase9_en_resultados,
               "distribucion_aprobada": distribucion_aprobada, "naturaleza": naturaleza, "rubros": rubros, "politicas": politicas,
               "cambios_sin_sustento": cambios_sin_sustento, "servicios": servicios, "activos": activos, "inventarios": inventarios,
               "planilla_libro": planilla_libro, "pagos_planilla": pagos_planilla}
