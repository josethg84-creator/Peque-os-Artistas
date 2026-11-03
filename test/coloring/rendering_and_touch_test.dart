import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/coloring_canvas.dart';
import 'package:pequenos_artistas/coloring/coloring_controller.dart';
import 'package:pequenos_artistas/coloring/engine/drawing_painter.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/models/drawing.dart';
import 'package:pequenos_artistas/models/drawing_category.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';

import '../test_helpers.dart';

/// Dos cuadrados que comparten un borde (x = 500) y un círculo pequeño.
const twoSquares = '''<svg viewBox="0 0 1024 1024">
<g id="regiones">
<path id="fondo" class="region" fill="#FFFFFF" stroke="none" d="M0,0 L1024,0 L1024,1024 L0,1024Z"/>
<path id="a" class="region" fill="#FFFFFF" stroke="#000000" stroke-width="14" d="M100,100 L500,100 L500,900 L100,900Z"/>
<path id="b" class="region" fill="#FFFFFF" stroke="#000000" stroke-width="14" d="M500,100 L900,100 L900,900 L500,900Z"/>
<path id="punto" class="region" fill="#FFFFFF" stroke="#000000" stroke-width="14" d="M720,960 A16,16 0 0 1 688,960 A16,16 0 0 1 720,960Z"/>
</g>
<g id="detalles"></g>
</svg>''';

const red = Color(0xFFE53935);

/// Renderiza el dibujo a [size] px y devuelve una función para leer píxeles.
Future<Color Function(int x, int y)> render(VectorDrawing d, Map<String, Color> colors, int size) async {
  final recorder = ui.PictureRecorder();
  DrawingPainter(
    drawing: d,
    colors: FixedRegionColors(colors),
  ).paint(Canvas(recorder), Size.square(size.toDouble()));
  final image = await recorder.endRecording().toImage(size, size);
  final bytes = (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!;
  return (x, y) {
    final i = (y * size + x) * 4;
    return Color.fromARGB(255, bytes.getUint8(i), bytes.getUint8(i + 1), bytes.getUint8(i + 2));
  };
}

bool isBlack(Color c) => c.r < 0.2 && c.g < 0.2 && c.b < 0.2;
bool isWhite(Color c) => c.r > 0.95 && c.g > 0.95 && c.b > 0.95;
bool isRed(Color c) => c.r > 0.8 && c.g < 0.35 && c.b < 0.35;

Drawing catalogEntry(String id, String file) => Drawing(
  id: id,
  name: 'Prueba',
  category: DrawingCategory.animals,
  file: file,
  difficulty: Difficulty.easy,
  recommendedAge: '4-5',
  description: '',
);

void main() {
  group('3. Los contornos permanecen visibles', () {
    testWidgets('pintar una región no tapa su contorno ni el de la vecina', (tester) async {
      final d = parseColoringSvg(twoSquares);
      await tester.runAsync(() async {
        final px = await render(d, {'a': red}, 1024);
        expect(isRed(px(300, 500)), isTrue, reason: 'interior de a pintado');
        expect(isWhite(px(700, 500)), isTrue, reason: 'b sigue blanca');
        expect(isWhite(px(50, 50)), isTrue, reason: 'el fondo sigue blanco');
        for (final (x, y) in [(500, 500), (100, 500), (300, 100), (300, 900), (497, 300), (503, 300)]) {
          expect(isBlack(px(x, y)), isTrue, reason: 'contorno en ($x, $y)');
        }
      });
    });

    testWidgets('en un dibujo real, pintar todas las regiones conserva todos los trazos negros', (
      tester,
    ) async {
      final d = parseColoringSvg(File('assets/drawings/animals/animal_gato.svg').readAsStringSync());
      await tester.runAsync(() async {
        const size = 512;
        int countBlack(Color Function(int, int) px) {
          var n = 0;
          for (var y = 0; y < size; y++) {
            for (var x = 0; x < size; x++) {
              if (isBlack(px(x, y))) n++;
            }
          }
          return n;
        }

        final blank = countBlack(await render(d, {}, size));
        final painted = await render(d, {for (final r in d.regions) r.id: red}, size);
        expect(blank, greaterThan(5000));
        // Los trazos negros siguen ahí (el rojo no se cuenta como negro).
        expect(countBlack(painted), closeTo(blank, blank * 0.01));
      });
    });
  });

  group('10-11. Coordenadas táctiles, tamaños y límites', () {
    Future<ColoringController> pumpCanvas(
      WidgetTester tester,
      Size size, {
      String file = 'mem/two.svg',
    }) async {
      final controller = ColoringController(
        drawingId: 'prueba',
        file: file,
        loader: diskDrawingLoader({'mem/two.svg': twoSquares}),
        store: InMemoryCreationStore(),
        saveDelay: Duration.zero,
      )..selectColor(kidPalette.first);
      await controller.load();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Align(
              alignment: Alignment.topLeft,
              child: SizedBox.fromSize(
                size: size,
                child: ColoringCanvas(drawing: catalogEntry('prueba', file), controller: controller),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      addTearDown(controller.dispose);
      return controller;
    }

    for (final size in const [Size(300, 300), Size(700, 450), Size(360, 640), Size(1200, 900)]) {
      testWidgets('lienzo de ${size.width.toInt()}×${size.height.toInt()}: cada toque pinta su región', (
        tester,
      ) async {
        setScreenSize(tester, const Size(1300, 1000));
        final c = await pumpCanvas(tester, size);
        final d = c.drawing!;
        // El dibujo se mantiene cuadrado (sin deformarse).
        final rect = tester.getRect(drawingCanvasFinder);
        expect(rect.width, closeTo(rect.height, 1));

        await tester.tapAt(screenPointOf(tester, d, const Offset(300, 500)));
        expect(c.regionColors.keys, ['a']);
        await tester.tapAt(screenPointOf(tester, d, const Offset(700, 300)));
        expect(c.regionColors.keys, unorderedEquals(['a', 'b']));
        await tester.tapAt(screenPointOf(tester, d, const Offset(40, 40)));
        expect(c.regionColors.keys, unorderedEquals(['a', 'b', 'fondo']));
        await tester.pump(const Duration(seconds: 1));
      });
    }

    testWidgets('un toque justo en el borde compartido pinta una sola región', (tester) async {
      final c = await pumpCanvas(tester, const Size(500, 500));
      await tester.tapAt(screenPointOf(tester, c.drawing!, const Offset(500, 500)));
      expect(c.regionColors, hasLength(1));
      expect(c.regionColors.keys.single, isIn(['a', 'b']));
      await tester.pump(const Duration(seconds: 1));
    });

    testWidgets('una región pequeña se acierta aunque el dedo caiga un poco fuera', (tester) async {
      final c = await pumpCanvas(tester, const Size(500, 500));
      final d = c.drawing!;
      // Escala ≈ 0,47: 12 dp de tolerancia ≈ 25 unidades del dibujo.
      await tester.tapAt(screenPointOf(tester, d, const Offset(704 + 30, 960)));
      expect(c.regionColors.keys, ['punto']);
      // Lejos de cualquier figura, se pinta el fondo.
      await tester.tapAt(screenPointOf(tester, d, const Offset(704 + 150, 960)));
      expect(c.regionColors.keys, unorderedEquals(['punto', 'fondo']));
      await tester.pump(const Duration(seconds: 1));
    });

    testWidgets('un toque fuera del dibujo (bandas laterales) no pinta nada', (tester) async {
      setScreenSize(tester, const Size(1300, 1000));
      final c = await pumpCanvas(tester, const Size(900, 400));
      final rect = tester.getRect(find.byType(ColoringCanvas));
      await tester.tapAt(rect.topLeft + const Offset(5, 200));
      expect(c.regionColors, isEmpty);
      await tester.pump(const Duration(seconds: 1));
    });

    // Con el dibujo ampliado, tocar cada zona pequeña visible pinta esa zona.
    Future<void> expectPreciseTaps(WidgetTester tester, ColoringController c, {required double zoom}) async {
      final d = c.drawing!;
      final view = tester.getRect(find.byType(InteractiveViewer)).deflate(30);
      // Los botones de zoom tapan una esquina del dibujo: esas zonas se alcanzan arrastrando.
      final buttons = [
        for (final label in ['Ampliar', 'Alejar', 'Ver el dibujo entero'])
          for (final e in find.bySemanticsLabel(label).evaluate())
            tester.getRect(find.byWidget(e.widget)).inflate(12),
      ];
      final small = d.regions.where((r) => r.id != VectorDrawing.backgroundId).toList()
        ..sort((a, b) => (a.bounds.width * a.bounds.height).compareTo(b.bounds.width * b.bounds.height));
      var tapped = 0;
      // Las zonas pequeñas que se ven enteras…
      for (final r in small) {
        final p = screenPointOf(tester, d, interiorPoint(d, r.id, step: 4, margin: 8));
        if (!view.contains(p) || buttons.any((b) => b.contains(p))) continue;
        await tester.tapAt(p);
        await tester.pump();
        expect(c.selectedRegion, r.id, reason: '${r.id} con zoom ×${zoom.toStringAsFixed(1)}');
        if (++tapped == 6) break;
      }
      // …y una cuadrícula de puntos: cada toque pinta la zona dibujada debajo.
      final canvas = tester.getRect(drawingCanvasFinder);
      for (var gy = 0; gy < 5; gy++) {
        for (var gx = 0; gx < 5; gx++) {
          final p = Offset(view.left + view.width * (gx + .5) / 5, view.top + view.height * (gy + .5) / 5);
          if (buttons.any((b) => b.contains(p))) continue;
          // Misma regla que la app: sobre una línea gana la zona más cercana
          // (el margen de acierto es de 12 px en la pantalla, con o sin zoom).
          final scale = DrawingPainter.fit(d.viewBox, canvas.size).scale;
          final expected = d.hitTest(
            DrawingPainter.toViewBox(p - canvas.topLeft, d.viewBox, canvas.size),
            tolerance: ColoringCanvas.touchTolerance / scale,
          );
          if (expected == null) continue;
          await tester.tapAt(p);
          await tester.pump();
          expect(c.selectedRegion, expected, reason: '$p con zoom ×${zoom.toStringAsFixed(1)}');
          tapped++;
        }
      }
      expect(tapped, greaterThan(0));
      await tester.pump(const Duration(seconds: 1));
    }

    double zoomOf(WidgetTester tester) => tester
        .widget<InteractiveViewer>(find.byType(InteractiveViewer))
        .transformationController!
        .value
        .getMaxScaleOnAxis();

    testWidgets('los botones amplían, alejan y vuelven a mostrar el dibujo entero', (tester) async {
      setScreenSize(tester, const Size(1300, 1000));
      final c = await pumpCanvas(
        tester,
        const Size(500, 500),
        file: 'assets/drawings/animals/animal_gato.svg',
      );
      // Al principio solo está «Ampliar».
      expect(find.bySemanticsLabel('Ampliar'), findsOneWidget);
      expect(find.bySemanticsLabel('Alejar'), findsNothing);
      expect(find.bySemanticsLabel('Ver el dibujo entero'), findsNothing);
      final before = tester.getRect(drawingCanvasFinder);

      await tester.tap(find.bySemanticsLabel('Ampliar'));
      await tester.pumpAndSettle();
      expect(zoomOf(tester), closeTo(ColoringCanvas.zoomStep, 0.01));
      expect(tester.getRect(drawingCanvasFinder).width, closeTo(before.width * ColoringCanvas.zoomStep, 1));
      expect(find.bySemanticsLabel('Alejar'), findsOneWidget);
      await expectPreciseTaps(tester, c, zoom: zoomOf(tester));

      // Hasta el máximo: el botón de ampliar se apaga.
      for (var i = 0; i < 5; i++) {
        await tester.tap(find.bySemanticsLabel('Ampliar'));
        await tester.pumpAndSettle();
      }
      expect(zoomOf(tester), closeTo(ColoringCanvas.maxZoom, 0.01));
      expect(
        tester.getSemantics(find.bySemanticsLabel('Ampliar')),
        isSemantics(isEnabled: false, isButton: true, hasEnabledState: true),
      );
      await expectPreciseTaps(tester, c, zoom: zoomOf(tester));

      await tester.tap(find.bySemanticsLabel('Alejar'));
      await tester.pumpAndSettle();
      expect(zoomOf(tester), closeTo(ColoringCanvas.maxZoom / ColoringCanvas.zoomStep, 0.01));

      await tester.tap(find.bySemanticsLabel('Ver el dibujo entero'));
      await tester.pumpAndSettle();
      expect(zoomOf(tester), closeTo(1, 0.001));
      expect(tester.getRect(drawingCanvasFinder), before);
      expect(find.bySemanticsLabel('Alejar'), findsNothing);
    });

    testWidgets('pellizcar amplía el dibujo y los toques siguen siendo precisos', (tester) async {
      setScreenSize(tester, const Size(1300, 1000));
      final c = await pumpCanvas(
        tester,
        const Size(500, 500),
        file: 'assets/drawings/fantasy/fantasia_robot.svg',
      );
      final center = tester.getRect(drawingCanvasFinder).center;
      final a = await tester.startGesture(center - const Offset(30, 0), pointer: 1);
      final b = await tester.startGesture(center + const Offset(30, 0), pointer: 2);
      for (var i = 1; i <= 10; i++) {
        await a.moveTo(center - Offset(30 + 9.0 * i, 0));
        await b.moveTo(center + Offset(30 + 9.0 * i, 0));
        await tester.pump(const Duration(milliseconds: 16));
      }
      await a.up();
      await b.up();
      await tester.pumpAndSettle();
      expect(zoomOf(tester), greaterThan(2));
      expect(c.regionColors, isEmpty, reason: 'pellizcar no pinta');
      await expectPreciseTaps(tester, c, zoom: zoomOf(tester));
    });

    testWidgets('arrastrar con el dibujo ampliado lo mueve sin pintar', (tester) async {
      setScreenSize(tester, const Size(1300, 1000));
      final c = await pumpCanvas(
        tester,
        const Size(500, 500),
        file: 'assets/drawings/animals/animal_gato.svg',
      );
      await tester.tap(find.bySemanticsLabel('Ampliar'));
      await tester.pumpAndSettle();
      final before = tester.getRect(drawingCanvasFinder);
      await tester.drag(find.byType(InteractiveViewer), const Offset(120, 80));
      await tester.pumpAndSettle();
      final after = tester.getRect(drawingCanvasFinder);
      expect(after.topLeft, isNot(before.topLeft));
      expect(c.regionColors, isEmpty);
      // El dibujo no se sale del marco: no quedan huecos.
      final view = tester.getRect(find.byType(InteractiveViewer));
      expect(after.left, lessThanOrEqualTo(view.left + 0.5));
      expect(after.top, lessThanOrEqualTo(view.top + 0.5));
      await expectPreciseTaps(tester, c, zoom: zoomOf(tester));
    });

    testWidgets('dibujo real a dos tamaños: el mismo punto del dibujo pinta la misma región', (tester) async {
      setScreenSize(tester, const Size(1300, 1000));
      const file = 'assets/drawings/fantasy/fantasia_extraterrestre.svg';
      for (final size in const [Size(320, 320), Size(900, 600)]) {
        final c = await pumpCanvas(tester, size, file: file);
        final d = c.drawing!;
        for (final id in ['ojo_izquierdo', 'barriga', 'antena_derecha_bola', 'pie_derecho']) {
          await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, id, step: 4, margin: 4)));
          expect(c.selectedRegion, id, reason: '$id a ${size.width}×${size.height}');
        }
        await tester.pump(const Duration(seconds: 1));
      }
    });
  });
}
