import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';
import 'package:pequenos_artistas/learning/learning_progress.dart';
import 'package:pequenos_artistas/navigation/app_router.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/reading_content.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllable_games.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllables_screen.dart';
import 'package:pequenos_artistas/reading/syllabifier.dart';
import 'package:pequenos_artistas/reading/syllable_games.dart';
import 'package:pequenos_artistas/reading/widgets/reading_widgets.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

import '../test_helpers.dart';

final raw = jsonDecode(File(ReadingContent.path).readAsStringSync()) as Map<String, dynamic>;
final content = ReadingContent.parse(raw);

String plain(String s) => s
    .toLowerCase()
    .replaceAll('á', 'a')
    .replaceAll('é', 'e')
    .replaceAll('í', 'i')
    .replaceAll('ó', 'o')
    .replaceAll('ú', 'u');

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(finder, 250, scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

List<String> get spoken => lastNarrator!.spoken;

LearningAudio audioWith({
  RecordingNarrator? narrator,
  LearningSettings settings = const LearningSettings(),
}) => LearningAudio(
  effects: RecordingSoundEffects(),
  narrator: narrator ?? RecordingNarrator(),
  music: RecordingMusic(),
  settings: () => settings,
);

void main() {
  group('contenido', () {
    test('vocales y las 10 familias pedidas, con 5 sílabas cada una', () {
      expect(content.families.map((f) => f.id), [
        'vocales',
        'm',
        'p',
        's',
        'l',
        't',
        'n',
        'd',
        'f',
        'c',
        'b',
      ]);
      expect(content.syllablesOf(content.families[9]).map((s) => s.text), ['ca', 'co', 'cu', 'que', 'qui']);
      for (final f in content.families) {
        expect(content.syllablesOf(f), hasLength(5), reason: f.id);
        expect(f.isVowels ? f.letterAudio : f.letterAudio?.tts, f.isVowels ? isNull : isNotEmpty);
      }
      expect(content.syllables, hasLength(55));
      expect(content.levels.map((l) => l.locked), [false, false, true], reason: 'el avanzado, bloqueado');
    });

    test(
      'cada sílaba: id, texto, familia, audio (minúsculas, nunca deletreada), velocidades, palabra y nivel',
      () {
        for (final s in content.syllables.values) {
          expect(s.id, s.text);
          expect(s.audio.tts, s.text.toLowerCase(), reason: '«${s.text}» se dice en minúsculas');
          expect(s.audio.tts, isNot(contains(' ')));
          expect(Syllabifier.split(s.text), [s.text], reason: '«${s.text}» es una sola sílaba');
          expect(s.speeds, containsAll(['normal', 'lenta']));
          expect(s.level, 1);
          expect(content.familyOf(s), isNotNull);
          expect(content.wordOf(s), isNotNull, reason: s.id);
        }
      },
    );

    test('las palabras: separación validada por el silabeador de Dart (independiente del de Python)', () {
      for (final w in content.words.values) {
        expect(w.syllables.join(), w.text, reason: w.text);
        expect(Syllabifier.split(w.text), w.syllables, reason: w.text);
      }
    });

    test('cada palabra de ejemplo empieza por su sílaba (FUEGO, anotado como diptongo)', () {
      for (final s in content.syllables.values) {
        final w = content.wordOf(s)!;
        final first = plain(w.syllables.first);
        if (w.note != null) {
          expect(first.startsWith(s.text) && first.length == s.text.length + 1, isTrue, reason: w.text);
        } else {
          expect(first, s.text, reason: '${w.text} empieza por ${s.text}');
        }
      }
      expect(content.words['mama']!.text, 'mamá');
      expect(content.words['pelota']!.syllables, ['pe', 'lo', 'ta']);
    });

    test('imágenes: las que hay existen y se ven; las que faltan quedan marcadas como pendientes', () {
      final rawWords = {for (final w in raw['words'] as List) (w as Map)['id']: w};
      var pending = 0;
      for (final w in content.words.values) {
        final json = rawWords[w.id]!['picture'];
        if (json != null) {
          expect(SpeechPicture.fromJson(json), isNotNull, reason: '${w.text}: $json');
        } else {
          pending++;
          expect(w.hasPicture, w.imageReady, reason: w.text);
        }
        expect(w.image, startsWith('assets/images/aprendo_leer/palabras/'));
      }
      expect(pending, greaterThan(0), reason: 'hay imágenes pendientes (ver la lista)');
    });

    test('audios grabados: los que dice el contenido existen; si no hay, se usa la voz', () {
      for (final a in [
        for (final s in content.syllables.values) s.audio,
        for (final w in content.words.values) w.audio,
        for (final f in content.families) ?f.letterAudio,
      ]) {
        if (a.clip case final clip?) expect(File(clip).existsSync(), isTrue, reason: clip);
      }
    });
  });

  group('motor de audio', () {
    late FakeClipPlayer clips;
    setUp(() => clips = FakeClipPlayer());

    test('sin grabación, usa la voz del dispositivo con el texto en minúsculas', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      await voice.play(const ReadingAudio(tts: 'ma'));
      expect(narrator.spoken, ['ma']);
      expect(clips.played, isEmpty);
      expect(voice.status, ReadingVoiceStatus.idle);
    });

    test('con grabación, usa el archivo; despacio, al 70 %', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      const a = ReadingAudio(clip: 'assets/audio/reading/silabas/ma.mp3', tts: 'ma');
      await voice.play(a);
      await voice.play(a, speed: ReadingSpeed.slow);
      expect(clips.played, [
        ('assets/audio/reading/silabas/ma.mp3', 1.0),
        ('assets/audio/reading/silabas/ma.mp3', 0.7),
      ]);
      expect(narrator.spoken, isEmpty);
    });

    test('si la grabación falla, se oye con la voz del dispositivo', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer(fail: true));
      await voice.play(const ReadingAudio(clip: 'assets/audio/reading/silabas/ma.mp3', tts: 'ma'));
      expect(narrator.spoken, ['ma']);
      expect(voice.lastClipError, isNotNull);
    });

    test('despacio con la voz del dispositivo', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      await voice.play(const ReadingAudio(tts: 'pelota'), speed: ReadingSpeed.slow);
      expect(narrator.slow, ['pelota']);
    });

    test('un sonido nuevo corta el anterior (nunca se superponen)', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      await voice.play(const ReadingAudio(tts: 'ma'));
      final stops = narrator.stops;
      final clipStops = clips.stops;
      await voice.play(const ReadingAudio(tts: 'me'));
      expect(clips.stops, greaterThan(clipStops), reason: 'se para la grabación anterior');
      expect(narrator.stops, greaterThanOrEqualTo(stops), reason: 'se calla la voz anterior');
      // Mientras suena una frase larga, otra la interrumpe y la primera no sigue.
      narrator.pending = Completer();
      final first = voice.play(const ReadingAudio(tts: 'frase larga'));
      await Future<void>.delayed(Duration.zero);
      narrator.pending = null;
      await voice.play(const ReadingAudio(tts: 'mo'));
      expect(narrator.spoken.last, 'mo');
      expect(voice.status, ReadingVoiceStatus.idle);
      unawaited(first);
    });

    test('«pe. pelota»: varias seguidas en una sola frase', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      await voice.playAll(const [ReadingAudio(tts: 'pe'), ReadingAudio(tts: 'pelota')]);
      expect(narrator.spoken, ['pe. pelota']);
    });

    test('sin voz en español: lo indica (la pantalla muestra el aviso) y no se cuelga', () async {
      final narrator = RecordingNarrator(
        info: const VoiceInfo(available: false, description: 'Sin voz en español'),
      );
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      await voice.play(const ReadingAudio(tts: 'ma'));
      expect(voice.status, ReadingVoiceStatus.noVoice);
      expect(voice.message, 'Sin voz en español');
      expect(narrator.spoken, isEmpty);
      // Con grabación, sí se oye aunque no haya voz.
      await voice.play(const ReadingAudio(clip: 'assets/audio/reading/silabas/ma.mp3', tts: 'ma'));
      expect(clips.played, hasLength(1));
    });

    test('con la voz apagada en los ajustes: no suena nada y se explica', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(
        audioWith(narrator: narrator, settings: const LearningSettings(voiceOn: false)),
        clips: clips,
      );
      await voice.play(const ReadingAudio(clip: 'assets/audio/reading/silabas/ma.mp3', tts: 'ma'));
      expect(voice.status, ReadingVoiceStatus.muted);
      expect(clips.played, isEmpty);
      expect(narrator.spoken, isEmpty);
    });

    test('al salir de la pantalla se libera el reproductor', () async {
      final voice = ReadingVoice(audioWith(), clips: clips);
      voice.dispose();
      await Future<void>.delayed(Duration.zero);
      expect(clips.disposed, isTrue);
    });
  });

  group('lógica de los juegos', () {
    test('«Escucha y encuentra»: una sola correcta, sin repetir seguido, posición variable', () {
      for (final f in [null, ...content.families.map((f) => f.id)]) {
        final qs = SyllableGames.listenFind(content, familyId: f, random: Random(3));
        expect(qs, hasLength(8), reason: '$f');
        for (final (i, q) in qs.indexed) {
          expect(q.options, hasLength(3));
          expect(q.options.where(q.isRight), hasLength(1), reason: '$f: ${q.target.text}');
          expect({for (final o in q.options) plain(o.text)}, hasLength(3), reason: 'sin opciones repetidas');
          if (i > 0) {
            expect(q.target.id, isNot(qs[i - 1].target.id), reason: 'no la misma sílaba dos veces seguidas');
            expect(q.options.indexOf(q.target), isNot(qs[i - 1].options.indexOf(qs[i - 1].target)));
          }
        }
      }
      // Con las consonantes, las otras opciones terminan en la misma vocal (MA / PA / SA).
      final q = SyllableGames.listenFind(content, familyId: 'm', random: Random(1)).first;
      expect(q.options.map((o) => o.text.characters.last).toSet(), hasLength(1));
    });

    test('«Une sílaba y palabra»: solo palabras con imagen; las otras opciones no están en la palabra', () {
      final qs = SyllableGames.matchWord(content, random: Random(5), count: 30);
      expect(qs, hasLength(30));
      for (final q in qs) {
        expect(q.word.hasPicture, isTrue, reason: q.word.text);
        expect(q.options.where(q.isRight), hasLength(1));
        expect(plain(q.word.syllables.first), q.answer.text);
        for (final o in q.options.where((o) => !q.isRight(o))) {
          expect(
            q.word.syllables.map(plain),
            isNot(contains(plain(o.text))),
            reason: '${q.word.text}: ${o.text}',
          );
        }
      }
    });
  });

  group('pantallas', () {
    setUp(() => ReadingVoice.clipPlayerFactory = FakeClipPlayer.new);
    tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

    testWidgets('sílaba: se resalta, suena, muestra palabra e imagen, y se repite sin límite', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.readingSyllables);
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel('Familia de la P'));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba pe'));
      expect(spoken.last, 'pe');
      expect(tester.widget<Semantics>(find.bySemanticsLabel('Sílaba pe').first).properties.selected, isTrue);
      expect(find.bySemanticsLabel('Dibujo: pelota'), findsOneWidget);
      for (var i = 0; i < 3; i++) {
        await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la sílaba'));
      }
      expect(spoken.where((s) => s == 'pe'), hasLength(4));
      await tapAndSettle(tester, find.bySemanticsLabel('Palabra la palabra pelota'));
      expect(spoken.last, 'pelota');
      await tapAndSettle(tester, find.bySemanticsLabel('Despacio la palabra pelota'));
      expect(lastNarrator!.slow.last, 'pelota');
      // Sin ilustración todavía: marcador claro, nunca una imagen equivocada.
      await tapAndSettle(tester, find.bySemanticsLabel('Familia de la M'));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ma'));
      expect(find.bySemanticsLabel('Imagen pendiente de mamá'), findsOneWidget);
      expect(find.text('Imagen pendiente'), findsOneWidget);
    });

    testWidgets('«Escucha y encuentra»: error amable, volver a escuchar, acierto y final', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      tester
          .state<NavigatorState>(find.byType(Navigator))
          .push(
            MaterialPageRoute<void>(
              builder: (_) => const SyllableGameScreen(
                game: SyllableGame.listenFind,
                args: ReadingGameArgs(familyId: 'm'),
                seed: 7,
              ),
            ),
          );
      await tester.pumpAndSettle();
      final qs = SyllableGames.listenFind(content, familyId: 'm', random: Random(7));
      expect(spoken.last, qs.first.target.text, reason: 'la primera sílaba suena al entrar');
      for (final (i, q) in qs.indexed) {
        final wrong = q.options.firstWhere((o) => !q.isRight(o));
        if (i == 0) {
          await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${wrong.text}'));
          expect(find.text(SyllableGameScreen.tryAgain), findsOneWidget);
          expect(spoken.last, SyllableGameScreen.tryAgain);
          await tapAndSettle(tester, find.bySemanticsLabel('Escuchar otra vez'));
          expect(spoken.last, q.target.text);
        }
        await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${q.target.text}'));
        expect(spoken.last, SyllableGameScreen.praise);
        expect(find.byType(ReadingCelebration), findsOneWidget);
        await tapAndSettle(tester, find.bySemanticsLabel(i == qs.length - 1 ? 'Terminar' : 'Siguiente'));
        if (i < qs.length - 1) expect(spoken.last, qs[i + 1].target.text);
      }
      expect(find.bySemanticsLabel('Acertaste 7 de 8 a la primera'), findsOneWidget);
      expect(find.bySemanticsLabel('Jugar otra vez'), findsOneWidget);
    });

    testWidgets('«Une sílaba y palabra»: al acertar se oye «pe. pelota» y «¡Muy bien!»', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      tester
          .state<NavigatorState>(find.byType(Navigator))
          .push(
            MaterialPageRoute<void>(
              builder: (_) => const SyllableGameScreen(game: SyllableGame.matchWord, seed: 2),
            ),
          );
      await tester.pumpAndSettle();
      final q = SyllableGames.matchWord(content, random: Random(2)).first;
      expect(spoken.last, q.word.text, reason: 'se oye la palabra al empezar');
      expect(find.bySemanticsLabel('Dibujo: ${q.word.text}'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${q.answer.text}'));
      expect(spoken.sublist(spoken.length - 2), [
        '${q.answer.text}. ${q.word.text}',
        SyllableGameScreen.praise,
      ]);
      expect(
        find.bySemanticsLabel(RegExp('^Palabra por sílabas: ${q.word.syllables.join(' - ')}')),
        findsOneWidget,
      );
    });

    testWidgets('desde las sílabas se abren los juegos; el nivel avanzado está bloqueado', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.readingSyllables);
      await tester.pumpAndSettle();
      expect(find.bySemanticsLabel(RegExp('^Nivel avanzado: .*Todavía no está disponible')), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Escucha y encuentra'));
      expect(find.byType(SyllableGameScreen), findsOneWidget);
      await tapAndSettle(tester, find.byTooltip('Volver'));
      await tapAndSettle(tester, find.bySemanticsLabel('Une sílaba y palabra'));
      expect(find.byType(SyllableGameScreen), findsOneWidget);
    });

    test('las actividades de «Aprendo a leer» van sin música, para oír bien la voz', () {
      for (final r in [AppRoutes.readingSyllables, AppRoutes.readingListenFind, AppRoutes.readingMatchWord]) {
        expect(AppRouter.musicFor(r, const SizedBox()), isNull, reason: r);
      }
    });
  });
}
