#!/usr/bin/env python3
"""Control de calidad de la colección de dibujos.

Comprueba el catálogo, la estructura de cada SVG, las miniaturas, las vistas previas PNG y el
área visible de cada región (medida antes con tools/measure_regions.mjs).
Termina con código 1 si encuentra errores. Uso: python3 tools/validate_assets.py
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "assets" / "catalog" / "catalog.json"
AREAS = ROOT / "build" / "qa" / "region_areas.json"
NS = "{http://www.w3.org/2000/svg}"

EXPECTED = {"animales": 11, "vehiculos": 5, "dinosaurios": 5, "frutas": 5, "fantasia": 5}
REQUIRED = ["id", "name", "category", "file", "thumbnail", "difficulty", "recommended_age", "description"]
DIFFICULTIES = {"facil", "media", "dificil"}
THUMB_SIZE = (512, 512)
FORBIDDEN_TAGS = {"text", "image", "linearGradient", "radialGradient", "pattern", "filter", "use", "font"}
ALLOWED_COLORS = {"#FFFFFF", "#000000", "none"}
SAFE_NAME = re.compile(r"^[a-z0-9_]+\.(svg|png)$")
EDGE_MARGIN = 48       # px sin trazos junto al borde del PNG
MIN_AREA_ERROR = 900   # área visible mínima de una región (px² en 1024x1024)
MIN_AREA_WARN = 2000   # por debajo se avisa: zona pequeña para un dedo infantil

errors, warnings = [], []


def check_svg(item):
    svg = ET.parse(ROOT / item["file"]).getroot()
    if svg.get("viewBox") != "0 0 1024 1024":
        errors.append(f"{item['id']}: viewBox inesperado {svg.get('viewBox')}")
    for el in svg.iter():
        tag = el.tag.replace(NS, "")
        if tag in FORBIDDEN_TAGS:
            errors.append(f"{item['id']}: elemento no permitido <{tag}>")
        for attr in ("fill", "stroke"):
            v = el.get(attr)
            if v is not None and v not in ALLOWED_COLORS:
                errors.append(f"{item['id']}: color no permitido {attr}={v}")
        if el.get("transform"):
            errors.append(f"{item['id']}: transform no permitido (las regiones usan coordenadas absolutas)")
    group = svg.find(f"{NS}g[@id='regiones']")
    if group is None:
        errors.append(f"{item['id']}: falta el grupo 'regiones'")
        return 0
    ids = []
    for el in group:
        rid = el.get("id")
        d = (el.get("d") or "").strip()
        if el.tag != f"{NS}path" or el.get("class") != "region":
            errors.append(f"{item['id']}: hijo de 'regiones' que no es <path class='region'>")
        if not rid or not re.fullmatch(r"[a-z0-9_]+", rid):
            errors.append(f"{item['id']}: id de región inválido {rid!r}")
        if not d.upper().endswith("Z") or d.upper().count("M") != 1:
            errors.append(f"{item['id']}: la región {rid} no es un único trazado cerrado")
        if el.get("fill") != "#FFFFFF":
            errors.append(f"{item['id']}: la región {rid} no está en blanco")
        ids.append(rid)
    if len(ids) != len(set(ids)):
        errors.append(f"{item['id']}: ids de región duplicados")
    if not ids or ids[0] != "fondo":
        errors.append(f"{item['id']}: la primera región debe ser 'fondo'")
    details = svg.find(f"{NS}g[@id='detalles']")
    if details is not None and details.get("pointer-events") != "none":
        errors.append(f"{item['id']}: los detalles deben tener pointer-events='none'")
    regions = len(ids) - 1
    if item.get("regions") is not None and item["regions"] != regions:
        errors.append(f"{item['id']}: el catálogo dice {item['regions']} zonas y el SVG tiene {regions}")
    return regions


def preview_path(item):
    """Vista previa de 1024 px (solo control de calidad, no la usa la app)."""
    return ROOT / "assets" / "previews" / f"{item['id']}.png"


def check_thumbnail(item):
    img = Image.open(ROOT / item["thumbnail"])
    if img.size != THUMB_SIZE:
        errors.append(f"{item['id']}: miniatura de tamaño {img.size}, se esperaba {THUMB_SIZE}")
    if img.mode not in ("L", "LA"):
        errors.append(f"{item['id']}: la miniatura debe estar en escala de grises (modo {img.mode})")
    gray = np.asarray(img.convert("L"))
    if (gray < 64).mean() < 0.005:
        errors.append(f"{item['id']}: la miniatura parece vacía (casi sin trazos)")


def check_png(item):
    img = Image.open(preview_path(item))
    if img.size != (1024, 1024):
        errors.append(f"{item['id']}: PNG de tamaño {img.size}, se esperaba 1024x1024")
    rgb = np.asarray(img.convert("RGB")).astype(int)
    gray = rgb.mean(axis=2)
    m = EDGE_MARGIN
    border = np.concatenate([gray[:m].ravel(), gray[-m:].ravel(), gray[:, :m].ravel(), gray[:, -m:].ravel()])
    if (border < 128).any():
        errors.append(f"{item['id']}: hay trazos a menos de {m}px del borde")
    if (np.abs(rgb[..., 0] - rgb[..., 1]) + np.abs(rgb[..., 1] - rgb[..., 2])).max() > 30:
        errors.append(f"{item['id']}: la vista previa contiene color (debe ser blanco y negro)")


def check_areas(item, areas):
    if areas is None:
        return None
    measured = areas.get(item["id"])
    if measured is None:
        errors.append(f"{item['id']}: sin medición de áreas (ejecuta node tools/measure_regions.mjs)")
        return None
    measured = {k: v for k, v in measured.items() if k != "fondo"}
    for rid, area in sorted(measured.items(), key=lambda kv: kv[1]):
        if area == 0:
            errors.append(f"{item['id']}: la región {rid} queda totalmente tapada")
        elif area < MIN_AREA_ERROR:
            errors.append(f"{item['id']}: la región {rid} es muy pequeña ({area} px²)")
        elif area < MIN_AREA_WARN:
            warnings.append(f"{item['id']}: la región {rid} es pequeña para tocar ({area} px²)")
    return min(measured.values()) if measured else None


def main():
    items = json.loads(CATALOG.read_text(encoding="utf-8"))["drawings"]
    areas = json.loads(AREAS.read_text(encoding="utf-8")) if AREAS.is_file() else None
    if areas is None:
        warnings.append("no existe build/qa/region_areas.json: no se comprobó el tamaño de las zonas")
    if len(items) != sum(EXPECTED.values()):
        errors.append(f"el catálogo tiene {len(items)} entradas, se esperaban {sum(EXPECTED.values())}")
    for key in ("id", "name", "file", "thumbnail"):
        values = [i.get(key) for i in items]
        dup = {v for v in values if values.count(v) > 1}
        if dup:
            errors.append(f"valores duplicados en '{key}': {sorted(dup)}")
    counts = {}
    for i in items:
        counts[i.get("category")] = counts.get(i.get("category"), 0) + 1
    if counts != EXPECTED:
        errors.append(f"reparto por categoría {counts}, se esperaba {EXPECTED}")

    print(f"{'id':26s} {'zonas':>5s} {'menor zona (px²)':>17s}  dificultad")
    for item in items:
        missing = [k for k in REQUIRED if not str(item.get(k) or "").strip()]
        if missing:
            errors.append(f"{item.get('id')}: faltan campos {missing}")
            continue
        if item["difficulty"] not in DIFFICULTIES:
            errors.append(f"{item['id']}: dificultad desconocida {item['difficulty']!r}")
        ok = True
        for key in ("file", "thumbnail"):
            rel = item.get(key)
            if not rel:
                continue
            p = ROOT / rel
            if Path(rel).is_absolute() or ".." in Path(rel).parts:
                errors.append(f"{item['id']}: ruta no relativa {rel}")
            if not SAFE_NAME.match(p.name):
                errors.append(f"{item['id']}: nombre de archivo no seguro {p.name}")
            if Path(rel).stem != item["id"]:
                errors.append(f"{item['id']}: el archivo {rel} no coincide con el id")
            if not p.is_file():
                errors.append(f"{item['id']}: no existe {rel}")
                ok = False
        if not ok:
            continue
        regions = check_svg(item)
        check_thumbnail(item)
        if preview_path(item).is_file():
            check_png(item)
        else:
            warnings.append(f"{item['id']}: falta la vista previa de control (node tools/render_previews.mjs)")
        smallest = check_areas(item, areas)
        print(f"{item['id']:26s} {regions:5d} {smallest if smallest is not None else '-':>17}  {item['difficulty']}")

    print()
    for w in warnings:
        print("AVISO:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"\n{len(items)} dibujos, {len(errors)} errores, {len(warnings)} avisos")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
