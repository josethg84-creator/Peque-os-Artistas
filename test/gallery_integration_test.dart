import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/engine/drawing_painter.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/models/drawing_category.dart';
import 'package:pequenos_artistas/screens/coloring_screen.dart';
import 'package:pequenos_artistas/screens/gallery_screen.dart';
import 'package:pequenos_artistas/screens/search_screen.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';
import 'package:pequenos_artistas/widgets/drawing_card.dart';

import 'test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

final catalog = (jsonDecode(File('assets/catalog/catalog.json').readAsStringSync())['drawings'] as List)
    .cast<Map<String, dynamic>>();

String cardLabel(Map<String, dynamic> d) {
  const levels = {'facil': 'fácil', 'media': 'media', 'dificil': 'difícil'};
  return '${d['name']}. Dificultad ${levels[d['difficulty']]}';
}

List<String> cardIds(WidgetTester tester) =>
    tester.widgetList<DrawingCard>(find.byType(DrawingCard)).map((c) => c.drawing.id).toList();

void main() {
  testWidgets('cada una de las 59 tarjetas abre su propio dibujo con sus regiones', (tester) async {
    setScreenSize(tester, const Size(1000, 1400));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
    var opened = 0;
    for (final category in DrawingCategory.values) {
      final entries = catalog.where((d) => d['category'] == category.id).toList();
      await tapAndSettle(tester, find.bySemanticsLabel('${category.label}, ${entries.length} dibujos'));
      expect(
        cardIds(tester),
        entries.map((d) => d['id']).toList(),
        reason: 'orden y contenido de ${category.label}',
      );

      for (final entry in entries) {
        await tapAndSettle(tester, find.bySemanticsLabel(cardLabel(entry)));
        final screen = tester.widget<ColoringScreen>(find.byType(ColoringScreen));
        expect(screen.drawingId, entry['id']);
        expect(find.text(entry['name'] as String), findsOneWidget);
        // El lienzo cargó exactamente las regiones del SVG de ese dibujo.
        final painter = tester.widget<CustomPaint>(drawingCanvasFinder).painter! as DrawingPainter;
        final expected = parseColoringSvg(File(entry['file'] as String).readAsStringSync());
        expect(painter.drawing.regions.map((r) => r.id).toList(), expected.regions.map((r) => r.id).toList());
        opened++;
        await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
        expect(find.byType(GalleryScreen), findsOneWidget);
      }
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a categorías'));
    }
    expect(opened, 59);
  });

  testWidgets('las tarjetas marcan los dibujos pintados y los colores no se mezclan', (tester) async {
    setScreenSize(tester, const Size(1000, 1400));
    final store = InMemoryCreationStore();
    await pumpApp(tester, store: store);
    await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
    await tapAndSettle(tester, find.bySemanticsLabel('Animales, 14 dibujos'));
    expect(find.bySemanticsLabel(RegExp(DrawingCard.paintedLabel)), findsNothing);

    Future<void> paintHead(String label, String file, String color) async {
      await tapAndSettle(tester, find.bySemanticsLabel(label));
      await tapAndSettle(tester, find.bySemanticsLabel(color));
      final d = parseColoringSvg(File(file).readAsStringSync());
      await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, 'cabeza')));
      await tester.pump();
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    }

    await paintHead('Gato. Dificultad media', 'assets/drawings/animals/animal_gato.svg', 'Rojo');
    await paintHead('Perro. Dificultad fácil', 'assets/drawings/animals/animal_perro.svg', 'Azul');

    expect(find.bySemanticsLabel('Gato. Dificultad media. ${DrawingCard.paintedLabel}'), findsOneWidget);
    expect(find.bySemanticsLabel('Perro. Dificultad fácil. ${DrawingCard.paintedLabel}'), findsOneWidget);
    expect(find.bySemanticsLabel('Conejo. Dificultad media'), findsOneWidget); // sin insignia

    final gato = (await store.latestFor('animal_gato'))!;
    final perro = (await store.latestFor('animal_perro'))!;
    expect(gato.regionColors, {'cabeza': const Color(0xFFE53935)});
    expect(perro.regionColors, {'cabeza': const Color(0xFF1E57C8)});
  });

  group('Búsqueda y filtros', () {
    Future<void> openSearch(WidgetTester tester) async {
      setScreenSize(tester, const Size(800, 1300));
      await pumpApp(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
      await tapAndSettle(tester, find.bySemanticsLabel('Buscar dibujos'));
      expect(find.byType(SearchScreen), findsOneWidget);
    }

    Future<List<String>> allResultIds(WidgetTester tester) async {
      final seen = <String>[];
      final scrollable = find.byType(Scrollable).last;
      for (var i = 0; i < 20; i++) {
        for (final id in cardIds(tester)) {
          if (!seen.contains(id)) seen.add(id);
        }
        await tester.drag(scrollable, const Offset(0, -500));
        await tester.pumpAndSettle();
      }
      // Vuelve arriba (los filtros están en la cabecera).
      for (var i = 0; i < 20; i++) {
        await tester.drag(scrollable, const Offset(0, 500));
      }
      await tester.pumpAndSettle();
      return seen;
    }

    testWidgets('muestra los 59 y busca por nombre sin tildes', (tester) async {
      await openSearch(tester);
      expect(find.text('59 dibujos'), findsOneWidget);
      await tester.enterText(find.byType(TextField), 'leon');
      await tester.pumpAndSettle();
      expect(find.text('1 dibujo'), findsOneWidget);
      expect(cardIds(tester), ['animal_leon']);
      await tapAndSettle(tester, find.bySemanticsLabel('León. Dificultad media'));
      expect(tester.widget<ColoringScreen>(find.byType(ColoringScreen)).drawingId, 'animal_leon');
    });

    testWidgets('filtra por categoría y dificultad, y ordena de la A a la Z', (tester) async {
      await openSearch(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('Dinosaurios'));
      expect(find.text('8 dibujos'), findsOneWidget);
      expect(await allResultIds(tester), [
        'dinosaurio_01',
        'dinosaurio_02',
        'dinosaurio_03',
        'dinosaurio_04',
        'dinosaurio_05',
        'dinosaurio_06',
        'dinosaurio_07',
        'dinosaurio_08',
      ]);

      await tapAndSettle(tester, find.bySemanticsLabel('A → Z'));
      // Bebé dinosaurio, Brontosaurio, Espinosaurio, Estegosaurio, Pteranodonte,
      // T-Rex, Triceratops y Velociraptor.
      expect(await allResultIds(tester), [
        'dinosaurio_05',
        'dinosaurio_04',
        'dinosaurio_06',
        'dinosaurio_03',
        'dinosaurio_07',
        'dinosaurio_01',
        'dinosaurio_02',
        'dinosaurio_08',
      ]);

      await tapAndSettle(tester, find.bySemanticsLabel('Todos'));
      await tapAndSettle(tester, find.bySemanticsLabel('Difícil'));
      expect(find.text('34 dibujos'), findsOneWidget);
      // Orden de la A a la Z.
      expect(await allResultIds(tester), [
        'animal_abeja',
        'vehiculo_autobus',
        'vehiculo_automovil',
        'vehiculo_avion',
        'vehiculo_barco',
        'dinosaurio_04',
        'mar_caballito',
        'mar_cangrejo',
        'animal_cebra',
        'fantasia_dragon',
        'animal_elefante',
        'dinosaurio_06',
        'dinosaurio_03',
        'fruta_fresa',
        'fantasia_hada',
        'fantasia_hada_hongo',
        'vehiculo_helicoptero',
        'animal_jirafa',
        'animal_mariposa',
        'fruta_naranja',
        'animal_oruga',
        'animal_pez',
        'fruta_pina',
        'dinosaurio_07',
        'fantasia_robot',
        'fantasia_robot_heroe',
        'dinosaurio_01',
        'animal_tortuga',
        'mar_tortuga',
        'vehiculo_tren',
        'dinosaurio_02',
        'fantasia_unicornio',
        'granja_vaca',
        'dinosaurio_08',
      ]);

      await tapAndSettle(tester, find.bySemanticsLabel('Todas'));
      await tapAndSettle(tester, find.bySemanticsLabel('Normal'));
      expect(await allResultIds(tester), catalog.map((d) => d['id']).toList());
    });

    testWidgets('sin resultados muestra un estado vacío que quita los filtros', (tester) async {
      await openSearch(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('Frutas'));
      await tester.enterText(find.byType(TextField), 'dragón');
      await tester.pumpAndSettle();
      expect(find.text('No encontramos dibujos'), findsOneWidget);
      await tapAndSettle(tester, find.text('Quitar filtros'));
      expect(find.text('59 dibujos'), findsOneWidget);
      expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, isEmpty);
    });
  });
}
