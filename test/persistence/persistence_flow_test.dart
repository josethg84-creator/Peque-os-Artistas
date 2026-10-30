import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/engine/drawing_painter.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/screens/coloring_screen.dart';
import 'package:pequenos_artistas/screens/home_screen.dart';
import 'package:pequenos_artistas/screens/saved_drawings_screen.dart';
import 'package:pequenos_artistas/widgets/friendly_date.dart';

import '../test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

VectorDrawing svgOf(String id, String folder) =>
    parseColoringSvg(File('assets/drawings/$folder/$id.svg').readAsStringSync());

final gato = svgOf('animal_gato', 'animals');

Future<void> paint(WidgetTester tester, VectorDrawing d, String region, String color) async {
  await tapAndSettle(tester, find.bySemanticsLabel(color));
  await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, region)));
  await tester.pump();
}

/// Colores que muestra el lienzo abierto.
Color? canvasColor(WidgetTester tester, String region) =>
    (tester.widget<CustomPaint>(drawingCanvasFinder).painter! as DrawingPainter).colors.colorOf(region);

/// Miniaturas de «Mis dibujos» (pintor + colores fijos).
List<DrawingPainter> thumbnails(WidgetTester tester) => tester
    .widgetList<CustomPaint>(
      find.descendant(of: find.byType(SavedDrawingsScreen), matching: find.byType(CustomPaint)),
    )
    .map((w) => w.painter)
    .whereType<DrawingPainter>()
    .toList();

Finder card(String name) => find.bySemanticsLabel(RegExp('^${RegExp.escape(name)}\\. '));

/// Reinicia la app sobre el mismo almacenamiento (como cerrarla y abrirla).
Future<KeyValueCreationStore> restartApp(WidgetTester tester, MemoryBackend backend) async {
  await tester.pumpWidget(const SizedBox());
  await tester.pump(const Duration(seconds: 1));
  final store = KeyValueCreationStore(backend);
  await pumpApp(tester, store: store);
  return store;
}

void main() {
  testWidgets('1-3, 6. pintar, salir, cerrar la app y recuperar exactamente los colores', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final backend = MemoryBackend();
    await pumpApp(tester, store: KeyValueCreationStore(backend));
    await startPainting(tester);
    await paint(tester, gato, 'cuerpo', 'Naranja');
    await paint(tester, gato, 'cabeza', 'Naranja');
    await paint(tester, gato, 'barriga', 'Amarillo');
    await paint(tester, gato, 'fondo', 'Celeste');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));

    await restartApp(tester, backend);
    await openMyGallery(tester);
    expect(card('Gato'), findsOneWidget);
    expect(find.text('Hoy'), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp('Sin terminar')), findsOneWidget);

    await tapAndSettle(tester, card('Gato'));
    expect(find.byType(ColoringScreen), findsOneWidget);
    expect(canvasColor(tester, 'cuerpo'), const Color(0xFFFF8F00));
    expect(canvasColor(tester, 'cabeza'), const Color(0xFFFF8F00));
    expect(canvasColor(tester, 'barriga'), const Color(0xFFFFD600));
    expect(canvasColor(tester, 'fondo'), const Color(0xFF29B6F6));
    expect(canvasColor(tester, 'cola'), isNull);
  });

  testWidgets('4-5, 7. dos dibujos separados; actualizar una creación actualiza su miniatura', (
    tester,
  ) async {
    setScreenSize(tester, const Size(420, 900));
    final store = InMemoryCreationStore();
    await pumpApp(tester, store: store);
    await startPainting(tester); // gato
    await paint(tester, gato, 'cabeza', 'Rojo');
    await tapAndSettle(tester, find.bySemanticsLabel('Otro dibujo'));
    await tapAndSettle(tester, find.bySemanticsLabel('Perro'));
    final perro = svgOf('animal_perro', 'animals');
    await paint(tester, perro, 'cabeza', 'Azul');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));

    await openMyGallery(tester);
    expect(card('Gato'), findsOneWidget);
    expect(card('Perro'), findsOneWidget);
    Color? thumbColor(String drawingId) =>
        thumbnails(tester)
            .firstWhere((p) => p.drawing.regions.length == svgOf(drawingId, 'animals').regions.length)
            .colors
            .colorOf('cabeza');
    expect(thumbColor('animal_gato'), const Color(0xFFE53935));
    expect(thumbColor('animal_perro'), const Color(0xFF1E57C8));

    // Actualizar el gato: la misma creación, con otro color.
    await tapAndSettle(tester, card('Gato'));
    await paint(tester, gato, 'cabeza', 'Verde');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(thumbColor('animal_gato'), const Color(0xFF2E7D32));
    expect(thumbColor('animal_perro'), const Color(0xFF1E57C8));
    expect((await store.loadAll()).creations, hasLength(2)); // no se duplicó
  });

  testWidgets('«¡Terminado!» solo cuando todas las zonas tienen color', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
    await tapAndSettle(tester, find.bySemanticsLabel('Frutas, 5 dibujos'));
    await tapAndSettle(tester, find.bySemanticsLabel('Plátano. Dificultad fácil'));
    final platano = svgOf('fruta_platano', 'fruits');
    await paint(tester, platano, 'platano', 'Amarillo');
    await paint(tester, platano, 'tallo', 'Marrón');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a categorías'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    await openMyGallery(tester);
    expect(find.text('¡Terminado!'), findsNothing);

    await tapAndSettle(tester, card('Plátano'));
    await paint(tester, platano, 'punta', 'Marrón');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.text('¡Terminado!'), findsOneWidget);
  });

  testWidgets('«Pintar otra vez» crea una versión nueva sin tocar la anterior', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final store = InMemoryCreationStore();
    await pumpApp(tester, store: store);
    await startPainting(tester);
    await paint(tester, gato, 'cabeza', 'Rojo');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await openMyGallery(tester);

    await tapAndSettle(tester, find.bySemanticsLabel('Pintar otra vez'));
    expect(canvasColor(tester, 'cabeza'), isNull); // empieza desde el original
    await paint(tester, gato, 'cuerpo', 'Azul');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));

    expect(card('Gato'), findsNWidgets(2));
    final creations = (await store.loadAll()).creations;
    expect(creations.map((c) => c.regionColors.keys.single), ['cuerpo', 'cabeza']);
  });

  testWidgets('8. borrar pide confirmación y no afecta al catálogo ni a otras creaciones', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final store = InMemoryCreationStore();
    await pumpApp(tester, store: store);
    await startPainting(tester);
    await paint(tester, gato, 'cabeza', 'Rojo');
    await tapAndSettle(tester, find.bySemanticsLabel('Otro dibujo'));
    await tapAndSettle(tester, find.bySemanticsLabel('Perro'));
    await paint(tester, svgOf('animal_perro', 'animals'), 'cabeza', 'Azul');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await openMyGallery(tester);

    // Las tarjetas están ordenadas por fecha: el perro es el primero.
    await tapAndSettle(tester, find.bySemanticsLabel('Borrar').first);
    expect(find.text('¿Borrar este dibujo pintado?'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('No, guardarlo'));
    expect(card('Perro'), findsOneWidget);

    await tapAndSettle(tester, find.bySemanticsLabel('Borrar').first);
    await tapAndSettle(tester, find.bySemanticsLabel('Sí, borrar'));
    expect(card('Perro'), findsNothing);
    expect(card('Gato'), findsOneWidget);
    expect(await store.latestFor('animal_perro'), isNull);

    // El perro sigue en la galería y se puede volver a pintar.
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
    await tapAndSettle(tester, find.bySemanticsLabel('Animales, 11 dibujos'));
    await tapAndSettle(tester, find.bySemanticsLabel('Perro. Dificultad media'));
    expect(canvasColor(tester, 'cabeza'), isNull);
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('9. las creaciones dañadas no se muestran como válidas', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final backend = MemoryBackend();
    backend.data['creation.v2.animal_oso-roto'] = '{"format_version":2,"id":"animal_oso-ro';
    await pumpApp(tester, store: KeyValueCreationStore(backend));
    await openMyGallery(tester);
    expect(find.text('¡Tu galería te espera!'), findsOneWidget);
    expect(backend.data, contains('creation.v2.animal_oso-roto')); // se conserva
  });

  testWidgets('9b. la zona para adultos lista y elimina, con confirmación, los datos dañados', (
    tester,
  ) async {
    setScreenSize(tester, const Size(420, 900));
    final backend = MemoryBackend();
    backend.data['creation.v2.animal_oso-roto'] = 'dañado';
    final store = KeyValueCreationStore(backend);
    await pumpApp(tester, store: store);
    await tester.longPress(find.bySemanticsLabel('Zona para adultos'));
    await tester.pumpAndSettle();
    final q = tester.widget<Text>(find.textContaining('¿cuánto es')).data!;
    final m = RegExp(r'(\d+) × (\d+)').firstMatch(q)!;
    await tapAndSettle(tester, find.widgetWithText(OutlinedButton, '${int.parse(m[1]!) * int.parse(m[2]!)}'));
    expect(find.textContaining('1 registro(s) dañado(s)'), findsOneWidget);
    await tapAndSettle(tester, find.text('Eliminar datos dañados (1)'));
    await tapAndSettle(tester, find.text('Cancelar'));
    expect(backend.data, contains('creation.v2.animal_oso-roto'));
    await tapAndSettle(tester, find.text('Eliminar datos dañados (1)'));
    await tapAndSettle(tester, find.text('Eliminar'));
    expect(backend.data, isEmpty);
  });

  testWidgets('10. si el almacenamiento falla se avisa, se puede seguir pintando y reintentar', (
    tester,
  ) async {
    setScreenSize(tester, const Size(420, 900));
    final backend = MemoryBackend();
    await pumpApp(tester, store: KeyValueCreationStore(backend));
    await startPainting(tester);
    backend.failWrites = true;
    await paint(tester, gato, 'cabeza', 'Rojo');
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('No se guardó · Reintentar'), findsOneWidget);
    await paint(tester, gato, 'cola', 'Azul'); // se puede seguir pintando
    await tester.pump(const Duration(seconds: 1));
    backend.failWrites = false;
    await tapAndSettle(tester, find.text('No se guardó · Reintentar'));
    expect(find.text('Guardado'), findsOneWidget);
    expect(
      (await KeyValueCreationStore(backend).latestFor('animal_gato'))!.regionColors.keys,
      unorderedEquals(['cabeza', 'cola']),
    );
  });

  testWidgets('10b. si no se pueden leer los dibujos guardados se muestra un aviso con reintento', (
    tester,
  ) async {
    setScreenSize(tester, const Size(420, 900));
    final backend = MemoryBackend()..failReads = true;
    await pumpApp(tester, store: KeyValueCreationStore(backend));
    await openMyGallery(tester);
    expect(find.text('No pudimos abrir tus dibujos'), findsOneWidget);
    backend.failReads = false;
    await tapAndSettle(tester, find.text('Reintentar'));
    expect(find.text('¡Tu galería te espera!'), findsOneWidget);
  });

  testWidgets('11. se guarda al pasar a segundo plano, sin esperar al cierre', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final backend = MemoryBackend();
    await pumpApp(tester, store: KeyValueCreationStore(backend));
    await startPainting(tester);
    await paint(tester, gato, 'cola', 'Morado');
    expect(backend.data, isEmpty); // todavía dentro de la pausa de 0,6 s
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    await tester.pump();
    expect((await KeyValueCreationStore(backend).latestFor('animal_gato'))!.regionColors.keys, ['cola']);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('11b. el estado se mantiene al navegar entre pantallas', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
    await tapAndSettle(tester, find.bySemanticsLabel('Animales, 11 dibujos'));
    await tapAndSettle(tester, find.bySemanticsLabel('Gato. Dificultad fácil'));
    await paint(tester, gato, 'cola', 'Rosa');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a categorías'));
    await tapAndSettle(tester, find.bySemanticsLabel('Buscar dibujos'));
    await tester.enterText(find.byType(TextField), 'gato');
    await tester.pumpAndSettle();
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Gato\. Dificultad fácil')));
    expect(canvasColor(tester, 'cola'), const Color(0xFFF06292));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.byType(HomeScreen), findsNothing);
  });

  testWidgets('12. guardar y recuperar no usan la red', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final previous = HttpOverrides.current;
    final noNetwork = _NoNetwork();
    HttpOverrides.global = noNetwork;
    addTearDown(() => HttpOverrides.global = previous);

    final backend = MemoryBackend();
    await pumpApp(tester, store: KeyValueCreationStore(backend));
    await startPainting(tester);
    await paint(tester, gato, 'cabeza', 'Rojo');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await restartApp(tester, backend);
    await openMyGallery(tester);
    await tapAndSettle(tester, card('Gato'));
    expect(canvasColor(tester, 'cabeza'), const Color(0xFFE53935));
    expect(noNetwork.attempts, 0);
  });

  test('12b. la app no pide permiso de internet ni incluye paquetes de red', () {
    final manifest = File('android/app/src/main/AndroidManifest.xml').readAsStringSync();
    expect(manifest, isNot(contains('android.permission.INTERNET')));
    // Sin copia automática en la nube: las creaciones no salen del dispositivo.
    expect(manifest, contains('android:allowBackup="false"'));
    final pubspec = File('pubspec.yaml').readAsStringSync();
    final deps = RegExp(r'^dependencies:\n((?:  .*\n|\n)*?)\S', multiLine: true).firstMatch(pubspec)![1]!;
    for (final pkg in ['http:', 'dio:', 'firebase', 'analytics', 'cloud_']) {
      expect(deps, isNot(contains(pkg)), reason: pkg);
    }
  });

  test('fechas amables', () {
    final now = DateTime(2026, 10, 29, 18);
    expect(friendlyDate(DateTime(2026, 10, 29, 8), now: now), 'Hoy');
    expect(friendlyDate(DateTime(2026, 10, 28, 23), now: now), 'Ayer');
    expect(friendlyDate(DateTime(2026, 10, 25), now: now), 'Hace 4 días');
    expect(friendlyDate(DateTime(2026, 9, 3), now: now), '03/09/2026');
  });
}

class _NoNetwork extends HttpOverrides {
  int attempts = 0;

  @override
  HttpClient createHttpClient(SecurityContext? context) {
    attempts++;
    throw const SocketException('Sin conexión (prueba)');
  }
}
