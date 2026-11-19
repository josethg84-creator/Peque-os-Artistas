import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';
import 'package:pequenos_artistas/learning/learning_progress.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/complete_words.dart';
import 'package:pequenos_artistas/reading/reading_content.dart';
import 'package:pequenos_artistas/reading/reading_progress.dart';
import 'package:pequenos_artistas/reading/screens/complete_words_game_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllable_games.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllables_screen.dart';

import '../test_helpers.dart';

LearningAudio audioWith({
  RecordingNarrator? narrator,
  LearningSettings settings = const LearningSettings(),
}) => LearningAudio(
  effects: RecordingSoundEffects(),
  narrator: narrator ?? RecordingNarrator(),
  music: RecordingMusic(),
  settings: () => settings,
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

/// «Por sílabas»: la palabra se dice sílaba a sílaba, además de corrida.
void main() {
  setUp(() => ReadingVoice.clipPlayerFactory = FakeClipPlayer.new);
  tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

  group('motor', () {
    test('cada sílaba suena por separado, en minúsculas y en orden, resaltando la que suena', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      final marks = <int?>[];
      final saidAt = <String>[];
      final ok = await voice.playSyllables(
        const [ReadingAudio(tts: 'PE'), ReadingAudio(tts: 'lo'), ReadingAudio(tts: 'ta')],
        onSyllable: (i) {
          marks.add(i);
          if (i != null) saidAt.add(narrator.spoken.length.toString());
        },
      );
      expect(ok, isTrue);
      expect(narrator.spoken, ['pe', 'lo', 'ta']);
      expect(marks, [0, 1, 2, null]);
      // Cada sílaba se marca ANTES de decirla (0, 1 y 2 frases dichas).
      expect(saidAt, ['0', '1', '2']);
      expect(voice.status, ReadingVoiceStatus.idle);
    });

    test('despacio, con grabación si existe, y en silencio si el sonido está apagado', () async {
      final narrator = RecordingNarrator();
      final clips = FakeClipPlayer();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      await voice.playSyllables(const [
        ReadingAudio(clip: 'assets/audio/reading/silabas/ma.mp3', tts: 'ma'),
        ReadingAudio(tts: 'no'),
      ], speed: ReadingSpeed.slow);
      expect(clips.played, [('assets/audio/reading/silabas/ma.mp3', ReadingVoice.slowRate)]);
      expect(narrator.slow, ['no']);
      final muted = ReadingVoice(
        audioWith(narrator: narrator, settings: const LearningSettings(voiceOn: false)),
        clips: FakeClipPlayer(),
      );
      expect(await muted.playSyllables(const [ReadingAudio(tts: 'ma')]), isFalse);
      expect(muted.status, ReadingVoiceStatus.muted);
    });

    test('otro sonido lo corta (nunca se superponen)', () async {
      final narrator = RecordingNarrator()..pending = Completer();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      final first = voice.playSyllables(const [ReadingAudio(tts: 'pe'), ReadingAudio(tts: 'lo')]);
      await Future<void>.delayed(Duration.zero);
      final second = voice.play(const ReadingAudio(tts: 'mesa'));
      narrator.pending!.complete();
      narrator.pending = null;
      expect(await first, isFalse);
      await second;
      expect(narrator.spoken, ['pe', 'mesa'], reason: '«lo» ya no suena');
    });
  });

  group('pantallas', () {
    testWidgets('Completo palabras: «Por sílabas» dice la palabra por sílabas y cuenta como pista', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 1000));
      final progress = ReadingController(ReadingStore(MemoryBackend()), celebrations: false)..load();
      await pumpApp(tester, reading: progress);
      await open(
        tester,
        const CompleteWordsGameScreen(args: CompleteGameArgs(level: 1, mode: CompleteMode.choose), seed: 3),
      );
      final content = await CompleteWordsContent.load(rootBundleForTests(tester));
      final e = content.session(1, CompleteMode.choose, done: (_) => false, random: Random(3)).first;
      await tapAndSettle(tester, find.bySemanticsLabel('Por sílabas la palabra'));
      expect(lastNarrator!.spoken.sublist(lastNarrator!.spoken.length - e.syllables.length), [
        for (final s in e.syllables) s.toLowerCase(),
      ]);
      // Acertar: queda registrado como hecho con pista (no «sin ayuda»).
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${e.answer.toLowerCase()}'));
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(progress.progress.withHints, contains('${CompleteMode.choose.id}:${e.id}'));
    });

    testWidgets('Aprendo las sílabas: la palabra de ejemplo por sílabas', (tester) async {
      setScreenSize(tester, const Size(420, 1000));
      await pumpApp(tester);
      unawaited(tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.readingSyllables));
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel('Familia de la M'));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba mo'));
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Por sílabas la palabra ')));
      expect(lastNarrator!.spoken.sublist(lastNarrator!.spoken.length - 2), ['mo', 'no']);
    });

    testWidgets('Une sílaba y palabra: «Por sílabas» solo aparece tras acertar (antes daría la respuesta)', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 1000));
      await pumpApp(tester);
      await open(
        tester,
        const SyllableGameScreen(
          game: SyllableGame.matchWord,
          args: ReadingGameArgs(familyId: 'm'),
          seed: 7,
        ),
      );
      expect(find.bySemanticsLabel(RegExp('^Por sílabas')), findsNothing);
      final content = await ReadingContent.load(rootBundleForTests(tester));
      final options = find.bySemanticsLabel(RegExp(r'^Sílaba '));
      // Probar opciones hasta acertar.
      for (var i = 0; i < options.evaluate().length; i++) {
        await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Sílaba ')).at(i));
        if (find.bySemanticsLabel(RegExp('^Por sílabas')).evaluate().isNotEmpty) break;
      }
      expect(content.syllables, isNotEmpty);
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Por sílabas')));
      expect(lastNarrator!.spoken.last, isNot(contains(' ')), reason: 'la última sílaba suena sola');
    });

    testWidgets('Aprendo a Hablar: «Por sílabas» en la tarjeta de la palabra, resaltando cada sílaba', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      unawaited(
        tester
            .state<NavigatorState>(find.byType(Navigator))
            .pushNamed(AppRoutes.speechWords, arguments: const SpeechWordsArgs('animales')),
      );
      await tester.pumpAndSettle();
      lastNarrator!.pending = Completer();
      await tester.tap(find.bySemanticsLabel('Por sílabas: perro').first);
      await tester.pump();
      expect(lastNarrator!.spoken.last, 'pe');
      expect(find.bySemanticsLabel('Sílabas: pe, rro'), findsOneWidget);
      lastNarrator!.pending!.complete();
      lastNarrator!.pending = null;
      await tester.pumpAndSettle();
      expect(lastNarrator!.spoken.sublist(lastNarrator!.spoken.length - 2), ['pe', 'rro']);
      // Escuchar la palabra corrida sigue igual.
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
      expect(lastNarrator!.spoken.last, 'perro');
    });
  });
}

/// El paquete de recursos de la app en las pruebas.
AssetBundle rootBundleForTests(WidgetTester tester) =>
    DefaultAssetBundle.of(tester.element(find.byType(Navigator)));
