import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
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
  group('Estados vacíos e imágenes ausentes', () {
    final oneAnimalWithoutPreview = jsonEncode({
      'drawings': [
        {
          'id': 'animal_gato',
          'name': 'Gato',
          'category': 'animales',
          'file': 'assets/drawings/animals/animal_gato.svg',
          'thumbnail': 'assets/thumbnails/animal_gato.png',
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
      await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
      await tapAndSettle(tester, find.bySemanticsLabel('Frutas, 0 dibujos'));
      expect(find.text('Todavía no hay dibujos aquí'), findsOneWidget);
      await tapAndSettle(tester, find.text('Ver categorías'));
      expect(find.text('Elige una categoría'), findsOneWidget);
    });

    testWidgets('una imagen ausente se sustituye por un marcador identificado', (tester) async {
      setScreenSize(tester, const Size(400, 860));
      await pumpApp(tester, service: service());
      await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
      await tapAndSettle(tester, find.bySemanticsLabel('Animales, 1 dibujo'));
      expect(find.byType(MissingImagePlaceholder), findsOneWidget);
      expect(find.text(MissingImagePlaceholder.label), findsOneWidget);
      expect(find.byType(Image), findsNothing);
    });

    testWidgets('sin catálogo, «Colorear» muestra las categorías vacías sin «¡Vamos a pintar!»', (
      tester,
    ) async {
      setScreenSize(tester, const Size(400, 860));
      await pumpApp(tester, service: fakeCatalogService('{"drawings": []}', {}));
      await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
      expect(find.text('Elige una categoría'), findsOneWidget);
      expect(find.bySemanticsLabel('¡Vamos a pintar!'), findsNothing);
      expect(find.bySemanticsLabel('Animales, 0 dibujos'), findsOneWidget);
    });

    testWidgets('una imagen que no se puede cargar muestra el marcador', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: SizedBox(
            width: 200,
            height: 200,
            child: DrawingThumbnail(asset: 'assets/thumbnails/no_existe.png'),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(MissingImagePlaceholder), findsOneWidget);
    });
  });
}
