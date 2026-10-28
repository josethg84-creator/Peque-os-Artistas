"""Vehículos: automóvil, autobús, avión, tren y barco."""


def automovil(d):
    d.poly("cabina", [(330, 505), (395, 335), (645, 335), (725, 505)])
    d.poly("ventana_trasera", [(405, 362), (505, 362), (505, 490), (358, 490)])
    d.poly("ventana_delantera", [(535, 362), (628, 362), (688, 490), (535, 490)])
    d.rrect("carroceria", 170, 495, 684, 205, 56)
    d.rrect("puerta", 440, 525, 170, 120, 18)
    d.circle("faro", 805, 565, 30)
    d.rrect("luz_trasera", 196, 540, 34, 54, 12)
    d.circle("rueda_trasera", 330, 705, 88)
    d.circle("rueda_delantera", 694, 705, 88)
    d.circle("tapacubos_trasero", 330, 705, 38)
    d.circle("tapacubos_delantero", 694, 705, 38)
    d.line([(560, 585), (590, 585)], 12)


def autobus(d):
    d.rrect("carroceria", 130, 290, 764, 420, 56)
    d.rrect("franja", 130, 530, 764, 64, 0)
    for i, x in enumerate((170, 320, 470, 620)):
        d.rrect(f"ventana_{i + 1}", x, 335, 120, 130, 18)
    d.rrect("parabrisas", 770, 335, 88, 180, 18)
    d.circle("faro", 850, 640, 26)
    d.rrect("luz_trasera", 146, 600, 40, 66, 12)
    d.circle("rueda_trasera", 290, 710, 82)
    d.circle("rueda_delantera", 734, 710, 82)
    d.circle("tapacubos_trasero", 290, 710, 36)
    d.circle("tapacubos_delantero", 734, 710, 36)


def avion(d):
    d.scallop("nube_1", 250, 230, 105, 50, 9, 0.85)
    d.scallop("nube_2", 790, 800, 115, 52, 9, 0.85)
    d.blob("ala_trasera", [(560, 490), (650, 340), (705, 345), (660, 500)])
    d.blob("cola", [(215, 500), (175, 290), (255, 290), (345, 490)])
    d.ellipse("fuselaje", 512, 525, 335, 100)
    d.ellipse("cabina", 768, 492, 52, 36)
    for i, x in enumerate((360, 450, 540, 630)):
        d.circle(f"ventanilla_{i + 1}", x, 505, 30)
    d.blob("estabilizador", [(205, 545), (330, 545), (290, 620), (210, 620)])
    d.blob("ala", [(420, 560), (600, 560), (530, 745), (440, 745)])
    d.smile(810, 560, 26, 10)


def tren(d):
    d.scallop("humo_1", 615, 215, 70, 42, 8, 0.85)
    d.scallop("humo_2", 735, 140, 58, 34, 8, 0.85)
    d.poly("chimenea", [(565, 430), (552, 315), (648, 315), (635, 430)])
    d.rrect("chimenea_borde", 530, 280, 140, 44, 18)
    d.rrect("caldera", 380, 420, 410, 190, 60)
    d.rrect("frente", 770, 440, 50, 150, 18)
    d.rrect("cabina", 190, 330, 210, 290, 20)
    d.rrect("techo", 165, 295, 260, 52, 22)
    d.rrect("ventana_cabina", 228, 380, 134, 105, 16)
    d.rrect("chasis", 170, 600, 650, 54, 24)
    d.poly("quitapiedras", [(820, 605), (880, 700), (820, 700)])
    for i, (x, r) in enumerate([(270, 68), (460, 72), (650, 72)]):
        d.circle(f"rueda_{i + 1}", x, 700, r)
        d.circle(f"centro_rueda_{i + 1}", x, 700, 26)
    d.line([(140, 782), (900, 782)], 12)


def barco(d):
    d.circle("sol", 815, 230, 62)
    for x0, y0, x1, y1 in [(815, 140, 815, 115), (900, 230, 925, 230), (878, 167, 896, 149), (878, 293, 896, 311),
                           (752, 167, 734, 149)]:
        d.line([(x0, y0), (x1, y1)], 12)
    d.poly("vela_grande", [(495, 205), (495, 565), (255, 565)])
    d.poly("vela_pequena", [(540, 255), (540, 565), (720, 565)])
    d.rrect("mastil", 497, 180, 34, 420, 14)
    d.poly("bandera", [(531, 182), (636, 216), (531, 252)])
    d.poly("casco", [(200, 600), (824, 600), (740, 745), (290, 745)])
    d.poly("franja", [(232, 648), (792, 648), (770, 690), (258, 690)])
    d.waves("agua", 110, 914, 742, 880, 8)
