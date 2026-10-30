import 'dart:convert';

import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/learning/learning_controller.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';
import 'package:pequenos_artistas/learning/learning_progress.dart';
import 'package:pequenos_artistas/learning/learning_store.dart';
import 'package:pequenos_artistas/learning/rewards.dart';
import 'package:pequenos_artistas/persistence/creation.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';

Future<LearningController> open(MemoryBackend backend) async {
  final c = LearningController(LearningStore(backend), clock: () => DateTime.utc(2026, 10, 30, 9));
  await c.load();
  return c;
}

void main() {
  test('sin datos: nivel inicial, sonidos y voz activados, sin premios', () async {
    final c = await open(MemoryBackend());
    expect(c.settings.level, LearningLevel.initial);
    expect(c.settings.soundOn && c.settings.voiceOn, isTrue);
    expect(c.progress.rewards, isEmpty);
    expect(c.progress.stars, 0);
  });

  test('las preferencias se conservan al reiniciar', () async {
    final backend = MemoryBackend();
    final c = await open(backend);
    await c.updateSettings(
      c.settings.copyWith(soundOn: false, voiceOn: false, level: LearningLevel.advanced),
    );
    final again = await open(backend);
    expect(again.settings.soundOn, isFalse);
    expect(again.settings.voiceOn, isFalse);
    expect(again.settings.level, LearningLevel.advanced);
  });

  test('los premios se conceden una sola vez y no desaparecen al reiniciar', () async {
    final backend = MemoryBackend();
    final c = await open(backend);
    final first = await c.recordSession(GameId.colors, completed: true, points: 4);
    expect(first.map((r) => r.id), unorderedEquals(['primera_actividad', 'explorador_colores']));
    final second = await c.recordSession(GameId.colors, completed: true, points: 4);
    expect(second, isEmpty);
    final again = await open(backend);
    expect(again.progress.rewards.keys, unorderedEquals(['primera_actividad', 'explorador_colores']));
    expect(again.progress.game(GameId.colors).sessions, 2);
    expect(again.progress.stars, 8);
  });

  test('cada juego tiene su propio progreso', () async {
    final c = await open(MemoryBackend());
    await c.recordSession(GameId.shapes, completed: true, points: 5);
    expect(c.progress.game(GameId.shapes).sessions, 1);
    expect(c.progress.game(GameId.shapes).questions, 5);
    for (final g in [GameId.colors, GameId.animals, GameId.memory]) {
      expect(c.progress.game(g).sessions, 0, reason: g.id);
      expect(c.progress.game(g).questions, 0, reason: g.id);
    }
  });

  test('premios de constancia: cinco actividades y todos los juegos', () async {
    final c = await open(MemoryBackend());
    final all = <String>[];
    for (final g in [GameId.colors, GameId.colors, GameId.shapes, GameId.animals]) {
      all.addAll((await c.recordSession(g, completed: true, points: 1)).map((r) => r.id));
    }
    expect(all, isNot(contains('cinco_actividades')));
    expect(all, isNot(contains('todos_los_juegos')));
    final fifth = (await c.recordSession(GameId.memory, completed: true, points: 2)).map((r) => r.id);
    expect(fifth, containsAll(['maestro_parejas', 'cinco_actividades']));
    expect(fifth, isNot(contains('todos_los_juegos')), reason: 'faltan los juegos nuevos');
    expect((await c.recordSession(GameId.puzzle, completed: true, points: 3)).map((r) => r.id), [
      'maestro_rompecabezas',
    ]);
    expect((await c.recordSession(GameId.maze, completed: true, points: 3)).map((r) => r.id), [
      'explorador_laberintos',
    ]);
    final last = (await c.recordSession(GameId.tracing, completed: true, points: 3)).map((r) => r.id);
    expect(last, containsAll(['pequeno_escritor', 'todos_los_juegos']));
    expect(c.progress.rewards, hasLength(rewards.length));
  });

  test('una partida abandonada suma lo acertado pero no cuenta como terminada', () async {
    final c = await open(MemoryBackend());
    final earned = await c.recordSession(GameId.animals, completed: false, points: 2);
    expect(earned, isEmpty);
    expect(c.progress.game(GameId.animals).sessions, 0);
    expect(c.progress.game(GameId.animals).questions, 2);
    expect(c.progress.stars, 2);
    expect(await c.recordSession(GameId.animals, completed: false, points: 0), isEmpty);
  });

  test('progreso dañado: se usa la copia de seguridad', () async {
    final backend = MemoryBackend();
    final c = await open(backend);
    await c.recordSession(GameId.colors, completed: true, points: 4);
    await c.recordSession(GameId.shapes, completed: true, points: 4);
    backend.data[LearningStore.key] = '{"roto": tr';
    final again = await open(backend);
    expect(again.recoveredFromBackup, isTrue);
    expect(again.progress.game(GameId.colors).sessions, 1); // versión anterior válida
  });

  test('todo dañado: se empieza de cero sin borrar los datos dañados', () async {
    final backend = MemoryBackend()..data[LearningStore.key] = 'basura';
    final c = await open(backend);
    expect(c.startedFromDamagedData, isTrue);
    expect(c.progress.totalSessions, 0);
    expect(backend.data[LearningStore.damagedKey], 'basura');
  });

  test('campos ausentes o no válidos toman valores por defecto sin perder lo demás', () {
    final p = LearningProgress.fromJson(
      jsonDecode('''{
      "format_version": 1,
      "settings": {"sound_on": "sí", "level": "experto"},
      "games": {"colores": {"sessions": 3, "questions": -1}, "juego_raro": {"sessions": 9}},
      "rewards": {"explorador_colores": "2026-10-01T00:00:00Z", "malo": 5},
      "stars": "muchas"
    }''') as Map<String, dynamic>,
    );
    expect(p.settings.soundOn, isTrue);
    expect(p.settings.level, LearningLevel.initial);
    expect(p.game(GameId.colors).sessions, 3);
    expect(p.game(GameId.colors).questions, 0);
    expect(p.rewards.keys, ['explorador_colores']);
    expect(p.stars, 0);
  });

  test('si el almacenamiento falla se sigue jugando y se reintenta', () async {
    final backend = MemoryBackend();
    final c = await open(backend);
    backend.failWrites = true;
    final earned = await c.recordSession(GameId.colors, completed: true, points: 4);
    expect(earned, isNotEmpty);
    expect(c.saveFailed, isTrue);
    backend.failWrites = false;
    await c.recordSession(GameId.colors, completed: true, points: 4);
    expect(c.saveFailed, isFalse);
    expect((await open(backend)).progress.game(GameId.colors).sessions, 2);
  });

  test('no toca las creaciones de la Fase 5 que comparten almacenamiento', () async {
    final backend = MemoryBackend();
    final creations = KeyValueCreationStore(backend);
    final t = DateTime.utc(2026, 10, 29);
    await creations.save(
      Creation(
        id: 'animal_gato-1',
        drawingId: 'animal_gato',
        regionColors: const {'cola': Color(0xFFE53935)},
        createdAt: t,
        updatedAt: t,
        totalRegions: 11,
      ),
    );
    final c = await open(backend);
    await c.updateSettings(c.settings.copyWith(level: LearningLevel.intermediate));
    await c.recordSession(GameId.memory, completed: true, points: 2);
    final report = await creations.loadAll();
    expect(report.creations.single.regionColors, {'cola': const Color(0xFFE53935)});
    expect(report.problems, isEmpty); // las claves learning.* no se confunden
  });
}
