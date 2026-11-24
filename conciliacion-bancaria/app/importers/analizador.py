"""Convierte un archivo en registros normalizados listos para persistir.

Flujo: detectar formato → leer filas → detectar encabezado/mapeo (o usar el manual)
→ normalizar cada fila → validar (moneda, saldos, fechas) → calcular huellas.
"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.importers import lectores
from app.importers.columnas import cumple_requeridos, detectar_encabezado, sinonimos
from app.importers.normalizacion import (clasificar_movimiento, es_vacio, limpiar_codigo,
                                         normalizar_texto, parse_fecha, parse_importe)

MONEDAS = {
    "PEN": {"PEN", "S/", "S/.", "SOLES", "SOL", "MN", "M.N.", "NUEVOS SOLES", "1"},
    "USD": {"USD", "US$", "$", "DOLARES", "DOLAR", "ME", "M.E.", "DOLARES AMERICANOS", "2"},
    "EUR": {"EUR", "€", "EUROS", "EURO"},
}


def normalizar_moneda(valor) -> str | None:
    t = normalizar_texto(valor).replace(" ", "") if not es_vacio(valor) else ""
    for codigo, alias in MONEDAS.items():
        if t in {a.replace(" ", "") for a in alias}:
            return codigo
    return None


@dataclass
class ResultadoAnalisis:
    tipo: str
    formato: str
    metodo: str = "TABLA"           # TABLA | TEXTO_PDF
    fila_encabezado: int | None = None
    encabezados: list[str] = field(default_factory=list)
    mapeo: dict[int, str] = field(default_factory=dict)
    registros: list[dict] = field(default_factory=list)
    errores: list[dict] = field(default_factory=list)       # filas descartadas
    advertencias: list[str] = field(default_factory=list)
    filas_filtradas: int = 0        # p. ej. otras subcuentas en el mayor
    saldo_inicial: Decimal | None = None
    saldo_final: Decimal | None = None
    saldos_consistentes: bool | None = None
    descuadres_saldo: list[dict] = field(default_factory=list)

    @property
    def fecha_desde(self) -> date | None:
        return min((r["fecha"] for r in self.registros), default=None)

    @property
    def fecha_hasta(self) -> date | None:
        return max((r["fecha"] for r in self.registros), default=None)


def huella(tipo: str, r: dict) -> str:
    if tipo == "BANCO":
        partes = [r["fecha"], r["importe"], r.get("numero_operacion") or "",
                  normalizar_texto(r.get("descripcion"))[:60]]
    else:
        partes = [r["fecha"], r["importe"], r.get("numero_operacion") or "",
                  r.get("voucher") or "", normalizar_texto(r.get("glosa"))[:60]]
    return hashlib.sha256("|".join(str(p) for p in partes).encode()).hexdigest()


def analizar(
    nombre_archivo: str,
    contenido: bytes,
    tipo: str,
    moneda_cuenta: str,
    *,
    mapeo_manual: dict[int, str] | None = None,
    anio: int | None = None,
    cuenta_contable: str | None = None,
    invertir_signo: bool = False,
) -> ResultadoAnalisis:
    if tipo not in ("BANCO", "LIBRO"):
        raise lectores.ErrorImportacion("Tipo de importación inválido.")
    formato = lectores.detectar_formato(nombre_archivo, contenido)
    res = ResultadoAnalisis(tipo=tipo, formato=formato)

    if formato == "PDF":
        pdf = lectores.leer_pdf(contenido)
        anio = anio or _anio_en_texto(pdf.texto)
        filas = pdf.tablas
        if mapeo_manual is None and (not filas or detectar_encabezado(filas, tipo) is None):
            if tipo == "LIBRO":
                raise lectores.ErrorImportacion(
                    "No se encontró una tabla de libro mayor en el PDF. Exporte el mayor en Excel o CSV.")
            res.metodo = "TEXTO_PDF"
            crudos, adv = lectores.filas_desde_texto_pdf(pdf.lineas, anio)
            res.advertencias.append(
                "El PDF no tiene tablas estructuradas: se interpretaron las líneas de texto. "
                "Revise la vista previa con atención.")
            res.advertencias.extend(adv[:20])
            for c in crudos:
                _agregar_banco(res, c, moneda_cuenta)
            _validar_saldos(res)
            return res
    elif formato == "XLSX":
        filas = lectores.leer_xlsx(contenido)
    else:
        filas = lectores.leer_csv(contenido)

    if not filas:
        raise lectores.ErrorImportacion("El archivo está vacío.")

    if mapeo_manual is not None:
        idx_enc = _fila_encabezado_manual(filas, tipo)
        mapeo = {int(k): v for k, v in mapeo_manual.items() if v}
        if not cumple_requeridos(set(mapeo.values()), tipo):
            raise lectores.ErrorImportacion(
                "El mapeo manual debe incluir la fecha y el importe (o cargo/abono, debe/haber).")
    else:
        hallado = detectar_encabezado(filas, tipo)
        if hallado is None:
            raise lectores.ErrorImportacion(
                "No se identificaron las columnas de fecha e importe. Use el mapeo manual.")
        idx_enc, mapeo = hallado

    res.fila_encabezado = idx_enc
    res.encabezados = [str(c) if c is not None else "" for c in filas[idx_enc]]
    res.mapeo = mapeo
    anio = anio or _anio_en_filas(filas[:idx_enc])
    encabezado_norm = [normalizar_texto(c) for c in filas[idx_enc]]

    for offset, fila in enumerate(filas[idx_enc + 1:], start=idx_enc + 2):
        if [normalizar_texto(c) for c in fila] == encabezado_norm:
            continue  # encabezado repetido en otra página
        valores = {campo: (fila[i] if i < len(fila) else None) for i, campo in mapeo.items()}
        if all(es_vacio(v) for v in valores.values()):
            continue
        if tipo == "BANCO":
            _fila_banco(res, offset, valores, moneda_cuenta, anio, invertir_signo)
        else:
            _fila_libro(res, offset, valores, moneda_cuenta, anio, cuenta_contable, invertir_signo)

    if tipo == "BANCO":
        _inferir_signo_por_saldo(res)
        _validar_saldos(res)
    elif res.registros and res.saldo_inicial is not None:
        res.saldo_final = res.saldo_inicial + sum(r["importe"] for r in res.registros)
    if not res.registros:
        res.advertencias.append("No se obtuvo ningún movimiento válido del archivo.")
    return res


# ---------------------------------------------------------------------------
def _anio_en_texto(texto: str) -> int | None:
    anios = re.findall(r"\b(20[0-9]{2})\b", texto)
    return int(max(set(anios), key=anios.count)) if anios else None


def _anio_en_filas(filas: list[list]) -> int | None:
    return _anio_en_texto(" ".join(str(c) for f in filas for c in f if c is not None))


def _fila_encabezado_manual(filas: list[list], tipo: str) -> int:
    hallado = detectar_encabezado(filas, tipo)
    if hallado:
        return hallado[0]
    for i, f in enumerate(filas[:40]):  # primera fila con ≥2 textos
        if sum(1 for c in f if isinstance(c, str) and c.strip()) >= 2:
            return i
    return 0


def _error(res: ResultadoAnalisis, fila: int, mensaje: str) -> None:
    res.errores.append({"fila": fila, "mensaje": mensaje})


def _moneda_fila(res, fila, valor, moneda_cuenta) -> bool:
    if es_vacio(valor):
        return True
    m = normalizar_moneda(valor)
    if m and m != moneda_cuenta:
        _error(res, fila, f"Moneda {m} distinta a la de la cuenta ({moneda_cuenta}).")
        return False
    return True


def _es_fila_saldo(texto: str) -> str | None:
    t = normalizar_texto(texto)
    if re.search(r"SALDO\s+(ANTERIOR|INICIAL|AL\s+INICIO|DEL\s+MES\s+ANTERIOR)", t):
        return "INICIAL"
    if re.search(r"SALDO\s+(FINAL|ACTUAL|AL\s+CIERRE)|^TOTAL(ES)?\b", t):
        return "FINAL"
    return None


def _fila_banco(res, fila, v, moneda_cuenta, anio, invertir):
    fecha = parse_fecha(v.get("fecha"), anio)
    descripcion = str(v.get("descripcion") or "").strip()
    if fecha is None:
        especial = _es_fila_saldo(descripcion or str(v.get("fecha") or ""))
        if especial == "INICIAL":
            s = parse_importe(v.get("saldo")) or parse_importe(v.get("importe"))
            if s is not None:
                res.saldo_inicial = s
            return
        if especial == "FINAL":
            return
        if any(parse_importe(v.get(k)) for k in ("importe", "cargo", "abono")):
            _error(res, fila, f"Fecha no reconocida: «{v.get('fecha')}».")
        return
    if _es_fila_saldo(descripcion) == "INICIAL":
        s = parse_importe(v.get("saldo")) or parse_importe(v.get("importe"))
        if s is not None:
            res.saldo_inicial = s
        return

    importe = _importe(v, "abono", "cargo")
    if importe is None:
        _error(res, fila, "Importe vacío o no reconocido.")
        return
    if invertir:
        importe = -importe
    if importe == 0:
        _error(res, fila, "Movimiento con importe cero (omitido).")
        return
    if not _moneda_fila(res, fila, v.get("moneda"), moneda_cuenta):
        return
    _agregar_banco(res, {
        "fila": fila,
        "fecha": fecha,
        "fecha_valuta": parse_fecha(v.get("fecha_valuta"), anio),
        "descripcion": descripcion,
        "numero_operacion": limpiar_codigo(v.get("numero_operacion")),
        "referencia": (str(v.get("referencia")).strip()[:120] if not es_vacio(v.get("referencia")) else None),
        "importe": importe,
        "saldo": parse_importe(v.get("saldo")),
        "_importe_columna_unica": "importe" in v and "cargo" not in v and "abono" not in v,
    }, moneda_cuenta)


def _agregar_banco(res, r: dict, moneda: str) -> None:
    r.setdefault("referencia", None)
    r["descripcion"] = (r.get("descripcion") or "(sin descripción)")[:255]
    r["moneda"] = moneda
    r["categoria"] = clasificar_movimiento(r["descripcion"])
    r["hash"] = huella("BANCO", r)
    res.registros.append(r)


def _importe(v: dict, positivo: str, negativo: str) -> Decimal | None:
    """Importe con signo: + ingreso a la cuenta, − egreso."""
    p, n = parse_importe(v.get(positivo)), parse_importe(v.get(negativo))
    if p is not None or n is not None:
        return abs(p or Decimal("0")) - abs(n or Decimal("0"))
    return parse_importe(v.get("importe"))


def _fila_libro(res, fila, v, moneda_cuenta, anio, cuenta_contable, invertir):
    glosa = str(v.get("glosa") or "").strip()
    cuenta = limpiar_codigo(v.get("cuenta"))
    if cuenta_contable and cuenta and not cuenta.startswith(cuenta_contable):
        # fila de otra subcuenta: solo se cuenta si tiene datos de movimiento
        if parse_fecha(v.get("fecha"), anio):
            res.filas_filtradas += 1
        return
    fecha = parse_fecha(v.get("fecha"), anio)
    if fecha is None:
        especial = _es_fila_saldo(glosa or str(v.get("fecha") or "") or str(v.get("voucher") or ""))
        if especial == "INICIAL":
            s = _importe(v, "debe", "haber")
            if s is not None:
                res.saldo_inicial = s
            return
        if especial is None and any(parse_importe(v.get(k)) for k in ("importe", "debe", "haber")):
            _error(res, fila, f"Fecha no reconocida: «{v.get('fecha')}».")
        return
    if _es_fila_saldo(glosa) == "INICIAL":
        s = _importe(v, "debe", "haber")
        if s is not None:
            res.saldo_inicial = s
        return
    debe = abs(parse_importe(v.get("debe")) or Decimal("0"))
    haber = abs(parse_importe(v.get("haber")) or Decimal("0"))
    if "debe" in v or "haber" in v:
        importe = debe - haber
    else:
        importe = parse_importe(v.get("importe"))
        if importe is None:
            _error(res, fila, "Importe vacío o no reconocido.")
            return
        debe, haber = (importe, Decimal("0")) if importe > 0 else (Decimal("0"), -importe)
    if invertir:
        importe, debe, haber = -importe, haber, debe
    if importe == 0:
        _error(res, fila, "Asiento con importe cero (omitido).")
        return
    if not _moneda_fila(res, fila, v.get("moneda"), moneda_cuenta):
        return
    r = {
        "fila": fila,
        "fecha": fecha,
        "voucher": limpiar_codigo(v.get("voucher")),
        "glosa": (glosa or "(sin glosa)")[:255],
        "numero_operacion": limpiar_codigo(v.get("numero_operacion")),
        "medio_pago": (limpiar_codigo(v.get("medio_pago")) or None),
        "tercero": (str(v.get("tercero")).strip()[:200] if not es_vacio(v.get("tercero")) else None),
        "cuenta_contable": cuenta or cuenta_contable,
        "debe": debe,
        "haber": haber,
        "importe": importe,
        "moneda": moneda_cuenta,
    }
    if r["medio_pago"]:
        r["medio_pago"] = r["medio_pago"][:4]
    r["hash"] = huella("LIBRO", r)
    res.registros.append(r)


def _inferir_signo_por_saldo(res: ResultadoAnalisis) -> None:
    """Si hay una sola columna de importe sin negativos pero sí saldo, deduce el signo."""
    regs = res.registros
    if not regs or not all(r.get("_importe_columna_unica") for r in regs):
        return
    if any(r["importe"] < 0 for r in regs) or sum(1 for r in regs if r.get("saldo") is not None) < 2:
        return
    orden = _orden_cronologico(regs)
    previo = res.saldo_inicial
    cambiados = 0
    for r in orden:
        if r.get("saldo") is not None and previo is not None:
            if previo - r["importe"] == r["saldo"]:
                r["importe"] = -r["importe"]
                cambiados += 1
        previo = r.get("saldo") if r.get("saldo") is not None else previo
    if cambiados:
        for r in regs:
            r["hash"] = huella("BANCO", r)
        res.advertencias.append(
            f"La columna de importe no tenía signo: se dedujeron {cambiados} cargos a partir del saldo.")


def _orden_cronologico(regs: list[dict]) -> list[dict]:
    """Los bancos exportan a veces del más reciente al más antiguo."""
    if len(regs) > 1 and regs[0]["fecha"] > regs[-1]["fecha"]:
        return list(reversed(regs))
    return regs


def _validar_saldos(res: ResultadoAnalisis) -> None:
    regs = [r for r in res.registros]
    for r in regs:
        r.pop("_importe_columna_unica", None)
    con_saldo = [r for r in regs if r.get("saldo") is not None]
    if len(con_saldo) < 2:
        if regs and res.saldo_inicial is not None:
            res.saldo_final = res.saldo_inicial + sum(r["importe"] for r in regs)
        return
    orden = _orden_cronologico(regs)
    if orden is not regs:
        res.advertencias.append("El archivo está en orden descendente; se validó en orden cronológico.")

    primero = orden[0]
    if res.saldo_inicial is None and primero.get("saldo") is not None:
        res.saldo_inicial = primero["saldo"] - primero["importe"]
    previo = res.saldo_inicial
    descuadres = []
    for r in orden:
        if r.get("saldo") is None or previo is None:
            previo = r.get("saldo", previo)
            continue
        esperado = previo + r["importe"]
        if esperado != r["saldo"]:
            descuadres.append({"fila": r["fila"], "esperado": str(esperado), "saldo": str(r["saldo"]),
                               "diferencia": str(r["saldo"] - esperado)})
        previo = r["saldo"]
    ultimo_saldo = next((r["saldo"] for r in reversed(orden) if r.get("saldo") is not None), None)
    res.saldo_final = ultimo_saldo
    res.saldos_consistentes = not descuadres
    res.descuadres_saldo = descuadres[:50]
    if descuadres:
        res.advertencias.append(
            f"Continuidad de saldos: {len(descuadres)} fila(s) no cuadran (saldo anterior + movimiento ≠ saldo). "
            "Puede deberse a movimientos del mismo día en distinto orden o a un error de lectura.")
