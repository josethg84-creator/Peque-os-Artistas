import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/aac/aac_catalog.dart';
import 'package:pequenos_artistas/aac/phrase_composer.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

void main() {
  final raw = jsonDecode(File(AacCatalog.asset).readAsStringSync()) as Map<String, dynamic>;
  final catalog = AacCatalog.parse(raw);
  Pictogram p(String id) => catalog.byId(id)!;
  String say(List<String> ids, {bool feminine = false}) =>
      composePhrase([for (final id in ids) p(id)], feminine: feminine);

  group('catálogo de pictogramas', () {
    test('al menos 150 conceptos y todos se cargan (ninguno se descarta)', () {
      expect((raw['pictograms'] as List).length, greaterThanOrEqualTo(150));
      expect(catalog.pictograms, hasLength((raw['pictograms'] as List).length));
      expect(catalog.pictograms.map((x) => x.id).toSet(), hasLength(catalog.pictograms.length));
    });

    test('las 10 categorías pedidas, cada una con contenido', () {
      expect(catalog.categories.map((c) => c.name), [
        'Necesidades básicas',
        'Comida y bebida',
        'Emociones',
        'Familia y personas',
        'Juegos',
        'Actividades',
        'Lugares',
        'Salud y bienestar',
        'Preguntas y respuestas',
        'Palabras esenciales',
      ]);
      for (final c in catalog.categories) {
        expect(catalog.inCategory(c.id).length, greaterThanOrEqualTo(12), reason: c.name);
      }
    });

    test('cada pictograma tiene todos sus campos y lo que se ve es lo que se dice', () {
      final orders = <int>{};
      for (final raw in (raw['pictograms'] as List).cast<Map<String, dynamic>>()) {
        for (final key in [
          'id',
          'category',
          'text',
          'speech',
          'picture',
          'color',
          'order',
          'active',
          'related',
          'kind',
        ]) {
          expect(raw.containsKey(key), isTrue, reason: '${raw['id']}.$key');
        }
        expect(raw['speech'], raw['text'], reason: raw['id'] as String);
        expect(orders.add(raw['order'] as int), isTrue);
      }
      for (final x in catalog.pictograms) {
        expect(catalog.category(x.category), isNotNull, reason: x.id);
        expect(x.color, catalog.category(x.category)!.color, reason: x.id);
        for (final r in x.related) {
          expect(catalog.byId(r), isNotNull, reason: '${x.id} → $r');
        }
        expect(x.label(), isNot(contains('{')));
        expect(x.label(feminine: true), isNot(contains('{')));
      }
    });

    test('las ilustraciones existen (dibujos del catálogo) y no se repiten en las frases clave', () {
      for (final x in catalog.pictograms) {
        if (x.picture case DrawingPicture(:final drawingId)) {
          final found = Directory('assets/drawings')
              .listSync(recursive: true)
              .any((f) => f.path.endsWith('/$drawingId.svg'));
          expect(found, isTrue, reason: x.id);
        }
      }
    });

    test('tablero rápido: las 12 palabras esenciales', () {
      expect(catalog.resolve(catalog.quick).map((x) => x.label()), [
        'Sí',
        'No',
        'Ayuda',
        'Agua',
        'Baño',
        'Comer',
        'Dolor',
        'Más',
        'Terminé',
        'Para',
        'Quiero',
        'No quiero',
      ]);
    });

    test('las tarjetas del ejemplo', () {
      final labels = catalog.pictograms.map((x) => x.label()).toSet();
      for (final t in [
        'Quiero agua.',
        'Tengo hambre.',
        'Necesito ayuda.',
        'Quiero descansar.',
        'Tengo sueño.',
        'Me duele aquí.',
        'Quiero ir al baño.',
        'Estoy feliz.',
        'Estoy triste.',
        'No entiendo.',
      ]) {
        expect(labels, contains(t));
      }
      expect(p('estoy_cansado').label(feminine: true), 'Estoy cansada.');
      expect(catalog.feelings.length, greaterThanOrEqualTo(12));
      expect(catalog.learn.length, greaterThanOrEqualTo(10));
    });

    test('datos raros se descartan sin romper el tablero', () {
      final c = AacCatalog.parse({
        'categories': [
          {'id': 'x', 'name': 'X', 'color': '#FF0000', 'icon': 'star'},
        ],
        'pictograms': [
          {
            'id': 'a',
            'category': 'x',
            'text': 'Hola.',
            'speech': 'Otra cosa',
            'picture': {'icon': 'star'},
          },
          {
            'id': 'a',
            'category': 'x',
            'text': 'Repetido',
            'picture': {'icon': 'star'},
          },
          {
            'id': 'b',
            'category': 'x',
            'text': 'Sin dibujo',
            'picture': {'icon': 'no_existe'},
          },
        ],
        'boards': {
          'quick': ['a', 'zzz'],
        },
      });
      expect(c.pictograms.map((x) => x.id), ['a']);
      expect(c.byId('a')!.speech, 'Hola.', reason: 'la voz dice lo que se ve');
      expect(c.quick, ['a']);
    });
  });

  group('constructor de frases', () {
    test('los ejemplos pedidos', () {
      expect(say(['yo', 'quiero', 'agua']), 'Yo quiero agua.');
      expect(say(['quiero', 'jugar', 'con', 'mi', 'perro']), 'Quiero jugar con mi perro.');
      expect(say(['estoy', 'feliz']), 'Estoy feliz.');
      expect(say(['no_quiero', 'comer']), 'No quiero comer.');
      expect(say(['necesito', 'ayuda']), 'Necesito ayuda.');
      expect(say(['me_duele', 'cabeza']), 'Me duele la cabeza.');
      expect(say(['quiero', 'ir', 'parque']), 'Quiero ir al parque.');
      expect(say(['quiero', 'ir', 'a', 'parque']), 'Quiero ir al parque.');
    });

    test('artículos, contracciones, género y preguntas', () {
      expect(say(['vamos', 'casa']), 'Vamos a casa.');
      expect(say(['vamos', 'playa']), 'Vamos a la playa.');
      expect(say(['quiero', 'pelota']), 'Quiero la pelota.');
      expect(say(['quiero', 'galleta']), 'Quiero una galleta.');
      expect(say(['me_duele', 'orejas']), 'Me duele las orejas.', reason: 'no se corrige al niño');
      expect(say(['estoy', 'cansado'], feminine: true), 'Estoy cansada.');
      expect(say(['donde', 'mama']), '¿Dónde mamá?');
      expect(say(['quiero_agua']), 'Quiero agua.');
      expect(say(['puedo_jugar']), '¿Puedo jugar?');
      expect(say(['mas', 'agua']), 'Más agua.');
      expect(say(['yo', 'quiero', 'agua', 'y', 'pan']), 'Yo quiero agua y pan.');
      expect(composePhrase(const []), '');
    });

    test('cualquier combinación da una frase con mayúscula y punto', () {
      final all = catalog.pictograms;
      for (var i = 0; i < all.length; i++) {
        final s = composePhrase([all[i], all[(i * 7) % all.length], all[(i * 13) % all.length]]);
        expect(s, matches(RegExp(r'^[¿¡]?[A-ZÁÉÍÓÚÑ].*[.!?]$')), reason: s);
        expect(s, isNot(contains('  ')));
        expect(RegExp(r'\ba el\b').hasMatch(s), isFalse, reason: s);
      }
    });

    test('sugerencias: relacionadas con la última pieza, sin limitar la elección', () {
      expect(suggestNext(catalog, const []).map((x) => x.id), containsAll(['yo', 'quiero', 'necesito']));
      expect(suggestNext(catalog, [p('yo')]).map((x) => x.id), contains('quiero'));
      expect(suggestNext(catalog, [p('me_duele')]).map((x) => x.id), contains('cabeza'));
      expect(suggestNext(catalog, [p('quiero')]).length, lessThanOrEqualTo(8));
    });
  });
}
