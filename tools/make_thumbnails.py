#!/usr/bin/env python3
"""Genera las miniaturas de la galería a partir de las vistas previas.

Cada miniatura es un PNG cuadrado de 512x512 en escala de grises, reducido con
filtro Lanczos desde el render de 1024x1024 (assets/previews/<id>.png), y se
guarda en la ruta del campo `thumbnail` del catálogo. Así la app no carga
imágenes de alta resolución en la galería.

Uso (desde la raíz del proyecto, después de node tools/render_previews.mjs):
    python3 tools/make_thumbnails.py
"""

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "assets" / "catalog" / "catalog.json"
SIZE = 512


def main():
    drawings = json.loads(CATALOG.read_text(encoding="utf-8"))["drawings"]
    total = 0
    for item in drawings:
        source = ROOT / "assets" / "previews" / f"{item['id']}.png"
        target = ROOT / item["thumbnail"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as img:
            thumb = img.convert("L").resize((SIZE, SIZE), Image.LANCZOS)
        thumb.save(target, optimize=True)
        total += target.stat().st_size
        print(f"{item['id']:26s} -> {item['thumbnail']} ({target.stat().st_size // 1024} KB)")
    print(f"\n{len(drawings)} miniaturas, {total // 1024} KB en total")


if __name__ == "__main__":
    main()
