"""Fase 5: catálogo de pictogramas de «Quiero decir» (comunicación aumentativa).

Cada pictograma: id, categoría, texto (lo que se ve), texto para voz (el mismo
texto: lo que se ve es lo que se dice), ilustración, orden, activo, tipo
gramatical, artículo y referencias relacionadas (sugerencias del constructor).

Las ilustraciones son propias (caras, cuerpo, niños, dibujos del catálogo) o
pictogramas de Material (Apache 2.0). Este guion comprueba cada referencia y
escribe lib/aac/aac_icons.dart con los iconos que aún no conoce la app.

{o|a}: forma masculina o femenina, según el ajuste del adulto.

Uso: python3 tools/aac/pictograms.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "speech"))
from content_common import APPLE, BANANA, BOY, GIRL, GRAPES, ORANGE, STRAWBERRY, D, E, K  # noqa: E402

FLUTTER_ICONS = Path("/opt/sdk/flutter/packages/flutter/lib/src/material/icons.dart")


def M(name, color):
    return {"icon": name, "color": color}


IMG = "assets/images/quiero_decir/"


def I(name, icon, color):
    """Ilustración 3D (con el icono de reserva si no se puede abrir)."""
    return {"image": IMG + name + ".webp", "icon": icon, "color": color}


# Ilustraciones 3D de las tarjetas de categoría.
CATEGORY_IMAGES = {"comida": "comer", "personas": "nino", "juegos": "pelota",
                   "actividades": "pintar", "lugares": "casa"}


def B(part):
    return {"body": part}


CATEGORIES = [
    ("necesidades", "Necesidades básicas", "#4FC3F7", "pan_tool"),
    ("comida", "Comida y bebida", "#FFB74D", "restaurant"),
    ("emociones", "Emociones", "#F06292", "emoji_emotions"),
    ("personas", "Familia y personas", "#BA68C8", "family_restroom"),
    ("juegos", "Juegos", "#81C784", "toys"),
    ("actividades", "Actividades", "#4DB6AC", "directions_run"),
    ("lugares", "Lugares", "#7986CB", "place"),
    ("salud", "Salud y bienestar", "#E57373", "healing"),
    ("preguntas", "Preguntas y respuestas", "#FFD54F", "help_outline"),
    ("esenciales", "Palabras esenciales", "#90A4AE", "star"),
]

P = []


def add(cat, *rows):
    for row in rows:
        pid, text, pic, kind, *rest = row
        article = rest[0] if len(rest) > 0 else None
        related = rest[1] if len(rest) > 1 else []
        extra = rest[2] if len(rest) > 2 else {}
        P.append({"id": pid, "category": cat, "text": text, "speech": text, "picture": pic,
                  "kind": kind, "article": article, "related": related, **extra})


F = "frase"
# ───────────────── Necesidades básicas
add("necesidades",
    ("quiero_agua", "Quiero agua.", M("water_drop", "#039BE5"), F),
    ("tengo_hambre", "Tengo hambre.", M("restaurant", "#FB8C00"), F),
    ("tengo_sed", "Tengo sed.", M("local_drink", "#29B6F6"), F),
    ("necesito_ayuda", "Necesito ayuda.", M("pan_tool", "#E53935"), F),
    ("quiero_descansar", "Quiero descansar.", M("weekend", "#7E57C2"), F),
    ("tengo_sueno", "Tengo sueño.", M("bedtime", "#3949AB"), F),
    ("quiero_bano", "Quiero ir al baño.", M("wc", "#0288D1"), F),
    ("tengo_frio", "Tengo frío.", M("severe_cold", "#4FC3F7"), F),
    ("tengo_calor", "Tengo calor.", M("wb_sunny", "#FB8C00"), F),
    ("quiero_comer", "Quiero comer.", M("lunch_dining", "#FB8C00"), F),
    ("quiero_mama", "Quiero a mamá.", M("woman", "#E91E63"), F),
    ("quiero_casa", "Quiero ir a casa.", M("house", "#E57373"), F),
    ("necesito_abrazo", "Necesito un abrazo.", M("volunteer_activism", "#F06292"), F),
    ("quiero_lavarme", "Quiero lavarme las manos.", M("wash", "#29B6F6"), F),
    ("quiero_cambiarme", "Quiero cambiarme de ropa.", M("checkroom", "#7E57C2"), F),
    ("necesito_silencio", "Necesito silencio.", M("volume_off", "#546E7A"), F),
    ("quiero_salir", "Quiero salir.", M("door_front_door", "#8D6E63"), F),
    ("espera", "Espera, por favor.", M("hourglass_bottom", "#FFA000"), F),
    ("quiero_estar_solo", "Quiero estar sol{o|a} un ratito.", M("self_improvement", "#26A69A"), F),
)

N = "sustantivo"
# ───────────────── Comida y bebida
add("comida",
    ("agua", "agua", M("water_drop", "#039BE5"), N, None, ["mas", "terminado"]),
    ("leche", "leche", M("local_drink", "#90A4AE"), N, None),
    ("jugo", "jugo", M("local_drink", "#FB8C00"), N, None),
    ("pan", "pan", M("bakery_dining", "#D7A86E"), N, None),
    ("galleta", "galleta", M("cookie", "#8D6E63"), N, "una"),
    ("fruta", "fruta", ORANGE, N, None),
    ("manzana", "manzana", APPLE, N, "una"),
    ("platano", "plátano", BANANA, N, "un"),
    ("fresas", "fresas", STRAWBERRY, N, None),
    ("uvas", "uvas", GRAPES, N, None),
    ("sopa", "sopa", M("soup_kitchen", "#FB8C00"), N, None),
    ("arroz", "arroz", M("rice_bowl", "#8D6E63"), N, None),
    ("pizza", "pizza", M("local_pizza", "#F4511E"), N, None),
    ("fideos", "fideos", M("ramen_dining", "#FFB74D"), N, None),
    ("pescado", "pescado", M("set_meal", "#0288D1"), N, None),
    ("huevo", "huevo", M("egg", "#FBC02D"), N, "un"),
    ("helado", "helado", M("icecream", "#F48FB1"), N, "un"),
    ("ensalada", "ensalada", M("eco", "#43A047"), N, None),
    ("pastel", "pastel", M("cake", "#AB47BC"), N, None),
    ("desayuno", "desayuno", M("free_breakfast", "#6D4C41"), N, "el"),
    ("cena", "cena", M("restaurant_menu", "#5C6BC0"), N, "la"),
)

A = "adjetivo"
# ───────────────── Emociones
add("emociones",
    ("estoy_feliz", "Estoy feliz.", E("feliz"), F),
    ("estoy_contento", "Estoy content{o|a}.", K("feliz", False, BOY, True), F),
    ("estoy_triste", "Estoy triste.", E("triste"), F),
    ("estoy_enojado", "Estoy enojad{o|a}.", E("enojado"), F),
    ("tengo_miedo", "Tengo miedo.", E("asustado"), F),
    ("estoy_cansado", "Estoy cansad{o|a}.", E("cansado"), F),
    ("estoy_sorprendido", "Estoy sorprendid{o|a}.", E("sorprendido"), F),
    ("estoy_tranquilo", "Estoy tranquil{o|a}.", E("tranquilo"), F),
    ("estoy_aburrido", "Estoy aburrid{o|a}.", E("aburrido"), F),
    ("estoy_emocionado", "Estoy emocionad{o|a}.", E("emocionado"), F),
    ("estoy_nervioso", "Estoy nervios{o|a}.", M("sentiment_neutral", "#FFA726"), F),
    ("quiero_tranquilo", "Quiero estar tranquil{o|a}.", M("self_improvement", "#26A69A"), F),
    ("me_gusta_frase", "Me gusta.", M("thumb_up", "#43A047"), F),
    ("no_me_gusta_frase", "No me gusta.", M("thumb_down", "#E53935"), F),
    ("te_quiero", "Te quiero.", M("favorite", "#E91E63"), F),
    ("feliz", "feliz", E("feliz"), A),
    ("triste", "triste", E("triste"), A),
    ("enojado", "enojad{o|a}", E("enojado"), A),
    ("cansado", "cansad{o|a}", E("cansado"), A),
    ("asustado", "asustad{o|a}", E("asustado"), A),
    ("tranquilo", "tranquil{o|a}", E("tranquilo"), A),
)

PR = "pronombre"
# ───────────────── Familia y personas
add("personas",
    ("yo", "yo", I("nino", "emoji_people", "#26A69A"), PR, None, ["quiero", "estoy", "tengo", "necesito", "me_gusta"]),
    ("tu", "tú", M("person", "#7E57C2"), PR, None, ["quieres", "estas"]),
    ("el_persona", "él", M("boy", "#1E88E5"), PR, None),
    ("ella", "ella", M("girl", "#EC407A"), PR, None),
    ("nosotros", "nosotros", M("groups", "#FB8C00"), PR, None, ["vamos", "jugamos"]),
    ("mama", "mamá", M("woman", "#E91E63"), N, None),
    ("papa", "papá", M("man", "#1E88E5"), N, None),
    ("hermano", "hermano", K("feliz", False, "#81C784"), N, None),
    ("hermana", "hermana", K("feliz", True, "#FFB74D"), N, None),
    ("abuelo", "abuelo", M("elderly", "#6D4C41"), N, None),
    ("abuela", "abuela", M("elderly_woman", "#8E24AA"), N, None),
    ("bebe", "bebé", M("child_care", "#F48FB1"), N, "el"),
    ("maestra", "maestra", M("cast_for_education", "#00897B"), N, "la"),
    ("amigo", "amigo", M("face", "#42A5F5"), N, None),
    ("amiga", "amiga", M("face_3", "#EC407A"), N, None),
    ("familia", "familia", M("family_restroom", "#E91E63"), N, "la"),
    ("doctor", "doctor", M("medical_services", "#E53935"), N, "el"),
    ("perro", "perro", D("animal_perro"), N, "el"),
    ("gato", "gato", D("animal_gato"), N, "el"),
)

V = "verbo"
# ───────────────── Juegos
add("juegos",
    ("jugar", "jugar", M("toys", "#FB8C00"), V, None, ["con", "pelota", "bloques", "afuera"]),
    ("jugamos", "¿Jugamos?", M("sports_handball", "#43A047"), F),
    ("mi_turno", "Mi turno.", M("front_hand", "#1E88E5"), F),
    ("tu_turno", "Tu turno.", M("back_hand", "#EC407A"), F),
    ("pelota", "pelota", I("pelota", "sports_soccer", "#E53935"), N, "la"),
    ("bloques", "bloques", M("widgets", "#FFA000"), N, "los"),
    ("rompecabezas", "rompecabezas", M("extension", "#7E57C2"), N, "el"),
    ("coche", "coche", D("vehiculo_automovil"), N, "el"),
    ("tren", "tren", D("vehiculo_tren"), N, "el"),
    ("munecos", "muñecos", M("smart_toy", "#546E7A"), N, "los"),
    ("pintar", "pintar", I("pintar", "brush", "#AB47BC"), V),
    ("colorear", "colorear", M("palette", "#EC407A"), V),
    ("escondite", "escondite", M("visibility_off", "#5D4037"), N, "el"),
    ("musica", "música", M("music_note", "#AB47BC"), N, "la"),
    ("bailar", "bailar", M("nightlife", "#EC407A"), V),
    ("cantar", "cantar", M("mic", "#F06292"), V),
    ("cuento", "cuento", M("auto_stories", "#8E24AA"), N, "un"),
    ("columpio", "columpio", M("attractions", "#26A69A"), N, "el"),
    ("burbujas", "burbujas", M("bubble_chart", "#4FC3F7"), N, "las"),
)

# ───────────────── Actividades (verbos en infinitivo)
add("actividades",
    ("comer", "comer", I("comer", "lunch_dining", "#FB8C00"), V),
    ("beber", "beber", M("local_drink", "#29B6F6"), V, None, ["agua", "leche", "jugo"]),
    ("dormir", "dormir", M("bedtime", "#3949AB"), V),
    ("banarme", "bañarme", M("bathtub", "#29B6F6"), V),
    ("vestirme", "vestirme", M("checkroom", "#7E57C2"), V),
    ("lavarme_dientes", "lavarme los dientes", M("clean_hands", "#26C6DA"), V),
    ("leer", "leer", M("menu_book", "#8E24AA"), V, None, ["cuento"]),
    ("ver", "ver", M("visibility", "#1E88E5"), V, None, ["television", "cuento"]),
    ("television", "televisión", M("tv", "#455A64"), N, "la"),
    ("ir", "ir", M("directions_walk", "#43A047"), V, None, ["parque", "casa", "bano", "escuela"], {"takes_a": True}),
    ("salir", "salir", M("door_front_door", "#8D6E63"), V),
    ("pasear", "pasear", M("directions_walk", "#7CB342"), V),
    ("escuchar", "escuchar", M("hearing", "#7E57C2"), V, None, ["musica", "cuento"]),
    ("hablar", "hablar", M("record_voice_over", "#26A69A"), V),
    ("esperar", "esperar", M("hourglass_bottom", "#FFA000"), V),
    ("sentarme", "sentarme", M("chair", "#8D6E63"), V),
    ("abrir", "abrir", M("lock_open", "#43A047"), V),
    ("cerrar", "cerrar", M("lock", "#E53935"), V),
    ("ayudar", "ayudar", M("handshake", "#FB8C00"), V),
    ("guardar", "guardar", M("inventory_2", "#A1887F"), V),
    ("abrazar", "abrazar", M("favorite", "#F06292"), V),
)

# ───────────────── Lugares
PL = {"place": True}
add("lugares",
    ("casa", "casa", I("casa", "house", "#E57373"), N, None, [], PL),
    ("escuela", "escuela", M("school", "#5C9DED"), N, "la", [], PL),
    ("parque", "parque", M("park", "#43A047"), N, "el", [], PL),
    ("bano", "baño", M("wc", "#0288D1"), N, "el", [], PL),
    ("cocina", "cocina", M("kitchen", "#78909C"), N, "la", [], PL),
    ("cuarto", "cuarto", M("bed", "#5C6BC0"), N, "el", [], PL),
    ("jardin", "jardín", M("yard", "#43A047"), N, "el", [], PL),
    ("playa", "playa", M("beach_access", "#FFB300"), N, "la", [], PL),
    ("tienda", "tienda", M("storefront", "#FB8C00"), N, "la", [], PL),
    ("hospital", "hospital", M("local_hospital", "#E53935"), N, "el", [], PL),
    ("piscina", "piscina", M("pool", "#039BE5"), N, "la", [], PL),
    ("biblioteca", "biblioteca", M("local_library", "#8E24AA"), N, "la", [], PL),
    ("calle", "calle", M("signpost", "#78909C"), N, "la", [], PL),
    ("afuera", "afuera", M("forest", "#7CB342"), "palabra"),
    ("aqui", "aquí", M("place", "#E53935"), "palabra"),
)

# ───────────────── Salud y bienestar
add("salud",
    ("me_duele_aqui", "Me duele aquí.", M("healing", "#E53935"), F),
    ("me_duele", "me duele", M("healing", "#E53935"), V, None, ["cabeza", "barriga", "boca", "orejas", "pierna", "mano"]),
    ("cabeza", "cabeza", B("cabeza"), N, "la"),
    ("barriga", "barriga", E("enfermo"), N, "la"),
    ("boca", "boca", B("boca"), N, "la"),
    ("orejas", "orejas", B("orejas"), N, "las"),
    ("ojos", "ojos", B("ojos"), N, "los"),
    ("nariz", "nariz", B("nariz"), N, "la"),
    ("pierna", "pierna", B("piernas"), N, "la"),
    ("brazo", "brazo", B("brazos"), N, "el"),
    ("mano", "mano", B("manos"), N, "la"),
    ("pie", "pie", B("pies"), N, "el"),
    ("me_siento_mal", "Me siento mal.", E("enfermo"), F),
    ("estoy_enfermo", "Estoy enferm{o|a}.", E("enfermo"), F),
    ("me_cai", "Me caí.", M("personal_injury", "#E53935"), F),
    ("quiero_curita", "Quiero una curita.", M("healing", "#FFAB91"), F),
    ("me_pica", "Me pica.", M("pest_control", "#8D6E63"), F),
    ("necesito_descansar", "Necesito descansar.", M("hotel", "#5C6BC0"), F),
    ("dolor", "dolor", M("sick", "#E53935"), N, None),
)

Q = "pregunta"
# ───────────────── Preguntas y respuestas
add("preguntas",
    ("que", "¿Qué?", M("help_outline", "#FFA000"), Q),
    ("donde", "¿Dónde?", M("place", "#E53935"), Q),
    ("quien", "¿Quién?", M("person_search", "#7E57C2"), Q),
    ("cuando", "¿Cuándo?", M("schedule", "#1E88E5"), Q),
    ("por_que", "¿Por qué?", M("psychology_alt", "#26A69A"), Q),
    ("como", "¿Cómo?", M("lightbulb", "#FBC02D"), Q),
    ("que_es_esto", "¿Qué es esto?", M("search", "#3949AB"), F),
    ("donde_mama", "¿Dónde está mamá?", M("woman", "#E91E63"), F),
    ("puedo_jugar", "¿Puedo jugar?", M("toys", "#FB8C00"), F),
    ("me_ayudas", "¿Me ayudas?", M("pan_tool", "#E53935"), F),
    ("no_se", "No sé.", M("question_mark", "#90A4AE"), F),
    ("no_entiendo", "No entiendo.", M("psychology", "#5C6BC0"), F),
    ("otra_vez", "Otra vez.", M("replay", "#26A69A"), F),
    ("si_por_favor", "Sí, por favor.", M("thumb_up", "#43A047"), F),
    ("no_gracias", "No, gracias.", M("do_not_disturb_on", "#E53935"), F),
    ("gracias", "Gracias.", M("favorite", "#E91E63"), F),
    ("por_favor", "Por favor.", M("emoji_people", "#26A69A"), F),
    ("hola", "Hola.", M("waving_hand", "#FFB300"), F),
    ("adios", "Adiós.", M("waving_hand", "#7E57C2"), F),
)

W = "palabra"
DET = "determinante"
PREP = "preposicion"
# ───────────────── Palabras esenciales
add("esenciales",
    ("si", "sí", M("check_circle", "#43A047"), W),
    ("no", "no", M("cancel", "#E53935"), W, None, ["quiero", "me_gusta"]),
    ("mas", "más", M("add_circle", "#1E88E5"), W, None, ["agua", "comer", "jugar"]),
    ("terminado", "terminé", M("done_all", "#43A047"), W),
    ("para", "para", M("pan_tool", "#E53935"), W),
    ("ayuda", "ayuda", M("support", "#E53935"), N, None),
    ("quiero", "quiero", M("front_hand", "#FB8C00"), V, None, ["agua", "comer", "jugar", "ir", "descansar_v", "mama"]),
    ("no_quiero", "no quiero", M("do_not_touch", "#E53935"), V, None, ["comer", "dormir", "jugar"]),
    ("quieres", "quieres", M("front_hand", "#7E57C2"), V, None, ["jugar", "comer"]),
    ("necesito", "necesito", M("priority_high", "#E53935"), V, None, ["ayuda", "agua", "descansar_v", "bano"]),
    ("tengo", "tengo", M("back_hand", "#26A69A"), V, None, ["hambre", "sed", "sueno", "frio", "dolor"]),
    ("estoy", "estoy", M("accessibility_new", "#26A69A"), V, None, ["feliz", "triste", "cansado", "enojado", "tranquilo"]),
    ("estas", "estás", M("accessibility_new", "#7E57C2"), V, None, ["feliz", "triste", "cansado"]),
    ("me_gusta", "me gusta", M("thumb_up", "#43A047"), V, None, ["jugar", "musica", "pelota", "pizza"]),
    ("no_me_gusta", "no me gusta", M("thumb_down", "#E53935"), V),
    ("vamos", "vamos", M("directions_run", "#43A047"), V, None, ["parque", "casa", "jugar"], {"takes_a": True}),
    ("descansar_v", "descansar", M("weekend", "#7E57C2"), V),
    ("hambre", "hambre", M("restaurant", "#FB8C00"), N, None),
    ("sed", "sed", M("local_drink", "#29B6F6"), N, None),
    ("sueno", "sueño", M("bedtime", "#3949AB"), N, None),
    ("frio", "frío", M("severe_cold", "#4FC3F7"), N, None),
    ("mi", "mi", M("emoji_people", "#26A69A"), DET, None, ["perro", "gato", "mama", "papa", "pelota"]),
    ("tu_det", "tu", M("person", "#7E57C2"), DET),
    ("con", "con", M("join_inner", "#5C6BC0"), PREP, None, ["mi", "mama", "papa", "amigo", "pelota"]),
    ("a", "a", M("arrow_forward", "#43A047"), PREP, None, ["parque", "casa", "escuela"]),
    ("en", "en", M("place", "#7986CB"), PREP),
    ("y", "y", M("add", "#90A4AE"), "conjuncion"),
    ("ahora", "ahora", M("alarm", "#E53935"), W),
    ("despues", "después", M("update", "#1E88E5"), W),
    ("tambien", "también", M("library_add", "#26A69A"), W),
)

BOARDS = {
    # Tablero rápido: palabras esenciales que no se pueden ocultar.
    "quick": ["si", "no", "ayuda", "agua", "bano", "comer", "dolor", "mas", "terminado", "para", "quiero", "no_quiero"],
    # Emociones y necesidades.
    "feelings": ["estoy_feliz", "estoy_contento", "estoy_triste", "tengo_miedo", "estoy_enojado", "estoy_cansado",
                 "estoy_tranquilo", "estoy_nervioso", "necesito_abrazo", "quiero_tranquilo", "necesito_descansar",
                 "me_duele_aqui", "me_siento_mal", "tengo_hambre", "tengo_sed", "quiero_bano", "necesito_ayuda",
                 "quiero_estar_solo"],
    # Lo primero que propone el constructor.
    "start": ["yo", "quiero", "no_quiero", "necesito", "estoy", "tengo", "me_duele", "me_gusta", "vamos", "mas", "no"],
}

# «Aprendo a comunicarme con Lolo»: (pregunta, respuesta, otras dos).
LEARN = [
    ("¿Cómo pedirías agua?", "quiero_agua", ["estoy_feliz", "me_cai"]),
    ("¿Cómo puedes decir que necesitas ayuda?", "necesito_ayuda", ["te_quiero", "tengo_frio"]),
    ("¿Cómo dices que quieres ir al baño?", "quiero_bano", ["quiero_comer", "hola"]),
    ("¿Cómo dices que tienes hambre?", "tengo_hambre", ["tengo_sueno", "otra_vez"]),
    ("¿Cómo dices que algo te duele?", "me_duele_aqui", ["me_gusta_frase", "gracias"]),
    ("¿Cómo dices que estás triste?", "estoy_triste", ["estoy_feliz", "tengo_calor"]),
    ("¿Cómo dices que quieres descansar?", "quiero_descansar", ["quiero_salir", "jugamos"]),
    ("¿Cómo dices que no entiendes?", "no_entiendo", ["si_por_favor", "adios"]),
    ("¿Cómo saludas?", "hola", ["adios", "espera"]),
    ("¿Cómo das las gracias?", "gracias", ["no_se", "me_pica"]),
    ("¿Cómo pides que pare?", "para", ["mas", "si"]),
    ("¿Cómo dices que ya terminaste?", "terminado", ["ahora", "mas"]),
    ("¿Cómo pides un abrazo?", "necesito_abrazo", ["necesito_silencio", "tengo_frio"]),
    ("¿Cómo dices que tienes sueño?", "tengo_sueno", ["tengo_sed", "estoy_feliz"]),
]


def material_names():
    return set(re.findall(r"static const IconData (\w+) =", FLUTTER_ICONS.read_text()))


def known_names():
    text = (ROOT / "lib/speech/speech_content.dart").read_text()
    block = text[text.index("abstract final class SpeechIcons"):]
    known = set(re.findall(r"'(\w+)': Icons\.", block))
    extra = (ROOT / "lib/speech/speech_icons_extra.dart").read_text()
    return known | set(re.findall(r"'(\w+)': Icons\.", extra))


def main():
    material, known = material_names(), known_names()
    ids = [p["id"] for p in P]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    idset = set(ids)
    need = set()
    for order, p in enumerate(P, start=1):
        p["order"] = order
        p["active"] = True
        for r in p["related"]:
            assert r in idset, (p["id"], r)
        icon = p["picture"].get("icon")
        if icon and icon not in known:
            assert icon in material, f"icono inexistente: {icon}"
            need.add(icon)
        image = p["picture"].get("image")
        if image:
            assert (ROOT / image).is_file(), image
        drawing = p["picture"].get("drawing")
        if drawing:
            assert any((ROOT / "assets/drawings").rglob(f"{drawing}.svg")), drawing
    for cat, name in CATEGORY_IMAGES.items():
        assert any(c[0] == cat for c in CATEGORIES), cat
        assert (ROOT / IMG / f"{name}.webp").is_file(), name
    for _, _, _, icon in CATEGORIES:
        if icon not in known:
            assert icon in material, icon
            need.add(icon)
    for board, items in BOARDS.items():
        for i in items:
            assert i in idset, (board, i)
    for q, a, others in LEARN:
        for i in (a, *others):
            assert i in idset, (q, i)
    data = {
        "format_version": 1,
        "categories": [{"id": i, "name": n, "color": c, "icon": ic, "order": k,
                        **({"image": IMG + CATEGORY_IMAGES[i] + ".webp"} if i in CATEGORY_IMAGES else {})}
                       for k, (i, n, c, ic) in enumerate(CATEGORIES, start=1)],
        "pictograms": [{**p, "color": next(c for i, _, c, _ in CATEGORIES if i == p["category"])} for p in P],
        "boards": BOARDS,
        "learn": [{"question": q, "answer": a, "others": o} for q, a, o in LEARN],
    }
    (ROOT / "assets/aac/pictograms.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lines = ["// GENERADO por tools/aac/pictograms.py: no editar a mano.",
             "import 'package:flutter/material.dart';", "",
             "/// Pictogramas de Material que usa «Quiero decir» (fase 5).",
             "const aacIcons = <String, IconData>{",
             *[f"  '{n}': Icons.{n}," for n in sorted(need)], "};", ""]
    (ROOT / "lib/aac/aac_icons.dart").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "lib/aac/aac_icons.dart").write_text("\n".join(lines))
    per = {}
    for p in P:
        per[p["category"]] = per.get(p["category"], 0) + 1
    print(len(P), "pictogramas", per, len(need), "iconos nuevos")


if __name__ == "__main__":
    main()
