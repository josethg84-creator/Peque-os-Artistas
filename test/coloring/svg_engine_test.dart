import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/engine/svg_path_parser.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';

String svgWith(String regions, {String details = '', String viewBox = '0 0 1024 1024'}) =>
    '''<?xml version="1.0" encoding="UTF-8"?>
<!-- prueba -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="$viewBox">
  <g id="regiones">
    <path id="fondo" class="region" fill="#FFFFFF" stroke="none" d="M0,0 L1024,0 L1024,1024 L0,1024Z"/>
    $regions
  </g>
  <g id="detalles" pointer-events="none">$details</g>
</svg>''';

String region(String id, String d) =>
    '<path id="$id" class="region" fill="#FFFFFF" stroke="#000000" stroke-width="14" d="$d"/>';

void main() {
  group('Trazados SVG', () {
    test('líneas absolutas y relativas, H y V', () {
      final abs = parseSvgPathData('M10,10 L110,10 L110,110 L10,110Z');
      final rel = parseSvgPathData('m10 10 h100 v100 h-100 z');
      for (final p in [abs, rel]) {
        expect(p.contains(const Offset(60, 60)), isTrue);
        expect(p.contains(const Offset(120, 60)), isFalse);
        expect(p.getBounds(), const Rect.fromLTRB(10, 10, 110, 110));
      }
    });

    test('arcos: dos medias elipses forman una elipse completa', () {
      final p = parseSvgPathData('M300,200 A100,50 0 0 1 100,200 A100,50 0 0 1 300,200Z');
      expect(p.contains(const Offset(200, 200)), isTrue);
      expect(p.contains(const Offset(290, 200)), isTrue);
      expect(p.contains(const Offset(200, 260)), isFalse);
      final b = p.getBounds();
      expect(b.left, closeTo(100, 0.5));
      expect(b.right, closeTo(300, 0.5));
      expect(b.top, closeTo(150, 0.5));
      expect(b.bottom, closeTo(250, 0.5));
    });

    test('arco con rotación y números compactos', () {
      final p = parseSvgPathData('M0,0L1e2,0 A50,25 30 01 0,0Z');
      expect(p.getBounds().width, greaterThan(90));
    });

    test('curvas cúbicas y cuadráticas (también S y T)', () {
      final c = parseSvgPathData('M0,100 C0,0 200,0 200,100 S400,200 400,100 Z');
      final q = parseSvgPathData('M0,100 Q100,0 200,100 T400,100 Z');
      expect(c.getBounds().right, closeTo(400, 0.5));
      expect(q.getBounds().right, closeTo(400, 0.5));
    });

    test('datos inválidos lanzan DrawingFormatException', () {
      for (final bad in ['', '   ', '10 10', 'M10', 'M0,0 A10,10 0 2 1 5,5', 'M0,0 L1,x']) {
        expect(() => parseSvgPathData(bad), throwsA(isA<DrawingFormatException>()), reason: bad);
      }
    });
  });

  group('Lectura del SVG de coloreado', () {
    test('lee regiones en orden, contornos y detalles', () {
      final d = parseColoringSvg(
        svgWith(
          region('a', 'M100,100 L500,100 L500,500 L100,500Z') +
              region('b', 'M300,300 L700,300 L700,700 L300,700Z'),
          details:
              '<path class="detalle" fill="#000000" stroke="none" d="M0,0 L10,0 L10,10Z"/>'
              '<path class="detalle" fill="none" stroke="#000000" stroke-width="10" d="M0,0 L50,50"/>',
        ),
      );
      expect(d.regions.map((r) => r.id), ['fondo', 'a', 'b']);
      expect(d.region('a')!.strokeWidth, 14);
      expect(d.region('fondo')!.strokeColor, isNull);
      expect(d.details.map((e) => e.kind), [DetailKind.fill, DetailKind.stroke]);
      expect(d.viewBox, const Rect.fromLTWH(0, 0, 1024, 1024));
    });

    test('la región visible es la última que contiene el punto', () {
      final d = parseColoringSvg(
        svgWith(
          region('a', 'M100,100 L500,100 L500,500 L100,500Z') +
              region('b', 'M300,300 L700,300 L700,700 L300,700Z'),
        ),
      );
      expect(d.regionAt(const Offset(200, 200)), 'a');
      expect(d.regionAt(const Offset(400, 400)), 'b'); // b tapa a a.
      expect(d.regionAt(const Offset(900, 900)), 'fondo');
      expect(d.regionAt(const Offset(2000, 2000)), isNull);
    });

    test('rechaza ids duplicados, regiones abiertas, transform y elementos extraños', () {
      final cases = {
        'duplicado': svgWith(region('a', 'M0,0 L9,0 L9,9Z') + region('a', 'M0,0 L9,0 L9,9Z')),
        'abierta': svgWith(region('a', 'M0,0 L9,0 L9,9')),
        'transform': svgWith(
          '<path id="a" class="region" fill="#FFFFFF" transform="scale(2)" d="M0,0 L9,0 L9,9Z"/>',
        ),
        'rect': svgWith('<rect id="a" width="10" height="10"/>'),
        'sin id': svgWith('<path class="region" fill="#FFFFFF" d="M0,0 L9,0 L9,9Z"/>'),
        'color': svgWith('<path id="a" class="region" fill="url(#g)" d="M0,0 L9,0 L9,9Z"/>'),
        'viewBox': svgWith('', viewBox: '0 0 0 1024'),
        'no svg': '<html></html>',
      };
      cases.forEach((name, svg) {
        expect(() => parseColoringSvg(svg), throwsA(isA<DrawingFormatException>()), reason: name);
      });
    });

    test('tolerancia: un toque junto a una figura pequeña la elige; lejos, el fondo', () {
      final d = parseColoringSvg(
        svgWith(region('punto', 'M532,512 A20,20 0 0 1 492,512 A20,20 0 0 1 532,512Z')),
      );
      expect(d.hitTest(const Offset(512, 512)), 'punto');
      expect(d.hitTest(const Offset(542, 512)), 'fondo'); // sin tolerancia
      expect(d.hitTest(const Offset(542, 512), tolerance: 24), 'punto');
      expect(d.hitTest(const Offset(700, 512), tolerance: 24), 'fondo');
    });

    test('la tolerancia nunca cambia un toque que ya acierta en una figura', () {
      final d = parseColoringSvg(
        svgWith(
          region('a', 'M100,100 L500,100 L500,500 L100,500Z') +
              region('b', 'M505,100 L900,100 L900,500 L505,500Z'),
        ),
      );
      expect(d.hitTest(const Offset(498, 300), tolerance: 40), 'a');
      expect(d.hitTest(const Offset(507, 300), tolerance: 40), 'b');
    });
  });
}
