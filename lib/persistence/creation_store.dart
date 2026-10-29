import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/painting.dart';

import 'creation.dart';
import 'key_value_backend.dart';

/// Error al leer o escribir en el almacenamiento del dispositivo.
class StorageException implements Exception {
  StorageException(this.message);
  final String message;

  @override
  String toString() => 'StorageException: $message';
}

enum StoredProblemKind {
  /// Ni la copia principal ni la de seguridad se pueden leer.
  damaged,

  /// Datos de una versión antigua que no se pudieron migrar.
  unmigrated,
}

/// Datos guardados que no se pueden mostrar. Se conservan (nunca se borran
/// automáticamente) y la zona para adultos permite revisarlos.
class StoredProblem {
  const StoredProblem({required this.key, required this.kind, required this.reason});
  final String key;
  final StoredProblemKind kind;
  final String reason;
}

class CreationReport {
  const CreationReport({required this.creations, this.problems = const [], this.recovered = const []});

  /// Creaciones válidas, de la más reciente a la más antigua.
  final List<Creation> creations;
  final List<StoredProblem> problems;

  /// Ids recuperados desde la copia de seguridad en esta lectura.
  final List<String> recovered;
}

/// Almacén de las creaciones del niño.
abstract interface class CreationStore {
  /// Avisa cuando termina de guardar o borrar algo.
  Listenable get changes;

  Future<CreationReport> loadAll();
  Future<Creation?> load(String creationId);

  /// La creación más reciente de un dibujo (la que se continúa desde la galería).
  Future<Creation?> latestFor(String drawingId);

  Future<void> save(Creation creation);
  Future<void> delete(String creationId);

  /// Borra datos dañados. Solo lo hace un adulto, a propósito y con confirmación.
  Future<void> discardProblem(StoredProblem problem);

  String newCreationId(String drawingId);
}

/// Implementación sobre un [KeyValueBackend]:
///
/// * `creation.v2.<id>`: la creación (JSON con suma de verificación).
/// * `creation.v2.<id>.bak`: la última versión válida anterior.
///
/// Al guardar: (1) la versión válida actual pasa a la copia de seguridad y se
/// verifica, (2) se escribe la nueva, (3) se vuelve a leer y se verifica. Si
/// falla (1), la principal no se toca; si falla (2) o (3), la lectura usa la
/// copia de seguridad y repara la principal. Nunca quedan ambas dañadas por un
/// mismo guardado.
class KeyValueCreationStore implements CreationStore {
  KeyValueCreationStore(this.backend, {Random? random}) : _random = random ?? Random();

  static const prefix = 'creation.v${Creation.formatVersion}.';
  static const backupSuffix = '.bak';
  static const legacyPrefix = 'progress.v1.';

  final KeyValueBackend backend;
  final Random _random;
  final _changes = _Signal();
  Future<void>? _migration;

  @override
  Listenable get changes => _changes;

  static String keyFor(String creationId) => '$prefix$creationId';

  @override
  String newCreationId(String drawingId) {
    final stamp = DateTime.now().microsecondsSinceEpoch.toRadixString(36);
    final salt = _random.nextInt(1 << 30).toRadixString(36);
    final base = drawingId.toLowerCase().replaceAll(RegExp(r'[^a-z0-9_]'), '_');
    return '${base.length > 50 ? base.substring(0, 50) : base}-$stamp$salt';
  }

  Future<T> _guard<T>(String what, Future<T> Function() action) async {
    try {
      return await action();
    } on StorageException {
      rethrow;
    } catch (e) {
      throw StorageException('$what: $e');
    }
  }

  @override
  Future<void> save(Creation creation) async {
    await _ready();
    final key = keyFor(creation.id);
    final encoded = creation.encode();
    await _guard('guardar', () async {
      final current = await backend.read(key);
      if (current != null && current != encoded && _tryDecode(current) != null) {
        // La copia se comprueba ANTES de tocar la principal: si no quedó bien,
        // se aborta y la principal (válida) sigue intacta.
        await backend.write('$key$backupSuffix', current);
        if (await backend.read('$key$backupSuffix') != current) {
          throw StorageException('no se pudo escribir la copia de seguridad');
        }
      }
      await backend.write(key, encoded);
      final check = await backend.read(key);
      if (check != encoded) throw StorageException('la escritura no se completó');
    });
    _changes.fire();
  }

  @override
  Future<void> delete(String creationId) async {
    await _ready();
    final key = keyFor(creationId);
    await _guard('borrar', () async {
      await backend.remove(key);
      await backend.remove('$key$backupSuffix');
    });
    _changes.fire();
  }

  @override
  Future<Creation?> load(String creationId) async {
    await _ready();
    return (await _loadKey(keyFor(creationId))).creation;
  }

  @override
  Future<Creation?> latestFor(String drawingId) async {
    final report = await loadAll();
    for (final c in report.creations) {
      if (c.drawingId == drawingId) return c;
    }
    return null;
  }

  @override
  Future<CreationReport> loadAll() async {
    await _ready();
    final keys = await _guard('leer', backend.keys);
    final creations = <Creation>[];
    final problems = <StoredProblem>[];
    final recovered = <String>[];
    for (final key in keys) {
      if (key.startsWith(legacyPrefix)) {
        problems.add(
          StoredProblem(key: key, kind: StoredProblemKind.unmigrated, reason: 'formato antiguo no válido'),
        );
        continue;
      }
      if (!key.startsWith(prefix) || key.endsWith(backupSuffix)) continue;
      final result = await _loadKey(key);
      if (result.creation != null) {
        creations.add(result.creation!);
        if (result.recovered) recovered.add(result.creation!.id);
      } else {
        problems.add(
          StoredProblem(key: key, kind: StoredProblemKind.damaged, reason: result.reason ?? 'dañado'),
        );
      }
    }
    // Copias de seguridad sin principal (p. ej. se perdió la principal).
    for (final key in keys.where((k) => k.startsWith(prefix) && k.endsWith(backupSuffix))) {
      final main = key.substring(0, key.length - backupSuffix.length);
      if (keys.contains(main)) continue;
      final result = await _loadKey(main);
      if (result.creation != null) {
        creations.add(result.creation!);
        recovered.add(result.creation!.id);
      }
    }
    creations.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return CreationReport(creations: creations, problems: problems, recovered: recovered);
  }

  @override
  Future<void> discardProblem(StoredProblem problem) async {
    await _guard('borrar', () async {
      await backend.remove(problem.key);
      await backend.remove('${problem.key}$backupSuffix');
    });
    _changes.fire();
  }

  /// Lee la principal; si está dañada, la copia de seguridad (y repara la
  /// principal con ella). No borra nada.
  Future<({Creation? creation, bool recovered, String? reason})> _loadKey(String key) async {
    final raw = await _guard('leer', () => backend.read(key));
    String? reason;
    if (raw != null) {
      try {
        final c = Creation.decode(raw);
        if (keyFor(c.id) == key) return (creation: c, recovered: false, reason: null);
        reason = 'el id no coincide con la clave';
      } on FormatException catch (e) {
        reason = e.message;
      }
    } else {
      reason = 'no existe';
    }
    final backupRaw = await _guard('leer', () => backend.read('$key$backupSuffix'));
    final backup = backupRaw == null ? null : _tryDecode(backupRaw);
    if (backup != null && keyFor(backup.id) == key) {
      try {
        await backend.write(key, backupRaw!);
      } catch (_) {
        // Si no se puede reparar ahora, se intentará en la próxima lectura.
      }
      return (creation: backup, recovered: true, reason: null);
    }
    return (creation: null, recovered: false, reason: reason);
  }

  static Creation? _tryDecode(String raw) {
    try {
      return Creation.decode(raw);
    } on FormatException {
      return null;
    }
  }

  Future<void> _ready() => _migration ??= _migrateLegacy().catchError((Object _) {
    _migration = null; // Se reintentará en la próxima operación.
  });

  /// Migra el formato 1 (`progress.v1.<dibujo>`, un progreso por dibujo) a
  /// creaciones. La clave antigua solo se borra después de comprobar que la
  /// nueva se escribió bien; si no se puede leer, se conserva intacta.
  Future<void> _migrateLegacy() async {
    final keys = await backend.keys();
    for (final key in keys.where((k) => k.startsWith(legacyPrefix))) {
      final raw = await backend.read(key);
      final creation = raw == null ? null : _decodeLegacy(raw, key.substring(legacyPrefix.length));
      if (creation == null) continue;
      final newKey = keyFor(creation.id);
      final encoded = creation.encode();
      if (await backend.read(newKey) == null) await backend.write(newKey, encoded);
      final written = await backend.read(newKey);
      if (written != null && _tryDecode(written) != null) await backend.remove(key);
    }
  }

  static Creation? _decodeLegacy(String raw, String drawingId) {
    try {
      final json = jsonDecode(raw);
      if (json is! Map<String, dynamic> || json['format_version'] != 1 || json['drawing_id'] != drawingId) {
        return null;
      }
      final updated = _date(json['updated_at']);
      final regions = json['regions'];
      if (updated == null || regions is! Map<String, dynamic>) return null;
      final colors = <String, Color>{};
      for (final e in regions.entries) {
        final c = Creation.colorFromHex(e.value);
        if (c != null) colors[e.key] = c;
      }
      final id = '${drawingId.toLowerCase().replaceAll(RegExp(r'[^a-z0-9_]'), '_')}-v1';
      if (colors.isEmpty || !Creation.idPattern.hasMatch(id)) return null;
      return Creation(
        id: id,
        drawingId: drawingId,
        regionColors: colors,
        createdAt: updated,
        updatedAt: updated,
        totalRegions: 0, // Se completa al abrir el dibujo.
      );
    } catch (_) {
      return null;
    }
  }
}

class _Signal extends ChangeNotifier {
  void fire() => notifyListeners();
}

/// Almacén en memoria (pruebas).
class InMemoryCreationStore extends KeyValueCreationStore {
  InMemoryCreationStore([MemoryBackend? backend]) : super(backend ?? MemoryBackend());

  MemoryBackend get memory => backend as MemoryBackend;
}

/// Fecha guardada como texto ISO; cualquier otro tipo cuenta como ausente.
DateTime? _date(Object? value) => value is String ? DateTime.tryParse(value) : null;
