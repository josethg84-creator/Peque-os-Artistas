import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../audio/ui_sounds.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_motion.dart';
import '../../widgets/motion/pressable.dart';
import 'home_art.dart';

/// Tipografía redondeada del inicio (Fredoka, licencia OFL).
TextStyle fredoka(double size, {FontWeight weight = FontWeight.w700, Color color = AppColors.ink}) =>
    TextStyle(
      fontFamily: 'Fredoka',
      fontSize: size,
      fontWeight: weight,
      fontVariations: [FontVariation('wght', weight.value.toDouble())],
      color: color,
      height: 1.0,
    );

/// Logo «Pequeños Artistas»: cada letra de un color, con borde blanco grueso,
/// sombra y un degradado vertical que le da relieve.
class RainbowTitle extends StatelessWidget {
  const RainbowTitle({super.key, required this.size});

  final double size;

  static const _colors = [
    Color(0xFF4FB3FF),
    Color(0xFFFF6B9E),
    Color(0xFFFFB300),
    Color(0xFF5CC689),
    Color(0xFF9B7BEA),
    Color(0xFFFF7A59),
  ];

  Widget _word(String word, int offset) {
    final base = fredoka(size, weight: FontWeight.w700);
    List<InlineSpan> spans({required bool outline}) => [
      for (final (i, ch) in word.characters.indexed)
        TextSpan(
          text: ch,
          style: outline
              ? base.copyWith(
                  foreground: Paint()
                    ..style = PaintingStyle.stroke
                    ..strokeWidth = size * 0.16
                    ..strokeJoin = StrokeJoin.round
                    ..color = Colors.white,
                  shadows: [
                    Shadow(
                      color: const Color(0x55583A8F),
                      offset: Offset(0, size * 0.07),
                      blurRadius: size * 0.08,
                    ),
                  ],
                )
              : base.copyWith(
                  foreground: Paint()
                    ..shader = LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Color.lerp(_colors[(i + offset) % _colors.length], Colors.white, 0.35)!,
                        _colors[(i + offset) % _colors.length],
                        Color.lerp(_colors[(i + offset) % _colors.length], Colors.black, 0.18)!,
                      ],
                      stops: const [0, 0.55, 1],
                    ).createShader(Rect.fromLTWH(0, 0, 0, size * 1.05)),
                ),
        ),
    ];
    return Stack(
      children: [
        Text.rich(TextSpan(children: spans(outline: true)), textAlign: TextAlign.center),
        Text.rich(TextSpan(children: spans(outline: false)), textAlign: TextAlign.center),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      header: true,
      label: 'Pequeños Artistas',
      excludeSemantics: true,
      child: FittedBox(
        fit: BoxFit.scaleDown,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _word('Pequeños', 0),
            Transform.translate(offset: Offset(0, -size * 0.12), child: _word('Artistas', 3)),
          ],
        ),
      ),
    );
  }
}

/// Botón redondo de las esquinas (configuración y música).
class CornerButton extends StatelessWidget {
  const CornerButton({
    super.key,
    required this.icon,
    required this.label,
    required this.colors,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final List<Color> colors;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final action = withSound(context, SoundCue.tap, onPressed);
    return Pressable(
      child: Semantics(
        button: true,
        label: label,
        excludeSemantics: true,
        onTap: action,
        child: Tooltip(
          message: label,
          child: GestureDetector(
            onTap: action,
            child: Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: colors,
                ),
                border: Border.all(color: Colors.white, width: 3),
                boxShadow: [
                  BoxShadow(color: colors.last.withValues(alpha: 0.9), offset: const Offset(0, 4)),
                  const BoxShadow(color: Color(0x33000000), blurRadius: 10, offset: Offset(0, 6)),
                ],
              ),
              child: Icon(icon, color: Colors.white, size: 30),
            ),
          ),
        ),
      ),
    );
  }
}

/// Tarjeta grande del menú: degradado pastel, borde blanco, relieve (un
/// «labio» más oscuro debajo), ilustración grande y texto redondeado.
class HomeMenuCard extends StatelessWidget {
  const HomeMenuCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final HomeIcon icon;

  /// Color pastel principal de la tarjeta.
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final action = guardRoute(context, withSound(context, SoundCue.tap, onTap));
    final dark = Color.lerp(color, Colors.black, 0.18)!;
    final textColor = Color.lerp(color, const Color(0xFF2A2350), 0.78)!;
    return Pressable(
      scale: 0.95,
      child: Semantics(
        button: true,
        label: title,
        hint: subtitle,
        excludeSemantics: true,
        onTap: action,
        child: GestureDetector(
          onTap: action,
          child: LayoutBuilder(
            builder: (context, box) {
              final h = box.maxHeight.isFinite ? box.maxHeight : 160.0;
              return Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(28),
                  boxShadow: [
                    BoxShadow(color: dark, offset: const Offset(0, 6)),
                    const BoxShadow(color: Color(0x2A000000), blurRadius: 14, offset: Offset(0, 10)),
                  ],
                ),
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(color: Colors.white, width: 3),
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [Color.lerp(color, Colors.white, 0.55)!, color],
                    ),
                  ),
                  padding: const EdgeInsets.fromLTRB(8, 8, 8, 10),
                  child: Column(
                    children: [
                      Expanded(
                        child: CustomPaint(size: Size.infinite, painter: HomeIconPainter(icon)),
                      ),
                      const SizedBox(height: 4),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(title, style: fredoka(min(30, h * 0.17), color: textColor)),
                      ),
                      const SizedBox(height: 3),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          subtitle,
                          style: fredoka(
                            min(17, h * 0.1),
                            weight: FontWeight.w500,
                            color: textColor.withValues(alpha: 0.8),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

/// Botón de la barra inferior (Perfil, Logros, Configuración).
class BottomPillButton extends StatelessWidget {
  const BottomPillButton({super.key, required this.label, required this.art, required this.onTap});

  final String label;
  final Widget art;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final action = guardRoute(context, withSound(context, SoundCue.tap, onTap));
    return Pressable(
      child: Semantics(
        button: true,
        label: label,
        excludeSemantics: true,
        onTap: action,
        child: GestureDetector(
          onTap: action,
          child: LayoutBuilder(
            builder: (context, box) {
              // Botón estrecho: icono encima del texto, para que este no se encoja.
              final narrow = box.maxWidth < 132;
              final text = FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(label, style: fredoka(narrow ? 15 : 19, color: const Color(0xFF3B3355))),
              );
              return Container(
                height: 62,
                padding: const EdgeInsets.symmetric(horizontal: 8),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: const Color(0xFFF1E4CF), width: 2),
                  boxShadow: const [
                    BoxShadow(color: Color(0xFFE6D3B5), offset: Offset(0, 4)),
                    BoxShadow(color: Color(0x22000000), blurRadius: 10, offset: Offset(0, 6)),
                  ],
                ),
                child: narrow
                    ? Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox.square(dimension: 30, child: art),
                          const SizedBox(height: 1),
                          text,
                        ],
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox.square(dimension: 38, child: art),
                          const SizedBox(width: 6),
                          Flexible(child: text),
                        ],
                      ),
              );
            },
          ),
        ),
      ),
    );
  }
}

/// Destello que flota suavemente unas cuantas veces y se queda quieto (no
/// hay animaciones infinitas). Con movimiento reducido, quieto desde el principio.
class FloatingSparkle extends StatefulWidget {
  const FloatingSparkle({
    super.key,
    required this.size,
    this.color = const Color(0xFFFFD54F),
    this.delay = 0,
  });

  final double size;
  final Color color;

  /// Desfase (0-1) para que no floten todos a la vez.
  final double delay;

  @override
  State<FloatingSparkle> createState() => _FloatingSparkleState();
}

class _FloatingSparkleState extends State<FloatingSparkle> with SingleTickerProviderStateMixin {
  static const cycles = 3;
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2400),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!AppMotion.reduced(context) && !_c.isAnimating && _c.value == 0) {
      _c.value = widget.delay;
      _c.animateTo(
        cycles.toDouble(),
        duration: Duration(milliseconds: (2400 * (cycles - widget.delay)).round()),
      );
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, child) =>
            Transform.translate(offset: Offset(0, sin(_c.value * 2 * pi) * widget.size * 0.18), child: child),
        child: CustomPaint(size: Size.square(widget.size), painter: _SparklePainter(widget.color)),
      ),
    );
  }
}

class _SparklePainter extends CustomPainter {
  _SparklePainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;
    final p = Path()
      ..moveTo(c.dx, c.dy - r)
      ..quadraticBezierTo(c.dx + r * 0.15, c.dy - r * 0.15, c.dx + r, c.dy)
      ..quadraticBezierTo(c.dx + r * 0.15, c.dy + r * 0.15, c.dx, c.dy + r)
      ..quadraticBezierTo(c.dx - r * 0.15, c.dy + r * 0.15, c.dx - r, c.dy)
      ..quadraticBezierTo(c.dx - r * 0.15, c.dy - r * 0.15, c.dx, c.dy - r)
      ..close();
    canvas.drawPath(p, soft(p.getBounds(), color));
  }

  @override
  bool shouldRepaint(_SparklePainter old) => old.color != color;
}
