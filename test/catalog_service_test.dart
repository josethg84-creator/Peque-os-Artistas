import 'dart:io';

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/models/drawing.dart';
import 'package:pequenos_artistas/models/drawing_category.dart';
import 'package:pequenos_artistas/services/catalog_service.dart';

import 'test_helpers.dart';

String catalogWith(List<Object?> drawings) => jsonEncode({'drawings': drawings});

Map<String, Object?> entry(String id, {String category = 'animales', String? thumbnail}) => {
  'id': id,
  'name': 'Nombre $id',
  'category': category,
  'file': 'assets/drawings/$id.svg',
  'thumbnail': thumbnail ?? 'assets/thumbnails/$id.png',
  'difficulty': 'facil',
  'recommended_age': '4-5',
  'description': 'Descripción',
};

void main() {
  group('Catálogo real de la Fase 1', () {
    test('tiene 30 dibujos válidos, sin incidencias y con todos sus archivos', () async {
      final catalog = await realCatalogService().load();
      expect(catalog.issues, isEmpty);
      expect(catalog.drawings, hasLength(30));
      expect(catalog.drawings.every((d) => d.thumbnailAvailable), isTrue);
      final assets = diskAssets();
      for (final d in catalog.drawings) {
        expect(assets, contains(d.file));
        expect(assets, contains(d.thumbnail));
      }
    });

    test('reparte 10/5/5/5/5 entre las cinco categorías', () async {
      final catalog = await realCatalogService().load();
      expect(catalog.byCategory(DrawingCategory.animals), hasLength(10));
      for (final c in [
        DrawingCategory.vehicles,
        DrawingCategory.dinosaurs,
        DrawingCategory.fruits,
        DrawingCategory.fantasy,
      ]) {
        expect(catalog.byCategory(c), hasLength(5), reason: c.label);
      }
    });

    test('las portadas de las categorías existen en el catálogo', () async {
      final catalog = await realCatalogService().load();
      for (final c in DrawingCategory.values) {
        expect(catalog.byId(c.coverDrawingId), isNotNull, reason: c.label);
      }
    });

    test('las rutas del catálogo están declaradas en pubspec.yaml', () {
      // Los recursos se declaran por carpeta: comprobamos cada carpeta usada.
      final pubspec = File('pubspec.yaml').readAsStringSync();
      final data = jsonDecode(realCatalogJson()) as Map<String, dynamic>;
      for (final d in (data['drawings'] as List).cast<Map<String, dynamic>>()) {
        for (final key in ['file', 'thumbnail']) {
          final path = d[key] as String;
          final folder = path.substring(0, path.lastIndexOf('/') + 1);
          expect(pubspec, contains('- $folder'), reason: path);
        }
      }
      expect(pubspec, contains('- ${CatalogService.catalogPath}'));
    });
  });

  group('Lectura robusta', () {
    test('marca la miniatura ausente sin descartar el dibujo', () {
      final catalog = CatalogService.parse(catalogWith([entry('a')]), {'assets/drawings/a.svg'});
      expect(catalog.drawings.single.thumbnailAvailable, isFalse);
      expect(catalog.drawings.single.thumbnailAsset, isNull);
      expect(catalog.issues.single, contains('falta la miniatura'));
    });

    test('descarta dibujos cuyo SVG no existe', () {
      final catalog = CatalogService.parse(catalogWith([entry('a')]), {'assets/thumbnails/a.png'});
      expect(catalog.drawings, isEmpty);
      expect(catalog.issues.single, contains('no existe'));
    });

    test('descarta categorías desconocidas, ids duplicados y campos ausentes', () {
      final assets = {'assets/drawings/a.svg', 'assets/drawings/b.svg', 'assets/thumbnails/a.png'};
      final catalog = CatalogService.parse(
        catalogWith([
          entry('a'),
          entry('a'),
          entry('b', category: 'planetas'),
          {'id': 'c'},
          'texto suelto',
        ]),
        assets,
      );
      expect(catalog.drawings.map((d) => d.id), ['a']);
      expect(catalog.issues, hasLength(4));
    });

    test('rechaza rutas inseguras aunque existan', () {
      final e = entry('a')..['file'] = 'assets/../secreto.svg';
      final catalog = CatalogService.parse(catalogWith([e]), {'assets/../secreto.svg'});
      expect(catalog.drawings, isEmpty);
    });

    test('un JSON inválido produce un catálogo vacío con la incidencia', () {
      final catalog = CatalogService.parse('{ no es json', {});
      expect(catalog.isEmpty, isTrue);
      expect(catalog.issues.single, contains('JSON'));
    });

    test('si falta el archivo del catálogo no lanza excepción', () async {
      final service = CatalogService(bundle: MemoryBundle({}), assetLister: () async => {});
      final catalog = await service.load();
      expect(catalog.isEmpty, isTrue);
      expect(catalog.issues.single, contains('No se encontró'));
    });

    test('la dificultad desconocida se interpreta como fácil', () {
      final e = entry('a')..['difficulty'] = '???';
      final catalog = CatalogService.parse(catalogWith([e]), {'assets/drawings/a.svg'});
      expect(catalog.drawings.single.difficulty, Difficulty.easy);
    });
  });
}
