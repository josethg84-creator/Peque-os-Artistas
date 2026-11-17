"""«Aprendo a leer» · Fase 6: «Escucho y escribo» (dictados).

Genera assets/reading/dictations.json REUTILIZANDO el contenido ya validado:
- 50 dictados de sílabas: las 10 familias de la Fase 3 (syllables.json),
  empezando por M, P, S, L y T;
- 100 dictados de palabras: las palabras con imagen de la Fase 4
  (complete_words.json), de las más fáciles a las más difíciles;
- 50 dictados de oraciones: oraciones de la Fase 5 (sentences.json) que solo
  tienen una forma de ordenarse.

Cada dictado lleva: id, tipo, nivel, texto correcto, audio, imagen, tarjetas,
pistas, reglas de validación y criterios de evaluación.

Validaciones:
- Solución única: en las tarjetas no hay dos que suenen igual (seseo, b/v,
  c/k/qu), ni distractores que formen la respuesta de otra manera.
- En el teclado, las grafías que suenan EXACTAMENTE igual en una sílaba
  aislada (SA / ZA, BA / VA, CA / KA) se aceptan de forma explícita como
  alternativas: solo con el oído no se pueden distinguir. En palabras y
  oraciones no hay alternativas: la imagen deja claro qué palabra es.
- Las palabras se separan en sílabas con el mismo silabeador de siempre.

Uso: python3 tools/reading/dictations.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from syllabify import split  # noqa: E402
from words import plain, sound, valid_spelling  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FAMILY_ORDER = ["m", "p", "s", "l", "t", "n", "d", "f", "c", "b"]


def load(name):
    return json.loads((ROOT / "assets/reading" / name).read_text(encoding="utf-8"))


def homophones(syl):
    """Otras grafías de una sílaba aislada que suenan igual (latinoamericano)."""
    out = set()
    target = sound(syl)
    v = "aeiou"
    for onset in ["b", "v", "s", "z", "c", "k", "qu", "ce", "ci"]:
        for vowel in v:
            cand = onset + vowel if onset not in ("ce", "ci") else onset
            if cand in out or cand == syl:
                continue
            if sound(cand) == target and cand != syl:
                ok = valid_spelling(cand) or cand in ("ke", "ki", "ka", "ko", "ku", "ce", "ci")
                if ok and cand not in ("ze", "zi"):
                    out.add(cand)
    return sorted(out)


def syllable_dictations(syl_data, rnd):
    by_id = {s["id"]: s for s in syl_data["syllables"]}
    words = syl_data["words"]
    fams = {f["id"]: f for f in syl_data["families"]}
    out = []
    for fam in FAMILY_ORDER:
        f = fams[fam]
        sylls = [by_id[i] for i in f["syllables"]]
        for s in sylls:
            text = s["text"]
            # Distractores: 2 de la misma familia (otra vocal) y 1 de otra familia
            # con la misma vocal. Nunca uno que suene igual.
            same = [x["text"] for x in sylls if x["text"] != text]
            rnd.shuffle(same)
            vowel = plain(text)[-1]
            other = [x["text"] for x in syl_data["syllables"]
                     if x["family"] not in (fam, "vocales") and plain(x["text"])[-1] == vowel]
            rnd.shuffle(other)
            options = [text] + same[:2] + other[:1]
            assert len({sound(o) for o in options}) == 4, options
            rnd.shuffle(options)
            word = words.get(s["word"]) if isinstance(words, dict) else None
            w = next((x for x in syl_data["words"] if x["id"] == s["word"]), None) if not word else word
            out.append({
                "id": f"dictado_silaba_{s['id']}",
                "type": "silaba",
                "level": 1,
                "difficulty": FAMILY_ORDER.index(fam) // 5 + 1,
                "family": fam,
                "text": text,
                "audio": s["audio"],
                "picture": w.get("picture") if w else None,
                "example": w["text"] if w else None,
                "cards": options,
                "target": [text],
                "modes": ["tarjetas", "teclado"],
                "hints": {
                    "count": len(text),
                    "count_label": f"{len(text)} letras",
                    "first": text[0],
                    "model": text,
                },
                "validation": {
                    "case": "ignore",
                    "accents": "required",
                    "spaces": "ignore_edges",
                    "final_period": "none",
                    "alternatives": homophones(text),
                },
            })
    assert len(out) == 50, len(out)
    return out


def word_dictations(cw, rnd):
    words = {w["id"]: w for w in cw["words"]}
    exercises = {e["word"]: e for e in cw["exercises"]}
    playable = [w for w in cw["words"] if w.get("picture") or w.get("image_ready")]
    playable.sort(key=lambda w: (w["level"], len(w["syllables"]), w["id"]))
    out = []
    for w in playable:
        parts = w["syllables"]
        assert split(w["text"]) == parts, w["text"]
        e = exercises[w["id"]]
        extra = [o for o in e["options"] if o != e["answer"]]
        rnd.shuffle(extra)
        distractors = []
        for o in extra:
            # Que no suene como ninguna sílaba de la palabra y no se repita.
            if sound(o) in {sound(p) for p in parts} or o in distractors:
                continue
            distractors.append(o)
            if len(distractors) == (1 if w["level"] == 1 else 2):
                break
        cards = parts + distractors
        rnd.shuffle(cards)
        # Con los distractores puestos en el lugar de su sílaba no sale otra
        # palabra válida: ya lo comprobó la Fase 4 (opciones con una sola respuesta).
        out.append({
            "id": f"dictado_palabra_{w['id']}",
            "type": "palabra",
            "level": 2,
            "difficulty": w["level"],
            "text": w["text"],
            "audio": w["audio"],
            "picture": w.get("picture"),
            "image": w["image"] if w.get("image_ready") else None,
            "cards": cards,
            "target": parts,
            "modes": ["tarjetas", "teclado"],
            "hints": {
                "count": len(parts),
                "count_label": f"{len(parts)} sílaba" + ("s" if len(parts) > 1 else ""),
                "first": parts[0],
                "model": w["text"],
            },
            "validation": {
                "case": "ignore",
                "accents": "required",
                "spaces": "required",
                "final_period": "none",
                "alternatives": [],
            },
        })
    assert len(out) == 100, len(out)
    assert len({d["text"] for d in out}) == 100
    return out


def sentence_dictations(sd):
    quota = {1: 16, 2: 16, 3: 8, 4: 10}
    out = []
    for level, n in quota.items():
        pool = [s for s in sd["sentences"] if s["level"] == level and s["order"] and len(s["words"]) <= (6 if level <= 2 else 7)]
        assert len(pool) >= n, (level, len(pool))
        for s in pool[:n]:
            words = [w["text"] for w in s["words"]]
            pieces = words[:-1] + [words[-1] + "."]
            assert " ".join(pieces) == s["text"]
            out.append({
                "id": f"dictado_{s['id']}",
                "type": "oracion",
                "level": 3,
                "difficulty": level,
                "sentence": s["id"],
                "text": s["text"],
                "audio": {"clip": s["audio"]["clip"], "tts": s["text"]},
                "scene": s["scene"],
                "cards": pieces,
                "target": pieces,
                "modes": ["ordenar", "teclado"],
                "hints": {
                    "count": len(words),
                    "count_label": f"{len(words)} palabras",
                    "first": words[0],
                    "model": s["text"],
                },
                "validation": {
                    "case": "ignore",
                    "accents": "required",
                    "spaces": "required",
                    "final_period": "optional",
                    "alternatives": [],
                },
            })
    assert len(out) == 50
    return out


CRITERIA = {
    "correct": "La respuesta coincide con el texto correcto (sin contar mayúsculas ni espacios de más) "
               "o con una alternativa aceptada.",
    "independent": "Acierto sin pistas: se registra aparte de los aciertos con ayuda.",
    "errors": ["tilde", "letra", "sílaba", "espacios", "palabra", "orden"],
}

LEVELS = [
    {"id": 1, "name": "Escucho sílabas", "type": "silaba"},
    {"id": 2, "name": "Escucho palabras", "type": "palabra"},
    {"id": 3, "name": "Escucho oraciones", "type": "oracion"},
]


def main():
    rnd = random.Random(2026)
    dictations = (syllable_dictations(load("syllables.json"), rnd)
                  + word_dictations(load("complete_words.json"), rnd)
                  + sentence_dictations(load("sentences.json")))
    ids = [d["id"] for d in dictations]
    assert len(ids) == len(set(ids))
    for d in dictations:
        d["criteria"] = CRITERIA
        # Las tarjetas contienen exactamente lo necesario para la respuesta.
        for piece in d["target"]:
            assert d["cards"].count(piece) >= d["target"].count(piece), d["id"]
        assert d["audio"]["tts"], d["id"]
    data = {"format_version": 1, "levels": LEVELS, "dictations": dictations}
    out = ROOT / "assets/reading/dictations.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    count = {t: sum(1 for d in dictations if d["type"] == t) for t in ("silaba", "palabra", "oracion")}
    alts = {d["text"]: d["validation"]["alternatives"] for d in dictations if d["validation"]["alternatives"]}
    print(f"{out.relative_to(ROOT)}: {count}; grabaciones {sum(bool(d['audio']['clip']) for d in dictations)}; "
          f"alternativas aceptadas: {alts}")


if __name__ == "__main__":
    main()
