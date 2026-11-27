"""Contexto de auditoría y tipos de resultado.

El contexto reutiliza los motores existentes y se carga de forma perezosa (solo lo que piden las reglas ejecutadas):
- fase 3: `analisis.motor.preparar_contexto` (movimientos, árbol de saldos, antigüedad, origen-destino, plan de cuentas);
- fase 4: `compensacion.partidas.composicion` (saldos realmente pendientes tras compensaciones aprobadas);
- fase 5: registros auxiliares (activos, cronogramas, gastos anticipados, servicios en proceso, inventario);
- fase 6: diferencias de conciliaciones vigentes y conciliaciones en memoria (sin guardar) con plantillas internas.
"""
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from functools import cached_property
from types import SimpleNamespace

from sqlalchemy import or_, select

from app.importers.normalizacion import normalizar_texto
from app.models import (CentroCosto, Conciliacion, DiferenciaConciliacion, DocumentoRegistro, LineaDiario, LoteContable,
                        PartidaAbierta, RegistroAuxiliar)

CERO = Decimal("0")
C2 = Decimal("0.01")


def dec(v) -> Decimal:
    if v in (None, ""):
        return CERO
    return v if isinstance(v, Decimal) else Decimal(str(v))


def norm_doc(v) -> str:
    """Serie o número normalizado para comparar (sin espacios, guiones ni ceros a la izquierda); el original se conserva."""
    s = re.sub(r"[^0-9A-Z]", "", normalizar_texto(str(v or "")))
    return s.lstrip("0") or ("0" if s else "")


def doc_de(ln) -> str | None:
    if not ln.numero:
        return None
    return f"{ln.serie}-{ln.numero}" if ln.serie else ln.numero


def asiento_de(ln) -> str | None:
    return "-".join(p for p in (ln.subdiario, ln.asiento) if p) or None


@dataclass
class Res:
    """Resultado de una regla: un hallazgo POTENCIAL con su evidencia verificable."""
    titulo: str
    condicion: str
    importe: Decimal = CERO
    cuenta: str | None = None
    tercero: str | None = None
    razon_social: str | None = None
    documento: str | None = None
    asiento: str | None = None
    linea_id: int | None = None
    centro_costo: str | None = None
    proyecto: str | None = None
    evidencia: list = field(default_factory=list)
    clave: str | None = None            # identidad estable del hallazgo (huella)
    exposicion: str | None = None       # clave de exposición monetaria (agrupación sin duplicar)
    causa: str | None = None
    efecto: str | None = None
    criterio: str | None = None
    recomendacion: str | None = None
    impacto_potencial: str | None = None
    estructural: bool | None = None
    calidad: str = "SUFICIENTE"
    tributario: str | None = None
    regularizacion: str | None = None
    personal: bool = False
    riesgo_minimo: str | None = None
    probabilidad: int | None = None
    impacto_forzado: int | None = None
    detalle: dict = field(default_factory=dict)


@dataclass
class Salida:
    res: list = field(default_factory=list)
    poblacion: int = 0
    importe: Decimal = CERO
    metodo: str = ""
    estado: str | None = None           # SIN_DATOS | PENDIENTE_EVALUACION
    mensaje: str | None = None


def ev_linea(ln, desc=None) -> dict:
    return {"tipo": "LINEA", "tabla": "lineas_diario", "id": ln.id or None,
            "descripcion": desc or f"Línea {ln.id} · asiento {asiento_de(ln) or '—'} · cuenta {ln.cuenta} · "
                                   f"{'D' if ln.debe else 'H'} {ln.debe or ln.haber} · {ln.glosa or 'sin glosa'}",
            "datos": {"fecha": ln.fecha.isoformat() if ln.fecha else None, "periodo": ln.periodo, "cuenta": ln.cuenta,
                      "tercero": ln.tercero, "documento": doc_de(ln), "debe": str(ln.debe), "haber": str(ln.haber), "lote_id": ln.lote_id}}


def ev_calc(desc, **datos) -> dict:
    return {"tipo": "CALCULO", "tabla": None, "id": None, "descripcion": desc,
            "datos": {k: (str(v) if isinstance(v, (Decimal, date)) else v) for k, v in datos.items()}}


def ev_reg(tabla, rid, desc, **datos) -> dict:
    return {"tipo": "REGISTRO", "tabla": tabla, "id": rid, "descripcion": desc,
            "datos": {k: (str(v) if isinstance(v, (Decimal, date)) else v) for k, v in datos.items()}}


class Regla:
    """Vista de la regla para los evaluadores (parámetros ya decodificados)."""

    def __init__(self, r):
        self.id, self.codigo, self.nombre, self.riesgo = r.id, r.codigo, r.nombre, r.riesgo
        self.p = json.loads(r.parametros or "{}")
        self.cuentas = [x.strip() for x in (r.cuentas or "").split(",") if x.strip()]
        self.definicion = json.loads(r.definicion) if r.definicion else None
        self.excepciones = json.loads(r.excepciones) if r.excepciones else {}
        self.criterio, self.recomendacion = r.criterio, r.recomendacion

    def en(self, cuenta, por_defecto=()) -> bool:
        pref = self.cuentas or list(por_defecto)
        return not pref or any((cuenta or "").startswith(x) for x in pref)

    def excluido(self, cuenta=None, tercero=None, documento=None) -> bool:
        x = self.excepciones
        return bool((cuenta and any(cuenta.startswith(c) for c in x.get("cuentas", []))) or (tercero and tercero in x.get("terceros", []))
                    or (documento and documento in x.get("documentos", [])))


class Contexto:
    def __init__(self, db, encargo, alcance: dict, materialidad: dict | None, avance=lambda p, e: None):
        self.db, self.encargo, self.alcance, self.mat, self.avance = db, encargo, alcance, materialidad, avance
        self.empresa_id, self.ejercicio, self.periodo, self.corte = encargo.empresa_id, encargo.ejercicio, encargo.periodo, encargo.fecha_corte

    # ---------------------------------------------------------------- fase 3
    @cached_property
    def ctx3(self):
        from app.analisis.motor import preparar_contexto
        ctx, f, control = preparar_contexto(self.db, self.empresa_id, self.ejercicio, 1, min(self.periodo, 13))
        self.fuentes3, self.control3 = f, control
        return ctx

    @cached_property
    def lineas_todas(self) -> list:
        return [ln for ln in self.ctx3.lineas if ln.fecha is None or ln.fecha <= self.corte or ln.periodo == 13]

    @cached_property
    def centros(self) -> dict:
        return {c.codigo: c for c in self.db.scalars(select(CentroCosto).where(CentroCosto.empresa_id == self.empresa_id))}

    def en_alcance(self, ln) -> bool:
        a = self.alcance
        if a.get("cuentas") and not any(ln.cuenta.startswith(c) for c in a["cuentas"]):
            return False
        if a.get("centros_costo") and ln.cc not in a["centros_costo"]:
            return False
        if a.get("proyectos") and ln.proyecto not in a["proyectos"]:
            return False
        if a.get("unidades_negocio"):
            c = self.centros.get(ln.cc)
            if not c or c.unidad_negocio not in a["unidades_negocio"]:
                return False
        return True

    @cached_property
    def lineas(self) -> list:
        """Movimientos del ejercicio hasta el corte dentro del alcance del encargo."""
        if not any(self.alcance.get(k) for k in ("cuentas", "centros_costo", "proyectos", "unidades_negocio")):
            return self.lineas_todas
        return [ln for ln in self.lineas_todas if self.en_alcance(ln)]

    @cached_property
    def asientos(self) -> dict:
        out = defaultdict(list)
        for ln in self.lineas_todas:
            if ln.asiento:
                out[(ln.lote_id, ln.periodo, ln.subdiario or "", ln.asiento)].append(ln)
        return out

    def asiento_en_alcance(self, lineas) -> bool:
        return any(self.en_alcance(ln) for ln in lineas)

    @property
    def plan(self) -> dict:
        return self.ctx3.plan

    @cached_property
    def lotes(self) -> dict:
        return {x.id: x for x in self.db.scalars(select(LoteContable).where(LoteContable.empresa_id == self.empresa_id))}

    # ---------------------------------------------------------------- eventos posteriores (evidencia complementaria)
    @cached_property
    def posteriores(self) -> list:
        """Movimientos posteriores al corte (mismo ejercicio y el siguiente): solo como evidencia, nunca integran el saldo histórico."""
        from app.analisis.motor import cargar_lineas
        activos = [i for i, x in self.lotes.items() if x.estado == "ACTIVO"]
        return cargar_lineas(self.db, (LineaDiario.empresa_id == self.empresa_id) & LineaDiario.lote_id.in_(activos or [0]) & or_(
            (LineaDiario.ejercicio == self.ejercicio) & (LineaDiario.fecha_contable > self.corte),
            (LineaDiario.ejercicio == self.ejercicio + 1) & (LineaDiario.periodo.between(1, 3))))

    # ---------------------------------------------------------------- registros (fases 2 y 5)
    def documentos(self, tipo: str) -> list:
        q = (select(DocumentoRegistro).join(LoteContable, LoteContable.id == DocumentoRegistro.lote_id)
             .where(DocumentoRegistro.empresa_id == self.empresa_id, DocumentoRegistro.tipo == tipo, LoteContable.estado == "ACTIVO",
                    DocumentoRegistro.ejercicio == self.ejercicio, DocumentoRegistro.periodo <= self.periodo))
        return self.db.scalars(q.order_by(DocumentoRegistro.id)).all()

    def registros(self, tipo: str) -> list[dict]:
        out = []
        for r in self.db.scalars(select(RegistroAuxiliar).where(RegistroAuxiliar.empresa_id == self.empresa_id, RegistroAuxiliar.tipo == tipo,
                                                                RegistroAuxiliar.vigente.is_(True)).order_by(RegistroAuxiliar.id)):
            d = json.loads(r.datos)
            d.update(_id=r.id, _clave=r.clave, _cuenta=r.cuenta, _fecha=r.fecha_referencia)
            out.append(d)
        return out

    # ---------------------------------------------------------------- fase 4
    @cached_property
    def partidas(self):
        """Partidas abiertas pendientes (fase 4) o None si el motor de compensación no se ha ejecutado."""
        if not self.db.scalar(select(PartidaAbierta.id).where(PartidaAbierta.empresa_id == self.empresa_id).limit(1)):
            return None
        from app.compensacion import partidas
        return partidas.composicion(self.db, self.empresa_id, self.corte, solo_pendientes=True, incluir_propuestas=False)

    # ---------------------------------------------------------------- fase 6
    def diferencias_conciliacion(self, tipos: tuple) -> list:
        """Diferencias abiertas de la versión vigente de las conciliaciones (fase 6) al corte o anteriores más recientes."""
        ultimos = {}
        for c in self.db.scalars(select(Conciliacion).where(Conciliacion.empresa_id == self.empresa_id, Conciliacion.tipo_codigo.in_(tipos),
                                                            Conciliacion.fecha_corte <= self.corte, Conciliacion.version_id.is_not(None))
                                 .order_by(Conciliacion.fecha_corte)):
            ultimos[c.ambito_clave] = c
        if not ultimos:
            return []
        return self.db.scalars(select(DiferenciaConciliacion).where(
            DiferenciaConciliacion.version_id.in_([c.version_id for c in ultimos.values()]),
            DiferenciaConciliacion.estado.notin_(("SUBSANADO", "APROBADO", "CERRADO")))).all()

    def conciliar_en_memoria(self, tipo: str, ambito: dict | None = None) -> list[dict]:
        """Ejecuta una plantilla de la fase 6 cuyas fuentes son internas, sin guardar nada (motor y clasificador de la fase 6)."""
        cache = self.__dict__.setdefault("_conc_mem", {})
        ck = (tipo, json.dumps(ambito or {}, sort_keys=True))
        if ck in cache:
            v = cache[ck]
            return v[0] if isinstance(v, tuple) else v
        from app.conciliacion import catalogo, clasificar, fuentes
        from app.conciliacion.motor import Comparador, Tolerancia
        from app.models import PlantillaConciliacion
        catalogo.sembrar(self.db)
        p = self.db.scalar(select(PlantillaConciliacion).where(PlantillaConciliacion.empresa_id.is_(None), PlantillaConciliacion.codigo == tipo))
        cfg = catalogo.configuracion(self.db, p)
        cx = fuentes.Contexto(self.db, self.empresa_id, self.ejercicio, min(self.periodo, 12), self.corte, ambito or {})
        libros = self.__dict__.setdefault("_libros5", {})  # el libro de la fase 5 se carga una sola vez para todas las plantillas
        cx._libro = libros
        por, info, n = {}, {}, 0
        for lado, spec in cfg["fuentes"].items():
            if spec["tipo"] in ("ARCHIVO", "EMPRESA_RELACIONADA") or (spec["tipo"] == "BANCO" and not (ambito or {}).get("cuenta_bancaria_id")):
                cache[ck] = []
                return []
            fn = fuentes.CONSTRUCTORES[spec["tipo"]]
            regs, meta = fn(cx, spec.get("parametros", {}))
            for r in regs:
                n += 1
                r.update(_id=-n, _lado=lado, _val=Decimal(r["importe"] or 0), id=-n, lado=lado)
                r.setdefault("datos", {})
            por[lado] = regs
            info[lado] = {"rol": spec.get("rol"), "nombre": spec.get("nombre"), "saldo": meta.get("saldo")}
        t = cfg.get("tolerancia") or {}
        tol = Tolerancia(Decimal(str(t.get("importe_absoluto") or "0")), None, int(t.get("dias") or 0))
        comp = Comparador(por, cfg, tol, set(cfg.get("confirmar_automaticamente") or []), set())
        comp.ejecutar(cfg["pasadas"], cfg["reglas"], [])
        run = SimpleNamespace(fecha_corte=self.corte, ejercicio=self.ejercicio, periodo=min(self.periodo, 12), empresa_id=self.empresa_id,
                              ambito="{}")
        R = clasificar.Resultado(comp, info, tipo, cfg, cx, run, tol)
        clasificar.clasificar(R, cfg["reglas"])
        for d in R.difs:
            d["_registros"] = [R.registros[i] for i in d["registros"]]
        cache[ck] = (R.difs, R.reporte)
        return R.difs

    def reporte_en_memoria(self, tipo, ambito=None) -> dict:
        self.conciliar_en_memoria(tipo, ambito)
        v = self._conc_mem.get((tipo, json.dumps(ambito or {}, sort_keys=True)))
        return v[1] if isinstance(v, tuple) else {}

    # ---------------------------------------------------------------- materialidad
    def significativo(self, importe, modulo=None, cuenta=None) -> bool:
        """Importe sobre la materialidad de ejecución (por cuenta o tipo si se definió). Sin materialidad aprobada: falso."""
        u = self.umbral(modulo, cuenta)
        return u is not None and abs(dec(importe)) >= u

    def umbral(self, modulo=None, cuenta=None):
        m = self.mat
        if not m:
            return None
        for pref, v in sorted((m.get("por_cuenta") or {}).items(), key=lambda x: -len(x[0])):
            if cuenta and cuenta.startswith(pref):
                return dec(v)
        if modulo and (m.get("por_tipo") or {}).get(modulo) is not None:
            return dec(m["por_tipo"][modulo])
        return dec(m["materialidad_ejecucion"])


def fin_mes(fecha: date) -> date:
    return (fecha.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def periodo_de(fecha: date | None) -> int | None:
    return fecha.year * 100 + fecha.month if fecha else None


def fase3(ax, tipo: str, codigo: str, *, cuentas=None, valor=None, importe_minimo="0", tolerancia_pct="0", parametros=None,
          lineas=None) -> list:
    """Evalúa un evaluador de la fase 3 con una regla transitoria (no se guarda) y devuelve sus hallazgos."""
    from app.analisis import reglas as r3
    from app.models import ReglaAnalisis
    reg = ReglaAnalisis(id=None, codigo=codigo[:12], nombre=codigo, tipo=tipo, cuentas=",".join(cuentas) if cuentas else None,
                        valor=Decimal(str(valor)) if valor is not None else None, importe_minimo=dec(importe_minimo),
                        tolerancia_pct=dec(tolerancia_pct), parametros=json.dumps(parametros or {}), riesgo="MEDIO")
    ctx = ax.ctx3
    original = ctx.lineas
    if lineas is not None:
        ctx.lineas = lineas
    try:
        return r3.evaluar(reg, ctx)
    finally:
        ctx.lineas = original


def res_de_h3(h, prefijo, **kw) -> Res:
    ev = {k: v for k, v in (h.evidencia or {}).items() if not isinstance(v, (list, dict))}
    lista = [x for x in (h.evidencia or {}).values() if isinstance(x, list)]
    clave = f"{prefijo}|{h.cuenta}|{h.tercero}|{h.documento}|{h.linea_id}|{h.periodo}"
    base = dict(titulo=h.titulo, condicion=h.titulo, importe=h.importe, cuenta=h.cuenta, tercero=h.tercero, documento=h.documento,
                asiento=h.asiento, linea_id=h.linea_id, evidencia=[ev_calc("Evidencia calculada (motor de análisis, fase 3)", **ev)]
                + ([ev_calc("Detalle", items=lista[0][:30])] if lista else []), clave=clave,
                exposicion=h.clave_exposicion or (f"LINEA|{h.linea_id}" if h.linea_id else f"DOC|{h.tercero}|{h.documento}" if h.documento
                                                  else f"CUENTA|{h.cuenta}|{h.tercero or ''}"))
    base.update(kw)
    return Res(**base)
