"""Fase 4: juegos de sílabas y sonidos. «¿Con qué empieza?» (misma sílaba
inicial) y «Palabras que riman». Las palabras son ids del vocabulario
(words.json y vocabulary.json); «Palmas y sílabas» y «Escucho y encuentro»
usan directamente la pronunciación del vocabulario.
Uso: python3 tools/speech/phonology.py (después de vocabulary.py)"""

import json

from content_common import ROOT, save

# (palabra modelo, la que empieza igual, otras dos que no)
STARTS = [
    ("mama", "mariposa", ["perro", "sol"]),
    ("pelota", "perro", ["gato", "luna"]),
    ("gato", "galleta", ["sol", "mesa"]),
    ("sol", "sopa", ["casa", "nube"]),
    ("luna", "lupa", ["mesa", "oso"]),
    ("casa", "camion", ["pez", "flor"]),
    ("mesa", "metro", ["gato", "sol"]),
    ("pato", "papa", ["nube", "oso"]),
    ("taza", "taxi", ["perro", "luna"]),
    ("conejo", "cocina", ["mesa", "pez"]),
    ("ballena", "balon", ["sol", "flor"]),
    ("lavadora", "lapiz", ["oso", "nube"]),
    ("dinosaurio", "dibujo", ["gato", "sol"]),
    ("regalo", "regla", ["luna", "oso"]),
    ("tortuga", "tormenta", ["casa", "pez"]),
    ("vaca", "valla", ["luna", "flor"]),
]

# (palabra, la que rima, otras dos que no)
RHYMES = [
    ("gato", "pato", ["sol", "mesa"]),
    ("mesa", "fresa", ["perro", "luna"]),
    ("luna", "cuna", ["gato", "flor"]),
    ("camion", "avion", ["mesa", "gato"]),
    ("leche", "coche", ["luna", "oso"]),
    ("abeja", "oveja", ["sol", "tren"]),
    ("flor", "tractor", ["mesa", "luna"]),
    ("semilla", "silla", ["gato", "sol"]),
    ("campana", "ventana", ["perro", "flor"]),
    ("toalla", "valla", ["luna", "tren"]),
    ("cohete", "patinete", ["casa", "oso"]),
    ("escalera", "nevera", ["luna", "gato"]),
    ("ballena", "cena", ["sol", "pato"]),
]


def main():
    words = json.loads((ROOT / "assets/speech/words.json").read_text())
    vocab = json.loads((ROOT / "assets/speech/vocabulary.json").read_text())
    ids = {w["id"] for c in words["categories"] for w in c["words"]} | {w["id"] for w in vocab["words"]}
    out = {"format_version": 1, "starts": [], "rhymes": []}
    for key, rows in (("starts", STARTS), ("rhymes", RHYMES)):
        for target, answer, others in rows:
            for w in (target, answer, *others):
                assert w in ids, (key, w)
            out[key].append({"target": target, "answer": answer, "others": others})
    print(len(out["starts"]), len(out["rhymes"]), save("phonology.json", out))


if __name__ == "__main__":
    main()
