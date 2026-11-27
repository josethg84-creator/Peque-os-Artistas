"""Reglas configurables por el contador (diseñador visual), sin código ni SQL.

Definición declarativa:
{"fuente": "LINEAS" | "ASIENTOS" | "SALDOS" | "COMPRAS" | "VENTAS",
 "condiciones": {"y": [ {"campo": "cuenta", "op": "empieza", "valor": "63"}, {"o": [ … ]} ]},
 "agrupar": {"por": ["tercero"], "medida": "suma" | "conteo" | "maximo", "campo": "importe", "op": ">", "valor": 10000},   (opcional)
 "titulo": "texto con {campo}"}
Los campos y operadores están en listas blancas; los valores se comparan con tipos validados.
"""
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from app.auditoria.base import CERO, Res, Salida, asiento_de, dec, doc_de, ev_calc, ev_linea, ev_reg
from app.importers.normalizacion import normalizar_texto

CAMPOS = {
    "LINEAS": {"cuenta": "texto", "debe": "num", "haber": "num", "importe": "num", "tercero": "texto", "razon_social": "texto", "glosa": "texto",
               "centro_costo": "texto", "proyecto": "texto", "fecha": "fecha", "fecha_emision": "fecha", "periodo": "num", "tipo_documento": "texto",
               "serie": "texto", "numero": "texto", "moneda": "texto", "usuario_registro": "texto", "origen_asiento": "texto", "asiento": "texto",
               "maquinaria": "texto"},
    "ASIENTOS": {"asiento": "texto", "periodo": "num", "fecha": "fecha", "total": "num", "lineas": "num", "cuentas": "texto", "sin_documento": "bool",
                 "glosa": "texto"},
    "SALDOS": {"cuenta": "texto", "saldo_inicial": "num", "debe": "num", "haber": "num", "saldo_final": "num", "movimientos": "num"},
    "COMPRAS": {"tercero": "texto", "razon_social": "texto", "tipo_documento": "texto", "serie": "texto", "numero": "texto", "fecha_emision": "fecha",
                "base": "num", "igv": "num", "total": "num", "moneda": "texto", "codigo_detraccion": "texto"},
}
CAMPOS["VENTAS"] = CAMPOS["COMPRAS"]
OPERADORES = {"=", "!=", ">", ">=", "<", "<=", "entre", "contiene", "no_contiene", "empieza", "no_empieza", "vacio", "no_vacio", "en", "no_en"}
MEDIDAS = {"suma", "conteo", "maximo", "promedio"}


class ErrorDefinicion(Exception):
    status = 422


def validar(defi: dict) -> dict:
    if not isinstance(defi, dict) or defi.get("fuente") not in CAMPOS:
        raise ErrorDefinicion(f"Fuente no válida. Use una de: {', '.join(CAMPOS)}.")
    campos = CAMPOS[defi["fuente"]]

    def chk(c, prof=0):
        if prof > 6:
            raise ErrorDefinicion("Demasiados niveles de condiciones anidadas.")
        if not isinstance(c, dict):
            raise ErrorDefinicion("Condición no válida.")
        for logico in ("y", "o"):
            if logico in c:
                if not isinstance(c[logico], list) or not c[logico]:
                    raise ErrorDefinicion(f"El grupo «{logico}» debe contener condiciones.")
                for x in c[logico]:
                    chk(x, prof + 1)
                return
        if c.get("campo") not in campos:
            raise ErrorDefinicion(f"Campo no permitido: {c.get('campo')}. Campos de {defi['fuente']}: {', '.join(campos)}.")
        if c.get("op") not in OPERADORES:
            raise ErrorDefinicion(f"Operador no permitido: {c.get('op')}.")
        if c["op"] not in ("vacio", "no_vacio"):
            _valor(campos[c["campo"]], c.get("valor"), c["op"])
    chk(defi.get("condiciones") or {"y": [{"campo": next(iter(campos)), "op": "no_vacio"}]})
    a = defi.get("agrupar")
    if a:
        if any(p not in campos for p in a.get("por", [])) or a.get("medida") not in MEDIDAS or a.get("op") not in {">", ">=", "<", "<=", "=", "!="}:
            raise ErrorDefinicion("Agrupación no válida (campos, medida u operador).")
        if a.get("medida") != "conteo" and campos.get(a.get("campo")) != "num":
            raise ErrorDefinicion("La medida de la agrupación debe usar un campo numérico.")
        _valor("num", a.get("valor"), a["op"])
    return defi


def _valor(tipo, v, op):
    try:
        if op in ("entre",):
            if not isinstance(v, list) or len(v) != 2:
                raise ErrorDefinicion("«entre» requiere dos valores.")
            return [_valor(tipo, x, "=") for x in v]
        if op in ("en", "no_en"):
            if not isinstance(v, list):
                raise ErrorDefinicion(f"«{op}» requiere una lista.")
            return [_valor(tipo, x, "=") for x in v]
        if tipo == "num":
            return Decimal(str(v))
        if tipo == "fecha":
            return date.fromisoformat(str(v))
        if tipo == "bool":
            return str(v).lower() in ("1", "true", "si", "sí")
        if v is None or len(str(v)) > 200:
            raise ErrorDefinicion("Valor de texto vacío o demasiado largo.")
        return normalizar_texto(str(v))
    except (InvalidOperation, ValueError, TypeError):
        raise ErrorDefinicion(f"Valor no válido para un campo {tipo}: {v}")


def _cumple(reg: dict, c: dict, campos: dict) -> bool:
    if "y" in c:
        return all(_cumple(reg, x, campos) for x in c["y"])
    if "o" in c:
        return any(_cumple(reg, x, campos) for x in c["o"])
    tipo, op = campos[c["campo"]], c["op"]
    v = reg.get(c["campo"])
    if op == "vacio":
        return v in (None, "", 0) and v is not False
    if op == "no_vacio":
        return v not in (None, "")
    if v is None:
        return False
    obj = _valor(tipo, c.get("valor"), op)
    if tipo == "texto":
        v = normalizar_texto(str(v))
    if op == "=":
        return v == obj
    if op == "!=":
        return v != obj
    if op in (">", ">=", "<", "<="):
        return {">": v > obj, ">=": v >= obj, "<": v < obj, "<=": v <= obj}[op]
    if op == "entre":
        return obj[0] <= v <= obj[1]
    if op == "contiene":
        return obj in v
    if op == "no_contiene":
        return obj not in v
    if op == "empieza":
        return str(v).startswith(obj)
    if op == "no_empieza":
        return not str(v).startswith(obj)
    if op == "en":
        return v in obj
    if op == "no_en":
        return v not in obj
    return False


def _registros(ax, fuente):
    if fuente == "LINEAS":
        for ln in ax.lineas:
            yield {"cuenta": ln.cuenta, "debe": ln.debe, "haber": ln.haber, "importe": ln.debe + ln.haber, "tercero": ln.tercero,
                   "razon_social": ln.razon_social, "glosa": ln.glosa, "centro_costo": ln.cc, "proyecto": ln.proyecto, "fecha": ln.fecha,
                   "fecha_emision": ln.fecha_emision, "periodo": Decimal(ln.periodo or 0), "tipo_documento": ln.tipo_doc, "serie": ln.serie,
                   "numero": ln.numero, "moneda": ln.moneda, "usuario_registro": ln.usuario_registro, "origen_asiento": ln.origen_asiento,
                   "asiento": asiento_de(ln), "maquinaria": ln.maquinaria, "_ln": ln}
    elif fuente == "ASIENTOS":
        for k, ls in ax.asientos.items():
            yield {"asiento": "-".join(p for p in (k[2], k[3]) if p), "periodo": Decimal(k[1]), "fecha": ls[0].fecha,
                   "total": sum((x.debe for x in ls), CERO), "lineas": Decimal(len(ls)), "cuentas": " ".join(sorted({x.cuenta for x in ls})),
                   "sin_documento": not any(x.numero for x in ls), "glosa": ls[0].glosa, "_ln": ls[0], "_ls": ls}
    elif fuente == "SALDOS":
        for c, n in ax.ctx3.nodos.items():
            if n.hijos == 0 or n.propio:
                yield {"cuenta": c, "saldo_inicial": dec(n.si) / 100, "debe": dec(n.debe) / 100, "haber": dec(n.haber) / 100,
                       "saldo_final": dec(n.sf) / 100, "movimientos": Decimal(n.n)}
    else:
        for d in ax.documentos(fuente):
            yield {"tercero": d.documento_tercero, "razon_social": d.razon_social, "tipo_documento": d.tipo_documento, "serie": d.serie, "numero": d.numero,
                   "fecha_emision": d.fecha_emision, "base": dec(d.base_imponible), "igv": dec(d.igv), "total": dec(d.total), "moneda": d.moneda,
                   "codigo_detraccion": d.codigo_detraccion, "_doc": d}


def _importe(reg) -> Decimal:
    for k in ("importe", "total", "saldo_final"):
        if reg.get(k) is not None:
            return abs(dec(reg[k]))
    return CERO


def _titulo(defi, reg, defecto):
    t = defi.get("titulo") or defecto
    return re.sub(r"\{(\w+)\}", lambda m: str(reg.get(m.group(1), "")), t)[:250]


def evaluar(ax, r, limite: int | None = None) -> Salida:
    defi = validar(r.definicion or {})
    campos = CAMPOS[defi["fuente"]]
    cond = defi.get("condiciones") or {"y": []}
    n, out = 0, []
    agrupados = defaultdict(list)
    for reg in _registros(ax, defi["fuente"]):
        n += 1
        if cond.get("y") == [] or _cumple(reg, cond, campos):
            if defi.get("agrupar"):
                agrupados[tuple(str(reg.get(p) or "") for p in defi["agrupar"]["por"])].append(reg)
            else:
                out.append(_res(ax, r, defi, reg))
                if limite and len(out) >= limite:
                    break
    if defi.get("agrupar"):
        a = defi["agrupar"]
        for k, regs in agrupados.items():
            vals = [dec(x.get(a.get("campo"))) for x in regs]
            m = {"suma": sum(vals, CERO), "conteo": Decimal(len(regs)), "maximo": max(vals) if vals else CERO,
                 "promedio": (sum(vals, CERO) / len(vals)) if vals else CERO}[a["medida"]]
            obj = Decimal(str(a["valor"]))
            if {">": m > obj, ">=": m >= obj, "<": m < obj, "<=": m <= obj, "=": m == obj, "!=": m != obj}[a["op"]]:
                g = dict(zip(a["por"], k))
                x = Res(titulo=_titulo(defi, g, f"{r.nombre}: " + ", ".join(f"{p} {v}" for p, v in g.items())), condicion=f"{a['medida']} de "
                        f"{a.get('campo') or 'registros'} = {m} ({a['op']} {obj}) en {len(regs)} registros.", importe=sum((_importe(y) for y in regs), CERO),
                        cuenta=g.get("cuenta"), tercero=g.get("tercero"), evidencia=[ev_calc("Agrupación", medida=a["medida"], valor=m, umbral=obj, registros=len(regs))]
                        + [ev_linea(y["_ln"]) for y in regs[:10] if y.get("_ln")], clave=f"CFG|{r.codigo}|{'|'.join(k)}",
                        exposicion=f"CFG|{r.codigo}|{'|'.join(k)}", calidad="PARCIAL")
                out.append(x)
                if limite and len(out) >= limite:
                    break
    return Salida(out, n, metodo=f"Regla configurable sobre {defi['fuente']}: condiciones declarativas (sin código ni SQL).")


def _res(ax, r, defi, reg) -> Res:
    ln = reg.get("_ln")
    if ln is not None:
        ev = [ev_linea(x) for x in reg.get("_ls", [ln])[:15]]
        return Res(titulo=_titulo(defi, reg, f"{r.nombre}: {reg.get('cuenta') or reg.get('asiento') or ''}"), condicion=f"Cumple las condiciones de la "
                   f"regla {r.codigo}.", importe=_importe(reg), cuenta=ln.cuenta, tercero=ln.tercero, documento=doc_de(ln), asiento=asiento_de(ln),
                   linea_id=ln.id, centro_costo=ln.cc, proyecto=ln.proyecto, evidencia=ev,
                   clave=f"CFG|{r.codigo}|{ln.id if defi['fuente'] == 'LINEAS' else reg.get('asiento')}|{ln.periodo}",
                   exposicion=f"LINEA|{ln.id}" if defi["fuente"] == "LINEAS" else f"ASIENTO|{ln.lote_id}|{ln.periodo}|{asiento_de(ln)}")
    d = reg.get("_doc")
    if d is not None:
        return Res(titulo=_titulo(defi, reg, f"{r.nombre}: {d.serie}-{d.numero}"), condicion=f"Cumple las condiciones de la regla {r.codigo}.",
                   importe=_importe(reg), tercero=d.documento_tercero, documento=f"{d.serie}-{d.numero}",
                   evidencia=[ev_reg("documentos_registro", d.id, f"{d.serie}-{d.numero}")], clave=f"CFG|{r.codigo}|DOC|{d.id}",
                   exposicion=f"DOC|{d.documento_tercero}|{d.serie}-{d.numero}")
    return Res(titulo=_titulo(defi, reg, f"{r.nombre}: cuenta {reg.get('cuenta')}"), condicion=f"Cumple las condiciones de la regla {r.codigo}.",
               importe=_importe(reg), cuenta=reg.get("cuenta"), evidencia=[ev_calc("Saldo de la cuenta", **{k: v for k, v in reg.items() if not k.startswith("_")})],
               clave=f"CFG|{r.codigo}|{reg.get('cuenta')}", exposicion=f"CUENTA|{reg.get('cuenta')}")


EVALUADORES = {"configurable": evaluar}
