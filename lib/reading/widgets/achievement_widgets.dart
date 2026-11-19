import 'dart:math';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../speech/speech_content.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../achievements.dart';
import '../learning_report.dart';

/// Componentes de la Fase 7: medalla, estrellas, avatar, tarjetas de módulo
/// y de etapa. Las medallas se dibujan (no son emojis); su ilustración 3D
/// definitiva está pendiente (ver assets/images/aprendo_leer/medallas/README.md).

/// Avatar del perfil (dibujos que ya tiene la app).
SpeechPicture avatarPicture(String avatar) => switch (avatar) {
  'nina' => const KidPicture(girl: true, shirt: Color(0xFFEC407A)),
  'nino' => const KidPicture(),
  'robot' => const DrawingPicture('fantasia_robot'),
  'dragon' => const DrawingPicture('fantasia_dragon'),
  _ => const LoloPicture(),
};

const avatarNames = {'lolo': 'Lolo', 'nina': 'Niña', 'nino': 'Niño', 'robot': 'Robot', 'dragon': 'Dragón'};

/// Una medalla: círculo con cinta e icono. Bloqueada, gris con candado.
class MedalBadge extends StatelessWidget {
  const MedalBadge({super.key, required this.medal, required this.unlocked, this.size = 96});

  final MedalDef medal;
  final bool unlocked;
  final double size;

  @override
  Widget build(BuildContext context) {
    final color = unlocked ? medal.color : const Color(0xFFD7D3E0);
    final dark = Color.lerp(color, Colors.black, 0.35)!;
    return SizedBox(
      width: size,
      height: size * 1.15,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          // Cintas.
          Positioned(
            bottom: 0,
            child: CustomPaint(size: Size(size * 0.62, size * 0.42), painter: _RibbonPainter(dark)),
          ),
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                center: const Alignment(-0.3, -0.4),
                colors: [Color.lerp(color, Colors.white, 0.55)!, color, dark],
                stops: const [0, 0.65, 1],
              ),
              border: Border.all(color: Colors.white, width: size * 0.05),
              boxShadow: [
                BoxShadow(color: dark.withValues(alpha: 0.35), blurRadius: 8, offset: const Offset(0, 4)),
              ],
            ),
            child: Icon(
              unlocked ? medal.icon : Icons.lock_rounded,
              color: unlocked ? Colors.white : const Color(0xFF8E8A9A),
              size: size * 0.46,
            ),
          ),
        ],
      ),
    );
  }
}

class _RibbonPainter extends CustomPainter {
  _RibbonPainter(this.color);
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color;
    final w = size.width;
    final h = size.height;
    for (final left in [true, false]) {
      final x0 = left ? w * 0.08 : w * 0.56;
      final path = Path()
        ..moveTo(x0, 0)
        ..lineTo(x0 + w * 0.36, 0)
        ..lineTo(x0 + w * 0.36, h)
        ..lineTo(x0 + w * 0.18, h * 0.8)
        ..lineTo(x0, h)
        ..close();
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(_RibbonPainter old) => old.color != color;
}

/// Estrellas acumuladas.
class StarCount extends StatelessWidget {
  const StarCount({super.key, required this.stars, this.size = 30});
  final int stars;
  final double size;

  @override
  Widget build(BuildContext context) => Semantics(
    label: '$stars estrellas',
    excludeSemantics: true,
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF4C7),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppColors.sun, width: 3),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.star_rounded, color: AppColors.sun, size: size),
          const SizedBox(width: 6),
          Text('$stars', style: fredoka(size * 0.8, color: AppColors.ink)),
        ],
      ),
    ),
  );
}

/// Avatar redondo.
class AvatarView extends StatelessWidget {
  const AvatarView({super.key, required this.avatar, this.size = 96});
  final String avatar;
  final double size;

  @override
  Widget build(BuildContext context) => Semantics(
    image: true,
    label: 'Avatar: ${avatarNames[avatar] ?? 'Lolo'}',
    excludeSemantics: true,
    child: Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(size * 0.08),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: const Color(0xFFE8F1FF),
        border: Border.all(color: Colors.white, width: 4),
        boxShadow: const [BoxShadow(color: Color(0x22000000), blurRadius: 8, offset: Offset(0, 3))],
      ),
      child: ClipOval(child: SpeechPictureView(picture: avatarPicture(avatar))),
    ),
  );
}

/// Barra con texto «x de y» (no solo color).
class CountBar extends StatelessWidget {
  const CountBar({super.key, required this.value, required this.total, required this.color, this.label});
  final int value;
  final int total;
  final Color color;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final f = total == 0 ? 0.0 : min(1.0, value / total);
    return Semantics(
      label: '${label ?? ''} $value de $total'.trim(),
      excludeSemantics: true,
      child: Row(
        children: [
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: LinearProgressIndicator(
                value: f,
                minHeight: 14,
                backgroundColor: Color.lerp(color, Colors.white, 0.75),
                valueColor: AlwaysStoppedAnimation(color),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text('$value de $total', style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

/// Tarjeta de progreso de un módulo (pantalla infantil).
class ModuleProgressCard extends StatelessWidget {
  const ModuleProgressCard({super.key, required this.report, required this.color, required this.onTap});
  final ModuleReport report;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final r = report;
    return Semantics(
      button: true,
      label:
          '${r.title}. Hechas ${r.done} de ${r.available}. Bien ${r.correct}. Sin ayuda ${r.mastered}. ${r.level}.',
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          width: 300,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: color, width: 3),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(r.title, style: fredoka(20, color: AppColors.ink)),
              const SizedBox(height: 6),
              CountBar(value: r.correct, total: r.available, color: color, label: 'Bien hechas'),
              const SizedBox(height: 6),
              Wrap(
                spacing: 10,
                runSpacing: 4,
                children: [
                  _Chip(icon: Icons.play_circle_outline_rounded, text: 'Hechas: ${r.done}'),
                  _Chip(icon: Icons.check_circle_outline_rounded, text: 'Bien: ${r.correct}'),
                  _Chip(icon: Icons.star_outline_rounded, text: 'Sin ayuda: ${r.mastered}'),
                ],
              ),
              const SizedBox(height: 4),
              Text(r.level, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(icon, size: 18, color: AppColors.inkSoft),
      const SizedBox(width: 3),
      Text(text, style: Theme.of(context).textTheme.bodySmall),
    ],
  );
}
