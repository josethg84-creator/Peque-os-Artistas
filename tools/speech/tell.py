"""«Ahora cuéntamelo tú»: 8 secuencias de 4 dibujos para ordenar y contar.
Uso: python3 tools/speech/tell.py"""

from content_common import BOY, GIRL, I, D, K, S, APPLE, save

LUNA = lambda e="feliz", up=False: K(e, True, GIRL, up)
MATEO = lambda e="feliz", up=False: K(e, False, BOY, up)
DOG = D("animal_perro")


def seq(sid, title, steps, ending):
    """steps: (dibujo, frase, pregunta de Lolo)."""
    return {"id": sid, "title": title, "steps": [{"picture": p, "phrase": f, "question": q} for p, f, q in steps], "ending": ending}


TELL = [
    seq("semilla", "La semilla mágica", [
        (S("jardin", (LUNA("sorprendido"), .45, .62, .45), (I("seed", "#8D6E63"), .78, .8, .12)), "Una niña encuentra una semilla.", "¿Qué encuentra la niña?"),
        (S("jardin", (LUNA(), .4, .62, .42), (I("plant", "#8D6E63"), .74, .78, .18)), "La niña planta la semilla.", "¿Qué hace la niña con la semilla?"),
        (S("jardin", (LUNA(), .4, .62, .42), (I("water", "#039BE5"), .74, .64, .16)), "La niña riega la planta.", "¿Qué le da la niña a la planta?"),
        (S("jardin", (LUNA("emocionado", True), .35, .62, .42), (I("flower", "#EC407A"), .72, .66, .28)), "¡Aparece una flor!", "¿Qué pasó al final?"),
    ], "La niña plantó una semilla, la regó y creció una flor."),
    seq("pastel", "Hacemos un pastel", [
        (S("cocina", (MATEO(), .4, .62, .42), (I("egg", "#F9A825"), .76, .76, .14)), "Mateo mezcla los huevos y la harina.", "¿Qué hace Mateo primero?"),
        (S("cocina", (I("hot", "#F4511E"), .5, .55, .3)), "El pastel se hornea.", "¿Dónde va el pastel?"),
        (S("cocina", (MATEO(), .35, .62, .4), (I("cake", "#AB47BC"), .72, .7, .24)), "Mateo decora el pastel.", "¿Qué hace Mateo ahora?"),
        (S("cocina", (MATEO("emocionado", True), .35, .62, .42), (I("cake", "#AB47BC"), .72, .7, .24), (LUNA("feliz"), .9, .62, .3)), "Todos comen pastel.", "¿Qué pasó al final?"),
    ], "Mateo mezcló, horneó y decoró un pastel, y todos lo comieron."),
    seq("perro_bano", "El baño de Toby", [
        (S("jardin", (DOG, .5, .66, .45), (I("trash", "#8D6E63"), .8, .82, .14)), "Toby juega en el barro.", "¿Qué hace Toby?"),
        (S("casa", (DOG, .45, .66, .42), (I("bath", "#29B6F6"), .78, .7, .22)), "Toby se baña con agua y jabón.", "¿Qué hacen con Toby?"),
        (S("casa", (DOG, .45, .66, .42), (I("towel", "#F48FB1"), .78, .6, .2)), "Lo secan con una toalla.", "¿Con qué lo secan?"),
        (S("jardin", (DOG, .45, .64, .45), (I("star", "#FBC02D"), .8, .35, .14)), "¡Toby está limpio y feliz!", "¿Cómo está Toby al final?"),
    ], "Toby se ensució, lo bañaron, lo secaron y quedó limpio y feliz."),
    seq("lluvia", "Después de la lluvia", [
        (S("cielo", (I("cloud", "#78909C"), .5, .45, .4)), "Llegan unas nubes grises.", "¿Qué hay en el cielo?"),
        (S("lluvia", (LUNA("sorprendido"), .5, .64, .45)), "Empieza a llover.", "¿Qué pasa ahora?"),
        (S("jardin", (I("sun", "#FFB300"), .5, .35, .3)), "Sale el sol.", "¿Qué sale después?"),
        (S("cielo", (I("rainbow", "#EC407A"), .5, .45, .55), (LUNA("emocionado", True), .3, .76, .32)), "¡Aparece un arcoíris!", "¿Qué aparece al final?"),
    ], "Llegaron las nubes, llovió, salió el sol y apareció un arcoíris."),
    seq("dientes", "Dientes limpios", [
        (S("cocina", (MATEO(), .4, .62, .42), (APPLE, .76, .72, .18)), "Mateo come una manzana.", "¿Qué come Mateo?"),
        (S("casa", (I("clean", "#29B6F6"), .5, .55, .3)), "Toma su cepillo de dientes.", "¿Qué toma Mateo?"),
        (S("casa", (MATEO("feliz", True), .5, .62, .48)), "Se cepilla los dientes.", "¿Qué hace con el cepillo?"),
        (S("casa", (MATEO("emocionado", True), .45, .62, .45), (I("star", "#FBC02D"), .8, .35, .14)), "¡Sonríe con los dientes limpios!", "¿Cómo termina?"),
    ], "Mateo comió, tomó su cepillo, se lavó los dientes y sonrió."),
    seq("dormir", "A dormir", [
        (S("dormitorio", (LUNA(), .45, .62, .45), (I("shirt", "#9FA8DA"), .8, .7, .16)), "Luna se pone el pijama.", "¿Qué se pone Luna?"),
        (S("dormitorio", (LUNA("tranquilo"), .45, .62, .45), (I("read", "#8E24AA"), .8, .62, .18)), "Escucha un cuento.", "¿Qué escucha Luna?"),
        (S("dormitorio", (I("lamp", "#FBC02D"), .5, .45, .3)), "Apagan la luz.", "¿Qué hacen con la luz?"),
        (S("noche", (LUNA("tranquilo"), .5, .62, .45), (I("sleepz", "#5C6BC0"), .8, .3, .16)), "Luna se duerme.", "¿Qué pasa al final?"),
    ], "Luna se puso el pijama, escuchó un cuento, apagaron la luz y se durmió."),
    seq("pollito", "El pollito", [
        (S("parque", (I("egg", "#F9A825"), .5, .7, .25)), "Hay un huevo en el nido.", "¿Qué hay en el nido?"),
        (S("parque", (I("egg", "#F9A825"), .5, .7, .25), (I("sprout", "#8D6E63"), .5, .5, .12)), "El huevo se rompe.", "¿Qué le pasa al huevo?"),
        (S("parque", (D("granja_patito", **{"*": "#FFD54F"}), .5, .66, .35)), "Sale un pollito.", "¿Quién sale del huevo?"),
        (S("parque", (D("granja_gallina"), .35, .62, .4), (D("granja_patito", **{"*": "#FFD54F"}), .7, .72, .25)), "El pollito camina con su mamá.", "¿Con quién camina?"),
    ], "El huevo se rompió, salió un pollito y caminó con su mamá."),
    seq("escuela", "Vamos a la escuela", [
        (S("dormitorio", (MATEO(), .45, .62, .45), (I("backpack", "#E53935"), .8, .7, .16)), "Mateo prepara su mochila.", "¿Qué prepara Mateo?"),
        (S("parque", (MATEO(), .4, .62, .42), (I("man", "#3949AB"), .72, .6, .36)), "Camina a la escuela con papá.", "¿Adónde va con papá?"),
        (S("escuela", (MATEO(), .4, .64, .42), (I("abc", "#E53935"), .76, .4, .2)), "Aprende las letras en clase.", "¿Qué aprende en clase?"),
        (S("parque", (MATEO("emocionado", True), .32, .62, .4), (LUNA("feliz", True), .7, .62, .4)), "Juega con sus amigos en el recreo.", "¿Qué hace en el recreo?"),
    ], "Mateo preparó la mochila, fue a la escuela, aprendió las letras y jugó en el recreo."),
]

if __name__ == "__main__":
    print(len(TELL), save("tell.json", {"format_version": 1, "sequences": TELL}))
