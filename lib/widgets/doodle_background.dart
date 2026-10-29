import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Fondo decorativo muy suave (manchas de pintura en las esquinas). Es
/// estático: se pinta una vez y queda aislado con [RepaintBoundary], así que
/// no cuesta nada al desplazar ni al animar el contenido.
class DoodleBackground extends StatelessWidget {
  const DoodleBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const Positioned.fill(
          child: ExcludeSemantics(
            child: RepaintBoundary(child: CustomPaint(painter: _DoodlePainter())),
          ),
        ),
        child,
      ],
    );
  }
}

class _DoodlePainter extends CustomPainter {
  const _DoodlePainter();

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    final r = (w < h ? w : h) * 0.22;
    void blob(Offset c, double radius, Color color) =>
        canvas.drawCircle(c, radius, Paint()..color = color.withValues(alpha: 0.09));
    blob(Offset(-r * 0.2, h * 0.08), r, AppColors.sun);
    blob(Offset(r * 0.6, -r * 0.3), r * 0.6, AppColors.coral);
    blob(Offset(w + r * 0.15, h * 0.92), r * 1.1, AppColors.sky);
    blob(Offset(w - r * 0.8, h + r * 0.2), r * 0.6, AppColors.leaf);
    // Unos puntitos de color, como salpicaduras.
    final dots = [
      (0.12, 0.3, AppColors.grape),
      (0.9, 0.18, AppColors.leaf),
      (0.06, 0.82, AppColors.berry),
      (0.82, 0.7, AppColors.sun),
    ];
    for (final (x, y, color) in dots) {
      canvas.drawCircle(Offset(w * x, h * y), r * 0.07, Paint()..color = color.withValues(alpha: 0.18));
    }
  }

  @override
  bool shouldRepaint(_DoodlePainter oldDelegate) => false;
}
