"""Motor de compensación automática (analítica).

Partición: empresa · cuenta (o grupo de cuentas autorizado) · tercero · moneda. Nunca se cruzan
empresas, terceros ni monedas de forma automática.

Niveles de búsqueda (en orden):
  1. Documental exacta: la partida que cancela lleva la misma serie y número del documento.
  2. Referencias: documento de referencia, orden de compra/servicio, número en la glosa o mismo asiento.
  3. Importe: igualdad exacta o combinaciones (varios a uno / uno a varios) con límites de búsqueda.
  4. Fecha: solo suma puntos (proximidad); nunca basta por sí sola.
  5. Antigüedad (FIFO): solo si la política de la cuenta lo autoriza y la partida no tiene una
     referencia documental propia.

Puntuación 0–100 (calidad de la coincidencia, no una probabilidad). Se aprueba automáticamente solo
si la política lo permite, la coincidencia es inequívoca, la clasificación no está en duda y la
puntuación alcanza el umbral. Las ambiguas se guardan como candidatas que requieren decisión.
"""
import hashlib
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import bindparam, func, insert, select, update
from sqlalchemy.orm import Session

from app.analisis import saldos as saldos_f
from app.compensacion import partidas
from app.importers.normalizacion import normalizar_texto
from app.models import (Aplicacion, AprobacionCompensacion, AuditoriaCompensacion, CandidatoCompensacion,
                        EjecucionCompensacion, ExcepcionCompensacion, GrupoCompensacion, PartidaAbierta, SnapshotCompensacion)

CERO = Decimal("0")
C2 = Decimal("0.01")


class Cancelado(Exception):
    pass


class Conflicto(Exception):
    status = 409


def confianza(p: int) -> str:
    return "MUY_ALTA" if p >= 95 else "ALTA" if p >= 80 else "MEDIA" if p >= 60 else "BAJA"


@dataclass(eq=False)
class It:
    id: int
    cuenta: str
    tercero: str | None
    moneda: str
    rol: str
    clase: str
    serie: str | None
    numero: str | None
    ref: str | None
    oc: str | None
    proyecto: str | None
    glosa: str
    asiento: tuple | None
    fecha: date
    disponible: Decimal
    importe: Decimal
    importe_mn: Decimal
    pendiente_clase: bool
    origen_datos: str
    constancia: str | None
    retencion: str | None
    codigo_detraccion: str | None
    tipo_documento: str | None

    @property
    def doc(self) -> str | None:
        return f"{self.serie}-{self.numero}" if self.serie and self.numero else self.numero

    def mn_de(self, monto: Decimal) -> Decimal:
        return (self.importe_mn * monto / self.importe).quantize(C2, ROUND_HALF_UP) if self.importe else CERO


@dataclass
class Candidato:
    nivel: int
    origenes: list            # [(It, monto)]
    aplicaciones: list        # [(It, monto)]
    importe: Decimal
    componentes: dict
    puntuacion: int
    regla: str
    ambiguo: bool = False
    alternativas: list = field(default_factory=list)
    bloqueos: list = field(default_factory=list)  # motivos que impiden la aprobación automática


def _norm_doc(t: str | None) -> str:
    return re.sub(r"[^0-9A-Z]", "", normalizar_texto(t or ""))


def _dias(a: date, b: date) -> int:
    return abs((a - b).days)


def puntuar(nivel: int, origenes, aplicaciones, pesos: dict, *, cuenta_misma=True, exacto=True, referencias=False,
            ambiguo=False, penalizacion=25) -> tuple[int, dict]:
    o0, a0 = origenes[0][0], aplicaciones[0][0]
    comp = {"tercero": pesos["tercero"] if o0.tercero and o0.tercero == a0.tercero else 0,
            "documento": pesos["documento"] if nivel == 1 else (round(pesos["documento"] * 2 / 3) if nivel == 2 else 0),
            "moneda": pesos["moneda"] if o0.moneda == a0.moneda else 0,
            "importe": pesos["importe"] if exacto and len(origenes) == 1 and len(aplicaciones) == 1 else
            (round(pesos["importe"] * 0.8) if exacto else round(pesos["importe"] * 0.4)),
            "referencias": pesos["referencias"] if referencias or nivel in (1, 2) else 0,
            "cuenta": pesos["cuenta"] if cuenta_misma else round(pesos["cuenta"] / 2)}
    d = max(_dias(o.fecha, a.fecha) for o, _ in origenes for a, _ in aplicaciones)
    antes = any(a.fecha < o.fecha for o, _ in origenes for a, _ in aplicaciones)
    comp["fecha"] = 2 if antes else (pesos["fecha"] if d <= 30 else round(pesos["fecha"] * .6) if d <= 90
                                      else round(pesos["fecha"] * .3) if d <= 365 else 0)
    total = sum(comp.values())
    if ambiguo:
        comp["ambiguedad"] = -penalizacion
        total -= penalizacion
    return max(0, min(100, total)), comp


def _repartir(origenes: list[It], aplicaciones: list[It], dispo: dict) -> tuple[list, list, Decimal]:
    """Aplica en orden (fecha) hasta agotar lo disponible; devuelve montos por lado y total."""
    po, pa, total = [], [], CERO
    io = ia = 0
    resto_o = {o.id: dispo[o.id] for o in origenes}
    resto_a = {a.id: dispo[a.id] for a in aplicaciones}
    usados_o, usados_a = defaultdict(lambda: CERO), defaultdict(lambda: CERO)
    while io < len(origenes) and ia < len(aplicaciones):
        o, a = origenes[io], aplicaciones[ia]
        m = min(resto_o[o.id], resto_a[a.id])
        if m > 0:
            usados_o[o.id] += m
            usados_a[a.id] += m
            resto_o[o.id] -= m
            resto_a[a.id] -= m
            total += m
        if resto_o[o.id] <= 0:
            io += 1
        if resto_a[a.id] <= 0:
            ia += 1
    po = [(o, usados_o[o.id]) for o in origenes if usados_o[o.id] > 0]
    pa = [(a, usados_a[a.id]) for a in aplicaciones if usados_a[a.id] > 0]
    return po, pa, total


def _subconjuntos(objetivo: Decimal, items: list[It], dispo: dict, max_k: int, max_nodos: int, tol: Decimal, limite=2):
    """Combinaciones de 2..max_k partidas cuya suma disponible iguala el objetivo (±tolerancia).
    Devuelve hasta `limite` soluciones (2 basta para saber que es ambiguo)."""
    vals = sorted(((dispo[i.id], i) for i in items if dispo[i.id] > 0 and dispo[i.id] <= objetivo + tol),
                  key=lambda x: -x[0])
    sol, nodos = [], [0]

    def dfs(inicio, acum, elegidos):
        if nodos[0] > max_nodos or len(sol) >= limite:
            return
        nodos[0] += 1
        if len(elegidos) >= 2 and abs(acum - objetivo) <= tol:
            sol.append(list(elegidos))
            return
        if len(elegidos) >= max_k:
            return
        for j in range(inicio, len(vals)):
            v, it = vals[j]
            if acum + v > objetivo + tol:
                continue
            elegidos.append(it)
            dfs(j + 1, acum + v, elegidos)
            elegidos.pop()
            if len(sol) >= limite:
                return
    dfs(0, CERO, [])
    return sol, nodos[0] > max_nodos


# ------------------------------------------------------------------ búsqueda por partición
def buscar(origenes: list[It], aplicaciones: list[It], params: dict, cfg: partidas.Config, cuenta_misma: bool,
           regla_nombre: str) -> tuple[list[Candidato], list[dict]]:
    pesos, pen = params["pesos"], int(params.get("penalizacion_ambiguedad", 25))
    tol = Decimal(str(params.get("tolerancia", "0")))
    ventana = int(params.get("ventana_dias", 365))
    dispo = {i.id: i.disponible for i in origenes + aplicaciones}
    cands, obs = [], []

    def vivos(lista):
        return [i for i in lista if dispo[i.id] > 0]

    def registrar(nivel, os_, as_, *, exacto=True, referencias=False, regla=None):
        po, pa, total = _repartir(os_, as_, dispo)
        if total <= 0:
            return None
        p, comp = puntuar(nivel, po, pa, pesos, cuenta_misma=cuenta_misma, exacto=exacto, referencias=referencias, penalizacion=pen)
        c = Candidato(nivel, po, pa, total, comp, p, regla or regla_nombre)
        for it, m in po + pa:
            dispo[it.id] -= m
            if it.pendiente_clase:
                c.bloqueos.append(f"clasificación de la partida {it.id} pendiente de revisión")
        cands.append(c)
        return c

    def ambiguo(nivel, aplic: It, alternativas: list[list[It]], motivo):
        alt = [{"origenes": [x.id for x in grupo], "importe": str(sum((dispo[x.id] for x in grupo), CERO))} for grupo in alternativas]
        p, comp = puntuar(nivel, [(alternativas[0][0], dispo[alternativas[0][0].id])], [(aplic, dispo[aplic.id])], pesos,
                          cuenta_misma=cuenta_misma, ambiguo=True, penalizacion=pen)
        cands.append(Candidato(nivel, [(x, dispo[x.id]) for x in alternativas[0]], [(aplic, dispo[aplic.id])], dispo[aplic.id],
                               comp, p, regla_nombre, ambiguo=True, alternativas=alt, bloqueos=[motivo]))
        obs.append({"codigo": "AMBIGUA", "item": aplic, "titulo": f"Coincidencia ambigua ({motivo})",
                    "importe": dispo[aplic.id], "detalle": json.dumps(alt)})

    # ---- Nivel 1 y 2: documento exacto y referencias
    por_doc = defaultdict(list)
    por_num = defaultdict(list)
    for o in origenes:
        if o.numero:
            por_doc[(_norm_doc(o.serie), _norm_doc(o.numero))].append(o)
            por_num[_norm_doc(o.numero)].append(o)
    enlaces = defaultdict(list)  # origen → [(aplicacion, nivel)]
    ambiguas = set()
    for a in aplicaciones:
        destino, nivel = [], None
        if a.numero:
            destino = [o for o in por_doc.get((_norm_doc(a.serie), _norm_doc(a.numero)), []) if o is not a]
            nivel = 1 if destino else None
        if not destino and a.ref:
            r = _norm_doc(a.ref)
            destino = [o for o in origenes if o.numero and r in (_norm_doc(o.doc), _norm_doc(o.numero))]
            nivel = 2 if destino else None
        if not destino and a.oc:
            destino = [o for o in origenes if o.oc and o.oc == a.oc]
            nivel = 2 if destino else None
        if not destino and a.glosa:
            g = _norm_doc(a.glosa)
            destino = [o for o in origenes if o.serie and o.numero and _norm_doc(o.doc) in g]
            nivel = 2 if destino else None
        if not destino and a.asiento:
            destino = [o for o in origenes if o.asiento == a.asiento]
            nivel = 2 if len(destino) == 1 else None
            if len(destino) > 1:
                destino = []
        if len(destino) == 1:
            enlaces[destino[0]].append((a, nivel))
        elif len(destino) > 1:
            ambiguas.add(a.id)
            ambiguo(nivel or 1, a, [[o] for o in destino], "el mismo documento corresponde a varias partidas")
        elif a.numero and a.clase not in ("SALDO_INICIAL",) and not any(o.numero for o in origenes if _norm_doc(o.numero) == _norm_doc(a.numero)):
            obs.append({"codigo": "REFERENCIA_INEXISTENTE", "item": a, "importe": a.disponible,
                        "titulo": f"La partida referencia el documento {a.doc}, que no figura como pendiente del tercero"})
        if a.clase == "NOTA_CREDITO" and not a.ref and nivel != 1:
            obs.append({"codigo": "NC_SIN_REFERENCIA", "item": a, "importe": a.disponible,
                        "titulo": "Nota de crédito sin documento de referencia"})
    especiales = {"DETRACCION", "RETENCION", "PERCEPCION"}
    for o in sorted(enlaces, key=lambda x: (x.fecha, x.id)):
        lst = sorted(enlaces[o], key=lambda x: (x[0].fecha, x[0].id))
        normales = [a for a, _ in lst if a.clase not in especiales]
        nivel = min(n for _, n in lst)
        if normales:
            # el pago neto más los tributos vinculados al mismo documento cancelan su importe exacto
            exacto = sum(dispo[a.id] for a, _ in lst) == dispo[o.id]
            c = registrar(nivel, [o], normales, referencias=True, exacto=exacto)
            if c:
                c.regla = f"{regla_nombre} · N{nivel} documental"
        for a, n in lst:
            if a.clase in especiales:
                c = registrar(n, [o], [a], referencias=True, exacto=dispo[a.id] == dispo[o.id])
                if c:
                    c.regla = f"{regla_nombre} · {a.clase.lower()}"
                    _verificar_tributo(c, o, a, cfg, obs)

    # ---- Nivel 3: importe (exacto y combinaciones)
    max_k, max_c, max_n = int(params["max_combinacion"]), int(params["max_candidatos"]), int(params["max_nodos"])
    for a in sorted(vivos(aplicaciones), key=lambda x: (x.fecha, x.id)):
        if a.id in ambiguas or a.clase in especiales or a.origen_datos == "APERTURA_CONSOLIDADA" or not a.tercero:
            continue
        # el documento suele preceder a su cancelación; un anticipo, en cambio, precede a lo que cancela
        posibles = [o for o in vivos(origenes) if o.origen_datos != "APERTURA_CONSOLIDADA"
                    and (o.fecha <= a.fecha or "ANTICIPO" in (a.clase, o.clase)) and _dias(a.fecha, o.fecha) <= ventana]
        iguales = [o for o in posibles if abs(dispo[o.id] - dispo[a.id]) <= tol]
        if len(iguales) == 1:
            c = registrar(3, iguales, [a])
            if c:
                c.regla = f"{regla_nombre} · N3 importe"
            continue
        if len(iguales) > 1:
            ambiguas.add(a.id)
            ambiguo(3, a, [[o] for o in iguales], "varias partidas con el mismo importe")
            continue
        recientes = sorted(posibles, key=lambda x: (x.fecha, x.id), reverse=True)[:max_c]
        sol, cortado = _subconjuntos(dispo[a.id], recientes, dispo, max_k, max_n, tol)
        if len(sol) == 1:
            c = registrar(3, sorted(sol[0], key=lambda x: (x.fecha, x.id)), [a])
            if c:
                c.regla = f"{regla_nombre} · N3 combinación"
        elif len(sol) > 1:
            ambiguas.add(a.id)
            ambiguo(3, a, sol, "varias combinaciones de documentos suman el importe")
        if cortado:
            obs.append({"codigo": "LIMITE_BUSQUEDA", "item": a, "importe": dispo[a.id],
                        "titulo": "Se alcanzó el límite de combinaciones; revise manualmente"})
    for o in sorted(vivos(origenes), key=lambda x: (x.fecha, x.id)):
        if o.origen_datos == "APERTURA_CONSOLIDADA" or not o.tercero:
            continue
        posibles = sorted([a for a in vivos(aplicaciones) if a.id not in ambiguas and a.clase not in especiales
                           and a.fecha >= o.fecha and (a.fecha - o.fecha).days <= ventana], key=lambda x: (x.fecha, x.id))[:max_c]
        sol, _ = _subconjuntos(dispo[o.id], posibles, dispo, max_k, max_n, tol)
        if len(sol) == 1:
            c = registrar(3, [o], sorted(sol[0], key=lambda x: (x.fecha, x.id)))
            if c:
                c.regla = f"{regla_nombre} · N3 pagos parciales"

    # ---- Nivel 5: FIFO (solo con política autorizada)
    if params.get("fifo"):
        for a in sorted(vivos(aplicaciones), key=lambda x: (x.fecha, x.id)):
            if a.id in ambiguas or a.clase in especiales or a.clase == "NOTA_CREDITO" or a.pendiente_clase:
                continue
            if a.numero and a.clase not in ("SALDO_INICIAL",):
                continue  # tiene referencia documental propia: no se aplica por antigüedad
            pend = sorted([o for o in vivos(origenes) if o.fecha <= a.fecha], key=lambda x: (x.fecha, x.id))
            if pend:
                c = registrar(5, pend, [a], exacto=False)
                if c:
                    c.regla = f"{regla_nombre} · N5 antigüedad (FIFO)"
    # sobrantes
    for a in vivos(aplicaciones):
        if a.clase == "NOTA_CREDITO" and dispo[a.id] < a.disponible:
            obs.append({"codigo": "EXCEDENTE", "item": a, "importe": dispo[a.id],
                        "titulo": "Nota de crédito con saldo excedente después de aplicarse"})
    return cands, obs


def _verificar_tributo(c: Candidato, o: It, a: It, cfg: partidas.Config, obs: list):
    if a.clase == "DETRACCION":
        if not a.constancia:
            c.bloqueos.append("detracción sin número de constancia")
            obs.append({"codigo": "DETRACCION_SIN_CONSTANCIA", "item": a, "importe": a.disponible,
                        "titulo": "Detracción relacionada sin constancia de depósito"})
        reglas = [r for r in cfg.tasas.get("DETRACCION", []) if r["codigo"] == (a.codigo_detraccion or o.codigo_detraccion)]
        if reglas and "tasa" in reglas[0]:
            esperado = (o.importe * Decimal(str(reglas[0]["tasa"])) / 100).quantize(Decimal("1"), ROUND_HALF_UP)
            if abs(esperado - a.importe) > Decimal(str(reglas[0].get("tolerancia", "1"))):
                c.bloqueos.append(f"importe de detracción distinto del esperado ({esperado})")
                obs.append({"codigo": "DETRACCION_TASA", "item": a, "importe": a.importe,
                            "titulo": f"Detracción de {a.importe} vs {esperado} esperado ({reglas[0]['tasa']} % código {reglas[0]['codigo']})"})
        elif not reglas:
            c.bloqueos.append("sin tasa de detracción configurada para verificar el importe")
    elif a.clase == "RETENCION":
        if not (a.retencion or a.tipo_documento == "20" or a.serie):
            c.bloqueos.append("retención sin comprobante")
            obs.append({"codigo": "RETENCION_SIN_COMPROBANTE", "item": a, "importe": a.disponible,
                        "titulo": "Retención relacionada sin comprobante de retención"})
        reglas = cfg.tasas.get("RETENCION", [])
        if reglas and "tasa" in reglas[0]:
            esperado = (o.importe * Decimal(str(reglas[0]["tasa"])) / 100).quantize(C2, ROUND_HALF_UP)
            if abs(esperado - a.importe) > Decimal(str(reglas[0].get("tolerancia", "0.10"))):
                c.bloqueos.append(f"retención distinta de la esperada ({esperado})")
        else:
            c.bloqueos.append("sin tasa de retención configurada para verificar el importe")
    elif a.clase == "PERCEPCION":
        c.bloqueos.append("percepción: verificar su aplicación tributaria")
        obs.append({"codigo": "PERCEPCION_REVISION", "item": a, "importe": a.importe,
                    "titulo": "Percepción relacionada: verificar su tratamiento tributario"})


# ------------------------------------------------------------------ ejecución
def clave_idempotencia(empresa_id, corte, cuentas, version, reglas_v) -> str:
    return hashlib.sha256(f"{empresa_id}|{corte}|{','.join(sorted(cuentas))}|{version}|{reglas_v}".encode()).hexdigest()


def crear(db: Session, empresa_id: int, corte: date, usuario: str, cuentas: list[str] | None = None, forzar=False) -> tuple[EjecucionCompensacion, bool]:
    cfg = partidas.configuracion(db, empresa_id, corte)
    cuentas = sorted(cuentas or [c for c, p in cfg.cuentas.items() if p.get("activa", True)])
    en_curso = db.scalar(select(EjecucionCompensacion).where(EjecucionCompensacion.empresa_id == empresa_id,
                                                              EjecucionCompensacion.estado.in_(("EN_COLA", "PROCESANDO"))))
    if en_curso:
        raise Conflicto(f"Ya hay una compensación en curso para la empresa (#{en_curso.id}).")
    version = saldos_f.version_datos(db, empresa_id)
    reglas_v = json.dumps(cfg.reglas, sort_keys=True) + json.dumps(cfg.general, sort_keys=True, default=str) + \
        json.dumps([(x["id"], x["version"]) for x in cfg.entre_cuentas])
    clave = clave_idempotencia(empresa_id, corte, cuentas, version, reglas_v)
    previo = db.scalar(select(EjecucionCompensacion).where(EjecucionCompensacion.empresa_id == empresa_id,
                                                            EjecucionCompensacion.clave_idempotencia == clave,
                                                            EjecucionCompensacion.estado == "COMPLETADO")
                       .order_by(EjecucionCompensacion.id.desc()))
    if previo and not forzar:
        return previo, False  # idempotente: mismos datos, reglas y corte
    inicio = partidas.ejercicio_inicio(db, empresa_id, cfg) or corte.year
    run = EjecucionCompensacion(empresa_id=empresa_id, fecha_corte=corte, ejercicio_inicio=inicio, cuentas=",".join(cuentas),
                                clave_idempotencia=clave, version_datos=version, usuario=usuario,
                                reglas_snapshot=json.dumps({"cuentas": {c: cfg.cuentas[c] for c in cuentas if c in cfg.cuentas},
                                                            "versiones": cfg.reglas, "general": cfg.general,
                                                            "entre_cuentas": cfg.entre_cuentas}, default=str))
    db.add(run)
    db.flush()
    auditar(db, empresa_id, usuario, "EJECUTAR", "run", run.id, {"corte": corte.isoformat(), "cuentas": cuentas, "forzar": forzar})
    db.commit()
    return run, True


def auditar(db, empresa_id, usuario, accion, entidad, entidad_id=None, detalle=None, rol=None):
    db.add(AuditoriaCompensacion(empresa_id=empresa_id, usuario=usuario or "sistema", rol=rol, accion=accion, entidad=entidad,
                                 entidad_id=entidad_id, detalle=detalle if detalle is None or isinstance(detalle, str)
                                 else json.dumps(detalle, ensure_ascii=False, default=str)))


def ejecutar(db: Session, run_id: int, avance=lambda p, e: None) -> dict:
    run = db.get(EjecucionCompensacion, run_id)
    t0 = time.perf_counter()
    marca, tiempos, etapa = [t0], {}, ["Inicio"]

    def paso(pct, nombre):
        ahora = time.perf_counter()
        tiempos[etapa[0]] = int((ahora - marca[0]) * 1000)
        marca[0], etapa[0] = ahora, nombre
        if db.scalar(select(EjecucionCompensacion.cancelar).where(EjecucionCompensacion.id == run_id)):
            raise Cancelado()
        run.progreso, run.etapa, run.estado = pct, nombre, "PROCESANDO"
        db.commit()
        avance(pct, nombre)

    run.intentos = (run.intentos or 0) + 1
    try:
        res = _ejecutar(db, run, paso)
        tiempos[etapa[0]] = int((time.perf_counter() - marca[0]) * 1000)
        run.estado, run.progreso, run.etapa = "COMPLETADO", 100, "Completado"
        run.duracion_ms, run.tiempos, run.finalizado_en = int((time.perf_counter() - t0) * 1000), json.dumps(tiempos), datetime.now()
        db.commit()
        return res
    except Cancelado:
        db.rollback()
        run = db.get(EjecucionCompensacion, run_id)
        run.estado, run.etapa, run.finalizado_en = "CANCELADO", "Cancelado por el usuario", datetime.now()
        db.commit()
        raise
    except Exception as exc:
        db.rollback()
        run = db.get(EjecucionCompensacion, run_id)
        run.estado, run.error, run.finalizado_en = "ERROR", str(exc)[:2000], datetime.now()
        db.commit()
        raise


def _items(db, empresa_id, corte, cuentas) -> list[It]:
    q = select(PartidaAbierta).where(PartidaAbierta.empresa_id == empresa_id, PartidaAbierta.vigente.is_(True),
                                     PartidaAbierta.fecha_contable <= corte, PartidaAbierta.clase != "DIFERENCIA_CAMBIO",
                                     func.round(PartidaAbierta.importe - PartidaAbierta.importe_comprometido, 2) > 0)
    out = []
    for p in db.scalars(q):
        if not any(p.cuenta.startswith(c) for c in cuentas):
            continue
        out.append(It(p.id, p.cuenta, p.tercero, p.moneda, p.rol, p.clase, p.serie, p.numero, p.documento_referencia,
                      p.orden_compra_servicio, p.proyecto, p.glosa or "",
                      (p.lote_id, p.periodo, p.subdiario or "", p.numero_asiento) if p.numero_asiento else None,
                      p.fecha_contable, (p.importe - p.importe_comprometido).quantize(C2), p.importe, p.importe_mn,
                      p.clasificacion_pendiente and p.origen_datos != "APERTURA_CONSOLIDADA", p.origen_datos,
                      p.constancia_detraccion, p.retencion, p.codigo_detraccion, p.tipo_documento))
    return out


def _ejecutar(db: Session, run: EjecucionCompensacion, paso) -> dict:
    e, corte = run.empresa_id, run.fecha_corte
    cuentas = run.cuentas.split(",")
    cfg = partidas.configuracion(db, e, corte)
    paso(5, "Construyendo partidas desde el libro")
    construccion = partidas.construir(db, e, cfg, corte.year, lambda p, t: None)
    paso(30, "Retirando propuestas automáticas anteriores no aprobadas")
    retiradas = 0
    for g in db.scalars(select(GrupoCompensacion).where(GrupoCompensacion.empresa_id == e, GrupoCompensacion.estado == "PROPUESTA",
                                                        GrupoCompensacion.origen_propuesta == "AUTOMATICA")):
        _liberar(db, g, "RECHAZADA", aplicado=False)
        g.estado = "RECHAZADA"
        db.add(AprobacionCompensacion(empresa_id=e, grupo_id=g.id, accion="RECHAZAR", usuario="motor",
                                      comentario=f"Reemplazada por la ejecución #{run.id}"))
        retiradas += 1
    db.commit()
    paso(35, "Buscando coincidencias")
    items = _items(db, e, corte, cuentas)
    particiones = defaultdict(lambda: ([], []))
    grupo_cuentas = {}
    for regla in cfg.entre_cuentas:
        for c in regla.get("cuentas", []):
            grupo_cuentas[c] = regla
    for it in items:
        regla_ec = next((r for c, r in grupo_cuentas.items() if it.cuenta.startswith(c)), None)
        clave_cta = f"R{regla_ec['id']}" if regla_ec else it.cuenta
        o, a = particiones[(clave_cta, it.tercero, it.moneda)]
        (o if it.rol == "ORIGEN" else a).append(it)
    todos, obs = [], []
    total = max(len(particiones), 1)
    for n, ((clave_cta, tercero, moneda), (o, a)) in enumerate(particiones.items()):
        if n % 500 == 0:
            paso(35 + int(35 * n / total), f"Buscando coincidencias ({n}/{len(particiones)} grupos)")
        if not o and not a:
            continue
        cuenta_ref = (o or a)[0].cuenta
        pref = cfg.regla_de(cuenta_ref)
        params = cfg.cuentas.get(pref, partidas.PARAMETROS_CUENTA)
        cands, ob = buscar(sorted(o, key=lambda x: (x.fecha, x.id)), sorted(a, key=lambda x: (x.fecha, x.id)), params, cfg,
                           not clave_cta.startswith("R"), f"Cuenta {pref}")
        for c in cands:
            c.params, c.pref, c.version = params, pref, cfg.reglas.get(pref, {}).get("version")
            c.entre = clave_cta.startswith("R")
        todos += cands
        obs += ob
    paso(72, f"Registrando {len(todos)} coincidencias")
    stats = _persistir(db, run, todos)
    paso(85, "Registrando observaciones")
    stats["observaciones_nuevas"] = _observaciones(db, run, obs, corte)
    paso(92, "Guardando la composición del saldo a la fecha de corte")
    comp = partidas.composicion(db, e, corte, cuentas=cuentas, incluir_propuestas=True)
    filas = [{"run_id": run.id, "empresa_id": e, "item_id": x.item["id"], "fecha_corte": corte, "cuenta": x.item["cuenta"],
              "tercero": x.item["tercero"], "rol": x.item["rol"], "moneda": x.item["moneda"], "importe": x.item["importe"],
              "aplicado": x.aplicado, "pendiente": x.pendiente, "pendiente_mn": x.pendiente_mn, "estado_cancelacion": x.cancelacion,
              "estado_vencimiento": x.vencimiento, "dias_vencido": x.dias} for x in comp]
    for i in range(0, len(filas), 5000):
        db.execute(insert(SnapshotCompensacion), filas[i:i + 5000])
    conc = partidas.conciliacion(db, e, corte)
    resumen = {**stats, "construccion": construccion, "propuestas_retiradas": retiradas, "partidas": len(comp),
               "partidas_pendientes": sum(1 for x in comp if x.pendiente > 0),
               "conciliado": conc["conciliado"], "diferencia_conciliacion": conc["totales"]["diferencia"]}
    run.resumen = json.dumps(resumen, default=str)
    db.commit()
    return {"run_id": run.id, "resumen": resumen}


def _sentencia_ajuste():
    t = PartidaAbierta.__table__
    comp = func.round(t.c.importe_comprometido + bindparam("d_comp", type_=t.c.importe.type), 2)
    apl = func.round(t.c.importe_aplicado + bindparam("d_apl", type_=t.c.importe.type), 2)
    return (update(t).where(t.c.id == bindparam("p_id"), t.c.empresa_id == bindparam("p_emp"), t.c.vigente.is_(True),
                            comp <= t.c.importe, comp >= 0, apl >= 0, apl <= comp)
            .values(importe_comprometido=comp, importe_aplicado=apl, version=t.c.version + 1))


_AJUSTE = _sentencia_ajuste()


def _ajustar(db, item_id: int, empresa_id: int, comprometido: Decimal, aplicado: Decimal):
    """UPDATE condicional (control optimista): nunca deja la partida sobreaplicada ni negativa.
    La sentencia se compila una sola vez (Core) para que el registro masivo no pague su construcción en cada llamada."""
    r = db.connection().execute(_AJUSTE, {"p_id": item_id, "p_emp": empresa_id, "d_comp": comprometido, "d_apl": aplicado})
    if r.rowcount != 1:
        raise Conflicto(f"La partida {item_id} no tiene saldo disponible suficiente o fue modificada por otro usuario.")
    cargada = db.identity_map.get(db.identity_key(PartidaAbierta, item_id))
    if cargada is not None:  # evita leer importes desactualizados en la misma sesión
        db.expire(cargada, ["importe_comprometido", "importe_aplicado", "version"])


def _liberar(db, g: GrupoCompensacion, nuevo_estado: str, aplicado: bool, reversion_id=None):
    for a in db.scalars(select(Aplicacion).where(Aplicacion.grupo_id == g.id, Aplicacion.estado.in_(("PROPUESTA", "APROBADA")))):
        menos_apl = -a.importe if aplicado and a.estado == "APROBADA" else CERO
        _ajustar(db, a.origen_item_id, g.empresa_id, -a.importe, menos_apl)
        _ajustar(db, a.aplicacion_item_id, g.empresa_id, -a.importe, menos_apl)
        a.estado = nuevo_estado
        if reversion_id:
            a.reversion_id = reversion_id


def modalidad(n_o: int, n_a: int, parcial: bool) -> str:
    base = "UNO_A_UNO" if n_o == 1 and n_a == 1 else "UNO_A_VARIOS" if n_o == 1 else "VARIOS_A_UNO" if n_a == 1 else "VARIOS_A_VARIOS"
    return base + ("_PARCIAL" if parcial else "")


def crear_grupo(db, *, empresa_id, run_id, origenes, aplicaciones, regla, version, nivel, puntuacion, componentes, ambiguo,
                propuesto_por, origen_propuesta, aprobar: bool, justificacion=None, entre_cuentas=False, entre_terceros=False,
                tipo_cambio=None, aprobador=None) -> GrupoCompensacion:
    """Crea el grupo y sus aplicaciones validando disponibilidad (transaccional y con control optimista)."""
    pares = []
    io = ia = 0
    ro = [[it, m] for it, m in origenes]
    ra = [[it, m] for it, m in aplicaciones]
    while io < len(ro) and ia < len(ra):
        m = min(ro[io][1], ra[ia][1])
        if m > 0:
            pares.append((ro[io][0], ra[ia][0], m))
            ro[io][1] -= m
            ra[ia][1] -= m
        if ro[io][1] <= 0:
            io += 1
        if ra[ia][1] <= 0:
            ia += 1
    total = sum((m for *_, m in pares), CERO)
    fechas = [it.fecha for it, _ in origenes] + [it.fecha for it, _ in aplicaciones]
    parcial = any(it.disponible - sum((m for o, a, m in pares if it in (o, a)), CERO) > 0 for it, _ in origenes + aplicaciones)
    o0 = origenes[0][0]
    g = GrupoCompensacion(
        empresa_id=empresa_id, run_id=run_id, modalidad=modalidad(len(origenes), len(aplicaciones), parcial),
        origen_propuesta=origen_propuesta, nivel=nivel, regla=regla[:80], regla_version=version, puntuacion=puntuacion,
        confianza=confianza(puntuacion), componentes=json.dumps(componentes), ambiguo=ambiguo,
        cuenta=",".join(sorted({it.cuenta for it, _ in origenes + aplicaciones}))[:60],
        tercero=",".join(sorted({it.tercero or "-" for it, _ in origenes + aplicaciones}))[:80], moneda=o0.moneda,
        importe=total, fecha_efectiva=max(fechas), estado="APROBADA" if aprobar else "PROPUESTA",
        justificacion=justificacion, propuesto_por=propuesto_por, aprobado_por=(aprobador or propuesto_por) if aprobar else None,
        aprobado_en=datetime.now() if aprobar else None, entre_cuentas=entre_cuentas, entre_terceros=entre_terceros)
    db.add(g)
    db.flush()
    def en_moneda(it, m):  # importe expresado en la moneda propia de la partida (conversión autorizada)
        if it.moneda == o0.moneda or not tipo_cambio:
            return m
        return (m * tipo_cambio if it.moneda == "PEN" else m / tipo_cambio).quantize(C2, ROUND_HALF_UP)

    acumulado = defaultdict(lambda: CERO)
    filas = []
    for o, a, m in pares:
        acumulado[o.id] += en_moneda(o, m)
        acumulado[a.id] += en_moneda(a, m)
        mn_o = o.mn_de(en_moneda(o, m))
        mn_a = a.mn_de(en_moneda(a, m))
        filas.append({"empresa_id": empresa_id, "grupo_id": g.id, "origen_item_id": o.id, "aplicacion_item_id": a.id, "importe": m,
                      "moneda": o.moneda, "tipo_cambio": tipo_cambio, "importe_mn_origen": mn_o, "importe_mn_aplicacion": mn_a,
                      "diferencia_cambio": (mn_a - mn_o) if (o.moneda != "PEN" or a.moneda != "PEN") else CERO, "fecha_efectiva": max(o.fecha, a.fecha),
                      "regla": regla[:80], "puntuacion": puntuacion, "usuario": propuesto_por,
                      "estado": "APROBADA" if aprobar else "PROPUESTA"})
    for item_id, m in acumulado.items():
        _ajustar(db, item_id, empresa_id, m, m if aprobar else CERO)
    db.execute(insert(Aplicacion), filas)
    if aprobar:
        db.add(AprobacionCompensacion(empresa_id=empresa_id, grupo_id=g.id, accion="AUTOAPROBAR" if origen_propuesta == "AUTOMATICA" else "APROBAR",
                                      usuario=aprobador or propuesto_por, comentario="Política de aprobación automática" if origen_propuesta == "AUTOMATICA" else None))
    return g


def _persistir(db, run, cands: list[Candidato], bloque: int = 500) -> dict:
    """Registra los candidatos. Se trabaja por bloques dentro de un punto de guardado; si algún grupo del bloque choca
    con una operación concurrente (control optimista), el bloque se deshace y se reprocesa grupo a grupo."""
    stats = defaultdict(int)
    importe_aprobado = [CERO]
    filas_c = []
    decisiones: dict[int, tuple] = {}

    def auto_de(c):
        return bool(c.params.get("autoaprobar")) and c.puntuacion >= int(c.params.get("umbral_auto", 95)) and not c.bloqueos \
            and not c.entre and c.nivel <= 3

    def registrar(c):
        auto = auto_de(c)
        g = crear_grupo(db, empresa_id=run.empresa_id, run_id=run.id, origenes=c.origenes, aplicaciones=c.aplicaciones,
                        regla=c.regla, version=c.version, nivel=c.nivel, puntuacion=c.puntuacion,
                        componentes={**c.componentes, "bloqueos": c.bloqueos}, ambiguo=False, propuesto_por="motor",
                        origen_propuesta="AUTOMATICA", aprobar=auto, entre_cuentas=c.entre)
        return g.id, auto

    validos = [c for c in cands if not c.ambiguo]
    for i in range(0, len(validos), bloque):
        lote = validos[i:i + bloque]
        try:
            with db.begin_nested():
                res = [registrar(c) for c in lote]
            for c, r in zip(lote, res):
                decisiones[id(c)] = r
        except Conflicto:
            for c in lote:
                try:
                    with db.begin_nested():
                        decisiones[id(c)] = registrar(c)
                except Conflicto:
                    decisiones[id(c)] = None
    for c in cands:
        decision, grupo_id = "REQUIERE_DECISION", None
        if c.ambiguo:
            stats["ambiguas"] += 1
        elif decisiones.get(id(c)) is None:
            decision = "DESCARTADO"
            stats["conflictos"] += 1
        else:
            grupo_id, auto = decisiones[id(c)]
            decision = "AUTOAPROBADO" if auto else "PROPUESTO"
            stats["autoaprobadas" if auto else "propuestas"] += 1
            if auto:
                importe_aprobado[0] += c.importe
            stats[f"nivel_{c.nivel}"] += 1
        filas_c.append({"run_id": run.id, "empresa_id": run.empresa_id, "nivel": c.nivel,
                        "origenes": json.dumps([{"item_id": it.id, "importe": str(m)} for it, m in c.origenes]),
                        "aplicaciones": json.dumps([{"item_id": it.id, "importe": str(m)} for it, m in c.aplicaciones]),
                        "importe": c.importe, "puntuacion": c.puntuacion,
                        "componentes": json.dumps({**c.componentes, "bloqueos": c.bloqueos, "alternativas": c.alternativas}),
                        "ambiguo": c.ambiguo, "alternativas": len(c.alternativas), "decision": decision, "grupo_id": grupo_id,
                        "cuenta": c.origenes[0][0].cuenta, "tercero": c.origenes[0][0].tercero, "moneda": c.origenes[0][0].moneda})
    for i in range(0, len(filas_c), 2000):
        db.execute(insert(CandidatoCompensacion), filas_c[i:i + 2000])
    db.commit()
    return {**stats, "importe_autoaprobado": str(importe_aprobado[0]), "candidatos": len(cands)}


def _observaciones(db, run, obs, corte) -> int:
    existentes = set(db.scalars(select(ExcepcionCompensacion.huella).where(ExcepcionCompensacion.empresa_id == run.empresa_id)))
    nuevas = []
    for o in obs:
        it = o["item"]
        h = hashlib.sha256(f"{o['codigo']}|{it.id}".encode()).hexdigest()
        if h in existentes:
            continue
        existentes.add(h)
        nuevas.append({"empresa_id": run.empresa_id, "run_id": run.id, "item_id": it.id, "codigo": o["codigo"], "titulo": o["titulo"][:255],
                       "detalle": o.get("detalle"), "importe": Decimal(o.get("importe") or 0).quantize(C2), "huella": h, "estado": "ABIERTA"})
    # diferencias de cambio pendientes de evaluación y saldos sin detalle
    for x in partidas.composicion(db, run.empresa_id, corte, incluir_propuestas=False):
        it = x.item
        if it["origen_datos"] == "APERTURA_CONSOLIDADA" and x.pendiente > 0:
            h = hashlib.sha256(f"SALDO_SIN_DETALLE|{it['id']}".encode()).hexdigest()
            if h not in existentes:
                existentes.add(h)
                nuevas.append({"empresa_id": run.empresa_id, "run_id": run.id, "item_id": it["id"], "codigo": "SALDO_SIN_DETALLE",
                               "titulo": "Saldo inicial pendiente de desagregación por documento", "detalle": None,
                               "importe": x.pendiente, "huella": h, "estado": "ABIERTA"})
        if it["clasificacion_pendiente"] and it["origen_datos"] != "APERTURA_CONSOLIDADA":
            h = hashlib.sha256(f"CLASIFICACION|{it['id']}".encode()).hexdigest()
            if h not in existentes:
                existentes.add(h)
                nuevas.append({"empresa_id": run.empresa_id, "run_id": run.id, "item_id": it["id"], "codigo": "CLASIFICACION_AMBIGUA",
                               "titulo": f"Clasificación pendiente de revisión ({it['clase']}): {it['clase_motivo']}"[:255],
                               "detalle": None, "importe": it["importe"], "huella": h, "estado": "ABIERTA"})
    # diferencias de cambio por aplicaciones en ME sin registro en MN
    for a in db.execute(select(Aplicacion.grupo_id, func.sum(Aplicacion.diferencia_cambio)).where(
            Aplicacion.empresa_id == run.empresa_id, Aplicacion.estado == "APROBADA", Aplicacion.moneda != "PEN")
            .group_by(Aplicacion.grupo_id)):
        if a[1] and Decimal(str(a[1])):
            h = hashlib.sha256(f"DIF_CAMBIO|{a[0]}".encode()).hexdigest()
            if h not in existentes:
                existentes.add(h)
                nuevas.append({"empresa_id": run.empresa_id, "run_id": run.id, "item_id": None, "grupo_id": a[0],
                               "codigo": "DIFERENCIA_CAMBIO", "titulo": "Diferencia de cambio entre emisión y cancelación pendiente de evaluación",
                               "detalle": None, "importe": abs(Decimal(str(a[1]))).quantize(C2), "huella": h, "estado": "ABIERTA"})
    for f in nuevas:
        f.setdefault("grupo_id", None)
    if nuevas:
        db.execute(insert(ExcepcionCompensacion), nuevas)
    db.commit()
    return len(nuevas)
