import 'drawing.dart';
import 'drawing_category.dart';

enum DrawingSort { catalog, alphabetical }

/// Criterios de búsqueda de la galería. Es inmutable y no depende de widgets,
/// así que se prueba sin interfaz.
class DrawingFilter {
  const DrawingFilter({this.query = '', this.category, this.difficulty, this.sort = DrawingSort.catalog});

  /// Texto buscado en el nombre del dibujo y de su categoría (sin distinguir
  /// mayúsculas ni tildes).
  final String query;
  final DrawingCategory? category;
  final Difficulty? difficulty;
  final DrawingSort sort;

  bool get isActive =>
      query.trim().isNotEmpty || category != null || difficulty != null || sort != DrawingSort.catalog;

  DrawingFilter copyWith({
    String? query,
    DrawingCategory? Function()? category,
    Difficulty? Function()? difficulty,
    DrawingSort? sort,
  }) => DrawingFilter(
    query: query ?? this.query,
    category: category != null ? category() : this.category,
    difficulty: difficulty != null ? difficulty() : this.difficulty,
    sort: sort ?? this.sort,
  );

  List<Drawing> apply(Iterable<Drawing> drawings) {
    final q = normalize(query);
    final result = drawings.where((d) {
      if (category != null && d.category != category) return false;
      if (difficulty != null && d.difficulty != difficulty) return false;
      if (q.isEmpty) return true;
      return normalize(d.name).contains(q) || normalize(d.category.label).contains(q);
    }).toList();
    if (sort == DrawingSort.alphabetical) {
      result.sort((a, b) {
        final byName = normalize(a.name).compareTo(normalize(b.name));
        return byName != 0 ? byName : a.id.compareTo(b.id);
      });
    }
    return result;
  }

  static const _accents = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n'};

  /// Minúsculas, sin tildes y sin espacios sobrantes: «León» → «leon».
  static String normalize(String text) {
    final lower = text.toLowerCase().trim();
    final buffer = StringBuffer();
    for (final ch in lower.split('')) {
      buffer.write(_accents[ch] ?? ch);
    }
    return buffer.toString().replaceAll(RegExp(r'\s+'), ' ');
  }
}
