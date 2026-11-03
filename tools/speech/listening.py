"""«Escucho y respondo»: 56 ejercicios originales de comprensión oral en 3
niveles. Tipos: quien, donde, objeto (para qué sirve), secuencia,
instruccion (dos pasos, se toca en orden), emocion y escena (mirar un dibujo).
Uso: python3 tools/speech/listening.py"""

from content_common import BOY, GIRL, I, D, K, E, S, APPLE, BANANA, GRAPES, STRAWBERRY, save

LUNA = lambda e="feliz", up=False: K(e, True, GIRL, up)
MATEO = lambda e="feliz", up=False: K(e, False, BOY, up)
DOG, CAT, BEAR = D("animal_perro"), D("animal_gato"), D("animal_oso")
RABBIT, MONKEY, TURTLE = D("animal_conejo"), D("animal_mono"), D("animal_tortuga")
DUCK = D("granja_patito", **{"*": "#FFD54F"})
COW, HEN, SHEEP = D("granja_vaca"), D("granja_gallina"), D("granja_oveja")
FISH, BUTTERFLY = D("animal_pez"), D("animal_mariposa", **{"*": "#AB47BC"})
BOAT, PLANE, TRAIN, CAR = D("vehiculo_barco"), D("vehiculo_avion"), D("vehiculo_tren"), D("vehiculo_automovil")

O = lambda text, picture: {"text": text, "picture": picture}
EX = []


def ex(level, kind, say, question, options, answer=None, steps=None, scene=None):
    n = sum(1 for e in EX if e["type"] == kind) + 1
    e = {"id": f"{kind}_{n}", "level": level, "type": kind, "say": say, "question": question,
         "options": [O(t, p) for t, p in options]}
    if scene:
        e["scene"] = scene
    if steps is not None:
        e["steps"] = steps
    else:
        e["answer"] = answer
    EX.append(e)


# ───────────── Nivel 1: una frase corta, una sola idea ─────────────
ex(1, "quien", "El gato duerme en la cama.", "¿Quién duerme?", [("El perro", DOG), ("El gato", CAT), ("El pato", DUCK)], 1)
ex(1, "quien", "La niña baila con su abuela.", "¿Quién baila con la abuela?", [("El niño", MATEO()), ("La niña", LUNA()), ("El oso", BEAR)], 1)
ex(1, "quien", "El pato nada en el lago.", "¿Quién nada?", [("El pato", DUCK), ("La vaca", COW), ("El mono", MONKEY)], 0)
ex(1, "quien", "El mono come un plátano.", "¿Quién come un plátano?", [("El conejo", RABBIT), ("El oso", BEAR), ("El mono", MONKEY)], 2)

ex(1, "donde", "Mateo juega en la playa.", "¿Dónde juega Mateo?", [("En la playa", S("playa")), ("En la cocina", S("cocina")), ("En la escuela", S("escuela"))], 0)
ex(1, "donde", "Papá prepara la sopa en la cocina.", "¿Dónde está papá?", [("En el dormitorio", S("dormitorio")), ("En la cocina", S("cocina")), ("En el parque", S("parque"))], 1)
ex(1, "donde", "Luna duerme en su cama.", "¿Dónde duerme Luna?", [("En la mesa", I("table", "#8D6E63")), ("En la silla", I("chair", "#8D6E63")), ("En la cama", I("bed", "#5C6BC0"))], 2)
ex(1, "donde", "El pájaro canta en el árbol.", "¿Dónde canta el pájaro?", [("En el agua", I("sea", "#039BE5")), ("En el árbol", I("tree", "#43A047")), ("En la casa", I("home2", "#E57373"))], 1)

ex(1, "objeto", "Con la cuchara tomo la sopa.", "¿Con qué tomo la sopa?", [("La cuchara", I("spoon", "#78909C")), ("El lápiz", I("pencil", "#FFB300")), ("La pelota", I("ball", "#E53935"))], 0)
ex(1, "objeto", "Después del baño me seco con la toalla.", "¿Con qué me seco?", [("El libro", I("book", "#8E24AA")), ("La toalla", I("towel", "#F48FB1")), ("La bici", I("bike", "#1E88E5"))], 1)
ex(1, "objeto", "Cuando llueve, uso el paraguas.", "¿Qué uso cuando llueve?", [("Las gafas", I("glasses", "#5D4037")), ("Los zapatos", I("shoes", "#6D4C41")), ("El paraguas", I("umbrella", "#7E57C2"))], 2)
ex(1, "objeto", "Con el lápiz dibujo una casa.", "¿Con qué dibujo?", [("El lápiz", I("pencil", "#FFB300")), ("La cuchara", I("spoon", "#78909C")), ("La toalla", I("towel", "#F48FB1"))], 0)

ex(1, "emocion", "Lolo encontró a su amigo y se ríe.", "¿Cómo está Lolo?", [("Feliz", E("feliz")), ("Triste", E("triste")), ("Enojado", E("enojado"))], 0)
ex(1, "emocion", "A la niña se le cayó el helado y llora.", "¿Cómo se siente la niña?", [("Sorprendida", E("sorprendido")), ("Triste", E("triste")), ("Feliz", E("feliz"))], 1)
ex(1, "emocion", "Mateo corrió mucho y ahora quiere dormir.", "¿Cómo está Mateo?", [("Enojado", E("enojado")), ("Asustado", E("asustado")), ("Cansado", E("cansado"))], 2)

ex(1, "escena", "Mira el dibujo.", "¿Con qué juega la niña?", [("Con una pelota", I("ball", "#E53935")), ("Con un libro", I("book", "#8E24AA")), ("Con un pastel", I("cake", "#AB47BC"))], 0,
   scene=S("parque", (LUNA("feliz", True), .4, .62, .45), (I("ball", "#E53935"), .72, .8, .14)))
ex(1, "escena", "Mira el dibujo.", "¿Qué animal está en la playa?", [("El gato", CAT), ("El perro", DOG), ("La vaca", COW)], 1,
   scene=S("playa", (DOG, .45, .7, .4), (I("sun", "#FFB300"), .82, .2, .2)))
ex(1, "escena", "Mira el dibujo.", "¿Qué hay en el cielo?", [("El sol", I("sun", "#FFB300")), ("La luna", I("moon", "#FDD835")), ("Un arcoíris", I("rainbow", "#EC407A"))], 1,
   scene=S("noche", (I("moon", "#FDD835"), .75, .22, .2), (LUNA("tranquilo"), .4, .64, .42)))

# ───────────── Nivel 2: dos personajes, causas y orden ─────────────
ex(2, "quien", "El conejo salta y la tortuga camina despacio.", "¿Quién camina despacio?", [("El conejo", RABBIT), ("La tortuga", TURTLE), ("El perro", DOG)], 1)
ex(2, "quien", "Papá lee un cuento y Mateo escucha.", "¿Quién lee el cuento?", [("Papá", I("man", "#3949AB")), ("Mateo", MATEO()), ("La abuela", I("elderly_woman", "#8E24AA"))], 0)
ex(2, "quien", "La vaca come hierba mientras la gallina busca semillas.", "¿Quién busca semillas?", [("La vaca", COW), ("La oveja", SHEEP), ("La gallina", HEN)], 2)

ex(2, "donde", "Después de clase, Luna juega en el parque.", "¿Dónde juega Luna después de clase?", [("En la escuela", S("escuela")), ("En el parque", S("parque")), ("En la playa", S("playa"))], 1)
ex(2, "donde", "El gato salió de la casa y se subió al árbol.", "¿Dónde está el gato ahora?", [("En la casa", I("home2", "#E57373")), ("En el árbol", I("tree", "#43A047")), ("En el coche", CAR)], 1)
ex(2, "donde", "Los peces nadan en el mar y los pájaros vuelan en el cielo.", "¿Dónde nadan los peces?", [("En el cielo", I("cloud", "#78909C")), ("En el bosque", S("bosque")), ("En el mar", I("sea", "#039BE5"))], 2)

ex(2, "objeto", "Lo miro para saber la hora.", "¿Qué es?", [("El reloj", I("clock", "#5C6BC0")), ("La lámpara", I("lamp", "#FBC02D")), ("La puerta", I("door", "#8D6E63"))], 0)
ex(2, "objeto", "Sirve para abrir la puerta de casa.", "¿Qué es?", [("La cuchara", I("spoon", "#78909C")), ("La llave", I("key", "#FFB300")), ("La pelota", I("ball", "#E53935"))], 1)
ex(2, "objeto", "Lo abrimos para leer un cuento.", "¿Qué es?", [("La bici", I("bike", "#1E88E5")), ("La cama", I("bed", "#5C6BC0")), ("El libro", I("book", "#8E24AA"))], 2)
ex(2, "objeto", "Lleva a muchos niños a la escuela por la calle.", "¿Qué es?", [("El autobús", I("bus", "#FBC02D")), ("El barco", BOAT), ("El avión", PLANE)], 0)

ex(2, "emocion", "Hay un ruido muy fuerte en la noche y el perrito se esconde.", "¿Cómo se siente el perrito?", [("Asustado", E("asustado")), ("Feliz", E("feliz")), ("Cansado", E("cansado"))], 0)
ex(2, "emocion", "¡Mateo abre la caja y encuentra un regalo!", "¿Cómo se siente Mateo?", [("Triste", E("triste")), ("Sorprendido", E("sorprendido")), ("Cansado", E("cansado"))], 1)
ex(2, "emocion", "Su hermano rompió el dibujo de Luna. Luna aprieta los puños.", "¿Cómo se siente Luna?", [("Feliz", E("feliz")), ("Tranquila", E("tranquilo")), ("Enojada", E("enojado"))], 2)

ex(2, "secuencia", "Primero me pongo la camiseta y después los zapatos.", "¿Qué me pongo después?", [("La camiseta", I("shirt", "#64B5F6")), ("Los zapatos", I("shoes", "#6D4C41")), ("Las gafas", I("glasses", "#5D4037"))], 1)
ex(2, "secuencia", "Luna se lava las manos y después come.", "¿Qué hace Luna primero?", [("Come", I("eat", "#FB8C00")), ("Se lava las manos", I("wash", "#29B6F6")), ("Duerme", I("sleep", "#5C6BC0"))], 1)
ex(2, "secuencia", "Planto la semilla, la riego y crece una flor.", "¿Qué pasa al final?", [("Planto la semilla", I("seed", "#8D6E63")), ("Riego", I("watering", "#039BE5")), ("Crece una flor", I("flower", "#EC407A"))], 2)
ex(2, "secuencia", "Por la mañana sale el sol y por la noche sale la luna.", "¿Qué sale por la noche?", [("El sol", I("sun", "#FFB300")), ("La luna", I("moon", "#FDD835")), ("Una nube", I("cloud", "#78909C"))], 1)

ex(2, "escena", "Mira el dibujo.", "¿Qué preparan los niños?", [("Una pizza", I("pizza", "#F4511E")), ("Un pastel", I("cake", "#AB47BC")), ("Una sopa", I("soup", "#FB8C00"))], 1,
   scene=S("cocina", (MATEO(), .3, .62, .4), (I("cake", "#AB47BC"), .55, .7, .2), (LUNA("emocionado"), .8, .62, .4)))
ex(2, "escena", "Mira el dibujo.", "¿Qué tiempo hace?", [("Hace sol", I("sun", "#FFB300")), ("Llueve", I("rain", "#039BE5")), ("Nieva", I("snow", "#90CAF9"))], 1,
   scene=S("lluvia", (LUNA(), .45, .64, .45), (I("umbrella", "#7E57C2"), .45, .3, .25)))
ex(2, "escena", "Mira el dibujo.", "¿Qué animal vuela?", [("El oso", BEAR), ("El conejo", RABBIT), ("La mariposa", BUTTERFLY)], 2,
   scene=S("bosque", (BEAR, .3, .66, .4), (RABBIT, .7, .74, .25), (BUTTERFLY, .65, .3, .16)))

ex(2, "instruccion", "Toca primero el perro y después el gato.", "Toca en orden.", [("El gato", CAT), ("El pato", DUCK), ("El perro", DOG), ("El conejo", RABBIT)], steps=[2, 0])
ex(2, "instruccion", "Toca la manzana y luego el plátano.", "Toca en orden.", [("El plátano", BANANA), ("Las uvas", GRAPES), ("La manzana", APPLE), ("La fresa", STRAWBERRY)], steps=[2, 0])

# ───────────── Nivel 3: instrucciones de dos pasos y más detalles ─────────────
ex(3, "instruccion", "Primero toca el sol y después la luna.", "Toca en orden.", [("La nube", I("cloud", "#78909C")), ("La luna", I("moon", "#FDD835")), ("La estrella", I("star", "#FBC02D")), ("El sol", I("sun", "#FFB300"))], steps=[3, 1])
ex(3, "instruccion", "Toca la cuchara y después el vaso.", "Toca en orden.", [("El lápiz", I("pencil", "#FFB300")), ("El vaso", I("glass", "#29B6F6")), ("La toalla", I("towel", "#F48FB1")), ("La cuchara", I("spoon", "#78909C"))], steps=[3, 1])
ex(3, "instruccion", "Toca lo que usas para dormir y después lo que usas para comer.", "Toca en orden.", [("La cama", I("bed", "#5C6BC0")), ("La pelota", I("ball", "#E53935")), ("La cuchara", I("spoon", "#78909C")), ("El libro", I("book", "#8E24AA"))], steps=[0, 2])
ex(3, "instruccion", "Toca el animal que nada y después el que vuela.", "Toca en orden.", [("El pez", FISH), ("La mariposa", BUTTERFLY), ("La vaca", COW), ("El oso", BEAR)], steps=[0, 1])
ex(3, "instruccion", "Primero toca a la niña y después al perro.", "Toca en orden.", [("El perro", DOG), ("El niño", MATEO()), ("La niña", LUNA()), ("El gato", CAT)], steps=[2, 0])
ex(3, "instruccion", "Toca el autobús y después el barco.", "Toca en orden.", [("El avión", PLANE), ("El barco", BOAT), ("El autobús", I("bus", "#FBC02D")), ("El tren", TRAIN)], steps=[2, 1])

ex(3, "secuencia", "Mateo se despierta, desayuna y va a la escuela.", "¿Qué hace Mateo después de desayunar?", [("Duerme", I("sleep", "#5C6BC0")), ("Va a la escuela", I("school", "#E53935")), ("Se baña", I("bath", "#29B6F6"))], 1)
ex(3, "secuencia", "Primero llueve, después sale el sol y al final aparece el arcoíris.", "¿Qué aparece al final?", [("La lluvia", I("rain", "#039BE5")), ("El sol", I("sun", "#FFB300")), ("El arcoíris", I("rainbow", "#EC407A"))], 2)
ex(3, "secuencia", "Antes de dormir, Luna se baña y se pone el pijama.", "¿Qué hace Luna antes de ponerse el pijama?", [("Se baña", I("bath", "#29B6F6")), ("Come pizza", I("pizza", "#F4511E")), ("Juega a la pelota", I("ball", "#E53935"))], 0)
ex(3, "secuencia", "El pollito sale del huevo, come semillas y luego duerme con su mamá.", "¿Qué hace el pollito antes de dormir?", [("Nada en el lago", I("swim", "#039BE5")), ("Come semillas", I("seed", "#8D6E63")), ("Vuela al cielo", I("cloud", "#78909C"))], 1)

ex(3, "escena", "Mira el dibujo.", "¿Quién tiene la pelota?", [("Luna", LUNA()), ("Mateo", MATEO()), ("El perro", DOG)], 1,
   scene=S("parque", (LUNA(), .2, .62, .36), (MATEO("feliz", True), .55, .62, .36), (I("ball", "#E53935"), .68, .8, .12), (DOG, .86, .72, .24)))
ex(3, "escena", "Mira el dibujo.", "¿Qué hay en el mar?", [("Un barco", BOAT), ("Un coche", CAR), ("Un tren", TRAIN)], 0,
   scene=S("playa", (LUNA("tranquilo"), .25, .66, .38), (BOAT, .7, .45, .25)))
ex(3, "escena", "Mira el dibujo.", "¿Qué animal NO está en el bosque?", [("El oso", BEAR), ("El conejo", RABBIT), ("La vaca", COW)], 2,
   scene=S("bosque", (BEAR, .3, .66, .4), (RABBIT, .72, .74, .25)))

ex(3, "quien", "El oso le da miel al conejo, y el conejo le da una zanahoria al oso.", "¿Quién da la zanahoria?", [("El oso", BEAR), ("El conejo", RABBIT), ("El mono", MONKEY)], 1)
ex(3, "quien", "Luna le presta su lápiz a Mateo porque él no tiene.", "¿Quién no tiene lápiz?", [("Luna", LUNA()), ("Mateo", MATEO()), ("La maestra", I("teacher", "#00897B"))], 1)

ex(3, "emocion", "El perro de Mateo se perdió, pero ahora vuelve corriendo a casa.", "¿Cómo se siente Mateo al final?", [("Triste", E("triste")), ("Feliz", E("feliz")), ("Asustado", E("asustado"))], 1)

LEVELS = [
    {"level": 1, "title": "Nivel 1", "subtitle": "Escucho una frase"},
    {"level": 2, "title": "Nivel 2", "subtitle": "Escucho y pienso"},
    {"level": 3, "title": "Nivel 3", "subtitle": "Escucho, recuerdo y hago"},
]

if __name__ == "__main__":
    ids = [e["id"] for e in EX]
    assert len(ids) == len(set(ids))
    for e in EX:
        if "answer" in e:
            assert 0 <= e["answer"] < len(e["options"]), e["id"]
    print(len(EX), {l: sum(e["level"] == l for e in EX) for l in (1, 2, 3)},
          save("listening.json", {"format_version": 1, "levels": LEVELS, "exercises": EX}))
