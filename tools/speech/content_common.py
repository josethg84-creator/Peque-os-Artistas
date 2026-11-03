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
APPLE = D("fruta_manzana", manzana="#E53935", hoja="#43A047", tallo="#8D5524", brillo="#FFFFFF")
BANANA = D("fruta_platano", platano="#FFD600", tallo="#8D6E63", punta="#6D4C41")
STRAWBERRY = D("fruta_fresa", fresa="#E53935", hojas="#43A047", tallo="#2E7D32")
ORANGE = D("fruta_naranja", naranja="#FF8F00", hoja="#43A047", tallo="#8D5524", brillo="#FFFFFF")
GRAPES = D("fruta_uvas", **{"uva_*": "#8E44AD", "hoja": "#43A047", "tallo": "#8D5524"})

BOY = "#64B5F6"
GIRL = "#F48FB1"


def save(name, data):
    path = OUT / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path
