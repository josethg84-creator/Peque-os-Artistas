import 'package:flutter/material.dart';

/// Un color de la paleta con su nombre (para accesibilidad y tooltips).
class PaletteColor {
  const PaletteColor(this.name, this.color, {this.restoresOriginal = false});
  final String name;
  final Color color;

  /// El blanco devuelve la región a su estado original (sin pintar).
  final bool restoresOriginal;
}

/// Paleta infantil de 24 colores en orden de arcoíris: vivos y fáciles de
/// distinguir, con tonos claros y oscuros de los principales, y el blanco para
/// dejar una zona como estaba. Los 13 colores de la primera paleta conservan su
/// valor exacto, así que los dibujos guardados se ven igual.
const kidPalette = <PaletteColor>[
  PaletteColor('Rojo', Color(0xFFE53935)),
  PaletteColor('Granate', Color(0xFF8E1B2E)),
  PaletteColor('Coral', Color(0xFFFF7F66)),
  PaletteColor('Naranja', Color(0xFFFF8F00)),
  PaletteColor('Melocotón', Color(0xFFFFC48C)),
  PaletteColor('Amarillo', Color(0xFFFFD600)),
  PaletteColor('Amarillo claro', Color(0xFFFFF59D)),
  PaletteColor('Lima', Color(0xFFC6E03A)),
  PaletteColor('Verde claro', Color(0xFF7CB342)),
  PaletteColor('Verde', Color(0xFF2E7D32)),
  PaletteColor('Menta', Color(0xFF80DEB8)),
  PaletteColor('Turquesa', Color(0xFF1FB5A8)),
  PaletteColor('Celeste', Color(0xFF29B6F6)),
  PaletteColor('Azul', Color(0xFF1E57C8)),
  PaletteColor('Azul marino', Color(0xFF1A2A6C)),
  PaletteColor('Lila', Color(0xFFC5A3E8)),
  PaletteColor('Morado', Color(0xFF8E44AD)),
  PaletteColor('Rosa', Color(0xFFF06292)),
  PaletteColor('Rosa claro', Color(0xFFF8BBD0)),
  PaletteColor('Beige', Color(0xFFE8CFA6)),
  PaletteColor('Marrón', Color(0xFF8D5524)),
  PaletteColor('Gris', Color(0xFF9E9E9E)),
  PaletteColor('Negro', Color(0xFF212121)),
  PaletteColor('Blanco', Color(0xFFFFFFFF), restoresOriginal: true),
];
