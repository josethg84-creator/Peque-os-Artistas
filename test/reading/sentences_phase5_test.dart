import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';
import 'package:pequenos_artistas/learning/learning_progress.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/reading_progress.dart';
import 'package:pequenos_artistas/reading/screens/reading_sentences_screen.dart';
import 'package:pequenos_artistas/reading/screens/sentence_games_screen.dart';
import 'package:pequenos_artistas/reading/screens/sentence_reader_screen.dart';
import 'package:pequenos_artistas/reading/sentences.dart';
import 'package:pequenos_artistas/reading/syllabifier.dart';
import 'package:pequenos_artistas/reading/widgets/reading_widgets.dart';
import 'package:pequenos_artistas/reading/widgets/sentence_widgets.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

import '../test_helpers.dart';

final raw = jsonDecode(File(SentenceCatalog.path).readAsStringSync()) as Map<String, dynamic>;
final content = SentenceCatalog.parse(raw);

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

List<String> get spoken => lastNarrator!.spoken;

Future<void> open(WidgetTester tester, Widget screen) async {
  tester.state<NavigatorState>(find.byType(Navigator)).push(MaterialPageRoute<void>(builder: (_) => screen));
  await tester.pumpAndSettle();
}

ReadingController newProgress([KeyValueBackend? backend]) =>
    ReadingController(ReadingStore(backend ?? MemoryBackend()))..load();

String plain(String s) => s
    .toLowerCase()
    .replaceAll('á', 'a')
    .replaceAll('é', 'e')
    .replaceAll('í', 'i')
    .replaceAll('ó', 'o')
    .replaceAll('ú', 'u');

void main() {
  setUp(() => ReadingVoice.clipPlayerFactory = FakeClipPlayer.new);
  tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

  group('catálogo de oraciones', () {
    test('al menos 100 oraciones, con todos los datos y en los 4 niveles', () {
      expect(content.sentences.length, greaterThanOrEqualTo(100));
      for (final level in SentenceCatalog.levels) {
        expect(content.ofLevel(level).length, greaterThanOrEqualTo(20), reason: 'nivel $level');
        expect(content.levelNames[level], isNotEmpty);
      }
      final ids = content.sentences.map((s) => s.id).toSet();
      expect(ids.length, content.sentences.length, reason: 'ids únicos');
      expect(
        content.sentences.length,
        (raw['sentences'] as List).length,
        reason: 'ninguna se descarta al leer',
      );
      for (final s in content.sentences) {
        expect(s.text, matches(RegExp(r'^[A-ZÁÉÍÓÚÑ].*\.$')), reason: s.text);
        expect(s.words.map((w) => w.text).join(' '), s.text.substring(0, s.text.length - 1), reason: s.text);
        expect(s.question.options, hasLength(3), reason: s.text);
        expect({for (final o in s.question.options) o.text}, hasLength(3));
        expect(s.question.explanation, contains(s.text));
        expect(s.image, startsWith('assets/images/aprendo_leer/oraciones/'));
        expect(s.scene, isA<ScenePicture>());
        expect((s.scene as ScenePicture).items, isNotEmpty, reason: '${s.text}: escena con dibujos');
        // La palabra de la pista responde a la pregunta.
        // (Salvo las formas del verbo: «Llueve» → lluvia, «nevando» → nieve.)
        if (const {'Llueve', 'nevando'}.contains(s.words[s.question.hintWord].text)) continue;
        final hint = plain(s.words[s.question.hintWord].text);
        final answer = plain(s.question.options[s.question.answer].text);
        expect(
          hint.substring(0, min(3, hint.length)),
          answer.split(' ').last.substring(0, min(3, answer.split(' ').last.length)),
          reason: '${s.text}: pista «$hint», respuesta «$answer»',
        );
      }
    });

    test('las imágenes de opciones y escenas existen (ninguna sale como estrella de reserva)', () {
      for (final s in raw['sentences'] as List) {
        final q = (s as Map)['question'] as Map;
        for (final o in q['options'] as List) {
          expect(
            SpeechPicture.fromJson((o as Map)['picture']),
            isNotNull,
            reason: '${s['text']}: ${o['text']}',
          );
        }
        for (final item in (s['scene'] as Map)['items'] as List) {
          expect(SpeechPicture.fromJson((item as Map)['p']), isNotNull, reason: '${s['text']}');
          if ((item['p'] as Map)['drawing'] case final String d) {
            final found = Directory('assets/drawings')
                .listSync(recursive: true)
                .any((f) => f.path.endsWith('/$d.svg'));
            expect(found, isTrue, reason: d);
          }
        }
        if (s['image_ready'] == true) expect(File(s['image'] as String).existsSync(), isTrue);
        final audio = s['audio'] as Map;
        if (audio['clip'] case final String c) expect(File(c).existsSync(), isTrue, reason: c);
      }
    });

    test('nivel 1: solo sílabas enseñadas (familias M P S L T N D F C·Q B, vocales e inversas)', () {
      const taught = 'mpsltndfcb';
      bool decodable(String syl) {
        final s = plain(syl);
        if (RegExp(r'^[aeiou]$').hasMatch(s) || RegExp(r'^[aeiou][lsn]$').hasMatch(s)) return true;
        if (RegExp(r'^qu[ei]$').hasMatch(s)) return true;
        final m = RegExp(r'^([a-z])([aeiou])$').firstMatch(s);
        if (m == null) return false;
        if (m[1] == 'c') return 'aou'.contains(m[2]!);
        return taught.contains(m[1]!);
      }

      for (final s in content.ofLevel(1)) {
        for (final w in s.words) {
          if (w.text.toLowerCase() == 'y') continue;
          for (final syl in Syllabifier.split(w.text)) {
            expect(decodable(syl), isTrue, reason: '${s.text}: «$syl» de «${w.text}» no se ha enseñado');
          }
        }
      }
    });

    test('nivel 4 tiene grupos consonánticos; niveles 1-3 no (p. ej. «blanco» y «flores» van al 4)', () {
      const clusters = ['pl', 'bl', 'cl', 'gl', 'fl', 'pr', 'br', 'tr', 'dr', 'cr', 'gr', 'fr'];
      bool hasCluster(String w) => Syllabifier.split(w).any((s) => clusters.any(plain(s).startsWith));
      for (final s in content.sentences) {
        final any = s.words.any((w) => hasCluster(w.text));
        expect(any, s.level == 4, reason: '${s.text} (nivel ${s.level})');
      }
      expect(content.ofLevel(4).map((s) => s.text), contains('El conejo blanco come una zanahoria.'));
      expect(content.ofLevel(4).map((s) => s.text), contains('La mariposa vuela sobre las flores.'));
      for (final s in content.ofLevel(3)) {
        expect(s.words.length, greaterThanOrEqualTo(6), reason: s.text);
      }
    });

    test('«Ordena»: solo oraciones con una única forma (sin «y», 3 a 7 palabras)', () {
      final orderable = content.sentences.where((s) => s.orderable).toList();
      expect(orderable.length, greaterThanOrEqualTo(60));
      for (final s in orderable) {
        expect(s.words.length, inInclusiveRange(3, 7), reason: s.text);
        expect(s.words.map((w) => w.text.toLowerCase()), isNot(contains('y')), reason: s.text);
      }
      // Un adjetivo que puede ir delante del nombre: no se usa.
      expect(content.sentences.firstWhere((s) => s.text.startsWith('El perro pequeño')).orderable, isFalse);
    });

    test('«Escucha y elige»: las otras dos escenas no comparten fondo ni dibujos', () {
      for (final s in content.sentences.where((s) => s.listenOptions.isNotEmpty)) {
        expect(s.listenOptions, hasLength(2));
        final mine = s.scene as ScenePicture;
        for (final id in s.listenOptions) {
          final other = content.byId[id]!.scene as ScenePicture;
          expect(other.background, isNot(mine.background), reason: '${s.text} / $id');
        }
      }
    });
  });

  group('motor de audio: oraciones, palabras y resaltado', () {
    final mama = content.sentences.first; // «Mi mamá me ama.»

    test('1 · reproduce la oración completa con la voz del dispositivo', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      final ok = await voice.playSentence(mama, onWord: (_) {});
      expect(ok, isTrue);
      expect(narrator.spoken, ['Mi mamá me ama.']);
      expect(voice.status, ReadingVoiceStatus.idle);
    });

    test('2 · reproduce una palabra sola, en minúsculas', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      await voice.play(mama.words.first.audio);
      expect(narrator.spoken, ['mi']);
    });

    test('3 · lento: palabra por palabra, despacio, resaltando cada una mientras suena', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      final seen = <int?>[];
      final saidWhenHighlighted = <String>[];
      await voice.playSentence(
        mama,
        speed: ReadingSpeed.slow,
        onWord: (i) {
          seen.add(i);
          if (i != null) saidWhenHighlighted.add(mama.words[i].text);
        },
      );
      expect(narrator.slow, ['mi', 'mamá', 'me', 'ama']);
      expect(seen, [0, 1, 2, 3, null]);
      expect(saidWhenHighlighted, ['Mi', 'mamá', 'me', 'ama']);
      expect(voice.lastHighlight, SentenceHighlight.wordByWord);
    });

    test('4 · normal: el resaltado sigue los avisos REALES de la voz (posición de cada palabra)', () async {
      final narrator = RecordingNarrator()..reportsWords = true;
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      final seen = <int?>[];
      await voice.playSentence(mama, onWord: seen.add);
      expect(narrator.boundaries, [0, 3, 8, 11]);
      expect(seen, [0, 1, 2, 3, null]);
      expect(voice.lastHighlight, SentenceHighlight.voiceEvents);
    });

    test('4 · grabación con tiempos medidos: resalta según la posición del audio', () async {
      final clips = FakeClipPlayer()
        ..positions = const [
          Duration(milliseconds: 0),
          Duration(milliseconds: 350),
          Duration(milliseconds: 900),
          Duration(milliseconds: 1200),
          Duration(milliseconds: 1500),
        ];
      final recorded = ReadingSentence(
        id: 'grabada',
        text: mama.text,
        level: 1,
        families: const ['m'],
        words: mama.words,
        scene: mama.scene,
        image: mama.image,
        imageReady: false,
        clip: 'assets/audio/reading/oraciones/grabada.mp3',
        wordMs: const [0, 300, 800, 1100],
        question: mama.question,
        orderable: true,
        listenOptions: const [],
      );
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: clips);
      final seen = <int?>[];
      await voice.playSentence(recorded, onWord: seen.add);
      expect(clips.played.single.$1, 'assets/audio/reading/oraciones/grabada.mp3');
      expect(narrator.spoken, isEmpty);
      expect(seen, [0, 1, 2, 3, 3, null]);
      expect(voice.lastHighlight, SentenceHighlight.recordedTimes);
    });

    test('5 · si la voz no avisa de las palabras: se oye entera, sin resaltado inventado', () async {
      final narrator = RecordingNarrator(); // no avisa de las palabras
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      final seen = <int?>[];
      final ok = await voice.playSentence(mama, onWord: seen.add);
      expect(ok, isTrue);
      expect(narrator.spoken, ['Mi mamá me ama.']);
      expect(seen, [null], reason: 'ninguna palabra resaltada por temporizador');
      expect(voice.lastHighlight, SentenceHighlight.none);
    });

    test('parar corta la oración y quita el resaltado; nunca se superponen', () async {
      final narrator = RecordingNarrator()..pending = Completer();
      final voice = ReadingVoice(audioWith(narrator: narrator), clips: FakeClipPlayer());
      final seen = <int?>[];
      final first = voice.playSentence(mama, onWord: seen.add);
      await Future<void>.delayed(Duration.zero);
      await voice.stop();
      narrator.pending!.complete();
      narrator.pending = null;
      expect(await first, isFalse);
      expect(narrator.stops, greaterThan(0));
      expect(voice.status, ReadingVoiceStatus.idle);
    });

    test('sin sonido en los ajustes: no suena y se explica', () async {
      final narrator = RecordingNarrator();
      final voice = ReadingVoice(
        audioWith(narrator: narrator, settings: const LearningSettings(voiceOn: false)),
        clips: FakeClipPlayer(),
      );
      expect(await voice.playSentence(mama, onWord: (_) {}), isFalse);
      expect(voice.status, ReadingVoiceStatus.muted);
      expect(narrator.spoken, isEmpty);
    });

    test('los avisos de palabra solo llegan de la frase actual', () async {
      final narrator = RecordingNarrator()..reportsWords = true;
      final audio = audioWith(narrator: narrator);
      final got = <int>[];
      await audio.say('uno dos', onBoundary: got.add);
      expect(got, [0, 4]);
    });
  });

  group('lógica de los juegos', () {
    final s = content.sentences.first;

    test('6 · comprensión: opciones barajadas, error sin castigo y pista', () {
      final r = ComprehensionRound(s, random: Random(1));
      expect(r.options.map((o) => o.text).toSet(), s.question.options.map((o) => o.text).toSet());
      final wrong = (r.correctIndex + 1) % 3;
      expect(r.choose(wrong), isFalse);
      expect(r.wrong, {wrong});
      expect(r.solved, isFalse);
      expect(r.choose(r.correctIndex), isTrue);
      expect(r.firstTry, isFalse);
    });

    test('7 · ordenar: empieza desordenada, se comprueba, la pista coloca la siguiente', () {
      final target = content.sentences.firstWhere((x) => x.orderable && x.words.length >= 4);
      final r = OrderRound(target, random: Random(2));
      expect([for (final i in r.bank) r.pieces[i]].join(' '), isNot(r.pieces.join(' ')));
      // Al revés: incorrecta.
      for (final i in [...r.bank].reversed) {
        r.place(i);
      }
      if (r.check()) fail('el orden inverso no debería valer');
      expect(r.wrongAttempts, 1);
      // La pista quita las mal puestas y coloca la primera correcta.
      r.hint();
      expect(r.pieces[r.placed.first], r.pieces.first);
      while (!r.complete) {
        r.hint();
      }
      expect(r.check(), isTrue);
      expect(r.firstTry, isFalse);
    });

    test('7 · ordenar: si una palabra se repite, vale cualquiera de las dos', () {
      final rep = content.sentences.firstWhere((x) => x.text == 'La nube tapa la luna.');
      final r = OrderRound(rep, random: Random(3));
      // «la» aparece una vez en minúscula: colocar por texto.
      for (final word in rep.pieces) {
        r.place(r.bank.firstWhere((i) => r.pieces[i] == word));
      }
      expect(r.check(), isTrue);
    });

    test('8 · escuchar y elegir: tres dibujos, uno correcto', () {
      final r = ListenSelectRound(s, content, random: Random(4));
      expect(r.choices, hasLength(3));
      expect(r.choices, contains(s));
      expect(r.choose((r.correctIndex + 1) % 3), isFalse);
      expect(r.choose(r.correctIndex), isTrue);
    });
  });

  group('9 · progreso', () {
    test('escuchar no es leer; leída sin ayuda solo si se acierta sin escucharla', () async {
      final backend = MemoryBackend();
      final p = newProgress(backend);
      await p.load();
      p.recordSentenceHeard('a');
      p.recordWordPlayed('Mamá');
      p.recordQuestionAnswered('a');
      p.recordSentenceAttempt();
      p.recordQuestionSolved('a', firstTry: false, usedHints: true, listenedFirst: true);
      p.recordQuestionSolved('b', firstTry: true, usedHints: false, listenedFirst: false);
      await p.flush();
      final again = newProgress(backend);
      await again.load();
      final g = again.progress;
      expect(g.sentencesHeard, {'a'});
      expect(g.sentencesReadAlone, {'b'}, reason: '«a» se escuchó antes de responder');
      expect(g.wordsPlayed, {'mamá'});
      expect(g.questionsAnswered, {'a', 'b'});
      expect(g.questionsCorrect, {'a', 'b'});
      expect(g.sentenceAttempts, 1);
      expect(g.withHints, contains(ReadingProgress.key(ReadingController.sentenceQuestionMode, 'a')));
      expect(g.firstTry, contains(ReadingProgress.key(ReadingController.sentenceQuestionMode, 'b')));
    });

    test('el progreso guardado antes de la Fase 5 se sigue leyendo', () {
      final old = ReadingProgress(
        completed: {
          'completa_pato': {'elige'},
        },
        attempts: 3,
      );
      final json = old.toJson()
        ..removeWhere((k, _) => k.startsWith('sentence') || k.startsWith('questions') || k == 'words_played');
      final payload = {'format_version': ReadingStore.formatVersion, ...json};
      final back = ReadingProgress.fromJson(payload);
      expect(back.completed['completa_pato'], {'elige'});
      expect(back.sentencesHeard, isEmpty);
      expect(back.sentenceLevel, 1);
    });

    test('10 · los niveles se abren al resolver 8 preguntas del anterior', () async {
      final p = newProgress();
      await p.load();
      Iterable<String> idsOf(int l) => content.ofLevel(l).map((s) => s.id);
      expect(p.sentenceLevelOpen(1, idsOf), isTrue);
      expect(p.sentenceLevelOpen(2, idsOf), isFalse);
      for (final s in content.ofLevel(1).take(ReadingController.unlockAfter)) {
        p.recordQuestionSolved(s.id, firstTry: true, usedHints: false, listenedFirst: true);
      }
      expect(p.sentenceLevelOpen(2, idsOf), isTrue);
      expect(p.sentenceLevelOpen(3, idsOf), isFalse);
      expect(p.progress.sentenceLevel, 2);
    });
  });

  group('pantallas', () {
    testWidgets('lector: escuchar, lento, repetir, tocar una palabra, escuchar palabra, parar y navegar', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 900));
      final progress = newProgress();
      await pumpApp(tester, reading: progress);
      await open(tester, const SentenceReaderScreen(args: SentenceReaderArgs(level: 1)));
      expect(find.byType(SentenceWords), findsOneWidget);
      expect(find.text('Ilustración provisional'), findsOneWidget);

      lastNarrator!.reportsWords = true;
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la oración'));
      expect(spoken.last, 'Mi mamá me ama.');
      expect(progress.progress.sentencesHeard, contains('oracion_1_01'));

      await tapAndSettle(tester, find.bySemanticsLabel('Velocidad Lento'));
      await tapAndSettle(tester, find.bySemanticsLabel('Repetir la oración'));
      expect(lastNarrator!.slow, containsAllInOrder(['mi', 'mamá', 'me', 'ama']));

      await tapAndSettle(tester, find.bySemanticsLabel('Palabra mamá'));
      expect(spoken.last, 'mamá');
      expect(progress.progress.wordsPlayed, contains('mamá'));
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la palabra mamá'));
      expect(spoken.last, 'mamá');

      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente oración'));
      await tapAndSettle(tester, find.bySemanticsLabel('Velocidad Normal'));
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la oración'));
      expect(spoken.last, 'Papá toma sopa.');
      await tapAndSettle(tester, find.bySemanticsLabel('Anterior'));
      expect(find.bySemanticsLabel('Oración: Mi mamá me ama.'), findsOneWidget);
    });

    testWidgets('lector: resaltado visible mientras suena una palabra', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await open(tester, const SentenceReaderScreen(args: SentenceReaderArgs(level: 1)));
      lastNarrator!.pending = Completer();
      await tester.tap(find.bySemanticsLabel('Palabra ama'));
      await tester.pump();
      final node = tester.getSemantics(find.bySemanticsLabel('Palabra ama'));
      expect(node.flagsCollection.isSelected, ui.Tristate.isTrue);
      lastNarrator!.pending!.complete();
      lastNarrator!.pending = null;
      await tester.pumpAndSettle();
    });

    testWidgets('lector: sin avisos de palabra, aviso honesto (no se inventa el resaltado)', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await open(tester, const SentenceReaderScreen(args: SentenceReaderArgs(level: 1)));
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la oración'));
      expect(find.textContaining('no avisa de qué palabra'), findsOneWidget);
    });

    testWidgets('6 · comprensión: error → «Casi», pista con la palabra; acierto → se guarda', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final progress = newProgress();
      await pumpApp(tester, reading: progress);
      await open(
        tester,
        const SentenceGameScreen(
          args: SentenceGameArgs(activity: SentenceActivity.question, sentenceId: 'oracion_1_02'),
          seed: 1,
        ),
      );
      expect(spoken.last, '¿Qué toma papá?');
      await tapAndSettle(tester, find.bySemanticsLabel('Respuesta: pizza'));
      expect(find.byType(ReadingTryAgain), findsOneWidget);
      expect(find.bySemanticsLabel('Respuesta: pizza, no es esta'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Pista'));
      expect(find.bySemanticsLabel('Palabra sopa, pista'), findsOneWidget);
      expect(spoken.last, 'sopa');
      await tapAndSettle(tester, find.bySemanticsLabel('Respuesta: sopa'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(find.textContaining('La oración dice'), findsOneWidget);
      final p = progress.progress;
      expect(p.questionsCorrect, contains('oracion_1_02'));
      expect(p.sentencesReadAlone, isEmpty, reason: 'escuchó la pista antes de acertar');
      expect(p.withHints, contains('comprende:oracion_1_02'));
    });

    testWidgets('6 · comprensión sin escuchar: cuenta como leída sin ayuda', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final progress = newProgress();
      await pumpApp(tester, reading: progress);
      await open(
        tester,
        const SentenceGameScreen(
          args: SentenceGameArgs(activity: SentenceActivity.question, sentenceId: 'oracion_1_03'),
          seed: 1,
        ),
      );
      await tapAndSettle(tester, find.bySemanticsLabel('Respuesta: pato'));
      expect(progress.progress.sentencesReadAlone, {'oracion_1_03'});
      expect(progress.progress.firstTry, contains('comprende:oracion_1_03'));
    });

    testWidgets('7 · ordena la oración tocando las palabras', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final progress = newProgress();
      await pumpApp(tester, reading: progress);
      await open(
        tester,
        const SentenceGameScreen(
          args: SentenceGameArgs(activity: SentenceActivity.order, sentenceId: 'oracion_1_02'),
          seed: 5,
        ),
      );
      for (final w in ['Papá', 'toma', 'sopa.']) {
        await tapAndSettle(tester, find.bySemanticsLabel('Palabra ${w.replaceAll('.', '')}').last);
      }
      expect(find.bySemanticsLabel('Tu oración: Papá toma sopa.'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(progress.isCompleted('oracion_1_02', ReadingController.sentenceOrderMode), isTrue);
    });

    testWidgets('7 · ordena la oración arrastrando, y quitar una palabra', (tester) async {
      setScreenSize(tester, const Size(420, 1400));
      await pumpApp(tester);
      await open(
        tester,
        const SentenceGameScreen(
          args: SentenceGameArgs(activity: SentenceActivity.order, sentenceId: 'oracion_1_02'),
          seed: 5,
        ),
      );
      Future<void> drag(String word) async {
        final from = tester.getCenter(find.bySemanticsLabel('Palabra $word').last);
        final to = tester.getCenter(find.bySemanticsLabel(RegExp('^Tu oración')));
        final g = await tester.startGesture(from);
        await tester.pump(const Duration(milliseconds: 100));
        await g.moveBy(const Offset(0, -20));
        await tester.pump(const Duration(milliseconds: 50));
        await g.moveTo(to);
        await tester.pump(const Duration(milliseconds: 50));
        await g.up();
        await tester.pumpAndSettle();
      }

      await drag('Papá');
      expect(find.bySemanticsLabel('Tu oración: Papá'), findsOneWidget);
      await drag('sopa');
      // Tocar una palabra colocada la devuelve.
      await tapAndSettle(tester, find.bySemanticsLabel('Palabra sopa').first);
      expect(find.bySemanticsLabel('Tu oración: Papá'), findsOneWidget);
      await drag('toma');
      await drag('sopa');
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
    });

    testWidgets('8 · escucha y elige: suena al empezar; un error marca el dibujo; se acierta', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 900));
      final progress = newProgress();
      await pumpApp(tester, reading: progress);
      await open(
        tester,
        const SentenceGameScreen(
          args: SentenceGameArgs(activity: SentenceActivity.listen, sentenceId: 'oracion_1_01'),
          seed: 2,
        ),
      );
      expect(spoken.first, 'Mi mamá me ama.');
      final round = ListenSelectRound(content.byId['oracion_1_01']!, content, random: Random(2));
      final wrong = (round.correctIndex + 1) % 3;
      await tapAndSettle(tester, find.bySemanticsLabel('Dibujo ${wrong + 1} de 3'));
      expect(find.bySemanticsLabel('Dibujo ${wrong + 1} de 3, no es esta'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Dibujo ${round.correctIndex + 1} de 3'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(progress.isCompleted('oracion_1_01', ReadingController.sentenceListenMode), isTrue);
    });

    testWidgets('10 · niveles: el 2 está cerrado al principio y se abre tras 8 preguntas', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final progress = newProgress();
      await pumpApp(tester, reading: progress);
      unawaited(tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.readingSentences));
      await tester.pumpAndSettle();
      expect(find.bySemanticsLabel(RegExp(r'^Nivel 2: .*Se abre')), findsOneWidget);
      for (final s in content.ofLevel(1).take(ReadingController.unlockAfter)) {
        progress.recordQuestionSolved(s.id, firstTry: true, usedHints: false, listenedFirst: true);
      }
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Nivel 2: .*de \d+ oraciones')));
      await tapAndSettle(tester, find.bySemanticsLabel('Leer oraciones'));
      expect(find.byType(SentenceReaderScreen), findsOneWidget);
      expect(find.textContaining('Nivel 2'), findsOneWidget);
    });

    for (final (size, scale) in const [
      (Size(360, 720), 1.0),
      (Size(360, 720), 1.3),
      (Size(800, 1280), 1.0),
      (Size(1280, 800), 1.6),
    ]) {
      testWidgets('11 · ${size.width.toInt()}×${size.height.toInt()} texto ×$scale: sin desbordamientos', (
        tester,
      ) async {
        setScreenSize(tester, size, textScale: scale);
        await pumpApp(tester);
        final screens = <Widget>[
          const ReadingSentencesScreen(),
          for (final level in SentenceCatalog.levels)
            SentenceReaderScreen(args: SentenceReaderArgs(level: level)),
          for (final a in [SentenceActivity.question, SentenceActivity.order, SentenceActivity.listen])
            for (final level in SentenceCatalog.levels)
              SentenceGameScreen(
                args: SentenceGameArgs(activity: a, level: level),
                seed: 1,
              ),
        ];
        for (final screen in screens) {
          await open(tester, screen);
          expect(tester.takeException(), isNull, reason: '$screen');
          tester.state<NavigatorState>(find.byType(Navigator)).pop();
          await tester.pumpAndSettle();
        }
      });
    }
  });
}
