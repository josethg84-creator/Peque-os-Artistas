"""Cálculo de saldos y árbol jerárquico de cuentas a partir de la información importada.

Fuentes (sin duplicar información):
  * Movimientos: líneas de lotes ACTIVOS de libro diario. Para un periodo sin diario se usa el
    libro mayor (si existe). Nunca se suman diario y mayor del mismo periodo.
  * Apertura: lote ACTIVO de saldos iniciales del ejercicio. Si existe, las líneas del periodo 00
    del diario (asiento de apertura) se ignoran para no duplicar; si no existe, el periodo 00 del
    diario hace de apertura. Sin ninguna de las dos, el saldo inicial es preliminar.

Precisión: las sumas se hacen en SQL sobre céntimos enteros (ROUND(importe*100)) y se convierten a
Decimal, de modo que el resultado es exacto en SQLite y en PostgreSQL.

Saldos con signo: positivo = deudor, negativo = acreedor.
"""
import hashlib
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.analisis import pcge
from app.models import CuentaContable, LineaDiario, LoteContable, SaldoCuenta

CERO = Decimal("0")
CIEN = Decimal("100")


def cent(col):
    return func.coalesce(func.sum(func.round(col * 100)), 0)


def dec(centimos) -> Decimal:
    return (Decimal(int(centimos or 0)) / CIEN).quantize(Decimal("0.01"))


# ------------------------------------------------------------------ fuentes y versión
def version_datos(db: Session, empresa_id: int) -> str:
    """Huella de los lotes de la empresa: cambia al importar, anular o reemplazar información."""
    filas = db.execute(select(LoteContable.id, LoteContable.estado, LoteContable.registros_importados,
                              LoteContable.hash_archivo, LoteContable.creado_en)
                       .where(LoteContable.empresa_id == empresa_id).order_by(LoteContable.id)).all()
    return hashlib.sha256(repr(filas).encode()).hexdigest()[:32]


@dataclass
class Fuentes:
    empresa_id: int
    ejercicio: int
    por_periodo: dict[int, dict] = field(default_factory=dict)  # periodo → {"tipo", "lotes"}
    lotes_apertura: list[int] = field(default_factory=list)
    apertura: str = "NINGUNA"  # SALDOS_INICIALES | DIARIO_00 | NINGUNA
    advertencias: list[str] = field(default_factory=list)

    def filtro_lineas(self, desde: int, hasta: int, incluir_apertura_diario=False):
        """Condición SQL sobre LineaDiario para los periodos [desde, hasta]."""
        condiciones = []
        for p, info in self.por_periodo.items():
            if p == 0 and not incluir_apertura_diario:
                continue
            if desde <= p <= hasta:
                condiciones.append(and_(LineaDiario.periodo == p, LineaDiario.lote_id.in_(info["lotes"])))
        if not condiciones:
            return LineaDiario.id < 0  # ningún movimiento
        return and_(LineaDiario.empresa_id == self.empresa_id, LineaDiario.ejercicio == self.ejercicio, or_(*condiciones))

    def periodos_con_datos(self) -> list[int]:
        return sorted(p for p in self.por_periodo if p not in (0,))


def fuentes(db: Session, empresa_id: int, ejercicio: int) -> Fuentes:
    f = Fuentes(empresa_id, ejercicio)
    filas = db.execute(
        select(LoteContable.tipo_informacion, LineaDiario.periodo, LineaDiario.lote_id)
        .join(LoteContable, LoteContable.id == LineaDiario.lote_id)
        .where(LineaDiario.empresa_id == empresa_id, LineaDiario.ejercicio == ejercicio, LoteContable.estado == "ACTIVO",
               LoteContable.tipo_informacion.in_(("DIARIO", "MAYOR")))
        .group_by(LoteContable.tipo_informacion, LineaDiario.periodo, LineaDiario.lote_id)).all()
    candidatos: dict[int, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for tipo, periodo, lote in filas:
        candidatos[periodo if periodo is not None else -1][tipo].add(lote)
    for p, tipos in candidatos.items():
        if p == -1:
            f.advertencias.append("Hay líneas sin periodo: no se incluyen en el análisis.")
            continue
        tipo = "DIARIO" if tipos.get("DIARIO") else "MAYOR"
        f.por_periodo[p] = {"tipo": tipo, "lotes": sorted(tipos[tipo])}
        if tipos.get("DIARIO") and tipos.get("MAYOR"):
            f.advertencias.append(f"Periodo {p:02d}: hay diario y mayor; se usa el diario para no duplicar movimientos.")
        if tipo == "MAYOR":
            f.advertencias.append(f"Periodo {p:02d}: solo hay libro mayor; verifique que la importación sea completa.")
    f.lotes_apertura = list(db.scalars(select(LoteContable.id).where(
        LoteContable.empresa_id == empresa_id, LoteContable.ejercicio == ejercicio, LoteContable.estado == "ACTIVO",
        LoteContable.tipo_informacion == "SALDOS_INICIALES")))
    if f.lotes_apertura:
        f.apertura = "SALDOS_INICIALES"
        if 0 in f.por_periodo:
            f.advertencias.append("Se usan los saldos iniciales importados; el asiento de apertura del diario (periodo 00) "
                                  "se excluye para no duplicar.")
    elif 0 in f.por_periodo:
        f.apertura = "DIARIO_00"
    else:
        f.advertencias.append("No hay saldos iniciales ni asiento de apertura del ejercicio: los saldos iniciales son "
                              "PRELIMINARES (solo consideran movimientos importados del ejercicio).")
    return f


# ------------------------------------------------------------------ agregación por cuenta
@dataclass
class Hoja:
    si: int = 0          # céntimos
    debe: int = 0
    haber: int = 0
    n: int = 0
    terceros: set = field(default_factory=set)
    por_periodo: dict = field(default_factory=dict)  # p → (debe, haber) céntimos


def saldos_hoja(db: Session, f: Fuentes, desde: int, hasta: int, *, filtro_extra=None) -> dict[str, Hoja]:
    hojas: dict[str, Hoja] = defaultdict(Hoja)
    # apertura
    if f.apertura == "SALDOS_INICIALES" and f.lotes_apertura and filtro_extra is None:
        for c, v in db.execute(select(SaldoCuenta.cuenta, cent(SaldoCuenta.saldo_inicial_debe) - cent(SaldoCuenta.saldo_inicial_haber))
                               .where(SaldoCuenta.lote_id.in_(f.lotes_apertura)).group_by(SaldoCuenta.cuenta)):
            hojas[c].si += int(v)
    # movimientos anteriores al rango (incluye periodo 00 del diario cuando hace de apertura)
    previos = f.filtro_lineas(0 if f.apertura == "DIARIO_00" else 1, desde - 1, incluir_apertura_diario=f.apertura == "DIARIO_00")
    q = select(LineaDiario.cuenta, cent(LineaDiario.debe_mn) - cent(LineaDiario.haber_mn)).where(previos)
    if filtro_extra is not None:
        q = q.where(filtro_extra)
    for c, v in db.execute(q.group_by(LineaDiario.cuenta)):
        hojas[c].si += int(v)
    # movimientos del rango
    rango = f.filtro_lineas(desde, hasta)
    q = select(LineaDiario.cuenta, LineaDiario.periodo, cent(LineaDiario.debe_mn), cent(LineaDiario.haber_mn),
               func.count()).where(rango)
    if filtro_extra is not None:
        q = q.where(filtro_extra)
    for c, p, d, h, n in db.execute(q.group_by(LineaDiario.cuenta, LineaDiario.periodo)):
        hj = hojas[c]
        hj.debe += int(d)
        hj.haber += int(h)
        hj.n += n
        hj.por_periodo[p] = (int(d), int(h))
    q = select(LineaDiario.cuenta, LineaDiario.documento_tercero).where(rango, LineaDiario.documento_tercero.is_not(None))
    if filtro_extra is not None:
        q = q.where(filtro_extra)
    for c, t in db.execute(q.distinct()):
        hojas[c].terceros.add(t)
    return hojas


# ------------------------------------------------------------------ árbol
@dataclass
class Nodo:
    codigo: str
    padre: str | None
    descripcion: str | None
    naturaleza: str | None
    si: int = 0
    debe: int = 0
    haber: int = 0
    n: int = 0
    terceros: set = field(default_factory=set)
    propio: bool = False      # tiene líneas registradas directamente en este código
    hijos: int = 0
    anterior: int | None = None  # saldo final del periodo comparable anterior

    @property
    def sf(self) -> int:
        return self.si + self.debe - self.haber

    def como_dict(self) -> dict:
        sf = self.sf
        var = None if self.anterior is None else sf - self.anterior
        pct = None
        if self.anterior:  # base cero → variación porcentual no aplicable
            pct = round(float(Decimal(var) / abs(Decimal(self.anterior)) * 100), 2)
        return {
            "cuenta": self.codigo, "padre": self.padre, "nivel": len(self.codigo), "nivel_nombre": pcge.nombre_nivel(self.codigo),
            "descripcion": self.descripcion, "naturaleza": self.naturaleza, "perfil": pcge.perfil(self.codigo).clave,
            "saldo_inicial": str(dec(self.si)), "debe": str(dec(self.debe)), "haber": str(dec(self.haber)),
            "neto": str(dec(self.debe - self.haber)), "saldo_final": str(dec(sf)),
            "movimientos": self.n, "terceros": len(self.terceros), "tiene_hijos": self.hijos > 0, "movimiento_propio": self.propio,
            "saldo_anterior": str(dec(self.anterior)) if self.anterior is not None else None,
            "variacion": str(dec(var)) if var is not None else None, "variacion_pct": pct,
        }


def construir_arbol(hojas: dict[str, Hoja], plan: dict[str, CuentaContable]) -> dict[str, Nodo]:
    codigos_plan = set(plan) | set(hojas)
    nodos: dict[str, Nodo] = {}

    def nodo(c: str) -> Nodo:
        if c not in nodos:
            p = plan.get(c)
            nodos[c] = Nodo(c, None, (p.descripcion if p else None) or pcge.nombre_pcge(c),
                            (p.naturaleza if p and p.naturaleza else None) or pcge.naturaleza_pcge(c))
        return nodos[c]

    for codigo, h in hojas.items():
        if not (h.si or h.debe or h.haber or h.n):
            continue
        cadena = pcge.ancestros(codigo, codigos_plan) + [codigo]
        for c in cadena:  # cada línea se suma una sola vez en cada nivel de su propia cadena
            nd = nodo(c)
            nd.si += h.si
            nd.debe += h.debe
            nd.haber += h.haber
            nd.n += h.n
            nd.terceros |= h.terceros
        nodos[codigo].propio = bool(h.n)
    for c, nd in nodos.items():
        ancestros = [a for a in pcge.ancestros(c, codigos_plan) if a in nodos]
        nd.padre = ancestros[-1] if ancestros else None
        if nd.padre:
            nodos[nd.padre].hijos += 1
    return nodos


def plan_de(db: Session, empresa_id: int) -> dict[str, CuentaContable]:
    return {c.codigo: c for c in db.scalars(select(CuentaContable).where(CuentaContable.empresa_id == empresa_id))}


def periodo_anterior(ejercicio: int, desde: int, hasta: int) -> tuple[int, int, int] | None:
    """Rango comparable inmediatamente anterior, de la misma longitud."""
    largo = hasta - desde + 1
    if desde - largo >= 1:
        return ejercicio, desde - largo, desde - 1
    if desde == 1 and largo <= 12:
        return ejercicio - 1, 13 - largo, 12
    return None


def totales(nodos: dict[str, Nodo]) -> dict:
    """Totales sobre los elementos 1–9 (las cuentas de orden van por separado)."""
    raices = [n for n in nodos.values() if n.padre is None]
    bal = [n for n in raices if n.codigo[0] != "0"]
    orden = [n for n in raices if n.codigo[0] == "0"]
    s = lambda lista, attr: sum(getattr(x, attr) for x in lista)  # noqa: E731
    return {
        "debe": str(dec(s(bal, "debe"))), "haber": str(dec(s(bal, "haber"))),
        "saldo_inicial": str(dec(s(bal, "si"))), "saldo_final": str(dec(sum(x.sf for x in bal))),
        "movimientos": s(bal, "n"), "cuentas_orden": {"debe": str(dec(s(orden, "debe"))), "haber": str(dec(s(orden, "haber")))},
        "cuadra": s(bal, "debe") == s(bal, "haber"),
    }


# ------------------------------------------------------------------ caché
_CACHE: dict[tuple, dict] = {}
_LOCK = threading.Lock()
_MAX = 64


def balance(db: Session, empresa_id: int, ejercicio: int, desde: int, hasta: int, *, comparar=True) -> dict:
    """Árbol completo con totales, comparación con el periodo anterior y control de cuadre.
    Se cachea por (empresa, ejercicio, rango, versión de datos); importar o anular un lote lo invalida."""
    version = version_datos(db, empresa_id)
    clave = (empresa_id, ejercicio, desde, hasta, version, comparar)
    with _LOCK:
        if clave in _CACHE:
            return _CACHE[clave]
    f = fuentes(db, empresa_id, ejercicio)
    plan = plan_de(db, empresa_id)
    hojas = saldos_hoja(db, f, desde, hasta)
    nodos = construir_arbol(hojas, plan)
    advertencias = list(f.advertencias)
    faltantes = [p for p in range(desde, min(hasta, 12) + 1) if p not in f.por_periodo]
    if faltantes:
        advertencias.append(f"Periodos sin información importada en el rango: {', '.join(f'{p:02d}' for p in faltantes)}.")
    if comparar:
        ant = periodo_anterior(ejercicio, desde, hasta)
        if ant:
            fa = fuentes(db, empresa_id, ant[0])
            if any(ant[1] <= p <= ant[2] for p in fa.por_periodo) or fa.apertura != "NINGUNA":
                previo = construir_arbol(saldos_hoja(db, fa, ant[1], ant[2]), plan)
                for c, nd in nodos.items():
                    nd.anterior = previo[c].sf if c in previo else 0
    control = control_cuadre(db, f, desde, hasta, nodos)
    res = {"empresa_id": empresa_id, "ejercicio": ejercicio, "desde": desde, "hasta": hasta, "version_datos": version,
           "fuentes": {str(p): v for p, v in sorted(f.por_periodo.items())}, "apertura": f.apertura,
           "preliminar": f.apertura == "NINGUNA", "advertencias": advertencias,
           "totales": totales(nodos), "control": control,
           "nodos": [n.como_dict() for n in sorted(nodos.values(), key=lambda x: x.codigo)]}
    with _LOCK:
        if len(_CACHE) >= _MAX:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[clave] = res
    return res


def control_cuadre(db: Session, f: Fuentes, desde: int, hasta: int, nodos: dict[str, Nodo]) -> dict:
    """Concilia el árbol con la información original: la suma directa de las líneas fuente debe ser
    igual a la suma de los elementos del árbol (garantiza que no hubo duplicación ni pérdidas)."""
    d, h, n = db.execute(select(cent(LineaDiario.debe_mn), cent(LineaDiario.haber_mn), func.count())
                         .where(f.filtro_lineas(desde, hasta))).one()
    raices = [x for x in nodos.values() if x.padre is None]
    ad, ah, an = sum(x.debe for x in raices), sum(x.haber for x in raices), sum(x.n for x in raices)
    return {"origen_debe": str(dec(d)), "origen_haber": str(dec(h)), "origen_lineas": n,
            "arbol_debe": str(dec(ad)), "arbol_haber": str(dec(ah)), "arbol_lineas": an,
            "conciliado": (int(d), int(h), n) == (ad, ah, an)}


def limpiar_cache():
    with _LOCK:
        _CACHE.clear()
