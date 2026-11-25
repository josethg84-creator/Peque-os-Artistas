"""Motor de validación contable.

Recibe los registros ya extraídos y normalizados y devuelve observaciones clasificadas.
Las reglas que dependen de datos maestros (plan de cuentas, centros de costo, tipos de
cambio, terceros) solo se aplican si la empresa los tiene cargados; si no, se emite una
recomendación informativa en lugar de suponer un error.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.contable.analitica import ReglasAnaliticas, validar_analitica
from app.contable.campos import CAMPOS, TIPOS, es_obligatorio
from app.contable.homologacion import CAMPOS_IMPORTE_TOTAL, Extraccion, _asiento, _documento
from app.contable.observaciones import Obs
from app.core.utils import ruc_valido
from app.models import (CentroCosto, ConfiguracionContable, CuentaContable, DocumentoRegistro, LineaDiario,
                        LoteContable, ReglaDestino, SaldoCuenta, Tercero, TipoCambio)

CERO = Decimal("0")
TASAS_IGV = (Decimal("0.18"), Decimal("0.10"))


@dataclass
class Contexto:
    empresa_id: int
    tipo: str
    ejercicio: int | None
    periodo: int | None
    importacion_completa: bool
    hash_archivo: str
    tolerancia: Decimal = Decimal("0.01")
    materialidad: Decimal = Decimal("100")
    tolerancia_tc: Decimal = Decimal("0.005")
    tolerancia_conversion: Decimal = Decimal("0.05")
    prefijos_sin_movimiento: list[str] = field(default_factory=list)
    plan: dict[str, CuentaContable] | None = None
    centros: set[str] | None = None
    tipos_cambio: dict[tuple, tuple] = field(default_factory=dict)
    terceros: dict[str, set[str]] = field(default_factory=dict)
    analitica: ReglasAnaliticas | None = None
    lote_previo_mismo_archivo: int | None = None


def cargar_contexto(db: Session, empresa_id: int, tipo: str, ejercicio, periodo, completa: bool,
                    hash_archivo: str) -> Contexto:
    cfg = db.scalar(select(ConfiguracionContable).where(ConfiguracionContable.empresa_id == empresa_id)) \
        or ConfiguracionContable(empresa_id=empresa_id)
    ctx = Contexto(empresa_id, tipo, ejercicio, periodo, completa, hash_archivo,
                   tolerancia=Decimal(str(cfg.tolerancia_descuadre if cfg.tolerancia_descuadre is not None else "0.01")),
                   materialidad=Decimal(str(cfg.materialidad if cfg.materialidad is not None else "100")),
                   tolerancia_tc=Decimal(str(cfg.tolerancia_tipo_cambio if cfg.tolerancia_tipo_cambio is not None else "0.005")),
                   tolerancia_conversion=Decimal(str(cfg.tolerancia_conversion if cfg.tolerancia_conversion is not None else "0.05")),
                   prefijos_sin_movimiento=_lista(cfg.prefijos_sin_movimiento))
    plan = list(db.scalars(select(CuentaContable).where(CuentaContable.empresa_id == empresa_id)))
    ctx.plan = {c.codigo: c for c in plan} or None
    centros = db.scalars(select(CentroCosto.codigo).where(CentroCosto.empresa_id == empresa_id)).all()
    ctx.centros = set(centros) or None
    for t in db.scalars(select(TipoCambio).where(TipoCambio.empresa_id == empresa_id)):
        ctx.tipos_cambio[(t.fecha, t.moneda)] = (t.compra, t.venta)
    for rol, num in db.execute(select(Tercero.rol, Tercero.numero_documento).where(Tercero.empresa_id == empresa_id)):
        ctx.terceros.setdefault(rol, set()).add(num)
    reglas = list(db.scalars(select(ReglaDestino).where(ReglaDestino.empresa_id == empresa_id,
                                                         ReglaDestino.activa.is_(True))))
    ctx.analitica = ReglasAnaliticas.desde_config(cfg, reglas, ctx.plan)
    ctx.lote_previo_mismo_archivo = db.scalar(select(LoteContable.id).where(
        LoteContable.empresa_id == empresa_id, LoteContable.hash_archivo == hash_archivo,
        LoteContable.tipo_informacion == tipo, LoteContable.estado == "ACTIVO").limit(1))
    return ctx


def _lista(texto: str | None) -> list[str]:
    return [p.strip() for p in (texto or "").split(",") if p.strip()]


# ===================================================================== entrada
def validar(db: Session, ex: Extraccion, mapeo: dict[str, int], ctx: Contexto,
            columnas_vacias: list[str]) -> list[Obs]:
    obs: list[Obs] = []
    tipo = ctx.tipo
    _campos_opcionales(tipo, mapeo, columnas_vacias, obs)
    if ctx.lote_previo_mismo_archivo:
        obs.append(Obs("DUP003", mensaje=f"El archivo ya fue importado en el lote #{ctx.lote_previo_mismo_archivo}."))
    regs = ex.registros

    if tipo in ("DIARIO", "MAYOR", "SALDOS_INICIALES"):
        _validar_lineas(db, regs, ctx, obs)
    elif tipo == "BALANCE":
        _validar_balance(db, regs, ctx, obs)
    elif tipo in ("COMPRAS", "VENTAS"):
        _validar_registro(db, regs, ctx, obs)
    elif tipo in ("CXC", "CXP"):
        _validar_cartera(regs, ctx, obs)
    elif tipo == "PLAN_CUENTAS":
        _validar_plan(regs, ctx, obs)
    elif tipo in ("CLIENTES", "PROVEEDORES"):
        _validar_terceros(regs, obs)
    elif tipo == "CENTROS_COSTO":
        _validar_centros(regs, ctx, obs)
    elif tipo == "TIPOS_CAMBIO":
        _validar_tipos_cambio(regs, obs)
    _validar_totales_archivo(ex, ctx, obs)
    return obs


# ===================================================================== comunes
def _campos_opcionales(tipo, mapeo, columnas_vacias, obs):
    tdef = TIPOS[tipo]
    alternativos = {c for g in tdef.requeridos for c in g}
    faltan = [CAMPOS[c].etiqueta for c in tdef.campos
              if c not in mapeo and c not in alternativos and not es_obligatorio(tipo, c)
              and c not in ("importe_mn", "importe_me", "indicador_dh", "saldo_inicial", "saldo_final")]
    if faltan:
        obs.append(Obs("EST004", mensaje=f"Campos opcionales no informados ({len(faltan)}): {', '.join(faltan)}."))
    for c in columnas_vacias:
        obs.append(Obs("EST005", campo=c, mensaje=f"La columna homologada como «{CAMPOS[c].etiqueta}» no tiene datos."))


def _rango_periodo(ctx: Contexto) -> tuple[date, date] | None:
    if not ctx.ejercicio:
        return None
    if ctx.periodo and 1 <= ctx.periodo <= 12:
        inicio = date(ctx.ejercicio, ctx.periodo, 1)
        fin = date(ctx.ejercicio + (ctx.periodo == 12), ctx.periodo % 12 + 1, 1)
        return inicio, date.fromordinal(fin.toordinal() - 1)
    return date(ctx.ejercicio, 1, 1), date(ctx.ejercicio, 12, 31)


def _fuera_de_periodo(fecha: date | None, ctx: Contexto) -> bool:
    rango = _rango_periodo(ctx)
    return bool(fecha and rango and not (rango[0] <= fecha <= rango[1]))


def _validar_cuenta(cuenta: str | None, reg: dict, ctx: Contexto, obs: list[Obs], con_movimiento=True):
    if not cuenta:
        return
    if not cuenta.isdigit() or cuenta[0] == "0":
        obs.append(Obs("CTA004", fila=reg["_fila"], cuenta=cuenta, valor=cuenta))
    if con_movimiento and any(cuenta.startswith(p) for p in ctx.prefijos_sin_movimiento):
        obs.append(Obs("CTA003", fila=reg["_fila"], cuenta=cuenta, asiento=_asiento(reg),
                       mensaje=f"Movimiento en la cuenta {cuenta}, restringida por la política de la empresa."))
    if ctx.plan is None:
        return
    c = ctx.plan.get(cuenta)
    if c is None:
        obs.append(Obs("CTA001", fila=reg["_fila"], cuenta=cuenta, asiento=_asiento(reg), valor=cuenta))
        return
    if not c.activa:
        obs.append(Obs("CTA002", fila=reg["_fila"], cuenta=cuenta, asiento=_asiento(reg)))
    if con_movimiento and not c.admite_movimiento:
        obs.append(Obs("CTA003", fila=reg["_fila"], cuenta=cuenta, asiento=_asiento(reg)))


def _validar_tc(reg: dict, fecha: date | None, ctx: Contexto, obs: list[Obs], mn: Decimal, me: Decimal):
    moneda = reg.get("moneda")
    if moneda in (None, "PEN"):
        if moneda == "PEN" and reg.get("tipo_cambio") not in (None, CERO, Decimal("1")) and not me:
            return
        return
    tc = reg.get("tipo_cambio")
    if tc is None or tc <= 0:
        if me or mn:
            obs.append(Obs("TC003", severidad="MEDIO" if tc is None else None, fila=reg["_fila"],
                           cuenta=reg.get("cuenta"), asiento=_asiento(reg), documento=_documento(reg),
                           campo="tipo_cambio", valor=str(tc) if tc is not None else "(vacío)"))
        return
    if me and mn:
        diferencia = abs(mn - (me * tc).quantize(Decimal("0.01")))
        if diferencia > max(ctx.tolerancia_conversion, mn * Decimal("0.001")):
            obs.append(Obs("TC001", fila=reg["_fila"], cuenta=reg.get("cuenta"), asiento=_asiento(reg),
                           documento=_documento(reg), campo="tipo_cambio",
                           valor=f"MN {mn} vs ME {me} × {tc}",
                           mensaje=f"Conversión inconsistente: MN {mn} ≠ ME {me} × TC {tc} (dif. {diferencia})."))
    oficial = ctx.tipos_cambio.get((fecha, moneda)) if fecha else None
    if oficial and min(abs(tc - oficial[0]), abs(tc - oficial[1])) > ctx.tolerancia_tc:
        obs.append(Obs("TC002", fila=reg["_fila"], cuenta=reg.get("cuenta"), asiento=_asiento(reg),
                       documento=_documento(reg), campo="tipo_cambio", valor=str(tc),
                       mensaje=f"TC {tc} distinto al registrado el {fecha:%d/%m/%Y} "
                               f"(compra {oficial[0]}, venta {oficial[1]})."))


def _validar_tercero(reg, rol, ctx, obs):
    doc = reg.get("documento_tercero")
    if not doc:
        return
    tdi = (reg.get("tipo_documento_identidad") or "").lstrip("0") or reg.get("tipo_documento_identidad")
    if (tdi == "6" or (tdi is None and len(doc) == 11 and doc.isdigit())) and not ruc_valido(doc):
        obs.append(Obs("TER001", fila=reg["_fila"], documento=_documento(reg), campo="documento_tercero", valor=doc,
                       mensaje=f"RUC {doc} inválido (longitud o dígito verificador)."))
    elif tdi == "1" and not (doc.isdigit() and len(doc) == 8):
        obs.append(Obs("TER001", fila=reg["_fila"], documento=_documento(reg), campo="documento_tercero", valor=doc,
                       mensaje=f"DNI {doc} inválido (debe tener 8 dígitos)."))
    if rol and rol in ctx.terceros and doc not in ctx.terceros[rol]:
        obs.append(Obs("TER002", fila=reg["_fila"], documento=_documento(reg), valor=doc,
                       mensaje=f"{'Proveedor' if rol == 'PROVEEDOR' else 'Cliente'} {doc} no registrado en el maestro."))


def _validar_totales_archivo(ex: Extraccion, ctx: Contexto, obs: list[Obs]):
    if not ex.total_archivo:
        return
    campo_d, campo_h = CAMPOS_IMPORTE_TOTAL.get(ctx.tipo, (None, None))
    if not campo_d:
        return
    procesado_d = sum((r.get(campo_d) or CERO for r in ex.registros), CERO)
    procesado_h = sum((r.get(campo_h) or CERO for r in ex.registros), CERO) if campo_h else None
    archivo_d, archivo_h = ex.total_archivo
    difs = []
    if archivo_d is not None and abs(archivo_d - procesado_d) > ctx.tolerancia:
        difs.append(f"{CAMPOS[campo_d].etiqueta}: archivo {archivo_d} vs procesado {procesado_d}")
    if campo_h and archivo_h is not None and abs(archivo_h - procesado_h) > ctx.tolerancia:
        difs.append(f"{CAMPOS[campo_h].etiqueta}: archivo {archivo_h} vs procesado {procesado_h}")
    if difs:
        obs.append(Obs("TOT001", mensaje="Diferencia entre el total del archivo y lo procesado — " + "; ".join(difs) + "."))


# ===================================================================== libros diario / mayor / saldos iniciales
def _clave_asiento(r: dict) -> tuple | None:
    if not r.get("numero_asiento"):
        return None
    return (r.get("ejercicio"), r.get("periodo"), r.get("subdiario") or "", r["numero_asiento"])


def _validar_lineas(db, regs, ctx: Contexto, obs):
    tipo = ctx.tipo
    if ctx.plan is None:
        obs.append(Obs("CTA000"))
    usa_cc = any(r.get("centro_costo") for r in regs)
    if usa_cc and ctx.centros is None:
        obs.append(Obs("CC000"))
    sev_pd = "CRITICO" if ctx.importacion_completa else "ALTO"

    for r in regs:
        if tipo != "SALDOS_INICIALES" and _fuera_de_periodo(r.get("fecha_contable"), ctx):
            obs.append(Obs("FEC002", fila=r["_fila"], cuenta=r.get("cuenta"), asiento=_asiento(r),
                           campo="fecha_contable", valor=f"{r['fecha_contable']:%d/%m/%Y}"))
        if r.get("moneda") is None:
            obs.append(Obs("MON002", fila=r["_fila"], cuenta=r.get("cuenta"), asiento=_asiento(r)))
            r["moneda"] = "USD"
        mn = r["debe_mn"] + r["haber_mn"]
        me = r["debe_me"] + r["haber_me"]
        _validar_tc(r, r.get("fecha_contable") or r.get("fecha_emision"), ctx, obs, mn, me)
        _validar_cuenta(r.get("cuenta"), r, ctx, obs)
        cc = r.get("centro_costo")
        if cc and ctx.centros is not None and cc not in ctx.centros:
            obs.append(Obs("CC001", fila=r["_fila"], cuenta=r.get("cuenta"), asiento=_asiento(r), valor=cc))
        if not cc and ctx.plan and (c := ctx.plan.get(r.get("cuenta") or "")) and c.requiere_centro_costo:
            obs.append(Obs("CC002", fila=r["_fila"], cuenta=r.get("cuenta"), asiento=_asiento(r)))
        if r.get("fecha_vencimiento") and r.get("fecha_emision") and r["fecha_vencimiento"] < r["fecha_emision"]:
            obs.append(Obs("FEC003", fila=r["_fila"], cuenta=r.get("cuenta"), documento=_documento(r)))

    # Partida doble por asiento completo (empresa · ejercicio · periodo · subdiario · número)
    if tipo == "DIARIO" or (tipo == "MAYOR" and ctx.importacion_completa):
        asientos: dict[tuple, list[dict]] = defaultdict(list)
        for r in regs:
            k = _clave_asiento(r)
            if k:
                asientos[k].append(r)
        for k, lineas in asientos.items():
            d = sum((x["debe_mn"] for x in lineas), CERO)
            h = sum((x["haber_mn"] for x in lineas), CERO)
            if abs(d - h) > ctx.tolerancia:
                obs.append(Obs("PD001", severidad=sev_pd, fila=lineas[0]["_fila"], asiento=_asiento(lineas[0]),
                               valor=f"{d} / {h}",
                               mensaje=f"Asiento {_asiento(lineas[0])} (periodo {k[1]}) descuadrado en MN: "
                                       f"debe {d} · haber {h} · diferencia {d - h}."))
            dme = sum((x["debe_me"] for x in lineas), CERO)
            hme = sum((x["haber_me"] for x in lineas), CERO)
            if (dme or hme) and all(x["debe_me"] or x["haber_me"] for x in lineas) and abs(dme - hme) > ctx.tolerancia:
                obs.append(Obs("PD002", fila=lineas[0]["_fila"], asiento=_asiento(lineas[0]), valor=f"{dme} / {hme}",
                               mensaje=f"Asiento {_asiento(lineas[0])} descuadrado en ME: debe {dme} · haber {hme}."))
        _duplicados_documento(regs, obs)
        _duplicados_en_base(db, regs, ctx, obs)

    if ctx.importacion_completa and tipo in ("DIARIO", "MAYOR", "SALDOS_INICIALES"):
        d = sum((x["debe_mn"] for x in regs), CERO)
        h = sum((x["haber_mn"] for x in regs), CERO)
        if abs(d - h) > ctx.tolerancia:
            obs.append(Obs("PD003", mensaje=f"Totales de la importación descuadrados: debe {d} · haber {h} · "
                                            f"diferencia {d - h}.", valor=f"{d - h}"))

    if tipo == "SALDOS_INICIALES":
        saldos = defaultdict(lambda: CERO)
        filas = {}
        for r in regs:
            saldos[r["cuenta"]] += r["debe_mn"] - r["haber_mn"]
            filas.setdefault(r["cuenta"], r["_fila"])
        for cuenta, saldo in saldos.items():
            _naturaleza(cuenta, saldo, filas[cuenta], ctx, obs)

    if tipo == "DIARIO" or (tipo == "MAYOR" and ctx.importacion_completa):
        obs.extend(validar_analitica(regs, ctx.analitica, _clave_asiento))
    elif tipo == "MAYOR":
        obs.append(Obs("DES007", mensaje="Las reglas de clases 6, 7 y 9 no se aplican a una importación parcial del mayor."))


def _duplicados_documento(regs, obs):
    """Un documento con varias líneas en el MISMO asiento es legítimo; se observa solo si la misma
    combinación documento + cuenta + lado + importe aparece en asientos distintos."""
    vistos: dict[tuple, str] = {}
    for r in regs:
        if not r.get("numero_documento"):
            continue
        lado = "D" if r["debe_mn"] else "H"
        k = (r.get("documento_tercero"), r.get("tipo_documento"), r.get("serie"), r["numero_documento"],
             r.get("cuenta"), lado, r["debe_mn"] or r["haber_mn"])
        asiento = _asiento(r) or f"fila {r['_fila']}"
        if k in vistos and vistos[k] != asiento:
            obs.append(Obs("DUP001", fila=r["_fila"], cuenta=r.get("cuenta"), asiento=asiento, documento=_documento(r),
                           mensaje=f"El documento {_documento(r)} ya figura en el asiento {vistos[k]} con la misma "
                                   "cuenta, lado e importe."))
        else:
            vistos.setdefault(k, asiento)


def _duplicados_en_base(db, regs, ctx: Contexto, obs):
    numeros = {r["numero_documento"] for r in regs if r.get("numero_documento")}
    if not numeros:
        return
    existentes = set()
    lista = list(numeros)
    for i in range(0, len(lista), 500):
        q = (select(LineaDiario.documento_tercero, LineaDiario.serie, LineaDiario.numero_documento,
                    LineaDiario.cuenta, LineaDiario.debe_mn, LineaDiario.haber_mn, LineaDiario.lote_id)
             .join(LoteContable, LoteContable.id == LineaDiario.lote_id)
             .where(LineaDiario.empresa_id == ctx.empresa_id, LoteContable.estado == "ACTIVO",
                    LoteContable.tipo_informacion == ctx.tipo, LineaDiario.numero_documento.in_(lista[i:i + 500])))
        for t, s, n, c, d, h, lote in db.execute(q):
            existentes.add((t, s, n, c, d, h))
    for r in regs:
        if r.get("numero_documento") and (r.get("documento_tercero"), r.get("serie"), r["numero_documento"],
                                           r.get("cuenta"), r["debe_mn"], r["haber_mn"]) in existentes:
            obs.append(Obs("DUP002", fila=r["_fila"], cuenta=r.get("cuenta"), asiento=_asiento(r),
                           documento=_documento(r)))


# ===================================================================== naturaleza
def naturaleza_pcge(cuenta: str) -> str | None:
    """Naturaleza esperada según el PCGE. Las cuentas correctoras de activo (19, 29, 39) son acreedoras."""
    if not cuenta or not cuenta[0].isdigit():
        return None
    if cuenta[:2] in ("19", "29", "39"):
        return "A"
    clase = cuenta[0]
    if clase in "12369":
        return "D"
    if clase in "457":
        return "A" if cuenta[:2] != "59" else None
    return None  # clase 8 (saldos intermediarios) y 0 (orden): depende del resultado


def _naturaleza(cuenta, saldo: Decimal, fila, ctx: Contexto, obs):
    if not saldo:
        return
    nat = None
    if ctx.plan and (c := ctx.plan.get(cuenta)) and c.naturaleza:
        nat = c.naturaleza
    nat = nat or naturaleza_pcge(cuenta)
    if (nat == "D" and saldo < 0) or (nat == "A" and saldo > 0):
        sev = "ALTO" if abs(saldo) >= ctx.materialidad else "MEDIO"
        obs.append(Obs("NAT001", severidad=sev, fila=fila, cuenta=cuenta, valor=str(saldo),
                       mensaje=f"La cuenta {cuenta} es de naturaleza {'deudora' if nat == 'D' else 'acreedora'} y "
                               f"presenta saldo {'acreedor' if saldo < 0 else 'deudor'} de {abs(saldo)}."))


# ===================================================================== balance de comprobación
def _validar_balance(db, regs, ctx: Contexto, obs):
    if ctx.plan is None:
        obs.append(Obs("CTA000"))
    codigos = [r["cuenta"] for r in regs if r.get("cuenta")]
    conteo = defaultdict(int)
    for c in codigos:
        conteo[c] += 1
    unicos = set(codigos)
    hojas = cuentas_de_detalle(regs, ctx.tolerancia)
    vistos = set()
    for r in regs:
        c = r["cuenta"]
        if conteo[c] > 1 and c in vistos:
            obs.append(Obs("DUP004", fila=r["_fila"], cuenta=c, mensaje=f"La cuenta {c} aparece más de una vez."))
        vistos.add(c)
        si = r["saldo_inicial_debe"] - r["saldo_inicial_haber"]
        mov = r["movimiento_debe"] - r["movimiento_haber"]
        sf = r["saldo_final_debe"] - r["saldo_final_haber"]
        informa_sf = any(r.get(k) for k in ("saldo_final_debe", "saldo_final_haber"))
        if informa_sf and abs(si + mov - sf) > ctx.tolerancia:
            obs.append(Obs("SAL001", fila=r["_fila"], cuenta=c, valor=f"{si + mov} vs {sf}",
                           mensaje=f"Cuenta {c}: saldo inicial {si} + movimientos {mov} = {si + mov}, "
                                   f"pero el saldo final informado es {sf}."))
        if c in hojas:
            _naturaleza(c, sf if informa_sf else si + mov, r["_fila"], ctx, obs)
            _validar_cuenta(c, r, ctx, obs, con_movimiento=bool(r["movimiento_debe"] or r["movimiento_haber"]))

    hojas_regs = [r for r in regs if r["cuenta"] in hojas]
    sev = "CRITICO" if ctx.importacion_completa else "ALTO"
    for k_d, k_h, nombre in (("saldo_inicial_debe", "saldo_inicial_haber", "saldos iniciales"),
                             ("movimiento_debe", "movimiento_haber", "movimientos"),
                             ("saldo_final_debe", "saldo_final_haber", "saldos finales")):
        d = sum((r[k_d] for r in hojas_regs), CERO)
        h = sum((r[k_h] for r in hojas_regs), CERO)
        if abs(d - h) > ctx.tolerancia:
            obs.append(Obs("PD003", severidad=sev, mensaje=f"Balance descuadrado en {nombre}: deudor {d} · acreedor {h} · "
                                                         f"diferencia {d - h} (cuentas de último nivel).",
                           valor=str(d - h)))

    # Cruce con el libro diario importado del mismo periodo
    if ctx.ejercicio:
        q = (select(LineaDiario.cuenta, func.sum(LineaDiario.debe_mn), func.sum(LineaDiario.haber_mn))
             .join(LoteContable, LoteContable.id == LineaDiario.lote_id)
             .where(LineaDiario.empresa_id == ctx.empresa_id, LoteContable.estado == "ACTIVO",
                    LoteContable.tipo_informacion == "DIARIO", LineaDiario.ejercicio == ctx.ejercicio)
             .group_by(LineaDiario.cuenta))
        if ctx.periodo and 1 <= ctx.periodo <= 12:
            q = q.where(LineaDiario.periodo == ctx.periodo)
        diario = {c: (Decimal(str(d or 0)), Decimal(str(h or 0))) for c, d, h in db.execute(q)}
        if diario:
            for r in hojas_regs:
                d, h = diario.get(r["cuenta"], (CERO, CERO))
                if abs(d - r["movimiento_debe"]) > ctx.tolerancia or abs(h - r["movimiento_haber"]) > ctx.tolerancia:
                    obs.append(Obs("SAL002", fila=r["_fila"], cuenta=r["cuenta"],
                                   valor=f"{r['movimiento_debe']}/{r['movimiento_haber']} vs {d}/{h}",
                                   mensaje=f"Cuenta {r['cuenta']}: movimientos del balance "
                                           f"{r['movimiento_debe']} / {r['movimiento_haber']} y del diario {d} / {h}."))
            faltantes = set(diario) - hojas
            for c in sorted(faltantes)[:50]:
                if not any(c.startswith(x) or x.startswith(c) for x in unicos):
                    obs.append(Obs("SAL002", cuenta=c, mensaje=f"La cuenta {c} tiene movimientos en el diario pero no "
                                                               "figura en el balance."))
        # Cruce con saldos iniciales (solo tiene sentido para el primer periodo o el balance anual)
        if ctx.periodo in (None, 0, 1):
            q = (select(SaldoCuenta.cuenta, func.sum(SaldoCuenta.saldo_inicial_debe - SaldoCuenta.saldo_inicial_haber))
                 .join(LoteContable, LoteContable.id == SaldoCuenta.lote_id)
                 .where(SaldoCuenta.empresa_id == ctx.empresa_id, LoteContable.estado == "ACTIVO",
                        SaldoCuenta.tipo == "SALDOS_INICIALES", SaldoCuenta.ejercicio == ctx.ejercicio)
                 .group_by(SaldoCuenta.cuenta))
            iniciales = {c: Decimal(str(v or 0)) for c, v in db.execute(q)}
            if iniciales:
                for r in hojas_regs:
                    si = r["saldo_inicial_debe"] - r["saldo_inicial_haber"]
                    esperado = iniciales.get(r["cuenta"], CERO)
                    if abs(si - esperado) > ctx.tolerancia:
                        obs.append(Obs("SAL003", fila=r["_fila"], cuenta=r["cuenta"], valor=f"{si} vs {esperado}",
                                       mensaje=f"Cuenta {r['cuenta']}: saldo inicial del balance {si}; "
                                               f"saldos iniciales importados {esperado}."))


def cuentas_de_detalle(regs: list[dict], tolerancia: Decimal) -> set[str]:
    """Distingue filas de detalle de filas de resumen (niveles superiores del balance).

    Una cuenta es de resumen solo si sus importes coinciden con la suma de sus cuentas de detalle;
    así, una cuenta de título con movimiento propio (error de registro) no se descarta.
    """
    def valores(r):
        return (r["saldo_inicial_debe"] - r["saldo_inicial_haber"], r["movimiento_debe"], r["movimiento_haber"],
                r["saldo_final_debe"] - r["saldo_final_haber"])
    por_codigo = {}
    for r in regs:
        if r.get("cuenta"):
            v = valores(r)
            previo = por_codigo.get(r["cuenta"])
            por_codigo[r["cuenta"]] = tuple(a + b for a, b in zip(previo, v)) if previo else v
    detalle: set[str] = set()
    for c in sorted(por_codigo, key=len, reverse=True):
        hijos = [d for d in detalle if d != c and d.startswith(c)]
        if hijos:
            suma = tuple(sum((por_codigo[h][i] for h in hijos), CERO) for i in range(4))
            if all(abs(a - b) <= tolerancia for a, b in zip(por_codigo[c], suma)):
                continue  # fila de resumen
        detalle.add(c)
    return detalle


# ===================================================================== compras / ventas
def _validar_registro(db, regs, ctx: Contexto, obs):
    rol = "PROVEEDOR" if ctx.tipo == "COMPRAS" else "CLIENTE"
    vistos: dict[tuple, int] = {}
    for r in regs:
        doc = _documento(r)
        if _fuera_de_periodo(r.get("fecha_emision"), ctx):
            # En compras es válido anotar comprobantes de hasta 12 meses anteriores.
            obs.append(Obs("FEC002", severidad="INFORMATIVO" if ctx.tipo == "COMPRAS" else None, fila=r["_fila"],
                           documento=doc, campo="fecha_emision", valor=f"{r['fecha_emision']:%d/%m/%Y}",
                           mensaje=("Comprobante emitido fuera del periodo (admisible si se anota dentro del plazo "
                                    "legal)." if ctx.tipo == "COMPRAS" else None)))
        if r.get("fecha_vencimiento") and r.get("fecha_emision") and r["fecha_vencimiento"] < r["fecha_emision"]:
            obs.append(Obs("FEC003", fila=r["_fila"], documento=doc))
        partes = [r.get(k) or CERO for k in ("base_imponible", "igv", "no_gravado", "otros_tributos")]
        total = r.get("total") or CERO
        if any(partes) and abs(sum(partes, CERO) - total) > Decimal("0.10"):
            obs.append(Obs("REG001", fila=r["_fila"], documento=doc, valor=f"{sum(partes, CERO)} vs {total}",
                           mensaje=f"Comprobante {doc}: suma de componentes {sum(partes, CERO)} ≠ total {total}."))
        base, igv = r.get("base_imponible") or CERO, r.get("igv") or CERO
        if base and igv and not any(abs(base * t - igv) <= max(Decimal("1.00"), base * t / 100) for t in TASAS_IGV):
            obs.append(Obs("REG002", fila=r["_fila"], documento=doc, valor=f"{(igv / base * 100):.2f} %",
                           mensaje=f"Comprobante {doc}: IGV {igv} equivale a {(igv / base * 100):.2f} % de la base."))
        if r.get("moneda") not in (None, "PEN"):
            _validar_tc(r, r.get("fecha_emision"), ctx, obs, CERO, CERO)
        _validar_tercero(r, rol, ctx, obs)
        if r.get("cuenta"):
            _validar_cuenta(r["cuenta"], r, ctx, obs)
        k = (r.get("tipo_documento"), r.get("serie"), r.get("numero_documento"), r.get("documento_tercero"))
        if k in vistos:
            obs.append(Obs("DUP001", fila=r["_fila"], documento=doc,
                           mensaje=f"El comprobante {doc} del tercero {r.get('documento_tercero')} se repite "
                                   f"(fila {vistos[k]})."))
        else:
            vistos[k] = r["_fila"]
    numeros = list({r["numero_documento"] for r in regs if r.get("numero_documento")})
    existentes = set()
    for i in range(0, len(numeros), 500):
        q = (select(DocumentoRegistro.tipo_documento, DocumentoRegistro.serie, DocumentoRegistro.numero,
                    DocumentoRegistro.documento_tercero)
             .join(LoteContable, LoteContable.id == DocumentoRegistro.lote_id)
             .where(DocumentoRegistro.empresa_id == ctx.empresa_id, DocumentoRegistro.tipo == ctx.tipo,
                    LoteContable.estado == "ACTIVO", DocumentoRegistro.numero.in_(numeros[i:i + 500])))
        existentes.update(tuple(x) for x in db.execute(q))
    for r in regs:
        if (r.get("tipo_documento"), r.get("serie"), r.get("numero_documento"), r.get("documento_tercero")) in existentes:
            obs.append(Obs("DUP002", fila=r["_fila"], documento=_documento(r)))


def _validar_cartera(regs, ctx, obs):
    rol = "CLIENTE" if ctx.tipo == "CXC" else "PROVEEDOR"
    vistos = {}
    for r in regs:
        doc = _documento(r)
        if r.get("total") and r.get("saldo_pendiente") and abs(r["saldo_pendiente"]) > abs(r["total"]) + ctx.tolerancia:
            obs.append(Obs("CAR001", fila=r["_fila"], documento=doc, valor=f"{r['saldo_pendiente']} > {r['total']}"))
        if r.get("fecha_vencimiento") and r.get("fecha_emision") and r["fecha_vencimiento"] < r["fecha_emision"]:
            obs.append(Obs("FEC003", fila=r["_fila"], documento=doc))
        if r.get("moneda") not in (None, "PEN") and r.get("tipo_cambio") is not None and r["tipo_cambio"] <= 0:
            obs.append(Obs("TC003", fila=r["_fila"], documento=doc))
        _validar_tercero(r, rol, ctx, obs)
        if r.get("cuenta"):
            _validar_cuenta(r["cuenta"], r, ctx, obs)
        k = (r.get("documento_tercero"), r.get("tipo_documento"), r.get("serie"), r.get("numero_documento"))
        if k in vistos:
            obs.append(Obs("DUP001", fila=r["_fila"], documento=doc,
                           mensaje=f"El documento {doc} se repite (fila {vistos[k]})."))
        else:
            vistos[k] = r["_fila"]


# ===================================================================== maestros
def _validar_plan(regs, ctx, obs):
    codigos = {}
    for r in regs:
        c = r.get("cuenta")
        if c in codigos:
            obs.append(Obs("CTA005", fila=r["_fila"], cuenta=c, mensaje=f"La cuenta {c} se repite (fila {codigos[c]})."))
        else:
            codigos[c] = r["_fila"]
        if c and (not c.isdigit() or c[0] == "0"):
            obs.append(Obs("CTA004", fila=r["_fila"], cuenta=c, valor=c))
        nat = (r.get("naturaleza") or "").strip().upper()
        if nat and nat[:1] not in ("D", "A", "C"):
            obs.append(Obs("EST006", fila=r["_fila"], cuenta=c, campo="naturaleza", valor=nat,
                           mensaje="Naturaleza no reconocida (use D = deudora o A = acreedora)."))
    existentes = set(ctx.plan or {}) | set(codigos)
    for r in regs:
        for k in ("cuenta_destino_debe", "cuenta_destino_haber"):
            dest = r.get(k)
            if dest and dest not in existentes:
                obs.append(Obs("CTA006", fila=r["_fila"], cuenta=r.get("cuenta"), campo=k, valor=dest,
                               mensaje=f"La cuenta {r.get('cuenta')} tiene destino {dest}, que no existe en el plan."))


def _validar_terceros(regs, obs):
    vistos = {}
    for r in regs:
        doc = r.get("documento_tercero")
        if doc in vistos:
            obs.append(Obs("DUP004", fila=r["_fila"], valor=doc, mensaje=f"El documento {doc} se repite (fila {vistos[doc]})."))
        else:
            vistos[doc] = r["_fila"]
        _validar_tercero(r, None, Contexto(0, "", None, None, False, ""), obs)


def _validar_centros(regs, ctx, obs):
    vistos = {}
    for r in regs:
        cc = r.get("centro_costo")
        if cc in vistos:
            obs.append(Obs("DUP004", fila=r["_fila"], valor=cc, mensaje=f"El centro de costo {cc} se repite."))
        else:
            vistos[cc] = r["_fila"]
        dest = r.get("cuenta_destino")
        if dest and ctx.plan is not None and dest not in ctx.plan:
            obs.append(Obs("CTA006", fila=r["_fila"], cuenta=dest, valor=dest,
                           mensaje=f"El centro {cc} tiene como destino la cuenta {dest}, que no existe en el plan."))


def _validar_tipos_cambio(regs, obs):
    vistos = {}
    anterior: dict[str, tuple] = {}
    for r in sorted(regs, key=lambda x: (x.get("moneda") or "USD", x.get("fecha") or date.min)):
        r["moneda"] = r.get("moneda") or "USD"
        k = (r.get("fecha"), r["moneda"])
        if k in vistos:
            obs.append(Obs("DUP004", fila=r["_fila"], valor=str(k[0]), mensaje=f"Fecha {k[0]} repetida para {k[1]}."))
            continue
        vistos[k] = r["_fila"]
        compra, venta = r.get("compra"), r.get("venta")
        for nombre, v in (("compra", compra), ("venta", venta)):
            if v is not None and v <= 0:
                obs.append(Obs("TC003", fila=r["_fila"], campo=nombre, valor=str(v)))
        if compra and venta and compra > venta:
            obs.append(Obs("TC005", fila=r["_fila"], valor=f"{compra} > {venta}"))
        ref = venta or compra
        prev = anterior.get(r["moneda"])
        if ref and prev and prev[1] and abs(ref - prev[1]) / prev[1] > Decimal("0.05"):
            obs.append(Obs("TC004", fila=r["_fila"], valor=f"{prev[1]} → {ref}",
                           mensaje=f"El tipo de cambio pasa de {prev[1]} ({prev[0]}) a {ref} ({r.get('fecha')})."))
        if ref:
            anterior[r["moneda"]] = (r.get("fecha"), ref)
