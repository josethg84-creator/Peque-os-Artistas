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

# id del dibujo -> (archivo de origen, carpeta). Si el archivo de origen ya no
# está en «Catalogo Imagenes/», se conserva el SVG que hay en assets/.
IMAGES = {
    # Primera tanda.
    "animal_jirafa": ("Jirafa kawaii para colorear_edited.png", "animals"),
    "animal_cebra": ("Cebra adorable para colorear.png", "animals"),
    # Segunda tanda (sustituyen a dibujos anteriores o son nuevos).
    "animal_tortuga": ("Tortuga sonriente para colorear.png", "animals"),
    "granja_cerdito": ("Cerdito tierno de líneas gruesas.png", "farm"),
    "granja_gallina": ("Gallina sonriente para colorear.png", "farm"),
    "granja_gallo": ("Gallo caricaturesco con plumas curvas.png", "farm"),
    "granja_oveja": ("Oveja Chibi Sonriente con Lana Esponjosa.png", "farm"),
    "granja_patito": ("Patito sonriente para colorear.png", "farm"),
    "mar_ballena": ("Ballena feliz saltando entre olas.png", "sea"),
    "mar_cangrejo": ("Cangrejo sonriente para colorear.png", "sea"),
    "mar_delfin": ("Delfín sonriente saltando entre olas.png", "sea"),
    "mar_estrella": ("Estrella de mar sonriente para colorear.png", "sea"),
    "mar_pulpo": ("Pulpo kawaii con tentáculos ondulantes.png", "sea"),
    "dinosaurio_01": ("T-Rex sonriente entre hierbas y rocas.png", "dinosaurs"),
    "dinosaurio_02": ("Triceratops sonriente entre rocas y hierba.png", "dinosaurs"),
    "dinosaurio_03": ("Estegosaurio sonriente entre rocas y hierba.png", "dinosaurs"),
    "dinosaurio_04": ("Brontosaurio feliz en la naturaleza.png", "dinosaurs"),
    "dinosaurio_06": ("Espinosaurio junto al volcán.png", "dinosaurs"),
    "dinosaurio_07": ("Pteranodonte sonriente sobre paisaje volcánico.png", "dinosaurs"),
    "dinosaurio_08": ("Velociraptor sonriente en paisaje prehistórico.png", "dinosaurs"),
    "fantasia_dragon": ("Dragón sonriente con alas extendidas.png", "fantasy"),
    "fantasia_unicornio": ("Unicornio alegre para colorear.png", "fantasy"),
    "fantasia_grifo": ("Grifo amistoso con alas extendidas.png", "fantasy"),
    "fantasia_zorro_alado": ("Zorro alado con estrellas.png", "fantasy"),
    # Tercera tanda.
    "animal_gato": ("Gato kawaii para colorear.png", "animals"),
    "animal_perro": ("Perrito tierno con collar y lengua fuera.png", "animals"),
    "animal_conejo": ("Conejo tierno para colorear.png", "animals"),
    "animal_leon": ("León Adorable para Colorear.png", "animals"),
    "animal_elefante": ("Elefante bebé sonriente para colorear.png", "animals"),
    "animal_oso": ("Oso de peluche para colorear.png", "animals"),
    "animal_mono": ("Mono feliz con cola rizada.png", "animals"),
    "granja_vaca": ("Vaca chibi para colorear.png", "farm"),
    "granja_poni": ("Poni sonriente con crines onduladas.png", "farm"),
    "fantasia_hada": ("Hada Mariposa con Varita Estrellada.png", "fantasy"),
    "fantasia_hada_hongo": ("Hada risueña sobre un hongo mágico.png", "fantasy"),
    "fantasia_robot": ("Robot sonriente con cohete y engranajes.png", "fantasy"),
    "fantasia_robot_heroe": ("Robot héroe entre estrellas y planetas.png", "fantasy"),
    # Cuarta tanda (Imágenes 3): sustituyen a los vehículos, al pez y a la
    # mariposa, y añaden helicóptero, abeja, oruga, tortuga marina y caballito.
    "vehiculo_barco": ("Barco sonriente entre olas y nubes.png", "vehicles"),
    "vehiculo_tren": ("Trenecito feliz entre montañas.png", "vehicles"),
    "vehiculo_automovil": ("Coche sonriente en la carretera.png", "vehicles"),
    "vehiculo_autobus": ("Autobús sonriente en la carretera.png", "vehicles"),
    "vehiculo_avion": ("Avión sonriente entre nubes y sol.png", "vehicles"),
    "vehiculo_helicoptero": ("Helicóptero sonriente en el cielo.png", "vehicles"),
    "animal_pez": ("Pez sonriente en el fondo marino.png", "animals"),
    "animal_mariposa": ("Mariposa sonriente en jardín encantado.png", "animals"),
    "animal_abeja": ("Abeja feliz entre flores y sol.png", "animals"),
    "animal_oruga": ("Oruga sonriente sobre una hoja.png", "animals"),
    "mar_tortuga": ("Tortuga marina sonriente entre algas.png", "sea"),
    "mar_caballito": ("Caballito de mar kawaii bajo el mar.png", "sea"),
    # Quinta tanda (Imágenes 4): frutas.
    "fruta_manzana": ("Manzana kawaii en el jardín soleado.png", "fruits"),
    "fruta_platano": ("Plátano feliz bajo el sol.png", "fruits"),
    "fruta_fresa": ("Trío de fresas bajo el sol feliz.png", "fruits"),
    "fruta_naranja": ("Naranjas sonrientes en un día soleado.png", "fruits"),
    "fruta_uvas": ("Racimo de uvas kawaii bajo el sol.png", "fruits"),
    "fruta_pina": ("Piña sonriente bajo el sol y las nubes.png", "fruits"),
    "fruta_sandia": ("Sandía Kawaii bajo el sol.png", "fruits"),
    "fruta_cerezas": ("Cerezas kawaii bajo el sol.png", "fruits"),
}

# Algunos dibujos tienen pequeñas aberturas en la línea por las que una zona
# «se escapa» al fondo: se cierran con este radio (px a 1024), y la línea
# dibujada también queda cerrada.
CLOSE: dict[str, int] = {}

# Aberturas demasiado anchas para cerrarlas sin estropear otras líneas: se
# sellan con un trazo corto (coordenadas a 1024 y grosor en px), que pasa a
# formar parte de la línea dibujada.
SEALS = {
    # La línea exterior de la oreja izquierda acaba suelta junto a la cabeza.
    "animal_cebra": [((145, 243), (172, 243), 10)],
}

# Nombres de las regiones (número de la imagen anotada build/qa/anotado_*.png ->
# nombre). Las que no aparecen se llaman zona_NN.
NAMES: dict[str, dict[int, str]] = {
    # Las alas se llaman ala_*: «La mariposa de colores» solo tiñe las alas.
    "animal_mariposa": {
        1: "cabeza", 2: "ala_1", 3: "ala_2", 4: "ala_3", 5: "ala_4", 6: "ala_5", 7: "nube", 8: "ala_6",
        9: "ala_7", 10: "flor_derecha", 11: "ala_8", 12: "flor_izquierda", 13: "sol", 14: "ala_9",
        15: "ala_10", 16: "cuerpo_2", 17: "cuerpo_1", 18: "hoja_1", 19: "hoja_2", 20: "cuerpo_3",
        21: "hoja_3", 22: "ala_11", 23: "hoja_4", 24: "cuerpo_4", 25: "ala_12", 26: "flor_derecha_centro",
        27: "tallo", 28: "hoja_5", 29: "flor_izquierda_centro", 30: "ala_13",
    },
    # Frutas: «Aprendo a Hablar» las pinta con sus colores reales por nombre.
    "fruta_manzana": {
        1: "manzana", 2: "hoja", 3: "nube_derecha", 4: "sol", 5: "nube_izquierda", 6: "tallo",
        7: "boca", 8: "brillo", 9: "ojo_derecho_brillo", 10: "ojo_izquierdo_brillo",
    },
    "fruta_platano": {
        1: "platano", 2: "sol", 3: "nube_1", 4: "arbusto_derecho", 5: "nube_2", 6: "arbusto_izquierdo",
        7: "tallo", 8: "tallo_corte", 9: "boca", 10: "punta",
    },
    "fruta_fresa": {
        1: "fresa", 2: "fresa_cortada", 3: "hoja_suelo_1", 4: "hojas", 5: "nube_izquierda", 6: "sol",
        7: "hoja_detras", 8: "hoja_suelo_2", 9: "nube_derecha", 10: "flor_1", 11: "hoja_suelo_3",
        12: "hoja_1", 13: "hoja_2", 14: "hoja_3", 15: "fresa_cortada_borde", 16: "flor_2",
        17: "hojas_cortada", 18: "tallo", 19: "hoja_4", 20: "boca", 21: "flor_centro", 22: "flor_3",
        23: "ojo_brillo",
    },
    "fruta_naranja": {
        1: "naranja", 2: "naranja_centro", 3: "hoja", 4: "naranja_cortada", 5: "nube_izquierda",
        6: "rodaja", 7: "sol", 8: "nube_derecha", 9: "hoja_suelo_1", 10: "gajo_1", 11: "gajo_2",
        12: "gajo_3", 13: "gajo_4", 14: "gajo_5", 15: "rodaja_gajo_2", 16: "hoja_suelo_2", 17: "gajo_6",
        18: "gajo_7", 19: "rodaja_gajo_1", 20: "rodaja_gajo_3", 21: "rodaja_gajo_4", 22: "gajo_8",
        23: "rodaja_borde", 24: "tallo", 25: "boca",
    },
    "fruta_uvas": {
        1: "hoja", 2: "uva_1", 3: "nube_derecha", 4: "arbusto_derecho", 5: "arbusto_izquierdo", 6: "sol",
        7: "nube_izquierda", 8: "uva_2", 9: "uva_3", 10: "uva_4", 11: "uva_5", 12: "uva_6", 13: "uva_7",
        14: "uva_8", 15: "uva_9", 16: "uva_10", 17: "tallo", 18: "boca",
    },
    "animal_gato": {
        1: "cabeza", 2: "cuerpo", 3: "pata_trasera", 4: "cola", 5: "raya_frente_2",
        6: "oreja_izquierda_interior", 7: "oreja_derecha_interior", 8: "raya_cola_4", 9: "raya_cola_1",
        10: "raya_cola_2", 11: "raya_cola_3", 12: "raya_frente_3", 13: "raya_frente_1",
        14: "raya_lomo_2", 15: "raya_lomo_1",
    },
    "animal_perro": {
        1: "cabeza", 2: "cuerpo", 3: "pata_trasera_derecha", 4: "pata_trasera_izquierda", 5: "cola",
        6: "lengua", 7: "placa", 8: "collar_derecho", 9: "collar_izquierdo", 10: "brillo_ojo_derecho",
        11: "brillo_ojo_izquierdo",
    },
    "animal_jirafa": {
        1: "cuerpo", 2: "cabeza", 3: "hocico", 4: "pata_trasera_izquierda", 5: "pata_trasera_derecha",
        6: "mancha_1", 7: "mancha_2", 8: "oreja_derecha", 9: "oreja_izquierda", 10: "mancha_3",
        11: "mechon_cola", 12: "mancha_4", 13: "mancha_5", 14: "pezuna_1", 15: "pezuna_2",
        16: "mancha_6", 17: "pezuna_3", 18: "pezuna_4", 19: "cuerno_derecho", 20: "cuerno_izquierdo",
        21: "mancha_7",
    },
    "animal_cebra": {
        1: "cuerpo", 2: "cabeza", 3: "hocico", 4: "cuello", 5: "pata_trasera_derecha", 6: "oreja_derecha",
        7: "oreja_izquierda", 8: "mechon_cola", 9: "pezuna_delantera_derecha", 10: "pezuna_trasera_derecha",
        11: "pata_trasera_izquierda_1", 12: "pezuna_trasera_izquierda", 13: "pezuna_delantera_izquierda",
        14: "crin_1", 15: "crin_2", 16: "oreja_derecha_interior", 17: "crin_3", 18: "lomo", 19: "cola",
        20: "pata_delantera_izquierda_1", 21: "oreja_izquierda_interior", 22: "pata_delantera_izquierda_2",
        23: "pata_trasera_izquierda_2", 24: "mejilla", 25: "crin_7", 26: "crin_6",
        27: "pata_delantera_izquierda_3", 28: "crin_5", 29: "crin_8", 30: "crin_4",
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
    for (x1, y1), (x2, y2), width in SEALS.get(did, []):
        cv2.line(ink, (x1 * WORK, y1 * WORK), (x2 * WORK, y2 * WORK), 1, width * WORK, cv2.LINE_AA)
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
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{did:18s} {len(regions):3d} regiones  {len(small):3d} huecos blancos  {out.stat().st_size // 1024} KB")
    return gray, labels, regions


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotate", action="store_true")
    ap.add_argument("ids", nargs="*", help="solo estos dibujos (por defecto, todos)")
    args = ap.parse_args()
    for did, (source, folder) in IMAGES.items():
        if args.ids and did not in args.ids:
            continue
        if not (SOURCE / source).exists():
            print(f"{did:18s} sin imagen de origen: se conserva el SVG actual")
            continue
        if args.annotate:
            gray = load(SOURCE / source)
            _, labels, regions, _ = segment(gray, did)
            annotate(did, gray, labels, regions)
            print(did, len(regions), "regiones")
        else:
            build(did, source, folder)
