#!/usr/bin/env python3
"""Genera los dibujos SVG de la colección inicial y el catálogo JSON.

Uso (desde la raíz del proyecto):
    python3 tools/generate_drawings.py
    node tools/render_previews.mjs      # PNG 1024x1024 de vista previa (control de calidad)
    python3 tools/make_thumbnails.py    # miniaturas 512x512 que usa la app
    python3 tools/validate_assets.py    # control de calidad
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from drawing_lib import build  # noqa: E402
from drawings import animals, dinosaurs, fantasy, fruits, vehicles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DRAWINGS_DIR = ROOT / "assets" / "drawings"
CATALOG = ROOT / "assets" / "catalog" / "catalog.json"

# (id, nombre, categoría, carpeta, función, descripción)
DRAWINGS = [
    ("animal_gato", "Gato", "animales", "animals", animals.gato,
     "Gatito sentado de frente con orejas puntiagudas, bigotes y cola curvada."),
    ("animal_perro", "Perro", "animales", "animals", animals.perro,
     "Perrito sonriente con orejas caídas, lengua afuera, collar y placa."),
    ("animal_conejo", "Conejo", "animales", "animals", animals.conejo,
     "Conejito de orejas largas con dientes, patitas y cola redonda."),
    ("animal_leon", "León", "animales", "animals", animals.leon,
     "Leoncito sentado con melena ondulada y cola con mechón."),
    ("animal_elefante", "Elefante", "animales", "animals", animals.elefante,
     "Elefante de frente con orejas grandes y trompa curvada."),
    ("animal_jirafa", "Jirafa", "animales", "animals", animals.jirafa,
     "Jirafa de perfil con cuello largo, cuernitos y manchas grandes."),
    ("animal_oso", "Oso", "animales", "animals", animals.oso,
     "Osito sentado con orejas redondas, barriga y plantas de las patas."),
    ("animal_mariposa", "Mariposa", "animales", "animals", animals.mariposa,
     "Mariposa simétrica con cuatro alas, manchas redondas y antenas."),
    ("animal_pez", "Pez", "animales", "animals", animals.pez,
     "Pez de perfil con aletas, franjas, ojo grande y burbujas."),
    ("animal_tortuga", "Tortuga", "animales", "animals", animals.tortuga,
     "Tortuga sonriente de perfil con caparazón de placas grandes."),
    # Convertida de «Catalogo Imagenes/» (sin función: ver FROM_IMAGES).
    ("animal_cebra", "Cebra", "animales", "animals", None,
     "Cebra tierna de pie con rayas, crin, orejas y cola con mechón."),
    ("vehiculo_automovil", "Automóvil", "vehiculos", "vehicles", vehicles.automovil,
     "Coche de perfil con dos ventanas, puerta, faro y ruedas grandes."),
    ("vehiculo_autobus", "Autobús", "vehiculos", "vehicles", vehicles.autobus,
     "Autobús de perfil con cuatro ventanas, parabrisas y franja lateral."),
    ("vehiculo_avion", "Avión", "vehiculos", "vehicles", vehicles.avion,
     "Avión sonriente con ventanillas redondas, alas y dos nubes."),
    ("vehiculo_tren", "Tren", "vehiculos", "vehicles", vehicles.tren,
     "Locomotora de vapor con chimenea, humo, cabina y tres ruedas."),
    ("vehiculo_barco", "Barco", "vehiculos", "vehicles", vehicles.barco,
     "Velero con dos velas, bandera, casco con franja, olas y sol."),
    ("dinosaurio_01", "Rex sonriente", "dinosaurios", "dinosaurs", dinosaurs.rex,
     "Pequeño tiranosaurio amigable de perfil con brazitos cortos y manchas."),
    ("dinosaurio_02", "Triceratops", "dinosaurios", "dinosaurs", dinosaurs.triceratops,
     "Triceratops sonriente con gola ondulada y tres cuernos redondeados."),
    ("dinosaurio_03", "Estegosaurio", "dinosaurios", "dinosaurs", dinosaurs.estegosaurio,
     "Estegosaurio con cinco placas en el lomo y cola con púas suaves."),
    ("dinosaurio_04", "Braquiosaurio", "dinosaurios", "dinosaurs", dinosaurs.braquiosaurio,
     "Dinosaurio de cuello muy largo con manchas redondas."),
    ("dinosaurio_05", "Bebé dinosaurio", "dinosaurios", "dinosaurs", dinosaurs.bebe_huevo,
     "Bebé dinosaurio saliendo del huevo con la cáscara en la cabeza."),
    ("fruta_manzana", "Manzana", "frutas", "fruits", fruits.manzana,
     "Manzana sonriente con tallo, hoja y brillo."),
    ("fruta_platano", "Plátano", "frutas", "fruits", fruits.platano,
     "Plátano curvado y sonriente con tallo y punta."),
    ("fruta_fresa", "Fresa", "frutas", "fruits", fruits.fresa,
     "Fresa sonriente con corona de hojas, tallo y semillas."),
    ("fruta_naranja", "Naranja", "frutas", "fruits", fruits.naranja,
     "Naranja redonda y sonriente con tallo, hoja y brillo."),
    ("fruta_uvas", "Uvas", "frutas", "fruits", fruits.uvas,
     "Racimo de diez uvas grandes con tallo y hoja."),
    ("fantasia_hada", "Hada", "fantasia", "fantasy", fantasy.hada,
     "Hada pequeña con cuatro alas, vestido acampanado y varita de estrella."),
    ("fantasia_robot", "Robot amigable", "fantasia", "fantasy", fantasy.robot,
     "Robot que saluda, con antena, panel con corazón y pies grandes."),
    ("fantasia_dragon", "Dragón sonriente", "fantasia", "fantasy", fantasy.dragon,
     "Dragoncito sentado con alas, cuernitos y cola terminada en corazón."),
    ("fantasia_unicornio", "Unicornio", "fantasia", "fantasy", fantasy.unicornio,
     "Unicornio de perfil con cuerno, melena, cola ondulada y ojo feliz."),
    ("fantasia_extraterrestre", "Pequeño extraterrestre", "fantasia", "fantasy", fantasy.extraterrestre,
     "Extraterrestre simpático con antenas, ojos grandes y dos estrellas."),
]


# Dibujos convertidos de «Catalogo Imagenes/» con tools/drawings_from_images.py:
# su SVG no se genera aquí (se conserva) y la descripción es la de la imagen.
FROM_IMAGES = {
    "animal_gato": "Gatito kawaii sentado con orejas puntiagudas, bigotes, barriga y cola curvada.",
    "animal_perro": "Perrito sonriente con orejas caídas, mancha en el ojo, collar con placa y cola.",
    "animal_conejo": "Conejito de orejas largas con dientes, bigotes, patitas y cola redonda.",
    "animal_leon": "Leoncito tierno con melena ondulada, orejas redondas y cola con mechón.",
    "animal_elefante": "Elefante kawaii sentado con orejas grandes y trompa curvada.",
    "animal_jirafa": "Jirafa de cuello largo con cuernitos, manchas redondas y cola con mechón.",
    "animal_tortuga": "Tortuga sonriente con caparazón de placas, patitas y cola.",
    "animal_cebra": "Cebra tierna de pie con rayas, crin, orejas y cola con mechón.",
}


def difficulty(regions):
    """Dificultad según el número de zonas para colorear (sin contar el fondo)."""
    if regions <= 12:
        return "facil", "4-5"
    if regions <= 20:
        return "media", "5-6"
    return "dificil", "6-7"


def main():
    catalog = []
    for did, name, category, folder, func, desc in DRAWINGS:
        out = DRAWINGS_DIR / folder / f"{did}.svg"
        if did in FROM_IMAGES:
            # Regiones del SVG convertido (sin contar el fondo).
            regions = out.read_text(encoding="utf-8").count('class="region"') - 1
            desc = FROM_IMAGES[did]
        else:
            drawing = build(func)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(drawing.to_svg(did), encoding="utf-8")
            regions = len(drawing.regions)
        diff, age = difficulty(regions)
        catalog.append({
            "id": did,
            "name": name,
            "category": category,
            "file": f"assets/drawings/{folder}/{did}.svg",
            "thumbnail": f"assets/thumbnails/{did}.png",
            "difficulty": diff,
            "recommended_age": age,
            "regions": regions,
            "description": desc,
        })
        print(f"{did:26s} {regions:3d} zonas  {diff}")
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 2,
        "collection": "Pequeños Artistas - colección inicial",
        "canvas": {"width": 1024, "height": 1024},
        "drawings": catalog,
    }
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(catalog)} dibujos -> {CATALOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
