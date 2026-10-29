import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/screens/coloring_screen.dart';
import 'package:pequenos_artistas/screens/home_screen.dart';
import 'package:pequenos_artistas/services/progress_store.dart';

import '../test_helpers.dart';

/// Pruebas de integración del juego completo (pantallas reales, dibujos
/// reales, almacenamiento en memoria).
Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

VectorDrawing svgOf(String file) => parseColoringSvg(File(file).readAsStringSync());

Future<void> paint(WidgetTester tester, VectorDrawing d, String region, String colorName) async {
  await tapAndSettle(tester, find.bySemanticsLabel(colorName));
  await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, region)));
  await tester.pump();
}

bool enabled(WidgetTester tester, String label) =>
    isSemantics(isEnabled: true).matches(tester.getSemantics(find.bySemanticsLabel(label)), {});

bool selected(WidgetTester tester, String label) =>
    isSemantics(isSelected: true).matches(tester.getSemantics(find.bySemanticsLabel(label)), {});

Map<String, dynamic> savedRegions(InMemoryProgressStore store, String id) =>
    (jsonDecode(store.raw[id]!) as Map<String, dynamic>)['regions'] as Map<String, dynamic>;

const gatoFile = 'assets/drawings/animals/animal_gato.svg';

void main() {
  testWidgets('elegir dibujo y color, pintar zonas, deshacer, rehacer y guardar al salir', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final store = InMemoryProgressStore();
    await pumpApp(tester, store: store);
    await tapAndSettle(tester, find.bySemanticsLabel('Galería'));
    await tapAndSettle(tester, find.bySemanticsLabel('Animales, 10 dibujos'));
    await tapAndSettle(tester, find.bySemanticsLabel('Gato. Dificultad fácil'));
    expect(find.byType(ColoringScreen), findsOneWidget);
    expect(find.text('Vista previa: pintar llegará pronto'), findsNothing);

    // Paleta: los 12 colores pedidos (y verde claro), con el activo marcado.
    for (final c in ['Rojo', 'Azul', 'Amarillo', 'Verde', 'Naranja', 'Morado', 'Rosa', 'Celeste', 'Marrón']) {
      expect(find.bySemanticsLabel(c), findsOneWidget, reason: c);
    }
    expect(kidPalette.map((c) => c.name), containsAll(['Negro', 'Gris', 'Blanco']));
    expect(selected(tester, 'Rojo'), isTrue);
    expect(enabled(tester, 'Deshacer'), isFalse);
    expect(enabled(tester, 'Limpiar'), isFalse);

    final d = svgOf(gatoFile);
    await paint(tester, d, 'cuerpo', 'Azul');
    expect(selected(tester, 'Azul'), isTrue);
    expect(enabled(tester, 'Deshacer'), isTrue);
    expect(enabled(tester, 'Limpiar'), isTrue);
    await paint(tester, d, 'cabeza', 'Amarillo');
    await paint(tester, d, 'cabeza', 'Rosa'); // cambia de color

    await tapAndSettle(tester, find.bySemanticsLabel('Deshacer')); // cabeza vuelve a amarillo
    expect(enabled(tester, 'Rehacer'), isTrue);
    await tapAndSettle(tester, find.bySemanticsLabel('Deshacer')); // cabeza sin pintar
    await tapAndSettle(tester, find.bySemanticsLabel('Rehacer')); // cabeza amarilla

    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(savedRegions(store, 'animal_gato'), {
      'cuerpo':
          '#${kidPalette.firstWhere((c) => c.name == 'Azul').color.toARGB32().toRadixString(16).toUpperCase()}',
      'cabeza':
          '#${kidPalette.firstWhere((c) => c.name == 'Amarillo').color.toARGB32().toRadixString(16).toUpperCase()}',
    });
  });

  testWidgets('el progreso se recupera desde «Mis dibujos» y limpiar pide confirmación', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final store = InMemoryProgressStore();
    await pumpApp(tester, store: store);
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!')); // abre el gato
    final d = svgOf(gatoFile);
    await paint(tester, d, 'cola', 'Verde');
    await paint(tester, d, 'barriga', 'Naranja');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.byType(HomeScreen), findsOneWidget);

    await tapAndSettle(tester, find.bySemanticsLabel('Mis dibujos'));
    await tapAndSettle(tester, find.bySemanticsLabel('Gato, pintado'));
    // Los colores vuelven, pero el historial empieza de cero.
    expect(enabled(tester, 'Limpiar'), isTrue);
    expect(enabled(tester, 'Deshacer'), isFalse);

    await tapAndSettle(tester, find.bySemanticsLabel('Limpiar'));
    expect(find.text('¿Borrar todos los colores?'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('No, seguir pintando'));
    expect(enabled(tester, 'Limpiar'), isTrue);

    await tapAndSettle(tester, find.bySemanticsLabel('Limpiar'));
    await tapAndSettle(tester, find.bySemanticsLabel('Sí, borrar'));
    expect(enabled(tester, 'Limpiar'), isFalse);
    expect(enabled(tester, 'Deshacer'), isTrue); // limpiar se puede deshacer

    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(store.raw, isEmpty); // un dibujo limpio no ocupa espacio
    expect(find.text('Aquí verás tus dibujos'), findsOneWidget);
  });

  testWidgets('«Otro dibujo» abre un dibujo nuevo sin arrastrar los colores', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final store = InMemoryProgressStore();
    await pumpApp(tester, store: store);
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
    await paint(tester, svgOf(gatoFile), 'cabeza', 'Morado');

    await tapAndSettle(tester, find.bySemanticsLabel('Otro dibujo'));
    await tapAndSettle(tester, find.bySemanticsLabel('Perro'));
    expect(find.text('Perro'), findsOneWidget);
    expect(enabled(tester, 'Limpiar'), isFalse);
    expect(enabled(tester, 'Deshacer'), isFalse);
    expect(savedRegions(store, 'animal_gato').keys, ['cabeza']);
    expect(store.raw.containsKey('animal_perro'), isFalse);

    // Volver lleva al inicio (el dibujo anterior se sustituyó).
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets('el borrador quita el color de una zona', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final store = InMemoryProgressStore();
    await pumpApp(tester, store: store);
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
    final d = svgOf(gatoFile);
    await paint(tester, d, 'cola', 'Rojo');
    await paint(tester, d, 'cuerpo', 'Rojo');
    await tapAndSettle(tester, find.bySemanticsLabel('Borrador'));
    expect(selected(tester, 'Borrador'), isTrue);
    expect(selected(tester, 'Rojo'), isFalse);
    await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, 'cola')));
    await tester.pump();
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(savedRegions(store, 'animal_gato').keys, ['cuerpo']);
  });

  testWidgets('en horizontal el lienzo sigue respondiendo con precisión', (tester) async {
    setScreenSize(tester, const Size(900, 420));
    final store = InMemoryProgressStore();
    await pumpApp(tester, store: store);
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
    final d = svgOf(gatoFile);
    for (final region in ['oreja_izquierda_interior', 'hocico', 'pata_derecha']) {
      await paint(tester, d, region, 'Celeste');
    }
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(savedRegions(store, 'animal_gato').keys, ['oreja_izquierda_interior', 'hocico', 'pata_derecha']);
  });

  testWidgets('un SVG ausente muestra un error amable con reintento', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final catalog = jsonEncode({
      'drawings': [
        {
          'id': 'animal_fantasma',
          'name': 'Fantasma',
          'category': 'animales',
          'file': 'assets/drawings/animals/animal_fantasma.svg',
          'difficulty': 'facil',
        },
      ],
    });
    // El catálogo cree que el archivo existe, pero no se puede leer.
    await pumpApp(
      tester,
      service: fakeCatalogService(catalog, {'assets/drawings/animals/animal_fantasma.svg'}),
    );
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
    expect(find.text('No pudimos abrir este dibujo'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
    expect(enabled(tester, 'Borrador'), isFalse);
    await tapAndSettle(tester, find.text('Reintentar'));
    expect(find.text('No pudimos abrir este dibujo'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.byType(HomeScreen), findsOneWidget);
  });
}
