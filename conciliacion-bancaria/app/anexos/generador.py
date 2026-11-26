"""Generación de anexos: cálculo, conciliación, versiones y generación masiva.

- Saldo final contable = saldo inicial + debe − haber (con el signo natural de la cuenta).
- El detalle se compara con el saldo contable: la DIFERENCIA se muestra tal cual (nunca se ajusta).
- Igualdad matemática ≠ sustento documental: un anexo cuadrado puede estar «parcialmente sustentado».
- Cada generación crea una versión solo si el contenido cambió (idempotente). Las versiones aprobadas
  son inmutables: un anexo aprobado o cerrado no se regenera sin una reapertura autorizada.
"""
import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from app.anexos import catalogo, constructores, expresiones
from app.anexos.datos import CERO, C2, Ctx, Filtros, crear as crear_ctx, dec, fin_de_periodo
from app.models import (AdjuntoAnexo, Anexo, Aplicacion, AprobacionAnexo, AuditoriaAnexo, ConciliacionAnexo,
                        ConfiguracionAnexos, DetalleAnexo, GeneracionAnexos, HallazgoAnexo, PartidaAbierta, PlantillaAnexo,
                        RegistroAuxiliar, RevisionAnexo, VersionAnexo)

COLUMNAS_FIJAS = ("clave", "cuenta", "categoria", "fecha", "fecha_vencimiento", "tipo_documento", "serie", "numero", "tercero",
                  "razon_social", "glosa", "moneda", "tipo_cambio", "importe_original", "importe_aplicado", "saldo_me", "saldo",
                  "dias", "tramo", "centro_costo", "proyecto", "referencia", "linea_id", "item_id", "estado_sustento", "observacion")
PARAMETROS_DEFECTO = {"separacion_funciones": True, "tolerancia": "0.00",
                      "aprobacion_automatica": {"activa": False, "autorizada_por": None, "resultados": ["CUADRADO"]}}
SEVERIDAD_ORDEN = {"ALTA": 0, "MEDIA": 1, "BAJA": 2, "INFORMATIVA": 3}


class Conflicto(Exception):
    status = 409


class Cancelado(Exception):
    pass


def _j(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def auditar(db: Session, empresa_id: int, usuario: str, accion: str, entidad: str, entidad_id=None, detalle=None, rol=None):
    db.add(AuditoriaAnexo(empresa_id=empresa_id, usuario=usuario or "sistema", rol=rol, accion=accion, entidad=entidad,
                          entidad_id=entidad_id, detalle=None if detalle is None else json.dumps(detalle, default=_j, ensure_ascii=False)))


def configuracion(db: Session, empresa_id: int) -> dict:
    c = db.scalar(select(ConfiguracionAnexos).where(ConfiguracionAnexos.empresa_id == empresa_id))
    p = json.loads(json.dumps(PARAMETROS_DEFECTO))
    if c:
        guardado = json.loads(c.parametros or "{}")
        p.update({k: v for k, v in guardado.items() if k != "aprobacion_automatica"})
        p["aprobacion_automatica"].update(guardado.get("aprobacion_automatica", {}))
    return p


# ------------------------------------------------------------------ cálculo de un anexo
def calcular(ctx: Ctx, cuenta: str, plantilla: dict, tolerancia: Decimal = CERO) -> dict:
    esp = plantilla["especialidad"]
    res = constructores.Resultado()
    constructores.CONSTRUCTORES.get(esp, constructores.generico)(ctx, cuenta, plantilla, res)
    nat = ctx.naturaleza(cuenta)
    sg = 1 if nat == "D" else -1
    s = ctx.saldos_de(cuenta)
    saldo_contable = dec(s["sf"] * sg)
    filas = sorted(res.filas, key=lambda r: (r["cuenta"] or "", r["razon_social"] or r["tercero"] or "", str(r["fecha"] or ""), r["clave"] or ""))
    vistos = Counter()
    for r in filas:  # claves únicas dentro de la versión
        vistos[r["clave"]] += 1
        if vistos[r["clave"]] > 1:
            r["clave"] = f"{r['clave']}#{vistos[r['clave']]}"
    por_estado = defaultdict(lambda: CERO)
    for r in filas:
        por_estado[r["estado_sustento"]] += r["saldo"]
    detalle = sum(por_estado.values(), CERO).quantize(C2)
    diferencia = (saldo_contable - detalle).quantize(C2)
    imp = ctx.saldo_balance_importado(cuenta)
    saldo_bal = dec(imp * sg) if imp is not None else None
    hall = list(res.hallazgos)

    def h(codigo, sev, titulo, detalle_=None, importe=None):
        hall.append({"codigo": codigo, "severidad": sev, "titulo": titulo, "detalle": detalle_, "importe": importe, "clave_fila": None})
    if abs(diferencia) > tolerancia:
        h("DIFERENCIA_CONCILIACION", "ALTA", f"El detalle no explica el saldo contable: diferencia {diferencia}",
          "La diferencia se muestra sin ajustes; revise movimientos sin detalle, cronogramas o registros auxiliares.", diferencia)
    if por_estado["SIN_DETALLE"]:
        h("SALDO_SIN_DETALLE", "MEDIA", f"Saldo sin detalle documental: {por_estado['SIN_DETALLE'].quantize(C2)}",
          "Corresponde a saldos iniciales consolidados: solicite la desagregación por documento.", por_estado["SIN_DETALLE"].quantize(C2))
    if por_estado["POR_CLASIFICAR"]:
        h("PARTIDAS_POR_CLASIFICAR", "MEDIA", f"Partidas pendientes de clasificación: {por_estado['POR_CLASIFICAR'].quantize(C2)}",
          None, por_estado["POR_CLASIFICAR"].quantize(C2))
    sin_doc_bruto = sum((abs(r["saldo"]) for r in filas if r["estado_sustento"] == "SIN_DOCUMENTO"), CERO).quantize(C2)
    if sin_doc_bruto:
        h("PENDIENTE_SUSTENTO", "BAJA", f"Partidas sin sustento documental por {sin_doc_bruto} (valor absoluto; neto {por_estado['SIN_DOCUMENTO'].quantize(C2)})",
          "El saldo está identificado pero no tiene comprobante o documento adjunto.", sin_doc_bruto)
    if saldo_contable < 0 and esp not in ("ORIGEN_DESTINO",):
        h("SALDO_CONTRARIO", "MEDIA", f"Saldo contrario a la naturaleza de la cuenta ({'deudora' if nat == 'D' else 'acreedora'}): {saldo_contable}",
          None, saldo_contable)
    if saldo_bal is not None and saldo_bal != saldo_contable:
        h("BALANCE_IMPORTADO_DIFIERE", "ALTA", f"El balance de comprobación importado muestra {saldo_bal} y el libro {saldo_contable}",
          "Revise la integridad de la importación del diario o del balance.", (saldo_bal - saldo_contable).quantize(C2))
    if ctx.f.apertura == "NINGUNA":
        h("SALDOS_PRELIMINARES", "INFORMATIVA", "No hay saldos iniciales importados: el saldo inicial es preliminar.")
    if ctx.filtros.activos():
        h("ANEXO_FILTRADO", "INFORMATIVA", "Anexo filtrado por " + ", ".join(f"{k}: {v}" for k, v in ctx.filtros.como_dict().items()) +
          ": los saldos iniciales importados no se incluyen.")
    # reglas propias de la plantilla (motor seguro de expresiones)
    for regla in plantilla.get("reglas", []):
        try:
            if regla["tipo"] == "CONDICION_FILA" and regla.get("expresion"):
                arbol = expresiones.compilar(regla["expresion"])
                n = 0
                for r in filas:
                    if expresiones.evaluar(arbol, {**r, **r["datos"]}):
                        n += 1
                        if n <= 50:
                            hall.append({"codigo": regla["codigo"], "severidad": regla["severidad"], "titulo": f"{regla['descripcion']}: "
                                         f"{r.get('documento') or r.get('razon_social') or r['clave']}", "detalle": None,
                                         "importe": r["saldo"], "clave_fila": r["clave"]})
            elif regla["tipo"] == "UMBRAL_DIFERENCIA":
                lim = Decimal(str(regla["parametros"].get("umbral", 0)))
                if abs(diferencia) > lim:
                    h(regla["codigo"], regla["severidad"], f"{regla['descripcion']} (diferencia {diferencia} > {lim})", None, diferencia)
            elif regla["tipo"] == "SALDO_ANTIGUO":
                dias = int(regla["parametros"].get("dias", 365))
                viejas = [r for r in filas if r["dias"] and r["dias"] > dias and r["saldo"]]
                if viejas:
                    h(regla["codigo"], regla["severidad"], f"{regla['descripcion']}: {len(viejas)} partidas con más de {dias} días",
                      None, sum((r["saldo"] for r in viejas), CERO))
        except expresiones.ErrorExpresion as exc:
            h("REGLA_INVALIDA", "INFORMATIVA", f"La regla {regla['codigo']} no se pudo evaluar: {exc}")
    sustentado = por_estado["DOCUMENTADO"].quantize(C2)
    # importe bruto sin sustento: las partidas a favor no compensan la falta de sustento de otras
    bruto = sum((abs(r["saldo"]) for r in filas if r["estado_sustento"] != "DOCUMENTADO"), CERO).quantize(C2)
    insuficiente = not filas and saldo_contable != 0 or (not s["n"] and not s["si"] and not ctx.lineas)
    resumen = {
        "cuenta": cuenta, "descripcion": ctx.descripcion(cuenta), "naturaleza": nat, "especialidad": esp,
        "saldo_inicial": str(dec(s["si"] * sg)), "debe": str(dec(s["debe"])), "haber": str(dec(s["haber"])),
        "saldo_final_contable": str(saldo_contable), "saldo_me": str(dec(s["sf_me"] * sg)) if s["sf_me"] else None,
        "saldo_detalle": str(detalle), "saldo_sustentado": str(sustentado),
        "sin_documento": str(por_estado["SIN_DOCUMENTO"].quantize(C2)), "sin_detalle": str(por_estado["SIN_DETALLE"].quantize(C2)),
        "por_clasificar": str(por_estado["POR_CLASIFICAR"].quantize(C2)),
        "saldo_pendiente_sustento": str((detalle - sustentado).quantize(C2)), "pendiente_sustento_bruto": str(bruto),
        "diferencia": str(diferencia),
        "saldo_balance_importado": str(saldo_bal) if saldo_bal is not None else None,
        "diferencia_balance_importado": str((saldo_bal - saldo_contable).quantize(C2)) if saldo_bal is not None else None,
        "movimientos": s["n"], "filas": len(filas), "apertura": ctx.f.apertura, "advertencias": ctx.advertencias,
        "filtros": ctx.filtros.como_dict(), "formula": "Saldo final = saldo inicial + debe − haber (signo natural de la cuenta)",
        "extras": res.extras, "insuficiente": bool(insuficiente),
    }
    return {"resumen": resumen, "filas": filas, "hallazgos": hall}


def clasificar(resumen: dict, abiertas: int, tolerancia: Decimal = CERO) -> tuple[str, str]:
    dif = Decimal(resumen["diferencia"])
    pendiente = Decimal(resumen.get("pendiente_sustento_bruto") or resumen["saldo_pendiente_sustento"])
    if resumen.get("insuficiente"):
        return "INFORMACION_INSUFICIENTE", "No hay información contable suficiente para construir el anexo."
    if abs(dif) > tolerancia:
        return "DESCUADRADO", f"El detalle no explica el saldo contable (diferencia {dif})."
    if pendiente:
        return "PARCIALMENTE_SUSTENTADO", (f"El saldo cuadra, pero partidas por {pendiente} (valor absoluto) no tienen sustento "
                                           "documental completo (sin documento, sin detalle o por clasificar).")
    if abiertas:
        return "CUADRADO_CON_OBSERVACIONES", f"El saldo cuadra y está sustentado, con {abiertas} observaciones abiertas."
    return "CUADRADO", "El detalle explica el saldo y todas las partidas tienen sustento identificado."


# ------------------------------------------------------------------ persistencia
def clave_anexo(cuenta: str, corte: date, plantilla_id: int, filtros: dict) -> str:
    return hashlib.sha256(json.dumps([cuenta, corte.isoformat(), plantilla_id, filtros], sort_keys=True).encode()).hexdigest()[:40]


def _hash_contenido(calc: dict, snap: dict) -> str:
    r = calc["resumen"]
    base = {k: r[k] for k in ("saldo_inicial", "debe", "haber", "saldo_final_contable", "saldo_detalle", "saldo_sustentado",
                               "diferencia", "saldo_balance_importado")}
    filas = [[_j(f.get(c)) for c in COLUMNAS_FIJAS] + [json.dumps(f["datos"], default=_j, sort_keys=True)] for f in calc["filas"]]
    hall = sorted((x["codigo"], x["titulo"], _j(x["importe"])) for x in calc["hallazgos"])
    return hashlib.sha256(json.dumps([base, filas, hall, snap.get("id"), snap.get("version")], default=_j).encode()).hexdigest()


def _huella(h: dict) -> str:
    """Identidad estable de una observación entre versiones (no depende de los importes del título)."""
    return hashlib.sha256(f"{h['codigo']}|{h.get('clave_fila') or ''}".encode()).hexdigest()[:40]


def sincronizar_hallazgos(db: Session, anexo: Anexo, version_id: int, hallazgos: list[dict], numero: int) -> list[dict]:
    existentes = {x.huella: x for x in db.scalars(select(HallazgoAnexo).where(HallazgoAnexo.anexo_id == anexo.id,
                                                                              HallazgoAnexo.origen == "SISTEMA"))}
    vistos, out = set(), []
    for h in hallazgos:
        hu = _huella(h)
        if hu in vistos:
            continue
        vistos.add(hu)
        x = existentes.get(hu)
        if x is None:
            x = HallazgoAnexo(empresa_id=anexo.empresa_id, anexo_id=anexo.id, origen="SISTEMA", huella=hu, codigo=h["codigo"])
            db.add(x)
        elif x.estado == "SUBSANADO" and x.resuelto_por and x.resuelto_por.startswith("sistema"):
            x.estado, x.resuelto_por, x.resuelto_en = "ABIERTO", None, None  # reaparece
        x.version_id, x.severidad, x.titulo, x.detalle = version_id, h["severidad"], h["titulo"], h.get("detalle")
        x.importe = h.get("importe")
        x.clave_fila = h.get("clave_fila")
        out.append({"huella": hu, "codigo": h["codigo"], "titulo": h["titulo"], "severidad": h["severidad"]})
    for hu, x in existentes.items():
        if hu not in vistos and x.estado == "ABIERTO":
            x.estado, x.resuelto_por, x.resuelto_en = "SUBSANADO", f"sistema (no se reproduce en la versión {numero})", datetime.now()
    db.flush()
    return out


def abiertas(db: Session, anexo_id: int) -> int:
    return db.scalar(select(func.count()).select_from(HallazgoAnexo).where(
        HallazgoAnexo.anexo_id == anexo_id, HallazgoAnexo.estado == "ABIERTO", HallazgoAnexo.severidad != "INFORMATIVA")) or 0


def guardar(db: Session, ctx: Ctx, cuenta: str, plantilla: PlantillaAnexo, usuario: str, *, run_id=None, motivo=None,
            snap: dict | None = None, politica: dict | None = None) -> tuple[Anexo, str]:
    """Calcula y guarda una nueva versión si el contenido cambió. Devuelve (anexo, estado)."""
    snap = snap or catalogo.snapshot(db, plantilla)
    politica = politica or configuracion(db, ctx.empresa_id)
    tol = Decimal(str(politica.get("tolerancia") or "0"))
    calc = calcular(ctx, cuenta, snap, tol)
    filtros = ctx.filtros.como_dict()
    clave = clave_anexo(cuenta, ctx.corte, plantilla.id, filtros)
    a = db.scalar(select(Anexo).where(Anexo.empresa_id == ctx.empresa_id, Anexo.clave == clave))
    h = _hash_contenido(calc, snap)
    if a is None:
        a = Anexo(empresa_id=ctx.empresa_id, clave=clave, cuenta=cuenta, descripcion=calc["resumen"]["descripcion"], elemento=cuenta[:1] or "0",
                  ejercicio=ctx.ejercicio, periodo=ctx.periodo, fecha_corte=ctx.corte, filtros=json.dumps(filtros) if filtros else None,
                  plantilla_id=plantilla.id, especialidad=plantilla.especialidad, estado_revision="PENDIENTE_GENERACION",
                  moneda=filtros.get("moneda") or "PEN", naturaleza=calc["resumen"]["naturaleza"])
        db.add(a)
        db.flush()
    actual = db.get(VersionAnexo, a.version_id) if a.version_id else None
    if a.estado_revision in ("APROBADO", "CERRADO"):
        return a, ("PROTEGIDO" if actual and actual.hash_contenido == h else "PROTEGIDO_CON_CAMBIOS")
    if actual and actual.hash_contenido == h:
        return a, "SIN_CAMBIOS"
    numero = (a.version_actual or 0) + 1
    v = VersionAnexo(anexo_id=a.id, empresa_id=a.empresa_id, numero=numero, run_id=run_id, motivo=motivo,
                     version_datos=ctx.version_datos, version_compensacion=ctx.version_compensacion,
                     plantilla_snapshot=json.dumps(snap, default=_j), reglas_snapshot=json.dumps(snap.get("reglas", []), default=_j),
                     resumen="{}", hash_contenido=h, filas=len(calc["filas"]), generado_por=usuario)
    db.add(v)
    db.flush()
    filas_db = []
    for i, f in enumerate(calc["filas"]):
        d = {c: f.get(c) for c in COLUMNAS_FIJAS}
        d.update(version_id=v.id, anexo_id=a.id, orden=i, cuenta=f["cuenta"] or cuenta, clave=str(f["clave"])[:160],
                 datos=json.dumps(f["datos"], default=_j, ensure_ascii=False) if f["datos"] else None)
        for k in ("categoria",):
            d[k] = (d[k] or None) and str(d[k])[:80]
        for k, n in (("glosa", 255), ("razon_social", 255), ("observacion", 500), ("referencia", 80), ("tramo", 60)):
            d[k] = (d[k] or None) and str(d[k])[:n]
        filas_db.append(d)
    for i in range(0, len(filas_db), 2000):
        db.execute(insert(DetalleAnexo), filas_db[i:i + 2000])
    hall = sincronizar_hallazgos(db, a, v.id, calc["hallazgos"], numero)
    n_abiertas = abiertas(db, a.id)
    resultado, explicacion = clasificar(calc["resumen"], n_abiertas, tol)
    r = calc["resumen"]
    r.update(resultado=resultado, explicacion=explicacion, hallazgos=hall)
    v.resumen = json.dumps(r, default=_j, ensure_ascii=False)
    db.add(ConciliacionAnexo(anexo_id=a.id, version_id=v.id, saldo_inicial=Decimal(r["saldo_inicial"]), debe=Decimal(r["debe"]),
                             haber=Decimal(r["haber"]), saldo_contable=Decimal(r["saldo_final_contable"]),
                             saldo_balance_importado=Decimal(r["saldo_balance_importado"]) if r["saldo_balance_importado"] else None,
                             diferencia_balance_importado=Decimal(r["diferencia_balance_importado"]) if r["diferencia_balance_importado"] else None,
                             saldo_detalle=Decimal(r["saldo_detalle"]), sustentado=Decimal(r["saldo_sustentado"]),
                             sin_documento=Decimal(r["sin_documento"]), sin_detalle=Decimal(r["sin_detalle"]),
                             por_clasificar=Decimal(r["por_clasificar"]), diferencia=Decimal(r["diferencia"]), resultado=resultado,
                             cuadra=Decimal(r["diferencia"]) == 0, explicacion=explicacion))
    previo = a.estado_revision
    a.version_actual, a.version_id, a.resultado = numero, v.id, resultado
    a.descripcion = r["descripcion"]
    a.saldo_inicial, a.debe, a.haber = Decimal(r["saldo_inicial"]), Decimal(r["debe"]), Decimal(r["haber"])
    a.saldo_contable, a.saldo_detalle = Decimal(r["saldo_final_contable"]), Decimal(r["saldo_detalle"])
    a.saldo_sustentado, a.saldo_pendiente_sustento = Decimal(r["saldo_sustentado"]), Decimal(r["saldo_pendiente_sustento"])
    a.diferencia, a.observaciones_abiertas = Decimal(r["diferencia"]), n_abiertas
    a.elaborado_por = a.elaborado_por or usuario
    a.lock_version = (a.lock_version or 0) + 1
    if previo == "PENDIENTE_GENERACION":
        a.estado_revision = "GENERADO"
    elif previo == "REABIERTO":
        a.estado_revision = "EN_ELABORACION"
    db.add(RevisionAnexo(anexo_id=a.id, version_id=v.id, de_estado=previo, a_estado=a.estado_revision, usuario=usuario,
                         comentario=motivo or f"Se generó la versión {numero}",
                         cambios=json.dumps({"version": numero, "resultado": resultado, "diferencia": r["diferencia"]})))
    aa = politica.get("aprobacion_automatica") or {}
    if aa.get("activa") and aa.get("autorizada_por") and resultado in (aa.get("resultados") or ["CUADRADO"]) and not n_abiertas \
            and a.estado_revision in ("GENERADO", "EN_ELABORACION"):
        a.estado_revision, a.aprobado_por, a.aprobado_en = "APROBADO", f"política ({aa['autorizada_por']})", datetime.now()
        v.inmutable, v.estado_al_cerrar = True, "APROBADO"
        db.add(AprobacionAnexo(anexo_id=a.id, version_id=v.id, accion="APROBAR_POLITICA", usuario="sistema",
                               comentario=f"Aprobación automática autorizada por {aa['autorizada_por']}"))
        db.add(RevisionAnexo(anexo_id=a.id, version_id=v.id, de_estado="GENERADO", a_estado="APROBADO", usuario="sistema",
                             comentario="Aprobado por política autorizada (cuadrado y sin observaciones)"))
    return a, "NUEVA_VERSION"


# ------------------------------------------------------------------ selección de cuentas y generación masiva
def seleccionar(ctx: Ctx, alcance: dict) -> list[str]:
    modo = alcance.get("modo", "BALANCE")
    if modo == "CUENTAS":
        return sorted({c.strip() for c in alcance.get("cuentas", []) if c and c.strip()})
    hojas = []
    for c in ctx.hojas():
        s = ctx.saldos_de(c)
        if s["sf"] or s["n"] or s["si"]:
            hojas.append(c)
    if modo == "ELEMENTO":
        el = str(alcance.get("elemento", ""))
        hojas = [c for c in hojas if c.startswith(el)]
    elif modo == "RANGO":
        d, h = str(alcance.get("desde", "")), str(alcance.get("hasta", "")) + "￿"
        hojas = [c for c in hojas if d <= c <= h]
    dig = alcance.get("digitos")
    if dig:
        hojas = sorted({c[:int(dig)] if len(c) > int(dig) else c for c in hojas})
    return hojas


def version_compensacion(db: Session, empresa_id: int) -> str:
    x = db.execute(select(func.count(Aplicacion.id), func.max(Aplicacion.id), func.max(Aplicacion.reversion_id))
                   .where(Aplicacion.empresa_id == empresa_id, Aplicacion.estado == "APROBADA")).one()
    p = db.execute(select(func.count(PartidaAbierta.id), func.max(PartidaAbierta.version)).where(PartidaAbierta.empresa_id == empresa_id)).one()
    return hashlib.sha256(repr((x, p)).encode()).hexdigest()[:24]


def clave_run(db: Session, empresa_id: int, ejercicio, periodo, corte, alcance, version_datos) -> str:
    plantillas = db.execute(select(func.count(PlantillaAnexo.id), func.max(PlantillaAnexo.actualizado_en), func.max(PlantillaAnexo.version))
                            .where((PlantillaAnexo.empresa_id == empresa_id) | PlantillaAnexo.empresa_id.is_(None))).one()
    soporte = db.execute(select(func.count(RegistroAuxiliar.id), func.max(RegistroAuxiliar.id)).where(RegistroAuxiliar.empresa_id == empresa_id)).one()
    adj = db.execute(select(func.count(AdjuntoAnexo.id), func.max(AdjuntoAnexo.id)).where(AdjuntoAnexo.empresa_id == empresa_id)).one()
    cfg = configuracion(db, empresa_id)
    reab = db.scalar(select(func.max(AprobacionAnexo.id)).join(Anexo, Anexo.id == AprobacionAnexo.anexo_id).where(Anexo.empresa_id == empresa_id))
    base = [empresa_id, ejercicio, periodo, corte.isoformat(), alcance, version_datos, version_compensacion(db, empresa_id),
            repr(plantillas), repr(soporte), repr(adj), cfg, reab]
    return hashlib.sha256(json.dumps(base, sort_keys=True, default=str).encode()).hexdigest()


def crear_run(db: Session, empresa_id: int, ejercicio: int, periodo: int, corte: date | None, alcance: dict, usuario: str,
              forzar=False) -> tuple[GeneracionAnexos, bool]:
    corte = corte or fin_de_periodo(ejercicio, periodo)
    en_curso = db.scalar(select(GeneracionAnexos).where(GeneracionAnexos.empresa_id == empresa_id,
                                                         GeneracionAnexos.estado.in_(("EN_COLA", "PROCESANDO"))))
    if en_curso and en_curso.creado_en and en_curso.creado_en > datetime.now() - timedelta(hours=2):
        raise Conflicto(f"Ya hay una generación en curso (#{en_curso.id}). Espere a que termine o cancélela.")
    from app.analisis import saldos
    catalogo.sembrar(db)
    vd = saldos.version_datos(db, empresa_id)
    clave = clave_run(db, empresa_id, ejercicio, periodo, corte, alcance, vd)
    if not forzar:
        previo = db.scalar(select(GeneracionAnexos).where(GeneracionAnexos.empresa_id == empresa_id, GeneracionAnexos.clave_idempotencia == clave,
                                                         GeneracionAnexos.estado == "COMPLETADO").order_by(GeneracionAnexos.id.desc()))
        if previo:
            return previo, False
    run = GeneracionAnexos(empresa_id=empresa_id, ejercicio=ejercicio, periodo=periodo, fecha_corte=corte,
                           alcance=json.dumps(alcance, ensure_ascii=False), clave_idempotencia=clave, version_datos=vd, usuario=usuario)
    db.add(run)
    db.flush()
    auditar(db, empresa_id, usuario, "GENERAR_ANEXOS", "run", run.id, {"alcance": alcance, "corte": corte, "forzar": forzar})
    db.commit()
    return run, True


def ejecutar_run(db: Session, run_id: int, avance=lambda p, e: None) -> dict:
    run = db.get(GeneracionAnexos, run_id)
    t0 = time.perf_counter()
    tiempos = {}
    marca = [time.perf_counter(), "Inicio"]

    def etapa(nombre, pct):
        """Registra la duración de la etapa que termina y anuncia la siguiente."""
        ahora = time.perf_counter()
        tiempos[marca[1]] = int((ahora - marca[0]) * 1000)
        marca[0], marca[1] = ahora, nombre
        run.etapa, run.progreso = nombre, pct
        avance(pct, nombre)
    run.estado = "PROCESANDO"
    db.commit()
    try:
        alcance = json.loads(run.alcance)
        catalogo.sembrar(db)
        fl = Filtros(**{k: alcance.get("filtros", {}).get(k) for k in ("centro_costo", "proyecto", "unidad_negocio", "moneda")})
        etapa("Carga del libro, saldos y fuentes", 3)
        ctx = crear_ctx(db, run.empresa_id, run.ejercicio, run.periodo, run.fecha_corte, fl)
        cuentas = seleccionar(ctx, alcance)
        run.total_cuentas = len(cuentas)
        etapa("Composición de partidas (fase 4) al corte", 6)
        from app.compensacion import partidas as partidas4
        prefijos4 = list(partidas4.configuracion(db, run.empresa_id, run.fecha_corte).cuentas)
        if any(c.startswith(tuple(prefijos4)) or any(p.startswith(c) for p in prefijos4) for c in cuentas) or \
                any(c.startswith("19") for c in cuentas):
            ctx.composicion("")  # partidas y compensaciones aprobadas de la fase 4 (una sola vez)
        etapa(f"Generación y conciliación de {len(cuentas)} anexos", 8)
        politica = configuracion(db, run.empresa_id)
        plantillas_cache: dict = {}
        snaps: dict = {}
        plantilla_fija = alcance.get("plantilla_id")
        conteo = Counter()
        resultados = Counter()
        protegidos_cambios, errores = [], []
        for i, c in enumerate(cuentas):
            if i % 25 == 0:
                db.commit()
                db.refresh(run)
                if run.cancelar:
                    raise Cancelado()
                avance(8 + int(88 * i / max(len(cuentas), 1)), f"Generando anexos ({i}/{len(cuentas)})")
            try:
                p = plantillas_cache.get(c) or catalogo.para_cuenta(db, run.empresa_id, c, plantilla_fija)
                plantillas_cache[c] = p
                if p.id not in snaps:
                    snaps[p.id] = catalogo.snapshot(db, p)
                with db.begin_nested():
                    a, estado = guardar(db, ctx, c, p, run.usuario, run_id=run.id, snap=snaps[p.id], politica=politica,
                                        motivo=alcance.get("motivo"))
                conteo[estado] += 1
                resultados[a.resultado or "—"] += 1
                if estado == "PROTEGIDO_CON_CAMBIOS":
                    protegidos_cambios.append({"cuenta": c, "anexo_id": a.id})
            except (ValueError, expresiones.ErrorExpresion) as exc:
                errores.append({"cuenta": c, "error": str(exc)})
        db.commit()
        etapa("Completado", 98)
        resumen = {"cuentas": len(cuentas), "nuevas_versiones": conteo["NUEVA_VERSION"], "sin_cambios": conteo["SIN_CAMBIOS"],
                   "protegidos": conteo["PROTEGIDO"] + conteo["PROTEGIDO_CON_CAMBIOS"],
                   "protegidos_con_cambios": protegidos_cambios[:200], "por_resultado": dict(resultados), "errores": errores[:200],
                   "lineas_leidas": len(ctx.lineas), "advertencias": ctx.advertencias}
        run.estado, run.progreso, run.etapa = "COMPLETADO", 100, "Completado"
        run.resumen = json.dumps(resumen, default=_j, ensure_ascii=False)
    except Cancelado:
        db.rollback()
        run = db.get(GeneracionAnexos, run_id)
        run.estado, run.etapa = "CANCELADO", "Cancelado por el usuario (las versiones ya guardadas se conservan)"
        resumen = {"cancelado": True}
    except Exception as exc:
        db.rollback()
        run = db.get(GeneracionAnexos, run_id)
        run.estado, run.error = "ERROR", str(exc)[:2000]
        db.commit()
        raise
    run.tiempos = json.dumps(tiempos)
    run.duracion_ms = int((time.perf_counter() - t0) * 1000)
    run.finalizado_en = datetime.now()
    db.commit()
    return {"run_id": run.id, "estado": run.estado, "resumen": resumen}


def run_dict(r: GeneracionAnexos) -> dict:
    return {"id": r.id, "ejercicio": r.ejercicio, "periodo": r.periodo, "fecha_corte": r.fecha_corte.isoformat(),
            "alcance": json.loads(r.alcance), "estado": r.estado, "progreso": r.progreso, "etapa": r.etapa,
            "total_cuentas": r.total_cuentas, "resumen": json.loads(r.resumen) if r.resumen else None,
            "tiempos": json.loads(r.tiempos) if r.tiempos else None, "error": r.error, "duracion_ms": r.duracion_ms,
            "usuario": r.usuario, "creado_en": _j(r.creado_en), "finalizado_en": _j(r.finalizado_en)}


def marcar_cancelacion(db: Session, run: GeneracionAnexos):
    db.execute(update(GeneracionAnexos).where(GeneracionAnexos.id == run.id).values(cancelar=True))
    db.commit()
