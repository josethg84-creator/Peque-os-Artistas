import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_router.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/complete_words.dart';
import 'package:pequenos_artistas/reading/reading_progress.dart';
import 'package:pequenos_artistas/reading/screens/complete_words_game_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_words_screen.dart';
import 'package:pequenos_artistas/reading/syllabifier.dart';
import 'package:pequenos_artistas/reading/widgets/reading_widgets.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

import '../test_helpers.dart';

final raw = jsonDecode(File(CompleteWordsContent.path).readAsStringSync()) as Map<String, dynamic>;
final content = CompleteWordsContent.parse(raw);

String plain(String s) => s
    .toLowerCase()
    .replaceAll('á', 'a')
    .replaceAll('é', 'e')
    .replaceAll('í', 'i')
    .replaceAll('ó', 'o')
    .replaceAll('ú', 'u');

/// Cómo suena (seseo y yeísmo), igual que el generador.
String sound(String s) {
  var x = plain(s);
  x = x.replaceAll(RegExp(r'qu(?=[ei])'), 'k').replaceAll(RegExp(r'gu(?=[ei])'), 'g');
  x = x.replaceAll(RegExp(r'c(?=[ei])'), 's').replaceAll(RegExp(r'g(?=[ei])'), 'j');
  return x
      .replaceAll('c', 'k')
      .replaceAll('z', 's')
      .replaceAll('v', 'b')
      .replaceAll('ll', 'y')
      .replaceAll('h', '');
}

const clusters = {'pl', 'bl', 'cl', 'gl', 'fl', 'pr', 'br', 'tr', 'dr', 'cr', 'gr', 'fr'};
bool isCluster(String s) => clusters.any(plain(s).startsWith);

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

/// Los ejercicios que verá la partida con [seed] (misma lógica que la pantalla).
List<CompleteExercise> sessionFor(int level, CompleteMode mode, int seed, {ReadingController? progress}) =>
    content.session(
      level,
      mode,
      done: (e) => progress?.isCompleted(e.id, mode.id) ?? false,
      random: Random(seed),
    );

Future<ReadingController> openGame(
  WidgetTester tester,
  int level,
  CompleteMode mode, {
  int seed = 3,
  ReadingController? reading,
}) async {
  setScreenSize(tester, const Size(420, 900));
  final controller =
      reading ?? (ReadingController(ReadingStore(MemoryBackend()), celebrations: false)..load());
  await pumpApp(tester, reading: controller);
  tester
      .state<NavigatorState>(find.byType(Navigator))
      .push(
        MaterialPageRoute<void>(
          builder: (_) => CompleteWordsGameScreen(
            args: CompleteGameArgs(level: level, mode: mode),
            seed: seed,
          ),
        ),
      );
  await tester.pumpAndSettle();
  return controller;
}

void main() {
  group('catálogo', () {
    test('al menos 100 palabras, con los ejemplos pedidos bien separados y en su nivel', () {
      expect(content.words.length, greaterThanOrEqualTo(100));
      const examples = {
        'pato': ('pa-to', 1),
        'sapo': ('sa-po', 1),
        'mesa': ('me-sa', 1),
        'luna': ('lu-na', 1),
        'gato': ('ga-to', 1),
        'casa': ('ca-sa', 1),
        'moto': ('mo-to', 1),
        'puma': ('pu-ma', 1),
        'pelota': ('pe-lo-ta', 2),
        'maleta': ('ma-le-ta', 2),
        'zapato': ('za-pa-to', 2),
        'camisa': ('ca-mi-sa', 2),
        'moneda': ('mo-ne-da', 2),
        'mariposa': ('ma-ri-po-sa', 2),
        'manzana': ('man-za-na', 2),
        'plato': ('pla-to', 3),
        'brazo': ('bra-zo', 3),
        'flor': ('flor', 3),
        'tren': ('tren', 3),
        'globo': ('glo-bo', 3),
        'fruta': ('fru-ta', 3),
        'dragon': ('dra-gón', 3),
      };
      for (final MapEntry(key: id, value: (split, level)) in examples.entries) {
        final w = content.words[id]!;
        expect(w.syllables.join('-'), split, reason: id);
        expect(w.level, level, reason: id);
      }
      for (final level in [1, 2, 3]) {
        expect(
          content.words.values.where((w) => w.level == level).length,
          greaterThanOrEqualTo(30),
          reason: '$level',
        );
      }
    });

    test('ortografía y separación de cada palabra, validadas con el silabeador de Dart', () {
      for (final w in content.words.values) {
        expect(w.syllables.join(), w.text, reason: w.text);
        expect(Syllabifier.split(w.text), w.syllables, reason: w.text);
        expect(w.text, isNot(contains(RegExp('[A-Z0-9 ]'))), reason: w.text);
      }
    });

    test('cada ejercicio: id único, todos los campos y UNA sola respuesta correcta sin ambigüedad', () {
      final ids = <String>{};
      final catalog = {for (final w in content.words.values) plain(w.text)};
      for (final e in content.exercises) {
        expect(ids.add(e.id), isTrue, reason: e.id);
        final w = content.wordOf(e);
        expect(e.syllables, w.syllables);
        expect(e.answer, e.syllables[e.missing]);
        expect(e.category, isNotEmpty);
        expect(e.options.where(e.isRight), hasLength(1), reason: e.id);
        expect(e.options.length, e.level == 1 ? 3 : 4, reason: e.id);
        expect(
          {for (final o in e.options) sound(o)},
          hasLength(e.options.length),
          reason: '${e.id}: opciones que suenan igual',
        );
        for (final o in e.options.where((o) => !e.isRight(o))) {
          final formed = [...e.syllables]..[e.missing] = o;
          expect(catalog, isNot(contains(plain(formed.join()))), reason: '${e.id}: «$o» forma otra palabra');
          expect(
            isCluster(o),
            isCluster(e.answer),
            reason: '${e.id}: «$o» no tiene la forma de «${e.answer}»',
          );
          expect(Syllabifier.split(o), [o], reason: '«$o» es una sílaba');
        }
        expect(e.orderable, e.syllables.length >= 2);
      }
    });

    test('imágenes: las que hay se ven; las que faltan no entran en los juegos', () {
      final rawWords = {for (final w in raw['words'] as List) (w as Map)['id']: w};
      for (final w in content.words.values) {
        if (rawWords[w.id]!['picture'] != null) {
          expect(SpeechPicture.fromJson(rawWords[w.id]!['picture']), isNotNull, reason: w.text);
        }
      }
      final pending = {for (final e in content.pendingImage) e.wordId};
      expect(pending, isNotEmpty);
      for (final mode in CompleteMode.values) {
        for (final level in [1, 2, 3]) {
          final p = content.playable(level, mode);
          expect(p.length, greaterThanOrEqualTo(ReadingController.unlockAfter), reason: '$level ${mode.id}');
          expect(p.where((e) => pending.contains(e.wordId)), isEmpty);
        }
      }
      expect(
        content.playable(3, CompleteMode.order).map((e) => e.wordId),
        isNot(contains('flor')),
        reason: 'una sola sílaba no se ordena',
      );
    });
  });

  group('lógica de las pistas', () {
    test('tras dos intentos fallidos se quita una opción equivocada (nunca quedan menos de dos)', () {
      final e = content.exercises.firstWhere((e) => e.level == 2);
      final r = CompleteRound(e, CompleteMode.choose, Random(1));
      final wrong = e.options.firstWhere((o) => !e.isRight(o));
      r.chosen = wrong;
      expect(r.check(), isFalse);
      expect(r.options, hasLength(4));
      r.chosen = r.options.firstWhere((o) => !e.isRight(o));
      expect(r.check(), isFalse);
      expect(r.options, hasLength(3));
      expect(r.options, contains(e.answer));
      for (var i = 0; i < 5; i++) {
        r.chosen = r.options.firstWhere((o) => !e.isRight(o));
        r.check();
      }
      expect(r.options.length, 2);
      r.chosen = e.answer;
      expect(r.check(), isTrue);
      expect(r.solved, isTrue);
    });

    test(
      'ordenar: las tarjetas empiezan desordenadas; se comprueba el orden y la ayuda señala la siguiente',
      () {
        for (final e in content.exercises.where((e) => e.orderable)) {
          final r = CompleteRound(e, CompleteMode.order, Random(4));
          expect(
            r.pieces.map((p) => p.$2).join(),
            isNot(e.syllables.join()),
            reason: '${e.id} ya venía en orden',
          );
        }
        final e = content.exercises.firstWhere((e) => e.wordId == 'mariposa');
        final r = CompleteRound(e, CompleteMode.order, Random(4));
        expect(r.nextPiece, 0);
        int pieceOf(String s) => r.pieces.firstWhere((p) => p.$2 == s && !r.placed.contains(p.$1)).$1;
        r.placed.addAll([pieceOf('ma'), pieceOf('po')]);
        expect(r.nextPiece, isNull, reason: 'ya hay un error: primero hay que corregirlo');
        expect(r.check(), isFalse);
        expect(r.placed, isEmpty);
        for (final s in e.syllables) {
          r.placed.add(pieceOf(s));
        }
        expect(r.check(), isTrue);
      },
    );
  });

  group('progreso', () {
    test('se guarda con su propia clave, sobrevive a reiniciar y se recupera de la copia', () async {
      final backend = MemoryBackend();
      final c = ReadingController(ReadingStore(backend), celebrations: false);
      await c.load();
      c.recordAttempt(correct: false);
      c.recordAttempt(correct: true);
      c.recordCompleted('completa_pato', 'elige', firstTry: false, usedHints: true);
      c.recordCompleted('completa_gato', 'arrastra', firstTry: true, usedHints: false);
      await c.flush();
      final again = ReadingController(ReadingStore(backend), celebrations: false);
      await again.load();
      expect(again.progress.attempts, 2);
      expect(again.progress.correctAnswers, 1);
      expect(again.isCompleted('completa_pato', 'elige'), isTrue);
      expect(again.isCompleted('completa_pato', 'arrastra'), isFalse);
      expect(again.progress.withHints, {'elige:completa_pato'});
      expect(again.progress.firstTry, {'arrastra:completa_gato'});
      expect(ReadingStore.key, 'reading.v1.state');
      // Dañado: se usa la copia anterior.
      again.recordCompleted('completa_casa', 'elige', firstTry: true, usedHints: false);
      await again.flush();
      await backend.write(ReadingStore.key, '{"roto": ');
      final recovered = await ReadingStore(backend).load();
      expect(recovered.completed.keys, containsAll(['completa_pato', 'completa_gato']));
      // Un checksum que no cuadra no se acepta.
      final tampered = ReadingStore.encode(again.progress).replaceFirst('completa_pato', 'completa_xxx');
      expect(ReadingStore.decode(tampered), isNull);
      await again.clearAll();
      expect(await backend.read(ReadingStore.key), isNull);
    });

    test('el nivel siguiente se abre al completar ${ReadingController.unlockAfter} del anterior', () async {
      final c = ReadingController(ReadingStore(MemoryBackend()), celebrations: false);
      expect(levelUnlocked(content, c, 1), isTrue);
      expect(levelUnlocked(content, c, 2), isFalse);
      final level1 = content.playable(1, CompleteMode.choose);
      for (final e in level1.take(ReadingController.unlockAfter - 1)) {
        c.recordCompleted(e.id, 'elige', firstTry: true, usedHints: false);
      }
      expect(levelUnlocked(content, c, 2), isFalse);
      c.recordCompleted(level1.last.id, 'ordena', firstTry: true, usedHints: false);
      expect(levelUnlocked(content, c, 2), isTrue);
      expect(levelUnlocked(content, c, 3), isFalse);
    });
  });

  group('pantallas', () {
    setUp(() => ReadingVoice.clipPlayerFactory = FakeClipPlayer.new);
    tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

    testWidgets('modo «elige»: escuchar, error amable, pistas, acierto con la palabra y progreso', (
      tester,
    ) async {
      final reading = await openGame(tester, 2, CompleteMode.choose);
      final e = sessionFor(2, CompleteMode.choose, 3).first;
      final word = content.wordOf(e);
      expect(spoken.last, word.text, reason: 'la palabra suena al empezar');
      expect(find.text(CompleteWordsGameScreen.instruction), findsOneWidget);
      expect(find.bySemanticsLabel('Dibujo: ${word.text}'), findsOneWidget);
      final shown = [...e.syllables]..[e.missing] = 'hueco';
      expect(find.bySemanticsLabel('Palabra por sílabas: ${shown.join(' - ')}'), findsOneWidget);
      // Un error: sin castigo, «¡Casi!», se puede volver a escuchar.
      final wrong = e.options.firstWhere((o) => !e.isRight(o));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba $wrong'));
      expect(spoken.last, wrong);
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.text(CompleteWordsGameScreen.tryAgain), findsOneWidget);
      expect(spoken.last, CompleteWordsGameScreen.tryAgain);
      expect(find.bySemanticsLabel('Siguiente'), findsNothing, reason: 'no se avanza sin acertar');
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la palabra'));
      expect(spoken.last, word.text);
      // Pistas: despacio, la sílaba que falta, primera letra y, después, la respuesta.
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la palabra despacio'));
      expect(lastNarrator!.slow.last, word.text);
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la sílaba que falta'));
      expect(spoken.last, e.answer.toLowerCase());
      await tapAndSettle(tester, find.bySemanticsLabel('Pista'));
      final first = [...e.syllables]..[e.missing] = '${e.answer.characters.first}…';
      expect(find.bySemanticsLabel('Palabra por sílabas: ${first.join(' - ')}'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Pista'));
      // Acierto: la palabra completa y la felicitación.
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${e.answer}'));
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(spoken.sublist(spoken.length - 2), [word.text, CompleteWordsGameScreen.praise]);
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(reading.progress.attempts, 2);
      expect(reading.progress.correctAnswers, 1);
      expect(reading.isCompleted(e.id, 'elige'), isTrue);
      expect(reading.progress.withHints, {'elige:${e.id}'});
      expect(reading.progress.firstTry, isEmpty);
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      expect(spoken.last, content.wordOf(sessionFor(2, CompleteMode.choose, 3)[1]).text);
    });

    testWidgets('modo «arrastra»: la sílaba se arrastra al hueco; también vale tocarla', (tester) async {
      final reading = await openGame(tester, 1, CompleteMode.drag);
      final s = sessionFor(1, CompleteMode.drag, 3);
      for (final (i, e) in s.take(2).indexed) {
        final option = find.bySemanticsLabel('Sílaba ${e.answer}');
        await tester.ensureVisible(option);
        await tester.pumpAndSettle();
        if (i == 0) {
          // Arrastrar de verdad hasta el hueco.
          final slot = find.bySemanticsLabel('Hueco para soltar la sílaba');
          final gesture = await tester.startGesture(tester.getCenter(option));
          await tester.pump(const Duration(milliseconds: 50));
          await gesture.moveTo(tester.getCenter(slot));
          await tester.pump(const Duration(milliseconds: 50));
          await gesture.up();
          await tester.pumpAndSettle();
        } else {
          await tester.tap(option); // alternativa por toque
          await tester.pumpAndSettle();
        }
        final filled = [...e.syllables]..[e.missing] = e.answer;
        expect(
          find.bySemanticsLabel(RegExp('^Palabra por sílabas: ${filled.join(' - ')}')),
          findsOneWidget,
          reason: e.id,
        );
        await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
        expect(reading.isCompleted(e.id, 'arrastra'), isTrue, reason: e.id);
        expect(reading.progress.firstTry, contains('arrastra:${e.id}'));
        await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      }
    });

    testWidgets('modo «ordena»: tocar en orden, quitar la última, error amable y acierto', (tester) async {
      final reading = await openGame(tester, 2, CompleteMode.order);
      final e = sessionFor(2, CompleteMode.order, 3).first;
      final syllables = e.syllables;
      // En el orden equivocado (al revés): no vale y se puede repetir.
      for (final s in syllables.reversed) {
        await tapAndSettle(tester, find.bySemanticsLabel('Sílaba $s'));
      }
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.text(CompleteWordsGameScreen.tryAgain), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${syllables.first}'));
      await tapAndSettle(tester, find.bySemanticsLabel('Quitar la última'));
      expect(find.bySemanticsLabel(RegExp(r'^Palabra por sílabas: \? - \?')), findsOneWidget);
      for (final s in syllables) {
        await tapAndSettle(tester, find.bySemanticsLabel('Sílaba $s'));
      }
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(reading.isCompleted(e.id, 'ordena'), isTrue);
    });

    testWidgets('partida completa: resumen, progreso guardado y el nivel 2 se abre', (tester) async {
      final backend = MemoryBackend();
      final reading = await openGame(
        tester,
        1,
        CompleteMode.choose,
        reading: ReadingController(ReadingStore(backend), celebrations: false)..load(),
      );
      final s = sessionFor(1, CompleteMode.choose, 3);
      expect(s, hasLength(8));
      for (final (i, e) in s.indexed) {
        await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${e.answer}'));
        await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
        await tapAndSettle(tester, find.bySemanticsLabel(i == s.length - 1 ? 'Terminar' : 'Siguiente'));
      }
      expect(find.bySemanticsLabel('Acertaste 8 de 8 a la primera'), findsOneWidget);
      expect(find.bySemanticsLabel('Siguiente nivel'), findsOneWidget);
      await reading.flush();
      final restarted = ReadingController(ReadingStore(backend), celebrations: false);
      await restarted.load();
      expect(restarted.completedIn(s.map((e) => e.id), 'elige'), 8);
      expect(levelUnlocked(content, restarted, 2), isTrue);
      // La siguiente partida empieza por palabras aún no hechas.
      final next = sessionFor(1, CompleteMode.choose, 9, progress: restarted);
      expect(next.first.id, isNot(isIn(s.map((e) => e.id))));
    });

    testWidgets('elegir nivel y modo: los niveles cerrados no se pueden jugar todavía', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.readingWords);
      await tester.pumpAndSettle();
      expect(find.byType(ReadingWordsScreen), findsOneWidget);
      expect(find.bySemanticsLabel(RegExp('^Nivel 2: Palabras largas. Se abre')), findsOneWidget);
      // Tocar un nivel cerrado no lo elige: se sigue en el nivel 1.
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Nivel 2:')));
      await tapAndSettle(tester, find.bySemanticsLabel('Elige la sílaba'));
      final game = tester.widget<CompleteWordsGameScreen>(find.byType(CompleteWordsGameScreen));
      expect(game.args.level, 1);
      expect(game.args.mode, CompleteMode.choose);
    });

    for (final (size, scale) in const [
      (Size(360, 720), 1.0),
      (Size(360, 720), 1.3),
      (Size(1280, 800), 1.0),
      (Size(800, 1280), 1.6),
    ]) {
      testWidgets(
        '${size.width.toInt()}×${size.height.toInt()} texto ×$scale: los 3 modos sin desbordamientos',
        (tester) async {
          setScreenSize(tester, size, textScale: scale);
          await pumpApp(tester);
          for (final mode in CompleteMode.values) {
            tester
                .state<NavigatorState>(find.byType(Navigator))
                .push(
                  MaterialPageRoute<void>(
                    builder: (_) =>
                        CompleteWordsGameScreen(args: CompleteGameArgs(level: 2, mode: mode), seed: 1),
                  ),
                );
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull, reason: mode.id);
            tester.state<NavigatorState>(find.byType(Navigator)).pop();
            await tester.pumpAndSettle();
          }
          tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.readingWords);
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
        },
      );
    }

    test('las partidas van sin música', () {
      expect(AppRouter.musicFor(AppRoutes.readingWordsGame, const SizedBox()), isNull);
      expect(AppRouter.musicFor(AppRoutes.readingWords, const SizedBox()), isNull);
    });
  });
}
