import 'dart:ui';

/// Un cambio atómico: el color anterior y el nuevo de una o varias regiones
/// (`null` = sin pintar). Un toque cambia una región; «limpiar» cambia todas
/// a la vez y se deshace también de una vez.
class ColorEdit {
  ColorEdit(Map<String, (Color?, Color?)> changes) : changes = Map.unmodifiable(changes);

  final Map<String, (Color? before, Color? after)> changes;
}

/// Historial de deshacer y rehacer con un límite de pasos para acotar la
/// memoria. Un cambio nuevo descarta lo que se podía rehacer.
class ColoringHistory {
  ColoringHistory({this.limit = 100});

  final int limit;
  final _undo = <ColorEdit>[];
  final _redo = <ColorEdit>[];

  bool get canUndo => _undo.isNotEmpty;
  bool get canRedo => _redo.isNotEmpty;
  int get undoCount => _undo.length;

  void record(ColorEdit edit) {
    _undo.add(edit);
    if (_undo.length > limit) _undo.removeAt(0);
    _redo.clear();
  }

  ColorEdit? undo() {
    if (_undo.isEmpty) return null;
    final edit = _undo.removeLast();
    _redo.add(edit);
    return edit;
  }

  ColorEdit? redo() {
    if (_redo.isEmpty) return null;
    final edit = _redo.removeLast();
    _undo.add(edit);
    return edit;
  }
}
