import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/color_palette_bar.dart';
import 'package:pequenos_artistas/coloring/coloring_controller.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';

import '../test_helpers.dart';

void main() {
  test('24 colores con nombres y valores distintos, y el blanco al final', () {
    expect(kidPalette, hasLength(24));
    expect(kidPalette.map((c) => c.name).toSet(), hasLength(24));
    expect(kidPalette.map((c) => c.color).toSet(), hasLength(24));
    expect(kidPalette.where((c) => c.restoresOriginal).map((c) => c.name), ['Blanco']);
    expect(kidPalette.last.name, 'Blanco');
  });

  test('los colores de la primera paleta conservan su valor (los dibujos guardados no cambian)', () {
    const original = {
      'Rojo': 0xFFE53935,
      'Naranja': 0xFFFF8F00,
      'Amarillo': 0xFFFFD600,
      'Verde claro': 0xFF7CB342,
      'Verde': 0xFF2E7D32,
      'Celeste': 0xFF29B6F6,
      'Azul': 0xFF1E57C8,
      'Morado': 0xFF8E44AD,
      'Rosa': 0xFFF06292,
      'Marrón': 0xFF8D5524,
      'Gris': 0xFF9E9E9E,
      'Negro': 0xFF212121,
      'Blanco': 0xFFFFFFFF,
    };
    original.forEach(
      (name, value) => expect(kidPalette.firstWhere((c) => c.name == name).color, Color(value), reason: name),
    );
  });

  for (final axis in Axis.values) {
    testWidgets('la barra (${axis.name}) muestra los 24 colores en dos líneas y cada uno se puede elegir', (
      tester,
    ) async {
      final controller = ColoringController(
        drawingId: 'prueba',
        file: 'assets/drawings/fruits/fruta_platano.svg',
        loader: diskDrawingLoader(),
        store: InMemoryCreationStore(),
      );
      addTearDown(controller.dispose);
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: axis == Axis.horizontal ? 400 : 160,
              height: axis == Axis.horizontal ? 160 : 600,
              child: ListenableBuilder(
                listenable: controller,
                builder: (_, _) => ColorPaletteBar(controller: controller, axis: axis),
              ),
            ),
          ),
        ),
      );
      // Dos líneas: del rojo a la turquesa en una, y del celeste al blanco en la otra.
      Offset pos(String name) => tester.getCenter(find.bySemanticsLabel(RegExp('^$name(,|\$)')));
      final first = pos('Rojo'), second = pos('Celeste');
      if (axis == Axis.horizontal) {
        expect(second.dy, greaterThan(first.dy + 40));
        expect(second.dx, closeTo(first.dx, 1));
      } else {
        expect(second.dx, greaterThan(first.dx + 40));
        expect(second.dy, closeTo(first.dy, 1));
      }
      for (final c in kidPalette.where((c) => !c.restoresOriginal)) {
        final swatch = find.bySemanticsLabel(RegExp('^${RegExp.escape(c.name)}\$'));
        await tester.ensureVisible(swatch);
        await tester.pumpAndSettle();
        await tester.tap(swatch);
        await tester.pump();
        expect(controller.color, c, reason: c.name);
      }
    });
  }
}
