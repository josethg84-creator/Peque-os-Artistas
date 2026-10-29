import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/coloring_canvas.dart';
import 'package:pequenos_artistas/coloring/engine/drawing_painter.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/learning/audio/learning_audio.dart';
import 'package:pequenos_artistas/learning/learning_controller.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';
import 'package:pequenos_artistas/learning/learning_progress.dart';
import 'package:pequenos_artistas/learning/learning_store.dart';
import 'package:pequenos_artistas/learning/screens/learning_game_screen.dart';
import 'package:pequenos_artistas/learning/screens/memory_game_screen.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/screens/categories_screen.dart';
import 'package:pequenos_artistas/widgets/mascot.dart';
import 'package:pequenos_artistas/widgets/motion/delayed_loading.dart';

import 'test_helpers.dart';

/// Pruebas de la Fase 7: animaciones, efectos, celebraciones y sonidos.
Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

VectorDrawing platano() =>
    parseColoringSvg(File('assets/drawings/fruits/fruta_platano.svg').readAsStringSync());

Finder anyCompletionMessage() =>
    find.byWidgetPredicate((w) => w is Text && ColoringCanvas.completionMessages.contains(w.data));

DrawingPainter canvasPainter(WidgetTester tester) =>
    tester.widget<CustomPaint>(drawingCanvasFinder).painter! as DrawingPainter;

int count(SoundCue cue) => lastSounds!.played.where((c) => c == cue).length;

Future<void> openPlatano(WidgetTester tester) async {
  await tapAndSettle(tester, find.bySemanticsLabel('Galería'));
  await tapAndSettle(tester, find.bySemanticsLabel('Frutas, 5 dibujos'));
  await tapAndSettle(tester, find.bySemanticsLabel('Plátano. Dificultad fácil'));
}

/// Pinta todas las zonas del plátano (sin esperar a que acaben las animaciones).
Future<void> paintAll(WidgetTester tester, VectorDrawing d, String color) async {
  await tapAndSettle(tester, find.bySemanticsLabel(color));
  for (final r in d.regions.where((r) => r.id != 'fondo')) {
    await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, r.id)));
    await tester.pump();
  }
}

void reduceMotion(WidgetTester tester) {
  tester.platformDispatcher.accessibilityFeaturesTestValue = const FakeAccessibilityFeatures(
    disableAnimations: true,
  );
  addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);
}

void main() {
  testWidgets('un doble toque rápido en un botón solo abre una pantalla', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    final galeria = find.bySemanticsLabel('Galería');
    await tester.tap(galeria);
    await tester.tap(galeria);
    await tester.pumpAndSettle();
    expect(find.byType(CategoriesScreen, skipOffstage: false), findsOneWidget);
    // Si se hubieran abierto dos, al volver una vez seguiríamos en la galería.
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    expect(find.text('¡Hola! ¿Qué quieres pintar hoy?'), findsOneWidget);
  });

  testWidgets('los botones responden al lector de pantalla y una doble activación abre una sola pantalla', (
    tester,
  ) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    // Dos activaciones seguidas con TalkBack (acción «tocar» de accesibilidad).
    tester.semantics.tap(find.semantics.byLabel('Galería'));
    tester.semantics.tap(find.semantics.byLabel('Galería'));
    await tester.pumpAndSettle();
    expect(find.byType(CategoriesScreen, skipOffstage: false), findsOneWidget);
    tester.semantics.tap(find.semantics.byLabel('Volver al inicio'));
    await tester.pumpAndSettle();
    expect(find.text('¡Hola! ¿Qué quieres pintar hoy?'), findsOneWidget);
  });

  testWidgets('el color se aplica al instante y el relleno se anima sin tocar los contornos', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await openPlatano(tester);
    final d = platano();
    await tapAndSettle(tester, find.bySemanticsLabel('Azul'));
    await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, 'platano')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 60));

    final painter = canvasPainter(tester);
    final blue = kidPalette.firstWhere((c) => c.name == 'Azul').color;
    // El modelo ya tiene el color definitivo (para guardar y deshacer)…
    expect(painter.colors.colorOf('platano'), blue);
    // …mientras la animación del relleno avanza desde el punto tocado.
    expect(painter.fill!.isActive, isTrue);
    expect(painter.fill!.regionId, 'platano');
    expect(painter.fill!.progress, inExclusiveRange(0, 1));
    expect(count(SoundCue.pop), 1);

    await tester.pumpAndSettle();
    expect(painter.fill!.isActive, isFalse);
    expect(painter.colors.colorOf('platano'), blue);
    // Solo cambia la zona tocada.
    expect(painter.colors.colorOf('tallo'), isNull);
  });

  testWidgets('la celebración sale una sola vez al terminar, no al repintar ni al reabrir', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await openPlatano(tester);
    final d = platano();
    await paintAll(tester, d, 'Amarillo');
    expect(anyCompletionMessage(), findsOneWidget);
    expect(find.byType(Mascot), findsWidgets);
    expect(count(SoundCue.celebrate), 1);

    // La celebración no bloquea: se puede seguir pintando y se oculta sola.
    await paintAll(tester, d, 'Verde');
    await tester.pumpAndSettle();
    expect(count(SoundCue.celebrate), 1);
    expect(anyCompletionMessage(), findsNothing);

    // Reabrir el dibujo terminado no vuelve a celebrarlo.
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a categorías'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    await tapAndSettle(tester, find.bySemanticsLabel('Mis dibujos'));
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Plátano\. ')));
    expect(drawingCanvasFinder, findsOneWidget);
    expect(anyCompletionMessage(), findsNothing);
    expect(count(SoundCue.celebrate), 1);
  });

  testWidgets('con movimiento reducido todo funciona sin animaciones ni confeti', (tester) async {
    reduceMotion(tester);
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await openPlatano(tester);
    final d = platano();
    await tapAndSettle(tester, find.bySemanticsLabel('Rojo'));
    await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, 'platano')));
    await tester.pump();
    expect(canvasPainter(tester).fill!.isActive, isFalse); // sin animación de relleno
    await paintAll(tester, d, 'Rojo');
    expect(anyCompletionMessage(), findsOneWidget); // el mensaje sí se muestra
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);

    // Los minijuegos también se pueden jugar.
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a categorías'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    await tapAndSettle(tester, find.bySemanticsLabel('Aprender jugando'));
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Une las parejas')));
    await tester.tap(find.byKey(const ValueKey('carta-0')));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });

  testWidgets('una carta que se está dando la vuelta se puede volver a tocar', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final learning = LearningController(LearningStore(MemoryBackend()));
    await learning.load();
    await learning.updateSettings(learning.settings.copyWith(level: LearningLevel.advanced));
    await pumpApp(tester, learning: learning);
    tester
        .state<NavigatorState>(find.byType(Navigator))
        .push(
          MaterialPageRoute<void>(builder: (_) => const LearningGameScreen(game: GameId.memory, seed: 3)),
        );
    await tester.pumpAndSettle();

    String label(int id) => tester
        .widget<Semantics>(
          find.descendant(of: find.byKey(ValueKey('carta-$id')), matching: find.byType(Semantics)).first,
        )
        .properties
        .label!;
    Future<void> flip(int id) async {
      await tester.tap(find.byKey(ValueKey('carta-$id')));
      await tester.pumpAndSettle();
    }

    // Busca dos cartas distintas (12 cartas con la semilla fija).
    int? first;
    for (var a = 0; a < 11 && first == null; a += 2) {
      await flip(a);
      await flip(a + 1);
      if (!label(a).endsWith('pareja encontrada')) first = a;
    }
    expect(first, isNotNull);
    expect(find.text('¡Casi! Inténtalo otra vez'), findsOneWidget);
    await tester.pump(MemoryGameScreen.mismatchPause);
    await tester.pump(const Duration(milliseconds: 60)); // a mitad del giro de vuelta
    expect(label(first!), contains('boca abajo'));
    await tester.tap(find.byKey(ValueKey('carta-$first')));
    await tester.pumpAndSettle();
    expect(label(first), isNot(contains('boca abajo')));
  });

  testWidgets('el premio nuevo suena una vez con confeti; repetir no lo vuelve a celebrar', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Aprender jugando'));
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Une las parejas')));
    // Nivel inicial: 2 parejas. Se prueban parejas de cartas boca abajo hasta terminar.
    bool finished() => find.text('¡Excelente trabajo!').evaluate().isNotEmpty;
    bool faceDown(int id) {
      final card = find.byKey(ValueKey('carta-$id'));
      if (card.evaluate().isEmpty) return false;
      final s = tester.widget<Semantics>(find.descendant(of: card, matching: find.byType(Semantics)).first);
      return s.properties.label!.contains('boca abajo');
    }

    for (var round = 0; round < 6 && !finished(); round++) {
      for (var a = 0; a < 4; a++) {
        for (var b = a + 1; b < 4; b++) {
          if (finished() || !faceDown(a) || !faceDown(b)) continue;
          await tester.tap(find.byKey(ValueKey('carta-$a')));
          await tester.pump();
          await tester.tap(find.byKey(ValueKey('carta-$b')));
          await tester.pump();
          await tester.pump(MemoryGameScreen.mismatchPause);
          await tester.pumpAndSettle();
        }
      }
    }
    expect(find.text('¡Excelente trabajo!'), findsOneWidget);
    expect(find.text('¡Pegatina nueva!'), findsOneWidget);
    expect(count(SoundCue.reward), 1);
    expect(count(SoundCue.celebrate), 1);
    expect(find.byType(Mascot), findsWidgets);

    await tapAndSettle(tester, find.bySemanticsLabel('Otros juegos'));
    expect(count(SoundCue.reward), 1);
  });

  testWidgets('Mis dibujos vacío muestra a la mascota y un mensaje amable', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    expect(find.byType(Mascot), findsOneWidget); // en el inicio
    await tapAndSettle(tester, find.bySemanticsLabel('Mis dibujos'));
    expect(find.text('¡Tu galería te espera!'), findsOneWidget);
    expect(find.textContaining('Aquí aparecerán tus dibujos favoritos'), findsOneWidget);
    expect(find.byType(Mascot), findsOneWidget);
  });

  testWidgets('el indicador de carga solo aparece si la espera es larga', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: DelayedLoading(message: 'Preparando tus colores…')),
      ),
    );
    double opacity() => tester.widget<AnimatedOpacity>(find.byType(AnimatedOpacity)).opacity;
    expect(opacity(), 0);
    await tester.pump(const Duration(milliseconds: 100));
    expect(opacity(), 0);
    await tester.pump(DelayedLoading.delay);
    expect(opacity(), 1);
    await tester.pump(const Duration(milliseconds: 400)); // termina de aparecer
    expect(find.bySemanticsLabel('Preparando tus colores…'), findsOneWidget);
    await tester.pumpWidget(const SizedBox()); // se cancela el temporizador al salir
  });

  testWidgets('el interruptor de sonido del inicio silencia todos los efectos', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Sonidos activados'));
    expect(find.bySemanticsLabel('Sonidos desactivados'), findsOneWidget);
    await openPlatano(tester);
    final d = platano();
    await paintAll(tester, d, 'Rosa');
    await tester.pumpAndSettle();
    expect(lastSounds!.played, isEmpty);
    expect(anyCompletionMessage(), findsNothing); // ya se ocultó
  });

  group('prioridad del audio', () {
    late DateTime now;
    late RecordingSoundEffects effects;
    late LearningSettings settings;
    late LearningAudio audio;

    setUp(() {
      now = DateTime(2026, 1, 1);
      effects = RecordingSoundEffects();
      settings = const LearningSettings();
      audio = LearningAudio(
        effects: effects,
        narrator: RecordingNarrator(),
        settings: () => settings,
        clock: () => now,
      );
    });

    test('un toque no corta una celebración que está sonando', () async {
      await audio.play(SoundCue.celebrate);
      now = now.add(const Duration(milliseconds: 200));
      await audio.play(SoundCue.pop);
      await audio.play(SoundCue.select);
      expect(effects.played, [SoundCue.celebrate]);
      now = now.add(LearningAudio.importantWindow);
      await audio.play(SoundCue.pop);
      expect(effects.played, [SoundCue.celebrate, SoundCue.pop]);
    });

    test('un premio sí puede sonar tras una celebración', () async {
      await audio.play(SoundCue.celebrate);
      await audio.play(SoundCue.reward);
      expect(effects.played, [SoundCue.celebrate, SoundCue.reward]);
    });

    test('con los sonidos desactivados no suena nada', () async {
      settings = settings.copyWith(soundOn: false);
      for (final cue in SoundCue.values) {
        await audio.play(cue);
      }
      expect(effects.played, isEmpty);
    });
  });
}
