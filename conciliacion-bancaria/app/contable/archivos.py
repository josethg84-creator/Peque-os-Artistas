"""Área de preparación (staging) y lectura de archivos contables: XLSX, XLS, CSV y TXT.

El archivo subido se guarda en `DATA_DIR/staging/<token>/` hasta que se confirma o expira,
de modo que los pasos del asistente (hoja, encabezado, homologación, validación) trabajan
siempre sobre el mismo contenido sin volver a subirlo.
"""
import csv
import hashlib
import io
import json
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.core import config
from app.contable.campos import CAMPOS, TIPOS, clave_encabezado, sinonimos_de
from app.importers.lectores import ErrorImportacion

FORMATOS = {"xlsx": "XLSX", "xlsm": "XLSX", "xls": "XLS", "csv": "CSV", "txt": "TXT", "tsv": "CSV"}
DELIMITADORES = {"AUTO": None, "PUNTO_COMA": ";", "COMA": ",", "TAB": "\t", "BARRA": "|"}
HORAS_EXPIRACION = 24
_TOKEN = re.compile(r"^[0-9a-f]{32}$")


def dir_staging() -> Path:
    d = config.DATA_DIR / "staging"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ruta(token: str) -> Path:
    if not _TOKEN.match(token or ""):
        raise ErrorImportacion("Identificador de archivo inválido.")
    ruta = dir_staging() / token
    if not ruta.exists():
        raise ErrorImportacion("El archivo ya no está disponible (expiró o fue confirmado). Vuelva a cargarlo.")
    return ruta


def limpiar_expirados() -> None:
    limite = time.time() - HORAS_EXPIRACION * 3600
    for d in dir_staging().iterdir():
        if d.is_dir() and d.stat().st_mtime < limite:
            shutil.rmtree(d, ignore_errors=True)


def detectar_formato(nombre: str, contenido: bytes) -> str:
    if contenido[:4] == b"%PDF":
        raise ErrorImportacion("Los archivos PDF no se admiten para información contable: exporte a Excel, CSV o TXT.")
    if contenido[:2] == b"PK":
        return "XLSX"
    if contenido[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "XLS"
    ext = nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""
    if ext in ("xlsx", "xlsm", "xls"):
        raise ErrorImportacion("El archivo tiene extensión de Excel pero su contenido no es un libro válido.")
    return FORMATOS.get(ext, "TXT")


def guardar(contenido: bytes, nombre: str, empresa_id: int, usuario: str) -> dict:
    limpiar_expirados()
    if not contenido:
        raise ErrorImportacion("El archivo está vacío.")
    formato = detectar_formato(nombre, contenido)
    token = uuid.uuid4().hex
    ruta = dir_staging() / token
    ruta.mkdir()
    (ruta / "archivo").write_bytes(contenido)
    meta = {"token": token, "nombre": Path(nombre).name[:255], "formato": formato, "tamano": len(contenido),
            "hash": hashlib.sha256(contenido).hexdigest(), "empresa_id": empresa_id, "usuario": usuario,
            "subido_en": datetime.now().isoformat(timespec="seconds")}
    try:
        meta["hojas"] = listar_hojas(contenido, formato)
    except ErrorImportacion:
        shutil.rmtree(ruta, ignore_errors=True)
        raise
    (ruta / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    return meta


def meta(token: str) -> dict:
    return json.loads((_ruta(token) / "meta.json").read_text())


def contenido(token: str) -> bytes:
    return (_ruta(token) / "archivo").read_bytes()


def descartar(token: str) -> None:
    try:
        shutil.rmtree(_ruta(token), ignore_errors=True)
    except ErrorImportacion:
        pass


# ---------------------------------------------------------------- lectura
def listar_hojas(datos: bytes, formato: str) -> list[dict]:
    if formato == "XLSX":
        from openpyxl import load_workbook
        try:
            wb = load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
        except Exception as exc:
            raise ErrorImportacion(f"Archivo Excel estructuralmente inválido: {exc}") from exc
        hojas = [{"nombre": ws.title, "filas": ws.max_row or 0, "columnas": ws.max_column or 0}
                 for ws in wb.worksheets]
        wb.close()
        return hojas
    if formato == "XLS":
        libro = _abrir_xls(datos)
        return [{"nombre": s.name, "filas": s.nrows, "columnas": s.ncols} for s in libro.sheets()]
    filas = _leer_texto(datos, "AUTO")
    return [{"nombre": "(texto)", "filas": len(filas), "columnas": max((len(f) for f in filas), default=0)}]


def _abrir_xls(datos: bytes):
    try:
        import xlrd
    except ImportError as exc:  # pragma: no cover
        raise ErrorImportacion("Falta la librería xlrd para leer archivos .xls.") from exc
    try:
        return xlrd.open_workbook(file_contents=datos)
    except Exception as exc:
        raise ErrorImportacion(f"Archivo .xls estructuralmente inválido: {exc}") from exc


def leer_filas(datos: bytes, formato: str, hoja: str | None = None, delimitador: str = "AUTO") -> list[list]:
    """Todas las filas de la hoja como listas (valores crudos: str, número, date)."""
    if formato == "XLSX":
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
        ws = wb[hoja] if hoja and hoja in wb.sheetnames else wb.worksheets[0]
        filas = [list(f) for f in ws.iter_rows(values_only=True)]
        wb.close()
    elif formato == "XLS":
        import xlrd
        libro = _abrir_xls(datos)
        hoja_x = libro.sheet_by_name(hoja) if hoja and hoja in libro.sheet_names() else libro.sheet_by_index(0)
        filas = []
        for r in range(hoja_x.nrows):
            fila = []
            for c in range(hoja_x.ncols):
                celda = hoja_x.cell(r, c)
                if celda.ctype == xlrd.XL_CELL_DATE:
                    fila.append(xlrd.xldate_as_datetime(celda.value, libro.datemode).date())
                elif celda.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    fila.append(None)
                else:
                    fila.append(celda.value)
            filas.append(fila)
    else:
        filas = _leer_texto(datos, delimitador)
    if formato not in ("XLSX", "XLS"):
        ancho = max((len(f) for f in filas), default=0)
        return [list(f) + [None] * (ancho - len(f)) for f in filas]
    # quitar columnas vacías al final para no arrastrar formato de Excel
    ancho = max((max((i + 1 for i, v in enumerate(f) if v not in (None, "")), default=0) for f in filas), default=0)
    return [list(f[:ancho]) + [None] * (ancho - len(f[:ancho])) for f in filas]


def _decodificar(datos: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return datos.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ErrorImportacion("No se pudo decodificar el archivo de texto.")


def _leer_texto(datos: bytes, delimitador: str) -> list[list]:
    texto = _decodificar(datos)
    delim = DELIMITADORES.get(delimitador) if delimitador in DELIMITADORES else delimitador
    if not delim:
        muestra = "\n".join(texto.splitlines()[:60])
        conteos = {d: sum(linea.count(d) for linea in muestra.splitlines()) for d in ("|", ";", "\t", ",")}
        delim = max(conteos, key=conteos.get) if any(conteos.values()) else ","
        if conteos.get("|", 0) and conteos["|"] >= conteos.get(";", 0):
            delim = "|"
    filas = [[c.strip() for c in fila] for fila in csv.reader(io.StringIO(texto), delimiter=delim)]
    # El formato PLE termina cada línea con «|»: se descarta la columna vacía final común a todas las filas.
    if filas and all((not f) or f[-1] == "" for f in filas if f):
        filas = [f[:-1] if f else f for f in filas]
    return filas


# ---------------------------------------------------------------- encabezados
@dataclass
class Encabezado:
    fila: int            # 1-based; 0 = sin encabezado
    filas: int           # 1 o 2 filas combinadas
    nombres: list[str]
    inicio_datos: int    # índice 0-based de la primera fila de datos


def construir_encabezado(filas: list[list], fila: int, n_filas: int = 1) -> Encabezado:
    ancho = max((len(f) for f in filas), default=0)
    if fila <= 0:
        return Encabezado(0, 0, [f"Columna {i + 1}" for i in range(ancho)], 0)
    if fila > len(filas):
        raise ErrorImportacion(f"La fila de encabezado {fila} no existe (la hoja tiene {len(filas)} filas).")
    actual = [_texto(c) for c in filas[fila - 1]] + [""] * ancho
    nombres = actual[:ancho]
    if n_filas == 2 and fila >= 2:
        padre, previo = [], ""
        for c in (filas[fila - 2] + [None] * ancho)[:ancho]:
            previo = _texto(c) or previo  # celdas combinadas: se repite el título del grupo
            padre.append(previo)
        nombres = [f"{p} {h}".strip() if p and p != h else h for p, h in zip(padre, nombres)]
    nombres = [n or f"Columna {i + 1}" for i, n in enumerate(nombres)]
    return Encabezado(fila, n_filas, nombres, fila)


def _texto(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, datetime):
        return f"{v:%d/%m/%Y}" if (v.hour, v.minute, v.second) == (0, 0, 0) else f"{v:%d/%m/%Y %H:%M}"
    if isinstance(v, date):
        return f"{v:%d/%m/%Y}"
    return str(v).strip()


def puntaje_encabezado(nombres: list, tipo: str) -> float:
    claves = {clave_encabezado(n) for n in nombres if _texto(n)}
    puntos = 0.0
    for campo in TIPOS[tipo].campos:
        sins = set(sinonimos_de(tipo, campo))
        if claves & sins:
            puntos += 1
        elif any(any(re.search(rf"(^|\s){re.escape(s)}(\s|$)", c) for s in sins if len(s) > 2) for c in claves):
            puntos += 0.5
    return puntos


def detectar_encabezado(filas: list[list], tipo: str, max_filas: int = 40) -> tuple[int, int, float]:
    """(fila 1-based, filas combinadas, puntaje). Fila 0 si no se reconoce ninguna."""
    mejor = (0, 1, 0.0)
    for i, fila in enumerate(filas[:max_filas]):
        textos = [c for c in fila if isinstance(c, str) and c.strip()]
        if len(textos) < 2:
            continue
        p1 = puntaje_encabezado(fila, tipo)
        if p1 > mejor[2]:
            mejor = (i + 1, 1, p1)
        if i >= 1:
            p2 = puntaje_encabezado(construir_encabezado(filas, i + 1, 2).nombres, tipo)
            if p2 > mejor[2] + 0.5:
                mejor = (i + 1, 2, p2)
    return mejor if mejor[2] >= 2 else (0, 1, mejor[2])


def valor_texto(v) -> str:
    return _texto(v)


__all__ = ["CAMPOS", "construir_encabezado", "detectar_encabezado", "guardar", "leer_filas", "meta"]
