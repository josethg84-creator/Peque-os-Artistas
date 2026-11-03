"""«Yo puedo expresarme»: necesidades, emociones y el constructor
QUIÉN + QUÉ SIENTE + POR QUÉ. Uso: python3 tools/speech/expressions.py"""

from content_common import BOY, GIRL, I, K, S, save

NEEDS = [
    ("tomar_agua", "Quiero tomar agua.", S("cocina", (K("feliz", True, GIRL), .38, .62, .45), (I("water", "#039BE5"), .76, .62, .22))),
    ("hambre", "Tengo hambre.", S("cocina", (K("triste", False, BOY), .38, .62, .45), (I("eat", "#F4511E"), .76, .62, .22))),
    ("descansar", "Necesito descansar.", S("dormitorio", (K("cansado", True, GIRL), .5, .6, .5))),
    ("jugar", "Quiero jugar.", S("parque", (K("emocionado", False, BOY), .4, .6, .45), (I("ball", "#E53935"), .76, .8, .16))),
    ("ayuda", "Necesito ayuda.", S("casa", (K("triste", True, GIRL), .4, .62, .45), (I("help", "#26A69A"), .76, .5, .22))),
    ("bano", "Quiero ir al baño.", S("casa", (K("sorprendido", False, BOY), .4, .62, .45), (I("toilet", "#5C6BC0"), .76, .6, .22))),
    ("frio", "Tengo frío.", S("lluvia", (K("triste", True, GIRL), .5, .62, .48), (I("snow", "#4FC3F7"), .8, .3, .16))),
    ("calor", "Tengo calor.", S("playa", (K("cansado", False, BOY), .45, .64, .48), (I("hot", "#F4511E"), .8, .3, .16))),
    ("duele", "Me duele aquí.", S("casa", (K("triste", False, BOY), .45, .62, .48), (I("hurt", "#E53935"), .78, .5, .18))),
    ("sueno", "Tengo sueño.", S("noche", (K("cansado", True, GIRL), .5, .62, .5))),
]

# id, nombre, emoción del dibujo, masculino, femenino, ejemplos
EMOTIONS = [
    ("alegria", "Alegría", "feliz", "contento", "contenta", [
        "Estoy contento porque voy a jugar.", "Estoy feliz porque viene mi abuela."]),
    ("tristeza", "Tristeza", "triste", "triste", "triste", [
        "Estoy triste porque extraño a mi amigo.", "Estoy triste porque se rompió mi juguete."]),
    ("miedo", "Miedo", "asustado", "asustado", "asustada", [
        "Tengo miedo porque hay truenos.", "Estoy asustada porque está muy oscuro."]),
    ("enojo", "Enojo", "enojado", "enojado", "enojada", [
        "Estoy enojado porque se cayó mi torre.", "Estoy enojada porque no me tocó mi turno."]),
    ("sorpresa", "Sorpresa", "sorprendido", "sorprendido", "sorprendida", [
        "Estoy sorprendido porque recibí un regalo.", "Estoy sorprendida porque vi un arcoíris."]),
    ("tranquilidad", "Tranquilidad", "tranquilo", "tranquilo", "tranquila", [
        "Estoy tranquilo porque escucho música suave.", "Estoy tranquila porque respiro despacio."]),
    ("cansancio", "Cansancio", "cansado", "cansado", "cansada", [
        "Estoy cansado porque corrí mucho.", "Estoy cansada porque jugué toda la tarde."]),
]

# QUIÉN: texto, verbo (estoy/está), femenino, dibujo
WHO = [
    ("yo_nino", "Yo", "estoy", False, True, K("feliz", False, BOY)),
    ("yo_nina", "Yo", "estoy", True, True, K("feliz", True, GIRL)),
    ("amigo", "Mi amigo", "está", False, False, K("feliz", False, "#81C784")),
    ("hermana", "Mi hermana", "está", True, False, K("feliz", True, "#CE93D8")),
    ("mama", "Mamá", "está", True, False, I("woman", "#AB47BC")),
    ("papa", "Papá", "está", False, False, I("man", "#3949AB")),
]

# POR QUÉ: emoción -> [(id, yo, otra persona, dibujo)]
WHY = {
    "alegria": [
        ("perro", "porque juego con mi perro", "porque juega con su perro", I("pets", "#FB8C00")),
        ("cumple", "porque es mi cumpleaños", "porque es su cumpleaños", I("cake", "#AB47BC")),
        ("parque", "porque vamos al parque", "porque vamos al parque", I("tree", "#2E7D32")),
    ],
    "tristeza": [
        ("amigo", "porque extraño a mi amigo", "porque extraña a su amigo", I("friends", "#00ACC1")),
        ("juguete", "porque se rompió mi juguete", "porque se rompió su juguete", I("toys", "#FB8C00")),
        ("lluvia", "porque llueve y no puedo salir", "porque llueve y no puede salir", I("umbrella", "#5C6BC0")),
    ],
    "miedo": [
        ("truenos", "porque hay truenos", "porque hay truenos", I("rain", "#78909C")),
        ("oscuro", "porque está oscuro", "porque está oscuro", I("moon", "#5C6BC0")),
        ("ruido", "porque escuché un ruido fuerte", "porque escuchó un ruido fuerte", I("hearing", "#8D6E63")),
    ],
    "enojo": [
        ("torre", "porque se cayó mi torre", "porque se cayó su torre", I("blocks", "#43A047")),
        ("turno", "porque no me tocó mi turno", "porque no le tocó su turno", I("clock", "#00897B")),
        ("lapiz", "porque perdí mi lápiz", "porque perdió su lápiz", I("pencil", "#FB8C00")),
    ],
    "sorpresa": [
        ("regalo", "porque recibí un regalo", "porque recibió un regalo", I("gift", "#E53935")),
        ("arcoiris", "porque vi un arcoíris", "porque vio un arcoíris", I("rainbow", "#EC407A")),
        ("visita", "porque llegó la abuela de visita", "porque llegó la abuela de visita", I("elderly_woman", "#8E24AA")),
    ],
    "tranquilidad": [
        ("cama", "porque estoy en mi cama", "porque está en su cama", I("bed", "#5C6BC0")),
        ("musica", "porque escucho música suave", "porque escucha música suave", I("music", "#AB47BC")),
        ("respiro", "porque respiro despacio", "porque respira despacio", K("tranquilo")),
    ],
    "cansancio": [
        ("correr", "porque corrí mucho", "porque corrió mucho", I("run", "#43A047")),
        ("jugar", "porque jugué toda la tarde", "porque jugó toda la tarde", I("play", "#FB8C00")),
        ("noche", "porque ya es de noche", "porque ya es de noche", I("moon", "#5C6BC0")),
    ],
}

if __name__ == "__main__":
    data = {
        "format_version": 1,
        "needs": [{"id": i, "text": t, "picture": p} for i, t, p in NEEDS],
        "emotions": [
            {"id": i, "name": n, "face": f, "masculine": m, "feminine": fe, "examples": ex,
             "reasons": [{"id": rid, "me": me, "other": other, "picture": pic} for rid, me, other, pic in WHY[i]]}
            for i, n, f, m, fe, ex in EMOTIONS
        ],
        "who": [{"id": i, "text": t, "verb": v, "feminine": fem, "first_person": fp, "picture": p} for i, t, v, fem, fp, p in WHO],
    }
    print(save("expressions.json", data))
