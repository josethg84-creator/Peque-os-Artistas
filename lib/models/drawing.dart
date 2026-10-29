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
    this.thumbnail,
    this.regions,
    this.thumbnailAvailable = false,
  });

  final String id;
  final String name;
  final DrawingCategory category;

  /// Ruta del SVG con regiones rellenables (lo usa el motor de coloreado).
  final String file;

  /// Ruta de la miniatura PNG (512×512) para la galería, si el catálogo la indica.
  final String? thumbnail;
  final Difficulty difficulty;
  final String recommendedAge;
  final String description;
  final int? regions;

  /// `true` solo si el PNG de [thumbnail] existe realmente entre los assets.
  final bool thumbnailAvailable;

  /// Ruta de imagen segura para mostrar, o `null` si hay que usar un marcador.
  String? get thumbnailAsset => thumbnailAvailable ? thumbnail : null;
}
