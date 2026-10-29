import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_motion.dart';

/// Confeti de una sola vez (≈1,6 s) para los logros importantes. Pocas
/// partículas, sin destellos rápidos, y no recibe toques. Con movimiento
/// reducido no se muestra.
class ConfettiBurst extends StatefulWidget {
  const ConfettiBurst({super.key, this.particles = 36, this.seed = 7});

  final int particles;
  final int seed;

  static const duration = Duration(milliseconds: 1600);

  @override
  State<ConfettiBurst> createState() => _ConfettiBurstState();
}

class _ConfettiBurstState extends State<ConfettiBurst> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: ConfettiBurst.duration);
  late final List<_Piece> _pieces;

  static const _colors = [
    AppColors.coral,
    AppColors.sky,
    AppColors.sun,
    AppColors.leaf,
    AppColors.grape,
    AppColors.berry,
  ];

  @override
  void initState() {
    super.initState();
    final r = math.Random(widget.seed);
    _pieces = [
      for (var i = 0; i < widget.particles; i++)
        _Piece(
          x: r.nextDouble(),
          drift: (r.nextDouble() - 0.5) * 0.3,
          speed: 0.7 + r.nextDouble() * 0.5,
          spin: (r.nextDouble() - 0.5) * 8,
          size: 6 + r.nextDouble() * 6,
          color: _colors[i % _colors.length],
          delay: r.nextDouble() * 0.25,
        ),
    ];
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!AppMotion.reduced(context) && _c.status == AnimationStatus.dismissed) _c.forward();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (AppMotion.reduced(context)) return const SizedBox.shrink();
    return IgnorePointer(
      child: RepaintBoundary(
        child: AnimatedBuilder(
          animation: _c,
          builder: (context, _) => _c.isCompleted
              ? const SizedBox.expand()
              : CustomPaint(size: Size.infinite, painter: _ConfettiPainter(_pieces, _c.value)),
        ),
      ),
    );
  }
}

class _Piece {
  _Piece({
    required this.x,
    required this.drift,
    required this.speed,
    required this.spin,
    required this.size,
    required this.color,
    required this.delay,
  });

  final double x, drift, speed, spin, size, delay;
  final Color color;
}

class _ConfettiPainter extends CustomPainter {
  _ConfettiPainter(this.pieces, this.t);

  final List<_Piece> pieces;
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint();
    for (final p in pieces) {
      final local = ((t - p.delay) / (1 - p.delay)).clamp(0.0, 1.0);
      if (local <= 0) continue;
      final y = -20 + local * p.speed * (size.height + 40);
      final x = (p.x + p.drift * local) * size.width;
      final fade = local > 0.75 ? (1 - local) / 0.25 : 1.0;
      paint.color = p.color.withValues(alpha: fade);
      canvas.save();
      canvas.translate(x, y);
      canvas.rotate(p.spin * local);
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromCenter(center: Offset.zero, width: p.size, height: p.size * 0.6),
          const Radius.circular(2),
        ),
        paint,
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter old) => old.t != t;
}

/// Estrellas que suben y se desvanecen una vez (acierto o fin de actividad).
class RisingStars extends StatefulWidget {
  const RisingStars({super.key, this.count = 5});

  final int count;

  static const duration = Duration(milliseconds: 900);

  @override
  State<RisingStars> createState() => _RisingStarsState();
}

class _RisingStarsState extends State<RisingStars> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: RisingStars.duration);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!AppMotion.reduced(context) && _c.status == AnimationStatus.dismissed) _c.forward();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (AppMotion.reduced(context)) return const SizedBox.shrink();
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          if (_c.isCompleted) return const SizedBox.shrink();
          final t = Curves.easeOut.transform(_c.value);
          return LayoutBuilder(
            builder: (context, box) => Stack(
              clipBehavior: Clip.none,
              children: [
                for (var i = 0; i < widget.count; i++)
                  Positioned(
                    left: box.maxWidth * (i + 0.5) / widget.count - 14,
                    top: box.maxHeight * (0.7 - t * (0.5 + (i.isEven ? 0.1 : 0))),
                    child: Opacity(
                      opacity: (1 - t).clamp(0.0, 1.0),
                      child: const Icon(Icons.star_rounded, color: AppColors.sun, size: 28),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Sacudida horizontal breve y suave (un error, sin dramatismo).
class Shake extends StatefulWidget {
  const Shake({super.key, required this.trigger, required this.child});

  /// Cada vez que cambia, se sacude una vez.
  final int trigger;
  final Widget child;

  @override
  State<Shake> createState() => _ShakeState();
}

class _ShakeState extends State<Shake> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 320),
  );

  @override
  void didUpdateWidget(Shake old) {
    super.didUpdateWidget(old);
    if (old.trigger != widget.trigger && !AppMotion.reduced(context)) _c.forward(from: 0);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _c,
    child: widget.child,
    builder: (context, child) => Transform.translate(
      offset: Offset(math.sin(_c.value * math.pi * 4) * 6 * (1 - _c.value), 0),
      child: child,
    ),
  );
}
