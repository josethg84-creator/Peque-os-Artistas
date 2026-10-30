import 'dart:collection';
import 'dart:math';

import '../learning_level.dart';

/// Columnas y filas del laberinto según el nivel.
(int cols, int rows) mazeSizeFor(LearningLevel level) => switch (level) {
  LearningLevel.initial => (4, 4),
  LearningLevel.intermediate => (6, 6),
  LearningLevel.advanced => (8, 8),
};

enum Dir {
  up(0, -1, 1),
  right(1, 0, 2),
  down(0, 1, 4),
  left(-1, 0, 8);

  const Dir(this.dx, this.dy, this.bit);
  final int dx, dy;

  /// Bit de la pared en ese lado de la casilla.
  final int bit;

  Dir get opposite => switch (this) {
    Dir.up => Dir.down,
    Dir.down => Dir.up,
    Dir.left => Dir.right,
    Dir.right => Dir.left,
  };
}

typedef Cell = ({int x, int y});

/// Laberinto «perfecto»: entre dos casillas cualesquiera hay exactamente un
/// camino, así que siempre se puede llegar a la meta y no hay zonas cerradas.
/// Se genera con un recorrido en profundidad aleatorio (con semilla).
class Maze {
  Maze._(this.cols, this.rows, this._walls);

  /// Todas las paredes cerradas al principio; el recorrido las va abriendo.
  factory Maze.generate(int cols, int rows, Random random) {
    final walls = List<int>.filled(cols * rows, 15);
    final visited = List<bool>.filled(cols * rows, false);
    final stack = <Cell>[(x: 0, y: 0)];
    visited[0] = true;
    while (stack.isNotEmpty) {
      final c = stack.last;
      final options = [
        for (final d in Dir.values)
          if (_inside(c.x + d.dx, c.y + d.dy, cols, rows) && !visited[(c.y + d.dy) * cols + c.x + d.dx]) d,
      ];
      if (options.isEmpty) {
        stack.removeLast();
        continue;
      }
      final d = options[random.nextInt(options.length)];
      final n = (x: c.x + d.dx, y: c.y + d.dy);
      walls[c.y * cols + c.x] &= ~d.bit;
      walls[n.y * cols + n.x] &= ~d.opposite.bit;
      visited[n.y * cols + n.x] = true;
      stack.add(n);
    }
    return Maze._(cols, rows, walls);
  }

  final int cols, rows;
  final List<int> _walls;

  static bool _inside(int x, int y, int cols, int rows) => x >= 0 && y >= 0 && x < cols && y < rows;

  bool contains(Cell c) => _inside(c.x, c.y, cols, rows);

  bool hasWall(Cell c, Dir d) => _walls[c.y * cols + c.x] & d.bit != 0;

  /// Se puede pasar de [c] hacia [d]: no hay pared ni se sale del laberinto.
  bool canMove(Cell c, Dir d) => contains(c) && !hasWall(c, d) && contains((x: c.x + d.dx, y: c.y + d.dy));

  /// Camino más corto (incluye origen y destino), o `null` si no existe.
  List<Cell>? solve(Cell from, Cell to) {
    final prev = <Cell, Cell>{};
    final queue = Queue<Cell>()..add(from);
    final seen = <Cell>{from};
    while (queue.isNotEmpty) {
      final c = queue.removeFirst();
      if (c == to) {
        final path = <Cell>[c];
        while (path.last != from) {
          path.add(prev[path.last]!);
        }
        return path.reversed.toList();
      }
      for (final d in Dir.values) {
        if (!canMove(c, d)) continue;
        final n = (x: c.x + d.dx, y: c.y + d.dy);
        if (seen.add(n)) {
          prev[n] = c;
          queue.add(n);
        }
      }
    }
    return null;
  }

  /// Casilla más lejana (por el camino) desde [from]: buena meta.
  Cell farthestFrom(Cell from) {
    final dist = <Cell, int>{from: 0};
    final queue = Queue<Cell>()..add(from);
    var best = from;
    while (queue.isNotEmpty) {
      final c = queue.removeFirst();
      if (dist[c]! > dist[best]!) best = c;
      for (final d in Dir.values) {
        if (!canMove(c, d)) continue;
        final n = (x: c.x + d.dx, y: c.y + d.dy);
        if (!dist.containsKey(n)) {
          dist[n] = dist[c]! + 1;
          queue.add(n);
        }
      }
    }
    return best;
  }

  /// Número de pasos abiertos (en un laberinto perfecto: casillas − 1).
  int get openings {
    var n = 0;
    for (var y = 0; y < rows; y++) {
      for (var x = 0; x < cols; x++) {
        if (canMove((x: x, y: y), Dir.right)) n++;
        if (canMove((x: x, y: y), Dir.down)) n++;
      }
    }
    return n;
  }
}

/// Temas de los laberintos: quién recorre y qué busca.
enum MazeTheme {
  rabbit(
    'Ayuda al conejo a llegar a la fresa',
    'animal_conejo',
    'fruta_fresa',
    '¡El conejo encontró su fresa!',
  ),
  car('Lleva el coche hasta la meta', 'vehiculo_automovil', null, '¡El coche llegó a la meta!'),
  butterfly('Guía a la mariposa hasta la flor', 'animal_mariposa', null, '¡La mariposa llegó a la flor!'),
  treasure('Encuentra el camino hacia el tesoro', 'fantasia_dragon', null, '¡Encontraste el tesoro!');

  const MazeTheme(this.instruction, this.player, this.goalDrawing, this.success);

  final String instruction;

  /// Dibujo del catálogo que hace de personaje.
  final String player;

  /// Dibujo del catálogo que hace de meta (o un icono si es `null`).
  final String? goalDrawing;
  final String success;
}

enum MoveResult { moved, blocked, goal, ignored }

/// Una partida: el personaje parte de [start] y debe llegar a [goal]. No puede
/// atravesar paredes ni salir del laberinto.
class MazeGame {
  MazeGame({required this.maze, required this.theme, required this.start}) : goal = maze.farthestFrom(start) {
    reset();
  }

  factory MazeGame.random(LearningLevel level, MazeTheme theme, Random random) {
    final (cols, rows) = mazeSizeFor(level);
    final maze = Maze.generate(cols, rows, random);
    final corners = [(x: 0, y: 0), (x: cols - 1, y: 0), (x: 0, y: rows - 1), (x: cols - 1, y: rows - 1)];
    return MazeGame(maze: maze, theme: theme, start: corners[random.nextInt(corners.length)]);
  }

  final Maze maze;
  final MazeTheme theme;
  final Cell start;
  final Cell goal;
  late Cell position;
  late List<Cell> trail;
  int bumps = 0;

  bool get reached => position == goal;

  void reset() {
    position = start;
    trail = [start];
    bumps = 0;
  }

  MoveResult move(Dir d) {
    if (reached) return MoveResult.ignored;
    if (!maze.canMove(position, d)) {
      bumps++;
      return MoveResult.blocked;
    }
    position = (x: position.x + d.dx, y: position.y + d.dy);
    // Volver sobre los propios pasos borra el rastro.
    if (trail.length >= 2 && trail[trail.length - 2] == position) {
      trail.removeLast();
    } else {
      trail.add(position);
    }
    return reached ? MoveResult.goal : MoveResult.moved;
  }

  /// Avanza hacia [target] paso a paso (dedo que se mueve deprisa) hasta
  /// llegar o chocar con una pared. Devuelve el último resultado.
  MoveResult moveToward(Cell target) {
    var result = MoveResult.ignored;
    for (var guard = 0; guard < maze.cols + maze.rows && position != target && !reached; guard++) {
      final dx = target.x - position.x, dy = target.y - position.y;
      // Primero el eje con más distancia; si hay pared, se prueba el otro.
      final primary = dx.abs() >= dy.abs() ? (dx > 0 ? Dir.right : Dir.left) : (dy > 0 ? Dir.down : Dir.up);
      final secondary = dx.abs() >= dy.abs()
          ? (dy == 0 ? null : (dy > 0 ? Dir.down : Dir.up))
          : (dx == 0 ? null : (dx > 0 ? Dir.right : Dir.left));
      if (maze.canMove(position, primary)) {
        result = move(primary);
      } else if (secondary != null && maze.canMove(position, secondary)) {
        result = move(secondary);
      } else {
        bumps++;
        return MoveResult.blocked;
      }
    }
    return result;
  }

  /// Pista: el camino desde donde está el personaje hasta la meta.
  List<Cell> hint() => maze.solve(position, goal) ?? const [];
}
