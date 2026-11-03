"""20 cuentos originales de «Lolo me cuenta un cuento».

Cada cuento: título, categoría, portada, personajes, 5 escenas ilustradas
(fondo + personajes y objetos), 3 preguntas con dibujos y 3 escenas para
ordenar. Uso: python3 tools/speech/stories.py
"""

from content_common import BOY, GIRL, I, D, K, S, APPLE, BANANA, STRAWBERRY, ORANGE, GRAPES, LOLO, save

CATEGORIES = ["Animales", "Amistad", "Familia", "Naturaleza", "Emociones", "Hábitos saludables",
              "Aventuras", "Colores", "Valores", "Vida cotidiana"]

DOG, CAT, DUCK, BEAR, RABBIT, MONKEY, COW, TURTLE = (D("animal_perro"), D("animal_gato"), D("granja_patito"),
    D("animal_oso"), D("animal_conejo"), D("animal_mono"), D("granja_vaca"), D("animal_tortuga"))
BUTTERFLY, FISH, HEN = D("animal_mariposa"), D("animal_pez"), D("granja_gallina")
# Cuando el color importa en el cuento, el dibujo lleva ese color en todas sus zonas.
def tinted(drawing, color):
    return D(drawing, **{"*": color})


YELLOW_DUCK = tinted("granja_patito", "#FFD54F")
LUNA = lambda e="feliz", up=False: K(e, True, GIRL, up)
MATEO = lambda e="feliz", up=False: K(e, False, BOY, up)
SOL = lambda e="feliz", up=False: K(e, True, "#FFD54F", up, "#3E2723")
BALL = I("ball", "#E53935")


def sw(c):
    return {"swatch": c}


def Q(question, options, answer=0):
    """options: lista de (texto, dibujo); la correcta es la [answer]."""
    return {"question": question, "options": [{"text": t, "picture": p} for t, p in options], "answer": answer}


def story(sid, title, category, characters, scenes, questions, order=(0, 2, 4), cover=None):
    return {
        "id": sid, "title": title, "category": category,
        "cover": cover or scenes[0][1],
        "characters": [{"name": n, "picture": p} for n, p in characters],
        "scenes": [{"text": t, "picture": p} for t, p in scenes],
        "questions": questions,
        "order": list(order),
    }


ST = []

# Animales.
ST.append(story("toby_pelota", "Toby y la pelota roja", "Animales", [("Toby", DOG), ("Luna", LUNA())], [
    ("Toby es un perro pequeño y juguetón.", S("casa", (DOG, .5, .62, .5))),
    ("Una mañana, Toby encontró una pelota roja.", S("casa", (DOG, .4, .62, .45), (BALL, .75, .78, .16))),
    ("Toby llevó la pelota al jardín.", S("jardin", (DOG, .45, .64, .45), (BALL, .7, .82, .14))),
    ("Su amiga Luna llegó para jugar con él.", S("jardin", (DOG, .32, .66, .4), (LUNA("feliz", True), .7, .6, .45))),
    ("Los dos jugaron felices toda la tarde.", S("jardin", (DOG, .3, .66, .4), (BALL, .52, .5, .14), (LUNA("emocionado", True), .74, .6, .45))),
], [
    Q("¿Cómo se llamaba el perro?", [("Toby", DOG), ("Pipo", DUCK), ("Bruno", BEAR)]),
    Q("¿De qué color era la pelota?", [("Azul", sw("#1E57C8")), ("Roja", sw("#E53935")), ("Verde", sw("#2E7D32"))], 1),
    Q("¿Dónde jugaba Toby?", [("En la escuela", S("escuela")), ("En la playa", S("playa")), ("En el jardín", S("jardin"))], 2),
]))
DUCK = YELLOW_DUCK
ST.append(story("pipo_nadar", "Pipo quiere nadar", "Animales", [("Pipo", DUCK), ("Mamá pata", HEN)], [
    ("Pipo es un patito amarillo que vive junto al lago.", S("parque", (DUCK, .5, .64, .45))),
    ("Pipo quería nadar, pero el agua le daba un poco de miedo.", S("playa", (DUCK, .5, .78, .35))),
    ("Su mamá le dijo: «Lo haremos juntos, despacito».", S("playa", (HEN, .32, .74, .38), (DUCK, .66, .8, .3))),
    ("Pipo metió una patita, luego la otra… ¡y empezó a flotar!", S("playa", (DUCK, .5, .62, .35))),
    ("Desde ese día, Pipo nada feliz con su mamá.", S("playa", (HEN, .35, .6, .32), (DUCK, .65, .64, .28))),
], [
    Q("¿Qué animal es Pipo?", [("Un patito", DUCK), ("Un gato", CAT), ("Un mono", MONKEY)]),
    Q("¿Qué quería hacer Pipo?", [("Volar", I("cloud", "#64B5F6")), ("Nadar", I("swim", "#0288D1")), ("Dormir", I("sleep", "#5C6BC0"))], 1),
    Q("¿Quién lo ayudó?", [("Su mamá", HEN), ("Un perro", DOG), ("Lolo", LOLO)]),
]))

# Amistad.
ST.append(story("rita_tito", "Rita y Tito comparten", "Amistad", [("Rita", RABBIT), ("Tito", MONKEY)], [
    ("Rita, la coneja, tenía tres zanahorias.", S("jardin", (RABBIT, .5, .62, .45), (I("salad", "#FB8C00"), .8, .8, .16))),
    ("Tito, el mono, tenía muchos plátanos.", S("bosque", (MONKEY, .45, .62, .45), (BANANA, .78, .8, .2))),
    ("Tito tenía hambre de zanahorias, y Rita de plátanos.", S("parque", (RABBIT, .3, .64, .4), (MONKEY, .7, .64, .4))),
    ("Entonces decidieron compartir.", S("parque", (RABBIT, .3, .64, .38), (BANANA, .5, .82, .16), (MONKEY, .72, .64, .38))),
    ("¡Compartir hizo la merienda más divertida!", S("parque", (RABBIT, .32, .62, .4), (MONKEY, .68, .62, .4), (I("love", "#E91E63"), .5, .3, .16))),
], [
    Q("¿Qué tenía Rita?", [("Zanahorias", I("salad", "#FB8C00")), ("Pelotas", BALL), ("Libros", I("book", "#E53935"))]),
    Q("¿Qué comía Tito?", [("Fresas", STRAWBERRY), ("Pan", I("bread", "#C77C2E")), ("Plátanos", BANANA)], 2),
    Q("¿Qué hicieron los amigos?", [("Compartir", I("friends", "#00ACC1")), ("Pelear", I("sad", "#E53935")), ("Dormir", I("sleep", "#5C6BC0"))]),
]))
ST.append(story("mateo_amigo", "El nuevo amigo de Mateo", "Amistad", [("Mateo", MATEO()), ("Sol", SOL())], [
    ("Mateo llegó a una escuela nueva.", S("escuela", (MATEO("asustado"), .5, .64, .48))),
    ("No conocía a nadie y estaba un poco triste.", S("escuela", (MATEO("triste"), .5, .64, .48))),
    ("Una niña llamada Sol se acercó y le dijo: «¡Hola!».", S("escuela", (MATEO("sorprendido"), .32, .64, .42), (SOL("feliz", True), .7, .64, .42))),
    ("Sol lo invitó a jugar con los bloques.", S("escuela", (MATEO(), .3, .64, .4), (I("blocks", "#43A047"), .5, .82, .16), (SOL(), .72, .64, .4))),
    ("Desde ese día, Mateo y Sol son buenos amigos.", S("parque", (MATEO("feliz", True), .32, .62, .42), (SOL("feliz", True), .7, .62, .42))),
], [
    Q("¿Cómo se sentía Mateo al principio?", [("Triste", K("triste")), ("Enojado", K("enojado")), ("Con sueño", K("cansado"))]),
    Q("¿Quién saludó a Mateo?", [("Lolo", LOLO), ("Sol", SOL()), ("Un perro", DOG)], 1),
    Q("¿Con qué jugaron?", [("Con bloques", I("blocks", "#43A047")), ("Con agua", I("water", "#039BE5")), ("Con un tren", D("vehiculo_tren"))]),
]))

# Familia.
ST.append(story("abuela_pastel", "Cocinamos con la abuela", "Familia", [("Luna", LUNA()), ("La abuela", I("elderly_woman", "#8E24AA"))], [
    ("Luna fue a visitar a su abuela.", S("casa", (LUNA("feliz", True), .35, .64, .42), (I("elderly_woman", "#8E24AA"), .7, .64, .38))),
    ("La abuela dijo: «¡Hagamos un pastel!».", S("cocina", (I("elderly_woman", "#8E24AA"), .4, .6, .4), (I("cake", "#AB47BC"), .74, .72, .2))),
    ("Luna puso la harina y la abuela, los huevos.", S("cocina", (LUNA(), .35, .64, .4), (I("egg", "#F9A825"), .66, .76, .14))),
    ("Esperaron juntas mientras el pastel se horneaba.", S("cocina", (LUNA("tranquilo"), .35, .64, .4), (I("clock", "#00897B"), .7, .4, .18))),
    ("¡El pastel quedó delicioso y lo compartieron!", S("cocina", (LUNA("emocionado", True), .32, .62, .4), (I("cake", "#AB47BC"), .68, .72, .22))),
], [
    Q("¿A quién visitó Luna?", [("A su abuela", I("elderly_woman", "#8E24AA")), ("A su maestra", I("teacher", "#3949AB")), ("A Toby", DOG)]),
    Q("¿Qué cocinaron?", [("Una sopa", I("soup", "#FB8C00")), ("Un pastel", I("cake", "#AB47BC")), ("Una pizza", I("pizza", "#F4511E"))], 1),
    Q("¿Cómo quedó el pastel?", [("Delicioso", K("feliz")), ("Quemado", I("fire", "#F4511E")), ("Frío", I("snow", "#4FC3F7"))]),
]))
ST.append(story("cumple_papa", "El cumpleaños de papá", "Familia", [("Mateo", MATEO()), ("Papá", I("man", "#3949AB"))], [
    ("Hoy es el cumpleaños de papá.", S("casa", (I("man", "#3949AB"), .5, .6, .45))),
    ("Mateo quería darle una sorpresa.", S("dormitorio", (MATEO("emocionado", True), .5, .64, .48))),
    ("Mateo pintó un dibujo con muchos colores.", S("casa", (MATEO(), .4, .64, .42), (I("paint", "#E91E63"), .75, .7, .2))),
    ("Le dio el dibujo a papá con un abrazo.", S("casa", (MATEO("feliz", True), .35, .64, .4), (I("gift", "#E53935"), .5, .76, .14), (I("man", "#3949AB"), .72, .62, .38))),
    ("Papá dijo: «¡Es el mejor regalo del mundo!».", S("casa", (I("man", "#3949AB"), .4, .6, .42), (I("love", "#E91E63"), .72, .4, .2))),
], [
    Q("¿De quién era el cumpleaños?", [("De papá", I("man", "#3949AB")), ("De Lolo", LOLO), ("De la abuela", I("elderly_woman", "#8E24AA"))]),
    Q("¿Qué regaló Mateo?", [("Una pelota", BALL), ("Un dibujo", I("paint", "#E91E63")), ("Un pastel", I("cake", "#AB47BC"))], 1),
    Q("¿Cómo se sintió papá?", [("Feliz", K("feliz")), ("Triste", K("triste")), ("Enojado", K("enojado"))]),
]))

# Naturaleza.
ST.append(story("semilla_luna", "La semilla de Luna", "Naturaleza", [("Luna", LUNA())], [
    ("Luna encontró una semilla pequeñita.", S("jardin", (LUNA("sorprendido"), .5, .62, .45), (I("seed", "#8D6E63"), .78, .78, .12))),
    ("La plantó en una maceta con tierra.", S("jardin", (LUNA(), .4, .62, .42), (I("plant", "#8D6E63"), .74, .76, .18))),
    ("Cada día la regaba con un poco de agua.", S("jardin", (LUNA(), .4, .62, .42), (I("water", "#039BE5"), .74, .66, .16))),
    ("Un día salió una plantita verde.", S("jardin", (I("sprout", "#43A047"), .5, .72, .3))),
    ("¡Y al final creció una flor muy bonita!", S("jardin", (LUNA("emocionado", True), .35, .62, .42), (I("flower", "#EC407A"), .72, .66, .3))),
], [
    Q("¿Qué encontró Luna?", [("Una semilla", I("seed", "#8D6E63")), ("Una piedra", I("circle", "#9E9E9E")), ("Un juguete", I("toys", "#FB8C00"))]),
    Q("¿Qué le daba Luna a la planta?", [("Leche", I("glass", "#90A4AE")), ("Agua", I("water", "#039BE5")), ("Pan", I("bread", "#C77C2E"))], 1),
    Q("¿Qué creció al final?", [("Una flor", I("flower", "#EC407A")), ("Un árbol de manzanas", APPLE), ("Una nube", I("cloud", "#64B5F6"))]),
]))
ST.append(story("lluvia_arcoiris", "La lluvia y el arcoíris", "Naturaleza", [("Mateo", MATEO()), ("Toby", DOG)], [
    ("Mateo quería salir a jugar con Toby.", S("casa", (MATEO(), .35, .64, .42), (DOG, .7, .68, .35))),
    ("Pero empezó a llover mucho.", S("lluvia", (MATEO("triste"), .5, .64, .45))),
    ("Mateo esperó mirando por la ventana.", S("casa", (MATEO("tranquilo"), .4, .64, .45))),
    ("Cuando paró la lluvia, salió el sol.", S("jardin", (I("sun", "#FFB300"), .5, .35, .3))),
    ("¡Y en el cielo apareció un arcoíris de colores!", S("cielo", (I("rainbow", "#EC407A"), .5, .45, .55), (MATEO("emocionado", True), .3, .75, .35), (DOG, .72, .8, .28))),
], [
    Q("¿Qué pasó cuando Mateo quería jugar?", [("Empezó a llover", I("umbrella", "#5C6BC0")), ("Se hizo de noche", I("moon", "#5C6BC0")), ("Nevó", I("snow", "#4FC3F7"))]),
    Q("¿Qué salió cuando paró la lluvia?", [("La luna", I("moon", "#5C6BC0")), ("El sol", I("sun", "#FFB300")), ("Las estrellas", I("star", "#FBC02D"))], 1),
    Q("¿Qué apareció en el cielo?", [("Un arcoíris", I("rainbow", "#EC407A")), ("Un avión", D("vehiculo_avion")), ("Un barco", D("vehiculo_barco"))]),
], order=(1, 3, 4)))

# Emociones.
ST.append(story("bruno_noche", "Bruno y la noche", "Emociones", [("Bruno", BEAR), ("Mamá osa", BEAR)], [
    ("Bruno es un osito que vive en el bosque.", S("bosque", (BEAR, .5, .64, .45))),
    ("Cuando llegó la noche, Bruno sintió miedo.", S("noche", (BEAR, .5, .66, .42))),
    ("Bruno le dijo a su mamá: «Tengo miedo».", S("noche", (BEAR, .32, .66, .36), (BEAR, .7, .62, .45))),
    ("Mamá encendió una lucecita y le dio un abrazo.", S("dormitorio", (I("lamp", "#FBC02D"), .78, .4, .18), (BEAR, .4, .64, .42))),
    ("Bruno se sintió tranquilo y se durmió.", S("dormitorio", (BEAR, .4, .64, .4), (I("sleepz", "#5C6BC0"), .72, .4, .18))),
], [
    Q("¿Qué animal es Bruno?", [("Un osito", BEAR), ("Un gato", CAT), ("Un conejo", RABBIT)]),
    Q("¿Cómo se sintió Bruno de noche?", [("Feliz", K("feliz")), ("Con miedo", K("asustado")), ("Enojado", K("enojado"))], 1),
    Q("¿Qué lo ayudó?", [("Una luz y un abrazo", I("lamp", "#FBC02D")), ("Un helado", I("icecream", "#EC407A")), ("Una pelota", BALL)]),
]))
ST.append(story("mateo_enojo", "Cuando Mateo se enojó", "Emociones", [("Mateo", MATEO()), ("Sol", SOL())], [
    ("Mateo hizo una torre muy alta con bloques.", S("casa", (MATEO("feliz"), .4, .64, .42), (I("blocks", "#43A047"), .74, .68, .24))),
    ("Sin querer, Sol tocó la torre y se cayó.", S("casa", (SOL("sorprendido"), .66, .64, .42), (I("blocks", "#43A047"), .35, .82, .18))),
    ("Mateo se enojó mucho.", S("casa", (MATEO("enojado"), .5, .64, .48))),
    ("Respiró despacio y dijo: «Estoy enojado porque se cayó mi torre».", S("casa", (MATEO("tranquilo"), .5, .64, .48))),
    ("Sol le pidió perdón y construyeron una torre juntos.", S("casa", (MATEO("feliz"), .3, .64, .4), (I("blocks", "#43A047"), .5, .7, .2), (SOL("feliz"), .72, .64, .4))),
], [
    Q("¿Qué construyó Mateo?", [("Una torre", I("blocks", "#43A047")), ("Un barco", D("vehiculo_barco")), ("Una casa", I("home", "#F4511E"))]),
    Q("¿Cómo se sintió Mateo cuando se cayó la torre?", [("Feliz", K("feliz")), ("Enojado", K("enojado")), ("Con sueño", K("cansado"))], 1),
    Q("¿Qué hizo Mateo para calmarse?", [("Respirar despacio", K("tranquilo")), ("Gritar", I("sad", "#E53935")), ("Correr", I("run", "#43A047"))]),
]))

# Hábitos saludables.
ST.append(story("sol_dientes", "Los dientes brillantes de Sol", "Hábitos saludables", [("Sol", SOL())], [
    ("Sol comió una merienda muy rica.", S("cocina", (SOL(), .4, .64, .42), (APPLE, .76, .72, .18))),
    ("Después fue al baño a lavarse los dientes.", S("casa", (SOL(), .4, .64, .42), (I("wash", "#29B6F6"), .74, .62, .2))),
    ("Puso un poquito de pasta en el cepillo.", S("casa", (I("clean", "#29B6F6"), .5, .6, .3))),
    ("Cepilló arriba, abajo y por todos lados.", S("casa", (SOL("feliz", True), .5, .64, .48))),
    ("¡Sus dientes quedaron limpios y brillantes!", S("casa", (SOL("emocionado", True), .45, .64, .45), (I("star", "#FBC02D"), .78, .34, .16))),
], [
    Q("¿Qué hizo Sol después de comer?", [("Se lavó los dientes", I("wash", "#29B6F6")), ("Se durmió", I("sleep", "#5C6BC0")), ("Pintó", I("paint", "#E91E63"))]),
    Q("¿Qué usó para lavarse los dientes?", [("Una cuchara", I("spoon", "#8D6E63")), ("Un cepillo", I("clean", "#29B6F6")), ("Un libro", I("book", "#E53935"))], 1),
    Q("¿Cómo quedaron sus dientes?", [("Brillantes", I("star", "#FBC02D")), ("Sucios", I("trash", "#8D6E63")), ("Azules", sw("#1E57C8"))]),
]))
ST.append(story("lola_frutas", "Lola come frutas", "Hábitos saludables", [("Lola", COW), ("Lolo", LOLO)], [
    ("Lola, la vaca, siempre tenía poca energía.", S("parque", (COW, .5, .64, .45))),
    ("Lolo le dijo: «¡Prueba las frutas!».", S("parque", (COW, .35, .64, .4), (LOLO, .72, .58, .35))),
    ("Lola probó una manzana, un plátano y unas uvas.", S("cocina", (APPLE, .28, .7, .2), (BANANA, .5, .72, .2), (GRAPES, .72, .7, .2))),
    ("También bebió mucha agua fresca.", S("parque", (COW, .45, .64, .42), (I("water", "#039BE5"), .78, .62, .18))),
    ("¡Ahora Lola corre y salta con mucha energía!", S("parque", (COW, .45, .6, .45), (I("star", "#FBC02D"), .8, .3, .14))),
], [
    Q("¿Qué animal es Lola?", [("Una vaca", COW), ("Una gallina", HEN), ("Un pez", FISH)]),
    Q("¿Quién le dio un consejo?", [("Toby", DOG), ("Lolo", LOLO), ("Bruno", BEAR)], 1),
    Q("¿Qué comió Lola?", [("Frutas", APPLE), ("Caramelos", I("cookie", "#8D6E63")), ("Nada", I("circle", "#9E9E9E"))]),
]))

# Aventuras.
ST.append(story("barco_papel", "El barco de papel", "Aventuras", [("Mateo", MATEO()), ("Luna", LUNA())], [
    ("Mateo y Luna hicieron un barco de papel.", S("casa", (MATEO(), .3, .64, .4), (D("vehiculo_barco"), .5, .78, .2), (LUNA(), .72, .64, .4))),
    ("Lo llevaron al charco del parque.", S("parque", (D("vehiculo_barco"), .5, .8, .22))),
    ("El viento empujó el barco… ¡fush!", S("parque", (D("vehiculo_barco"), .62, .78, .22), (I("wind", "#90CAF9"), .32, .5, .2))),
    ("El barquito navegó hasta el otro lado.", S("parque", (D("vehiculo_barco"), .8, .78, .2), (MATEO("emocionado", True), .3, .62, .38))),
    ("Los dos aplaudieron: «¡Qué gran aventura!».", S("parque", (MATEO("feliz", True), .3, .62, .4), (LUNA("feliz", True), .7, .62, .4))),
], [
    Q("¿Qué hicieron Mateo y Luna?", [("Un barco de papel", D("vehiculo_barco")), ("Un avión", D("vehiculo_avion")), ("Un tren", D("vehiculo_tren"))]),
    Q("¿Dónde navegó el barco?", [("En el charco del parque", S("parque")), ("En la cocina", S("cocina")), ("En la escuela", S("escuela"))]),
    Q("¿Qué empujó el barco?", [("El viento", I("wind", "#90CAF9")), ("Un perro", DOG), ("La lluvia", I("umbrella", "#5C6BC0"))]),
]))
ST.append(story("tesoro_parque", "El tesoro del parque", "Aventuras", [("Sol", SOL()), ("Toby", DOG)], [
    ("Sol encontró un mapa del tesoro.", S("casa", (SOL("sorprendido"), .4, .64, .42), (I("map", "#8D6E63"), .76, .66, .2))),
    ("Con Toby, siguió el camino hasta el árbol grande.", S("parque", (SOL(), .3, .64, .4), (DOG, .58, .7, .3))),
    ("Toby olfateó y empezó a escarbar.", S("parque", (DOG, .5, .7, .4))),
    ("¡Encontraron una caja llena de pinturas!", S("parque", (I("gift", "#E53935"), .5, .74, .24), (I("paint2", "#E91E63"), .5, .44, .2))),
    ("Ese día pintaron el dibujo más bonito del mundo.", S("casa", (SOL("emocionado", True), .4, .62, .42), (I("paint2", "#E91E63"), .76, .68, .2))),
], [
    Q("¿Qué encontró Sol al principio?", [("Un mapa", I("map", "#8D6E63")), ("Una flor", I("flower", "#EC407A")), ("Un libro", I("book", "#E53935"))]),
    Q("¿Quién escarbó?", [("Lolo", LOLO), ("Toby", DOG), ("Un gato", CAT)], 1),
    Q("¿Qué había en la caja?", [("Pinturas", I("paint2", "#E91E63")), ("Comida", I("eat", "#F4511E")), ("Zapatos", I("shoes", "#8D6E63"))]),
]))

# Colores.
ST.append(story("mariposa_colores", "La mariposa de colores", "Colores", [("Mariposa", BUTTERFLY), ("Luna", LUNA())], [
    ("En el jardín vivía una mariposa blanca.", S("jardin", (tinted("animal_mariposa", "#FFFFFF"), .5, .5, .4))),
    ("Se posó en una flor roja y sus alas se pusieron rojas.", S("jardin", (tinted("animal_mariposa", "#E53935"), .5, .45, .32), (I("flower", "#E53935"), .5, .75, .2))),
    ("Luego voló a una flor amarilla… ¡y se volvió amarilla!", S("jardin", (tinted("animal_mariposa", "#FFD600"), .5, .45, .32), (I("flower", "#FFD600"), .5, .75, .2))),
    ("Después visitó una flor azul y otra morada.", S("jardin", (I("flower", "#1E57C8"), .35, .75, .2), (I("flower", "#8E44AD"), .65, .75, .2))),
    ("Luna dijo: «¡Es la mariposa más colorida del jardín!».", S("jardin", (LUNA("emocionado", True), .35, .62, .42), (BUTTERFLY, .72, .4, .3))),
], [
    Q("¿De qué color era la mariposa al principio?", [("Blanca", sw("#FFFFFF")), ("Negra", sw("#212121")), ("Verde", sw("#2E7D32"))]),
    Q("¿Dónde se posaba la mariposa?", [("En las flores", I("flower", "#EC407A")), ("En los autos", D("vehiculo_automovil")), ("En la mesa", I("table", "#795548"))]),
    Q("¿De qué color se volvió con la flor amarilla?", [("Roja", sw("#E53935")), ("Amarilla", sw("#FFD600")), ("Azul", sw("#1E57C8"))], 1),
]))
ST.append(story("pintor_arcoiris", "El pintor del arcoíris", "Colores", [("Mateo", MATEO()), ("Lolo", LOLO)], [
    ("Mateo quería pintar un arcoíris.", S("casa", (MATEO(), .45, .64, .45), (I("paint2", "#E91E63"), .78, .68, .18))),
    ("Primero pintó el rojo, como una manzana.", S("casa", (APPLE, .35, .62, .25), (sw("#E53935"), .68, .62, .25))),
    ("Después el amarillo, como el sol.", S("casa", (I("sun", "#FFB300"), .35, .6, .25), (sw("#FFD600"), .68, .62, .25))),
    ("Luego el verde, como el pasto, y el azul, como el mar.", S("casa", (sw("#2E7D32"), .35, .62, .25), (sw("#1E57C8"), .68, .62, .25))),
    ("Lolo dijo: «¡Qué arcoíris tan bonito!».", S("cielo", (I("rainbow", "#EC407A"), .5, .45, .55), (LOLO, .8, .75, .25))),
], [
    Q("¿Qué quería pintar Mateo?", [("Un arcoíris", I("rainbow", "#EC407A")), ("Un perro", DOG), ("Una casa", I("home", "#F4511E"))]),
    Q("¿Qué color es como el sol?", [("Azul", sw("#1E57C8")), ("Amarillo", sw("#FFD600")), ("Verde", sw("#2E7D32"))], 1),
    Q("¿Qué color es como el mar?", [("Azul", sw("#1E57C8")), ("Rojo", sw("#E53935")), ("Marrón", sw("#8D5524"))]),
]))

# Valores.
ST.append(story("nina_paciencia", "La paciencia de Nina", "Valores", [("Nina", TURTLE), ("Rita", RABBIT)], [
    ("Nina es una tortuga que camina despacito.", S("bosque", (TURTLE, .5, .7, .45))),
    ("Rita, la coneja, siempre iba muy rápido.", S("bosque", (RABBIT, .5, .64, .42))),
    ("Un día, Rita se torció la pata y no podía saltar.", S("bosque", (RABBIT, .5, .66, .42), (I("hurt", "#E53935"), .76, .4, .16))),
    ("Nina la esperó y caminó a su lado, sin prisa.", S("bosque", (TURTLE, .32, .72, .36), (RABBIT, .68, .66, .36))),
    ("Rita le dijo: «Gracias por esperarme, amiga».", S("jardin", (TURTLE, .32, .72, .36), (RABBIT, .66, .64, .38), (I("love", "#E91E63"), .5, .3, .14))),
], [
    Q("¿Cómo camina Nina?", [("Despacito", TURTLE), ("Muy rápido", I("run", "#43A047")), ("Volando", BUTTERFLY)]),
    Q("¿Qué le pasó a Rita?", [("Se torció la pata", I("hurt", "#E53935")), ("Se durmió", I("sleep", "#5C6BC0")), ("Comió mucho", I("eat", "#F4511E"))]),
    Q("¿Qué dijo Rita al final?", [("¡Vete!", I("sad", "#E53935")), ("Gracias, amiga", I("love", "#E91E63")), ("Nada", I("circle", "#9E9E9E"))], 1),
]))
ST.append(story("tito_verdad", "Tito dice la verdad", "Valores", [("Tito", MONKEY), ("Mamá", I("woman", "#AB47BC"))], [
    ("Tito jugaba con la pelota dentro de casa.", S("casa", (MONKEY, .45, .64, .42), (BALL, .78, .78, .14))),
    ("¡Pum! La pelota rompió un vaso.", S("casa", (I("glass", "#90A4AE"), .5, .72, .2), (BALL, .72, .8, .14))),
    ("Tito tenía miedo, pero decidió decir la verdad.", S("casa", (MONKEY, .5, .64, .45))),
    ("Le dijo a mamá: «Fui yo. Lo siento».", S("casa", (MONKEY, .35, .66, .38), (I("woman", "#AB47BC"), .7, .62, .4))),
    ("Mamá le dio un abrazo: «Gracias por decir la verdad».", S("casa", (MONKEY, .38, .66, .36), (I("woman", "#AB47BC"), .65, .62, .4), (I("love", "#E91E63"), .5, .3, .14))),
], [
    Q("¿Con qué jugaba Tito?", [("Con una pelota", BALL), ("Con un tren", D("vehiculo_tren")), ("Con pinturas", I("paint", "#E91E63"))]),
    Q("¿Qué se rompió?", [("Un vaso", I("glass", "#90A4AE")), ("Una silla", I("chair", "#8D6E63")), ("Una ventana", I("window", "#29B6F6"))]),
    Q("¿Qué hizo Tito?", [("Se escondió", I("search", "#8D6E63")), ("Dijo la verdad", I("talk", "#26A69A")), ("Lloró", K("triste"))], 1),
]))

# Vida cotidiana.
ST.append(story("dia_escuela", "Un día en la escuela", "Vida cotidiana", [("Luna", LUNA()), ("La maestra", I("teacher", "#3949AB"))], [
    ("Luna se puso su mochila y fue a la escuela.", S("parque", (LUNA("feliz"), .45, .64, .45), (I("backpack", "#E53935"), .78, .7, .16))),
    ("Saludó a la maestra: «¡Buenos días!».", S("escuela", (LUNA("feliz", True), .32, .64, .4), (I("teacher", "#3949AB"), .7, .64, .36))),
    ("En clase aprendieron las letras.", S("escuela", (I("abc", "#E53935"), .5, .75, .25))),
    ("En el recreo jugó con sus amigos.", S("parque", (LUNA("emocionado", True), .32, .62, .4), (MATEO("feliz", True), .7, .62, .4))),
    ("Al volver a casa, le contó todo a su mamá.", S("casa", (LUNA("feliz"), .35, .64, .4), (I("woman", "#AB47BC"), .7, .62, .38))),
], [
    Q("¿Adónde fue Luna?", [("A la escuela", S("escuela")), ("A la playa", S("playa")), ("Al bosque", S("bosque"))]),
    Q("¿Qué aprendieron en clase?", [("Las letras", I("abc", "#E53935")), ("A nadar", I("swim", "#0288D1")), ("A cocinar", I("cake", "#AB47BC"))]),
    Q("¿A quién le contó todo al volver?", [("A Lolo", LOLO), ("A su mamá", I("woman", "#AB47BC")), ("A Toby", DOG)], 1),
]))
ST.append(story("mercado", "Vamos al mercado", "Vida cotidiana", [("Mateo", MATEO()), ("Papá", I("man", "#3949AB"))], [
    ("Mateo y papá fueron al mercado.", S("parque", (MATEO(), .3, .64, .4), (I("man", "#3949AB"), .7, .62, .38))),
    ("Compraron manzanas rojas y plátanos amarillos.", S("casa", (APPLE, .35, .66, .24), (BANANA, .66, .68, .24))),
    ("Mateo ayudó a llevar la bolsa.", S("parque", (MATEO("feliz"), .45, .64, .45), (I("shop", "#FB8C00"), .78, .7, .18))),
    ("En casa lavaron las frutas.", S("cocina", (I("water", "#039BE5"), .4, .6, .18), (APPLE, .64, .72, .2))),
    ("¡Y prepararon una ensalada de frutas deliciosa!", S("cocina", (MATEO("emocionado", True), .35, .62, .42), (GRAPES, .72, .7, .22))),
], [
    Q("¿Adónde fueron Mateo y papá?", [("Al mercado", I("shop", "#FB8C00")), ("Al cine", I("tv", "#5C6BC0")), ("Al hospital", I("hospital", "#E53935"))]),
    Q("¿Qué compraron?", [("Frutas", APPLE), ("Juguetes", I("toys", "#FB8C00")), ("Zapatos", I("shoes", "#8D6E63"))]),
    Q("¿Qué prepararon al final?", [("Una sopa", I("soup", "#FB8C00")), ("Una ensalada de frutas", GRAPES), ("Un pastel", I("cake", "#AB47BC"))], 1),
]))

assert len(ST) == 20, len(ST)

if __name__ == "__main__":
    path = save("stories.json", {"format_version": 1, "categories": CATEGORIES, "stories": ST})
    per = {}
    for s in ST:
        per[s["category"]] = per.get(s["category"], 0) + 1
    print(len(ST), "cuentos", per, "->", path)
