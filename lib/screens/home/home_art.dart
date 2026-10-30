import 'dart:math';

import 'package:flutter/material.dart';

/// Ilustraciones vectoriales originales de la pantalla de inicio. Cada forma
/// se rellena con un degradado radial (luz arriba a la izquierda, sombra abajo)
/// para dar un volumen suave de estilo 3D infantil, sin imágenes externas.

Color _mix(Color a, Color b, double t) => Color.lerp(a, b, t)!;

/// Relleno con volumen: claro arriba a la izquierda, sombra abajo a la derecha.
Paint soft(Rect r, Color base, {double light = 0.45, double dark = 0.22}) => Paint()
  ..shader = RadialGradient(
    center: const Alignment(-0.35, -0.5),
    radius: 1.05,
    colors: [_mix(base, Colors.white, light), base, _mix(base, Colors.black, dark)],
    stops: const [0, 0.55, 1],
  ).createShader(r);

Paint _line(Color c, double w) => Paint()
  ..color = c
  ..style = PaintingStyle.stroke
  ..strokeWidth = w
  ..strokeCap = StrokeCap.round
  ..strokeJoin = StrokeJoin.round;

void _shape(Canvas canvas, Path p, Color base, {double outline = 1.6}) {
  final r = p.getBounds();
  canvas.drawPath(p, soft(r, base));
  if (outline > 0) canvas.drawPath(p, _line(_mix(base, Colors.black, 0.4).withValues(alpha: 0.55), outline));
}

void _circle(Canvas c, Offset o, double r, Color base, {double outline = 1.4}) => _shape(
  c,
  Path()..addOval(Rect.fromCircle(center: o, radius: r)),
  base,
  outline: outline,
);

void _oval(Canvas c, Offset o, double w, double h, Color base, {double outline = 1.4, double angle = 0}) {
  c.save();
  c.translate(o.dx, o.dy);
  c.rotate(angle);
  _shape(
    c,
    Path()..addOval(Rect.fromCenter(center: Offset.zero, width: w, height: h)),
    base,
    outline: outline,
  );
  c.restore();
}

/// Brazo/manga como cápsula (rectángulo de puntas redondas a lo largo de a→b).
void _capsule(Canvas c, Offset a, Offset b, double w, Color base) {
  final d = b - a;
  c.save();
  c.translate(a.dx, a.dy);
  c.rotate(atan2(d.dy, d.dx));
  final r = RRect.fromRectAndRadius(Rect.fromLTWH(-w / 2, -w / 2, d.distance + w, w), Radius.circular(w / 2));
  _shape(c, Path()..addRRect(r), base, outline: 1.2);
  c.restore();
}

/// Pincel: mango de madera, virola plateada y punta con pintura.
void brush(Canvas c, Offset grip, double angle, double len, Color paint) {
  c.save();
  c.translate(grip.dx, grip.dy);
  c.rotate(angle);
  // El pincel apunta hacia -y (arriba) en su propio sistema.
  _capsule(c, Offset(0, len * 0.35), Offset(0, -len * 0.45), len * 0.11, const Color(0xFFD08A4E));
  _shape(
    c,
    Path()..addRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(-len * 0.075, -len * 0.62, len * 0.15, len * 0.2),
        const Radius.circular(3),
      ),
    ),
    const Color(0xFFCFD6E0),
  );
  final tip = Path()
    ..moveTo(-len * 0.08, -len * 0.62)
    ..quadraticBezierTo(-len * 0.11, -len * 0.82, 0, -len * 0.98)
    ..quadraticBezierTo(len * 0.11, -len * 0.82, len * 0.08, -len * 0.62)
    ..close();
  _shape(c, tip, paint);
  c.restore();
}

/// Manchas de pintura con salpicaduras.
void splash(Canvas c, Offset o, double r, Color color) {
  _circle(c, o, r, color, outline: 0);
  final rnd = Random(o.dx.toInt() * 31 + o.dy.toInt());
  for (var i = 0; i < 5; i++) {
    final a = rnd.nextDouble() * pi * 2;
    final d = r * (1.2 + rnd.nextDouble() * 0.6);
    _circle(c, o + Offset(cos(a), sin(a)) * d, r * (0.15 + rnd.nextDouble() * 0.2), color, outline: 0);
  }
}

// --------------------------------------------------------------- personajes

/// Un niño y una niña con pinceles y un perrito entre los dos (lienzo de
/// diseño de 360 × 230, escalado al espacio disponible).
class CharactersPainter extends CustomPainter {
  const CharactersPainter();

  static const designSize = Size(360, 230);

  static const _skin = Color(0xFFFFD2AE);
  static const _ink = Color(0xFF3B2A35);

  @override
  void paint(Canvas canvas, Size size) {
    final k = min(size.width / designSize.width, size.height / designSize.height);
    canvas.save();
    canvas.translate((size.width - designSize.width * k) / 2, size.height - designSize.height * k);
    canvas.scale(k);
    // Sombra en el suelo.
    canvas.drawOval(
      Rect.fromCenter(center: const Offset(180, 224), width: 330, height: 18),
      Paint()..color = const Color(0x22000000),
    );
    splash(canvas, const Offset(22, 200), 9, const Color(0xFF4FB3FF));
    splash(canvas, const Offset(340, 196), 9, const Color(0xFFFFC93C));
    splash(canvas, const Offset(318, 30), 6, const Color(0xFFFF6B8B));
    splash(canvas, const Offset(36, 34), 6, const Color(0xFF5CC689));
    _boy(canvas);
    _girl(canvas);
    _dog(canvas);
    canvas.restore();
  }

  void _eyes(Canvas c, Offset l, Offset r, {bool lashes = false}) {
    for (final e in [l, r]) {
      _oval(c, e, 17, 21, const Color(0xFF3A2416), outline: 0);
      c.drawCircle(e + const Offset(3, -4), 3.6, Paint()..color = Colors.white);
      c.drawCircle(e + const Offset(-3, 5), 1.6, Paint()..color = Colors.white.withValues(alpha: 0.9));
    }
    if (lashes) {
      final p = _line(_ink, 2);
      c.drawLine(l + const Offset(-8, -8), l + const Offset(-12, -12), p);
      c.drawLine(r + const Offset(8, -8), r + const Offset(12, -12), p);
    }
  }

  void _cheeks(Canvas c, Offset l, Offset r) {
    final p = Paint()..color = const Color(0xFFFF7FA0).withValues(alpha: 0.45);
    c.drawOval(Rect.fromCenter(center: l, width: 16, height: 10), p);
    c.drawOval(Rect.fromCenter(center: r, width: 16, height: 10), p);
  }

  void _smile(Canvas c, Offset center, double w) {
    final p = Path()
      ..moveTo(center.dx - w / 2, center.dy)
      ..quadraticBezierTo(center.dx, center.dy + w * 0.75, center.dx + w / 2, center.dy)
      ..close();
    c.drawPath(p, Paint()..color = const Color(0xFF9B2F3A));
    c.save();
    c.clipPath(p);
    c.drawOval(
      Rect.fromCenter(center: center + Offset(0, w * 0.5), width: w * 0.6, height: w * 0.4),
      Paint()..color = const Color(0xFFFF8FA3),
    );
    c.drawRect(Rect.fromLTWH(center.dx - w / 2, center.dy - 2, w, 5), Paint()..color = Colors.white);
    c.restore();
  }

  void _boy(Canvas c) {
    const shirt = Color(0xFF4FA8F5);
    // Cuerpo y brazos.
    _shape(c, Path()..addRRect(RRect.fromLTRBR(58, 150, 142, 232, const Radius.circular(30))), shirt);
    _shape(
      c,
      Path()..addRRect(RRect.fromLTRBR(82, 176, 118, 232, const Radius.circular(10))),
      const Color(0xFFFFC93C),
    );
    _capsule(c, const Offset(130, 170), const Offset(138, 200), 18, shirt);
    _circle(c, const Offset(139, 205), 10, _skin);
    _capsule(c, const Offset(70, 168), const Offset(52, 140), 20, shirt);
    _capsule(c, const Offset(52, 142), const Offset(42, 120), 15, _skin);
    brush(c, const Offset(42, 116), -0.35, 70, const Color(0xFF4FB3FF));
    _circle(c, const Offset(43, 116), 10, _skin);
    // Cabeza.
    _circle(c, const Offset(57, 108), 10, _skin);
    _circle(c, const Offset(143, 108), 10, _skin);
    _circle(c, const Offset(100, 104), 44, _skin);
    // Pelo con flequillo.
    final hair = Path()
      ..moveTo(56, 102)
      ..quadraticBezierTo(54, 58, 100, 52)
      ..quadraticBezierTo(146, 58, 145, 102)
      ..lineTo(134, 84)
      ..lineTo(122, 74)
      ..lineTo(112, 86)
      ..lineTo(100, 72)
      ..lineTo(88, 86)
      ..lineTo(76, 74)
      ..lineTo(66, 88)
      ..close()
      ..moveTo(92, 54)
      ..quadraticBezierTo(100, 34, 112, 46)
      ..quadraticBezierTo(104, 46, 102, 56)
      ..close();
    _shape(c, hair, const Color(0xFF8B4A24));
    _eyes(c, const Offset(84, 106), const Offset(116, 106));
    final brow = _line(const Color(0xFF6B3518), 2.6);
    c.drawArc(
      Rect.fromCenter(center: const Offset(84, 92), width: 14, height: 6),
      pi * 1.15,
      pi * 0.7,
      false,
      brow,
    );
    c.drawArc(
      Rect.fromCenter(center: const Offset(116, 92), width: 14, height: 6),
      pi * 1.15,
      pi * 0.7,
      false,
      brow,
    );
    c.drawCircle(const Offset(100, 118), 2.6, Paint()..color = const Color(0xFFE59F7A));
    _cheeks(c, const Offset(71, 122), const Offset(129, 122));
    _smile(c, const Offset(100, 125), 24);
    c.drawCircle(const Offset(126, 132), 3, Paint()..color = const Color(0xFF4FB3FF));
  }

  void _girl(Canvas c) {
    const dress = Color(0xFFFF8FB8);
    const hair = Color(0xFFA9552E);
    // Pelo de atrás y coletas.
    _circle(c, const Offset(212, 124), 17, hair);
    _circle(c, const Offset(308, 124), 17, hair);
    _shape(
      c,
      Path()..addOval(Rect.fromCenter(center: const Offset(260, 112), width: 104, height: 112)),
      hair,
    );
    // Cuerpo (vestido) y brazos.
    _shape(
      c,
      Path()
        ..moveTo(236, 150)
        ..lineTo(284, 150)
        ..quadraticBezierTo(306, 190, 304, 232)
        ..lineTo(216, 232)
        ..quadraticBezierTo(214, 190, 236, 150)
        ..close(),
      dress,
    );
    for (final dot in const [Offset(246, 196), Offset(272, 210), Offset(262, 180), Offset(286, 194)]) {
      c.drawCircle(dot, 3.4, Paint()..color = Colors.white.withValues(alpha: 0.75));
    }
    _capsule(c, const Offset(232, 170), const Offset(224, 200), 17, dress);
    _circle(c, const Offset(223, 205), 10, _skin);
    _capsule(c, const Offset(288, 166), const Offset(306, 140), 19, dress);
    _capsule(c, const Offset(306, 142), const Offset(318, 120), 14, _skin);
    brush(c, const Offset(318, 116), 0.4, 70, const Color(0xFFFF6B8B));
    _circle(c, const Offset(317, 116), 10, _skin);
    // Cabeza.
    _circle(c, const Offset(260, 106), 42, _skin);
    final bangs = Path()
      ..moveTo(218, 104)
      ..quadraticBezierTo(214, 62, 260, 58)
      ..quadraticBezierTo(306, 62, 302, 104)
      ..quadraticBezierTo(292, 80, 270, 78)
      ..quadraticBezierTo(250, 92, 228, 86)
      ..quadraticBezierTo(222, 94, 218, 104)
      ..close();
    _shape(c, bangs, hair);
    // Lazo.
    _shape(
      c,
      Path()
        ..moveTo(284, 62)
        ..lineTo(268, 48)
        ..lineTo(270, 74)
        ..close()
        ..moveTo(284, 62)
        ..lineTo(302, 50)
        ..lineTo(298, 76)
        ..close(),
      const Color(0xFFFF6B9E),
    );
    _circle(c, const Offset(284, 62), 6, const Color(0xFFFF4F8B));
    _eyes(c, const Offset(244, 108), const Offset(276, 108), lashes: true);
    c.drawCircle(const Offset(260, 120), 2.4, Paint()..color = const Color(0xFFE59F7A));
    _cheeks(c, const Offset(232, 124), const Offset(288, 124));
    _smile(c, const Offset(260, 127), 22);
    c.drawCircle(const Offset(236, 134), 3, Paint()..color = const Color(0xFFFF6B8B));
  }

  void _dog(Canvas c) {
    const fur = Color(0xFFFFF1DC);
    const ear = Color(0xFFB8763E);
    _oval(c, const Offset(180, 210), 84, 46, fur);
    _oval(c, const Offset(162, 226), 26, 14, fur);
    _oval(c, const Offset(198, 226), 26, 14, fur);
    // Collar.
    _shape(
      c,
      Path()..addRRect(RRect.fromLTRBR(146, 186, 214, 198, const Radius.circular(6))),
      const Color(0xFFE53935),
    );
    _circle(c, const Offset(180, 202), 6, const Color(0xFFFFC93C));
    // Orejas caídas.
    _shape(
      c,
      Path()
        ..moveTo(150, 136)
        ..quadraticBezierTo(126, 150, 134, 186)
        ..quadraticBezierTo(150, 190, 158, 156)
        ..close(),
      ear,
    );
    _shape(
      c,
      Path()
        ..moveTo(210, 136)
        ..quadraticBezierTo(234, 150, 226, 186)
        ..quadraticBezierTo(210, 190, 202, 156)
        ..close(),
      ear,
    );
    _oval(c, const Offset(180, 160), 80, 66, fur);
    c.drawCircle(
      const Offset(196, 154),
      13,
      Paint()..color = const Color(0xFFE9B07A).withValues(alpha: 0.85),
    );
    _eyes(c, const Offset(166, 155), const Offset(195, 155));
    _oval(c, const Offset(180, 176), 34, 24, Colors.white, outline: 0.8);
    _oval(c, const Offset(180, 168), 14, 10, const Color(0xFF3B2A22), outline: 0);
    c.drawCircle(const Offset(177, 166), 2, Paint()..color = Colors.white.withValues(alpha: 0.8));
    final mouth = _line(const Color(0xFF3B2A22), 1.8);
    c.drawLine(const Offset(180, 172), const Offset(180, 178), mouth);
    c.drawArc(Rect.fromCenter(center: const Offset(174, 178), width: 12, height: 8), 0, pi, false, mouth);
    c.drawArc(Rect.fromCenter(center: const Offset(186, 178), width: 12, height: 8), 0, pi, false, mouth);
    _oval(c, const Offset(180, 186), 9, 10, const Color(0xFFFF7FA0), outline: 0.8);
  }

  @override
  bool shouldRepaint(CharactersPainter oldDelegate) => false;
}

// --------------------------------------------------------------- fondo

/// Cielo, arcoíris, nubes, colinas y flores. Estático (se pinta una vez).
class SkyScenePainter extends CustomPainter {
  const SkyScenePainter();

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    canvas.drawRect(
      Offset.zero & size,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF8ED2FF), Color(0xFFC9ECFF), Color(0xFFFFF3E6)],
          stops: [0, 0.45, 1],
        ).createShader(Offset.zero & size),
    );
    // Arcoíris a los lados.
    const bands = [
      Color(0xFFFF8A80),
      Color(0xFFFFCC80),
      Color(0xFFFFF59D),
      Color(0xFFA5D6A7),
      Color(0xFF90CAF9),
      Color(0xFFCE93D8),
    ];
    void rainbow(Offset c, double r) {
      for (final (i, color) in bands.indexed) {
        canvas.drawCircle(c, r - i * r * 0.07, _line(color.withValues(alpha: 0.7), r * 0.07));
      }
    }

    rainbow(Offset(-w * 0.02, h * 0.42), w * 0.32);
    rainbow(Offset(w * 1.02, h * 0.4), w * 0.3);
    // Nubes.
    void cloud(Offset c, double s) {
      final p = Paint()..color = Colors.white;
      final shade = Paint()..color = const Color(0xFFDDEEFF);
      for (final (dx, dy, r) in [
        (-0.9, 0.15, 0.55),
        (-0.3, -0.2, 0.75),
        (0.4, -0.05, 0.65),
        (0.95, 0.2, 0.5),
      ]) {
        canvas.drawCircle(c + Offset(dx * s, dy * s + s * 0.08), r * s, shade);
      }
      for (final (dx, dy, r) in [
        (-0.9, 0.15, 0.55),
        (-0.3, -0.2, 0.75),
        (0.4, -0.05, 0.65),
        (0.95, 0.2, 0.5),
      ]) {
        canvas.drawCircle(c + Offset(dx * s, dy * s), r * s, p);
      }
    }

    cloud(Offset(w * 0.12, h * 0.07), w * 0.06);
    cloud(Offset(w * 0.86, h * 0.05), w * 0.05);
    cloud(Offset(w * 0.6, h * 0.28), w * 0.035);
    // Colinas al fondo.
    final hill = Path()
      ..moveTo(0, h * 0.5)
      ..quadraticBezierTo(w * 0.25, h * 0.4, w * 0.5, h * 0.48)
      ..quadraticBezierTo(w * 0.75, h * 0.4, w, h * 0.47)
      ..lineTo(w, h)
      ..lineTo(0, h)
      ..close();
    canvas.drawPath(
      hill,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFB6E59B), Color(0xFFDDF3C8)],
        ).createShader(Rect.fromLTWH(0, h * 0.4, w, h * 0.6)),
    );
    // Flores sueltas en las colinas.
    final rnd = Random(4);
    const petals = [Color(0xFFFF8FB8), Color(0xFFFFD54F), Color(0xFFB39DDB), Color(0xFFFF8A65)];
    for (var i = 0; i < 14; i++) {
      final x = rnd.nextDouble() * w;
      final y = h * (0.5 + rnd.nextDouble() * 0.48);
      if (x > w * 0.08 && x < w * 0.92 && y > h * 0.55) continue; // detrás del menú no se ven
      flower(canvas, Offset(x, y), w * 0.013, petals[i % petals.length]);
    }
  }

  @override
  bool shouldRepaint(SkyScenePainter oldDelegate) => false;
}

void flower(Canvas c, Offset o, double r, Color color) {
  for (var i = 0; i < 5; i++) {
    final a = i * 2 * pi / 5;
    c.drawCircle(o + Offset(cos(a), sin(a)) * r, r * 0.75, Paint()..color = color);
  }
  c.drawCircle(o, r * 0.6, Paint()..color = const Color(0xFFFFE082));
}

// --------------------------------------------------------------- adornos

/// Estrella sonriente (junto al título).
class SmilingStarPainter extends CustomPainter {
  const SmilingStarPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final s = min(size.width, size.height);
    final c = Offset(size.width / 2, size.height / 2);
    final p = Path();
    for (var i = 0; i < 10; i++) {
      final r = (i.isEven ? 0.5 : 0.23) * s;
      final a = -pi / 2 + i * pi / 5;
      final q = c + Offset(cos(a), sin(a)) * r;
      i == 0 ? p.moveTo(q.dx, q.dy) : p.lineTo(q.dx, q.dy);
    }
    p.close();
    canvas.drawPath(p.shift(Offset(0, s * 0.04)), Paint()..color = const Color(0x33000000));
    _shape(canvas, p, const Color(0xFFFFC93C), outline: s * 0.025);
    canvas.drawCircle(c + Offset(-s * 0.08, -s * 0.02), s * 0.035, Paint()..color = const Color(0xFF3B2A35));
    canvas.drawCircle(c + Offset(s * 0.08, -s * 0.02), s * 0.035, Paint()..color = const Color(0xFF3B2A35));
    canvas.drawArc(
      Rect.fromCenter(center: c + Offset(0, s * 0.05), width: s * 0.14, height: s * 0.1),
      0,
      pi,
      false,
      _line(const Color(0xFF3B2A35), s * 0.022),
    );
    final blush = Paint()..color = const Color(0xFFFF7FA0).withValues(alpha: 0.5);
    canvas.drawCircle(c + Offset(-s * 0.15, s * 0.05), s * 0.035, blush);
    canvas.drawCircle(c + Offset(s * 0.15, s * 0.05), s * 0.035, blush);
  }

  @override
  bool shouldRepaint(SmilingStarPainter oldDelegate) => false;
}

/// Pincel grande inclinado con gota de pintura (junto al título).
class TitleBrushPainter extends CustomPainter {
  const TitleBrushPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final s = min(size.width, size.height);
    brush(canvas, Offset(size.width * 0.32, size.height * 0.78), 0.65, s * 0.85, const Color(0xFF4FB3FF));
    _circle(
      canvas,
      Offset(size.width * 0.86, size.height * 0.42),
      s * 0.06,
      const Color(0xFF4FB3FF),
      outline: 0,
    );
  }

  @override
  bool shouldRepaint(TitleBrushPainter oldDelegate) => false;
}

// --------------------------------------------------------------- iconos

enum HomeIcon { palette, puzzle, bookBulb, frame, star, gear }

/// Iconos ilustrados de las tarjetas y botones (lienzo de diseño 100 × 100).
class HomeIconPainter extends CustomPainter {
  const HomeIconPainter(this.icon);

  final HomeIcon icon;

  @override
  void paint(Canvas canvas, Size size) {
    final k = min(size.width, size.height) / 100;
    canvas.save();
    canvas.translate((size.width - 100 * k) / 2, (size.height - 100 * k) / 2);
    canvas.scale(k);
    switch (icon) {
      case HomeIcon.palette:
        _palette(canvas);
      case HomeIcon.puzzle:
        _puzzle(canvas);
      case HomeIcon.bookBulb:
        _bookBulb(canvas);
      case HomeIcon.frame:
        _frame(canvas);
      case HomeIcon.star:
        const SmilingStarPainter().paint(canvas, const Size(100, 100));
      case HomeIcon.gear:
        _gear(canvas);
    }
    canvas.restore();
  }

  void _palette(Canvas c) {
    final p = Path()
      ..moveTo(50, 12)
      ..cubicTo(82, 12, 96, 36, 92, 56)
      ..cubicTo(88, 74, 70, 70, 66, 80)
      ..cubicTo(62, 92, 44, 92, 30, 86)
      ..cubicTo(8, 76, 4, 44, 18, 28)
      ..cubicTo(26, 18, 38, 12, 50, 12)
      ..close();
    _shape(c, p, const Color(0xFFF6D7A7), outline: 2);
    _circle(c, const Offset(36, 70), 7, const Color(0xFFFFF3E0), outline: 1.4);
    for (final (o, color) in const [
      (Offset(30, 40), Color(0xFFE53935)),
      (Offset(46, 28), Color(0xFFFFC93C)),
      (Offset(64, 30), Color(0xFF5CC689)),
      (Offset(76, 46), Color(0xFF4FB3FF)),
      (Offset(24, 56), Color(0xFF9B7BEA)),
    ]) {
      _circle(c, o, 7.5, color, outline: 1);
    }
    brush(c, const Offset(66, 88), 0.75, 52, const Color(0xFF4FB3FF));
  }

  /// Pieza de rompecabezas: cuadrado con dos salientes redondos (arriba y a
  /// la derecha).
  Path _piece(double x, double y, double s) {
    final k = s * 0.17;
    final square = Path()..addRect(Rect.fromLTWH(x, y, s, s));
    final knobs = Path()
      ..addOval(Rect.fromCircle(center: Offset(x + s / 2, y - k * 0.55), radius: k))
      ..addOval(Rect.fromCircle(center: Offset(x + s + k * 0.55, y + s / 2), radius: k));
    return Path.combine(PathOperation.union, square, knobs);
  }

  void _puzzle(Canvas c) {
    c.save();
    c.translate(50, 50);
    c.rotate(-0.25);
    c.translate(-50, -50);
    _shape(c, _piece(14, 34, 40), const Color(0xFF4FB3FF), outline: 2);
    _shape(c, _piece(50, 30, 38), const Color(0xFFFF6B9E), outline: 2);
    _shape(c, _piece(34, 66, 30), const Color(0xFFFFC93C), outline: 2);
    c.restore();
  }

  void _bookBulb(Canvas c) {
    // Libro abierto.
    final left = Path()
      ..moveTo(50, 62)
      ..quadraticBezierTo(32, 54, 10, 60)
      ..lineTo(10, 88)
      ..quadraticBezierTo(32, 82, 50, 90)
      ..close();
    final right = Path()
      ..moveTo(50, 62)
      ..quadraticBezierTo(68, 54, 90, 60)
      ..lineTo(90, 88)
      ..quadraticBezierTo(68, 82, 50, 90)
      ..close();
    _shape(
      c,
      Path()..addRRect(RRect.fromLTRBR(6, 62, 94, 94, const Radius.circular(6))),
      const Color(0xFF43A047),
      outline: 2,
    );
    _shape(c, left, const Color(0xFFFFFDF6), outline: 1.6);
    _shape(c, right, const Color(0xFFFFFDF6), outline: 1.6);
    final lines = _line(const Color(0xFFB0BEC5), 2);
    for (var i = 0; i < 3; i++) {
      c.drawLine(Offset(18, 68 + i * 6.0), Offset(42, 70 + i * 6.0), lines);
      c.drawLine(Offset(58, 70 + i * 6.0), Offset(82, 68 + i * 6.0), lines);
    }
    // Bombilla con rayos.
    final rays = _line(const Color(0xFFFFB300), 3);
    for (final a in [-2.6, -2.1, -1.57, -1.05, -0.55]) {
      c.drawLine(
        Offset(50 + cos(a) * 28, 30 + sin(a) * 28),
        Offset(50 + cos(a) * 36, 30 + sin(a) * 36),
        rays,
      );
    }
    _circle(c, const Offset(50, 28), 17, const Color(0xFFFFE066), outline: 2);
    _shape(
      c,
      Path()..addRRect(RRect.fromLTRBR(42, 42, 58, 54, const Radius.circular(3))),
      const Color(0xFF9AA5B1),
      outline: 1.4,
    );
    c.drawCircle(const Offset(44, 22), 4, Paint()..color = Colors.white.withValues(alpha: 0.8));
  }

  void _frame(Canvas c) {
    _shape(
      c,
      Path()..addRRect(RRect.fromLTRBR(8, 14, 92, 86, const Radius.circular(6))),
      const Color(0xFFF2B33D),
      outline: 2,
    );
    final inner = RRect.fromLTRBR(18, 24, 82, 76, const Radius.circular(3));
    c.save();
    c.clipRRect(inner);
    c.drawRRect(
      inner,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF81D4FA), Color(0xFFE1F5FE)],
        ).createShader(inner.outerRect),
    );
    _circle(c, const Offset(66, 36), 7, const Color(0xFFFFD54F), outline: 0);
    final m = Path()
      ..moveTo(18, 70)
      ..lineTo(40, 42)
      ..lineTo(56, 62)
      ..lineTo(66, 52)
      ..lineTo(82, 70)
      ..lineTo(82, 76)
      ..lineTo(18, 76)
      ..close();
    _shape(c, m, const Color(0xFF7E57C2), outline: 0);
    _shape(c, Path()..addOval(const Rect.fromLTRB(4, 64, 96, 100)), const Color(0xFF66BB6A), outline: 0);
    c.restore();
    c.drawRRect(inner, _line(const Color(0xFFB7791F), 2));
  }

  void _gear(Canvas c) {
    final p = Path();
    for (var i = 0; i < 16; i++) {
      final a = i * pi / 8;
      final r = i.isEven ? 44.0 : 34.0;
      final q = Offset(50 + cos(a) * r, 50 + sin(a) * r);
      i == 0 ? p.moveTo(q.dx, q.dy) : p.lineTo(q.dx, q.dy);
    }
    p
      ..close()
      ..addOval(Rect.fromCircle(center: const Offset(50, 50), radius: 14))
      ..fillType = PathFillType.evenOdd;
    _shape(c, p, const Color(0xFF64B5F6), outline: 2);
  }

  @override
  bool shouldRepaint(HomeIconPainter oldDelegate) => oldDelegate.icon != icon;
}
