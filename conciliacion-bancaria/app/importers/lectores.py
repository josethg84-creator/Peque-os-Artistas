"""Lectura de archivos a filas crudas (listas de celdas)."""
import csv
import io
import re
from dataclasses import dataclass, field

from app.importers.normalizacion import normalizar_texto, parse_fecha, parse_importe


class ErrorImportacion(Exception):
    """Error de formato que se muestra al usuario tal cual."""


def detectar_formato(nombre: str, contenido: bytes) -> str:
    ext = nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""
    if contenido[:4] == b"%PDF":
        return "PDF"
    if contenido[:2] == b"PK":  # zip → xlsx
        return "XLSX"
    if contenido[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ErrorImportacion(
            "Formato Excel 97-2003 (.xls) no soportado: guárdelo como .xlsx o .csv e intente de nuevo.")
    if ext in {"csv", "txt", "tsv"}:
        return "CSV"
    if ext in {"xlsx", "xlsm"}:
        return "XLSX"
    if ext == "pdf":
        return "PDF"
    # intento como texto delimitado
    return "CSV"


def leer_csv(contenido: bytes) -> list[list]:
    texto = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = contenido.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise ErrorImportacion("No se pudo decodificar el archivo de texto.")
    muestra = "\n".join(texto.splitlines()[:50])
    try:
        dialecto = csv.Sniffer().sniff(muestra, delimiters=";,\t|")
        delim = dialecto.delimiter
    except csv.Error:
        conteos = {d: muestra.count(d) for d in (";", ",", "\t", "|")}
        delim = max(conteos, key=conteos.get)
    lector = csv.reader(io.StringIO(texto), delimiter=delim)
    return [[c.strip() for c in fila] for fila in lector]


def leer_xlsx(contenido: bytes, hoja: str | None = None) -> list[list]:
    from openpyxl import load_workbook
    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as exc:  # archivo corrupto o protegido
        raise ErrorImportacion(f"No se pudo abrir el Excel: {exc}") from exc
    ws = libro[hoja] if hoja and hoja in libro.sheetnames else libro.worksheets[0]
    filas = [list(f) for f in ws.iter_rows(values_only=True)]
    libro.close()
    return [f for f in filas if any(c not in (None, "") for c in f)]


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
@dataclass
class ResultadoPDF:
    tablas: list[list] = field(default_factory=list)   # filas de tablas detectadas
    lineas: list[str] = field(default_factory=list)    # texto plano por líneas
    texto: str = ""


def leer_pdf(contenido: bytes) -> ResultadoPDF:
    import pdfplumber
    res = ResultadoPDF()
    try:
        with pdfplumber.open(io.BytesIO(contenido)) as pdf:
            for pagina in pdf.pages:
                for tabla in pagina.extract_tables() or []:
                    for fila in tabla:
                        if fila and any(c not in (None, "") for c in fila):
                            res.tablas.append([(c or "").replace("\n", " ").strip() for c in fila])
                txt = pagina.extract_text() or ""
                res.texto += txt + "\n"
                res.lineas.extend(l.strip() for l in txt.splitlines() if l.strip())
    except Exception as exc:
        raise ErrorImportacion(f"No se pudo leer el PDF: {exc}") from exc
    if not res.texto.strip():
        raise ErrorImportacion(
            "El PDF no contiene texto seleccionable (probablemente es una imagen escaneada). "
            "Solicite al banco el estado de cuenta digital o en Excel/CSV.")
    return res


_FECHA = r"(\d{1,2}[/\-.](?:\d{1,2}|[A-Za-z]{3})(?:[/\-.]\d{2,4})?)"
_MONTO = r"(\(?-?(?:S/|US\$|\$)?\s?\d{1,3}(?:[,.]\d{3})*[.,]\d{2}\)?-?)"
_RE_LINEA = re.compile(
    rf"^{_FECHA}\s+(?:{_FECHA}\s+)?(.+?)\s+{_MONTO}(?:\s+{_MONTO})?\s*$")
_RE_SALDO_INICIAL = re.compile(r"SALDO\s+(ANTERIOR|INICIAL|AL\s+INICIO)\D*?" + _MONTO)
_RE_OPERACION = re.compile(r"(?:^|\s)(?:N[°ºO]?\.?\s*OP\.?\s*|OP[.:]?\s*)?(\d{5,})(?:\s|$)")

_PALABRAS_CARGO = re.compile(
    r"\bITF\b|COMISION|MANTENIMIENTO|PORTES?|\bPAGO|RETIRO|CHEQUE|CARGO|DEBITO|ENVIADA|"
    r"TRANSF\.?\s*A\b|TRANSF.*ENV|\bA\s+TERCEROS|IMPUESTO|EMBARGO|DETRACCION")


def filas_desde_texto_pdf(lineas: list[str], anio: int | None) -> tuple[list[dict], list[str]]:
    """Respaldo cuando el PDF no tiene tablas: interpreta líneas 'fecha … monto [saldo]'."""
    advertencias: list[str] = []
    registros: list[dict] = []
    saldo_previo = None
    for linea in lineas:
        m = _RE_SALDO_INICIAL.search(normalizar_texto(linea))
        if m and not registros:
            saldo_previo = parse_importe(m.group(2))

    for n, linea in enumerate(lineas, start=1):
        m = _RE_LINEA.match(linea)
        if not m:
            continue
        fecha = parse_fecha(m.group(1), anio)
        if not fecha:
            continue
        descripcion = m.group(3).strip()
        if re.search(r"SALDO\s+(ANTERIOR|INICIAL|FINAL)", normalizar_texto(descripcion)):
            continue
        monto = parse_importe(m.group(4))
        saldo = parse_importe(m.group(5)) if m.group(5) else None
        if monto is None:
            continue
        op = _RE_OPERACION.search(descripcion)
        signo_explicito = monto < 0
        importe = monto
        if not signo_explicito:
            if saldo is not None and saldo_previo is not None and abs(saldo - saldo_previo) == abs(monto):
                importe = abs(monto) if saldo >= saldo_previo else -abs(monto)
            elif _PALABRAS_CARGO.search(normalizar_texto(descripcion)):
                importe = -abs(monto)
                advertencias.append(f"Línea {n}: signo deducido por palabra clave («{descripcion[:40]}»).")
        if saldo is not None:
            saldo_previo = saldo
        registros.append({
            "fila": n,
            "fecha": fecha,
            "fecha_valuta": parse_fecha(m.group(2), anio) if m.group(2) else None,
            "descripcion": descripcion,
            "numero_operacion": op.group(1) if op else None,
            "importe": importe,
            "saldo": saldo,
        })
    return registros, advertencias
