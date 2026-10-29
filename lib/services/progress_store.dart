import 'dart:convert';
import 'dart:ui';

import 'package:flutter/foundation.dart';

import 'package:shared_preferences/shared_preferences.dart';

/// Progreso guardado de un dibujo. No modifica nunca el archivo original:
/// solo guarda qué color tiene cada región pintada.
class SavedProgress {
  SavedProgress({required this.drawingId, required Map<String, Color> regionColors, required this.updatedAt})
    : regionColors = Map.unmodifiable(regionColors);

  /// Versión del formato de guardado. Si cambia, los datos antiguos se
  /// descartan de forma controlada en lugar de interpretarse mal.
  static const formatVersion = 1;

  final String drawingId;
  final Map<String, Color> regionColors;
  final DateTime updatedAt;

  Map<String, Object> toJson() => {
    'format_version': formatVersion,
    'drawing_id': drawingId,
    'updated_at': updatedAt.toUtc().toIso8601String(),
    'regions': {for (final e in regionColors.entries) e.key: _hex(e.value)},
  };

  /// Devuelve `null` si los datos están dañados o son de otra versión.
  static SavedProgress? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    if (json['format_version'] != formatVersion) return null;
    final id = json['drawing_id'];
    final regions = json['regions'];
    final updated = DateTime.tryParse(json['updated_at'] as String? ?? '');
    if (id is! String || regions is! Map<String, dynamic> || updated == null) return null;
    final colors = <String, Color>{};
    for (final e in regions.entries) {
      final color = _parseHex(e.value);
      if (color != null) colors[e.key] = color;
    }
    return SavedProgress(drawingId: id, regionColors: colors, updatedAt: updated);
  }

  static String _hex(Color c) => '#${c.toARGB32().toRadixString(16).padLeft(8, '0').toUpperCase()}';

  static Color? _parseHex(Object? value) {
    if (value is! String) return null;
    final m = RegExp(r'^#([0-9a-fA-F]{8})$').firstMatch(value);
    return m == null ? null : Color(int.parse(m[1]!, radix: 16));
  }
}

/// Almacén local del progreso de cada dibujo.
abstract interface class ProgressStore {
  /// Avisa cuando se ha terminado de guardar o borrar algún progreso.
  Listenable get changes;

  Future<SavedProgress?> load(String drawingId);
  Future<void> save(SavedProgress progress);
  Future<void> delete(String drawingId);

  /// Todos los progresos guardados, del más reciente al más antiguo.
  Future<List<SavedProgress>> loadAll();
}

/// Implementación con `shared_preferences` (archivo local privado de la app).
class SharedPreferencesProgressStore with _ChangeSignal implements ProgressStore {
  SharedPreferencesProgressStore([SharedPreferencesAsync? prefs])
    : _prefs = prefs ?? SharedPreferencesAsync();

  static const keyPrefix = 'progress.v${SavedProgress.formatVersion}.';

  final SharedPreferencesAsync _prefs;

  @override
  Future<SavedProgress?> load(String drawingId) async {
    try {
      final raw = await _prefs.getString('$keyPrefix$drawingId');
      if (raw == null) return null;
      final progress = SavedProgress.fromJson(jsonDecode(raw));
      return progress?.drawingId == drawingId ? progress : null;
    } catch (_) {
      return null; // Datos dañados: se empieza de cero sin bloquear al niño.
    }
  }

  @override
  Future<void> save(SavedProgress progress) async {
    await _prefs.setString('$keyPrefix${progress.drawingId}', jsonEncode(progress.toJson()));
    _signal();
  }

  @override
  Future<void> delete(String drawingId) async {
    await _prefs.remove('$keyPrefix$drawingId');
    _signal();
  }

  @override
  Future<List<SavedProgress>> loadAll() async {
    final keys = await _prefs.getKeys();
    final result = <SavedProgress>[];
    for (final key in keys.where((k) => k.startsWith(keyPrefix))) {
      final progress = await load(key.substring(keyPrefix.length));
      if (progress != null) result.add(progress);
    }
    result.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return result;
  }
}

/// Almacén en memoria (pruebas y entornos sin almacenamiento).
class InMemoryProgressStore with _ChangeSignal implements ProgressStore {
  final _data = <String, String>{};

  /// Contenido serializado, para inspeccionarlo en las pruebas.
  Map<String, String> get raw => _data;

  @override
  Future<SavedProgress?> load(String drawingId) async {
    final raw = _data[drawingId];
    if (raw == null) return null;
    try {
      return SavedProgress.fromJson(jsonDecode(raw));
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> save(SavedProgress progress) async {
    _data[progress.drawingId] = jsonEncode(progress.toJson());
    _signal();
  }

  @override
  Future<void> delete(String drawingId) async {
    _data.remove(drawingId);
    _signal();
  }

  @override
  Future<List<SavedProgress>> loadAll() async {
    final all = [for (final id in _data.keys) await load(id)].whereType<SavedProgress>().toList();
    all.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return all;
  }
}

/// Aviso de cambios compartido por los almacenes.
mixin _ChangeSignal {
  final _changes = _Signal();

  Listenable get changes => _changes;

  void _signal() => _changes.fire();
}

class _Signal extends ChangeNotifier {
  void fire() => notifyListeners();
}
