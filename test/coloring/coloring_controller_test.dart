import 'dart:convert';
import 'dart:io';

import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/coloring_controller.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/services/drawing_loader.dart';
import 'package:pequenos_artistas/persistence/creation.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import '../test_helpers.dart';

PaletteColor paletteColor(String name) => kidPalette.firstWhere((c) => c.name == name);

final red = paletteColor('Rojo');
final blue = paletteColor('Azul');
final green = paletteColor('Verde');
final white = paletteColor('Blanco');

const gatoFile = 'assets/drawings/animals/animal_gato.svg';
const perroFile = 'assets/drawings/animals/animal_perro.svg';

Future<ColoringController> openDrawing(
  String id,
  String file, {
  CreationStore? store,
  DrawingLoader? loader,
}) async {
  final c = ColoringController(
    drawingId: id,
    file: file,
    loader: loader ?? diskDrawingLoader(),
    store: store ?? InMemoryCreationStore(),
    saveDelay: Duration.zero,
  );
  await c.load();
  return c;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Pintar regiones', () {
    test('1. tocar una región la rellena con el color elegido', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      expect(c.status, ColoringStatus.ready);
      c.selectColor(red);
      expect(c.tapRegion('cuerpo'), isTrue);
      expect(c.colorOf('cuerpo'), red.color);
      expect(c.selectedRegion, 'cuerpo');
    });

    test('1b. tocar por coordenadas pinta la región que se ve en ese punto', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      final p = interiorPoint(c.drawing!, 'barriga');
      c.selectColor(blue);
      expect(c.tapAt(p), 'barriga');
      expect(c.colorOf('barriga'), blue.color);
      // La barriga está encima del cuerpo: el cuerpo no cambia.
      expect(c.colorOf('cuerpo'), isNull);
    });

    test('2. las regiones vecinas no cambian', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      c.selectColor(red);
      c.tapRegion('cabeza');
      expect(c.regionColors, {'cabeza': red.color});
      for (final r in c.drawing!.regions.where((r) => r.id != 'cabeza')) {
        expect(c.colorOf(r.id), isNull, reason: r.id);
      }
    });

    test('4. una región puede cambiar de color varias veces; los demás colores se conservan', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      c.selectColor(red);
      c.tapRegion('cola');
      for (final color in [blue, green, red, blue]) {
        c.selectColor(color);
        c.tapRegion('cabeza');
        expect(c.colorOf('cabeza'), color.color);
        expect(c.colorOf('cola'), red.color);
      }
    });

    test('tocar con el mismo color no añade pasos al historial', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      c.selectColor(red);
      expect(c.tapRegion('cola'), isTrue);
      expect(c.tapRegion('cola'), isFalse);
      c.undo();
      expect(c.canUndo, isFalse);
      expect(c.colorOf('cola'), isNull);
    });

    test('una región desconocida se ignora', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      expect(c.tapRegion('no_existe'), isFalse);
      expect(c.hasColoring, isFalse);
    });
  });

  group('Herramientas', () {
    test('5. el borrador y el blanco devuelven la región a su estado original', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      c.selectColor(red);
      c.tapRegion('cola');
      c.tapRegion('cabeza');
      c.toggleEraser();
      expect(c.tool, ColoringTool.eraser);
      c.tapRegion('cola');
      expect(c.colorOf('cola'), isNull);
      expect(c.colorOf('cabeza'), red.color);
      c.selectColor(white);
      expect(c.tool, ColoringTool.paint);
      c.tapRegion('cabeza');
      expect(c.colorOf('cabeza'), isNull);
      expect(c.hasColoring, isFalse);
    });

    test('6. deshacer y rehacer restauran el estado esperado', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      c.selectColor(red);
      c.tapRegion('cola'); // 1
      c.selectColor(blue);
      c.tapRegion('cola'); // 2
      c.tapRegion('cabeza'); // 3
      expect(c.regionColors, {'cola': blue.color, 'cabeza': blue.color});

      c.undo();
      expect(c.regionColors, {'cola': blue.color});
      c.undo();
      expect(c.regionColors, {'cola': red.color});
      c.undo();
      expect(c.regionColors, isEmpty);
      expect(c.canUndo, isFalse);
      c.undo(); // sin efecto
      expect(c.regionColors, isEmpty);

      c.redo();
      c.redo();
      expect(c.regionColors, {'cola': blue.color});
      expect(c.canRedo, isTrue);

      // Un cambio nuevo descarta lo que se podía rehacer.
      c.selectColor(green);
      c.tapRegion('cuerpo');
      expect(c.canRedo, isFalse);
      expect(c.regionColors, {'cola': blue.color, 'cuerpo': green.color});
    });

    test('7. limpiar restaura el dibujo y se puede deshacer', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      c.selectColor(red);
      for (final r in ['cola', 'cuerpo', 'cabeza', 'fondo']) {
        c.tapRegion(r);
      }
      c.clear();
      expect(c.regionColors, isEmpty);
      expect(c.hasColoring, isFalse);
      c.undo();
      expect(c.regionColors.keys, unorderedEquals(['cola', 'cuerpo', 'cabeza', 'fondo']));
      c.redo();
      expect(c.regionColors, isEmpty);
    });

    test('el historial tiene un límite y no crece sin control', () async {
      final c = await openDrawing('animal_gato', gatoFile);
      for (var i = 0; i < 150; i++) {
        c.selectColor(i.isEven ? red : blue);
        c.tapRegion('cola');
      }
      var steps = 0;
      while (c.canUndo) {
        c.undo();
        steps++;
      }
      expect(steps, 100);
    });
  });

  group('Sesiones y guardado', () {
    test('8. cambiar de dibujo no mezcla estados', () async {
      final store = InMemoryCreationStore();
      final gato = await openDrawing('animal_gato', gatoFile, store: store);
      gato.selectColor(red);
      gato.tapRegion('cabeza');
      await gato.save();
      gato.dispose();

      final perro = await openDrawing('animal_perro', perroFile, store: store);
      expect(perro.regionColors, isEmpty);
      expect(perro.canUndo, isFalse);
      perro.selectColor(blue);
      perro.tapRegion('cabeza');
      await perro.save();

      final gatoOtraVez = await openDrawing('animal_gato', gatoFile, store: store);
      expect(gatoOtraVez.regionColors, {'cabeza': red.color});
      expect(gatoOtraVez.canUndo, isFalse); // El historial no se guarda.
    });

    test('9. los colores guardados se recuperan (formato versionado con verificación)', () async {
      final store = InMemoryCreationStore();
      final c = await openDrawing('animal_gato', gatoFile, store: store);
      c.selectColor(red);
      c.tapRegion('cola');
      c.selectColor(paletteColor('Celeste'));
      c.tapRegion('fondo');
      expect(c.hasUnsavedChanges, isTrue);
      await c.save();
      expect(c.hasUnsavedChanges, isFalse);
      expect(c.saveState, SaveState.saved);

      final raw = store.memory.data[KeyValueCreationStore.keyFor(c.activeCreationId!)]!;
      final json = jsonDecode(raw) as Map<String, dynamic>;
      expect(json['format_version'], Creation.formatVersion);
      expect(json['drawing_id'], 'animal_gato');
      expect(json['total_regions'], 11);
      expect(json['painted_regions'], 1); // el fondo no cuenta
      expect(json['status'], 'en_progreso');
      expect(json['checksum'], isA<String>());
      expect(json['regions'], {'cola': '#FFE53935', 'fondo': '#FF29B6F6'});

      final again = await openDrawing('animal_gato', gatoFile, store: store);
      expect(again.regionColors, c.regionColors);
      expect(again.activeCreationId, c.activeCreationId);
    });

    testWidgets('9b. el guardado automático se hace tras una pausa y al cerrar', (tester) async {
      final store = InMemoryCreationStore();
      final c = ColoringController(
        drawingId: 'animal_gato',
        file: gatoFile,
        loader: diskDrawingLoader(),
        store: store,
        saveDelay: const Duration(milliseconds: 600),
      );
      await c.load();
      c.tapRegion('cola');
      expect(c.saveState, SaveState.pending);
      await tester.pump(const Duration(milliseconds: 300));
      expect(store.memory.data, isEmpty);
      await tester.pump(const Duration(milliseconds: 400));
      expect((await store.latestFor('animal_gato'))!.regionColors.keys, ['cola']);
      expect(c.saveState, SaveState.saved);

      c.tapRegion('cabeza');
      c.dispose(); // Se guarda al salir aunque no haya pasado la pausa.
      await tester.pump();
      expect((await store.latestFor('animal_gato'))!.regionColors.keys, unorderedEquals(['cola', 'cabeza']));
    });

    test('limpiar y guardar borra la creación (y solo esa)', () async {
      final store = InMemoryCreationStore();
      final perro = await openDrawing('animal_perro', perroFile, store: store);
      perro.tapRegion('cabeza');
      await perro.save();
      final c = await openDrawing('animal_gato', gatoFile, store: store);
      c.tapRegion('cola');
      await c.save();
      c.clear();
      await c.save();
      expect(await store.latestFor('animal_gato'), isNull);
      expect(await store.latestFor('animal_perro'), isNotNull);
    });

    test('regiones o colores no válidos en datos de la versión 1 se migran sin ellos', () async {
      final store = InMemoryCreationStore();
      store.memory.data['progress.v1.animal_gato'] = jsonEncode({
        'format_version': 1,
        'drawing_id': 'animal_gato',
        'updated_at': '2026-01-01T00:00:00Z',
        'regions': {'cola': '#FFE53935', 'region_borrada': '#FF000000', 'cabeza': 'rojo'},
      });
      final c = await openDrawing('animal_gato', gatoFile, store: store);
      expect(c.regionColors, {'cola': const Color(0xFFE53935)});
    });

    test('una creación dañada no se usa, no se borra y se puede empezar otra', () async {
      final store = InMemoryCreationStore();
      store.memory.data['creation.v2.animal_gato-roto'] = '{"format_version": 2, "id": "animal_gato-ro';
      final c = await openDrawing('animal_gato', gatoFile, store: store);
      expect(c.status, ColoringStatus.ready);
      expect(c.regionColors, isEmpty);
      expect(store.memory.data, contains('creation.v2.animal_gato-roto'));
    });

    test('almacén real con shared_preferences: guarda, lista y borra', () async {
      SharedPreferencesAsyncPlatform.instance = InMemorySharedPreferencesAsync.empty();
      final store = KeyValueCreationStore(SharedPreferencesBackend(SharedPreferencesAsync()));
      final c = await openDrawing('animal_gato', gatoFile, store: store);
      c.tapRegion('cola');
      await c.save();
      final p = await openDrawing('animal_perro', perroFile, store: store);
      p.tapRegion('cabeza');
      await p.save();

      final all = (await store.loadAll()).creations;
      expect(all.map((e) => e.drawingId), ['animal_perro', 'animal_gato']);
      expect((await store.load(c.activeCreationId!))!.regionColors.keys, ['cola']);
      await store.delete(c.activeCreationId!);
      expect(await store.load(c.activeCreationId!), isNull);
      expect(await store.latestFor('animal_perro'), isNotNull);
    });
  });

  group('12. Errores de carga manejables', () {
    test('un SVG que no existe deja la sesión en estado de error', () async {
      final c = await openDrawing('x', 'assets/drawings/animals/no_existe.svg');
      expect(c.status, ColoringStatus.error);
      expect(c.errorMessage, contains('no existe'));
      expect(c.tapRegion('cola'), isFalse);
      expect(c.coloringEngineReady, isFalse);
    });

    test('un SVG dañado deja la sesión en estado de error', () async {
      const file = 'assets/drawings/roto.svg';
      final c = await openDrawing(
        'x',
        file,
        loader: diskDrawingLoader({
          file: '<svg viewBox="0 0 1024 1024"><g id="regiones"><path id="a" d="M0,0 L1,1"/></g></svg>',
        }),
      );
      expect(c.status, ColoringStatus.error);
      expect(c.errorMessage, contains('cerrado'));
    });

    test('un fallo del almacén no impide pintar y se reintenta', () async {
      final store = InMemoryCreationStore()..memory.failReads = true;
      store.memory.failWrites = true;
      final c = await openDrawing('animal_gato', gatoFile, store: store);
      expect(c.status, ColoringStatus.ready);
      c.tapRegion('cola');
      await c.save();
      expect(c.hasUnsavedChanges, isTrue);
      expect(c.saveState, SaveState.failed);
      expect(c.colorOf('cola'), red.color);
      store.memory
        ..failReads = false
        ..failWrites = false;
      await c.save(); // «Reintentar»
      expect(c.saveState, SaveState.saved);
      expect((await store.latestFor('animal_gato'))!.regionColors.keys, ['cola']);
    });

    test('el cargador no guarda los fallos: se puede reintentar', () async {
      final files = <String, String>{};
      final loader = DrawingLoader(bundle: MemoryBundle(files));
      await expectLater(loader.load('a.svg'), throwsA(isA<DrawingLoadException>()));
      files['a.svg'] = File(gatoFile).readAsStringSync();
      expect((await loader.load('a.svg')).regions, isNotEmpty);
    });
  });
}
