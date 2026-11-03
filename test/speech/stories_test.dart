import 'dart:convert';
import 'dart:io';

import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final stories = parseStories(
    jsonDecode(File(SpeechContent.storiesAsset).readAsStringSync()) as Map<String, dynamic>,
  );

  test('20 cuentos originales, 2 por cada una de las 10 categorías', () {
    expect(stories, hasLength(20));
    final per = <String, int>{};
    for (final s in stories) {
      per[s.category] = (per[s.category] ?? 0) + 1;
    }
    expect(per.keys, [
      'Animales',
      'Amistad',
      'Familia',
      'Naturaleza',
      'Emociones',
      'Hábitos saludables',
      'Aventuras',
      'Colores',
      'Valores',
      'Vida cotidiana',
    ]);
    expect(per.values.every((n) => n == 2), isTrue);
  });

  test('cada cuento: portada, personajes, 5 escenas ilustradas, 3 preguntas y 3 escenas para ordenar', () {
    for (final s in stories) {
      expect(s.characters, isNotEmpty, reason: s.title);
      expect(s.scenes, hasLength(5), reason: s.title);
      expect(s.scenes.every((x) => x.picture is ScenePicture), isTrue, reason: s.title);
      expect(s.scenes.every((x) => RegExp(r'[.!»]$').hasMatch(x.text)), isTrue, reason: s.title);
      expect(s.questions, hasLength(3), reason: s.title);
      for (final q in s.questions) {
        expect(q.options, hasLength(3), reason: '${s.title}: ${q.instruction}');
        expect(q.options.every((o) => o.picture != null), isTrue, reason: q.instruction);
        expect(q.options.map((o) => o.label).toSet(), hasLength(3), reason: q.instruction);
      }
      // No siempre es la primera opción la correcta.
      expect(s.order, hasLength(3), reason: s.title);
      expect([...s.order]..sort(), s.order, reason: '${s.title}: el orden va de menor a mayor');
    }
    final answers = stories.expand((s) => s.questions).map((q) => q.answer).toSet();
    expect(answers, containsAll([0, 1, 2]));
  });

  test('«Toby y la pelota roja», como en el ejemplo', () {
    final toby = stories.firstWhere((s) => s.id == 'toby_pelota');
    expect(toby.scenes.map((x) => x.text), [
      'Toby es un perro pequeño y juguetón.',
      'Una mañana, Toby encontró una pelota roja.',
      'Toby llevó la pelota al jardín.',
      'Su amiga Luna llegó para jugar con él.',
      'Los dos jugaron felices toda la tarde.',
    ]);
    expect(toby.questions.map((q) => q.instruction), [
      '¿Cómo se llamaba el perro?',
      '¿De qué color era la pelota?',
      '¿Dónde jugaba Toby?',
    ]);
    expect([for (final q in toby.questions) q.options[q.answer].label], ['Toby', 'Roja', 'En el jardín']);
  });

  test('las mariposas del cuento de colores tienen el color que dice el texto', () {
    final m = stories.firstWhere((s) => s.id == 'mariposa_colores');
    Color? wing(int scene) {
      final item = (m.scenes[scene].picture as ScenePicture).items.first.picture as DrawingPicture;
      return item.colorFor('ala_izquierda') ?? item.colorFor('zona_01') ?? item.colorFor('cuerpo');
    }

    expect(wing(0)!.toARGB32(), 0xFFFFFFFF);
    expect(wing(1)!.toARGB32(), 0xFFE53935);
    expect(wing(2)!.toARGB32(), 0xFFFFD600);
  });
}
