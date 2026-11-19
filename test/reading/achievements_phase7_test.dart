import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/creation.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/reading/achievement_data.dart';
import 'package:pequenos_artistas/reading/achievements.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/complete_words.dart';
import 'package:pequenos_artistas/reading/dictation.dart';
import 'package:pequenos_artistas/reading/learning_report.dart';
import 'package:pequenos_artistas/reading/reading_content.dart';
import 'package:pequenos_artistas/reading/reading_progress.dart';
import 'package:pequenos_artistas/reading/screens/achievements_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllable_games.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllables_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_tracking_screen.dart';
import 'package:pequenos_artistas/reading/sentences.dart';
import 'package:pequenos_artistas/reading/syllable_games.dart';
import 'package:pequenos_artistas/screens/not_found_screen.dart';

import '../test_helpers.dart';

Map<String, dynamic> json(String path) => jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;

final catalogs = ReadingCatalogs(
  syllables: ReadingContent.parse(json(ReadingContent.path)),
  words: CompleteWordsContent.parse(json(CompleteWordsContent.path)),
  sentences: SentenceCatalog.parse(json(SentenceCatalog.path)),
  dictations: DictationCatalog.parse(json(DictationCatalog.path)),
);

var _now = DateTime(2026, 11, 19);

ReadingController newController({KeyValueBackend? backend, bool celebrations = true}) => ReadingController(
  ReadingStore(backend ?? MemoryBackend()),
  clock: () => _now,
  celebrations: celebrations,
);

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(finder, 250, scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

Future<void> open(WidgetTester tester, Widget screen) async {
  tester.state<NavigatorState>(find.byType(Navigator)).push(MaterialPageRoute<void>(builder: (_) => screen));
  await tester.pumpAndSettle();
}

/// Progreso guardado en el formato de antes de la Fase 7.
String formatV1(Map<String, dynamic> body) {
  final payload = {'format_version': 1, ...body};
  return jsonEncode({...payload, 'checksum': Creation.checksumOf(payload)});
}

void main() {
  setUp(() {
    _now = DateTime(2026, 11, 19);
    ReadingVoice.clipPlayerFactory = FakeClipPlayer.new;
  });
  tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

  group('1 · 3 · 5 · registro y estrellas', () {
    test('cada actividad real se registra con su día y su módulo', () async {
      final c = newController();
      await c.load();
      c.recordSyllableHeard('ma');
      c.recordSyllableAnswer('ma', game: 'escucha_encuentra', correct: false);
      c.recordSyllableAnswer('ma', game: 'escucha_encuentra', correct: true, mistakes: 1);
      c.recordCompleted('completa_pato', 'elige', firstTry: true, usedHints: false);
      c.recordSentenceHeard('oracion_1_01');
      c.recordDictation(
        'dictado_silaba_ma',
        type: 'silaba',
        level: 1,
        mode: 'tarjetas',
        correct: true,
        hints: 0,
      );
      final a = c.progress.achievements;
      expect(a.syllablesHeard, {'ma'});
      expect(a.syllableStats['ma']!.attempts, 2);
      expect(a.syllableStats['ma']!.correct, 1);
      expect(a.days['2026-11-19'], {
        ReadingModule.syllables: 3,
        ReadingModule.words: 1,
        ReadingModule.sentences: 1,
        ReadingModule.dictation: 1,
      });
      expect(a.lastActivity.keys.toSet(), ReadingModule.all.toSet());
    });

    test('estrellas: 1 por completar, 2 más sin pistas; con pistas solo 1', () async {
      final c = newController();
      await c.load();
      c.recordCompleted('completa_pato', 'elige', firstTry: true, usedHints: false);
      expect(c.stars, StarRules.complete + StarRules.independent);
      c.recordCompleted('completa_gato', 'elige', firstTry: false, usedHints: true);
      expect(c.stars, 3 + StarRules.complete);
      // Cada estrella tiene su motivo registrado.
      expect(
        c.progress.achievements.rewards.keys,
        containsAll(['hecho:elige:completa_pato', 'solo:elige:completa_pato']),
      );
      expect(c.progress.achievements.rewards['hecho:elige:completa_pato']!.date, '2026-11-19');
    });

    test('repetir el mismo ejercicio no da más estrellas (sin recompensas infinitas)', () async {
      final c = newController();
      await c.load();
      for (var i = 0; i < 20; i++) {
        c.recordCompleted('completa_pato', 'elige', firstTry: true, usedHints: false);
        c.recordDictation('d1', type: 'palabra', level: 2, mode: 'teclado', correct: true, hints: 0);
        c.recordSentenceHeard('oracion_1_01');
      }
      expect(c.stars, 3 + 3 + 1);
    });

    test('series: bonificación limitada a 3 al día', () async {
      final c = newController();
      await c.load();
      for (var i = 0; i < 10; i++) {
        c.recordSeries(ReadingModule.words);
      }
      expect(c.stars, StarRules.maxSeriesPerDay * StarRules.series);
      _now = DateTime(2026, 11, 20);
      c.recordSeries(ReadingModule.words);
      expect(c.stars, StarRules.maxSeriesPerDay * StarRules.series + 1);
    });

    test('esfuerzo: acertar algo que antes se falló, una vez al día por módulo', () async {
      final c = newController();
      await c.load();
      c.recordDictation(
        'd1',
        type: 'palabra',
        level: 2,
        mode: 'teclado',
        correct: false,
        hints: 0,
        error: 'accent',
      );
      c.recordDictation('d1', type: 'palabra', level: 2, mode: 'teclado', correct: true, hints: 0);
      expect(c.progress.achievements.rewards.keys, contains('esfuerzo:2026-11-19:dictado'));
      c.recordDictation(
        'd2',
        type: 'palabra',
        level: 2,
        mode: 'teclado',
        correct: false,
        hints: 0,
        error: 'letter',
      );
      c.recordDictation('d2', type: 'palabra', level: 2, mode: 'teclado', correct: true, hints: 0);
      expect(c.progress.achievements.rewards.keys.where((k) => k.startsWith('esfuerzo:')), hasLength(1));
    });
  });

  group('4 · 5 · medallas', () {
    test('12 medallas con id único, nombre, descripción, condición y lugar para su ilustración', () {
      expect(Medals.all, hasLength(12));
      expect(Medals.all.map((m) => m.id).toSet(), hasLength(12));
      expect(Medals.all.map((m) => m.name), [
        'Mi primera sílaba',
        'Explorador de letras',
        'Maestro de sílabas',
        'Completo mis palabras',
        'Mi primera oración',
        'Gran lector',
        'Comprendo lo que leo',
        'Mi primer dictado',
        'Buen escritor',
        'Aprendo cada día',
        'Superé un desafío',
        'Pequeño gran artista',
      ]);
      for (final m in Medals.all) {
        expect(m.description, isNotEmpty);
        expect(m.howTo, isNotEmpty);
        expect(m.image, 'assets/images/aprendo_leer/medallas/${m.id}.webp');
        expect(m.condition(ReadingProgress()), isFalse, reason: '${m.id}: sin progreso no se consigue');
      }
    });

    test('se consiguen al cumplir su condición, con fecha, y solo una vez', () async {
      final c = newController();
      await c.load();
      c.recordSyllableAnswer('ma', game: 'escucha_encuentra', correct: true, firstTry: true);
      expect(c.progress.achievements.medals, {'primera_silaba': '2026-11-19'});
      expect(c.pendingCelebrations.map((m) => m.id), ['primera_silaba']);
      _now = DateTime(2026, 11, 25);
      c.recordSyllableAnswer('me', game: 'escucha_encuentra', correct: true, firstTry: true);
      expect(c.progress.achievements.medals['primera_silaba'], '2026-11-19', reason: 'no se vuelve a dar');
      expect(c.takeCelebration()!.id, 'primera_silaba');
      expect(c.takeCelebration(), isNull);
    });

    test('condiciones verificables de cada medalla', () async {
      final c = newController(celebrations: false);
      await c.load();
      for (final id in ['a', 'ma', 'pa', 'sa', 'la']) {
        c.recordSyllableHeard(id);
      }
      expect(c.progress.achievements.medals.keys, contains('explorador_letras'));
      for (var i = 0; i < 20; i++) {
        c.recordCompleted('completa_$i', 'ordena', firstTry: false, usedHints: true);
      }
      expect(c.progress.achievements.medals.keys, contains('completo_palabras'));
      c.recordSentenceHeard('oracion_1_01');
      expect(c.progress.achievements.medals.keys, contains('primera_oracion'));
      for (var i = 0; i < 10; i++) {
        c.recordQuestionSolved('o$i', firstTry: true, usedHints: false, listenedFirst: false);
      }
      expect(c.progress.achievements.medals.keys, containsAll(['gran_lector', 'comprendo']));
      c.recordDictation(
        'd',
        type: 'silaba',
        level: 1,
        mode: 'tarjetas',
        correct: false,
        hints: 0,
        error: 'syllable',
      );
      c.recordDictation(
        'd',
        type: 'silaba',
        level: 1,
        mode: 'tarjetas',
        correct: false,
        hints: 0,
        error: 'syllable',
      );
      expect(c.progress.achievements.medals.keys, isNot(contains('primer_dictado')));
      c.recordDictation('d', type: 'silaba', level: 1, mode: 'tarjetas', correct: true, hints: 2);
      expect(c.progress.achievements.medals.keys, containsAll(['primer_dictado', 'supere_desafio']));
      expect(
        c.progress.achievements.medals.keys,
        isNot(contains('buen_escritor')),
        reason: 'con pistas no cuenta',
      );
      for (var i = 0; i < 10; i++) {
        c.recordDictation('x$i', type: 'palabra', level: 2, mode: 'teclado', correct: true, hints: 0);
      }
      expect(c.progress.achievements.medals.keys, contains('buen_escritor'));
      c.recordSyllableAnswer('ma', game: 'une_palabra', correct: true);
      expect(c.progress.achievements.medals.keys, contains('pequeno_gran_artista'));
      for (var d = 20; d < 25; d++) {
        _now = DateTime(2026, 11, d);
        c.recordSyllableHeard('ma');
      }
      expect(c.progress.achievements.medals.keys, contains('aprendo_cada_dia'));
      expect(c.progress.achievements.medals.keys, isNot(contains('maestro_silabas')));
    });
  });

  group('6 · 7 · 10 · persistencia, separación y recuperación', () {
    test('estrellas, medallas, historial y perfil se guardan y se recuperan', () async {
      final backend = MemoryBackend();
      final c = newController(backend: backend);
      await c.load();
      c.setAlias('Sofi');
      c.setAvatar('robot');
      c.setCelebrationSound(false);
      c.recordSyllableAnswer('ma', game: 'escucha_encuentra', correct: true, firstTry: true);
      await c.flush();
      final again = newController(backend: backend);
      await again.load();
      final a = again.progress.achievements;
      expect(a.profile.alias, 'Sofi');
      expect(a.profile.avatar, 'robot');
      expect(a.profile.celebrationSound, isFalse);
      expect(a.stars, 3);
      expect(a.medals, {'primera_silaba': '2026-11-19'});
      expect(again.pendingCelebrations, isEmpty, reason: 'al reabrir no se vuelve a celebrar');
      expect(jsonDecode((await backend.read(ReadingStore.key))!)['format_version'], 2);
    });

    test('el apodo no admite datos de más (solo letras, como mucho 16)', () {
      expect(ReadingProfile.cleanAlias('  Ana  María  '), 'Ana María');
      expect(ReadingProfile.cleanAlias('Ana@mail.com 555-1234'), 'Anamailcom -');
      expect(ReadingProfile.cleanAlias('A' * 40).length, ReadingProfile.maxAlias);
    });

    test('los datos de lectura van en su propia clave; borrarlos no toca nada más', () async {
      final backend = MemoryBackend();
      await backend.write('learning.v1.state', 'otro módulo');
      final c = newController(backend: backend);
      await c.load();
      c.recordSyllableHeard('ma');
      await c.flush();
      await c.clearAll();
      expect(await backend.read(ReadingStore.key), isNull);
      expect(await backend.read('learning.v1.state'), 'otro módulo');
      expect(c.stars, 0);
    });

    test(
      'el progreso de antes de la Fase 7 se conserva, gana sus estrellas y medallas, y queda una copia',
      () async {
        final backend = MemoryBackend();
        final old = formatV1({
          'completed': {
            'completa_pato': ['elige'],
            'oracion_1_01': ['comprende'],
          },
          'first_try': ['elige:completa_pato'],
          'with_hints': <String>[],
          'correct_answers': 1,
          'attempts': 1,
          'sentences_heard': ['oracion_1_01'],
          'questions_answered': ['oracion_1_01'],
          'questions_correct': ['oracion_1_01'],
          'dictations': {
            'dictado_silaba_ma': {
              'type': 'silaba',
              'level': 1,
              'mode': 'tarjetas',
              'attempts': 1,
              'correct': true,
              'independent': true,
            },
          },
        });
        await backend.write(ReadingStore.key, old);
        final c = newController(backend: backend);
        await c.load();
        await c.flush();
        final p = c.progress;
        expect(p.completed['completa_pato'], {'elige'}, reason: 'no se pierde nada');
        expect(p.dictations['dictado_silaba_ma']!.correct, isTrue);
        expect(p.schema, ReadingProgress.currentSchema);
        // pato: 1+2; oración: completar 1 + escuchar 1; dictado: 1+2.
        expect(c.stars, 3 + 2 + 3);
        expect(p.achievements.medals.keys, containsAll(['primera_oracion', 'primer_dictado']));
        expect(c.pendingCelebrations, isEmpty, reason: 'lo anterior no se celebra de golpe');
        expect(await backend.read(ReadingStore.migrationBackupKey), old, reason: 'copia intacta');
        // Recuperar la copia.
        c.recordSyllableHeard('ma');
        expect(await c.restoreMigrationBackup(), isTrue);
        expect(c.progress.achievements.syllablesHeard, isEmpty);
        expect(c.progress.completed['completa_pato'], {'elige'});
      },
    );

    test('datos dañados: se usa la copia de seguridad', () async {
      final backend = MemoryBackend();
      final c = newController(backend: backend);
      await c.load();
      c.recordSyllableHeard('ma');
      await c.flush();
      c.recordSyllableHeard('pa');
      await c.flush();
      await backend.write(ReadingStore.key, '{roto');
      final again = newController(backend: backend);
      await again.load();
      expect(again.progress.achievements.syllablesHeard, {'ma'});
    });
  });

  group('2 · 9 · progreso calculado y recomendaciones', () {
    test('sin actividad: todo a cero (nada inventado) y se sugiere empezar', () {
      final r = ReadingReport(ReadingProgress(), catalogs);
      for (final m in r.modules) {
        expect((m.done, m.correct, m.mastered), (0, 0, 0), reason: m.title);
        expect(m.pending, m.available);
        expect(m.lastDate, isNull);
      }
      expect(r.modules.map((m) => m.available), [55, 100, 105, 200]);
      expect(r.recommendations.single.id, 'empezar');
      expect(r.currentStage.number, 1);
    });

    test('completar no es dominar: con pistas cuenta como hecha, no como dominada', () async {
      final c = newController(celebrations: false);
      await c.load();
      final e = catalogs.words.exercises.firstWhere((e) => catalogs.words.words[e.wordId]!.hasPicture);
      c.recordCompleted(e.id, 'elige', firstTry: false, usedHints: true);
      final r = ReadingReport(c.progress, catalogs).module(ReadingModule.words);
      expect((r.done, r.correct, r.mastered), (1, 1, 0));
      expect(r.toPractice, [catalogs.words.wordOf(e).text.toUpperCase()]);
      expect(r.lastDate, '2026-11-19');
    });

    test('fallos repetidos en MA, ME, MI…: recomienda repasar la familia M, con la evidencia', () async {
      final c = newController(celebrations: false);
      await c.load();
      for (final s in ['ma', 'me', 'mi', 'mo']) {
        c.recordSyllableAnswer(s, game: 'escucha_encuentra', correct: false);
      }
      c.recordSyllableAnswer('mu', game: 'escucha_encuentra', correct: true);
      final r = ReadingReport(c.progress, catalogs);
      final rec = r.recommendations.firstWhere((x) => x.id == 'familia_m');
      expect(rec.forChild, contains('MA, ME, MI, MO, MU'));
      expect(rec.evidence, '4 errores en 5 respuestas de esa familia.');
      expect(r.module(ReadingModule.syllables).toPractice.single, startsWith('Familia M'));
    });

    test('dictados difíciles → tarjetas; tildes; palabras fáciles → oraciones', () async {
      final c = newController(celebrations: false);
      await c.load();
      for (var i = 0; i < 3; i++) {
        c.recordDictation(
          'd$i',
          type: 'palabra',
          level: 2,
          mode: 'teclado',
          correct: false,
          hints: 0,
          error: 'accent',
        );
      }
      final playable = catalogs.words.exercises
          .where((e) => catalogs.words.words[e.wordId]!.hasPicture)
          .take(8);
      for (final e in playable) {
        c.recordCompleted(e.id, 'elige', firstTry: true, usedHints: false);
      }
      final ids = ReadingReport(c.progress, catalogs).recommendations.map((r) => r.id);
      expect(ids, containsAll(['dictado_tarjetas', 'tildes', 'pasar_oraciones']));
    });

    test('el camino refleja actividades reales y nunca se bloquea', () async {
      final c = newController(celebrations: false);
      await c.load();
      for (final v in ['a', 'e', 'i', 'o', 'u']) {
        c.recordSyllableHeard(v);
      }
      final r = ReadingReport(c.progress, catalogs);
      expect(r.path, hasLength(6));
      expect(r.path.first.done, isTrue);
      expect(r.currentStage.number, 2);
      expect(r.path.map((s) => s.route).toSet(), hasLength(4), reason: 'cada etapa abre su actividad');
    });
  });

  group('pantallas', () {
    testWidgets('los juegos de sílabas registran las respuestas (antes no se guardaban)', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final c = newController(celebrations: false);
      await pumpApp(tester, reading: c);
      await open(
        tester,
        const SyllableGameScreen(
          game: SyllableGame.listenFind,
          args: ReadingGameArgs(familyId: 'm'),
          seed: 7,
        ),
      );
      final content = catalogs.syllables;
      final q = SyllableGames.listenFind(content, familyId: 'm', random: Random(7)).first;
      final wrong = q.options.firstWhere((o) => !q.isRight(o));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${wrong.text}'));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${q.target.text}'));
      final stat = c.progress.achievements.syllableStats[q.target.id]!;
      expect((stat.attempts, stat.correct, stat.firstTry), (2, 1, 0));
    });

    testWidgets('6 · celebración: medalla, felicitación y «Continuar aprendiendo»', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final c = newController();
      await pumpApp(tester, reading: c);
      c.recordSyllableAnswer('ma', game: 'escucha_encuentra', correct: true, firstTry: true);
      await tester.pumpAndSettle();
      expect(find.text('¡Nueva medalla!'), findsOneWidget);
      expect(find.text('Mi primera sílaba'), findsOneWidget);
      expect(lastNarrator!.spoken.last, contains('Conseguiste la medalla Mi primera sílaba'));
      await tapAndSettle(tester, find.text('Continuar aprendiendo'));
      expect(find.text('¡Nueva medalla!'), findsNothing);
    });

    testWidgets('6 · sin sonido de celebración y con movimiento reducido', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final c = newController();
      await c.load();
      c.setCelebrationSound(false);
      await pumpApp(tester, reading: c);
      tester.platformDispatcher.accessibilityFeaturesTestValue = const FakeAccessibilityFeatures(
        disableAnimations: true,
      );
      addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
      await tester.pumpAndSettle();
      final spoken = lastNarrator!.spoken.length;
      c.recordSyllableAnswer('ma', game: 'escucha_encuentra', correct: true, firstTry: true);
      await tester.pump();
      expect(find.text('¡Nueva medalla!'), findsOneWidget);
      expect(find.byType(TweenAnimationBuilder<double>), findsNothing);
      expect(lastNarrator!.spoken.length, spoken, reason: 'sin felicitación hablada');
    });

    testWidgets('«Mis logros»: apodo, etapa, estrellas, medallas, módulos y sugerencia reales', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 1000));
      final c = newController(celebrations: false);
      await c.load();
      c.setAlias('Leo');
      c.recordCompleted('completa_pato', 'elige', firstTry: true, usedHints: false);
      await pumpApp(tester, reading: c);
      await open(tester, const MyAchievementsScreen());
      expect(find.text('¡Hola, Leo!'), findsOneWidget);
      expect(find.bySemanticsLabel('3 estrellas'), findsOneWidget);
      expect(find.bySemanticsLabel('Medallas: 0 de 12'), findsOneWidget);
      expect(
        find.bySemanticsLabel(RegExp(r'^Completo palabras\. Hechas 1 de 100\. Bien 1\. Sin ayuda 1')),
        findsOneWidget,
      );
      expect(find.bySemanticsLabel(RegExp('^Para practicar:')), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Mis medallas'));
      expect(find.bySemanticsLabel(RegExp(r'^Mi primera sílaba\. Bloqueada\.')), findsOneWidget);
    });

    testWidgets('«Mi camino»: 6 etapas, tocar una abre su actividad', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await open(tester, const LearningPathScreen());
      for (var i = 1; i <= 6; i++) {
        expect(find.bySemanticsLabel(RegExp('^Etapa $i:')), findsOneWidget);
      }
      expect(find.bySemanticsLabel(RegExp(r'^Etapa 1: .*Estás aquí')), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Etapa 6:')));
      expect(find.text('Escucho y escribo'), findsWidgets);
    });

    testWidgets('8 · el panel adulto solo se abre verificado (desde la zona para adultos)', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      final nav = tester.state<NavigatorState>(find.byType(Navigator));
      nav.pushNamed(AppRoutes.readingTracking);
      await tester.pumpAndSettle();
      expect(find.byType(NotFoundScreen), findsOneWidget);
      expect(find.byType(ReadingTrackingScreen), findsNothing);
      nav.pushNamed(AppRoutes.readingTracking, arguments: const AdultZoneArgs.verified());
      await tester.pumpAndSettle();
      expect(find.byType(ReadingTrackingScreen), findsOneWidget);
      expect(find.textContaining('No es una evaluación ni un diagnóstico'), findsOneWidget);
    });

    testWidgets('panel adulto: datos reales, perfil, sugerencias y borrar con confirmación', (tester) async {
      setScreenSize(tester, const Size(800, 1280));
      final c = newController(celebrations: false);
      await c.load();
      for (final s in ['ma', 'me', 'mi', 'mo']) {
        c.recordSyllableAnswer(s, game: 'escucha_encuentra', correct: false);
      }
      await pumpApp(tester, reading: c);
      tester
          .state<NavigatorState>(find.byType(Navigator))
          .pushNamed(AppRoutes.readingTracking, arguments: const AdultZoneArgs.verified());
      await tester.pumpAndSettle();
      expect(find.textContaining('Intentos registrados: 4'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.textContaining('Por qué:'),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.textContaining('Repasar la familia M'), findsWidgets);
      expect(find.textContaining('Por qué: 4 errores en 4 respuestas'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.textContaining('Aún no hay datos suficientes'),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.textContaining('Aún no hay datos suficientes'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.byType(TextField),
        -300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.enterText(find.byType(TextField), 'Mía');
      expect(c.progress.achievements.profile.alias, 'Mía');
      await tapAndSettle(tester, find.text('Borrar el progreso de lectura'));
      await tapAndSettle(tester, find.text('Borrar'));
      expect(c.progress.achievements.syllableStats, isEmpty);
    });

    testWidgets('la zona para adultos tiene el acceso al seguimiento', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      tester
          .state<NavigatorState>(find.byType(Navigator))
          .pushNamed(AppRoutes.adultZone, arguments: const AdultZoneArgs.verified());
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.text('Seguimiento de «Aprendo a leer»'));
      expect(find.byType(ReadingTrackingScreen), findsOneWidget);
    });

    testWidgets('«Aprendo a leer» muestra el progreso real y los accesos a logros', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final c = newController(celebrations: false);
      await c.load();
      c.recordSyllableHeard('ma');
      await pumpApp(tester, reading: c);
      tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.reading);
      await tester.pumpAndSettle();
      expect(find.bySemanticsLabel('Actividades empezadas: 1 de 4'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Mis logros'));
      expect(find.byType(MyAchievementsScreen), findsOneWidget);
    });

    for (final (size, scale) in const [
      (Size(360, 720), 1.0),
      (Size(360, 720), 1.3),
      (Size(800, 1280), 1.0),
      (Size(1280, 800), 1.6),
    ]) {
      testWidgets('12 · ${size.width.toInt()}×${size.height.toInt()} texto ×$scale: sin desbordamientos', (
        tester,
      ) async {
        setScreenSize(tester, size, textScale: scale);
        final c = newController(celebrations: false);
        await c.load();
        c.setAlias('Valentina Sofía');
        c.recordSyllableHeard('ma');
        c.recordDictation('d', type: 'palabra', level: 2, mode: 'teclado', correct: true, hints: 0);
        _now = DateTime(2026, 11, 20);
        c.recordSyllableHeard('pa');
        await pumpApp(tester, reading: c);
        for (final screen in const [
          MyAchievementsScreen(),
          MedalsScreen(),
          LearningPathScreen(),
          ReadingTrackingScreen(),
        ]) {
          await open(tester, screen);
          expect(tester.takeException(), isNull, reason: '$screen');
          tester.state<NavigatorState>(find.byType(Navigator)).pop();
          await tester.pumpAndSettle();
        }
        // La celebración tampoco se desborda.
        final d = newController();
        await d.load();
        await pumpApp(tester, reading: d);
        d.recordSyllableAnswer('ma', game: 'escucha_encuentra', correct: true, firstTry: true);
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull, reason: 'celebración');
      });
    }
  });
}
