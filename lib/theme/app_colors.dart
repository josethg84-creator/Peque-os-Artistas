import 'package:flutter/material.dart';

/// Paleta de la interfaz: colores alegres sobre fondos claros.
abstract final class AppColors {
  static const background = Color(0xFFFFF8EC);
  static const surface = Color(0xFFFFFFFF);
  static const ink = Color(0xFF3B3355);
  static const inkSoft = Color(0xFF6E6787);

  static const coral = Color(0xFFFF7A59);
  static const sky = Color(0xFF4FB3FF);
  static const sun = Color(0xFFFFC93C);
  static const leaf = Color(0xFF5CC689);
  static const grape = Color(0xFF9B7BEA);
  static const berry = Color(0xFFFF6B8B);
  static const ocean = Color(0xFF26B5C7);

  /// Colores sobrios de la zona para adultos (distinta del área infantil).
  static const adultBackground = Color(0xFFF2F3F5);
  static const adultAccent = Color(0xFF4A5568);

  /// Color de texto legible sobre [background]: blanco si contrasta al menos
  /// 3:1 (texto grande, WCAG); si no, la tinta oscura de la app.
  static Color onColor(Color background) {
    double l(Color c) => c.computeLuminance();
    final white = 1.05 / (l(background) + 0.05);
    return white >= 3 ? Colors.white : ink;
  }

  /// [color] oscurecido lo justo para que un texto blanco grande contraste
  /// al menos 3:1 (WCAG). Si ya contrasta, se devuelve igual.
  static Color forWhiteText(Color color) {
    var c = color;
    for (var i = 0; i < 20 && 1.05 / (c.computeLuminance() + 0.05) < 3; i++) {
      c = Color.lerp(c, Colors.black, 0.05)!;
    }
    return c;
  }
}
