import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../persistence/creation.dart';
import '../persistence/key_value_backend.dart';

/// Progreso de «Aprendo a leer», guardado SOLO en el dispositivo con su
/// propia clave (`reading.v1.state`): no toca el progreso de otros módulos.
/// Solo cuenta lo que se ha hecho; no hay notas ni etiquetas.
class ReadingProgress {
  ReadingProgress({
    Map<String, Set<String>>? completed,
    Set<String>? firstTry,
    Set<String>? withHints,
    this.correctAnswers = 0,
    this.attempts = 0,
  }) : completed = completed ?? {},
       firstTry = firstTry ?? {},
       withHints = withHints ?? {};

  /// Ejercicio → modos en que se completó («elige», «arrastra», «ordena»).
  final Map<String, Set<String>> completed;

  /// «modo:ejercicio» acertados a la primera.
  final Set<String> firstTry;

  /// «modo:ejercicio» completados usando alguna pista.
  final Set<String> withHints;

  /// Respuestas correctas e intentos (cada «Comprobar»).
  int correctAnswers;
  int attempts;

  static String key(String mode, String exerciseId) => '$mode:$exerciseId';

  Map<String, dynamic> toJson() => {
    'completed': {
      for (final e in (completed.entries.toList()..sort((a, b) => a.key.compareTo(b.key))))
        e.key: (e.value.toList()..sort()),
    },
    'first_try': firstTry.toList()..sort(),
    'with_hints': withHints.toList()..sort(),
    'correct_answers': correctAnswers,
    'attempts': attempts,
  };

  static ReadingProgress fromJson(Map<String, dynamic> json) {
    Set<String> strings(Object? v) => {...(v is List ? v : const []).whereType<String>()};
    int count(Object? v) => v is int && v >= 0 ? v : 0;
    return ReadingProgress(
      completed: {
        if (json['completed'] case final Map<String, dynamic> m)
          for (final e in m.entries) e.key: strings(e.value),
      },
      firstTry: strings(json['first_try']),
      withHints: strings(json['with_hints']),
      correctAnswers: count(json['correct_answers']),
      attempts: count(json['attempts']),
    );
  }
}

class ReadingStore {
  ReadingStore(this.backend);

  static const key = 'reading.v1.state';
  static const backupKey = '$key.bak';
  static const formatVersion = 1;

  final KeyValueBackend backend;

  static String encode(ReadingProgress p) {
    final payload = {'format_version': formatVersion, ...p.toJson()};
    return jsonEncode({...payload, 'checksum': Creation.checksumOf(payload)});
  }

  /// `null` si está dañado (JSON roto, versión desconocida o checksum que no cuadra).
  static ReadingProgress? decode(String? raw) {
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw);
      if (json is! Map<String, dynamic> || json['format_version'] != formatVersion) return null;
      final payload = {...json}..remove('checksum');
      if (json['checksum'] != Creation.checksumOf(payload)) return null;
      return ReadingProgress.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  Future<ReadingProgress> load() async =>
      decode(await backend.read(key)) ?? decode(await backend.read(backupKey)) ?? ReadingProgress();

  Future<void> save(ReadingProgress p) async {
    final current = await backend.read(key);
    if (decode(current) != null) await backend.write(backupKey, current!);
    await backend.write(key, encode(p));
  }

  Future<void> clear() async {
    await backend.remove(key);
    await backend.remove(backupKey);
  }
}

/// Lleva el progreso de «Aprendo a leer» y lo guarda al momento.
class ReadingController extends ChangeNotifier {
  ReadingController(this._store);

  final ReadingStore _store;
  ReadingProgress _progress = ReadingProgress();
  ReadingProgress get progress => _progress;

  /// Ejercicios completados de un nivel para desbloquear el siguiente.
  static const unlockAfter = 8;

  Future<void>? _loading;
  Future<void> load() => _loading ??= () async {
    try {
      _progress = await _store.load();
    } catch (_) {
      // Sin almacenamiento, el juego funciona igual (sin guardar).
    }
    notifyListeners();
  }();

  /// Cada «Comprobar».
  void recordAttempt({required bool correct}) {
    _progress.attempts++;
    if (correct) _progress.correctAnswers++;
    _changed();
  }

  /// Un ejercicio terminado en un modo.
  void recordCompleted(String exerciseId, String mode, {required bool firstTry, required bool usedHints}) {
    (_progress.completed[exerciseId] ??= {}).add(mode);
    final k = ReadingProgress.key(mode, exerciseId);
    if (firstTry) _progress.firstTry.add(k);
    if (usedHints) _progress.withHints.add(k);
    _changed();
  }

  bool isCompleted(String exerciseId, String mode) =>
      _progress.completed[exerciseId]?.contains(mode) ?? false;

  /// Cuántos de [exerciseIds] están completos en [mode].
  int completedIn(Iterable<String> exerciseIds, String mode) =>
      exerciseIds.where((id) => isCompleted(id, mode)).length;

  void _changed() {
    notifyListeners();
    unawaited(_save());
  }

  Future<void>? _saving;
  bool _dirty = false;

  Future<void> _save() async {
    if (_saving != null) {
      _dirty = true;
      return _saving;
    }
    final done = Completer<void>();
    _saving = done.future;
    try {
      do {
        _dirty = false;
        try {
          await _store.save(_progress);
        } catch (_) {}
      } while (_dirty);
    } finally {
      _saving = null;
      done.complete();
    }
  }

  /// Borra el progreso de lectura (zona de adultos).
  Future<void> clearAll() async {
    _progress = ReadingProgress();
    notifyListeners();
    while (_saving != null) {
      await _saving;
    }
    try {
      await _store.clear();
    } catch (_) {}
  }

  /// Espera a que termine lo que se esté guardando (pruebas y cierre).
  @visibleForTesting
  Future<void> flush() async {
    while (_saving != null) {
      await _saving;
    }
  }
}
