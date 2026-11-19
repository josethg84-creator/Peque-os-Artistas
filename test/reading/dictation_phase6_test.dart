import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/complete_words.dart';
import 'package:pequenos_artistas/reading/dictation.dart';
import 'package:pequenos_artistas/reading/reading_progress.dart';
import 'package:pequenos_artistas/reading/screens/dictation_game_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_dictation_screen.dart';
import 'package:pequenos_artistas/reading/sentences.dart';
import 'package:pequenos_artistas/reading/syllabifier.dart';
import 'package:pequenos_artistas/reading/widgets/reading_widgets.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

import '../test_helpers.dart';

final raw = jsonDecode(File(DictationCatalog.path).readAsStringSync()) as Map<String, dynamic>;
final catalog = DictationCatalog.parse(raw);
Dictation byText(DictationType t, String text) =>
    catalog.dictations.firstWhere((d) => d.type == t && d.text == text);

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

ReadingController newProgress([KeyValueBackend? backend]) => ReadingController(
  ReadingStore(backend ?? MemoryBackend()),
  clock: () => DateTime(2026, 11, 17),
  celebrations: false,
)..load();

/// El primer dictado de la partida (misma lógica que la pantalla, sin progreso).
Dictation firstOf(int level, int seed) {
  final all = [...catalog.ofLevel(level)]..shuffle(Random(seed));
  all.sort((a, b) => a.difficulty - b.difficulty);
  return all.first;
}

Future<ReadingController> openGame(WidgetTester tester, int level, DictationMode mode, {int seed = 1}) async {
  setScreenSize(tester, const Size(420, 1100));
  final progress = newProgress();
  await pumpApp(tester, reading: progress);
  tester
      .state<NavigatorState>(find.byType(Navigator))
      .push(
        MaterialPageRoute<void>(
          builder: (_) => DictationGameScreen(
            args: DictationArgs(level: level, mode: mode),
            seed: seed,
          ),
        ),
      );
  await tester.pumpAndSettle();
  return progress;
}

DictationResult check(Dictation d, String s) => DictationChecker.check(d, s);

void main() {
  setUp(() => ReadingVoice.clipPlayerFactory = FakeClipPlayer.new);
  tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

  group('catálogo', () {
    test('50 sílabas, 100 palabras y 50 oraciones, con todos los datos', () {
      final byType = {
        for (final t in DictationType.values) t: catalog.dictations.where((d) => d.type == t).length,
      };
      expect(byType, {DictationType.syllable: 50, DictationType.word: 100, DictationType.sentence: 50});
      expect(catalog.dictations.length, (raw['dictations'] as List).length, reason: 'ninguno se descarta');
      expect(catalog.byId.length, 200, reason: 'ids únicos');
      for (final d in catalog.dictations) {
        expect(d.audio.tts, isNotEmpty);
        expect(d.modes, isNotEmpty);
        expect(d.countLabel, isNotEmpty);
        // Las tarjetas contienen la respuesta.
        for (final p in d.target) {
          expect(d.cards, contains(p), reason: d.id);
        }
        if (d.type != DictationType.syllable) expect(d.picture, isNotNull, reason: '${d.id}: imagen');
        if (d.type == DictationType.word) {
          expect(d.target, Syllabifier.split(d.text), reason: d.text);
        }
        if (d.type == DictationType.sentence) expect(d.target.join(' '), d.text);
      }
    });

    test('reutiliza las sílabas, palabras y oraciones de las fases anteriores', () {
      final words = CompleteWordsContent.parse(
        jsonDecode(File(CompleteWordsContent.path).readAsStringSync()) as Map<String, dynamic>,
      );
      final sentences = SentenceCatalog.parse(
        jsonDecode(File(SentenceCatalog.path).readAsStringSync()) as Map<String, dynamic>,
      );
      final wordTexts = {for (final w in words.words.values) w.text};
      final sentenceTexts = {for (final s in sentences.sentences) s.text};
      for (final d in catalog.dictations) {
        if (d.type == DictationType.word) expect(wordTexts, contains(d.text));
        if (d.type == DictationType.sentence) {
          expect(sentenceTexts, contains(d.text));
          expect(sentences.sentences.firstWhere((s) => s.text == d.text).orderable, isTrue, reason: d.text);
        }
      }
      for (final ex in ['ma', 'me', 'mi', 'mo', 'mu', 'pa', 'su', 'la', 'tu']) {
        expect(
          catalog.dictations.where((d) => d.type == DictationType.syllable && d.text == ex),
          hasLength(1),
        );
      }
      for (final ex in ['pato', 'mesa', 'gato', 'pelota', 'casa', 'luna', 'mariposa', 'manzana']) {
        expect(
          catalog.dictations.where((d) => d.type == DictationType.word && d.text == ex),
          hasLength(1),
          reason: ex,
        );
      }
      expect(catalog.dictations.where((d) => d.text == 'Mi mamá me ama.'), hasLength(1));
    });

    test('las imágenes existen y en las tarjetas no hay dos que suenen igual', () {
      String sound(String s) => s
          .toLowerCase()
          .replaceAll(RegExp(r'qu(?=[ei])'), 'k')
          .replaceAll(RegExp(r'c(?=[ei])'), 's')
          .replaceAll('c', 'k')
          .replaceAll('z', 's')
          .replaceAll('v', 'b');
      for (final d in raw['dictations'] as List) {
        final m = d as Map;
        if (m['picture'] != null) {
          expect(SpeechPicture.fromJson(m['picture']), isNotNull, reason: '${m['id']}');
        }
        if (m['type'] != 'oracion') {
          final cards = (m['cards'] as List).cast<String>();
          expect(cards.map(sound).toSet().length, cards.length, reason: '${m['id']}: $cards');
        }
      }
    });
  });

  group('6 · 7 · corrección educativa', () {
    final mesa = byText(DictationType.word, 'mesa');
    final arbol = byText(DictationType.word, 'árbol');
    final pelota = byText(DictationType.word, 'pelota');
    final ma = byText(DictationType.syllable, 'ma');
    final sa = byText(DictationType.syllable, 'sa');
    final mama = byText(DictationType.sentence, 'Mi mamá me ama.');

    test('correcto: sin contar mayúsculas ni espacios de más', () {
      expect(check(mesa, 'mesa').correct, isTrue);
      expect(check(mesa, '  MESA ').correct, isTrue);
      expect(check(ma, 'Ma').correct, isTrue);
    });

    test('tildes: falta, sobra o está en otra letra (no se da por buena)', () {
      final r = check(arbol, 'arbol');
      expect(r.correct, isFalse);
      expect(r.issue, DictationIssue.accent);
      expect(r.message, contains('falta la tilde'));
      expect(check(mesa, 'mésa').message, contains('no lleva tilde'));
      expect(check(arbol, 'arból').message, contains('otra letra'));
      final s = check(mama, 'Mi mama me ama.');
      expect(s.issue, DictationIssue.accent);
      expect(s.marked, {1});
    });

    test('letras, sílabas y espacios se distinguen', () {
      expect(check(mesa, 'mea').issue, DictationIssue.letter);
      expect(check(mesa, 'mea').message, contains('falta una letra'));
      expect(check(mesa, 'messa').message, contains('sobra una letra'));
      expect(check(mesa, 'masa').message, contains('una letra que cambiar'));
      final syl = check(pelota, 'peloma');
      expect(syl.issue, isIn([DictationIssue.letter, DictationIssue.syllable]));
      final two = check(pelota, 'pamota');
      expect(two.issue, DictationIssue.syllable);
      expect(two.marked, {0, 1});
      expect(check(pelota, 'pe').message, contains('3 sílabas'));
      expect(check(mesa, 'me sa').issue, DictationIssue.spaces);
      expect(check(mama, 'Mimamá me ama').issue, DictationIssue.spaces);
      expect(check(ma, 'pe').issue, DictationIssue.syllable);
    });

    test('oraciones: palabras mal, que faltan o en otro orden; mayúscula y punto son consejos', () {
      expect(check(mama, 'Mi mamá me ama.').correct, isTrue);
      final lower = check(mama, 'mi mamá me ama');
      expect(lower.correct, isTrue);
      expect(lower.tip, contains('mayúscula'));
      expect(check(mama, 'Mi mamá me ama').tip, contains('punto'));
      expect(check(mama, 'Mi papá me ama.').issue, DictationIssue.word);
      expect(check(mama, 'Mi papá me ama.').marked, {1});
      expect(check(mama, 'Mi mamá ama.').message, contains('Falta'));
      expect(check(mama, 'Me mamá mi ama.').issue, DictationIssue.order);
    });

    test('sílabas que suenan igual (SA / ZA): alternativa aceptada de forma explícita', () {
      expect(sa.alternatives, ['za']);
      final r = check(sa, 'za');
      expect(r.correct, isTrue);
      expect(r.alternative, isTrue);
      expect(r.message, contains('SA'));
      // En palabras no: la imagen deja claro cuál es.
      expect(check(byText(DictationType.word, 'vaca'), 'baca').correct, isFalse);
    });

    test('tarjetas: correctas, en otro orden o con una tarjeta que no va', () {
      expect(DictationChecker.checkCards(mesa, ['me', 'sa']).correct, isTrue);
      expect(DictationChecker.checkCards(mesa, ['sa', 'me']).issue, DictationIssue.order);
      final other = mesa.cards.firstWhere((c) => !mesa.target.contains(c));
      expect(DictationChecker.checkCards(mesa, ['me', other]).marked, {1});
      expect(DictationChecker.checkCards(mama, mama.target).correct, isTrue);
    });
  });

  group('8 · 9 · pistas e intentos', () {
    test('pistas progresivas; con pistas no cuenta como sin ayuda', () {
      final pelota = byText(DictationType.word, 'pelota');
      final r = DictationRound(pelota, DictationMode.cards, random: Random(1));
      expect(r.nextHint(), 1);
      expect(r.nextHint(), 2);
      expect(r.placed, isEmpty);
      expect(r.nextHint(), 3);
      expect(r.built, ['pe'], reason: 'la pista 3 coloca la primera sílaba');
      expect(r.nextHint(), 4);
      expect(r.nextHint(), 4, reason: 'no hay más de 4');
      for (final p in ['lo', 'ta']) {
        r.place(r.bank.firstWhere((i) => pelota.cards[i] == p));
      }
      expect(r.check().correct, isTrue);
      expect(r.independent, isFalse);
    });

    test('los intentos y los errores se conservan', () {
      final r = DictationRound(byText(DictationType.word, 'mesa'), DictationMode.keyboard);
      r.typed = 'meza';
      expect(r.check().correct, isFalse);
      r.typed = 'mesa';
      expect(r.check().correct, isTrue);
      expect(r.attempts, 2);
      expect(r.issues, [DictationIssue.letter]);
      expect(r.independent, isTrue, reason: 'sin pistas, aunque con un error');
      expect(r.firstTry, isFalse);
    });

    test('sílabas: la pista 3 dice la primera letra pero no pone la tarjeta (sería la respuesta)', () {
      final r = DictationRound(byText(DictationType.syllable, 'ma'), DictationMode.cards, random: Random(1));
      r.nextHint();
      r.nextHint();
      r.nextHint();
      expect(r.placed, isEmpty);
      expect(r.dictation.firstHint, 'm');
      expect(letterNames['m'], 'eme');
    });

    test('sílabas: tocar otra tarjeta la cambia', () {
      final ma = byText(DictationType.syllable, 'ma');
      final r = DictationRound(ma, DictationMode.cards, random: Random(1));
      r.place(r.bank.first);
      r.place(r.bank.first);
      expect(r.placed, hasLength(1));
    });
  });

  group('10 · progreso', () {
    test('se guarda por dictado con fecha, intentos, pistas, modo y errores', () async {
      final backend = MemoryBackend();
      final p = newProgress(backend);
      await p.load();
      p.recordDictation(
        'd1',
        type: 'palabra',
        level: 2,
        mode: 'teclado',
        correct: false,
        hints: 0,
        error: 'accent',
      );
      p.recordDictation('d1', type: 'palabra', level: 2, mode: 'teclado', correct: true, hints: 2);
      p.recordDictation('d2', type: 'silaba', level: 1, mode: 'tarjetas', correct: true, hints: 0);
      p.recordCompleted('completa_pato', 'elige', firstTry: true, usedHints: false);
      await p.flush();
      final again = newProgress(backend);
      await again.load();
      final d1 = again.progress.dictations['d1']!;
      expect(d1.attempts, 2);
      expect(d1.correct, isTrue);
      expect(d1.independent, isFalse, reason: 'acertado con pistas');
      expect(d1.hints, 2);
      expect(d1.mode, 'teclado');
      expect(d1.date, '2026-11-17');
      expect(d1.errors, {'accent': 1});
      expect(again.progress.dictations['d2']!.independent, isTrue);
      expect(again.progress.completed['completa_pato'], {'elige'}, reason: 'no toca lo de otras fases');
    });

    test('los niveles se abren al acertar 8 dictados del anterior', () async {
      final p = newProgress();
      await p.load();
      Iterable<String> ids(int l) => catalog.ofLevel(l).map((d) => d.id);
      expect(p.dictationLevelOpen(2, ids), isFalse);
      for (final d in catalog.ofLevel(1).take(ReadingController.unlockAfter)) {
        p.recordDictation(d.id, type: 'silaba', level: 1, mode: 'tarjetas', correct: true, hints: 3);
      }
      expect(p.dictationLevelOpen(2, ids), isTrue);
      expect(p.dictationLevelOpen(3, ids), isFalse);
    });
  });

  group('pantallas', () {
    testWidgets('1 · 2 · el dictado suena al empezar; repetir, lento y parar', (tester) async {
      await openGame(tester, 1, DictationMode.cards);
      final d = firstOf(1, 1);
      expect(spoken.first, 'Escucha y toca la sílaba que oyes. ${d.text}');
      expect(find.text('Sin grabación: se oye con la voz del dispositivo.'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar el dictado'));
      expect(spoken.last, d.text);
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar el dictado despacio'));
      expect(lastNarrator!.slow.last, d.text);
      final stops = lastNarrator!.stops;
      await tapAndSettle(tester, find.bySemanticsLabel('Parar el audio'));
      expect(lastNarrator!.stops, greaterThanOrEqualTo(stops));
    });

    testWidgets('3 · nivel 1 con tarjetas: error → «Vamos a intentarlo otra vez»; acierto → se guarda', (
      tester,
    ) async {
      final progress = await openGame(tester, 1, DictationMode.cards);
      final d = firstOf(1, 1);
      final wrong = d.cards.firstWhere((c) => c != d.text);
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba $wrong'));
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.text(DictationGameScreen.tryAgain), findsOneWidget);
      // Corregir: quitar la tarjeta y poner la buena.
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba $wrong'));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba ${d.text}'));
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(find.bySemanticsLabel('Respuesta correcta: ${d.text}'), findsOneWidget);
      final rec = progress.progress.dictations[d.id]!;
      expect(rec.attempts, 2);
      expect(rec.correct, isTrue);
      expect(rec.independent, isTrue);
      expect(rec.errors, {'syllable': 1});
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la respuesta'));
      expect(spoken.last, d.text);
    });

    testWidgets('4 · 7 · teclado: tilde que falta, se corrige con las teclas de ayuda', (tester) async {
      final progress = await openGame(tester, 2, DictationMode.keyboard, seed: 3);
      final d = firstOf(2, 3);
      await tester.enterText(
        find.byType(TextField),
        DictationChecker.stripAccents(d.text) == d.text
            ? '${d.text}x'
            : DictationChecker.stripAccents(d.text),
      );
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.text(DictationGameScreen.tryAgain), findsOneWidget);
      await tester.enterText(find.byType(TextField), d.text);
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(progress.progress.dictations[d.id]!.correct, isTrue);
    });

    testWidgets('4 · teclado: las teclas «á é í ó ú ñ» escriben en el campo', (tester) async {
      await openGame(tester, 2, DictationMode.keyboard);
      await tester.enterText(find.byType(TextField), 'arb');
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel('Escribir ñ'));
      expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, 'arbñ');
    });

    testWidgets('8 · pistas en pantalla: lento, cuántas, la primera y el modelo; se registran', (
      tester,
    ) async {
      final progress = await openGame(tester, 2, DictationMode.cards, seed: 2);
      final d = firstOf(2, 2);
      await tapAndSettle(tester, find.bySemanticsLabel('Pista 1 de 4'));
      expect(lastNarrator!.slow.last, d.audio.tts);
      await tapAndSettle(tester, find.bySemanticsLabel('Pista 2 de 4'));
      expect(find.bySemanticsLabel('Pista: tiene ${d.countLabel}'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Pista 3 de 4'));
      expect(find.bySemanticsLabel('Pista: empieza por ${d.firstHint}'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Pista 4 de 4'));
      expect(find.bySemanticsLabel('Pista: así se escribe, ${d.model}'), findsOneWidget);
      for (final p in d.target.skip(1)) {
        await tapAndSettle(tester, find.bySemanticsLabel('Sílaba $p').last);
      }
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(find.textContaining('con 4 pistas'), findsOneWidget);
      final rec = progress.progress.dictations[d.id]!;
      expect(rec.correct, isTrue);
      expect(rec.independent, isFalse);
      expect(rec.hints, 4);
    });

    testWidgets('5 · oraciones: ordenar las palabras', (tester) async {
      final progress = await openGame(tester, 3, DictationMode.order, seed: 4);
      final d = firstOf(3, 4);
      for (final w in d.target) {
        await tapAndSettle(tester, find.bySemanticsLabel('Palabra ${w.replaceAll('.', '')}').last);
      }
      expect(find.bySemanticsLabel('Tu respuesta: ${d.text}'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(progress.progress.dictations[d.id]!.mode, 'ordenar');
    });

    testWidgets('oraciones con teclado: sin punto final, correcto con consejo', (tester) async {
      await openGame(tester, 3, DictationMode.keyboard, seed: 4);
      final d = firstOf(3, 4);
      await tester.enterText(find.byType(TextField), d.text.substring(0, d.text.length - 1));
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
      expect(find.textContaining('termina con un punto'), findsOneWidget);
    });

    testWidgets('una partida completa de 8 dictados termina con el resumen', (tester) async {
      await openGame(tester, 1, DictationMode.keyboard, seed: 5);
      final all = [...catalog.ofLevel(1)]..shuffle(Random(5));
      all.sort((a, b) => a.difficulty - b.difficulty);
      for (final d in all.take(DictationGameScreen.sessionLength)) {
        await tester.enterText(find.byType(TextField), d.text);
        await tester.pumpAndSettle();
        await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
        await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^(Siguiente|Terminar)\$')));
      }
      expect(find.textContaining('Terminaste'), findsWidgets);
      expect(find.bySemanticsLabel('Acertaste 8 de 8 sin pistas'), findsOneWidget);
    });

    testWidgets('10 · niveles en la pantalla principal y modos de cada nivel', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final progress = newProgress();
      await pumpApp(tester, reading: progress);
      unawaited(tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.readingDictation));
      await tester.pumpAndSettle();
      expect(find.bySemanticsLabel('Tocar tarjetas'), findsOneWidget);
      expect(find.bySemanticsLabel('Escribir con teclado'), findsOneWidget);
      for (final d in catalog.ofLevel(1).take(8)) {
        progress.recordDictation(d.id, type: 'silaba', level: 1, mode: 'tarjetas', correct: true, hints: 0);
      }
      for (final d in catalog.ofLevel(2).take(8)) {
        progress.recordDictation(d.id, type: 'palabra', level: 2, mode: 'tarjetas', correct: true, hints: 0);
      }
      await tester.pumpAndSettle();
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Nivel 3: .*acertados')));
      expect(find.bySemanticsLabel('Ordenar palabras'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Ordenar palabras'));
      expect(find.byType(DictationGameScreen), findsOneWidget);
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
          const ReadingDictationScreen(),
          for (final level in DictationCatalog.levels)
            for (final mode in modesForLevel(level))
              DictationGameScreen(
                args: DictationArgs(level: level, mode: mode),
                seed: 1,
              ),
        ];
        for (final screen in screens) {
          tester
              .state<NavigatorState>(find.byType(Navigator))
              .push(MaterialPageRoute<void>(builder: (_) => screen));
          await tester.pumpAndSettle();
          // Con todas las pistas abiertas también cabe.
          for (var i = 0; i < 4; i++) {
            final hint = find.bySemanticsLabel(RegExp(r'^Pista \d de 4$'));
            if (hint.evaluate().isEmpty) break;
            await tapAndSettle(tester, hint);
          }
          expect(tester.takeException(), isNull, reason: '$screen');
          tester.state<NavigatorState>(find.byType(Navigator)).pop();
          await tester.pumpAndSettle();
        }
      });
    }
  });
}
