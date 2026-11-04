import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/aac/aac_controller.dart';
import 'package:pequenos_artistas/learning/learning_progress.dart';
import 'package:pequenos_artistas/learning/screens/learning_hub_screen.dart';
import 'package:pequenos_artistas/learning/screens/rewards_screen.dart';
import 'package:pequenos_artistas/learning/learning_store.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/creation.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/screens/categories_screen.dart';
import 'package:pequenos_artistas/screens/home_screen.dart';
import 'package:pequenos_artistas/screens/saved_drawings_screen.dart';
import 'package:pequenos_artistas/services/progress_overview.dart';
import 'package:pequenos_artistas/speech/screens/speech_hub_screen.dart';
import 'package:pequenos_artistas/speech/speech_progress.dart';

import 'test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(finder, 250, scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

Future<void> push(WidgetTester tester, String route, [Object? args]) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
  await tester.pumpAndSettle();
}

Future<void> back(WidgetTester tester) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pop();
  await tester.pumpAndSettle();
}

List<String> get spoken => lastNarrator!.spoken;

void main() {
  group('navegación entre módulos', () {
    testWidgets(
      'desde el inicio: Colorear, Mini Juegos, Aprendo a Hablar, Mis Dibujos y Mis Logros, y volver',
      (tester) async {
        setScreenSize(tester, const Size(420, 900));
        await pumpApp(tester);
        for (final (label, check) in [
          ('Colorear', find.byType(CategoriesScreen)),
          ('Mini Juegos', find.byType(LearningHubScreen)),
          ('Aprendo a Hablar', find.byType(SpeechHubScreen)),
          ('Galería', find.byType(SavedDrawingsScreen)),
          ('Logros', find.byType(RewardsScreen)),
        ]) {
          await tapAndSettle(tester, find.bySemanticsLabel(label));
          expect(check, findsWidgets, reason: label);
          await back(tester);
          expect(find.byType(HomeScreen), findsOneWidget, reason: 'vuelve al inicio desde $label');
        }
      },
    );

    testWidgets('el tablero rápido está a un toque desde el inicio y desde «Aprendo a Hablar»', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('Necesito decir algo'));
      await tapAndSettle(tester, find.bySemanticsLabel('Ayuda'));
      expect(spoken.last, 'Ayuda');
      await back(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('Aprendo a Hablar'));
      expect(find.bySemanticsLabel('Necesito decir algo'), findsOneWidget);
    });

    testWidgets('en una tableta en horizontal los accesos van al lado de la ilustración', (tester) async {
      setScreenSize(tester, const Size(1280, 800));
      await pumpApp(tester);
      expect(find.bySemanticsLabel('Necesito decir algo'), findsOneWidget);
      expect(find.bySemanticsLabel('Aprendo a Hablar'), findsOneWidget, reason: 'sin duplicar la insignia');
    });

    testWidgets('rutas inexistentes o sin sus datos muestran una pantalla amable', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      for (final (route, args) in [
        ('/no-existe', null),
        (AppRoutes.speechStory, null),
        (AppRoutes.aacCategory, 'no es un argumento'),
        (AppRoutes.speechWordGame, const SpeechGameArgs('juego-que-no-existe')),
      ]) {
        await push(tester, route, args);
        expect(find.text('Ups, aquí no hay nada'), findsOneWidget, reason: route);
        await back(tester);
      }
    });
  });

  group('audio', () {
    testWidgets('al volver atrás, la voz de la pantalla que se cierra se calla', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await push(tester, AppRoutes.speechStories);
      await push(tester, AppRoutes.speechStory, const SpeechStoryArgs('toby_pelota'));
      final stops = lastNarrator!.stops;
      await back(tester);
      expect(lastNarrator!.stops, greaterThan(stops));
      // Cerrar un diálogo no corta la voz.
      await push(tester, AppRoutes.aacFavorites);
      final before = lastNarrator!.stops;
      showDialog<void>(context: tester.element(find.byType(Scaffold).last), builder: (_) => const Text('x'));
      await tester.pumpAndSettle();
      Navigator.of(tester.element(find.text('x'))).pop();
      await tester.pumpAndSettle();
      expect(lastNarrator!.stops, before);
    });

    testWidgets('«Reducir animaciones» (zona de adultos) llega a toda la app', (tester) async {
      setScreenSize(tester, const Size(800, 1280));
      await pumpApp(tester);
      bool reduced() => MediaQuery.of(tester.element(find.byType(Scaffold).last)).disableAnimations;
      expect(reduced(), isFalse);
      await push(tester, AppRoutes.adultZone, const AdultZoneArgs.verified());
      await tapAndSettle(tester, find.text('Reducir animaciones'));
      expect(reduced(), isTrue);
    });
  });

  group('datos guardados', () {
    test('progreso de la 1.ª entrega (sin los campos nuevos) se lee sin perder nada', () {
      final payload = {
        'format_version': 1,
        'words_heard': ['perro', 'gato'],
        'phrases_heard': ['quiero_agua'],
        'practice_days': ['2026-01-02'],
      };
      final raw = jsonEncode({...payload, 'checksum': Creation.checksumOf(payload)});
      final p = SpeechStore.decode(raw)!;
      expect(p.wordsHeard, {'perro', 'gato'});
      expect(p.phrasesHeard, {'quiero_agua'});
      expect(p.stars, 0);
      expect(p.preferences.level, 1);
      expect(p.storiesBuilt, isEmpty);
      expect(p.today, isNull);
      // Y se vuelve a guardar con todos los campos.
      expect(SpeechStore.decode(SpeechStore.encode(p))!.wordsHeard, {'perro', 'gato'});
    });

    test('ajustes de juegos antiguos (sin «reducir animaciones») y dañados', () {
      final old = LearningSettings.fromJson({'sound_on': false, 'voice_volume': 0.4});
      expect(old.soundOn, isFalse);
      expect(old.voiceVolume, 0.4);
      expect(old.reduceMotion, isFalse);
      final odd = LearningSettings.fromJson({
        'reduce_motion': 'sí',
        'voice_volume': double.nan,
        'master_volume': 7,
      });
      expect(odd.reduceMotion, isFalse);
      expect(odd.voiceVolume, 1.0);
      expect(odd.masterVolume, 1.0);
      expect(
        LearningSettings.fromJson(const LearningSettings(reduceMotion: true).toJson()).reduceMotion,
        isTrue,
      );
    });

    test('datos dañados: se usa la copia o se empieza de cero, sin romper', () async {
      final backend = MemoryBackend();
      await backend.write(SpeechStore.key, 'no es json');
      expect((await SpeechStore(backend).load()).wordsHeard, isEmpty);
      await backend.write(LearningStore.key, '{"format_version": 999}');
      expect((await LearningStore(backend).load()).progress.stars, 0);
      await backend.write(AacStore.key, '[1, 2, 3]');
      expect((await AacStore(backend).load()).favorites, isEmpty);
      // Un checksum que no cuadra no se acepta.
      final p = SpeechProgress(wordsHeard: {'perro'});
      final tampered = SpeechStore.encode(p).replaceFirst('perro', 'gato');
      expect(SpeechStore.decode(tampered), isNull);
    });

    test('vista integrada del progreso, leída de cada módulo', () {
      final o = ProgressOverview.from(
        drawingsSaved: 3,
        drawingsFinished: 1,
        learning: LearningProgress(stars: 4),
        speech: SpeechProgress(
          wordsHeard: {'a', 'b'},
          sentencesBuilt: {'x'},
          storiesBuilt: {'y'},
          storiesHeard: {'c'},
          conversationsDone: {'d'},
          syllablesDone: {'e'},
          activitiesDone: {'juego_rimas': 2},
          stars: 5,
        ),
        aac: AacPreferences(favorites: ['Hola.']),
      );
      expect(o.wordsPracticed, 2);
      expect(o.sentencesBuilt, 2);
      expect(o.phonologyActivities, 3);
      expect(o.favoritePhrases, 1);
      expect(o.lines.join(' '), isNot(contains(RegExp('retraso|trastorno|anormal'))));
    });
  });

  group('recorridos principales', () {
    testWidgets('E: decir «Necesito ayuda» desde el tablero, sin estrellas ni micrófono', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final speech = SpeechController(SpeechStore(MemoryBackend()));
      await speech.load();
      await pumpApp(tester, speech: speech);
      await push(tester, AppRoutes.aac);
      await tapAndSettle(tester, find.bySemanticsLabel('Necesidades básicas'));
      await tapAndSettle(tester, find.bySemanticsLabel('Necesito ayuda.'));
      expect(spoken.last, 'Necesito ayuda.');
      expect(speech.progress.stars, 0, reason: 'comunicarse no depende de premios ni los da');
      expect(lastRecorder, isNull);
    });

    testWidgets('F: un adulto revisa el resumen de todo lo hecho', (tester) async {
      setScreenSize(tester, const Size(800, 1280));
      await pumpApp(tester);
      await push(tester, AppRoutes.adultZone, const AdultZoneArgs.verified());
      expect(find.text('Resumen de todo lo hecho'), findsOneWidget);
      expect(find.textContaining('Dibujos guardados: 0'), findsOneWidget);
      expect(find.textContaining('Frases favoritas de «Quiero decir»: 0'), findsOneWidget);
    });
  });
}
