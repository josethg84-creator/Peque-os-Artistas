import 'package:flutter/material.dart';

/// Un color de la paleta con su nombre (para accesibilidad y tooltips).
class PaletteColor {
  const PaletteColor(this.name, this.color);
  final String name;
  final Color color;
}

/// Paleta infantil inicial: colores vivos y fáciles de distinguir.
const kidPalette = <PaletteColor>[
  PaletteColor('Rojo', Color(0xFFE53935)),
  PaletteColor('Naranja', Color(0xFFFF8F00)),
  PaletteColor('Amarillo', Color(0xFFFFD600)),
  PaletteColor('Verde claro', Color(0xFF7CB342)),
  PaletteColor('Verde', Color(0xFF2E7D32)),
  PaletteColor('Celeste', Color(0xFF29B6F6)),
  PaletteColor('Azul', Color(0xFF1E57C8)),
  PaletteColor('Morado', Color(0xFF8E44AD)),
  PaletteColor('Rosa', Color(0xFFF06292)),
  PaletteColor('Marrón', Color(0xFF8D5524)),
  PaletteColor('Gris', Color(0xFF9E9E9E)),
  PaletteColor('Negro', Color(0xFF212121)),
];
