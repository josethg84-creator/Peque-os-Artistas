import 'dart:convert';
import 'dart:io';
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/coloring_controller.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';

import '../test_helpers.dart';

/// Comprueba los 31 dibujos reales de la Fase 1 con el motor de coloreado.
void main() {
  final catalog = (jsonDecode(File('assets/catalog/catalog.json').readAsStringSync())['drawings'] as List)
      .cast<Map<String, dynamic>>();
  final report = StringBuffer();

  test('el catálogo tiene 31 dibujos', () => expect(catalog, hasLength(31)));

  for (final entry in catalog) {
    final id = entry['id'] as String;
    test('$id: se lee, coincide con el catálogo y todas sus regiones se pueden tocar', () {
      final watch = Stopwatch()..start();
      final drawing = parseColoringSvg(File(entry['file'] as String).readAsStringSync());
      final parseMs = watch.elapsedMilliseconds;

      expect(drawing.viewBox, const Rect.fromLTWH(0, 0, 1024, 1024));
      expect(drawing.regions.first.id, VectorDrawing.backgroundId);
      expect(drawing.regions.length - 1, entry['regions'], reason: 'número de zonas del catálogo');
      final ids = drawing.regions.map((r) => r.id).toList();
      expect(ids.toSet(), hasLength(ids.length), reason: 'ids únicos');

      // Barrido cada 4 unidades: qué región responde en cada punto.
      final hits = <String, int>{};
      for (var y = 2.0; y < 1024; y += 4) {
        for (var x = 2.0; x < 1024; x += 4) {
          final hit = drawing.regionAt(Offset(x, y));
          if (hit != null) hits[hit] = (hits[hit] ?? 0) + 1;
        }
      }
      final unreachable = ids.where((r) => !hits.containsKey(r)).toList();
      expect(unreachable, isEmpty, reason: 'regiones imposibles de tocar');

      // Área visible aproximada (cada muestra = 16 unidades²).
      final smallest = ids
          .where((r) => r != VectorDrawing.backgroundId)
          .map((r) => (r, hits[r]! * 16))
          .reduce((a, b) => a.$2 <= b.$2 ? a : b);
      expect(smallest.$2, greaterThanOrEqualTo(800), reason: 'región ${smallest.$1} demasiado pequeña');

      // Todos los puntos del dibujo pertenecen a alguna región (el fondo cubre todo).
      expect(hits.values.fold<int>(0, (a, b) => a + b), 256 * 256);
      report.writeln(
        '$id: ${ids.length - 1} zonas, menor ${smallest.$1} ≈ ${smallest.$2} u², lectura ${parseMs}ms',
      );
    });
  }

  for (final entry in catalog) {
    final id = entry['id'] as String;
    test('$id: tocar cada región pinta esa región y ninguna otra', () async {
      final c = ColoringController(
        drawingId: id,
        file: entry['file'] as String,
        loader: diskDrawingLoader(),
        store: InMemoryCreationStore(),
        saveDelay: const Duration(days: 1),
      );
      await c.load();
      expect(c.status, ColoringStatus.ready);
      final d = c.drawing!;
      for (final (i, region) in d.regions.indexed) {
        final color = kidPalette[i % (kidPalette.length - 1)]; // sin el blanco
        c.selectColor(color);
        final before = Map.of(c.regionColors);
        final hit = c.tapAt(interiorPoint(d, region.id), tolerance: 12);
        expect(hit, region.id, reason: '$id/${region.id}');
        expect(c.colorOf(region.id), color.color, reason: '$id/${region.id}');
        final others = Map.of(c.regionColors)..remove(region.id);
        expect(others, before..remove(region.id), reason: 'no cambian otras regiones ($id/${region.id})');
      }
      expect(c.regionColors, hasLength(d.regions.length));
      c.clear();
      expect(c.regionColors, isEmpty);
      c.dispose();
    });
  }

  tearDownAll(() {
    // ignore: avoid_print
    print('\nResumen del motor con los dibujos reales:\n$report');
  });
}
