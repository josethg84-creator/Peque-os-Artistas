import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/screens/listening_screens.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final raw = jsonDecode(File(SpeechContent.listeningAsset).readAsStringSync()) as Map<String, dynamic>;
  final content = ListeningContent.fromJson(raw);

  test('al menos 50 ejercicios válidos, todos se cargan y sin repetir', () {
    expect((raw['exercises'] as List).length, content.exercises.length, reason: 'ninguno se descarta');
    expect(content.exercises.length, greaterThanOrEqualTo(50));
    expect(content.exercises.map((e) => '${e.say} ${e.question}').toSet().length, content.exercises.length);
  });

  test('cubre los siete tipos pedidos', () {
    for (final t in ListeningType.values) {
      expect(content.exercises.where((e) => e.type == t).length, greaterThanOrEqualTo(4), reason: t.id);
    }
  });

  test('tres niveles de dificultad gradual', () {
    expect(content.levels.map((l) => l.level), [1, 2, 3]);
    for (final l in content.levels) {
      expect(content.ofLevel(l.level).length, greaterThanOrEqualTo(12), reason: '${l.level}');
    }
    // Nivel 1: una frase y tres respuestas, sin instrucciones de dos pasos.
    expect(content.ofLevel(1).every((e) => e.steps == null && e.options.length == 3), isTrue);
    // Las instrucciones de dos pasos son de los niveles 2 y 3, y casi todas del 3.
    final steps = content.exercises.where((e) => e.steps != null).toList();
    expect(steps.every((e) => e.level >= 2), isTrue);
    expect(steps.where((e) => e.level == 3).length, greaterThan(steps.length ~/ 2));
    // Las frases se alargan con el nivel.
    double avg(int l) =>
        content.ofLevel(l).map((e) => e.say.length).reduce((a, b) => a + b) / content.ofLevel(l).length;
    expect(avg(2), greaterThan(avg(1)));
  });

  test('cada pregunta tiene dibujos, frase y pregunta bien escritas', () {
    for (final e in content.exercises) {
      expect(e.options.every((o) => o.picture != null && o.label.isNotEmpty), isTrue, reason: e.id);
      expect(e.say, matches(RegExp(r'[.!]$')), reason: e.id);
      if (e.steps == null) expect(e.question, endsWith('?'), reason: e.id);
      if (e.type == ListeningType.escena) expect(e.scene, isNotNull, reason: e.id);
      final q = e.toQuestion();
      expect(q.answer, e.steps?.last ?? e.answer);
      expect(q.speech, contains(e.say));
    }
  });

  test('una ronda mezcla tipos y no repite ejercicios', () {
    final round = ListeningScreen.pickRound(content.ofLevel(2), Random(3), 8);
    expect(round, hasLength(8));
    expect(round.map((e) => e.id).toSet(), hasLength(8));
    for (var i = 1; i < round.length; i++) {
      expect(round[i].type, isNot(round[i - 1].type));
    }
  });

  test('se descartan ejercicios mal escritos', () {
    ListeningExercise? parse(Map<String, dynamic> m) => ListeningExercise.fromJson({
      'id': 'x',
      'level': 1,
      'type': 'quien',
      'say': 'Hola.',
      'question': '¿Quién?',
      'options': [
        {
          'text': 'A',
          'picture': {'icon': 'sun'},
        },
        {
          'text': 'B',
          'picture': {'icon': 'moon'},
        },
      ],
      ...m,
    });
    expect(parse({'answer': 1}), isNotNull);
    expect(parse({'answer': 2}), isNull);
    expect(parse({'type': 'otro', 'answer': 0}), isNull);
    expect(
      parse({
        'steps': [0, 0],
      }),
      isNull,
    );
    expect(
      parse({
        'steps': [1, 0],
      })!.answer,
      0,
    );
    expect(
      parse({
        'answer': 0,
        'options': [
          {
            'text': 'A',
            'picture': {'icon': 'no_existe'},
          },
          {
            'text': 'B',
            'picture': {'icon': 'moon'},
          },
        ],
      }),
      isNull,
    );
  });
}
