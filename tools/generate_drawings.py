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
    ("animal_conejo", "Conejo", "animales", "animals", None, ""),
    ("animal_leon", "León", "animales", "animals", animals.leon,
     "Leoncito sentado con melena ondulada y cola con mechón."),
    ("animal_elefante", "Elefante", "animales", "animals", animals.elefante,
     "Elefante de frente con orejas grandes y trompa curvada."),
    ("animal_jirafa", "Jirafa", "animales", "animals", animals.jirafa,
     "Jirafa de perfil con cuello largo, cuernitos y manchas grandes."),
    ("animal_oso", "Oso", "animales", "animals", None, ""),
    ("animal_mariposa", "Mariposa", "animales", "animals", None, ""),
    ("animal_pez", "Pez", "animales", "animals", None, ""),
    ("animal_abeja", "Abeja", "animales", "animals", None, ""),
    ("animal_oruga", "Oruga", "animales", "animals", None, ""),
    ("animal_tortuga", "Tortuga", "animales", "animals", None, ""),
    # Convertida de «Catalogo Imagenes/» (sin función: ver FROM_IMAGES).
    ("animal_cebra", "Cebra", "animales", "animals", None,
     "Cebra tierna de pie con rayas, crin, orejas y cola con mechón."),
    ("animal_mono", "Mono", "animales", "animals", None, ""),
    ("granja_cerdito", "Cerdito", "granja", "farm", None, ""),
    ("granja_gallina", "Gallina", "granja", "farm", None, ""),
    ("granja_gallo", "Gallo", "granja", "farm", None, ""),
    ("granja_oveja", "Oveja", "granja", "farm", None, ""),
    ("granja_patito", "Patito", "granja", "farm", None, ""),
    ("granja_vaca", "Vaca", "granja", "farm", None, ""),
    ("granja_poni", "Poni", "granja", "farm", None, ""),
    ("mar_ballena", "Ballena", "mar", "sea", None, ""),
    ("mar_cangrejo", "Cangrejo", "mar", "sea", None, ""),
    ("mar_delfin", "Delfín", "mar", "sea", None, ""),
    ("mar_estrella", "Estrella de mar", "mar", "sea", None, ""),
    ("mar_pulpo", "Pulpo", "mar", "sea", None, ""),
    ("mar_tortuga", "Tortuga marina", "mar", "sea", None, ""),
    ("mar_caballito", "Caballito de mar", "mar", "sea", None, ""),
    ("vehiculo_automovil", "Automóvil", "vehiculos", "vehicles", None, ""),
    ("vehiculo_autobus", "Autobús", "vehiculos", "vehicles", None, ""),
    ("vehiculo_avion", "Avión", "vehiculos", "vehicles", None, ""),
    ("vehiculo_tren", "Tren", "vehiculos", "vehicles", None, ""),
    ("vehiculo_barco", "Barco", "vehiculos", "vehicles", None, ""),
    ("vehiculo_helicoptero", "Helicóptero", "vehiculos", "vehicles", None, ""),
    ("dinosaurio_01", "T-Rex", "dinosaurios", "dinosaurs", None, ""),
    ("dinosaurio_02", "Triceratops", "dinosaurios", "dinosaurs", None, ""),
    ("dinosaurio_03", "Estegosaurio", "dinosaurios", "dinosaurs", None, ""),
    ("dinosaurio_04", "Brontosaurio", "dinosaurios", "dinosaurs", None, ""),
    ("dinosaurio_05", "Bebé dinosaurio", "dinosaurios", "dinosaurs", dinosaurs.bebe_huevo,
     "Bebé dinosaurio saliendo del huevo con la cáscara en la cabeza."),
    ("dinosaurio_06", "Espinosaurio", "dinosaurios", "dinosaurs", None, ""),
    ("dinosaurio_07", "Pteranodonte", "dinosaurios", "dinosaurs", None, ""),
    ("dinosaurio_08", "Velociraptor", "dinosaurios", "dinosaurs", None, ""),
    ("fruta_manzana", "Manzana", "frutas", "fruits", None, ""),
    ("fruta_platano", "Plátano", "frutas", "fruits", None, ""),
    ("fruta_fresa", "Fresa", "frutas", "fruits", None, ""),
    ("fruta_naranja", "Naranja", "frutas", "fruits", None, ""),
    ("fruta_uvas", "Uvas", "frutas", "fruits", None, ""),
    ("fruta_pina", "Piña", "frutas", "fruits", None, ""),
    ("fruta_sandia", "Sandía", "frutas", "fruits", None, ""),
    ("fruta_cerezas", "Cerezas", "frutas", "fruits", None, ""),
    ("fantasia_hada", "Hada", "fantasia", "fantasy", None, ""),
    ("fantasia_hada_hongo", "Hada del hongo", "fantasia", "fantasy", None, ""),
    ("fantasia_robot", "Robot amigable", "fantasia", "fantasy", None, ""),
    ("fantasia_robot_heroe", "Robot héroe", "fantasia", "fantasy", None, ""),
    ("fantasia_dragon", "Dragón", "fantasia", "fantasy", None, ""),
    ("fantasia_unicornio", "Unicornio", "fantasia", "fantasy", None, ""),
    ("fantasia_grifo", "Grifo", "fantasia", "fantasy", None, ""),
    ("fantasia_zorro_alado", "Zorro alado", "fantasia", "fantasy", None, ""),
    ("fantasia_extraterrestre", "Pequeño extraterrestre", "fantasia", "fantasy", fantasy.extraterrestre,
     "Extraterrestre simpático con antenas, ojos grandes y dos estrellas."),
]


# Dibujos convertidos de «Catalogo Imagenes/» con tools/drawings_from_images.py:
# su SVG no se genera aquí (se conserva) y la descripción es la de la imagen.
FROM_IMAGES = {
    "animal_gato": "Gatito kawaii sentado con rayas en la frente, el lomo y la cola, y bigotes.",
    "animal_perro": "Perrito sentado con orejas caídas, lengua fuera, collar con placa y cola.",
    "animal_conejo": "Conejito sentado de frente con orejas largas, dientes, bigotes y patitas con almohadillas.",
    "animal_leon": "Leoncito sonriente con melena grande, orejas redondas y cola con mechón.",
    "animal_elefante": "Elefante bebé sentado con orejas grandes, trompa levantada y uñitas.",
    "animal_jirafa": "Jirafa de cuello largo con cuernitos, manchas redondas y cola con mechón.",
    "animal_tortuga": "Tortuga sonriente con caparazón de placas hexagonales y patitas.",
    "animal_cebra": "Cebra tierna de pie con rayas, crin, orejas y cola con mechón.",
    "animal_oso": "Osito de peluche sentado con hocico, barriga redonda y almohadillas en las patas.",
    "animal_mono": "Monito sentado con orejas redondas, cara sonriente y cola rizada.",
    "granja_vaca": "Vaca chibi con cuernitos, manchas, ubre y cola con mechón.",
    "granja_poni": "Poni sonriente de pie con crin y cola onduladas.",
    "fantasia_hada": "Hada con alas de mariposa y varita de estrella entre flores.",
    "fantasia_hada_hongo": "Hada risueña sentada sobre un hongo mágico con estrellas y flores.",
    "fantasia_robot": "Robot sonriente con el pulgar arriba, engranaje, cohete y nubes.",
    "fantasia_robot_heroe": "Robot héroe con un rayo en el pecho entre estrellas, planetas y nubes.",
    "granja_cerdito": "Cerdito sonriente de pie con orejas caídas, hocico grande y cola rizada.",
    "granja_gallina": "Gallina sonriente con cresta, ala grande y cola de plumas.",
    "granja_gallo": "Gallo con cresta, barbilla, ala y una cola de plumas largas y curvas.",
    "granja_oveja": "Ovejita de lana esponjosa con cara redonda, orejas caídas y patitas.",
    "granja_patito": "Patito sonriente con pico grande, ala y patas palmeadas.",
    "mar_ballena": "Ballena feliz con chorro de agua, cola levantada y olas.",
    "mar_cangrejo": "Cangrejo sonriente con dos pinzas grandes y ocho patitas.",
    "mar_delfin": "Delfín sonriente saltando del agua entre salpicaduras.",
    "mar_estrella": "Estrella de mar sonriente con cinco brazos llenos de puntitos.",
    "mar_pulpo": "Pulpo kawaii con ocho tentáculos ondulados y ventosas.",
    "dinosaurio_01": "Tiranosaurio sonriente con rayas, entre hierbas y rocas.",
    "dinosaurio_02": "Triceratops sonriente con gola, tres cuernos y manchas.",
    "dinosaurio_03": "Estegosaurio sonriente con placas en el lomo, entre rocas y hierba.",
    "dinosaurio_04": "Brontosaurio de cuello largo con montañas, nubes y una palmera.",
    "dinosaurio_06": "Espinosaurio con vela en el lomo junto a un volcán.",
    "dinosaurio_07": "Pteranodonte volando sobre un paisaje con volcanes y nubes.",
    "dinosaurio_08": "Velociraptor sonriente corriendo en un paisaje prehistórico.",
    "fantasia_dragon": "Dragoncito sentado con alas extendidas, cuernitos y cola en punta.",
    "fantasia_unicornio": "Unicornio alegre con cuerno, melena y cola ondulada y un corazón.",
    "fantasia_grifo": "Grifo amistoso, mitad águila y mitad león, con alas extendidas.",
    "fantasia_zorro_alado": "Zorrito con alas, cola esponjosa y estrellas.",
    "vehiculo_barco": "Barco sonriente con chimenea, ancla y salvavidas entre olas, nubes y sol.",
    "vehiculo_tren": "Trenecito feliz con locomotora y vagón sobre las vías, entre montañas.",
    "vehiculo_automovil": "Coche sonriente con ruedas grandes en la carretera, con árbol, nubes y sol.",
    "vehiculo_autobus": "Autobús sonriente con muchas ventanas en la carretera, con árbol y sol.",
    "vehiculo_avion": "Avión sonriente con ventanillas redondas volando entre nubes y sol.",
    "vehiculo_helicoptero": "Helicóptero sonriente con hélice grande y patines, en el cielo con nubes.",
    "animal_pez": "Pez sonriente con rayas y aletas en el fondo marino, con algas, concha y estrella.",
    "animal_mariposa": "Mariposa sonriente con alas de corazones y lunares en un jardín con flores.",
    "animal_abeja": "Abeja feliz con alas y rayas volando entre flores, con nubes y sol.",
    "animal_oruga": "Oruga sonriente de muchos segmentos sobre una hoja, entre flores.",
    "mar_tortuga": "Tortuga marina sonriente con caparazón de placas entre algas, conchas y burbujas.",
    "mar_caballito": "Caballito de mar kawaii con cola enroscada entre algas, corales y una estrella.",
    "fruta_manzana": "Manzana kawaii con tallo, hoja y brillo en un jardín con sol y nubes.",
    "fruta_platano": "Plátano feliz con tallo y punta entre arbustos, con sol y nubes.",
    "fruta_fresa": "Trío de fresas: una sonriente con semillas, otra cortada, hojas y una flor bajo el sol.",
    "fruta_naranja": "Naranjas sonrientes: una entera con tallo y hoja, otra cortada y una rodaja con gajos.",
    "fruta_uvas": "Racimo de uvas kawaii con hoja grande y zarcillo, entre arbustos y bajo el sol.",
    "fruta_pina": "Piña sonriente con corona de hojas y piel a cuadros, bajo el sol y las nubes.",
    "fruta_sandia": "Sandía kawaii entera con rayas y una tajada con pepitas bajo el sol.",
    "fruta_cerezas": "Dos cerezas kawaii unidas por el tallo, con hojas, una flor y el sol.",
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
