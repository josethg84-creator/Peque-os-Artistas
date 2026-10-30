import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/learning/audio/learning_audio.dart';
import 'package:pequenos_artistas/learning/learning_content.dart';
import 'package:pequenos_artistas/learning/learning_controller.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';
import 'package:pequenos_artistas/learning/learning_store.dart';
import 'package:pequenos_artistas/learning/quiz_specs.dart';
import 'package:pequenos_artistas/learning/screens/learning_hub_screen.dart';
import 'package:pequenos_artistas/learning/screens/memory_game_screen.dart';
import 'package:pequenos_artistas/learning/widgets/answer_option.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/screens/home_screen.dart';

import '../test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// Con siete juegos el menú se desplaza: se vuelve arriba hasta ver los niveles.
Future<void> tapLevel(WidgetTester tester, String level) async {
  final button = find.bySemanticsLabel('Nivel $level');
  if (button.evaluate().isEmpty) {
    await tester.dragUntilVisible(button, find.byType(CustomScrollView), const Offset(0, 300));
  }
  await tapAndSettle(tester, button);
}

Future<void> openHub(WidgetTester tester) => tapAndSettle(tester, find.bySemanticsLabel('Aprender jugando'));

Future<void> openGame(WidgetTester tester, String title) =>
    tapAndSettle(tester, find.bySemanticsLabel(RegExp('^${RegExp.escape(title)}')));

/// Texto de la instrucción actual (en minúsculas).
String instruction(WidgetTester tester) {
  final text = tester
      .widgetList<Text>(find.byType(Text))
      .map((t) => t.data ?? '')
      .firstWhere((t) => t.startsWith('Encuentra el color') || t.startsWith('¿Dónde está'));
  return text.toLowerCase();
}

List<AnswerOption> options(WidgetTester tester) =>
    tester.widgetList<AnswerOption>(find.byType(AnswerOption)).toList();

/// Opción correcta: la única cuyo nombre aparece en la instrucción.
AnswerOption correctOption(WidgetTester tester) {
  final text = instruction(tester);
  final matches = options(tester)
      .where((o) => RegExp('\\b${o.label.toLowerCase()}\\b').hasMatch(text))
      .toList();
  expect(matches, hasLength(1), reason: text);
  return matches.single;
}

Future<void> tapOption(WidgetTester tester, AnswerOption option) =>
    tapAndSettle(tester, find.byWidget(option));

/// Juega una partida completa; en la primera pregunta se equivoca a propósito.
Future<int> playQuiz(WidgetTester tester, {bool makeMistake = true}) async {
  var questions = 0;
  while (true) {
    questions++;
    final good = correctOption(tester);
    if (makeMistake && questions == 1) {
      final wrong = options(tester).firstWhere((o) => o.label != good.label);
      await tapOption(tester, wrong);
      expect(find.text('¡Inténtalo otra vez!'), findsOneWidget);
      expect(options(tester).firstWhere((o) => o.label == wrong.label).state, OptionState.wrong);
      expect(find.text('Siguiente'), findsNothing); // no avanza
    }
    await tapOption(tester, correctOption(tester));
    expect(options(tester).firstWhere((o) => o.label == good.label).state, OptionState.correct);
    final last = find.text('¡Terminar!');
    if (last.evaluate().isNotEmpty) {
      await tapAndSettle(tester, last);
      return questions;
    }
    await tapAndSettle(tester, find.text('Siguiente'));
  }
}

String cardLabel(WidgetTester tester, int id) => tester
    .widget<Semantics>(
      find.descendant(of: find.byKey(ValueKey('carta-$id')), matching: find.byType(Semantics)).first,
    )
    .properties
    .label!;

Future<void> flipCard(WidgetTester tester, int id) async {
  await tester.tap(find.byKey(ValueKey('carta-$id')));
  await tester.pump(const Duration(milliseconds: 300));
}

/// Resuelve el juego de parejas descubriendo cartas como lo haría un niño.
Future<({int mismatches})> playMemory(WidgetTester tester, int cards) async {
  final known = <int, String>{};
  final done = <int>{};
  var mismatches = 0;
  String face(int id) => cardLabel(tester, id).split(',').first;
  while (done.length < cards) {
    final a = [for (var i = 0; i < cards; i++) i].firstWhere((i) => !done.contains(i));
    await flipCard(tester, a);
    known[a] = face(a);
    var b = known.entries
        .where((e) => e.key != a && !done.contains(e.key) && e.value == known[a])
        .map((e) => e.key)
        .firstOrNull;
    b ??= [for (var i = 0; i < cards; i++) i]
        .firstWhere((i) => i != a && !done.contains(i) && !known.containsKey(i));
    final last = done.length + 2 == cards;
    await flipCard(tester, b);
    if (last) {
      // La última pareja termina la partida y se muestra la felicitación.
      await tester.pumpAndSettle();
      done.addAll([a, b]);
      break;
    }
    known[b] = face(b);
    if (known[a] == known[b]) {
      done.addAll([a, b]);
      expect(cardLabel(tester, a), endsWith('pareja encontrada'));
    } else {
      mismatches++;
      expect(find.text('¡Casi! Inténtalo otra vez'), findsOneWidget);
      await tester.pump(MemoryGameScreen.mismatchPause);
      await tester.pumpAndSettle();
      expect(cardLabel(tester, a), contains('boca abajo'));
    }
  }
  await tester.pumpAndSettle();
  return (mismatches: mismatches);
}

void main() {
  testWidgets('Aprende los colores: de principio a fin, con error, premios y sonidos', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    await pumpApp(tester);
    await openHub(tester);
    await openGame(tester, 'Aprende los colores');
    expect(instruction(tester), startsWith('encuentra el color'));
    expect(options(tester), hasLength(3)); // nivel inicial
    // Los nombres se ven escritos: no se depende solo del color.
    for (final o in options(tester)) {
      expect(o.caption, o.label);
    }
    final questions = await playQuiz(tester);
    expect(questions, 4);
    expect(find.text('¡Excelente trabajo!'), findsOneWidget);
    expect(find.bySemanticsLabel('Pegatina Explorador de colores, conseguida'), findsOneWidget);
    expect(find.bySemanticsLabel('Pegatina Primera actividad, conseguida'), findsOneWidget);
    expect(lastSounds!.played, containsAll([SoundCue.tryAgain, SoundCue.correct, SoundCue.celebrate]));
    expect(lastNarrator!.spoken.first, startsWith('Encuentra el color'));
    expect(lastNarrator!.spoken, contains('¡Inténtalo otra vez!'));

    // Jugar otra vez: los premios no se repiten.
    await tapAndSettle(tester, find.bySemanticsLabel('Jugar otra vez'));
    await playQuiz(tester, makeMistake: false);
    expect(find.text('¡Pegatina nueva!'), findsNothing);
    await tapAndSettle(tester, find.text('Otros juegos'));
    expect(find.byType(LearningHubScreen), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp(r'Aprende los colores\. Jugado 2 veces')), findsOneWidget);
  });

  testWidgets('Descubre las formas: modelo, explicación y avance', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    await pumpApp(tester);
    await openHub(tester);
    await openGame(tester, 'Descubre las formas');
    expect(instruction(tester), startsWith('¿dónde está'));
    final good = correctOption(tester);
    await tapOption(tester, good);
    final shape = const ShapesSpec().pool(LearningLevel.intermediate).firstWhere((s) => s.name == good.label);
    expect(find.text(shape.explanation), findsOneWidget);
    await tapAndSettle(tester, find.text('Siguiente'));
    await playQuiz(tester);
    expect(find.text('¡Excelente trabajo!'), findsOneWidget);
    expect(find.bySemanticsLabel('Pegatina Experto en formas, conseguida'), findsOneWidget);
  });

  testWidgets('Encuentra a los animales: dibujos del catálogo y frase sencilla', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    await pumpApp(tester);
    await openHub(tester);
    await openGame(tester, 'Encuentra a los animales');
    expect(find.byType(Image), findsNWidgets(3)); // miniaturas reales del catálogo
    final good = correctOption(tester);
    await tapOption(tester, good);
    expect(find.text(learnAnimals.firstWhere((a) => a.name == good.label).fact), findsOneWidget);
    await tapAndSettle(tester, find.text('Siguiente'));
    await playQuiz(tester);
    expect(find.bySemanticsLabel('Pegatina Amigo de los animales, conseguida'), findsOneWidget);
  });

  testWidgets('nivel avanzado: animales en silueta, 4 opciones y 6 preguntas', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    await pumpApp(tester);
    await openHub(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Nivel Avanzado'));
    await openGame(tester, 'Encuentra a los animales');
    expect(options(tester), hasLength(4));
    expect(find.byType(AnimalSilhouette), findsNWidgets(4));
    expect(await playQuiz(tester, makeMistake: false), 6);
  });

  testWidgets('Une las parejas: 2, 4 y 6 parejas según el nivel, sin tiempo ni castigo', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    await pumpApp(tester);
    await openHub(tester);
    for (final (level, pairs) in [('Inicial', 2), ('Intermedio', 4), ('Avanzado', 6)]) {
      await tapLevel(tester, level);
      await openGame(tester, 'Une las parejas');
      expect(find.byKey(ValueKey('carta-${pairs * 2 - 1}')), findsOneWidget);
      expect(find.byKey(ValueKey('carta-${pairs * 2}')), findsNothing);
      await playMemory(tester, pairs * 2);
      expect(find.text('¡Excelente trabajo!'), findsOneWidget);
      await tapAndSettle(tester, find.text('Otros juegos'));
    }
    expect(find.bySemanticsLabel(RegExp(r'Une las parejas\. Jugado 3 veces')), findsOneWidget);
  });

  testWidgets('reiniciar un juego a mitad empieza de nuevo y guarda lo acertado', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    final backend = MemoryBackend();
    await pumpApp(tester, learningBackend: backend);
    await openHub(tester);
    await openGame(tester, 'Aprende los colores');
    await tapOption(tester, correctOption(tester));
    await tapAndSettle(tester, find.text('Siguiente'));
    await tapAndSettle(tester, find.bySemanticsLabel('Empezar de nuevo'));
    expect(find.bySemanticsLabel('Pregunta 1 de 4'), findsOneWidget);
    final saved = await LearningStore(backend).load();
    expect(saved.progress.game(GameId.colors).questions, 1);
    expect(saved.progress.game(GameId.colors).sessions, 0);
  });

  testWidgets('progreso, premios y preferencias se conservan al cerrar y abrir la app', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    final backend = MemoryBackend();
    await pumpApp(tester, learningBackend: backend);
    await openHub(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Sonidos activados'));
    await tapAndSettle(tester, find.bySemanticsLabel('Nivel Intermedio'));
    await openGame(tester, 'Aprende los colores');
    await playQuiz(tester);
    await tapAndSettle(tester, find.text('Otros juegos'));

    // «Reinicio»: app nueva sobre el mismo almacenamiento.
    await tester.pumpWidget(const SizedBox());
    final learning = LearningController(LearningStore(backend));
    await pumpApp(tester, learning: learning);
    await openHub(tester);
    expect(find.bySemanticsLabel('Sonidos desactivados'), findsOneWidget);
    expect(learning.settings.level, LearningLevel.intermediate);
    await tapAndSettle(tester, find.bySemanticsLabel('Mis premios'));
    expect(find.bySemanticsLabel('Pegatina Explorador de colores, conseguida'), findsOneWidget);
    expect(find.bySemanticsLabel('Tienes 5 estrellas'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a los juegos'));

    // Con los sonidos desactivados no suena nada.
    await openGame(tester, 'Aprende los colores');
    expect(options(tester), hasLength(4));
    await tapOption(tester, correctOption(tester));
    expect(lastSounds!.played, isEmpty);
    expect(lastNarrator!.spoken, isNotEmpty); // la voz sigue activada
  });

  testWidgets('la voz se puede desactivar y el botón «Escuchar» desaparece', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    await pumpApp(tester);
    await openHub(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Voz activada'));
    await openGame(tester, 'Descubre las formas');
    expect(find.bySemanticsLabel('Escuchar'), findsNothing);
    lastSounds!.played.clear();
    await tapOption(tester, correctOption(tester));
    expect(lastNarrator!.spoken, isEmpty);
    expect(lastSounds!.played, [SoundCue.correct]); // los sonidos siguen activos
  });

  testWidgets('«Escuchar» lee la instrucción y al salir se libera el audio', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    await pumpApp(tester);
    await openHub(tester);
    await openGame(tester, 'Aprende los colores');
    lastNarrator!.spoken.clear();
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
    expect(lastNarrator!.spoken.single, startsWith('Encuentra el color'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a los juegos'));
    expect(lastNarrator!.stops, greaterThan(0)); // la voz se calla al salir del juego
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    expect(find.byType(HomeScreen), findsOneWidget);
    expect(lastSounds!.releases, 1); // reproductores liberados al salir de la sección
  });

  testWidgets('jugar no altera los dibujos guardados de la Fase 5 ni usa la red', (tester) async {
    setScreenSize(tester, setScreenSizeDefault);
    final previous = HttpOverrides.current;
    final noNetwork = _NoNetwork();
    HttpOverrides.global = noNetwork;
    addTearDown(() => HttpOverrides.global = previous);

    final backend = MemoryBackend(); // mismo almacenamiento para todo, como en la app
    final creations = KeyValueCreationStore(backend);
    await pumpApp(tester, store: creations, learningBackend: backend);
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
    final gato = svgOf('animals', 'animal_gato');
    await tapAndSettle(tester, find.bySemanticsLabel('Rojo'));
    await tester.tapAt(screenPointOf(tester, gato, interiorPoint(gato, 'cabeza')));
    await tester.pump();
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    final before = Map.of((await creations.latestFor('animal_gato'))!.regionColors);

    await openHub(tester);
    await openGame(tester, 'Une las parejas');
    await playMemory(tester, 4);
    await tapAndSettle(tester, find.text('Otros juegos'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    await tapAndSettle(tester, find.bySemanticsLabel('Mis dibujos'));
    expect(find.bySemanticsLabel(RegExp(r'^Gato\. ')), findsOneWidget);
    final report = await creations.loadAll();
    expect(report.creations.single.regionColors, before);
    expect(report.problems, isEmpty);
    expect(noNetwork.attempts, 0);
  });
}

Size setScreenSizeDefault = const Size(420, 900);

class _NoNetwork extends HttpOverrides {
  int attempts = 0;

  @override
  HttpClient createHttpClient(SecurityContext? context) {
    attempts++;
    throw const SocketException('Sin conexión (prueba)');
  }
}
