import 'dart:ui';

import 'svg_path_parser.dart';
import 'vector_drawing.dart';

/// Lee los SVG de la Fase 1 (ver docs/DIBUJOS.md):
///
/// ```xml
/// <svg viewBox="0 0 1024 1024">
///   <g id="regiones"> <path id="..." class="region" fill=".." stroke=".." stroke-width=".." d="...Z"/> ... </g>
///   <g id="detalles"> <path class="detalle" ... d="..."/> ... </g>
/// </svg>
/// ```
///
/// Es un lector deliberadamente pequeño para ese formato controlado (que
/// valida `tools/validate_assets.py`), no un intérprete SVG general: no admite
/// `transform`, `<use>`, estilos CSS ni otras figuras. Ante cualquier
/// desviación lanza [DrawingFormatException] en lugar de dibujar algo erróneo.
VectorDrawing parseColoringSvg(String svg) {
  final viewBox = _viewBox(svg);
  final regions = <DrawingRegion>[];
  final details = <DrawingDetail>[];
  final groups = <String?>[];

  for (final tag in _tag.allMatches(svg)) {
    final closing = tag[1] == '/';
    final name = tag[2]!;
    final attrs = _attributes(tag[3] ?? '');
    final selfClosing = tag[4] == '/';
    if (name == 'g') {
      if (closing) {
        if (groups.isNotEmpty) groups.removeLast();
      } else if (!selfClosing) {
        groups.add(attrs['id']);
      }
      continue;
    }
    if (closing) continue;
    if (attrs.containsKey('transform')) {
      throw DrawingFormatException('transform no admitido en <$name>');
    }
    if (name != 'path') {
      if (const {'svg', 'title', 'desc'}.contains(name)) continue;
      throw DrawingFormatException('elemento no admitido: <$name>');
    }
    final group = groups.isEmpty ? null : groups.last;
    final d = attrs['d'];
    if (d == null) throw DrawingFormatException('<path> sin atributo d');

    if (group == 'regiones') {
      final id = attrs['id'];
      if (id == null || id.isEmpty) throw DrawingFormatException('región sin id');
      if (regions.any((r) => r.id == id)) throw DrawingFormatException('id de región duplicado: $id');
      if (!d.trimRight().toUpperCase().endsWith('Z')) {
        throw DrawingFormatException('la región $id no es un trazado cerrado');
      }
      // El relleno original debe ser un color plano (normalmente blanco).
      _color(attrs['fill']);
      final stroke = _color(attrs['stroke']);
      regions.add(
        DrawingRegion(
          id: id,
          path: parseSvgPathData(d),
          strokeColor: stroke,
          strokeWidth: stroke == null ? 0 : double.tryParse(attrs['stroke-width'] ?? '') ?? 1,
        ),
      );
    } else if (group == 'detalles') {
      final fill = _color(attrs['fill']);
      final stroke = _color(attrs['stroke']);
      final path = parseSvgPathData(d);
      if (stroke != null) {
        details.add(
          DrawingDetail(
            path: path,
            kind: DetailKind.stroke,
            color: stroke,
            strokeWidth: double.tryParse(attrs['stroke-width'] ?? '') ?? 1,
          ),
        );
      } else if (fill != null) {
        details.add(DrawingDetail(path: path, kind: DetailKind.fill, color: fill));
      }
    } else {
      throw DrawingFormatException('<path> fuera de los grupos "regiones" o "detalles"');
    }
  }

  if (regions.isEmpty) throw DrawingFormatException('el dibujo no tiene regiones');
  return VectorDrawing(viewBox: viewBox, regions: regions, details: details);
}

final _tag = RegExp(r'<(/?)([a-zA-Z][\w:-]*)((?:\s+[\w:-]+\s*=\s*"[^"]*")*)\s*(/?)>');
final _attr = RegExp(r'([\w:-]+)\s*=\s*"([^"]*)"');

Map<String, String> _attributes(String source) => {for (final m in _attr.allMatches(source)) m[1]!: m[2]!};

Rect _viewBox(String svg) {
  final root = RegExp(r'<svg\b[^>]*>').firstMatch(svg);
  if (root == null) throw DrawingFormatException('no es un archivo SVG');
  final value = _attributes(root[0]!.substring(4, root[0]!.length - 1))['viewBox'];
  final parts = value?.trim().split(RegExp(r'[\s,]+')).map(double.tryParse).toList();
  if (parts == null || parts.length != 4 || parts.contains(null) || parts[2]! <= 0 || parts[3]! <= 0) {
    throw DrawingFormatException('viewBox ausente o no válido');
  }
  return Rect.fromLTWH(parts[0]!, parts[1]!, parts[2]!, parts[3]!);
}

Color? _color(String? value) {
  if (value == null || value == 'none') return null;
  final hex = RegExp(r'^#([0-9a-fA-F]{6})$').firstMatch(value);
  if (hex == null) throw DrawingFormatException('color no admitido: $value');
  return Color(0xFF000000 | int.parse(hex[1]!, radix: 16));
}
