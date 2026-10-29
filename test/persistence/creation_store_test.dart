import 'dart:convert';
import 'dart:io';
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/persistence/creation.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';

const red = Color(0xFFE53935);
const blue = Color(0xFF1E57C8);
const green = Color(0xFF2E7D32);

Creation creation(String id, String drawing, Map<String, Color> colors, {int total = 11, DateTime? at}) {
  final t = at ?? DateTime.utc(2026, 10, 29, 10);
  return Creation(
    id: id,
    drawingId: drawing,
    regionColors: colors,
    createdAt: t,
    updatedAt: t,
    totalRegions: total,
  );
}

void main() {
  group('Formato de una creación', () {
    test('se codifica y decodifica sin perder nada', () {
      final c = creation('gato-1', 'animal_gato', {'cola': red, 'cabeza': blue, 'fondo': green});
      final back = Creation.decode(c.encode());
      expect(back.id, 'gato-1');
      expect(back.drawingId, 'animal_gato');
      expect(back.regionColors, c.regionColors);
      expect(back.createdAt, c.createdAt);
      expect(back.updatedAt, c.updatedAt);
      expect(back.totalRegions, 11);
    });

    test('estado: sin comenzar, en progreso y terminado (el fondo no cuenta)', () {
      expect(creation('a', 'd', {}).status, CreationStatus.notStarted);
      expect(creation('a', 'd', {'fondo': red}, total: 2).status, CreationStatus.inProgress);
      expect(creation('a', 'd', {'x': red}, total: 2).status, CreationStatus.inProgress);
      final done = creation('a', 'd', {'x': red, 'y': blue, 'fondo': green}, total: 2);
      expect(done.status, CreationStatus.completed);
      expect(done.progress, 1.0);
      expect(creation('a', 'd', {'x': red}, total: 4).progress, 0.25);
      // Total desconocido (migrado): nunca se marca como terminado.
      expect(creation('a', 'd', {'x': red}, total: 0).status, CreationStatus.inProgress);
      expect(creation('a', 'd', {'x': red}, total: 0).progress, isNull);
    });

    test('detecta datos incompletos, alterados o de otra versión', () {
      final raw = creation('gato-1', 'animal_gato', {'cola': red}).encode();
      final cases = {
        'truncado': raw.substring(0, raw.length ~/ 2),
        'alterado': raw.replaceFirst('#FFE53935', '#FF000000'),
        'sin suma': jsonEncode((jsonDecode(raw) as Map)..remove('checksum')),
        'versión': raw.replaceFirst('"format_version":2', '"format_version":3'),
        'vacío': '',
        'no objeto': '[1,2]',
      };
      cases.forEach((name, value) {
        expect(() => Creation.decode(value), throwsFormatException, reason: name);
      });
    });
  });

  group('Almacén de creaciones', () {
    late MemoryBackend backend;
    late KeyValueCreationStore store;
    setUp(() {
      backend = MemoryBackend();
      store = KeyValueCreationStore(backend);
    });

    test('1-3. guarda varias regiones y recupera exactamente los mismos colores', () async {
      final colors = {'cola': red, 'cabeza': blue, 'barriga': green, 'fondo': red};
      await store.save(creation('gato-1', 'animal_gato', colors));
      // Un almacén nuevo sobre los mismos datos = la app vuelve a abrirse.
      final reopened = KeyValueCreationStore(backend);
      expect((await reopened.load('gato-1'))!.regionColors, colors);
      expect((await reopened.latestFor('animal_gato'))!.id, 'gato-1');
    });

    test('4. dos dibujos se guardan por separado', () async {
      await store.save(creation('gato-1', 'animal_gato', {'cabeza': red}));
      await store.save(creation('perro-1', 'animal_perro', {'cabeza': blue}));
      expect((await store.latestFor('animal_gato'))!.regionColors, {'cabeza': red});
      expect((await store.latestFor('animal_perro'))!.regionColors, {'cabeza': blue});
      expect(backend.data.keys.where((k) => !k.endsWith('.bak')), hasLength(2));
    });

    test('5. actualizar una creación conserva una sola entrada y guarda copia de la anterior', () async {
      final first = creation('gato-1', 'animal_gato', {'cola': red});
      await store.save(first);
      final second = Creation(
        id: 'gato-1',
        drawingId: 'animal_gato',
        regionColors: {'cola': red, 'cabeza': blue},
        createdAt: first.createdAt,
        updatedAt: first.updatedAt.add(const Duration(minutes: 5)),
        totalRegions: 11,
      );
      await store.save(second);
      final report = await store.loadAll();
      expect(report.creations, hasLength(1));
      expect(report.creations.single.regionColors, second.regionColors);
      expect(report.creations.single.createdAt, first.createdAt);
      final backup = Creation.decode(backend.data['${KeyValueCreationStore.keyFor('gato-1')}.bak']!);
      expect(backup.regionColors, first.regionColors);
    });

    test('las creaciones se listan de la más reciente a la más antigua', () async {
      await store.save(creation('a-1', 'animal_gato', {'x': red}, at: DateTime.utc(2026, 1, 1)));
      await store.save(creation('b-1', 'animal_perro', {'x': red}, at: DateTime.utc(2026, 3, 1)));
      await store.save(creation('c-1', 'animal_oso', {'x': red}, at: DateTime.utc(2026, 2, 1)));
      expect((await store.loadAll()).creations.map((c) => c.id), ['b-1', 'c-1', 'a-1']);
    });

    test('8. borrar una creación no toca las demás ni el dibujo original', () async {
      final svg = File('assets/drawings/animals/animal_gato.svg');
      final before = svg.readAsStringSync();
      await store.save(creation('gato-1', 'animal_gato', {'cola': red}));
      await store.save(creation('gato-2', 'animal_gato', {'cola': blue}));
      await store.save(creation('gato-2', 'animal_gato', {'cola': green})); // crea .bak
      await store.delete('gato-2');
      expect(backend.data.keys.where((k) => k.contains('gato-2')), isEmpty);
      expect((await store.loadAll()).creations.map((c) => c.id), ['gato-1']);
      expect(svg.readAsStringSync(), before);
    });

    group('9. Datos dañados o incompletos', () {
      test('una escritura interrumpida no destruye la versión válida anterior', () async {
        await store.save(creation('gato-1', 'animal_gato', {'cola': red}));
        backend.truncateWritesTo = 40;
        await expectLater(
          store.save(creation('gato-1', 'animal_gato', {'cola': blue})),
          throwsA(isA<StorageException>()),
        );
        backend.truncateWritesTo = null;
        var loaded = await KeyValueCreationStore(backend).load('gato-1');
        expect(loaded!.regionColors, {'cola': red}, reason: 'falló la copia: la principal no se tocó');

        // Ahora solo falla la escritura de la principal (la copia sí se completa).
        await store.save(creation('gato-1', 'animal_gato', {'cola': green}));
        final good = backend.data[KeyValueCreationStore.keyFor('gato-1')]!;
        backend.truncateWritesTo = good.length + 5; // la copia (= good) cabe; la nueva, no
        await expectLater(
          store.save(creation('gato-1', 'animal_gato', {'cola': blue, 'cabeza': blue, 'barriga': blue})),
          throwsA(isA<StorageException>()),
        );
        backend.truncateWritesTo = null;
        loaded = await KeyValueCreationStore(backend).load('gato-1');
        expect(loaded!.regionColors, {'cola': green}, reason: 'falló la principal: se usa la copia');
        // La principal quedó reparada con la copia de seguridad.
        expect(Creation.decode(backend.data[KeyValueCreationStore.keyFor('gato-1')]!).regionColors, {
          'cola': green,
        });
      });

      test('si la principal está dañada se usa la copia y se informa', () async {
        await store.save(creation('gato-1', 'animal_gato', {'cola': red}));
        await store.save(creation('gato-1', 'animal_gato', {'cola': blue}));
        backend.data[KeyValueCreationStore.keyFor('gato-1')] = '{"basura": tr';
        final report = await store.loadAll();
        expect(report.creations.single.regionColors, {'cola': red});
        expect(report.recovered, ['gato-1']);
        expect(report.problems, isEmpty);
      });

      test('si falta la principal pero hay copia, se recupera', () async {
        await store.save(creation('gato-1', 'animal_gato', {'cola': red}));
        await store.save(creation('gato-1', 'animal_gato', {'cola': blue}));
        backend.data.remove(KeyValueCreationStore.keyFor('gato-1'));
        final report = await store.loadAll();
        expect(report.creations.single.regionColors, {'cola': red});
        expect(report.recovered, ['gato-1']);
      });

      test('si todo está dañado se informa, no se muestra y NO se borra', () async {
        await store.save(creation('perro-1', 'animal_perro', {'cola': red}));
        backend.data['creation.v2.gato-1'] = 'xx';
        backend.data['creation.v2.gato-1.bak'] = 'yy';
        backend.data['creation.v2.otro-id'] = creation('distinto', 'animal_gato', {'x': red}).encode();
        final report = await store.loadAll();
        expect(report.creations.map((c) => c.id), ['perro-1']);
        expect(
          report.problems.map((p) => p.key),
          unorderedEquals(['creation.v2.gato-1', 'creation.v2.otro-id']),
        );
        expect(
          backend.data.keys,
          containsAll(['creation.v2.gato-1', 'creation.v2.gato-1.bak', 'creation.v2.otro-id']),
        );
      });

      test('solo un adulto, a propósito, elimina los datos dañados', () async {
        await store.save(creation('perro-1', 'animal_perro', {'cola': red}));
        backend.data['creation.v2.gato-1'] = 'xx';
        final problem = (await store.loadAll()).problems.single;
        await store.discardProblem(problem);
        expect(backend.data.keys, [KeyValueCreationStore.keyFor('perro-1')]);
      });
    });

    group('Migración del formato 1', () {
      String v1(String drawing, Map<String, String> regions) => jsonEncode({
        'format_version': 1,
        'drawing_id': drawing,
        'updated_at': '2026-10-20T08:00:00.000Z',
        'regions': regions,
      });

      test('convierte cada progreso antiguo en una creación y luego borra la clave antigua', () async {
        backend.data['progress.v1.animal_gato'] = v1('animal_gato', {'cola': '#FFE53935'});
        backend.data['progress.v1.animal_perro'] = v1('animal_perro', {'cabeza': '#FF1E57C8'});
        final report = await store.loadAll();
        expect(report.creations.map((c) => c.drawingId), unorderedEquals(['animal_gato', 'animal_perro']));
        expect((await store.latestFor('animal_gato'))!.regionColors, {'cola': red});
        expect(backend.data.keys.where((k) => k.startsWith('progress.v1.')), isEmpty);
        expect(report.problems, isEmpty);
      });

      test('los datos antiguos ilegibles se conservan y se informan', () async {
        backend.data['progress.v1.animal_gato'] = '{roto';
        final report = await store.loadAll();
        expect(report.creations, isEmpty);
        expect(report.problems.single.kind, StoredProblemKind.unmigrated);
        expect(backend.data, contains('progress.v1.animal_gato'));
      });

      test('si la escritura falla durante la migración, no se pierde nada y se reintenta', () async {
        backend.data['progress.v1.animal_gato'] = v1('animal_gato', {'cola': '#FFE53935'});
        backend.failWrites = true;
        await expectLater(store.loadAll(), completes);
        expect(backend.data, contains('progress.v1.animal_gato'));
        backend.failWrites = false;
        expect((await store.latestFor('animal_gato'))!.regionColors, {'cola': red});
        expect(backend.data.keys.where((k) => k.startsWith('progress.v1.')), isEmpty);
      });
    });

    group('10. Fallos del almacenamiento', () {
      test('leer o escribir con errores lanza StorageException sin borrar nada', () async {
        await store.save(creation('gato-1', 'animal_gato', {'cola': red}));
        final snapshot = Map.of(backend.data);
        backend.failWrites = true;
        await expectLater(
          store.save(creation('gato-1', 'animal_gato', {'cola': blue})),
          throwsA(isA<StorageException>()),
        );
        await expectLater(store.delete('gato-1'), throwsA(isA<StorageException>()));
        backend.failReads = true;
        await expectLater(store.loadAll(), throwsA(isA<StorageException>()));
        backend
          ..failReads = false
          ..failWrites = false;
        expect(backend.data, snapshot);
        expect((await store.load('gato-1'))!.regionColors, {'cola': red});
      });
    });

    test('los ids nuevos son únicos y válidos', () {
      final ids = {for (var i = 0; i < 200; i++) store.newCreationId('animal_gato')};
      expect(ids, hasLength(200));
      expect(ids.every(Creation.idPattern.hasMatch), isTrue);
      expect(ids.every((id) => id.startsWith('animal_gato-')), isTrue);
    });

    test('avisa de los cambios al guardar y al borrar', () async {
      var signals = 0;
      store.changes.addListener(() => signals++);
      await store.save(creation('gato-1', 'animal_gato', {'cola': red}));
      await store.delete('gato-1');
      expect(signals, 2);
    });
  });
}
