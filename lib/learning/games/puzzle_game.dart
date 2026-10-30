import 'dart:math';

import '../learning_level.dart';

/// Piezas por lado según el nivel: 2×2 = 4, 3×3 = 9 y 4×4 = 16.
int puzzleSideFor(LearningLevel level) => switch (level) {
  LearningLevel.initial => 2,
  LearningLevel.intermediate => 3,
  LearningLevel.advanced => 4,
};

enum DropResult {
  /// La pieza estaba en su sitio: se queda fija.
  correct,

  /// Ese no es su sitio: vuelve a la bandeja (sin castigo).
  wrong,

  /// Pieza ya colocada o casilla ocupada.
  ignored,
}

/// Rompecabezas de piezas cuadradas. La pieza `i` va en la casilla `i`
/// (numeradas por filas, de izquierda a derecha y de arriba abajo).
class PuzzleGame {
  PuzzleGame({required this.side, Random? random}) : assert(side >= 2) {
    final r = random ?? Random();
    final order = List<int>.generate(pieces, (i) => i);
    // Se baraja hasta que el orden no sea el resuelto (en 4 piezas podría tocar).
    do {
      order.shuffle(r);
    } while (_isIdentity(order));
    _tray = order;
  }

  final int side;
  late List<int> _tray;
  final _placed = <int>{};
  int _attempts = 0;

  int get pieces => side * side;

  /// Piezas que quedan por colocar, en el orden en que se ven en la bandeja.
  List<int> get tray => List.unmodifiable(_tray);
  bool isPlaced(int piece) => _placed.contains(piece);
  int get placedCount => _placed.length;
  int get attempts => _attempts;
  bool get isComplete => _placed.length == pieces;

  /// Fila y columna de una casilla (o de la posición correcta de una pieza).
  (int row, int col) cellOf(int index) => (index ~/ side, index % side);

  DropResult drop(int piece, int cell) {
    if (piece < 0 || piece >= pieces || cell < 0 || cell >= pieces) return DropResult.ignored;
    if (_placed.contains(piece) || _placed.contains(cell)) return DropResult.ignored;
    _attempts++;
    if (piece != cell) return DropResult.wrong;
    _placed.add(piece);
    _tray.remove(piece);
    return DropResult.correct;
  }

  static bool _isIdentity(List<int> order) {
    for (var i = 0; i < order.length; i++) {
      if (order[i] != i) return false;
    }
    return true;
  }
}
