"""Imágenes promocionales de la ficha de Google Play a partir de capturas REALES.

Solo compone: fondo pastel, título y la captura sin retocar dentro de un marco
redondeado. No inventa pantallas ni funciones.

    python3 tools/store_promo.py <carpeta_capturas_telefono>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / 'assets/fonts/Fredoka.ttf'
OUT = ROOT / 'store_assets/promo'
INK = (54, 42, 92)


def font(size, weight=600):
    f = ImageFont.truetype(str(FONT), size)
    try:
        f.set_variation_by_axes([weight, 100])
    except Exception:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def gradient(size, top, bottom):
    w, h = size
    im = Image.new('RGB', size, top)
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return im


def framed(shot, width):
    """La captura con esquinas redondeadas, borde blanco y sombra suave."""
    shot = shot.convert('RGB')
    h = round(shot.height * width / shot.width)
    shot = shot.resize((width, h), Image.LANCZOS)
    r, border = width // 14, max(6, width // 60)
    W, H = width + 2 * border, h + 2 * border
    card = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], r + border, fill=255)
    card.paste((255, 255, 255, 255), (0, 0), mask)
    inner = Image.new('L', (width, h), 0)
    ImageDraw.Draw(inner).rounded_rectangle([0, 0, width - 1, h - 1], r, fill=255)
    card.paste(shot, (border, border), inner)
    shadow = Image.new('RGBA', (W + 80, H + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 52, W + 40, H + 52], r + border, fill=(60, 40, 90, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    shadow.alpha_composite(card, (40, 40))
    return shadow


def centered(d, y, text, f, fill=INK, width=1080):
    for line in text.split('\n'):
        w = d.textlength(line, font=f)
        d.text(((width - w) / 2, y), line, font=f, fill=fill)
        y += f.size * 1.18
    return y


def promo(shot_path, title, subtitle, top, bottom, name):
    im = gradient((1080, 2160), top, bottom).convert('RGBA')
    d = ImageDraw.Draw(im)
    y = centered(d, 120, title, font(92))
    centered(d, y + 20, subtitle, font(46, 500), fill=(90, 80, 120))
    card = framed(Image.open(shot_path), 680)
    im.alpha_composite(card, ((1080 - card.width) // 2, 540))
    small = font(30, 500)
    centered(d, 2160 - 70, 'Captura real de la app', small, fill=(120, 110, 150))
    im.convert('RGB').save(OUT / name, optimize=True)


def feature_graphic():
    im = gradient((1024, 500), (255, 243, 226), (226, 240, 255)).convert('RGBA')
    art = Image.open(ROOT / 'assets/ui/pequenos_artistas_inicio.webp').convert('RGB')
    # La parte de arriba de la ilustración real del inicio (logo, niños y perrito).
    art = art.crop((0, 0, art.width, art.width))
    card = framed(art, 380)
    im.alpha_composite(card, (0, (500 - card.height) // 2 + 6))
    d = ImageDraw.Draw(im)
    d.text((450, 110), 'Pequeños Artistas', font=font(62), fill=INK)
    d.text((452, 200), 'Colorea, juega y\naprende a hablar', font=font(42, 500), fill=(90, 80, 120), spacing=10)
    colors = [(239, 83, 80), (255, 167, 38), (255, 213, 79), (102, 187, 106), (41, 182, 246), (126, 87, 194), (240, 98, 146)]
    for k, c in enumerate(colors):
        x = 456 + k * 52
        d.ellipse([x, 340, x + 36, 376], fill=c, outline='white', width=4)
    im.convert('RGB').save(OUT / 'feature_graphic_1024x500_v2.png', optimize=True)


def main():
    src = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    promo(src / '02_aprendo_a_hablar.png', 'Aprendo a Hablar', 'Palabras, frases, juegos\ny misiones del día',
          (232, 247, 236), (206, 236, 255), 'promo_aprendo_a_hablar_1080x2160.png')
    promo(src / '03b_lolo_respuesta.png', 'Hablemos con Lolo', 'Conversaciones con tarjetas\npara responder',
          (255, 240, 226), (240, 230, 255), 'promo_lolo_1080x2160.png')
    promo(src / '06_tablero_pictogramas.png', 'Quiero decir', 'Pictogramas para formar\nfrases y escucharlas',
          (255, 236, 236), (230, 242, 255), 'promo_tablero_pictogramas_1080x2160.png')
    feature_graphic()


if __name__ == '__main__':
    main()
