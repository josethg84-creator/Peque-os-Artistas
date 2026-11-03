import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final c = ExpressionContent.fromJson(
    jsonDecode(File(SpeechContent.expressionsAsset).readAsStringSync()) as Map<String, dynamic>,
  );

  test('las necesidades pedidas, con ilustración, texto y voz', () {
    expect(
      c.needs.map((n) => n.text),
      containsAll([
        'Quiero tomar agua.',
        'Tengo hambre.',
        'Necesito descansar.',
        'Quiero jugar.',
        'Necesito ayuda.',
        'Quiero ir al baño.',
        'Tengo frío.',
        'Tengo calor.',
        'Me duele aquí.',
      ]),
    );
    expect(c.needs.every((n) => n.picture is ScenePicture), isTrue);
  });

  test('las 7 emociones, con ejemplos «Estoy… porque…» y sin juzgarlas', () {
    expect(c.emotions.map((e) => e.name), [
      'Alegría',
      'Tristeza',
      'Miedo',
      'Enojo',
      'Sorpresa',
      'Tranquilidad',
      'Cansancio',
    ]);
    for (final e in c.emotions) {
      expect(e.examples, hasLength(2), reason: e.name);
      expect(e.examples.every((x) => x.contains(' porque ')), isTrue, reason: e.name);
      expect(e.reasons, hasLength(3), reason: e.name);
    }
    const judging = ['mala', 'malo', 'buena emoción', 'no debes', 'no hay que'];
    final all = [
      for (final e in c.emotions) ...e.examples,
      for (final e in c.emotions)
        for (final r in e.reasons) r.me,
    ];
    expect(all.where((x) => judging.any(x.toLowerCase().contains)), isEmpty);
    expect(c.emotions.first.examples.first, 'Estoy contento porque voy a jugar.');
    expect(c.emotions[1].examples.first, 'Estoy triste porque extraño a mi amigo.');
  });

  test('constructor: género y persona correctos en todas las combinaciones', () {
    ExpressionWho who(String id) => c.who.firstWhere((w) => w.id == id);
    EmotionInfo emo(String id) => c.emotions.firstWhere((e) => e.id == id);
    expect(
      ExpressionContent.sentence(who('yo_nino'), emo('alegria'), emo('alegria').reasons.first),
      'Yo estoy contento porque juego con mi perro.',
    );
    expect(
      ExpressionContent.sentence(who('hermana'), emo('alegria'), emo('alegria').reasons.first),
      'Mi hermana está contenta porque juega con su perro.',
    );
    expect(
      ExpressionContent.sentence(who('yo_nina'), emo('miedo'), emo('miedo').reasons.last),
      'Yo estoy asustada porque escuché un ruido fuerte.',
    );
    expect(
      ExpressionContent.sentence(who('papa'), emo('cansancio'), emo('cansancio').reasons.first),
      'Papá está cansado porque corrió mucho.',
    );
    // Todas: «Yo» con «estoy» y verbos en primera persona; los demás con «está».
    for (final w in c.who) {
      for (final e in c.emotions) {
        for (final r in e.reasons) {
          final s = ExpressionContent.sentence(w, e, r);
          expect(s, startsWith('${w.text} ${w.firstPerson ? 'estoy' : 'está'} '), reason: s);
          expect(s, contains(w.feminine ? e.feminine : e.masculine), reason: s);
          expect(s, endsWith('.'), reason: s);
          if (!w.firstPerson) expect(s.contains(' mi ') || s.contains(' mí '), isFalse, reason: s);
        }
      }
    }
  });
}
