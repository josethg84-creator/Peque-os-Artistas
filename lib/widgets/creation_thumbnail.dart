import 'package:flutter/material.dart';

import '../coloring/engine/drawing_painter.dart';
import '../coloring/engine/vector_drawing.dart';
import '../models/drawing.dart';
import '../persistence/creation.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';

/// Miniatura de una creación guardada: el dibujo con los colores del niño.
class CreationThumbnail extends StatefulWidget {
  const CreationThumbnail({super.key, required this.drawing, required this.creation});

  final Drawing drawing;
  final Creation creation;

  @override
  State<CreationThumbnail> createState() => _CreationThumbnailState();
}

class _CreationThumbnailState extends State<CreationThumbnail> {
  Future<VectorDrawing>? _vector;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _vector ??= AppServices.of(context).drawings.load(widget.drawing.file);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<VectorDrawing>(
      future: _vector,
      builder: (context, snapshot) {
        final vector = snapshot.data;
        if (vector == null) {
          return snapshot.hasError
              ? const Icon(Icons.broken_image_rounded, size: 48, color: AppColors.inkSoft)
              : const SizedBox.shrink();
        }
        return RepaintBoundary(
          child: CustomPaint(
            painter: DrawingPainter(drawing: vector, colors: FixedRegionColors(widget.creation.regionColors)),
          ),
        );
      },
    );
  }
}
