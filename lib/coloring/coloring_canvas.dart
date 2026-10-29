import 'package:flutter/material.dart';

import '../models/drawing.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import 'coloring_controller.dart';
import 'engine/drawing_painter.dart';

/// Área central del lienzo: el dibujo vectorial escalado y centrado, sin
/// deformarse, dentro de un marco cuadrado. Cada toque se convierte a
/// coordenadas del dibujo y pinta la región correspondiente.
class ColoringCanvas extends StatelessWidget {
  const ColoringCanvas({super.key, required this.drawing, required this.controller});

  final Drawing drawing;
  final ColoringController controller;

  /// Margen de acierto alrededor de las figuras, en píxeles lógicos.
  static const touchTolerance = 12.0;

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
              ColoringStatus.loading => const Center(
                child: CircularProgressIndicator(color: AppColors.coral, semanticsLabel: 'Cargando dibujo'),
              ),
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

class _InteractiveDrawingState extends State<_InteractiveDrawing> {
  DrawingPainter? _painter;

  @override
  Widget build(BuildContext context) {
    final vector = widget.controller.drawing!;
    // El pintor se crea una vez por dibujo; los toques solo lo repintan.
    final painter = _painter?.drawing == vector
        ? _painter!
        : _painter = DrawingPainter(drawing: vector, colors: widget.controller);
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = constraints.biggest;
        return Semantics(
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
        );
      },
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
