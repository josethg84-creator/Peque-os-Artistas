import 'dart:math';
import 'dart:ui';

import '../learning_level.dart';

/// Secciones de «Trazos y escritura».
enum TraceSection {
  lines('Líneas', 'Sigue la línea con el dedo'),
  letters('Letras', 'Escribe la letra siguiendo la guía'),
  numbers('Números', 'Escribe el número siguiendo la guía'),
  dots('Unir puntos', 'Une los puntos en orden');

  const TraceSection(this.title, this.instruction);
  final String title;
  final String instruction;
}

/// Un ejercicio: uno o varios trazos (cada uno, una lista de puntos en un
/// lienzo de 0 a 1). En «unir puntos», [dots] son los puntos numerados.
class TraceItem {
  const TraceItem({
    required this.id,
    required this.label,
    required this.section,
    required this.strokes,
    this.spoken,
  });

  final String id;

  /// Texto corto en pantalla («A», «7», «Ondas»…).
  final String label;
  final TraceSection section;
  final List<List<Offset>> strokes;

  /// Lo que dice la voz (si no, [label]).
  final String? spoken;

  bool get isDots => section == TraceSection.dots;

  /// Puntos numerados de «unir puntos» (el primer trazo, en orden).
  List<Offset> get dots => strokes.first;
}

/// Ayuda por nivel (se elige con los botones de nivel, sin pedir la edad):
/// inicial ≈ 4-5 años, intermedio ≈ 5-6, avanzado ≈ 6-7.
class TraceDifficulty {
  const TraceDifficulty({
    required this.tolerance,
    required this.coverage,
    required this.showStrokeOrder,
    required this.guideWidth,
    required this.itemsPerSession,
  });

  /// Distancia máxima (en fracción del lienzo) al recorrido para contar.
  final double tolerance;

  /// Parte del recorrido que hay que cubrir para completarlo.
  final double coverage;

  /// Números y flechas de inicio en cada trazo.
  final bool showStrokeOrder;

  /// Grosor de la guía (fracción del lienzo).
  final double guideWidth;

  /// Ejercicios que forman una actividad completa.
  final int itemsPerSession;

  static TraceDifficulty of(LearningLevel level) => switch (level) {
    LearningLevel.initial => const TraceDifficulty(
      tolerance: 0.085,
      coverage: 0.72,
      showStrokeOrder: true,
      guideWidth: 0.11,
      itemsPerSession: 3,
    ),
    LearningLevel.intermediate => const TraceDifficulty(
      tolerance: 0.065,
      coverage: 0.8,
      showStrokeOrder: true,
      guideWidth: 0.085,
      itemsPerSession: 4,
    ),
    LearningLevel.advanced => const TraceDifficulty(
      tolerance: 0.05,
      coverage: 0.86,
      showStrokeOrder: false,
      guideWidth: 0.065,
      itemsPerSession: 5,
    ),
  };
}

/// Comprueba, mientras el niño dibuja, cuánto del recorrido ha seguido.
///
/// Cada trazo se divide en puntos de control cada [step] de longitud. Un punto
/// de control se cubre cuando el dedo pasa cerca (a menos de la tolerancia).
/// Se completa al cubrir la parte pedida de **cada** trazo, en cualquier orden
/// (a los niños no se les exige el orden exacto). Los garabatos lejos de la
/// guía no cuentan. En «unir puntos» hay que llegar a los puntos en orden.
class TraceEvaluator {
  TraceEvaluator(this.item, this.difficulty, {this.step = 0.025}) {
    for (final s in item.strokes) {
      _checkpoints.add(resample(s, step));
    }
    reset();
  }

  final TraceItem item;
  final TraceDifficulty difficulty;
  final double step;
  final _checkpoints = <List<Offset>>[];
  late List<List<bool>> _covered;
  int _nextDot = 0;
  int _onPath = 0, _offPath = 0;

  /// Para «unir puntos»: siguiente punto que hay que alcanzar.
  int get nextDot => _nextDot;
  List<List<Offset>> get checkpoints => _checkpoints;
  bool isCovered(int stroke, int i) => _covered[stroke][i];

  void reset() {
    _covered = [for (final c in _checkpoints) List<bool>.filled(c.length, false)];
    _nextDot = 0;
    _onPath = 0;
    _offPath = 0;
  }

  /// Un punto del dedo (en coordenadas 0-1). Devuelve si estaba cerca de la guía.
  bool addPoint(Offset p) {
    if (item.isDots) return _addDotPoint(p);
    final tol = difficulty.tolerance;
    var near = false;
    for (var s = 0; s < _checkpoints.length; s++) {
      final cps = _checkpoints[s];
      for (var i = 0; i < cps.length; i++) {
        if ((cps[i] - p).distance <= tol) {
          _covered[s][i] = true;
          near = true;
        }
      }
    }
    near ? _onPath++ : _offPath++;
    return near;
  }

  bool _addDotPoint(Offset p) {
    final dots = item.dots;
    if (_nextDot >= dots.length) return false;
    final near = (dots[_nextDot] - p).distance <= difficulty.tolerance * 1.2;
    if (near) _nextDot++;
    return near;
  }

  /// Progreso de 0 a 1.
  double get progress {
    if (item.isDots) {
      final n = item.dots.length;
      return n <= 1 ? 1 : ((_nextDot - 1).clamp(0, n - 1)) / (n - 1);
    }
    var total = 0.0;
    for (var s = 0; s < _covered.length; s++) {
      // Cada trazo cuenta hasta su meta de cobertura (no se compensa uno con otro).
      total += (strokeProgress(s) / difficulty.coverage).clamp(0.0, 1.0);
    }
    return total / _covered.length;
  }

  double strokeProgress(int s) {
    final c = _covered[s];
    return c.where((v) => v).length / c.length;
  }

  bool get isComplete => item.isDots
      ? _nextDot >= item.dots.length
      : [for (var s = 0; s < _covered.length; s++) s].every((s) => strokeProgress(s) >= difficulty.coverage);

  /// El dedo va casi siempre lejos de la guía (para animar a seguirla).
  bool get mostlyOffPath => _onPath + _offPath >= 12 && _offPath > 1.5 * _onPath;

  /// Puntos a distancia fija a lo largo del trazo (incluye extremos).
  static List<Offset> resample(List<Offset> pts, double step) {
    if (pts.length < 2) return List.of(pts);
    final out = <Offset>[pts.first];
    var carry = 0.0;
    for (var i = 1; i < pts.length; i++) {
      final a = pts[i - 1], b = pts[i];
      final len = (b - a).distance;
      var t = step - carry;
      while (t <= len) {
        out.add(Offset.lerp(a, b, t / len)!);
        t += step;
      }
      carry = len - (t - step);
    }
    if ((out.last - pts.last).distance > step * 0.3) out.add(pts.last);
    return out;
  }
}

// ------------------------------------------------------------------ recorridos

const _l = 0.25, _r = 0.75, _t = 0.18, _b = 0.85, _m = 0.515, _c = 0.5;

List<Offset> _line(List<(double, double)> pts) => [for (final (x, y) in pts) Offset(x, y)];

/// Arco de elipse (ángulos en grados, sentido de las agujas del reloj en
/// pantalla: 0 = derecha, 90 = abajo, -90 = arriba).
List<Offset> _arc(double cx, double cy, double rx, double ry, double from, double to, {int steps = 40}) => [
  for (var i = 0; i <= steps; i++)
    Offset(
      cx + rx * cos((from + (to - from) * i / steps) * pi / 180),
      cy + ry * sin((from + (to - from) * i / steps) * pi / 180),
    ),
];

List<Offset> _join(List<List<Offset>> parts) => [for (final p in parts) ...p];

TraceItem _item(TraceSection s, String id, String label, List<List<Offset>> strokes, {String? spoken}) =>
    TraceItem(id: id, label: label, section: s, strokes: strokes, spoken: spoken);

/// Grafomotricidad: líneas y formas básicas.
final traceLines = <TraceItem>[
  _item(TraceSection.lines, 'horizontal', 'Línea horizontal', [
    _line([(0.12, 0.5), (0.88, 0.5)]),
  ]),
  _item(TraceSection.lines, 'vertical', 'Línea vertical', [
    _line([(0.5, 0.12), (0.5, 0.88)]),
  ]),
  _item(TraceSection.lines, 'diagonal', 'Línea diagonal', [
    _line([(0.15, 0.85), (0.85, 0.15)]),
  ]),
  _item(TraceSection.lines, 'curva', 'Línea curva', [_arc(0.5, 0.78, 0.36, 0.5, 180, 360)]),
  _item(TraceSection.lines, 'ondas', 'Ondas', [
    [for (var i = 0; i <= 80; i++) Offset(0.1 + 0.8 * i / 80, 0.5 + 0.13 * sin(2 * pi * 2 * i / 80))],
  ]),
  _item(TraceSection.lines, 'zigzag', 'Zigzag', [
    _line([(0.1, 0.62), (0.26, 0.38), (0.42, 0.62), (0.58, 0.38), (0.74, 0.62), (0.9, 0.38)]),
  ]),
  _item(TraceSection.lines, 'circulo', 'Círculo', [_arc(0.5, 0.5, 0.32, 0.32, -90, 270, steps: 72)]),
];

/// Letras mayúsculas de imprenta (trazos sencillos), con la Ñ.
final traceLetters = <TraceItem>[
  for (final e in <String, List<List<Offset>>>{
    'A': [
      _line([(_c, _t), (_l, _b)]),
      _line([(_c, _t), (_r, _b)]),
      _line([(0.34, 0.62), (0.66, 0.62)]),
    ],
    'B': [
      _line([(_l, _t), (_l, _b)]),
      _join([
        _line([(_l, _t), (0.56, _t)]),
        _arc(0.56, 0.348, 0.17, 0.168, -90, 90),
        _line([(0.56, _m), (_l, _m)]),
      ]),
      _join([
        _line([(_l, _m), (0.58, _m)]),
        _arc(0.58, 0.683, 0.18, 0.167, -90, 90),
        _line([(0.58, _b), (_l, _b)]),
      ]),
    ],
    'C': [_arc(0.53, _m, 0.29, 0.335, -45, -315)],
    'D': [
      _line([(_l, _t), (_l, _b)]),
      _join([
        _line([(_l, _t), (0.43, _t)]),
        _arc(0.43, _m, 0.32, 0.335, -90, 90),
        _line([(0.43, _b), (_l, _b)]),
      ]),
    ],
    'E': [
      _line([(_r, _t), (_l, _t), (_l, _b), (_r, _b)]),
      _line([(_l, _m), (0.66, _m)]),
    ],
    'F': [
      _line([(_r, _t), (_l, _t), (_l, _b)]),
      _line([(_l, _m), (0.66, _m)]),
    ],
    'G': [
      _join([_arc(0.52, _m, 0.29, 0.335, -45, -360)]),
      _line([(0.81, _m), (0.56, _m)]),
    ],
    'H': [
      _line([(_l, _t), (_l, _b)]),
      _line([(_r, _t), (_r, _b)]),
      _line([(_l, _m), (_r, _m)]),
    ],
    'I': [
      _line([(_c, _t), (_c, _b)]),
      _line([(0.36, _t), (0.64, _t)]),
      _line([(0.36, _b), (0.64, _b)]),
    ],
    'J': [
      _join([
        _line([(0.66, _t), (0.66, 0.66)]),
        _arc(0.48, 0.66, 0.18, 0.19, 0, 180),
      ]),
    ],
    'K': [
      _line([(_l, _t), (_l, _b)]),
      _line([(_r, _t), (_l, _m), (_r, _b)]),
    ],
    'L': [
      _line([(_l, _t), (_l, _b), (_r, _b)]),
    ],
    'M': [
      _line([(0.22, _b), (0.22, _t), (_c, 0.6), (0.78, _t), (0.78, _b)]),
    ],
    'N': [
      _line([(_l, _b), (_l, _t), (_r, _b), (_r, _t)]),
    ],
    'Ñ': [
      _line([(_l, _b), (_l, 0.26), (_r, _b), (_r, 0.26)]),
      [for (var i = 0; i <= 30; i++) Offset(0.36 + 0.28 * i / 30, 0.13 - 0.035 * sin(2 * pi * i / 30))],
    ],
    'O': [_arc(_c, _m, 0.29, 0.335, -90, 270, steps: 72)],
    'P': [
      _line([(_l, _b), (_l, _t)]),
      _join([
        _line([(_l, _t), (0.55, _t)]),
        _arc(0.55, 0.335, 0.18, 0.155, -90, 90),
        _line([(0.55, 0.49), (_l, 0.49)]),
      ]),
    ],
    'Q': [
      _arc(_c, _m, 0.29, 0.335, -90, 270, steps: 72),
      _line([(0.6, 0.68), (0.8, 0.9)]),
    ],
    'R': [
      _line([(_l, _b), (_l, _t)]),
      _join([
        _line([(_l, _t), (0.55, _t)]),
        _arc(0.55, 0.335, 0.18, 0.155, -90, 90),
        _line([(0.55, 0.49), (_l, 0.49)]),
      ]),
      _line([(0.47, 0.49), (_r, _b)]),
    ],
    'S': [
      _join([_arc(_c, 0.35, 0.22, 0.17, -25, -270), _arc(_c, 0.685, 0.23, 0.165, -90, 155)]),
    ],
    'T': [
      _line([(0.22, _t), (0.78, _t)]),
      _line([(_c, _t), (_c, _b)]),
    ],
    'U': [
      _join([
        _line([(_l, _t), (_l, 0.6)]),
        _arc(_c, 0.6, 0.25, 0.25, 180, 0),
        _line([(_r, 0.6), (_r, _t)]),
      ]),
    ],
    'V': [
      _line([(_l, _t), (_c, _b), (_r, _t)]),
    ],
    'W': [
      _line([(0.18, _t), (0.34, _b), (_c, 0.45), (0.66, _b), (0.82, _t)]),
    ],
    'X': [
      _line([(_l, _t), (_r, _b)]),
      _line([(_r, _t), (_l, _b)]),
    ],
    'Y': [
      _line([(_l, _t), (_c, _m)]),
      _line([(_r, _t), (_c, _m), (_c, _b)]),
    ],
    'Z': [
      _line([(_l, _t), (_r, _t), (_l, _b), (_r, _b)]),
    ],
  }.entries)
    _item(TraceSection.letters, 'letra_${e.key}', e.key, e.value, spoken: 'La letra ${e.key}'),
];

/// Números del 1 al 10.
final traceNumbers = <TraceItem>[
  for (final e in <(String, String), List<List<Offset>>>{
    ('1', 'uno'): [
      _line([(0.36, 0.32), (0.55, _t), (0.55, _b)]),
    ],
    ('2', 'dos'): [
      _join([
        _arc(_c, 0.37, 0.21, 0.19, -165, 25),
        _line([(0.69, 0.45), (0.3, _b), (0.73, _b)]),
      ]),
    ],
    ('3', 'tres'): [
      _join([_arc(_c, 0.34, 0.2, 0.16, -155, 90), _arc(_c, 0.67, 0.22, 0.18, -90, 155)]),
    ],
    ('4', 'cuatro'): [
      _line([(0.6, _b), (0.6, _t), (0.27, 0.65), (0.76, 0.65)]),
    ],
    ('5', 'cinco'): [
      _join([
        _line([(0.7, _t), (0.36, _t), (0.33, 0.48)]),
        _arc(0.5, 0.66, 0.22, 0.19, -125, 155),
      ]),
    ],
    ('6', 'seis'): [
      _join([
        _arc(0.55, 0.62, 0.27, 0.44, -80, -180, steps: 20),
        _arc(0.5, 0.66, 0.22, 0.19, 180, 540, steps: 60),
      ]),
    ],
    ('7', 'siete'): [
      _line([(0.28, _t), (0.72, _t), (0.42, _b)]),
    ],
    ('8', 'ocho'): [
      _join([_arc(_c, 0.34, 0.17, 0.16, 90, 450, steps: 50), _arc(_c, 0.67, 0.2, 0.18, -90, 270, steps: 50)]),
    ],
    ('9', 'nueve'): [
      _join([
        _arc(_c, 0.36, 0.19, 0.18, 0, 360, steps: 50),
        _line([(0.69, 0.36), (0.62, _b)]),
      ]),
    ],
    ('10', 'diez'): [
      _line([(0.17, 0.3), (0.32, _t), (0.32, _b)]),
      _arc(0.63, _m, 0.17, 0.335, -90, 270, steps: 60),
    ],
  }.entries)
    _item(TraceSection.numbers, 'numero_${e.key.$1}', e.key.$1, e.value, spoken: 'El número ${e.key.$2}'),
];

/// Unir puntos: el dibujo aparece al llegar al último punto.
final traceDots = <TraceItem>[
  _item(TraceSection.dots, 'estrella', 'Estrella', [
    [
      for (var i = 0; i <= 10; i++)
        Offset(
          0.5 + (i.isEven ? 0.38 : 0.16) * cos((-90 + 36 * i) * pi / 180),
          0.53 + (i.isEven ? 0.38 : 0.16) * sin((-90 + 36 * i) * pi / 180),
        ),
    ],
  ], spoken: 'Una estrella'),
  _item(TraceSection.dots, 'casa', 'Casa', [
    _line([(0.22, 0.88), (0.22, 0.48), (0.5, 0.16), (0.78, 0.48), (0.78, 0.88), (0.22, 0.88)]),
  ], spoken: 'Una casa'),
  _item(TraceSection.dots, 'corazon', 'Corazón', [
    _line([
      (0.5, 0.86),
      (0.2, 0.55),
      (0.16, 0.36),
      (0.25, 0.22),
      (0.38, 0.2),
      (0.5, 0.32),
      (0.62, 0.2),
      (0.75, 0.22),
      (0.84, 0.36),
      (0.8, 0.55),
      (0.5, 0.86),
    ]),
  ], spoken: 'Un corazón'),
  _item(TraceSection.dots, 'pez', 'Pez', [
    _line([
      (0.14, 0.5),
      (0.3, 0.32),
      (0.55, 0.28),
      (0.72, 0.42),
      (0.88, 0.28),
      (0.88, 0.72),
      (0.72, 0.58),
      (0.55, 0.72),
      (0.3, 0.68),
      (0.14, 0.5),
    ]),
  ], spoken: 'Un pez'),
  _item(TraceSection.dots, 'barco', 'Barco', [
    _line([
      (0.12, 0.62),
      (0.88, 0.62),
      (0.74, 0.84),
      (0.26, 0.84),
      (0.12, 0.62),
      (0.48, 0.62),
      (0.48, 0.14),
      (0.78, 0.52),
      (0.48, 0.52),
    ]),
  ], spoken: 'Un barco'),
];

List<TraceItem> traceItems(TraceSection section) => switch (section) {
  TraceSection.lines => traceLines,
  TraceSection.letters => traceLetters,
  TraceSection.numbers => traceNumbers,
  TraceSection.dots => traceDots,
};
