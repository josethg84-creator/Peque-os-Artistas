"""Fase 4: «Mi historia». Personajes, lugares, acciones, objetos y finales
para que el niño construya su propia historia. La gramática (artículos,
«al»/«a la», «lo»/«la», contento/contenta) la resuelve la app.
No se piden nombres, fotos ni datos personales.
Uso: python3 tools/speech/mystory.py"""

from content_common import BOY, GIRL, D, E, I, K, APPLE, save

# (id, nombre, femenino, dibujo)
CHARACTERS = [
    ("conejo", "conejo", False, D("animal_conejo")),
    ("nina", "niña", True, K("feliz", True, GIRL)),
    ("nino", "niño", False, K("feliz", False, BOY)),
    ("oso", "oso", False, D("animal_oso")),
    ("tortuga", "tortuga", True, D("animal_tortuga")),
    ("dragon", "dragón", False, D("fantasia_dragon")),
    ("gallina", "gallina", True, D("granja_gallina")),
    ("mariposa", "mariposa", True, D("animal_mariposa", **{"ala_*": "#AB47BC"})),
]

# (id, nombre, femenino, fondo de escena)
PLACES = [
    ("bosque", "bosque", False, "bosque"),
    ("playa", "playa", True, "playa"),
    ("parque", "parque", False, "parque"),
    ("jardin", "jardín", False, "jardin"),
    ("escuela", "escuela", True, "escuela"),
    ("cocina", "cocina", True, "cocina"),
]

# (id, verbo, preposición tras el verbo, dibujo, tipos de objeto que admite)
ACTIONS = [
    ("buscar", "buscar", "", I("search", "#3949AB"), ["comida", "juguete", "planta", "cosa"]),
    ("comer", "comer", "", I("eat", "#FB8C00"), ["comida"]),
    ("jugar", "jugar", "con", I("play", "#EC407A"), ["juguete"]),
    ("recoger", "recoger", "", I("help", "#26A69A"), ["comida", "planta", "juguete"]),
    ("plantar", "plantar", "", I("plant", "#43A047"), ["planta"]),
    ("mirar", "mirar", "", I("look", "#5C6BC0"), ["cosa", "planta", "juguete"]),
]

# (id, nombre, femenino, tipo, dibujo)
OBJECTS = [
    ("zanahoria", "zanahoria", True, "comida", I("carrot", "#FB8C00")),
    ("manzana", "manzana", True, "comida", APPLE),
    ("pastel", "pastel", False, "comida", I("cake", "#AB47BC")),
    ("pelota", "pelota", True, "juguete", I("ball", "#E53935")),
    ("robot", "robot", False, "juguete", I("robot", "#546E7A")),
    ("flor", "flor", True, "planta", I("flower", "#EC407A")),
    ("semilla", "semilla", True, "planta", I("seed", "#8D6E63")),
    ("estrella", "estrella", True, "cosa", I("star", "#FBC02D")),
    ("regalo", "regalo", False, "cosa", I("gift", "#E53935")),
]

# (id, plantilla, dibujo). {el} = el personaje con artículo; {contento} =
# concordancia; {lo} = «lo»/«la» según el objeto.
ENDINGS = [
    ("feliz", "¡Y {el} se puso muy {contento}!", E("feliz")),
    ("compartir", "Después, {el} {lo} compartió con sus amigos.", I("friends", "#FB8C00")),
    ("casa", "Al final, {el} volvió a casa a descansar.", I("home2", "#E57373")),
    ("dormir", "Por la noche, {el} durmió muy {contento}.", I("sleepz", "#5C6BC0")),
]

if __name__ == "__main__":
    data = {
        "format_version": 1,
        "characters": [{"id": i, "noun": n, "feminine": f, "picture": p} for i, n, f, p in CHARACTERS],
        "places": [{"id": i, "noun": n, "feminine": f, "scene": b} for i, n, f, b in PLACES],
        "actions": [{"id": i, "verb": v, "prep": pr, "picture": p, "objects": o} for i, v, pr, p, o in ACTIONS],
        "objects": [{"id": i, "noun": n, "feminine": f, "kind": k, "picture": p} for i, n, f, k, p in OBJECTS],
        "endings": [{"id": i, "template": t, "picture": p} for i, t, p in ENDINGS],
    }
    for a in ACTIONS:
        assert any(o[3] in a[4] for o in OBJECTS), a[0]
    print(save("mystory.json", data))
