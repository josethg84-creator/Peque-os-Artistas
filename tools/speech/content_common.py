"""Ayudas para escribir el contenido de «Aprendo a Hablar» (Fase 3) en Python
y guardarlo como JSON en assets/speech/. El contenido es original."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "speech"


def I(name, color=None):
    return {"icon": name, "color": color} if color else {"icon": name}


def D(drawing, **colors):
    return {"drawing": drawing, "colors": colors} if colors else {"drawing": drawing}


def K(emotion="feliz", girl=False, shirt=None, arms_up=False, hair=None):
    k = {"emotion": emotion, "girl": girl}
    if shirt:
        k["shirt"] = shirt
    if hair:
        k["hair"] = hair
    if arms_up:
        k["arms_up"] = True
    return {"kid": k}


def E(emotion):
    return {"emotion": emotion}


def S(bg, *items):
    """Escena: fondo y elementos (picture, x, y, tamaño)."""
    return {"scene": bg, "items": [{"p": p, "x": x, "y": y, "s": s} for (p, x, y, s) in items]}


LOLO = {"lolo": True}
# Las frutas traen sol, nubes y plantas: también con colores reales.
SUNNY = {"sol": "#FFD54F", "nube_*": "#E3F2FD", "arbusto_*": "#81C784", "hoja_*": "#66BB6A", "boca": "#E57373", "ojo_*": "#FFFFFF"}
APPLE = D("fruta_manzana", manzana="#E53935", hoja="#43A047", tallo="#8D5524", brillo="#FFFFFF", **SUNNY)
BANANA = D("fruta_platano", platano="#FFD600", tallo="#8D6E63", punta="#6D4C41", tallo_corte="#A1887F", **SUNNY)
STRAWBERRY = D("fruta_fresa", fresa="#E53935", hojas="#43A047", tallo="#2E7D32", fresa_cortada="#EF5350",
               fresa_cortada_borde="#FFCDD2", hojas_cortada="#43A047", hoja_detras="#388E3C",
               **{"flor_*": "#F48FB1", "flor_centro": "#FFD54F"}, **SUNNY)
ORANGE = D("fruta_naranja", naranja="#FF8F00", hoja="#43A047", tallo="#8D5524", brillo="#FFFFFF",
           naranja_cortada="#FB8C00", naranja_centro="#FFE0B2", rodaja="#FB8C00", rodaja_borde="#FFE0B2",
           **{"gajo_*": "#FFB74D", "rodaja_gajo_*": "#FFB74D"}, **SUNNY)
GRAPES = D("fruta_uvas", **{"uva_*": "#8E44AD", "hoja": "#43A047", "tallo": "#8D5524"}, **SUNNY)

BOY = "#64B5F6"
GIRL = "#F48FB1"


def save(name, data):
    path = OUT / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path
