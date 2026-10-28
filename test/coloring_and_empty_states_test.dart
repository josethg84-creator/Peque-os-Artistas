import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/coloring_controller.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/services/catalog_service.dart';
import 'package:pequenos_artistas/widgets/drawing_thumbnail.dart';

import 'test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

void main() {
  group('Pantalla de coloreado', () {
    testWidgets('tiene lienzo, paleta, borrador, deshacer, rehacer, limpiar y volver', (tester) async {
      setScreenSize(tester, const Size(400, 860));
      await pumpApp(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));

      expect(find.bySemanticsLabel('Dibujo para colorear: Gato'), findsOneWidget);
      for (final c in kidPalette.take(4)) {
        expect(find.bySemanticsLabel(c.name), findsOneWidget);
      }
      for (final label in ['Borrador', 'Deshacer', 'Rehacer', 'Limpiar', 'Volver a la galería']) {
        expect(find.bySemanticsLabel(label), findsOneWidget, reason: label);
      }
    });

    testWidgets('elegir color y borrador cambia la selección; el resto sigue desactivado', (tester) async {
      setScreenSize(tester, const Size(400, 860));
      await pumpApp(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));

      bool isSelected(String label) =>
          isSemantics(isSelected: true).matches(tester.getSemantics(find.bySemanticsLabel(label)), {});
      bool isEnabled(String label) =>
          isSemantics(isEnabled: true).matches(tester.getSemantics(find.bySemanticsLabel(label)), {});

      expect(isSelected('Rojo'), isTrue);
      await tapAndSettle(tester, find.bySemanticsLabel('Azul'));
      expect(isSelected('Azul'), isTrue);
      expect(isSelected('Rojo'), isFalse);

      await tapAndSettle(tester, find.bySemanticsLabel('Borrador'));
      expect(isSelected('Borrador'), isTrue);
      expect(isSelected('Azul'), isFalse);

      // Elegir un color vuelve a la herramienta de pintar.
      await tapAndSettle(tester, find.bySemanticsLabel('Verde'));
      expect(isSelected('Borrador'), isFalse);

      // Sin motor de coloreado no hay nada que deshacer, rehacer ni limpiar.
      for (final label in ['Deshacer', 'Rehacer', 'Limpiar']) {
        expect(isEnabled(label), isFalse, reason: label);
      }
      expect(find.text('Vista previa: pintar llegará pronto'), findsOneWidget);
    });

    test('el controlador no declara historial mientras no exista el motor', () {
      final c = ColoringController();
      expect(c.coloringEngineReady, isFalse);
      expect(c.canUndo || c.canRedo || c.hasColoring, isFalse);
      c.toggleEraser();
      expect(c.tool, ColoringTool.eraser);
      c.selectColor(kidPalette[3]);
      expect(c.tool, ColoringTool.paint);
      expect(c.color, kidPalette[3]);
    });
  });

  group('Estados vacíos e imágenes ausentes', () {
    final oneAnimalWithoutPreview = jsonEncode({
      'drawings': [
        {
          'id': 'animal_gato',
          'name': 'Gato',
          'category': 'animales',
          'file': 'assets/drawings/animals/animal_gato.svg',
          'preview': 'assets/previews/animal_gato.png',
          'difficulty': 'facil',
          'recommended_age': '4-5',
          'description': 'Prueba',
        },
      ],
    });
    CatalogService service() => fakeCatalogService(
      oneAnimalWithoutPreview,
      {'assets/drawings/animals/animal_gato.svg'}, // el PNG «no existe»
    );

    testWidgets('una categoría sin dibujos muestra un estado vacío amable', (tester) async {
      setScreenSize(tester, const Size(400, 860));
      await pumpApp(tester, service: service());
      await tapAndSettle(tester, find.bySemanticsLabel('Galería'));
      await tapAndSettle(tester, find.bySemanticsLabel('Frutas, 0 dibujos'));
      expect(find.text('Todavía no hay dibujos aquí'), findsOneWidget);
      await tapAndSettle(tester, find.text('Ver categorías'));
      expect(find.text('Elige una categoría'), findsOneWidget);
    });

    testWidgets('una imagen ausente se sustituye por un marcador identificado', (tester) async {
      setScreenSize(tester, const Size(400, 860));
      await pumpApp(tester, service: service());
      await tapAndSettle(tester, find.bySemanticsLabel('Galería'));
      await tapAndSettle(tester, find.bySemanticsLabel('Animales, 1 dibujo'));
      expect(find.byType(MissingImagePlaceholder), findsOneWidget);
      expect(find.text(MissingImagePlaceholder.label), findsOneWidget);
      expect(find.byType(Image), findsNothing);
    });

    testWidgets('sin catálogo, «¡Vamos a pintar!» lleva a las categorías vacías', (tester) async {
      setScreenSize(tester, const Size(400, 860));
      await pumpApp(tester, service: fakeCatalogService('{"drawings": []}', {}));
      await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
      expect(find.text('Elige una categoría'), findsOneWidget);
      expect(find.bySemanticsLabel('Animales, 0 dibujos'), findsOneWidget);
    });

    testWidgets('una imagen que no se puede cargar muestra el marcador', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: SizedBox(
            width: 200,
            height: 200,
            child: DrawingThumbnail(asset: 'assets/previews/no_existe.png'),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(MissingImagePlaceholder), findsOneWidget);
    });
  });
}
