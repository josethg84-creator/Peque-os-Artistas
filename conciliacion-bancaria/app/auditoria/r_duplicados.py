"""Módulo DUPLICIDADES: motor común de detección exacta y aproximada.

1. Las líneas se agregan por (asiento, documento): varias líneas del MISMO comprobante en el mismo asiento son legítimas.
2. Coincidencia EXACTA: mismo tercero, tipo, serie y número normalizados (sin ceros a la izquierda, guiones ni espacios; el
   valor original se conserva en la evidencia) registrados en asientos distintos.
3. Coincidencia APROXIMADA: mismo tercero, moneda e importe con fechas dentro de N días y números de documento
   distintos pero equivalentes o vacíos (posible doble registro con otra numeración).
4. Pagos y cobranzas: varias aplicaciones al mismo documento solo se observan si su suma EXCEDE el importe del documento
   (los pagos parciales que no lo exceden son legítimos).
5. Operaciones recurrentes: el mismo importe del mismo tercero en meses distintos no es duplicado (fuera de la ventana).
"""
from collections import defaultdict

from sqlalchemy import select

from app.auditoria.base import CERO, Res, Salida, asiento_de, dec, doc_de, ev_calc, ev_linea, ev_reg, norm_doc
from app.importers.normalizacion import normalizar_texto
from app.models import CuentaBancaria, Importacion, MovimientoBanco

CLASES = {
    # clase: (prefijos, lado del documento, tipos de documento admitidos o None, título)
    "COMPRAS": (("42", "43", "46", "47"), "H", ("01", "03", "12", "14", "08", "1", "3"), "Factura de compra"),
    "VENTAS": (("12", "13", "16"), "D", ("01", "03", "12", "08", "1", "3"), "Factura de venta"),
    "HONORARIOS": (("42", "46"), "H", ("02", "2"), "Recibo por honorarios"),
    "NOTAS_CREDITO": (("12", "13", "42", "43", "46"), None, ("07", "7"), "Nota de crédito"),
    "PROVISIONES": (("41", "46", "48"), "H", None, "Provisión"),
    "ACTIVOS": (("32", "33", "34"), "D", None, "Adquisición de activo"),
    "DEPRECIACIONES": (("68",), "D", None, "Depreciación o amortización"),
    "RETENCIONES": (("40113", "40114", "40173", "40174"), "H", None, "Comprobante de retención o percepción"),
    "PLANILLAS": (("41",), "H", None, "Registro de planilla"),
}


def _grupo_doc(ls):
    ln = ls[0]
    return {"lineas": ls, "tercero": ln.tercero or "", "td": (ln.tipo_doc or "").lstrip("0"), "serie": ln.serie or "", "numero": ln.numero or "",
            "fecha": ln.fecha, "moneda": ln.moneda, "importe": sum((x.debe + x.haber for x in ls), CERO), "cuenta": ln.cuenta,
            "glosa": normalizar_texto(ln.glosa or ""), "asiento": asiento_de(ln), "periodo": ln.periodo, "k_asiento": (ln.lote_id, ln.periodo, ln.subdiario, ln.asiento)}


def _documentos(ax, prefijos, lado, tipos, sin_doc=False) -> list[dict]:
    """Agrega por (asiento, cuenta, documento): una sola entrada por comprobante y asiento."""
    por = defaultdict(list)
    for ln in ax.lineas:
        if not ln.cuenta.startswith(prefijos) or ln.periodo == 0:
            continue
        if lado == "D" and not ln.debe or lado == "H" and not ln.haber:
            continue
        if tipos and (ln.tipo_doc or "").lstrip("0") not in {t.lstrip("0") for t in tipos}:
            continue
        if not sin_doc and not ln.numero:
            continue
        doc = (norm_doc(ln.serie), norm_doc(ln.numero)) if ln.numero else (ln.cuenta, normalizar_texto(ln.glosa or ""), ln.tercero or "")
        por[(ln.lote_id, ln.periodo, ln.subdiario, ln.asiento, ln.cuenta[:2], doc)].append(ln)
    return [_grupo_doc(ls) for ls in por.values()]


def _res(clase, titulo, docs, condicion, tipo_coincidencia, importe, **kw) -> Res:
    ln = docs[0]["lineas"][0]
    claves = sorted(f"{d['k_asiento']}" for d in docs)
    return Res(titulo=titulo, condicion=condicion, importe=importe, cuenta=ln.cuenta, tercero=ln.tercero, razon_social=ln.razon_social,
               documento=doc_de(ln), asiento=", ".join(d["asiento"] or "?" for d in docs), linea_id=ln.id, centro_costo=ln.cc, proyecto=ln.proyecto,
               evidencia=[ev_linea(x, f"{d['asiento']}: {x.cuenta} {x.debe or x.haber} · doc original «{x.serie or ''}-{x.numero or ''}» · {x.glosa or ''}")
                          for d in docs for x in d["lineas"][:5]]
               + [ev_calc("Comparación", tipo=tipo_coincidencia, tercero=ln.tercero, documento_normalizado=f"{norm_doc(ln.serie)}-{norm_doc(ln.numero)}",
                          importes=[str(d["importe"]) for d in docs], fechas=[d["fecha"].isoformat() if d["fecha"] else None for d in docs])],
               clave=f"DUP|{clase}|{tipo_coincidencia}|{'|'.join(claves)}", exposicion=f"DOC|{ln.tercero}|{norm_doc(ln.serie)}|{norm_doc(ln.numero)}",
               detalle={"coincidencia": tipo_coincidencia, "asientos": [d["asiento"] for d in docs]}, **kw)


def _exactos_y_aproximados(ax, r, clase, docs, nombre) -> list[Res]:
    dias = int(r.p.get("dias_aproximado", 5))
    out = []
    usados = set()
    exactos = defaultdict(list)
    for d in docs:
        if d["numero"]:
            exactos[(d["tercero"], d["td"], norm_doc(d["serie"]), norm_doc(d["numero"]))].append(d)
    for k, ds in exactos.items():
        asientos = {d["k_asiento"] for d in ds}
        if len(asientos) < 2:
            continue  # varias líneas del mismo comprobante en un mismo asiento: legítimo
        iguales = len({d["importe"] for d in ds}) == 1
        exceso = sum((d["importe"] for d in ds), CERO) - max(d["importe"] for d in ds)
        out.append(_res(clase, f"{nombre} {ds[0]['serie']}-{ds[0]['numero']}: figura en {len(asientos)} asientos", ds,
                        f"El mismo comprobante (tercero {k[0] or 'sin RUC'}, documento {ds[0]['serie']}-{ds[0]['numero']}) figura en {len(asientos)} asientos "
                        f"distintos por {', '.join(str(d['importe']) for d in ds)}." + ("" if iguales else " Los importes difieren: puede tratarse de "
                                                                                       "un documento modificado; requiere revisión."),
                        "EXACTA", exceso, causa="Posible doble registro del comprobante.", probabilidad=4 if iguales else 2,
                        regularizacion="REQUIERE_AJUSTE" if iguales else "REQUIERE_DOCUMENTACION"))
        usados |= {id(d) for d in ds}
    # aproximados: mismo tercero, moneda e importe en pocos días con numeración distinta (o sin numeración)
    por_importe = defaultdict(list)
    for d in docs:
        if id(d) not in usados and d["importe"] and d["fecha"]:
            por_importe[(d["tercero"], d["moneda"], d["importe"], d["cuenta"][:2])].append(d)
    for k, ds in por_importe.items():
        if len(ds) < 2 or not k[0]:
            continue
        ds.sort(key=lambda d: d["fecha"])
        cluster = [ds[0]]
        for d in ds[1:]:
            if (d["fecha"] - cluster[-1]["fecha"]).days <= dias and d["k_asiento"] != cluster[-1]["k_asiento"]:
                cluster.append(d)
            else:
                if len(cluster) > 1:
                    out.append(_aprox(clase, nombre, cluster, dias))
                cluster = [d]
        if len(cluster) > 1:
            out.append(_aprox(clase, nombre, cluster, dias))
    return out


def _aprox(clase, nombre, ds, dias) -> Res:
    nums = sorted({f"{d['serie']}-{d['numero']}".strip("-") or "(sin número)" for d in ds})
    return _res(clase, f"Posible duplicidad ({nombre.lower()}): mismo tercero e importe en {len(ds)} registros", ds,
                f"{len(ds)} registros del tercero {ds[0]['tercero']} por {ds[0]['importe']} {ds[0]['moneda']} en {dias} días o menos con documentos "
                f"{', '.join(nums)}.", "APROXIMADA", ds[0]["importe"] * (len(ds) - 1), calidad="PARCIAL",
                causa="Coincidencia aproximada: puede ser una operación recurrente o un doble registro con numeración distinta.", probabilidad=2)


def documentos(ax, r) -> Salida:
    clase = r.p.get("clase", "COMPRAS")
    pref, lado, tipos, nombre = CLASES[clase]
    pref = tuple(r.cuentas) or pref
    docs = _documentos(ax, pref, lado, tipos, sin_doc=clase in ("PROVISIONES", "DEPRECIACIONES", "PLANILLAS"))
    if clase in ("PROVISIONES", "DEPRECIACIONES", "PLANILLAS"):
        out = _mismo_periodo(clase, nombre, docs)
    else:
        out = _exactos_y_aproximados(ax, r, clase, docs, nombre)
    if clase == "ACTIVOS":
        out += _activos_registro(ax)
    return Salida(out, len(docs), sum((d["importe"] for d in docs), CERO),
                  f"{nombre}: agregación por asiento y documento; coincidencia exacta por tercero, tipo, serie y número normalizados; "
                  f"aproximada por tercero, moneda e importe dentro de {r.p.get('dias_aproximado', 5)} días.")


def _mismo_periodo(clase, nombre, docs) -> list[Res]:
    """Provisiones, depreciaciones y planillas: mismo tercero/activo, cuenta, importe y glosa en el mismo periodo y asientos distintos."""
    g = defaultdict(list)
    for d in docs:
        ln = d["lineas"][0]
        g[(d["periodo"], d["cuenta"], d["tercero"], ln.maquinaria or "", d["importe"], d["glosa"])].append(d)
    out = []
    for k, ds in g.items():
        if len({d["k_asiento"] for d in ds}) > 1 and k[4]:
            out.append(_res(clase, f"{nombre} duplicada en la cuenta {k[1]} (periodo {k[0]:02d})", ds,
                            f"{len(ds)} registros con la misma cuenta, tercero/activo, importe {k[4]} y glosa «{ds[0]['lineas'][0].glosa or ''}» en el "
                            f"mismo periodo, en asientos distintos.", "EXACTA", k[4] * (len(ds) - 1),
                            causa="Posible doble registro de la provisión o del cálculo periódico.", probabilidad=4, regularizacion="REQUIERE_AJUSTE"))
    return out


def _activos_registro(ax) -> list[Res]:
    g = defaultdict(list)
    for a in ax.registros("ACTIVO_FIJO"):
        g[(normalizar_texto(a.get("descripcion") or ""), str(a.get("costo_inicial")), str(a.get("fecha_adquisicion")))].append(a)
    out = []
    for k, xs in g.items():
        if len(xs) > 1 and k[0]:
            out.append(Res(titulo=f"Activo posiblemente duplicado en el registro: {xs[0].get('descripcion')}",
                           condicion=f"Códigos {', '.join(str(x['_clave']) for x in xs)} con la misma descripción, costo {k[1]} y fecha {k[2]}.",
                           importe=dec(k[1]) * (len(xs) - 1), cuenta=xs[0].get("_cuenta"), documento=str(xs[0]["_clave"]),
                           evidencia=[ev_reg("annex_support_records", x["_id"], f"Activo {x['_clave']}", **{c: x.get(c) for c in ("descripcion", "costo_inicial", "fecha_adquisicion")})
                                      for x in xs], clave=f"DUPACT|{'|'.join(sorted(str(x['_clave']) for x in xs))}",
                           exposicion=f"ACTIVO|{'|'.join(sorted(str(x['_clave']) for x in xs))}", calidad="PARCIAL", probabilidad=3))
    return out


def aplicaciones(ax, r) -> Salida:
    """Pagos (42/43/46 al debe contra caja y bancos) o cobranzas (12/13/16 al haber): exceso sobre el documento."""
    tipo = r.p.get("clase", "PAGOS")
    pref, lado_doc = (("42", "43", "44", "46", "47"), "H") if tipo == "PAGOS" else (("12", "13", "14", "16"), "D")
    origen = defaultdict(lambda: CERO)
    aplic = defaultdict(list)
    n = 0
    for k, ls in ax.asientos.items():
        caja = any(x.cuenta.startswith("10") for x in ls)
        for x in ls:
            if not x.cuenta.startswith(pref) or not x.numero:
                continue
            kd = (x.tercero or "", norm_doc(x.serie), norm_doc(x.numero))
            es_origen = (x.haber if lado_doc == "H" else x.debe) > 0
            if es_origen:
                origen[kd] += x.haber if lado_doc == "H" else x.debe
            elif caja:
                n += 1
                aplic[kd].append((k, x))
    for x in ax.ctx3.lineas_hasta_corte:  # documentos de ejercicios anteriores pagados en este
        if x.periodo == 0 and x.cuenta.startswith(pref) and x.numero:
            kd = (x.tercero or "", norm_doc(x.serie), norm_doc(x.numero))
            origen[kd] += abs(x.haber - x.debe)
    out = []
    for kd, aps in aplic.items():
        total = sum(((x.debe if lado_doc == "H" else x.haber) for _, x in aps), CERO)
        doc = origen.get(kd, CERO)
        if len({k for k, _ in aps}) > 1 and doc and total > doc:
            x0 = aps[0][1]
            docs = [_grupo_doc([x]) for _, x in aps]
            out.append(_res(tipo, f"{'Pago' if tipo == 'PAGOS' else 'Cobranza'} duplicado potencial del documento {doc_de(x0)}", docs,
                            f"{len(aps)} {'pagos' if tipo == 'PAGOS' else 'cobranzas'} por {total} aplicados a un documento de {doc} "
                            f"(exceso {total - doc}). Los pagos parciales que no exceden el documento no se observan.", "EXACTA", total - doc,
                            causa="Posible pago duplicado o aplicación a un documento equivocado.", probabilidad=4, regularizacion="REQUIERE_CONCILIACION"))
            out[-1].evidencia.append(ev_calc("Saldo del documento", importe_documento=doc, aplicado=total, exceso=total - doc))
    return Salida(out, n, metodo="Suma de pagos/cobranzas (con movimiento de caja o bancos) por documento frente a su importe original; "
                                 "solo se observa el exceso.")


def transferencias(ax, r) -> Salida:
    dias = int(r.p.get("dias", 3))
    out = []
    movs = ax.db.scalars(select(MovimientoBanco).join(CuentaBancaria, CuentaBancaria.id == MovimientoBanco.cuenta_bancaria_id)
                         .join(Importacion, Importacion.id == MovimientoBanco.importacion_id)
                         .where(CuentaBancaria.empresa_id == ax.empresa_id, Importacion.estado == "ACTIVA", MovimientoBanco.fecha <= ax.corte,
                                MovimientoBanco.posible_duplicado.is_(True), MovimientoBanco.estado_conciliacion != "EXCLUIDO")).all()
    for m in movs:
        out.append(Res(titulo=f"Movimiento bancario posiblemente duplicado ({m.numero_operacion or m.descripcion})",
                       condicion=f"El estado de cuenta contiene el movimiento del {m.fecha:%d/%m/%Y} por {m.importe} marcado como posible duplicado en la "
                                 f"importación (fase 1): {m.motivo_duplicado or ''}.", importe=abs(m.importe), documento=m.numero_operacion,
                       evidencia=[ev_reg("movimientos_banco", m.id, m.descripcion or "", fecha=m.fecha, importe=m.importe)],
                       clave=f"DUPMB|{m.id}", exposicion=f"MB|{m.id}", calidad="PARCIAL"))
    # libro: misma operación bancaria (número) e importe en asientos distintos
    g = defaultdict(list)
    for ln in ax.lineas:
        if ln.cuenta.startswith("10") and ln.numero and not ln.serie:
            g[(ln.cuenta, norm_doc(ln.numero), ln.debe - ln.haber)].append(ln)
    for k, ls in g.items():
        asientos = {(x.lote_id, x.periodo, x.subdiario, x.asiento) for x in ls}
        if len(asientos) > 1 and k[2]:
            docs = [_grupo_doc([x]) for x in ls]
            if max(d["fecha"] for d in docs) and (max(d["fecha"] for d in docs) - min(d["fecha"] for d in docs)).days <= max(dias, 31):
                out.append(_res("TRANSFERENCIAS", f"Transferencia {ls[0].numero} registrada {len(asientos)} veces en libros", docs,
                                f"La operación {ls[0].numero} de la cuenta {k[0]} por {abs(k[2])} figura en {len(asientos)} asientos.", "EXACTA",
                                abs(k[2]) * (len(asientos) - 1), probabilidad=4, regularizacion="REQUIERE_CONCILIACION"))
    return Salida(out, sum(len(v) for v in g.values()), metodo="Número de operación bancaria e importe repetidos en libros; duplicados marcados en la "
                                                               "importación de estados de cuenta (fase 1).")


def asientos(ax, r) -> Salida:
    firmas = defaultdict(list)
    for k, ls in ax.asientos.items():
        f = frozenset((x.cuenta, x.debe, x.haber, x.tercero or "", norm_doc(x.numero)) for x in ls)
        if sum((x.debe for x in ls), CERO) >= dec(r.p.get("importe_minimo", "0")):
            firmas[f].append(k)
    out = []
    for f, ks in firmas.items():
        if len(ks) > 1:
            ls = ax.asientos[ks[0]]
            fechas = sorted(ax.asientos[k][0].fecha for k in ks if ax.asientos[k][0].fecha)
            if fechas and (fechas[-1] - fechas[0]).days > int(r.p.get("dias", 31)):
                continue  # mismos importes en meses distintos: operación recurrente
            et = ["-".join(p for p in (k[2], k[3]) if p) for k in ks]
            tot = sum((x.debe for x in ls), CERO)
            out.append(Res(titulo=f"Asientos idénticos: {', '.join(et)}", condicion=f"{len(ks)} asientos con las mismas cuentas, terceros, documentos e "
                           f"importes ({tot}).", importe=tot * (len(ks) - 1), cuenta=ls[0].cuenta, asiento=", ".join(et), linea_id=ls[0].id,
                           evidencia=[ev_linea(x) for k in ks for x in ax.asientos[k][:6]], clave=f"DUPASI|{'|'.join(sorted(map(str, ks)))}",
                           exposicion=f"ASIENTO_DUP|{'|'.join(sorted(map(str, ks)))}", probabilidad=4, regularizacion="REQUIERE_AJUSTE"))
    return Salida(out, len(ax.asientos), metodo="Firma completa del asiento (cuenta, debe, haber, tercero, documento) repetida dentro de 31 días.")


def detracciones(ax, r) -> Salida:
    g = defaultdict(list)
    for ln in ax.lineas:
        if ln.constancia:
            g[norm_doc(ln.constancia)].append(ln)
    out = []
    for c, ls in g.items():
        asientos = {(x.lote_id, x.periodo, x.subdiario, x.asiento) for x in ls}
        if len(asientos) > 1:
            docs = [_grupo_doc([x]) for x in ls]
            out.append(_res("DETRACCIONES", f"Constancia de detracción {ls[0].constancia} registrada {len(asientos)} veces", docs,
                            f"La constancia {ls[0].constancia} figura en {len(asientos)} asientos.", "EXACTA",
                            max(x.debe + x.haber for x in ls) * (len(asientos) - 1), probabilidad=4))
            out[-1].documento = ls[0].constancia
    return Salida(out, sum(len(v) for v in g.values()), metodo="Número de constancia de detracción repetido en asientos distintos.")


def distribuciones(ax, r) -> Salida:
    od = ax.ctx3.destino or {}
    out = []
    for a in od.get("asientos", []):
        if a["estado"] == "LINEA_DESTINO_REPETIDA":
            out.append(Res(titulo=f"Línea de destino repetida en el asiento {a['asiento']}", condicion=f"El asiento {a['asiento']} repite una línea de "
                           f"destino (clase 9): origen {a['origen']}, destino {a['destino']}.", importe=dec(a["destino"]) - dec(a["origen"]),
                           asiento=a["asiento"], linea_id=a["linea_id"], evidencia=[ev_calc("Origen y destino del asiento (fase 3)", **a)],
                           clave=f"DUPDIST|{a['asiento']}|{a['periodo']}", exposicion=f"DESTINO|{a['asiento']}|{a['periodo']}", probabilidad=4))
    return Salida(out, len(od.get("asientos", [])), metodo="Análisis de origen y destino de la fase 3 (líneas de destino repetidas por asiento).")


EVALUADORES = {"dup_documentos": documentos, "dup_aplicaciones": aplicaciones, "dup_transferencias": transferencias, "dup_asientos": asientos,
               "dup_detracciones": detracciones, "dup_distribuciones": distribuciones}
