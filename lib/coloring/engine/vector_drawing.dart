import 'dart:ui';

/// Zona coloreable de un dibujo: un trazado cerrado con identificador único.
class DrawingRegion {
  DrawingRegion({required this.id, required this.path, this.strokeColor, this.strokeWidth = 0})
    : bounds = path.getBounds();

  final String id;
  final Path path;

  /// Rectángulo que contiene la región; descarta rápido los toques lejanos.
  final Rect bounds;

  /// Contorno de la región (null = sin contorno, como el fondo).
  final Color? strokeColor;
  final double strokeWidth;

  bool contains(Offset point) => bounds.contains(point) && path.contains(point);
}

enum DetailKind { stroke, fill }

/// Trazo decorativo (ojos, bocas...). Se pinta encima de los colores y no
/// recibe toques.
class DrawingDetail {
  const DrawingDetail({required this.path, required this.kind, required this.color, this.strokeWidth = 0});

  final Path path;
  final DetailKind kind;
  final Color color;
  final double strokeWidth;
}

/// Dibujo vectorial listo para colorear: regiones en orden de pintado (de
/// atrás hacia adelante) y detalles. Se construye una sola vez por archivo.
class VectorDrawing {
  VectorDrawing({
    required this.viewBox,
    required List<DrawingRegion> regions,
    required List<DrawingDetail> details,
  }) : regions = List.unmodifiable(regions),
       details = List.unmodifiable(details),
       _byId = {for (final r in regions) r.id: r};

  /// Id de la región de fondo según el formato de la Fase 1.
  static const backgroundId = 'fondo';

  final Rect viewBox;
  final List<DrawingRegion> regions;
  final List<DrawingDetail> details;
  final Map<String, DrawingRegion> _byId;

  DrawingRegion? region(String id) => _byId[id];
  bool hasRegion(String id) => _byId.containsKey(id);

  /// Región visible en [point] (coordenadas del viewBox): la última de la lista
  /// que lo contiene, igual que en el SVG.
  String? regionAt(Offset point) {
    for (var i = regions.length - 1; i >= 0; i--) {
      if (regions[i].contains(point)) return regions[i].id;
    }
    return null;
  }

  /// Igual que [regionAt], pero si el toque cae en el fondo (o fuera) muy
  /// cerca de una figura, elige esa figura: los dedos pequeños no siempre
  /// aciertan en las zonas estrechas. [tolerance] va en unidades del viewBox.
  String? hitTest(Offset point, {double tolerance = 0}) {
    final direct = regionAt(point);
    if (tolerance <= 0 || (direct != null && direct != backgroundId)) return direct;

    final votes = <String, int>{};
    for (final radius in [tolerance / 2, tolerance]) {
      for (var k = 0; k < 8; k++) {
        final angle = k * 3.141592653589793 / 4;
        final sample = point + Offset.fromDirection(angle, radius);
        final id = regionAt(sample);
        if (id != null && id != backgroundId) votes[id] = (votes[id] ?? 0) + 1;
      }
    }
    if (votes.isEmpty) return direct;
    // Más votos gana; a igualdad, la región que está más arriba.
    String? best;
    var bestVotes = 0;
    for (final r in regions) {
      final v = votes[r.id] ?? 0;
      if (v > 0 && v >= bestVotes) {
        best = r.id;
        bestVotes = v;
      }
    }
    return best;
  }
}
