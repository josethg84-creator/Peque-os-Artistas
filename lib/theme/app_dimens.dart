/// Medidas comunes. Los objetivos táctiles infantiles superan los 48 dp
/// recomendados por Android para compensar la precisión de los dedos pequeños.
abstract final class AppDimens {
  static const double minTouchTarget = 64;
  static const double radiusLarge = 32;
  static const double radiusMedium = 24;
  static const double gap = 16;
  static const double gapLarge = 24;
  static const double pagePadding = 20;

  /// Ancho a partir del cual se considera pantalla de tableta.
  static const double tabletBreakpoint = 720;

  /// Ancho máximo del contenido para que no se estire en tabletas.
  static const double maxContentWidth = 1100;
}
