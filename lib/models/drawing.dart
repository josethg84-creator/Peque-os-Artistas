import 'drawing_category.dart';

enum Difficulty {
  easy('facil', 'Fácil', 1),
  medium('media', 'Media', 2),
  hard('dificil', 'Difícil', 3);

  const Difficulty(this.id, this.label, this.stars);

  final String id;
  final String label;
  final int stars;

  static Difficulty? fromId(String? id) {
    for (final d in values) {
      if (d.id == id) return d;
    }
    return null;
  }
}

/// Un dibujo del catálogo (`assets/catalog/catalog.json`).
class Drawing {
  const Drawing({
    required this.id,
    required this.name,
    required this.category,
    required this.file,
    required this.difficulty,
    required this.recommendedAge,
    required this.description,
    this.preview,
    this.regions,
    this.previewAvailable = false,
  });

  final String id;
  final String name;
  final DrawingCategory category;

  /// Ruta del SVG con regiones rellenables (lo usará el motor de la Fase 3).
  final String file;

  /// Ruta del PNG de vista previa, si el catálogo la indica.
  final String? preview;
  final Difficulty difficulty;
  final String recommendedAge;
  final String description;
  final int? regions;

  /// `true` solo si el PNG de [preview] existe realmente entre los assets.
  final bool previewAvailable;

  /// Ruta de imagen segura para mostrar, o `null` si hay que usar un marcador.
  String? get previewAsset => previewAvailable ? preview : null;
}
