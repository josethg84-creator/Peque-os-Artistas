"""Separación en sílabas del español escrito (versión Python, independiente
de lib/reading/syllabifier.dart, para que ambas se comprueben mutuamente)."""

STRONG = set("aeoáéóíú")
WEAK = set("iuü")
VOWELS = STRONG | WEAK
CLUSTERS = {"pl", "bl", "cl", "gl", "fl", "kl", "pr", "br", "tr", "dr", "cr", "gr", "fr", "kr"}


def _tokens(word):
    low = word.lower()
    out = []  # (texto, minúscula, es_vocal)
    i = 0
    while i < len(word):
        c = low[i]
        nxt = low[i + 1] if i + 1 < len(low) else ""
        aft = low[i + 2] if i + 2 < len(low) else ""
        if c + nxt in ("ch", "ll", "rr"):
            out.append((word[i:i + 2], c + nxt, False)); i += 2; continue
        if c in "qg" and nxt == "u" and aft in "eiéí" and aft:
            out.append((word[i:i + 2], c + nxt, False)); i += 2; continue
        if c == "y":
            prev_vowel = i > 0 and low[i - 1] in VOWELS
            vowel = nxt == "" or (nxt not in VOWELS and i > 0 and not prev_vowel)
            out.append((word[i], "i" if vowel else "y", vowel)); i += 1; continue
        out.append((word[i], c, c in VOWELS)); i += 1
    return out


def _joins(a, b):
    a_weak, b_weak = a in WEAK, b in WEAK
    if not a_weak and not b_weak:
        return False
    if a_weak and b_weak:
        return a != b or a == "ü"
    return True


def split(word):
    groups = []  # [es_nucleo, [tokens]]
    for t in _tokens(word):
        if t[2]:
            if groups and groups[-1][0] and _joins(groups[-1][1][-1][1], t[1]):
                groups[-1][1].append(t)
            else:
                groups.append([True, [t]])
        else:
            if groups and not groups[-1][0]:
                groups[-1][1].append(t)
            else:
                groups.append([False, [t]])
    out, cur, seen = [], "", False
    for g, (nucleus, toks) in enumerate(groups):
        text = "".join(t[0] for t in toks)
        if nucleus:
            if seen:
                out.append(cur); cur = ""
            cur += text; seen = True
            continue
        if not seen or g + 1 >= len(groups):
            cur += text
            continue
        n = len(toks)
        pair = lambda k: toks[k][1] + toks[k + 1][1]
        keep = 0 if n == 1 else (0 if pair(0) in CLUSTERS else 1) if n == 2 else (1 if pair(1) in CLUSTERS else 2) if n == 3 else n - 2
        cur += "".join(t[0] for t in toks[:keep])
        out.append(cur)
        cur = "".join(t[0] for t in toks[keep:])
        seen = False
    if cur:
        if seen or not out:
            out.append(cur)
        else:
            out[-1] += cur
    return out


if __name__ == "__main__":
    for w, e in [("mamá", "ma-má"), ("dinosaurio", "di-no-sau-rio"), ("pingüino", "pin-güi-no"),
                 ("obstáculo", "obs-tá-cu-lo"), ("búho", "bú-ho"), ("quitasol", "qui-ta-sol"), ("rey", "rey"),
                 ("bicicleta", "bi-ci-cle-ta"), ("león", "le-ón"), ("cuidado", "cui-da-do"), ("leyes", "le-yes")]:
        got = "-".join(split(w))
        assert got == e, (w, got, e)
    print("silabeo OK")
