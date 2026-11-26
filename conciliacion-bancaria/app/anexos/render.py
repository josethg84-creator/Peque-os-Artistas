"""Aplicación de la plantilla a las filas de una versión: columnas, filtros, campos calculados, orden,
agrupaciones, subtotales y totales. Lo usan la pantalla, la vista de impresión y las exportaciones.

Los filtros de la plantilla son de PRESENTACIÓN: la conciliación del anexo siempre considera el detalle
completo de la versión.
"""
import json
from collections import OrderedDict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.anexos import catalogo, expresiones
from app.models import DetalleAnexo

CERO = Decimal("0")
OPERADORES = ("=", "!=", ">", ">=", "<", "<=", "contiene", "empieza", "vacio", "no_vacio")
_FIJAS = [c.key for c in DetalleAnexo.__table__.columns if c.key not in ("id", "version_id", "anexo_id", "orden", "datos")]


def tipos(especialidad: str, formulas=()) -> dict:
    t = {c: tp for c, _, tp in catalogo.campos(especialidad)}
    for f in formulas:
        t[f["campo"]] = f.get("tipo", "importe")
    return t


def _conv(v, tipo):
    if v is None or v == "":
        return None
    if tipo in ("importe", "pct", "tasa"):
        return v if isinstance(v, Decimal) else Decimal(str(v))
    if tipo == "entero":
        return int(v)
    if tipo == "fecha":
        return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])
    return v


def filas_version(db: Session, version_id: int, especialidad: str) -> list[dict]:
    t = tipos(especialidad)
    cols = [getattr(DetalleAnexo, c) for c in _FIJAS] + [DetalleAnexo.datos, DetalleAnexo.id]
    out = []
    for r in db.execute(select(*cols).where(DetalleAnexo.version_id == version_id).order_by(DetalleAnexo.orden)):
        d = dict(zip(_FIJAS, r[:len(_FIJAS)]))
        d["id"] = r[-1]
        d["documento"] = (f"{d['serie']}-{d['numero']}" if d["serie"] else d["numero"]) if d["numero"] else None
        extra = json.loads(r[-2]) if r[-2] else {}
        for k, v in extra.items():
            d[k] = _conv(v, t.get(k, "texto")) if not isinstance(v, (bool, dict, list)) else v
        out.append(d)
    return out


def _cumple(fila: dict, f: dict) -> bool:
    v = fila.get(f["campo"])
    op, val = f.get("op", "="), f.get("valor")
    if op == "vacio":
        return v in (None, "")
    if op == "no_vacio":
        return v not in (None, "")
    if op == "contiene":
        return str(val or "").upper() in str(v or "").upper()
    if op == "empieza":
        return str(v or "").upper().startswith(str(val or "").upper())
    if isinstance(v, Decimal) or isinstance(v, int):
        try:
            val = Decimal(str(val))
        except Exception:
            return False
    elif isinstance(v, date):
        try:
            val = date.fromisoformat(str(val)[:10])
        except ValueError:
            return False
    else:
        v, val = str(v or "").upper(), str(val or "").upper()
    try:
        return {"=": v == val, "!=": v != val, ">": v > val, ">=": v >= val, "<": v < val, "<=": v <= val}[op]
    except TypeError:
        return False


def validar_formulas(especialidad: str, formulas: list[dict]) -> None:
    disponibles = set(tipos(especialidad)) | {"documento"}
    for f in formulas:
        if not f.get("campo") or not f["campo"].isidentifier():
            raise expresiones.ErrorExpresion(f"Nombre de campo calculado no válido: {f.get('campo')}")
        if f["campo"] in disponibles:
            raise expresiones.ErrorExpresion(f"El campo calculado «{f['campo']}» ya existe.")
        expresiones.compilar(f["expresion"], disponibles)
        disponibles.add(f["campo"])


def aplicar(snap: dict, filas: list[dict], *, filtros_extra: list | None = None, buscar: str | None = None,
            ignorar_filtros_plantilla=False) -> dict:
    formulas = snap.get("formulas", [])
    t = tipos(snap["especialidad"], formulas)
    errores = []
    if formulas:
        compiladas = []
        for f in formulas:
            try:
                compiladas.append((f, expresiones.compilar(f["expresion"])))
            except expresiones.ErrorExpresion as exc:
                errores.append(f"{f['campo']}: {exc}")
        for r in filas:
            for f, arbol in compiladas:
                try:
                    v = expresiones.evaluar(arbol, r)
                    r[f["campo"]] = _conv(v, f.get("tipo", "importe")) if not isinstance(v, bool) else v
                except (expresiones.ErrorExpresion, ValueError, ArithmeticError):
                    r[f["campo"]] = None
    total_filas = len(filas)
    flt = ([] if ignorar_filtros_plantilla else snap.get("filtros", [])) + (filtros_extra or [])
    if flt:
        filas = [r for r in filas if all(_cumple(r, f) for f in flt)]
    if buscar:
        b = buscar.upper()
        filas = [r for r in filas if any(b in str(r.get(k) or "").upper() for k in
                                         ("documento", "razon_social", "tercero", "glosa", "categoria", "cuenta", "proyecto", "referencia"))]
    for campo in reversed(snap.get("orden") or []):
        desc = campo.startswith("-")
        c = campo.lstrip("-")
        filas.sort(key=lambda r: (r.get(c) is None, r.get(c) if not isinstance(r.get(c), (date,)) else r.get(c).isoformat()), reverse=desc)
    cols = [c for c in snap["columnas"] if c.get("visible", True)]
    for f in formulas:
        if not any(c["campo"] == f["campo"] for c in cols):
            cols.append({"campo": f["campo"], "titulo": f["titulo"], "tipo": f.get("tipo", "importe"), "visible": True, "total": f.get("tipo") == "importe"})
    sumables = {c["campo"] for c in cols if c.get("total") and t.get(c["campo"], c.get("tipo")) in ("importe",)} | {"saldo"}
    subt = [c for c in snap.get("subtotales") or [] if c] or sorted(sumables)

    def suma(lst, campo):
        return sum(((r.get(campo) or CERO) for r in lst if isinstance(r.get(campo), (Decimal, int))), CERO)
    totales = {c: suma(filas, c) for c in sumables}
    grupos = []
    agrupar = [g for g in snap.get("agrupar_por") or [] if g]
    if agrupar:
        g = OrderedDict()
        for r in filas:
            k = tuple(str(r.get(a) or "—") for a in agrupar)
            g.setdefault(k, []).append(r)
        filas_ord = []
        for k, lst in g.items():
            grupos.append({"clave": " · ".join(k), "filas": len(lst), "subtotales": {c: suma(lst, c) for c in subt}})
            filas_ord.extend(lst)
        filas = filas_ord
    return {"columnas": [{**c, "tipo": t.get(c["campo"], c.get("tipo", "texto"))} for c in cols], "filas": filas,
            "grupos": grupos, "agrupar_por": agrupar, "subtotales": subt, "totales": totales, "total_filas": total_filas,
            "filas_filtradas": len(filas), "filtros_aplicados": flt, "errores_formulas": errores}


def serial(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, date):
        return v.isoformat()
    return v
