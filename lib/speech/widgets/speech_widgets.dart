import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../coloring/auto_colors.dart';
import '../../coloring/engine/drawing_painter.dart';
import '../../coloring/engine/vector_drawing.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_motion.dart';
import '../speech_content.dart';
import 'speech_art.dart';

/// Color de la sección «Aprendo a Hablar» (el verde de Lolo).
const speechAccent = LoloPainter.green;

/// Lolo, el lorito guía. Saluda con el ala unas pocas veces al aparecer y
/// mueve el pico mientras [talking] (sin animaciones infinitas).
class Lolo extends StatefulWidget {
  const Lolo({super.key, this.size = 72, this.waves = 2});

  final double size;
  final int waves;

  @override
  State<Lolo> createState() => _LoloState();
}

class _LoloState extends State<Lolo> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 700),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!AppMotion.reduced(context) && widget.waves > 0 && !_c.isAnimating && _c.value == 0) {
      _c.animateTo(widget.waves.toDouble(), duration: _c.duration! * widget.waves);
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
        builder: (context, _) {
          final t = sin((_c.value % 1) * pi);
          return CustomPaint(
            size: Size.square(widget.size),
            painter: LoloPainter(wing: t, beakOpen: t),
          );
        },
      ),
    );
  }
}

/// Lolo con un bocadillo. Al tocarlo, dice el texto en voz alta.
class LoloBubble extends StatefulWidget {
  const LoloBubble({super.key, required this.text, this.size = 72, this.spoken});

  final String text;
  final double size;

  /// Lo que dice al tocarlo (por defecto, [text]).
  final String? spoken;

  @override
  State<LoloBubble> createState() => _LoloBubbleState();
}

class _LoloBubbleState extends State<LoloBubble> {
  int _taps = 0;

  void _tap() {
    setState(() => _taps++);
    unawaited(AppServices.maybeOf(context)?.audio.say(widget.spoken ?? widget.text) ?? Future.value());
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Lolo dice: ${widget.text}',
      hint: 'Toca para escuchar a Lolo',
      excludeSemantics: true,
      onTap: _tap,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: _tap,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Lolo(key: ValueKey(_taps), size: widget.size, waves: _taps == 0 ? 2 : 1),
            const SizedBox(width: 6),
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
                  border: Border.all(color: LoloPainter.green.withValues(alpha: 0.5), width: 2),
                  boxShadow: const [BoxShadow(color: Color(0x1F000000), blurRadius: 8, offset: Offset(0, 3))],
                ),
                child: Text(widget.text, style: Theme.of(context).textTheme.titleMedium),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// La ilustración de una palabra o frase, cuadrada.
class SpeechPictureView extends StatelessWidget {
  const SpeechPictureView({super.key, required this.picture, this.tint});

  final SpeechPicture picture;

  /// Color de la categoría (fondo de los pictogramas).
  final Color? tint;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: switch (picture) {
        ImagePicture(:final path) => Image.asset(
          path,
          fit: BoxFit.contain,
          errorBuilder: (_, _, _) =>
              const _IconTile(icon: Icons.image_not_supported_rounded, color: AppColors.inkSoft),
        ),
        final DrawingPicture p => _CatalogDrawing(picture: p),
        EmotionPicture(:final emotion) => CustomPaint(painter: EmotionFacePainter(emotion)),
        BodyPicture(:final part) => CustomPaint(painter: BodyPartPainter(part)),
        SwatchPicture(:final color) => CustomPaint(painter: PaintSplashPainter(color)),
        final IconPicture p => _IconTile(icon: p.icon, color: p.color ?? tint ?? AppColors.grape),
      },
    );
  }
}

/// Pictograma grande sobre una baldosa redondeada con relieve.
class _IconTile extends StatelessWidget {
  const _IconTile({required this.icon, required this.color});

  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        final side = box.biggest.shortestSide;
        return Center(
          child: Container(
            width: side * 0.86,
            height: side * 0.86,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(side * 0.22),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color.lerp(color, Colors.white, 0.86)!, Color.lerp(color, Colors.white, 0.62)!],
              ),
              border: Border.all(color: Colors.white, width: max(2, side * 0.02)),
              boxShadow: [
                BoxShadow(color: Color.lerp(color, Colors.white, 0.35)!, offset: Offset(0, side * 0.025)),
                const BoxShadow(color: Color(0x22000000), blurRadius: 10, offset: Offset(0, 6)),
              ],
            ),
            child: Icon(
              icon,
              size: side * 0.56,
              color: color,
              shadows: [
                Shadow(
                  color: Color.lerp(color, Colors.black, 0.4)!.withValues(alpha: 0.35),
                  offset: Offset(0, side * 0.02),
                  blurRadius: side * 0.02,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// Un dibujo del catálogo de colorear, pintado con colores alegres.
class _CatalogDrawing extends StatefulWidget {
  const _CatalogDrawing({required this.picture});

  final DrawingPicture picture;

  @override
  State<_CatalogDrawing> createState() => _CatalogDrawingState();
}

class _CatalogDrawingState extends State<_CatalogDrawing> {
  Future<VectorDrawing?>? _drawing;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _drawing ??= _load();
  }

  @override
  void didUpdateWidget(_CatalogDrawing old) {
    super.didUpdateWidget(old);
    if (old.picture.drawingId != widget.picture.drawingId) _drawing = _load();
  }

  Future<VectorDrawing?> _load() async {
    final services = AppServices.of(context);
    try {
      final entry = (await services.catalog.load()).byId(widget.picture.drawingId);
      return entry == null ? null : await services.drawings.load(entry.file);
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<VectorDrawing?>(
      future: _drawing,
      builder: (context, snapshot) {
        final d = snapshot.data;
        if (d == null) {
          return snapshot.connectionState == ConnectionState.done
              ? const _IconTile(icon: Icons.image_not_supported_rounded, color: AppColors.inkSoft)
              : const SizedBox.expand();
        }
        return CustomPaint(
          painter: DrawingPainter(drawing: d, colors: _PictureColors(widget.picture, d)),
        );
      },
    );
  }
}

/// Los colores fijados en el contenido y, para el resto, colores alegres.
class _PictureColors extends AutoColors {
  _PictureColors(this.picture, VectorDrawing drawing) : super(drawing, picture.drawingId, background: null);

  final DrawingPicture picture;

  @override
  Color? colorOf(String regionId) => picture.colorFor(regionId) ?? super.colorOf(regionId);
}

/// Botón grande y redondeado de las actividades (Escuchar, Despacio…).
class SpeechActionButton extends StatelessWidget {
  const SpeechActionButton({
    super.key,
    required this.icon,
    required this.label,
    required this.color,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null;
    return Semantics(
      container: true,
      button: true,
      enabled: enabled,
      label: label,
      excludeSemantics: true,
      onTap: onPressed,
      child: Opacity(
        opacity: enabled ? 1 : 0.4,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(24),
            onTap: onPressed,
            child: Ink(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color.lerp(color, Colors.white, 0.35)!, color],
                ),
                border: Border.all(color: Colors.white, width: 2.5),
                boxShadow: [
                  BoxShadow(color: Color.lerp(color, Colors.black, 0.2)!, offset: const Offset(0, 4)),
                  const BoxShadow(color: Color(0x22000000), blurRadius: 8, offset: Offset(0, 6)),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(icon, color: Colors.white, size: 34),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      label,
                      style: Theme.of(context).textTheme.labelLarge
                          ?.copyWith(color: Colors.white, fontWeight: FontWeight.w800),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Dice [text] (normal o despacio) con la voz de la app.
void speak(BuildContext context, String text, {bool slow = false}) {
  final audio = AppServices.maybeOf(context)?.audio;
  if (audio != null) unawaited(audio.say(text, slow: slow));
}
