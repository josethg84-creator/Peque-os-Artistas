"""Comparación de anexos: dos versiones del mismo anexo, o el anexo contra otra fecha de corte
(mes anterior, ejercicio anterior). Las fechas de corte para las que no existe versión se calculan
al vuelo con el mismo motor (sin guardarlas), indicándolo en el resultado."""
import json
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.anexos import datos as datos_mod
from app.anexos import generador, render
from app.models import Anexo, VersionAnexo

CERO = Decimal("0")


def _doc(r) -> str | None:
    if r.get("numero"):
        return f"{r.get('tercero') or ''}|{r.get('tipo_documento') or ''}|{r.get('serie') or ''}|{r.get('numero')}"
    return None


def comparar_filas(base: list[dict], nueva: list[dict]) -> dict:
    """`base` es la referencia (anterior); `nueva` la actual."""
    b = {r["clave"]: r for r in base}
    n = {r["clave"]: r for r in nueva}
    b_doc = {_doc(r): r for r in base if _doc(r)}
    nuevas, canceladas, cambios, reclas, antig = [], [], [], [], []
    reclas_base = set()
    for k, r in n.items():
        if k in b:
            o = b[k]
            if o["saldo"] != r["saldo"]:
                cambios.append({"clave": k, "documento": r.get("documento"), "razon_social": r.get("razon_social"),
                                "antes": o["saldo"], "despues": r["saldo"], "variacion": r["saldo"] - o["saldo"]})
            if (o.get("tramo") or "") != (r.get("tramo") or "") and r["saldo"]:
                antig.append({"clave": k, "documento": r.get("documento"), "antes": o.get("tramo"), "despues": r.get("tramo"),
                              "saldo": r["saldo"]})
            if (o.get("categoria") or "") != (r.get("categoria") or "") or (o.get("cuenta") or "") != (r.get("cuenta") or ""):
                reclas.append({"clave": k, "documento": r.get("documento"), "antes": f"{o.get('cuenta')} · {o.get('categoria') or ''}",
                               "despues": f"{r.get('cuenta')} · {r.get('categoria') or ''}", "saldo": r["saldo"]})
        else:
            d = _doc(r)
            o = b_doc.get(d) if d else None
            if o is not None and o["clave"] not in n:
                reclas_base.add(o["clave"])
                reclas.append({"clave": k, "documento": r.get("documento"), "antes": f"{o.get('cuenta')} · {o.get('categoria') or ''}",
                               "despues": f"{r.get('cuenta')} · {r.get('categoria') or ''}", "saldo": r["saldo"]})
            else:
                nuevas.append({"clave": k, "documento": r.get("documento"), "razon_social": r.get("razon_social"),
                               "categoria": r.get("categoria"), "saldo": r["saldo"]})
    for k, o in b.items():
        if k not in n and k not in reclas_base:
            canceladas.append({"clave": k, "documento": o.get("documento"), "razon_social": o.get("razon_social"),
                               "categoria": o.get("categoria"), "saldo": o["saldo"]})
    tot_b = sum((r["saldo"] for r in base), CERO)
    tot_n = sum((r["saldo"] for r in nueva), CERO)
    return {"partidas_nuevas": nuevas, "partidas_canceladas": canceladas, "cambios_importe": cambios, "reclasificaciones": reclas,
            "cambios_antiguedad": antig,
            "totales": {"base": tot_b, "nueva": tot_n, "variacion": tot_n - tot_b},
            "conteo": {"nuevas": len(nuevas), "canceladas": len(canceladas), "cambios_importe": len(cambios),
                       "reclasificaciones": len(reclas), "cambios_antiguedad": len(antig)}}


def _hallazgos(resumen: dict) -> dict:
    return {h["huella"]: h for h in resumen.get("hallazgos", [])}


def comparar(db: Session, a: Anexo, contra: str, usuario: str) -> dict:
    """contra: 'version:N' | 'aprobada' | 'original' | 'mes_anterior' | 'ejercicio_anterior' | 'corte:AAAA-MM-DD'."""
    actual = db.get(VersionAnexo, a.version_id)
    if not actual:
        raise LookupError("El anexo no tiene versiones")
    snap = json.loads(actual.plantilla_snapshot)
    filas_n = render.filas_version(db, actual.id, a.especialidad)
    res_n = json.loads(actual.resumen)
    base_v = None
    if contra.startswith("version:"):
        num = int(contra.split(":", 1)[1])
        base_v = db.scalar(select(VersionAnexo).where(VersionAnexo.anexo_id == a.id, VersionAnexo.numero == num))
    elif contra == "original":
        base_v = db.scalar(select(VersionAnexo).where(VersionAnexo.anexo_id == a.id).order_by(VersionAnexo.numero))
    elif contra == "aprobada":
        base_v = db.scalar(select(VersionAnexo).where(VersionAnexo.anexo_id == a.id, VersionAnexo.inmutable.is_(True),
                                                      VersionAnexo.id != actual.id).order_by(VersionAnexo.numero.desc()))
        if base_v is None:
            raise LookupError("No hay una versión aprobada anterior a la actual")
    if base_v is not None or contra.startswith("version:"):
        if base_v is None:
            raise LookupError("Versión no encontrada")
        filas_b = render.filas_version(db, base_v.id, a.especialidad)
        res_b = json.loads(base_v.resumen)
        etiqueta = f"Versión {base_v.numero} ({base_v.generado_en:%d/%m/%Y %H:%M})"
        calculado = False
    else:
        if contra == "mes_anterior":
            m = a.fecha_corte.month - 1 or 12
            ej = a.fecha_corte.year - (1 if a.fecha_corte.month == 1 else 0)
            corte, periodo = datos_mod.fin_de_periodo(ej, m), m
        elif contra == "ejercicio_anterior":
            ej = a.fecha_corte.year - 1
            import calendar
            corte = date(ej, a.fecha_corte.month, min(a.fecha_corte.day, calendar.monthrange(ej, a.fecha_corte.month)[1]))
            periodo = a.periodo
        elif contra.startswith("corte:"):
            corte = date.fromisoformat(contra.split(":", 1)[1])
            ej, periodo = corte.year, corte.month
        else:
            raise ValueError("Comparación no válida")
        filtros = datos_mod.Filtros(**(json.loads(a.filtros) if a.filtros else {}))
        existente = db.scalar(select(Anexo).where(Anexo.empresa_id == a.empresa_id, Anexo.cuenta == a.cuenta, Anexo.fecha_corte == corte,
                                                  Anexo.plantilla_id == a.plantilla_id, Anexo.filtros.is_(a.filtros) if a.filtros is None
                                                  else Anexo.filtros == a.filtros))
        if existente and existente.version_id:
            v = db.get(VersionAnexo, existente.version_id)
            filas_b, res_b = render.filas_version(db, v.id, a.especialidad), json.loads(v.resumen)
            etiqueta, calculado = f"Anexo al {corte:%d/%m/%Y} (versión {v.numero})", False
        else:
            ctx = datos_mod.crear(db, a.empresa_id, ej, periodo, corte, filtros)
            calc = generador.calcular(ctx, a.cuenta, snap)
            filas_b = [{**{k: v for k, v in f.items() if k != "datos"}, **f["datos"]} for f in calc["filas"]]
            res_b = calc["resumen"]
            res_b["hallazgos"] = [{"huella": generador._huella(h), "codigo": h["codigo"], "titulo": h["titulo"], "severidad": h["severidad"]}
                                  for h in calc["hallazgos"]]
            etiqueta, calculado = f"Cálculo al {corte:%d/%m/%Y} (sin versión guardada)", True
    out = comparar_filas(filas_b, filas_n)
    hb, hn = _hallazgos(res_b), _hallazgos(res_n)
    out["observaciones_nuevas"] = [hn[k] for k in hn if k not in hb]
    out["observaciones_subsanadas"] = [hb[k] for k in hb if k not in hn]
    out["resumen"] = {"base": {k: res_b.get(k) for k in ("saldo_final_contable", "saldo_detalle", "diferencia", "resultado")},
                      "actual": {k: res_n.get(k) for k in ("saldo_final_contable", "saldo_detalle", "diferencia", "resultado")}}
    out["base"] = etiqueta
    out["actual"] = f"Versión {actual.numero} al {a.fecha_corte:%d/%m/%Y}"
    out["calculado_al_vuelo"] = calculado
    generador.auditar(db, a.empresa_id, usuario, "COMPARAR", "anexo", a.id, {"contra": contra})
    db.commit()
    return out
