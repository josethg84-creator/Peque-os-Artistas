import 'package:flutter/foundation.dart';
import 'package:flutter/rendering.dart';

import 'vector_drawing.dart';

/// Colores aplicados por región que el pintor consulta en cada repintado.
abstract interface class RegionColors implements Listenable {
  Color? colorOf(String regionId);
}

/// Pinta un [VectorDrawing] escalado y centrado en el espacio disponible:
/// cada región con su color (o blanco) y su contorno, en el mismo orden que el
/// SVG; después los detalles. Los contornos se pintan siempre encima del
/// relleno de su región, así que nunca quedan tapados por el color.
class DrawingPainter extends CustomPainter {
  DrawingPainter({required this.drawing, required this.colors}) : super(repaint: colors);

  final VectorDrawing drawing;
  final RegionColors colors;

  static const unpainted = Color(0xFFFFFFFF);

  /// Transformación viewBox → lienzo (escala uniforme, centrada).
  static ({double scale, Offset offset}) fit(Rect viewBox, Size size) {
    final scale = (size.width / viewBox.width) < (size.height / viewBox.height)
        ? size.width / viewBox.width
        : size.height / viewBox.height;
    final offset = Offset(
      (size.width - viewBox.width * scale) / 2 - viewBox.left * scale,
      (size.height - viewBox.height * scale) / 2 - viewBox.top * scale,
    );
    return (scale: scale, offset: offset);
  }

  /// Convierte un punto del lienzo a coordenadas del viewBox.
  static Offset toViewBox(Offset local, Rect viewBox, Size size) {
    final t = fit(viewBox, size);
    return (local - t.offset) / t.scale;
  }

  @override
  void paint(Canvas canvas, Size size) {
    final t = fit(drawing.viewBox, size);
    canvas.save();
    canvas.translate(t.offset.dx, t.offset.dy);
    canvas.scale(t.scale);
    canvas.clipRect(drawing.viewBox);

    final fill = Paint()..style = PaintingStyle.fill;
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;

    for (final region in drawing.regions) {
      fill.color = colors.colorOf(region.id) ?? unpainted;
      canvas.drawPath(region.path, fill);
      final strokeColor = region.strokeColor;
      if (strokeColor != null && region.strokeWidth > 0) {
        stroke
          ..color = strokeColor
          ..strokeWidth = region.strokeWidth;
        canvas.drawPath(region.path, stroke);
      }
    }
    for (final detail in drawing.details) {
      if (detail.kind == DetailKind.stroke) {
        stroke
          ..color = detail.color
          ..strokeWidth = detail.strokeWidth;
        canvas.drawPath(detail.path, stroke);
      } else {
        fill.color = detail.color;
        canvas.drawPath(detail.path, fill);
      }
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(DrawingPainter oldDelegate) =>
      oldDelegate.drawing != drawing || oldDelegate.colors != colors;
}

/// Colores fijos (p. ej. la miniatura de un dibujo guardado).
class FixedRegionColors extends ChangeNotifier implements RegionColors {
  FixedRegionColors(Map<String, Color> colors) : _colors = Map.unmodifiable(colors);

  final Map<String, Color> _colors;

  @override
  Color? colorOf(String regionId) => _colors[regionId];
}
