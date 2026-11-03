import 'dart:math';

import 'package:flutter/material.dart';

import '../../screens/home/home_art.dart';

/// Ilustraciones originales de «Aprendo a Hablar», con el mismo volumen suave
/// (luz arriba a la izquierda) que las del inicio. Todas se dibujan en un
/// lienzo de 100 × 100 y se escalan, así que se ven nítidas a cualquier tamaño.

void _scaleTo100(Canvas canvas, Size size) {
  final s = min(size.width, size.height) / 100;
  canvas.translate((size.width - 100 * s) / 2, (size.height - 100 * s) / 2);
  canvas.scale(s);
}

/// Lolo, el lorito que acompaña al niño. [wing] (0-1) levanta el ala para
/// saludar; [beakOpen] (0-1) abre el pico al hablar.
class LoloPainter extends CustomPainter {
  const LoloPainter({this.wing = 0, this.beakOpen = 0});

  final double wing;
  final double beakOpen;

  static const green = Color(0xFF43C46A);
  static const darkGreen = Color(0xFF2E9E57);
  static const yellow = Color(0xFFFFD54F);
  static const red = Color(0xFFFF5A5F);
  static const blue = Color(0xFF42A5F5);
  static const orange = Color(0xFFFF9F1C);

  @override
  void paint(Canvas canvas, Size size) {
    _scaleTo100(canvas, size);
    // Cola: plumas azules y rojas.
    for (final (dx, color, a) in [(-5.0, blue, 0.25), (0.0, red, 0.0), (5.0, blue, -0.25)]) {
      oval3d(canvas, Offset(50 + dx, 88), 9, 22, color, angle: a);
    }
    // Patas.
    for (final x in [42.0, 58.0]) {
      oval3d(canvas, Offset(x, 86), 11, 6, orange);
    }
    // Cuerpo y barriga.
    oval3d(canvas, const Offset(50, 62), 46, 52, green);
    oval3d(canvas, const Offset(52, 68), 27, 32, yellow, outline: 0);
    // Ala (se levanta al saludar).
    canvas.save();
    canvas.translate(31, 50);
    canvas.rotate(0.25 + wing * 1.5);
    oval3d(canvas, const Offset(0, 12), 18, 34, darkGreen);
    for (final (y, color) in [(24.0, blue), (28.0, red)]) {
      oval3d(canvas, Offset(0, y), 12, 9, color, outline: 0.8);
    }
    canvas.restore();
    // Penacho.
    for (final (o, a, color) in [
      (const Offset(43, 11), -0.5, red),
      (const Offset(50, 7), 0.0, orange),
      (const Offset(57, 11), 0.5, red),
    ]) {
      oval3d(canvas, o, 7, 16, color, angle: a);
    }
    // Cabeza.
    circle3d(canvas, const Offset(50, 30), 21, green);
    // Mejilla clara alrededor del ojo y rubor.
    oval3d(canvas, const Offset(58, 29), 22, 20, const Color(0xFFFFF6DE), outline: 0);
    canvas.drawOval(
      Rect.fromCenter(center: const Offset(51, 39), width: 8, height: 5),
      Paint()..color = const Color(0x66FF6B8B),
    );
    // Ojo con brillo.
    canvas.drawCircle(const Offset(60, 28), 5.2, Paint()..color = const Color(0xFF2B2440));
    canvas.drawCircle(const Offset(61.8, 26.2), 1.8, Paint()..color = Colors.white);
    // Pico (curvo, de loro): mandíbula de abajo y la de arriba encima.
    final lower = Path()
      ..moveTo(66, 36 + beakOpen * 2)
      ..quadraticBezierTo(73, 38 + beakOpen * 5, 67, 43 + beakOpen * 4)
      ..quadraticBezierTo(63, 41 + beakOpen * 3, 64, 37 + beakOpen * 2)
      ..close();
    shape3d(canvas, lower, const Color(0xFFE07B00), outline: 1);
    final upper = Path()
      ..moveTo(64, 26)
      ..quadraticBezierTo(80, 26, 76, 41)
      ..quadraticBezierTo(73, 36, 65, 37)
      ..close();
    shape3d(canvas, upper, orange, outline: 1.2);
  }

  @override
  bool shouldRepaint(LoloPainter old) => old.wing != wing || old.beakOpen != beakOpen;
}

/// Carita redonda con una emoción.
class EmotionFacePainter extends CustomPainter {
  const EmotionFacePainter(this.emotion);

  final String emotion;

  static final _ink = Paint()
    ..color = const Color(0xFF3B3355)
    ..style = PaintingStyle.stroke
    ..strokeWidth = 3.2
    ..strokeCap = StrokeCap.round;
  static final _fill = Paint()..color = const Color(0xFF3B3355);

  @override
  void paint(Canvas canvas, Size size) {
    _scaleTo100(canvas, size);
    final face = switch (emotion) {
      'enojado' => const Color(0xFFFF8A65),
      'enfermo' => const Color(0xFFC5E1A5),
      'triste' => const Color(0xFF90CAF9),
      'tranquilo' => const Color(0xFFB2EBF2),
      _ => const Color(0xFFFFD54F),
    };
    circle3d(canvas, const Offset(50, 52), 40, face, outline: 2);
    const le = Offset(36, 44), re = Offset(64, 44);

    void dotEyes() {
      canvas.drawCircle(le, 4.5, _fill);
      canvas.drawCircle(re, 4.5, _fill);
    }

    void wideEyes() {
      for (final e in [le, re]) {
        canvas.drawCircle(e, 8, Paint()..color = Colors.white);
        canvas.drawCircle(e, 8, _ink..strokeWidth = 2.4);
        canvas.drawCircle(e, 3.5, _fill);
      }
      _ink.strokeWidth = 3.2;
    }

    void brows(double inner, double outer, {double y = 32}) {
      canvas.drawLine(Offset(le.dx - 8, y + outer), Offset(le.dx + 7, y + inner), _ink);
      canvas.drawLine(Offset(re.dx + 8, y + outer), Offset(re.dx - 7, y + inner), _ink);
    }

    void mouth(double curve, {double width = 26, double y = 68}) {
      final p = Path()
        ..moveTo(50 - width / 2, y)
        ..quadraticBezierTo(50, y + curve, 50 + width / 2, y);
      canvas.drawPath(p, _ink);
    }

    void blush() {
      for (final x in [27.0, 73.0]) {
        canvas.drawOval(
          Rect.fromCenter(center: Offset(x, 60), width: 11, height: 6),
          Paint()..color = const Color(0x55FF5A7A),
        );
      }
    }

    switch (emotion) {
      case 'feliz':
        dotEyes();
        blush();
        final p = Path()
          ..moveTo(34, 63)
          ..quadraticBezierTo(50, 84, 66, 63)
          ..close();
        canvas.drawPath(p, Paint()..color = const Color(0xFF8E2A3A));
        canvas.drawPath(p, _ink);
      case 'triste':
        dotEyes();
        brows(-5, 3);
        mouth(-12, y: 74);
        // Lagrimita.
        final tear = Path()
          ..moveTo(64, 52)
          ..quadraticBezierTo(60, 60, 64, 62)
          ..quadraticBezierTo(68, 60, 64, 52);
        canvas.drawPath(tear, Paint()..color = const Color(0xFF1E88E5));
      case 'enojado':
        dotEyes();
        brows(6, -3, y: 33);
        mouth(-9, width: 24, y: 72);
      case 'asustado':
        wideEyes();
        brows(-4, 0, y: 28);
        final p = Path()
          ..moveTo(38, 72)
          ..cubicTo(42, 66, 46, 78, 50, 72)
          ..cubicTo(54, 66, 58, 78, 62, 72);
        canvas.drawPath(p, _ink);
      case 'sorprendido':
        wideEyes();
        brows(-3, -3, y: 27);
        canvas.drawOval(
          Rect.fromCenter(center: const Offset(50, 72), width: 14, height: 18),
          Paint()..color = const Color(0xFF8E2A3A),
        );
        canvas.drawOval(Rect.fromCenter(center: const Offset(50, 72), width: 14, height: 18), _ink);
      case 'cansado':
        for (final e in [le, re]) {
          canvas.drawLine(e - const Offset(7, 0), e + const Offset(7, 0), _ink);
          canvas.drawArc(Rect.fromCircle(center: e, radius: 7), 0, pi, false, _ink..strokeWidth = 2);
        }
        _ink.strokeWidth = 3.2;
        canvas.drawOval(Rect.fromCenter(center: const Offset(50, 72), width: 10, height: 7), _fill);
        _zzz(canvas);
      case 'tranquilo':
        for (final e in [le, re]) {
          canvas.drawArc(
            Rect.fromCircle(center: e + const Offset(0, -2), radius: 6),
            0.2,
            pi - 0.4,
            false,
            _ink,
          );
        }
        blush();
        mouth(8, width: 20);
      case 'aburrido':
        for (final e in [le, re]) {
          canvas.drawCircle(e + const Offset(0, 2), 4, _fill);
          canvas.drawLine(e - const Offset(8, 1), e + const Offset(8, -1), _ink);
        }
        mouth(0, width: 22, y: 70);
      case 'enfermo':
        for (final e in [le, re]) {
          canvas.drawLine(e - const Offset(5, 5), e + const Offset(5, 5), _ink);
          canvas.drawLine(e + const Offset(-5, 5), e + const Offset(5, -5), _ink);
        }
        final p = Path()
          ..moveTo(36, 72)
          ..cubicTo(41, 66, 45, 78, 50, 72)
          ..cubicTo(55, 66, 59, 78, 64, 72);
        canvas.drawPath(p, _ink);
        // Gotita de sudor.
        final drop = Path()
          ..moveTo(80, 30)
          ..quadraticBezierTo(75, 39, 80, 41)
          ..quadraticBezierTo(85, 39, 80, 30);
        canvas.drawPath(drop, Paint()..color = const Color(0xFF64B5F6));
      case 'carinoso':
        for (final e in [le, re]) {
          _heart(canvas, e, 7, const Color(0xFFE53950));
        }
        blush();
        mouth(12, width: 24);
    }
  }

  static void _heart(Canvas c, Offset o, double r, Color color) {
    final p = Path()
      ..moveTo(o.dx, o.dy + r)
      ..cubicTo(o.dx - r * 1.6, o.dy - r * 0.2, o.dx - r * 0.7, o.dy - r * 1.4, o.dx, o.dy - r * 0.45)
      ..cubicTo(o.dx + r * 0.7, o.dy - r * 1.4, o.dx + r * 1.6, o.dy - r * 0.2, o.dx, o.dy + r);
    shape3d(c, p, color, outline: 0);
  }

  static void _zzz(Canvas c) {
    final p = Paint()
      ..color = const Color(0xFF5C6BC0)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.4
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    for (final (o, s) in [(const Offset(76, 14), 9.0), (const Offset(88, 4), 6.0)]) {
      c.drawPath(
        Path()
          ..moveTo(o.dx, o.dy)
          ..lineTo(o.dx + s, o.dy)
          ..lineTo(o.dx, o.dy + s)
          ..lineTo(o.dx + s, o.dy + s),
        p,
      );
    }
  }

  @override
  bool shouldRepaint(EmotionFacePainter old) => old.emotion != emotion;
}

/// Niño con una parte del cuerpo resaltada (las demás, más claras). Para las
/// partes de la cara se dibuja la cara de cerca.
class BodyPartPainter extends CustomPainter {
  const BodyPartPainter(this.part);

  final String part;

  static const faceParts = {'pelo', 'ojos', 'nariz', 'boca', 'orejas'};
  static const highlight = Color(0xFFFF4F8B);

  static const skin = Color(0xFFF5C7A1);
  static const hair = Color(0xFF7B4A2E);
  static const shirt = Color(0xFF64B5F6);
  static const pants = Color(0xFF7986CB);
  static const shoes = Color(0xFFFF8A65);

  @override
  void paint(Canvas canvas, Size size) {
    _scaleTo100(canvas, size);
    final parts = faceParts.contains(part) ? _face() : _body();
    // Primero todo en suave; después la parte elegida, entera y rodeada por un
    // anillo rosa que la señala.
    canvas.saveLayer(const Rect.fromLTWH(0, 0, 100, 100), Paint()..color = const Color(0x8C000000));
    for (final MapEntry(key: name, value: draw) in parts.entries) {
      if (name != part) draw(canvas);
    }
    canvas.restore();
    final chosen = parts[part];
    if (chosen == null) return;
    chosen(canvas);
    for (final r in _rings[part] ?? const <Rect>[]) {
      final ring = RRect.fromRectAndRadius(r, Radius.circular(min(r.width, r.height) / 2));
      canvas.drawRRect(
        ring,
        Paint()
          ..color = highlight.withValues(alpha: 0.35)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 6,
      );
      canvas.drawRRect(
        ring,
        Paint()
          ..color = highlight
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.6,
      );
    }
  }

  /// Dónde se dibuja el anillo que señala cada parte.
  static const _rings = <String, List<Rect>>{
    'cabeza': [Rect.fromLTRB(32, 4, 68, 40)],
    'brazos': [Rect.fromLTRB(16, 34, 42, 66), Rect.fromLTRB(58, 34, 84, 66)],
    'manos': [Rect.fromLTRB(15, 55, 33, 73), Rect.fromLTRB(67, 55, 85, 73)],
    'piernas': [Rect.fromLTRB(35, 61, 65, 91)],
    'pies': [Rect.fromLTRB(30, 83, 52, 97), Rect.fromLTRB(48, 83, 70, 97)],
    'pelo': [Rect.fromLTRB(12, 8, 88, 46)],
    'ojos': [Rect.fromLTRB(29, 40, 71, 60)],
    'nariz': [Rect.fromLTRB(41, 54, 59, 70)],
    'boca': [Rect.fromLTRB(35, 64, 65, 82)],
    'orejas': [Rect.fromLTRB(5, 39, 31, 65), Rect.fromLTRB(69, 39, 95, 65)],
  };

  Map<String, void Function(Canvas)> _body() => {
    'piernas': (c) {
      capsule3d(c, const Offset(44, 64), const Offset(43, 86), 9, pants);
      capsule3d(c, const Offset(56, 64), const Offset(57, 86), 9, pants);
    },
    'pies': (c) {
      oval3d(c, const Offset(41, 90), 14, 7, shoes);
      oval3d(c, const Offset(59, 90), 14, 7, shoes);
    },
    'brazos': (c) {
      capsule3d(c, const Offset(37, 41), const Offset(25, 61), 8, shirt);
      capsule3d(c, const Offset(63, 41), const Offset(75, 61), 8, shirt);
    },
    'cuerpo': (c) {
      shape3d(c, Path()..addRRect(RRect.fromLTRBR(35, 36, 65, 68, const Radius.circular(10))), shirt);
    },
    'manos': (c) {
      circle3d(c, const Offset(24, 64), 5.5, skin);
      circle3d(c, const Offset(76, 64), 5.5, skin);
    },
    'cabeza': (c) {
      circle3d(c, const Offset(50, 22), 14, skin);
      shape3d(
        c,
        Path()
          ..addArc(Rect.fromCircle(center: const Offset(50, 21), radius: 14.5), pi, pi)
          ..close(),
        hair,
        outline: 0.8,
      );
      c.drawCircle(const Offset(45, 24), 1.8, Paint()..color = const Color(0xFF3B3355));
      c.drawCircle(const Offset(55, 24), 1.8, Paint()..color = const Color(0xFF3B3355));
      c.drawArc(
        Rect.fromCenter(center: const Offset(50, 28), width: 8, height: 5),
        0.2,
        pi - 0.4,
        false,
        Paint()
          ..color = const Color(0xFF3B3355)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.4
          ..strokeCap = StrokeCap.round,
      );
    },
  };

  Map<String, void Function(Canvas)> _face() => {
    'orejas': (c) {
      circle3d(c, const Offset(18, 52), 9, skin);
      circle3d(c, const Offset(82, 52), 9, skin);
    },
    'cara': (c) => circle3d(c, const Offset(50, 54), 32, skin, outline: 1.6),
    'pelo': (c) {
      final p = Path()
        ..moveTo(18, 50)
        ..cubicTo(14, 18, 40, 10, 52, 14)
        ..cubicTo(70, 10, 88, 22, 82, 50)
        ..cubicTo(76, 34, 66, 28, 56, 34)
        ..cubicTo(48, 24, 30, 30, 18, 50)
        ..close();
      shape3d(c, p, hair);
    },
    'ojos': (c) {
      for (final x in [39.0, 61.0]) {
        c.drawOval(
          Rect.fromCenter(center: Offset(x, 50), width: 12, height: 13),
          Paint()..color = Colors.white,
        );
        c.drawCircle(Offset(x, 51), 4.5, Paint()..color = const Color(0xFF4E342E));
        c.drawCircle(Offset(x + 1.5, 49.5), 1.5, Paint()..color = Colors.white);
        c.drawOval(
          Rect.fromCenter(center: Offset(x, 50), width: 12, height: 13),
          Paint()
            ..color = const Color(0xFF3B3355)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.4,
        );
      }
    },
    'nariz': (c) => oval3d(c, const Offset(50, 62), 9, 7, const Color(0xFFEDA98A)),
    'boca': (c) {
      final p = Path()
        ..moveTo(40, 71)
        ..quadraticBezierTo(50, 82, 60, 71)
        ..close();
      c.drawPath(p, Paint()..color = const Color(0xFFC2185B));
      c.drawPath(
        p,
        Paint()
          ..color = const Color(0xFF3B3355)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.6
          ..strokeJoin = StrokeJoin.round,
      );
    },
  };

  @override
  bool shouldRepaint(BodyPartPainter old) => old.part != part;
}

/// Mancha de pintura de un color (para aprender los colores).
class PaintSplashPainter extends CustomPainter {
  const PaintSplashPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    _scaleTo100(canvas, size);
    final p = Path();
    const n = 9;
    for (var i = 0; i <= n * 2; i++) {
      final a = i * pi / n;
      final r = i.isEven ? 38.0 : 30.0 + (i % 3) * 3;
      final o = Offset(50 + cos(a) * r, 50 + sin(a) * r);
      if (i == 0) {
        p.moveTo(o.dx, o.dy);
      } else {
        final prev = (i - 1) * pi / n;
        final c = Offset(50 + cos((a + prev) / 2) * 44, 50 + sin((a + prev) / 2) * 44);
        p.quadraticBezierTo(c.dx, c.dy, o.dx, o.dy);
      }
    }
    p.close();
    final light = color.computeLuminance() > 0.8;
    canvas.drawPath(p.shift(const Offset(0, 3)), Paint()..color = const Color(0x22000000));
    shape3d(canvas, p, color, outline: light ? 2.2 : 1.6);
    if (light) {
      canvas.drawPath(
        p,
        Paint()
          ..color = const Color(0xFFB0A8C0)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }
    // Gotitas.
    for (final (o, r) in [
      (const Offset(88, 22), 5.0),
      (const Offset(14, 80), 4.0),
      (const Offset(86, 84), 3.0),
    ]) {
      circle3d(canvas, o, r, color, outline: light ? 1.4 : 0.8);
    }
  }

  @override
  bool shouldRepaint(PaintSplashPainter old) => old.color != color;
}
