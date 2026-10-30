/// Nivel de dificultad de «Aprender jugando». Se elige con tres botones; no
/// se pide la edad ni ningún dato personal. Por defecto: inicial.
enum LearningLevel {
  initial('inicial', 'Inicial', 1),
  intermediate('intermedio', 'Intermedio', 2),
  advanced('avanzado', 'Avanzado', 3);

  const LearningLevel(this.id, this.label, this.stars);

  final String id;
  final String label;
  final int stars;

  static LearningLevel fromId(String? id) =>
      values.firstWhere((l) => l.id == id, orElse: () => LearningLevel.initial);
}

/// Identificadores estables de los minijuegos (se guardan en el progreso).
enum GameId {
  colors('colores', 'Aprende los colores'),
  shapes('formas', 'Descubre las formas'),
  animals('animales', 'Encuentra a los animales'),
  memory('parejas', 'Une las parejas'),
  puzzle('rompecabezas', 'Rompecabezas'),
  maze('laberintos', 'Laberintos'),
  tracing('trazos', 'Trazos y escritura');

  const GameId(this.id, this.title);

  final String id;
  final String title;

  static GameId? fromId(String? id) {
    for (final g in values) {
      if (g.id == id) return g;
    }
    return null;
  }
}
