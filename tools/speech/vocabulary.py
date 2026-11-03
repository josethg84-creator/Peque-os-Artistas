"""Fase 4: banco de vocabulario (más de 200 palabras nuevas, sin repetir las de
words.json). Cada palabra: id, texto, artículo, categoría, ilustración,
pronunciación por sílabas, frase de ejemplo y nivel orientativo (1 a 3).

Las ilustraciones son dibujos del catálogo, dibujos propios (niños, escenas,
caritas) o pictogramas de Material (Apache 2.0). Este guion comprueba que
cada icono existe en Flutter y escribe también lib/speech/speech_icons_extra.dart.

Uso: python3 tools/speech/vocabulary.py"""

import json
import re
from pathlib import Path

from content_common import BOY, GIRL, D, E, K, S, ROOT, save

FLUTTER_ICONS = Path("/opt/sdk/flutter/packages/flutter/lib/src/material/icons.dart")


def M(name, color):
    return {"icon": name, "color": color}


# Grupos nuevos (los demás ya existen en words.json y se amplían).
NEW_CATEGORIES = [
    {"id": "escuela", "name": "Escuela", "color": "#5C9DED", "icon": "school"},
    {"id": "transporte", "name": "Transporte", "color": "#FF7043", "icon": "directions_bus"},
    {"id": "objetos", "name": "Objetos cotidianos", "color": "#AB47BC", "icon": "inventory_2"},
]

W = {}


def add(cat, *words):
    W.setdefault(cat, [])
    for (wid, text, article, pic, pron, example, level) in words:
        W[cat].append({"id": wid, "text": text, "article": article, "picture": pic,
                       "pronunciation": pron, "example": example, "level": level})


add("animales",
    ("jirafa", "jirafa", "la", D("animal_jirafa"), "ji-ra-fa", "La jirafa tiene el cuello muy largo.", 1),
    ("oso", "oso", "el", D("animal_oso"), "o-so", "El oso duerme en su cueva.", 1),
    ("tortuga", "tortuga", "la", D("animal_tortuga"), "tor-tu-ga", "La tortuga camina muy despacio.", 1),
    ("cebra", "cebra", "la", D("animal_cebra"), "ce-bra", "La cebra tiene rayas blancas y negras.", 2),
    ("cerdo", "cerdo", "el", D("granja_cerdito"), "cer-do", "El cerdo juega en el barro.", 1),
    ("gallina", "gallina", "la", D("granja_gallina"), "ga-lli-na", "La gallina pone un huevo.", 1),
    ("gallo", "gallo", "el", D("granja_gallo"), "ga-llo", "El gallo canta por la mañana.", 1),
    ("oveja", "oveja", "la", D("granja_oveja"), "o-ve-ja", "La oveja tiene mucha lana.", 1),
    ("caballo", "caballo", "el", D("granja_poni"), "ca-ba-llo", "El caballo corre por el campo.", 1),
    ("ballena", "ballena", "la", D("mar_ballena"), "ba-lle-na", "La ballena nada en el mar.", 2),
    ("cangrejo", "cangrejo", "el", D("mar_cangrejo"), "can-gre-jo", "El cangrejo camina por la arena.", 2),
    ("delfin", "delfín", "el", D("mar_delfin"), "del-fín", "El delfín salta en el agua.", 2),
    ("estrella_mar", "estrella de mar", "la", D("mar_estrella"), "es-tre-lla de mar", "La estrella de mar vive en el agua.", 3),
    ("pulpo", "pulpo", "el", D("mar_pulpo"), "pul-po", "El pulpo tiene ocho brazos.", 2),
    ("dinosaurio", "dinosaurio", "el", D("dinosaurio_01"), "di-no-sau-rio", "El dinosaurio es muy grande.", 2),
    ("unicornio", "unicornio", "el", D("fantasia_unicornio"), "u-ni-cor-nio", "El unicornio tiene un cuerno.", 3),
    ("dragon", "dragón", "el", D("fantasia_dragon"), "dra-gón", "El dragón vuela sobre el castillo.", 2),
    ("pajaro", "pájaro", "el", M("flutter_dash", "#29B6F6"), "pá-ja-ro", "El pájaro canta en el árbol.", 1),
    ("abeja", "abeja", "la", M("emoji_nature", "#F9A825"), "a-be-ja", "La abeja vuela de flor en flor.", 1),
    ("escarabajo", "escarabajo", "el", M("bug_report", "#43A047"), "es-ca-ra-ba-jo", "El escarabajo camina por la hoja.", 3),
    ("mascota", "mascota", "la", M("pets", "#8D6E63"), "mas-co-ta", "Mi mascota es un perro.", 2),
)

add("hogar",
    ("sofa", "sofá", "el", M("weekend", "#7E57C2"), "so-fá", "Leemos un cuento en el sofá.", 1),
    ("television", "televisión", "la", M("tv", "#455A64"), "te-le-vi-sión", "Vemos dibujos en la televisión.", 2),
    ("nevera", "nevera", "la", M("kitchen", "#78909C"), "ne-ve-ra", "La leche está en la nevera.", 2),
    ("cocina", "cocina", "la", S("cocina"), "co-ci-na", "Papá prepara la comida en la cocina.", 1),
    ("bano", "baño", "el", M("wc", "#29B6F6"), "ba-ño", "Me lavo las manos en el baño.", 1),
    ("ducha", "ducha", "la", M("shower", "#039BE5"), "du-cha", "Me lavo el pelo en la ducha.", 1),
    ("banera", "bañera", "la", M("bathtub", "#26C6DA"), "ba-ñe-ra", "El bebé juega en la bañera.", 2),
    ("escalera", "escalera", "la", M("stairs", "#8D6E63"), "es-ca-le-ra", "Subo la escalera despacio.", 2),
    ("jardin", "jardín", "el", M("yard", "#43A047"), "jar-dín", "Las flores crecen en el jardín.", 1),
    ("dormitorio", "dormitorio", "el", S("dormitorio"), "dor-mi-to-rio", "Mi cama está en el dormitorio.", 3),
    ("cuna", "cuna", "la", M("crib", "#F48FB1"), "cu-na", "El bebé duerme en la cuna.", 1),
    ("microondas", "microondas", "el", M("microwave", "#607D8B"), "mi-cro-on-das", "Calentamos la sopa en el microondas.", 3),
    ("lavadora", "lavadora", "la", M("local_laundry_service", "#42A5F5"), "la-va-do-ra", "La ropa se lava en la lavadora.", 2),
    ("llave", "llave", "la", M("key", "#FFB300"), "lla-ve", "Abro la puerta con la llave.", 1),
    ("escoba", "escoba", "la", M("cleaning_services", "#8D6E63"), "es-co-ba", "Barro el suelo con la escoba.", 2),
    ("telefono", "teléfono", "el", M("phone", "#43A047"), "te-lé-fo-no", "La abuela llama por teléfono.", 2),
    ("garaje", "garaje", "el", M("garage", "#78909C"), "ga-ra-je", "El coche duerme en el garaje.", 2),
    ("tejado", "tejado", "el", M("roofing", "#E53935"), "te-ja-do", "El gato sube al tejado.", 2),
    ("valla", "valla", "la", M("fence", "#A1887F"), "va-lla", "La valla está alrededor del jardín.", 3),
    ("radio", "radio", "la", M("radio", "#5C6BC0"), "ra-dio", "Escuchamos música en la radio.", 2),
    ("plancha", "plancha", "la", M("iron", "#90A4AE"), "plan-cha", "Mamá usa la plancha con cuidado.", 3),
    ("cortina", "cortina", "la", M("curtains", "#BA68C8"), "cor-ti-na", "Abro la cortina para ver el sol.", 2),
)

add("escuela",
    ("escuela", "escuela", "la", M("school", "#5C9DED"), "es-cue-la", "Voy a la escuela con mi mochila.", 1),
    ("lapiz", "lápiz", "el", M("edit", "#FFB300"), "lá-piz", "Escribo mi nombre con el lápiz.", 1),
    ("mochila", "mochila", "la", M("backpack", "#E53935"), "mo-chi-la", "Guardo mis libros en la mochila.", 1),
    ("tijeras", "tijeras", "las", M("content_cut", "#EF6C00"), "ti-je-ras", "Corto el papel con las tijeras.", 2),
    ("regla", "regla", "la", M("straighten", "#00897B"), "re-gla", "Dibujo una línea con la regla.", 2),
    ("pincel", "pincel", "el", M("brush", "#8E24AA"), "pin-cel", "Pinto un sol con el pincel.", 1),
    ("pinturas", "pinturas", "las", M("palette", "#EC407A"), "pin-tu-ras", "Mezclo las pinturas de colores.", 2),
    ("cuaderno", "cuaderno", "el", M("menu_book", "#3949AB"), "cua-der-no", "Dibujo en mi cuaderno.", 2),
    ("pizarra", "pizarra", "la", M("co_present", "#2E7D32"), "pi-za-rra", "La maestra escribe en la pizarra.", 2),
    ("calculadora", "calculadora", "la", M("calculate", "#546E7A"), "cal-cu-la-do-ra", "Sumamos con la calculadora.", 3),
    ("mapa", "mapa", "el", M("map", "#26A69A"), "ma-pa", "Buscamos el mar en el mapa.", 2),
    ("companeros", "compañeros", "los", M("groups", "#FB8C00"), "com-pa-ñe-ros", "Juego con mis compañeros en el recreo.", 3),
    ("musica", "música", "la", M("music_note", "#AB47BC"), "mú-si-ca", "En clase cantamos con música.", 1),
    ("letras", "letras", "las", M("abc", "#E53935"), "le-tras", "Aprendo las letras del abecedario.", 2),
    ("numeros", "números", "los", M("pin", "#1E88E5"), "nú-me-ros", "Cuento los números del uno al diez.", 2),
    ("cuento", "cuento", "el", M("auto_stories", "#8E24AA"), "cuen-to", "La maestra lee un cuento.", 1),
    ("calendario", "calendario", "el", M("calendar_month", "#F4511E"), "ca-len-da-rio", "Miramos el día en el calendario.", 3),
    ("trofeo", "trofeo", "el", M("emoji_events", "#FBC02D"), "tro-fe-o", "Ganamos un trofeo en la carrera.", 3),
    ("campana", "campana", "la", M("notifications", "#FFA000"), "cam-pa-na", "Suena la campana del recreo.", 2),
    ("ciencia", "ciencia", "la", M("science", "#00ACC1"), "cien-cia", "Hacemos un experimento de ciencia.", 3),
    ("piano", "piano", "el", M("piano", "#37474F"), "pia-no", "La niña toca el piano.", 2),
    ("balon", "balón", "el", M("sports_soccer", "#424242"), "ba-lón", "Pateamos el balón en el patio.", 1),
    ("dibujo", "dibujo", "el", M("draw", "#EC407A"), "di-bu-jo", "Hago un dibujo de mi familia.", 1),
)

add("transporte",
    ("autobus", "autobús", "el", D("vehiculo_autobus"), "au-to-bús", "Vamos a la escuela en autobús.", 1),
    ("camion", "camión", "el", M("local_shipping", "#1E88E5"), "ca-mión", "El camión lleva muchas cajas.", 1),
    ("moto", "moto", "la", M("two_wheeler", "#E53935"), "mo-to", "La moto hace mucho ruido.", 1),
    ("taxi", "taxi", "el", M("local_taxi", "#FBC02D"), "ta-xi", "Tomamos un taxi para ir al médico.", 2),
    ("bomberos", "camión de bomberos", "el", M("fire_truck", "#D32F2F"), "ca-mión de bom-be-ros", "El camión de bomberos es rojo.", 3),
    ("cohete", "cohete", "el", M("rocket_launch", "#5E35B1"), "co-he-te", "El cohete viaja a la luna.", 2),
    ("tractor", "tractor", "el", M("agriculture", "#43A047"), "trac-tor", "El tractor trabaja en el campo.", 2),
    ("velero", "velero", "el", M("sailing", "#039BE5"), "ve-le-ro", "El velero navega con el viento.", 2),
    ("canoa", "canoa", "la", M("kayaking", "#FB8C00"), "ca-no-a", "Remamos en la canoa por el río.", 2),
    ("tranvia", "tranvía", "el", M("tram", "#00897B"), "tran-ví-a", "El tranvía pasa por la ciudad.", 3),
    ("metro", "metro", "el", M("subway", "#3949AB"), "me-tro", "El metro va por debajo de la tierra.", 2),
    ("patinete", "patinete", "el", M("electric_scooter", "#EC407A"), "pa-ti-ne-te", "Voy al parque en patinete.", 2),
    ("furgoneta", "furgoneta", "la", M("airport_shuttle", "#6D4C41"), "fur-go-ne-ta", "La furgoneta lleva a toda la familia.", 3),
    ("semaforo", "semáforo", "el", M("traffic", "#43A047"), "se-má-fo-ro", "Cruzamos cuando el semáforo está en verde.", 3),
    ("caravana", "caravana", "la", M("rv_hookup", "#8D6E63"), "ca-ra-va-na", "Dormimos en la caravana de vacaciones.", 3),
    ("trineo", "trineo", "el", M("sledding", "#0288D1"), "tri-ne-o", "Bajamos por la nieve en trineo.", 3),
    ("gasolinera", "gasolinera", "la", M("local_gas_station", "#F4511E"), "ga-so-li-ne-ra", "El coche se llena en la gasolinera.", 3),
    ("aeropuerto", "aeropuerto", "el", M("flight_takeoff", "#1565C0"), "a-e-ro-puer-to", "El avión sale del aeropuerto.", 3),
    ("estacion", "estación", "la", M("train", "#6A1B9A"), "es-ta-ción", "Esperamos el tren en la estación.", 3),
    ("puerto", "puerto", "el", M("anchor", "#455A64"), "puer-to", "Los barcos descansan en el puerto.", 3),
)

add("alimentos",
    ("pizza", "pizza", "la", M("local_pizza", "#F4511E"), "piz-za", "Comemos pizza con queso.", 1),
    ("hamburguesa", "hamburguesa", "la", M("lunch_dining", "#A1887F"), "ham-bur-gue-sa", "La hamburguesa tiene pan y tomate.", 2),
    ("sopa", "sopa", "la", M("soup_kitchen", "#FB8C00"), "so-pa", "La sopa está muy caliente.", 1),
    ("arroz", "arroz", "el", M("rice_bowl", "#8D6E63"), "a-rroz", "Como arroz con verduras.", 1),
    ("espaguetis", "espaguetis", "los", M("dinner_dining", "#F9A825"), "es-pa-gue-tis", "Me encantan los espaguetis con tomate.", 3),
    ("tostada", "tostada", "la", M("breakfast_dining", "#D7A86E"), "tos-ta-da", "Desayuno una tostada con mantequilla.", 2),
    ("galleta", "galleta", "la", M("cookie", "#8D6E63"), "ga-lle-ta", "Mi galleta tiene chocolate.", 1),
    ("cruasan", "cruasán", "el", M("bakery_dining", "#E0A35A"), "crua-sán", "El cruasán está recién hecho.", 3),
    ("leche", "leche", "la", M("local_drink", "#90A4AE"), "le-che", "Bebo un vaso de leche.", 1),
    ("jugo", "jugo", "el", M("local_drink", "#FB8C00"), "ju-go", "El jugo de naranja es dulce.", 1),
    ("pescado", "pescado", "el", M("set_meal", "#0288D1"), "pes-ca-do", "Hoy comemos pescado.", 2),
    ("huevo_frito", "huevo frito", "el", M("egg_alt", "#FBC02D"), "hue-vo fri-to", "Desayuno un huevo frito.", 2),
    ("ensalada", "ensalada", "la", M("eco", "#43A047"), "en-sa-la-da", "La ensalada tiene lechuga y tomate.", 2),
    ("fideos", "fideos", "los", M("ramen_dining", "#FFB74D"), "fi-de-os", "La sopa de fideos está rica.", 2),
    ("miel", "miel", "la", M("hive", "#FFA000"), "miel", "La abeja hace miel.", 2),
    ("desayuno", "desayuno", "el", M("free_breakfast", "#6D4C41"), "de-sa-yu-no", "El desayuno es por la mañana.", 2),
    ("cena", "cena", "la", M("restaurant_menu", "#5C6BC0"), "ce-na", "La cena es por la noche.", 2),
    ("comida", "comida", "la", M("restaurant", "#E53935"), "co-mi-da", "La comida está en la mesa.", 1),
    ("brocheta", "brocheta", "la", M("kebab_dining", "#8D6E63"), "bro-che-ta", "La brocheta tiene carne y verduras.", 3),
    ("merienda", "merienda", "la", M("brunch_dining", "#EC407A"), "me-rien-da", "La merienda es a media tarde.", 3),
)

add("familia",
    ("tio", "tío", "el", M("man", "#00897B"), "tí-o", "Mi tío me lleva al parque.", 1),
    ("tia", "tía", "la", M("woman", "#AB47BC"), "tí-a", "Mi tía hace un pastel.", 1),
    ("primo", "primo", "el", K("feliz", False, "#81C784"), "pri-mo", "Juego a la pelota con mi primo.", 1),
    ("prima", "prima", "la", K("feliz", True, "#FFB74D"), "pri-ma", "Mi prima canta muy bonito.", 1),
    ("hijo", "hijo", "el", K("emocionado", False, BOY, True), "hi-jo", "El hijo abraza a su papá.", 2),
    ("hija", "hija", "la", K("emocionado", True, GIRL, True), "hi-ja", "La hija ayuda a su mamá.", 2),
    ("nieto", "nieto", "el", K("tranquilo", False, "#9575CD"), "nie-to", "El abuelo juega con su nieto.", 2),
    ("nieta", "nieta", "la", K("tranquilo", True, "#4DD0E1"), "nie-ta", "La abuela peina a su nieta.", 2),
    ("vecino", "vecino", "el", M("man", "#6D4C41"), "ve-ci-no", "El vecino tiene un perro.", 2),
    ("vecina", "vecina", "la", M("woman", "#EF6C00"), "ve-ci-na", "La vecina riega sus flores.", 2),
    ("gemelos", "gemelos", "los", M("people", "#1E88E5"), "ge-me-los", "Los gemelos se parecen mucho.", 3),
    ("bisabuela", "bisabuela", "la", M("elderly_woman", "#8E24AA"), "bi-sa-bue-la", "La bisabuela cuenta historias.", 3),
    ("padres", "padres", "los", M("family_restroom", "#E91E63"), "pa-dres", "Mis padres me quieren mucho.", 2),
)

add("naturaleza",
    ("lluvia", "lluvia", "la", M("thunderstorm", "#039BE5"), "llu-via", "La lluvia moja el jardín.", 1),
    ("viento", "viento", "el", M("air", "#78909C"), "vien-to", "El viento mueve las hojas.", 1),
    ("arcoiris", "arcoíris", "el", M("looks", "#EC407A"), "ar-co-í-ris", "Después de la lluvia sale el arcoíris.", 2),
    ("hoja", "hoja", "la", M("eco", "#66BB6A"), "ho-ja", "La hoja es verde.", 1),
    ("semilla", "semilla", "la", M("grain", "#8D6E63"), "se-mi-lla", "Planto una semilla en la tierra.", 2),
    ("planta", "planta", "la", M("spa", "#43A047"), "plan-ta", "La planta necesita agua.", 1),
    ("bosque", "bosque", "el", S("bosque"), "bos-que", "En el bosque hay muchos árboles.", 2),
    ("rio", "río", "el", M("water", "#0288D1"), "rí-o", "El río lleva agua fría.", 1),
    ("playa", "playa", "la", S("playa"), "pla-ya", "Hacemos castillos en la playa.", 1),
    ("volcan", "volcán", "el", M("volcano", "#E64A19"), "vol-cán", "El volcán está dormido.", 3),
    ("tormenta", "tormenta", "la", S("lluvia"), "tor-men-ta", "En la tormenta hay rayos y truenos.", 2),
    ("rayo", "rayo", "el", M("flash_on", "#FBC02D"), "ra-yo", "El rayo ilumina el cielo.", 2),
    ("gota", "gota", "la", M("water_drop", "#29B6F6"), "go-ta", "Una gota de agua cae de la nube.", 2),
    ("hierba", "hierba", "la", M("grass", "#7CB342"), "hier-ba", "La vaca come hierba.", 2),
    ("tierra", "tierra", "la", M("public", "#1E88E5"), "tie-rra", "Vivimos en el planeta Tierra.", 2),
    ("cielo", "cielo", "el", S("cielo"), "cie-lo", "El cielo está azul.", 1),
    ("noche", "noche", "la", S("noche"), "no-che", "Por la noche salen las estrellas.", 1),
    ("dia", "día", "el", M("light_mode", "#FFB300"), "dí-a", "Hoy es un día muy bonito.", 1),
    ("amanecer", "amanecer", "el", M("wb_twilight", "#FF7043"), "a-ma-ne-cer", "Al amanecer canta el gallo.", 3),
    ("frio", "frío", "el", M("severe_cold", "#4FC3F7"), "frí-o", "En invierno hace mucho frío.", 2),
    ("calor", "calor", "el", M("thermostat", "#F4511E"), "ca-lor", "En verano hace calor.", 2),
    ("ola", "ola", "la", M("waves", "#0288D1"), "o-la", "La ola llega a la orilla.", 2),
    ("campo", "campo", "el", M("terrain", "#689F38"), "cam-po", "Las vacas viven en el campo.", 2),
    ("tornado", "tornado", "el", M("tornado", "#78909C"), "tor-na-do", "El tornado gira muy rápido.", 3),
)

add("emociones",
    ("emocionado", "emocionado", None, E("emocionado"), "e-mo-cio-na-do", "Estoy emocionado por mi cumpleaños.", 2),
    ("contento", "contento", None, K("feliz", False, "#4DB6AC"), "con-ten-to", "Estoy contento con mi dibujo.", 1),
    ("nervioso", "nervioso", None, M("sentiment_neutral", "#FFA726"), "ner-vio-so", "Estoy nervioso antes de la función.", 3),
    ("orgulloso", "orgulloso", None, K("emocionado", True, "#7986CB", True), "or-gu-llo-so", "Estoy orgulloso de mi torre.", 3),
    ("preocupado", "preocupado", None, M("sentiment_dissatisfied", "#7E57C2"), "pre-o-cu-pa-do", "Estoy preocupado porque mi gato no vuelve.", 3),
    ("valiente", "valiente", None, K("feliz", False, "#E57373", True), "va-lien-te", "Soy valiente en la oscuridad.", 2),
    ("timido", "tímido", None, M("face", "#F48FB1"), "tí-mi-do", "Estoy tímido en mi primer día.", 3),
    ("alegre", "alegre", None, M("sentiment_satisfied", "#FFB300"), "a-le-gre", "Hoy me siento alegre.", 1),
    ("amor", "amor", "el", M("favorite", "#E91E63"), "a-mor", "Siento mucho amor por mi familia.", 2),
    ("confundido", "confundido", None, M("psychology", "#5C6BC0"), "con-fun-di-do", "Estoy confundido con el juego.", 3),
    ("divertido", "divertido", None, M("celebration", "#EC407A"), "di-ver-ti-do", "El juego es muy divertido.", 2),
    ("curioso", "curioso", None, M("travel_explore", "#00897B"), "cu-rio-so", "Soy curioso y hago preguntas.", 2),
    ("miedo", "miedo", "el", M("mood_bad", "#5E35B1"), "mie-do", "Tengo miedo de los truenos.", 1),
    ("sueno", "sueño", "el", M("bedtime", "#3949AB"), "sue-ño", "Tengo sueño por la noche.", 1),
    ("hambre", "hambre", "el", M("fastfood", "#FB8C00"), "ham-bre", "Tengo hambre a la hora de comer.", 1),
    ("sed", "sed", "la", M("local_drink", "#29B6F6"), "sed", "Tengo sed después de correr.", 1),
    ("risa", "risa", "la", M("sentiment_very_satisfied", "#FFCA28"), "ri-sa", "Me da risa el payaso.", 1),
    ("abrazo", "abrazo", "el", M("volunteer_activism", "#F06292"), "a-bra-zo", "Le doy un abrazo a mi hermano.", 1),
)

add("acciones",
    ("escribir", "escribir", None, M("edit_note", "#3949AB"), "es-cri-bir", "Me gusta escribir mi nombre.", 1),
    ("dibujar", "dibujar", None, M("draw", "#EC407A"), "di-bu-jar", "Vamos a dibujar un sol.", 1),
    ("cocinar", "cocinar", None, M("outdoor_grill", "#E64A19"), "co-ci-nar", "Papá va a cocinar la cena.", 2),
    ("lavar", "lavar", None, M("wash", "#29B6F6"), "la-var", "Voy a lavar mis manos.", 1),
    ("abrazar", "abrazar", None, M("favorite", "#F06292"), "a-bra-zar", "Me gusta abrazar a mi mamá.", 1),
    ("escuchar", "escuchar", None, M("hearing", "#7E57C2"), "es-cu-char", "Me gusta escuchar cuentos.", 1),
    ("reir", "reír", None, M("emoji_emotions", "#FFB300"), "re-ír", "Nos gusta reír con los amigos.", 2),
    ("llorar", "llorar", None, M("sentiment_very_dissatisfied", "#5C6BC0"), "llo-rar", "El bebé empieza a llorar.", 2),
    ("aplaudir", "aplaudir", None, M("sign_language", "#FB8C00"), "a-plau-dir", "Vamos a aplaudir al final.", 2),
    ("subir", "subir", None, M("north", "#43A047"), "su-bir", "Voy a subir al tobogán.", 2),
    ("bajar", "bajar", None, M("south", "#E53935"), "ba-jar", "Voy a bajar por la escalera.", 2),
    ("empujar", "empujar", None, M("pan_tool", "#8D6E63"), "em-pu-jar", "Ayudo a empujar el carrito.", 3),
    ("lanzar", "lanzar", None, M("sports_baseball", "#F4511E"), "lan-zar", "Voy a lanzar la pelota.", 2),
    ("atrapar", "atrapar", None, M("sports_handball", "#00897B"), "a-tra-par", "Intento atrapar la pelota.", 3),
    ("construir", "construir", None, M("construction", "#FFA000"), "cons-truir", "Vamos a construir una torre.", 3),
    ("regar", "regar", None, M("water_drop", "#039BE5"), "re-gar", "Ayudo a regar las plantas.", 2),
    ("plantar", "plantar", None, M("local_florist", "#EC407A"), "plan-tar", "Vamos a plantar una flor.", 2),
    ("volar", "volar", None, M("flight", "#1E88E5"), "vo-lar", "Los pájaros saben volar.", 1),
    ("comprar", "comprar", None, M("shopping_cart", "#43A047"), "com-prar", "Vamos a comprar fruta.", 2),
    ("llamar", "llamar", None, M("call", "#26A69A"), "lla-mar", "Voy a llamar a la abuela.", 2),
    ("vestirse", "vestirse", None, M("checkroom", "#7E57C2"), "ves-tir-se", "Es hora de vestirse para salir.", 3),
    ("montar", "montar", None, M("pedal_bike", "#E53935"), "mon-tar", "Me gusta montar en bici.", 2),
    ("esconder", "esconder", None, M("visibility_off", "#5D4037"), "es-con-der", "Vamos a esconder el tesoro.", 2),
    ("buscar", "buscar", None, M("search", "#3949AB"), "bus-car", "Vamos a buscar mis zapatos.", 1),
    ("saludar", "saludar", None, M("waving_hand", "#FFB300"), "sa-lu-dar", "Vamos a saludar a la maestra.", 1),
    ("compartir", "compartir", None, M("share", "#00ACC1"), "com-par-tir", "Me gusta compartir mis juguetes.", 2),
    ("ayudar", "ayudar", None, M("handshake", "#FB8C00"), "a-yu-dar", "Me gusta ayudar en casa.", 1),
    ("soplar", "soplar", None, M("air", "#4FC3F7"), "so-plar", "Vamos a soplar las velas.", 2),
)

add("objetos",
    ("zapatos", "zapatos", "los", M("shoes", "#6D4C41"), "za-pa-tos", "Me pongo los zapatos para salir.", 1),
    ("paraguas", "paraguas", "el", M("umbrella", "#7E57C2"), "pa-ra-guas", "Llevo el paraguas porque llueve.", 1),
    ("jabon", "jabón", "el", M("soap", "#4FC3F7"), "ja-bón", "Me lavo las manos con jabón.", 1),
    ("toalla", "toalla", "la", M("dry", "#F48FB1"), "to-a-lla", "Me seco con la toalla.", 1),
    ("regalo", "regalo", "el", M("card_giftcard", "#E53935"), "re-ga-lo", "Abro mi regalo de cumpleaños.", 1),
    ("caja", "caja", "la", M("inventory_2", "#A1887F"), "ca-ja", "Guardo los juguetes en la caja.", 1),
    ("bolsa", "bolsa", "la", M("shopping_bag", "#EC407A"), "bol-sa", "Llevo la fruta en la bolsa.", 1),
    ("cesta", "cesta", "la", M("shopping_basket", "#8D6E63"), "ces-ta", "Ponemos las manzanas en la cesta.", 2),
    ("linterna", "linterna", "la", M("flashlight_on", "#FBC02D"), "lin-ter-na", "Con la linterna veo en la oscuridad.", 2),
    ("carta", "carta", "la", M("mail", "#1E88E5"), "car-ta", "Escribo una carta a la abuela.", 2),
    ("taza", "taza", "la", M("local_cafe", "#8D6E63"), "ta-za", "Bebo leche en mi taza.", 1),
    ("camiseta", "camiseta", "la", M("checkroom", "#42A5F5"), "ca-mi-se-ta", "Mi camiseta es azul.", 1),
    ("auriculares", "auriculares", "los", M("headphones", "#455A64"), "au-ri-cu-la-res", "Escucho música con los auriculares.", 3),
    ("camara", "cámara", "la", M("photo_camera", "#37474F"), "cá-ma-ra", "Hago una foto con la cámara.", 2),
    ("curita", "curita", "la", M("healing", "#FFAB91"), "cu-ri-ta", "Me pongo una curita en la rodilla.", 2),
    ("termometro", "termómetro", "el", M("thermostat", "#E53935"), "ter-mó-me-tro", "El termómetro mide la fiebre.", 3),
    ("moneda", "moneda", "la", M("savings", "#FFB300"), "mo-ne-da", "Guardo una moneda en mi alcancía.", 2),
    ("papelera", "papelera", "la", M("delete", "#78909C"), "pa-pe-le-ra", "Tiro el papel a la papelera.", 2),
    ("pila", "pila", "la", M("battery_full", "#43A047"), "pi-la", "El juguete necesita una pila.", 3),
    ("computadora", "computadora", "la", M("computer", "#5C6BC0"), "com-pu-ta-do-ra", "Papá trabaja en la computadora.", 2),
    ("tableta", "tableta", "la", M("tablet", "#26A69A"), "ta-ble-ta", "Vemos un cuento en la tableta.", 2),
    ("lupa", "lupa", "la", M("zoom_in", "#00897B"), "lu-pa", "Miro la hormiga con la lupa.", 2),
    ("cuchara", "cuchara", "la", M("restaurant", "#90A4AE"), "cu-cha-ra", "Tomo la sopa con la cuchara.", 1),
    ("foco", "foco", "el", M("lightbulb", "#FFCA28"), "fo-co", "El foco da luz a la casa.", 2),
)

# Pronunciación por sílabas de algunas palabras de la 1.ª entrega (para los
# juegos de sílabas y sonidos).
EXISTING_PRONUNCIATION = {
    "mama": "ma-má", "papa": "pa-pá", "perro": "pe-rro", "gato": "ga-to", "conejo": "co-ne-jo",
    "elefante": "e-le-fan-te", "pato": "pa-to", "mariposa": "ma-ri-po-sa", "mono": "mo-no",
    "manzana": "man-za-na", "platano": "plá-ta-no", "fresa": "fre-sa", "helado": "he-la-do",
    "pelota": "pe-lo-ta", "coche": "co-che", "tren": "tren", "avion": "a-vión", "barco": "bar-co",
    "bicicleta": "bi-ci-cle-ta", "casa": "ca-sa", "cama": "ca-ma", "silla": "si-lla", "mesa": "me-sa",
    "ventana": "ven-ta-na", "libro": "li-bro", "sol": "sol", "luna": "lu-na", "estrella": "es-tre-lla",
    "nube": "nu-be", "flor": "flor", "arbol": "ár-bol", "pez": "pez", "leon": "le-ón", "vaca": "va-ca",
    "oso_peluche": None,
}


def material_names():
    text = FLUTTER_ICONS.read_text()
    return set(re.findall(r"static const IconData (\w+) =", text))


def speech_icon_names():
    text = (ROOT / "lib/speech/speech_content.dart").read_text()
    block = text[text.index("abstract final class SpeechIcons"):]
    return set(re.findall(r"'(\w+)': Icons\.", block))


def main():
    words_json = json.loads((ROOT / "assets/speech/words.json").read_text())
    existing_ids = {w["id"] for c in words_json["categories"] for w in c["words"]}
    existing_texts = {w["text"] for c in words_json["categories"] for w in c["words"]}
    verbs = {v["id"] for v in json.loads((ROOT / "assets/speech/verbs.json").read_text())["verbs"]}
    material = material_names()
    known = speech_icon_names()
    extra = set()
    ids = set()
    total = 0
    for cat, words in W.items():
        for w in words:
            assert w["id"] not in existing_ids and w["id"] not in ids, w["id"]
            assert w["text"] not in existing_texts and w["text"] not in verbs, w["text"]
            ids.add(w["id"])
            assert w["pronunciation"].replace("-", "") == w["text"].lower(), w
            assert w["text"].lower() in w["example"].lower(), w
            assert w["level"] in (1, 2, 3)
            icon = w["picture"].get("icon")
            if icon and icon not in known:
                assert icon in material, f"icono inexistente: {icon}"
                extra.add(icon)
            total += 1
    for c in NEW_CATEGORIES:
        if c["icon"] not in known:
            assert c["icon"] in material, c["icon"]
            extra.add(c["icon"])
    for wid, pron in EXISTING_PRONUNCIATION.items():
        if pron:
            text = next(w["text"] for c in words_json["categories"] for w in c["words"] if w["id"] == wid)
            assert pron.replace("-", "") == text.lower(), (wid, pron)
    data = {
        "format_version": 1,
        "categories": NEW_CATEGORIES,
        "words": [{**w, "category": cat} for cat, words in W.items() for w in words],
        "pronunciation": {k: v for k, v in EXISTING_PRONUNCIATION.items() if v},
    }
    save("vocabulary.json", data)
    lines = [
        "// GENERADO por tools/speech/vocabulary.py: no editar a mano.",
        "import 'package:flutter/material.dart';",
        "",
        "/// Pictogramas de Material que usa el banco de vocabulario (fase 4).",
        "const extraSpeechIcons = <String, IconData>{",
        *[f"  '{n}': Icons.{n}," for n in sorted(extra)],
        "};",
        "",
    ]
    (ROOT / "lib/speech/speech_icons_extra.dart").write_text("\n".join(lines))
    print(total, {c: len(ws) for c, ws in W.items()}, len(extra), "iconos extra")


if __name__ == "__main__":
    main()
