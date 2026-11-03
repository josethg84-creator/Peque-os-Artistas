import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_activities.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

Map<String, dynamic> readJson(String path) =>
    jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;

SpeechContent realContent() => SpeechContent.parse(
  readJson(SpeechContent.wordsAsset),
  readJson(SpeechContent.phrasesAsset),
  verbs: readJson(SpeechContent.verbsAsset),
  sentences: readJson(SpeechContent.sentencesAsset),
);

void main() {
  final content = realContent();

  test('los 15 verbos pedidos, con su presente bien conjugado', () {
    expect(content.verbs.map((v) => v.infinitive), [
      'comer',
      'beber',
      'jugar',
      'correr',
      'dormir',
      'saltar',
      'caminar',
      'pintar',
      'leer',
      'cantar',
      'bailar',
      'mirar',
      'hablar',
      'abrir',
      'cerrar',
    ]);
    final comer = content.verbs.first;
    expect(
      [for (final p in VerbPerson.values) comer.sentence(p)],
      [
        'Yo como una manzana.',
        'Tú comes una manzana.',
        'Él come una manzana.',
        'Ella come una manzana.',
        'Nosotros comemos una manzana.',
      ],
    );
    // Los irregulares también.
    String forms(String id) =>
        VerbPerson.values.map(content.verbs.firstWhere((v) => v.id == id).form).join(' ');
    expect(forms('dormir'), 'duermo duermes duerme duerme dormimos');
    expect(forms('jugar'), 'juego juegas juega juega jugamos');
    expect(forms('cerrar'), 'cierro cierras cierra cierra cerramos');
    expect(content.verbs.firstWhere((v) => v.id == 'leer').gerund, 'leyendo');
  });

  test('contenido de oraciones: sujetos, acciones, 12 para ordenar y 8 para completar', () {
    final s = content.sentences;
    expect(s.subjects, hasLength(6));
    expect(s.actions, hasLength(7));
    expect(s.actions.every((a) => content.verbs.any((v) => v.id == a.verbId)), isTrue);
    expect(s.order, hasLength(12));
    // Tres niveles: 3, 4 y 5 o más palabras.
    expect(s.order.map((o) => o.words.length).toSet(), containsAll([3, 4, 5]));
    expect(s.complete, hasLength(8));
    for (final c in s.complete) {
      expect(c.options.map((o) => o.text), contains(c.answer), reason: c.full);
      expect(c.options.map((o) => o.text).toSet(), hasLength(c.options.length), reason: c.full);
    }
  });

  for (final quiz in SpeechQuizKind.values) {
    test('${quiz.title}: preguntas válidas y siempre iguales con la misma semilla', () {
      final a = quiz.build(content, Random(7));
      final b = quiz.build(content, Random(7));
      expect(a, isNotEmpty);
      expect(a.map((q) => q.prompt ?? q.speech), b.map((q) => q.prompt ?? q.speech));
      for (final q in a) {
        expect(q.answer, inInclusiveRange(0, q.options.length - 1), reason: q.speech);
        expect(q.options.map((o) => o.label).toSet(), hasLength(q.options.length), reason: q.speech);
        expect(q.speech.trim(), isNotEmpty);
      }
    });
  }

  test('completar: la respuesta es la palabra que falta y al acertar se dice la oración', () {
    for (final q in completeQuestions(content, Random(1))) {
      final full = q.afterCorrect!;
      expect(q.prompt!.replaceFirst('___', q.options[q.answer].label), full);
    }
  });

  test('pregunta o afirmación: la mitad son preguntas y la respuesta coincide con los signos', () {
    final qs = questionOrStatementQuestions(content, Random(3));
    expect(qs.where((q) => q.answer == 1), hasLength(qs.length ~/ 2));
    for (final q in qs) {
      expect(q.prompt!.startsWith('¿') && q.prompt!.endsWith('?'), q.answer == 1, reason: q.prompt);
      expect(q.options.map((o) => o.label), ['Afirmación', 'Pregunta']);
    }
  });

  test('verbos: completar con la forma correcta, elegir la acción, ¿quién está…? y escuchar', () {
    final qs = verbQuestions(content, Random(5));
    expect(qs, hasLength(8));
    final complete = qs.where((q) => q.instruction == 'Completa la oración');
    expect(complete, isNotEmpty);
    for (final q in complete) {
      expect(q.prompt!.replaceFirst('___', q.options[q.answer].label), q.afterCorrect);
    }
    final who = qs.where((q) => q.instruction.startsWith('¿Quién está'));
    expect(who, isNotEmpty);
    expect(who.every((q) => q.options.every((o) => o.badge != null)), isTrue);
    final listen = qs.where((q) => q.instruction == 'Escucha y señala');
    expect(listen.every((q) => q.options.every((o) => !o.showLabel)), isTrue);
  });

  test('comprensión: se pregunta por una palabra con su artículo o por una frase', () {
    final qs = [for (var seed = 0; seed < 20; seed++) ...comprehensionQuestions(content, Random(seed))];
    // Con 20 semillas salen las tres formas de preguntar.
    expect(qs.any((q) => q.instruction.startsWith('Señala')), isTrue);
    expect(qs.any((q) => q.instruction.startsWith('¿Dónde están')), isTrue);
    expect(qs.any((q) => q.instruction.startsWith('¿Dónde está ')), isTrue);
    for (final q in qs) {
      final right = q.options[q.answer];
      expect(right.showLabel, isFalse);
      if (q.instruction.startsWith('¿Dónde')) {
        expect(q.instruction, endsWith('${right.label}?'));
        expect(q.instruction, matches(RegExp(r'^¿Dónde (está (el|la)|están (los|las)) ')));
      } else if (q.instruction.startsWith('Señala')) {
        expect(q.instruction, 'Señala: ${right.label}');
      } else {
        expect(q.speech, contains(right.label));
      }
    }
  });
}
