import 'package:flutter/material.dart';

/// Icono de borrador dibujado a mano (Material Icons no incluye uno).
/// Toma el color y el tamaño del [IconTheme] actual.
class EraserIcon extends StatelessWidget {
  const EraserIcon({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = IconTheme.of(context);
    final size = theme.size ?? 24;
    return SizedBox.square(
      dimension: size,
      child: CustomPaint(painter: _EraserPainter(theme.color ?? Colors.black)),
    );
  }
}

class _EraserPainter extends CustomPainter {
  _EraserPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 24;
    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2 * s
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;
    canvas.save();
    canvas.translate(12 * s, 11 * s);
    canvas.rotate(-0.7);
    final body = RRect.fromRectAndRadius(
      Rect.fromCenter(center: Offset.zero, width: 18 * s, height: 9 * s),
      Radius.circular(2 * s),
    );
    canvas.drawRRect(body, stroke);
    canvas.drawRRect(
      RRect.fromRectAndCorners(
        Rect.fromLTWH(-9 * s, -4.5 * s, 7 * s, 9 * s),
        topLeft: Radius.circular(2 * s),
        bottomLeft: Radius.circular(2 * s),
      ),
      Paint()..color = color,
    );
    canvas.restore();
    canvas.drawLine(Offset(4 * s, 21 * s), Offset(20 * s, 21 * s), stroke);
  }

  @override
  bool shouldRepaint(_EraserPainter oldDelegate) => oldDelegate.color != color;
}
