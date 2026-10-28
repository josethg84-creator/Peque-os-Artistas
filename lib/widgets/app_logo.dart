import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Logotipo provisional: una paleta de pintor con gotas de colores y un pincel.
class AppLogo extends StatelessWidget {
  const AppLogo({super.key, this.size = 140});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Logotipo de Pequeños Artistas',
      image: true,
      child: SizedBox.square(
        dimension: size,
        child: CustomPaint(painter: _LogoPainter()),
      ),
    );
  }
}

class _LogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 100;
    final outline = Paint()
      ..color = AppColors.ink
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5 * s
      ..strokeJoin = StrokeJoin.round;

    // Paleta: óvalo con un hueco para el pulgar.
    final palette = Path()..addOval(Rect.fromLTWH(6 * s, 14 * s, 82 * s, 70 * s));
    final hole = Path()..addOval(Rect.fromCircle(center: Offset(30 * s, 64 * s), radius: 8 * s));
    final shape = Path.combine(PathOperation.difference, palette, hole);
    canvas.drawPath(shape, Paint()..color = const Color(0xFFFFE7B8));
    canvas.drawPath(shape, outline);

    const blobs = [AppColors.coral, AppColors.sun, AppColors.leaf, AppColors.sky, AppColors.grape];
    const centers = [Offset(28, 34), Offset(48, 26), Offset(68, 32), Offset(72, 54), Offset(56, 68)];
    for (var i = 0; i < blobs.length; i++) {
      final c = centers[i] * s;
      canvas.drawCircle(c, 8.5 * s, Paint()..color = blobs[i]);
      canvas.drawCircle(c, 8.5 * s, outline..strokeWidth = 2.5 * s);
    }

    // Pincel cruzando la paleta.
    canvas.save();
    canvas.translate(82 * s, 78 * s);
    canvas.rotate(-math.pi / 4);
    final handle = RRect.fromRectAndRadius(
      Rect.fromLTWH(-4 * s, -2 * s, 8 * s, 30 * s),
      Radius.circular(4 * s),
    );
    canvas.drawRRect(handle, Paint()..color = AppColors.sky);
    canvas.drawRRect(handle, outline..strokeWidth = 2.5 * s);
    final tip = Path()
      ..moveTo(-4 * s, -2 * s)
      ..quadraticBezierTo(0, -18 * s, 0, -20 * s)
      ..quadraticBezierTo(0, -18 * s, 4 * s, -2 * s)
      ..close();
    canvas.drawPath(tip, Paint()..color = AppColors.coral);
    canvas.drawPath(tip, outline);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
