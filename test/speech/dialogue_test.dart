import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final json = jsonDecode(File(SpeechContent.conversationsAsset).readAsStringSync()) as Map<String, dynamic>;
  final parsed = parseConversations(json);

  final guided = parsed.conversations.where((c) => c.category != 'elige').toList();

  test('12 categorías guiadas con 3 conversaciones cada una y «Tú eliges», todas válidas', () {
    expect(parsed.categories.map((c) => c.name), [
      'Saludos y despedidas',
      'Mi familia',
      'Mis emociones',
      'Mis juguetes',
      'Mis alimentos',
      'Mis animales favoritos',
      'Mis actividades diarias',
      'Mi escuela',
      'Mis amigos',
      'Pedir ayuda',
      'Expresar necesidades',
      'Describir objetos',
      'Tú eliges',
    ]);
    // Ninguna se descartó por errores de contenido.
    expect((json['conversations'] as List), hasLength(40));
    expect(parsed.conversations, hasLength(40));
    for (final c in parsed.categories.where((c) => c.id != 'elige')) {
      expect(parsed.conversations.where((x) => x.category == c.id), hasLength(3), reason: c.name);
    }
    for (final c in guided) {
      expect(c.validate(), isEmpty, reason: c.id);
      for (final n in c.nodes.values) {
        expect(n.options.length, inInclusiveRange(3, 4), reason: '${c.id}: ${n.lolo}');
      }
    }
  });

  test('cualquier camino termina en 3 a 5 intercambios', () {
    for (final c in guided) {
      // Recorre todos los caminos posibles.
      void walk(String? node, int depth) {
        if (node == null) {
          expect(depth, inInclusiveRange(1, 5), reason: c.id);
          return;
        }
        expect(depth, lessThan(5), reason: '${c.id}: camino demasiado largo');
        for (final o in c.nodes[node]!.options) {
          walk(o.next, depth + 1);
        }
      }

      walk(c.start, 0);
      // Las conversaciones sin ramas tienen al menos 3 preguntas.
      if (c.nodes.length == 3) {
        var s = DialogueSession(c);
        while (!s.finished) {
          s.choose(0);
        }
        expect(s.exchanges, hasLength(3), reason: c.id);
        s = DialogueSession(c);
        expect(s.current!.lolo, c.nodes[c.start]!.lolo);
      }
    }
  });

  test('el motor sigue las ramas, corta a los 5 intercambios y se puede terminar', () {
    final hola = parsed.conversations.firstWhere((c) => c.id == 'saludo_hola');
    var s = DialogueSession(hola);
    expect(s.current!.lolo, '¡Hola! ¿Cómo estás hoy?');
    // «Estoy triste» lleva a la rama de consuelo y luego vuelve a la pregunta 2.
    final reply = s.choose(2);
    expect(reply, 'Gracias por decírmelo. Aquí estoy contigo.');
    expect(s.current!.lolo, '¿Quieres que hagamos algo juntos para sentirnos mejor?');
    s.choose(0);
    expect(s.current!.lolo, '¿Quieres jugar conmigo?');
    s.choose(0);
    s.choose(0);
    expect(s.finished, isTrue);
    expect(s.exchanges.map((e) => e.answer.text), [
      'Estoy triste.',
      'Un abrazo.',
      '¡Sí, quiero jugar!',
      '¡Adiós, Lolo!',
    ]);
    expect(s.endedEarly, isFalse);

    // Contenido con un bucle: el motor corta igual a los 5.
    final loop = Conversation.fromJson({
      'id': 'bucle',
      'category': 'x',
      'title': 'Bucle',
      'picture': {'lolo': true},
      'start': 'a',
      'nodes': {
        'a': {
          'lolo': '¿Otra vez?',
          'options': [
            {
              'text': 'Sí',
              'picture': {'icon': 'star'},
              'reply': '¡Vale!',
              'next': 'a',
            },
            {
              'text': 'No',
              'picture': {'icon': 'star'},
              'reply': 'Adiós',
            },
          ],
        },
      },
    })!;
    s = DialogueSession(loop);
    for (var i = 0; i < 5; i++) {
      s.choose(0);
    }
    expect(s.finished, isTrue);
    expect(s.exchanges, hasLength(5));

    s = DialogueSession(hola)..choose(0);
    s.end();
    expect(s.finished && s.endedEarly, isTrue);
  });

  test('una conversación con un salto a un nodo que no existe se descarta', () {
    final bad = {
      'id': 'mala',
      'category': 'x',
      'title': 'Mala',
      'picture': {'lolo': true},
      'start': 'a',
      'nodes': {
        'a': {
          'lolo': '¿Hola?',
          'options': [
            {
              'text': 'Sí',
              'picture': {'icon': 'star'},
              'reply': 'Bien',
              'next': 'no_existe',
            },
            {
              'text': 'No',
              'picture': {'icon': 'star'},
              'reply': 'Bien',
            },
          ],
        },
      },
    };
    expect(Conversation.fromJson(bad), isNull);
  });

  group('conversaciones adaptativas (fase 4)', () {
    final adaptive = parsed.conversations.where((c) => c.category == 'elige').toList();

    test('la pregunta siguiente depende de lo elegido y termina con una oración', () {
      final animal = adaptive.firstWhere((c) => c.id == 'elige_animal');
      var s = DialogueSession(animal);
      expect(s.current!.lolo, '¿Qué animal te gusta?');
      int pick(String text) => s.current!.options.indexWhere((o) => o.text == text);
      s.choose(pick('El perro.'));
      expect(s.current!.lolo, '¿Qué hace el perro?');
      expect(s.current!.options.map((o) => o.text), ['Corre.', 'Duerme.', 'Come.']);
      expect(s.choose(pick('Corre.')), '¡El perro corre!');
      expect(s.current!.lolo, '¿Quieres escuchar la oración?');
      expect(s.choose(pick('Sí, quiero escucharla.')), 'El perro corre por el parque.');
      expect(s.finished, isTrue);

      // Otro camino, otra pregunta.
      s = DialogueSession(animal);
      s.choose(pick('El pájaro.'));
      expect(s.current!.lolo, '¿Qué hace el pájaro?');
      expect(s.current!.options.map((o) => o.text), contains('Vuela.'));
    });

    test('todas las combinaciones llevan a una oración bien escrita y el bucle se corta', () {
      for (final c in adaptive) {
        expect(c.validate(), isEmpty, reason: c.id);
        for (final first in c.nodes[c.start]!.options) {
          for (final second in c.nodes[first.next]!.options) {
            final ask = c.nodes[second.next]!;
            final yes = ask.options.first;
            expect(yes.next, isNull);
            expect(yes.reply, matches(RegExp(r'^[A-ZÁÉÍÓÚ].*\.$')), reason: yes.reply);
            expect(ask.options.last.next, c.start, reason: 'elegir otra vez');
          }
        }
        // Eligiendo «otra vez» siempre, la sesión se corta a los 5 intercambios.
        final s = DialogueSession(c);
        while (!s.finished) {
          s.choose(s.current!.options.length - 1);
        }
        expect(s.exchanges, hasLength(5));
      }
    });
  });
}
