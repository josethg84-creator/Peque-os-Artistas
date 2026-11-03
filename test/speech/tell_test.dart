import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final tell = parseTell(
    jsonDecode(File(SpeechContent.tellAsset).readAsStringSync()) as Map<String, dynamic>,
  );

  test('8 historias de 4 dibujos, con una pregunta de Lolo por dibujo y su final', () {
    expect(tell, hasLength(8));
    for (final t in tell) {
      expect(t.steps, hasLength(4), reason: t.id);
      expect(t.steps.every((s) => s.question.endsWith('?')), isTrue, reason: t.id);
      expect(t.steps.map((s) => s.phrase).toSet(), hasLength(4), reason: t.id);
      expect(t.ending, endsWith('.'), reason: t.id);
    }
  });

  test('la semilla, como en el ejemplo', () {
    final s = tell.firstWhere((t) => t.id == 'semilla');
    expect(s.steps.map((x) => x.phrase), [
      'Una niña encuentra una semilla.',
      'La niña planta la semilla.',
      'La niña riega la planta.',
      '¡Aparece una flor!',
    ]);
    expect(s.ending, 'La niña plantó una semilla, la regó y creció una flor.');
  });
}
