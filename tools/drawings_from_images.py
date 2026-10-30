#!/usr/bin/env python3
"""Convierte los dibujos de línea de «Catalogo Imagenes/» en dibujos para colorear.

La app colorea por regiones vectoriales (SVG con zonas cerradas), así que una
imagen PNG no sirve tal cual. Este script:

1. Encaja la imagen en el lienzo de 1024 × 1024 con margen.
2. Separa la tinta (líneas negras) del papel.
3. Cada zona blanca cerrada es una región coloreable; el exterior es el «fondo».
   Las zonas diminutas (brillos de los ojos, huecos entre bigotes) se quedan
   en blanco y no se pueden colorear.
4. Traza el contorno de cada región, ensanchado unos píxeles para que el color
   llegue por debajo de la línea, y la tinta como detalle negro encima.
5. Nombra las regiones con los nombres de NAMES (asignados mirando la imagen
   anotada que genera ``--annotate``); las demás quedan como ``zona_NN``.

Uso (desde la raíz; necesita numpy, Pillow y opencv-python-headless):
    python3 tools/drawings_from_images.py --annotate   # imágenes numeradas en build/qa/
    python3 tools/drawings_from_images.py              # escribe los SVG
Después: python3 tools/generate_drawings.py (catálogo), node tools/render_previews.mjs,
python3 tools/make_thumbnails.py, node tools/measure_regions.mjs y
python3 tools/validate_assets.py.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Catalogo Imagenes"
QA = ROOT / "build" / "qa"

CANVAS = 1024
MARGIN = 72          # margen libre alrededor del dibujo (el control pide 48 px)
WORK = 2             # se trabaja al doble de resolución para contornos suaves
INK_LEVEL = 150      # gris por debajo del cual es tinta
MIN_REGION = 700     # px² (en 1024): por debajo, la zona no es coloreable
BLEED = 3            # px que la región se mete por debajo de la línea

# id del dibujo -> (archivo de origen, carpeta)
IMAGES = {
    "animal_gato": ("Gato kawaii para colorear.png", "animals"),
    "animal_perro": ("Perrito tierno para colorear.png", "animals"),
    "animal_conejo": ("Conejito adorable para colorear_edited.png", "animals"),
    "animal_leon": ("Leoncito tierno para colorear_edited.png", "animals"),
    "animal_elefante": ("Elefante Kawaii para Colorear.png", "animals"),
    "animal_jirafa": ("Jirafa kawaii para colorear_edited.png", "animals"),
    "animal_tortuga": ("Tortuga tierna para colorear.png", "animals"),
}

# Algunos dibujos tienen pequeñas aberturas en la línea por las que una zona
# «se escapa» al fondo: se cierran con este radio (px a 1024), y la línea
# dibujada también queda cerrada.
CLOSE = {"animal_elefante": 5}

# Nombres de las regiones (número de la imagen anotada build/qa/anotado_*.png ->
# nombre). Las que no aparecen se llaman zona_NN.
NAMES: dict[str, dict[int, str]] = {
    "animal_gato": {
        1: "cabeza", 2: "cuerpo", 3: "barriga", 4: "cola", 5: "hocico", 6: "pata_izquierda",
        7: "pata_derecha", 8: "oreja_derecha", 9: "oreja_izquierda", 10: "oreja_derecha_interior",
        11: "oreja_izquierda_interior", 12: "nariz",
    },
    "animal_perro": {
        1: "cuerpo", 2: "cabeza", 3: "oreja_derecha", 4: "oreja_izquierda", 5: "hocico", 6: "barriga",
        7: "mancha_ojo", 8: "cola", 9: "pata_derecha", 10: "pata_izquierda", 11: "muslo_derecho",
        12: "muslo_izquierdo", 13: "mejilla", 14: "collar_derecho", 15: "collar_izquierdo", 16: "placa",
    },
    "animal_conejo": {
        1: "cabeza", 2: "cuerpo", 3: "oreja_izquierda", 4: "oreja_derecha", 5: "pata_derecha",
        6: "pata_izquierda", 7: "oreja_derecha_interior", 8: "oreja_izquierda_interior", 9: "cola",
    },
    "animal_leon": {
        1: "cabeza", 2: "melena", 3: "melena_arriba", 4: "hocico", 5: "pecho", 6: "muslo_derecho",
        7: "muslo_izquierdo", 8: "pata_derecha", 9: "pata_izquierda", 10: "mechon_cola",
        11: "oreja_derecha", 12: "oreja_izquierda", 13: "cola", 14: "oreja_derecha_interior",
        15: "oreja_izquierda_interior",
    },
    "animal_elefante": {
        1: "cabeza", 2: "cuerpo", 3: "oreja_derecha_interior", 4: "oreja_izquierda_interior",
        5: "oreja_derecha", 6: "trompa", 7: "oreja_izquierda", 8: "pata_trasera_izquierda",
        9: "pata_trasera_derecha", 10: "pecho", 11: "dedo_1", 12: "dedo_2", 13: "dedo_3", 14: "dedo_4",
    },
    "animal_jirafa": {
        1: "cuerpo", 2: "cabeza", 3: "hocico", 4: "pata_trasera_izquierda", 5: "pata_trasera_derecha",
        6: "mancha_1", 7: "mancha_2", 8: "oreja_derecha", 9: "oreja_izquierda", 10: "mancha_3",
        11: "mechon_cola", 12: "mancha_4", 13: "mancha_5", 14: "pezuna_1", 15: "pezuna_2",
        16: "mancha_6", 17: "pezuna_3", 18: "pezuna_4", 19: "cuerno_derecho", 20: "cuerno_izquierdo",
        21: "mancha_7",
    },
    "animal_tortuga": {
        1: "cabeza", 2: "borde_caparazon", 3: "placa_centro", 4: "pata_trasera", 5: "pata_delantera",
        6: "placa_1", 7: "placa_2", 8: "placa_3", 9: "pata_delantera_2", 10: "placa_4", 11: "placa_5",
        12: "barriga", 13: "placa_6", 14: "placa_7", 15: "placa_8", 16: "cola", 17: "pata_trasera_2",
        18: "dedo_1", 19: "dedo_2", 20: "dedo_3", 21: "dedo_4", 22: "dedo_5", 23: "dedo_6",
    },
}


def load(path):
    """Imagen en gris, encajada en el lienzo de trabajo con margen."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im.convert("RGBA"))
        im = bg
    gray = np.asarray(im.convert("L"))
    ys, xs = np.where(gray < 200)
    crop = gray[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    size = CANVAS * WORK
    inner = size - 2 * MARGIN * WORK
    scale = inner / max(h, w)
    resized = cv2.resize(crop, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_CUBIC)
    canvas = np.full((size, size), 255, np.uint8)
    y0 = (size - resized.shape[0]) // 2
    x0 = (size - resized.shape[1]) // 2
    canvas[y0:y0 + resized.shape[0], x0:x0 + resized.shape[1]] = resized
    return canvas


def segment(gray, did=None):
    ink = (gray < INK_LEVEL).astype(np.uint8)
    radius = CLOSE.get(did, 0) * WORK
    if radius:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1,) * 2)
        ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel)
    paper = (1 - ink).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(paper, connectivity=4)
    size = gray.shape[0]
    min_area = MIN_REGION * WORK * WORK
    regions, small = [], []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        touches_border = x == 0 or y == 0 or x + w == size or y + h == size
        if touches_border:
            continue  # exterior: es el fondo
        (regions if area >= min_area else small).append((i, area))
    regions.sort(key=lambda t: -t[1])  # las grandes primero: las de dentro se pintan encima
    return ink, labels, regions, small


def contour_path(mask, epsilon):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(contours, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, epsilon, True)
    pts = [(round(p[0][0] / WORK), round(p[0][1] / WORK)) for p in c]
    # Coordenadas enteras: la región va por debajo de la línea, no se nota.
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    return "M" + " L".join(f"{x},{y}" for x, y in pts) + "Z", pts


def compound_path(mask, epsilon):
    """Todos los contornos (exteriores y huecos) en un solo trazado."""
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    for c in contours:
        if cv2.contourArea(c) < 2 * WORK * WORK:
            continue
        c = cv2.approxPolyDP(c, epsilon, True)
        if len(c) < 3:
            continue
        parts.append("M" + " L".join(f"{p[0][0] / WORK:.1f},{p[0][1] / WORK:.1f}" for p in c) + "Z")
    return " ".join(parts)


def annotate(did, gray, labels, regions):
    out = Image.fromarray(gray).convert("RGB").resize((CANVAS, CANVAS))
    draw = ImageDraw.Draw(out)
    font = ImageFont.load_default(size=22)
    rng = np.random.default_rng(3)
    tint = np.asarray(out).copy()
    small_labels = cv2.resize(labels.astype(np.int32), (CANVAS, CANVAS), interpolation=cv2.INTER_NEAREST)
    for k, (i, _) in enumerate(regions, start=1):
        tint[small_labels == i] = rng.integers(120, 250, 3)
    out = Image.fromarray(tint)
    draw = ImageDraw.Draw(out)
    for k, (i, _) in enumerate(regions, start=1):
        ys, xs = np.where(small_labels == i)
        # punto interior más alejado del borde, para poner el número
        m = (small_labels == i).astype(np.uint8)
        dist = cv2.distanceTransform(m, cv2.DIST_L2, 3)
        y, x = np.unravel_index(dist.argmax(), dist.shape)
        draw.text((x - 10, y - 12), str(k), fill=(0, 0, 0), font=font, stroke_width=3, stroke_fill=(255, 255, 255))
    QA.mkdir(parents=True, exist_ok=True)
    out.save(QA / f"anotado_{did}.png")


def build(did, source, folder):
    gray = load(SOURCE / source)
    ink, labels, regions, small = segment(gray, did)
    names = NAMES.get(did, {})
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * BLEED * WORK + 1,) * 2)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<!-- Pequeños Artistas - {did}. Convertido de «Catalogo Imagenes/{source}» '
        f'con tools/drawings_from_images.py. -->',
        f'<svg xmlns="http://www.w3.org/2000/svg" id="{did}" width="{CANVAS}" height="{CANVAS}" '
        f'viewBox="0 0 {CANVAS} {CANVAS}">',
        '  <g id="regiones">',
        f'    <path id="fondo" class="region" fill="#FFFFFF" stroke="none" d="M0,0 L{CANVAS},0 '
        f'L{CANVAS},{CANVAS} L0,{CANVAS}Z"/>',
    ]
    used = set()
    for k, (i, _) in enumerate(regions, start=1):
        rid = names.get(k, f"zona_{k:02d}")
        assert rid not in used, (did, rid)
        used.add(rid)
        mask = cv2.dilate((labels == i).astype(np.uint8), kernel)
        d, _ = contour_path(mask, 0.9 * WORK / 2)
        lines.append(f'    <path id="{rid}" class="region" fill="#FFFFFF" stroke="none" d="{d}"/>')
    lines.append("  </g>")
    lines.append('  <g id="detalles" pointer-events="none">')
    # Huecos diminutos (brillos de los ojos...): blancos y no coloreables.
    if small:
        smask = np.isin(labels, [i for i, _ in small]).astype(np.uint8)
        lines.append(f'    <path class="detalle" fill="#FFFFFF" stroke="none" d="{compound_path(smask, 0.5 * WORK / 2)}"/>')
    lines.append(f'    <path class="detalle" fill="#000000" stroke="none" d="{compound_path(ink, 0.7 * WORK / 2)}"/>')
    lines.append("  </g>")
    lines.append("</svg>")
    out = ROOT / "assets" / "drawings" / folder / f"{did}.svg"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{did:18s} {len(regions):3d} regiones  {len(small):3d} huecos blancos  {out.stat().st_size // 1024} KB")
    return gray, labels, regions


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotate", action="store_true")
    args = ap.parse_args()
    for did, (source, folder) in IMAGES.items():
        if args.annotate:
            gray = load(SOURCE / source)
            _, labels, regions, _ = segment(gray, did)
            annotate(did, gray, labels, regions)
            print(did, len(regions), "regiones")
        else:
            build(did, source, folder)
