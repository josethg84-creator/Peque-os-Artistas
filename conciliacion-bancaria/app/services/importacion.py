"""Servicio de importación: análisis, detección de duplicados, persistencia y anulación."""
import hashlib
import json
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import auditoria
from app.importers.analizador import ResultadoAnalisis, analizar
from app.importers.lectores import ErrorImportacion
from app.models import (CuentaBancaria, EstadoConciliacion, EstadoImportacion, Importacion,
                        MovimientoBanco, MovimientoLibro)

ACCIONES_DUPLICADOS = ("marcar", "omitir")


class ConflictoImportacion(Exception):
    def __init__(self, mensaje: str, importacion_id: int):
        super().__init__(mensaje)
        self.importacion_id = importacion_id


def _modelo(tipo: str):
    return MovimientoBanco if tipo == "BANCO" else MovimientoLibro


def hash_archivo(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def importacion_previa(db: Session, cuenta_id: int, tipo: str, h: str) -> Importacion | None:
    return db.scalar(select(Importacion).where(
        Importacion.cuenta_bancaria_id == cuenta_id, Importacion.tipo == tipo,
        Importacion.hash_archivo == h, Importacion.estado == EstadoImportacion.ACTIVA))


def analizar_para_cuenta(
    db: Session,
    cuenta: CuentaBancaria,
    nombre: str,
    contenido: bytes,
    tipo: str,
    *,
    mapeo_manual: dict[int, str] | None = None,
    anio: int | None = None,
    invertir_signo: bool = False,
) -> ResultadoAnalisis:
    res = analizar(
        nombre, contenido, tipo, cuenta.moneda,
        mapeo_manual=mapeo_manual, anio=anio,
        cuenta_contable=cuenta.cuenta_contable if tipo == "LIBRO" else None,
        invertir_signo=invertir_signo,
    )
    marcar_duplicados(db, cuenta.id, tipo, res)
    if res.filas_filtradas:
        res.advertencias.append(
            f"Se ignoraron {res.filas_filtradas} fila(s) de subcuentas distintas a {cuenta.cuenta_contable}.")
    return res


def marcar_duplicados(db: Session, cuenta_id: int, tipo: str, res: ResultadoAnalisis) -> None:
    """Anota en cada registro `duplicado` = {origen, motivo, existente_id}.

    - Dentro del archivo: misma huella; si ambos traen saldo y difiere, son movimientos
      distintos (p. ej. dos cobros de ITF iguales el mismo día) y no se marcan.
    - Contra la base: misma huella en un movimiento vigente de otra importación
      (estados de cuenta con periodos solapados). Si ambos tienen saldo, debe coincidir.
    """
    vistos: dict[tuple, int] = {}
    for r in res.registros:
        r["duplicado"] = None
        clave = (r["hash"], r.get("saldo"))
        if clave in vistos:
            r["duplicado"] = {"origen": "ARCHIVO", "existente_id": None,
                              "motivo": f"Repetido dentro del archivo (igual a la fila {vistos[clave]})."}
        else:
            vistos[clave] = r["fila"]

    hashes = {r["hash"] for r in res.registros}
    if not hashes:
        return
    Modelo = _modelo(tipo)
    existentes: dict[str, list] = defaultdict(list)
    for lote in _trozos(list(hashes), 500):
        for m in db.scalars(select(Modelo).where(
                Modelo.cuenta_bancaria_id == cuenta_id, Modelo.hash_registro.in_(lote),
                Modelo.estado_conciliacion != EstadoConciliacion.EXCLUIDO)):
            existentes[m.hash_registro].append(m)
    usados: set[int] = set()
    for r in res.registros:
        if r["duplicado"]:
            continue
        for m in existentes.get(r["hash"], []):
            if m.id in usados:
                continue
            saldo_m = getattr(m, "saldo", None)
            if r.get("saldo") is not None and saldo_m is not None and saldo_m != r["saldo"]:
                continue
            usados.add(m.id)
            r["duplicado"] = {"origen": "BASE", "existente_id": m.id,
                              "motivo": f"Ya existe (movimiento #{m.id}, importación #{m.importacion_id})."}
            break


def _trozos(lista, n):
    for i in range(0, len(lista), n):
        yield lista[i:i + n]


def confirmar(
    db: Session,
    cuenta: CuentaBancaria,
    nombre: str,
    contenido: bytes,
    tipo: str,
    usuario: str,
    *,
    mapeo_manual: dict[int, str] | None = None,
    anio: int | None = None,
    invertir_signo: bool = False,
    accion_duplicados: str = "marcar",
    forzar: bool = False,
) -> Importacion:
    if accion_duplicados not in ACCIONES_DUPLICADOS:
        raise ErrorImportacion("Acción de duplicados inválida.")
    h = hash_archivo(contenido)
    previa = importacion_previa(db, cuenta.id, tipo, h)
    if previa and not forzar:
        raise ConflictoImportacion(
            f"Este archivo ya fue importado (importación #{previa.id} del "
            f"{previa.creado_en:%d/%m/%Y %H:%M}).", previa.id)

    res = analizar_para_cuenta(db, cuenta, nombre, contenido, tipo, mapeo_manual=mapeo_manual,
                               anio=anio, invertir_signo=invertir_signo)
    if not res.registros:
        raise ErrorImportacion("El archivo no contiene movimientos válidos para importar.")

    imp = Importacion(
        cuenta_bancaria_id=cuenta.id, tipo=tipo, nombre_archivo=nombre[:255], formato=res.formato,
        hash_archivo=h, usuario=usuario, saldo_inicial=res.saldo_inicial, saldo_final=res.saldo_final,
        mapeo=json.dumps({"fila_encabezado": res.fila_encabezado, "metodo": res.metodo,
                          "columnas": {res.encabezados[i] if i < len(res.encabezados) else str(i): c
                                       for i, c in res.mapeo.items()}}, ensure_ascii=False),
        advertencias=json.dumps({"advertencias": res.advertencias, "errores": res.errores[:200],
                                 "descuadres_saldo": res.descuadres_saldo}, ensure_ascii=False),
    )
    db.add(imp)
    db.flush()

    Modelo = _modelo(tipo)
    ingresos = egresos = Decimal("0")
    duplicados = omitidos = 0
    fechas = []
    for r in res.registros:
        dup = r.get("duplicado")
        if dup and dup["origen"] == "BASE" and accion_duplicados == "omitir":
            omitidos += 1
            continue
        comunes = dict(
            cuenta_bancaria_id=cuenta.id, importacion_id=imp.id, fecha=r["fecha"],
            importe=r["importe"], moneda=r["moneda"], numero_operacion=r.get("numero_operacion"),
            hash_registro=r["hash"], fila_origen=r["fila"],
            posible_duplicado=bool(dup), motivo_duplicado=dup["motivo"][:255] if dup else None,
            duplicado_de_id=dup["existente_id"] if dup else None,
        )
        if tipo == "BANCO":
            mov = Modelo(**comunes, fecha_valuta=r.get("fecha_valuta"), descripcion=r["descripcion"],
                         referencia=r.get("referencia"), saldo=r.get("saldo"), categoria=r["categoria"])
        else:
            mov = Modelo(**comunes, voucher=r.get("voucher"), glosa=r["glosa"],
                         medio_pago=r.get("medio_pago"), tercero=r.get("tercero"),
                         cuenta_contable=r.get("cuenta_contable"), debe=r["debe"], haber=r["haber"])
        db.add(mov)
        duplicados += bool(dup)
        fechas.append(r["fecha"])
        if r["importe"] > 0:
            ingresos += r["importe"]
        else:
            egresos += -r["importe"]

    imp.total_registros = len(fechas)
    imp.total_duplicados = duplicados
    imp.total_omitidos = omitidos
    imp.total_ingresos = ingresos
    imp.total_egresos = egresos
    imp.fecha_desde = min(fechas) if fechas else None
    imp.fecha_hasta = max(fechas) if fechas else None
    auditoria.registrar(
        db, usuario=usuario, entidad="importacion", entidad_id=imp.id, accion="IMPORTAR",
        empresa_id=cuenta.empresa_id,
        detalle=(f"{tipo} · {nombre} · {imp.total_registros} movimientos, {duplicados} posibles "
                 f"duplicados, {omitidos} omitidos" + (" · reimportación forzada" if previa else "")),
    )
    db.commit()
    db.refresh(imp)
    return imp


def anular(db: Session, imp: Importacion, motivo: str, usuario: str) -> Importacion:
    if imp.estado == EstadoImportacion.ANULADA:
        raise ErrorImportacion("La importación ya está anulada.")
    if not motivo or len(motivo.strip()) < 5:
        raise ErrorImportacion("Indique el motivo de la anulación (mínimo 5 caracteres).")
    Modelo = _modelo(imp.tipo)
    movs = list(db.scalars(select(Modelo).where(Modelo.importacion_id == imp.id)))
    bloqueados = [m for m in movs if m.estado_conciliacion in
                  (EstadoConciliacion.CONCILIADO, EstadoConciliacion.PROPUESTO)]
    if bloqueados:
        raise ErrorImportacion(
            f"No se puede anular: {len(bloqueados)} movimiento(s) ya están conciliados o propuestos.")
    for m in movs:
        m.estado_conciliacion = EstadoConciliacion.EXCLUIDO
    imp.estado = EstadoImportacion.ANULADA
    imp.motivo_anulacion = motivo.strip()[:255]
    auditoria.registrar(db, usuario=usuario, entidad="importacion", entidad_id=imp.id,
                        accion="ANULAR", empresa_id=imp.cuenta.empresa_id,
                        detalle=f"{imp.nombre_archivo}: {motivo.strip()}")
    db.commit()
    return imp


def resolver_duplicado(db: Session, tipo: str, mov, decision: str, usuario: str, comentario: str | None):
    """decision: 'EXCLUIR' (es duplicado real) | 'MANTENER' (es un movimiento legítimo)."""
    if not mov.posible_duplicado and decision == "MANTENER":
        raise ErrorImportacion("El movimiento no está marcado como posible duplicado.")
    if mov.estado_conciliacion in (EstadoConciliacion.CONCILIADO, EstadoConciliacion.PROPUESTO):
        raise ErrorImportacion("El movimiento está conciliado o propuesto; desconcílielo primero.")
    antes = auditoria.instantanea(mov, ["posible_duplicado", "estado_conciliacion", "motivo_duplicado"])
    if decision == "EXCLUIR":
        mov.estado_conciliacion = EstadoConciliacion.EXCLUIDO
    elif decision == "MANTENER":
        mov.posible_duplicado = False
        mov.estado_conciliacion = EstadoConciliacion.PENDIENTE
        mov.motivo_duplicado = f"Revisado: no es duplicado. {comentario or ''}".strip()[:255]
    elif decision == "RESTAURAR":
        if mov.estado_conciliacion != EstadoConciliacion.EXCLUIDO or not mov.posible_duplicado:
            raise ErrorImportacion("Solo se restauran movimientos excluidos como duplicados.")
        imp = db.get(Importacion, mov.importacion_id)
        if imp and imp.estado == EstadoImportacion.ANULADA:
            raise ErrorImportacion("El movimiento pertenece a una importación anulada.")
        mov.estado_conciliacion = EstadoConciliacion.PENDIENTE
    else:
        raise ErrorImportacion("Decisión inválida.")
    auditoria.registrar(
        db, usuario=usuario, entidad=f"movimiento_{tipo.lower()}", entidad_id=mov.id,
        accion=f"DUPLICADO_{decision}", antes=antes,
        despues=auditoria.instantanea(mov, ["posible_duplicado", "estado_conciliacion", "motivo_duplicado"]),
        detalle=comentario, empresa_id=mov_empresa(db, mov))
    db.commit()
    return mov


def mov_empresa(db: Session, mov) -> int | None:
    cuenta = db.get(CuentaBancaria, mov.cuenta_bancaria_id)
    return cuenta.empresa_id if cuenta else None
