"""Validación de contabilidad analítica: clases 6, 7 y 9 del PCGE.

En el PCGE los gastos por naturaleza (clase 6) se transfieren a destino (clase 9, u otras
cuentas como inventarios o activo en curso) con contrapartida en la cuenta 79 *Cargas
imputables a cuentas de costos y gastos*. Si se carga el destino sin abonar la 79, el gasto
queda duplicado en los estados financieros por naturaleza y por función.

Nada de esto se asume fijo: cada empresa configura si usa la clase 9, si el destino se
registra en el mismo asiento o al cierre del periodo, qué cuentas son destinables, el prefijo
de destino, la cuenta de cargas imputables, si exige centro de costo y reglas específicas
(p. ej. 60 → 20/61). El plan de cuentas puede además indicar el destino de cada cuenta.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from app.contable.observaciones import Obs

CERO = Decimal("0")


@dataclass
class ReglaEspecifica:
    prefijo_origen: str
    destino_debe: list[str]
    destino_haber: list[str]
    requiere_centro_costo: bool
    descripcion: str | None


@dataclass
class ReglasAnaliticas:
    usa_clase_9: bool = True
    modo: str = "MISMO_ASIENTO"  # MISMO_ASIENTO | PERIODO | NO_APLICA
    destinables: list[str] = field(default_factory=lambda: ["62", "63", "64", "65", "66", "67", "68"])
    destino: list[str] = field(default_factory=lambda: ["9"])
    cargas_imputables: str = "79"
    exigir_cc: bool = False
    validar_78: bool = True
    tolerancia: Decimal = Decimal("0.01")
    especificas: list[ReglaEspecifica] = field(default_factory=list)
    destino_plan: dict[str, str] = field(default_factory=dict)  # cuenta → prefijo de destino (debe)

    @classmethod
    def desde_config(cls, cfg, reglas, plan) -> "ReglasAnaliticas":
        lista = lambda t: [p.strip() for p in (t or "").split(",") if p.strip()]  # noqa: E731
        r = cls(
            usa_clase_9=cfg.usa_clase_9 if cfg.usa_clase_9 is not None else True,
            modo=cfg.modo_destino or "MISMO_ASIENTO",
            destinables=lista(cfg.prefijos_destinables) if cfg.prefijos_destinables is not None
            else ["62", "63", "64", "65", "66", "67", "68"],
            destino=lista(cfg.prefijo_destino) or ["9"],
            cargas_imputables=cfg.cuenta_cargas_imputables or "79",
            exigir_cc=bool(cfg.exigir_centro_costo_destino),
            validar_78=cfg.validar_cuenta_78 if cfg.validar_cuenta_78 is not None else True,
            tolerancia=Decimal(str(cfg.tolerancia_descuadre if cfg.tolerancia_descuadre is not None else "0.01")),
        )
        r.especificas = [ReglaEspecifica(x.prefijo_origen, lista(x.destino_debe), lista(x.destino_haber),
                                         x.requiere_centro_costo, x.descripcion) for x in reglas]
        r.destino_plan = {c: p.cuenta_destino_debe for c, p in (plan or {}).items() if p.cuenta_destino_debe}
        return r


def _empieza(cuenta: str | None, prefijos) -> bool:
    return bool(cuenta) and any(cuenta.startswith(p) for p in prefijos)


def _neto(lineas, prefijos, signo=1) -> Decimal:
    return sum(((x["debe_mn"] - x["haber_mn"]) * signo for x in lineas if _empieza(x.get("cuenta"), prefijos)), CERO)


def validar_analitica(regs: list[dict], reglas: ReglasAnaliticas | None, clave_asiento) -> list[Obs]:
    obs: list[Obs] = []
    if reglas is None:
        return obs
    if not reglas.usa_clase_9 or reglas.modo == "NO_APLICA":
        if any(_empieza(r.get("cuenta"), reglas.destino) for r in regs):
            obs.append(Obs("DES007", severidad="MEDIO",
                           mensaje="La empresa está configurada sin contabilidad analítica de destino, pero el "
                                   "archivo contiene cuentas de destino. Revise la configuración."))
        else:
            obs.append(Obs("DES007", mensaje="La empresa no utiliza cuentas de destino: no se aplicaron las reglas 6/79/9."))
        return obs

    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for r in regs:
        if reglas.modo == "PERIODO":
            grupos[(r.get("ejercicio"), r.get("periodo"))].append(r)
        else:
            k = clave_asiento(r)
            if k:
                grupos[k].append(r)

    for k, lineas in grupos.items():
        etiqueta = (f"periodo {k[1]}/{k[0]}" if reglas.modo == "PERIODO"
                    else f"asiento {'-'.join(str(p) for p in k[2:] if p)}")
        asiento = None if reglas.modo == "PERIODO" else "-".join(str(p) for p in k[2:] if p)
        fila = lineas[0]["_fila"]
        gasto = _neto(lineas, reglas.destinables)
        destino = _neto(lineas, reglas.destino)
        cargas = _neto(lineas, [reglas.cargas_imputables], -1)
        primera_gasto = next((x for x in lineas if _empieza(x.get("cuenta"), reglas.destinables)), None)

        if gasto and not destino and not cargas:
            obs.append(Obs("DES001", fila=primera_gasto["_fila"], cuenta=primera_gasto.get("cuenta"), asiento=asiento,
                           valor=str(gasto),
                           mensaje=f"En el {etiqueta} hay gasto destinable por {gasto} sin cargo a destino ni abono a "
                                   f"la {reglas.cargas_imputables}."))
        if abs(destino - cargas) > reglas.tolerancia:
            obs.append(Obs("DES002", fila=fila, asiento=asiento, cuenta=reglas.cargas_imputables,
                           valor=f"{destino} vs {cargas}",
                           mensaje=f"En el {etiqueta} el destino suma {destino} y la {reglas.cargas_imputables} "
                                   f"{cargas}: el gasto podría quedar duplicado en los estados financieros."))
        if destino and abs(gasto - destino) > reglas.tolerancia:
            obs.append(Obs("DES003", fila=fila, asiento=asiento, valor=f"{gasto} vs {destino}",
                           mensaje=f"En el {etiqueta} el gasto de origen ({gasto}) difiere del destino ({destino})."))

        if reglas.exigir_cc:
            for x in lineas:
                if _empieza(x.get("cuenta"), reglas.destino) and not x.get("centro_costo"):
                    obs.append(Obs("DES004", fila=x["_fila"], cuenta=x.get("cuenta"), asiento=asiento))

        # Destino definido en el plan de cuentas
        destinos_usados = {x["cuenta"] for x in lineas if _empieza(x.get("cuenta"), reglas.destino)}
        if reglas.modo == "MISMO_ASIENTO" and destinos_usados:
            for x in lineas:
                esperado = reglas.destino_plan.get(x.get("cuenta") or "")
                if esperado and _empieza(x.get("cuenta"), reglas.destinables) \
                        and not any(d.startswith(esperado) for d in destinos_usados):
                    obs.append(Obs("DES005", fila=x["_fila"], cuenta=x.get("cuenta"), asiento=asiento, valor=esperado,
                                   mensaje=f"La cuenta {x['cuenta']} tiene destino configurado {esperado}, pero el "
                                           f"asiento usa {', '.join(sorted(destinos_usados))}."))

        # Reglas específicas configuradas por la empresa (p. ej. 60 → 20 / 61)
        if reglas.modo == "MISMO_ASIENTO":
            for regla in reglas.especificas:
                origen = [x for x in lineas if _empieza(x.get("cuenta"), [regla.prefijo_origen])
                          and x["debe_mn"] > x["haber_mn"]]
                if not origen:
                    continue
                falta_d = regla.destino_debe and not any(_empieza(x.get("cuenta"), regla.destino_debe) for x in lineas)
                falta_h = regla.destino_haber and not any(_empieza(x.get("cuenta"), regla.destino_haber) for x in lineas)
                if falta_d or falta_h:
                    obs.append(Obs("DES005", fila=origen[0]["_fila"], cuenta=origen[0].get("cuenta"), asiento=asiento,
                                   mensaje=f"Regla «{regla.descripcion or regla.prefijo_origen}»: se esperaba destino "
                                           f"debe {', '.join(regla.destino_debe) or '—'} y haber "
                                           f"{', '.join(regla.destino_haber) or '—'} en el {etiqueta}."))
                if regla.requiere_centro_costo:
                    for x in origen:
                        if not x.get("centro_costo"):
                            obs.append(Obs("DES004", fila=x["_fila"], cuenta=x.get("cuenta"), asiento=asiento,
                                           mensaje=f"La cuenta {x['cuenta']} requiere centro de costo según la regla "
                                                   f"«{regla.descripcion or regla.prefijo_origen}»."))

        # Cuenta 78: cargas cubiertas por provisiones
        if reglas.validar_78 and reglas.modo == "MISMO_ASIENTO":
            aplica_48 = any(_empieza(x.get("cuenta"), ["48"]) and x["debe_mn"] > 0 for x in lineas)
            abono_78 = any(_empieza(x.get("cuenta"), ["78"]) and x["haber_mn"] > 0 for x in lineas)
            if aplica_48 and not abono_78:
                obs.append(Obs("DES006", fila=fila, asiento=asiento, cuenta="48",
                               mensaje=f"En el {etiqueta} se aplica una provisión (cargo a 48) sin abono a la 78."))
            elif abono_78 and not aplica_48:
                obs.append(Obs("DES006", fila=fila, asiento=asiento, cuenta="78",
                               mensaje=f"En el {etiqueta} se abona la 78 sin aplicar una provisión de la cuenta 48."))
    return obs
