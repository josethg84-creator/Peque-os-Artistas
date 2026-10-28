"""Animales: gato, perro, conejo, león, elefante, jirafa, oso, mariposa, pez y tortuga."""

import math

from drawing_lib import mirror


def gato(d):
    d.band("cola", [(640, 820), (770, 790), (810, 690), (770, 610)], 52, 44)
    d.ellipse("cuerpo", 512, 735, 175, 170)
    d.ellipse("barriga", 512, 765, 95, 110)
    d.ellipse("pata_izquierda", 445, 885, 62, 38)
    d.ellipse("pata_derecha", 579, 885, 62, 38)
    d.poly("oreja_izquierda", [(325, 350), (345, 130), (495, 262)])
    d.poly("oreja_derecha", mirror([(325, 350), (345, 130), (495, 262)]))
    d.poly("oreja_izquierda_interior", [(362, 300), (372, 190), (452, 262)])
    d.poly("oreja_derecha_interior", mirror([(362, 300), (372, 190), (452, 262)]))
    d.ellipse("cabeza", 512, 405, 195, 165)
    d.ellipse("hocico", 512, 480, 78, 52)
    d.eyes(512, 395, 72, 24)
    d.oval_dot(512, 458, 24, 15)
    d.line([(512, 470), (512, 490)])
    d.smile(486, 490, 26, 10)
    d.smile(538, 490, 26, 10)
    for y, dy in ((468, -12), (492, 6)):
        d.line([(410, y), (330, y + dy)], 8)
        d.line([(614, y), (694, y + dy)], 8)


def perro(d):
    d.band("cola", [(650, 790), (760, 730), (800, 640)], 48, 40)
    d.ellipse("cuerpo", 512, 745, 175, 160)
    d.ellipse("barriga", 512, 775, 92, 102)
    d.ellipse("pata_izquierda", 445, 888, 62, 38)
    d.ellipse("pata_derecha", 579, 888, 62, 38)
    d.rrect("collar", 400, 560, 224, 52, 26)
    d.circle("placa", 512, 628, 28)
    d.ellipse("cabeza", 512, 405, 185, 165)
    d.ellipse("mancha_ojo", 590, 382, 66, 60)
    pts = [(392, 268), (300, 290), (262, 410), (290, 540), (352, 552), (382, 450), (406, 330)]
    d.blob("oreja_izquierda", pts)
    d.blob("oreja_derecha", mirror(pts))
    d.blob("lengua", [(484, 528), (540, 528), (544, 580), (512, 604), (480, 580)])
    d.ellipse("hocico", 512, 490, 88, 58)
    d.ellipse("nariz", 512, 462, 36, 24)
    d.eyes(512, 390, 74, 24)
    d.line([(512, 486), (512, 506)])
    d.smile(484, 506, 28, 10)
    d.smile(540, 506, 28, 10)


def conejo(d):
    d.ellipse("oreja_izquierda", 438, 250, 48, 135, -10)
    d.ellipse("oreja_derecha", 586, 250, 48, 135, 10)
    d.ellipse("oreja_izquierda_interior", 440, 262, 23, 95, -10)
    d.ellipse("oreja_derecha_interior", 584, 262, 23, 95, 10)
    d.circle("cola", 685, 800, 44)
    d.ellipse("cuerpo", 512, 745, 165, 165)
    d.ellipse("barriga", 512, 775, 95, 105)
    d.ellipse("pata_izquierda", 430, 898, 68, 34)
    d.ellipse("pata_derecha", 594, 898, 68, 34)
    d.ellipse("brazo_izquierdo", 428, 700, 36, 52, 15)
    d.ellipse("brazo_derecho", 596, 700, 36, 52, -15)
    d.circle("cabeza", 512, 445, 155)
    d.rrect("dientes", 484, 498, 56, 50, 12)
    d.eyes(512, 425, 62, 22)
    d.oval_dot(512, 474, 18, 12)
    d.line([(512, 484), (512, 496)])
    d.smile(490, 494, 22, 6)
    d.smile(534, 494, 22, 6)
    d.line([(512, 502), (512, 544)], 6)


def leon(d):
    d.band("cola", [(660, 820), (790, 800), (838, 700)], 36, 30)
    d.ellipse("punta_cola", 846, 672, 42, 52)
    d.ellipse("cuerpo", 512, 775, 165, 135)
    d.ellipse("pata_izquierda", 440, 895, 60, 34)
    d.ellipse("pata_derecha", 584, 895, 60, 34)
    d.scallop("melena", 512, 405, 225, 215, 16, 0.9)
    d.circle("oreja_izquierda", 380, 265, 56)
    d.circle("oreja_derecha", 644, 265, 56)
    d.circle("oreja_izquierda_interior", 380, 265, 30)
    d.circle("oreja_derecha_interior", 644, 265, 30)
    d.circle("cabeza", 512, 415, 152)
    d.ellipse("hocico", 512, 490, 82, 54)
    d.path(
        "nariz",
        [("M", [(472, 446)]), ("Q", [(512, 436), (552, 446)]), ("Q", [(536, 486), (512, 490)]), ("Q", [(488, 486), (472, 446)])],
        [(472, 436), (552, 490)],
    )
    d.eyes(512, 392, 62, 24)
    d.line([(512, 490), (512, 504)])
    d.smile(488, 504, 24, 9)
    d.smile(536, 504, 24, 9)


def elefante(d):
    ear = [(410, 300), (300, 250), (195, 330), (190, 480), (270, 570), (395, 530)]
    inner = [(395, 330), (310, 300), (240, 360), (240, 470), (295, 520), (380, 495)]
    d.blob("oreja_izquierda", ear)
    d.blob("oreja_derecha", mirror(ear))
    d.blob("oreja_izquierda_interior", inner)
    d.blob("oreja_derecha_interior", mirror(inner))
    d.ellipse("cuerpo", 512, 725, 185, 145)
    d.rrect("pata_izquierda", 395, 790, 95, 125, 34)
    d.rrect("pata_derecha", 534, 790, 95, 125, 34)
    d.ellipse("cabeza", 512, 420, 150, 140)
    d.band("trompa", [(512, 470), (512, 590), (536, 670), (590, 700)], 70, 52)
    d.eyes(512, 400, 55, 22)
    for x in (418, 442, 466, 558, 582, 606):
        d.line([(x - 8, 905), (x, 895), (x + 8, 905)], 7)
    for y in (560, 610):
        d.line([(486, y), (512, y + 8), (538, y)], 7)
    d.smile(452, 500, 22, 8)
    d.smile(572, 500, 22, 8)


def jirafa(d):
    d.band("cola", [(780, 680), (820, 740), (830, 790)], 40, 34)
    d.ellipse("punta_cola", 832, 812, 22, 32)
    for i, x in enumerate((455, 545, 640, 730)):
        d.rrect(f"pata_{i + 1}", x, 730, 60, 190, 26)
        d.rrect(f"pezuna_{i + 1}", x - 4, 880, 68, 42, 16)
    d.ellipse("cuerpo", 600, 690, 200, 105)
    d.band("cuello", [(480, 640), (430, 470), (400, 310)], 100, 82)
    d.blob("melena", [(450, 260), (480, 330), (500, 450), (530, 590), (505, 600), (468, 460), (440, 330)])
    d.band("cuerno_izquierdo", [(355, 230), (345, 130)], 42)
    d.band("cuerno_derecho", [(410, 230), (420, 130)], 42)
    d.circle("cuerno_izquierdo_bola", 345, 112, 28)
    d.circle("cuerno_derecho_bola", 422, 112, 28)
    d.ellipse("oreja", 472, 226, 60, 28, -25)
    d.ellipse("cabeza", 380, 270, 100, 72)
    d.ellipse("hocico", 300, 300, 58, 50)
    for i, (x, y, rx, ry) in enumerate(
        [(540, 670, 42, 34), (640, 640, 38, 30), (720, 700, 36, 30), (620, 740, 40, 28), (460, 720, 28, 26)]
    ):
        d.ellipse(f"mancha_{i + 1}", x, y, rx, ry)
    for i, (x, y, r) in enumerate([(465, 585, 32), (440, 480, 31), (418, 380, 29)]):
        d.circle(f"mancha_cuello_{i + 1}", x, y, r)
    d.eye(370, 250, 20)
    d.dot(275, 285, 7)
    d.smile(290, 320, 26, 10)


def oso(d):
    d.circle("oreja_izquierda", 372, 268, 58)
    d.circle("oreja_derecha", 652, 268, 58)
    d.circle("oreja_izquierda_interior", 372, 268, 30)
    d.circle("oreja_derecha_interior", 652, 268, 30)
    d.ellipse("cuerpo", 512, 745, 185, 165)
    d.ellipse("barriga", 512, 775, 108, 110)
    d.ellipse("brazo_izquierdo", 365, 715, 46, 78, 25)
    d.ellipse("brazo_derecho", 659, 715, 46, 78, -25)
    d.ellipse("pata_izquierda", 420, 880, 70, 48)
    d.ellipse("pata_derecha", 604, 880, 70, 48)
    d.ellipse("planta_izquierda", 420, 885, 36, 26)
    d.ellipse("planta_derecha", 604, 885, 36, 26)
    d.circle("cabeza", 512, 415, 168)
    d.ellipse("hocico", 512, 482, 80, 58)
    d.ellipse("nariz", 512, 458, 36, 24)
    d.eyes(512, 390, 64, 24)
    d.line([(512, 482), (512, 500)])
    d.smile(488, 500, 24, 9)
    d.smile(536, 500, 24, 9)


def mariposa(d):
    up = [(505, 470), (430, 300), (310, 200), (200, 225), (165, 340), (225, 455), (370, 505)]
    low = [(505, 530), (380, 525), (262, 585), (232, 705), (300, 790), (420, 745), (495, 630)]
    d.blob("ala_superior_izquierda", up)
    d.blob("ala_superior_derecha", mirror(up))
    d.blob("ala_inferior_izquierda", low)
    d.blob("ala_inferior_derecha", mirror(low))
    d.circle("mancha_superior_izquierda", 300, 330, 56)
    d.circle("mancha_superior_derecha", 724, 330, 56)
    d.circle("mancha_inferior_izquierda", 345, 665, 44)
    d.circle("mancha_inferior_derecha", 679, 665, 44)
    d.line([(496, 300), (470, 220), (430, 175)])
    d.line([(528, 300), (554, 220), (594, 175)])
    d.circle("antena_izquierda", 424, 168, 24)
    d.circle("antena_derecha", 600, 168, 24)
    d.ellipse("cuerpo", 512, 585, 40, 210)
    d.circle("cabeza", 512, 330, 58)
    d.eyes(512, 322, 22, 11)
    d.smile(512, 348, 18, 7, 8)


def _franja(d, rid, x0, x1, cx=470, cy=512, rx=265, ry=172, n=8):
    """Franja vertical que sigue el contorno del cuerpo elíptico del pez."""
    def y(x):
        return ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    top = [(x, cy - y(x)) for x in xs]
    bottom = [(x, cy + y(x)) for x in reversed(xs)]
    d.poly(rid, top + [(x1 + 12, cy)] + bottom + [(x0 + 12, cy)])


def pez(d):
    d.blob("cola", [(700, 512), (845, 375), (880, 450), (850, 512), (880, 574), (845, 649)])
    d.blob("aleta_superior", [(400, 380), (500, 255), (620, 280), (660, 380)])
    d.blob("aleta_inferior", [(500, 630), (570, 735), (640, 630)])
    d.ellipse("cuerpo", 470, 512, 265, 172)
    _franja(d, "franja_1", 540, 600)
    _franja(d, "franja_2", 655, 700)
    d.blob("aleta_lateral", [(400, 545), (480, 505), (515, 575), (450, 610)])
    d.circle("ojo", 320, 470, 40)
    d.circle("burbuja_1", 175, 330, 34)
    d.circle("burbuja_2", 220, 230, 26)
    d.eye(328, 470, 20)
    d.line([(385, 425), (402, 512), (385, 598)])
    d.smile(255, 545, 30, 12)


def tortuga(d):
    for i, (x, y) in enumerate([(340, 690), (440, 712), (620, 712), (720, 690)]):
        d.ellipse(f"pata_{i + 1}", x, y, 48, 62)
    d.blob("cola", [(770, 630), (850, 645), (875, 668), (770, 690)])
    d.ellipse("cabeza", 238, 545, 92, 80)
    d.arc_shape(
        "caparazon",
        (290, 640),
        [("A", 250, 235, 0, 1, (790, 640))],
        [(290, 405), (790, 640)],
    )
    d.rrect("borde", 270, 620, 540, 54, 27)
    d.blob("placa_central", [(540, 455), (600, 485), (610, 555), (540, 590), (470, 555), (480, 485)])
    d.blob("placa_izquierda", [(400, 520), (440, 545), (430, 595), (370, 600), (350, 555)])
    d.blob("placa_derecha", mirror([(400, 520), (440, 545), (430, 595), (370, 600), (350, 555)], 540))
    d.eye(215, 525, 20)
    d.smile(205, 570, 34, 12)
