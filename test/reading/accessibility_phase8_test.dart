import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/complete_words.dart';
import 'package:pequenos_artistas/reading/dictation.dart';
import 'package:pequenos_artistas/reading/screens/complete_words_game_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_dictation_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_sentences_screen.dart';

import '../test_helpers.dart';

/// Fase 8: pautas de accesibilidad automáticas de Flutter en TODAS las
/// pantallas de «Aprendo a leer»: áreas táctiles de 48 × 48 como mínimo
/// (Android), botones con etiqueta y contraste de texto suficiente.
void main() {
  setUp(() => ReadingVoice.clipPlayerFactory = FakeClipPlayer.new);
  tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

  final routes = <String, (String, Object?)>{
    'Aprendo a leer': (AppRoutes.reading, null),
    'Sílabas': (AppRoutes.readingSyllables, null),
    'Escucha y encuentra': (AppRoutes.readingListenFind, null),
    'Une sílaba y palabra': (AppRoutes.readingMatchWord, null),
    'Completo palabras': (AppRoutes.readingWords, null),
    'Completa · elige': (
      AppRoutes.readingWordsGame,
      const CompleteGameArgs(level: 1, mode: CompleteMode.choose),
    ),
    'Completa · arrastra': (
      AppRoutes.readingWordsGame,
      const CompleteGameArgs(level: 1, mode: CompleteMode.drag),
    ),
    'Completa · ordena': (
      AppRoutes.readingWordsGame,
      const CompleteGameArgs(level: 1, mode: CompleteMode.order),
    ),
    'Oraciones': (AppRoutes.readingSentences, null),
    'Lector': (AppRoutes.readingSentencesRead, const SentenceReaderArgs(level: 1)),
    '¿Qué entendiste?': (
      AppRoutes.readingSentencesGame,
      const SentenceGameArgs(activity: SentenceActivity.question, level: 1),
    ),
    'Ordena la oración': (
      AppRoutes.readingSentencesGame,
      const SentenceGameArgs(activity: SentenceActivity.order, level: 1),
    ),
    'Escucha y elige': (
      AppRoutes.readingSentencesGame,
      const SentenceGameArgs(activity: SentenceActivity.listen, level: 1),
    ),
    'Dictado': (AppRoutes.readingDictation, null),
    'Dictado · tarjetas': (
      AppRoutes.readingDictationGame,
      const DictationArgs(level: 1, mode: DictationMode.cards),
    ),
    'Dictado · teclado': (
      AppRoutes.readingDictationGame,
      const DictationArgs(level: 1, mode: DictationMode.keyboard),
    ),
    'Mis logros': (AppRoutes.readingAchievements, null),
    'Mis medallas': (AppRoutes.readingMedals, null),
    'Mi camino': (AppRoutes.readingPath, null),
    'Panel adultos': (AppRoutes.readingTracking, const AdultZoneArgs.verified()),
  };

  // Tamaños que no cubrían las pruebas anteriores: móvil pequeño, móvil en
  // horizontal y escritorio (con texto grande en el pequeño).
  for (final (size, scale) in const [(Size(320, 568), 1.3), (Size(740, 360), 1.0), (Size(1366, 768), 1.0)]) {
    testWidgets('${size.width.toInt()}×${size.height.toInt()} ×$scale: ninguna pantalla se desborda', (
      tester,
    ) async {
      setScreenSize(tester, size, textScale: scale);
      await pumpApp(tester);
      for (final MapEntry(key: name, value: (route, args)) in routes.entries) {
        tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull, reason: name);
        tester.state<NavigatorState>(find.byType(Navigator)).pop();
        await tester.pumpAndSettle();
      }
    });
  }

  for (final MapEntry(key: name, value: (route, args)) in routes.entries) {
    testWidgets('$name: áreas táctiles, etiquetas y contraste', (tester) async {
      final semantics = tester.ensureSemantics();
      setScreenSize(tester, const Size(412, 915));
      await pumpApp(tester);
      tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
      await tester.pumpAndSettle();
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      await expectLater(tester, meetsGuideline(textContrastGuideline));
      semantics.dispose();
    });
  }
}
