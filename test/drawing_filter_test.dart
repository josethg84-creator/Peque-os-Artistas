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

  test('sin filtros devuelve los 59 en el orden del catálogo', () {
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
    expect(ids(const DrawingFilter(query: 'dinosaurio')), hasLength(8));
    expect(ids(const DrawingFilter(query: 'granja')), hasLength(7));
    expect(ids(const DrawingFilter(query: 'fruta')), hasLength(8));
  });

  test('filtro por categoría', () {
    for (final (c, n) in [
      (DrawingCategory.animals, 14),
      (DrawingCategory.farm, 7),
      (DrawingCategory.sea, 7),
      (DrawingCategory.vehicles, 6),
      (DrawingCategory.dinosaurs, 8),
      (DrawingCategory.fruits, 8),
      (DrawingCategory.fantasy, 9),
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
    expect(ids(const DrawingFilter(difficulty: Difficulty.hard)), [
      'animal_elefante',
      'animal_jirafa',
      'animal_mariposa',
      'animal_pez',
      'animal_abeja',
      'animal_oruga',
      'animal_tortuga',
      'animal_cebra',
      'granja_vaca',
      'mar_cangrejo',
      'mar_tortuga',
      'mar_caballito',
      'vehiculo_automovil',
      'vehiculo_autobus',
      'vehiculo_avion',
      'vehiculo_tren',
      'vehiculo_barco',
      'vehiculo_helicoptero',
      'dinosaurio_01',
      'dinosaurio_02',
      'dinosaurio_03',
      'dinosaurio_04',
      'dinosaurio_06',
      'dinosaurio_07',
      'dinosaurio_08',
      'fruta_fresa',
      'fruta_naranja',
      'fruta_pina',
      'fantasia_hada',
      'fantasia_hada_hongo',
      'fantasia_robot',
      'fantasia_robot_heroe',
      'fantasia_dragon',
      'fantasia_unicornio',
    ]);
  });

  test('orden alfabético (las tildes no alteran el orden)', () {
    final names = const DrawingFilter(sort: DrawingSort.alphabetical)
        .apply(catalog.drawings)
        .map((d) => d.name);
    final normalized = names.map(DrawingFilter.normalize).toList();
    expect(normalized, [...normalized]..sort());
    expect(names.first, 'Abeja');
    expect(names.take(4), ['Abeja', 'Autobús', 'Automóvil', 'Avión']);
  });

  test('filtros combinados y copyWith', () {
    var f = const DrawingFilter(category: DrawingCategory.animals, difficulty: Difficulty.medium);
    expect(ids(f), ['animal_gato', 'animal_conejo', 'animal_leon', 'animal_oso', 'animal_mono']);
    f = f.copyWith(sort: DrawingSort.alphabetical);
    expect(ids(f), ['animal_conejo', 'animal_gato', 'animal_leon', 'animal_mono', 'animal_oso']);
    f = f.copyWith(category: () => null, query: 'o');
    expect(f.category, isNull);
    expect(f.apply(catalog.drawings).every((d) => d.difficulty == Difficulty.medium), isTrue);
    expect(f.isActive, isTrue);
  });
}
