import 'dart:async';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/motion/celebration.dart';
import '../../widgets/motion/delayed_loading.dart';
import '../audio/reading_voice.dart';
import '../reading_activities.dart';
import '../reading_content.dart';

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
        Flexible(
          child: Semantics(
            label: '${index + 1} de $total',
            excludeSemantics: true,
            child: Text(
              '${index + 1} de $total',
              style: fredoka(20, color: AppColors.ink),
              textAlign: TextAlign.center,
            ),
          ),
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

/// Carga el contenido real de «Aprendo a leer» y lo pasa a [builder].
class ReadingContentBuilder extends StatefulWidget {
  const ReadingContentBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, ReadingContent content) builder;

  @override
  State<ReadingContentBuilder> createState() => _ReadingContentBuilderState();
}

class _ReadingContentBuilderState extends State<ReadingContentBuilder> {
  Future<ReadingContent>? _future;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _future ??= ReadingContent.load(DefaultAssetBundle.of(context));
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<ReadingContent>(
      future: _future,
      builder: (context, snapshot) {
        final content = snapshot.data;
        if (content != null) return widget.builder(context, content);
        if (snapshot.hasError) {
          return const Center(child: Text('No pudimos abrir las sílabas. Inténtalo de nuevo más tarde.'));
        }
        return const DelayedLoading(message: 'Preparando las sílabas…', color: ReadingActivities.accent);
      },
    );
  }
}

/// La imagen de una palabra: su ilustración 3D (si ya está), el dibujo de la
/// app que la representa o, si aún no hay ninguno, un marcador «Imagen
/// pendiente» bien visible (nunca una imagen que pueda confundir).
class ReadingWordPicture extends StatelessWidget {
  const ReadingWordPicture({super.key, required this.word, required this.color});

  final ReadingWord word;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final picture = word.picture;
    final Widget child;
    if (word.imageReady) {
      child = ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Image.asset(word.image, fit: BoxFit.contain, excludeFromSemantics: true),
      );
    } else if (picture != null) {
      child = SpeechPictureView(picture: picture, tint: color);
    } else {
      child = _PendingImage(word: word.text, color: color);
    }
    return Semantics(
      label: word.hasPicture ? 'Dibujo: ${word.text}' : 'Imagen pendiente de ${word.text}',
      excludeSemantics: true,
      child: AspectRatio(aspectRatio: 1, child: child),
    );
  }
}

class _PendingImage extends StatelessWidget {
  const _PendingImage({required this.word, required this.color});

  final String word;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Color.lerp(color, Colors.white, 0.85),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: Color.lerp(color, Colors.white, 0.3)!,
          width: 3,
          strokeAlign: BorderSide.strokeAlignInside,
        ),
      ),
      padding: const EdgeInsets.all(10),
      child: FittedBox(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.image_outlined, size: 48, color: Color.lerp(color, Colors.black, 0.3)),
            Text(word.toUpperCase(), style: fredoka(26, color: AppColors.ink)),
            Text(
              'Imagen pendiente',
              style: fredoka(14, weight: FontWeight.w600, color: AppColors.inkSoft),
            ),
          ],
        ),
      ),
    );
  }
}

/// «Escuchar» (velocidad normal) y «Despacio», conectados al motor de audio.
class ReadingPlayButtons extends StatelessWidget {
  const ReadingPlayButtons({
    super.key,
    required this.onPlay,
    this.listenLabel = 'Escuchar',
    this.slowLabel = 'Despacio',
    this.semanticSuffix = '',
    this.color = AppColors.sky,
  });

  final void Function(ReadingSpeed speed) onPlay;
  final String listenLabel;
  final String slowLabel;

  /// Para los lectores de pantalla («Escuchar la sílaba»).
  final String semanticSuffix;
  final Color color;

  @override
  Widget build(BuildContext context) {
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
            semanticLabel: '$listenLabel$semanticSuffix',
            color: color,
            onPressed: () => onPlay(ReadingSpeed.normal),
          ),
        ),
        SizedBox(
          width: 132,
          child: SpeechActionButton(
            icon: Icons.slow_motion_video_rounded,
            label: slowLabel,
            semanticLabel: '$slowLabel$semanticSuffix',
            color: AppColors.grape,
            onPressed: () => onPlay(ReadingSpeed.slow),
          ),
        ),
      ],
    );
  }
}

/// Aviso cuando no se puede oír nada (sonido apagado o sin voz en español):
/// la actividad sigue funcionando con la vista.
class ReadingVoiceNotice extends StatelessWidget {
  const ReadingVoiceNotice({super.key, required this.voice});

  final ReadingVoice voice;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: voice,
      builder: (context, _) {
        final status = voice.status;
        if (status != ReadingVoiceStatus.noVoice && status != ReadingVoiceStatus.muted) {
          return const SizedBox.shrink();
        }
        final text = voice.message ?? 'No se puede reproducir el sonido en este dispositivo.';
        return Semantics(
          liveRegion: true,
          label: text,
          excludeSemantics: true,
          child: Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF3E0),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFFFFB74D), width: 2),
            ),
            child: Row(
              children: [
                Icon(
                  status == ReadingVoiceStatus.muted
                      ? Icons.volume_off_rounded
                      : Icons.record_voice_over_outlined,
                  color: const Color(0xFFEF6C00),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
              ],
            ),
          ),
        );
      },
    );
  }
}
