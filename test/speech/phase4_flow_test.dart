import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';
import 'package:pequenos_artistas/speech/speech_progress.dart';
import 'package:pequenos_artistas/speech/voice_practice.dart';

import '../test_helpers.dart';
import 'content_fixture.dart';

/// Toca una tarjeta de una lista que se construye a medida que se desplaza.
Future<void> tapCard(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(finder, 250, scrollable: find.byType(Scrollable).first);
  await tapAndSettle(tester, finder);
}

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

List<String> get spoken => lastNarrator!.spoken;

Future<SpeechController> openApp(WidgetTester tester, {Size size = const Size(420, 900)}) async {
  setScreenSize(tester, size);
  final speech = SpeechController(
    SpeechStore(MemoryBackend()),
    recorder: () => lastRecorder = FakeVoiceRecorder(),
  );
  await speech.load();
  await pumpApp(tester, speech: speech);
  return speech;
}

Future<void> push(WidgetTester tester, String route, [Object? args]) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
  await tester.pumpAndSettle();
}

Future<void> back(WidgetTester tester) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pop();
  await tester.pumpAndSettle();
}

void main() {
  late SpeechContent content;
  setUpAll(() async => content = await fullContent());

  group('Etapas A y B · sugerencias y Mi aventura de hoy', () {
    testWidgets('el menú muestra la aventura y las sugerencias de Lolo, que llevan a la actividad', (
      tester,
    ) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speech);
      expect(find.bySemanticsLabel(RegExp(r'^Mi aventura de hoy\. 0 de 5')), findsOneWidget);
      expect(find.text('Lolo te propone'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a escuchar tus primeras palabras!'));
      expect(find.text('Familia'), findsWidgets);
      expect(spoken.last, 'mamá');
      expect(speech.progress.visits[AppRoutes.speechWords], 1);
    });

    testWidgets('misiones opcionales: saltar, volver a ponerla y completar una', (tester) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speech);
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Mi aventura de hoy')));
      expect(spoken.last, startsWith('¡Hola! Esta es tu aventura de hoy.'));
      for (final t in [
        'Escucha 3 palabras',
        'Construye 2 frases',
        'Practica un verbo',
        'Escucha una historia',
        'Charla con Lolo',
      ]) {
        await tester.scrollUntilVisible(
          find.bySemanticsLabel(RegExp('^$t: ')),
          200,
          scrollable: find.byType(Scrollable).first,
        );
        expect(find.bySemanticsLabel(RegExp('^$t: ')), findsOneWidget, reason: t);
      }
      await tester.scrollUntilVisible(
        find.bySemanticsLabel(RegExp('^Arcoíris')),
        -200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.bySemanticsLabel('Arcoíris: 0 de 5 misiones hechas'), findsOneWidget);

      await tapAndSettle(tester, find.bySemanticsLabel('Saltar: Practica un verbo'));
      expect(find.bySemanticsLabel('Practica un verbo: Saltada'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a ponerla: Practica un verbo'));
      expect(find.bySemanticsLabel('Practica un verbo: 0 de 1'), findsOneWidget);

      await tester.scrollUntilVisible(
        find.bySemanticsLabel(RegExp('^Arcoíris')),
        -200,
        scrollable: find.byType(Scrollable).first,
      );
      await tapCard(tester, find.bySemanticsLabel('¡Vamos! Escucha 3 palabras'));
      expect(spoken.last, 'mamá');
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      await back(tester);
      expect(find.bySemanticsLabel('Escucha 3 palabras: ¡Hecho!'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.bySemanticsLabel(RegExp('^Arcoíris')),
        -200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.bySemanticsLabel('Arcoíris: 1 de 5 misiones hechas'), findsOneWidget);

      // Saltar las demás completa la aventura (sin rachas ni castigos).
      for (final t in [
        'Construye 2 frases',
        'Practica un verbo',
        'Escucha una historia',
        'Charla con Lolo',
      ]) {
        await tapCard(tester, find.bySemanticsLabel('Saltar: $t'));
      }
      expect(spoken.last, '¡Completaste tu aventura de hoy! ¡El arcoíris brilla!');
      expect(speech.progress.activitiesDone['aventura'], 1);
    });
  });

  group('Etapa C · sílabas y sonidos', () {
    testWidgets('palmas: una palma por sílaba; si no, se enseñan las sílabas y se repite', (tester) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speech);
      await tapCard(tester, find.bySemanticsLabel('Sílabas y sonidos'));
      await tapAndSettle(tester, find.bySemanticsLabel('Nivel Difícil'));
      await tapCard(tester, find.bySemanticsLabel('Palmas y sílabas'));
      SpeechWord current() {
        final text = RegExp(r'^Escucha: (.+)\. Da una palma').firstMatch(spoken.last)!.group(1)!;
        return content.words.firstWhere((w) => w.text == text && w.pronunciation != null);
      }

      var w = current();
      expect(w.syllables.length, greaterThanOrEqualTo(4));
      for (var i = 0; i < w.syllables.length; i++) {
        await tapAndSettle(tester, find.bySemanticsLabel('Dar una palma'));
      }
      expect(find.bySemanticsLabel('Palmas: ${w.syllables.length}'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('¡Listo!'));
      expect(spoken.last, startsWith('¡Muy bien! ${w.syllables.join(', ')}.'));
      expect(find.bySemanticsLabel('Sílabas: ${w.syllables.join(' - ')}'), findsOneWidget);
      expect(speech.progress.syllablesDone, {w.id});
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));

      w = current();
      await tapAndSettle(tester, find.bySemanticsLabel('Dar una palma'));
      await tapAndSettle(tester, find.bySemanticsLabel('¡Listo!'));
      expect(spoken.last, '¡Casi! Escucha otra vez: ${w.syllables.join(', ')}. Ahora da tú las palmas.');
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar las sílabas despacio'));
      expect(lastNarrator!.slow.last, '${w.syllables.join(', ')}. ${w.text}.');
      await tapAndSettle(tester, find.bySemanticsLabel('Dar las palmas otra vez'));
      expect(find.bySemanticsLabel('Dar una palma'), findsOneWidget);
    });

    testWidgets('rimas y ¿con qué empieza?: Lolo dice las palabras y se responde tocando', (tester) async {
      final speech = await openApp(tester);
      for (final game in ['rimas', 'empieza', 'encuentro']) {
        await push(tester, AppRoutes.speechSoundGame, SpeechGameArgs(game, level: 1));
        for (var i = 0; i < 6; i++) {
          final asked = spoken.last;
          String? answer;
          if (game == 'encuentro') {
            answer = asked.replaceFirst('Escucha y encuentra: ', '');
          } else {
            final target = RegExp(r'(?:rima con|empieza como) (.+?)\?').firstMatch(asked)!.group(1)!;
            final sets = game == 'rimas' ? content.phonology.rhymes : content.phonology.starts;
            final byId = {for (final w in content.words) w.id: w};
            answer = byId[sets.firstWhere((s) => byId[s.target]!.text == target).answer]!.text;
            expect(asked, contains('Escucha: '));
          }
          await tapAndSettle(tester, find.bySemanticsLabel(answer).first);
          await tapAndSettle(tester, find.bySemanticsLabel(i == 5 ? 'Terminar' : 'Siguiente'));
        }
        expect(speech.progress.activitiesDone['juego_$game'], 1, reason: game);
        await back(tester);
      }
      expect(speech.today.count(Daily.sounds), 3);
    });
  });

  group('Etapa D · juegos de palabras', () {
    testWidgets('¿De qué grupo es? y completar la frase con el vocabulario nuevo', (tester) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speechWordGame, const SpeechGameArgs('grupo', level: 3));
      final q = RegExp(r'^¿En qué grupo va (.+)\?$').firstMatch(spoken.last)!.group(1)!;
      final cat = content.categories.firstWhere((c) => c.words.any((w) => w.withArticle == q));
      await tapAndSettle(tester, find.bySemanticsLabel(cat.name));
      expect(spoken.last, endsWith('va en ${cat.name.toLowerCase()}.'));
      await back(tester);

      await push(tester, AppRoutes.speechWordGame, const SpeechGameArgs('frase', level: 2));
      final prompt = spoken.last.replaceFirst('Completa la frase: ', '');
      final word = content.words.firstWhere((w) => w.example != null && blank(w) == prompt);
      await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
      expect(lastNarrator!.slow.last, spoken.last);
      expect(speech.progress.repeats[AppRoutes.speechWordGame], 1);
      await tapAndSettle(tester, find.bySemanticsLabel(word.text));
      expect(spoken.last, word.example);
    });

    testWidgets('las palabras muestran sus sílabas y su frase de ejemplo', (tester) async {
      await openApp(tester);
      await push(tester, AppRoutes.speechWords, const SpeechWordsArgs('transporte'));
      expect(spoken.last, 'autobús');
      expect(find.text('au · to · bús'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('En una frase'));
      expect(spoken.last, 'Vamos a la escuela en autobús.');
    });
  });

  group('Etapa E · conversación adaptativa y Mi historia', () {
    testWidgets('Lolo pregunta según lo que eligió el niño', (tester) async {
      await openApp(tester);
      await push(tester, AppRoutes.speechConversation, const SpeechConversationArgs('elige_animal'));
      expect(spoken.last, '¿Qué animal te gusta?');
      await tapAndSettle(tester, find.bySemanticsLabel('El perro.'));
      expect(spoken.last, '¿Qué hace el perro?');
      await tapAndSettle(tester, find.bySemanticsLabel('Corre.'));
      expect(spoken.last, '¿Quieres escuchar la oración?');
      await tapAndSettle(tester, find.bySemanticsLabel('Sí, quiero escucharla.'));
      expect(spoken, contains('El perro corre por el parque.'));
    });

    testWidgets('inventar una historia, escucharla, despacio y repetir (sin micrófono)', (tester) async {
      final speech = await openApp(tester);
      speech.setMicAllowed(false);
      await push(tester, AppRoutes.speech);
      await tapCard(tester, find.bySemanticsLabel('Mi historia'));
      expect(spoken.last, '¡Vamos a inventar una historia! ¿Quién está en tu historia?');
      await tapAndSettle(tester, find.bySemanticsLabel('un conejo'));
      expect(spoken.last, 'un conejo. ¿Adónde fue el conejo?');
      await tapAndSettle(tester, find.bySemanticsLabel('al bosque'));
      await tapAndSettle(tester, find.bySemanticsLabel('a buscar'));
      expect(
        find.bySemanticsLabel('Tu historia hasta ahora: Un conejo fue al bosque a buscar…'),
        findsOneWidget,
      );
      await tapAndSettle(tester, find.bySemanticsLabel('una zanahoria'));
      await tapAndSettle(tester, find.bySemanticsLabel('¡Y el conejo se puso muy contento!'));
      const story = 'Un conejo fue al bosque a buscar una zanahoria. ¡Y el conejo se puso muy contento!';
      expect(find.bySemanticsLabel('Tu historia: $story'), findsOneWidget);
      expect(spoken.last, story);
      expect(speech.progress.storiesBuilt, {story});
      expect(speech.progress.stars, 1);
      await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
      expect(lastNarrator!.slow.last, story);
      await tapAndSettle(tester, find.bySemanticsLabel('Repite conmigo'));
      expect(spoken.last, 'Repite conmigo: Un conejo fue al bosque a buscar una zanahoria.');
      // Sin micrófono: no hay botón de grabar, pero todo lo demás funciona.
      expect(find.bySemanticsLabel('Grabar mi historia'), findsNothing);
      await tapAndSettle(tester, find.bySemanticsLabel('Otra historia'));
      expect(spoken.last, '¿Quién está en tu historia?');
    });
  });

  group('Etapa F · panel, ajustes y resumen para adultos', () {
    testWidgets('«Mis aventuras con Lolo» muestra estrellas, recompensas y favoritas', (tester) async {
      final speech = await openApp(tester);
      for (var i = 0; i < 10; i++) {
        speech.markWordHeard(content.words[i].id);
      }
      speech
        ..markVisit(AppRoutes.speechStories)
        ..markVisit(AppRoutes.speechStories)
        ..markVisit(AppRoutes.speechWordGroups);
      await push(tester, AppRoutes.speechProgress);
      expect(find.text('Mis aventuras con Lolo'), findsWidgets);
      expect(find.bySemanticsLabel('Recompensa: Primeras palabras'), findsOneWidget);
      expect(find.bySemanticsLabel('Coleccionista de palabras: 10 de 50'), findsOneWidget);
      expect(find.bySemanticsLabel('Favorita: Lolo me cuenta un cuento'), findsOneWidget);
    });

    testWidgets('ajustes del adulto y resumen sin etiquetas diagnósticas', (tester) async {
      final speech = await openApp(tester, size: const Size(800, 1280));
      await push(tester, AppRoutes.adultZone, const AdultZoneArgs.verified());
      await tester.scrollUntilVisible(find.text('5-6 años'), 300);
      await tapAndSettle(tester, find.text('5-6 años'));
      expect(speech.progress.preferences.ageRange, '5-6');
      expect(speech.progress.preferences.level, 2, reason: 'la edad propone un nivel');
      await tapAndSettle(tester, find.text('Fácil'));
      expect(speech.progress.preferences.level, 1, reason: 'se puede cambiar a mano');
      await tapAndSettle(tester, find.widgetWithText(FilterChip, 'Animales'));
      expect(speech.progress.preferences.favoriteCategories, {'animales'});
      await tapAndSettle(tester, find.text('5 min'));
      expect(speech.progress.preferences.minutes, 5);
      await tester.scrollUntilVisible(find.text('Narración más lenta'), 300);
      await tapAndSettle(tester, find.text('Narración más lenta'));
      expect(speech.progress.preferences.slowVoice, isTrue);
      expect(find.textContaining('Lo que Lolo propone hoy y por qué'), findsOneWidget);
      expect(find.textContaining('• Palabras: Animales:'), findsOneWidget);

      // Ninguna etiqueta diagnóstica en la zona de adultos.
      final texts = [
        for (final t in tester.widgetList<Text>(find.byType(Text)))
          (t.data ?? t.textSpan?.toPlainText() ?? '').toLowerCase(),
      ].join(' ');
      for (final bad in ['retraso', 'trastorno', 'anormal', ' normal']) {
        expect(texts, isNot(contains(bad)), reason: bad);
      }

      // La voz lenta se aplica en todo el módulo.
      await push(tester, AppRoutes.speechWords, const SpeechWordsArgs('animales'));
      expect(lastNarrator!.slow.last, 'perro');
    });
  });

  testWidgets('accesibilidad: los botones nuevos tienen nombre y tamaño táctil suficiente', (tester) async {
    final handle = tester.ensureSemantics();
    await openApp(tester);
    for (final (route, args) in [
      (AppRoutes.speechMission, null),
      (AppRoutes.speechSounds, null),
      (AppRoutes.speechClaps, const SpeechGameArgs('palmas', level: 1)),
      (AppRoutes.speechMyStory, null),
      (AppRoutes.speechWordGames, null),
    ]) {
      await push(tester, route, args);
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      await back(tester);
    }
    handle.dispose();
  });
}

String blank(SpeechWord w) {
  final e = w.example!;
  final i = e.toLowerCase().indexOf(w.text.toLowerCase());
  return '${e.substring(0, i)}...${e.substring(i + w.text.length)}';
}

// Evita el aviso de import no usado en algunas versiones.
// ignore: unused_element
const _semantics = SemanticsFlag.isButton;
