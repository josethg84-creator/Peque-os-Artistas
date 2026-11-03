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
      case 'emocionado':
        dotEyes();
        blush();
        final p = Path()
          ..moveTo(32, 62)
          ..quadraticBezierTo(50, 88, 68, 62)
          ..close();
        canvas.drawPath(p, Paint()..color = const Color(0xFF8E2A3A));
        canvas.drawPath(p, _ink);
        for (final o in const [Offset(14, 18), Offset(86, 16)]) {
          _heart(canvas, o, 6, const Color(0xFFFFC93C));
        }
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

/// Un niño o una niña (estilo chibi con volumen) con una emoción en la cara.
/// Personaje de cuentos, conversaciones y ejercicios.
class KidPainter extends CustomPainter {
  const KidPainter({
    this.girl = false,
    this.shirt = const Color(0xFF64B5F6),
    this.hair = const Color(0xFF7B4A2E),
    this.emotion = 'feliz',
    this.armsUp = false,
  });

  final bool girl;
  final Color shirt;
  final Color hair;
  final String emotion;

  /// Brazos levantados (saluda, celebra, se sorprende).
  final bool armsUp;

  static const skin = Color(0xFFF5C7A1);
  static const pants = Color(0xFF7986CB);
  static const shoes = Color(0xFFFF8A65);

  @override
  void paint(Canvas canvas, Size size) {
    _scaleTo100(canvas, size);
    // Piernas y zapatos.
    capsule3d(canvas, const Offset(44, 74), const Offset(44, 88), 8, girl ? skin : pants);
    capsule3d(canvas, const Offset(56, 74), const Offset(56, 88), 8, girl ? skin : pants);
    oval3d(canvas, const Offset(42, 92), 12, 6, shoes);
    oval3d(canvas, const Offset(58, 92), 12, 6, shoes);
    // Brazos.
    final up = armsUp || emotion == 'sorprendido' || emotion == 'emocionado';
    for (final side in [-1.0, 1.0]) {
      final from = Offset(50 + side * 12, 58);
      final to = up ? Offset(50 + side * 24, 40) : Offset(50 + side * 21, 72);
      capsule3d(canvas, from, to, 7, shirt);
      circle3d(canvas, to, 4.5, skin);
    }
    // Cuerpo: camiseta o vestido.
    if (girl) {
      shape3d(
        canvas,
        Path()
          ..moveTo(40, 52)
          ..lineTo(60, 52)
          ..lineTo(68, 78)
          ..quadraticBezierTo(50, 82, 32, 78)
          ..close(),
        shirt,
      );
    } else {
      shape3d(canvas, Path()..addRRect(RRect.fromLTRBR(37, 52, 63, 78, const Radius.circular(8))), shirt);
    }
    // Coletas (detrás de la cabeza).
    if (girl) {
      circle3d(canvas, const Offset(29, 32), 7, hair);
      circle3d(canvas, const Offset(71, 32), 7, hair);
    }
    // Cabeza y pelo.
    circle3d(canvas, const Offset(50, 34), 18, skin);
    shape3d(
      canvas,
      Path()
        ..moveTo(32, 33)
        ..cubicTo(30, 12, 70, 10, 68, 33)
        ..cubicTo(62, 24, 54, 22, 50, 26)
        ..cubicTo(44, 21, 37, 25, 32, 33)
        ..close(),
      hair,
      outline: 1,
    );
    _face(canvas);
  }

  void _face(Canvas canvas) {
    final ink = Paint()
      ..color = const Color(0xFF3B3355)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8
      ..strokeCap = StrokeCap.round;
    final dot = Paint()..color = const Color(0xFF3B3355);
    const le = Offset(43, 35), re = Offset(57, 35);
    // Mejillas.
    for (final x in [39.0, 61.0]) {
      canvas.drawOval(
        Rect.fromCenter(center: Offset(x, 41), width: 6, height: 3.5),
        Paint()..color = const Color(0x55FF6B8B),
      );
    }
    void mouth(double curve, {double w = 10, double y = 43}) => canvas.drawPath(
      Path()
        ..moveTo(50 - w / 2, y)
        ..quadraticBezierTo(50, y + curve, 50 + w / 2, y),
      ink,
    );
    switch (emotion) {
      case 'triste':
        canvas.drawCircle(le, 2, dot);
        canvas.drawCircle(re, 2, dot);
        canvas.drawLine(le + const Offset(-3, -3), le + const Offset(3, -5), ink);
        canvas.drawLine(re + const Offset(3, -3), re + const Offset(-3, -5), ink);
        mouth(-4, y: 45);
      case 'enojado':
        canvas.drawCircle(le, 2, dot);
        canvas.drawCircle(re, 2, dot);
        canvas.drawLine(le + const Offset(-3, -5), le + const Offset(3, -3), ink);
        canvas.drawLine(re + const Offset(3, -5), re + const Offset(-3, -3), ink);
        mouth(-3, w: 8, y: 45);
      case 'asustado' || 'sorprendido':
        for (final e in [le, re]) {
          canvas.drawCircle(e, 3.4, Paint()..color = Colors.white);
          canvas.drawCircle(e, 3.4, ink..strokeWidth = 1.2);
          canvas.drawCircle(e, 1.6, dot);
        }
        ink.strokeWidth = 1.8;
        canvas.drawOval(Rect.fromCenter(center: const Offset(50, 45), width: 6, height: 7), dot);
      case 'cansado':
        for (final e in [le, re]) {
          canvas.drawLine(e - const Offset(3, 0), e + const Offset(3, 0), ink);
        }
        canvas.drawOval(Rect.fromCenter(center: const Offset(50, 45), width: 4, height: 3), dot);
      case 'tranquilo':
        for (final e in [le, re]) {
          canvas.drawArc(Rect.fromCircle(center: e, radius: 3), 0.3, pi - 0.6, false, ink);
        }
        mouth(3);
      default: // feliz, emocionado
        canvas.drawCircle(le, 2.2, dot);
        canvas.drawCircle(re, 2.2, dot);
        final p = Path()
          ..moveTo(44, 42)
          ..quadraticBezierTo(50, 50, 56, 42)
          ..close();
        canvas.drawPath(p, Paint()..color = const Color(0xFF8E2A3A));
        if (emotion == 'emocionado') {
          for (final o in [const Offset(24, 16), const Offset(78, 14)]) {
            canvas.drawPath(
              Path()
                ..moveTo(o.dx, o.dy - 5)
                ..lineTo(o.dx + 1.5, o.dy - 1.5)
                ..lineTo(o.dx + 5, o.dy)
                ..lineTo(o.dx + 1.5, o.dy + 1.5)
                ..lineTo(o.dx, o.dy + 5)
                ..lineTo(o.dx - 1.5, o.dy + 1.5)
                ..lineTo(o.dx - 5, o.dy)
                ..lineTo(o.dx - 1.5, o.dy - 1.5)
                ..close(),
              Paint()..color = const Color(0xFFFFC93C),
            );
          }
        }
    }
  }

  @override
  bool shouldRepaint(KidPainter old) =>
      old.girl != girl ||
      old.shirt != shirt ||
      old.hair != hair ||
      old.emotion != emotion ||
      old.armsUp != armsUp;
}

/// Fondos de las escenas (pastel, con volumen suave).
class SceneBackgroundPainter extends CustomPainter {
  const SceneBackgroundPainter(this.kind);

  final String kind;

  static const kinds = {
    'jardin',
    'parque',
    'bosque',
    'playa',
    'noche',
    'lluvia',
    'cielo',
    'casa',
    'cocina',
    'dormitorio',
    'escuela',
  };

  @override
  void paint(Canvas canvas, Size size) {
    _scaleTo100(canvas, size);
    const r = Rect.fromLTWH(0, 0, 100, 100);
    canvas.clipRRect(RRect.fromRectAndRadius(r, const Radius.circular(12)));
    void sky(List<Color> c) => canvas.drawRect(
      r,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: c,
        ).createShader(r),
    );
    void ground(Color c, {double y = 68}) {
      final p = Path()
        ..moveTo(0, y)
        ..quadraticBezierTo(50, y - 8, 100, y)
        ..lineTo(100, 100)
        ..lineTo(0, 100)
        ..close();
      shape3d(canvas, p, c, outline: 0);
    }

    void cloud(Offset o, double s) {
      for (final (dx, dy, rr) in [(-6.0, 1.0, 5.0), (0.0, -2.0, 6.5), (6.0, 1.0, 5.0)]) {
        canvas.drawCircle(
          o + Offset(dx * s, dy * s),
          rr * s,
          Paint()..color = Colors.white.withValues(alpha: 0.9),
        );
      }
    }

    void tree(Offset base, double s) {
      capsule3d(canvas, base, base - Offset(0, 16 * s), 5 * s, const Color(0xFF8D6E63));
      for (final (dx, dy, rr) in [(-6.0, -20.0, 8.0), (6.0, -20.0, 8.0), (0.0, -27.0, 9.0)]) {
        circle3d(canvas, base + Offset(dx * s, dy * s), rr * s, const Color(0xFF66BB6A), outline: 0.6);
      }
    }

    void wall(Color c, Color floor) {
      canvas.drawRect(r, Paint()..color = c);
      canvas.drawRect(const Rect.fromLTWH(0, 70, 100, 30), Paint()..color = floor);
      canvas.drawLine(
        const Offset(0, 70),
        const Offset(100, 70),
        Paint()
          ..color = const Color(0x22000000)
          ..strokeWidth = 1.2,
      );
    }

    void window(Rect w, List<Color> view) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(w.inflate(2), const Radius.circular(3)),
        Paint()..color = Colors.white,
      );
      canvas.drawRect(
        w,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: view,
          ).createShader(w),
      );
      final f = Paint()
        ..color = Colors.white
        ..strokeWidth = 1.6;
      canvas.drawLine(Offset(w.center.dx, w.top), Offset(w.center.dx, w.bottom), f);
      canvas.drawLine(Offset(w.left, w.center.dy), Offset(w.right, w.center.dy), f);
    }

    switch (kind) {
      case 'noche':
        sky(const [Color(0xFF283593), Color(0xFF5C6BC0)]);
        circle3d(canvas, const Offset(78, 20), 9, const Color(0xFFFFF59D), outline: 0);
        for (final o in const [
          Offset(15, 15),
          Offset(35, 25),
          Offset(55, 12),
          Offset(25, 40),
          Offset(65, 35),
          Offset(90, 45),
        ]) {
          canvas.drawCircle(o, 1.3, Paint()..color = Colors.white);
        }
        ground(const Color(0xFF33691E));
      case 'lluvia':
        sky(const [Color(0xFF90A4AE), Color(0xFFCFD8DC)]);
        cloud(const Offset(30, 18), 1.6);
        cloud(const Offset(72, 14), 1.4);
        final drop = Paint()
          ..color = const Color(0xFF64B5F6)
          ..strokeWidth = 1.4
          ..strokeCap = StrokeCap.round;
        for (var i = 0; i < 14; i++) {
          final o = Offset(6.0 + i * 7, 30.0 + (i % 3) * 10);
          canvas.drawLine(o, o + const Offset(-2, 5), drop);
        }
        ground(const Color(0xFF81C784));
      case 'playa':
        sky(const [Color(0xFF81D4FA), Color(0xFFE1F5FE)]);
        circle3d(canvas, const Offset(80, 18), 8, const Color(0xFFFFD54F), outline: 0);
        canvas.drawRect(const Rect.fromLTWH(0, 50, 100, 22), Paint()..color = const Color(0xFF4FC3F7));
        ground(const Color(0xFFFFE0B2), y: 72);
      case 'cielo':
        sky(const [Color(0xFF64B5F6), Color(0xFFBBDEFB)]);
        cloud(const Offset(25, 25), 1.4);
        cloud(const Offset(70, 55), 1.7);
        cloud(const Offset(80, 15), 1.0);
      case 'bosque':
        sky(const [Color(0xFFB3E5FC), Color(0xFFE8F5E9)]);
        ground(const Color(0xFF81C784));
        tree(const Offset(14, 74), 1.1);
        tree(const Offset(86, 72), 1.2);
        tree(const Offset(66, 64), 0.8);
      case 'parque':
        sky(const [Color(0xFF90CAF9), Color(0xFFE3F2FD)]);
        cloud(const Offset(22, 16), 1.1);
        ground(const Color(0xFF9CCC65));
        tree(const Offset(85, 72), 1.1);
        // Columpio.
        final post = Paint()
          ..color = const Color(0xFFE57373)
          ..strokeWidth = 2.2
          ..strokeCap = StrokeCap.round;
        canvas.drawLine(const Offset(8, 70), const Offset(14, 44), post);
        canvas.drawLine(const Offset(30, 70), const Offset(24, 44), post);
        canvas.drawLine(const Offset(13, 44), const Offset(25, 44), post);
      case 'casa':
        wall(const Color(0xFFFFF3E0), const Color(0xFFD7B899));
        window(const Rect.fromLTWH(62, 16, 26, 24), const [Color(0xFF81D4FA), Color(0xFFE1F5FE)]);
        canvas.drawRRect(
          RRect.fromLTRBR(10, 20, 30, 36, const Radius.circular(2)),
          Paint()..color = const Color(0xFFFFCC80),
        );
      case 'cocina':
        wall(const Color(0xFFE0F7FA), const Color(0xFFBCAAA4));
        window(const Rect.fromLTWH(38, 14, 24, 20), const [Color(0xFF81D4FA), Color(0xFFE1F5FE)]);
        shape3d(
          canvas,
          Path()..addRRect(RRect.fromLTRBR(0, 56, 100, 70, const Radius.circular(2))),
          const Color(0xFFFFCC80),
          outline: 0.8,
        );
      case 'dormitorio':
        wall(const Color(0xFFEDE7F6), const Color(0xFFD1C4E9));
        window(const Rect.fromLTWH(64, 14, 24, 22), const [Color(0xFF283593), Color(0xFF5C6BC0)]);
        shape3d(
          canvas,
          Path()..addRRect(RRect.fromLTRBR(6, 58, 56, 76, const Radius.circular(5))),
          const Color(0xFF9FA8DA),
        );
        shape3d(
          canvas,
          Path()..addRRect(RRect.fromLTRBR(8, 52, 22, 60, const Radius.circular(4))),
          Colors.white,
        );
      case 'escuela':
        wall(const Color(0xFFFFF8E1), const Color(0xFFBCAAA4));
        shape3d(
          canvas,
          Path()..addRRect(RRect.fromLTRBR(18, 12, 82, 44, const Radius.circular(3))),
          const Color(0xFF2E7D32),
          outline: 1.6,
        );
        final chalk = Paint()
          ..color = Colors.white
          ..strokeWidth = 1.2
          ..strokeCap = StrokeCap.round;
        canvas.drawLine(const Offset(26, 22), const Offset(46, 22), chalk);
        canvas.drawLine(const Offset(26, 30), const Offset(60, 30), chalk);
        canvas.drawLine(const Offset(26, 37), const Offset(40, 37), chalk);
      default: // jardin
        sky(const [Color(0xFF90CAF9), Color(0xFFE3F2FD)]);
        circle3d(canvas, const Offset(82, 16), 8, const Color(0xFFFFD54F), outline: 0);
        cloud(const Offset(28, 18), 1.2);
        ground(const Color(0xFF9CCC65));
        for (final (o, c) in [
          (const Offset(10, 84), const Color(0xFFF06292)),
          (const Offset(90, 86), const Color(0xFFFFD54F)),
          (const Offset(20, 94), const Color(0xFFBA68C8)),
        ]) {
          for (var k = 0; k < 5; k++) {
            final a = k * 2 * pi / 5;
            canvas.drawCircle(o + Offset(cos(a) * 2.6, sin(a) * 2.6), 2, Paint()..color = c);
          }
          canvas.drawCircle(o, 1.6, Paint()..color = const Color(0xFFFFF59D));
        }
    }
  }

  @override
  bool shouldRepaint(SceneBackgroundPainter old) => old.kind != kind;
}

/// Un zapato deportivo (los iconos de Material no tienen uno sin tachar).
class ShoePainter extends CustomPainter {
  const ShoePainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.shortestSide;
    canvas.translate((size.width - s) / 2, (size.height - s) / 2);
    Offset p(double x, double y) => Offset(x * s, y * s);
    final upper = Path()
      ..moveTo(p(0.1, 0.72).dx, p(0.1, 0.72).dy)
      ..lineTo(p(0.12, 0.34).dx, p(0.12, 0.34).dy)
      ..quadraticBezierTo(p(0.2, 0.28).dx, p(0.2, 0.28).dy, p(0.3, 0.32).dx, p(0.3, 0.32).dy)
      ..quadraticBezierTo(p(0.36, 0.46).dx, p(0.36, 0.46).dy, p(0.5, 0.46).dx, p(0.5, 0.46).dy)
      ..quadraticBezierTo(p(0.78, 0.5).dx, p(0.78, 0.5).dy, p(0.9, 0.62).dx, p(0.9, 0.62).dy)
      ..quadraticBezierTo(p(0.94, 0.68).dx, p(0.94, 0.68).dy, p(0.9, 0.72).dx, p(0.9, 0.72).dy)
      ..close();
    shape3d(canvas, upper, color, outline: s * 0.012);
    final sole = RRect.fromRectAndRadius(
      Rect.fromLTRB(0.07 * s, 0.68 * s, 0.94 * s, 0.8 * s),
      Radius.circular(s * 0.05),
    );
    canvas.drawRRect(sole, Paint()..color = Colors.white);
    canvas.drawRRect(
      sole,
      Paint()
        ..color = Color.lerp(color, Colors.black, 0.35)!
        ..style = PaintingStyle.stroke
        ..strokeWidth = s * 0.02,
    );
    final lace = Paint()
      ..color = Colors.white
      ..strokeWidth = s * 0.035
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 3; i++) {
      final x = 0.36 + i * 0.09;
      canvas.drawLine(p(x, 0.44 + i * 0.012), p(x + 0.06, 0.5 + i * 0.012), lace);
    }
  }

  @override
  bool shouldRepaint(ShoePainter old) => old.color != color;
}
