import 'dart:convert';

import '../persistence/creation.dart';
import '../persistence/creation_store.dart' show StorageException;
import '../persistence/key_value_backend.dart';
import 'learning_progress.dart';

/// Resultado de leer el progreso de «Aprender jugando».
class LearningLoad {
  const LearningLoad(this.progress, {this.recovered = false, this.damaged = false});
  final LearningProgress progress;

  /// Se usó la copia de seguridad.
  final bool recovered;

  /// No se pudo leer nada válido: se empieza de cero, pero los datos dañados se
  /// conservan aparte (no se borran).
  final bool damaged;
}

/// Guarda el progreso, las preferencias y los premios en el mismo
/// almacenamiento local que las creaciones de la Fase 5, con claves propias
/// (`learning.v1.*`) que no interfieren con `creation.v2.*`.
///
/// Misma protección que las creaciones: suma de verificación, copia de
/// seguridad comprobada antes de sobrescribir y verificación tras escribir.
class LearningStore {
  LearningStore(this.backend);

  static const key = 'learning.v1.state';
  static const backupKey = '$key.bak';
  static const damagedKey = '$key.damaged';

  final KeyValueBackend backend;

  static String encode(LearningProgress progress) {
    final payload = progress.toJson();
    return jsonEncode({...payload, 'checksum': Creation.checksumOf(payload)});
  }

  static LearningProgress? decode(String? raw) {
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw);
      if (json is! Map<String, dynamic> || json['format_version'] != LearningProgress.formatVersion) {
        return null;
      }
      final checksum = json['checksum'];
      final payload = Map<String, dynamic>.of(json)..remove('checksum');
      if (checksum != Creation.checksumOf(payload)) return null;
      return LearningProgress.fromJson(payload);
    } catch (_) {
      return null;
    }
  }

  Future<LearningLoad> load() async {
    try {
      final raw = await backend.read(key);
      if (raw == null && await backend.read(backupKey) == null) return LearningLoad(LearningProgress());
      final main = decode(raw);
      if (main != null) return LearningLoad(main);
      final backupRaw = await backend.read(backupKey);
      final backup = decode(backupRaw);
      if (backup != null) {
        await backend.write(key, backupRaw!);
        return LearningLoad(backup, recovered: true);
      }
      // Nada válido: se conserva una copia de lo dañado y se empieza de cero.
      if (raw != null) await backend.write(damagedKey, raw);
      return LearningLoad(LearningProgress(), damaged: true);
    } catch (e) {
      throw StorageException('leer progreso: $e');
    }
  }

  Future<void> save(LearningProgress progress) async {
    final encoded = encode(progress);
    try {
      final current = await backend.read(key);
      if (current != null && current != encoded && decode(current) != null) {
        await backend.write(backupKey, current);
        if (await backend.read(backupKey) != current) throw StorageException('copia de seguridad incompleta');
      }
      await backend.write(key, encoded);
      if (await backend.read(key) != encoded) throw StorageException('escritura incompleta');
    } on StorageException {
      rethrow;
    } catch (e) {
      throw StorageException('guardar progreso: $e');
    }
  }
}
