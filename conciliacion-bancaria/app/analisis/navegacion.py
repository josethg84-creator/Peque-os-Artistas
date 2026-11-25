"""Navegación progresiva: balance → cuenta → subcuenta → tercero → documento → asiento → línea original.

Todas las consultas se filtran por empresa y por las fuentes vigentes (lotes activos, sin duplicar
diario/mayor). Nada se modifica: solo lectura.
"""
import functools
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, literal, or_, select
from sqlalchemy.orm import Session

from app.analisis.saldos import CERO, Fuentes, cent, dec, fuentes
from app.contable import archivos
from app.models import LineaDiario, LoteContable, SaldoCuenta


class NoEncontrado(Exception):
    status = 404


@dataclass
class Filtros:
    cuenta: str | None = None        # prefijo: 12 incluye 1212, 121201…
    tercero: str | None = None
    documento: str | None = None     # «serie-número» o solo número
    centro_costo: str | None = None
    proyecto: str | None = None
    maquinaria: str | None = None
    moneda: str | None = None
    texto: str | None = None

    def aplicar(self, q):
        if self.cuenta:
            q = q.where(LineaDiario.cuenta.like(f"{self.cuenta}%"))
        if self.tercero:
            q = q.where(LineaDiario.documento_tercero == self.tercero) if self.tercero != "(sin tercero)" \
                else q.where(LineaDiario.documento_tercero.is_(None))
        if self.documento:
            if "-" in self.documento:
                serie, numero = self.documento.rsplit("-", 1)
                q = q.where(func.coalesce(LineaDiario.serie, "") == serie, LineaDiario.numero_documento == numero)
            elif self.documento == "(sin documento)":
                q = q.where(LineaDiario.numero_documento.is_(None))
            else:
                q = q.where(LineaDiario.numero_documento == self.documento)
        for campo, col in (("centro_costo", LineaDiario.centro_costo), ("proyecto", LineaDiario.proyecto),
                           ("maquinaria", LineaDiario.activo_maquinaria), ("moneda", LineaDiario.moneda)):
            v = getattr(self, campo)
            if v:
                q = q.where(col.is_(None)) if v == "(vacío)" else q.where(col == v)
        if self.texto:
            p = f"%{self.texto}%"
            q = q.where(or_(LineaDiario.glosa.ilike(p), LineaDiario.razon_social.ilike(p),
                            LineaDiario.numero_documento.ilike(p), LineaDiario.numero_asiento.ilike(p),
                            LineaDiario.documento_tercero.ilike(p), LineaDiario.cuenta.ilike(p)))
        return q

    @property
    def solo_cuenta(self) -> bool:
        return not any((self.documento, self.centro_costo, self.proyecto, self.maquinaria, self.moneda, self.texto))


def _apertura(db: Session, f: Fuentes, filtros: Filtros, por_tercero=False):
    """Saldos de apertura (saldos iniciales importados) aplicables al filtro."""
    if f.apertura != "SALDOS_INICIALES" or not filtros.solo_cuenta:
        return {}
    q = select(SaldoCuenta.documento_tercero if por_tercero else literal("*"),
               cent(SaldoCuenta.saldo_inicial_debe) - cent(SaldoCuenta.saldo_inicial_haber)) \
        .where(SaldoCuenta.lote_id.in_(f.lotes_apertura))
    if filtros.cuenta:
        q = q.where(SaldoCuenta.cuenta.like(f"{filtros.cuenta}%"))
    if filtros.tercero:
        q = q.where(SaldoCuenta.documento_tercero == filtros.tercero)
    return {k: int(v) for k, v in db.execute(q.group_by(SaldoCuenta.documento_tercero if por_tercero else literal("*")))}


def _filtro_previo(f: Fuentes, desde: int):
    return f.filtro_lineas(0 if f.apertura == "DIARIO_00" else 1, desde - 1, incluir_apertura_diario=f.apertura == "DIARIO_00")


def terceros(db: Session, empresa_id: int, ejercicio: int, desde: int, hasta: int, filtros: Filtros) -> dict:
    f = fuentes(db, empresa_id, ejercicio)
    clave = func.coalesce(LineaDiario.documento_tercero, "(sin tercero)")
    filas: dict[str, dict] = {}

    def fila(t):
        return filas.setdefault(t, {"tercero": t, "razon_social": None, "si": 0, "debe": 0, "haber": 0, "movimientos": 0,
                                    "documentos": 0})
    for t, v in _apertura(db, f, filtros, por_tercero=True).items():
        fila(t or "(sin tercero)")["si"] += v
    q = filtros.aplicar(select(clave, cent(LineaDiario.debe_mn) - cent(LineaDiario.haber_mn)).where(_filtro_previo(f, desde)))
    for t, v in db.execute(q.group_by(clave)):
        fila(t)["si"] += int(v)
    q = filtros.aplicar(select(clave, func.max(LineaDiario.razon_social), cent(LineaDiario.debe_mn), cent(LineaDiario.haber_mn),
                               func.count(), func.count(func.distinct(LineaDiario.numero_documento)))
                        .where(f.filtro_lineas(desde, hasta)))
    for t, rs, d, h, n, docs in db.execute(q.group_by(clave)):
        x = fila(t)
        x.update(razon_social=rs, debe=int(d), haber=int(h), movimientos=n, documentos=docs)
    items = []
    for x in filas.values():
        sf = x["si"] + x["debe"] - x["haber"]
        if not (x["si"] or x["debe"] or x["haber"]):
            continue
        items.append({**x, "si": str(dec(x["si"])), "debe": str(dec(x["debe"])), "haber": str(dec(x["haber"])),
                      "saldo_final": str(dec(sf)), "_abs": abs(sf)})
    items.sort(key=lambda x: (-x["_abs"], x["tercero"]))
    for x in items:
        x.pop("_abs")
    return {"items": items, "total": len(items)}


def documentos(db: Session, empresa_id: int, ejercicio: int, desde: int, hasta: int, filtros: Filtros) -> dict:
    """Composición por documento (tipo · serie · número) de la cuenta y tercero filtrados."""
    f = fuentes(db, empresa_id, ejercicio)
    hasta_filtro = f.filtro_lineas(0 if f.apertura == "DIARIO_00" else 1, hasta, incluir_apertura_diario=f.apertura == "DIARIO_00")
    clave = (LineaDiario.tipo_documento, LineaDiario.serie, LineaDiario.numero_documento, LineaDiario.documento_tercero)
    rango = LineaDiario.periodo >= desde
    q = filtros.aplicar(select(*clave, func.max(LineaDiario.razon_social),
                               cent(LineaDiario.debe_mn) - cent(LineaDiario.haber_mn),
                               func.sum(func.round(LineaDiario.debe_mn * 100)).filter(rango),
                               func.sum(func.round(LineaDiario.haber_mn * 100)).filter(rango),
                               func.min(func.coalesce(LineaDiario.fecha_emision, LineaDiario.fecha_contable)),
                               func.max(LineaDiario.fecha_vencimiento), func.count())
                        .where(hasta_filtro)).group_by(*clave)
    items = []
    for td, serie, num, ter, rs, saldo, d, h, emision, venc, n in db.execute(q):
        d, h = int(d or 0), int(h or 0)
        sf = int(saldo)
        items.append({"tipo_documento": td, "serie": serie, "numero": num, "documento": f"{serie}-{num}" if serie else (num or "(sin documento)"),
                      "tercero": ter, "razon_social": rs, "si": str(dec(sf - d + h)), "debe": str(dec(d)), "haber": str(dec(h)),
                      "saldo_final": str(dec(sf)), "fecha_emision": emision.isoformat() if emision else None,
                      "fecha_vencimiento": venc.isoformat() if venc else None, "movimientos": n, "pendiente": sf != 0})
    items.sort(key=lambda x: (not x["pendiente"], x["fecha_emision"] or "", x["documento"]))
    return {"items": items, "total": len(items)}


COLUMNAS_MOV = (LineaDiario.id, LineaDiario.lote_id, LineaDiario.periodo, LineaDiario.fecha_contable, LineaDiario.subdiario,
                LineaDiario.numero_asiento, LineaDiario.numero_linea, LineaDiario.glosa, LineaDiario.cuenta,
                LineaDiario.descripcion_cuenta, LineaDiario.tipo_documento, LineaDiario.serie, LineaDiario.numero_documento,
                LineaDiario.documento_tercero, LineaDiario.razon_social, LineaDiario.moneda, LineaDiario.tipo_cambio,
                LineaDiario.debe_mn, LineaDiario.haber_mn, LineaDiario.debe_me, LineaDiario.haber_me, LineaDiario.centro_costo,
                LineaDiario.proyecto, LineaDiario.activo_maquinaria, LineaDiario.fecha_emision, LineaDiario.fecha_vencimiento,
                LineaDiario.hoja, LineaDiario.fila_origen)
ORDEN_MOV = (LineaDiario.fecha_contable, LineaDiario.periodo, LineaDiario.subdiario, LineaDiario.numero_asiento,
             LineaDiario.numero_linea, LineaDiario.id)


def _fila_mov(r, archivo=None) -> dict:
    d = {}
    for col, v in zip(COLUMNAS_MOV, r):
        d[col.key] = str(v) if isinstance(v, Decimal) else v.isoformat() if hasattr(v, "isoformat") else v
    d["archivo"] = archivo
    return d


def movimientos(db: Session, empresa_id: int, ejercicio: int, desde: int, hasta: int, filtros: Filtros,
                pagina: int = 1, por_pagina: int = 100) -> dict:
    """Movimientos filtrados con saldo acumulado (parte del saldo inicial del mismo filtro)."""
    f = fuentes(db, empresa_id, ejercicio)
    si = sum(_apertura(db, f, filtros).values())
    si += int(db.scalar(filtros.aplicar(select(cent(LineaDiario.debe_mn) - cent(LineaDiario.haber_mn))
                                        .where(_filtro_previo(f, desde)))) or 0)
    base = filtros.aplicar(select(*COLUMNAS_MOV).where(f.filtro_lineas(desde, hasta)))
    total, td, th = db.execute(filtros.aplicar(select(func.count(), cent(LineaDiario.debe_mn), cent(LineaDiario.haber_mn))
                                               .where(f.filtro_lineas(desde, hasta)))).one()
    acumulado = func.sum(func.round((LineaDiario.debe_mn - LineaDiario.haber_mn) * 100)).over(order_by=ORDEN_MOV)
    sub = base.add_columns(acumulado.label("acum"), LoteContable.nombre_archivo) \
        .join(LoteContable, LoteContable.id == LineaDiario.lote_id).subquery()
    por_pagina = max(1, min(por_pagina, 1000))
    orden = [sub.c[c.key] for c in ORDEN_MOV]
    filas = db.execute(select(sub).order_by(*orden).offset((max(pagina, 1) - 1) * por_pagina).limit(por_pagina)).all()
    items = []
    for r in filas:
        x = _fila_mov(r[:len(COLUMNAS_MOV)], r[-1])
        x["saldo_acumulado"] = str(dec(si + int(r[-2] or 0)))
        items.append(x)
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina, "saldo_inicial": str(dec(si)),
            "total_debe": str(dec(td)), "total_haber": str(dec(th)), "saldo_final": str(dec(si + int(td) - int(th))),
            "items": items}


def _linea(db: Session, empresa_id: int, linea_id: int) -> LineaDiario:
    ln = db.get(LineaDiario, linea_id)
    if not ln or ln.empresa_id != empresa_id:  # aislamiento multiempresa
        raise NoEncontrado("Movimiento no encontrado")
    return ln


def asiento(db: Session, empresa_id: int, linea_id: int) -> dict:
    """Asiento completo (con contrapartidas) al que pertenece la línea."""
    ln = _linea(db, empresa_id, linea_id)
    q = select(*COLUMNAS_MOV).where(LineaDiario.lote_id == ln.lote_id, LineaDiario.empresa_id == empresa_id)
    if ln.numero_asiento:
        q = q.where(LineaDiario.numero_asiento == ln.numero_asiento, LineaDiario.periodo == ln.periodo,
                    func.coalesce(LineaDiario.subdiario, "") == (ln.subdiario or ""))
    else:
        q = q.where(LineaDiario.id == ln.id)
    lote = db.get(LoteContable, ln.lote_id)
    lineas = [_fila_mov(r, lote.nombre_archivo) for r in db.execute(q.order_by(LineaDiario.numero_linea, LineaDiario.id))]
    d = sum((Decimal(x["debe_mn"]) for x in lineas), CERO)
    h = sum((Decimal(x["haber_mn"]) for x in lineas), CERO)
    return {"linea_id": linea_id, "asiento": "-".join(p for p in (ln.subdiario, ln.numero_asiento) if p) or None,
            "periodo": ln.periodo, "ejercicio": ln.ejercicio, "fecha": ln.fecha_contable.isoformat() if ln.fecha_contable else None,
            "lote": {"id": lote.id, "archivo": lote.nombre_archivo, "tipo": lote.tipo_informacion, "estado": lote.estado},
            "lineas": lineas, "total_debe": str(d), "total_haber": str(h), "cuadra": d == h}


@functools.lru_cache(maxsize=4)
def _filas_archivo(lote_id: int, hoja: str | None, delimitador: str, fila_enc: int, filas_enc: int, _hash: str):
    meta_y_datos = archivos.archivo_de_lote(lote_id, _hash)
    if not meta_y_datos:
        return None
    meta, datos = meta_y_datos
    filas = archivos.leer_filas(datos, meta["formato"], hoja, delimitador)
    enc = archivos.construir_encabezado(filas, fila_enc, filas_enc)
    return enc.nombres, filas


def linea_original(db: Session, empresa_id: int, linea_id: int) -> dict:
    """Nivel 7: la fila tal como venía en el archivo importado, junto a su versión normalizada."""
    import json
    ln = _linea(db, empresa_id, linea_id)
    lote = db.get(LoteContable, ln.lote_id)
    normalizada = {c.key: (str(getattr(ln, c.key)) if isinstance(getattr(ln, c.key), Decimal) else
                           getattr(ln, c.key).isoformat() if hasattr(getattr(ln, c.key), "isoformat") else getattr(ln, c.key))
                   for c in LineaDiario.__table__.columns}
    opciones = json.loads(lote.opciones or "{}")
    res = {"lote": {"id": lote.id, "archivo": lote.nombre_archivo, "hoja": lote.hoja, "sistema": lote.sistema_origen,
                    "usuario": lote.usuario, "fecha": lote.creado_en.isoformat() if lote.creado_en else None,
                    "estado": lote.estado, "hash": lote.hash_archivo},
           "fila": ln.fila_origen, "normalizada": normalizada, "original": None,
           "mapeo": json.loads(lote.mapeo or "{}")}
    datos = _filas_archivo(lote.id, lote.hoja, opciones.get("delimitador", "AUTO"), lote.fila_encabezado,
                           opciones.get("filas_encabezado", 1), lote.hash_archivo)
    if datos is None:
        res["aviso"] = "El archivo original de este lote no está archivado (lotes importados antes de la fase 3)."
    elif ln.fila_origen and ln.fila_origen <= len(datos[1]):
        nombres, filas = datos
        fila = filas[ln.fila_origen - 1]
        res["original"] = [{"columna": nombres[i] if i < len(nombres) else f"Columna {i + 1}",
                            "valor": archivos.valor_texto(v)} for i, v in enumerate(fila)]
    return res
