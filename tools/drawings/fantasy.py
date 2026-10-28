"""Personajes fantásticos originales: hada, robot, dragón, unicornio y extraterrestre."""

from drawing_lib import mirror


def hada(d):
    d.ellipse("ala_superior_izquierda", 350, 480, 145, 82, -30)
    d.ellipse("ala_superior_derecha", 674, 480, 145, 82, 30)
    d.ellipse("ala_inferior_izquierda", 375, 640, 105, 60, 25)
    d.ellipse("ala_inferior_derecha", 649, 640, 105, 60, -25)
    d.rrect("pierna_izquierda", 460, 790, 42, 90, 18)
    d.rrect("pierna_derecha", 522, 790, 42, 90, 18)
    d.ellipse("zapato_izquierdo", 474, 885, 44, 24)
    d.ellipse("zapato_derecho", 550, 885, 44, 24)
    d.path(
        "vestido",
        [("M", [(445, 520)]), ("L", [(579, 520)]), ("L", [(690, 800)]), ("Q", [(512, 850), (334, 800)])],
        [(334, 520), (690, 830)],
    )
    d.circle("cinturon_flor", 512, 575, 26)
    d.band("brazo_izquierdo", [(470, 548), (395, 640)], 40)
    d.band("brazo_derecho", [(554, 548), (650, 500)], 40)
    d.band("varita", [(660, 495), (745, 365)], 26)
    d.star("estrella", 756, 340, 66, 30)
    d.circle("mono_izquierdo", 412, 340, 48)
    d.circle("mono_derecho", 612, 340, 48)
    d.circle("cara", 512, 418, 94)
    d.path(
        "flequillo",
        [("M", [(418, 410)]), ("C", [(420, 300), (604, 300), (606, 410)]), ("C", [(570, 365), (540, 360), (512, 385)]),
         ("C", [(484, 360), (454, 365), (418, 410)])],
        [(418, 320), (606, 410)],
    )
    d.circle("mano_izquierda", 392, 645, 24)
    d.circle("mano_derecha", 655, 495, 24)
    d.eyes(512, 430, 34, 12)
    d.smile(512, 462, 22, 9)


def robot(d):
    d.band("antena", [(512, 255), (512, 175)], 38)
    d.circle("antena_bola", 512, 150, 32)
    d.rrect("oreja_izquierda", 338, 305, 44, 90, 14)
    d.rrect("oreja_derecha", 642, 305, 44, 90, 14)
    d.rrect("cabeza", 372, 245, 280, 210, 44)
    d.circle("ojo_izquierdo", 450, 335, 42)
    d.circle("ojo_derecho", 574, 335, 42)
    d.arc_shape("boca", (458, 392), [("L", (566, 392)), ("A", 54, 40, 0, 1, (458, 392))], [(458, 392), (566, 432)])
    d.rrect("cuello", 466, 440, 92, 48, 10)
    d.band("brazo_izquierdo", [(370, 530), (290, 600), (275, 670)], 52)
    d.band("brazo_derecho", [(654, 530), (735, 470), (760, 395)], 52)
    d.circle("mano_izquierda", 272, 700, 40)
    d.circle("mano_derecha", 765, 365, 40)
    d.rrect("pierna_izquierda", 410, 720, 70, 110, 16)
    d.rrect("pierna_derecha", 544, 720, 70, 110, 16)
    d.rrect("pie_izquierdo", 385, 820, 120, 60, 26)
    d.rrect("pie_derecho", 519, 820, 120, 60, 26)
    d.rrect("cuerpo", 352, 475, 320, 260, 44)
    d.rrect("panel", 422, 520, 180, 135, 22)
    d.heart("corazon", 512, 588, 92)
    d.circle("boton_1", 398, 690, 24)
    d.circle("boton_2", 626, 690, 24)
    d.dot(458, 335, 16)
    d.dot(582, 335, 16)


def dragon(d):
    wing = [(410, 560), (215, 370), (230, 470), (185, 505), (240, 540), (225, 600), (330, 640)]
    d.poly("ala_izquierda", wing)
    d.poly("ala_derecha", mirror(wing))
    d.band("cola", [(620, 800), (760, 830), (830, 750)], 64, 26)
    d.heart("punta_cola", 840, 705, 80)
    d.ellipse("cuerpo", 512, 700, 170, 175)
    d.ellipse("barriga", 512, 745, 102, 122)
    d.ellipse("brazo_izquierdo", 385, 690, 36, 58, 30)
    d.ellipse("brazo_derecho", 639, 690, 36, 58, -30)
    d.ellipse("pata_izquierda", 430, 875, 64, 36)
    d.ellipse("pata_derecha", 594, 875, 64, 36)
    d.poly("cuerno_izquierdo", [(425, 300), (395, 185), (480, 275)])
    d.poly("cuerno_derecho", mirror([(425, 300), (395, 185), (480, 275)]))
    d.ellipse("cabeza", 512, 405, 175, 142)
    d.ellipse("hocico", 512, 470, 98, 62)
    for y in (700, 750, 800):
        d.line([(440, y), (512, y + 12), (584, y)], 8)
    d.eyes(512, 375, 70, 24)
    d.dot(485, 455, 8)
    d.dot(539, 455, 8)
    d.smile(512, 488, 40, 14)


def unicornio(d):
    d.blob("cola", [(770, 560), (860, 580), (900, 690), (860, 800), (820, 790), (850, 700), (800, 620)])
    for i, x in enumerate((470, 545, 650, 725)):
        d.rrect(f"pata_{i + 1}", x, 660, 58, 200, 26)
        d.rrect(f"pezuna_{i + 1}", x - 4, 830, 66, 42, 16)
    d.ellipse("cuerpo", 610, 620, 205, 108)
    d.band("cuello", [(520, 600), (440, 420)], 150, 130)
    d.poly("cuerno", [(355, 262), (390, 110), (420, 268)])
    d.band("melena", [(450, 255), (525, 320), (565, 440), (590, 555)], 64, 50)
    d.poly("oreja", [(425, 275), (445, 170), (490, 270)])
    d.ellipse("cabeza", 385, 330, 105, 82, 15)
    d.ellipse("hocico", 300, 390, 66, 56)
    d.line([(370, 215), (405, 200)], 7)
    d.line([(366, 175), (398, 160)], 7)
    d.happy_eye(380, 320, 22)
    d.dot(275, 380, 7)
    d.smile(300, 418, 30, 10)


def extraterrestre(d):
    d.star("estrella_1", 205, 250, 52, 24)
    d.star("estrella_2", 825, 790, 52, 24)
    d.band("antena_izquierda", [(455, 255), (400, 160)], 32)
    d.band("antena_derecha", [(569, 255), (624, 160)], 32)
    d.circle("antena_izquierda_bola", 395, 150, 30)
    d.circle("antena_derecha_bola", 629, 150, 30)
    d.band("brazo_izquierdo", [(400, 600), (315, 540)], 42)
    d.band("brazo_derecho", [(624, 600), (710, 660)], 42)
    d.circle("mano_izquierda", 300, 528, 34)
    d.circle("mano_derecha", 724, 672, 34)
    d.rrect("pierna_izquierda", 440, 760, 50, 92, 20)
    d.rrect("pierna_derecha", 534, 760, 50, 92, 20)
    d.ellipse("pie_izquierdo", 452, 860, 58, 28)
    d.ellipse("pie_derecho", 572, 860, 58, 28)
    d.ellipse("cuerpo", 512, 650, 132, 140)
    d.circle("barriga", 512, 675, 72)
    d.ellipse("cabeza", 512, 385, 205, 150)
    d.ellipse("ojo_izquierdo", 440, 370, 46, 58)
    d.ellipse("ojo_derecho", 584, 370, 46, 58)
    d.eye(448, 382, 24)
    d.eye(576, 382, 24)
    d.smile(512, 465, 40, 16)
