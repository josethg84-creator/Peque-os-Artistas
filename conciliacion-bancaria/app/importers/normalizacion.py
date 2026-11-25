"""Normalización de fechas, importes y textos provenientes de bancos peruanos y ERP."""
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


MESES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7,
    "AGO": 8, "SET": 9, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
    "JAN": 1, "APR": 4, "AUG": 8, "DEC": 12,
}


def normalizar_texto(valor) -> str:
    """Mayúsculas, sin tildes, espacios simples."""
    if valor is None:
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def es_vacio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and valor != valor:  # NaN
        return True
    return str(valor).strip() in {"", "-", "nan", "NaN", "None"}


def parse_fecha(valor, anio_por_defecto: int | None = None, orden: str = "DMY") -> date | None:
    """Convierte la fecha a `date`. Acepta date/datetime, serial de Excel y textos
    dd/mm/aaaa, dd-mm-aa, dd.mm.aaaa, aaaa-mm-dd, aaaammdd, dd/mm (con año por defecto),
    15-ENE-2026, 15ENE. `orden` (DMY | MDY | YMD | AUTO) resuelve las fechas numéricas ambiguas."""
    if es_vacio(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if 20000 < float(valor) < 80000:  # serial de Excel (1954–2119)
            return date(1899, 12, 30) + timedelta(days=int(valor))
        if 19000101 <= int(valor) <= 21001231:  # aaaammdd numérico
            return _crear(int(valor) // 10000, int(valor) // 100 % 100, int(valor) % 100)
        return None

    s = normalizar_texto(valor)
    s = s.split(" ")[0] if re.match(r"^\d{4}-\d{2}-\d{2}[ T]", s) else s

    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        return _crear(int(m[1]), int(m[2]), int(m[3]))

    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b", s)
    if m:
        a, b = int(m[1]), int(m[2])
        if orden == "MDY" or (orden == "AUTO" and b > 12 >= a):
            return _crear(_anio(m[3]), a, b)
        return _crear(_anio(m[3]), b, a)

    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return _crear(int(m[1]), int(m[2]), int(m[3]))

    m = re.match(r"^(\d{1,2})[-/.\s]?([A-Z]{3})[A-Z]*[-/.\s]?(\d{2,4})?\b", s)
    if m and m[2] in MESES:
        anio = _anio(m[3]) if m[3] else anio_por_defecto
        return _crear(anio, MESES[m[2]], int(m[1])) if anio else None

    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})$", s)
    if m and anio_por_defecto:
        return _crear(anio_por_defecto, int(m[2]), int(m[1]))
    return None


def _anio(texto: str) -> int:
    a = int(texto)
    return a + 2000 if a < 100 else a


def _crear(anio: int | None, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia) if anio else None
    except ValueError:
        return None


_RE_NUM = re.compile(r"[^\d,.\-]")
_RE_MONEDA = re.compile(r"S/\.?|US\$|USD|PEN|EUR|SOLES|DOLARES|€|\$")


def parse_importe(valor, decimal: str = "AUTO", decimales: int = 2) -> Decimal | None:
    """Convierte importes con formatos diversos a Decimal con 2 decimales.

    Soporta: 1,234.56 · 1.234,56 · S/ 1,234.56 · US$ 10 · (500.00) · 500.00- ·
    -500 · 500.00 CR · 500.00 DB · 1 234,56.
    `decimal`: AUTO (deduce), PUNTO (1,234.56) o COMA (1.234,56). `decimales`: precisión
    del resultado (2 para importes, 3–6 para tipos de cambio).
    """
    cuanto = Decimal(1).scaleb(-decimales)
    if es_vacio(valor):
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float, Decimal)):
        try:
            return Decimal(str(valor)).quantize(cuanto, rounding=ROUND_HALF_UP)
        except InvalidOperation:
            return None

    s = normalizar_texto(valor)
    negativo = False
    if s.startswith("(") and s.endswith(")"):
        negativo, s = True, s[1:-1]
    if re.search(r"\b(DB|DEBITO|CARGO|D)$", s):
        negativo = True
    s = re.sub(r"\b(CR|DB|D|C|DEBITO|CREDITO|CARGO|ABONO)$", "", s).strip()
    if s.endswith("-"):
        negativo, s = True, s[:-1]
    # Solo se toleran símbolos de moneda; cualquier otra letra hace el valor no procesable
    # (p. ej. «1,2a0.00» no debe convertirse silenciosamente en 120.00).
    s = _RE_MONEDA.sub("", s)
    if re.search(r"[A-Z]", s):
        return None
    s = _RE_NUM.sub("", s.replace(" ", ""))
    if s.startswith("-"):
        negativo, s = True, s[1:]
    s = s.replace("-", "")
    if not s or not any(ch.isdigit() for ch in s):
        return None

    if decimal == "PUNTO":
        s = s.replace(",", "")
    elif decimal == "COMA":
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):  # 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:  # 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        partes = s.split(",")
        # 1234,56 → decimal ; 1,234 o 1,234,567 → miles
        if len(partes) == 2 and len(partes[1]) in (1, 2):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1:  # 1.234.567
        s = s.replace(".", "")
    try:
        numero = Decimal(s).quantize(cuanto, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None
    return -numero if negativo else numero


def limpiar_codigo(valor) -> str | None:
    """Número de operación / documento: sin espacios, sin '.0' de Excel, sin ceros a la izquierda
    excesivos no se tocan (son significativos en algunos bancos)."""
    if es_vacio(valor):
        return None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    s = re.sub(r"\s+", "", str(valor)).upper()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s[:40] or None


# ---------------------------------------------------------------------------
# Clasificación preliminar de movimientos bancarios (se refina en la fase 3)
# ---------------------------------------------------------------------------
_CATEGORIAS = [
    ("ITF", [r"\bITF\b", r"IMP\.?\s*TRANS", r"IMPUESTO A LAS TRANS", r"IMPUESTO TRANSACC"]),
    ("INTERES", [r"\bINTERES", r"\bINT\.?\s*(GANAD|ACRED|DEP|CTA)", r"ABONO INT"]),
    ("COMISION", [r"COMISION", r"\bCOM\.?\s", r"MANTENIMIENTO", r"MANT\.?\s*CTA", r"\bPORTES?\b",
                  r"CARGO POR SERV", r"MEMBRESIA", r"ENVIO (DE )?ESTADO", r"\bGASTOS? BANC"]),
    ("RETENCION", [r"RETENCION", r"EMBARGO", r"DETRACCION"]),
    ("DEPOSITO", [r"DEPOSITO", r"\bDEP\.?\s", r"VENTANILLA"]),
    ("TRANSFERENCIA", [r"TRANSF", r"\bTRF\b", r"\bTRAN\b", r"\bCCI\b", r"INTERBANC", r"TELECR",
                       r"\bTIN\b", r"YAPE", r"\bPLIN\b"]),
    ("DEPOSITO", [r"\bDEP\.?\b", r"\bABONO\b", r"EFECTIVO"]),
    ("CHEQUE", [r"\bCHEQUE", r"\bCHQ\b", r"\bCH\.?\s*\d"]),
    ("PAGO", [r"\bPAGO", r"\bPAG\.?\b", r"PLANILLA", r"PROVEEDOR", r"\bSUNAT\b", r"ESSALUD",
              r"\bAFP\b", r"DEBITO AUTOM"]),
    ("RETIRO", [r"RETIRO", r"\bATM\b", r"CAJERO"]),
]
_CATEGORIAS_RE = [(c, [re.compile(p) for p in pats]) for c, pats in _CATEGORIAS]


def clasificar_movimiento(descripcion: str) -> str:
    texto = normalizar_texto(descripcion)
    for categoria, patrones in _CATEGORIAS_RE:
        if any(p.search(texto) for p in patrones):
            return categoria
    return "OTRO"
