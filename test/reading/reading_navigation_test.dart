import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/reading/reading_activities.dart';
import 'package:pequenos_artistas/reading/screens/reading_dictation_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_hub_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_sentences_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllables_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_words_screen.dart';
import 'package:pequenos_artistas/screens/home_screen.dart';
import 'package:pequenos_artistas/speech/screens/speech_hub_screen.dart';

import '../test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(finder, 250, scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

Future<void> push(WidgetTester tester, String route) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route);
  await tester.pumpAndSettle();
}

List<String> get spoken => lastNarrator!.spoken;

String plain(String s) => s
    .toLowerCase()
    .replaceAll('á', 'a')
    .replaceAll('é', 'e')
    .replaceAll('í', 'i')
    .replaceAll('ó', 'o')
    .replaceAll('ú', 'u');

const screens = {
  AppRoutes.readingSyllables: ReadingSyllablesScreen,
  AppRoutes.readingWords: ReadingWordsScreen,
  AppRoutes.readingSentences: ReadingSentencesScreen,
  AppRoutes.readingDictation: ReadingDictationScreen,
};

void main() {
  test('las imágenes de las 4 actividades existen', () {
    for (final a in ReadingActivities.all) {
      expect(File(a.image).existsSync(), isTrue, reason: a.image);
      expect(a.plannedImage, startsWith(ReadingActivities.folder));
    }
  });

  group('navegación', () {
    testWidgets('inicio → Aprendo a Hablar → Aprendo a leer → cada actividad → volver', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('Aprendo a Hablar'));
      expect(find.byType(SpeechHubScreen), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Aprendo a leer')));
      expect(find.byType(ReadingHubScreen), findsOneWidget);
      expect(find.text(ReadingHubScreen.greeting), findsOneWidget);
      for (final a in ReadingActivities.all) {
        await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^${RegExp.escape(a.title)}')));
        expect(find.byType(screens[a.route]!), findsOneWidget, reason: a.title);
        // Todas las actividades usan ya contenido real (Fases 3 a 6).
        await tapAndSettle(tester, find.byTooltip('Volver'));
        expect(find.byType(ReadingHubScreen), findsOneWidget, reason: 'vuelve desde ${a.title}');
      }
      await tapAndSettle(tester, find.byTooltip('Volver'));
      expect(find.byType(SpeechHubScreen), findsOneWidget);
    });

    testWidgets('«Ir al inicio» vuelve al menú principal desde una actividad', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await push(tester, AppRoutes.speech);
      await push(tester, AppRoutes.reading);
      await push(tester, AppRoutes.readingWords);
      await tapAndSettle(tester, find.bySemanticsLabel('Ir al inicio'));
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byType(ReadingWordsScreen), findsNothing);
    });
  });

  group('pantallas', () {
    testWidgets('sílabas (contenido real): familia, sílaba, siguiente y despacio', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await push(tester, AppRoutes.readingSyllables);
      await tapAndSettle(tester, find.bySemanticsLabel('Familia de la M'));
      expect(
        spoken.last,
        'eme. ma. me. mi. mo. mu',
        reason: 'nombre de la letra y sus sílabas, en minúsculas',
      );
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba me'));
      expect(spoken.last, 'me');
      expect(find.bySemanticsLabel(RegExp('^Palabra por sílabas: me - sa')), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      expect(spoken.last, 'mi');
      await tapAndSettle(tester, find.bySemanticsLabel('Despacio la sílaba'));
      expect(lastNarrator!.slow.last, 'mi');
    });

    testWidgets('oraciones (contenido real): abrir el lector, escuchar y tocar una palabra', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await push(tester, AppRoutes.readingSentences);
      await tapAndSettle(tester, find.bySemanticsLabel('Leer oraciones'));
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la oración'));
      expect(spoken.last, 'Mi mamá me ama.');
      await tapAndSettle(tester, find.bySemanticsLabel('Palabra ama'));
      expect(spoken.last, 'ama');
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente oración'));
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar la oración'));
      expect(spoken.last, 'Papá toma sopa.');
    });

    testWidgets('dictado (contenido real): elegir nivel 1 con tarjetas y oír el dictado', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await push(tester, AppRoutes.readingDictation);
      expect(find.bySemanticsLabel(RegExp(r'^Nivel 2: .*Se abre')), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Tocar tarjetas'));
      expect(spoken.last, startsWith('Escucha y toca la sílaba que oyes'));
    });
  });

  group('diseño adaptable', () {
    testWidgets('las sílabas van una al lado de otra (no ocupan todo el ancho)', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await push(tester, AppRoutes.readingSyllables);
      final a = tester.getRect(find.bySemanticsLabel('Sílaba a'));
      final e = tester.getRect(find.bySemanticsLabel('Sílaba e'));
      expect(a.width, lessThan(140));
      expect(e.top, a.top, reason: 'A y E en la misma fila');
    });

    for (final (size, scale) in const [
      (Size(360, 720), 1.0),
      (Size(360, 720), 1.3),
      (Size(800, 1280), 1.0),
      (Size(1280, 800), 1.0),
      (Size(1280, 800), 1.6),
    ]) {
      testWidgets('${size.width.toInt()}×${size.height.toInt()} texto ×$scale: sin desbordamientos', (
        tester,
      ) async {
        setScreenSize(tester, size, textScale: scale);
        await pumpApp(tester);
        for (final route in [AppRoutes.reading, ...screens.keys]) {
          await push(tester, route);
          expect(tester.takeException(), isNull, reason: route);
          tester.state<NavigatorState>(find.byType(Navigator)).pop();
          await tester.pumpAndSettle();
        }
      });
    }
  });
}
