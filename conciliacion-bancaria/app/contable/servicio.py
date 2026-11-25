"""Orquestación del asistente de importación contable: análisis, validación, confirmación,
plantillas de homologación y anulación de lotes."""
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from decimal import Decimal

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.contable import archivos
from app.contable.campos import CAMPOS, SISTEMAS_ORIGEN, TIPOS, describir_tipo, grupos_faltantes
from app.contable.homologacion import (CAMPOS_IMPORTE_TOTAL, OpcionesLectura, _asiento, extraer, mapeo_a_plantilla,
                                       sugerir_mapeo)
from app.contable.observaciones import Obs
from app.contable.validacion import cargar_contexto, validar
from app.core import auditoria
from app.importers.lectores import ErrorImportacion
from app.importers.normalizacion import es_vacio
from app.models import (CentroCosto, CuentaContable, DocumentoRegistro, Empresa, LineaDiario, LoteContable,
                        ObservacionImportacion, PlantillaImportacion, SaldoCuenta, Severidad, Tercero, TipoCambio)

CERO = Decimal("0")


class ErrorContable(Exception):
    def __init__(self, mensaje: str, status: int = 422):
        super().__init__(mensaje)
        self.status = status


@dataclass
class Parametros:
    token: str
    empresa_id: int
    tipo: str
    ejercicio: int | None = None
    periodo: int | None = None
    sistema_origen: str = "GENERICO"
    hoja: str | None = None
    fila_encabezado: int = 1
    filas_encabezado: int = 1
    delimitador: str = "AUTO"
    separador_decimal: str = "AUTO"
    formato_fecha: str = "AUTO"
    mapeo: dict[str, int] = field(default_factory=dict)
    importacion_completa: bool = True
    plantilla_id: int | None = None

    def verificar(self):
        if self.tipo not in TIPOS:
            raise ErrorContable("Tipo de información no válido.")
        if self.sistema_origen not in SISTEMAS_ORIGEN:
            raise ErrorContable("Sistema de origen no válido.")
        if TIPOS[self.tipo].transaccional and not self.ejercicio:
            raise ErrorContable("Indique el ejercicio contable.")
        if self.periodo is not None and not 0 <= self.periodo <= 13:
            raise ErrorContable("El periodo debe estar entre 00 (apertura) y 13 (cierre).")
        if self.separador_decimal not in ("AUTO", "PUNTO", "COMA"):
            raise ErrorContable("Separador decimal no válido.")
        if self.formato_fecha not in ("AUTO", "DMY", "MDY", "YMD"):
            raise ErrorContable("Formato de fecha no válido.")
        desconocidos = set(self.mapeo) - set(TIPOS[self.tipo].campos)
        if desconocidos:
            raise ErrorContable(f"Campos no válidos para {TIPOS[self.tipo].nombre}: {', '.join(sorted(desconocidos))}.")
        if len(set(self.mapeo.values())) != len(self.mapeo):
            raise ErrorContable("Una misma columna está asignada a más de un campo.")


# ------------------------------------------------------------------ pasos 3–5
def leer(p_token: str, hoja: str | None, delimitador: str = "AUTO") -> tuple[dict, list[list]]:
    m = archivos.meta(p_token)
    filas = archivos.leer_filas(archivos.contenido(p_token), m["formato"], hoja, delimitador)
    return m, filas


def vista_previa(token: str, tipo: str, hoja: str | None, delimitador: str = "AUTO", limite: int = 30) -> dict:
    m, filas = leer(token, hoja, delimitador)
    fila, n, puntaje = archivos.detectar_encabezado(filas, tipo) if tipo in TIPOS else (1, 1, 0)
    return {"archivo": m, "hoja": hoja or m["hojas"][0]["nombre"], "total_filas": len(filas),
            "filas": [[archivos.valor_texto(c) for c in f] for f in filas[:limite]],
            "sugerencia_encabezado": {"fila": fila, "filas": n, "puntaje": puntaje}}


def plantillas_para(db: Session, empresa_id: int, tipo: str, sistema: str | None = None):
    q = select(PlantillaImportacion).where(PlantillaImportacion.tipo_informacion == tipo,
                                           (PlantillaImportacion.empresa_id == empresa_id)
                                           | (PlantillaImportacion.empresa_id.is_(None)))
    if sistema:
        q = q.where(PlantillaImportacion.sistema_origen == sistema)
    return list(db.scalars(q.order_by(PlantillaImportacion.usos.desc(), PlantillaImportacion.id)))


def homologar(db: Session, p: Parametros) -> dict:
    m, filas = leer(p.token, p.hoja, p.delimitador)
    enc = archivos.construir_encabezado(filas, p.fila_encabezado, p.filas_encabezado)
    plantillas = plantillas_para(db, p.empresa_id, p.tipo)
    elegida = None
    if p.plantilla_id:
        elegida = next((x for x in plantillas if x.id == p.plantilla_id), None)
    elif plantillas:  # la plantilla que mejor encaja con los encabezados del archivo
        claves = set(mapeo_a_plantilla({i: i for i in range(len(enc.nombres))}, enc.nombres, False).values()) \
            if enc.fila else set()
        def encaje(pl):
            ref = json.loads(pl.mapeo).values()
            return sum(1 for r in ref if r in claves or (r.startswith("#") and not enc.fila))
        mejor = max(plantillas, key=encaje)
        if encaje(mejor) >= max(2, len(json.loads(mejor.mapeo)) * 0.6):
            elegida = mejor
    sugerido = sugerir_mapeo(p.tipo, enc.nombres, json.loads(elegida.mapeo) if elegida else None)
    datos = filas[enc.inicio_datos:enc.inicio_datos + 400]
    muestras = {}
    for i in range(len(enc.nombres)):
        vals = [archivos.valor_texto(f[i]) for f in datos if i < len(f) and not es_vacio(f[i])]
        muestras[i] = vals[:3]
    faltan = grupos_faltantes(p.tipo, set(sugerido))
    return {
        "tipo": describir_tipo(p.tipo),
        "encabezados": enc.nombres,
        "fila_encabezado": enc.fila, "filas_encabezado": enc.filas,
        "muestras": {str(k): v for k, v in muestras.items()},
        "mapeo_sugerido": sugerido,
        "faltantes": [sorted(g) for g in faltan],
        "plantilla_aplicada": _plantilla_dict(elegida) if elegida else None,
        "plantillas": [_plantilla_dict(x) for x in plantillas],
        "opciones_plantilla": json.loads(elegida.opciones) if elegida and elegida.opciones else None,
    }


def _plantilla_dict(pl: PlantillaImportacion) -> dict:
    return {"id": pl.id, "nombre": pl.nombre, "sistema_origen": pl.sistema_origen, "tipo_informacion": pl.tipo_informacion,
            "empresa_id": pl.empresa_id, "hoja": pl.hoja, "fila_encabezado": pl.fila_encabezado,
            "mapeo": json.loads(pl.mapeo), "opciones": json.loads(pl.opciones) if pl.opciones else {},
            "usos": pl.usos, "usuario": pl.usuario,
            "actualizado_en": pl.actualizado_en.isoformat() if pl.actualizado_en else None}


# ------------------------------------------------------------------ paso 6: validación
@dataclass
class Procesado:
    meta: dict
    encabezados: list[str]
    extraccion: object
    observaciones: list[Obs]
    ctx: object


def procesar(db: Session, p: Parametros, avance) -> Procesado:
    p.verificar()
    avance(5, "Leyendo el archivo")
    m, filas = leer(p.token, p.hoja, p.delimitador)
    hoja = p.hoja or m["hojas"][0]["nombre"]
    enc = archivos.construir_encabezado(filas, p.fila_encabezado, p.filas_encabezado)
    avance(15, f"Archivo leído: {len(filas)} filas")
    faltan = grupos_faltantes(p.tipo, set(p.mapeo))
    if faltan or any(i >= len(enc.nombres) for i in p.mapeo.values()):
        nombres = "; ".join(" o ".join(CAMPOS[c].etiqueta for c in sorted(g)) for g in faltan)
        obs = [Obs("EST001", mensaje=f"Faltan columnas obligatorias: {nombres or 'columna fuera de rango'}.")]
        return _finalizar(Procesado(m, enc.nombres, None, obs, None), hoja)

    op = OpcionesLectura(p.separador_decimal, p.formato_fecha, p.sistema_origen, p.ejercicio, p.periodo)
    avance(20, "Normalizando registros")
    ex = extraer(p.tipo, filas, enc.inicio_datos, p.mapeo, op)
    avance(55, f"{len(ex.registros)} registros normalizados; validando")
    vacias = [c for c, i in p.mapeo.items()
              if all(es_vacio(f[i] if i < len(f) else None) for f in filas[enc.inicio_datos:])]
    ctx = cargar_contexto(db, p.empresa_id, p.tipo, p.ejercicio, p.periodo, p.importacion_completa, m["hash"])
    avance(65, "Aplicando reglas contables")
    obs = ex.observaciones + validar(db, ex, p.mapeo, ctx, vacias)
    avance(90, "Clasificando observaciones")
    return _finalizar(Procesado(m, enc.nombres, ex, obs, ctx), hoja)


def _finalizar(pr: Procesado, hoja: str) -> Procesado:
    for o in pr.observaciones:
        o.archivo = pr.meta["nombre"]
        o.hoja = hoja
    pr.observaciones.sort(key=lambda o: (Severidad.ORDEN[o.severidad], o.codigo, o.fila or 0))
    return pr


def _serializar(v):
    if isinstance(v, Decimal):
        return str(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def resumen(pr: Procesado, p: Parametros) -> dict:
    sev = Counter(o.severidad for o in pr.observaciones)
    cod = Counter(o.codigo for o in pr.observaciones)
    ex = pr.extraccion
    campo_d, campo_h = CAMPOS_IMPORTE_TOTAL.get(p.tipo, (None, None))
    total_d = sum((r.get(campo_d) or CERO for r in ex.registros), CERO) if ex and campo_d else None
    total_h = sum((r.get(campo_h) or CERO for r in ex.registros), CERO) if ex and campo_h else None
    asientos = len({_asiento(r) for r in ex.registros if r.get("numero_asiento")}) if ex else 0
    return {
        "archivo": pr.meta["nombre"], "hoja": pr.observaciones[0].hoja if pr.observaciones else p.hoja,
        "tipo": p.tipo, "ejercicio": p.ejercicio, "periodo": p.periodo,
        "estructura_valida": not any(o.codigo == "EST001" for o in pr.observaciones),
        "filas_leidas": ex.filas_leidas if ex else 0, "filas_vacias": ex.filas_vacias if ex else 0,
        "filas_subtotal": ex.filas_subtotal if ex else 0,
        "registros_validos": len(ex.registros) if ex else 0, "registros_excluidos": ex.excluidos if ex else 0,
        "asientos": asientos,
        "total_debe": _serializar(total_d), "total_haber": _serializar(total_h),
        "total_archivo": [_serializar(x) for x in ex.total_archivo] if ex and ex.total_archivo else None,
        "severidades": {s: sev.get(s, 0) for s in ("CRITICO", "ALTO", "MEDIO", "INFORMATIVO")},
        "codigos": dict(cod.most_common()),
        "archivo_ya_importado": pr.ctx.lote_previo_mismo_archivo if pr.ctx else None,
    }


def validar_y_guardar(db: Session, p: Parametros, avance) -> dict:
    pr = procesar(db, p, avance)
    res = {"resumen": resumen(pr, p), "parametros": asdict(p),
           "muestra": [{k: _serializar(v) for k, v in r.items()} for r in (pr.extraccion.registros[:50] if pr.extraccion else [])]}
    ruta = archivos._ruta(p.token)
    (ruta / "validacion.json").write_text(json.dumps(
        {**res, "observaciones": [o.como_dict() for o in pr.observaciones]}, ensure_ascii=False, default=str))
    return res


def observaciones_validadas(token: str) -> list[dict]:
    ruta = archivos._ruta(token) / "validacion.json"
    if not ruta.exists():
        raise ErrorContable("Primero valide el archivo.")
    return json.loads(ruta.read_text())["observaciones"]


# ------------------------------------------------------------------ paso 7: confirmación
def confirmar(db: Session, p: Parametros, usuario: str, avance, *, confirmar_criticos: bool = False,
              motivo_criticos: str | None = None, reemplazar_previos: bool = False,
              guardar_plantilla: str | None = None) -> dict:
    if not db.get(Empresa, p.empresa_id):
        raise ErrorContable("Empresa no encontrada.", 404)
    pr = procesar(db, p, lambda pct, e: avance(int(pct * 0.6), e))
    sev = Counter(o.severidad for o in pr.observaciones)
    if any(o.codigo == "EST001" for o in pr.observaciones):
        raise ErrorContable("El archivo es estructuralmente inválido; corrija la homologación antes de importar.")
    if sev["CRITICO"] and not confirmar_criticos:
        raise ErrorContable(f"Hay {sev['CRITICO']} observación(es) crítica(s). Para importar de todas formas "
                            "confírmelo indicando el motivo.", 409)
    if sev["CRITICO"] and len((motivo_criticos or "").strip()) < 10:
        raise ErrorContable("Indique el motivo para importar con observaciones críticas (mínimo 10 caracteres).")
    ex = pr.extraccion
    if not ex.registros:
        raise ErrorContable("No hay registros válidos para importar.")

    avance(62, "Registrando lote")
    tdef = TIPOS[p.tipo]
    if reemplazar_previos and tdef.transaccional:
        previos = db.scalars(select(LoteContable).where(
            LoteContable.empresa_id == p.empresa_id, LoteContable.tipo_informacion == p.tipo,
            LoteContable.ejercicio == p.ejercicio, LoteContable.periodo == p.periodo,
            LoteContable.estado == "ACTIVO")).all()
        for previo in previos:
            _anular(db, previo, f"Reemplazado por nueva importación de {pr.meta['nombre']}", usuario)

    campo_d, campo_h = CAMPOS_IMPORTE_TOTAL.get(p.tipo, (None, None))
    plantilla = None
    if guardar_plantilla:
        plantilla = guardar_plantilla_desde(db, p, pr.encabezados, guardar_plantilla.strip(), usuario)
    elif p.plantilla_id:
        plantilla = db.get(PlantillaImportacion, p.plantilla_id)
        if plantilla:
            plantilla.usos += 1
    lote = LoteContable(
        empresa_id=p.empresa_id, tipo_informacion=p.tipo, ejercicio=p.ejercicio or 0, periodo=p.periodo,
        sistema_origen=p.sistema_origen, nombre_archivo=pr.meta["nombre"], hoja=pr.observaciones[0].hoja if pr.observaciones else p.hoja,
        fila_encabezado=p.fila_encabezado, hash_archivo=pr.meta["hash"], plantilla_id=plantilla.id if plantilla else None,
        mapeo=json.dumps({c: pr.encabezados[i] for c, i in p.mapeo.items()}, ensure_ascii=False),
        opciones=json.dumps({"separador_decimal": p.separador_decimal, "formato_fecha": p.formato_fecha,
                             "delimitador": p.delimitador, "filas_encabezado": p.filas_encabezado}),
        importacion_completa=p.importacion_completa, filas_leidas=ex.filas_leidas, filas_vacias=ex.filas_vacias,
        filas_subtotal=ex.filas_subtotal, registros_importados=len(ex.registros), registros_excluidos=ex.excluidos,
        total_debe=sum((r.get(campo_d) or CERO for r in ex.registros), CERO) if campo_d else CERO,
        total_haber=sum((r.get(campo_h) or CERO for r in ex.registros), CERO) if campo_h else CERO,
        total_archivo_debe=ex.total_archivo[0] if ex.total_archivo else None,
        total_archivo_haber=ex.total_archivo[1] if ex.total_archivo else None,
        obs_critico=sev["CRITICO"], obs_alto=sev["ALTO"], obs_medio=sev["MEDIO"], obs_informativo=sev["INFORMATIVO"],
        motivo_criticos=(motivo_criticos or "").strip()[:255] or None, usuario=usuario)
    db.add(lote)
    db.flush()

    avance(70, "Guardando registros normalizados")
    _persistir(db, lote, p, ex.registros, lote.hoja, avance)
    avance(92, "Guardando observaciones")
    filas_obs = [{"lote_id": lote.id, **{k: v for k, v in o.como_dict().items() if k not in ("titulo",)}}
                 for o in pr.observaciones]
    for o in filas_obs:
        o["valor"] = (o["valor"] or None) and str(o["valor"])[:120]
        o["mensaje"] = o["mensaje"][:500]
        o["recomendacion"] = (o["recomendacion"] or "")[:500] or None
        o["asiento"] = (o["asiento"] or None) and str(o["asiento"])[:80]
        o["documento"] = (o["documento"] or None) and str(o["documento"])[:80]
    for i in range(0, len(filas_obs), 1000):
        db.execute(insert(ObservacionImportacion), filas_obs[i:i + 1000])
    auditoria.registrar(
        db, usuario=usuario, entidad="lote_contable", entidad_id=lote.id, accion="IMPORTAR", empresa_id=p.empresa_id,
        detalle=(f"{tdef.nombre} {p.ejercicio or ''}-{p.periodo if p.periodo is not None else ''} · {pr.meta['nombre']} · "
                 f"{len(ex.registros)} registros · obs C{sev['CRITICO']}/A{sev['ALTO']}/M{sev['MEDIO']}/I{sev['INFORMATIVO']}"
                 + (f" · importado con críticos: {motivo_criticos.strip()}" if sev["CRITICO"] else "")))
    db.commit()
    archivos.archivar(p.token, lote.id)  # se conserva para la consulta de la línea original
    return lote_dict(lote)


def _limpio(r: dict, campos) -> dict:
    return {c: r.get(c) for c in campos}


def _persistir(db: Session, lote: LoteContable, p: Parametros, regs: list[dict], hoja: str, avance) -> None:
    base = {"lote_id": lote.id, "empresa_id": p.empresa_id}
    t = p.tipo
    if t in ("DIARIO", "MAYOR"):
        cols = [c.key for c in LineaDiario.__table__.columns if c.key not in ("id", "lote_id", "empresa_id", "hoja", "fila_origen")]
        filas = [{**base, **_limpio(r, cols), "ejercicio": r.get("ejercicio") or p.ejercicio,
                  "cuenta": r["cuenta"][:20], "hoja": hoja, "fila_origen": r["_fila"],
                  "numero_linea": r.get("numero_linea") or n + 1,
                  "moneda": r.get("moneda") or "PEN"} for n, r in enumerate(regs)]
        _insertar_lotes(db, LineaDiario, filas, avance)
    elif t in ("BALANCE", "SALDOS_INICIALES"):
        filas = []
        for r in regs:
            fila = {**base, "tipo": t, "ejercicio": p.ejercicio, "periodo": p.periodo, "cuenta": r["cuenta"],
                    "descripcion_cuenta": r.get("descripcion_cuenta"), "hoja": hoja, "fila_origen": r["_fila"],
                    "documento_tercero": r.get("documento_tercero"), "moneda": r.get("moneda") or "PEN"}
            if t == "BALANCE":
                fila.update({k: r[k] for k in ("saldo_inicial_debe", "saldo_inicial_haber", "movimiento_debe",
                                               "movimiento_haber", "saldo_final_debe", "saldo_final_haber")})
            else:
                neto = r["debe_mn"] - r["haber_mn"]
                fila.update(saldo_inicial_debe=max(neto, CERO), saldo_inicial_haber=max(-neto, CERO),
                            saldo_final_debe=max(neto, CERO), saldo_final_haber=max(-neto, CERO),
                            saldo_me_debe=r.get("debe_me") or None, saldo_me_haber=r.get("haber_me") or None)
            filas.append(fila)
        _insertar_lotes(db, SaldoCuenta, filas, avance)
    elif t in ("COMPRAS", "VENTAS", "CXC", "CXP"):
        filas = [{**base, "tipo": t, "ejercicio": p.ejercicio, "periodo": p.periodo, "cuo": r.get("cuo"),
                  "fecha_emision": r.get("fecha_emision"), "fecha_vencimiento": r.get("fecha_vencimiento"),
                  "tipo_documento": r.get("tipo_documento"), "serie": r.get("serie"), "numero": r.get("numero_documento"),
                  "tipo_documento_identidad": r.get("tipo_documento_identidad"),
                  "documento_tercero": r.get("documento_tercero"), "razon_social": r.get("razon_social"),
                  "moneda": r.get("moneda") or "PEN", "tipo_cambio": r.get("tipo_cambio"),
                  "base_imponible": r.get("base_imponible") or CERO, "igv": r.get("igv") or CERO,
                  "no_gravado": r.get("no_gravado") or CERO, "otros_tributos": r.get("otros_tributos") or CERO,
                  "total": r.get("total") or CERO, "importe_me": r.get("saldo_pendiente_me"),
                  "saldo_pendiente": r.get("saldo_pendiente"), "cuenta": r.get("cuenta"), "glosa": r.get("glosa"),
                  "codigo_detraccion": r.get("codigo_detraccion"), "constancia_detraccion": r.get("constancia_detraccion"),
                  "retencion": r.get("retencion"), "hoja": hoja, "fila_origen": r["_fila"]} for r in regs]
        _insertar_lotes(db, DocumentoRegistro, filas, avance)
    elif t == "PLAN_CUENTAS":
        def nat(v):
            v = (v or "").strip().upper()[:1]
            return {"D": "D", "A": "A", "C": "A"}.get(v)
        _upsert(db, CuentaContable, {"empresa_id": p.empresa_id}, "codigo", [
            {"codigo": r["cuenta"], "descripcion": (r.get("descripcion_cuenta") or "")[:255], "nivel": r.get("nivel") or len(r["cuenta"]),
             "naturaleza": nat(r.get("naturaleza")),
             "admite_movimiento": r.get("admite_movimiento") if r.get("admite_movimiento") is not None else True,
             "activa": r.get("activa") if r.get("activa") is not None else True,
             "requiere_centro_costo": bool(r.get("requiere_centro_costo")),
             "cuenta_destino_debe": r.get("cuenta_destino_debe"), "cuenta_destino_haber": r.get("cuenta_destino_haber"),
             "lote_id": lote.id} for r in regs])
    elif t in ("CLIENTES", "PROVEEDORES"):
        rol = "CLIENTE" if t == "CLIENTES" else "PROVEEDOR"
        _upsert(db, Tercero, {"empresa_id": p.empresa_id, "rol": rol}, "numero_documento", [
            {"numero_documento": r["documento_tercero"], "razon_social": (r.get("razon_social") or "")[:255],
             "tipo_documento_identidad": r.get("tipo_documento_identidad"), "direccion": r.get("direccion"),
             "estado_contribuyente": r.get("estado_contribuyente"), "condicion_domicilio": r.get("condicion_domicilio"),
             "lote_id": lote.id} for r in regs])
    elif t == "CENTROS_COSTO":
        _upsert(db, CentroCosto, {"empresa_id": p.empresa_id}, "codigo", [
            {"codigo": r["centro_costo"], "descripcion": (r.get("descripcion") or "")[:255],
             "cuenta_destino": r.get("cuenta_destino"), "unidad_negocio": r.get("unidad_negocio"),
             "activo": r.get("activa") if r.get("activa") is not None else True, "lote_id": lote.id} for r in regs])
    elif t == "TIPOS_CAMBIO":
        existentes = {(x.fecha, x.moneda): x for x in db.scalars(select(TipoCambio).where(TipoCambio.empresa_id == p.empresa_id))}
        vistos = set()
        for r in regs:
            k = (r["fecha"], r.get("moneda") or "USD")
            if k in vistos:
                continue
            vistos.add(k)
            compra, venta = r.get("compra") or r.get("venta"), r.get("venta") or r.get("compra")
            if k in existentes:
                existentes[k].compra, existentes[k].venta, existentes[k].lote_id = compra, venta, lote.id
            else:
                db.add(TipoCambio(empresa_id=p.empresa_id, fecha=k[0], moneda=k[1], compra=compra, venta=venta,
                                  lote_id=lote.id))


def _ajustar_longitudes(modelo, filas: list[dict]) -> None:
    """Recorta textos al largo de su columna (PostgreSQL rechaza excesos; SQLite no los controla)."""
    largos = {c.key: c.type.length for c in modelo.__table__.columns if getattr(c.type, "length", None)}
    for f in filas:
        for k, n in largos.items():
            v = f.get(k)
            if isinstance(v, str) and len(v) > n:
                f[k] = v[:n]


def _insertar_lotes(db, modelo, filas, avance, tam=2000):
    _ajustar_longitudes(modelo, filas)
    for i in range(0, len(filas), tam):
        db.execute(insert(modelo), filas[i:i + tam])
        avance(70 + int(20 * (i + tam) / max(len(filas), 1)), f"Guardando registros ({min(i + tam, len(filas))}/{len(filas)})")


def _upsert(db, modelo, filtro: dict, clave: str, filas: list[dict]):
    q = select(modelo)
    for k, v in filtro.items():
        q = q.where(getattr(modelo, k) == v)
    existentes = {getattr(x, clave): x for x in db.scalars(q)}
    vistos = set()
    for f in filas:
        if f[clave] in vistos:
            continue
        vistos.add(f[clave])
        _ajustar_longitudes(modelo, [f])
        obj = existentes.get(f[clave])
        if obj:
            for k, v in f.items():
                setattr(obj, k, v)
        else:
            db.add(modelo(**filtro, **f))


# ------------------------------------------------------------------ plantillas, lotes
def guardar_plantilla_desde(db: Session, p: Parametros, encabezados: list[str], nombre: str,
                            usuario: str) -> PlantillaImportacion:
    if len(nombre) < 3:
        raise ErrorContable("El nombre de la plantilla debe tener al menos 3 caracteres.")
    mapeo = mapeo_a_plantilla(p.mapeo, encabezados, p.fila_encabezado == 0)
    opciones = {"separador_decimal": p.separador_decimal, "formato_fecha": p.formato_fecha,
                "delimitador": p.delimitador, "filas_encabezado": p.filas_encabezado}
    pl = db.scalar(select(PlantillaImportacion).where(
        PlantillaImportacion.empresa_id == p.empresa_id, PlantillaImportacion.sistema_origen == p.sistema_origen,
        PlantillaImportacion.tipo_informacion == p.tipo, PlantillaImportacion.nombre == nombre))
    if pl is None:
        pl = PlantillaImportacion(empresa_id=p.empresa_id, sistema_origen=p.sistema_origen, tipo_informacion=p.tipo,
                                  nombre=nombre, usuario=usuario, mapeo="{}")
        db.add(pl)
    pl.mapeo = json.dumps(mapeo, ensure_ascii=False)
    pl.opciones = json.dumps(opciones)
    pl.hoja = p.hoja
    pl.fila_encabezado = p.fila_encabezado
    pl.usuario = usuario
    pl.usos = (pl.usos or 0) + 1
    db.flush()
    auditoria.registrar(db, usuario=usuario, entidad="plantilla_importacion", entidad_id=pl.id, accion="GUARDAR",
                        empresa_id=p.empresa_id, detalle=f"{SISTEMAS_ORIGEN[p.sistema_origen]} · {TIPOS[p.tipo].nombre} · {nombre}")
    return pl


def lote_dict(l: LoteContable) -> dict:
    d = {c.key: _serializar(getattr(l, c.key)) for c in LoteContable.__table__.columns}
    d["mapeo"] = json.loads(l.mapeo) if l.mapeo else {}
    d["opciones"] = json.loads(l.opciones) if l.opciones else {}
    d["tipo_nombre"] = TIPOS[l.tipo_informacion].nombre
    return d


def _anular(db: Session, lote: LoteContable, motivo: str, usuario: str) -> None:
    lote.estado = "ANULADO"
    lote.motivo_anulacion = motivo[:255]
    auditoria.registrar(db, usuario=usuario, entidad="lote_contable", entidad_id=lote.id, accion="ANULAR",
                        empresa_id=lote.empresa_id, detalle=motivo)


def anular(db: Session, lote: LoteContable, motivo: str, usuario: str) -> dict:
    if lote.estado == "ANULADO":
        raise ErrorContable("El lote ya está anulado.", 409)
    if not TIPOS[lote.tipo_informacion].transaccional:
        raise ErrorContable("Los maestros (plan de cuentas, terceros, centros de costo, tipos de cambio) se "
                            "actualizan registro a registro y no se anulan por lote: importe una versión corregida.", 409)
    if len((motivo or "").strip()) < 5:
        raise ErrorContable("Indique el motivo de la anulación (mínimo 5 caracteres).")
    _anular(db, lote, motivo.strip(), usuario)
    db.commit()
    return lote_dict(lote)
