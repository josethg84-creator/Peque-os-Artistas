"""«Aprendo a leer» · Fase 4: «Completa las palabras».

Genera assets/reading/complete_words.json con el catálogo de palabras y sus
ejercicios. Valida:
- la separación silábica de cada palabra con el silabeador (syllabify.py);
- el nivel según reglas fijas (1: dos sílabas directas; 2: tres o más sílabas
  sin grupos consonánticos ni diptongos; 3: sílabas trabadas, diptongos o
  palabras de una sílaba);
- que cada ejercicio tenga UNA sola respuesta correcta: ninguna opción falsa,
  puesta en el hueco, forma otra palabra conocida (del catálogo o del
  vocabulario de «Aprendo a Hablar»);
- que las opciones sean sílabas posibles en español y no se repitan.

Imágenes: «picture» es un dibujo o icono de la app que representa la palabra
sin ambigüedad; si no lo hay, la palabra queda pendiente de ilustración y no
entra en los juegos (se lista en assets/images/aprendo_leer/palabras/README.md).

Uso: python3 tools/reading/words.py
"""

import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from syllabify import split  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WORD_IMAGES = "assets/images/aprendo_leer/palabras"
AUDIO = "assets/audio/reading/palabras"


def D(d):
    return {"drawing": d}


def I(i):
    return {"icon": i}


def B(b):
    return {"body": b}


def S(color):
    return {"swatch": color}


P = None  # imagen pendiente

# (id, palabra, categoría, imagen)
WORDS = [
    # Animales
    ("pato", "pato", "animales", D("granja_patito")),
    ("sapo", "sapo", "animales", P),
    ("gato", "gato", "animales", D("animal_gato")),
    ("puma", "puma", "animales", P),
    ("mono", "mono", "animales", D("animal_mono")),
    ("vaca", "vaca", "animales", D("granja_vaca")),
    ("poni", "poni", "animales", D("granja_poni")),
    ("oso", "oso", "animales", D("animal_oso")),
    ("foca", "foca", "animales", P),
    ("loro", "loro", "animales", {"lolo": True}),
    ("perro", "perro", "animales", D("animal_perro")),
    ("gallo", "gallo", "animales", D("granja_gallo")),
    ("burro", "burro", "animales", P),
    ("abeja", "abeja", "animales", D("animal_abeja")),
    ("conejo", "conejo", "animales", D("animal_conejo")),
    ("jirafa", "jirafa", "animales", D("animal_jirafa")),
    ("oruga", "oruga", "animales", D("animal_oruga")),
    ("oveja", "oveja", "animales", D("granja_oveja")),
    ("gallina", "gallina", "animales", D("granja_gallina")),
    ("ballena", "ballena", "animales", D("mar_ballena")),
    ("elefante", "elefante", "animales", D("animal_elefante")),
    ("mariposa", "mariposa", "animales", D("animal_mariposa")),
    ("tortuga", "tortuga", "animales", D("animal_tortuga")),
    ("cebra", "cebra", "animales", D("animal_cebra")),
    ("pulpo", "pulpo", "animales", D("mar_pulpo")),
    ("delfin", "delfín", "animales", D("mar_delfin")),
    ("cangrejo", "cangrejo", "animales", D("mar_cangrejo")),
    ("cerdito", "cerdito", "animales", D("granja_cerdito")),
    ("dinosaurio", "dinosaurio", "animales", D("dinosaurio_01")),
    ("dragon", "dragón", "fantasía", D("fantasia_dragon")),
    ("hada", "hada", "fantasía", D("fantasia_hada")),
    ("robot", "robot", "juguetes", D("fantasia_robot")),
    ("unicornio", "unicornio", "fantasía", D("fantasia_unicornio")),
    # Frutas y comida
    ("pina", "piña", "comida", D("fruta_pina")),
    ("uvas", "uvas", "comida", D("fruta_uvas")),
    ("fresa", "fresa", "comida", D("fruta_fresa")),
    ("manzana", "manzana", "comida", D("fruta_manzana")),
    ("naranja", "naranja", "comida", D("fruta_naranja")),
    ("platano", "plátano", "comida", D("fruta_platano")),
    ("sandia", "sandía", "comida", D("fruta_sandia")),
    ("cereza", "cereza", "comida", D("fruta_cerezas")),
    ("helado", "helado", "comida", I("icecream")),
    ("huevo", "huevo", "comida", I("egg")),
    ("galleta", "galleta", "comida", I("cookie")),
    ("pizza", "pizza", "comida", I("pizza")),
    ("sopa", "sopa", "comida", I("soup")),
    ("queso", "queso", "comida", P),
    ("tomate", "tomate", "comida", P),
    ("fruta", "fruta", "comida", P),
    ("pan", "pan", "comida", I("bread")),
    # Casa y objetos
    ("mesa", "mesa", "casa", I("table")),
    ("casa", "casa", "casa", I("home")),
    ("cama", "cama", "casa", I("bed")),
    ("silla", "silla", "casa", I("chair")),
    ("taza", "taza", "casa", I("local_cafe")),
    ("vaso", "vaso", "casa", I("glass")),
    ("cuna", "cuna", "casa", I("crib")),
    ("foco", "foco", "casa", I("lamp")),
    ("llave", "llave", "casa", I("key")),
    ("ducha", "ducha", "casa", I("shower")),
    ("puerta", "puerta", "casa", I("door")),
    ("ventana", "ventana", "casa", I("window")),
    ("reloj", "reloj", "casa", I("clock")),
    ("tijera", "tijera", "casa", I("content_cut")),
    ("telefono", "teléfono", "casa", I("phone")),
    ("camara", "cámara", "casa", I("camera")),
    ("maleta", "maleta", "casa", P),
    ("moneda", "moneda", "casa", P),
    ("plato", "plato", "casa", P),
    ("cuchara", "cuchara", "casa", P),
    # Escuela y juguetes
    ("libro", "libro", "escuela", I("book")),
    ("lapiz", "lápiz", "escuela", I("pencil")),
    ("mochila", "mochila", "escuela", I("backpack")),
    ("escuela", "escuela", "escuela", I("school")),
    ("mapa", "mapa", "escuela", I("map")),
    ("pelota", "pelota", "juguetes", I("ball")),
    ("globo", "globo", "juguetes", P),
    ("regalo", "regalo", "juguetes", I("gift")),
    ("bicicleta", "bicicleta", "juguetes", I("bike")),
    ("moto", "moto", "transporte", P),
    # Transporte
    ("tren", "tren", "transporte", D("vehiculo_tren")),
    ("barco", "barco", "transporte", D("vehiculo_barco")),
    ("avion", "avión", "transporte", D("vehiculo_avion")),
    ("carro", "carro", "transporte", D("vehiculo_automovil")),
    ("autobus", "autobús", "transporte", D("vehiculo_autobus")),
    ("helicoptero", "helicóptero", "transporte", D("vehiculo_helicoptero")),
    ("semaforo", "semáforo", "transporte", I("traffic")),
    # Naturaleza
    ("luna", "luna", "naturaleza", I("moon")),
    ("sol", "sol", "naturaleza", I("sun")),
    ("nube", "nube", "naturaleza", I("cloud")),
    ("flor", "flor", "naturaleza", I("flower")),
    ("arbol", "árbol", "naturaleza", I("tree")),
    ("montana", "montaña", "naturaleza", I("mountain")),
    ("paraguas", "paraguas", "naturaleza", I("umbrella")),
    ("estrella", "estrella", "naturaleza", I("star")),
    ("corazon", "corazón", "naturaleza", I("heart")),
    # Cuerpo
    ("boca", "boca", "cuerpo", B("boca")),
    ("pelo", "pelo", "cuerpo", B("pelo")),
    ("nariz", "nariz", "cuerpo", B("nariz")),
    ("cabeza", "cabeza", "cuerpo", B("cabeza")),
    ("brazo", "brazo", "cuerpo", B("brazos")),
    ("pie", "pie", "cuerpo", B("pies")),
    ("mano", "mano", "cuerpo", P),
    # Colores
    ("rojo", "rojo", "colores", S("#E53935")),
    ("rosa", "rosa", "colores", S("#F48FB1")),
    ("azul", "azul", "colores", S("#1E88E5")),
    ("verde", "verde", "colores", S("#43A047")),
    ("negro", "negro", "colores", S("#212121")),
    ("blanco", "blanco", "colores", S("#FFFFFF")),
    ("morado", "morado", "colores", S("#8E24AA")),
    ("amarillo", "amarillo", "colores", S("#FDD835")),
    # Personas
    ("nino", "niño", "personas", {"kid": {"girl": False, "emotion": "feliz"}}),
    ("nina", "niña", "personas", {"kid": {"girl": True, "emotion": "feliz", "shirt": "#EC407A"}}),
    ("bebe", "bebé", "personas", I("child_care")),
    ("mama", "mamá", "personas", P),
    ("papa", "papá", "personas", P),
    ("zapato", "zapato", "ropa", P),
    ("camisa", "camisa", "ropa", P),
]

VOWELS = "aeiouáéíóú"
CLUSTERS = {"pl", "bl", "cl", "gl", "fl", "pr", "br", "tr", "dr", "cr", "gr", "fr"}
ONSETS = ["", "b", "c", "ch", "d", "f", "g", "j", "l", "ll", "m", "n", "ñ", "p", "r", "rr", "s", "t", "v", "z",
          "pl", "bl", "cl", "gl", "fl", "pr", "br", "tr", "dr", "cr", "gr", "fr"]


def plain(s):
    return s.lower().translate(str.maketrans("áéíóú", "aeiou"))


def is_open_simple(syl):
    """Sílaba directa: (consonante o dígrafo) + una vocal."""
    return re.fullmatch(r"(ch|ll|rr|qu|gu|[bcdfghjklmnñprstvyz])?[aeiouáéíóú]", syl.lower()) is not None


def has_cluster(syl):
    s = plain(syl)
    return any(s.startswith(c) for c in CLUSTERS)


def has_diphthong(syl):
    s = plain(syl).replace("qu", "q").replace("gu", "g")
    return sum(1 for ch in s if ch in "aeiou") >= 2


def level_of(parts):
    if len(parts) == 1 or any(has_cluster(p) or has_diphthong(p) for p in parts):
        return 3
    if len(parts) == 2 and all(is_open_simple(p) for p in parts):
        return 1
    if len(parts) >= 3:
        return 2
    return 3  # dos sílabas con alguna cerrada (u-vas, pan-…)


def valid_spelling(syl):
    """Ortografía posible en español para una sílaba inventada."""
    s = syl.lower()
    if re.search(r"c[ei]|g[ei]|z[ei]|k|q(?!u)|qu[aou]|gu[aou]", s):
        return False
    return split(s) == [s]


SIMPLE_ONSETS = ["b", "c", "d", "f", "g", "j", "l", "m", "n", "p", "r", "s", "t", "v"]
DIGRAPHS = {"ch", "ll", "rr", "qu", "gu"}


def parts_of(syl):
    """(inicio, vocales, final) de una sílaba (sin tildes)."""
    a = plain(syl)
    for d in ("qu", "gu"):
        if a.startswith(d) and len(a) > 2 and a[2] in "ei":
            m = re.fullmatch(r"([aeiou]+)([^aeiou]*)", a[2:])
            return (d, m.group(1), m.group(2)) if m else None
    m = re.fullmatch(r"([^aeiou]*)([aeiou]+)([^aeiou]*)", a)
    return m.groups() if m else None


def sound(syl):
    """Cómo suena en español latinoamericano (seseo y yeísmo): para no poner
    dos opciones que se oyen igual (SA / ZA, BA / VA, LLA / YA)."""
    s = plain(syl)
    s = re.sub(r"qu(?=[ei])", "k", s)
    s = re.sub(r"gu(?=[ei])", "g", s)
    s = re.sub(r"c(?=[ei])", "s", s)
    s = re.sub(r"g(?=[ei])", "j", s)
    s = s.replace("c", "k").replace("z", "s").replace("v", "b").replace("ll", "y").replace("h", "")
    return s


def candidate_syllables(answer):
    """Sílabas de la MISMA forma que [answer] (sin inicio, inicio simple o
    grupo consonántico; mismas vocales y mismo final), con otro sonido."""
    p = parts_of(answer)
    if not p:
        return []
    onset, nucleus, coda = p
    if onset == "":
        singles = [v + coda for v in "aeiou" if v != nucleus]
        diphthongs = [d + coda for d in ("ai", "ei", "oi", "au", "eu") if d != nucleus]
        pool = singles if len(nucleus) == 1 else diphthongs
    elif onset in CLUSTERS:
        pool = [c + nucleus + coda for c in sorted(CLUSTERS)]
    else:
        pool = [c + nucleus + coda for c in SIMPLE_ONSETS]
    target = sound(answer)
    out, sounds = [], set()
    for c in pool:
        if not valid_spelling(c) or sound(c) == target or sound(c) in sounds:
            continue
        sounds.add(sound(c))
        out.append(c)
    return out


def known_words():
    words = {plain(w[1]) for w in WORDS}
    for f in ("words.json", "vocabulary.json"):
        data = json.loads((ROOT / "assets/speech" / f).read_text(encoding="utf-8"))
        items = data["words"] if "words" in data else [w for c in data["categories"] for w in c["words"]]
        for w in items:
            words.add(plain(w["text"]))
    # Palabras comunes que no están en el vocabulario (para no crear respuestas
    # dudosas como PA-TO / GA-TO / RA-TO).
    words |= {"rato", "dato", "mato", "nata", "lata", "bata", "rata", "masa", "pasa", "tasa", "taza", "cosa", "rosa",
              "sopa", "ropa", "copa", "mono", "mano", "mina", "cama", "dama", "fama", "rama", "lima", "cima", "pelo",
              "velo", "bota", "nota", "cola", "hola", "bola", "mesa", "pesa", "sapo", "paso", "peso", "queso", "beso",
              "mapa", "papa", "capa", "pala", "sala", "mala", "luna", "cuna", "tuna", "puma", "suma", "pera", "cera",
              "foca", "boca", "roca", "loca", "toca", "poca", "vaca", "saca", "nube", "sube", "cubo", "tubo", "lobo",
              "moto", "foto", "boto", "gota", "pato", "mito", "pito", "gorro", "jarro", "barro", "carro", "corro",
              "perro", "cerro", "burro", "zorro", "torre", "loro", "toro", "coro", "oro", "lazo", "brazo", "plazo",
              "besa", "pela", "tela", "vela", "bala", "lana", "rana", "sana", "gana", "dona", "lona", "mona", "toma",
              "come", "bebe", "sube", "lava", "pasa", "mira", "tira", "pica", "pisa", "lisa", "risa", "misa", "casi",
              "dedo", "cede", "nene", "seda", "moda", "boda", "soda", "mudo", "nudo", "todo", "lodo", "codo", "pino",
              "vino", "fino", "tino", "sano", "rato", "ramo", "tomo", "como", "domo", "lomo", "humo", "pomo"}
    return words


def make_options(parts, missing, rnd, count, known):
    answer = parts[missing]
    good = []
    for cand in candidate_syllables(answer):
        test = parts[:missing] + [cand] + parts[missing + 1:]
        if plain("".join(test)) in known:
            continue  # formaría otra palabra: respuesta ambigua
        if plain(cand) in {plain(p) for p in parts}:
            continue  # ya está en la palabra
        good.append(cand)
    rnd.shuffle(good)
    distractors = good[: count - 1]
    assert len(distractors) == count - 1, f"pocas opciones para {''.join(parts)}"
    options = distractors + [answer.lower() if answer.islower() else answer]
    rnd.shuffle(options)
    return options


def missing_position(parts, level, index):
    if len(parts) == 1:
        return 0
    if level == 3:
        for i, p in enumerate(parts):
            if has_cluster(p) or has_diphthong(p):
                return i
    return index % len(parts)


def drawing_exists(name):
    return any((ROOT / "assets/drawings").rglob(f"{name}.svg"))


def main():
    known = known_words()
    rnd = random.Random(2026)
    ids = [w[0] for w in WORDS]
    assert len(ids) == len(set(ids)), "ids repetidos"
    assert len(WORDS) >= 100, len(WORDS)
    words, exercises = [], []
    for n, (wid, text, category, picture) in enumerate(WORDS):
        parts = split(text)
        assert "".join(parts) == text
        level = level_of(parts)
        if picture and "drawing" in picture:
            assert drawing_exists(picture["drawing"]), picture
        image = f"{WORD_IMAGES}/{wid}.webp"
        image_ready = (ROOT / image).is_file()
        clip = f"{AUDIO}/{wid}.mp3"
        words.append({
            "id": wid, "text": text, "syllables": parts, "level": level, "category": category,
            "picture": picture, "image": image, "image_ready": image_ready,
            "audio": {"clip": clip if (ROOT / clip).is_file() else None, "tts": text},
        })
        missing = missing_position(parts, level, n)
        option_count = 3 if level == 1 else 4
        options = make_options(parts, missing, rnd, option_count, known)
        assert options.count(parts[missing]) == 1
        assert len({plain(o) for o in options}) == len(options), options
        exercises.append({
            "id": f"completa_{wid}", "word": wid, "level": level, "category": category,
            "syllables": parts, "missing": missing, "answer": parts[missing], "options": options,
            # Modo «ordena»: solo palabras de 2 o más sílabas.
            "order": len(parts) >= 2,
        })
    data = {"format_version": 1, "words": words, "exercises": exercises}
    out = ROOT / "assets/reading/complete_words.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    by_level = {lv: sum(1 for w in words if w["level"] == lv) for lv in (1, 2, 3)}
    ready = [w for w in words if w["picture"] or w["image_ready"]]
    pending = [w["text"] for w in words if not (w["picture"] or w["image_ready"])]
    print(f"{out.relative_to(ROOT)}: {len(words)} palabras {by_level}; con imagen {len(ready)}; "
          f"pendientes ({len(pending)}): {', '.join(pending)}")


if __name__ == "__main__":
    main()
