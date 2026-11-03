import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final json = jsonDecode(File(SpeechContent.conversationsAsset).readAsStringSync()) as Map<String, dynamic>;
  final parsed = parseConversations(json);

  test('12 categorías con 3 conversaciones cada una, todas válidas', () {
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
    ]);
    // Ninguna se descartó por errores de contenido.
    expect((json['conversations'] as List), hasLength(36));
    expect(parsed.conversations, hasLength(36));
    for (final c in parsed.categories) {
      expect(parsed.conversations.where((x) => x.category == c.id), hasLength(3), reason: c.name);
    }
    for (final c in parsed.conversations) {
      expect(c.validate(), isEmpty, reason: c.id);
      for (final n in c.nodes.values) {
        expect(n.options.length, inInclusiveRange(3, 4), reason: '${c.id}: ${n.lolo}');
      }
    }
  });

  test('cualquier camino termina en 3 a 5 intercambios', () {
    for (final c in parsed.conversations) {
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
}
