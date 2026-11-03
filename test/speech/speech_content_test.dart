import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';

Map<String, dynamic> readJson(String path) =>
    jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;

void main() {
  final content = SpeechContent.parse(
    readJson(SpeechContent.wordsAsset),
    readJson(SpeechContent.phrasesAsset),
  );
  final catalogIds = {
    for (final d in readJson('assets/catalog/catalog.json')['drawings'] as List)
      (d as Map<String, dynamic>)['id'],
  };

  test('100 palabras en 10 grupos de 10, sin repetir', () {
    expect(content.categories.map((c) => c.name), [
      'Familia',
      'Animales',
      'Alimentos',
      'Juguetes',
      'Partes del cuerpo',
      'Colores',
      'Objetos del hogar',
      'Acciones',
      'Emociones',
      'Naturaleza',
    ]);
    for (final c in content.categories) {
      expect(c.words, hasLength(10), reason: c.name);
    }
    expect(content.words, hasLength(100));
    expect(content.words.map((w) => w.id).toSet(), hasLength(100));
  });

  test('cada palabra tiene su ilustración y los dibujos existen en el catálogo', () {
    // Nada se descartó al leer (el JSON y los pictogramas encajan).
    final raw = readJson(SpeechContent.wordsAsset)['categories'] as List;
    expect(raw.expand((c) => (c as Map<String, dynamic>)['words'] as List), hasLength(100));
    for (final w in content.words) {
      if (w.picture case DrawingPicture(:final drawingId)) {
        expect(catalogIds, contains(drawingId), reason: w.text);
      }
    }
    expect(content.word('perro')!.picture, isA<DrawingPicture>());
    expect(content.word('feliz')!.picture, isA<EmotionPicture>());
    expect(content.word('ojos')!.picture, isA<BodyPicture>());
    expect(content.word('rojo')!.picture, isA<SwatchPicture>());
    expect(content.word('casa')!.picture, isA<IconPicture>());
  });

  test('las frutas tienen sus colores reales (la manzana roja, el plátano amarillo)', () {
    DrawingPicture pic(String id) => content.word(id)!.picture as DrawingPicture;
    expect(pic('manzana').colorFor('manzana')!.toARGB32(), 0xFFE53935);
    expect(pic('platano').colorFor('platano')!.toARGB32(), 0xFFFFD600);
    expect(pic('uvas').colorFor('uva_7')!.toARGB32(), 0xFF8E44AD); // «uva_*» vale para todas
    expect(pic('uvas').colorFor('fondo'), isNull); // el fondo queda blanco
    expect(pic('perro').colors, isEmpty); // los animales, con colores alegres
  });

  test('las 12 frases útiles, con sus palabras sin puntuación', () {
    expect(content.phrases.map((p) => p.text), [
      'Quiero agua.',
      'Tengo hambre.',
      'Tengo sueño.',
      'Quiero jugar.',
      'Dame la pelota.',
      'Necesito ayuda.',
      'Estoy feliz.',
      'Me duele aquí.',
      'Vamos a casa.',
      'Gracias, mamá.',
      'Hola, ¿cómo estás?',
      'Buenas noches.',
    ]);
    expect(content.phrases[10].words, ['Hola', 'cómo', 'estás']);
    expect(content.phrases[9].words, ['Gracias', 'mamá']);
  });

  test('el contenido se amplía desde el JSON y lo que no se entiende se descarta', () {
    final c = SpeechContent.parse(
      {
        'categories': [
          {
            'id': 'nuevo',
            'name': 'Nuevo',
            'color': '#123456',
            'icon': 'star',
            'words': [
              {
                'id': 'a',
                'text': 'uno',
                'picture': {'icon': 'sun'},
              },
              {
                'id': 'a',
                'text': 'repetido',
                'picture': {'icon': 'sun'},
              },
              {
                'id': 'b',
                'text': 'sin dibujo',
                'picture': {'icon': 'no-existe'},
              },
              {
                'id': 'c',
                'text': 'imagen propia',
                'picture': {'image': 'assets/speech/img/c.png'},
              },
            ],
          },
          {'id': 'vacio', 'name': 'Vacío', 'words': []},
        ],
      },
      {
        'phrases': [
          {
            'id': 'p',
            'text': '  ¡Hola!  ',
            'picture': {'emotion': 'feliz'},
          },
          {
            'id': 'q',
            'text': 'Sin imagen',
            'picture': {'emotion': 'inventada'},
          },
        ],
      },
    );
    expect(c.categories.single.words.map((w) => w.id), ['a', 'c']);
    expect(c.categories.single.color.toARGB32(), 0xFF123456);
    expect(c.word('c')!.picture, isA<ImagePicture>());
    expect(c.phrases.single.text, '¡Hola!');
  });
}
