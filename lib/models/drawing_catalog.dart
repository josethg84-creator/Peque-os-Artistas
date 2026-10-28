import 'drawing.dart';
import 'drawing_category.dart';

/// Resultado de leer el catálogo: los dibujos válidos y las incidencias
/// encontradas (entradas descartadas, archivos ausentes...).
class DrawingCatalog {
  DrawingCatalog({required List<Drawing> drawings, List<String> issues = const []})
    : drawings = List.unmodifiable(drawings),
      issues = List.unmodifiable(issues);

  static final empty = DrawingCatalog(drawings: const []);

  final List<Drawing> drawings;
  final List<String> issues;

  bool get isEmpty => drawings.isEmpty;

  List<Drawing> byCategory(DrawingCategory category) =>
      drawings.where((d) => d.category == category).toList(growable: false);

  Drawing? byId(String? id) {
    for (final d in drawings) {
      if (d.id == id) return d;
    }
    return null;
  }

  /// Dibujos fáciles, en orden de catálogo, para el botón «¡Vamos a pintar!».
  List<Drawing> get suggestions {
    final easy = drawings.where((d) => d.difficulty == Difficulty.easy).toList();
    return easy.isNotEmpty ? easy : drawings;
  }
}
