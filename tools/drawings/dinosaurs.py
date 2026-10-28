"""Dinosaurios amigables (diseños originales)."""

import math


def rex(d):
    """dinosaurio_01: pequeño rex sonriente."""
    d.rrect("pierna_trasera", 560, 690, 66, 150, 30)
    d.ellipse("pie_trasero", 610, 848, 70, 30)
    d.band("cola", [(420, 680), (290, 730), (180, 700), (130, 620)], 140, 44)
    d.band("cuello", [(555, 585), (645, 465)], 175)
    d.ellipse("cuerpo", 490, 640, 185, 150, -15)
    d.blob("cabeza", [(560, 390), (650, 310), (790, 320), (850, 390), (830, 490), (700, 520), (590, 490)])
    d.ellipse("barriga", 550, 670, 85, 105, -15)
    d.band("brazo", [(630, 590), (690, 615), (705, 650)], 36, 30)
    d.rrect("pierna", 400, 700, 80, 150, 34)
    d.ellipse("pie", 452, 855, 84, 32)
    d.circle("mancha_1", 410, 580, 32)
    d.circle("mancha_2", 345, 650, 32)
    d.eye(700, 380, 24)
    d.dot(825, 370, 7)
    d.smile(770, 450, 50, 18)


def triceratops(d):
    d.rrect("pata_trasera_2", 700, 680, 74, 175, 30)
    d.rrect("pata_delantera_2", 460, 680, 74, 175, 30)
    d.band("cola", [(780, 620), (860, 660), (900, 720)], 80, 26)
    d.ellipse("cuerpo", 590, 615, 230, 150)
    d.rrect("pata_delantera", 390, 700, 80, 180, 32)
    d.rrect("pata_trasera", 640, 700, 80, 180, 32)
    d.scallop("gola", 340, 470, 128, 128, 11, 0.85)
    d.poly("cuerno_1", [(262, 445), (342, 455), (232, 295)])
    d.poly("cuerno_2", [(335, 430), (405, 452), (338, 280)])
    d.ellipse("cabeza", 290, 520, 128, 90)
    d.poly("cuerno_nariz", [(172, 505), (222, 468), (128, 418)])
    d.circle("mancha_1", 560, 560, 36)
    d.circle("mancha_2", 660, 520, 28)
    d.circle("mancha_3", 700, 620, 30)
    d.eye(285, 495, 22)
    d.smile(220, 555, 40, 14)


def estegosaurio(d):
    for i, (x, y, a) in enumerate([(310, 530, -40), (395, 465, -20), (495, 440, 0), (595, 455, 18), (680, 505, 38)]):
        r = math.radians(a)
        ux, uy = math.sin(r), -math.cos(r)
        nx, ny = math.cos(r), math.sin(r)
        h, w = 115, 52
        d.blob(
            f"placa_{i + 1}",
            [(x - nx * w, y - ny * w), (x + ux * h * 0.6 - nx * w * 0.8, y + uy * h * 0.6 - ny * w * 0.8),
             (x + ux * h, y + uy * h), (x + ux * h * 0.6 + nx * w * 0.8, y + uy * h * 0.6 + ny * w * 0.8),
             (x + nx * w, y + ny * w)],
        )
    d.rrect("pata_trasera_2", 330, 650, 70, 170, 30)
    d.rrect("pata_delantera_2", 590, 650, 70, 170, 30)
    d.poly("pua_1", [(150, 605), (125, 500), (215, 590)])
    d.poly("pua_2", [(220, 620), (240, 505), (300, 615)])
    d.band("cola", [(300, 640), (200, 640), (130, 580)], 90, 34)
    d.ellipse("cuerpo", 500, 610, 240, 140)
    d.band("cuello", [(690, 620), (770, 600)], 100)
    d.ellipse("cabeza", 810, 590, 92, 66)
    d.rrect("pata_trasera", 380, 680, 76, 180, 32)
    d.rrect("pata_delantera", 630, 680, 76, 180, 32)
    d.circle("mancha_1", 450, 580, 34)
    d.circle("mancha_2", 560, 560, 26)
    d.eye(820, 570, 20)
    d.smile(850, 615, 30, 12)


def braquiosaurio(d):
    d.rrect("pata_trasera_2", 340, 720, 70, 170, 30)
    d.rrect("pata_delantera_2", 540, 720, 70, 170, 30)
    d.band("cola", [(280, 700), (170, 730), (115, 670)], 90, 30)
    d.band("cuello", [(560, 640), (650, 440), (680, 270)], 110, 80)
    d.ellipse("cuerpo", 450, 680, 220, 130)
    d.ellipse("cabeza", 715, 240, 100, 64)
    d.rrect("pata_trasera", 290, 740, 78, 170, 32)
    d.rrect("pata_delantera", 500, 740, 78, 170, 32)
    d.circle("mancha_1", 400, 640, 36)
    d.circle("mancha_2", 500, 610, 26)
    d.circle("mancha_3", 600, 525, 30)
    d.circle("mancha_4", 640, 425, 30)
    d.eye(725, 220, 20)
    d.dot(800, 220, 6)
    d.smile(760, 262, 34, 12)


def bebe_huevo(d):
    d.ellipse("cuerpo", 512, 600, 140, 130)
    d.ellipse("cabeza", 512, 430, 155, 130)
    zig = [(300, 600), (345, 560), (390, 605), (435, 560), (480, 605), (525, 560), (570, 605), (615, 560),
           (660, 605), (700, 565), (724, 600)]
    d.arc_shape(
        "cascara_inferior",
        zig[0],
        [("L", p) for p in zig[1:]] + [("A", 212, 280, 0, 1, (300, 600))],
        [(300, 560), (724, 880)],
    )
    top = [(640, 300), (610, 330), (580, 300), (550, 332), (520, 300), (490, 332), (460, 300), (430, 330),
           (400, 300)]
    d.arc_shape("cascara_superior", top[0], [("L", p) for p in top[1:]] + [("A", 120, 105, 0, 0, (640, 300))],
                [(400, 195), (640, 332)])
    d.ellipse("mano_izquierda", 362, 585, 46, 30)
    d.ellipse("mano_derecha", 662, 585, 46, 30)
    d.circle("mancha_1", 430, 760, 36)
    d.circle("mancha_2", 610, 720, 32)
    d.circle("mancha_3", 560, 830, 26)
    d.eyes(512, 430, 60, 24)
    d.smile(512, 485, 38, 16)
