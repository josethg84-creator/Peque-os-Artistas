import 'dart:async';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/motion/celebration.dart';
import '../reading_activities.dart';

/// Componentes de «Aprendo a leer». Reutilizan los de la app (tarjetas del
/// menú, botones de acción, Lolo, confeti) y añaden solo lo propio de la
/// lectura: sílabas, huecos, barra de progreso y distintivo de demostración.

/// Ilustración de una tarjeta, con esquinas redondeadas y adaptada al hueco.
class ReadingArt extends StatelessWidget {
  const ReadingArt({super.key, required this.image, required this.fallbackIcon, required this.color});

  final String image;
  final IconData fallbackIcon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        final side = box.biggest.shortestSide;
        final icon = Center(
          child: Icon(fallbackIcon, size: side.isFinite ? side * 0.8 : 64, color: Colors.white),
        );
        if (!side.isFinite || side <= 0) return icon;
        return Center(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(side * 0.18),
            child: SizedBox.square(
              dimension: side,
              child: Image.asset(
                image,
                fit: BoxFit.contain,
                cacheWidth: (side * MediaQuery.devicePixelRatioOf(context)).ceil(),
                excludeFromSemantics: true,
                errorBuilder: (_, _, _) => icon,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Tarjeta grande de una actividad (la tarjeta de menú de la app).
class ReadingActivityCard extends StatelessWidget {
  const ReadingActivityCard({super.key, required this.activity, required this.onTap});

  final ReadingActivity activity;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return HomeMenuCard(
      title: activity.title,
      subtitle: activity.subtitle,
      color: activity.color,
      art: ReadingArt(image: activity.image, fallbackIcon: activity.icon, color: activity.color),
      onTap: onTap,
    );
  }
}

/// Barra de progreso redondeada con su texto («2 de 5»).
class ReadingProgressBar extends StatelessWidget {
  const ReadingProgressBar({
    super.key,
    required this.done,
    required this.total,
    required this.label,
    this.color = ReadingActivities.accent,
  });

  final int done;
  final int total;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final value = total == 0 ? 0.0 : (done / total).clamp(0.0, 1.0);
    return Semantics(
      label: '$label: $done de $total',
      excludeSemantics: true,
      child: Row(
        children: [
          Icon(Icons.star_rounded, color: AppColors.sun, size: 30),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('$label · $done de $total', style: fredoka(16, color: AppColors.ink)),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: LinearProgressIndicator(
                    value: value,
                    minHeight: 14,
                    backgroundColor: Color.lerp(color, Colors.white, 0.75),
                    valueColor: AlwaysStoppedAnimation(color),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Tarjeta grande de una sílaba (MA, ME…). Se ve en mayúsculas y se lee en
/// minúsculas.
class SyllableCard extends StatelessWidget {
  const SyllableCard({
    super.key,
    required this.text,
    required this.onTap,
    this.selected = false,
    this.color = ReadingActivities.accent,
    this.size = 84,
  });

  final String text;
  final VoidCallback? onTap;
  final bool selected;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    final bg = selected ? color : Color.lerp(color, Colors.white, 0.8)!;
    return Semantics(
      button: true,
      selected: selected,
      label: 'Sílaba ${text.toLowerCase()}',
      excludeSemantics: true,
      onTap: onTap,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(size * 0.3),
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            constraints: BoxConstraints(minWidth: size, minHeight: size),
            padding: EdgeInsets.symmetric(horizontal: size * 0.16),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(size * 0.3),
              border: Border.all(color: selected ? Colors.white : color, width: 3),
              boxShadow: [
                BoxShadow(color: Color.lerp(color, Colors.black, 0.25)!, offset: const Offset(0, 4)),
              ],
            ),
            // Centrado sin ocupar todo el ancho (las tarjetas van una al lado de otra).
            child: Center(
              widthFactor: 1,
              heightFactor: 1,
              child: Text(
                text.toUpperCase(),
                style: fredoka(size * 0.42, color: selected ? Colors.white : AppColors.ink),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Una palabra dividida en sílabas, con un hueco (o la sílaba elegida) en
/// [missing]. Sin [missing], muestra la palabra entera por sílabas.
class SyllableWord extends StatelessWidget {
  const SyllableWord({
    super.key,
    required this.syllables,
    this.missing,
    this.filled,
    this.highlight,
    this.color = ReadingActivities.accent,
    this.size = 64,
  });

  final List<String> syllables;
  final int? missing;

  /// Lo que se ha puesto en el hueco.
  final String? filled;

  /// Sílaba resaltada (la que se está aprendiendo).
  final int? highlight;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    final shown = [for (final (i, s) in syllables.indexed) i == missing ? (filled ?? '__') : s];
    return Semantics(
      label: missing == null
          ? 'Palabra por sílabas: ${syllables.join(' - ')}'
          : 'Palabra por sílabas: ${shown.map((s) => s == '__' ? 'hueco' : s).join(' - ')}',
      excludeSemantics: true,
      child: Wrap(
        alignment: WrapAlignment.center,
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final (i, s) in shown.indexed)
            Container(
              constraints: BoxConstraints(minWidth: size, minHeight: size),
              padding: EdgeInsets.symmetric(horizontal: size * 0.18),
              decoration: BoxDecoration(
                color: i == missing
                    ? (filled == null ? Colors.white : Color.lerp(color, Colors.white, 0.6))
                    : (i == highlight ? Color.lerp(color, Colors.white, 0.45) : Colors.white),
                borderRadius: BorderRadius.circular(size * 0.28),
                border: Border.all(
                  color: i == missing ? color : Color.lerp(color, Colors.white, 0.4)!,
                  width: i == missing ? 3.5 : 2,
                  strokeAlign: BorderSide.strokeAlignInside,
                ),
              ),
              child: Center(
                widthFactor: 1,
                heightFactor: 1,
                child: Text(s.toUpperCase(), style: fredoka(size * 0.46, color: AppColors.ink)),
              ),
            ),
        ],
      ),
    );
  }
}

/// «Escuchar» y «Despacio». En esta fase usan la voz de la app; el motor de
/// audio de lectura (con grabaciones de sílabas) llega en la Fase C.
class ReadingAudioButtons extends StatelessWidget {
  const ReadingAudioButtons({
    super.key,
    required this.text,
    this.listenLabel = 'Escuchar',
    this.slowLabel = 'Despacio',
    this.color = AppColors.sky,
  });

  final String text;
  final String listenLabel;
  final String slowLabel;
  final Color color;

  @override
  Widget build(BuildContext context) {
    void say({bool slow = false}) => unawaited(AppServices.of(context).audio.say(text, slow: slow));
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 12,
      runSpacing: 12,
      children: [
        SizedBox(
          width: 132,
          child: SpeechActionButton(
            icon: Icons.volume_up_rounded,
            label: listenLabel,
            color: color,
            onPressed: say,
          ),
        ),
        SizedBox(
          width: 132,
          child: SpeechActionButton(
            icon: Icons.slow_motion_video_rounded,
            label: slowLabel,
            color: AppColors.grape,
            onPressed: () => say(slow: true),
          ),
        ),
      ],
    );
  }
}

/// «Anterior» / «Siguiente» con el número de la actividad.
class ReadingStepNav extends StatelessWidget {
  const ReadingStepNav({
    super.key,
    required this.index,
    required this.total,
    required this.onPrevious,
    required this.onNext,
    this.nextLabel = 'Siguiente',
  });

  final int index;
  final int total;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;
  final String nextLabel;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        KidIconButton(
          icon: Icons.arrow_back_rounded,
          label: 'Anterior',
          color: AppColors.sky,
          onPressed: onPrevious,
        ),
        const SizedBox(width: 16),
        Semantics(
          label: '${index + 1} de $total',
          excludeSemantics: true,
          child: Text('${index + 1} de $total', style: fredoka(20, color: AppColors.ink)),
        ),
        const SizedBox(width: 16),
        KidIconButton(
          icon: Icons.arrow_forward_rounded,
          label: nextLabel,
          color: AppColors.leaf,
          onPressed: onNext,
        ),
      ],
    );
  }
}

/// Mensaje de felicitación con estrellas y confeti.
class ReadingCelebration extends StatelessWidget {
  const ReadingCelebration({super.key, required this.text, this.confetti = true});

  final String text;
  final bool confetti;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      label: text,
      excludeSemantics: true,
      child: Stack(
        alignment: Alignment.center,
        clipBehavior: Clip.none,
        children: [
          if (confetti) const Positioned.fill(child: IgnorePointer(child: ConfettiBurst(particles: 24))),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF4C7),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.sun, width: 3),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.star_rounded, color: AppColors.sun, size: 34),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(text, style: fredoka(20, color: AppColors.ink)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Mensaje amable cuando aún no es la respuesta (nunca un castigo).
class ReadingTryAgain extends StatelessWidget {
  const ReadingTryAgain({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      label: text,
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xFFE8F1FF),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppColors.sky, width: 3),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.favorite_rounded, color: AppColors.berry, size: 30),
            const SizedBox(width: 8),
            Flexible(
              child: Text(text, style: fredoka(19, color: AppColors.ink)),
            ),
          ],
        ),
      ),
    );
  }
}

/// Distintivo que avisa de que la pantalla usa datos de demostración.
class DemoBadge extends StatelessWidget {
  const DemoBadge({super.key});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Demostración: contenido de ejemplo',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
        decoration: BoxDecoration(color: const Color(0xFFFFE0B2), borderRadius: BorderRadius.circular(12)),
        child: Text(
          'Demostración',
          style: fredoka(13, weight: FontWeight.w600, color: AppColors.ink),
        ),
      ),
    );
  }
}

/// Botón «Inicio» (vuelve al menú principal desde cualquier pantalla).
class ReadingHomeButton extends StatelessWidget {
  const ReadingHomeButton({super.key});

  @override
  Widget build(BuildContext context) {
    return KidIconButton(
      icon: Icons.home_rounded,
      label: 'Ir al inicio',
      color: AppColors.coral,
      onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
    );
  }
}

/// Lolo con el mensaje de la pantalla (se escucha al tocarlo).
class ReadingLolo extends StatelessWidget {
  const ReadingLolo({super.key, required this.text, this.size = 64});

  final String text;
  final double size;

  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.centerLeft,
    child: LoloBubble(text: text, size: size),
  );
}
