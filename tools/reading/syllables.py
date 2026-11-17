"""«Aprendo a leer» · Fase 3: letras, familias silábicas y palabras de ejemplo.

Genera assets/reading/syllables.json. Comprueba:
- que la separación de cada palabra coincide con el silabeador (syllabify.py);
- que cada palabra de ejemplo empieza por su sílaba (o por esa sílaba en
  diptongo, como «fue-go» para FU, que se anota);
- que los dibujos existen y qué audios grabados hay.

Audio: si existe assets/audio/reading/<tipo>/<id>.mp3 se usa la grabación; si
no, la app usa la voz del dispositivo (marcado como pendiente de grabar).
Imágenes: «picture» es un dibujo o icono que ya tiene la app y que representa
la palabra sin ambigüedad; si no lo hay, la palabra queda con imagen pendiente
(la app muestra un marcador «Imagen pendiente») y no se usa en los juegos de
imagen. La ilustración 3D definitiva irá en assets/images/aprendo_leer/palabras/.

Uso: python3 tools/reading/syllables.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from syllabify import split  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AUDIO = "assets/audio/reading"
WORD_IMAGES = "assets/images/aprendo_leer/palabras"


def D(drawing):
    return {"drawing": drawing}


def I(icon):
    return {"icon": icon}


# (id, letra visible, nombre de la letra, color, [(sílaba, id palabra)])
FAMILIES = [
    ("vocales", "A E I O U", None, "#FFB74D",
     [("a", "abeja"), ("e", "elefante"), ("i", "iglesia"), ("o", "oso"), ("u", "uvas")]),
    ("m", "M", "eme", "#F48FB1",
     [("ma", "mama"), ("me", "mesa"), ("mi", "mimo"), ("mo", "mono"), ("mu", "muneca")]),
    ("p", "P", "pe", "#81D4FA",
     [("pa", "pato"), ("pe", "pelota"), ("pi", "pino"), ("po", "pollo"), ("pu", "puma")]),
    ("s", "S", "ese", "#A5D6A7",
     [("sa", "sapo"), ("se", "semaforo"), ("si", "silla"), ("so", "sopa"), ("su", "subibaja")]),
    ("l", "L", "ele", "#CE93D8",
     [("la", "lapiz"), ("le", "leon"), ("li", "libro"), ("lo", "loro"), ("lu", "luna")]),
    ("t", "T", "te", "#FFCC80",
     [("ta", "taza"), ("te", "telefono"), ("ti", "tijera"), ("to", "tomate"), ("tu", "tucan")]),
    ("n", "N", "ene", "#80CBC4",
     [("na", "naranja"), ("ne", "negro"), ("ni", "nina"), ("no", "nota"), ("nu", "nube")]),
    ("d", "D", "de", "#9FA8DA",
     [("da", "dado"), ("de", "dedo"), ("di", "dinosaurio"), ("do", "dona"), ("du", "ducha")]),
    ("f", "F", "efe", "#FFAB91",
     [("fa", "familia"), ("fe", "feliz"), ("fi", "fideos"), ("fo", "foco"), ("fu", "fuego")]),
    ("c", "C · Q", "ce y cu", "#B39DDB",
     [("ca", "casa"), ("co", "conejo"), ("cu", "cuna"), ("que", "queso"), ("qui", "quitasol")]),
    ("b", "B", "be", "#90CAF9",
     [("ba", "ballena"), ("be", "bebe"), ("bi", "bicicleta"), ("bo", "boca"), ("bu", "burro")]),
]

# id: (palabra, dibujo o icono existente que la representa sin ambigüedad o None)
WORDS = {
    "abeja": ("abeja", D("animal_abeja")),
    "elefante": ("elefante", D("animal_elefante")),
    "iglesia": ("iglesia", None),
    "oso": ("oso", D("animal_oso")),
    "uvas": ("uvas", D("fruta_uvas")),
    "mama": ("mamá", None),
    "mesa": ("mesa", I("table")),
    "mimo": ("mimo", None),
    "mono": ("mono", D("animal_mono")),
    "muneca": ("muñeca", None),
    "pato": ("pato", D("granja_patito")),
    "pelota": ("pelota", I("ball")),
    "pino": ("pino", None),
    "pollo": ("pollo", None),
    "puma": ("puma", None),
    "sapo": ("sapo", None),
    "semaforo": ("semáforo", I("traffic")),
    "silla": ("silla", I("chair")),
    "sopa": ("sopa", I("soup_kitchen")),
    "subibaja": ("subibaja", None),
    "lapiz": ("lápiz", I("edit")),
    "leon": ("león", D("animal_leon")),
    "libro": ("libro", I("menu_book")),
    "loro": ("loro", {"lolo": True}),
    "luna": ("luna", I("moon")),
    "taza": ("taza", I("local_cafe")),
    "telefono": ("teléfono", I("phone")),
    "tijera": ("tijera", I("content_cut")),
    "tomate": ("tomate", None),
    "tucan": ("tucán", None),
    "naranja": ("naranja", D("fruta_naranja")),
    "negro": ("negro", {"swatch": "#212121"}),
    "nina": ("niña", {"kid": {"girl": True, "emotion": "feliz", "shirt": "#EC407A"}}),
    "nota": ("nota", None),
    "nube": ("nube", I("cloud")),
    "dado": ("dado", None),
    "dedo": ("dedo", None),
    "dinosaurio": ("dinosaurio", D("dinosaurio_01")),
    "dona": ("dona", None),
    "ducha": ("ducha", I("shower")),
    "familia": ("familia", I("family_restroom")),
    "feliz": ("feliz", {"emotion": "feliz"}),
    "fideos": ("fideos", None),
    "foco": ("foco", I("lightbulb")),
    "fuego": ("fuego", None),
    "casa": ("casa", I("home")),
    "conejo": ("conejo", D("animal_conejo")),
    "cuna": ("cuna", I("crib")),
    "queso": ("queso", None),
    "quitasol": ("quitasol", I("beach_access")),
    "ballena": ("ballena", D("mar_ballena")),
    "bebe": ("bebé", I("child_care")),
    "bicicleta": ("bicicleta", I("pedal_bike")),
    "boca": ("boca", {"body": "boca"}),
    "burro": ("burro", None),
}

# Palabras de ejemplo cuya primera sílaba es la sílaba + otra vocal (diptongo).
DIPHTHONG_EXAMPLES = {"fuego": "En «fuego», la FU va unida a la E: FUE-GO."}

LEVELS = [
    {"id": 1, "name": "Inicial", "description": "Vocales y sílabas directas", "locked": False},
    {"id": 2, "name": "Intermedio", "description": "Sílabas, imágenes y palabras", "locked": False},
    {"id": 3, "name": "Avanzado", "description": "Sílabas inversas y trabadas (próximamente)", "locked": True},
]


def plain(s):
    return s.lower().translate(str.maketrans("áéíóú", "aeiou"))


def clip(kind, ident):
    path = f"{AUDIO}/{kind}/{ident}.mp3"
    return path if (ROOT / path).is_file() else None


def drawing_exists(name):
    return any((ROOT / "assets/drawings").rglob(f"{name}.svg"))


def main():
    families, syllables, words = [], [], []
    used_words = set()
    for fid, letter, letter_name, color, items in FAMILIES:
        assert len(items) == 5, fid
        family_letter = None if fid == "vocales" else fid
        families.append({
            "id": fid, "letter": letter, "color": color, "level": 1,
            "letter_name": letter_name,
            "letter_audio": None if letter_name is None else {"clip": clip("letras", fid), "tts": letter_name},
            "syllables": [s for s, _ in items],
        })
        for text, word_id in items:
            if family_letter and fid != "c":
                assert text.startswith(family_letter), (fid, text)
            parts = split(text)
            assert parts == [text], f"«{text}» no es una sola sílaba: {parts}"
            word, picture = WORDS[word_id]
            parts = split(word)
            first = plain(parts[0])
            if word_id in DIPHTHONG_EXAMPLES:
                assert first.startswith(text) and first[len(text):] in ("a", "e", "i", "o", "u"), word
            else:
                assert first == text, f"«{word}» ({'-'.join(parts)}) no empieza por la sílaba «{text}»"
            syllables.append({
                "id": text, "text": text, "family": fid, "level": 1,
                "audio": {"clip": clip("silabas", text), "tts": text},
                "speeds": ["normal", "lenta"],
                "word": word_id,
            })
            used_words.add(word_id)
    for word_id in sorted(used_words):
        word, picture = WORDS[word_id]
        if picture and "drawing" in picture:
            assert drawing_exists(picture["drawing"]), picture
        parts = split(word)
        assert "".join(parts) == word
        words.append({
            "id": word_id, "text": word, "syllables": parts, "level": 2,
            "picture": picture,
            "image": f"{WORD_IMAGES}/{word_id}.webp",
            "image_ready": (ROOT / f"{WORD_IMAGES}/{word_id}.webp").is_file(),
            "audio": {"clip": clip("palabras", word_id), "tts": word},
            **({"note": DIPHTHONG_EXAMPLES[word_id]} if word_id in DIPHTHONG_EXAMPLES else {}),
        })
    data = {"format_version": 1, "levels": LEVELS, "families": families, "syllables": syllables, "words": words}
    out = ROOT / "assets/reading/syllables.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    pending_img = [w["text"] for w in words if w["picture"] is None and not w["image_ready"]]
    recorded = sum(1 for s in syllables if s["audio"]["clip"])
    print(f"{out.relative_to(ROOT)}: {len(families)} familias, {len(syllables)} sílabas, {len(words)} palabras")
    print(f"audio grabado: {recorded}/{len(syllables)} sílabas; imágenes pendientes ({len(pending_img)}): {', '.join(pending_img)}")


if __name__ == "__main__":
    main()
