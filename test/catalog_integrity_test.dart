import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter_test/flutter_test.dart';

/// Comprueba el archivo real `assets/catalog/catalog.json` de la colección.
void main() {
  final data = jsonDecode(File('assets/catalog/catalog.json').readAsStringSync()) as Map<String, dynamic>;
  final drawings = (data['drawings'] as List).cast<Map<String, dynamic>>();

  const required = [
    'id',
    'name',
    'category',
    'file',
    'thumbnail',
    'difficulty',
    'recommended_age',
    'description',
  ];
  const expected = {
    'animales': [
      'Gato',
      'Perro',
      'Conejo',
      'León',
      'Elefante',
      'Jirafa',
      'Oso',
      'Mariposa',
      'Pez',
      'Tortuga',
    ],
    'vehiculos': ['Automóvil', 'Autobús', 'Avión', 'Tren', 'Barco'],
    'frutas': ['Manzana', 'Plátano', 'Fresa', 'Naranja', 'Uvas'],
    'fantasia': ['Hada', 'Robot amigable', 'Dragón sonriente', 'Unicornio', 'Pequeño extraterrestre'],
  };
  const folders = {
    'animales': 'animals',
    'vehiculos': 'vehicles',
    'dinosaurios': 'dinosaurs',
    'frutas': 'fruits',
    'fantasia': 'fantasy',
  };

  List<String> namesOf(String category) => [
    for (final d in drawings)
      if (d['category'] == category) d['name'] as String,
  ];

  test('hay exactamente 30 entradas', () => expect(drawings, hasLength(30)));

  test('las cinco categorías tienen 10, 5, 5, 5 y 5 dibujos', () {
    final counts = <String, int>{};
    for (final d in drawings) {
      counts[d['category'] as String] = (counts[d['category']] ?? 0) + 1;
    }
    expect(counts, {'animales': 10, 'vehiculos': 5, 'dinosaurios': 5, 'frutas': 5, 'fantasia': 5});
  });

  test('cada categoría contiene exactamente los dibujos pedidos', () {
    expected.forEach(
      (category, names) => expect(namesOf(category), unorderedEquals(names), reason: category),
    );
    // Cinco dinosaurios distintos.
    expect(namesOf('dinosaurios').toSet(), hasLength(5));
  });

  test('no hay campos obligatorios vacíos', () {
    for (final d in drawings) {
      for (final key in required) {
        final value = d[key];
        expect(value is String && value.trim().isNotEmpty, isTrue, reason: '${d['id']}.$key');
      }
      expect(d['difficulty'], isIn(['facil', 'media', 'dificil']), reason: d['id'] as String);
      expect(d['recommended_age'], matches(RegExp(r'^\d-\d$')), reason: d['id'] as String);
      expect(d['regions'], isA<int>(), reason: d['id'] as String);
    }
  });

  test('ids, nombres, archivos y miniaturas no se repiten', () {
    for (final key in ['id', 'name', 'file', 'thumbnail']) {
      final values = drawings.map((d) => d[key]).toList();
      expect(values.toSet(), hasLength(values.length), reason: key);
    }
  });

  test('rutas relativas, estables y coherentes con el id y la categoría', () {
    for (final d in drawings) {
      final id = d['id'] as String;
      expect(id, matches(RegExp(r'^[a-z0-9_]+$')));
      expect(d['file'], 'assets/drawings/${folders[d['category']]}/$id.svg');
      expect(d['thumbnail'], 'assets/thumbnails/$id.png');
    }
  });

  test('todos los archivos existen y no hay recursos duplicados por contenido', () {
    for (final key in ['file', 'thumbnail']) {
      final hashes = <String>{};
      for (final d in drawings) {
        final file = File(d[key] as String);
        expect(file.existsSync(), isTrue, reason: file.path);
        expect(hashes.add(base64Encode(file.readAsBytesSync())), isTrue, reason: 'duplicado: ${file.path}');
      }
    }
    // No hay SVG ni miniaturas sueltos fuera del catálogo.
    final listed = {for (final d in drawings) d['file'], for (final d in drawings) d['thumbnail']};
    final onDisk = [
      ...Directory('assets/drawings').listSync(recursive: true).whereType<File>(),
      ...Directory('assets/thumbnails').listSync().whereType<File>(),
    ].map((f) => f.path.replaceAll('\\', '/'));
    expect(onDisk.where((p) => !listed.contains(p)), isEmpty);
  });

  test('la dificultad es coherente con el número de zonas', () {
    for (final d in drawings) {
      final regions = d['regions'] as int;
      final level = regions <= 12 ? 'facil' : (regions <= 20 ? 'media' : 'dificil');
      expect(d['difficulty'], level, reason: '${d['id']} ($regions zonas)');
    }
  });

  testWidgets('las 30 miniaturas se pueden decodificar y son cuadradas de 512 px', (tester) async {
    await tester.runAsync(() async {
      for (final d in drawings) {
        final bytes = File(d['thumbnail'] as String).readAsBytesSync();
        final codec = await ui.instantiateImageCodec(bytes);
        final frame = await codec.getNextFrame();
        expect(frame.image.width, 512, reason: d['id'] as String);
        expect(frame.image.height, 512, reason: d['id'] as String);
        frame.image.dispose();
      }
    });
  });
}
