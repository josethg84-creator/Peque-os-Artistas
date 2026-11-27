"""Motor universal de comparación.

Pasadas: cada pasada compara dos fuentes (A↔B, B↔C…) en modo PARTIDAS (registro contra registro) o AGREGADO
(totales por clave). Reglas en orden de prioridad:
- CLAVE: identificadores (operación, documento, tercero…). 1:1, 1:N, N:1 y N:N cuando las sumas coinciden; parcial si
  la regla lo admite; si hay varias alternativas posibles → AMBIGUA (nunca se confirma sola).
- IMPORTE_FECHA: mismo importe (± tolerancia) y fecha dentro de la ventana; solo si la pareja es única en ambos sentidos.
- COMBINACION: un registro contra la suma de varios (búsqueda acotada por elementos y nodos).
- AGREGADO: totales por clave (concepto, trabajador, cuenta, activo, asiento…) campo por campo.
Antes: exclusiones (expresiones seguras), duplicados y decisiones manuales previas (se re-aplican si los registros siguen
disponibles). Las coincidencias exactas o dentro de tolerancia se confirman según la plantilla; las demás quedan propuestas.
"""
import bisect
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from dataclasses import dataclass, field
from decimal import Decimal

from app.anexos import expresiones
from app.conciliacion.fuentes import norm_doc, norm_tipo_doc
from app.importers.normalizacion import normalizar_texto

CERO = Decimal("0")
C2 = Decimal("0.01")
CAMPOS_DOC = {"serie", "numero", "operacion", "tercero", "referencia", "contrato"}


@dataclass
class Tolerancia:
    importe_absoluto: Decimal = CERO
    porcentaje: Decimal | None = None
    dias: int = 0

    def permitido(self, base: Decimal) -> Decimal:
        if self.porcentaje is None:
            return self.importe_absoluto
        pct = (abs(base) * self.porcentaje / 100).quantize(C2)
        return min(self.importe_absoluto, pct) if self.importe_absoluto > 0 else pct

    def dentro(self, diferencia: Decimal, base: Decimal) -> bool:
        return abs(diferencia) <= self.permitido(base)

    def como_dict(self):
        return {"importe_absoluto": str(self.importe_absoluto), "porcentaje": str(self.porcentaje) if self.porcentaje is not None else None,
                "dias": self.dias}


def valor(r: dict, campo: str):
    v = r.get(campo) if campo in r else r["datos"].get(campo)
    if v is None and campo in r["datos"]:
        v = r["datos"][campo]
    return v


def _num(v) -> Decimal:
    if v in (None, ""):
        return CERO
    return v if isinstance(v, Decimal) else Decimal(str(v))


def clave_de(r: dict, campos: list[str]):
    out = []
    for c in campos:
        v = valor(r, c)
        if c == "tipo_documento":
            v = norm_tipo_doc(v)
        elif c in CAMPOS_DOC:
            v = norm_doc(v)
        elif c == "periodo":
            v = str(v) if v else None
        else:
            v = normalizar_texto(str(v)) if v not in (None, "") else None
        if not v:
            return None
        out.append(v)
    return tuple(out)


@dataclass
class Grupo:
    pasada: str
    tipo: str
    modalidad: str
    nivel: int
    regla: str
    estado: str
    a: list = field(default_factory=list)   # [(registro, importe asignado)]
    b: list = field(default_factory=list)
    clave: str | None = None
    puntuacion: int = 0
    origen: str = "AUTOMATICO"
    detalle: dict = field(default_factory=dict)
    dias: int | None = None
    justificacion: str | None = None
    usuario: str = "motor"

    @property
    def importe_a(self):
        return sum((r["_val"] / abs(r["_val"]) * m if r["_val"] else CERO for r, m in self.a), CERO)

    @property
    def importe_b(self):
        return sum((r["_val"] / abs(r["_val"]) * m if r["_val"] else CERO for r, m in self.b), CERO)


@dataclass
class Pasada:
    nombre: str
    a: str
    b: str
    modo: str
    signo: str
    grupos: list = field(default_factory=list)
    dispo: dict = field(default_factory=dict)   # id de registro → saldo por conciliar (valor absoluto)
    ambiguos: set = field(default_factory=set)
    parciales: set = field(default_factory=set)
    claves_reporte: list = field(default_factory=list)
    omitida: str | None = None


class Comparador:
    def __init__(self, registros: dict[str, list[dict]], cfg: dict, tol: Tolerancia, auto: set[str], rechazadas: set[frozenset],
                 avance=lambda p, e: None, cancelar=lambda: False):
        self.reg = registros
        self.cfg = cfg
        self.tol = tol
        self.auto = auto
        self.rechazadas = rechazadas
        self.avance = avance
        self.cancelar = cancelar
        self.duplicados: dict[int, int] = {}      # id duplicado → id del original
        self.excluidos: dict[int, str] = {}
        self.pasadas: list[Pasada] = []

    # ---------------------------------------------------------------- preparación
    def exclusiones(self, reglas: list[dict]):
        for lado, lst in self.reg.items():
            for r in lst:
                if r.get("excluido"):
                    self.excluidos[r["_id"]] = r.get("motivo_exclusion") or "Excluido por la fuente"
        for rg in reglas:
            if rg["tipo"] != "EXCLUSION" or not rg["activa"]:
                continue
            arbol = expresiones.compilar(rg["parametros"]["expresion"])
            lados = rg["parametros"].get("lado", "*")
            for lado, lst in self.reg.items():
                if lados not in ("*", lado):
                    continue
                for r in lst:
                    try:
                        if expresiones.evaluar(arbol, {**r, **r["datos"]}):
                            self.excluidos[r["_id"]] = f"Regla {rg['codigo']}: {rg['descripcion']}"
                    except expresiones.ErrorExpresion:
                        continue

    def detectar_duplicados(self):
        for lado, claves_lst in (self.cfg.get("duplicados") or {}).items():
            vistos = {}
            for r in self.reg.get(lado, []):
                if r["_id"] in self.excluidos:
                    continue
                for campos in claves_lst:
                    k = clave_de(r, campos)
                    if not k:
                        continue
                    k = (tuple(campos), k, r["_val"] if "importe" not in campos else None)
                    if k in vistos:
                        self.duplicados[r["_id"]] = vistos[k]["_id"]
                        break
                    vistos[k] = r

    # ---------------------------------------------------------------- utilidades
    def _signo(self, p: Pasada, lado: str) -> int:
        return -1 if p.signo == "OPUESTO" and lado == p.b else 1

    def _pend(self, p: Pasada, lado: str):
        return [r for r in self.reg.get(lado, []) if p.dispo.get(r["_id"], CERO) > 0 and r["_id"] not in p.ambiguos]

    def _cmp(self, p: Pasada, r: dict, lado: str) -> Decimal:
        return r["_val"] * self._signo(p, lado)

    def _restante(self, p: Pasada, r: dict, lado: str) -> Decimal:
        """Saldo pendiente con su signo (comparable entre fuentes)."""
        v = self._cmp(p, r, lado)
        return p.dispo[r["_id"]] if v >= 0 else -p.dispo[r["_id"]]

    def _crear(self, p: Pasada, tipo: str, nivel: int, regla: str, a: list, b: list, *, clave=None, detalle=None, consumir=True,
               auto_ok=True, puntuacion=0):
        modalidad = f"{'1' if len(a) == 1 else 'N'}:{'1' if len(b) == 1 else 'N'}"
        estado = "AMBIGUA" if tipo == "AMBIGUA" else ("CONFIRMADA" if auto_ok and tipo in self.auto else "PROPUESTA")
        claves = frozenset([r["clave_registro"] for r, _ in a] + [r["clave_registro"] for r, _ in b])
        if estado == "PROPUESTA" and claves in self.rechazadas:
            return None  # el usuario ya rechazó esta misma propuesta
        fechas = [r["fecha"] for r, _ in a + b if r.get("fecha")]
        g = Grupo(p.nombre, tipo, modalidad, nivel, regla, estado, a, b, clave=clave, detalle=detalle or {}, puntuacion=puntuacion,
                  dias=(max(fechas) - min(fechas)).days if len(fechas) > 1 else None)
        if consumir:
            for r, m in a + b:
                p.dispo[r["_id"]] -= m
        p.grupos.append(g)
        return g

    def _verificaciones(self, p: Pasada, g: Grupo, regla: dict):
        """Comparaciones adicionales de la pareja: campos monetarios, fechas, periodos y monedas."""
        par = regla.get("parametros", {})
        for fa, fb, nombre, subtipo in par.get("comparar", []):
            va = sum((_num(valor(r, fa)) for r, _ in g.a), CERO)
            vb = sum((_num(valor(r, fb)) for r, _ in g.b), CERO) * self._signo(p, p.b)
            if va != vb:
                g.detalle.setdefault("campos", []).append({"nombre": nombre, "a": str(va), "b": str(vb), "diferencia": str(vb - va),
                                                            "subtipo": subtipo, "dentro_tolerancia": self.tol.dentro(vb - va, va)})
        dias = par.get("fecha_dias")
        if dias is not None and g.dias is not None and g.dias > dias:
            g.detalle["fuera_de_plazo"] = g.dias
        pa = {r.get("periodo") for r, _ in g.a if r.get("periodo")}
        pb = {r.get("periodo") for r, _ in g.b if r.get("periodo")}
        if pa and pb and pa != pb:
            g.detalle["periodos"] = [sorted(pa), sorted(x for x in pb if x)]
        ma, mb = {r["moneda"] for r, _ in g.a}, {r["moneda"] for r, _ in g.b}
        if ma != mb:
            g.detalle["monedas"] = [sorted(ma), sorted(mb)]

    # ---------------------------------------------------------------- reglas
    def regla_clave(self, p: Pasada, nivel: int, rg: dict):
        par = rg["parametros"]
        campos = par.get("campos", [])
        parcial = par.get("en_diferencia") == "PARCIAL"
        idx = {p.a: defaultdict(list), p.b: defaultdict(list)}
        for lado in (p.a, p.b):
            for r in self._pend(p, lado):
                k = clave_de(r, campos)
                if k:
                    idx[lado][k].append(r)
        for k, As in idx[p.a].items():
            Bs = idx[p.b].get(k)
            if not Bs:
                continue
            As = [r for r in As if p.dispo[r["_id"]] > 0]
            Bs = [r for r in Bs if p.dispo[r["_id"]] > 0]
            if not As or not Bs:
                continue
            ta = sum((self._restante(p, r, p.a) for r in As), CERO)
            tb = sum((self._restante(p, r, p.b) for r in Bs), CERO)
            dif = tb - ta
            etiqueta = " · ".join(k)
            ma = [(r, p.dispo[r["_id"]]) for r in As]
            mb = [(r, p.dispo[r["_id"]]) for r in Bs]
            if len(As) > 1 or len(Bs) > 1:
                if dif == 0 or self.tol.dentro(dif, ta):
                    g = self._crear(p, "EXACTA" if dif == 0 else "TOLERANCIA", nivel, rg["codigo"], ma, mb, clave=etiqueta)
                elif parcial and len(As) == 1 and (ta > 0) == (tb > 0) and abs(tb) < abs(ta):
                    g = self._crear(p, "PARCIAL", nivel, rg["codigo"], [(As[0], abs(tb))], mb, clave=etiqueta)
                    p.parciales.add(As[0]["_id"])
                else:
                    alternativas = [[r["_id"] for r in As], [r["_id"] for r in Bs]]
                    self._crear(p, "AMBIGUA", nivel, rg["codigo"], ma, mb, clave=etiqueta, consumir=False,
                                detalle={"alternativas": alternativas, "motivo": "Varios registros comparten la clave y los importes no cuadran"})
                    p.ambiguos |= {r["_id"] for r in As + Bs}
                    continue
            else:
                if dif == 0 or self.tol.dentro(dif, ta):
                    g = self._crear(p, "EXACTA" if dif == 0 else "TOLERANCIA", nivel, rg["codigo"], ma, mb, clave=etiqueta, puntuacion=100)
                elif parcial and (ta > 0) == (tb > 0):
                    m = min(abs(ta), abs(tb))
                    g = self._crear(p, "PARCIAL", nivel, rg["codigo"], [(As[0], m)], [(Bs[0], m)], clave=etiqueta, puntuacion=80)
                    p.parciales |= {As[0]["_id"] if abs(ta) > m else Bs[0]["_id"]}
                else:
                    g = self._crear(p, "DIFERENCIA", nivel, rg["codigo"], ma, mb, clave=etiqueta, puntuacion=70)
            if g:
                g.detalle["diferencia"] = str(dif)
                self._verificaciones(p, g, rg)

    def regla_importe_fecha(self, p: Pasada, nivel: int, rg: dict):
        par = rg["parametros"]
        dias = par.get("dias", self.tol.dias)
        extra = par.get("campos_extra", [])
        misma_moneda = par.get("misma_moneda", True)
        indice = defaultdict(list)
        for r in self._pend(p, p.b):
            k = (r["moneda"] if misma_moneda else "*", clave_de(r, extra) if extra else ())
            if extra and k[1] is None:
                continue
            indice[k].append((self._restante(p, r, p.b), r["_id"], r))
        for lst in indice.values():
            lst.sort(key=lambda x: (x[0], x[1]))
        cand_a, cand_b = {}, defaultdict(list)
        As = {r["_id"]: r for r in self._pend(p, p.a)}
        for aid, a in As.items():
            k = (a["moneda"] if misma_moneda else "*", clave_de(a, extra) if extra else ())
            lst = indice.get(k)
            if not lst:
                continue
            va = self._restante(p, a, p.a)
            t = self.tol.permitido(va)
            vals = [x[0] for x in lst]
            i, j = bisect.bisect_left(vals, va - t), bisect.bisect_right(vals, va + t)
            cs = [r for v, _, r in lst[i:j] if not (a.get("fecha") and r.get("fecha") and abs((a["fecha"] - r["fecha"]).days) > dias)]
            if cs:
                cand_a[aid] = cs
                for r in cs:
                    cand_b[r["_id"]].append(aid)
        for aid, cs in cand_a.items():
            a = As[aid]
            if p.dispo[aid] <= 0 or aid in p.ambiguos:
                continue
            cs = [r for r in cs if p.dispo[r["_id"]] > 0 and r["_id"] not in p.ambiguos]
            if not cs:
                continue
            if len(cs) == 1 and len([x for x in cand_b[cs[0]["_id"]] if p.dispo[x] > 0 and x not in p.ambiguos]) == 1:
                b = cs[0]
                va, vb = self._restante(p, a, p.a), self._restante(p, b, p.b)
                g = self._crear(p, "EXACTA" if va == vb else "TOLERANCIA", nivel, rg["codigo"], [(a, p.dispo[aid])], [(b, p.dispo[b["_id"]])],
                                puntuacion=90 if va == vb else 75)
                if g:
                    g.detalle["diferencia"] = str(vb - va)
                    self._verificaciones(p, g, rg)
            else:
                otros_a = sorted({x for r in cs for x in cand_b[r["_id"]] if p.dispo[x] > 0})
                self._crear(p, "AMBIGUA", nivel, rg["codigo"], [(As[x], p.dispo[x]) for x in otros_a], [(r, p.dispo[r["_id"]]) for r in cs],
                            consumir=False, detalle={"alternativas": [otros_a, [r["_id"] for r in cs]],
                                                     "motivo": "Varios registros con el mismo importe dentro de la ventana de fechas"})
                p.ambiguos |= set(otros_a) | {r["_id"] for r in cs}

    def regla_combinacion(self, p: Pasada, nivel: int, rg: dict):
        par = rg["parametros"]
        max_k, max_nodos, max_c = int(par.get("max_elementos", 4)), int(par.get("max_nodos", 20000)), int(par.get("max_candidatos", 20))
        dias = par.get("dias", self.tol.dias)
        agrupar = par.get("agrupar_por")
        for uno, varios in ((p.a, p.b), (p.b, p.a)):
            # índice por moneda y signo, ordenado por fecha: cada búsqueda revisa solo la ventana de días (no todos los pendientes)
            indice = defaultdict(list)
            for x in self._pend(p, varios):
                v = self._restante(p, x, varios)
                indice[(x["moneda"], v > 0)].append((x.get("fecha") or date.min, x["_id"], x))
            for lst in indice.values():
                lst.sort(key=lambda z: (z[0], z[1]))
            fechas = {k: [z[0] for z in lst] for k, lst in indice.items()}
            for r in self._pend(p, uno):
                if p.dispo[r["_id"]] <= 0 or r["_id"] in p.ambiguos:
                    continue
                objetivo = self._restante(p, r, uno)
                t = self.tol.permitido(objetivo)
                k = (r["moneda"], objetivo > 0)
                lst = indice.get(k)
                if not lst:
                    continue
                if r.get("fecha"):
                    i = bisect.bisect_left(fechas[k], r["fecha"] - timedelta(days=dias))
                    j = bisect.bisect_right(fechas[k], r["fecha"] + timedelta(days=dias))
                    ventana = lst[:bisect.bisect_right(fechas[k], date.min)] + lst[i:j]  # los registros sin fecha siempre se consideran
                else:
                    ventana = lst
                pool = []
                for _, xid, x in ventana:
                    if p.dispo[xid] <= 0 or xid in p.ambiguos:
                        continue
                    v = self._restante(p, x, varios)
                    if abs(v) > abs(objetivo) + t:
                        continue
                    if agrupar and clave_de(x, [agrupar]) != clave_de(r, [agrupar]):
                        continue
                    pool.append((abs((r["fecha"] - x["fecha"]).days) if r.get("fecha") and x.get("fecha") else 0, v, x))
                pool = sorted(pool, key=lambda z: (z[0], -abs(z[1])))[:max_c]
                if len(pool) < 2:
                    continue
                sol, nodos = [], [0]

                def dfs(i, acum, elegidos):
                    if nodos[0] > max_nodos or len(sol) >= 2:
                        return
                    nodos[0] += 1
                    if len(elegidos) >= 2 and abs(objetivo - acum) <= t:
                        sol.append(list(elegidos))
                        return
                    if len(elegidos) >= max_k:
                        return
                    for j in range(i, len(pool)):
                        v = pool[j][1]
                        if abs(acum + v) > abs(objetivo) + t:
                            continue
                        elegidos.append(pool[j])
                        dfs(j + 1, acum + v, elegidos)
                        elegidos.pop()
                dfs(0, CERO, [])
                if not sol:
                    continue
                miembros_r = [(r, p.dispo[r["_id"]])]
                if len(sol) == 1:
                    ms = [(x, p.dispo[x["_id"]]) for _, _, x in sol[0]]
                    a, b = (miembros_r, ms) if uno == p.a else (ms, miembros_r)
                    total = sum((v for _, v, _ in sol[0]), CERO)
                    g = self._crear(p, "EXACTA" if total == objetivo else "TOLERANCIA", nivel, rg["codigo"], a, b, auto_ok=False, puntuacion=60,
                                    detalle={"combinacion": True, "diferencia": str(total - objetivo)})
                    if g:
                        self._verificaciones(p, g, rg)
                else:
                    ids = sorted({x["_id"] for s in sol for _, _, x in s})
                    otros = [(x, p.dispo[x["_id"]]) for x in (z for _, _, z in pool) if x["_id"] in ids]
                    a, b = (miembros_r, otros) if uno == p.a else (otros, miembros_r)
                    self._crear(p, "AMBIGUA", nivel, rg["codigo"], a, b, consumir=False,
                                detalle={"alternativas": [[r["_id"]], [[x["_id"] for _, _, x in s] for s in sol]],
                                         "motivo": "Más de una combinación de registros suma el mismo importe"})
                    p.ambiguos |= {r["_id"]} | set(ids)

    def regla_agregado(self, p: Pasada, nivel: int, rg: dict):
        par = rg["parametros"]
        claves = par.get("claves", ["clave"])
        campos = par.get("campos", [{"nombre": "Importe", "campo": "importe"}])
        if not p.claves_reporte:
            p.claves_reporte = claves
        grupos = {p.a: defaultdict(list), p.b: defaultdict(list)}
        for lado in (p.a, p.b):
            for r in self._pend(p, lado):
                k = clave_de(r, claves)
                if k:
                    grupos[lado][k].append(r)
        for k, As in grupos[p.a].items():
            Bs = grupos[p.b].get(k)
            if not Bs:
                continue
            difs, max_dif = [], CERO
            for c in campos:
                va = sum((_num(valor(r, c["campo"])) for r in As), CERO)
                vb = sum((_num(valor(r, c["campo"])) for r in Bs), CERO) * self._signo(p, p.b)
                if va != vb:
                    difs.append({"nombre": c["nombre"], "campo": c["campo"], "a": str(va), "b": str(vb), "diferencia": str(vb - va),
                                 "subtipo": c.get("subtipo"), "dentro_tolerancia": self.tol.dentro(vb - va, va)})
                    max_dif = max(max_dif, abs(vb - va))
            tipo = "EXACTA" if not difs else ("TOLERANCIA" if all(x["dentro_tolerancia"] for x in difs) else "DIFERENCIA")
            g = self._crear(p, tipo if tipo != "EXACTA" else "AGREGADO", nivel, rg["codigo"], [(r, p.dispo[r["_id"]]) for r in As],
                            [(r, p.dispo[r["_id"]]) for r in Bs], clave=" · ".join(k), detalle={"campos": difs, "claves": claves},
                            auto_ok=tipo != "DIFERENCIA", puntuacion=100 if tipo == "EXACTA" else 70)
            if g and tipo == "EXACTA":
                g.estado = "CONFIRMADA"

    # ---------------------------------------------------------------- manuales previas
    def reaplicar(self, manuales: list[dict]):
        por_clave = {r["clave_registro"]: r for lst in self.reg.values() for r in lst}
        for m in manuales:
            p = next((x for x in self.pasadas if x.nombre == m["pasada"]), None)
            if not p:
                continue
            a = [(por_clave.get(k), Decimal(v)) for k, v in m["a"]]
            b = [(por_clave.get(k), Decimal(v)) for k, v in m["b"]]
            if any(r is None or p.dispo.get(r["_id"], CERO) < v for r, v in a + b):
                continue  # los registros cambiaron: la decisión no se re-aplica y se informa en el resumen
            g = self._crear(p, "MANUAL", 0, m.get("regla") or "MANUAL", a, b, auto_ok=False)
            if g:
                g.estado, g.origen, g.justificacion, g.usuario = "CONFIRMADA", "MANUAL", m.get("justificacion"), m.get("usuario", "?")
                g.detalle = m.get("detalle") or {}
                m["_reaplicada"] = True

    # ---------------------------------------------------------------- ejecución
    def ejecutar(self, pasadas_cfg: list[dict], reglas: list[dict], manuales: list[dict]):
        self.exclusiones(reglas)
        self.detectar_duplicados()
        for i, pc in enumerate(pasadas_cfg):
            p = Pasada(f"{pc['a']}-{pc['b']}", pc["a"], pc["b"], pc.get("modo", "PARTIDAS"), pc.get("signo", "IGUAL"))
            for lado in (p.a, p.b):
                for r in self.reg.get(lado, []):
                    if r["_id"] in self.excluidos or r["_id"] in self.duplicados:
                        continue
                    p.dispo[r["_id"]] = abs(r["_val"])
            if not self.reg.get(p.a) or not self.reg.get(p.b):
                p.omitida = f"La fuente {p.a if not self.reg.get(p.a) else p.b} no tiene registros"
            self.pasadas.append(p)
        self.reaplicar(manuales)
        for i, p in enumerate(self.pasadas):
            if p.omitida:
                continue
            for nivel, rg in enumerate([r for r in reglas if r["pasada"] == i and r["activa"]], start=1):
                if self.cancelar():
                    raise InterruptedError()
                self.avance(30 + int(40 * (i + nivel / 10) / max(len(self.pasadas), 1)), f"Pasada {p.nombre}: {rg['descripcion']}")
                fn = {"CLAVE": self.regla_clave, "IMPORTE_FECHA": self.regla_importe_fecha, "COMBINACION": self.regla_combinacion,
                      "AGREGADO": self.regla_agregado}.get(rg["tipo"])
                if fn:
                    fn(p, nivel, rg)


def huella_contenido(*partes) -> str:
    return hashlib.sha256(json.dumps(partes, sort_keys=True, default=str).encode()).hexdigest()

