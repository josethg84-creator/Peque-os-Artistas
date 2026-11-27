"""Homologación de columnas y extracción de registros normalizados.

1. `sugerir_mapeo`: propone qué columna corresponde a cada campo interno, con su origen
   (plantilla, coincidencia exacta o parcial) y nivel de confianza. El usuario confirma.
2. `extraer`: recorre las filas, descarta vacías, identifica subtotales/totales, convierte
   cada valor a su tipo (Decimal, fecha, código) y registra observaciones de conversión.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from app.contable.archivos import valor_texto
from app.contable.campos import CAMPOS, clave_encabezado, sinonimos_de, tipo_def
from app.contable.observaciones import Obs
from app.importers.analizador import normalizar_moneda
from app.importers.normalizacion import es_vacio, normalizar_texto, parse_fecha, parse_importe

CERO = Decimal("0")


# ------------------------------------------------------------------ sugerencias
def sugerir_mapeo(tipo: str, encabezados: list[str], plantilla_mapeo: dict | None = None) -> dict[str, dict]:
    """{campo: {"columna": idx, "origen": "PLANTILLA|EXACTA|PARCIAL", "confianza": 0-100}}"""
    claves = [clave_encabezado(h) for h in encabezados]
    campos = tipo_def(tipo).campos
    resultado: dict[str, dict] = {}
    usadas: set[int] = set()

    def asignar(campo, idx, origen, confianza):
        resultado[campo] = {"columna": idx, "origen": origen, "confianza": confianza}
        usadas.add(idx)

    for campo, ref in (plantilla_mapeo or {}).items():
        if campo not in campos:
            continue
        idx = None
        if isinstance(ref, str) and ref.startswith("#") and ref[1:].isdigit():
            idx = int(ref[1:])
            idx = idx if idx < len(claves) else None
        elif ref in claves:
            idx = claves.index(ref)
        if idx is not None and idx not in usadas:
            asignar(campo, idx, "PLANTILLA", 100)

    for campo in campos:  # coincidencia exacta, respetando la prioridad de sinónimos
        if campo in resultado:
            continue
        for s in sinonimos_de(tipo, campo):
            idx = next((i for i, c in enumerate(claves) if c == s and i not in usadas), None)
            if idx is not None:
                asignar(campo, idx, "EXACTA", 95)
                break

    candidatos = []  # coincidencia parcial: gana el sinónimo más largo
    for campo in campos:
        if campo in resultado:
            continue
        for s in sinonimos_de(tipo, campo):
            if len(s) < 3:
                continue
            for i, c in enumerate(claves):
                if i not in usadas and c and re.search(rf"(^|\s){re.escape(s)}(\s|$)", c):
                    candidatos.append((len(s), -campos.index(campo), campo, i))
    for _, _, campo, i in sorted(candidatos, reverse=True):
        if campo not in resultado and i not in usadas:
            asignar(campo, i, "PARCIAL", 60)
    return resultado


def mapeo_a_plantilla(mapeo: dict[str, int], encabezados: list[str], sin_encabezado: bool) -> dict[str, str]:
    """Las plantillas guardan el nombre normalizado del encabezado (o #índice si no hay encabezado)."""
    return {c: (f"#{i}" if sin_encabezado else clave_encabezado(encabezados[i])) for c, i in mapeo.items()}


# ------------------------------------------------------------------ extracción
RE_TOTAL = re.compile(r"(^|\s)(SUB\s?TOTAL(ES)?|TOTAL(ES)?|SUMAS?|SUMA TOTAL|TOTAL GENERAL|TOTAL CUENTA|"
                      r"TOTAL ASIENTO|TOTAL VOUCHER|TOTAL DEL MES|VAN|VIENEN)(\s|:|$)")
RE_TOTAL_GENERAL = re.compile(r"TOTAL(ES)?\s+GENERAL(ES)?|^TOTALES?:?$|SUMAS?\s+TOTAL(ES)?|TOTAL\s+(DEL\s+)?(LIBRO|BALANCE|REGISTRO)")
RE_SALDO_ANTERIOR = re.compile(r"SALDO\s+(ANTERIOR|INICIAL|DEL\s+MES\s+ANTERIOR)|VIENEN?")
BOOL_SI = {"S", "SI", "Y", "YES", "1", "TRUE", "VERDADERO", "X", "ACTIVO", "ACTIVA", "VIGENTE", "HABILITADO",
           "HABILITADA"}
BOOL_NO = {"N", "NO", "0", "FALSE", "FALSO", "INACTIVO", "INACTIVA", "BAJA", "ANULADO", "ANULADA", "DE BAJA"}
# Claves de contabilización SAP más comunes (cuentas de mayor, clientes, proveedores, activos).
SAP_DEBE = {"40", "70"} | {f"{n:02d}" for n in range(1, 10)} | {str(n) for n in range(21, 30)}
SAP_HABER = {"50", "75"} | {str(n) for n in range(11, 20)} | {str(n) for n in range(31, 40)}

CAMPOS_IMPORTE_TOTAL = {
    "DIARIO": ("debe_mn", "haber_mn"), "MAYOR": ("debe_mn", "haber_mn"),
    "SALDOS_INICIALES": ("debe_mn", "haber_mn"), "BALANCE": ("movimiento_debe", "movimiento_haber"),
    "COMPRAS": ("total", None), "VENTAS": ("total", None), "CXC": ("saldo_pendiente", None),
    "CXP": ("saldo_pendiente", None),
}


@dataclass
class OpcionesLectura:
    separador_decimal: str = "AUTO"   # AUTO | PUNTO | COMA
    formato_fecha: str = "AUTO"       # AUTO (dd/mm por defecto) | DMY | MDY | YMD
    sistema_origen: str = "GENERICO"
    ejercicio: int | None = None
    periodo: int | None = None

    @property
    def orden_fecha(self) -> str:
        return "DMY" if self.formato_fecha in ("AUTO", "YMD") else self.formato_fecha


@dataclass
class Extraccion:
    registros: list[dict] = field(default_factory=list)
    observaciones: list[Obs] = field(default_factory=list)
    filas_leidas: int = 0
    filas_vacias: int = 0
    filas_subtotal: int = 0
    filas_saldo_anterior: int = 0
    excluidos: int = 0
    total_archivo: tuple[Decimal | None, Decimal | None] | None = None


def interpretar_dh(valor, sistema: str) -> str | None:
    t = normalizar_texto(valor_texto(valor))
    if t in {"D", "DEBE", "CARGO", "S", "DEBIT", "DB", "DR", "+"} or (sistema == "SAP" and t in SAP_DEBE):
        return "D"
    if t in {"H", "HABER", "ABONO", "A", "CREDITO", "CREDIT", "CR", "-"} or (sistema == "SAP" and t in SAP_HABER):
        return "H"
    if t == "C":  # SAP/inglés: Credit; en ERP locales suele ser Cargo
        return "H" if sistema == "SAP" else "D"
    if t in SAP_DEBE:
        return "D"
    if t in SAP_HABER:
        return "H"
    return None


def _convertir(campo: str, valor, op: OpcionesLectura, obs: list[Obs], fila: int):
    """Convierte según el tipo del campo. Devuelve (valor, ok)."""
    tipo = CAMPOS[campo].tipo
    if es_vacio(valor):
        return None, True
    if tipo == "importe":
        v = parse_importe(valor, op.separador_decimal)
        if v is None:
            obs.append(Obs("IMP001", fila=fila, campo=campo, valor=valor_texto(valor)))
            return None, False
        return v, True
    if tipo == "tasa":
        v = parse_importe(valor, op.separador_decimal, decimales=6)
        if v is None:
            obs.append(Obs("TC003", fila=fila, campo=campo, valor=valor_texto(valor),
                           mensaje="Tipo de cambio no numérico."))
            return None, False
        return v, True
    if tipo == "fecha":
        v = parse_fecha(valor, op.ejercicio, op.orden_fecha)
        if v is None:
            obs.append(Obs("FEC001", fila=fila, campo=campo, valor=valor_texto(valor)))
            return None, False
        return v, True
    if tipo == "entero":
        try:
            return int(Decimal(str(valor_texto(valor)).replace(",", ""))), True
        except Exception:
            obs.append(Obs("EST006", fila=fila, campo=campo, valor=valor_texto(valor)))
            return None, False
    if tipo == "booleano":
        t = normalizar_texto(valor_texto(valor))
        if t in BOOL_SI:
            return True, True
        if t in BOOL_NO:
            return False, True
        obs.append(Obs("EST006", fila=fila, campo=campo, valor=valor_texto(valor),
                       mensaje="Valor lógico no reconocido (use S/N)."))
        return None, True
    if tipo == "moneda":
        m = normalizar_moneda(valor)
        if m is None:
            obs.append(Obs("MON001", fila=fila, campo=campo, valor=valor_texto(valor)))
            return valor_texto(valor)[:3].upper(), False
        return m, True
    if tipo == "codigo":
        s = re.sub(r"\s+", "", valor_texto(valor)).upper()
        return (s or None), True
    if tipo == "dh":
        return valor_texto(valor), True
    s = re.sub(r"\s+", " ", valor_texto(valor)).strip()
    return (s or None), True


def _es_total(textos: list[str]) -> tuple[bool, bool]:
    unido = " ".join(normalizar_texto(t) for t in textos if t)
    if not unido:
        return False, False
    return bool(RE_TOTAL.search(unido)), bool(RE_TOTAL_GENERAL.search(unido))


def extraer(tipo: str, filas: list[list], inicio: int, mapeo: dict[str, int], op: OpcionesLectura) -> Extraccion:
    ex = Extraccion()
    tdef = tipo_def(tipo)
    lineas = tipo in ("DIARIO", "MAYOR", "SALDOS_INICIALES")
    clave_principal = {"DIARIO": "cuenta", "MAYOR": "cuenta", "SALDOS_INICIALES": "cuenta", "BALANCE": "cuenta",
                       "PLAN_CUENTAS": "cuenta", "CENTROS_COSTO": "centro_costo", "TIPOS_CAMBIO": "fecha",
                       "CLIENTES": "documento_tercero", "PROVEEDORES": "documento_tercero"}.get(tipo, "numero_documento")
    totales_generales: list[tuple] = []
    totales_otros: list[tuple] = []
    campo_d, campo_h = CAMPOS_IMPORTE_TOTAL.get(tipo, (None, None))

    for idx in range(inicio, len(filas)):
        fila_excel = idx + 1
        fila = filas[idx]
        ex.filas_leidas += 1
        if all(es_vacio(c) for c in fila):
            ex.filas_vacias += 1
            continue
        crudos = {c: (fila[i] if i < len(fila) else None) for c, i in mapeo.items()}
        textos_fila = [valor_texto(c) for c in fila if isinstance(c, str)]

        # Subtotales y totales: tienen texto de total y no tienen el dato principal del registro,
        # o el dato principal mismo dice «TOTAL».
        es_total, es_general = _es_total(textos_fila)
        principal = valor_texto(crudos.get(clave_principal))
        # Fila con solo importes, sin cuenta ni textos (subtotal sin rótulo, típico de algunos reportes)
        solo_importes = (lineas or tipo == "BALANCE") and es_vacio(principal) \
            and not any(re.search(r"[A-Za-z]", t) for t in textos_fila) \
            and all(es_vacio(crudos.get(c)) for c in ("fecha_contable", "numero_asiento") if c in crudos)
        if solo_importes or (es_total and (es_vacio(principal) or RE_TOTAL.search(normalizar_texto(principal))
                                           or not re.search(r"\d", principal))):
            ex.filas_subtotal += 1
            if campo_d:
                d = parse_importe(crudos.get(campo_d), op.separador_decimal)
                h = parse_importe(crudos.get(campo_h), op.separador_decimal) if campo_h else None
                (totales_generales if es_general else totales_otros).append((d, h))
            continue
        if lineas and RE_SALDO_ANTERIOR.search(" ".join(normalizar_texto(t) for t in textos_fila)) \
                and es_vacio(crudos.get("numero_asiento")):
            ex.filas_saldo_anterior += 1
            continue

        obs_fila: list[Obs] = []
        reg: dict = {"_fila": fila_excel}
        valido = True
        for campo, valor in crudos.items():
            v, ok = _convertir(campo, valor, op, obs_fila, fila_excel)
            reg[campo] = v
            if not ok and CAMPOS[campo].tipo == "importe":
                valido = False

        # Información obligatoria
        for grupo in tdef.requeridos:
            if not any(reg.get(c) not in (None, "") for c in grupo):
                nombres = " / ".join(CAMPOS[c].etiqueta for c in sorted(grupo))
                if not (grupo & {c for c, _ in obs_fila_campos(obs_fila)}):
                    obs_fila.append(Obs("OBL001", fila=fila_excel, campo=",".join(sorted(grupo)),
                                        mensaje=f"Falta información obligatoria: {nombres}."))
                valido = False

        if lineas:
            _derivar_importes_linea(reg, mapeo, op, obs_fila, fila_excel)
        if tipo == "BALANCE":
            _derivar_balance(reg)
        if tipo in ("DIARIO", "MAYOR"):
            reg["ejercicio"] = reg.get("ejercicio") or (reg["fecha_contable"].year if reg.get("fecha_contable") else op.ejercicio)
            if reg.get("periodo") is None:
                reg["periodo"] = reg["fecha_contable"].month if reg.get("fecha_contable") and op.periodo not in (0, 13) else op.periodo

        for o in obs_fila:
            o.cuenta = o.cuenta or reg.get("cuenta")
            o.asiento = o.asiento or _asiento(reg)
            o.documento = o.documento or _documento(reg)
        ex.observaciones.extend(obs_fila)
        if valido:
            ex.registros.append(reg)
        else:
            ex.excluidos += 1

    if ex.filas_vacias:
        ex.observaciones.append(Obs("EST002", mensaje=f"Se omitieron {ex.filas_vacias} fila(s) vacía(s)."))
    if ex.filas_subtotal:
        ex.observaciones.append(Obs("EST003", mensaje=f"Se identificaron y excluyeron {ex.filas_subtotal} fila(s) "
                                                      "de subtotales o totales."))
    if ex.filas_saldo_anterior:
        ex.observaciones.append(Obs("EST003", mensaje=f"Se omitieron {ex.filas_saldo_anterior} fila(s) de «saldo "
                                                      "anterior / vienen» del libro (no son movimientos)."))
    elegidos = totales_generales or (totales_otros[-1:] if len(totales_otros) == 1 else [])
    if elegidos:
        d, h = elegidos[-1]
        ex.total_archivo = (d, h)
    return ex


def obs_fila_campos(obs: list[Obs]):
    for o in obs:
        for c in (o.campo or "").split(","):
            yield c, o


def _asiento(reg: dict) -> str | None:
    if not reg.get("numero_asiento"):
        return None
    partes = [str(reg.get("subdiario") or ""), str(reg["numero_asiento"])]
    return "-".join(p for p in partes if p)


def _documento(reg: dict) -> str | None:
    if not (reg.get("numero_documento") or reg.get("serie")):
        return None
    td = f"{reg['tipo_documento']} " if reg.get("tipo_documento") else ""
    return f"{td}{reg.get('serie') or ''}-{reg.get('numero_documento') or ''}".strip("-")


def _derivar_importes_linea(reg: dict, mapeo: dict, op: OpcionesLectura, obs: list[Obs], fila: int) -> None:
    """Normaliza a debe/haber MN y ME (siempre ≥ 0) a partir de columnas debe/haber o importe con signo."""
    for sufijo in ("mn", "me"):
        d_key, h_key, i_key = f"debe_{sufijo}", f"haber_{sufijo}", f"importe_{sufijo}"
        debe, haber = reg.get(d_key), reg.get(h_key)
        importe = reg.get(i_key)
        if debe is None and haber is None and importe is not None:
            dh = interpretar_dh(reg.get("indicador_dh"), op.sistema_origen) if reg.get("indicador_dh") else None
            if reg.get("indicador_dh") and dh is None:
                obs.append(Obs("IMP005", fila=fila, campo="indicador_dh", valor=str(reg.get("indicador_dh"))))
            if dh == "D":
                debe, haber = abs(importe), CERO
            elif dh == "H":
                debe, haber = CERO, abs(importe)
            else:
                debe, haber = (importe, CERO) if importe >= 0 else (CERO, -importe)
        debe, haber = debe or CERO, haber or CERO
        if debe < 0 or haber < 0:
            obs.append(Obs("IMP003", fila=fila, campo=d_key if debe < 0 else h_key,
                           valor=str(debe if debe < 0 else haber)))
            if debe < 0 and haber == 0:      # reversión en negativo: se traslada al lado contrario
                debe, haber = CERO, -debe
            elif haber < 0 and debe == 0:
                debe, haber = -haber, CERO
        if debe and haber:
            obs.append(Obs("IMP002", fila=fila, campo=f"{d_key},{h_key}", valor=f"{debe} / {haber}"))
        reg[d_key], reg[h_key] = debe, haber
    if not (reg["debe_mn"] or reg["haber_mn"] or reg["debe_me"] or reg["haber_me"]):
        obs.append(Obs("IMP004", fila=fila))
    if reg.get("moneda") is None:
        reg["moneda"] = "PEN" if not (reg["debe_me"] or reg["haber_me"]) else None


def _derivar_balance(reg: dict) -> None:
    for pref in ("saldo_inicial", "saldo_final"):
        firmado = reg.get(pref)
        if firmado is not None and reg.get(f"{pref}_debe") is None and reg.get(f"{pref}_haber") is None:
            reg[f"{pref}_debe"], reg[f"{pref}_haber"] = (firmado, CERO) if firmado >= 0 else (CERO, -firmado)
    for k in ("saldo_inicial_debe", "saldo_inicial_haber", "movimiento_debe", "movimiento_haber",
              "saldo_final_debe", "saldo_final_haber"):
        reg[k] = abs(reg.get(k) or CERO)
