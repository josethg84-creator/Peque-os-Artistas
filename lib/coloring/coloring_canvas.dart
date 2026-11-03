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
import '../widgets/motion/pressable.dart';
import '../audio/ui_sounds.dart';
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

  /// Ampliación máxima del dibujo (para pintar las zonas pequeñas).
  static const maxZoom = 5.0;

  /// Cuánto amplía o aleja cada toque de los botones + y −.
  static const zoomStep = 1.6;

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

  /// Ampliación y desplazamiento del dibujo (pellizcar o botones + y −).
  final _zoom = TransformationController();
  late final AnimationController _zoomAnimation = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 280),
  );
  Animation<Matrix4>? _zoomTween;
  Size _viewport = Size.zero;

  double get _zoomLevel => _zoom.value.getMaxScaleOnAxis();

  @override
  void initState() {
    super.initState();
    _seenFill = widget.controller.lastFill?.serial ?? 0;
    _encouraged = widget.controller.coloredFraction >= 0.5;
    widget.controller.addListener(_onChange);
    _zoom.addListener(_onZoom);
    _zoomAnimation.addListener(() {
      if (_zoomTween != null) _zoom.value = _zoomTween!.value;
    });
  }

  /// Estado de los botones (ampliado / al máximo) que se está mostrando.
  (bool, bool) _shownZoom = (false, false);

  /// Los botones − y «ver entero» solo aparecen con el dibujo ampliado, y el +
  /// se apaga al llegar al máximo.
  void _onZoom() {
    final state = (_zoomLevel > 1.01, _zoomLevel >= ColoringCanvas.maxZoom - 0.01);
    if (state != _shownZoom) setState(() => _shownZoom = state);
  }

  /// Amplía o aleja con un factor, manteniendo el centro de lo que se ve.
  void _zoomBy(double factor) {
    final current = _zoomLevel;
    final target = (current * factor).clamp(1.0, ColoringCanvas.maxZoom);
    if ((target - current).abs() < 0.001) return;
    final center = _zoom.toScene(_viewport.center(Offset.zero));
    final end = Matrix4.identity()
      ..translateByDouble(_viewport.width / 2, _viewport.height / 2, 0, 1)
      ..scaleByDouble(target, target, 1, 1)
      ..translateByDouble(-center.dx, -center.dy, 0, 1);
    _animateTo(_clamped(end, target));
  }

  /// Mantiene el dibujo dentro del marco (sin huecos al ampliar).
  Matrix4 _clamped(Matrix4 m, double zoom) {
    final w = _viewport.width, h = _viewport.height;
    final t = m.getTranslation();
    final x = t.x.clamp(w - w * zoom, 0.0);
    final y = t.y.clamp(h - h * zoom, 0.0);
    return Matrix4.identity()
      ..translateByDouble(x, y, 0, 1)
      ..scaleByDouble(zoom, zoom, 1, 1);
  }

  void _animateTo(Matrix4 end) {
    if (AppMotion.reduced(context)) {
      _zoom.value = end;
      return;
    }
    _zoomTween = Matrix4Tween(
      begin: _zoom.value,
      end: end,
    ).animate(CurvedAnimation(parent: _zoomAnimation, curve: Curves.easeOutCubic));
    _zoomAnimation.forward(from: 0);
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
    _zoomAnimation.dispose();
    _zoom.dispose();
    _reveal.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vector = widget.controller.drawing!;
    // El pintor se crea una vez por dibujo; los toques solo lo repintan.
    if (_painter != null && _painter!.drawing != vector) {
      // Otro dibujo: se vuelve a ver entero.
      _zoomAnimation.stop();
      _zoom.value = Matrix4.identity();
    }
    final painter = _painter?.drawing == vector
        ? _painter!
        : _painter = DrawingPainter(drawing: vector, colors: widget.controller, fill: _reveal);
    final zoomed = _zoomLevel > 1.01;
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = constraints.biggest;
        _viewport = size;
        return Stack(
          children: [
            Semantics(
              label: 'Dibujo para colorear: ${widget.name}',
              hint: 'Toca una zona para pintarla. Pellizca o usa el botón de ampliar para ver las zonas pequeñas',
              image: true,
              child: InteractiveViewer(
                transformationController: _zoom,
                minScale: 1,
                maxScale: ColoringCanvas.maxZoom,
                onInteractionStart: (_) => _zoomAnimation.stop(),
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTapUp: (details) {
                    // La posición llega ya en coordenadas del dibujo sin ampliar;
                    // el margen de acierto se mantiene en píxeles de la pantalla.
                    final scale = DrawingPainter.fit(vector.viewBox, size).scale * _zoomLevel;
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
            ),
            Positioned(
              right: 4,
              bottom: 4,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (zoomed) ...[
                    _ZoomButton(
                      icon: Icons.fit_screen_rounded,
                      label: 'Ver el dibujo entero',
                      onPressed: () => _animateTo(Matrix4.identity()),
                    ),
                    const SizedBox(height: 6),
                    _ZoomButton(
                      icon: Icons.zoom_out_rounded,
                      label: 'Alejar',
                      onPressed: () => _zoomBy(1 / ColoringCanvas.zoomStep),
                    ),
                    const SizedBox(height: 6),
                  ],
                  _ZoomButton(
                    icon: Icons.zoom_in_rounded,
                    label: 'Ampliar',
                    enabled: _zoomLevel < ColoringCanvas.maxZoom - 0.01,
                    onPressed: () => _zoomBy(ColoringCanvas.zoomStep),
                  ),
                ],
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

/// Botón redondo de ampliar, alejar o ver entero, en la esquina del lienzo.
class _ZoomButton extends StatelessWidget {
  const _ZoomButton({required this.icon, required this.label, required this.onPressed, this.enabled = true});

  final IconData icon;
  final String label;
  final VoidCallback onPressed;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final action = enabled ? withSound(context, SoundCue.tap, onPressed) : null;
    return Semantics(
      button: true,
      enabled: enabled,
      label: label,
      excludeSemantics: true,
      onTap: action,
      child: Tooltip(
        message: label,
        child: Pressable(
          enabled: enabled,
          child: GestureDetector(
            onTap: action,
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 150),
              opacity: enabled ? 1 : 0.4,
              child: Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.92),
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.inkSoft.withValues(alpha: 0.35), width: 2),
                  boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 6, offset: Offset(0, 2))],
                ),
                child: Icon(icon, color: AppColors.ink, size: 28),
              ),
            ),
          ),
        ),
      ),
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
