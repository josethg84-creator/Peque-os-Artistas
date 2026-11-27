"""Diseñador de conciliaciones personalizadas (asistente de 10 pasos): fuentes → homologación → campos de cruce →
campos monetarios → tolerancias → reglas → agrupación → prueba → revisión → guardado.

La definición es declarativa (JSON validado): no admite SQL ni código. Las condiciones de exclusión usan el
evaluador seguro de expresiones de la fase 5. Una plantilla personalizada requiere la autorización de un
supervisor o administrador (separación de funciones) antes de usarse en conciliaciones."""
import json
import re

from sqlalchemy import select

from app.anexos import expresiones
from app.conciliacion import catalogo, fuentes
from app.conciliacion.servicio import ErrorConciliacion, auditar, exigir
from app.models import PlantillaConciliacion, TipoConciliacion

IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,39}$")
TIPOS_REGLA = ("CLAVE", "IMPORTE_FECHA", "COMBINACION", "AGREGADO", "EXCLUSION", "CLASIFICACION")
CLASES_GRUPO = ("EXACTA", "TOLERANCIA", "PARCIAL", "DIFERENCIA", "AGREGADO")
LIMITES = {"max_elementos": (2, 8), "max_candidatos": (2, 60), "max_nodos": (100, 200000), "dias": (0, 366), "fecha_dias": (0, 366)}
PASOS = ["Fuentes", "Homologación", "Campos de cruce", "Campos monetarios", "Tolerancias", "Reglas", "Agrupación", "Prueba", "Revisión", "Guardado"]


def _campo(c, donde):
    if not isinstance(c, str) or not IDENT.match(c):
        raise ErrorConciliacion(f"{donde}: «{c}» no es un nombre de campo válido.")
    return c


def validar(cfg: dict) -> dict:
    """Valida y normaliza la definición. Devuelve la configuración lista para guardar (sin `reglas`) y las reglas."""
    if not isinstance(cfg, dict):
        raise ErrorConciliacion("Definición no válida.")
    fs = cfg.get("fuentes") or {}
    if len(fs) < 2 or len(fs) > 4 or any(k not in "ABCD" for k in fs):
        raise ErrorConciliacion("Defina entre dos y cuatro fuentes (A, B, C, D).")
    out_f = {}
    for lado, f in fs.items():
        if f.get("tipo") not in fuentes.TIPOS_FUENTE:
            raise ErrorConciliacion(f"Fuente {lado}: tipo no admitido ({f.get('tipo')}).")
        if f.get("rol", "EXTERNA") not in ("CONTABLE", "EXTERNA", "AUXILIAR_INTERNO"):
            raise ErrorConciliacion(f"Fuente {lado}: rol no válido.")
        par = f.get("parametros") or {}
        if not isinstance(par, dict) or any(not IDENT.match(k) for k in par):
            raise ErrorConciliacion(f"Fuente {lado}: parámetros no válidos.")
        for k in ("cuentas", "cuentas_documento", "cuentas_igv"):
            if k in par and (not isinstance(par[k], list) or any(not re.match(r"^\d{1,12}$", str(x)) for x in par[k])):
                raise ErrorConciliacion(f"Fuente {lado}: las cuentas deben ser códigos numéricos.")
        if f["tipo"] == "ARCHIVO":
            from app.contable.campos import tipo_def
            try:
                tipo_def(f.get("esquema") or "CONC_GENERICO")
            except KeyError:
                raise ErrorConciliacion(f"Fuente {lado}: esquema de homologación desconocido.")
        out_f[lado] = {"tipo": f["tipo"], "rol": f.get("rol", "EXTERNA"), "nombre": (f.get("nombre") or f["tipo"])[:120],
                       "esquema": f.get("esquema") or ("CONC_GENERICO" if f["tipo"] == "ARCHIVO" else None), "parametros": par}
    pas = cfg.get("pasadas") or [{"a": sorted(fs)[0], "b": sorted(fs)[1], "modo": "PARTIDAS", "signo": "IGUAL"}]
    for p in pas:
        if p.get("a") not in fs or p.get("b") not in fs or p["a"] == p["b"]:
            raise ErrorConciliacion("Cada comparación une dos fuentes distintas definidas.")
        if p.get("modo", "PARTIDAS") not in ("PARTIDAS", "AGREGADO") or p.get("signo", "IGUAL") not in ("IGUAL", "OPUESTO"):
            raise ErrorConciliacion("Modo o signo de comparación no válido.")
        if p.get("agrupar_por"):
            [_campo(c, "Agrupación") for c in p["agrupar_por"]]
    tol = cfg.get("tolerancia") or {}
    try:
        ta = float(tol.get("importe_absoluto") or 0)
        tp = None if tol.get("porcentaje") in (None, "") else float(tol["porcentaje"])
        td = int(tol.get("dias") or 0)
    except (TypeError, ValueError):
        raise ErrorConciliacion("Tolerancias no válidas.")
    if ta < 0 or (tp is not None and not 0 <= tp <= 100) or not 0 <= td <= 366:
        raise ErrorConciliacion("Las tolerancias deben ser positivas (porcentaje entre 0 y 100; días hasta 366).")
    reglas = []
    for i, r in enumerate(cfg.get("reglas") or []):
        if r.get("tipo") not in TIPOS_REGLA:
            raise ErrorConciliacion(f"Regla {i + 1}: tipo no admitido.")
        par = dict(r.get("parametros") or {})
        for k in ("campos", "claves", "campos_extra"):
            if k in par:
                par[k] = [_campo(c, f"Regla {i + 1}") for c in par[k]]
        for k, (lo, hi) in LIMITES.items():
            if k in par and par[k] is not None and not lo <= int(par[k]) <= hi:
                raise ErrorConciliacion(f"Regla {i + 1}: {k} debe estar entre {lo} y {hi} (límite combinatorio).")
        for t in par.get("comparar", []):
            if len(t) != 4:
                raise ErrorConciliacion(f"Regla {i + 1}: cada comparación monetaria indica campo A, campo B, nombre y subtipo.")
            _campo(t[0], "Campo monetario")
            _campo(t[1], "Campo monetario")
        if r["tipo"] in ("EXCLUSION", "CLASIFICACION"):
            try:
                expresiones.compilar(par.get("expresion") or "")
            except expresiones.ErrorExpresion as exc:
                raise ErrorConciliacion(f"Regla {i + 1}: expresión no válida ({exc}).")
        if r["tipo"] == "CLAVE" and not par.get("campos"):
            raise ErrorConciliacion(f"Regla {i + 1}: indique los campos de cruce.")
        if r["tipo"] == "AGREGADO" and not par.get("claves"):
            raise ErrorConciliacion(f"Regla {i + 1}: indique las claves de agrupación.")
        pasada = int(r.get("pasada") or 0)
        if pasada >= len(pas):
            raise ErrorConciliacion(f"Regla {i + 1}: la comparación {pasada} no existe.")
        reglas.append({"codigo": re.sub(r"[^A-Z0-9_]", "_", (r.get("codigo") or f"R{i + 1}").upper())[:40],
                       "descripcion": (r.get("descripcion") or r.get("codigo") or f"Regla {i + 1}")[:255], "tipo": r["tipo"], "pasada": pasada,
                       "parametros": par, "activa": bool(r.get("activa", True))})
    if not any(r["tipo"] in ("CLAVE", "IMPORTE_FECHA", "COMBINACION", "AGREGADO") for r in reglas):
        raise ErrorConciliacion("Defina al menos una regla de coincidencia.")
    auto = [x for x in (cfg.get("confirmar_automaticamente") or ["EXACTA"]) if x in CLASES_GRUPO]
    dup = {}
    for lado, claves in (cfg.get("duplicados") or {}).items():
        if lado in fs:
            dup[lado] = [[_campo(c, "Duplicados") for c in k] for k in claves]
    crit = cfg.get("criterios_aprobacion") or {}
    limpio = {"fuentes": out_f, "pasadas": [{"a": p["a"], "b": p["b"], "modo": p.get("modo", "PARTIDAS"), "signo": p.get("signo", "IGUAL"),
                                             **({"agrupar_por": p["agrupar_por"]} if p.get("agrupar_por") else {})} for p in pas],
              "duplicados": dup, "tolerancia": {"importe_absoluto": str(ta), "porcentaje": tp, "dias": td},
              "confirmar_automaticamente": auto,
              "criterios_aprobacion": {"sin_ambiguas": True, "sin_criticas_abiertas": bool(crit.get("sin_criticas_abiertas", True))}}
    for k in ("conceptos", "campos_obligatorios", "identificadores_unicos", "prioridades"):
        if k in cfg:
            limpio[k] = cfg[k]
    return {"configuracion": limpio, "reglas": reglas}


def guardar(db, empresa_id, usuario, datos: dict, plantilla_id=None) -> PlantillaConciliacion:
    r = exigir(db, empresa_id, usuario, "plantillas")
    catalogo.sembrar(db)
    tipo = datos.get("tipo_codigo") or "PERSONALIZADA"
    if not db.scalar(select(TipoConciliacion).where(TipoConciliacion.codigo == tipo)):
        raise ErrorConciliacion("Tipo de conciliación no válido.")
    v = validar(datos["configuracion"])
    if plantilla_id:
        p = db.get(PlantillaConciliacion, plantilla_id)
        if not p or p.empresa_id != empresa_id:
            raise LookupError("Plantilla no encontrada")
        p.version += 1
    else:
        codigo = re.sub(r"[^A-Z0-9_]", "_", (datos.get("codigo") or datos["nombre"]).upper())[:40]
        if db.scalar(select(PlantillaConciliacion).where(PlantillaConciliacion.empresa_id == empresa_id, PlantillaConciliacion.codigo == codigo)):
            raise ErrorConciliacion("Ya existe una plantilla con ese código.")
        p = PlantillaConciliacion(empresa_id=empresa_id, codigo=codigo, creado_por=usuario, personalizada=True)
        db.add(p)
    p.tipo_codigo, p.nombre, p.descripcion = tipo, datos["nombre"][:160], datos.get("descripcion")
    p.configuracion = json.dumps(v["configuracion"], ensure_ascii=False)
    p.autorizada, p.autorizada_por = False, None  # cada cambio requiere nueva autorización
    db.flush()
    catalogo.guardar_reglas(db, p, v["reglas"])
    auditar(db, empresa_id, usuario, "GUARDAR_PLANTILLA", "plantilla", p.id, {"version": p.version, "configuracion": v["configuracion"],
                                                                               "reglas": v["reglas"]}, r)
    db.commit()
    return p


def autorizar(db, empresa_id, usuario, plantilla_id) -> PlantillaConciliacion:
    r = exigir(db, empresa_id, usuario, "configurar")
    p = db.get(PlantillaConciliacion, plantilla_id)
    if not p or p.empresa_id != empresa_id:
        raise LookupError("Plantilla no encontrada")
    if p.creado_por.lower() == usuario.lower():
        raise ErrorConciliacion("Separación de funciones: quien diseña la plantilla no puede autorizarla.")
    p.autorizada, p.autorizada_por = True, usuario
    auditar(db, empresa_id, usuario, "AUTORIZAR_PLANTILLA", "plantilla", p.id, {"version": p.version}, r)
    db.commit()
    return p


def probar(db, empresa_id, usuario, run_id, definicion: dict) -> dict:
    """Paso 8: ejecuta la definición en memoria sobre las fuentes ya cargadas de una conciliación. No guarda nada."""
    from collections import Counter

    from app.conciliacion import servicio
    from app.conciliacion.motor import Comparador
    exigir(db, empresa_id, usuario, "plantillas")
    c = servicio.cargar(db, empresa_id, run_id)
    v = validar(definicion)
    cfg = {**v["configuracion"], "reglas": v["reglas"]}
    por, _ = servicio._registros_vigentes(db, c)
    faltan = [lado for lado in cfg["fuentes"] if lado not in por]
    if faltan:
        raise ErrorConciliacion(f"La conciliación de prueba no tiene registros para las fuentes {', '.join(faltan)}.")
    tol = servicio.tolerancia(db, empresa_id, c.tipo_codigo, json.loads(c.ambito or "{}"), cfg)
    comp = Comparador(por, cfg, tol, set(cfg["confirmar_automaticamente"]), set())
    comp.ejecutar(cfg["pasadas"], cfg["reglas"], [])
    grupos = Counter()
    pend = Counter()
    for p in comp.pasadas:
        for g in p.grupos:
            grupos[f"{g.tipo}:{g.estado}"] += 1
        for lado in (p.a, p.b):
            pend[lado] += sum(1 for r in comp.reg.get(lado, []) if p.dispo.get(r["_id"], 0) > 0)
    return {"registros": {k: len(x) for k, x in por.items()}, "grupos": dict(grupos), "pendientes": dict(pend),
            "duplicados": len(comp.duplicados), "excluidos": len(comp.excluidos), "pasos": PASOS,
            "nota": "Prueba en memoria: no se guardaron coincidencias ni diferencias."}
