import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/reading/reading_activities.dart';
import 'package:pequenos_artistas/reading/reading_demo.dart';
import 'package:pequenos_artistas/reading/screens/reading_dictation_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_hub_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_sentences_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_syllables_screen.dart';
import 'package:pequenos_artistas/reading/screens/reading_words_screen.dart';
import 'package:pequenos_artistas/reading/widgets/reading_widgets.dart';
import 'package:pequenos_artistas/screens/home_screen.dart';
import 'package:pequenos_artistas/speech/screens/speech_hub_screen.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

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
  group('datos de demostración', () {
    test('las sílabas de cada palabra forman la palabra y empiezan por su sílaba', () {
      for (final f in ReadingDemo.families) {
        expect(f.syllables, hasLength(5), reason: f.letter);
        for (final s in f.syllables) {
          expect(s.example.syllables.join(), s.example.text, reason: s.example.text);
          expect(plain(s.example.syllables.first), s.text, reason: '${s.example.text} empieza por ${s.text}');
          expect(plain(s.text).startsWith(f.letter.toLowerCase()), isTrue, reason: s.text);
        }
      }
      for (final w in ReadingDemo.words) {
        expect(w.word.syllables.join(), w.word.text, reason: w.word.text);
        expect(
          w.options.where((o) => o == w.answer),
          hasLength(1),
          reason: '${w.word.text}: una sola respuesta',
        );
        expect(w.options.length, inInclusiveRange(3, 4));
      }
      for (final d in ReadingDemo.dictations) {
        expect(d.pieces.join(d.joiner), d.spoken, reason: d.spoken);
        for (final p in d.pieces) {
          expect(d.cards, contains(p));
        }
      }
    });

    test('todas las imágenes de la demostración existen (ninguna sale como estrella de reserva)', () {
      final pictures = [
        for (final f in ReadingDemo.families)
          for (final s in f.syllables) s.example.pictureJson,
        for (final w in ReadingDemo.words) w.word.pictureJson,
        for (final s in ReadingDemo.sentences) s.pictureJson,
      ];
      for (final json in pictures) {
        expect(SpeechPicture.fromJson(json), isNotNull, reason: '$json');
      }
      for (final a in ReadingActivities.all) {
        expect(File(a.image).existsSync(), isTrue, reason: a.image);
        expect(a.plannedImage, startsWith(ReadingActivities.folder));
      }
    });
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
        // Sílabas (Fase 3), palabras (Fase 4) y oraciones (Fase 5) usan contenido
        // real; el dictado aún es demostración.
        expect(
          find.byType(DemoBadge),
          a == ReadingActivities.dictation ? findsOneWidget : findsNothing,
          reason: '${a.title}: distintivo de demostración',
        );
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

    testWidgets('dictado: escuchar, formar «mesa» con tarjetas, borrar y comprobar', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await push(tester, AppRoutes.readingDictation);
      await tapAndSettle(tester, find.bySemanticsLabel('Nivel 2: Palabras'));
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
      expect(spoken.last, 'mesa');
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba pa'));
      await tapAndSettle(tester, find.bySemanticsLabel('Borrar la última'));
      expect(find.bySemanticsLabel('Tu respuesta: vacía'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba me'));
      await tapAndSettle(tester, find.bySemanticsLabel('Sílaba sa'));
      expect(find.bySemanticsLabel('Tu respuesta: mesa'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Comprobar'));
      expect(find.byType(ReadingCelebration), findsOneWidget);
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
