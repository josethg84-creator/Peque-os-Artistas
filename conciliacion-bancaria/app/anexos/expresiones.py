"""Motor seguro de expresiones para campos calculados y reglas de plantillas.

Se analiza la expresión con `ast` y se EVALÚA RECORRIENDO EL ÁRBOL con una lista blanca de nodos:
números, textos, nombres de campos de la fila, + − × ÷, comparaciones, Y/O/NO y funciones permitidas.
No hay `eval`, ni acceso a atributos, índices, importaciones, lambdas, comprensiones ni SQL.
La aritmética monetaria se hace con Decimal.
"""
import ast
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MAX_LARGO = 500
MAX_NODOS = 120


class ErrorExpresion(ValueError):
    pass


def _dec(v):
    if v is None or v == "":
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        return Decimal(int(v))
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    try:
        return Decimal(str(v))
    except InvalidOperation:
        raise ErrorExpresion(f"«{v}» no es un número")


def _fecha(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            pass
    return None


def _si(cond, a, b):
    return a if cond else b


def _redondear(v, n=2):
    return _dec(v).quantize(Decimal(1).scaleb(-int(_dec(n))), ROUND_HALF_UP)


def _dias(a, b):
    fa, fb = _fecha(a), _fecha(b)
    return Decimal((fa - fb).days) if fa and fb else None


def _contiene(texto, buscado):
    return str(buscado or "").upper() in str(texto or "").upper()


def _div(a, b):
    b = _dec(b)
    return None if b == 0 else _dec(a) / b


FUNCIONES = {
    "SI": _si, "IF": _si,
    "ABS": lambda v: abs(_dec(v)),
    "REDONDEAR": _redondear, "ROUND": _redondear,
    "MIN": lambda *a: min(_dec(x) for x in a), "MAX": lambda *a: max(_dec(x) for x in a),
    "SUMA": lambda *a: sum((_dec(x) for x in a), Decimal("0")),
    "DIVIDIR": _div,
    "DIAS": _dias,
    "COALESCE": lambda *a: next((x for x in a if x not in (None, "")), None),
    "CONTIENE": _contiene,
    "MAYUS": lambda v: str(v or "").upper(),
    "ES_VACIO": lambda v: v in (None, ""),
}
_BIN = {ast.Add: lambda a, b: _dec(a) + _dec(b), ast.Sub: lambda a, b: _dec(a) - _dec(b),
        ast.Mult: lambda a, b: _dec(a) * _dec(b), ast.Div: lambda a, b: _div(a, b),
        ast.Mod: lambda a, b: _dec(a) % _dec(b)}
_CMP = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: _dec(a) < _dec(b),
        ast.LtE: lambda a, b: _dec(a) <= _dec(b), ast.Gt: lambda a, b: _dec(a) > _dec(b),
        ast.GtE: lambda a, b: _dec(a) >= _dec(b)}
_PERMITIDOS = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call, ast.Name, ast.Constant,
               ast.Load, ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd, ast.IfExp, *_BIN, *_CMP)


def _normalizar(texto: str) -> str:
    # Sintaxis tipo hoja de cálculo: Y / O / NO, "<>" y "=" de comparación
    t = texto.strip()
    if t.startswith("="):
        t = t[1:]
    out, i, en_texto = [], 0, None
    while i < len(t):
        ch = t[i]
        if en_texto:
            out.append(ch)
            if ch == en_texto:
                en_texto = None
            i += 1
            continue
        if ch in "\"'":
            en_texto = ch
            out.append(ch)
        elif t.startswith("<>", i):
            out.append("!=")
            i += 1
        elif ch == "=" and (i == 0 or t[i - 1] not in "<>!=") and not t.startswith("==", i):
            out.append("==")
        else:
            out.append(ch)
        i += 1
    t = "".join(out)
    import re
    return re.sub(r"\bY\b", " and ", re.sub(r"\bO\b", " or ", re.sub(r"\bNO\b", " not ", t)))


def compilar(texto: str, campos: set[str] | None = None) -> ast.Expression:
    """Valida la expresión. `campos`: nombres de campos válidos (None = no se valida el nombre)."""
    if not texto or len(texto) > MAX_LARGO:
        raise ErrorExpresion(f"La expresión debe tener entre 1 y {MAX_LARGO} caracteres.")
    try:
        arbol = ast.parse(_normalizar(texto), mode="eval")
    except SyntaxError as exc:
        raise ErrorExpresion(f"Sintaxis no válida: {exc.msg}")
    nodos = list(ast.walk(arbol))
    if len(nodos) > MAX_NODOS:
        raise ErrorExpresion("La expresión es demasiado compleja.")
    for n in nodos:
        if not isinstance(n, _PERMITIDOS):
            raise ErrorExpresion(f"Elemento no permitido en una fórmula: {type(n).__name__}.")
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.func.id.upper() not in FUNCIONES or n.keywords:
                raise ErrorExpresion(f"Función no permitida: {getattr(n.func, 'id', '?')}. "
                                     f"Disponibles: {', '.join(sorted(FUNCIONES))}.")
        if isinstance(n, ast.Constant) and not isinstance(n.value, (int, float, str, bool, type(None))):
            raise ErrorExpresion("Constante no permitida.")
        if isinstance(n, ast.Name) and campos is not None:
            es_funcion = any(isinstance(p, ast.Call) and p.func is n for p in nodos)
            if not es_funcion and n.id not in campos and n.id.upper() not in ("VERDADERO", "FALSO"):
                raise ErrorExpresion(f"Campo desconocido: {n.id}.")
    return arbol


def evaluar(arbol: ast.Expression, fila: dict):
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return Decimal(str(n.value)) if isinstance(n.value, (int, float)) and not isinstance(n.value, bool) else n.value
        if isinstance(n, ast.Name):
            if n.id.upper() == "VERDADERO":
                return True
            if n.id.upper() == "FALSO":
                return False
            v = fila.get(n.id)
            return Decimal(str(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
        if isinstance(n, ast.BinOp):
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            if isinstance(n.op, ast.Not):
                return not v
            return -_dec(v) if isinstance(n.op, ast.USub) else _dec(v)
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                return all(ev(x) for x in n.values)
            return any(ev(x) for x in n.values)
        if isinstance(n, ast.Compare):
            izq = ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                der = ev(comp)
                if not _CMP[type(op)](izq, der):
                    return False
                izq = der
            return True
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Call):
            fn = FUNCIONES[n.func.id.upper()]
            if n.func.id.upper() in ("SI", "IF"):  # evaluación perezosa
                a = n.args
                if len(a) != 3:
                    raise ErrorExpresion("SI(condición, si_verdadero, si_falso) requiere 3 argumentos.")
                return ev(a[1]) if ev(a[0]) else ev(a[2])
            return fn(*[ev(x) for x in n.args])
        raise ErrorExpresion(f"Elemento no permitido: {type(n).__name__}")
    try:
        return ev(arbol)
    except ErrorExpresion:
        raise
    except (TypeError, InvalidOperation, ArithmeticError, ValueError) as exc:
        raise ErrorExpresion(f"No se pudo calcular: {exc}")
