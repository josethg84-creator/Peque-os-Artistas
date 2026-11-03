import 'package:flutter/foundation.dart';
import 'package:flutter/painting.dart';

import 'engine/drawing_painter.dart';
import 'engine/vector_drawing.dart';
import 'palette.dart';

/// Colores alegres y fijos para cada dibujo, sin que el niño lo haya pintado
/// (rompecabezas e ilustraciones de «Aprendo a Hablar»). Los mismos colores
/// para la misma [seed].
class AutoColors extends ChangeNotifier implements RegionColors {
  /// [background] pinta el fondo del dibujo; `null` lo deja sin pintar (blanco).
  AutoColors(VectorDrawing drawing, String seed, {Color? background = const Color(0xFFFFF3D6)}) {
    final offset = seed.codeUnits.fold<int>(0, (a, b) => a + b);
    for (final (i, r) in drawing.regions.indexed) {
      if (r.id == VectorDrawing.backgroundId) {
        if (background != null) _map[r.id] = background;
      } else {
        _map[r.id] = cheerful[(i + offset) % cheerful.length].color;
      }
    }
  }

  /// Los colores vivos de la paleta: sin el blanco, el gris, el negro ni los
  /// tonos muy oscuros (que apagarían el dibujo).
  static final cheerful = kidPalette
      .where((c) => !c.restoresOriginal && !{'Negro', 'Gris', 'Granate', 'Azul marino'}.contains(c.name))
      .toList();

  final _map = <String, Color>{};

  @override
  Color? colorOf(String regionId) => _map[regionId];
}
