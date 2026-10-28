import 'package:flutter/foundation.dart';

import 'palette.dart';

enum ColoringTool { paint, eraser }

/// Estado de la pantalla de coloreado.
///
/// En la Fase 2 solo gestiona la selección de color y de herramienta. El motor
/// de coloreado por regiones (Fase 3) añadirá aquí el historial: entonces
/// [canUndo], [canRedo] y [hasColoring] reflejarán cambios reales y
/// [undo], [redo] y [clear] modificarán el dibujo. Hasta entonces no hay nada
/// que deshacer ni limpiar y los botones se muestran desactivados.
class ColoringController extends ChangeNotifier {
  ColoringController({PaletteColor? initialColor}) : _color = initialColor ?? kidPalette.first;

  PaletteColor _color;
  ColoringTool _tool = ColoringTool.paint;

  PaletteColor get color => _color;
  ColoringTool get tool => _tool;

  /// Disponible cuando exista el motor de coloreado (Fase 3).
  bool get coloringEngineReady => false;
  bool get canUndo => false;
  bool get canRedo => false;
  bool get hasColoring => false;

  void selectColor(PaletteColor color) {
    if (_color == color && _tool == ColoringTool.paint) return;
    _color = color;
    _tool = ColoringTool.paint;
    notifyListeners();
  }

  void toggleEraser() {
    _tool = _tool == ColoringTool.eraser ? ColoringTool.paint : ColoringTool.eraser;
    notifyListeners();
  }

  // Puntos de extensión para la Fase 3.
  void undo() {}
  void redo() {}
  void clear() {}
}
