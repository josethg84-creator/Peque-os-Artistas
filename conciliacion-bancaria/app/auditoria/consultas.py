"""Consultas de lectura del auditor (tablero, explorador, detalle) e importación de configuraciones del ERP."""
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select

from app.auditoria import catalogo
from app.auditoria.informes import _h, _mask
from app.auditoria.servicio import ErrorAuditoria, evento, exigir, puede, rol
from app.contable import archivos
from app.importers.normalizacion import normalizar_texto
from app.models import (AsignacionAuditoria, CategoriaRegla, ConfiguracionImportada, EjecucionAuditoria, EncargoAuditoria, EvidenciaHallazgo,
                        GrupoHallazgos, HallazgoAuditoria, ItemMuestra, PlanAccion, ReglaAuditoria, ResultadoRegla,
                        RevisionAuditoria, VersionRegla)

CERO = Decimal(0)


def fila(o, excluir=()) -> dict:
    out = {}
    for c in o.__table__.columns:
        if c.key in excluir:
            continue
        v = getattr(o, c.key)
        out[c.key] = str(v) if isinstance(v, Decimal) else v.isoformat() if hasattr(v, "isoformat") else v
    return out


def paginar(db, q, pagina, por_pagina):
    por_pagina = max(1, min(int(por_pagina or 50), 1000))
    pagina = max(1, int(pagina or 1))
    total = db.scalar(select(func.count()).select_from(q.order_by(None).subquery()))
    return total, q.limit(por_pagina).offset((pagina - 1) * por_pagina), pagina, por_pagina


def encargos_visibles(db, empresa_id, usuario):
    q = select(EncargoAuditoria).where(EncargoAuditoria.empresa_id == empresa_id)
    if rol(db, empresa_id, usuario) == "AUDITOR_EXTERNO":
        ids = select(AsignacionAuditoria.engagement_id).where(AsignacionAuditoria.empresa_id == empresa_id, AsignacionAuditoria.tipo == "AUDITOR_EXTERNO",
                                                               AsignacionAuditoria.usuario == usuario, AsignacionAuditoria.activa.is_(True),
                                                               or_(AsignacionAuditoria.vigente_hasta.is_(None), AsignacionAuditoria.vigente_hasta >= date.today()))
        q = q.where(EncargoAuditoria.id.in_(ids))
    return q


def encargo_dict(db, e) -> dict:
    from app.auditoria.motor import alcance_de, resumen_encargo
    d = fila(e)
    d["alcance"] = alcance_de(db, e)
    d["resumen"] = resumen_encargo(db, e.id)
    d["ejecuciones"] = [{**fila(r, ("reglas_snapshot", "materialidad_snapshot", "tiempos")), "resumen": json.loads(r.resumen) if r.resumen else None}
                        for r in db.scalars(select(EjecucionAuditoria).where(EjecucionAuditoria.engagement_id == e.id).order_by(EjecucionAuditoria.id.desc()).limit(20))]
    return d


def resultados_run(db, run_id) -> list[dict]:
    return [fila(r) for r in db.scalars(select(ResultadoRegla).where(ResultadoRegla.run_id == run_id).order_by(ResultadoRegla.modulo, ResultadoRegla.codigo))]


def hallazgos(db, empresa_id, usuario, f: dict) -> dict:
    ve = puede(db, empresa_id, usuario, "datos_personales")
    q = select(HallazgoAuditoria).where(HallazgoAuditoria.empresa_id == empresa_id,
                                        HallazgoAuditoria.engagement_id.in_(encargos_visibles(db, empresa_id, usuario).with_only_columns(EncargoAuditoria.id)))
    for k in ("engagement_id", "modulo", "riesgo", "estado", "tipo", "regla_codigo", "responsable", "grupo_id", "regularizacion"):
        if f.get(k) not in (None, ""):
            vals = str(f[k]).split(",")
            q = q.where(getattr(HallazgoAuditoria, k).in_([int(v) if k in ("engagement_id", "grupo_id") else v for v in vals]))
    if f.get("cuenta"):
        q = q.where(HallazgoAuditoria.cuenta.like(f"{f['cuenta']}%"))
    if f.get("tercero"):
        q = q.where(HallazgoAuditoria.tercero == f["tercero"])
    if f.get("centro_costo"):
        q = q.where(HallazgoAuditoria.centro_costo == f["centro_costo"])
    if f.get("solo_vigentes"):
        q = q.where(HallazgoAuditoria.vigente.is_(True))
    if f.get("bandeja"):
        q = q.where(HallazgoAuditoria.en_bandeja_regularizacion.is_(True))
    if f.get("vencidos"):
        q = q.where(HallazgoAuditoria.fecha_limite < date.today(), HallazgoAuditoria.estado.notin_(("CERRADO", "VERIFICADO")))
    if f.get("buscar"):
        b = f"%{f['buscar']}%"
        q = q.where(or_(HallazgoAuditoria.codigo.ilike(b), HallazgoAuditoria.titulo.ilike(b), HallazgoAuditoria.documento.ilike(b),
                        HallazgoAuditoria.asiento.ilike(b)))
    orden = {"importe": func.abs(HallazgoAuditoria.importe).desc(), "puntuacion": HallazgoAuditoria.puntuacion.desc(),
             "fecha": HallazgoAuditoria.fecha_deteccion.desc()}.get(f.get("orden"), HallazgoAuditoria.puntuacion.desc())
    total, qp, pagina, pp = paginar(db, q.order_by(orden, HallazgoAuditoria.id), f.get("pagina"), f.get("por_pagina"))
    return {"total": total, "pagina": pagina, "por_pagina": pp, "items": [_mask(_h(h), ve) for h in db.scalars(qp)]}


def hallazgo_detalle(db, empresa_id, usuario, h) -> dict:
    ve = puede(db, empresa_id, usuario, "datos_personales")
    conf = puede(db, empresa_id, usuario, "confidencial")
    d = _mask(_h(h), ve)
    d.update(lock_version=h.lock_version, engagement_id=h.engagement_id, run_id=h.run_id, ultima_run_id=h.ultima_run_id, clave_exposicion=h.clave_exposicion,
             riesgo_calculado=h.riesgo_calculado, riesgo_ajustado_por=h.riesgo_ajustado_por, justificacion_riesgo=h.justificacion_riesgo,
             sobre_materialidad=h.sobre_materialidad, claramente_insignificante=h.claramente_insignificante, estructural=h.estructural,
             en_bandeja_regularizacion=h.en_bandeja_regularizacion, detalle=json.loads(h.detalle or "{}"), anterior_id=h.anterior_id,
             centro_costo=h.centro_costo, proyecto=h.proyecto)
    evs = []
    for e in db.scalars(select(EvidenciaHallazgo).where(EvidenciaHallazgo.finding_id == h.id).order_by(EvidenciaHallazgo.id)):
        x = fila(e, ("ruta",))
        x["datos"] = json.loads(e.datos) if e.datos else None
        if e.confidencial and not (conf if not h.personal else ve):
            x.update(descripcion="(evidencia confidencial: acceso restringido)", datos=None, nombre_archivo=None)
        evs.append(x)
    d["evidencias"] = evs
    d["historial"] = [fila(r) for r in db.scalars(select(RevisionAuditoria).where(RevisionAuditoria.entidad == "HALLAZGO", RevisionAuditoria.entidad_id == h.id)
                                                  .order_by(RevisionAuditoria.id))]
    d["planes"] = [fila(p) for p in db.scalars(select(PlanAccion).where(PlanAccion.finding_id == h.id).order_by(PlanAccion.id))]
    g = db.get(GrupoHallazgos, h.grupo_id) if h.grupo_id else None
    d["grupo"] = {**fila(g), "miembros": [x.codigo for x in db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.grupo_id == g.id))]} if g else None
    return d


def tablero(db, empresa_id, usuario, engagement_id=None, ejercicio=None) -> dict:
    encs = encargos_visibles(db, empresa_id, usuario)
    if engagement_id:
        encs = encs.where(EncargoAuditoria.id == engagement_id)
    if ejercicio:
        encs = encs.where(EncargoAuditoria.ejercicio == ejercicio)
    ids = [e.id for e in db.scalars(encs)]
    hs = db.scalars(select(HallazgoAuditoria).where(HallazgoAuditoria.engagement_id.in_(ids or [0]))).all()
    vig = [h for h in hs if h.vigente and h.tipo != "FALSO_POSITIVO"]
    grupos = db.scalars(select(GrupoHallazgos).where(GrupoHallazgos.engagement_id.in_(ids or [0]))).all()
    runs = db.scalars(select(EjecucionAuditoria).where(EjecucionAuditoria.engagement_id.in_(ids or [0]), EjecucionAuditoria.estado_proceso == "COMPLETADO")).all()
    ultimos = {}
    for r in runs:
        ultimos[r.engagement_id] = r
    rr = db.scalars(select(ResultadoRegla).where(ResultadoRegla.run_id.in_([r.id for r in ultimos.values()] or [0]))).all()
    cuentas, movs = 0, 0
    for r in ultimos.values():
        ej = (json.loads(r.resumen or "{}").get("ejecucion") or {})
        cuentas += ej.get("cuentas_auditadas") or 0
        movs += ej.get("movimientos_evaluados") or 0
    hoy = date.today()
    revisados = sum(1 for h in hs if h.estado not in ("DETECTADO", "PENDIENTE_REVISION", "REABIERTO"))
    planes = db.scalars(select(PlanAccion).where(PlanAccion.finding_id.in_([h.id for h in hs] or [0]))).all()
    mensual = defaultdict(int)
    for h in hs:
        mensual[str(h.periodo)] += 1
    por_resp = defaultdict(lambda: {"asignados": 0, "cerrados": 0, "vencidos": 0})
    for h in vig:
        x = por_resp[h.responsable or "(sin asignar)"]
        x["asignados"] += 1
        x["cerrados"] += h.estado in ("CERRADO", "VERIFICADO")
        x["vencidos"] += bool(h.fecha_limite and h.fecha_limite < hoy and h.estado not in ("CERRADO", "VERIFICADO"))
    por_cuenta = Counter((h.cuenta or "(sin cuenta)")[:4] for h in vig)
    expo_mod = defaultdict(lambda: CERO)
    vistos = set()
    for h in sorted(vig, key=lambda x: -abs(x.importe)):
        if h.grupo_id not in vistos:
            expo_mod[h.modulo] += abs(h.importe)
            vistos.add(h.grupo_id)
    return {"kpi": {"cuentas_auditadas": cuentas, "movimientos_evaluados": movs, "reglas_ejecutadas": sum(1 for r in rr if r.estado in ("CON_EXCEPCIONES", "SIN_EXCEPCIONES", "REUTILIZADA")),
                    "reglas_no_ejecutadas": sum(1 for r in rr if r.estado not in ("CON_EXCEPCIONES", "SIN_EXCEPCIONES", "REUTILIZADA")),
                    "hallazgos": len(vig), "confirmados": sum(1 for h in hs if h.tipo == "CONFIRMADO"), "criticos": sum(1 for h in vig if h.riesgo == "CRITICO"),
                    "altos": sum(1 for h in vig if h.riesgo == "ALTO"), "pendientes": sum(1 for h in vig if h.estado not in ("CERRADO", "VERIFICADO", "SUBSANADO")),
                    "subsanados": sum(1 for h in hs if h.estado in ("SUBSANADO", "VERIFICADO") or h.tipo == "SUBSANADO"),
                    "falsos_positivos": sum(1 for h in hs if h.tipo == "FALSO_POSITIVO"),
                    "exposicion_potencial": str(sum((g.exposicion for g in grupos), CERO)), "exposicion_confirmada": str(sum((g.exposicion_confirmada for g in grupos), CERO)),
                    "exposicion_bruta": str(sum((abs(h.importe) for h in vig), CERO)),
                    "acciones_vencidas": sum(1 for p in planes if p.fecha_compromiso < hoy and p.estado not in ("COMPLETADO", "CANCELADO")),
                    "avance_revision": round(100 * revisados / len(hs), 1) if hs else None},
            "nota": "Exposición potencial y confirmada sin duplicar hallazgos superpuestos (grupos de exposición); la «bruta» suma todos los hallazgos.",
            "por_modulo": dict(Counter(h.modulo for h in vig)), "por_riesgo": dict(Counter(h.riesgo for h in vig)), "por_cuenta": dict(por_cuenta.most_common(12)),
            "por_centro_costo": dict(Counter(h.centro_costo or "(sin CC)" for h in vig).most_common(12)), "mensual": dict(sorted(mensual.items())),
            "recurrentes": [_h(h) for h in sorted(vig, key=lambda x: -x.reincidencias)[:10] if h.reincidencias],
            "exposicion_por_modulo": {k: str(v) for k, v in expo_mod.items()}, "por_responsable": dict(por_resp),
            "matriz": dict(Counter(f"{h.impacto}x{h.probabilidad}" for h in vig))}


def reglas(db, empresa_id, f: dict) -> list[dict]:
    catalogo.sembrar(db)
    cats = {c.id: c.codigo for c in db.scalars(select(CategoriaRegla))}
    todas = {}
    for r in db.scalars(select(ReglaAuditoria).where((ReglaAuditoria.empresa_id.is_(None)) | (ReglaAuditoria.empresa_id == empresa_id))
                        .order_by(ReglaAuditoria.empresa_id.is_not(None), ReglaAuditoria.codigo)):
        x = fila(r)
        x["modulo"] = cats[r.categoria_id]
        x["parametros"] = json.loads(r.parametros or "{}")
        x["definicion"] = json.loads(r.definicion) if r.definicion else None
        x["personalizada"] = r.empresa_id is not None
        todas[r.codigo] = x
    out = list(todas.values())
    if f.get("modulo"):
        out = [x for x in out if x["modulo"] == f["modulo"]]
    if f.get("buscar"):
        b = normalizar_texto(f["buscar"])
        out = [x for x in out if b in normalizar_texto(f"{x['codigo']} {x['nombre']}")]
    return out


def versiones_regla(db, rule_id) -> list[dict]:
    return [fila(v) for v in db.scalars(select(VersionRegla).where(VersionRegla.rule_id == rule_id).order_by(VersionRegla.version))]


def muestra_dict(db, m) -> dict:
    d = fila(m)
    d["criterios"] = json.loads(m.criterios)
    d["items"] = [fila(i) for i in db.scalars(select(ItemMuestra).where(ItemMuestra.sample_id == m.id).order_by(ItemMuestra.id))]
    return d


def papel_dict(p) -> dict:
    d = fila(p)
    d["contenido"] = json.loads(p.contenido)
    return d





# ------------------------------------------------------------------ importación de configuraciones del ERP (formatos homologados)
SINONIMOS = {"cuenta": ("CUENTA", "CODIGO", "COD CUENTA", "CUENTA CONTABLE", "GL ACCOUNT", "SAKNR", "NRO CUENTA"),
             "descripcion": ("DESCRIPCION", "NOMBRE", "DENOMINACION", "TXT50", "DESCRIPCION CUENTA"),
             "naturaleza": ("NATURALEZA", "TIPO SALDO", "D A", "DEUDORA ACREEDORA"),
             "admite_movimiento": ("ADMITE MOVIMIENTO", "MOVIMIENTO", "IMPUTABLE", "NIVEL DE REGISTRO"),
             "cuenta_destino_debe": ("CUENTA DESTINO", "DESTINO DEBE", "CTA DESTINO", "AMARRE DEBE"),
             "cuenta_destino_haber": ("DESTINO HABER", "AMARRE HABER", "CUENTA TRANSFERENCIA"),
             "rubro": ("RUBRO", "AGRUPACION", "RUBRO FINANCIERO", "PARTIDA", "LINEA REPORTE"),
             "estado_financiero": ("ESTADO FINANCIERO", "ESTADO", "REPORTE", "TIPO REPORTE"),
             "clase_rubro": ("CLASE RUBRO", "CLASE", "CATEGORIA"),
             "cuenta_origen": ("CUENTA ORIGEN", "ORIGEN"), "centro_costo": ("CENTRO COSTO", "CENTRO DE COSTO", "CC", "KOSTL"),
             "porcentaje": ("PORCENTAJE", "%", "PCT")}
SISTEMAS = ("SAP", "PROFICONT", "STARSOFT", "CONCAR", "OTRO")


def importar_configuracion(db, empresa_id, usuario, tipo, sistema, nombre, contenido: bytes, sustento=None, vigente_desde=None) -> ConfiguracionImportada:
    r = exigir(db, empresa_id, usuario, "reglas")
    if sistema not in SISTEMAS:
        raise ErrorAuditoria(f"Sistema no válido: {', '.join(SISTEMAS)}.")
    fmt = archivos.detectar_formato(nombre, contenido)
    filas = archivos.leer_filas(contenido, fmt)
    if not filas:
        raise ErrorAuditoria("El archivo no tiene filas.")
    hojas = filas if isinstance(filas, dict) else None
    filas = next(iter(hojas.values())) if hojas else filas
    enc = [normalizar_texto(str(x or "")) for x in filas[0]]
    idx = {}
    for campo, sins in SINONIMOS.items():
        for i, h in enumerate(enc):
            if h in sins or h == normalizar_texto(campo):
                idx.setdefault(campo, i)
    if "cuenta" not in idx and "cuenta_origen" not in idx:
        raise ErrorAuditoria("No se identificó la columna de cuenta en el archivo.")
    items = []
    for f in filas[1:]:
        if not any(f):
            continue
        x = {k: (str(f[i]).strip() if i < len(f) and f[i] not in (None, "") else None) for k, i in idx.items()}
        for k in ("cuenta", "cuenta_origen", "cuenta_destino_debe", "cuenta_destino_haber"):
            if x.get(k):
                x[k] = x[k].split(".")[0] if x[k].replace(".", "").isdigit() else x[k]
        if x.get("admite_movimiento") is not None:
            x["admite_movimiento"] = normalizar_texto(x["admite_movimiento"]) in ("S", "SI", "1", "TRUE", "X", "VERDADERO")
        if x.get("naturaleza"):
            x["naturaleza"] = {"DEUDORA": "D", "ACREEDORA": "A"}.get(normalizar_texto(x["naturaleza"]), normalizar_texto(x["naturaleza"])[:1])
        items.append(x)
    v = (db.scalar(select(func.max(ConfiguracionImportada.version)).where(ConfiguracionImportada.empresa_id == empresa_id,
                                                                            ConfiguracionImportada.tipo == tipo)) or 0) + 1
    c = ConfiguracionImportada(empresa_id=empresa_id, tipo=tipo, sistema=sistema, version=v, vigente_desde=vigente_desde, items=json.dumps(items, ensure_ascii=False),
                               registros=len(items), nombre_archivo=nombre[:255], hash_archivo=hashlib.sha256(contenido).hexdigest(), sustento=sustento,
                               usuario=usuario)
    db.add(c)
    db.flush()
    evento(db, empresa_id, usuario, "IMPORTAR_CONFIGURACION", "configuracion", c.id, {"tipo": tipo, "sistema": sistema, "version": v, "registros": len(items)}, r)
    db.commit()
    return c
