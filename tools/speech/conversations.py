"""Conversaciones guiadas de «Hablemos con Lolo».

Cada conversación son pocas preguntas de Lolo (3-4) con 3 respuestas en
tarjetas. Cada respuesta tiene la reacción de Lolo y, si hace falta, otra
pregunta distinta (rama). El motor de la app corta cada sesión a 5
intercambios como máximo.

Uso: python3 tools/speech/conversations.py
"""

from content_common import BOY, GIRL, I, D, K, E, S, APPLE, BANANA, STRAWBERRY, LOLO, save

CATEGORIES = [
    ("saludos", "Saludos y despedidas", "wave", "#FFB74D"),
    ("familia", "Mi familia", "family", "#F48FB1"),
    ("emociones", "Mis emociones", "emotions", "#FF8A80"),
    ("juguetes", "Mis juguetes", "toys", "#B39DDB"),
    ("alimentos", "Mis alimentos", "food", "#FFAB91"),
    ("animales", "Mis animales favoritos", "pets", "#A5D6A7"),
    ("dia", "Mis actividades diarias", "clock", "#90CAF9"),
    ("escuela", "Mi escuela", "school", "#FFE082"),
    ("amigos", "Mis amigos", "friends", "#80DEEA"),
    ("ayuda", "Pedir ayuda", "help", "#CE93D8"),
    ("necesidades", "Expresar necesidades", "water", "#81D4FA"),
    ("describir", "Describir objetos", "search", "#C5E1A5"),
]


def O(text, picture, reply, next_=None):
    o = {"text": text, "picture": picture, "reply": reply}
    if next_:
        o["next"] = next_
    return o


def conv(cid, cat, title, picture, steps, goodbye, branches=None):
    """steps: lista de (pregunta, [opciones]); se encadenan en orden.
    branches: nodos extra {id: (pregunta, [opciones])} a los que salta una opción."""
    nodes = {}
    ids = [f"p{i + 1}" for i in range(len(steps))]
    for i, (question, options) in enumerate(steps):
        nxt = ids[i + 1] if i + 1 < len(ids) else None
        nodes[ids[i]] = {"lolo": question, "options": [{**o, "next": o.get("next", nxt)} if nxt or "next" in o else o for o in options]}
    for bid, (question, options) in (branches or {}).items():
        nodes[bid] = {"lolo": question, "options": options}
    return {"id": cid, "category": cat, "title": title, "picture": picture, "start": "p1", "nodes": nodes, "goodbye": goodbye}


feliz, triste, cansado, emocionado = K("feliz", arms_up=True), K("triste"), K("cansado"), K("emocionado", True, GIRL)

C = []

# 1. Saludos y despedidas.
C += [
    conv("saludo_hola", "saludos", "¡Hola, Lolo!", S("jardin", (LOLO, .35, .6, .45), (K("feliz", True, GIRL, True), .7, .6, .45)), [
        ("¡Hola! ¿Cómo estás hoy?", [
            O("Estoy feliz.", feliz, "¡Qué alegría! Me gusta verte feliz."),
            O("Estoy cansado.", cansado, "Gracias por contármelo. Descansar un poquito ayuda mucho."),
            O("Estoy triste.", triste, "Gracias por decírmelo. Aquí estoy contigo.", "consuelo"),
            O("Estoy emocionado.", emocionado, "¡Qué bien! Se nota que hoy tienes mucha energía."),
        ]),
        ("¿Quieres jugar conmigo?", [
            O("¡Sí, quiero jugar!", I("play", "#FB8C00"), "¡Bien! Me encanta jugar contigo."),
            O("Ahora no, gracias.", I("thumb_up", "#5C6BC0"), "Está bien. Podemos jugar en otro momento."),
            O("Quiero hablar.", I("talk", "#26A69A"), "¡Claro! Hablar juntos también es divertido."),
        ]),
        ("¡Me tengo que ir! ¿Cómo nos despedimos?", [
            O("¡Adiós, Lolo!", I("wave", "#FFB300"), "¡Adiós! Fue un gusto hablar contigo."),
            O("¡Hasta mañana!", I("moon", "#5C6BC0"), "¡Hasta mañana! Que descanses."),
            O("¡Nos vemos pronto!", I("love", "#E91E63"), "¡Nos vemos pronto, amigo!"),
        ]),
    ], "¡Hasta la próxima! Me encantó saludarte.", {
        "consuelo": ("¿Quieres que hagamos algo juntos para sentirnos mejor?", [
            O("Un abrazo.", I("help", "#E91E63"), "¡Aquí tienes un abrazo grande de Lolo!", "p2"),
            O("Respirar despacio.", K("tranquilo"), "Respiremos juntos: tomamos aire… y lo soltamos despacio.", "p2"),
            O("Escuchar música.", I("dance", "#AB47BC"), "La música puede ayudarnos a sentirnos mejor.", "p2"),
        ]),
    }),
    conv("saludo_nombre", "saludos", "Nos presentamos", S("parque", (LOLO, .3, .58, .42), (K("feliz", False, BOY), .72, .6, .45)), [
        ("¡Hola! Yo soy Lolo, un lorito. ¿Cómo te saludas tú?", [
            O("¡Hola, Lolo!", I("wave", "#FFB300"), "¡Hola! ¡Qué bonito saludo!"),
            O("¡Buenos días!", I("sun", "#FFB300"), "¡Buenos días! Que tengas un día precioso."),
            O("¡Buenas tardes!", I("cloud", "#64B5F6"), "¡Buenas tardes! Qué gusto verte."),
        ]),
        ("¿Qué le dices a alguien que acabas de conocer?", [
            O("Mucho gusto.", I("love", "#E91E63"), "¡Muy bien! «Mucho gusto» es muy amable."),
            O("¿Quieres jugar?", I("play", "#FB8C00"), "¡Qué buena idea para hacer amigos!"),
            O("Me llamo… y tú, ¿cómo te llamas?", I("talk", "#26A69A"), "¡Perfecto! Así nos presentamos."),
        ]),
        ("¿Cómo te despides de tus amigos?", [
            O("¡Adiós!", I("wave", "#FFB300"), "¡Adiós! Un saludo con la mano también ayuda."),
            O("¡Hasta luego!", I("clock", "#00897B"), "¡Hasta luego! Muy bien dicho."),
            O("¡Chao!", I("love", "#E91E63"), "¡Chao, chao!"),
        ]),
    ], "¡Mucho gusto! Hasta pronto."),
    conv("saludo_noche", "saludos", "Buenas noches", S("noche", (LOLO, .3, .62, .4), (K("tranquilo", True, GIRL), .7, .62, .45)), [
        ("Ya es de noche. ¿Qué decimos antes de dormir?", [
            O("Buenas noches.", I("moon", "#5C6BC0"), "¡Buenas noches! Qué palabras tan bonitas."),
            O("Que descanses.", I("sleep", "#5C6BC0"), "Gracias. ¡Que descanses tú también!"),
            O("Hasta mañana.", I("sun", "#FFB300"), "¡Hasta mañana! Mañana será otro gran día."),
        ]),
        ("¿Qué haces antes de ir a la cama?", [
            O("Me lavo los dientes.", I("wash", "#29B6F6"), "¡Muy bien! Los dientes quedan limpios y brillantes."),
            O("Me pongo el pijama.", I("bed", "#5C6BC0"), "¡Qué cómodo es el pijama!"),
            O("Escucho un cuento.", I("read", "#8E24AA"), "¡A mí también me encantan los cuentos!"),
        ]),
        ("¿A quién le das las buenas noches?", [
            O("A mamá.", I("woman", "#AB47BC"), "¡Qué bonito! Mamá también te quiere."),
            O("A papá.", I("man", "#3949AB"), "¡Qué bonito! Papá estará contento."),
            O("A mi peluche.", D("animal_oso"), "¡Tu peluche te acompaña toda la noche!"),
        ]),
    ], "¡Buenas noches! Que sueñes cosas bonitas."),
]

# 2. Mi familia.
C += [
    conv("familia_quien", "familia", "Mi familia", S("casa", (I("family", "#F4511E"), .5, .6, .5)), [
        ("¿Con quién vives en tu casa?", [
            O("Con mamá y papá.", I("family", "#F4511E"), "¡Qué bonita familia!"),
            O("Con mi abuela.", I("elderly_woman", "#8E24AA"), "¡Las abuelas cuentan historias maravillosas!"),
            O("Con mis hermanos.", I("friends", "#00ACC1"), "¡Con hermanos siempre hay alguien para jugar!"),
        ]),
        ("¿Qué te gusta hacer con tu familia?", [
            O("Jugar juntos.", I("play", "#FB8C00"), "¡Jugar en familia es muy divertido!"),
            O("Comer juntos.", I("eat", "#F4511E"), "¡Comer juntos es un momento especial!"),
            O("Pasear.", I("walk", "#00897B"), "¡Pasear juntos es genial!"),
        ]),
        ("¿Cómo le dices a tu familia que la quieres?", [
            O("Con un abrazo.", I("help", "#E91E63"), "¡Los abrazos dicen mucho!"),
            O("Diciendo «te quiero».", I("love", "#E91E63"), "¡«Te quiero» son palabras mágicas!"),
            O("Con un dibujo.", I("paint", "#E91E63"), "¡Un dibujo hecho por ti es un regalo precioso!"),
        ]),
    ], "¡Saluda a tu familia de mi parte!"),
    conv("familia_ayudo", "familia", "Ayudo en casa", S("cocina", (K("feliz", True, GIRL, True), .5, .58, .5)), [
        ("¿Cómo ayudas en casa?", [
            O("Guardo mis juguetes.", I("toys", "#FB8C00"), "¡Muy bien! Así todo queda ordenado."),
            O("Pongo la mesa.", I("table", "#795548"), "¡Qué gran ayuda!"),
            O("Riego las plantas.", I("flower", "#43A047"), "¡Las plantas te lo agradecen!"),
        ]),
        ("¿Qué dices cuando alguien te ayuda?", [
            O("Gracias.", I("love", "#E91E63"), "¡Exacto! «Gracias» es muy importante."),
            O("Muchas gracias.", I("thumb_up", "#5C6BC0"), "¡Muy amable!"),
            O("Eres muy amable.", I("help", "#26A69A"), "¡Qué bonito decir eso!"),
        ]),
        ("¿Cómo te sientes cuando ayudas?", [
            O("Contento.", feliz, "¡Ayudar hace sentir bien!"),
            O("Orgulloso.", K("emocionado", False, BOY), "¡Puedes estar orgulloso!"),
            O("Cansado.", cansado, "A veces ayudar cansa. ¡Luego toca descansar!"),
        ]),
    ], "¡Eres una gran ayuda en casa!"),
    conv("familia_abuelos", "familia", "Mis abuelos", S("casa", (I("elderly", "#6D4C41"), .35, .6, .4), (I("elderly_woman", "#8E24AA"), .68, .6, .4)), [
        ("¿Qué haces con tus abuelos?", [
            O("Escucho sus cuentos.", I("read", "#8E24AA"), "¡Los abuelos saben muchas historias!"),
            O("Cocinamos juntos.", I("cake", "#AB47BC"), "¡Qué rico!"),
            O("Paseamos por el parque.", I("tree", "#2E7D32"), "¡Qué bonito paseo!"),
        ]),
        ("¿Qué comida te preparan?", [
            O("Sopa.", I("soup", "#FB8C00"), "¡Una sopa calentita!"),
            O("Pastel.", I("cake", "#AB47BC"), "¡Mmm, qué rico!"),
            O("Fruta.", APPLE, "¡La fruta está muy rica!"),
        ]),
        ("¿Qué les dices cuando te visitan?", [
            O("¡Qué bien que vinieron!", I("love", "#E91E63"), "¡Seguro que se ponen muy contentos!"),
            O("¡Los extrañaba!", K("feliz", True, GIRL), "¡Qué bonito decirlo!"),
            O("¿Quieren jugar?", I("play", "#FB8C00"), "¡A jugar todos juntos!"),
        ]),
    ], "¡Un saludo a tus abuelos!"),
]

# 3. Mis emociones.
C += [
    conv("emocion_hoy", "emociones", "¿Cómo me siento?", S("jardin", (LOLO, .3, .6, .4), (K("tranquilo", True, GIRL), .7, .6, .45)), [
        ("¿Cómo te sientes ahora?", [
            O("Feliz.", feliz, "¡Qué bien! ¿Quieres contarme qué te hace feliz?", "feliz"),
            O("Triste.", triste, "Está bien sentirse triste a veces. Gracias por contármelo.", "triste"),
            O("Enojado.", K("enojado"), "Todos nos enojamos a veces. Gracias por decírmelo.", "enojado"),
        ]),
    ], "Gracias por contarme cómo te sientes. ¡Todas las emociones son importantes!", {
        "feliz": ("¿Qué te hace feliz?", [
            O("Jugar con mis amigos.", I("friends", "#00ACC1"), "¡Jugar con amigos es genial!"),
            O("Estar con mi familia.", I("family", "#F4511E"), "¡La familia nos hace sentir bien!"),
            O("Pintar.", I("paint", "#E91E63"), "¡A mí también me encanta pintar!"),
        ]),
        "triste": ("¿Qué te puede ayudar a sentirte mejor?", [
            O("Un abrazo.", I("help", "#E91E63"), "¡Un abrazo grande de Lolo!"),
            O("Hablar con alguien.", I("talk", "#26A69A"), "Hablar con alguien que te quiere ayuda mucho."),
            O("Descansar.", I("rest", "#5C6BC0"), "Descansar un ratito también ayuda."),
        ]),
        "enojado": ("¿Qué podemos hacer cuando estamos enojados?", [
            O("Respirar despacio.", K("tranquilo"), "Muy bien: tomamos aire y lo soltamos despacio."),
            O("Contar hasta diez.", I("clock", "#00897B"), "¡Uno, dos, tres…! Contar ayuda a calmarse."),
            O("Decir lo que siento.", I("talk", "#26A69A"), "Decir lo que sentimos con palabras ayuda mucho."),
        ]),
    }),
    conv("emocion_miedo", "emociones", "Cuando tengo miedo", S("noche", (K("asustado", False, BOY), .5, .62, .5)), [
        ("A veces sentimos miedo. ¿Cuándo sientes miedo tú?", [
            O("Cuando está oscuro.", I("moon", "#5C6BC0"), "La oscuridad puede dar miedo. Una lucecita ayuda."),
            O("Cuando hay truenos.", I("cloud", "#78909C"), "Los truenos suenan fuerte, pero estás a salvo."),
            O("Cuando me pierdo.", I("search", "#8D6E63"), "Si te pierdes, busca a un adulto de confianza."),
        ]),
        ("¿Qué te ayuda cuando tienes miedo?", [
            O("Abrazar a mamá o papá.", I("family", "#F4511E"), "¡Un abrazo hace que el miedo se haga pequeñito!"),
            O("Mi peluche.", D("animal_oso"), "¡Los peluches son grandes compañeros!"),
            O("Una luz encendida.", I("lamp", "#FBC02D"), "¡Una lucecita ayuda mucho!"),
        ]),
        ("¿Qué le dices a un amigo que tiene miedo?", [
            O("No estás solo.", I("friends", "#00ACC1"), "¡Qué bonito! Así tu amigo se siente acompañado."),
            O("Yo te ayudo.", I("help", "#26A69A"), "¡Eres un gran amigo!"),
            O("Vamos con un adulto.", I("woman", "#AB47BC"), "¡Muy buena idea!"),
        ]),
    ], "Sentir miedo es normal. ¡Siempre puedes pedir ayuda!"),
    conv("emocion_sorpresa", "emociones", "¡Qué sorpresa!", S("casa", (K("sorprendido", True, GIRL), .4, .6, .45), (I("gift", "#E53935"), .75, .7, .25)), [
        ("¡Mira, un regalo! ¿Cómo te sientes?", [
            O("Sorprendido.", K("sorprendido"), "¡Qué sorpresa tan grande!"),
            O("Emocionado.", emocionado, "¡Uy, qué emoción!"),
            O("Curioso.", I("search", "#8D6E63"), "¿Qué habrá dentro?"),
        ]),
        ("¿Qué dices cuando te dan un regalo?", [
            O("¡Gracias!", I("love", "#E91E63"), "¡Muy bien dicho!"),
            O("¡Qué bonito!", I("star", "#FBC02D"), "¡Seguro que a quien te lo dio le encanta oírlo!"),
            O("¡Me encanta!", feliz, "¡Qué alegría!"),
        ]),
        ("¿A quién le darías tú un regalo?", [
            O("A mi mamá.", I("woman", "#AB47BC"), "¡Qué detalle tan bonito!"),
            O("A mi amigo.", I("friends", "#00ACC1"), "¡Tu amigo se pondrá muy contento!"),
            O("A Lolo.", LOLO, "¿A mí? ¡Gracias, qué ilusión!"),
        ]),
    ], "¡Las sorpresas son muy divertidas!"),
]

# 4. Mis juguetes.
C += [
    conv("juguete_favorito", "juguetes", "Mi juguete favorito", S("casa", (I("toys", "#FB8C00"), .5, .62, .45)), [
        ("¿Cuál es tu juguete favorito?", [
            O("La pelota.", I("ball", "#E53935"), "¡La pelota es muy divertida!"),
            O("Mi osito.", D("animal_oso"), "¡Los ositos son muy suaves!"),
            O("El tren.", D("vehiculo_tren"), "¡Chu, chu! ¡Qué bonito tren!"),
        ]),
        ("¿Dónde juegas con tus juguetes?", [
            O("En mi cuarto.", I("bed", "#5C6BC0"), "¡Tu cuarto es un lugar genial para jugar!"),
            O("En el parque.", I("tree", "#2E7D32"), "¡En el parque hay mucho espacio!"),
            O("En el jardín.", I("flower", "#EC407A"), "¡Al aire libre es muy divertido!"),
        ]),
        ("¿Compartes tus juguetes con tus amigos?", [
            O("Sí, me gusta compartir.", I("friends", "#00ACC1"), "¡Compartir es muy bonito!"),
            O("A veces.", I("thumb_up", "#5C6BC0"), "Está bien. ¡Poco a poco!"),
            O("Jugamos por turnos.", I("clock", "#00897B"), "¡Los turnos son una gran idea!"),
        ]),
    ], "¡Qué bien juegas! Hasta pronto."),
    conv("juguete_ordenar", "juguetes", "Recogemos los juguetes", S("dormitorio", (K("feliz", False, BOY), .6, .62, .45), (I("toys", "#FB8C00"), .25, .78, .22)), [
        ("¡Terminamos de jugar! ¿Qué hacemos con los juguetes?", [
            O("Los guardamos.", I("toys", "#FB8C00"), "¡Muy bien! Cada juguete a su lugar."),
            O("Los ordenamos juntos.", I("friends", "#00ACC1"), "¡Juntos es más rápido!"),
            O("Pido ayuda.", I("help", "#26A69A"), "¡Pedir ayuda está muy bien!"),
        ]),
        ("¿Dónde guardas la pelota?", [
            O("En la caja.", I("gift", "#8D6E63"), "¡Perfecto!"),
            O("En el armario.", I("door", "#6D4C41"), "¡Bien guardada!"),
            O("Debajo de la cama.", I("bed", "#5C6BC0"), "¡Ahí también está ordenada!"),
        ]),
        ("¿Cómo queda tu cuarto ahora?", [
            O("Muy ordenado.", I("star", "#FBC02D"), "¡Qué bien lo hiciste!"),
            O("Bonito.", feliz, "¡Da gusto verlo así!"),
            O("Limpio.", I("wash", "#29B6F6"), "¡Brilla de limpio!"),
        ]),
    ], "¡Qué ordenado! Eres un gran ayudante."),
    conv("juguete_inventar", "juguetes", "Inventamos un juego", S("parque", (K("emocionado", True, GIRL), .35, .6, .45), (K("feliz", False, BOY, True), .7, .6, .45)), [
        ("¡Vamos a inventar un juego! ¿Con qué jugamos?", [
            O("Con una pelota.", I("ball", "#E53935"), "¡Podemos lanzarla y atraparla!"),
            O("Con bloques.", I("blocks", "#43A047"), "¡Construiremos una torre altísima!"),
            O("Con pinturas.", I("paint", "#E91E63"), "¡Haremos un dibujo gigante!"),
        ]),
        ("¿Con quién jugamos?", [
            O("Con mis amigos.", I("friends", "#00ACC1"), "¡Cuantos más, mejor!"),
            O("Con mi hermano.", I("boy", "#1E88E5"), "¡Qué divertido!"),
            O("Contigo, Lolo.", LOLO, "¡Yupi! ¡Me encanta!"),
        ]),
        ("¿Cómo se llama nuestro juego?", [
            O("El gran juego.", I("star", "#FBC02D"), "¡Qué buen nombre!"),
            O("La aventura.", I("mountain", "#6D4C41"), "¡Una aventura increíble!"),
            O("El juego de Lolo.", LOLO, "¡Qué honor!"),
        ]),
    ], "¡Qué juego tan divertido inventamos!"),
]

# 5. Mis alimentos.
C += [
    conv("comida_favorita", "alimentos", "Mi comida favorita", S("cocina", (APPLE, .3, .64, .25), (BANANA, .52, .66, .25), (STRAWBERRY, .74, .64, .22)), [
        ("¿Cuál es tu fruta favorita?", [
            O("La manzana.", APPLE, "¡Las manzanas son crujientes!"),
            O("El plátano.", BANANA, "¡El plátano es dulce y suave!"),
            O("La fresa.", STRAWBERRY, "¡Las fresas son deliciosas!"),
        ]),
        ("¿Qué te gusta desayunar?", [
            O("Pan.", I("bread", "#C77C2E"), "¡Un pan calentito!"),
            O("Leche.", I("glass", "#90A4AE"), "¡La leche es muy nutritiva!"),
            O("Fruta.", APPLE, "¡Un desayuno muy sano!"),
        ]),
        ("¿Qué dices cuando la comida está rica?", [
            O("¡Qué rico!", feliz, "¡Muy bien dicho!"),
            O("¡Me gusta mucho!", I("thumb_up", "#5C6BC0"), "¡Qué bueno que te guste!"),
            O("Gracias por la comida.", I("love", "#E91E63"), "¡Qué amable!"),
        ]),
    ], "¡Que disfrutes tu comida!"),
    conv("comida_hambre", "alimentos", "Tengo hambre", S("cocina", (K("feliz", True, GIRL), .5, .6, .5)), [
        ("¿Cómo pides comida cuando tienes hambre?", [
            O("Tengo hambre, por favor.", I("eat", "#F4511E"), "¡Perfecto! Con «por favor» suena muy bien."),
            O("¿Me das algo de comer?", I("talk", "#26A69A"), "¡Muy bien pedido!"),
            O("Quiero comer.", I("eat", "#F4511E"), "¡Claro! Así lo entienden todos."),
        ]),
        ("¿Qué hacemos antes de comer?", [
            O("Lavarnos las manos.", I("wash", "#29B6F6"), "¡Muy importante! Manos limpias."),
            O("Sentarnos a la mesa.", I("chair", "#8D6E63"), "¡Muy bien!"),
            O("Ayudar a poner la mesa.", I("table", "#795548"), "¡Qué gran ayuda!"),
        ]),
        ("Si no te gusta una comida, ¿qué puedes decir?", [
            O("No me gusta, gracias.", I("thumb_up", "#5C6BC0"), "¡Muy amable! Así se dice con respeto."),
            O("¿Puedo probar un poquito?", I("eat", "#F4511E"), "¡Qué valiente! Probar es buena idea."),
            O("Prefiero otra cosa.", I("talk", "#26A69A"), "¡Bien dicho!"),
        ]),
    ], "¡Buen provecho!"),
    conv("comida_cocinar", "alimentos", "Cocinamos juntos", S("cocina", (I("cake", "#AB47BC"), .5, .62, .4)), [
        ("¡Vamos a cocinar! ¿Qué preparamos?", [
            O("Un pastel.", I("cake", "#AB47BC"), "¡Mmm, un pastel de cumpleaños!"),
            O("Una pizza.", I("pizza", "#F4511E"), "¡Una pizza con muchos colores!"),
            O("Una ensalada.", I("salad", "#43A047"), "¡Una ensalada fresquita!"),
        ]),
        ("¿Quién nos ayuda en la cocina?", [
            O("Mamá.", I("woman", "#AB47BC"), "¡Gracias, mamá!"),
            O("Papá.", I("man", "#3949AB"), "¡Gracias, papá!"),
            O("La abuela.", I("elderly_woman", "#8E24AA"), "¡La abuela cocina delicioso!"),
        ]),
        ("¿Cómo quedó la comida?", [
            O("¡Muy rica!", feliz, "¡Somos grandes cocineros!"),
            O("¡Deliciosa!", I("star", "#FBC02D"), "¡Qué bien nos quedó!"),
            O("¡Para chuparse los dedos!", K("emocionado", True, GIRL), "¡Ja, ja, ja! ¡Qué rica!"),
        ]),
    ], "¡Qué bien cocinamos juntos!"),
]

# 6. Mis animales favoritos.
C += [
    conv("animal_favorito", "animales", "Mi animal favorito", S("jardin", (D("animal_perro"), .32, .64, .38), (D("animal_gato"), .7, .64, .36)), [
        ("¿Cuál es tu animal favorito?", [
            O("El perro.", D("animal_perro"), "¡Los perros son muy leales!"),
            O("El gato.", D("animal_gato"), "¡Los gatos son muy suaves!"),
            O("El elefante.", D("animal_elefante"), "¡Los elefantes son enormes!"),
        ]),
        ("¿Qué sonido hace el perro?", [
            O("¡Guau, guau!", D("animal_perro"), "¡Muy bien! El perro dice «guau»."),
            O("¡Miau!", D("animal_gato"), "Ese es el gato. El perro dice «guau, guau»."),
            O("¡Muuu!", D("granja_vaca"), "Esa es la vaca. El perro dice «guau, guau»."),
        ]),
        ("¿Tienes una mascota?", [
            O("Sí, tengo una.", I("pets", "#FB8C00"), "¡Qué bien! Las mascotas nos acompañan."),
            O("No, pero me gustaría.", I("love", "#E91E63"), "¡Quizás algún día!"),
            O("Mi mascota eres tú, Lolo.", LOLO, "¡Ja, ja! ¡Qué divertido!"),
        ]),
    ], "¡Me encantan los animales!"),
    conv("animal_granja", "animales", "En la granja", S("parque", (D("granja_vaca"), .3, .62, .38), (D("granja_gallina"), .7, .66, .3)), [
        ("¡Estamos en la granja! ¿Qué animal ves?", [
            O("Una vaca.", D("granja_vaca"), "¡Muuu! La vaca nos da leche."),
            O("Una gallina.", D("granja_gallina"), "¡Cocoroco! La gallina pone huevos."),
            O("Un cerdito.", D("granja_cerdito"), "¡Oinc, oinc! ¡Qué gracioso!"),
        ]),
        ("¿Qué le damos de comer a los animales?", [
            O("Hierba.", I("tree", "#43A047"), "¡A la vaca le encanta la hierba!"),
            O("Maíz.", I("food", "#FBC02D"), "¡A las gallinas les gusta el maíz!"),
            O("Zanahorias.", I("salad", "#FB8C00"), "¡A los conejos les encantan!"),
        ]),
        ("¿Cómo tratamos a los animales?", [
            O("Con cariño.", I("love", "#E91E63"), "¡Exacto! Con mucho cariño."),
            O("Con cuidado.", I("help", "#26A69A"), "¡Muy bien!"),
            O("Les hablamos suave.", I("talk", "#26A69A"), "¡Así no se asustan!"),
        ]),
    ], "¡Qué bonita es la granja!"),
    conv("animal_mar", "animales", "Los animales del mar", S("playa", (D("mar_delfin"), .3, .55, .35), (D("mar_pulpo"), .72, .62, .32)), [
        ("¿Qué animal vive en el mar?", [
            O("El delfín.", D("mar_delfin"), "¡Los delfines saltan muy alto!"),
            O("El pulpo.", D("mar_pulpo"), "¡El pulpo tiene ocho brazos!"),
            O("La ballena.", D("mar_ballena"), "¡La ballena es enorme!"),
        ]),
        ("¿Qué hace el cangrejo?", [
            O("Camina de lado.", D("mar_cangrejo"), "¡Sí! El cangrejo camina de lado."),
            O("Vuela.", I("cloud", "#64B5F6"), "¡No! El cangrejo camina de lado por la arena."),
            O("Ladra.", D("animal_perro"), "¡Ja, ja! Ese es el perro. El cangrejo camina de lado."),
        ]),
        ("¿Te gustaría nadar con los peces?", [
            O("¡Sí, me encantaría!", I("swim", "#0288D1"), "¡Sería una aventura increíble!"),
            O("Me da un poco de miedo.", K("asustado"), "Está bien. Podemos mirarlos desde la orilla."),
            O("Prefiero mirarlos.", I("look", "#3949AB"), "¡Mirarlos también es muy bonito!"),
        ]),
    ], "¡Glu, glu! ¡Hasta pronto!"),
]

# 7. Mis actividades diarias.
C += [
    conv("dia_manana", "dia", "Por la mañana", S("dormitorio", (K("cansado", True, GIRL), .5, .6, .5)), [
        ("¡Buenos días! ¿Qué haces cuando te despiertas?", [
            O("Me estiro.", K("feliz", False, BOY, True), "¡Qué bien! Estirarse despierta el cuerpo."),
            O("Me lavo la cara.", I("wash", "#29B6F6"), "¡Agua fresquita!"),
            O("Saludo a mi familia.", I("family", "#F4511E"), "¡Un saludo para empezar el día!"),
        ]),
        ("¿Qué ropa te pones?", [
            O("Una camiseta.", I("shirt", "#64B5F6"), "¡Muy bien!"),
            O("Un vestido.", I("dress", "#F48FB1"), "¡Qué bonito!"),
            O("Mis zapatos.", I("shoes", "#8D6E63"), "¡A caminar!"),
        ]),
        ("¿Qué desayunas hoy?", [
            O("Leche y pan.", I("bread", "#C77C2E"), "¡Un buen desayuno!"),
            O("Fruta.", BANANA, "¡Qué sano!"),
            O("Huevo.", I("egg", "#F9A825"), "¡Muy rico!"),
        ]),
    ], "¡Que tengas un día muy bonito!"),
    conv("dia_bano", "dia", "La hora del baño", S("casa", (I("bath", "#29B6F6"), .5, .62, .45)), [
        ("¡Es la hora del baño! ¿Qué usamos?", [
            O("Jabón.", I("wash", "#29B6F6"), "¡Con jabón quedamos limpios!"),
            O("Agua tibia.", I("water", "#039BE5"), "¡Ni muy fría ni muy caliente!"),
            O("Una toalla.", I("towel", "#F48FB1"), "¡Para secarnos!"),
        ]),
        ("¿Qué juguete llevas al baño?", [
            O("Un patito.", D("granja_patito"), "¡Cua, cua! ¡Qué divertido!"),
            O("Un barco.", D("vehiculo_barco"), "¡El barco navega en el agua!"),
            O("Ninguno.", I("thumb_up", "#5C6BC0"), "¡Está bien!"),
        ]),
        ("¿Cómo te sientes después del baño?", [
            O("Limpio.", I("star", "#FBC02D"), "¡Brillas de limpio!"),
            O("Fresco.", K("tranquilo"), "¡Qué agradable!"),
            O("Con sueño.", cansado, "¡Es hora de descansar!"),
        ]),
    ], "¡Qué limpio quedaste!"),
    conv("dia_tarde", "dia", "Por la tarde", S("parque", (K("feliz", False, BOY, True), .5, .6, .5)), [
        ("¿Qué te gusta hacer por la tarde?", [
            O("Ir al parque.", I("tree", "#2E7D32"), "¡En el parque hay columpios!"),
            O("Dibujar.", I("paint", "#E91E63"), "¡Pintar es muy divertido!"),
            O("Leer un cuento.", I("read", "#8E24AA"), "¡Los cuentos nos llevan a otros mundos!"),
        ]),
        ("¿Con quién pasas la tarde?", [
            O("Con mi familia.", I("family", "#F4511E"), "¡Qué bien!"),
            O("Con mis amigos.", I("friends", "#00ACC1"), "¡Qué divertido!"),
            O("Con mi mascota.", D("animal_perro"), "¡Seguro que te sigue a todas partes!"),
        ]),
        ("¿Qué haces cuando se pone el sol?", [
            O("Vuelvo a casa.", I("home", "#F4511E"), "¡Muy bien!"),
            O("Ceno.", I("eat", "#F4511E"), "¡Buen provecho!"),
            O("Me preparo para dormir.", I("sleep", "#5C6BC0"), "¡A descansar!"),
        ]),
    ], "¡Qué tarde tan bonita!"),
]

# 8. Mi escuela.
C += [
    conv("escuela_clase", "escuela", "En mi clase", S("escuela", (K("feliz", True, GIRL), .3, .68, .38), (I("teacher", "#3949AB"), .72, .66, .32)), [
        ("¿Qué haces en la escuela?", [
            O("Aprendo cosas nuevas.", I("idea", "#FBC02D"), "¡Aprender es una aventura!"),
            O("Juego con mis amigos.", I("friends", "#00ACC1"), "¡En el recreo es muy divertido!"),
            O("Pinto y dibujo.", I("paint", "#E91E63"), "¡Qué artista!"),
        ]),
        ("¿Qué llevas en tu mochila?", [
            O("Mis lápices.", I("pencil", "#FB8C00"), "¡Para escribir y dibujar!"),
            O("Un cuaderno.", I("book", "#E53935"), "¡Para aprender muchas cosas!"),
            O("Mi merienda.", APPLE, "¡Para tener energía!"),
        ]),
        ("¿Qué dices si no entiendes algo?", [
            O("¿Me lo explicas otra vez?", I("talk", "#26A69A"), "¡Muy bien! Preguntar es muy inteligente."),
            O("Levanto la mano.", I("wave", "#FFB300"), "¡Así la maestra sabe que quieres hablar!"),
            O("Pido ayuda.", I("help", "#26A69A"), "¡Siempre se puede pedir ayuda!"),
        ]),
    ], "¡Qué bien lo pasas en la escuela!"),
    conv("escuela_recreo", "escuela", "En el recreo", S("parque", (K("emocionado", True, GIRL), .3, .6, .42), (K("feliz", False, BOY, True), .7, .6, .42)), [
        ("¡Es la hora del recreo! ¿A qué juegas?", [
            O("A la pelota.", I("ball", "#E53935"), "¡Gol!"),
            O("A correr.", I("run", "#43A047"), "¡Qué rápido corres!"),
            O("A saltar.", I("jump", "#00ACC1"), "¡Muy alto!"),
        ]),
        ("Un niño está solo. ¿Qué le dices?", [
            O("¿Quieres jugar conmigo?", I("friends", "#00ACC1"), "¡Qué bonito gesto!"),
            O("Hola, ¿cómo te llamas?", I("wave", "#FFB300"), "¡Así empiezan las amistades!"),
            O("Ven con nosotros.", I("help", "#26A69A"), "¡Muy amable!"),
        ]),
        ("¿Qué hacemos cuando suena el timbre?", [
            O("Volvemos a clase.", I("school", "#3949AB"), "¡Muy bien!"),
            O("Hacemos una fila.", I("friends", "#00ACC1"), "¡En orden!"),
            O("Guardamos la pelota.", I("ball", "#E53935"), "¡Muy ordenado!"),
        ]),
    ], "¡Qué recreo tan divertido!"),
    conv("escuela_maestra", "escuela", "Mi maestra", S("escuela", (I("teacher", "#3949AB"), .5, .66, .4)), [
        ("¿Cómo saludas a tu maestra por la mañana?", [
            O("¡Buenos días, maestra!", I("sun", "#FFB300"), "¡Qué saludo tan bonito!"),
            O("¡Hola, maestra!", I("wave", "#FFB300"), "¡Muy bien!"),
            O("Con una sonrisa.", feliz, "¡Una sonrisa alegra a todos!"),
        ]),
        ("¿Qué te enseña tu maestra?", [
            O("Las letras.", I("abc", "#E53935"), "¡A, B, C!"),
            O("Los números.", I("numbers", "#1E88E5"), "¡Uno, dos, tres!"),
            O("Canciones.", I("sing", "#EC407A"), "¡La la la!"),
        ]),
        ("¿Qué le dices al irte a casa?", [
            O("¡Hasta mañana!", I("wave", "#FFB300"), "¡Muy bien!"),
            O("¡Gracias, maestra!", I("love", "#E91E63"), "¡Qué agradecido!"),
            O("¡Adiós!", I("wave", "#FFB300"), "¡Adiós!"),
        ]),
    ], "¡Tu maestra estará muy contenta contigo!"),
]

# 9. Mis amigos.
C += [
    conv("amigo_mejor", "amigos", "Mi mejor amigo", S("parque", (K("feliz", False, BOY), .32, .6, .42), (K("feliz", True, GIRL), .7, .6, .42)), [
        ("¿Qué te gusta hacer con tus amigos?", [
            O("Jugar.", I("play", "#FB8C00"), "¡Jugar juntos es genial!"),
            O("Reír.", feliz, "¡Reír es lo mejor!"),
            O("Compartir.", I("friends", "#00ACC1"), "¡Compartir es muy bonito!"),
        ]),
        ("¿Cómo es un buen amigo?", [
            O("Amable.", I("love", "#E91E63"), "¡Muy bien!"),
            O("Me ayuda.", I("help", "#26A69A"), "¡Los amigos se ayudan!"),
            O("Me escucha.", I("look", "#3949AB"), "¡Escuchar es muy importante!"),
        ]),
        ("Si tu amigo se cae, ¿qué haces?", [
            O("Lo ayudo a levantarse.", I("help", "#26A69A"), "¡Eres un gran amigo!"),
            O("Le pregunto si está bien.", I("talk", "#26A69A"), "¡Qué atento!"),
            O("Llamo a un adulto.", I("woman", "#AB47BC"), "¡Muy buena idea!"),
        ]),
    ], "¡Qué suerte tienen tus amigos!"),
    conv("amigo_compartir", "amigos", "Compartimos", S("casa", (K("feliz", True, GIRL), .3, .6, .42), (I("ball", "#E53935"), .5, .82, .14), (K("feliz", False, BOY), .7, .6, .42)), [
        ("Tu amigo quiere tu juguete. ¿Qué le dices?", [
            O("Toma, juguemos juntos.", I("friends", "#00ACC1"), "¡Qué bonito compartir!"),
            O("Primero yo y luego tú.", I("clock", "#00897B"), "¡Los turnos son justos!"),
            O("Lo usamos un ratito cada uno.", I("thumb_up", "#5C6BC0"), "¡Gran idea!"),
        ]),
        ("¿Qué dice tu amigo cuando le prestas algo?", [
            O("Gracias.", I("love", "#E91E63"), "¡Muy bien!"),
            O("Eres muy bueno.", feliz, "¡Qué bonito!"),
            O("Luego te lo devuelvo.", I("thumb_up", "#5C6BC0"), "¡Muy responsable!"),
        ]),
        ("¿Cómo te sientes al compartir?", [
            O("Contento.", feliz, "¡Compartir nos hace sentir bien!"),
            O("Orgulloso.", K("emocionado", False, BOY), "¡Puedes estarlo!"),
            O("Un poco raro.", K("sorprendido"), "Está bien. ¡Poco a poco se aprende!"),
        ]),
    ], "¡Compartir es de grandes amigos!"),
    conv("amigo_perdon", "amigos", "Pedir perdón", S("parque", (K("triste", False, BOY), .32, .6, .42), (K("tranquilo", True, GIRL), .7, .6, .42)), [
        ("Sin querer empujaste a un amigo. ¿Qué le dices?", [
            O("Perdón, fue sin querer.", I("help", "#26A69A"), "¡Muy bien! Pedir perdón es de valientes."),
            O("¿Estás bien?", I("talk", "#26A69A"), "¡Qué atento!"),
            O("Lo siento mucho.", I("love", "#E91E63"), "¡Muy bonito!"),
        ]),
        ("¿Qué puede responder tu amigo?", [
            O("No pasa nada.", I("thumb_up", "#5C6BC0"), "¡Qué bien!"),
            O("Te perdono.", I("love", "#E91E63"), "¡Qué bonito perdonar!"),
            O("Sigamos jugando.", I("play", "#FB8C00"), "¡A jugar!"),
        ]),
        ("¿Cómo se sienten ahora?", [
            O("Felices.", feliz, "¡Amigos otra vez!"),
            O("Tranquilos.", K("tranquilo"), "¡Qué bien!"),
            O("Más amigos que antes.", I("friends", "#00ACC1"), "¡Así es la amistad!"),
        ]),
    ], "¡Pedir perdón y perdonar es muy importante!"),
]

# 10. Pedir ayuda.
C += [
    conv("ayuda_no_puedo", "ayuda", "No puedo solo", S("casa", (K("triste", True, GIRL), .5, .6, .5)), [
        ("¿Qué dices cuando algo es difícil?", [
            O("¿Me ayudas, por favor?", I("help", "#26A69A"), "¡Perfecto! Así se pide ayuda."),
            O("Necesito ayuda.", I("help", "#26A69A"), "¡Muy bien dicho!"),
            O("No puedo solo.", I("talk", "#26A69A"), "¡Está bien! Para eso estamos."),
        ]),
        ("¿A quién le pides ayuda?", [
            O("A mamá o papá.", I("family", "#F4511E"), "¡Siempre te ayudarán!"),
            O("A la maestra.", I("teacher", "#3949AB"), "¡Ella sabe mucho!"),
            O("A un adulto de confianza.", I("woman", "#AB47BC"), "¡Muy bien!"),
        ]),
        ("¿Qué dices después de que te ayudan?", [
            O("¡Gracias!", I("love", "#E91E63"), "¡Muy bien!"),
            O("¡Muchas gracias!", I("thumb_up", "#5C6BC0"), "¡Muy amable!"),
            O("¡Ahora sí puedo!", feliz, "¡Qué bien!"),
        ]),
    ], "¡Pedir ayuda es muy inteligente!"),
    conv("ayuda_perdido", "ayuda", "Si me pierdo", S("parque", (K("asustado", False, BOY), .5, .6, .5)), [
        ("Si te pierdes en el parque, ¿qué haces?", [
            O("Me quedo quieto.", I("thumb_up", "#5C6BC0"), "¡Muy bien! Así es más fácil encontrarte."),
            O("Busco a un policía.", I("help", "#1E88E5"), "¡Muy buena idea!"),
            O("Pido ayuda a un adulto.", I("woman", "#AB47BC"), "¡Muy bien!"),
        ]),
        ("¿Qué le dices al adulto?", [
            O("Me perdí.", I("search", "#8D6E63"), "¡Muy claro!"),
            O("Busco a mi mamá.", I("woman", "#AB47BC"), "¡Muy bien!"),
            O("¿Me ayuda, por favor?", I("help", "#26A69A"), "¡Perfecto!"),
        ]),
        ("¡Ya encontraste a tu familia! ¿Cómo te sientes?", [
            O("Tranquilo.", K("tranquilo"), "¡Qué alivio!"),
            O("Feliz.", feliz, "¡Qué alegría!"),
            O("Con ganas de un abrazo.", I("help", "#E91E63"), "¡Un abrazo grande!"),
        ]),
    ], "¡Qué bien sabes qué hacer!"),
    conv("ayuda_duele", "ayuda", "Me duele", S("casa", (K("triste", False, BOY), .5, .6, .5)), [
        ("Si te duele algo, ¿qué haces?", [
            O("Se lo digo a un adulto.", I("woman", "#AB47BC"), "¡Muy bien! Es lo más importante."),
            O("Señalo dónde me duele.", I("hurt", "#E53935"), "¡Así te pueden ayudar mejor!"),
            O("Digo: me duele aquí.", I("talk", "#26A69A"), "¡Perfecto!"),
        ]),
        ("¿Dónde te duele?", [
            O("La cabeza.", {"body": "cabeza"}, "Gracias por decirlo. Un adulto te cuidará."),
            O("La barriga.", I("hurt", "#E53935"), "Gracias por decirlo. Un adulto te cuidará."),
            O("La rodilla.", {"body": "piernas"}, "Gracias por decirlo. Una curita puede ayudar."),
        ]),
        ("¿Qué te ayuda a sentirte mejor?", [
            O("Descansar.", I("rest", "#5C6BC0"), "¡Descansar es muy bueno!"),
            O("Un abrazo.", I("help", "#E91E63"), "¡Un abrazo de Lolo!"),
            O("Beber agua.", I("water", "#039BE5"), "¡Muy bien!"),
        ]),
    ], "¡Que te mejores pronto!"),
]

# 11. Expresar necesidades.
C += [
    conv("necesito_sed", "necesidades", "Tengo sed", S("cocina", (K("cansado", True, GIRL), .4, .6, .45), (I("water", "#039BE5"), .78, .64, .22)), [
        ("¿Cómo pides agua?", [
            O("Quiero agua, por favor.", I("water", "#039BE5"), "¡Perfecto! Muy bien pedido."),
            O("Tengo sed.", I("glass", "#039BE5"), "¡Muy bien! Así te entienden."),
            O("¿Me das un vaso de agua?", I("glass", "#039BE5"), "¡Qué bien lo preguntas!"),
        ]),
        ("¿Qué más puedes pedir cuando lo necesitas?", [
            O("Ir al baño.", I("toilet", "#5C6BC0"), "¡Muy importante decirlo a tiempo!"),
            O("Descansar.", I("rest", "#5C6BC0"), "¡Todos necesitamos descansar!"),
            O("Comer algo.", I("eat", "#F4511E"), "¡Claro que sí!"),
        ]),
        ("¿Y qué dices al final?", [
            O("Gracias.", I("love", "#E91E63"), "¡Muy bien!"),
            O("Por favor y gracias.", I("thumb_up", "#5C6BC0"), "¡Palabras mágicas!"),
            O("Eres muy amable.", feliz, "¡Qué bonito!"),
        ]),
    ], "¡Qué bien sabes pedir lo que necesitas!"),
    conv("necesito_frio", "necesidades", "Tengo frío", S("lluvia", (K("triste", False, BOY), .5, .6, .5)), [
        ("¡Brrr! Hace frío. ¿Qué dices?", [
            O("Tengo frío.", I("snow", "#4FC3F7"), "¡Muy bien dicho!"),
            O("¿Me das mi abrigo?", I("jacket", "#E53935"), "¡Muy buena idea!"),
            O("Quiero una manta.", I("bed", "#5C6BC0"), "¡Una manta calentita!"),
        ]),
        ("¿Y si tienes calor?", [
            O("Tengo calor.", I("hot", "#F4511E"), "¡Muy bien!"),
            O("Quiero agua fresca.", I("water", "#039BE5"), "¡Muy bien!"),
            O("Me quito el abrigo.", I("jacket", "#E53935"), "¡Buena idea!"),
        ]),
        ("¿Cómo te sientes ahora?", [
            O("Calentito.", K("tranquilo"), "¡Qué agradable!"),
            O("Bien.", feliz, "¡Me alegro!"),
            O("Cómodo.", I("rest", "#5C6BC0"), "¡Qué bien!"),
        ]),
    ], "¡Decir cómo te sientes ayuda a que te cuiden!"),
    conv("necesito_descansar", "necesidades", "Necesito descansar", S("dormitorio", (K("cansado", True, GIRL), .5, .6, .5)), [
        ("Jugamos mucho. ¿Cómo está tu cuerpo?", [
            O("Cansado.", cansado, "Gracias por decírmelo."),
            O("Con mucha energía.", K("emocionado", False, BOY), "¡Qué energía!"),
            O("Con sueño.", I("sleep", "#5C6BC0"), "¡A descansar!"),
        ]),
        ("¿Qué puedes decir cuando estás cansado?", [
            O("Necesito descansar.", I("rest", "#5C6BC0"), "¡Muy bien dicho!"),
            O("Quiero dormir un ratito.", I("sleep", "#5C6BC0"), "¡Una siesta!"),
            O("Quiero jugar tranquilo.", I("read", "#8E24AA"), "¡Muy buena idea!"),
        ]),
        ("¿Qué hacemos para descansar?", [
            O("Nos acostamos.", I("bed", "#5C6BC0"), "¡Muy bien!"),
            O("Escuchamos música suave.", I("dance", "#AB47BC"), "¡Qué relajante!"),
            O("Leemos un cuento.", I("read", "#8E24AA"), "¡Qué bonito!"),
        ]),
    ], "¡Que descanses!"),
]

# 12. Describir objetos.
C += [
    conv("describir_pelota", "describir", "¿Cómo es la pelota?", S("jardin", (I("ball", "#E53935"), .5, .62, .4)), [
        ("Mira esta pelota. ¿De qué color es?", [
            O("Roja.", {"swatch": "#E53935"}, "¡Sí! Es roja."),
            O("Azul.", {"swatch": "#1E57C8"}, "Esa es azul. ¡Esta pelota es roja!"),
            O("Verde.", {"swatch": "#2E7D32"}, "Ese es verde. ¡Esta pelota es roja!"),
        ]),
        ("¿Qué forma tiene?", [
            O("Es redonda.", I("circle", "#E53935"), "¡Muy bien! Es redonda."),
            O("Es cuadrada.", I("square", "#1E57C8"), "¡Esa es cuadrada! La pelota es redonda."),
            O("Es una estrella.", I("star", "#FBC02D"), "¡Esa es una estrella! La pelota es redonda."),
        ]),
        ("¿Qué hacemos con una pelota?", [
            O("La lanzamos.", I("ball", "#E53935"), "¡Muy bien!"),
            O("La pateamos.", I("run", "#43A047"), "¡Gol!"),
            O("La hacemos rebotar.", I("jump", "#00ACC1"), "¡Bote, bote!"),
        ]),
    ], "¡Qué bien describes las cosas!"),
    conv("describir_grande", "describir", "Grande y pequeño", S("parque", (D("animal_elefante"), .35, .58, .5), (D("animal_mariposa"), .78, .45, .18)), [
        ("¿Qué animal es grande?", [
            O("El elefante.", D("animal_elefante"), "¡Sí! El elefante es muy grande."),
            O("La mariposa.", D("animal_mariposa"), "La mariposa es pequeñita. ¡El elefante es grande!"),
            O("El patito.", D("granja_patito"), "El patito es pequeño. ¡El elefante es grande!"),
        ]),
        ("¿Y cuál es pequeño?", [
            O("La mariposa.", D("animal_mariposa"), "¡Muy bien! La mariposa es pequeña."),
            O("La ballena.", D("mar_ballena"), "¡La ballena es enorme! La mariposa es pequeña."),
            O("La jirafa.", D("animal_jirafa"), "¡La jirafa es muy alta! La mariposa es pequeña."),
        ]),
        ("¿Cómo es la jirafa?", [
            O("Alta.", D("animal_jirafa"), "¡Sí! Tiene el cuello muy largo."),
            O("Baja.", D("granja_patito"), "¡No! La jirafa es muy alta."),
            O("Redonda.", I("circle", "#E53935"), "¡No! La jirafa es muy alta."),
        ]),
    ], "¡Sabes mucho de tamaños!"),
    conv("describir_osito", "describir", "Mi osito", S("dormitorio", (D("animal_oso"), .5, .6, .45)), [
        ("Toca tu osito. ¿Cómo es?", [
            O("Suave.", I("love", "#E91E63"), "¡Sí! Los ositos son muy suaves."),
            O("Esponjoso.", D("granja_oveja"), "¡Como una nube!"),
            O("Duro.", I("square", "#8D6E63"), "¡Mmm, los ositos suelen ser suaves!"),
        ]),
        ("¿De qué tamaño es?", [
            O("Pequeño.", I("zoom_out", "#8D6E63"), "¡Cabe en tus brazos!"),
            O("Grande.", I("zoom_in", "#8D6E63"), "¡Un osito gigante!"),
            O("Mediano.", D("animal_oso"), "¡Perfecto para abrazar!"),
        ]),
        ("¿Qué haces con tu osito?", [
            O("Lo abrazo.", I("help", "#E91E63"), "¡Qué bonito!"),
            O("Duermo con él.", I("sleep", "#5C6BC0"), "¡Te acompaña toda la noche!"),
            O("Juego con él.", I("play", "#FB8C00"), "¡Qué divertido!"),
        ]),
    ], "¡Tu osito es especial!"),
]


if __name__ == "__main__":
    data = {
        "format_version": 1,
        "categories": [{"id": i, "name": n, "icon": ic, "color": c} for i, n, ic, c in CATEGORIES],
        "conversations": C,
    }
    path = save("conversations.json", data)
    per = {}
    for c in C:
        per[c["category"]] = per.get(c["category"], 0) + 1
    print(len(C), "conversaciones", per, "->", path)
