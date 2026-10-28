import '../models/drawing_category.dart';

/// Nombres de las rutas de la aplicación.
abstract final class AppRoutes {
  static const home = '/';
  static const categories = '/categorias';
  static const gallery = '/galeria';
  static const coloring = '/colorear';
  static const savedDrawings = '/mis-dibujos';
  static const activities = '/actividades';
  static const adultZone = '/adultos';
}

/// Argumento de [AppRoutes.gallery].
class GalleryArgs {
  const GalleryArgs(this.category);
  final DrawingCategory category;
}

/// Argumento de [AppRoutes.coloring].
class ColoringArgs {
  const ColoringArgs(this.drawingId);
  final String drawingId;
}

/// Argumento de [AppRoutes.adultZone]: solo se concede tras la verificación.
class AdultZoneArgs {
  const AdultZoneArgs.verified();
}
