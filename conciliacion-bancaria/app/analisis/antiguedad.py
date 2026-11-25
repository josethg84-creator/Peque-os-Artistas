"""Antigüedad de saldos por documento.

Fuentes:
  LIBROS   saldo por documento (tercero · tipo · serie · número) de las cuentas de cartera, a la
           fecha de corte. Solo se netean líneas del MISMO documento; no se compensan documentos
           distintos entre sí (eso corresponde al motor de compensación de la fase 4).
  CARTERA  saldo pendiente informado por el ERP en los reportes de cuentas por cobrar / pagar.

Un resultado es PRELIMINAR cuando falta información para afirmar el saldo pendiente del documento:
líneas sin número de documento, saldo de apertura sin detalle, fecha base faltante, o saldo
contrario a la naturaleza (posible anticipo o cobro/pago aún no aplicado).
"""
import json
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.analisis import pcge
from app.analisis.saldos import cent, dec, fuentes
from app.models import ConfiguracionAntiguedad, DocumentoRegistro, LineaDiario, LoteContable, SaldoCuenta

RANGOS_DEFECTO = [[1, 30], [31, 60], [61, 90], [91, 180], [181, 365], [366, None]]


def etiquetas(rangos) -> list[str]:
    out = ["No vencido"]
    for a, b in rangos:
        out.append(f"Más de {a - 1} días" if b is None else f"De {a} a {b} días")
    return out


def tramo(dias: int, rangos) -> int:
    if dias <= 0:
        return 0
    for i, (a, b) in enumerate(rangos, start=1):
        if dias >= a and (b is None or dias <= b):
            return i
    return len(rangos)


def configuracion(db: Session, empresa_id: int, config_id: int | None = None) -> ConfiguracionAntiguedad:
    q = select(ConfiguracionAntiguedad).where(ConfiguracionAntiguedad.empresa_id == empresa_id)
    cfg = db.scalar(q.where(ConfiguracionAntiguedad.id == config_id)) if config_id else \
        db.scalar(q.order_by(ConfiguracionAntiguedad.predeterminada.desc(), ConfiguracionAntiguedad.id))
    if cfg is None:
        if config_id:
            raise ValueError("Configuración de antigüedad no encontrada")
        cfg = ConfiguracionAntiguedad(empresa_id=empresa_id, nombre="Estándar", rangos=json.dumps(RANGOS_DEFECTO),
                                      predeterminada=True)
        db.add(cfg)
        db.commit()
    return cfg


def calcular(db: Session, empresa_id: int, ejercicio: int, fecha_corte: date, *, base: str | None = None,
             fuente: str = "LIBROS", cuentas: str | None = None, config_id: int | None = None,
             tercero: str | None = None) -> dict:
    cfg = configuracion(db, empresa_id, config_id)
    rangos = json.loads(cfg.rangos)
    base = base or cfg.base
    prefijos = [p.strip() for p in (cuentas or cfg.cuentas).split(",") if p.strip()]
    docs = (_desde_libros if fuente == "LIBROS" else _desde_cartera)(db, empresa_id, ejercicio, fecha_corte, prefijos, tercero)
    nombres = etiquetas(rangos)
    tot = [Decimal("0")] * len(nombres)
    por_tercero: dict[str, dict] = {}
    preliminar_importe = Decimal("0")
    items = []
    for d in docs:
        fecha_base = d["fecha_vencimiento"] if base == "VENCIMIENTO" else d["fecha_emision"]
        motivos = list(d["motivos"])
        if fecha_base is None:
            fecha_base = d["fecha_emision"] or d["fecha_contable"]
            motivos.append("sin fecha de vencimiento: se usó la fecha de emisión" if base == "VENCIMIENTO" else "sin fecha de emisión")
        dias = (fecha_corte - fecha_base).days if fecha_base else 0
        t = tramo(dias, rangos)
        importe = d["importe"]
        nat = pcge.naturaleza_pcge(d["cuenta"]) or "D"
        expuesto = importe if nat == "D" else -importe  # saldo expresado según la naturaleza de la cuenta
        if expuesto < 0:
            motivos.append("saldo contrario a la naturaleza: posible anticipo o cobro/pago no aplicado")
        preliminar = bool(motivos)
        if preliminar:
            preliminar_importe += abs(expuesto)
        tot[t] += expuesto
        pt = por_tercero.setdefault(d["tercero"] or "(sin tercero)", {
            "tercero": d["tercero"] or "(sin tercero)", "razon_social": d["razon_social"], "tramos": [Decimal("0")] * len(nombres),
            "total": Decimal("0"), "documentos": 0, "preliminar": False})
        pt["tramos"][t] += expuesto
        pt["total"] += expuesto
        pt["documentos"] += 1
        pt["preliminar"] |= preliminar
        items.append({**d, "importe": str(expuesto), "dias": dias, "tramo": t, "tramo_nombre": nombres[t],
                      "fecha_base": fecha_base.isoformat() if fecha_base else None, "preliminar": preliminar,
                      "motivos": motivos, "fecha_emision": _iso(d["fecha_emision"]), "fecha_vencimiento": _iso(d["fecha_vencimiento"]),
                      "fecha_contable": _iso(d["fecha_contable"])})
    items.sort(key=lambda x: (-x["dias"], x["tercero"] or ""))
    terceros = sorted(por_tercero.values(), key=lambda x: -abs(x["total"]))
    for x in terceros:
        x["tramos"] = [str(v) for v in x["tramos"]]
        x["total"] = str(x["total"])
    antiguo = sum((Decimal(i["importe"]) for i in items if i["dias"] > cfg.dias_saldo_antiguo), Decimal("0"))
    return {"fecha_corte": fecha_corte.isoformat(), "base": base, "fuente": fuente, "cuentas": prefijos,
            "configuracion": {"id": cfg.id, "nombre": cfg.nombre, "rangos": rangos, "dias_saldo_antiguo": cfg.dias_saldo_antiguo},
            "tramos": nombres, "totales": [str(v) for v in tot], "total": str(sum(tot, Decimal("0"))),
            "importe_preliminar": str(preliminar_importe), "documentos_preliminares": sum(1 for i in items if i["preliminar"]),
            "saldo_antiguo": str(antiguo), "terceros": terceros, "documentos": items,
            "nota": ("Resultado PRELIMINAR en los documentos marcados. No se compensan documentos distintos entre sí: "
                     "esa conciliación corresponde a la fase 4.")}


def _iso(v):
    return v.isoformat() if v else None


def _desde_libros(db, empresa_id, ejercicio, corte, prefijos, tercero):
    f = fuentes(db, empresa_id, ejercicio)
    filtro = f.filtro_lineas(0 if f.apertura == "DIARIO_00" else 1, 13, incluir_apertura_diario=f.apertura == "DIARIO_00")
    cond_cuenta = or_(*[LineaDiario.cuenta.like(f"{p}%") for p in prefijos])
    clave = (LineaDiario.cuenta, LineaDiario.documento_tercero, LineaDiario.tipo_documento, LineaDiario.serie,
             LineaDiario.numero_documento)
    q = select(*clave, func.max(LineaDiario.razon_social), cent(LineaDiario.debe_mn) - cent(LineaDiario.haber_mn),
               func.min(LineaDiario.fecha_emision), func.max(LineaDiario.fecha_vencimiento),
               func.min(LineaDiario.fecha_contable), func.count()) \
        .where(filtro, cond_cuenta, LineaDiario.fecha_contable <= corte).group_by(*clave)
    if tercero:
        q = q.where(LineaDiario.documento_tercero == tercero)
    docs = []
    for cuenta, ter, td, serie, num, rs, saldo, emi, venc, fcont, n in db.execute(q):
        if not int(saldo):
            continue
        motivos = [] if num else ["líneas sin número de documento"]
        docs.append({"cuenta": cuenta, "tercero": ter, "razon_social": rs, "tipo_documento": td, "serie": serie,
                     "numero": num, "documento": f"{serie}-{num}" if serie else (num or "(sin documento)"),
                     "importe": dec(saldo), "fecha_emision": emi or fcont, "fecha_vencimiento": venc,
                     "fecha_contable": fcont, "lineas": n, "motivos": motivos, "fuente": "LIBROS"})
    if f.apertura == "SALDOS_INICIALES":
        q = select(SaldoCuenta.cuenta, SaldoCuenta.documento_tercero,
                   cent(SaldoCuenta.saldo_inicial_debe) - cent(SaldoCuenta.saldo_inicial_haber)) \
            .where(SaldoCuenta.lote_id.in_(f.lotes_apertura), or_(*[SaldoCuenta.cuenta.like(f"{p}%") for p in prefijos])) \
            .group_by(SaldoCuenta.cuenta, SaldoCuenta.documento_tercero)
        for cuenta, ter, saldo in db.execute(q):
            if int(saldo) and (not tercero or ter == tercero):
                docs.append({"cuenta": cuenta, "tercero": ter, "razon_social": None, "tipo_documento": None, "serie": None,
                             "numero": None, "documento": "(saldo de apertura)", "importe": dec(saldo),
                             "fecha_emision": date(ejercicio, 1, 1), "fecha_vencimiento": None, "fecha_contable": date(ejercicio, 1, 1),
                             "lineas": 0, "motivos": ["saldo de apertura sin detalle por documento"], "fuente": "APERTURA"})
    return docs


def _desde_cartera(db, empresa_id, ejercicio, corte, prefijos, tercero):
    q = select(DocumentoRegistro).join(LoteContable, LoteContable.id == DocumentoRegistro.lote_id).where(
        DocumentoRegistro.empresa_id == empresa_id, DocumentoRegistro.tipo.in_(("CXC", "CXP")),
        LoteContable.estado == "ACTIVO", DocumentoRegistro.ejercicio == ejercicio)
    if tercero:
        q = q.where(DocumentoRegistro.documento_tercero == tercero)
    docs = []
    for d in db.scalars(q):
        cuenta = d.cuenta or ("12" if d.tipo == "CXC" else "42")
        if prefijos and not any(cuenta.startswith(p) for p in prefijos):
            continue
        saldo = d.saldo_pendiente or Decimal("0")
        if not saldo:
            continue
        importe = saldo if d.tipo == "CXC" else -saldo
        docs.append({"cuenta": cuenta, "tercero": d.documento_tercero, "razon_social": d.razon_social,
                     "tipo_documento": d.tipo_documento, "serie": d.serie, "numero": d.numero,
                     "documento": f"{d.serie}-{d.numero}" if d.serie else (d.numero or "(sin documento)"),
                     "importe": importe, "fecha_emision": d.fecha_emision, "fecha_vencimiento": d.fecha_vencimiento,
                     "fecha_contable": d.fecha_emision, "lineas": 1, "motivos": [], "fuente": "CARTERA"})
    return docs
