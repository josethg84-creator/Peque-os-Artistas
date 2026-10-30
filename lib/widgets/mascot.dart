import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_motion.dart';

/// Pincelín: la mascota original de Pequeños Artistas, un pincel sonriente
/// dibujado con vectores (sin imágenes). Saluda con un balanceo suave unas
/// pocas veces y se queda quieto: nunca se anima sin parar.
class Mascot extends StatefulWidget {
  const Mascot({super.key, this.size = 96, this.waves = 2, this.paintColor = AppColors.coral});

  final double size;

  /// Número de saludos al aparecer (0 = quieto).
  final int waves;

  /// Color de la punta (p. ej. el color elegido al pintar).
  final Color paintColor;

  @override
  State<Mascot> createState() => _MascotState();
}

class _MascotState extends State<Mascot> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 700),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!AppMotion.reduced(context) && widget.waves > 0 && !_c.isAnimating && _c.value == 0) {
      _wave(widget.waves);
    }
  }

  Future<void> _wave(int times) async {
    for (var i = 0; i < times && mounted; i++) {
      await _c.forward(from: 0).orCancel.catchError((Object _) {});
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Pincelín, la mascota',
      image: true,
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          // Balanceo suave de ida y vuelta (máximo 10°).
          final angle = math.sin(_c.value * math.pi * 2) * 0.17;
          return Transform.rotate(
            angle: angle,
            alignment: Alignment.bottomCenter,
            child: SizedBox(
              width: widget.size * 0.62,
              height: widget.size,
              child: CustomPaint(painter: _MascotPainter(widget.paintColor)),
            ),
          );
        },
      ),
    );
  }
}

class _MascotPainter extends CustomPainter {
  _MascotPainter(this.tipColor);

  final Color tipColor;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    final ink = Paint()
      ..color = AppColors.ink
      ..style = PaintingStyle.stroke
      ..strokeWidth = w * 0.05
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;

    // Mango (cuerpo) con la cara.
    final body = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * 0.18, h * 0.42, w * 0.64, h * 0.55),
      Radius.circular(w * 0.3),
    );
    canvas.drawRRect(body, Paint()..color = AppColors.sky);
    canvas.drawRRect(body, ink);
    // Virola metálica.
    final ferrule = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * 0.14, h * 0.33, w * 0.72, h * 0.13),
      Radius.circular(w * 0.08),
    );
    canvas.drawRRect(ferrule, Paint()..color = const Color(0xFFD9DCE3));
    canvas.drawRRect(ferrule, ink);
    // Pelo del pincel con pintura.
    final tip = Path()
      ..moveTo(w * 0.2, h * 0.34)
      ..quadraticBezierTo(w * 0.18, h * 0.12, w * 0.5, h * 0.02)
      ..quadraticBezierTo(w * 0.82, h * 0.12, w * 0.8, h * 0.34)
      ..close();
    canvas.drawPath(tip, Paint()..color = tipColor);
    canvas.drawPath(tip, ink);
    // Ojos y sonrisa.
    final eye = Paint()..color = AppColors.ink;
    canvas.drawCircle(Offset(w * 0.38, h * 0.6), w * 0.06, eye);
    canvas.drawCircle(Offset(w * 0.62, h * 0.6), w * 0.06, eye);
    canvas.drawCircle(Offset(w * 0.4, h * 0.585), w * 0.02, Paint()..color = Colors.white);
    canvas.drawCircle(Offset(w * 0.64, h * 0.585), w * 0.02, Paint()..color = Colors.white);
    final smile = Path()
      ..moveTo(w * 0.36, h * 0.72)
      ..quadraticBezierTo(w * 0.5, h * 0.82, w * 0.64, h * 0.72);
    canvas.drawPath(smile, ink);
    // Mejillas.
    final cheek = Paint()..color = AppColors.berry.withValues(alpha: 0.45);
    canvas.drawCircle(Offset(w * 0.28, h * 0.7), w * 0.06, cheek);
    canvas.drawCircle(Offset(w * 0.72, h * 0.7), w * 0.06, cheek);
  }

  @override
  bool shouldRepaint(_MascotPainter old) => old.tipColor != tipColor;
}

/// La mascota con un bocadillo de texto corto.
class MascotBubble extends StatefulWidget {
  const MascotBubble({super.key, required this.text, this.size = 72, this.waves = 2, this.onTap});

  final String text;
  final double size;
  final int waves;

  /// Si se indica, Pincelín se puede tocar: vuelve a saludar y llama a [onTap].
  final VoidCallback? onTap;

  @override
  State<MascotBubble> createState() => _MascotBubbleState();
}

class _MascotBubbleState extends State<MascotBubble> {
  int _greetings = 0;

  void _greet(VoidCallback onTap) {
    setState(() => _greetings++);
    onTap();
  }

  @override
  Widget build(BuildContext context) {
    final text = widget.text;
    final size = widget.size;
    Widget mascot = Mascot(key: ValueKey(_greetings), size: size, waves: _greetings == 0 ? widget.waves : 1);
    final onTap = widget.onTap;
    if (onTap != null) {
      mascot = Semantics(
        button: true,
        label: 'Pincelín, la mascota',
        hint: 'Toca para que te salude',
        excludeSemantics: true,
        onTap: () => _greet(onTap),
        child: GestureDetector(behavior: HitTestBehavior.opaque, onTap: () => _greet(onTap), child: mascot),
      );
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        mascot,
        const SizedBox(width: 8),
        Flexible(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(20),
                topRight: Radius.circular(20),
                bottomRight: Radius.circular(20),
                bottomLeft: Radius.circular(4),
              ),
              boxShadow: const [BoxShadow(color: Color(0x1F000000), blurRadius: 8, offset: Offset(0, 3))],
            ),
            child: Text(text, style: Theme.of(context).textTheme.titleMedium),
          ),
        ),
      ],
    );
  }
}
