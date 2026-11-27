"""Construcción de fuentes: cada fuente se convierte en registros normalizados con referencia a su origen.

Fuentes internas (se leen sin modificarlas): libro (fase 2) a través del contexto de la fase 5, movimientos
bancarios (fase 1), registros de compras y ventas (fase 2), registros auxiliares y anexos (fase 5), reglas de
tasas (fase 4) y política de destino (fase 3). Fuentes externas: archivos homologados con la fase 2.
"""
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from types import SimpleNamespace

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.conciliacion import esquemas
from app.anexos import datos as datos5
from app.contable import archivos, homologacion

from app.importers.lectores import ErrorImportacion
from app.importers.normalizacion import normalizar_texto
from app.models import (Anexo, CuentaBancaria, DocumentoRegistro, Empresa, Importacion, LineaDiario, LoteContable,
                        MovimientoBanco, ReglaCompensacion, VersionAnexo)

CERO = Decimal("0")
C2 = Decimal("0.01")
ESQUEMAS = esquemas.ESQUEMAS  # importarlo registra los diseños de fuentes en el registro de la fase 2
CAMPOS_FIJOS = ("clave_registro", "origen_tabla", "origen_id", "fila_origen", "fecha", "fecha_valor", "periodo", "tipo_documento",
                "serie", "numero", "tercero", "razon_social", "referencia", "operacion", "descripcion", "cuenta", "centro_costo",
                "proyecto", "concepto", "moneda", "tipo_cambio", "importe", "importe_me", "cantidad", "personal")


class ErrorFuente(Exception):
    status = 422


def rec(**kw) -> dict:
    r = {c: None for c in CAMPOS_FIJOS}
    r.update(moneda="PEN", importe=CERO, personal=False, datos={})
    r.update(kw)
    if r["fecha"] and not r["periodo"]:
        r["periodo"] = r["fecha"].year * 100 + r["fecha"].month
    return r


def d(c: int) -> Decimal:
    return datos5.dec(c)


def norm_doc(v) -> str | None:
    """Comparación robusta de series, números y operaciones: sin espacios ni guiones; números sin ceros a la izquierda."""
    if v in (None, ""):
        return None
    s = re.sub(r"[^0-9A-Z]", "", normalizar_texto(str(v)))
    return (s.lstrip("0") or "0") if s.isdigit() else (s or None)


def norm_tipo_doc(v) -> str | None:
    if not v:
        return None
    s = str(v).strip()
    return s.zfill(2) if s.isdigit() else s.upper()


class Contexto:
    """Datos de la empresa al corte, compartidos por las fuentes de una conciliación (se cargan una vez)."""

    def __init__(self, db: Session, empresa_id: int, ejercicio: int, periodo: int, corte: date, ambito: dict):
        self.db, self.empresa_id, self.ejercicio, self.periodo, self.corte, self.ambito = db, empresa_id, ejercicio, periodo, corte, ambito
        self._libro: dict[int, datos5.Ctx] = {}
        self.empresa = db.get(Empresa, empresa_id)

    def libro(self, empresa_id: int | None = None) -> datos5.Ctx:
        e = empresa_id or self.empresa_id
        if e not in self._libro:
            fl = datos5.Filtros(centro_costo=self.ambito.get("centro_costo"), proyecto=self.ambito.get("proyecto"))
            self._libro[e] = datos5.crear(self.db, e, self.ejercicio, min(self.periodo, 13), self.corte, fl)
        return self._libro[e]

    def cuenta_bancaria(self) -> CuentaBancaria:
        cb = self.db.get(CuentaBancaria, self.ambito.get("cuenta_bancaria_id") or 0)
        if not cb or cb.empresa_id != self.empresa_id:
            raise ErrorFuente("Seleccione una cuenta bancaria de la empresa para la conciliación bancaria.")
        return cb


def _linea(ln: datos5.L, signo=1, me=False, **extra) -> dict:
    neto = (ln.neto_me if me else ln.neto) * signo
    return rec(clave_registro=f"L{ln.id}", origen_tabla="lineas_diario", origen_id=ln.id, fecha=ln.fecha,
               periodo=(ln.fecha.year * 100 + ln.fecha.month) if ln.fecha else None, tipo_documento=norm_tipo_doc(ln.tipo_doc),
               serie=ln.serie, numero=ln.numero, tercero=ln.tercero, razon_social=ln.razon_social, referencia=ln.referencia,
               operacion=ln.numero if not ln.serie else None, descripcion=ln.glosa, cuenta=ln.cuenta, centro_costo=ln.cc,
               proyecto=ln.proyecto, moneda=ln.moneda if me else "PEN", tipo_cambio=ln.tipo_cambio, importe=d(neto),
               importe_me=d(ln.neto_me * signo) if ln.moneda != "PEN" else None,
               datos={"asiento": ln.etiqueta_asiento, "maquinaria": ln.maquinaria, "debe": str(d(ln.debe)), "haber": str(d(ln.haber))},
               **extra)


# ------------------------------------------------------------------ fuentes internas
def libro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    meta = {}
    cuentas = list(p.get("cuentas") or ([cx.ambito["cuenta"]] if cx.ambito.get("cuenta") else []))
    me = False
    if p.get("por_cuenta_bancaria"):
        cb = cx.cuenta_bancaria()
        cuentas, me = [cb.cuenta_contable], cb.moneda != "PEN"
    if not cuentas:
        raise ErrorFuente("Indique la cuenta contable a conciliar.")
    ctx = cx.libro()
    tercero = None
    if p.get("tercero_relacionada"):
        rel = cx.db.get(Empresa, cx.ambito.get("empresa_relacionada_id") or 0)
        if not rel:
            raise ErrorFuente("Seleccione la empresa relacionada.")
        tercero = rel.ruc
    signo = -1 if p.get("naturaleza") == "A" else 1
    out = []
    for c in cuentas:
        for ln in ctx.de(c):
            if ln.periodo == 0 or (tercero and ln.tercero != tercero):
                continue
            out.append(_linea(ln, signo, me))
    if p.get("por_cuenta_bancaria"):
        s = sum((ctx.saldos_de(c)["sf_me" if me else "sf"] for c in cuentas), 0)
        meta["saldo"] = d(s)
        meta["observaciones"] = f"Saldo según libros al {cx.corte:%d/%m/%Y} en {cb.moneda}"
    return out, meta


def banco(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    cb = cx.cuenta_bancaria()
    db = cx.db
    desde = date(cx.ejercicio, 1, 1)
    q = (select(MovimientoBanco).join(Importacion, Importacion.id == MovimientoBanco.importacion_id)
         .where(MovimientoBanco.cuenta_bancaria_id == cb.id, Importacion.estado == "ACTIVA", MovimientoBanco.fecha >= desde,
                MovimientoBanco.fecha <= cx.corte).order_by(MovimientoBanco.fecha, MovimientoBanco.id))
    out = []
    saldo = None
    for m in db.scalars(q):
        out.append(rec(clave_registro=f"MB{m.id}", origen_tabla="movimientos_banco", origen_id=m.id, fila_origen=m.fila_origen,
                       fecha=m.fecha, fecha_valor=m.fecha_valuta, operacion=m.numero_operacion, referencia=m.referencia,
                       descripcion=m.descripcion, moneda=m.moneda, importe=Decimal(m.importe),
                       datos={"categoria": m.categoria, "saldo": str(m.saldo) if m.saldo is not None else None,
                              "posible_duplicado": m.posible_duplicado, "importacion_id": m.importacion_id}))
        if m.saldo is not None and not m.posible_duplicado:
            saldo = Decimal(m.saldo)
    cubre = db.scalar(select(func.max(Importacion.fecha_hasta)).where(Importacion.cuenta_bancaria_id == cb.id, Importacion.tipo == "BANCO",
                                                                      Importacion.estado == "ACTIVA"))
    meta = {"saldo": saldo, "observaciones": (f"Estado de cuenta hasta {cubre:%d/%m/%Y}" if cubre else "Sin estados de cuenta importados")
            + ("" if cubre and cubre >= cx.corte else " — no cubre la fecha de corte")}
    return out, meta


def registro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    tipo = p.get("registro", "COMPRAS")
    q = (select(DocumentoRegistro).join(LoteContable, LoteContable.id == DocumentoRegistro.lote_id)
         .where(DocumentoRegistro.empresa_id == cx.empresa_id, DocumentoRegistro.tipo == tipo, LoteContable.estado == "ACTIVO",
                DocumentoRegistro.ejercicio == cx.ejercicio, DocumentoRegistro.periodo == cx.periodo).order_by(DocumentoRegistro.id))
    out = []
    for r in cx.db.scalars(q):
        nc = norm_tipo_doc(r.tipo_documento) == "07"
        total = Decimal(r.total or 0)
        igv = Decimal(r.igv or 0)
        base = Decimal(r.base_imponible or 0) + Decimal(r.no_gravado or 0) + Decimal(r.otros_tributos or 0)
        if nc:  # las notas de crédito disminuyen el importe
            total, igv, base = -abs(total), -abs(igv), -abs(base)
        anulado = total == 0 and "ANUL" in normalizar_texto(r.glosa or "")
        out.append(rec(clave_registro=f"DR{r.id}", origen_tabla="documentos_registro", origen_id=r.id, fila_origen=r.fila_origen,
                       fecha=r.fecha_emision, periodo=r.ejercicio * 100 + (r.periodo or 0), tipo_documento=norm_tipo_doc(r.tipo_documento),
                       serie=r.serie, numero=r.numero, tercero=r.documento_tercero, razon_social=r.razon_social,
                       referencia=r.documento_referencia, descripcion=r.glosa, cuenta=r.cuenta, moneda=r.moneda or "PEN",
                       tipo_cambio=r.tipo_cambio, importe=total, importe_me=r.importe_me,
                       datos={"igv": str(igv), "base": str(base), "total": str(total), "anulado": anulado,
                              "codigo_detraccion": r.codigo_detraccion, "constancia": r.constancia_detraccion, "lote_id": r.lote_id}))
    return out, {}


def libro_documentos(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    """Provisiones por comprobante: total (cuenta del documento), IGV y base (otras cuentas del asiento). Se excluyen
    los asientos con movimiento de caja (pagos y cobranzas)."""
    ctx = cx.libro()
    doc_pref = tuple(p.get("cuentas_documento", ["42"]))
    igv_pref = tuple(p.get("cuentas_igv", ["4011"]))
    ing_pref = tuple(p.get("cuentas_ingreso", []))
    lado = p.get("lado_documento", "H")
    s = 1 if lado == "D" else -1  # compras: provisión al haber; ventas: al debe
    out = []
    for clave, lineas in ctx.asientos().items():
        if any(ln.periodo == 0 for ln in lineas) or any(ln.cuenta.startswith("10") for ln in lineas):
            continue
        docs = [ln for ln in lineas if ln.cuenta.startswith(doc_pref) and ln.numero]
        resto = [ln for ln in lineas if not ln.cuenta.startswith(doc_pref) and not ln.cuenta.startswith(igv_pref)]
        if ing_pref:
            resto = [ln for ln in resto if ln.cuenta.startswith(ing_pref)]
        igv_lin = [ln for ln in lineas if ln.cuenta.startswith(igv_pref)]
        if not docs:
            if ing_pref and resto:  # ingreso sin comprobante asociado (posible devengo no facturado)
                imp = sum(-ln.neto * s for ln in resto)
                if imp:
                    p0 = resto[0]
                    out.append(rec(clave_registro=f"LS{p0.id}", origen_tabla="lineas_diario", origen_id=p0.id, fecha=p0.fecha,
                                   descripcion=p0.glosa, cuenta=p0.cuenta, importe=d(imp), centro_costo=p0.cc, proyecto=p0.proyecto,
                                   datos={"asiento": p0.etiqueta_asiento, "sin_comprobante": True, "igv": "0", "base": str(d(imp))}))
            continue
        por_doc = defaultdict(list)
        for ln in docs:
            por_doc[(ln.tercero or "", norm_tipo_doc(ln.tipo_doc) or "", ln.serie or "", ln.numero)].append(ln)
        total_asiento = sum(sum(x.neto for x in ls) for ls in por_doc.values()) or 1
        igv_total = sum(x.neto for x in igv_lin)
        base_total = sum(x.neto for x in resto)
        for k, ls in por_doc.items():
            tot = sum(x.neto for x in ls)
            prop = Decimal(tot) / Decimal(total_asiento)
            p0 = ls[0]
            cuentas_dest = sorted({x.cuenta for x in resto})
            out.append(rec(clave_registro=f"LD{p0.id}", origen_tabla="lineas_diario", origen_id=p0.id, fecha=p0.fecha,
                           tipo_documento=k[1] or None, serie=p0.serie, numero=p0.numero, tercero=p0.tercero, razon_social=p0.razon_social,
                           referencia=p0.referencia, descripcion=p0.glosa, cuenta=p0.cuenta, centro_costo=p0.cc, proyecto=p0.proyecto,
                           moneda=p0.moneda, tipo_cambio=p0.tipo_cambio, importe=d(tot * s),
                           importe_me=d(sum(x.neto_me for x in ls) * s) if p0.moneda != "PEN" else None,
                           datos={"asiento": p0.etiqueta_asiento, "igv": str((d(-igv_total * s) * prop).quantize(C2)),
                                  "base": str((d(-base_total * s) * prop).quantize(C2)), "cuentas_destino": cuentas_dest,
                                  "periodo_contable": p0.periodo}))
    return out, {}


def _maquinaria(ln) -> str | None:
    return (ln.maquinaria or "").strip().upper() or None


def activos_registro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    from app.anexos import constructores as k5
    ctx = cx.libro()
    regs = {str(r["_clave"]): r for r in ctx.registros("ACTIVO_FIJO")}
    if not regs:
        return [], {"observaciones": "No hay registro de activos importado (fase 5 · registros auxiliares)."}
    plantilla = {"rangos_antiguedad": None, "parametros": {}}
    costo, dep = k5.Resultado(), k5.Resultado()
    k5.ppe(ctx, "3", plantilla, costo)
    k5.depreciacion(ctx, "39", plantilla, dep)
    deps = {f["datos"]["codigo_activo"]: f for f in dep.filas if f["datos"].get("codigo_activo")}
    out = []
    for f in costo.filas:
        cod = f["datos"].get("codigo_activo")
        if not cod:
            continue
        r = regs.get(str(cod), {})
        dp = deps.get(cod, {"datos": {}})
        out.append(rec(clave_registro=f"AF{cod}", origen_tabla="annex_support_records", origen_id=r.get("_id"), fecha=f["fecha"],
                       descripcion=f["glosa"], cuenta=f["cuenta"], centro_costo=f.get("centro_costo"), importe=f["saldo"],
                       datos={"clave": str(cod).upper(), "grupo": "TOTAL", "costo": str(f["saldo"]),
                              "dep_acumulada": str(dp["datos"].get("dep_final") or 0), "dep_periodo": str(dp["datos"].get("dep_periodo") or 0),
                              "dep_tributaria": str(dp["datos"].get("dep_tributaria")) if dp["datos"].get("dep_tributaria") is not None else None,
                              "valor_residual": str(r.get("valor_residual") or 0), "fecha_baja": r.get("fecha_baja"),
                              "cuenta_depreciacion": r.get("cuenta_depreciacion"), "vida_util_meses": r.get("vida_util_meses")}))
    return out, {}


def activos_libro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    acum = defaultdict(lambda: {"costo": 0, "dep_acumulada": 0, "dep_periodo": 0, "lineas": [], "ultima_dep": None})
    for pref, campo in [(x, "costo") for x in p.get("costo", ["33"])] + [(x, "dep_acumulada") for x in p.get("depreciacion", ["39"])] + \
            [(x, "dep_periodo") for x in p.get("gasto", ["68"])]:
        for c, v in ctx.apertura.items():
            if c.startswith(pref) and v and campo != "dep_periodo":
                a = acum[(None, c)]
                a[campo] += v if campo == "costo" else -v
        for ln in ctx.de(pref):
            k = (_maquinaria(ln), ln.cuenta if not _maquinaria(ln) else None)
            if campo == "dep_periodo" and not _maquinaria(ln):
                continue  # el gasto sin código no puede atribuirse a un activo
            a = acum[k]
            a[campo] += ln.neto if campo != "dep_acumulada" else -ln.neto
            a["lineas"].append(ln.id)
            if campo == "dep_periodo" and ln.fecha:
                a["ultima_dep"] = max(a["ultima_dep"] or ln.fecha, ln.fecha)
    out = []
    for (cod, cta), a in acum.items():
        if not (a["costo"] or a["dep_acumulada"] or a["dep_periodo"]):
            continue
        out.append(rec(clave_registro=f"AL{cod or cta}", origen_tabla="lineas_diario", origen_id=a["lineas"][0] if a["lineas"] else None,
                       cuenta=cta, descripcion="Saldo contable sin código de activo" if not cod else f"Activo {cod}",
                       importe=d(a["costo"]),
                       datos={"clave": cod, "grupo": "TOTAL" if not cod else None, "costo": str(d(a["costo"])),
                              "dep_acumulada": str(d(a["dep_acumulada"])), "dep_periodo": str(d(a["dep_periodo"])),
                              "ultima_depreciacion": a["ultima_dep"].isoformat() if a["ultima_dep"] else None, "lineas": a["lineas"][:50]}))
    return out, {}


def planilla_libro(cx: Contexto, p: dict, conceptos: list[dict]) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    mapeo = sorted(conceptos, key=lambda c: -len(c["cuenta"]))
    out = []
    for ln in ctx.lineas:
        if ln.periodo != cx.periodo:
            continue
        m = next((c for c in mapeo if ln.cuenta.startswith(c["cuenta"]) and (ln.haber if c["lado"] == "H" else ln.debe)), None)
        if not m:
            continue
        imp = ln.haber - ln.debe if m["lado"] == "H" else ln.debe - ln.haber
        clave = {"trabajador": ln.tercero or "(sin trabajador)", "centro_costo": ln.cc or "(sin centro de costo)"}.get(m["por"], "TOTAL")
        r = _linea(ln)
        r.update(clave_registro=f"PL{ln.id}", importe=d(imp), concepto=m["grupo"], personal=m["por"] == "trabajador")
        r["datos"]["clave"] = clave
        out.append(r)
    return out, {}


def inventario_libro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    out = []
    for c in ctx.hojas():
        if not c.startswith(tuple(p.get("cuentas", ["20"]))):
            continue
        s = ctx.saldos_de(c)
        out.append(rec(clave_registro=f"IN{c}", origen_tabla="lineas_diario", cuenta=c, descripcion=ctx.descripcion(c), importe=d(s["sf"]),
                       datos={"cuenta": c, "valor_inicial": str(d(s["si"])), "valor_entradas": str(d(s["debe"])),
                              "valor_salidas": str(d(s["haber"])), "valor_final": str(d(s["sf"]))}))
    return out, {}


CONCEPTOS_COSTO = {"mano_obra": "MANO_OBRA", "materiales": "MATERIALES", "combustible": "COMBUSTIBLE",
                   "servicios_terceros": "SERVICIOS_TERCEROS", "depreciacion": "DEPRECIACION", "indirectos": "INDIRECTOS"}
PALABRAS_COSTO = [("COMBUST", "COMBUSTIBLE"), ("PETROLEO", "COMBUSTIBLE"), ("DIESEL", "COMBUSTIBLE"), ("MANO", "MANO_OBRA"),
                  ("PERSONAL", "MANO_OBRA"), ("PLANILLA", "MANO_OBRA"), ("MATERIAL", "MATERIALES"), ("SUMINISTRO", "MATERIALES"),
                  ("SERVICIO", "SERVICIOS_TERCEROS"), ("TERCERO", "SERVICIOS_TERCEROS"), ("DEPREC", "DEPRECIACION"),
                  ("INDIRECT", "INDIRECTOS"), ("GENERAL", "INDIRECTOS")]


def concepto_costo(texto) -> str:
    t = normalizar_texto(texto or "")
    if t in CONCEPTOS_COSTO.values():
        return t
    return next((c for k, c in PALABRAS_COSTO if k in t), "INDIRECTOS")


def costos_libro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    from app.anexos.constructores import _categoria_costo
    ctx = cx.libro()
    out = []
    cuenta23 = p.get("cuenta_proceso", "23")
    for ln in ctx.lineas:
        if not ln.periodo:
            continue
        if ln.cuenta.startswith("6") and ln.neto:
            cat = CONCEPTOS_COSTO[_categoria_costo(SimpleNamespace(cuenta=ln.cuenta, glosa=ln.glosa))]
            r = _linea(ln)
            r.update(clave_registro=f"CO{ln.id}", concepto=cat if ln.proyecto else "SIN_PROYECTO",
                     proyecto=ln.proyecto or None)
            out.append(r)
        elif ln.cuenta.startswith(cuenta23):
            r = _linea(ln)
            # la cuenta 23 acumula los mismos costos (vía 71): se informa en el reporte y no se cruza contra el reporte operativo
            r.update(clave_registro=f"CP{ln.id}", concepto="CUENTA_23", excluido=True,
                     motivo_exclusion="Movimiento de la cuenta 23: se analiza por proyecto en el reporte (no duplica los costos de la clase 6)")
            out.append(r)
    return out, {}


def contratos(cx: Contexto) -> dict:
    return {str(r["_clave"]).upper(): r for r in cx.libro().registros("CONTRATO_FINANCIERO")}


def cuotas(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    desde = date(cx.ejercicio, 1, 1)
    todas = ctx.registros("CUOTA_FINANCIERA")
    ultima = defaultdict(int)
    for q in todas:
        ultima[str(q.get("contrato")).upper()] = max(ultima[str(q.get("contrato")).upper()], int(q.get("version") or 1))
    out = []
    from app.anexos.constructores import _d, _f
    for q in todas:
        cont = str(q.get("contrato")).upper()
        if int(q.get("version") or 1) != ultima[cont]:
            continue
        f = _f(q.get("fecha_vencimiento"))
        if not f or f < desde or f > cx.corte:
            continue
        for concepto, campo in (("CAPITAL", "capital"), ("INTERES", "interes"), ("COMISION", "comision")):
            v = _d(q.get(campo))
            if v:
                out.append(rec(clave_registro=f"CU{cont}|{q.get('numero')}|{concepto}", origen_tabla="annex_support_records",
                               origen_id=q["_id"], fecha=f, numero=str(q.get("numero")), concepto=concepto, importe=v,
                               descripcion=f"Cuota {q.get('numero')} del contrato {cont}",
                               datos={"contrato": cont, "pagada": str(q.get("pagada") or "").upper(), "version": ultima[cont]}))
    return out, {"observaciones": f"{len(out)} conceptos de cuotas vencidas entre {desde:%d/%m/%Y} y {cx.corte:%d/%m/%Y}"}


def financieras_libro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    conts = contratos(cx)
    pats = [(k, re.compile(re.escape(k))) for k in conts]
    out = []

    def contrato_de(ln):
        texto = " ".join(normalizar_texto(x or "") for x in (ln.referencia, ln.numero, ln.glosa))
        return next((k for k, pat in pats if pat.search(texto)), None)
    for pref, concepto in [(x, "CAPITAL") for x in p.get("cuentas", ["45"])] + [(x, "INTERES") for x in p.get("intereses", ["67"])]:
        for ln in ctx.de(pref):
            if not ln.periodo or not ln.debe:
                continue
            cont = contrato_de(ln)
            me = bool(cont and (conts[cont].get("moneda") or "PEN").upper() != "PEN")
            r = _linea(ln, me=me)
            r.update(clave_registro=f"FL{ln.id}", concepto=concepto, importe=d(ln.debe_me if me else ln.debe))
            if concepto == "INTERES" and "COMISION" in normalizar_texto(ln.glosa or ""):
                r["concepto"] = "COMISION"
            r["datos"]["contrato"] = cont
            out.append(r)
    return out, {}


def _tasa(db: Session, empresa_id: int, tipo: str, codigo: str | None, fecha: date | None):
    if not codigo:
        return None, "sin código"
    reglas = db.scalars(select(ReglaCompensacion).where(ReglaCompensacion.empresa_id == empresa_id, ReglaCompensacion.tipo == tipo,
                                                        ReglaCompensacion.codigo == codigo, ReglaCompensacion.activa.is_(True))).all()
    for r in reglas:
        if fecha and ((r.vigente_desde and fecha < r.vigente_desde) or (r.vigente_hasta and fecha > r.vigente_hasta)):
            continue
        par = json.loads(r.parametros or "{}")
        if par.get("tasa") in (None, ""):
            return None, f"la regla {codigo} no tiene tasa"
        if not r.autorizado_por:
            return None, f"la regla {codigo} no tiene aprobación del responsable tributario"
        return {"tasa": Decimal(str(par["tasa"])), "plazo_dias": par.get("plazo_dias"), "fuente": r.sustento,
                "autorizado_por": r.autorizado_por, "regla_id": r.id, "version": r.version}, None
    return None, f"no hay una regla vigente para el código {codigo}"


def detraccion_documentos(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    base, _ = registro(cx, {"registro": p.get("registro", "COMPRAS")})
    out = []
    for r in base:
        cod = r["datos"].get("codigo_detraccion")
        if not cod:
            continue
        info, error = _tasa(cx.db, cx.empresa_id, "DETRACCION", cod, r["fecha"])
        total = abs(Decimal(r["datos"]["total"]))
        esperado = (total * info["tasa"] / 100).quantize(Decimal("1"), ROUND_HALF_UP) if info else CERO
        r = dict(r, clave_registro=f"DT{r['origen_id']}", importe=esperado)
        r["datos"] = dict(r["datos"], total=str(total), tasa=str(info["tasa"]) if info else None, sin_tasa=error,
                          plazo_dias=info.get("plazo_dias") if info else None, fuente_normativa=info.get("fuente") if info else None,
                          aprobado_por=info.get("autorizado_por") if info else None)
        out.append(r)
    return out, {}


def constancias_libro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    f = cx.libro().f
    q = select(LineaDiario).where(f.filtro_lineas(1, min(cx.periodo, 13)), LineaDiario.constancia_detraccion.is_not(None),
                                  or_(LineaDiario.fecha_contable.is_(None), LineaDiario.fecha_contable <= cx.corte))
    out = []
    for ln in cx.db.scalars(q.order_by(LineaDiario.id)):
        imp = abs(Decimal(ln.debe_mn or 0) - Decimal(ln.haber_mn or 0))
        out.append(rec(clave_registro=f"LC{ln.id}", origen_tabla="lineas_diario", origen_id=ln.id, fecha=ln.fecha_contable,
                       operacion=ln.constancia_detraccion, tercero=ln.documento_tercero, razon_social=ln.razon_social, serie=ln.serie,
                       numero=ln.numero_documento, descripcion=ln.glosa, cuenta=ln.cuenta, importe=imp,
                       datos={"asiento": "-".join(x for x in (ln.subdiario, ln.numero_asiento) if x), "codigo": ln.codigo_detraccion}))
    return out, {}


TRIBUTOS = [("40111", "IGV"), ("40113", "PERCEPCION_IGV"), ("40114", "RETENCION_IGV"), ("4011", "IGV"), ("40171", "RENTA"),
            ("40173", "CUARTA"), ("40174", "QUINTA"), ("4017", "RENTA"), ("4031", "ESSALUD"), ("4032", "ONP"), ("407", "AFP"), ("40", "OTROS")]
ALIAS_TRIBUTO = {"IGV": "IGV", "IMPUESTO GENERAL A LAS VENTAS": "IGV", "RENTA": "RENTA", "RENTA TERCERA": "RENTA", "IMPUESTO A LA RENTA": "RENTA",
                 "ESSALUD": "ESSALUD", "ES SALUD": "ESSALUD", "ONP": "ONP", "QUINTA": "QUINTA", "RENTA QUINTA": "QUINTA", "CUARTA": "CUARTA",
                 "RENTA CUARTA": "CUARTA", "AFP": "AFP", "RETENCION IGV": "RETENCION_IGV", "PERCEPCION IGV": "PERCEPCION_IGV"}


def codigo_tributo(texto) -> str:
    t = normalizar_texto(texto or "")
    return ALIAS_TRIBUTO.get(t) or next((v for k, v in ALIAS_TRIBUTO.items() if k in t), t or "OTROS")


def tributos_libro(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    acum = defaultdict(lambda: {"haber": 0, "pagos": 0, "creditos": 0, "lineas": []})
    for ln in ctx.de("40"):
        if not ln.periodo:
            continue
        trib = next(t for k, t in TRIBUTOS if ln.cuenta.startswith(k))
        per = int(ln.numero) if ln.numero and re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])", ln.numero) else cx.ejercicio * 100 + ln.periodo
        a = acum[(trib, per)]
        a["lineas"].append(ln.id)
        a["haber"] += ln.haber
        if ln.debe:
            if any(cp.cuenta.startswith("10") for cp in ctx.contrapartidas(ln)):
                a["pagos"] += ln.debe
            else:
                a["creditos"] += ln.debe
    out = []
    for (trib, per), a in sorted(acum.items()):
        oblig = a["haber"] - a["creditos"]
        out.append(rec(clave_registro=f"TR{trib}|{per}", origen_tabla="lineas_diario", origen_id=a["lineas"][0], concepto=trib,
                       periodo=per, importe=d(oblig), descripcion=f"{trib} {per // 100}-{per % 100:02d}",
                       datos={"obligacion": str(d(oblig)), "pagos": str(d(a["pagos"])), "creditos": str(d(a["creditos"])),
                              "saldo": str(d(a["haber"] - a["pagos"] - a["creditos"])), "lineas": a["lineas"][:50]}))
    return out, {}


def empresa_relacionada(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    rel_id = cx.ambito.get("empresa_relacionada_id")
    ctx = cx.libro(rel_id)
    out = []
    for c in p.get("cuentas", ["13", "43"]):
        for ln in ctx.de(c):
            if ln.periodo and ln.tercero == cx.empresa.ruc:
                r = _linea(ln)
                r["clave_registro"] = f"E{rel_id}L{ln.id}"
                out.append(r)
    return out, {"observaciones": "Solo se leen las operaciones de la relacionada con la empresa como contraparte."}


def destino(cx: Contexto, p: dict, parte: str) -> tuple[list[dict], dict]:
    from app.analisis import destino as d3
    ctx = cx.libro()
    pol = d3.politica(cx.db, cx.empresa_id)
    reglas = d3.reglas_vigentes(cx.db, cx.empresa_id, cx.corte)
    excluidas = tuple(r.cuenta_origen for r in reglas if r.excluir)
    por_periodo = pol.modo == "PERIODO"
    acum = defaultdict(lambda: {"importe": 0, "lineas": [], "detalle": defaultdict(int)})
    for ln in ctx.lineas:
        if not ln.periodo:
            continue
        c = ln.cuenta
        if parte == "ORIGEN":
            ok = c.startswith("6") and c.startswith(tuple(pol.destinables)) and not (excluidas and c.startswith(excluidas))
            val = ln.neto
        elif parte == "DESTINO":
            ok = c.startswith(tuple(pol.destino))
            val = ln.neto
        else:
            ok = c.startswith(pol.cargas)
            val = -ln.neto
        if not ok:
            continue
        k = f"P{ln.periodo:02d}|{ln.cc or ''}" if por_periodo else f"{ln.lote_id}|{ln.periodo}|{ln.subdiario or ''}|{ln.asiento or ln.id}"
        a = acum[k]
        a["importe"] += val
        a["lineas"].append(ln)
        a["detalle"][(c, ln.cc or "")] += val
    out = []
    for k, a in acum.items():
        if not a["importe"] and not any(a["detalle"].values()):
            continue
        p0 = a["lineas"][0]
        out.append(rec(clave_registro=f"{parte[:2]}{k}", origen_tabla="lineas_diario", origen_id=p0.id, fecha=p0.fecha, referencia=k,
                       cuenta=p0.cuenta, centro_costo=p0.cc, descripcion=p0.glosa, importe=d(a["importe"]),
                       datos={"asiento": p0.etiqueta_asiento, "lineas": [x.id for x in a["lineas"]][:50],
                              "detalle": [{"cuenta": c, "centro_costo": cc, "importe": str(d(v))} for (c, cc), v in a["detalle"].items()],
                              "repetidas": len(a["lineas"]) - len({(x.cuenta, x.cc, x.debe, x.haber) for x in a["lineas"]})}))
    return out, {"observaciones": f"Política de destino: {pol.modo}; destinables {', '.join(pol.destinables)}; "
                                  f"destino {', '.join(pol.destino)}; transferencia {pol.cargas}"}


def anexo(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    lst = cx.db.scalars(select(Anexo).where(Anexo.empresa_id == cx.empresa_id, Anexo.fecha_corte == cx.corte, Anexo.version_id.is_not(None),
                                            Anexo.filtros.is_(None)).order_by(Anexo.cuenta)).all()
    out = []
    for a in lst:
        v = cx.db.get(VersionAnexo, a.version_id)
        out.append(rec(clave_registro=f"AX{a.id}", origen_tabla="accounting_annexes", origen_id=a.id, cuenta=a.cuenta,
                       descripcion=a.descripcion, importe=Decimal(a.saldo_detalle),
                       datos={"cuenta": a.cuenta, "anexo_id": a.id, "version": v.numero if v else None, "resultado": a.resultado,
                              "fuente_independiente": False}))
    cx.cuentas_anexo = [a.cuenta for a in lst]
    return out, {"observaciones": "Los anexos se generan desde el mismo libro: la comparación es una conciliación INTERNA y no "
                                  "constituye evidencia independiente de la exactitud del mayor."}


def mayor(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    cuentas = getattr(cx, "cuentas_anexo", None) or ctx.hojas()
    out = []
    for c in cuentas:
        s = ctx.saldos_de(c)
        sg = 1 if ctx.naturaleza(c) == "D" else -1
        out.append(rec(clave_registro=f"MY{c}", origen_tabla="lineas_diario", cuenta=c, descripcion=ctx.descripcion(c),
                       importe=d(s["sf"] * sg), datos={"cuenta": c, "naturaleza": ctx.naturaleza(c)}))
    return out, {}


def balance_importado(cx: Contexto, p: dict) -> tuple[list[dict], dict]:
    ctx = cx.libro()
    if not ctx.balance_importado():
        return [], {"observaciones": "No hay balance de comprobación importado para el periodo."}
    cuentas = getattr(cx, "cuentas_anexo", None) or ctx.hojas()
    out = []
    for c in cuentas:
        v = ctx.saldo_balance_importado(c)
        if v is None:
            continue
        sg = 1 if ctx.naturaleza(c) == "D" else -1
        out.append(rec(clave_registro=f"BI{c}", origen_tabla="saldos_cuenta", cuenta=c, importe=d(v * sg), datos={"cuenta": c}))
    return out, {}


# ------------------------------------------------------------------ archivos externos (homologación de la fase 2)
def leer_archivo(nombre: str, contenido: bytes, esquema: str, mapeo_guardado: dict | None = None, fila_encabezado: int | None = None,
                 mapeo_manual: dict | None = None) -> dict:
    fmt = archivos.detectar_formato(nombre, contenido)
    filas = archivos.leer_filas(contenido, fmt)
    if not filas:
        raise ErrorImportacion("El archivo no tiene filas.")
    if fila_encabezado is None:
        fila_encabezado, n_enc, _ = archivos.detectar_encabezado(filas, esquema)
    else:
        n_enc = 1
    enc = archivos.construir_encabezado(filas, fila_encabezado, n_enc)
    sug = homologacion.sugerir_mapeo(esquema, enc.nombres, mapeo_guardado)
    mapeo = {c: v["columna"] for c, v in sug.items()}
    if mapeo_manual:
        mapeo = {c: int(i) for c, i in mapeo_manual.items() if i is not None and str(i) != ""}
    ex = homologacion.extraer(esquema, filas, enc.inicio_datos, mapeo, homologacion.OpcionesLectura())
    return {"formato": fmt, "fila_encabezado": fila_encabezado, "encabezados": enc.nombres, "sugerencia": sug, "mapeo": mapeo,
            "registros": ex.registros, "observaciones": [o.mensaje or o.codigo for o in ex.observaciones[:200]],
            "excluidos": ex.excluidos, "filas_subtotal": ex.filas_subtotal,
            "mapeo_plantilla": homologacion.mapeo_a_plantilla(mapeo, enc.nombres, fila_encabezado == 0)}


def _periodo_texto(v, fecha=None) -> int | None:
    if v:
        m = re.search(r"(20\d{2})\D?(0[1-9]|1[0-2])", str(v))
        if m:
            return int(m.group(1)) * 100 + int(m.group(2))
    return fecha.year * 100 + fecha.month if fecha else None


def normalizar_archivo(esquema: str, registros: list[dict], nombre: str, conceptos_planilla: list[dict] | None = None) -> list[dict]:
    out = []
    h = hashlib.sha256(nombre.encode()).hexdigest()[:8]
    for i, r in enumerate(registros):
        fila = r.get("_fila")
        base = dict(clave_registro=f"F{h}:{fila}", origen_tabla="archivo", fila_origen=fila, fecha=r.get("fecha"),
                    periodo=_periodo_texto(r.get("periodo_texto"), r.get("fecha")), tipo_documento=norm_tipo_doc(r.get("tipo_documento")),
                    serie=r.get("serie"), numero=r.get("numero_documento"), tercero=r.get("documento_tercero"),
                    razon_social=r.get("razon_social"), referencia=r.get("referencia") or r.get("documento_referencia"),
                    operacion=r.get("numero_operacion"), descripcion=r.get("glosa"), cuenta=r.get("cuenta"),
                    centro_costo=r.get("centro_costo"), proyecto=r.get("proyecto"), moneda=r.get("moneda") or "PEN",
                    tipo_cambio=r.get("tipo_cambio"), importe=r.get("importe") or CERO, importe_me=r.get("importe_me"))
        if esquema == "CONC_PLANILLA":
            conc = normalizar_texto(r.get("concepto") or "")
            for m in conceptos_planilla or []:
                if conc in [normalizar_texto(x) for x in m["conceptos"]]:
                    clave = {"trabajador": r.get("documento_tercero"), "centro_costo": r.get("centro_costo") or "(sin centro de costo)"}.get(m["por"], "TOTAL")
                    out.append(rec(**{**base, "clave_registro": f"F{h}:{fila}:{m['grupo']}", "concepto": m["grupo"], "personal": True,
                                      "datos": {"clave": clave, "concepto_planilla": conc, "tipo_concepto": r.get("tipo_concepto"),
                                                "tipo_planilla": r.get("tipo_planilla")}}))
            continue
        if esquema == "CONC_KARDEX":
            datos = {k: (str(r[k]) if r.get(k) is not None else None) for k in
                     ("cantidad_inicial", "cantidad_entradas", "cantidad_salidas", "cantidad_final", "costo_unitario", "valor_inicial",
                      "valor_entradas", "valor_salidas", "valor_final")}
            datos.update(producto=r.get("producto"), almacen=r.get("almacen"), unidad=r.get("unidad"), cuenta=r.get("cuenta"))
            out.append(rec(**{**base, "clave_registro": f"K{h}:{r.get('producto')}|{r.get('almacen') or ''}|{fila}",
                              "importe": r.get("valor_final") or CERO, "cantidad": r.get("cantidad_final"), "concepto": r.get("producto"),
                              "datos": datos}))
            continue
        if esquema == "CONC_COSTOS":
            out.append(rec(**{**base, "concepto": concepto_costo(r.get("concepto")), "datos": {"orden_servicio": r.get("orden_servicio"),
                                                                                              "concepto_original": r.get("concepto")}}))
            continue
        if esquema == "CONC_CONSTANCIAS":
            out.append(rec(**{**base, "operacion": r.get("numero_constancia"), "datos": {"codigo": r.get("codigo_detraccion")}}))
            continue
        if esquema == "CONC_RETENCIONES":
            out.append(rec(**{**base, "concepto": normalizar_texto(r.get("tipo_retencion") or "RETENCION"),
                              "datos": {"base": str(r["base_imponible"]) if r.get("base_imponible") is not None else None}}))
            continue
        if esquema == "CONC_DECLARACIONES":
            ob = r.get("obligacion") or CERO
            out.append(rec(**{**base, "concepto": codigo_tributo(r.get("tributo")), "importe": ob, "operacion": r.get("numero_orden"),
                              "datos": {"obligacion": str(ob), "pagos": str(r.get("pagos") or 0),
                                        "creditos": str((r.get("creditos") or 0) + (r.get("compensaciones") or 0))}}))
            continue
        if esquema == "CONC_SALDOS":
            out.append(rec(**{**base, "importe": r.get("saldo") or CERO, "datos": {"cuenta": r.get("cuenta")}}))
            continue
        base["datos"] = {"contrato": r.get("contrato")} if r.get("contrato") else {}
        out.append(rec(**base))
    return out


CONSTRUCTORES = {"LIBRO": libro, "BANCO": banco, "REGISTRO": registro, "LIBRO_DOCUMENTOS": libro_documentos,
                 "ACTIVOS_REGISTRO": activos_registro, "ACTIVOS_LIBRO": activos_libro, "INVENTARIO_LIBRO": inventario_libro,
                 "COSTOS_LIBRO": costos_libro, "CUOTAS": cuotas, "FINANCIERAS_LIBRO": financieras_libro,
                 "DETRACCION_DOCUMENTOS": detraccion_documentos, "CONSTANCIAS_LIBRO": constancias_libro, "TRIBUTOS_LIBRO": tributos_libro,
                 "EMPRESA_RELACIONADA": empresa_relacionada, "DESTINO_ORIGEN": lambda cx, p: destino(cx, p, "ORIGEN"),
                 "DESTINO_DESTINO": lambda cx, p: destino(cx, p, "DESTINO"), "DESTINO_TRANSFERENCIA": lambda cx, p: destino(cx, p, "TRANSFERENCIA"),
                 "ANEXO": anexo, "MAYOR": mayor, "BALANCE_IMPORTADO": balance_importado}
TIPOS_FUENTE = sorted(list(CONSTRUCTORES) + ["ARCHIVO", "PLANILLA_LIBRO"])

