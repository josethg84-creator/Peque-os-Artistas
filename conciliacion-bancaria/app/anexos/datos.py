"""Contexto de datos de una generación de anexos.

Carga UNA vez (por generación) las líneas del libro del ejercicio hasta la fecha de corte, los saldos
iniciales, el balance de comprobación importado y, cuando se necesitan, la composición de partidas de
la fase 4, los estados bancarios de la fase 1, los registros auxiliares y los sustentos adjuntos.
Nada de esto se modifica: es una lectura.
"""
import calendar
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.analisis import pcge, saldos
from app.models import (AdjuntoAnexo, Aplicacion, CentroCosto, CuentaContable, LineaDiario, LoteContable, PartidaAbierta,
                        RegistroAuxiliar, SaldoCuenta)

CERO = Decimal("0")
C2 = Decimal("0.01")


def fin_de_periodo(ejercicio: int, periodo: int) -> date:
    m = min(max(periodo, 1), 12)
    return date(ejercicio, m, calendar.monthrange(ejercicio, m)[1])


class L(NamedTuple):
    id: int
    lote_id: int
    periodo: int | None
    fecha: date | None
    vencimiento: date | None
    subdiario: str | None
    asiento: str | None
    cuenta: str
    tercero: str | None
    razon_social: str | None
    tipo_doc: str | None
    serie: str | None
    numero: str | None
    glosa: str | None
    moneda: str
    tipo_cambio: Decimal | None
    debe: int        # céntimos MN
    haber: int
    debe_me: int     # céntimos ME
    haber_me: int
    cc: str | None
    proyecto: str | None
    maquinaria: str | None
    referencia: str | None
    orden: str | None

    @property
    def neto(self) -> int:
        return self.debe - self.haber

    @property
    def neto_me(self) -> int:
        return self.debe_me - self.haber_me

    @property
    def doc(self) -> str | None:
        if not self.numero:
            return None
        return f"{self.serie}-{self.numero}" if self.serie else self.numero

    @property
    def clave_asiento(self):
        return (self.lote_id, self.periodo, self.subdiario or "", self.asiento) if self.asiento else None

    @property
    def etiqueta_asiento(self) -> str | None:
        return "-".join(p for p in (self.subdiario, self.asiento) if p) or None


_COLS = (LineaDiario.id, LineaDiario.lote_id, LineaDiario.periodo, LineaDiario.fecha_contable, LineaDiario.fecha_vencimiento,
         LineaDiario.subdiario, LineaDiario.numero_asiento, LineaDiario.cuenta, LineaDiario.documento_tercero,
         LineaDiario.razon_social, LineaDiario.tipo_documento, LineaDiario.serie, LineaDiario.numero_documento,
         LineaDiario.glosa, LineaDiario.moneda, LineaDiario.tipo_cambio, LineaDiario.debe_mn, LineaDiario.haber_mn,
         LineaDiario.debe_me, LineaDiario.haber_me, LineaDiario.centro_costo, LineaDiario.proyecto,
         LineaDiario.activo_maquinaria, LineaDiario.documento_referencia, LineaDiario.orden_compra_servicio)


def _c(v) -> int:
    return int((Decimal(str(v or 0)) * 100).to_integral_value())


def dec(c: int) -> Decimal:
    return (Decimal(int(c or 0)) / 100).quantize(C2)


@dataclass
class Filtros:
    centro_costo: str | None = None
    proyecto: str | None = None
    unidad_negocio: str | None = None
    moneda: str | None = None

    def activos(self) -> bool:
        return any((self.centro_costo, self.proyecto, self.unidad_negocio, self.moneda))

    def como_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}


@dataclass
class Ctx:
    db: Session
    empresa_id: int
    ejercicio: int
    periodo: int
    corte: date
    filtros: Filtros = field(default_factory=Filtros)
    f: saldos.Fuentes | None = None
    plan: dict = field(default_factory=dict)
    lineas: list = field(default_factory=list)
    por_cuenta: dict = field(default_factory=dict)        # cuenta → [L]
    apertura: dict = field(default_factory=dict)          # cuenta → céntimos (saldos iniciales importados)
    apertura_ter: dict = field(default_factory=dict)      # (cuenta, tercero|None) → céntimos
    apertura_me: dict = field(default_factory=dict)       # cuenta → céntimos ME
    advertencias: list = field(default_factory=list)
    version_datos: str = ""
    _asientos: dict | None = None
    _comp: dict | None = None
    _comp_version: str | None = None
    _aplic_clase: dict | None = None
    _adjuntos: dict | None = None
    _registros: dict = field(default_factory=dict)
    _balance_importado: dict | None = None
    _centros: dict | None = None

    # ------------------------------------------------------------ carga
    def cargar(self) -> "Ctx":
        db = self.db
        self.f = saldos.fuentes(db, self.empresa_id, self.ejercicio)
        self.plan = {c.codigo: c for c in db.scalars(select(CuentaContable).where(CuentaContable.empresa_id == self.empresa_id))}
        self.version_datos = saldos.version_datos(db, self.empresa_id)
        self.advertencias = list(self.f.advertencias)
        diario00 = self.f.apertura == "DIARIO_00"
        filtro = self.f.filtro_lineas(0 if diario00 else 1, self.periodo, incluir_apertura_diario=diario00)
        q = select(*_COLS).where(filtro, or_(LineaDiario.fecha_contable.is_(None), LineaDiario.fecha_contable <= self.corte,
                                             LineaDiario.periodo == 0))
        fl = self.filtros
        if fl.centro_costo:
            q = q.where(LineaDiario.centro_costo == fl.centro_costo)
        if fl.proyecto:
            q = q.where(LineaDiario.proyecto == fl.proyecto)
        if fl.moneda:
            q = q.where(LineaDiario.moneda == fl.moneda)
        if fl.unidad_negocio:
            ccs = [c for c, u in self.centros().items() if u == fl.unidad_negocio]
            q = q.where(LineaDiario.centro_costo.in_(ccs or ["\x00"]))
        por = defaultdict(list)
        lineas = []
        for r in db.execute(q.order_by(LineaDiario.id)).yield_per(10000):
            ln = L(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12], r[13], r[14] or "PEN",
                   r[15], _c(r[16]), _c(r[17]), _c(r[18]), _c(r[19]), r[20], r[21], r[22], r[23], r[24])
            lineas.append(ln)
            por[ln.cuenta].append(ln)
        self.lineas, self.por_cuenta = lineas, por
        if self.f.apertura == "SALDOS_INICIALES" and not fl.activos():
            for c, t, mon, d, h, dme, hme in db.execute(
                    select(SaldoCuenta.cuenta, SaldoCuenta.documento_tercero, SaldoCuenta.moneda,
                           func.sum(SaldoCuenta.saldo_inicial_debe), func.sum(SaldoCuenta.saldo_inicial_haber),
                           func.sum(SaldoCuenta.saldo_me_debe), func.sum(SaldoCuenta.saldo_me_haber))
                    .where(SaldoCuenta.lote_id.in_(self.f.lotes_apertura))
                    .group_by(SaldoCuenta.cuenta, SaldoCuenta.documento_tercero, SaldoCuenta.moneda)):
                v = _c(d) - _c(h)
                self.apertura[c] = self.apertura.get(c, 0) + v
                self.apertura_ter[(c, t or None)] = self.apertura_ter.get((c, t or None), 0) + v
                if mon and mon != "PEN":
                    self.apertura_me[c] = self.apertura_me.get(c, 0) + _c(dme) - _c(hme)
        elif fl.activos() and self.f.apertura == "SALDOS_INICIALES":
            self.advertencias.append("Con filtros de centro de costo, proyecto, unidad o moneda los saldos iniciales importados "
                                     "no se pueden asignar: el anexo muestra solo los movimientos filtrados.")
        if self.f.apertura == "NINGUNA":
            self.advertencias.append("Sin saldos iniciales ni asiento de apertura: los saldos son preliminares.")
        return self

    # ------------------------------------------------------------ consultas en memoria
    def centros(self) -> dict:
        if self._centros is None:
            self._centros = {c.codigo: c.unidad_negocio for c in self.db.scalars(
                select(CentroCosto).where(CentroCosto.empresa_id == self.empresa_id))}
        return self._centros

    def hojas(self) -> list[str]:
        """Cuentas con información (líneas o saldo inicial)."""
        return sorted(set(self.por_cuenta) | {c for c, v in self.apertura.items() if v})

    def de(self, prefijo: str) -> list[L]:
        out = []
        for c, ls in self.por_cuenta.items():
            if c.startswith(prefijo):
                out.extend(ls)
        return out

    def es_apertura(self, ln: L) -> bool:
        return ln.periodo == 0

    def saldos_de(self, prefijo: str) -> dict:
        """Saldo inicial, debe, haber y final (céntimos, deudor positivo) de la cuenta (con sus subcuentas)."""
        si = sum(v for c, v in self.apertura.items() if c.startswith(prefijo))
        d = h = n = 0
        si_me = sum(v for c, v in self.apertura_me.items() if c.startswith(prefijo))
        mov_me = 0
        for ln in self.de(prefijo):
            mov_me += ln.neto_me
            if ln.periodo == 0:
                si += ln.neto
                continue
            d += ln.debe
            h += ln.haber
            n += 1
        return {"si": si, "debe": d, "haber": h, "sf": si + d - h, "n": n, "sf_me": si_me + mov_me}

    def naturaleza(self, cuenta: str) -> str:
        p = self.plan.get(cuenta)
        if p and p.naturaleza in ("D", "A"):
            return p.naturaleza
        for k in range(len(cuenta) - 1, 0, -1):
            p = self.plan.get(cuenta[:k])
            if p and p.naturaleza in ("D", "A"):
                return p.naturaleza
        return pcge.naturaleza_pcge(cuenta) or "D"

    def descripcion(self, cuenta: str) -> str | None:
        """Descripción del plan importado o del PCGE; si la analítica no figura, la del ancestro más cercano."""
        for k in range(len(cuenta), 0, -1):
            p = self.plan.get(cuenta[:k])
            d = (p.descripcion if p else None) or pcge.nombre_pcge(cuenta[:k])
            if d:
                return d
        return None

    def asientos(self) -> dict:
        if self._asientos is None:
            a = defaultdict(list)
            for ln in self.lineas:
                if ln.clave_asiento:
                    a[ln.clave_asiento].append(ln)
            self._asientos = a
        return self._asientos

    def contrapartidas(self, ln: L) -> list[L]:
        if not ln.clave_asiento:
            return []
        return [x for x in self.asientos().get(ln.clave_asiento, []) if x.id != ln.id and (x.neto > 0) != (ln.neto > 0)]

    # ------------------------------------------------------------ balance de comprobación importado
    def balance_importado(self) -> dict:
        """Saldos finales del balance de comprobación importado para el ejercicio y periodo (solo hojas)."""
        if self._balance_importado is None:
            lotes = list(self.db.scalars(select(LoteContable.id).where(
                LoteContable.empresa_id == self.empresa_id, LoteContable.ejercicio == self.ejercicio,
                LoteContable.estado == "ACTIVO", LoteContable.tipo_informacion == "BALANCE",
                or_(LoteContable.periodo == self.periodo, LoteContable.periodo.is_(None) if self.periodo >= 12 else False))))
            filas = defaultdict(int)
            if lotes:
                for c, d, h in self.db.execute(select(SaldoCuenta.cuenta, func.sum(SaldoCuenta.saldo_final_debe),
                                                      func.sum(SaldoCuenta.saldo_final_haber))
                                               .where(SaldoCuenta.lote_id.in_(lotes[-1:])).group_by(SaldoCuenta.cuenta)):
                    filas[c] += _c(d) - _c(h)
                codigos = set(filas)
                filas = {c: v for c, v in filas.items() if not any(o != c and o.startswith(c) for o in codigos)}
            self._balance_importado = dict(filas)
        return self._balance_importado

    def saldo_balance_importado(self, prefijo: str) -> int | None:
        b = self.balance_importado()
        if not b:
            return None
        return sum(v for c, v in b.items() if c.startswith(prefijo))

    # ------------------------------------------------------------ compensaciones (fase 4)
    def composicion(self, prefijo: str):
        """Composición de partidas de la fase 4 a la fecha de corte (solo compensaciones APROBADAS)."""
        from app.compensacion import partidas
        if self._comp is None:
            cfg = partidas.configuracion(self.db, self.empresa_id, self.corte)
            self._comp_prefijos = list(cfg.cuentas)
            partidas.construir(self.db, self.empresa_id, cfg, self.corte.year)
            self.db.commit()
            por = defaultdict(list)
            for e in partidas.composicion(self.db, self.empresa_id, self.corte, cuentas=self._comp_prefijos, incluir_propuestas=False):
                por[e.item["cuenta"]].append(e)
            self._comp = por
            ult = self.db.execute(select(func.count(Aplicacion.id), func.max(Aplicacion.id), func.max(Aplicacion.reversion_id))
                                  .where(Aplicacion.empresa_id == self.empresa_id, Aplicacion.estado == "APROBADA")).one()
            n_items = self.db.scalar(select(func.count(PartidaAbierta.id)).where(PartidaAbierta.empresa_id == self.empresa_id))
            self._comp_version = hashlib.sha256(repr((ult, n_items)).encode()).hexdigest()[:24]
        if not any(prefijo.startswith(p) or p.startswith(prefijo) for p in self._comp_prefijos):
            return None
        out = []
        for c, lst in self._comp.items():
            if c.startswith(prefijo):
                out.extend(lst)
        return out

    @property
    def version_compensacion(self) -> str | None:
        return self._comp_version

    def aplicado_por_clase(self, item_ids) -> dict:
        """item → {clase de la contrapartida: importe aplicado (moneda del ítem)} con aplicaciones aprobadas al corte."""
        if self._aplic_clase is None:
            self._aplic_clase = defaultdict(lambda: defaultdict(lambda: CERO))
            pa = PartidaAbierta.__table__.alias("contra")
            filas = self.db.execute(
                select(Aplicacion.origen_item_id, Aplicacion.aplicacion_item_id, Aplicacion.importe, pa.c.clase, pa.c.id)
                .join(pa, or_(pa.c.id == Aplicacion.aplicacion_item_id, pa.c.id == Aplicacion.origen_item_id))
                .where(Aplicacion.empresa_id == self.empresa_id, Aplicacion.estado == "APROBADA",
                       Aplicacion.fecha_efectiva <= self.corte))
            for o, a, imp, clase, pid in filas:
                if pid == a:
                    self._aplic_clase[o][clase] += imp
                elif pid == o:
                    self._aplic_clase[a][clase] += imp
        return self._aplic_clase

    # ------------------------------------------------------------ sustentos adjuntos
    def adjuntos(self) -> dict:
        if self._adjuntos is None:
            a = {"docs": set(), "claves": set(), "cuentas": set(), "items": set(), "lineas": set()}
            for cta, ter, docu, clave, item, linea in self.db.execute(
                    select(AdjuntoAnexo.cuenta, AdjuntoAnexo.tercero, AdjuntoAnexo.documento, AdjuntoAnexo.clave_fila,
                           AdjuntoAnexo.item_id, AdjuntoAnexo.linea_id).where(AdjuntoAnexo.empresa_id == self.empresa_id)):
                if docu:
                    a["docs"].add(((ter or "").strip(), docu.strip().upper()))
                if clave:
                    a["claves"].add(clave)
                if item:
                    a["items"].add(item)
                if linea:
                    a["lineas"].add(linea)
                if cta and not (ter or docu or clave or item or linea):
                    a["cuentas"].add(cta)
            self._adjuntos = a
        return self._adjuntos

    def tiene_adjunto(self, fila: dict) -> bool:
        a = self.adjuntos()
        if fila.get("clave") in a["claves"] or (fila.get("item_id") and fila["item_id"] in a["items"]) or \
                (fila.get("linea_id") and fila["linea_id"] in a["lineas"]):
            return True
        d = fila.get("documento")
        if d and (((fila.get("tercero") or ""), d.upper()) in a["docs"] or ("", d.upper()) in a["docs"]):
            return True
        return False

    def adjunto_de_cuenta(self, cuenta: str) -> bool:
        return any(cuenta.startswith(c) for c in self.adjuntos()["cuentas"])

    # ------------------------------------------------------------ registros auxiliares
    def registros(self, tipo: str) -> list[dict]:
        if tipo not in self._registros:
            filas = []
            for r in self.db.scalars(select(RegistroAuxiliar).where(
                    RegistroAuxiliar.empresa_id == self.empresa_id, RegistroAuxiliar.tipo == tipo,
                    RegistroAuxiliar.vigente.is_(True)).order_by(RegistroAuxiliar.id)):
                d = json.loads(r.datos)
                d.update(_id=r.id, _clave=r.clave, _cuenta=r.cuenta, _fecha=r.fecha_referencia)
                filas.append(d)
            self._registros[tipo] = filas
        return self._registros[tipo]


def crear(db: Session, empresa_id: int, ejercicio: int, periodo: int, corte: date | None = None,
          filtros: Filtros | None = None) -> Ctx:
    if not (1 <= periodo <= 13):
        raise ValueError("El periodo debe estar entre 01 y 13.")
    corte = corte or fin_de_periodo(ejercicio, periodo)
    if corte.year != ejercicio:
        raise ValueError("La fecha de corte debe pertenecer al ejercicio seleccionado.")
    if periodo <= 12 and corte > fin_de_periodo(ejercicio, periodo):
        raise ValueError("La fecha de corte no puede ser posterior al cierre del periodo seleccionado.")
    return Ctx(db, empresa_id, ejercicio, periodo, corte, filtros or Filtros()).cargar()
