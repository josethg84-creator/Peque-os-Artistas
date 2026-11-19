"""«Aprendo a leer» · Fase 5: «Leo mis primeras oraciones».

Genera assets/reading/sentences.json con el catálogo de oraciones, sus
preguntas de comprensión y los datos de «Ordena la oración» y «Escucha y
selecciona». Solo datos: la app no inventa nada en tiempo de ejecución.

El NIVEL de cada oración no se escribe a mano: se calcula con reglas fijas y
se comprueba que coincide con el bloque donde está escrita (si no, falla):

- Nivel 1 · «Muy sencillas»: TODAS las sílabas se pueden leer con lo enseñado
  en la Fase 3 (vocales y familias M P S L T N D F C·Q B): sílabas directas
  (ma, que…), vocales solas e inversas con L, S o N (el, es, un). Sin
  diptongos, sin sílabas trabadas (pan, sol) y sin otras letras (r, g, j, v,
  z, ñ, ll, ch, h, y consonante).
- Nivel 4 · «Grupos consonánticos»: alguna palabra tiene pl, bl, cl, gl, fl,
  pr, br, tr, dr, cr, gr o fr.
- Nivel 3 · «Descriptivas»: sin grupos consonánticos y con 6 palabras o más.
- Nivel 2 · «De todos los días»: el resto (hasta 5 palabras, sin grupos).

Validaciones:
- separación silábica con syllabify.py (la misma que comprueba la app);
- cada pregunta tiene 3 opciones distintas, todas con imagen, y una sola
  correcta; la respuesta aparece en la oración (es la palabra que se resalta
  como pista);
- «Ordena la oración» solo con oraciones de 3 a 7 palabras, sin «y» (dos
  partes que se podrían intercambiar) y sin las marcadas como ambiguas; la
  mayúscula inicial y el punto final se mantienen como pistas;
- «Escucha y selecciona»: las otras dos ilustraciones no comparten ningún
  elemento ni fondo con la correcta.

Imágenes: cada oración lleva una escena PROVISIONAL compuesta con fondos y
dibujos que ya tiene la app; la ilustración 3D definitiva es
assets/images/aprendo_leer/oraciones/<id>.webp y queda pendiente si no existe.

Audio: si existe assets/audio/reading/oraciones/<id>.mp3 se usa la grabación;
si además existe <id>.json con los milisegundos en que empieza cada palabra
(medidos sobre la grabación), se usan para resaltar. Si no, la voz del
dispositivo.

Uso: python3 tools/reading/sentences.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from syllabify import split  # noqa: E402
from words import WORDS as WORD_LIST, plain  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
IMAGES = "assets/images/aprendo_leer/oraciones"
AUDIO = "assets/audio/reading/oraciones"
WORD_AUDIO = "assets/audio/reading/palabras"


def I(i):
    return {"icon": i}


def SC(bg):
    return {"scene": bg}


# Imágenes de las opciones y de las escenas: las del catálogo de palabras
# (Fase 4) y algunas más que ya existen en la app.
PIC = {wid: (text, pic) for wid, text, _cat, pic in WORD_LIST if pic}
PIC.update({
    "mama": ("mamá", I("woman")),
    "papa": ("papá", I("man")),
    "abuela": ("abuela", I("elderly_woman")),
    "abuelo": ("abuelo", I("elderly")),
    "banana": ("banana", {"drawing": "fruta_platano"}),
    "leche": ("leche", I("milk")),
    "foto": ("foto", I("photo_camera")),
    "manos": ("manos", {"body": "manos"}),
    "pies": ("pies", {"body": "pies"}),
    "orejas": ("orejas", {"body": "orejas"}),
    "dientes": ("dientes", I("tooth")),
    "lluvia": ("lluvia", I("rain")),
    "nieve": ("nieve", I("snow")),
    "frio": ("frío", I("severe_cold")),
    "sueno": ("sueño", I("bedtime")),
    "hambre": ("hambre", I("restaurant")),
    "cuento": ("cuento", I("auto_stories")),
    "zanahoria": ("zanahoria", I("carrot")),
    "camisa": ("camisa", I("shirt")),
    "zapatos": ("zapatos", I("shoes")),
    "lentes": ("lentes", I("glasses")),
    "pajaro": ("pájaro", I("bird")),
    "frutas": ("frutas", I("apple")),
    "feliz": ("feliz", {"emotion": "feliz"}),
    "triste": ("triste", {"emotion": "triste"}),
    "enojado": ("enojado", {"emotion": "enojado"}),
    "cansado": ("cansado", {"emotion": "cansado"}),
    "asustado": ("asustado", {"emotion": "asustado"}),
    "ana": ("Ana", {"kid": {"girl": True, "emotion": "feliz", "shirt": "#EC407A"}}),
    "memo": ("Memo", {"kid": {"girl": False, "emotion": "feliz", "shirt": "#42A5F5"}}),
    "cafe": ("café", {"swatch": "#795548"}),
    "naranja_color": ("naranja", {"swatch": "#FB8C00"}),
    # Lugares (solo el fondo).
    "playa": ("playa", SC("playa")),
    "mar": ("mar", SC("playa")),
    "parque": ("parque", SC("parque")),
    "escuela_lugar": ("escuela", SC("escuela")),
    "jardin": ("jardín", SC("jardin")),
    "bosque": ("bosque", SC("bosque")),
    "cocina": ("cocina", SC("cocina")),
    "noche": ("de noche", SC("noche")),
    "dia": ("de día", I("wb_sunny")),
    "con_lluvia": ("con lluvia", SC("lluvia")),
    "nublado": ("nublado", I("cloud")),
    "soleado": ("soleado", I("sun")),
    "estrellado": ("con estrellas", I("star")),
})

LEVELS = [
    {"id": 1, "name": "Muy sencillas", "description": "Solo con las sílabas que ya conoces."},
    {"id": 2, "name": "De todos los días", "description": "Oraciones cortas de cosas que hacemos."},
    {"id": 3, "name": "Descriptivas", "description": "Oraciones más largas que cuentan cómo son las cosas."},
    {"id": 4, "name": "Con grupos de letras", "description": "Palabras con bl, tr, pr, fl…"},
]

# (oración, (fondo, [elementos de la escena]), pregunta, [3 opciones], índice
#  correcto, extras). Una opción es una clave de PIC o (clave, texto).
# extras: "order": False si al ordenarla hay otra oración válida (por ejemplo,
#         un adjetivo que también puede ir delante: «el pequeño perro»);
#         "hint": palabra de la oración que responde (si no es el texto de la
#         respuesta).
L1 = [
    ("Mi mamá me ama.", ("casa", ["mama", "memo"]), "¿Quién me ama?", ["mama", "papa", "bebe"], 0, {}),
    ("Papá toma sopa.", ("cocina", ["papa", "sopa"]), "¿Qué toma papá?", ["sopa", "helado", "pizza"], 0, {}),
    ("El pato nada.", ("playa", ["pato"]), "¿Quién nada?", ["pato", "mono", "oso"], 0, {}),
    ("La mesa es de Ana.", ("casa", ["mesa", "ana"]), "¿Qué es de Ana?", ["mesa", "cama", "cuna"], 0, {}),
    ("El oso camina.", ("bosque", ["oso"]), "¿Quién camina?", ["oso", "pato", "mono"], 0, {}),
    ("La pelota es de Memo.", ("parque", ["pelota", "memo"]), "¿Qué es de Memo?",
     ["pelota", "mapa", "foco"], 0, {}),
    ("Sale la luna.", ("noche", ["luna"]), "¿Qué sale?", ["luna", "sol", "nube"], 0, {}),
    ("El bebé come sopa.", ("cocina", ["bebe", "sopa"]), "¿Quién come sopa?", ["bebe", "papa", "abuela"], 0, {}),
    ("Tito tapa la cuna.", ("dormitorio", ["cuna", "memo"]), "¿Qué tapa Tito?", ["cuna", "mesa", "cama"], 0, {}),
    ("Pepe usa el mapa.", ("escuela", ["mapa", "memo"]), "¿Qué usa Pepe?", ["mapa", "pelota", "foco"], 0, {}),
    ("La nube tapa la luna.", ("noche", ["nube", "luna"]), "¿Qué tapa la nube?", ["luna", "sol", "casa"], 0,
     {"order": False}),
    ("Mi casa es bonita.", ("jardin", ["casa"]), "¿Qué es bonita?", ["casa", "cama", "mesa"], 0, {}),
    ("El mono come banana.", ("bosque", ["mono", "banana"]), "¿Qué come el mono?",
     ["banana", "sopa", "pizza"], 0, {}),
    ("Lola pasea al pato.", ("parque", ["ana", "pato"]), "¿A quién pasea Lola?", ["pato", "mono", "oso"], 0, {}),
    ("Mi papá me mima.", ("casa", ["papa", "memo"]), "¿Quién me mima?", ["papa", "mama", "bebe"], 0, {}),
    ("Ana se toca la boca.", ("casa", ["ana", "boca"]), "¿Qué se toca Ana?", ["boca", "pelo", "nariz"], 0, {}),
    ("Memo se toca el pelo.", ("casa", ["memo", "pelo"]), "¿Qué se toca Memo?", ["pelo", "boca", "pie"], 0, {}),
    ("El bebé se mete en la cuna.", ("dormitorio", ["bebe", "cuna"]), "¿Dónde se mete el bebé?",
     ["cuna", "mesa", "casa"], 0, {}),
    ("Papá saca el mapa.", ("parque", ["papa", "mapa"]), "¿Qué saca papá?", ["mapa", "pelota", "foco"], 0, {}),
    ("Tito come en la mesa.", ("cocina", ["memo", "mesa"]), "¿Dónde come Tito?", ["mesa", "cama", "cuna"], 0, {}),
    ("El pato es de Pepe.", ("jardin", ["pato", "memo"]), "¿Qué es de Pepe?", ["pato", "oso", "mono"], 0, {}),
    ("El mono se sube a la mesa.", ("casa", ["mono", "mesa"]), "¿A dónde se sube el mono?",
     ["mesa", "cama", "cuna"], 0, {}),
    ("Lola toma una foto.", ("parque", ["ana", "foto"]), "¿Qué toma Lola?", ["foto", "luna", "casa"], 0, {}),
    ("Amo a mi oso.", ("dormitorio", ["oso"]), "¿A quién amo?", ["oso", "pato", "mono"], 0, {}),
    ("La cama es de mamá.", ("dormitorio", ["cama", "mama"]), "¿Qué es de mamá?", ["cama", "mesa", "cuna"], 0, {}),
    ("Mamá besa al bebé.", ("casa", ["mama", "bebe"]), "¿A quién besa mamá?", ["bebe", "oso", "pato"], 0, {}),
]

L2 = [
    ("El gato toma leche.", ("cocina", ["gato", "leche"]), "¿Qué toma el gato?", ["leche", "sopa", "helado"], 0, {}),
    ("Ana lleva su mochila.", ("escuela", ["ana", "mochila"]), "¿Qué lleva Ana?",
     ["mochila", "pelota", "paraguas"], 0, {}),
    ("El perro corre.", ("parque", ["perro"]), "¿Quién corre?", ["perro", "gato", "pato"], 0, {}),
    ("Hoy hace sol.", ("cielo", ["sol"]), "¿Qué tiempo hace hoy?", ["sol", "lluvia", "nieve"], 0, {}),
    ("Me lavo las manos.", ("casa", ["manos"]), "¿Qué me lavo?", ["manos", "pies", "pelo"], 0, {}),
    ("Mi abuela hace galletas.", ("cocina", ["abuela", "galleta"]), "¿Qué hace la abuela?",
     [("galleta", "galletas"), "pizza", "sopa"], 0, {}),
    ("Vamos a la escuela.", ("escuela", ["mochila"]), "¿A dónde vamos?", ["escuela_lugar", "playa", "parque"], 0, {}),
    ("Luis juega con la pelota.", ("parque", ["memo", "pelota"]), "¿Con qué juega Luis?",
     ["pelota", "robot", "mapa"], 0, {}),
    ("El niño come helado.", ("parque", ["nino", "helado"]), "¿Qué come el niño?", ["helado", "pan", "sopa"], 0, {}),
    ("La gallina pone huevos.", ("jardin", ["gallina", "huevo"]), "¿Qué pone la gallina?",
     [("huevo", "huevos"), "uvas", "pan"], 0, {}),
    ("La vaca da leche.", ("jardin", ["vaca"]), "¿Qué da la vaca?", ["leche", "huevo", "pan"], 0, {}),
    ("Sofía está feliz.", ("parque", ["nina"]), "¿Cómo está Sofía?", ["feliz", "triste", "enojado"], 0, {}),
    ("Llueve mucho hoy.", ("lluvia", ["paraguas"]), "¿Qué pasa hoy?", ["lluvia", "sol", "nieve"], 0,
     {"hint": "Llueve"}),
    ("El bebé tiene sueño.", ("dormitorio", ["bebe", "cuna"]), "¿Qué tiene el bebé?",
     ["sueno", "hambre", "frio"], 0, {}),
    ("Mi casa tiene ventanas.", ("jardin", ["casa"]), "¿Qué tiene mi casa?",
     [("ventana", "ventanas"), "nube", "luna"], 0, {}),
    ("El barco navega.", ("playa", ["barco"]), "¿Qué navega?", ["barco", "carro", "autobus"], 0, {}),
    ("El avión vuela alto.", ("cielo", ["avion"]), "¿Qué vuela alto?", ["avion", "barco", "carro"], 0, {}),
    ("Tengo un perro.", ("casa", ["perro"]), "¿Qué tengo?", ["perro", "gato", "pato"], 0, {}),
    ("La jirafa come hojas.", ("bosque", ["jirafa"]), "¿Quién come hojas?", ["jirafa", "elefante", "mono"], 0, {}),
    ("Papá lee un cuento.", ("dormitorio", ["papa", "cuento"]), "¿Qué lee papá?", ["cuento", "pelota", "sopa"], 0,
     {}),
    ("Ana se lava los dientes.", ("casa", ["ana", "dientes"]), "¿Qué se lava Ana?",
     ["dientes", "pies", "pelo"], 0, {}),
    ("El sol calienta.", ("cielo", ["sol"]), "¿Qué calienta?", ["sol", "luna", "nube"], 0, {}),
    ("Me gusta la sandía.", ("cocina", ["sandia"]), "¿Qué me gusta?", ["sandia", "manzana", "uvas"], 0, {}),
    ("La mariposa es bonita.", ("jardin", ["mariposa"]), "¿Qué es bonita?", ["mariposa", "abeja", "oruga"], 0, {}),
    ("El conejo salta.", ("jardin", ["conejo"]), "¿Quién salta?", ["conejo", "tortuga", "oso"], 0, {}),
    ("La tortuga camina lento.", ("playa", ["tortuga"]), "¿Quién camina lento?",
     ["tortuga", "conejo", "perro"], 0, {}),
    ("Juan duerme en su cama.", ("dormitorio", ["nino", "cama"]), "¿Dónde duerme Juan?",
     ["cama", "mesa", "silla"], 0, {}),
]

L3 = [
    ("El gato café duerme en la cama.", ("dormitorio", ["gato", "cama"]), "¿De qué color es el gato?",
     ["cafe", "rosa", "azul"], 0, {"order": False}),
    ("La niña tiene un vestido rosa.", ("parque", ["nina"]), "¿De qué color es el vestido?",
     ["rosa", "azul", "verde"], 0, {}),
    ("El perro pequeño juega en el parque.", ("parque", ["perro", "pelota"]), "¿Dónde juega el perro?",
     ["parque", "playa", "escuela_lugar"], 0, {"order": False}),
    ("Mi abuelo tiene un gorro de color azul.", ("casa", ["abuelo"]), "¿De qué color es el gorro?",
     ["azul", "rojo", "amarillo"], 0, {}),
    ("La mariposa amarilla vuela en el jardín.", ("jardin", ["mariposa"]), "¿De qué color es la mariposa?",
     [("amarillo", "amarilla"), ("morado", "morada"), "verde"], 0, {"order": False}),
    ("El elefante tiene una nariz muy larga.", ("bosque", ["elefante"]), "¿Quién tiene la nariz larga?",
     ["elefante", "jirafa", "mono"], 0, {}),
    ("La jirafa tiene el cuello muy largo.", ("bosque", ["jirafa"]), "¿Quién tiene el cuello largo?",
     ["jirafa", "elefante", "oso"], 0, {}),
    ("Hay una pelota roja debajo de la mesa.", ("casa", ["pelota", "mesa"]), "¿Debajo de qué está la pelota?",
     ["mesa", "cama", "silla"], 0, {}),
    ("El sol calienta la arena del mar.", ("playa", ["sol"]), "¿Qué calienta el sol?",
     [("mar", "arena"), "escuela_lugar", "bosque"], 0, {}),
    ("Ana come una manzana roja y dulce.", ("cocina", ["ana", "manzana"]), "¿Qué come Ana?",
     ["manzana", "platano", "uvas"], 0, {}),
    ("El barco azul navega en el mar.", ("playa", ["barco"]), "¿De qué color es el barco?",
     ["azul", "rojo", "verde"], 0, {"order": False}),
    ("Mi mamá cocina una sopa caliente.", ("cocina", ["mama", "sopa"]), "¿Qué cocina mamá?",
     ["sopa", "pizza", "helado"], 0, {}),
    ("La luna sale cuando es de noche.", ("noche", ["luna"]), "¿Cuándo sale la luna?",
     ["noche", "dia", "con_lluvia"], 0, {}),
    ("El conejo come una zanahoria naranja.", ("jardin", ["conejo", "zanahoria"]), "¿Qué come el conejo?",
     ["zanahoria", "manzana", "pan"], 0, {}),
    ("Los niños juegan con la pelota en el patio.", ("escuela", ["nino", "nina", "pelota"]),
     "¿Con qué juegan los niños?", ["pelota", "robot", "mochila"], 0, {}),
    ("El gallo canta cuando sale el sol.", ("jardin", ["gallo", "sol"]), "¿Quién canta?",
     ["gallo", "gallina", "pato"], 0, {}),
    ("La abeja vuela cerca de la casa.", ("jardin", ["abeja", "casa"]), "¿Quién vuela cerca de la casa?",
     ["abeja", "oruga", "tortuga"], 0, {}),
    ("Mi perro tiene las orejas muy largas.", ("casa", ["perro"]), "¿Qué tiene largas el perro?",
     ["orejas", "pies", "boca"], 0, {}),
    ("La oveja tiene la lana muy suave.", ("jardin", ["oveja"]), "¿Quién tiene la lana suave?",
     ["oveja", "vaca", "cerdito"], 0, {}),
    ("El niño se pone la camisa azul.", ("dormitorio", ["nino", "camisa"]), "¿Qué se pone el niño?",
     ["camisa", "zapatos", "lentes"], 0, {}),
    ("Hay muchas nubes en el cielo hoy.", ("cielo", ["nube"]), "¿Qué hay en el cielo?",
     [("nube", "nubes"), "pelota", "mesa"], 0, {"order": False}),
    ("El autobús amarillo lleva a los niños.", ("escuela", ["autobus"]), "¿Qué lleva a los niños?",
     ["autobus", "barco", "avion"], 0, {"order": False}),
    ("La gata duerme junto a la ventana.", ("casa", ["gato", "ventana"]), "¿Dónde duerme la gata?",
     ["ventana", "puerta", "mesa"], 0, {}),
    ("Papá lava el carro con agua y jabón.", ("casa", ["papa", "carro"]), "¿Qué lava papá?",
     ["carro", "barco", "avion"], 0, {}),
    ("Un pájaro canta en la rama del árbol.", ("bosque", ["pajaro", "arbol"]), "¿Quién canta en la rama?",
     ["pajaro", "gato", "perro"], 0, {}),
    ("El delfín salta muy alto en el mar.", ("playa", ["delfin"]), "¿Quién salta en el mar?",
     ["delfin", "pulpo", "cangrejo"], 0, {}),
]

L4 = [
    ("El conejo blanco come una zanahoria.", ("jardin", ["conejo", "zanahoria"]), "¿De qué color es el conejo?",
     ["blanco", "negro", "rojo"], 0, {"order": False}),
    ("La mariposa vuela sobre las flores.", ("jardin", ["mariposa", "flor"]), "¿Sobre qué vuela la mariposa?",
     [("flor", "flores"), "casa", "mesa"], 0, {}),
    ("El elefante tiene una trompa larga.", ("bosque", ["elefante"]), "¿Quién tiene una trompa larga?",
     ["elefante", "jirafa", "cebra"], 0, {}),
    ("El tren pasa por el puente.", ("parque", ["tren"]), "¿Qué pasa por el puente?",
     ["tren", "barco", "avion"], 0, {}),
    ("Mi primo come una fresa.", ("cocina", ["nino", "fresa"]), "¿Qué come mi primo?",
     ["fresa", "uvas", "pan"], 0, {}),
    ("Leo un libro en la clase.", ("escuela", ["libro"]), "¿Qué leo?", ["libro", "mapa", "pelota"], 0, {}),
    ("El dragón vuela sobre el castillo.", ("cielo", ["dragon"]), "¿Quién vuela sobre el castillo?",
     ["dragon", "hada", "unicornio"], 0, {}),
    ("Hace frío y está nevando.", ("noche", ["nieve"]), "¿Qué tiempo hace?", ["nieve", "sol", "lluvia"], 0,
     {"hint": "nevando"}),
    ("La cebra tiene rayas negras y blancas.", ("bosque", ["cebra"]), "¿Quién tiene rayas?",
     ["cebra", "jirafa", "elefante"], 0, {}),
    ("El cangrejo camina por la playa.", ("playa", ["cangrejo"]), "¿Quién camina por la playa?",
     ["cangrejo", "pulpo", "ballena"], 0, {}),
    ("Mi abuela planta flores en el jardín.", ("jardin", ["abuela", "flor"]), "¿Qué planta la abuela?",
     [("flor", "flores"), "libro", "pelota"], 0, {}),
    ("Pablo come un plátano.", ("cocina", ["memo", "platano"]), "¿Qué come Pablo?",
     ["platano", "manzana", "fresa"], 0, {}),
    ("La ballena nada en el mar profundo.", ("playa", ["ballena"]), "¿Quién nada en el mar profundo?",
     ["ballena", "gato", "perro"], 0, {}),
    ("Las estrellas brillan en la noche.", ("noche", ["estrella", "luna"]), "¿Qué brilla en la noche?",
     [("estrella", "estrellas"), "sol", "nube"], 0, {}),
    ("Mi hermana dibuja un árbol grande.", ("jardin", ["nina", "arbol"]), "¿Qué dibuja mi hermana?",
     ["arbol", "casa", "sol"], 0, {}),
    ("El niño trepa al árbol.", ("bosque", ["nino", "arbol"]), "¿A dónde trepa el niño?",
     ["arbol", "mesa", "carro"], 0, {}),
    ("Tengo una bicicleta nueva.", ("parque", ["bicicleta"]), "¿Qué tengo?", ["bicicleta", "carro", "tren"], 0, {}),
    ("El pulpo tiene ocho brazos.", ("playa", ["pulpo"]), "¿Quién tiene ocho brazos?",
     ["pulpo", "cangrejo", "ballena"], 0, {}),
    ("Mi madre prepara el desayuno.", ("cocina", ["mama", "taza"]), "¿Quién prepara el desayuno?",
     [("mama", "madre"), "papa", "abuelo"], 0, {}),
    ("El granjero ordeña la vaca.", ("jardin", ["abuelo", "vaca"]), "¿Qué ordeña el granjero?",
     ["vaca", "oveja", "gallina"], 0, {}),
    ("El cocinero prepara una pizza.", ("cocina", ["pizza"]), "¿Qué prepara el cocinero?",
     ["pizza", "sopa", "helado"], 0, {}),
    ("Clara toma leche con pan.", ("cocina", ["nina", "leche", "pan"]), "¿Qué toma Clara?",
     ["leche", "sopa", "helado"], 0, {}),
    ("Bruno juega con su tren.", ("casa", ["memo", "tren"]), "¿Con qué juega Bruno?",
     ["tren", "pelota", "robot"], 0, {}),
    ("El cielo está nublado y gris.", ("lluvia", ["nube"]), "¿Cómo está el cielo?",
     ["nublado", "soleado", "estrellado"], 0, {}),
    ("La flor es de color rosa.", ("jardin", ["flor"]), "¿De qué color es la flor?",
     ["rosa", "azul", "verde"], 0, {}),
    ("Mi hermano pinta un tren grande.", ("casa", ["nino", "tren"]), "¿Qué pinta mi hermano?",
     ["tren", "flor", "sol"], 0, {}),
]

BLOCKS = [(1, L1), (2, L2), (3, L3), (4, L4)]

# ------------------------------------------------------------------ reglas
TAUGHT = set("mpsltndfcb")  # consonantes enseñadas en la Fase 3 (C con a, o, u; QU con e, i)
CLUSTERS = ("pl", "bl", "cl", "gl", "fl", "pr", "br", "tr", "dr", "cr", "gr", "fr")


def words_of(text):
    return re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]+", text)


def decodable_syllable(syl):
    """Se lee con lo enseñado: CV de una familia enseñada, V o VC inversa
    con L, S o N. Sin diptongos ni otras letras."""
    s = syl.lower()
    if re.fullmatch(r"[aeiouáéíóú]", s):
        return True
    if re.fullmatch(r"[aeiouáéíóú][lsn]", s):
        return True
    if re.fullmatch(r"qu[eiéí]", s):
        return True
    m = re.fullmatch(r"([a-zñ])([aeiouáéíóú])", s)
    if not m:
        return False
    c, v = m.groups()
    if c == "c":
        return plain(v) in "aou"
    return c in TAUGHT


def decodable_word(w):
    if w.lower() == "y":
        return True  # la conjunción «y» suena como la vocal i
    return all(decodable_syllable(s) for s in split(w))


def has_cluster(w):
    return any(c in plain(w) for c in CLUSTERS) and any(
        plain(s).startswith(CLUSTERS) for s in split(w))


def level_of(text):
    ws = words_of(text)
    if all(decodable_word(w) for w in ws):
        return 1
    if any(has_cluster(w) for w in ws):
        return 4
    if len(ws) >= 6:
        return 3
    return 2


def families_of(text):
    """Familias de la Fase 3 que aparecen, de la más usada a la menos."""
    count = {}
    for w in words_of(text):
        for s in split(w):
            p = plain(s)
            fam = "c" if p.startswith("qu") else p[0]
            if fam in TAUGHT:
                count[fam] = count.get(fam, 0) + 1
    return [f for f, _ in sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))]


def stem(w):
    p = plain(w)
    p = re.sub(r"(es|s)$", "", p) if len(p) > 4 else p
    return p[:-1] if len(p) > 3 and p[-1] in "aeo" else p


STOP = {"de", "la", "el", "los", "las", "un", "una", "con", "en"}


def find_hint(words, label, explicit):
    target = explicit or label
    for t in reversed([t for t in target.split() if t not in STOP]):
        for i, w in enumerate(words):
            if stem(w) == stem(t):
                return i
    return None


def option(spec):
    key, label = (spec, None) if isinstance(spec, str) else spec
    assert key in PIC, f"sin imagen: {key}"
    text, pic = PIC[key]
    return {"key": key, "text": label or text, "picture": pic}


def drawing_exists(name):
    return any((ROOT / "assets/drawings").rglob(f"{name}.svg"))


def check_picture(pic):
    if "drawing" in pic:
        assert drawing_exists(pic["drawing"]), pic


SCENES = {"jardin", "parque", "bosque", "playa", "noche", "lluvia", "cielo", "casa", "cocina", "dormitorio",
          "escuela"}


def layout(items):
    n = len(items)
    xs = {1: [0.5], 2: [0.32, 0.68], 3: [0.22, 0.5, 0.78]}[n]
    size = {1: 0.5, 2: 0.4, 3: 0.3}[n]
    out = []
    for key, x in zip(items, xs):
        assert key in PIC, f"escena sin imagen: {key}"
        pic = PIC[key][1]
        assert "scene" not in pic, key
        check_picture(pic)
        out.append({"p": pic, "x": x, "y": 0.62, "s": size})
    return out


def audio_for(sid, words):
    clip = f"{AUDIO}/{sid}.mp3"
    timings = None
    if (ROOT / clip).is_file():
        tfile = ROOT / f"{AUDIO}/{sid}.json"
        if tfile.is_file():
            t = json.loads(tfile.read_text(encoding="utf-8"))
            ok = (isinstance(t, list) and len(t) == len(words) and all(isinstance(x, int) for x in t)
                  and t == sorted(t) and len(set(t)) == len(t))
            assert ok, f"tiempos no válidos en {tfile}"
            timings = t
    else:
        clip = None
    return {"clip": clip, "word_ms": timings}


def word_clip(w):
    path = f"{WORD_AUDIO}/{plain(w)}.mp3"
    return path if (ROOT / path).is_file() else None


def write_pending(sentences):
    """Lista de ilustraciones 3D y grabaciones que faltan (para quien las haga)."""
    pending = [x for x in sentences if not x["image_ready"]]
    lines = [
        "# Ilustraciones de «Leo mis primeras oraciones»",
        "",
        "Generado por `tools/reading/sentences.py`. Mientras falte la ilustración 3D de una oración,",
        "la app muestra una **escena provisional** hecha con dibujos que ya tiene (y lo indica con",
        "«Ilustración provisional»).",
        "",
        "Formato: WEBP cuadrado (1024×1024), estilo 3D suave como el resto de la app, SIN texto",
        "dentro de la imagen. Debe mostrar exactamente lo que dice la oración y nada que confunda",
        "con las otras respuestas de su pregunta. Después: `python3 tools/reading/sentences.py`.",
        "",
        f"## Pendientes ({len(pending)} de {len(sentences)})",
        "",
        "| Archivo | Oración |",
        "|---|---|",
    ]
    lines += [f"| `{x['id']}.webp` | {x['text']} |" for x in pending]
    (ROOT / IMAGES / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    audio = [x for x in sentences if not x["audio"]["clip"]]
    lines = [
        "# Grabaciones de oraciones",
        "",
        "Generado por `tools/reading/sentences.py`. Si existe `<id>.mp3`, la app lo usa en lugar",
        "de la voz del dispositivo (mismas reglas de grabación que ../README.md, velocidad normal).",
        "",
        "Para que las palabras se resalten con la grabación, añade `<id>.json` con los",
        "milisegundos en que EMPIEZA cada palabra, medidos sobre ese audio (por ejemplo, en",
        "Audacity con etiquetas). Ejemplo para «Mi mamá me ama.»: `[0, 280, 820, 1050]`.",
        "El generador comprueba que haya un tiempo por palabra y que vayan en orden.",
        "Sin ese archivo, la grabación se oye igual pero sin resaltado (nunca se inventan tiempos).",
        "",
        f"## Pendientes ({len(audio)} de {len(sentences)})",
        "",
        "| Archivo | Qué se dice |",
        "|---|---|",
    ]
    lines += [f"| `{x['id']}.mp3` | {x['text']} |" for x in audio]
    (ROOT / AUDIO / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    sentences = []
    texts = set()
    for level, block in BLOCKS:
        for n, (text, (bg, items), question, opts, answer, extra) in enumerate(block, start=1):
            sid = f"oracion_{level}_{n:02d}"
            assert text not in texts, f"repetida: {text}"
            texts.add(text)
            assert text[0].isupper() and text.endswith("."), text
            got = level_of(text)
            assert got == level, f"«{text}» está en el nivel {level} pero las reglas dicen {got}"
            words = words_of(text)
            for w in words:
                assert "".join(split(w)) == w, w
            assert bg in SCENES, bg
            options = [option(o) for o in opts]
            assert len(options) == 3
            assert len({o["text"] for o in options}) == 3 and len({o["key"] for o in options}) == 3, opts
            for o in options:
                check_picture(o["picture"])
            correct = options[answer]
            hint = find_hint(words, correct["text"], extra.get("hint"))
            assert hint is not None, f"la respuesta de «{text}» no está en la oración"
            # Las opciones falsas no aparecen en la oración.
            for i, o in enumerate(options):
                if i != answer:
                    assert find_hint(words, o["text"], None) is None, (text, o["text"])
            order_ok = 3 <= len(words) <= 7 and "y" not in [w.lower() for w in words] and extra.get("order", True)
            image = f"{IMAGES}/{sid}.webp"
            explanation = f"{correct['text'][0].upper()}{correct['text'][1:]}. La oración dice: «{text}»"
            sentences.append({
                "id": sid,
                "text": text,
                "level": level,
                "families": families_of(text),
                "words": [{"text": w, "clip": word_clip(w)} for w in words],
                "scene": {"bg": bg, "items": layout(items)},
                "scene_keys": items,
                "image": image,
                "image_ready": (ROOT / image).is_file(),
                "audio": audio_for(sid, words),
                "question": {
                    "text": question,
                    "options": [{"text": o["text"], "picture": o["picture"]} for o in options],
                    "answer": answer,
                    "hint_word": hint,
                    "explanation": explanation,
                },
                "order": order_ok,
                "listen": not extra.get("skip_listen", False),
            })

    # «Escucha y selecciona»: dos escenas claramente distintas por oración.
    listenable = [s for s in sentences if s["listen"]]
    for i, s in enumerate(sentences):
        if not s["listen"]:
            s["listen_options"] = []
            continue
        mine = set(s["scene_keys"])
        mine_words = {stem(w["text"]) for w in s["words"]}
        picks = []
        for k in range(1, len(listenable)):
            other = listenable[(listenable.index(s) + k * 7) % len(listenable)]
            theirs = set(other["scene_keys"])
            if other is s or theirs & mine or other["scene"]["bg"] == s["scene"]["bg"]:
                continue
            if any(stem(PIC[t][0]) in mine_words for t in theirs):
                continue  # algo de la otra escena se nombra en esta oración
            if any(set(p["scene_keys"]) & theirs or p["scene"]["bg"] == other["scene"]["bg"] for p in picks):
                continue
            picks.append(other)
            if len(picks) == 2:
                break
        assert len(picks) == 2, s["text"]
        s["listen_options"] = [p["id"] for p in picks]
    for s in sentences:
        del s["scene_keys"]

    write_pending(sentences)
    data = {"format_version": 1, "levels": LEVELS, "sentences": sentences}
    out = ROOT / "assets/reading/sentences.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    by_level = {lv: sum(1 for s in sentences if s["level"] == lv) for lv in (1, 2, 3, 4)}
    assert len(sentences) >= 100, len(sentences)
    print(f"{out.relative_to(ROOT)}: {len(sentences)} oraciones {by_level}; "
          f"ordenables {sum(s['order'] for s in sentences)}; "
          f"escucha y selecciona {sum(bool(s['listen_options']) for s in sentences)}; "
          f"ilustraciones 3D listas {sum(s['image_ready'] for s in sentences)}; "
          f"grabaciones {sum(bool(s['audio']['clip']) for s in sentences)}")


if __name__ == "__main__":
    main()
