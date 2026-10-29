import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/models/drawing.dart';
import 'package:pequenos_artistas/models/drawing_catalog.dart';
import 'package:pequenos_artistas/models/drawing_category.dart';
import 'package:pequenos_artistas/models/drawing_filter.dart';

import 'test_helpers.dart';

void main() {
  late DrawingCatalog catalog;
  setUpAll(() async => catalog = await realCatalogService().load());

  List<String> ids(DrawingFilter f) => f.apply(catalog.drawings).map((d) => d.id).toList();

  test('sin filtros devuelve los 30 en el orden del catálogo', () {
    expect(ids(const DrawingFilter()), catalog.drawings.map((d) => d.id).toList());
    expect(const DrawingFilter().isActive, isFalse);
  });

  test('búsqueda por nombre sin distinguir mayúsculas ni tildes', () {
    expect(ids(const DrawingFilter(query: 'leon')), ['animal_leon']);
    expect(ids(const DrawingFilter(query: 'AVIÓN')), ['vehiculo_avion']);
    expect(ids(const DrawingFilter(query: '  platano ')), ['fruta_platano']);
    expect(ids(const DrawingFilter(query: 'pequeño')), ['fantasia_extraterrestre']);
    expect(ids(const DrawingFilter(query: 'xyz')), isEmpty);
  });

  test('la búsqueda también encuentra por categoría', () {
    expect(ids(const DrawingFilter(query: 'dinosaurio')), hasLength(5));
    expect(ids(const DrawingFilter(query: 'fruta')), hasLength(5));
  });

  test('filtro por categoría', () {
    for (final (c, n) in [
      (DrawingCategory.animals, 10),
      (DrawingCategory.vehicles, 5),
      (DrawingCategory.dinosaurs, 5),
      (DrawingCategory.fruits, 5),
      (DrawingCategory.fantasy, 5),
    ]) {
      final result = DrawingFilter(category: c).apply(catalog.drawings);
      expect(result, hasLength(n), reason: c.label);
      expect(result.every((d) => d.category == c), isTrue);
    }
  });

  test('filtro por dificultad coincide con el catálogo', () {
    for (final level in Difficulty.values) {
      final expected = catalog.drawings.where((d) => d.difficulty == level).map((d) => d.id).toList();
      expect(ids(DrawingFilter(difficulty: level)), expected, reason: level.label);
    }
    expect(ids(const DrawingFilter(difficulty: Difficulty.hard)), ['animal_jirafa', 'fantasia_robot']);
  });

  test('orden alfabético (las tildes no alteran el orden)', () {
    final names = const DrawingFilter(sort: DrawingSort.alphabetical)
        .apply(catalog.drawings)
        .map((d) => d.name);
    final normalized = names.map(DrawingFilter.normalize).toList();
    expect(normalized, [...normalized]..sort());
    expect(names.first, 'Autobús');
    expect(names.take(3), ['Autobús', 'Automóvil', 'Avión']);
  });

  test('filtros combinados y copyWith', () {
    var f = const DrawingFilter(category: DrawingCategory.animals, difficulty: Difficulty.easy);
    expect(ids(f), ['animal_gato', 'animal_elefante', 'animal_mariposa', 'animal_pez', 'animal_tortuga']);
    f = f.copyWith(sort: DrawingSort.alphabetical);
    expect(ids(f), ['animal_elefante', 'animal_gato', 'animal_mariposa', 'animal_pez', 'animal_tortuga']);
    f = f.copyWith(category: () => null, query: 'o');
    expect(f.category, isNull);
    expect(f.apply(catalog.drawings).every((d) => d.difficulty == Difficulty.easy), isTrue);
    expect(f.isActive, isTrue);
  });
}
