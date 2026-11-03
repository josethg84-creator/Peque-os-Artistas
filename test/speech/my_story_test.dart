import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final c = MyStoryContent.fromJson(
    jsonDecode(File(SpeechContent.myStoryAsset).readAsStringSync()) as Map<String, dynamic>,
  );
  StoryNoun ch(String id) => c.characters.firstWhere((x) => x.id == id);
  StoryNoun ob(String id) => c.objects.firstWhere((x) => x.id == id);
  StoryPlace pl(String id) => c.places.firstWhere((x) => x.id == id);
  StoryAction ac(String id) => c.actions.firstWhere((x) => x.id == id);
  StoryEnding en(String id) => c.endings.firstWhere((x) => x.id == id);

  test('el ejemplo: «Un conejo fue al bosque a buscar una zanahoria.»', () {
    final s = MyStory(
      character: ch('conejo'),
      place: pl('bosque'),
      action: ac('buscar'),
      object: ob('zanahoria'),
      ending: en('feliz'),
    );
    expect(s.firstSentence, 'Un conejo fue al bosque a buscar una zanahoria.');
    expect(s.text, 'Un conejo fue al bosque a buscar una zanahoria. ¡Y el conejo se puso muy contento!');
  });

  test('concordancia: género, «a la», «con» y «lo/la»', () {
    final s = MyStory(
      character: ch('tortuga'),
      place: pl('playa'),
      action: ac('jugar'),
      object: ob('pelota'),
      ending: en('compartir'),
    );
    expect(
      s.text,
      'Una tortuga fue a la playa a jugar con una pelota. Después, la tortuga la compartió con sus amigos.',
    );
    expect(ac('jugar').question, '¿Con qué fue a jugar?');
    final t = MyStory(
      character: ch('nina'),
      place: pl('jardin'),
      action: ac('plantar'),
      object: ob('semilla'),
      ending: en('dormir'),
    );
    expect(
      t.text,
      'Una niña fue al jardín a plantar una semilla. Por la noche, la niña durmió muy contenta.',
    );
    final u = MyStory(
      character: ch('dragon'),
      place: pl('cocina'),
      action: ac('comer'),
      object: ob('pastel'),
      ending: en('compartir'),
    );
    expect(u.lastSentence, 'Después, el dragón lo compartió con sus amigos.');
  });

  test('todas las combinaciones posibles son oraciones bien formadas', () {
    var n = 0;
    final article = RegExp(r'\b(un|una|el|la)\s+(\S+)');
    final fem = {
      for (final x in [...c.characters, ...c.objects]) x.noun: x.feminine,
    };
    for (final character in c.characters) {
      for (final place in c.places) {
        for (final action in c.actions) {
          for (final object in c.objectsFor(action)) {
            for (final ending in c.endings) {
              final s = MyStory(
                character: character,
                place: place,
                action: action,
                object: object,
                ending: ending,
              );
              final text = s.text;
              expect(text, matches(RegExp(r'^[A-ZÁÉÍÓÚÑ¡¿]')), reason: text);
              expect(text, isNot(contains('  ')));
              expect(text, isNot(contains('{')));
              expect(text, isNot(contains('a el ')), reason: text);
              expect(text, isNot(contains('de el ')), reason: text);
              expect(s.firstSentence, endsWith('.'));
              expect(s.lastSentence, matches(RegExp(r'[.!]$')));
              // Cada artículo concuerda con su sustantivo.
              for (final m in article.allMatches(text.toLowerCase())) {
                final noun = m.group(2)!.replaceAll(RegExp(r'[.!,]'), '');
                if (fem[noun] case final f?) {
                  expect(m.group(1) == 'una' || m.group(1) == 'la', f, reason: '$text ($noun)');
                }
              }
              if (text.contains('contento') || text.contains('contenta')) {
                expect(text.contains('contenta'), character.feminine, reason: text);
              }
              n++;
            }
          }
        }
      }
    }
    expect(n, greaterThan(1000));
  });

  test('se va contando mientras se elige', () {
    expect(storySoFar(character: ch('conejo')), 'Un conejo…');
    expect(
      storySoFar(character: ch('conejo'), place: pl('bosque'), action: ac('jugar')),
      'Un conejo fue al bosque a jugar con…',
    );
    expect(
      storySoFar(character: ch('oso'), place: pl('escuela'), action: ac('mirar'), object: ob('estrella')),
      'Un oso fue a la escuela a mirar una estrella.',
    );
    // Solo se ofrecen objetos que tienen sentido con la acción.
    expect(c.objectsFor(ac('comer')).map((o) => o.kind).toSet(), {'comida'});
    expect(c.objectsFor(ac('jugar')).map((o) => o.kind).toSet(), {'juguete'});
  });
}
