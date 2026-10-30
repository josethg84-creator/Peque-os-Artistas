import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/learning/games/maze.dart';
import 'package:pequenos_artistas/learning/games/puzzle_game.dart';
import 'package:pequenos_artistas/learning/games/tracing.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';

/// Lógica de los juegos nuevos: rompecabezas, laberintos y trazos.
void main() {
  group('rompecabezas', () {
    test('4, 9 y 16 piezas según el nivel', () {
      expect([for (final l in LearningLevel.values) pow(puzzleSideFor(l), 2)], [4, 9, 16]);
    });

    test('empieza desordenado; cada pieza solo encaja en su sitio', () {
      for (var seed = 0; seed < 50; seed++) {
        final g = PuzzleGame(side: 2, random: Random(seed));
        expect(g.tray, isNot([0, 1, 2, 3]), reason: 'nunca empieza resuelto');
      }
      final g = PuzzleGame(side: 3, random: Random(1));
      expect(g.drop(2, 5), DropResult.wrong);
      expect(g.isPlaced(2), isFalse);
      expect(g.tray, contains(2), reason: 'vuelve a la bandeja');
      expect(g.drop(2, 2), DropResult.correct);
      expect(g.drop(2, 2), DropResult.ignored, reason: 'ya colocada');
      for (var i = 0; i < 9; i++) {
        g.drop(i, i);
      }
      expect(g.isComplete, isTrue);
      expect(g.tray, isEmpty);
    });
  });

  group('laberintos', () {
    test('cientos de laberintos generados: todos perfectos y con meta alcanzable', () {
      for (final level in LearningLevel.values) {
        for (var seed = 0; seed < 150; seed++) {
          final game = MazeGame.random(level, MazeTheme.values[seed % 4], Random(seed));
          final m = game.maze;
          // Perfecto: árbol que conecta todas las casillas (casillas − 1 pasos).
          expect(m.openings, m.cols * m.rows - 1);
          for (var y = 0; y < m.rows; y++) {
            for (var x = 0; x < m.cols; x++) {
              expect(m.solve(game.start, (x: x, y: y)), isNotNull);
            }
          }
          final path = m.solve(game.start, game.goal)!;
          expect(path.length, greaterThan(m.cols), reason: 'recorrido interesante');
        }
      }
    });

    test('no se atraviesan paredes ni se sale; siguiendo la solución se llega', () {
      final game = MazeGame.random(LearningLevel.intermediate, MazeTheme.car, Random(7));
      final m = game.maze;
      // Bordes: nunca se puede salir.
      for (var i = 0; i < m.cols; i++) {
        expect(m.canMove((x: i, y: 0), Dir.up), isFalse);
        expect(m.canMove((x: i, y: m.rows - 1), Dir.down), isFalse);
      }
      // Un movimiento contra una pared no cambia la posición.
      final blocked = Dir.values.firstWhere((d) => !m.canMove(game.position, d));
      final before = game.position;
      expect(game.move(blocked), MoveResult.blocked);
      expect(game.position, before);
      expect(game.bumps, 1);
      // La pista lleva a la meta.
      final path = game.hint();
      MoveResult last = MoveResult.ignored;
      for (var i = 1; i < path.length; i++) {
        final d = Dir.values.firstWhere((d) => (x: path[i - 1].x + d.dx, y: path[i - 1].y + d.dy) == path[i]);
        last = game.move(d);
      }
      expect(last, MoveResult.goal);
      expect(game.reached, isTrue);
      game.reset();
      expect(game.position, game.start);
    });

    test('un arrastre rápido avanza casilla a casilla y se detiene en la pared', () {
      final game = MazeGame.random(LearningLevel.advanced, MazeTheme.treasure, Random(3));
      final r = game.moveToward(game.goal);
      // O llega, o se para en una pared sin haberla cruzado.
      if (r != MoveResult.goal) expect(game.position, isNot(game.goal));
      for (var i = 1; i < game.trail.length; i++) {
        final a = game.trail[i - 1], b = game.trail[i];
        expect((a.x - b.x).abs() + (a.y - b.y).abs(), 1, reason: 'sin saltos');
        final d = Dir.values.firstWhere((d) => (x: a.x + d.dx, y: a.y + d.dy) == b);
        expect(game.maze.canMove(a, d), isTrue, reason: 'nunca atraviesa paredes');
      }
    });
  });

  group('trazos', () {
    final all = [for (final s in TraceSection.values) ...traceItems(s)];

    test('hay líneas, 27 letras (con la Ñ), números del 1 al 10 y dibujos de puntos', () {
      expect(
        traceLines.map((i) => i.id),
        containsAll(['horizontal', 'vertical', 'diagonal', 'curva', 'ondas', 'zigzag', 'circulo']),
      );
      expect(traceLetters.map((i) => i.label).join(), 'ABCDEFGHIJKLMNÑOPQRSTUVWXYZ');
      expect(traceNumbers.map((i) => i.label), [for (var n = 1; n <= 10; n++) '$n']);
      expect(traceDots.length, greaterThanOrEqualTo(5));
      for (final item in all) {
        for (final p in item.strokes.expand((s) => s)) {
          expect(p.dx, inInclusiveRange(0.04, 0.96), reason: item.id);
          expect(p.dy, inInclusiveRange(0.04, 0.96), reason: item.id);
        }
      }
    });

    test('trazar encima de la guía completa cada ejercicio en todos los niveles', () {
      for (final level in LearningLevel.values) {
        final diff = TraceDifficulty.of(level);
        for (final item in all) {
          final e = TraceEvaluator(item, diff);
          expect(e.isComplete, isFalse);
          for (final stroke in item.strokes) {
            for (final p in TraceEvaluator.resample(stroke, 0.01)) {
              // Un pulso algo torpe: a 40 % de la tolerancia de la línea.
              e.addPoint(p + Offset(diff.tolerance * 0.4, 0));
            }
          }
          expect(e.isComplete, isTrue, reason: '${item.id} (${level.label})');
          expect(e.progress, closeTo(1, 1e-9));
        }
      }
    });

    test('garabatos lejos de la guía, o solo media letra, no la completan', () {
      final diff = TraceDifficulty.of(LearningLevel.initial);
      final h = traceLetters.firstWhere((i) => i.label == 'H');
      final e = TraceEvaluator(h, diff);
      final r = Random(1);
      for (var i = 0; i < 300; i++) {
        e.addPoint(Offset(0.85 + r.nextDouble() * 0.1, r.nextDouble()));
      }
      expect(e.isComplete, isFalse);
      expect(e.mostlyOffPath, isTrue);
      // Solo los dos palos verticales: falta el horizontal.
      for (final stroke in h.strokes.take(2)) {
        for (final p in TraceEvaluator.resample(stroke, 0.01)) {
          e.addPoint(p);
        }
      }
      expect(e.isComplete, isFalse);
      // Los extremos del travesaño tocan los palos y cuentan algo, pero falta el resto.
      expect(e.progress, inExclusiveRange(2 / 3, 0.95));
      e.reset();
      expect(e.progress, 0);
    });

    test('unir puntos exige el orden: saltarse un punto no cuenta', () {
      final star = traceDots.first;
      final e = TraceEvaluator(star, TraceDifficulty.of(LearningLevel.intermediate));
      e.addPoint(star.dots[0]);
      e.addPoint(star.dots[2]); // se salta el 1
      expect(e.nextDot, 1);
      for (final p in star.dots.skip(1)) {
        e.addPoint(p);
      }
      expect(e.isComplete, isTrue);
    });

    test('la ayuda disminuye con el nivel', () {
      final [a, b, c] = [for (final l in LearningLevel.values) TraceDifficulty.of(l)];
      expect(a.tolerance > b.tolerance && b.tolerance > c.tolerance, isTrue);
      expect(a.coverage < b.coverage && b.coverage < c.coverage, isTrue);
      expect(a.showStrokeOrder && !c.showStrokeOrder, isTrue);
    });
  });
}
