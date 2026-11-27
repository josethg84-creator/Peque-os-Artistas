"""Importación de registros auxiliares (CSV / XLSX) que sustentan anexos especializados.

Son datos que el ERP o el área responsable entregan (registro de activos, cronogramas financieros,
contratos de gastos anticipados, servicios en proceso, inventario valorizado). El sistema no los genera:
si no existen, el anexo se arma desde el libro y lo indica.
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.anexos.generador import auditar
from app.importers.lectores import ErrorImportacion, detectar_formato, leer_csv, leer_xlsx
from app.importers.normalizacion import es_vacio, normalizar_texto, parse_fecha, parse_importe
from app.models import RegistroAuxiliar

# tipo → (campos clave, obligatorios, campos fecha, campos importe, campo cuenta, campo fecha de referencia)
ESPEC = {
    "ACTIVO_FIJO": (["codigo"], ["codigo", "cuenta", "costo_inicial"],
                    ["fecha_adquisicion", "fecha_uso", "fecha_baja"],
                    ["costo_inicial", "adiciones", "mejoras", "transferencias", "bajas", "valor_residual", "depreciacion_acumulada_inicial",
                     "ajustes_depreciacion", "depreciacion_bajas", "tasa_tributaria"], "cuenta", None),
    "CONTRATO_FINANCIERO": (["contrato"], ["contrato", "cuenta", "capital"], ["fecha_desembolso"], ["capital", "tasa", "saldo_inicial"],
                            "cuenta", None),
    "CUOTA_FINANCIERA": (["contrato", "version", "numero"], ["contrato", "numero", "fecha_vencimiento", "capital"], ["fecha_vencimiento"],
                         ["capital", "interes", "comision", "otros"], None, None),
    "GASTO_ANTICIPADO": (["codigo"], ["codigo", "cuenta", "importe", "fecha_inicio", "fecha_fin"],
                         ["fecha_documento", "fecha_inicio", "fecha_fin"], ["importe"], "cuenta", None),
    "SERVICIO_PROCESO": (["proyecto"], ["proyecto"], ["fecha_inicio", "fecha_estimada", "fecha_real"], ["costo_acumulado_anterior"],
                         "cuenta", None),
    "INVENTARIO": (["codigo", "almacen"], ["codigo", "cuenta", "fecha_corte"], ["fecha_corte"], ["cantidad", "valor"], "cuenta", "fecha_corte"),
}
SINONIMOS = {"codigo_activo": "codigo", "cod": "codigo", "n_contrato": "contrato", "nro_contrato": "contrato", "cuota": "numero", "version_cronograma": "version", "n_version": "version",
             "n_cuota": "numero", "vencimiento": "fecha_vencimiento", "amortizacion": "capital", "intereses": "interes",
             "comisiones": "comision", "vida_util": "vida_util_meses", "costo": "costo_inicial", "inicio": "fecha_inicio",
             "fin": "fecha_fin", "termino": "fecha_fin", "fecha_termino": "fecha_fin", "monto": "importe", "orden_de_servicio": "orden_servicio",
             "os": "orden_servicio", "cuenta_contable": "cuenta", "costo_anterior": "costo_acumulado_anterior", "fecha": "fecha_corte",
             "entidad_financiera": "entidad", "ruc": "ruc", "precio_unitario": "costo_unitario", "valor_total": "valor"}


def _campo(enc) -> str:
    c = normalizar_texto(enc).lower()
    c = "".join(ch if ch.isalnum() else "_" for ch in c).strip("_")
    while "__" in c:
        c = c.replace("__", "_")
    return SINONIMOS.get(c, c)


def importar(db: Session, empresa_id: int, usuario: str, tipo: str, nombre: str, contenido: bytes) -> dict:
    if tipo not in ESPEC:
        raise ErrorImportacion(f"Tipo de registro no válido: {tipo}")
    claves, obligatorios, fechas, importes, campo_cuenta, campo_ref = ESPEC[tipo]
    fmt = detectar_formato(nombre, contenido)
    if fmt == "CSV":
        filas = leer_csv(contenido)
    elif fmt == "XLSX":
        filas = leer_xlsx(contenido)
    else:
        raise ErrorImportacion("Use un archivo CSV o XLSX.")
    if not filas:
        raise ErrorImportacion("El archivo está vacío.")
    enc = [_campo(x) for x in filas[0]]
    faltan = [c for c in obligatorios if c not in enc]
    if faltan:
        raise ErrorImportacion(f"Faltan columnas obligatorias: {', '.join(faltan)}. Columnas leídas: {', '.join(enc)}")
    nuevos = actualizados = 0
    errores = []
    existentes = {(r.clave, r.fecha_referencia): r for r in db.scalars(select(RegistroAuxiliar).where(
        RegistroAuxiliar.empresa_id == empresa_id, RegistroAuxiliar.tipo == tipo))}
    for i, f in enumerate(filas[1:], start=2):
        if all(es_vacio(v) for v in f):
            continue
        d = {}
        for c, v in zip(enc, f):
            if es_vacio(v):
                continue
            if c in fechas:
                fv = parse_fecha(v)
                if fv is None:
                    errores.append(f"Fila {i}: fecha no válida en «{c}» ({v})")
                    continue
                d[c] = fv.isoformat()
            elif c in importes:
                iv = parse_importe(v, decimales=6 if c == "tasa_tributaria" else 2)
                if iv is None:
                    errores.append(f"Fila {i}: importe no válido en «{c}» ({v})")
                    continue
                d[c] = str(iv)
            elif c in ("cantidad", "costo_unitario", "tasa"):
                iv = parse_importe(v, decimales=6)
                d[c] = str(iv) if iv is not None else None
            else:
                d[c] = str(v).strip() if not isinstance(v, float) or not v.is_integer() else str(int(v))
        falta = [c for c in obligatorios if c not in d]
        if falta:
            errores.append(f"Fila {i}: sin {', '.join(falta)}")
            continue
        clave = "-".join(str(d[c]) for c in claves if d.get(c) not in (None, ""))[:80]  # componente opcional (versión) omitido si falta
        ref = parse_fecha(d[campo_ref]) if campo_ref else None
        cuenta = (d.get(campo_cuenta) or "").strip() or None if campo_cuenta else None
        x = existentes.get((clave, ref))
        if x:
            if json.loads(x.datos) != d or x.cuenta != cuenta:
                auditar(db, empresa_id, usuario, "ACTUALIZAR_REGISTRO", "registro", x.id, {"antes": json.loads(x.datos), "despues": d})
                x.datos, x.cuenta, x.archivo, x.fila, x.vigente, x.usuario = json.dumps(d), cuenta, nombre[:255], i, True, usuario
                actualizados += 1
        else:
            x = RegistroAuxiliar(empresa_id=empresa_id, tipo=tipo, clave=clave, cuenta=cuenta, fecha_referencia=ref, datos=json.dumps(d),
                                 archivo=nombre[:255], fila=i, usuario=usuario)
            db.add(x)
            existentes[(clave, ref)] = x
            nuevos += 1
    auditar(db, empresa_id, usuario, "IMPORTAR_REGISTRO", "registro", None,
            {"tipo": tipo, "archivo": nombre, "nuevos": nuevos, "actualizados": actualizados, "errores": len(errores)})
    db.commit()
    return {"tipo": tipo, "nuevos": nuevos, "actualizados": actualizados, "errores": errores[:200]}
