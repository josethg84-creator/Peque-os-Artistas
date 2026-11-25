"""Partidas abiertas: configuración, construcción idempotente desde el libro, composición histórica
a cualquier fecha de corte, antigüedad real y conciliación con el saldo contable.

Alcance temporal: desde el `ejercicio_inicio` (configurable; por defecto, el primer ejercicio con
libro diario) hasta la fecha de corte. La apertura se toma SOLO del ejercicio de inicio (detalle de
partidas abiertas importadas como CxC/CxP del periodo 00 y, por diferencia, un saldo consolidado
«pendiente de desagregación»). En los ejercicios siguientes la continuidad viene de los propios
movimientos, así que sus aperturas (saldos iniciales o asiento del periodo 00) se ignoran.

Una partida es VIGENTE a una fecha de corte si su fecha contable es ≤ corte; su saldo pendiente a
esa fecha descuenta solo las aplicaciones APROBADAS con fecha efectiva ≤ corte y no revertidas.
"""
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, insert, or_, select, update
from sqlalchemy.orm import Session

from app.analisis import saldos as saldos_f
from app.compensacion.clasificacion import clasificar, naturaleza
from app.models import (Aplicacion, DocumentoRegistro, LineaDiario, LoteContable, PartidaAbierta, PartidaFuente,
                        ReglaCompensacion, SaldoCuenta)

CERO = Decimal("0")
C2 = Decimal("0.01")

CUENTAS_DEFECTO = {
    "12": ("Cuentas por cobrar comerciales – terceros", ["122"]),
    "13": ("Cuentas por cobrar comerciales – relacionadas", ["132"]),
    "14": ("Cuentas por cobrar al personal, accionistas y directores", ["1413"]),
    "16": ("Cuentas por cobrar diversas – terceros", []),
    "17": ("Cuentas por cobrar diversas – relacionadas", []),
    "40": ("Tributos y aportes por pagar", []),
    "41": ("Remuneraciones y participaciones por pagar", []),
    "42": ("Cuentas por pagar comerciales – terceros", ["422"]),
    "43": ("Cuentas por pagar comerciales – relacionadas", ["432"]),
    "44": ("Cuentas por pagar a accionistas y directores", []),
    "45": ("Obligaciones financieras", []),
    "46": ("Cuentas por pagar diversas – terceros", []),
    "47": ("Cuentas por pagar diversas – relacionadas", []),
}
PARAMETROS_CUENTA = {
    "activa": True, "ventana_dias": 365, "max_combinacion": 4, "max_candidatos": 20, "max_nodos": 20000,
    "tolerancia": "0.00", "fifo": False, "autoaprobar": False, "umbral_auto": 95, "anticipos": [],
    "subdiarios_pago": [], "pesos": {"tercero": 20, "documento": 30, "moneda": 10, "importe": 15, "referencias": 10,
                                     "fecha": 10, "cuenta": 5}, "penalizacion_ambiguedad": 25,
}
PARAMETROS_GENERALES = {"separar_proponer_aprobar": True, "ejercicio_inicio": None, "dias_vencimiento_defecto": None}


def sembrar(db: Session, empresa_id: int) -> None:
    existentes = {(r.tipo, r.codigo) for r in db.scalars(select(ReglaCompensacion).where(ReglaCompensacion.empresa_id == empresa_id))}
    cambios = False
    if ("GENERAL", "EMPRESA") not in existentes:
        db.add(ReglaCompensacion(empresa_id=empresa_id, tipo="GENERAL", codigo="EMPRESA", nombre="Políticas generales",
                                 parametros=json.dumps(PARAMETROS_GENERALES)))
        cambios = True
    for c, (nombre, anticipos) in CUENTAS_DEFECTO.items():
        if ("CUENTA", c) not in existentes:
            db.add(ReglaCompensacion(empresa_id=empresa_id, tipo="CUENTA", codigo=c, nombre=f"{c} {nombre}",
                                     parametros=json.dumps({**PARAMETROS_CUENTA, "anticipos": anticipos})))
            cambios = True
    if cambios:
        db.commit()


@dataclass
class Config:
    cuentas: dict[str, dict]          # prefijo → parámetros
    reglas: dict[str, dict]           # prefijo → ReglaCompensacion (versión)
    general: dict
    entre_cuentas: list[dict]
    conversion: list[dict]
    tasas: dict[str, list[dict]]      # DETRACCION/RETENCION/PERCEPCION → reglas

    def regla_de(self, cuenta: str) -> str | None:
        cands = [p for p in self.cuentas if cuenta.startswith(p) and self.cuentas[p].get("activa", True)]
        return max(cands, key=len) if cands else None

    def anticipos(self) -> list[str]:
        return [a for p in self.cuentas.values() for a in p.get("anticipos", [])]

    def subdiarios_pago(self) -> list[str]:
        return [a for p in self.cuentas.values() for a in p.get("subdiarios_pago", [])]


def _vigente(r: ReglaCompensacion, fecha: date) -> bool:
    return r.activa and (r.vigente_desde is None or r.vigente_desde <= fecha) and (r.vigente_hasta is None or r.vigente_hasta >= fecha)


def configuracion(db: Session, empresa_id: int, fecha: date | None = None) -> Config:
    sembrar(db, empresa_id)
    fecha = fecha or date.today()
    cuentas, reglas, entre, conv, tasas, general = {}, {}, [], [], defaultdict(list), dict(PARAMETROS_GENERALES)
    for r in db.scalars(select(ReglaCompensacion).where(ReglaCompensacion.empresa_id == empresa_id)):
        p = json.loads(r.parametros or "{}")
        if r.tipo == "GENERAL":
            general.update(p)
        elif not _vigente(r, fecha):
            continue
        elif r.tipo == "CUENTA":
            cuentas[r.codigo] = {**PARAMETROS_CUENTA, **p}
            reglas[r.codigo] = {"id": r.id, "version": r.version, "nombre": r.nombre}
        elif r.tipo == "ENTRE_CUENTAS":
            entre.append({**p, "id": r.id, "codigo": r.codigo, "version": r.version, "sustento": r.sustento})
        elif r.tipo == "CONVERSION_MONEDA":
            conv.append({**p, "id": r.id, "codigo": r.codigo})
        elif r.tipo in ("DETRACCION", "RETENCION", "PERCEPCION"):
            tasas[r.tipo].append({**p, "id": r.id, "codigo": r.codigo, "nombre": r.nombre,
                                  "desde": r.vigente_desde, "hasta": r.vigente_hasta})
    return Config(cuentas, reglas, general, entre, conv, dict(tasas))


def ejercicio_inicio(db: Session, empresa_id: int, cfg: Config) -> int | None:
    if cfg.general.get("ejercicio_inicio"):
        return int(cfg.general["ejercicio_inicio"])
    return db.scalar(select(func.min(LineaDiario.ejercicio)).join(LoteContable, LoteContable.id == LineaDiario.lote_id)
                     .where(LineaDiario.empresa_id == empresa_id, LoteContable.estado == "ACTIVO"))


def filtro_lineas_alcance(db: Session, empresa_id: int, inicio: int, hasta_ejercicio: int):
    """Líneas fuente del alcance: diario (o mayor) sin duplicar; periodo 00 solo en el ejercicio de
    inicio y solo si no hay saldos iniciales importados."""
    conds, aperturas = [], {}
    for ej in range(inicio, hasta_ejercicio + 1):
        f = saldos_f.fuentes(db, empresa_id, ej)
        incluir_00 = ej == inicio and f.apertura == "DIARIO_00"
        conds.append(f.filtro_lineas(0 if incluir_00 else 1, 13, incluir_apertura_diario=incluir_00))
        aperturas[ej] = f
    return or_(*conds) if conds else LineaDiario.id < 0, aperturas


# ------------------------------------------------------------------ construcción de partidas
def construir(db: Session, empresa_id: int, cfg: Config, hasta_ejercicio: int, avance=lambda p, e: None) -> dict:
    """Crea o actualiza partidas (idempotente por `clave_fuente`). Devuelve estadísticas."""
    inicio = ejercicio_inicio(db, empresa_id, cfg)
    if inicio is None:
        return {"inicio": None, "nuevas": 0, "vigentes": 0}
    prefijos = list(cfg.cuentas)
    filtro, fuentes = filtro_lineas_alcance(db, empresa_id, inicio, max(hasta_ejercicio, inicio))
    cond_cuenta = or_(*[LineaDiario.cuenta.like(f"{p}%") for p in prefijos]) if prefijos else LineaDiario.id < 0
    cols = (LineaDiario.id, LineaDiario.lote_id, LineaDiario.ejercicio, LineaDiario.periodo, LineaDiario.fecha_contable,
            LineaDiario.fecha_emision, LineaDiario.fecha_vencimiento, LineaDiario.subdiario, LineaDiario.numero_asiento,
            LineaDiario.cuenta, LineaDiario.documento_tercero, LineaDiario.razon_social, LineaDiario.tipo_documento,
            LineaDiario.serie, LineaDiario.numero_documento, LineaDiario.documento_referencia,
            LineaDiario.orden_compra_servicio, LineaDiario.proyecto, LineaDiario.centro_costo, LineaDiario.glosa,
            LineaDiario.moneda, LineaDiario.tipo_cambio, LineaDiario.debe_mn, LineaDiario.haber_mn, LineaDiario.debe_me,
            LineaDiario.haber_me, LineaDiario.codigo_detraccion, LineaDiario.constancia_detraccion, LineaDiario.retencion)
    avance(5, "Leyendo movimientos de las cuentas compensables")
    lineas = db.execute(select(*cols).where(filtro, cond_cuenta).order_by(LineaDiario.id)).all()
    # contrapartidas por asiento (para clasificar)
    claves_asiento = {(r.lote_id, r.periodo, r.subdiario or "", r.numero_asiento) for r in lineas if r.numero_asiento}
    lotes = {k[0] for k in claves_asiento}
    contra: dict[tuple, set] = defaultdict(set)
    if lotes:
        for lote, per, sub, asi, cta in db.execute(
                select(LineaDiario.lote_id, LineaDiario.periodo, LineaDiario.subdiario, LineaDiario.numero_asiento, LineaDiario.cuenta)
                .where(LineaDiario.lote_id.in_(lotes), LineaDiario.numero_asiento.is_not(None)).distinct()):
            k = (lote, per, sub or "", asi)
            if k in claves_asiento:
                contra[k].add(cta)
    avance(20, f"Agrupando {len(lineas)} movimientos en partidas")
    grupos: dict[tuple, list] = defaultdict(list)
    for r in lineas:
        neto = (r.debe_mn or CERO) - (r.haber_mn or CERO)
        neto_me = (r.debe_me or CERO) - (r.haber_me or CERO)
        if not neto and not neto_me:
            continue
        lado = "D" if (neto > 0 or (neto == 0 and neto_me > 0)) else "H"
        if r.numero_documento:
            k = (r.lote_id, r.periodo, r.subdiario or "", r.numero_asiento, r.cuenta, r.documento_tercero, r.tipo_documento,
                 r.serie, r.numero_documento, r.moneda or "PEN", lado)
        else:
            k = ("L", r.id)
        grupos[k].append(r)
    existentes = {c: (i, imp) for c, i, imp in db.execute(select(PartidaAbierta.clave_fuente, PartidaAbierta.id, PartidaAbierta.importe)
                                                          .where(PartidaAbierta.empresa_id == empresa_id))}
    nuevas, fuentes_nuevas, vistas = [], [], set()
    anticipos, sub_pago = cfg.anticipos(), cfg.subdiarios_pago()
    for k, lns in grupos.items():
        r0 = lns[0]
        clave = f"L{r0.lote_id}:{min(x.id for x in lns)}"
        vistas.add(clave)
        if clave in existentes:
            continue
        mn = abs(sum(((x.debe_mn or CERO) - (x.haber_mn or CERO) for x in lns), CERO))
        me = abs(sum(((x.debe_me or CERO) - (x.haber_me or CERO) for x in lns), CERO))
        lado = k[-1] if k[0] != "L" else ("D" if ((r0.debe_mn or CERO) - (r0.haber_mn or CERO)) > 0 or
                                          ((r0.debe_mn or CERO) == (r0.haber_mn or CERO) and (r0.debe_me or CERO) > 0) else "H")
        moneda = r0.moneda or "PEN"
        importe = me if moneda != "PEN" else mn
        es_dc = moneda != "PEN" and not me  # ajuste solo en MN (diferencia de cambio registrada)
        if es_dc:
            moneda, importe = "PEN", mn
        if not importe:
            continue
        ka = (r0.lote_id, r0.periodo, r0.subdiario or "", r0.numero_asiento)
        origen_datos = "APERTURA_DIARIO" if r0.periodo == 0 else "DIARIO"
        c = clasificar(cuenta=r0.cuenta, lado=lado, tipo_documento=r0.tipo_documento, glosa=r0.glosa, subdiario=r0.subdiario,
                       contrapartidas=contra.get(ka, set()) - {r0.cuenta}, origen_datos="DIARIO", anticipos=anticipos,
                       subdiarios_pago=sub_pago)
        clase = "DIFERENCIA_CAMBIO" if es_dc else ("SALDO_INICIAL" if origen_datos == "APERTURA_DIARIO" else c.clase)
        nuevas.append(dict(
            empresa_id=empresa_id, clave_fuente=clave, origen_datos=origen_datos, cuenta=r0.cuenta, tercero=r0.documento_tercero,
            razon_social=r0.razon_social, tipo_documento=r0.tipo_documento, serie=r0.serie, numero=r0.numero_documento,
            documento_referencia=r0.documento_referencia, orden_compra_servicio=r0.orden_compra_servicio, proyecto=r0.proyecto,
            centro_costo=r0.centro_costo, glosa=(r0.glosa or "")[:255] or None, subdiario=r0.subdiario,
            numero_asiento=r0.numero_asiento, lote_id=r0.lote_id, linea_id=min(x.id for x in lns), ejercicio=r0.ejercicio,
            periodo=r0.periodo, fecha_documento=r0.fecha_emision or r0.fecha_contable, fecha_contable=r0.fecha_contable,
            fecha_vencimiento=max((x.fecha_vencimiento for x in lns if x.fecha_vencimiento), default=None),
            lado=lado, rol=c.rol, clase=clase, clase_confianza=100 if es_dc else c.confianza,
            clase_motivo=("ajuste solo en moneda nacional" if es_dc else c.motivo)[:255], clasificacion_pendiente=False if es_dc else c.pendiente,
            moneda=moneda, tipo_cambio=r0.tipo_cambio, importe=importe.quantize(C2), importe_mn=mn.quantize(C2),
            importe_comprometido=CERO, importe_aplicado=CERO, codigo_detraccion=r0.codigo_detraccion,
            constancia_detraccion=r0.constancia_detraccion, retencion=r0.retencion, vigente=True, estado_revision="NINGUNA",
            version=1))
        fuentes_nuevas.append((clave, [(x.id, abs((x.debe_mn or CERO) - (x.haber_mn or CERO)), abs((x.debe_me or CERO) - (x.haber_me or CERO))) for x in lns]))

    avance(45, "Saldos de apertura del ejercicio de inicio")
    apert, apert_fuentes = _apertura(db, empresa_id, cfg, inicio, fuentes.get(inicio), existentes, vistas)
    nuevas += apert
    fuentes_nuevas += apert_fuentes
    for i in range(0, len(nuevas), 2000):
        db.execute(insert(PartidaAbierta), nuevas[i:i + 2000])
    ids = {c: i for c, i in db.execute(select(PartidaAbierta.clave_fuente, PartidaAbierta.id)
                                       .where(PartidaAbierta.empresa_id == empresa_id))}
    filas_f = []
    for clave, fs in fuentes_nuevas:
        tipo = "LINEA_DIARIO" if clave.startswith("L") else ("DOCUMENTO_REGISTRO" if clave.startswith("AD") else "SALDO_CUENTA")
        for fid, mn, me in fs:
            filas_f.append({"item_id": ids[clave], "empresa_id": empresa_id, "tipo_fuente": tipo, "fuente_id": fid,
                            "importe_mn": mn, "importe_me": me})
    for i in range(0, len(filas_f), 5000):
        db.execute(insert(PartidaFuente), filas_f[i:i + 5000])
    # partidas cuyas líneas ya no están vigentes (lote anulado o fuera de alcance)
    no_vistas = [i for c, (i, _) in existentes.items() if c not in vistas]
    for i in range(0, len(no_vistas), 500):
        db.execute(update(PartidaAbierta).where(PartidaAbierta.id.in_(no_vistas[i:i + 500])).values(vigente=False))
    vistas_ids = [i for c, (i, _) in existentes.items() if c in vistas]
    for i in range(0, len(vistas_ids), 500):
        db.execute(update(PartidaAbierta).where(PartidaAbierta.id.in_(vistas_ids[i:i + 500]), PartidaAbierta.vigente.is_(False))
                   .values(vigente=True))
    db.commit()
    return {"inicio": inicio, "nuevas": len(nuevas), "vigentes": len(vistas), "fuera_de_alcance": len(no_vistas)}


def _apertura(db, empresa_id, cfg: Config, inicio, fuente, existentes, vistas):
    """Partidas de apertura del ejercicio de inicio: detalle (CxC/CxP periodo 00) y saldo sin detalle por diferencia."""
    nuevas, fuentes = [], []
    if fuente is None or fuente.apertura != "SALDOS_INICIALES":
        return nuevas, fuentes
    f_ini = date(inicio, 1, 1)
    # detalle documental
    detalle_por = defaultdict(lambda: CERO)
    docs = db.scalars(select(DocumentoRegistro).join(LoteContable, LoteContable.id == DocumentoRegistro.lote_id).where(
        DocumentoRegistro.empresa_id == empresa_id, LoteContable.estado == "ACTIVO", DocumentoRegistro.tipo.in_(("CXC", "CXP")),
        DocumentoRegistro.ejercicio == inicio, DocumentoRegistro.periodo == 0)).all()
    for d in docs:
        if not d.cuenta or not cfg.regla_de(d.cuenta) or not d.saldo_pendiente:
            continue
        nat = naturaleza(d.cuenta)
        firmado = d.saldo_pendiente if d.tipo == "CXC" else -d.saldo_pendiente  # + deudor
        detalle_por[(d.cuenta, d.documento_tercero)] += firmado
        clave = f"AD{d.id}"
        vistas.add(clave)
        if clave in existentes:
            continue
        lado = "D" if firmado > 0 else "H"
        rol = "ORIGEN" if (lado == "D") == (nat == "D") else "APLICACION"
        moneda = d.moneda or "PEN"
        importe = abs(d.importe_me) if moneda != "PEN" and d.importe_me else abs(d.saldo_pendiente)
        nuevas.append(dict(
            empresa_id=empresa_id, clave_fuente=clave, origen_datos="APERTURA_DETALLE", cuenta=d.cuenta, tercero=d.documento_tercero,
            razon_social=d.razon_social, tipo_documento=d.tipo_documento, serie=d.serie, numero=d.numero, documento_referencia=None,
            orden_compra_servicio=None, proyecto=None, centro_costo=None, glosa=(d.glosa or "Partida abierta de apertura")[:255],
            subdiario=None, numero_asiento=None, lote_id=d.lote_id, linea_id=None, ejercicio=inicio, periodo=0,
            fecha_documento=d.fecha_emision or f_ini, fecha_contable=f_ini, fecha_vencimiento=d.fecha_vencimiento, lado=lado, rol=rol,
            clase="SALDO_INICIAL", clase_confianza=100, clase_motivo="Partida abierta importada (detalle de apertura)",
            clasificacion_pendiente=False, moneda=moneda, tipo_cambio=d.tipo_cambio, importe=importe, importe_mn=abs(d.saldo_pendiente),
            importe_original=d.total or None, importe_comprometido=CERO, importe_aplicado=CERO, codigo_detraccion=None,
            constancia_detraccion=None, retencion=None, referencia_historica=f"Lote {d.lote_id} · {d.tipo} · fila {d.fila_origen}",
            vigente=True, estado_revision="NINGUNA", version=1))
        fuentes.append((clave, [(d.id, abs(d.saldo_pendiente), abs(d.importe_me or CERO))]))
    # saldos consolidados (por cuenta y tercero) menos el detalle → pendiente de desagregación
    for sc_id, cuenta, tercero, sid, sih in db.execute(
            select(func.min(SaldoCuenta.id), SaldoCuenta.cuenta, SaldoCuenta.documento_tercero,
                   func.sum(SaldoCuenta.saldo_inicial_debe), func.sum(SaldoCuenta.saldo_inicial_haber))
            .where(SaldoCuenta.lote_id.in_(fuente.lotes_apertura)).group_by(SaldoCuenta.cuenta, SaldoCuenta.documento_tercero)):
        if not cfg.regla_de(cuenta):
            continue
        saldo = (Decimal(str(sid or 0)) - Decimal(str(sih or 0))).quantize(C2)
        detalle = detalle_por.pop((cuenta, tercero), CERO)
        if tercero is None:  # el detalle de otros terceros de la misma cuenta se descuenta del saldo sin tercero
            for (c, t), v in list(detalle_por.items()):
                if c == cuenta:
                    detalle += v
                    detalle_por.pop((c, t))
        resto = (saldo - detalle).quantize(C2)
        if not resto:
            continue
        clave = f"AC{sc_id}:{cuenta}:{tercero or '-'}"
        vistas.add(clave)
        if clave in existentes:
            continue
        nat = naturaleza(cuenta)
        lado = "D" if resto > 0 else "H"
        nuevas.append(dict(
            empresa_id=empresa_id, clave_fuente=clave, origen_datos="APERTURA_CONSOLIDADA", cuenta=cuenta, tercero=tercero,
            razon_social=None, tipo_documento=None, serie=None, numero=None, documento_referencia=None, orden_compra_servicio=None,
            proyecto=None, centro_costo=None, glosa="Saldo inicial pendiente de desagregación", subdiario=None, numero_asiento=None,
            lote_id=None, linea_id=None, ejercicio=inicio, periodo=0, fecha_documento=f_ini, fecha_contable=f_ini,
            fecha_vencimiento=None, lado=lado, rol="ORIGEN" if (lado == "D") == (nat == "D") else "APLICACION",
            clase="SALDO_INICIAL", clase_confianza=100, clase_motivo="Saldo de apertura sin detalle documental",
            clasificacion_pendiente=True, moneda="PEN", tipo_cambio=None, importe=abs(resto), importe_mn=abs(resto),
            importe_original=None, importe_comprometido=CERO, importe_aplicado=CERO, codigo_detraccion=None,
            constancia_detraccion=None, retencion=None, referencia_historica=f"Saldos iniciales {inicio}", vigente=True,
            estado_revision="NINGUNA", version=1))
        fuentes.append((clave, [(sc_id, abs(resto), CERO)]))
    return nuevas, fuentes


# ------------------------------------------------------------------ composición a una fecha de corte
@dataclass
class Estado:
    item: dict
    aplicado: Decimal
    propuesto: Decimal
    pendiente: Decimal
    pendiente_mn: Decimal
    cancelacion: str
    vencimiento: str
    dias: int | None
    revision: str


def aplicaciones_a(db: Session, empresa_id: int, corte: date, incluir_propuestas=False) -> dict[int, list]:
    """item → [aprobado, propuesto, aplicado_mn] a la fecha de corte (fecha efectiva ≤ corte)."""
    estados = ("APROBADA", "PROPUESTA") if incluir_propuestas else ("APROBADA",)
    out: dict[int, list] = defaultdict(lambda: [CERO, CERO, CERO])
    for col, col_mn in ((Aplicacion.origen_item_id, Aplicacion.importe_mn_origen), (Aplicacion.aplicacion_item_id, Aplicacion.importe_mn_aplicacion)):
        q = select(col, Aplicacion.estado, func.sum(func.round(Aplicacion.importe * 100)), func.sum(func.round(col_mn * 100))) \
            .where(Aplicacion.empresa_id == empresa_id, Aplicacion.estado.in_(estados), Aplicacion.fecha_efectiva <= corte) \
            .group_by(col, Aplicacion.estado)
        for item, est, cents, cents_mn in db.execute(q):
            x = out[item]
            if est == "APROBADA":
                x[0] += Decimal(int(cents)) / 100
                x[2] += Decimal(int(cents_mn)) / 100
            else:
                x[1] += Decimal(int(cents)) / 100
    return out


COLS_ITEM = [c for c in PartidaAbierta.__table__.columns]


def composicion(db: Session, empresa_id: int, corte: date, *, cuentas: list[str] | None = None, tercero: str | None = None,
                rol: str | None = None, moneda: str | None = None, solo_pendientes=False, incluir_propuestas=True,
                filtros_extra=None) -> list[Estado]:
    q = select(*COLS_ITEM).where(PartidaAbierta.empresa_id == empresa_id, PartidaAbierta.vigente.is_(True),
                                 PartidaAbierta.fecha_contable <= corte)
    if cuentas:
        q = q.where(or_(*[PartidaAbierta.cuenta.like(f"{c}%") for c in cuentas]))
    if tercero:
        q = q.where(PartidaAbierta.tercero == tercero)
    if rol:
        q = q.where(PartidaAbierta.rol == rol)
    if moneda:
        q = q.where(PartidaAbierta.moneda == moneda)
    if filtros_extra is not None:
        q = q.where(filtros_extra)
    apl = aplicaciones_a(db, empresa_id, corte, incluir_propuestas)
    revision = _revision_por_item(db, empresa_id)
    out = []
    for r in db.execute(q.order_by(PartidaAbierta.fecha_documento, PartidaAbierta.id)).mappings():
        it = dict(r)
        a = apl.get(it["id"], (CERO, CERO, CERO))
        pend = (it["importe"] - a[0]).quantize(C2)
        if solo_pendientes and pend <= 0:
            continue
        pend_mn = (it["importe_mn"] - a[2]).quantize(C2) if pend > 0 else CERO
        if pend <= 0:
            canc = "TOTAL"
        elif a[0] > 0:
            canc = "PARCIAL"
        elif it["rol"] == "APLICACION" and it["clase"] in ("ANTICIPO", "PAGO", "COBRANZA", "ENTREGA_RENDIR"):
            canc = "ANTICIPO_PENDIENTE" if it["clase"] == "ANTICIPO" else "PENDIENTE_APLICAR"
        else:
            canc = "PENDIENTE"
        if pend <= 0 or it["rol"] == "APLICACION":
            venc, dias = "NO_APLICA", None
        elif it["fecha_vencimiento"] is None:
            venc, dias = "SIN_VENCIMIENTO", None
        else:
            dias = (corte - it["fecha_vencimiento"]).days
            venc = "VENCIDO" if dias > 0 else "NO_VENCIDO"
        rev = revision.get(it["id"]) or it["estado_revision"]
        out.append(Estado(it, a[0], a[1], max(pend, CERO), max(pend_mn, CERO), canc, venc, dias, rev))
    return out


def _revision_por_item(db, empresa_id) -> dict[int, str]:
    """Estado de revisión derivado de los grupos vigentes que tocan la partida."""
    from app.models import GrupoCompensacion
    out = {}
    prioridad = {"REVERTIDA": 1, "APROBADA": 2, "PROPUESTA": 3}
    for col in (Aplicacion.origen_item_id, Aplicacion.aplicacion_item_id):
        for item, est in db.execute(select(col, GrupoCompensacion.estado).join(GrupoCompensacion, GrupoCompensacion.id == Aplicacion.grupo_id)
                                    .where(Aplicacion.empresa_id == empresa_id, GrupoCompensacion.estado.in_(tuple(prioridad)))):
            nuevo = {"PROPUESTA": "PROPUESTA", "APROBADA": "APROBADA", "REVERTIDA": "REVERTIDA"}[est]
            if prioridad[nuevo] >= prioridad.get(out.get(item), 0):
                out[item] = nuevo
    return out


def estado_dict(e: Estado) -> dict:
    d = {k: (str(v) if isinstance(v, Decimal) else v.isoformat() if hasattr(v, "isoformat") else v) for k, v in e.item.items()}
    d.update(aplicado=str(e.aplicado), propuesto=str(e.propuesto), pendiente=str(e.pendiente), pendiente_mn=str(e.pendiente_mn),
             disponible=str((e.item["importe"] - e.item["importe_comprometido"]).quantize(C2)),
             estado_cancelacion=e.cancelacion, estado_vencimiento=e.vencimiento, dias_vencido=e.dias, estado_revision=e.revision,
             documento=f"{e.item['serie']}-{e.item['numero']}" if e.item["serie"] else (e.item["numero"] or None))
    return d


def firmado(e: Estado, valor: Decimal) -> Decimal:
    """Expresa un importe con el signo contable (+ deudor / − acreedor) según el lado de la partida."""
    return valor if e.item["lado"] == "D" else -valor


# ------------------------------------------------------------------ conciliación con el saldo contable
def saldo_contable(db: Session, empresa_id: int, cfg: Config, corte: date) -> dict[str, Decimal]:
    inicio = ejercicio_inicio(db, empresa_id, cfg)
    if inicio is None:
        return {}
    filtro, fuentes = filtro_lineas_alcance(db, empresa_id, inicio, corte.year)
    prefijos = list(cfg.cuentas)
    out = defaultdict(lambda: CERO)
    q = select(LineaDiario.cuenta, saldos_f.cent(LineaDiario.debe_mn) - saldos_f.cent(LineaDiario.haber_mn)) \
        .where(filtro, LineaDiario.fecha_contable <= corte, or_(*[LineaDiario.cuenta.like(f"{p}%") for p in prefijos])) \
        .group_by(LineaDiario.cuenta)
    for c, v in db.execute(q):
        out[c] += saldos_f.dec(v)
    f = fuentes.get(inicio)
    if f is not None and f.apertura == "SALDOS_INICIALES" and corte >= date(inicio, 1, 1):
        for c, v in db.execute(select(SaldoCuenta.cuenta, saldos_f.cent(SaldoCuenta.saldo_inicial_debe) - saldos_f.cent(SaldoCuenta.saldo_inicial_haber))
                               .where(SaldoCuenta.lote_id.in_(f.lotes_apertura)).group_by(SaldoCuenta.cuenta)):
            if cfg.regla_de(c):
                out[c] += saldos_f.dec(v)
    return {c: v for c, v in out.items() if cfg.regla_de(c)}


def conciliacion(db: Session, empresa_id: int, corte: date) -> dict:
    """Saldo contable vs partidas abiertas: la diferencia se muestra explícitamente, sin ajustes."""
    cfg = configuracion(db, empresa_id, corte)
    contable = saldo_contable(db, empresa_id, cfg, corte)
    filas: dict[str, dict] = defaultdict(lambda: {k: CERO for k in ("saldo_contable", "origen", "aplicacion", "sin_detalle",
                                                                     "no_clasificado", "diferencia_cambio_aplicaciones")})
    for c, v in contable.items():
        filas[c]["saldo_contable"] = v
    for e in composicion(db, empresa_id, corte, incluir_propuestas=False):
        c = e.item["cuenta"]
        if not e.pendiente_mn:
            pass
        v = firmado(e, e.pendiente_mn)
        if e.item["origen_datos"] == "APERTURA_CONSOLIDADA":
            filas[c]["sin_detalle"] += v
        elif e.item["clasificacion_pendiente"]:
            filas[c]["no_clasificado"] += v
        elif e.item["rol"] == "ORIGEN":
            filas[c]["origen"] += v
        else:
            filas[c]["aplicacion"] += v
    # parte en MN de las aplicaciones aprobadas que no se netea (diferencias de cambio no registradas)
    from app.models import PartidaAbierta as P
    for c, lado_o, mn_o, mn_a in db.execute(
            select(P.cuenta, P.lado, func.sum(Aplicacion.importe_mn_origen), func.sum(Aplicacion.importe_mn_aplicacion))
            .join(P, P.id == Aplicacion.origen_item_id)
            .where(Aplicacion.empresa_id == empresa_id, Aplicacion.estado == "APROBADA", Aplicacion.fecha_efectiva <= corte,
                   P.vigente.is_(True)).group_by(P.cuenta, P.lado)):
        dif = Decimal(str(mn_o or 0)) - Decimal(str(mn_a or 0))
        filas[c]["diferencia_cambio_aplicaciones"] += (dif if lado_o == "D" else -dif).quantize(C2)
    out = []
    for c in sorted(filas):
        x = filas[c]
        explicado = x["origen"] + x["aplicacion"] + x["sin_detalle"] + x["no_clasificado"] + x["diferencia_cambio_aplicaciones"]
        dif = (x["saldo_contable"] - explicado).quantize(C2)
        out.append({"cuenta": c, **{k: str(v.quantize(C2)) for k, v in x.items()}, "partidas_netas": str(explicado.quantize(C2)),
                    "diferencia": str(dif), "conciliado": dif == 0})
    tot = {k: str(sum((Decimal(f[k]) for f in out), CERO)) for k in ("saldo_contable", "origen", "aplicacion", "sin_detalle",
                                                                       "no_clasificado", "diferencia_cambio_aplicaciones",
                                                                       "partidas_netas", "diferencia")}
    return {"fecha_corte": corte.isoformat(), "cuentas": out, "totales": tot, "conciliado": all(f["conciliado"] for f in out),
            "nota": "Saldos en moneda nacional con signo contable (+ deudor / − acreedor). Las diferencias se muestran tal cual; "
                    "no se generan ajustes."}
