import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../learning_content.dart';

/// Dibuja una forma geométrica con vectores (sin imágenes externas).
/// Con [outline] se dibuja solo el contorno discontinuo, como modelo.
class ShapeView extends StatelessWidget {
  const ShapeView({super.key, required this.kind, this.color = AppColors.sky, this.outline = false});

  final ShapeKind kind;
  final Color color;
  final bool outline;

  @override
  Widget build(BuildContext context) =>
      AspectRatio(aspectRatio: 1, child: CustomPaint(painter: _ShapePainter(kind, color, outline)));

  /// Trazado de la forma dentro de un cuadrado de lado [s].
  static Path pathFor(ShapeKind kind, double s) {
    switch (kind) {
      case ShapeKind.circle:
        return Path()..addOval(Rect.fromCircle(center: Offset(s / 2, s / 2), radius: s * 0.42));
      case ShapeKind.square:
        return Path()..addRRect(
          RRect.fromRectAndRadius(
            Rect.fromCenter(center: Offset(s / 2, s / 2), width: s * 0.74, height: s * 0.74),
            Radius.circular(s * 0.04),
          ),
        );
      case ShapeKind.rectangle:
        return Path()..addRRect(
          RRect.fromRectAndRadius(
            Rect.fromCenter(center: Offset(s / 2, s / 2), width: s * 0.9, height: s * 0.5),
            Radius.circular(s * 0.04),
          ),
        );
      case ShapeKind.oval:
        return Path()
          ..addOval(Rect.fromCenter(center: Offset(s / 2, s / 2), width: s * 0.9, height: s * 0.58));
      case ShapeKind.triangle:
        return Path()
          ..moveTo(s * 0.5, s * 0.1)
          ..lineTo(s * 0.92, s * 0.86)
          ..lineTo(s * 0.08, s * 0.86)
          ..close();
      case ShapeKind.star:
        final path = Path();
        for (var i = 0; i < 10; i++) {
          final r = (i.isEven ? 0.46 : 0.2) * s;
          final a = -math.pi / 2 + i * math.pi / 5;
          final p = Offset(s / 2 + r * math.cos(a), s * 0.53 + r * math.sin(a));
          i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
        }
        return path..close();
      case ShapeKind.heart:
        return Path()
          ..moveTo(s * 0.5, s * 0.3)
          ..cubicTo(s * 0.42, s * 0.12, s * 0.08, s * 0.14, s * 0.1, s * 0.4)
          ..cubicTo(s * 0.12, s * 0.62, s * 0.38, s * 0.76, s * 0.5, s * 0.9)
          ..cubicTo(s * 0.62, s * 0.76, s * 0.88, s * 0.62, s * 0.9, s * 0.4)
          ..cubicTo(s * 0.92, s * 0.14, s * 0.58, s * 0.12, s * 0.5, s * 0.3)
          ..close();
    }
  }
}

class _ShapePainter extends CustomPainter {
  _ShapePainter(this.kind, this.color, this.outline);

  final ShapeKind kind;
  final Color color;
  final bool outline;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.shortestSide;
    canvas.translate((size.width - s) / 2, (size.height - s) / 2);
    final path = ShapeView.pathFor(kind, s);
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round
      ..strokeWidth = s * 0.04
      ..color = outline ? AppColors.inkSoft : AppColors.ink;
    if (outline) {
      // Contorno discontinuo: es un modelo, no una opción.
      for (final metric in path.computeMetrics()) {
        for (var d = 0.0; d < metric.length; d += s * 0.08) {
          canvas.drawPath(metric.extractPath(d, d + s * 0.05), stroke);
        }
      }
      return;
    }
    canvas.drawPath(path, Paint()..color = color);
    canvas.drawPath(path, stroke);
  }

  @override
  bool shouldRepaint(_ShapePainter old) => old.kind != kind || old.color != color || old.outline != outline;
}
