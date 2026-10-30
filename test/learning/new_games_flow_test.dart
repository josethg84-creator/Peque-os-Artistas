import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/learning/audio/learning_audio.dart';
import 'package:pequenos_artistas/learning/games/maze.dart';
import 'package:pequenos_artistas/learning/games/tracing.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';
import 'package:pequenos_artistas/learning/screens/learning_game_screen.dart';
import 'package:pequenos_artistas/learning/screens/tracing_game_screen.dart';

import '../test_helpers.dart';

/// Los tres juegos nuevos, jugados en la app completa.
Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// Abre un juego del menú (con siete juegos, algunos quedan más abajo).
Future<void> openGame(WidgetTester tester, String title) async {
  final group = const {'Rompecabezas', 'Laberintos', 'Une las parejas'}.contains(title)
      ? 'Mini Juegos'
      : 'Actividades';
  await tapAndSettle(tester, find.bySemanticsLabel(group));
  final tile = find.bySemanticsLabel(RegExp('^${RegExp.escape(title)}'));
  if (tile.evaluate().isEmpty) {
    await tester.dragUntilVisible(tile, find.byType(CustomScrollView), const Offset(0, -300));
  }
  await tapAndSettle(tester, tile);
}

Future<void> dragPiece(WidgetTester tester, int piece, int cell) async {
  final from = tester.getCenter(find.byKey(ValueKey('pieza-$piece')));
  final to = tester.getCenter(find.byKey(ValueKey('casilla-$cell')));
  final g = await tester.startGesture(from);
  for (var i = 1; i <= 8; i++) {
    await g.moveTo(Offset.lerp(from, to, i / 8)!);
    await tester.pump(const Duration(milliseconds: 16));
  }
  await g.up();
  await tester.pumpAndSettle();
}

int count(SoundCue cue) => lastSounds!.played.where((c) => c == cue).length;

void main() {
  testWidgets('rompecabezas: arrastrar las piezas, una equivocada vuelve, y se completa', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await openGame(tester, 'Rompecabezas');
    // Nivel inicial: 4 piezas.
    for (var i = 0; i < 4; i++) {
      expect(find.byKey(ValueKey('pieza-$i')), findsOneWidget);
    }
    expect(find.byKey(const ValueKey('pieza-4')), findsNothing);
    expect(lastNarrator!.spoken.first, 'Arrastra cada pieza a su sitio');

    // Pieza en la casilla equivocada: vuelve a la bandeja.
    await dragPiece(tester, 0, 3);
    expect(find.byKey(const ValueKey('pieza-0')), findsOneWidget);
    expect(find.text('Esa pieza va en otro sitio'), findsOneWidget);
    expect(count(SoundCue.tryAgain), 1);

    await dragPiece(tester, 0, 0);
    expect(find.byKey(const ValueKey('pieza-0')), findsNothing, reason: 'colocada en el tablero');
    expect(count(SoundCue.correct), 1);
    // También se puede tocar la pieza y después su casilla.
    await tapAndSettle(tester, find.byKey(const ValueKey('pieza-1')));
    await tapAndSettle(tester, find.byKey(const ValueKey('casilla-1')));
    expect(find.byKey(const ValueKey('pieza-1')), findsNothing);
    await dragPiece(tester, 2, 2);
    await dragPiece(tester, 3, 3);

    expect(find.text('¡Excelente trabajo!'), findsOneWidget);
    expect(find.text('Maestro del rompecabezas'), findsOneWidget);
    expect(count(SoundCue.celebrate), 1);
  });

  testWidgets('rompecabezas: 9 piezas en intermedio y 16 en avanzado', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    for (final (level, pieces) in [('Intermedio', 9), ('Avanzado', 16)]) {
      await tapAndSettle(tester, find.bySemanticsLabel('Mini Juegos'));
      await tapAndSettle(tester, find.bySemanticsLabel('Nivel $level'));
      final tile = find.bySemanticsLabel(RegExp('^Rompecabezas'));
      await tester.dragUntilVisible(tile, find.byType(CustomScrollView), const Offset(0, -300));
      await tapAndSettle(tester, tile);
      expect(find.byKey(ValueKey('pieza-${pieces - 1}')), findsOneWidget);
      expect(find.byKey(ValueKey('pieza-$pieces')), findsNothing);
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a los juegos'));
      await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    }
  });

  testWidgets('laberinto: las paredes no se atraviesan y siguiendo el camino se llega a la meta', (
    tester,
  ) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    tester
        .state<NavigatorState>(find.byType(Navigator))
        .push(MaterialPageRoute<void>(builder: (_) => const LearningGameScreen(game: GameId.maze, seed: 5)));
    await tester.pumpAndSettle();
    // El mismo laberinto que genera la pantalla con esa semilla.
    final game = MazeGame.random(LearningLevel.initial, MazeTheme.rabbit, Random(5));
    expect(find.text(MazeTheme.rabbit.instruction), findsOneWidget);

    const labels = {
      Dir.up: 'Mover arriba',
      Dir.down: 'Mover abajo',
      Dir.left: 'Mover a la izquierda',
      Dir.right: 'Mover a la derecha',
    };
    // Contra una pared: no se mueve y se avisa con voz.
    final wall = Dir.values.firstWhere((d) => !game.maze.canMove(game.start, d));
    await tapAndSettle(tester, find.bySemanticsLabel(labels[wall]!));
    expect(lastNarrator!.spoken, contains('¡Ahí hay una pared! Busca otro camino'));

    // Pista: aparece y se desvanece sola.
    await tapAndSettle(tester, find.bySemanticsLabel('Pista'));

    final path = game.maze.solve(game.start, game.goal)!;
    for (var i = 1; i < path.length; i++) {
      final d = Dir.values.firstWhere((d) => (x: path[i - 1].x + d.dx, y: path[i - 1].y + d.dy) == path[i]);
      await tester.tap(find.bySemanticsLabel(labels[d]!));
      await tester.pump(const Duration(milliseconds: 200));
    }
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(find.text('¡Excelente trabajo!'), findsOneWidget);
    expect(find.text('Explorador de laberintos'), findsOneWidget);
    expect(lastNarrator!.spoken.where((t) => t.startsWith('¡El conejo encontró su fresa!')), hasLength(1));
    expect(
      lastNarrator!.spoken.last,
      '¡Ganaste una pegatina nueva!',
      reason: 'en cola, sin cortar la anterior',
    );
  });

  testWidgets('laberinto: arrastrar el dedo mueve al personaje por el camino abierto', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    tester
        .state<NavigatorState>(find.byType(Navigator))
        .push(MaterialPageRoute<void>(builder: (_) => const LearningGameScreen(game: GameId.maze, seed: 9)));
    await tester.pumpAndSettle();
    final game = MazeGame.random(LearningLevel.initial, MazeTheme.rabbit, Random(9));
    final board = find.byWidgetPredicate(
      (w) => w is CustomPaint && w.painter.runtimeType.toString() == '_MazePainter',
    );
    final rect = tester.getRect(board);
    final cell = rect.width / game.maze.cols;
    Offset center(Cell c) => rect.topLeft + Offset((c.x + 0.5) * cell, (c.y + 0.5) * cell);
    // Arrastre continuo por toda la solución.
    final path = game.maze.solve(game.start, game.goal)!;
    final g = await tester.startGesture(center(path.first));
    for (final c in path.skip(1)) {
      await g.moveTo(center(c));
      await tester.pump(const Duration(milliseconds: 30));
    }
    await g.up();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(find.text('¡Excelente trabajo!'), findsOneWidget);
  });

  testWidgets('trazos: escribir letras con el dedo, borrar, y completar la actividad', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await openGame(tester, 'Trazos y escritura');
    for (final s in ['Líneas', 'Letras', 'Números', 'Unir puntos']) {
      expect(find.bySemanticsLabel(RegExp('^$s')), findsOneWidget);
    }
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Letras')));
    await tapAndSettle(tester, find.bySemanticsLabel('La letra A'));
    expect(lastNarrator!.spoken.last, contains('La letra A'));

    final canvas = find.byKey(const ValueKey('lienzo-trazo'));
    Future<void> trace(TraceItem item, {Offset shift = Offset.zero}) async {
      final rect = tester.getRect(canvas);
      // Coordenadas del lienzo interior (dentro del borde de 3 px).
      final inner = rect.deflate(3);
      for (final stroke in item.strokes) {
        final pts = TraceEvaluator.resample(stroke, 0.02);
        final g = await tester.startGesture(inner.topLeft + (pts.first + shift) * inner.width);
        for (final p in pts.skip(1)) {
          await g.moveTo(inner.topLeft + (p + shift) * inner.width);
        }
        await g.up();
        await tester.pump();
      }
      await tester.pumpAndSettle();
    }

    // Un garabato fuera de la guía, y borrar.
    await trace(traceLetters[0], shift: const Offset(0.4, 0.4));
    expect(find.text('¡Muy bien!'), findsNothing);
    await tapAndSettle(tester, find.bySemanticsLabel('Borrar'));
    expect(tester.getSemantics(find.bySemanticsLabel('Progreso del trazo')).value, '0 %');

    // Nivel inicial: 3 letras seguidas (A, B y C).
    for (final (i, letter) in traceLetters.take(3).indexed) {
      await trace(letter);
      expect(find.text('¡Muy bien!'), findsOneWidget, reason: letter.label);
      await tapAndSettle(tester, find.text(i == 2 ? '¡Terminar!' : 'Siguiente'));
    }
    expect(find.text('¡Excelente trabajo!'), findsOneWidget);
    expect(find.text('Pequeño escritor'), findsOneWidget);
  });

  testWidgets('trazos: unir los puntos en orden descubre el dibujo', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    await openGame(tester, 'Trazos y escritura');
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Unir puntos')));
    await tapAndSettle(tester, find.bySemanticsLabel('Una casa'));
    final rect = tester.getRect(find.byKey(const ValueKey('lienzo-trazo'))).deflate(3);
    final dots = traceDots.firstWhere((d) => d.id == 'casa').dots;
    final g = await tester.startGesture(rect.topLeft + dots.first * rect.width);
    for (final p in dots.skip(1)) {
      await g.moveTo(rect.topLeft + p * rect.width);
      await tester.pump();
    }
    await g.up();
    await tester.pumpAndSettle();
    expect(find.text('¡Es una casa!'), findsOneWidget);
  });

  for (final (name, size, scale) in [
    ('teléfono pequeño, texto ×1.6', const Size(320, 568), 1.6),
    ('teléfono horizontal', const Size(740, 360), 1.0),
    ('tableta', const Size(1280, 800), 1.0),
  ]) {
    testWidgets('trazos sin desbordamientos: $name', (tester) async {
      setScreenSize(tester, size, textScale: scale);
      await pumpApp(tester);
      final nav = tester.state<NavigatorState>(find.byType(Navigator));
      for (final section in TraceSection.values) {
        nav.push(MaterialPageRoute<void>(builder: (_) => TracingSectionScreen(section: section)));
        await tester.pumpAndSettle();
        nav.push(MaterialPageRoute<void>(builder: (_) => TracingPracticeScreen(section: section, start: 0)));
        await tester.pumpAndSettle();
        expect(find.byKey(const ValueKey('lienzo-trazo')), findsOneWidget);
        nav.pop();
        nav.pop();
        await tester.pumpAndSettle();
      }
    });
  }
}
