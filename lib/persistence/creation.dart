import 'dart:convert';
import 'dart:ui';

/// Estado de una creación, calculado a partir de las zonas pintadas.
enum CreationStatus {
  notStarted('sin_comenzar'),
  inProgress('en_progreso'),
  completed('terminado');

  const CreationStatus(this.id);
  final String id;
}

/// Una creación del niño: los colores aplicados a UN dibujo del catálogo.
///
/// Solo se guardan datos (región → color), nunca imágenes: la miniatura se
/// reconstruye pintando el dibujo vectorial con estos colores. El archivo
/// original del dibujo no se modifica jamás.
class Creation {
  Creation({
    required this.id,
    required this.drawingId,
    required Map<String, Color> regionColors,
    required this.createdAt,
    required this.updatedAt,
    required this.totalRegions,
  }) : regionColors = Map.unmodifiable(regionColors);

  /// Versión actual del formato guardado (la 1 era «un progreso por dibujo»).
  static const formatVersion = 2;

  /// El fondo se puede pintar, pero no cuenta para el progreso.
  static const backgroundId = 'fondo';

  final String id;
  final String drawingId;
  final Map<String, Color> regionColors;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// Zonas del dibujo sin contar el fondo (0 = desconocido, p. ej. migrado).
  final int totalRegions;

  int get paintedRegions => regionColors.keys.where((k) => k != backgroundId).length;

  /// «Terminado» solo cuando todas las zonas (sin el fondo) tienen color: es
  /// un criterio fiable porque se conoce exactamente cada zona del dibujo.
  CreationStatus get status {
    if (regionColors.isEmpty) return CreationStatus.notStarted;
    if (totalRegions > 0 && paintedRegions >= totalRegions) return CreationStatus.completed;
    return CreationStatus.inProgress;
  }

  /// Fracción de zonas pintadas (0..1), o `null` si no se conoce el total.
  double? get progress => totalRegions > 0 ? (paintedRegions / totalRegions).clamp(0.0, 1.0) : null;

  static final idPattern = RegExp(r'^[a-z0-9_-]{1,80}$');

  Map<String, Object> _payload() => {
    'format_version': formatVersion,
    'id': id,
    'drawing_id': drawingId,
    'created_at': createdAt.toUtc().toIso8601String(),
    'updated_at': updatedAt.toUtc().toIso8601String(),
    'total_regions': totalRegions,
    'painted_regions': paintedRegions,
    'status': status.id,
    'regions': {for (final k in (regionColors.keys.toList()..sort())) k: colorToHex(regionColors[k]!)},
  };

  /// JSON con una suma de verificación para detectar datos alterados o a medias.
  String encode() {
    final payload = _payload();
    return jsonEncode({...payload, 'checksum': checksumOf(payload)});
  }

  /// Lee una creación guardada. Lanza [FormatException] si los datos están
  /// incompletos, dañados o son de otra versión.
  static Creation decode(String raw) {
    final Object? json;
    try {
      json = jsonDecode(raw);
    } on FormatException {
      throw const FormatException('JSON incompleto o dañado');
    }
    if (json is! Map<String, dynamic>) throw const FormatException('no es un objeto');
    if (json['format_version'] != formatVersion) {
      throw FormatException('versión de formato ${json['format_version']}');
    }
    final checksum = json['checksum'];
    final payload = Map<String, dynamic>.of(json)..remove('checksum');
    if (checksum is! String || checksum != checksumOf(payload)) {
      throw const FormatException('la suma de verificación no coincide');
    }
    final id = json['id'];
    final drawingId = json['drawing_id'];
    final created = _date(json['created_at']);
    final updated = _date(json['updated_at']);
    final total = json['total_regions'];
    final regions = json['regions'];
    if (id is! String || !idPattern.hasMatch(id)) throw const FormatException('id no válido');
    if (drawingId is! String || drawingId.isEmpty) throw const FormatException('dibujo no válido');
    if (created == null || updated == null) throw const FormatException('fechas no válidas');
    if (total is! int || total < 0) throw const FormatException('total de zonas no válido');
    if (regions is! Map<String, dynamic>) throw const FormatException('colores no válidos');
    final colors = <String, Color>{};
    for (final e in regions.entries) {
      final color = colorFromHex(e.value);
      if (color == null) throw FormatException('color no válido en ${e.key}');
      colors[e.key] = color;
    }
    return Creation(
      id: id,
      drawingId: drawingId,
      regionColors: colors,
      createdAt: created,
      updatedAt: updated,
      totalRegions: total,
    );
  }

  static String colorToHex(Color c) => '#${c.toARGB32().toRadixString(16).padLeft(8, '0').toUpperCase()}';

  static Color? colorFromHex(Object? value) {
    if (value is! String) return null;
    final m = RegExp(r'^#([0-9a-fA-F]{8})$').firstMatch(value);
    return m == null ? null : Color(int.parse(m[1]!, radix: 16));
  }

  /// FNV-1a de 32 bits sobre el JSON canónico (claves ordenadas). No es
  /// criptográfico: solo detecta escrituras truncadas o datos alterados.
  static String checksumOf(Map<String, dynamic> payload) {
    var hash = 0x811c9dc5;
    for (final byte in utf8.encode(_canonical(payload))) {
      hash ^= byte;
      hash = (hash * 0x01000193) & 0xFFFFFFFF;
    }
    return hash.toRadixString(16).padLeft(8, '0');
  }

  static String _canonical(Object? value) {
    if (value is Map) {
      final keys = value.keys.map((k) => k.toString()).toList()..sort();
      return '{${keys.map((k) => '${jsonEncode(k)}:${_canonical(value[k])}').join(',')}}';
    }
    return jsonEncode(value);
  }
}

/// Fecha guardada como texto ISO; cualquier otro tipo cuenta como ausente.
DateTime? _date(Object? value) => value is String ? DateTime.tryParse(value) : null;
