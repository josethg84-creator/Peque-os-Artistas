"""Mini-librería para construir dibujos para colorear en SVG.

Cada dibujo se compone de:
  * regiones: trazados cerrados (<path> terminado en Z) con id único, relleno
    blanco y contorno negro grueso. Son las zonas que el niño puede colorear.
    Se dibujan en orden (de atrás hacia adelante): la región visible en un
    punto es la ÚLTIMA que lo contiene.
  * detalles: trazos negros decorativos (ojos, sonrisas, bigotes...). No son
    rellenables y no deben capturar toques (pointer-events="none").

Todas las coordenadas se escriben sobre un lienzo de 1024 x 1024. Al exportar,
el dibujo se escala y se centra automáticamente dentro del área segura
(márgenes de MARGIN px) sin usar atributos transform, para que cualquier
parser de trazados SVG pueda leer las regiones directamente.
"""

import math

CANVAS = 1024
MARGIN = 104
REGION_STROKE = 14
DETAIL_STROKE = 10
BLACK = "#000000"
WHITE = "#FFFFFF"


def _f(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def _catmull_closed(pts):
    n = len(pts)
    segs = []
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((c1, c2, p2))
    return segs


def _catmull_open(pts):
    ext = [pts[0]] + list(pts) + [pts[-1]]
    segs = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, c1, c2, p2))
    return segs


def _bez(p0, c1, c2, p3, t):
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p3[1],
    )


def mirror(pts, axis=512):
    """Refleja una lista de puntos respecto a la vertical x = axis."""
    return [(2 * axis - x, y) for x, y in pts]


class Drawing:
    def __init__(self, s=1.0, dx=0.0, dy=0.0):
        self.s, self.dx, self.dy = s, dx, dy
        self.regions = []  # (id, d)
        self.details = []  # (kind, d, extra)
        self.bbox = [math.inf, math.inf, -math.inf, -math.inf]

    # ---- utilidades internas -------------------------------------------
    def _ext(self, x0, y0, x1, y1):
        b = self.bbox
        b[0], b[1] = min(b[0], x0), min(b[1], y0)
        b[2], b[3] = max(b[2], x1), max(b[3], y1)

    def _ext_pts(self, pts, pad=0):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self._ext(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def P(self, x, y):
        return f"{_f(x * self.s + self.dx)},{_f(y * self.s + self.dy)}"

    def L(self, v):
        return _f(v * self.s)

    def _add(self, rid, d):
        if any(r[0] == rid for r in self.regions):
            raise ValueError(f"id de región duplicado: {rid}")
        self.regions.append((rid, d))

    # ---- regiones (zonas rellenables) ----------------------------------
    def ellipse(self, rid, cx, cy, rx, ry, rot=0):
        a = math.radians(rot)
        ex, ey = rx * math.cos(a), rx * math.sin(a)
        r = max(rx, ry)
        self._ext(cx - r, cy - r, cx + r, cy + r)
        p1, p2 = self.P(cx + ex, cy + ey), self.P(cx - ex, cy - ey)
        arc = f"A{self.L(rx)},{self.L(ry)} {_f(rot)} 0 1"
        self._add(rid, f"M{p1} {arc} {p2} {arc} {p1}Z")

    def circle(self, rid, cx, cy, r):
        self.ellipse(rid, cx, cy, r, r)

    def rrect(self, rid, x, y, w, h, r=20):
        r = min(r, w / 2, h / 2)
        self._ext(x, y, x + w, y + h)
        a = f"A{self.L(r)},{self.L(r)} 0 0 1"
        d = (
            f"M{self.P(x + r, y)} L{self.P(x + w - r, y)} {a} {self.P(x + w, y + r)} "
            f"L{self.P(x + w, y + h - r)} {a} {self.P(x + w - r, y + h)} "
            f"L{self.P(x + r, y + h)} {a} {self.P(x, y + h - r)} "
            f"L{self.P(x, y + r)} {a} {self.P(x + r, y)}Z"
        )
        self._add(rid, d)

    def poly(self, rid, pts):
        """Polígono de lados rectos (las esquinas se ven redondeadas por el contorno)."""
        self._ext_pts(pts)
        d = "M" + " L".join(self.P(*p) for p in pts) + "Z"
        self._add(rid, d)

    def blob(self, rid, pts):
        """Forma orgánica: curva suave cerrada que pasa por los puntos."""
        self._ext_pts(pts, pad=12)
        d = f"M{self.P(*pts[0])}"
        for c1, c2, p in _catmull_closed(pts):
            d += f" C{self.P(*c1)} {self.P(*c2)} {self.P(*p)}"
        self._add(rid, d + "Z")

    def path(self, rid, cmds, bbox_pts):
        """Trazado libre. cmds: lista de (comando, [puntos]) con comandos M L Q C.
        bbox_pts: puntos que acotan la forma (para el centrado)."""
        self._ext_pts(bbox_pts)
        d = " ".join(c + " ".join(self.P(*p) for p in ps) for c, ps in cmds)
        self._add(rid, d + "Z")

    def arc_shape(self, rid, start, segments, bbox_pts):
        """Trazado con arcos: segments = lista de ('L', p) o ('A', rx, ry, large, sweep, p)."""
        self._ext_pts(bbox_pts)
        d = f"M{self.P(*start)}"
        for seg in segments:
            if seg[0] == "L":
                d += f" L{self.P(*seg[1])}"
            else:
                _, rx, ry, large, sweep, p = seg
                d += f" A{self.L(rx)},{self.L(ry)} 0 {large} {sweep} {self.P(*p)}"
        self._add(rid, d + "Z")

    def band(self, rid, pts, w0, w1=None, steps=24):
        """Banda gruesa con extremos redondeados siguiendo una curva suave
        (colas, cuellos, brazos, trompas...). w0/w1 = grosor inicial/final."""
        w1 = w0 if w1 is None else w1
        samples = []
        for p0, c1, c2, p3 in _catmull_open(pts):
            for k in range(steps):
                samples.append(_bez(p0, c1, c2, p3, k / steps))
        samples.append(pts[-1])
        n = len(samples)
        left, right = [], []
        for i, (x, y) in enumerate(samples):
            a = samples[max(i - 1, 0)]
            b = samples[min(i + 1, n - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty) or 1
            nx, ny = -ty / ln, tx / ln
            hw = (w0 + (w1 - w0) * i / (n - 1)) / 2
            left.append((x + nx * hw, y + ny * hw))
            right.append((x - nx * hw, y - ny * hw))
        self._ext_pts(left + right, pad=max(w0, w1) / 2)
        d = f"M{self.P(*left[0])} " + " ".join(f"L{self.P(*p)}" for p in left[1:])
        d += f" A{self.L(w1 / 2)},{self.L(w1 / 2)} 0 0 0 {self.P(*right[-1])} "
        d += " ".join(f"L{self.P(*p)}" for p in reversed(right[:-1]))
        d += f" A{self.L(w0 / 2)},{self.L(w0 / 2)} 0 0 0 {self.P(*left[0])}Z"
        self._add(rid, d)

    def scallop(self, rid, cx, cy, rx, ry, n, bulge=1.0, phase=0):
        """Contorno ondulado (melena, nubes, golas): arcos hacia afuera."""
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n + math.radians(phase)
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        chord = math.dist(pts[0], pts[1])
        r = chord / 2 / bulge
        self._ext(cx - rx - chord / 2, cy - ry - chord / 2, cx + rx + chord / 2, cy + ry + chord / 2)
        d = f"M{self.P(*pts[0])}"
        for i in range(1, n + 1):
            d += f" A{self.L(r)},{self.L(r)} 0 0 1 {self.P(*pts[i % n])}"
        self._add(rid, d + "Z")

    def star(self, rid, cx, cy, r_out, r_in=None, n=5, rot=-90):
        r_in = r_out * 0.5 if r_in is None else r_in
        pts = []
        for i in range(2 * n):
            r = r_out if i % 2 == 0 else r_in
            a = math.radians(rot + 180 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.poly(rid, pts)

    def heart(self, rid, cx, cy, w):
        """Corazón de ancho w centrado en (cx, cy)."""
        h = w * 0.9
        top = cy - h * 0.25
        cmds = [
            ("M", [(cx, top)]),
            ("C", [(cx - w * 0.1, top - h * 0.35), (cx - w * 0.55, top - h * 0.3), (cx - w * 0.5, top + h * 0.1)]),
            ("C", [(cx - w * 0.45, top + h * 0.45), (cx - w * 0.1, top + h * 0.6), (cx, cy + h * 0.5)]),
            ("C", [(cx + w * 0.1, top + h * 0.6), (cx + w * 0.45, top + h * 0.45), (cx + w * 0.5, top + h * 0.1)]),
            ("C", [(cx + w * 0.55, top - h * 0.3), (cx + w * 0.1, top - h * 0.35), (cx, top)]),
        ]
        self.path(rid, cmds, [(cx - w / 2, top - h * 0.3), (cx + w / 2, cy + h * 0.5)])

    def waves(self, rid, x0, x1, y_top, y_bottom, n):
        """Franja de agua con borde superior ondulado."""
        step = (x1 - x0) / n
        segs = []
        for i in range(1, n + 1):
            segs.append(("A", step / 2, step / 2.6, 0, 1, (x0 + i * step, y_top)))
        segs += [("L", (x1, y_bottom)), ("L", (x0, y_bottom))]
        self.arc_shape(rid, (x0, y_top), segs, [(x0, y_top - step / 2.6), (x1, y_bottom)])

    def leaf(self, rid, base, tip, width):
        """Hoja simétrica entre base y punta."""
        bx, by = base
        tx, ty = tip
        ln = math.dist(base, tip)
        nx, ny = -(ty - by) / ln, (tx - bx) / ln
        m1 = (bx + (tx - bx) * 0.3 + nx * width, by + (ty - by) * 0.3 + ny * width)
        m2 = (bx + (tx - bx) * 0.7 + nx * width, by + (ty - by) * 0.7 + ny * width)
        m3 = (bx + (tx - bx) * 0.7 - nx * width, by + (ty - by) * 0.7 - ny * width)
        m4 = (bx + (tx - bx) * 0.3 - nx * width, by + (ty - by) * 0.3 - ny * width)
        cmds = [("M", [base]), ("C", [m1, m2, tip]), ("C", [m3, m4, base])]
        self.path(rid, cmds, [base, tip, m1, m2, m3, m4])

    # ---- detalles (no rellenables) -------------------------------------
    def line(self, pts, w=DETAIL_STROKE):
        """Trazo abierto suave."""
        self._ext_pts(pts)
        if len(pts) == 2:
            d = f"M{self.P(*pts[0])} L{self.P(*pts[1])}"
        else:
            d = f"M{self.P(*pts[0])}"
            for _, c1, c2, p in _catmull_open(pts):
                d += f" C{self.P(*c1)} {self.P(*c2)} {self.P(*p)}"
        self.details.append(("stroke", d, w))

    def smile(self, cx, cy, w, h, lw=DETAIL_STROKE):
        self._ext(cx - w, cy, cx + w, cy + h)
        d = f"M{self.P(cx - w, cy)} Q{self.P(cx, cy + 2 * h)} {self.P(cx + w, cy)}"
        self.details.append(("stroke", d, lw))

    def happy_eye(self, cx, cy, w, lw=DETAIL_STROKE):
        """Ojo cerrado y sonriente (arco hacia arriba)."""
        d = f"M{self.P(cx - w, cy)} Q{self.P(cx, cy - w * 1.3)} {self.P(cx + w, cy)}"
        self.details.append(("stroke", d, lw))

    def dot(self, cx, cy, r):
        """Punto negro macizo (pupilas, fosas nasales, semillas)."""
        self._ext(cx - r, cy - r, cx + r, cy + r)
        a = f"A{self.L(r)},{self.L(r)} 0 1 1"
        d = f"M{self.P(cx - r, cy)} {a} {self.P(cx + r, cy)} {a} {self.P(cx - r, cy)}Z"
        self.details.append(("fill", d, None))

    def oval_dot(self, cx, cy, rx, ry, rot=0):
        a = math.radians(rot)
        ex, ey = rx * math.cos(a), rx * math.sin(a)
        arc = f"A{self.L(rx)},{self.L(ry)} {_f(rot)} 0 1"
        p1, p2 = self.P(cx + ex, cy + ey), self.P(cx - ex, cy - ey)
        self.details.append(("fill", f"M{p1} {arc} {p2} {arc} {p1}Z", None))

    def eye(self, cx, cy, r):
        """Ojo infantil: pupila negra con brillo blanco."""
        self.dot(cx, cy, r)
        k = r * 0.38
        a = f"A{self.L(k)},{self.L(k)} 0 1 1"
        hx, hy = cx + r * 0.32, cy - r * 0.32
        d = f"M{self.P(hx - k, hy)} {a} {self.P(hx + k, hy)} {a} {self.P(hx - k, hy)}Z"
        self.details.append(("white", d, None))

    def eyes(self, cx, cy, gap, r):
        self.eye(cx - gap, cy, r)
        self.eye(cx + gap, cy, r)

    # ---- exportación ---------------------------------------------------
    def to_svg(self, drawing_id):
        out = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f"<!-- Pequeños Artistas - {drawing_id}. Ilustración original creada para el proyecto. -->",
            f'<svg xmlns="http://www.w3.org/2000/svg" id="{drawing_id}" width="{CANVAS}" height="{CANVAS}" '
            f'viewBox="0 0 {CANVAS} {CANVAS}">',
            '  <g id="regiones">',
            f'    <path id="fondo" class="region" fill="{WHITE}" stroke="none" '
            f'd="M0,0 L{CANVAS},0 L{CANVAS},{CANVAS} L0,{CANVAS}Z"/>',
        ]
        for rid, d in self.regions:
            out.append(
                f'    <path id="{rid}" class="region" fill="{WHITE}" stroke="{BLACK}" '
                f'stroke-width="{REGION_STROKE}" stroke-linejoin="round" stroke-linecap="round" d="{d}"/>'
            )
        out.append("  </g>")
        out.append('  <g id="detalles" pointer-events="none">')
        for kind, d, w in self.details:
            if kind == "stroke":
                out.append(
                    f'    <path class="detalle" fill="none" stroke="{BLACK}" stroke-width="{w}" '
                    f'stroke-linecap="round" stroke-linejoin="round" d="{d}"/>'
                )
            elif kind == "fill":
                out.append(f'    <path class="detalle" fill="{BLACK}" stroke="none" d="{d}"/>')
            else:
                out.append(f'    <path class="detalle" fill="{WHITE}" stroke="none" d="{d}"/>')
        out.append("  </g>")
        out.append("</svg>")
        return "\n".join(out) + "\n"


def build(func, max_scale=1.25):
    """Dibuja dos veces: la primera mide, la segunda escala y centra."""
    probe = Drawing()
    func(probe)
    x0, y0, x1, y1 = probe.bbox
    # El contorno grueso sobresale media línea de cada forma.
    pad = REGION_STROKE / 2
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    avail = CANVAS - 2 * MARGIN
    s = min(avail / (x1 - x0), avail / (y1 - y0), max_scale)
    dx = CANVAS / 2 - s * (x0 + x1) / 2
    dy = CANVAS / 2 - s * (y0 + y1) / 2
    final = Drawing(s, dx, dy)
    func(final)
    return final
