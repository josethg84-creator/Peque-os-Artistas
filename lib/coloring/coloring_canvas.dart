import 'dart:async';

import 'package:flutter/material.dart';

import '../models/drawing.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../audio/phrases.dart';
import '../learning/audio/learning_audio.dart';
import '../services/app_services.dart';
import '../theme/app_motion.dart';
import '../widgets/mascot.dart';
import '../widgets/motion/celebration.dart';
import '../widgets/motion/delayed_loading.dart';
import 'coloring_controller.dart';
import 'engine/drawing_painter.dart';

/// Área central del lienzo: el dibujo vectorial escalado y centrado, sin
/// deformarse, dentro de un marco cuadrado. Cada toque se convierte a
/// coordenadas del dibujo y pinta la región correspondiente.
class ColoringCanvas extends StatelessWidget {
  /// «¡Elige tu color favorito!» solo con el primer dibujo de cada sesión.
  static bool _greetedThisSession = false;

  @visibleForTesting
  static void resetSessionGreeting() => _greetedThisSession = false;

  const ColoringCanvas({super.key, required this.drawing, required this.controller});

  final Drawing drawing;
  final ColoringController controller;

  /// Margen de acierto alrededor de las figuras, en píxeles lógicos.
  static const touchTolerance = 12.0;

  /// Duración de la animación de relleno (solo visual).
  static const fillDuration = Duration(milliseconds: 260);

  /// Mensajes de la celebración al terminar un dibujo (van rotando).
  static const completionMessages = [
    '¡Lo has conseguido!',
    '¡Qué gran trabajo!',
    '¡Tu creatividad es genial!',
    '¡Sigue creando!',
  ];

  @override
  Widget build(BuildContext context) {
    return Center(
      child: AspectRatio(
        aspectRatio: 1,
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
            border: Border.all(color: drawing.category.color, width: 6),
            boxShadow: const [BoxShadow(color: Color(0x22000000), blurRadius: 12, offset: Offset(0, 4))],
          ),
          clipBehavior: Clip.antiAlias,
          padding: const EdgeInsets.all(8),
          // El lienzo solo se reconstruye cuando cambia el estado de carga;
          // los colores se repintan directamente sin reconstruir widgets.
          child: ListenableBuilder(
            listenable: controller,
            builder: (context, _) => switch (controller.status) {
              ColoringStatus.loading => const DelayedLoading(message: 'Abriendo tu dibujo…'),
              ColoringStatus.error => _LoadError(message: controller.errorMessage, onRetry: controller.load),
              ColoringStatus.ready => _InteractiveDrawing(name: drawing.name, controller: controller),
            },
          ),
        ),
      ),
    );
  }
}

class _InteractiveDrawing extends StatefulWidget {
  const _InteractiveDrawing({required this.name, required this.controller});

  final String name;
  final ColoringController controller;

  @override
  State<_InteractiveDrawing> createState() => _InteractiveDrawingState();
}

class _InteractiveDrawingState extends State<_InteractiveDrawing> with TickerProviderStateMixin {
  DrawingPainter? _painter;
  late final _RevealAnimation _reveal = _RevealAnimation(
    AnimationController(vsync: this, duration: ColoringCanvas.fillDuration),
  );
  int _seenFill = 0;
  late int _seenCompletion = widget.controller.completionSerial;
  int _celebrations = 0;

  /// El ánimo de «vas por la mitad» se dice una vez por dibujo abierto.
  bool _encouraged = false;

  @override
  void initState() {
    super.initState();
    _seenFill = widget.controller.lastFill?.serial ?? 0;
    _encouraged = widget.controller.coloredFraction >= 0.5;
    widget.controller.addListener(_onChange);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (ColoringCanvas._greetedThisSession) return;
    final audio = AppServices.maybeOf(context)?.audio;
    if (audio == null) return;
    ColoringCanvas._greetedThisSession = true;
    if (widget.controller.coloredFraction == 0) {
      unawaited(audio.sayOneOf(Phrases.coloringStart, mode: VoiceMode.ambient));
    }
  }

  /// Reacciona a los toques: anima el relleno y, si el dibujo se acaba de
  /// terminar, lanza la celebración. El color ya está aplicado en el modelo.
  void _onChange() {
    final c = widget.controller;
    final audio = AppServices.maybeOf(context)?.audio;
    final fill = c.lastFill;
    if (fill != null && fill.serial != _seenFill) {
      _seenFill = fill.serial;
      _reveal.start(fill, animate: !AppMotion.reduced(context));
      if (c.completionSerial == _seenCompletion) unawaited(audio?.play(SoundCue.pop) ?? Future.value());
    }
    if (c.completionSerial != _seenCompletion) {
      _seenCompletion = c.completionSerial;
      _encouraged = true;
      unawaited(audio?.play(SoundCue.celebrate) ?? Future.value());
      unawaited(audio?.sayOneOf(Phrases.drawingDone, mode: VoiceMode.queue) ?? Future.value());
      setState(() => _celebrations++);
    } else if (!_encouraged && c.coloredFraction >= 0.5) {
      _encouraged = true;
      unawaited(audio?.sayOneOf(Phrases.coloringProgress, mode: VoiceMode.ambient) ?? Future.value());
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onChange);
    _reveal.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vector = widget.controller.drawing!;
    // El pintor se crea una vez por dibujo; los toques solo lo repintan.
    final painter = _painter?.drawing == vector
        ? _painter!
        : _painter = DrawingPainter(drawing: vector, colors: widget.controller, fill: _reveal);
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = constraints.biggest;
        return Stack(
          children: [
            Semantics(
              label: 'Dibujo para colorear: ${widget.name}',
              hint: 'Toca una zona para pintarla',
              image: true,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapUp: (details) {
                  final scale = DrawingPainter.fit(vector.viewBox, size).scale;
                  widget.controller.tapAt(
                    DrawingPainter.toViewBox(details.localPosition, vector.viewBox, size),
                    tolerance: ColoringCanvas.touchTolerance / scale,
                  );
                },
                child: RepaintBoundary(
                  child: CustomPaint(size: size, painter: painter),
                ),
              ),
            ),
            if (_celebrations > 0)
              Positioned.fill(
                child: _CompletionCelebration(
                  key: ValueKey(_celebrations),
                  color: widget.controller.color.color,
                ),
              ),
          ],
        );
      },
    );
  }
}

/// Animación del último relleno, compartida con el pintor.
class _RevealAnimation extends ChangeNotifier implements FillReveal {
  _RevealAnimation(this._controller) {
    _controller.addListener(notifyListeners);
  }

  final AnimationController _controller;
  FillEvent? _event;

  void start(FillEvent event, {required bool animate}) {
    _event = event;
    if (animate) {
      _controller.forward(from: 0);
    } else {
      _controller.value = 1;
    }
  }

  @override
  bool get isActive => _event != null && _controller.isAnimating;
  @override
  String get regionId => _event!.regionId;
  @override
  Color? get from => _event?.from;
  @override
  Color? get to => _event?.to;
  @override
  Offset? get origin => _event?.origin;
  @override
  double get progress => Curves.easeOutCubic.transform(_controller.value);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}

/// Celebración al terminar el dibujo: confeti, Pincelín y un mensaje. Dura
/// unos segundos, se oculta sola y no bloquea los toques.
class _CompletionCelebration extends StatefulWidget {
  const _CompletionCelebration({super.key, required this.color});

  final Color color;

  static const messages = ColoringCanvas.completionMessages;
  static const duration = Duration(milliseconds: 3200);

  @override
  State<_CompletionCelebration> createState() => _CompletionCelebrationState();
}

class _CompletionCelebrationState extends State<_CompletionCelebration> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: _CompletionCelebration.duration,
  )..forward();
  static int _count = 0;
  final String _message = _CompletionCelebration.messages[_count++ % _CompletionCelebration.messages.length];

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, child) {
          if (_c.isCompleted) return const SizedBox.shrink();
          final v = _c.value;
          final opacity = v < 0.08 ? v / 0.08 : (v > 0.85 ? (1 - v) / 0.15 : 1.0);
          return Opacity(opacity: opacity.clamp(0.0, 1.0), child: child);
        },
        child: Stack(
          children: [
            const Positioned.fill(child: ConfettiBurst()),
            Align(
              alignment: Alignment.bottomCenter,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Semantics(
                  liveRegion: true,
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(8, 6, 16, 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
                      border: Border.all(color: AppColors.sun, width: 3),
                      boxShadow: const [
                        BoxShadow(color: Color(0x26000000), blurRadius: 10, offset: Offset(0, 4)),
                      ],
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Mascot(size: 56, waves: 2, paintColor: widget.color),
                        const SizedBox(width: 8),
                        Flexible(child: Text(_message, style: Theme.of(context).textTheme.titleLarge)),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.message, required this.onRetry});

  final String? message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.broken_image_rounded, size: 72, color: AppColors.inkSoft),
            const SizedBox(height: 8),
            Text(
              'No pudimos abrir este dibujo',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            if (message != null)
              Text(
                message!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.inkSoft),
              ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}
