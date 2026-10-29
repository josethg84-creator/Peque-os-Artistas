import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/learning/games/memory_game.dart';
import 'package:pequenos_artistas/learning/games/quiz_game.dart';
import 'package:pequenos_artistas/learning/learning_content.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';

void main() {
  group('Motor de preguntas', () {
    QuizGame<String> game({int options = 3, int questions = 4, int seed = 1}) => QuizGame<String>(
      pool: const ['a', 'b', 'c', 'd', 'e', 'f'],
      optionCount: options,
      questionCount: questions,
      random: Random(seed),
    );

    test('cada pregunta tiene la respuesta entre opciones distintas', () {
      for (var seed = 0; seed < 30; seed++) {
        final g = game(options: 4, seed: seed);
        for (var i = 0; i < 4; i++) {
          final q = g.question;
          expect(q.options, hasLength(4));
          expect(q.options.toSet(), hasLength(4));
          expect(q.options, contains(q.target));
          g.answer(q.target);
          g.next();
        }
      }
    });

    test('un error no avanza ni castiga: se puede volver a intentar', () {
      final g = game();
      final wrong = g.question.options.firstWhere((o) => o != g.question.target);
      expect(g.answer(wrong), AnswerResult.tryAgain);
      expect(g.answered, isFalse);
      expect(g.wrongAnswers, {wrong});
      expect(g.answer(wrong), AnswerResult.ignored); // la misma no cuenta dos veces
      expect(g.next(), isFalse); // no se avanza sin acertar
      expect(g.answer(g.question.target), AnswerResult.correct);
      expect(g.answered, isTrue);
      expect(g.mistakes, 1);
      expect(g.firstTryCorrect, 0);
    });

    test('avanza entre preguntas y termina tras la última', () {
      final g = game(questions: 4);
      for (var i = 0; i < 4; i++) {
        expect(g.index, i);
        expect(g.isFinished, isFalse);
        g.answer(g.question.target);
        if (i < 3) expect(g.next(), isTrue);
      }
      expect(g.isFinished, isTrue);
      expect(g.next(), isFalse);
      expect(g.firstTryCorrect, 4);
    });

    test('las preguntas no repiten objetivo mientras haya elementos', () {
      final g = game(questions: 6);
      final targets = <String>{};
      for (var i = 0; i < 6; i++) {
        targets.add(g.question.target);
        g.answer(g.question.target);
        g.next();
      }
      expect(targets, hasLength(6));
    });

    test('reiniciar empieza desde la primera pregunta', () {
      final g = game();
      g.answer(g.question.options.firstWhere((o) => o != g.question.target));
      g.answer(g.question.target);
      g.next();
      g.restart();
      expect(g.index, 0);
      expect(g.answered, isFalse);
      expect(g.mistakes, 0);
      expect(g.wrongAnswers, isEmpty);
    });

    test('nivel avanzado: usa distractores parecidos', () {
      final g = QuizGame<LearnColor>(
        pool: learnColors,
        optionCount: 4,
        questionCount: 6,
        preferredDistractors: (t, _) => [
          for (final id in similarColors[t.id]!) learnColors.firstWhere((c) => c.id == id),
        ],
        random: Random(3),
      );
      for (var i = 0; i < 6; i++) {
        final q = g.question;
        final similar = similarColors[q.target.id]!;
        expect(q.options.where((o) => similar.contains(o.id)), isNotEmpty, reason: q.target.id);
        g.answer(q.target);
        g.next();
      }
    });

    test('no se puede crear con menos elementos que opciones', () {
      expect(
        () => QuizGame<String>(pool: const ['a', 'b'], optionCount: 3, questionCount: 2),
        throwsArgumentError,
      );
    });
  });

  group('Contenido por nivel', () {
    test('colores: 6 básicos en inicial, los 11 en los demás', () {
      expect(colorsFor(LearningLevel.initial).map((c) => c.id), [
        'rojo',
        'azul',
        'amarillo',
        'verde',
        'naranja',
        'morado',
      ]);
      expect(colorsFor(LearningLevel.intermediate), hasLength(11));
      expect(learnColors.map((c) => c.name), [
        'Rojo',
        'Azul',
        'Amarillo',
        'Verde',
        'Naranja',
        'Morado',
        'Rosa',
        'Celeste',
        'Marrón',
        'Negro',
        'Blanco',
      ]);
    });

    test('formas: las 7 pedidas, cada una con explicación', () {
      expect(learnShapes.map((s) => s.name), [
        'Círculo',
        'Cuadrado',
        'Triángulo',
        'Rectángulo',
        'Óvalo',
        'Estrella',
        'Corazón',
      ]);
      expect(learnShapes.every((s) => s.explanation.isNotEmpty), isTrue);
      expect(shapesFor(LearningLevel.initial), hasLength(5));
    });

    test('animales: los 10 del catálogo, con una frase cada uno', () {
      expect(learnAnimals.map((a) => a.name), [
        'Gato',
        'Perro',
        'Conejo',
        'León',
        'Elefante',
        'Jirafa',
        'Oso',
        'Mariposa',
        'Pez',
        'Tortuga',
      ]);
      expect(learnAnimals.every((a) => a.fact.isNotEmpty && a.drawingId.startsWith('animal_')), isTrue);
    });

    test('tamaño por nivel: más opciones, preguntas y parejas al subir', () {
      expect(quizSizeFor(LearningLevel.initial), (options: 3, questions: 4));
      expect(quizSizeFor(LearningLevel.intermediate), (options: 4, questions: 5));
      expect(quizSizeFor(LearningLevel.advanced), (options: 4, questions: 6));
      expect(LearningLevel.values.map(pairsFor), [2, 4, 6]);
    });
  });

  group('Une las parejas', () {
    MemoryGame game(int pairs, {int seed = 1}) =>
        MemoryGame(faces: memoryCardDrawings, pairs: pairs, random: Random(seed));

    test('cada cara aparece exactamente dos veces', () {
      for (final pairs in [2, 4, 6]) {
        final g = game(pairs);
        expect(g.cards, hasLength(pairs * 2));
        final counts = <String, int>{};
        for (final c in g.cards) {
          counts[c.face] = (counts[c.face] ?? 0) + 1;
        }
        expect(counts.values.every((n) => n == 2), isTrue);
        expect(counts, hasLength(pairs));
      }
    });

    test('reconoce las parejas y las deja descubiertas', () {
      final g = game(2);
      final a = g.cards.first;
      final b = g.cards.firstWhere((c) => c.id != a.id && c.face == a.face);
      expect(g.flip(a.id), FlipResult.flipped);
      expect(g.flip(a.id), FlipResult.ignored); // la misma carta otra vez
      expect(g.flip(b.id), FlipResult.match);
      expect(a.matched && b.matched, isTrue);
      expect(g.matchedPairs, 1);
      expect(g.flip(a.id), FlipResult.ignored);
    });

    test('si no coinciden se ocultan tras la pausa; mientras tanto no se gira otra', () {
      final g = game(2);
      final a = g.cards.first;
      final b = g.cards.firstWhere((c) => c.face != a.face);
      final other = g.cards.firstWhere((c) => c.id != a.id && c.id != b.id);
      g.flip(a.id);
      expect(g.flip(b.id), FlipResult.noMatch);
      expect(g.waitingToHide, isTrue);
      expect(g.flip(other.id), FlipResult.ignored);
      g.hideMismatch();
      expect(a.faceUp || b.faceUp, isFalse);
      expect(g.attempts, 1);
    });

    test('termina al encontrar todas las parejas y se puede reiniciar', () {
      final g = game(4);
      for (final face in g.cards.map((c) => c.face).toSet()) {
        final [x, y] = g.cards.where((c) => c.face == face).toList();
        g.flip(x.id);
        g.flip(y.id);
      }
      expect(g.isFinished, isTrue);
      g.restart();
      expect(g.isFinished, isFalse);
      expect(g.cards.every((c) => !c.faceUp && !c.matched), isTrue);
    });
  });
}
