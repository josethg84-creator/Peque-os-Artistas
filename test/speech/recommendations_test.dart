import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/speech/mission.dart';
import 'package:pequenos_artistas/speech/recommendations.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';
import 'package:pequenos_artistas/speech/speech_progress.dart';

import 'content_fixture.dart';

void main() {
  late SpeechContent content;
  setUpAll(() async => content = await fullContent());
  final day = DateTime(2026, 11, 3, 10);

  List<String> ids(SpeechProgress p, {DateTime? now, Duration time = Duration.zero}) =>
      recommendActivities(p, content, now: now ?? day, sessionTime: time).map((r) => r.id).toList();

  test('al empezar: primeras palabras y primera oración, siempre igual con los mismos datos', () {
    final first = ids(SpeechProgress());
    expect(first, hasLength(3));
    expect(first.take(2), ['palabras:familia', 'oracion:primera']);
    expect(ids(SpeechProgress()), first);
  });

  test('si practica mucho los animales, Lolo propone nuevas palabras de animales', () {
    final p = SpeechProgress(wordsHeard: {'perro', 'gato', 'conejo', 'mama'});
    final r = recommendActivities(p, content, now: day).first;
    expect(r.lolo, '¡Hoy podemos aprender nuevas palabras de animales!');
    expect((r.args! as SpeechWordsArgs).categoryId, 'animales');
    expect(r.reason, contains('3 palabras'));
  });

  test('un grupo favorito elegido por un adulto va primero', () {
    final p = SpeechProgress(wordsHeard: {'perro', 'gato'})..preferences.favoriteCategories.add('naturaleza');
    final r = recommendActivities(p, content, now: day).first;
    expect(r.id, 'palabras:naturaleza');
    expect(r.reason, contains('ajustes'));
  });

  test('con oraciones construidas propone formar una más larga', () {
    final p = SpeechProgress(sentencesBuilt: {'a', 'b', 'c'});
    final r = recommendActivities(
      p,
      content,
      now: day,
      max: 10,
    ).firstWhere((x) => x.id.startsWith('oracion'));
    expect(r.lolo, contains('oración más larga'));
    expect(r.route, AppRoutes.speechMyStory);
  });

  test('pedir repetir ofrece más práctica, sin penalizar', () {
    final p = SpeechProgress(repeats: {AppRoutes.speechListeningLevel: 4, AppRoutes.speechComplete: 1});
    final r = recommendActivities(p, content, now: day).first;
    expect(r.id, 'repetir:${AppRoutes.speechListeningLevel}');
    expect(r.lolo, contains('todas las veces que quieras'));
  });

  test('pasado el tiempo sugerido, propone un descanso', () {
    final p = SpeechProgress()..preferences.minutes = 5;
    expect(ids(p, time: const Duration(minutes: 4)), isNot(contains('descanso')));
    expect(ids(p, time: const Duration(minutes: 6)).first, 'descanso');
  });

  test('el resto varía con el día sin azar', () {
    final p = SpeechProgress(wordsHeard: {'perro'});
    final a = recommendActivities(p, content, now: day, max: 20).map((r) => r.id).toList();
    final b = recommendActivities(
      p,
      content,
      now: day.add(const Duration(days: 1)),
      max: 20,
    ).map((r) => r.id).toList();
    expect(a.toSet(), b.toSet());
    expect(a, isNot(b));
    expect(recommendActivities(p, content, now: day, max: 20).map((r) => r.id).toList(), a);
  });

  test('el nivel de escucha sigue al último terminado o al de los ajustes', () {
    final p = SpeechProgress()..preferences.level = 2;
    expect(nextListeningLevel(p), 2);
    p.activitiesDone['escucho_nivel_1'] = 1;
    expect(nextListeningLevel(p), 2);
    p.activitiesDone['escucho_nivel_2'] = 1;
    expect(nextListeningLevel(p), 3);
  });

  test('favoritas: las actividades más abiertas', () {
    final p = SpeechProgress(
      visits: {
        AppRoutes.speechStories: 5,
        AppRoutes.speechWordGroups: 2,
        AppRoutes.speechWords: 2,
        AppRoutes.speechMission: 9,
      },
    );
    expect(favoriteActivities(p), ['Lolo me cuenta un cuento', 'Mis primeras palabras']);
  });

  group('preferencias y día', () {
    test('se guardan y se recuperan; datos raros se ignoran', () async {
      final store = SpeechStore(MemoryBackend());
      final p = SpeechProgress()
        ..preferences.ageRange = '5-6'
        ..preferences.level = 2
        ..preferences.favoriteCategories.add('animales')
        ..preferences.minutes = 15
        ..preferences.slowVoice = true
        ..visits['x'] = 2
        ..repeats['y'] = 3
        ..today = DailyRecord(day: '2026-11-03', counts: {'palabras': 2}, skipped: {'verbo'});
      await store.save(p);
      final back = await store.load();
      expect(back.preferences.toJson(), p.preferences.toJson());
      expect(back.visits, {'x': 2});
      expect(back.repeats, {'y': 3});
      expect(back.today!.toJson(), p.today!.toJson());
      final odd = SpeechPreferences.fromJson({'age_range': '99', 'level': 7, 'minutes': 3});
      expect((odd.ageRange, odd.level, odd.minutes), (null, 1, 10));
      expect(SpeechPreferences.suggestedLevel('5-6'), 2);
    });

    test('lo de hoy se cuenta y al día siguiente empieza de cero', () async {
      var now = day;
      final speech = SpeechController(SpeechStore(MemoryBackend()), clock: () => now);
      await speech.load();
      speech
        ..markWordHeard('perro')
        ..markWordHeard('perro')
        ..markSentenceBuilt('El niño come.')
        ..setMissionSkipped('verbo', true);
      expect(speech.today.count(Daily.words), 2);
      expect(speech.today.skipped, {'verbo'});
      final t = DailyMission.tasks.first;
      expect(DailyMission.progress(speech.today, t), 2);
      speech.markWordHeard('gato');
      expect(DailyMission.done(speech.today, t), isTrue);
      now = day.add(const Duration(days: 1));
      expect(speech.today.count(Daily.words), 0);
      expect(speech.today.skipped, isEmpty);
    });

    test('la aventura se completa haciendo una y saltando las demás (sin rachas)', () {
      final today = DailyRecord(day: 'x', counts: {Daily.words: 3});
      expect(DailyMission.complete(today), isFalse);
      today.skipped.addAll(['oraciones', 'verbo', 'cuento', 'charla']);
      expect(DailyMission.complete(today), isTrue);
      expect(
        DailyMission.complete(DailyRecord(day: 'x', skipped: {...DailyMission.tasks.map((t) => t.id)})),
        isFalse,
      );
    });
  });
}
