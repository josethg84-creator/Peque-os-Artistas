import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/reading/audio/reading_voice.dart';
import 'package:pequenos_artistas/reading/learning_report.dart';
import 'package:pequenos_artistas/reading/screens/reading_dictation_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_sentences_screen.dart';
import 'package:pequenos_artistas/reading/screens/sentence_reader_screen.dart';
import 'package:pequenos_artistas/screens/not_found_screen.dart';

import '../test_helpers.dart';

/// Un paquete de recursos que no puede leer nada (recurso dañado o ausente).
class _BrokenBundle extends CachingAssetBundle {
  @override
  Future<ByteData> load(String key) async => throw FlutterError('No existe $key');
}

Widget _withBundle(Widget child) => DefaultAssetBundle(
  bundle: _BrokenBundle(),
  child: MaterialApp(home: Scaffold(body: child)),
);

void main() {
  setUp(() => ReadingVoice.clipPlayerFactory = FakeClipPlayer.new);
  tearDown(() => ReadingVoice.clipPlayerFactory = AudioPlayersClipPlayer.new);

  group('audio al cambiar de pantalla', () {
    testWidgets('salir del lector mientras suena: la voz se calla y nada falla después', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      tester
          .state<NavigatorState>(find.byType(Navigator))
          .push(
            MaterialPageRoute<void>(
              builder: (_) => const SentenceReaderScreen(args: SentenceReaderArgs(level: 1)),
            ),
          );
      await tester.pumpAndSettle();
      lastNarrator!
        ..reportsWords = true
        ..pending = Completer();
      await tester.tap(find.bySemanticsLabel('Escuchar la oración'));
      await tester.pump();
      final stops = lastNarrator!.stops;
      await tester.tap(find.byTooltip('Volver'));
      await tester.pumpAndSettle();
      expect(lastNarrator!.stops, greaterThan(stops), reason: 'al salir se para la voz');
      // La frase «termina» después de cerrar la pantalla: no debe tocar un widget ya cerrado.
      lastNarrator!.pending!.complete();
      lastNarrator!.pending = null;
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  });

  group('recursos que no se pueden leer', () {
    testWidgets('oraciones: mensaje claro, sin bloquear la app', (tester) async {
      await tester.pumpWidget(_withBundle(SentenceCatalogBuilder(builder: (_, _) => const Text('ok'))));
      await tester.pumpAndSettle();
      expect(find.text('No pudimos abrir las oraciones.'), findsOneWidget);
    });

    testWidgets('dictados: mensaje claro', (tester) async {
      await tester.pumpWidget(_withBundle(DictationCatalogBuilder(builder: (_, _) => const Text('ok'))));
      await tester.pumpAndSettle();
      expect(find.text('No pudimos abrir los dictados.'), findsOneWidget);
    });

    testWidgets('logros y panel: mensaje claro', (tester) async {
      await tester.pumpWidget(_withBundle(ReadingCatalogsBuilder(builder: (_, _) => const Text('ok'))));
      await tester.pumpAndSettle();
      expect(find.text('No pudimos abrir el progreso.'), findsOneWidget);
    });
  });

  group('rutas', () {
    for (final route in [
      AppRoutes.readingWordsGame,
      AppRoutes.readingSentencesRead,
      AppRoutes.readingSentencesGame,
      AppRoutes.readingDictationGame,
      AppRoutes.readingTracking,
      '/leer/no-existe',
    ]) {
      testWidgets('$route sin sus datos lleva a «No encontrado» (con salida)', (tester) async {
        setScreenSize(tester, const Size(420, 900));
        await pumpApp(tester);
        unawaited(tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route));
        await tester.pumpAndSettle();
        expect(find.byType(NotFoundScreen), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
