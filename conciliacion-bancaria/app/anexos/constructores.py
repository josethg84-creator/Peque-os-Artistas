"""Constructores de anexos por especialidad.

Cada constructor recibe el contexto de datos, la cuenta (prefijo) y la plantilla, y devuelve las filas del
detalle, las observaciones propias y tablas adicionales. Las filas expresan el saldo con el SIGNO NATURAL de
la cuenta (positivo cuando el saldo está en su lado normal: deudor para activos y gastos, acreedor para
pasivos, patrimonio e ingresos). Ningún constructor inventa documentos: lo que no tiene detalle queda como
«saldo sin detalle» y lo que no tiene comprobante, como «pendiente de sustento».
"""
import re
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.analisis import antiguedad as ant3
from app.anexos.datos import CERO, C2, Ctx, L, dec

TRAMO_SIN_VENC = "Sin fecha de vencimiento determinada"
TRAMO_NO_VENCIDO = "No vencido"
MESES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]


class Resultado:
    def __init__(self):
        self.filas: list[dict] = []
        self.hallazgos: list[dict] = []
        self.extras: dict = {}

    def hallazgo(self, codigo, severidad, titulo, detalle=None, importe=None, clave_fila=None):
        self.hallazgos.append({"codigo": codigo, "severidad": severidad, "titulo": titulo[:300], "detalle": detalle,
                               "importe": importe, "clave_fila": clave_fila})


def fila(**kw) -> dict:
    base = {"clave": None, "cuenta": None, "categoria": None, "fecha": None, "fecha_vencimiento": None, "tipo_documento": None,
            "serie": None, "numero": None, "tercero": None, "razon_social": None, "glosa": None, "moneda": "PEN",
            "tipo_cambio": None, "importe_original": None, "importe_aplicado": None, "saldo_me": None, "saldo": CERO,
            "dias": None, "tramo": None, "centro_costo": None, "proyecto": None, "referencia": None, "linea_id": None,
            "item_id": None, "estado_sustento": "DOCUMENTADO", "observacion": None, "datos": {}}
    base.update(kw)
    base["documento"] = (f"{base['serie']}-{base['numero']}" if base["serie"] else base["numero"]) if base["numero"] else None
    return base


def signo(ctx: Ctx, cuenta: str) -> int:
    return 1 if ctx.naturaleza(cuenta) == "D" else -1


def tramo_de(dias: int | None, rangos, vencimiento=False) -> str:
    if dias is None:
        return TRAMO_SIN_VENC
    if dias <= 0:
        return TRAMO_NO_VENCIDO if vencimiento else "0 días"
    nombres = ant3.etiquetas(rangos)
    return nombres[ant3.tramo(dias, rangos)]


def _d(v) -> Decimal | None:
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v).replace(",", "")).quantize(C2)
    except Exception:
        return None


def _f(v) -> date | None:
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _sustento(ctx: Ctx, r: dict, cuenta: str) -> dict:
    """Ajusta el estado de sustento con los adjuntos existentes (por fila, documento, partida o cuenta)."""
    if r["estado_sustento"] == "SIN_DOCUMENTO":
        if ctx.tiene_adjunto(r):
            r["estado_sustento"], r["observacion"] = "DOCUMENTADO", (r["observacion"] or "Sustentado con documento adjunto")
        elif ctx.adjunto_de_cuenta(r["cuenta"] or cuenta):
            r["estado_sustento"] = "DOCUMENTADO"
            r["observacion"] = r["observacion"] or "Sustentado con documentación adjunta a la cuenta"
    return r


# ------------------------------------------------------------------ genérico (por tercero y documento)
def generico(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado, *, agrupar_sin_doc="asiento", categoria=None,
             lineas: list[L] | None = None, sin_apertura=False) -> None:
    rangos = plantilla.get("rangos_antiguedad")
    # saldos iniciales importados (sin documento: no se inventa el detalle)
    if not sin_apertura:
        for (c, t), v in sorted(ctx.apertura_ter.items(), key=lambda x: (x[0][0], x[0][1] or "")):
            if c.startswith(cuenta) and v:
                sg = signo(ctx, c)
                res.filas.append(fila(clave=f"{c}|{t or ''}|SI", cuenta=c, categoria="Saldo inicial", tercero=t,
                                      fecha=date(ctx.ejercicio, 1, 1), saldo=dec(v * sg), estado_sustento="SIN_DETALLE",
                                      observacion="Saldo inicial importado sin detalle por documento"))
    grupos: dict[tuple, list[L]] = defaultdict(list)
    for ln in (lineas if lineas is not None else ctx.de(cuenta)):
        if ln.numero:
            k = ("D", ln.cuenta, ln.tercero or "", ln.tipo_doc or "", ln.serie or "", ln.numero)
        elif agrupar_sin_doc == "tercero":
            k = ("T", ln.cuenta, ln.tercero or "", "", "", "")
        else:
            k = ("A", ln.cuenta, ln.tercero or "", str(ln.lote_id), str(ln.periodo), ln.etiqueta_asiento or f"L{ln.id}")
        grupos[k].append(ln)
    for k, ls in grupos.items():
        neto = sum(x.neto for x in ls)
        neto_me = sum(x.neto_me for x in ls)
        if neto == 0 and neto_me == 0:
            continue
        c = k[1]
        sg = signo(ctx, c)
        p = ls[0]
        fechas = [x.fecha for x in ls if x.fecha]
        f0 = min(fechas) if fechas else None
        venc = next((x.vencimiento for x in ls if x.vencimiento), None)
        dias = (ctx.corte - (venc or f0)).days if (venc or f0) else None
        me = p.moneda if p.moneda != "PEN" else None
        r = fila(clave="|".join(k), cuenta=c, categoria=categoria, fecha=f0, fecha_vencimiento=venc,
                 tipo_documento=p.tipo_doc, serie=p.serie if k[0] == "D" else None, numero=p.numero if k[0] == "D" else None,
                 tercero=p.tercero, razon_social=next((x.razon_social for x in ls if x.razon_social), None),
                 glosa=p.glosa, moneda=p.moneda, tipo_cambio=p.tipo_cambio,
                 saldo_me=dec(neto_me * sg) if me else None, saldo=dec(neto * sg), dias=dias,
                 tramo=tramo_de(dias, rangos, vencimiento=bool(venc)), centro_costo=p.cc, proyecto=p.proyecto,
                 referencia=p.etiqueta_asiento, linea_id=p.id,
                 estado_sustento="DOCUMENTADO" if k[0] == "D" else "SIN_DOCUMENTO",
                 observacion=None if k[0] == "D" else "Movimiento sin comprobante identificado")
        res.filas.append(_sustento(ctx, r, cuenta))
    nota = (plantilla.get("parametros") or {}).get("nota")
    if nota:
        res.hallazgo("NOTA_PLANTILLA", "INFORMATIVA", nota)


# ------------------------------------------------------------------ cuenta 10
def efectivo(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    from sqlalchemy import func, select
    from app.models import Banco, CuentaBancaria, Importacion, MovimientoBanco
    db = ctx.db
    bancos = {cb.cuenta_contable: (cb, b) for cb, b in db.execute(
        select(CuentaBancaria, Banco).join(Banco, Banco.id == CuentaBancaria.banco_id)
        .where(CuentaBancaria.empresa_id == ctx.empresa_id))}
    tipos = {"101": "Caja", "102": "Fondo fijo", "103": "Efectivo en tránsito", "104": "Cuenta corriente", "105": "Otro equivalente",
             "106": "Depósito / ahorro", "107": "Fondo sujeto a restricción"}
    hojas = sorted({c for c in ctx.hojas() if c.startswith(cuenta)})
    for c in hojas:
        s = ctx.saldos_de(c)
        if not (s["sf"] or s["n"] or s["si"]):
            continue
        sg = signo(ctx, c)
        tipo = next((v for k, v in tipos.items() if c.startswith(k)), "Efectivo")
        datos = {"entidad": None, "numero_cuenta": None, "saldo_banco": None, "fecha_estado": None, "diferencia_banco": None,
                 "pendientes_banco": None, "estado_banco": "No aplica (efectivo en caja: requiere arqueo)" if c.startswith(("101", "102")) else
                 "Sin cuenta bancaria registrada"}
        moneda = "PEN"
        estado, obs = "SIN_DOCUMENTO", None
        if c in bancos:
            cb, b = bancos[c]
            moneda = cb.moneda
            num = re.sub(r"\s", "", cb.numero_cuenta)
            datos.update(entidad=b.nombre, numero_cuenta=("•" * max(len(num) - 4, 0)) + num[-4:])
            ult = db.execute(select(MovimientoBanco.fecha, MovimientoBanco.saldo).join(Importacion, Importacion.id == MovimientoBanco.importacion_id)
                             .where(MovimientoBanco.cuenta_bancaria_id == cb.id, Importacion.estado == "ACTIVA",
                                    MovimientoBanco.fecha <= ctx.corte, MovimientoBanco.saldo.is_not(None),
                                    MovimientoBanco.posible_duplicado.is_(False))
                             .order_by(MovimientoBanco.fecha.desc(), MovimientoBanco.id.desc()).limit(1)).first()
            cubre = db.scalar(select(func.max(Importacion.fecha_hasta)).where(Importacion.cuenta_bancaria_id == cb.id,
                                                                              Importacion.tipo == "BANCO", Importacion.estado == "ACTIVA"))
            pend = db.scalar(select(func.count()).select_from(MovimientoBanco).join(Importacion, Importacion.id == MovimientoBanco.importacion_id)
                             .where(MovimientoBanco.cuenta_bancaria_id == cb.id, Importacion.estado == "ACTIVA",
                                    MovimientoBanco.fecha <= ctx.corte, MovimientoBanco.estado_conciliacion == "PENDIENTE"))
            datos["pendientes_banco"] = pend
            if ult and cubre and cubre >= ctx.corte:
                saldo_libro = dec(s["sf_me"]) if moneda != "PEN" else dec(s["sf"])
                datos.update(saldo_banco=ult[1], fecha_estado=ult[0], diferencia_banco=(saldo_libro - ult[1]).quantize(C2),
                             estado_banco="Saldos coinciden (conciliación bancaria formal pendiente)" if saldo_libro == ult[1]
                             else "Con diferencia: requiere conciliación bancaria")
                estado = "DOCUMENTADO"
                obs = "Respaldado por el estado de cuenta importado"
                if saldo_libro != ult[1]:
                    res.hallazgo("DIFERENCIA_BANCO", "MEDIA", f"La cuenta {c} difiere del estado bancario en {datos['diferencia_banco']}",
                                 "La diferencia no implica error: puede deberse a partidas en tránsito. No se declara conciliada.",
                                 datos["diferencia_banco"], f"{c}|BANCO")
            else:
                datos["estado_banco"] = "Información bancaria insuficiente al corte"
                res.hallazgo("BANCO_SIN_ESTADO", "MEDIA", f"La cuenta {c} no tiene estado bancario que cubra la fecha de corte",
                             "Sin información bancaria suficiente la cuenta no se declara conciliada.", None, f"{c}|BANCO")
        r = fila(clave=f"{c}|BANCO", cuenta=c, categoria=tipo, moneda=moneda, saldo=dec(s["sf"] * sg),
                 saldo_me=dec(s["sf_me"] * sg) if moneda != "PEN" else None, estado_sustento=estado, observacion=obs, datos=datos)
        res.filas.append(_sustento(ctx, r, cuenta))


# ------------------------------------------------------------------ cartera (fase 4)
NOMBRE_CLASE = {"FACTURA": "Factura", "BOLETA": "Boleta", "RECIBO_HONORARIOS": "Recibo por honorarios", "NOTA_CREDITO": "Nota de crédito",
                "NOTA_DEBITO": "Nota de débito", "PAGO": "Pago por aplicar", "COBRANZA": "Cobranza por aplicar", "ANTICIPO": "Anticipo",
                "ENTREGA_RENDIR": "Entrega a rendir", "RENDICION": "Rendición", "PRESTAMO": "Préstamo", "AMORTIZACION": "Amortización",
                "DETRACCION": "Detracción", "RETENCION": "Retención", "PERCEPCION": "Percepción", "DIFERENCIA_CAMBIO": "Diferencia de cambio",
                "RECLASIFICACION": "Reclasificación", "EXTORNO": "Extorno", "SALDO_INICIAL": "Saldo inicial", "OTRO": "Otro"}


def _filas_composicion(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado, extra) -> bool:
    comp = ctx.composicion(cuenta)
    if comp is None:
        return False
    rangos = plantilla.get("rangos_antiguedad")
    vivos = [e for e in comp if e.pendiente != 0 or e.pendiente_mn != 0]
    aplic = ctx.aplicado_por_clase([e.item["id"] for e in vivos])
    for e in vivos:
        it = e.item
        c = it["cuenta"]
        sg = signo(ctx, c)
        firmado = e.pendiente_mn if it["lado"] == "D" else -e.pendiente_mn
        firmado_me = e.pendiente if it["lado"] == "D" else -e.pendiente
        if it["origen_datos"] == "APERTURA_CONSOLIDADA":
            estado, obs = "SIN_DETALLE", "Saldo inicial sin detalle por documento (pendiente de desagregación)"
        elif it["clasificacion_pendiente"]:
            estado, obs = "POR_CLASIFICAR", f"Clasificación por revisar: {it['clase_motivo'] or ''}"[:500]
        elif it["numero"]:
            estado, obs = "DOCUMENTADO", None
        else:
            estado, obs = "SIN_DOCUMENTO", "Partida sin comprobante identificado"
        if it["rol"] == "APLICACION":
            obs = (obs + " · " if obs else "") + "Saldo a favor / cancelación pendiente de aplicar"
        dias = e.dias
        por_clase = aplic.get(it["id"], {})
        r = fila(clave=f"P{it['id']}", cuenta=c, categoria=NOMBRE_CLASE.get(it["clase"], it["clase"]), fecha=it["fecha_documento"],
                 fecha_vencimiento=it["fecha_vencimiento"], tipo_documento=it["tipo_documento"], serie=it["serie"], numero=it["numero"],
                 tercero=it["tercero"], razon_social=it["razon_social"], glosa=it["glosa"], moneda=it["moneda"],
                 tipo_cambio=it["tipo_cambio"], importe_original=it["importe"], importe_aplicado=e.aplicado,
                 saldo_me=(firmado_me * sg).quantize(C2) if it["moneda"] != "PEN" else None, saldo=(firmado * sg).quantize(C2),
                 dias=dias if it["rol"] == "ORIGEN" else None,
                 tramo=(tramo_de(dias, rangos, vencimiento=True) if it["fecha_vencimiento"] else TRAMO_SIN_VENC)
                 if it["rol"] == "ORIGEN" else "Saldo a favor / por aplicar",
                 centro_costo=it["centro_costo"], proyecto=it["proyecto"],
                 referencia="-".join(x for x in (it["subdiario"], it["numero_asiento"]) if x) or None,
                 linea_id=it["linea_id"], item_id=it["id"], estado_sustento=estado, observacion=obs,
                 datos={"clase": it["clase"], "rol": it["rol"], **extra(it, por_clase)})
        res.filas.append(_sustento(ctx, r, cuenta))
    _diferencias_cambio(ctx, cuenta, res)
    return True


def _diferencias_cambio(ctx: Ctx, cuenta: str, res: Resultado) -> None:
    """Diferencias de cambio identificadas en aplicaciones aprobadas (fase 4): explican parte del saldo
    contable mientras no se regularicen. Se muestran como partidas por clasificar; no se genera asiento."""
    from sqlalchemy import select
    from app.models import Aplicacion, PartidaAbierta
    q = (select(Aplicacion.id, Aplicacion.diferencia_cambio, Aplicacion.fecha_efectiva, PartidaAbierta.cuenta, PartidaAbierta.lado,
                PartidaAbierta.tercero, PartidaAbierta.razon_social, PartidaAbierta.serie, PartidaAbierta.numero, PartidaAbierta.id,
                PartidaAbierta.linea_id)
         .join(PartidaAbierta, PartidaAbierta.id == Aplicacion.origen_item_id)
         .where(Aplicacion.empresa_id == ctx.empresa_id, Aplicacion.estado == "APROBADA", Aplicacion.fecha_efectiva <= ctx.corte,
                Aplicacion.diferencia_cambio != 0, PartidaAbierta.cuenta.like(f"{cuenta}%")))
    for aid, dif, fe, c, lado, ter, rs, serie, num, item, linea in ctx.db.execute(q):
        # dif = MN de la cancelación − MN del documento: en una cuenta acreedora el exceso queda como saldo deudor
        firmado = dif if lado == "H" else -dif
        doc = f"{serie}-{num}" if serie else num
        res.filas.append(fila(clave=f"DC{aid}", cuenta=c, categoria="Diferencia de cambio", fecha=fe, tercero=ter, razon_social=rs,
                              glosa=f"Diferencia de cambio en la aplicación de {doc}", saldo=(firmado * signo(ctx, c)).quantize(C2),
                              item_id=item, linea_id=linea, estado_sustento="POR_CLASIFICAR",
                              observacion="Diferencia de cambio identificada, pendiente de regularización (no se generan asientos)",
                              datos={"clase": "DIFERENCIA_CAMBIO", "rol": "AJUSTE"}))


def _q(v) -> Decimal:
    return Decimal(v).quantize(C2)


def cartera(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    def extra(it, pc):
        cp = pc.get("COBRANZA", CERO) + pc.get("PAGO", CERO)
        otros = sum((v for k, v in pc.items() if k not in ("COBRANZA", "PAGO", "NOTA_CREDITO", "ANTICIPO", "DETRACCION",
                                                           "RETENCION", "PERCEPCION")), CERO)
        return {"cobros_pagos": _q(cp), "notas_credito": _q(pc.get("NOTA_CREDITO", CERO)), "anticipos": _q(pc.get("ANTICIPO", CERO)),
                "detracciones": _q(pc.get("DETRACCION", CERO)),
                "retenciones": _q(pc.get("RETENCION", CERO) + pc.get("PERCEPCION", CERO)), "otros_aplicados": _q(otros)}
    if not _filas_composicion(ctx, cuenta, plantilla, res, extra):
        res.hallazgo("SIN_COMPENSACION", "INFORMATIVA", "La cuenta no está configurada como compensable: el detalle se arma "
                     "desde el libro por tercero y documento, sin aplicar cobros/pagos.")
        generico(ctx, cuenta, plantilla, res)
        return
    vencidas = [r for r in res.filas if r["dias"] and r["dias"] > 365 and r["saldo"] > 0]
    if vencidas:
        res.hallazgo("SALDO_ANTIGUO", "MEDIA", f"{len(vencidas)} documentos con más de 365 días de vencidos",
                     "Evalúe su recuperabilidad o exigibilidad; la antigüedad por sí sola no determina un deterioro.",
                     sum((r["saldo"] for r in vencidas), CERO))


SUBTIPOS_14 = [("1411", "Préstamo al personal"), ("1412", "Adelanto de remuneraciones"), ("1413", "Entrega a rendir"),
               ("1419", "Otras cuentas por cobrar al personal"), ("1421", "Suscripción de acciones"), ("1422", "Préstamo a accionistas"),
               ("1431", "Préstamo a directores"), ("1432", "Adelanto de dietas"), ("1433", "Entrega a rendir (directores)"),
               ("144", "Cuentas por cobrar a gerentes"), ("141", "Personal"), ("142", "Accionistas"), ("143", "Directores"),
               ("148", "Otras cuentas por cobrar"), ("14", "Otras cuentas por cobrar")]


def personal(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    def extra(it, pc):
        # en la fase 4 la contrapartida de una entrega (rendición con comprobantes) puede clasificarse como RENDICION o
        # como ANTICIPO de la misma subcuenta; los cobros en caja son devoluciones y el resto, descuentos u otros
        rend = pc.get("RENDICION", CERO) + pc.get("ANTICIPO", CERO)
        dev = pc.get("COBRANZA", CERO) + pc.get("PAGO", CERO)
        return {"entregado": it["importe"] if it["rol"] == "ORIGEN" else None, "rendiciones": _q(rend), "devoluciones": _q(dev),
                "descuentos": _q(sum((v for k, v in pc.items() if k not in ("RENDICION", "ANTICIPO", "COBRANZA", "PAGO")), CERO))}
    if not _filas_composicion(ctx, cuenta, plantilla, res, extra):
        generico(ctx, cuenta, plantilla, res)
    for r in res.filas:
        r["categoria"] = next((n for k, n in SUBTIPOS_14 if (r["cuenta"] or "").startswith(k)), r["categoria"])
    viejas = [r for r in res.filas if r["categoria"] and "rendir" in r["categoria"] and r["fecha"]
              and (ctx.corte - r["fecha"]).days > 30 and r["saldo"] > 0]
    if viejas:
        res.hallazgo("RENDICION_PENDIENTE", "MEDIA", f"{len(viejas)} entregas a rendir con más de 30 días sin rendir",
                     None, sum((r["saldo"] for r in viejas), CERO))


def estimacion(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    generico(ctx, cuenta, plantilla, res, agrupar_sin_doc="tercero")
    prefijos = (plantilla.get("parametros") or {}).get("cartera", ["12", "13", "16", "17"])
    cartera_ter = defaultdict(lambda: [CERO, CERO, CERO])
    total = [CERO, CERO, CERO]
    for p in prefijos:
        comp = ctx.composicion(p) or []
        for e in comp:
            if e.item["rol"] != "ORIGEN" or e.pendiente_mn <= 0:
                continue
            t = e.item["tercero"] or ""
            v = e.pendiente_mn
            x = cartera_ter[t]
            x[0] += v
            if e.dias and e.dias > 0:
                x[1] += v
            if e.dias and e.dias > 365:
                x[2] += v
            for i, add in enumerate((v, v if e.dias and e.dias > 0 else CERO, v if e.dias and e.dias > 365 else CERO)):
                total[i] += add
    for r in res.filas:
        t = r["tercero"] or ""
        tot, venc, v365 = cartera_ter.get(t, [CERO, CERO, CERO])
        r["datos"].update(cartera_total=tot.quantize(C2), cartera_vencida=venc.quantize(C2), vencida_365=v365.quantize(C2),
                          cobertura=(r["saldo"] / venc * 100).quantize(C2) if venc else None)
    res.extras["cartera"] = {"total": str(total[0].quantize(C2)), "vencida": str(total[1].quantize(C2)),
                             "vencida_365": str(total[2].quantize(C2))}
    res.hallazgo("JUICIO_DETERIORO", "INFORMATIVA", "La estimación de cobranza dudosa requiere evaluación profesional (NIIF 9): "
                 "el sistema relaciona la cartera y su antigüedad, pero no determina deterioros automáticamente.")


# ------------------------------------------------------------------ cuenta 18
def diferido(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    regs = [r for r in ctx.registros("GASTO_ANTICIPADO") if (r["_cuenta"] or "").startswith(cuenta) or cuenta.startswith(r["_cuenta"] or "~")]
    if not regs:
        res.hallazgo("SIN_REGISTRO_AUXILIAR", "MEDIA", "No hay cronograma de devengo importado para la cuenta: el detalle se arma "
                     "desde el libro y no se calcula el devengo.")
        generico(ctx, cuenta, plantilla, res)
        return
    for r in regs:
        imp = _d(r.get("importe")) or CERO
        ini, fin = _f(r.get("fecha_inicio")), _f(r.get("fecha_fin"))
        fdoc = _f(r.get("fecha_documento"))
        if fdoc and fdoc > ctx.corte:
            continue
        if not ini or not fin or fin < ini:
            res.hallazgo("CRONOGRAMA_INCOMPLETO", "MEDIA", f"Contrato {r['_clave']}: fechas de inicio y término no válidas",
                         clave_fila=f"GA|{r['_clave']}")
            devengado = None
        else:
            total_dias = (fin - ini).days + 1
            transcurridos = min(max((ctx.corte - ini).days + 1, 0), total_dias)
            devengado = (imp * transcurridos / total_dias).quantize(C2, ROUND_HALF_UP)
        pendiente = imp - (devengado or CERO)
        res.filas.append(fila(clave=f"GA|{r['_clave']}", cuenta=r["_cuenta"] or cuenta, categoria=r.get("tipo"), glosa=r.get("concepto"),
                              razon_social=r.get("proveedor"), tercero=r.get("ruc"), serie=r.get("serie"), numero=r.get("numero"),
                              fecha=ini, saldo=pendiente.quantize(C2), estado_sustento="DOCUMENTADO",
                              observacion="Devengo lineal por días según cronograma importado",
                              datos={"tipo": r.get("tipo"), "fecha_inicio": ini, "fecha_fin": fin, "contratado": imp,
                                     "devengado": devengado, "pendiente": pendiente.quantize(C2)}))


# ------------------------------------------------------------------ existencias
def existencias(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    regs = [r for r in ctx.registros("INVENTARIO") if (r["_cuenta"] or "").startswith(cuenta) and r["_fecha"] and r["_fecha"] <= ctx.corte]
    if not regs:
        res.hallazgo("SIN_INVENTARIO", "MEDIA", "No hay inventario valorizado importado al corte: el detalle se arma desde el libro.")
        generico(ctx, cuenta, plantilla, res, agrupar_sin_doc="asiento")
        return
    ultima = max(r["_fecha"] for r in regs)
    if ultima != ctx.corte:
        res.hallazgo("INVENTARIO_OTRA_FECHA", "MEDIA", f"El inventario más reciente es del {ultima:%d/%m/%Y}, no de la fecha de corte")
    for r in regs:
        if r["_fecha"] != ultima:
            continue
        cant = _d(r.get("cantidad"))
        cu = Decimal(str(r.get("costo_unitario") or 0)) if r.get("costo_unitario") not in (None, "") else None
        valor = _d(r.get("valor")) if r.get("valor") not in (None, "") else ((cant or CERO) * (cu or CERO)).quantize(C2, ROUND_HALF_UP)
        res.filas.append(fila(clave=f"INV|{r['_cuenta']}|{r.get('codigo')}|{r.get('almacen') or ''}", cuenta=r["_cuenta"],
                              categoria=ctx.descripcion(r["_cuenta"]), glosa=r.get("descripcion"), saldo=valor,
                              estado_sustento="DOCUMENTADO", observacion=f"Inventario valorizado al {ultima:%d/%m/%Y}",
                              datos={"codigo": r.get("codigo"), "descripcion": r.get("descripcion"), "unidad": r.get("unidad"),
                                     "cantidad": cant, "costo_unitario": cu, "almacen": r.get("almacen")}))


# ------------------------------------------------------------------ cuenta 23
CATEGORIAS_COSTO = [("mano_obra", ("62",), None), ("combustible", ("6", ), r"COMBUST|PETROLEO|DIESEL|GASOLIN"),
                    ("materiales", ("60", "61", "656"), None), ("servicios_terceros", ("63",), None),
                    ("depreciacion", ("681", "68"), None)]


def _categoria_costo(ln: L) -> str:
    for cat, prefijos, patron in CATEGORIAS_COSTO:
        if ln.cuenta.startswith(prefijos) and (patron is None or re.search(patron, (ln.glosa or "").upper())):
            return cat
    return "indirectos"


def servicios_proceso(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    sg = signo(ctx, cuenta)
    regs = {str(r["_clave"]): r for r in ctx.registros("SERVICIO_PROCESO")}

    def clave_de(ln: L) -> str:
        return ln.proyecto or ln.orden or (ln.cc and f"CC:{ln.cc}") or ""
    mov = defaultdict(lambda: {"debe": 0, "haber": 0, "cc": None, "lineas": []})
    for ln in ctx.de(cuenta):
        k = clave_de(ln)
        m = mov[k]
        if ln.periodo == 0:
            m.setdefault("apertura", 0)
            m["apertura"] += ln.neto
        elif any(cp.cuenta.startswith(cuenta) for cp in ctx.contrapartidas(ln)):
            m.setdefault("transf", 0)
            m["transf"] += ln.neto  # traslado de costos entre servicios
        else:
            m["debe"] += ln.debe
            m["haber"] += ln.haber
        m["cc"] = m["cc"] or ln.cc
        m["lineas"].append(ln)
    costos = defaultdict(lambda: defaultdict(int))
    for ln in ctx.lineas:
        if ln.cuenta.startswith("6") and ln.periodo and (ln.proyecto or ln.orden):
            costos[ln.proyecto or ln.orden][_categoria_costo(ln)] += ln.neto
    apertura = sum(v for c, v in ctx.apertura.items() if c.startswith(cuenta))
    asignado = 0
    claves = set(mov) | {k for k, r in regs.items() if (r["_cuenta"] or cuenta).startswith(cuenta) or cuenta.startswith(r["_cuenta"] or "~")}
    for k in sorted(claves):
        m = mov.get(k, {"debe": 0, "haber": 0, "cc": None, "lineas": []})
        r = regs.get(k, {})
        anterior = int(((_d(r.get("costo_acumulado_anterior")) or CERO) * 100)) if r else 0
        anterior += m.get("apertura", 0)
        asignado += int(((_d(r.get("costo_acumulado_anterior")) or CERO) * 100)) if r else 0
        saldo = anterior + m["debe"] - m["haber"] + m.get("transf", 0)
        if not saldo and not m["debe"] and not m["haber"] and not m.get("transf") and not r:
            continue
        cst = costos.get(k, {})
        estado_op = (r.get("estado_operativo") or "").upper() or None
        estado_fac = (r.get("estado_facturacion") or "").upper() or None
        estado_cont = (r.get("estado_contable") or "").upper() or None
        datos = {"cliente": r.get("cliente"), "contrato": r.get("contrato"), "orden_servicio": r.get("orden_servicio"),
                 "maquinaria": r.get("maquinaria"), "fecha_inicio": _f(r.get("fecha_inicio")), "fecha_estimada": _f(r.get("fecha_estimada")),
                 "fecha_real": _f(r.get("fecha_real")), "estado_operativo": estado_op, "estado_facturacion": estado_fac,
                 "estado_contable": estado_cont or ("PENDIENTE DE EVALUACIÓN" if estado_op in ("CULMINADO", "VALORIZADO", "FACTURADO") else None),
                 "costo_anterior": dec(anterior * sg), "costo_ejercicio": dec(m["debe"] * sg),
                 "reconocido": dec(m["haber"] * sg), "transferencias": dec(m.get("transf", 0) * sg),
                 **{c: dec(cst.get(c, 0)) for c in ("mano_obra", "materiales", "combustible", "servicios_terceros", "depreciacion", "indirectos")},
                 "pendiente_evaluacion": dec(saldo * sg) if estado_op in ("CULMINADO", "VALORIZADO", "FACTURADO", "SUSPENDIDO") else None}
        fila_k = f"SP|{k or '(sin proyecto)'}"
        obs = None
        if not r:
            obs = "Sin información operativa del servicio (registro auxiliar)"
        res.filas.append(_sustento(ctx, fila(clave=fila_k, cuenta=cuenta, categoria="Servicio en proceso", proyecto=k or None,
                                             centro_costo=r.get("centro_costo") or m["cc"], saldo=dec(saldo * sg),
                                             linea_id=m["lineas"][0].id if m["lineas"] else None,
                                             estado_sustento="DOCUMENTADO" if r else "SIN_DOCUMENTO", observacion=obs, datos=datos), cuenta))
        if saldo and estado_op in ("CULMINADO", "VALORIZADO", "FACTURADO"):
            res.hallazgo("SERVICIO_CULMINADO_EN_23", "ALTA", f"«{k}» está {estado_op.lower()} y mantiene saldo en la cuenta {cuenta}",
                         "Evalúe según la política contable (NIIF 15) si corresponde reconocer el costo en resultados, un activo por "
                         "contrato o un derecho de cobro. Un servicio pendiente de facturación no debe permanecer en la 23 por ese "
                         "solo hecho.", dec(saldo * sg), fila_k)
        if saldo and estado_op == "SUSPENDIDO":
            res.hallazgo("SERVICIO_SUSPENDIDO", "MEDIA", f"«{k}» está suspendido con costos acumulados", "Evalúe su recuperabilidad.",
                         dec(saldo * sg), fila_k)
        if saldo and not r:
            res.hallazgo("SERVICIO_SIN_REGISTRO", "MEDIA", f"«{k or 'sin proyecto'}» tiene costos acumulados sin información operativa",
                         None, dec(saldo * sg), fila_k)
    resto = apertura - asignado
    if resto:
        res.filas.append(fila(clave="SP|SI", cuenta=cuenta, categoria="Saldo inicial sin detalle por servicio", saldo=dec(resto * sg),
                              estado_sustento="SIN_DETALLE", observacion="Saldo inicial no asignado a servicios en el registro auxiliar"))


# ------------------------------------------------------------------ activo inmovilizado
def _activos(ctx: Ctx, cuenta: str, campo_cuenta="_cuenta") -> list[dict]:
    out = []
    for r in ctx.registros("ACTIVO_FIJO"):
        c = (r.get(campo_cuenta) if campo_cuenta != "_cuenta" else r["_cuenta"]) or ""
        if campo_cuenta != "_cuenta" and not c:
            c = "39"
        if c.startswith(cuenta) or (cuenta.startswith(c) and c):
            fa = _f(r.get("fecha_adquisicion"))
            if fa and fa > ctx.corte:
                continue
            out.append(r)
    return out


def _costo_final(r) -> Decimal:
    return sum(((_d(r.get(k)) or CERO) for k in ("costo_inicial", "adiciones", "mejoras", "transferencias")), CERO) - (_d(r.get("bajas")) or CERO)


def ppe(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    regs = _activos(ctx, cuenta)
    if not regs:
        res.hallazgo("SIN_REGISTRO_AUXILIAR", "MEDIA", "No se ha importado el registro de activos de la cuenta: el detalle se arma "
                     "desde el libro (por activo/maquinaria o documento).")
        generico(ctx, cuenta, plantilla, res)
        return
    for r in regs:
        cf = _costo_final(r)
        res.filas.append(fila(clave=f"AF|{r['_clave']}", cuenta=r["_cuenta"], categoria=r.get("categoria"), glosa=r.get("descripcion"),
                              fecha=_f(r.get("fecha_adquisicion")), centro_costo=r.get("centro_costo"), saldo=cf.quantize(C2),
                              estado_sustento="DOCUMENTADO", observacion=None,
                              datos={"codigo_activo": r["_clave"], "descripcion": r.get("descripcion"), "categoria_activo": r.get("categoria"),
                                     "fecha_adquisicion": _f(r.get("fecha_adquisicion")), "fecha_uso": _f(r.get("fecha_uso")),
                                     **{k: _d(r.get(k)) for k in ("costo_inicial", "adiciones", "mejoras", "transferencias", "bajas", "valor_residual")},
                                     "costo_final": cf.quantize(C2), "vida_util_meses": int(r["vida_util_meses"]) if r.get("vida_util_meses") else None,
                                     "ubicacion": r.get("ubicacion"), "maquinaria": r.get("maquinaria")}))


def _meses(desde: date, hasta: date) -> int:
    return max((hasta.year - desde.year) * 12 + hasta.month - desde.month + 1, 0)


def depreciacion(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    regs = _activos(ctx, cuenta, campo_cuenta="cuenta_depreciacion")
    if not regs:
        res.hallazgo("SIN_REGISTRO_AUXILIAR", "MEDIA", "No se ha importado el registro de activos: no se recalcula la depreciación.")
        generico(ctx, cuenta, plantilla, res)
        return
    inicio = date(ctx.ejercicio, 1, 1)
    sin_vida = []
    for r in regs:
        cf = _costo_final(r)
        residual = _d(r.get("valor_residual")) or CERO
        dep_ini = _d(r.get("depreciacion_acumulada_inicial")) or CERO
        vida = int(r["vida_util_meses"]) if str(r.get("vida_util_meses") or "").strip().isdigit() else None
        uso = _f(r.get("fecha_uso")) or _f(r.get("fecha_adquisicion"))
        dep_per = None
        if vida and uso:
            desde = max(uso.replace(day=1), inicio)
            meses = _meses(desde, ctx.corte) if uso <= ctx.corte else 0
            mensual = (cf - residual) / vida
            dep_per = min((mensual * meses).quantize(C2, ROUND_HALF_UP), max(cf - residual - dep_ini, CERO))
        else:
            sin_vida.append(r["_clave"])
        ajustes = _d(r.get("ajustes_depreciacion")) or CERO
        bajas = _d(r.get("depreciacion_bajas")) or CERO
        final = dep_ini + (dep_per or CERO) + ajustes - bajas
        tasa = _d(r.get("tasa_tributaria"))
        dep_trib = None
        if tasa is not None and uso and uso <= ctx.corte:
            dep_trib = (cf * tasa / 100 / 12 * _meses(max(uso.replace(day=1), inicio), ctx.corte)).quantize(C2, ROUND_HALF_UP)
        res.filas.append(fila(clave=f"DEP|{r['_clave']}", cuenta=r.get("cuenta_depreciacion") or cuenta, categoria=r.get("categoria"),
                              glosa=r.get("descripcion"), saldo=final.quantize(C2), estado_sustento="DOCUMENTADO",
                              observacion=None if vida else "Sin vida útil financiera: no se calcula la depreciación del periodo",
                              datos={"codigo_activo": r["_clave"], "descripcion": r.get("descripcion"), "costo_final": cf.quantize(C2),
                                     "dep_inicial": dep_ini, "dep_periodo": dep_per, "ajustes": ajustes, "bajas": bajas,
                                     "dep_final": final.quantize(C2), "valor_neto": (cf - final).quantize(C2), "vida_util_meses": vida,
                                     "dep_tributaria": dep_trib,
                                     "diferencia_tributaria": (dep_per - dep_trib).quantize(C2) if dep_per is not None and dep_trib is not None else None}))
    if sin_vida:
        res.hallazgo("SIN_VIDA_UTIL", "MEDIA", f"{len(sin_vida)} activos sin vida útil financiera registrada",
                     "No se usan las tasas tributarias como vida útil financiera. Registre la vida útil estimada (NIC 16).")
    res.extras["nota"] = "Depreciación del periodo recalculada en línea recta desde el mes en que el activo está disponible para su uso."


# ------------------------------------------------------------------ cuenta 40
TRIBUTOS = [("40111", "IGV – cuenta propia"), ("40112", "IGV – servicios prestados por no domiciliados"), ("40113", "IGV – régimen de percepciones"),
            ("40114", "IGV – régimen de retenciones"), ("4011", "IGV"), ("40171", "Impuesto a la renta de tercera categoría"),
            ("40172", "Impuesto a la renta de segunda categoría"), ("40173", "Retenciones de cuarta categoría"),
            ("40174", "Retenciones de quinta categoría"), ("40175", "Renta de no domiciliados"), ("4017", "Impuesto a la renta"),
            ("4018", "Otros impuestos y contraprestaciones"), ("40311", "EsSalud"), ("4031", "EsSalud"), ("4032", "ONP"),
            ("4033", "Contribución al SENATI"), ("4034", "Contribución al SENCICO"), ("403", "Aportes a instituciones públicas"),
            ("407", "Administradoras de fondos de pensiones"), ("409", "Otros costos administrativos e intereses"), ("40", "Otros tributos")]


def tributos(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    mapa = (plantilla.get("parametros") or {}).get("tributos")
    tabla = sorted((mapa.items() if mapa else TRIBUTOS), key=lambda x: -len(x[0]))

    def nombre(c):
        return next((n for k, n in tabla if c.startswith(k)), "Otros tributos")

    def concepto(glosa):
        g = (glosa or "").upper()
        return "Intereses" if re.search(r"INTERES|MORATORI", g) else ("Multa" if re.search(r"MULTA|INFRACC", g) else "Tributo")

    def extra(it, pc):
        es_origen = it["rol"] == "ORIGEN"
        return {"tributo": nombre(it["cuenta"]), "periodo_tributario": f"{it['ejercicio']}-{(it['periodo'] or 0):02d}",
                "determinado": it["importe"] if es_origen else None, "pagos": _q(pc.get("PAGO", CERO)),
                "compensaciones": _q(sum((v for k, v in pc.items() if k in ("NOTA_CREDITO", "RECLASIFICACION", "OTRO", "EXTORNO")), CERO)),
                "creditos": _q(sum((v for k, v in pc.items() if k in ("RETENCION", "PERCEPCION", "DETRACCION", "DIFERENCIA_CAMBIO")), CERO)),
                "concepto": concepto(it["glosa"]), "exigible": "Sí" if es_origen else "No (saldo a favor / crédito)"}
    if not _filas_composicion(ctx, cuenta, plantilla, res, extra):
        generico(ctx, cuenta, plantilla, res)
        for r in res.filas:
            r["datos"].update(tributo=nombre(r["cuenta"] or cuenta), concepto=concepto(r["glosa"]),
                              exigible="Sí" if r["saldo"] > 0 else "No (saldo a favor / crédito)")
    for r in res.filas:
        r["categoria"] = r["datos"].get("tributo") or nombre(r["cuenta"] or cuenta)
    por_trib = defaultdict(lambda: CERO)
    for r in res.filas:
        por_trib[(r["cuenta"], r["datos"].get("tributo"))] += r["saldo"]
    for (c, t), v in por_trib.items():
        if v < 0:
            res.hallazgo("TRIBUTO_SALDO_A_FAVOR", "MEDIA", f"{t} ({c}) presenta saldo deudor de {abs(v)}",
                         "Un saldo deudor en la cuenta 40 no es una obligación exigible: evalúe si es crédito fiscal, pago en exceso o "
                         "error de registro.", abs(v), f"{c}|{t}")


# ------------------------------------------------------------------ cuenta 41
CONCEPTOS_41 = [("4111", "Sueldos y salarios"), ("4112", "Comisiones"), ("4113", "Remuneraciones en especie"), ("4114", "Gratificaciones"),
                ("4115", "Vacaciones"), ("411", "Remuneraciones"), ("413", "Participación de los trabajadores"),
                ("4151", "Compensación por tiempo de servicios (CTS)"), ("4152", "Adelanto de CTS"), ("4153", "Pensiones y jubilaciones"),
                ("415", "Beneficios sociales"), ("419", "Otras remuneraciones y participaciones"), ("41", "Remuneraciones")]


def remuneraciones(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    def concepto(c):
        if "LIQUIDAC" in c.upper():
            return "Liquidación"
        return next((n for k, n in CONCEPTOS_41 if c.startswith(k)), "Otros beneficios")
    acc = defaultdict(lambda: {"si": 0, "prov": 0, "pagos": 0, "ajustes": 0, "rs": None, "linea": None, "liq": False})
    for (c, t), v in ctx.apertura_ter.items():
        if c.startswith(cuenta) and v:
            acc[(c, t)]["si"] += v
    for ln in ctx.de(cuenta):
        x = acc[(ln.cuenta, ln.tercero)]
        x["rs"] = x["rs"] or ln.razon_social
        x["linea"] = x["linea"] or ln.id
        x["liq"] = x["liq"] or bool(re.search(r"LIQUIDAC", (ln.glosa or "").upper()))
        if ln.periodo == 0:
            x["si"] += ln.neto
            continue
        x["prov"] += ln.haber
        if ln.debe:
            if any(cp.cuenta.startswith("10") for cp in ctx.contrapartidas(ln)):
                x["pagos"] += ln.debe
            else:
                x["ajustes"] += ln.debe
    for (c, t), x in sorted(acc.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        sg = signo(ctx, c)
        neto = x["si"] - x["prov"] + x["pagos"] + x["ajustes"]  # deudor positivo
        if not (neto or x["prov"] or x["pagos"]):
            continue
        conc = "Liquidación" if x["liq"] else concepto(c)
        sin_ter = not t
        res.filas.append(_sustento(ctx, fila(
            clave=f"{c}|{t or ''}|REM", cuenta=c, categoria=conc, tercero=t, razon_social=x["rs"], saldo=dec(neto * sg),
            linea_id=x["linea"], estado_sustento="SIN_DETALLE" if sin_ter and not x["prov"] and not x["pagos"] else (
                "SIN_DOCUMENTO" if sin_ter else "DOCUMENTADO"),
            observacion="Sin trabajador identificado" if sin_ter else None,
            datos={"concepto": conc, "saldo_inicial": dec(x["si"] * sg), "provisiones": dec(x["prov"]), "pagos": dec(x["pagos"]),
                   "ajustes": dec(x["ajustes"]), "personal": True}), cuenta))
    res.extras["datos_personales"] = True


# ------------------------------------------------------------------ cuenta 45
def financieras(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    contratos = [r for r in ctx.registros("CONTRATO_FINANCIERO") if (r["_cuenta"] or cuenta).startswith(cuenta) or cuenta.startswith(r["_cuenta"] or "~")]
    if not contratos:
        res.hallazgo("SIN_REGISTRO_AUXILIAR", "MEDIA", "No se han importado contratos ni cronogramas financieros: el detalle se arma desde el libro.")
        generico(ctx, cuenta, plantilla, res)
        return
    cuotas = defaultdict(list)
    for q in ctx.registros("CUOTA_FINANCIERA"):
        cuotas[str(q.get("contrato"))].append(q)
    lineas = ctx.de(cuenta)
    usadas = set()
    asignado_ap = 0
    for k in contratos:
        cod = str(k["_clave"])
        patron = re.compile(re.escape(cod.upper()))
        mias = [ln for ln in lineas if ln.id not in usadas and any(patron.search((v or "").upper()) for v in (ln.referencia, ln.numero, ln.glosa))]
        usadas |= {ln.id for ln in mias}
        sg = signo(ctx, k["_cuenta"] or cuenta)
        moneda = (k.get("moneda") or "PEN").upper()
        neto = sum(x.neto for x in mias)
        neto_me = sum(x.neto_me for x in mias)
        ap = 0
        ruc = k.get("ruc_entidad")
        if ruc:
            ap = sum(v for (c, t), v in ctx.apertura_ter.items() if c.startswith(cuenta) and t == ruc)
            asignado_ap += ap
        si_contrato = _d(k.get("saldo_inicial"))
        capital = _d(k.get("capital")) or CERO
        amort = sum((x.debe_me if moneda != "PEN" else x.debe) for x in mias if x.periodo)
        lst = sorted(cuotas.get(cod, []), key=lambda q: _f(q.get("fecha_vencimiento")) or date.max)
        vencidas = [q for q in lst if (_f(q.get("fecha_vencimiento")) or date.max) <= ctx.corte]
        futuras = [q for q in lst if (_f(q.get("fecha_vencimiento")) or date.max) > ctx.corte]
        cap_venc = sum(((_d(q.get("capital")) or CERO) for q in vencidas), CERO)
        estado_pago = all(str(q.get("pagada", "")).strip().upper() in ("S", "SI", "SÍ", "N", "NO") for q in lst) and lst
        impagas = [q for q in vencidas if str(q.get("pagada", "")).strip().upper() in ("N", "NO")] if estado_pago else None
        pendiente = capital - cap_venc + (sum(((_d(q.get("capital")) or CERO) for q in impagas), CERO) if impagas else CERO)
        lim = date(ctx.corte.year + 1, ctx.corte.month, min(ctx.corte.day, 28))
        corriente = sum(((_d(q.get("capital")) or CERO) for q in futuras if (_f(q.get("fecha_vencimiento")) or date.max) <= lim), CERO)
        corriente += sum(((_d(q.get("capital")) or CERO) for q in (impagas or [])), CERO)
        prox = futuras[0] if futuras else None
        datos = {"entidad": k.get("entidad"), "contrato": cod, "tipo": k.get("tipo"), "capital_original": capital,
                 "amortizado_libros": dec(amort), "capital_pendiente": pendiente.quantize(C2),
                 "intereses": sum(((_d(q.get("interes")) or CERO) for q in vencidas), CERO).quantize(C2),
                 "comisiones": sum(((_d(q.get("comision")) or CERO) + (_d(q.get("otros")) or CERO) for q in vencidas), CERO).quantize(C2),
                 "cuotas_vencidas": len(impagas) if impagas is not None else None,
                 "importe_vencido": sum(((_d(q.get("capital")) or CERO) for q in impagas), CERO) if impagas is not None else None,
                 "proximo_vencimiento": _f(prox.get("fecha_vencimiento")) if prox else None,
                 "proxima_cuota": sum(((_d(prox.get(c)) or CERO) for c in ("capital", "interes", "comision")), CERO) if prox else None,
                 "porcion_corriente": corriente.quantize(C2), "porcion_no_corriente": (pendiente - corriente).quantize(C2),
                 "garantias": k.get("garantias")}
        saldo_libro = dec((ap + neto) * sg)
        saldo_libro_mon = dec(neto_me * sg) if moneda != "PEN" else saldo_libro
        res.filas.append(fila(clave=f"FIN|{cod}", cuenta=k["_cuenta"] or cuenta, categoria=k.get("tipo"), tercero=ruc,
                              razon_social=k.get("entidad"), moneda=moneda, saldo=saldo_libro,
                              saldo_me=saldo_libro_mon if moneda != "PEN" else None,
                              linea_id=mias[0].id if mias else None, estado_sustento="DOCUMENTADO",
                              observacion=None if lst else "Contrato sin cronograma de cuotas importado", datos=datos))
        if si_contrato is not None and not ap:
            res.hallazgo("SALDO_INICIAL_CONTRATO", "INFORMATIVA", f"El contrato {cod} informa saldo inicial {si_contrato}; asigne el RUC de "
                         "la entidad para vincular el saldo inicial del libro.", clave_fila=f"FIN|{cod}")
        if lst and moneda == "PEN" and abs(pendiente - saldo_libro) > Decimal("1") and (ap or not ctx.apertura):
            res.hallazgo("CRONOGRAMA_DIFIERE", "MEDIA", f"Contrato {cod}: capital pendiente según cronograma {pendiente} y saldo en libros {saldo_libro}",
                         "Revise amortizaciones no registradas o diferencias en el cronograma.", (pendiente - saldo_libro).quantize(C2), f"FIN|{cod}")
        if impagas:
            res.hallazgo("CUOTAS_VENCIDAS", "ALTA", f"Contrato {cod}: {len(impagas)} cuotas vencidas impagas", None,
                         datos["importe_vencido"], f"FIN|{cod}")
        if lst and impagas is None:
            res.hallazgo("ESTADO_CUOTAS_NO_INFORMADO", "INFORMATIVA", f"Contrato {cod}: el cronograma no indica qué cuotas están pagadas",
                         "Sin esa información no se calculan cuotas vencidas impagas.", clave_fila=f"FIN|{cod}")
    resto = [ln for ln in lineas if ln.id not in usadas]
    if resto:
        generico(ctx, cuenta, plantilla, res, lineas=resto, sin_apertura=True, categoria="Sin contrato identificado")
    ap_total = sum(v for (c, t), v in ctx.apertura_ter.items() if c.startswith(cuenta))
    if ap_total - asignado_ap:
        sg = signo(ctx, cuenta)
        res.filas.append(fila(clave=f"{cuenta}|SI", cuenta=cuenta, categoria="Saldo inicial", saldo=dec((ap_total - asignado_ap) * sg),
                              estado_sustento="SIN_DETALLE", observacion="Saldo inicial no vinculado a un contrato"))


# ------------------------------------------------------------------ elemento 5
def patrimonio(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    hojas = sorted({c for c in ctx.hojas() if c.startswith(cuenta)})
    for c in hojas:
        sg = signo(ctx, c)
        si = ctx.apertura.get(c, 0)
        cat = defaultdict(int)
        primera = None
        for ln in ctx.por_cuenta.get(c, []):
            if ln.periodo == 0:
                si += ln.neto
                continue
            primera = primera or ln.id
            contra = [x.cuenta for x in ctx.contrapartidas(ln)]
            nat = ln.neto * sg  # positivo = aumenta el patrimonio
            if any(x.startswith("89") for x in contra) or c.startswith("59") and any(x.startswith("8") for x in contra):
                cat["resultado"] += nat
            elif nat > 0 and any(x.startswith(("10", "14", "16", "3", "2")) for x in contra):
                cat["aportes"] += nat
            elif nat < 0 and any(x.startswith(("44", "10", "46")) for x in contra):
                cat["distribuciones"] += nat
            elif any(x.startswith("5") for x in contra):
                cat["capitalizaciones" if c.startswith("50") and nat > 0 else "reclasificaciones"] += nat
            else:
                cat["ajustes"] += nat
        final = si * sg + sum(cat.values())
        if not (final or si or cat):
            continue
        r = fila(clave=f"{c}|PN", cuenta=c, categoria=ctx.descripcion(c), saldo=dec(final), linea_id=primera,
                 estado_sustento="SIN_DOCUMENTO", observacion="Requiere actas, escrituras o acuerdos que sustenten los movimientos",
                 datos={"saldo_inicial": dec(si * sg), **{k: dec(cat.get(k, 0)) for k in
                                                         ("aportes", "distribuciones", "capitalizaciones", "reclasificaciones", "ajustes", "resultado")}})
        res.filas.append(_sustento(ctx, r, cuenta))


# ------------------------------------------------------------------ elemento 6
TIPOS_GASTO = [("60", "Compras"), ("61", "Variación de existencias"), ("62", "Gastos de personal"), ("634", "Mantenimiento y reparaciones"),
               ("635", "Alquileres"), ("63", "Servicios de terceros"), ("64", "Tributos"), ("651", "Seguros"), ("65", "Otros gastos de gestión"),
               ("66", "Pérdida por medición de activos"), ("67", "Gastos financieros"), ("681", "Depreciación"), ("68", "Valuación y deterioro"),
               ("69", "Costo de ventas")]
MATERIALIDAD_VARIACION = Decimal("1000")


def _mes(f: date | None) -> str | None:
    return f"{f.year}-{f.month:02d}" if f else None


def _variaciones(ctx: Ctx, lineas, res: Resultado, sg=1):
    por = defaultdict(lambda: defaultdict(int))
    for ln in lineas:
        if ln.periodo:
            por[ln.cuenta][ln.periodo] += ln.neto * sg
    for c, meses in por.items():
        if len(meses) < 3:
            continue
        for p, v in meses.items():
            otros = [x for q, x in meses.items() if q != p]
            prom = Decimal(sum(otros)) / len(otros)
            if prom and abs(v - prom) > abs(prom) * Decimal("0.5") and abs(Decimal(v) - prom) / 100 >= MATERIALIDAD_VARIACION:
                res.hallazgo("VARIACION_SIGNIFICATIVA", "INFORMATIVA",
                             f"{c}: el mes {p:02d} ({dec(v)}) se aparta más de 50 % del promedio de los demás meses ({dec(int(prom))})",
                             "Verifique registros duplicados, omitidos o estacionales.", dec(int(Decimal(v) - prom)), f"{c}|{p:02d}")


def gastos(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    centros = ctx.centros()
    lineas = ctx.de(cuenta)
    grupos = defaultdict(list)
    for ln in lineas:
        k = (ln.cuenta, ln.tercero or "", ln.tipo_doc or "", ln.serie or "", ln.numero or "", ln.cc or "", ln.proyecto or "",
             ln.maquinaria or "", _mes(ln.fecha) or "", "" if ln.numero else (ln.etiqueta_asiento or f"L{ln.id}"))
        grupos[k].append(ln)
    for k, ls in grupos.items():
        neto = sum(x.neto for x in ls)
        if not neto:
            continue
        p = ls[0]
        sg = signo(ctx, p.cuenta)
        tipo = next((n for pre, n in TIPOS_GASTO if p.cuenta.startswith(pre)), "Otros gastos")
        r = fila(clave="|".join(k), cuenta=p.cuenta, categoria=tipo, fecha=min((x.fecha for x in ls if x.fecha), default=None),
                 tipo_documento=p.tipo_doc, serie=p.serie, numero=p.numero, tercero=p.tercero, razon_social=p.razon_social,
                 glosa=p.glosa, moneda=p.moneda, saldo=dec(neto * sg), centro_costo=p.cc, proyecto=p.proyecto,
                 referencia=p.etiqueta_asiento, linea_id=p.id,
                 estado_sustento="DOCUMENTADO" if p.numero else "SIN_DOCUMENTO",
                 observacion=None if p.numero else "Gasto sin comprobante identificado (pendiente de sustento)",
                 datos={"mes": _mes(p.fecha), "tipo_gasto": tipo, "maquinaria": p.maquinaria, "unidad_negocio": centros.get(p.cc)})
        res.filas.append(_sustento(ctx, r, cuenta))
    sin = [r for r in res.filas if r["estado_sustento"] == "SIN_DOCUMENTO"]
    if sin:
        res.hallazgo("GASTO_SIN_SUSTENTO", "MEDIA", f"{len(sin)} registros de gasto sin comprobante identificado",
                     "Adjunte el sustento o verifique si corresponden a provisiones o asientos de ajuste.",
                     sum((r["saldo"] for r in sin), CERO))
    _variaciones(ctx, lineas, res)


# ------------------------------------------------------------------ elemento 7
TRANSFERENCIA = ("71", "72", "78", "79")


def ingresos(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    centros = ctx.centros()
    lineas = ctx.de(cuenta)
    grupos = defaultdict(list)
    for ln in lineas:
        k = (ln.cuenta, ln.tercero or "", ln.tipo_doc or "", ln.serie or "", ln.numero or "", ln.proyecto or "", _mes(ln.fecha) or "",
             "" if ln.numero else (ln.etiqueta_asiento or f"L{ln.id}"))
        grupos[k].append(ln)
    for k, ls in grupos.items():
        neto = sum(x.neto for x in ls)
        if not neto:
            continue
        p = ls[0]
        sg = signo(ctx, p.cuenta)
        ing = sum(x.haber for x in ls)
        nc = sum(x.debe for x in ls if x.tipo_doc == "07")
        desc = sum(x.debe for x in ls if x.tipo_doc != "07" and (x.cuenta.startswith("74") or re.search(r"DESCUENT|BONIFIC", (x.glosa or "").upper())))
        aj = sum(x.debe for x in ls) - nc - desc
        transf = p.cuenta.startswith(TRANSFERENCIA)
        r = fila(clave="|".join(k), cuenta=p.cuenta, categoria="Cuenta de transferencia contable" if transf else ctx.descripcion(p.cuenta[:2]),
                 fecha=min((x.fecha for x in ls if x.fecha), default=None), tipo_documento=p.tipo_doc, serie=p.serie, numero=p.numero,
                 tercero=p.tercero, razon_social=p.razon_social, glosa=p.glosa, moneda=p.moneda, saldo=dec(neto * sg),
                 centro_costo=p.cc, proyecto=p.proyecto, referencia=p.etiqueta_asiento, linea_id=p.id,
                 estado_sustento="DOCUMENTADO" if p.numero or transf else "SIN_DOCUMENTO",
                 observacion="No constituye ingreso económico (transferencia)" if transf else (None if p.numero else "Ingreso sin comprobante identificado"),
                 datos={"mes": _mes(p.fecha), "ingresos": dec(ing), "descuentos": dec(desc), "notas_credito": dec(nc), "ajustes": dec(aj),
                        "unidad_negocio": centros.get(p.cc), "transferencia": "Sí" if transf else "No"})
        res.filas.append(_sustento(ctx, r, cuenta))
    res.extras["ingresos_economicos"] = str(sum((r["saldo"] for r in res.filas if r["datos"]["transferencia"] == "No"), CERO))
    res.extras["transferencias"] = str(sum((r["saldo"] for r in res.filas if r["datos"]["transferencia"] == "Sí"), CERO))
    _variaciones(ctx, [x for x in lineas if not x.cuenta.startswith(TRANSFERENCIA)], res, sg=-1)


# ------------------------------------------------------------------ origen y destino (79 / 9)
def origen_destino(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    from app.analisis import destino as dest_mod
    from app.analisis import motor as motor3
    centros = ctx.centros()
    lineas = ctx.de(cuenta)
    grupos = defaultdict(list)
    for ln in lineas:
        if ln.periodo == 0:
            continue
        grupos[(ln.cuenta, ln.cc or "", ln.proyecto or "", _mes(ln.fecha) or "")].append(ln)
    total = 0
    for k, ls in grupos.items():
        neto = sum(x.neto for x in ls) * signo(ctx, k[0])
        total += neto
    for k, ls in grupos.items():
        sg = signo(ctx, k[0])
        neto = sum(x.neto for x in ls) * sg
        if not neto:
            continue
        res.filas.append(fila(clave="|".join(k), cuenta=k[0], categoria=ctx.descripcion(k[0]), centro_costo=k[1] or None,
                              proyecto=k[2] or None, saldo=dec(neto), referencia=ls[0].etiqueta_asiento, linea_id=ls[0].id,
                              estado_sustento="DOCUMENTADO" if k[1] else "SIN_DOCUMENTO",
                              observacion=None if k[1] else "Destino sin centro de costo",
                              datos={"mes": k[3] or None, "porcentaje": (Decimal(neto) / total * 100).quantize(C2) if total else None,
                                     "unidad_negocio": centros.get(k[1])}))
    # validación 6 / 79 / 9 / 78 con las reglas configuradas (fase 3)
    filtro = ctx.f.filtro_lineas(1, min(ctx.periodo, 12))
    from sqlalchemy import and_, or_
    from app.models import LineaDiario
    ls3 = motor3.cargar_lineas(ctx.db, and_(filtro, or_(LineaDiario.fecha_contable.is_(None), LineaDiario.fecha_contable <= ctx.corte),
                                            or_(*[LineaDiario.cuenta.like(f"{p}%") for p in ("6", "9", "79", "78")])))
    an = dest_mod.analizar(ctx.db, ctx.empresa_id, ls3, ctx.ejercicio, min(ctx.periodo, 12))
    tabla = []
    for o in an["origenes"]:
        tabla.append({"cuenta_origen": o["clave"], "descripcion": o["descripcion"], "importe_sujeto": str(o["origen"]),
                      "cuenta_transferencia": "79", "destino_esperado": str(o["esperado"]), "sin_regla": str(o["sin_regla"]),
                      "estado": o["estado"]})
    destinos = [{"cuenta_destino": d["clave"], "esperado": str(d["esperado"]), "registrado": str(d["registrado"]),
                 "diferencia": str(d["diferencia"]), "estado": d["estado"]} for d in an["destinos"]]
    res.extras["origen_destino"] = {"origenes": tabla, "destinos": destinos,
                                    "por_periodo": [{k: (str(v) if isinstance(v, Decimal) else v) for k, v in x.items()} for x in an["resumen"]],
                                    "politica": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in an["politica"].items()}}
    for x in an["resumen"]:
        if x["estado"] in ("DESTINO_DUPLICADO", "DUPLICIDAD_PRESENTACION"):
            res.hallazgo(x["estado"], "ALTA", f"Periodo {x['periodo']:02d}: posible duplicidad de gastos en la presentación "
                         f"(origen {x['origen']}, destino {x['destino']}, 79 {x['cargas_imputables']})",
                         "La clase 9 y la clase 6 no deben sumarse en los estados financieros.", x["diferencia"], f"P{x['periodo']}")
        elif x["estado"] == "DIFERENCIA":
            res.hallazgo("DIFERENCIA_ORIGEN_DESTINO", "MEDIA", f"Periodo {x['periodo']:02d}: origen {x['origen']} y destino {x['destino']} difieren",
                         "No toda la clase 6 debe distribuirse: verifique las exclusiones configuradas.", x["diferencia"], f"P{x['periodo']}")
    for d in an["destinos"]:
        if d["estado"] == "DIFERENCIA":
            res.hallazgo("DESTINO_DIFIERE", "MEDIA", f"Destino {d['clave']}: esperado {d['esperado']}, registrado {d['registrado']}",
                         None, d["diferencia"], f"D{d['clave']}")


# ------------------------------------------------------------------ elementos 8 y 0
def cierre(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    generico(ctx, cuenta, plantilla, res, agrupar_sin_doc="tercero", categoria="Saldo intermediario / cuenta de cierre")
    for r in res.filas:
        if r["estado_sustento"] == "SIN_DOCUMENTO":
            r["estado_sustento"], r["observacion"] = "DOCUMENTADO", "Cuenta de cálculo: se sustenta con los saldos de las cuentas que la originan"


def orden(ctx: Ctx, cuenta: str, plantilla: dict, res: Resultado) -> None:
    generico(ctx, cuenta, plantilla, res, categoria="Cuenta de orden (control)")
    res.extras["nota"] = ("Las cuentas de orden registran garantías, compromisos, contingencias y otros controles. No se presentan "
                          "como activos ni pasivos reconocidos.")


CONSTRUCTORES = {
    "EFECTIVO": efectivo, "CARTERA": cartera, "PERSONAL": personal, "ESTIMACION": estimacion, "DIFERIDO": diferido,
    "EXISTENCIAS": existencias, "SERVICIOS_PROCESO": servicios_proceso, "PPE": ppe, "DEPRECIACION": depreciacion,
    "TRIBUTOS": tributos, "REMUNERACIONES": remuneraciones, "FINANCIERAS": financieras, "PATRIMONIO": patrimonio,
    "GASTOS": gastos, "INGRESOS": ingresos, "ORIGEN_DESTINO": origen_destino, "CIERRE": cierre, "ORDEN": orden,
    "GENERICO": generico,
}
