import 'package:shared_preferences/shared_preferences.dart';

/// Almacenamiento clave-valor de texto. Separarlo permite usar el
/// almacenamiento real del dispositivo en la app y uno en memoria (con fallos
/// simulados) en las pruebas.
abstract interface class KeyValueBackend {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> remove(String key);
  Future<Set<String>> keys();
}

/// Almacenamiento privado de la app mediante `shared_preferences`
/// (`SharedPreferencesAsync`; en Android usa Jetpack DataStore). Funciona sin
/// conexión y no comparte datos con otras apps ni servidores.
class SharedPreferencesBackend implements KeyValueBackend {
  SharedPreferencesBackend([SharedPreferencesAsync? prefs]) : _prefs = prefs ?? SharedPreferencesAsync();

  final SharedPreferencesAsync _prefs;

  @override
  Future<String?> read(String key) => _prefs.getString(key);

  @override
  Future<void> write(String key, String value) => _prefs.setString(key, value);

  @override
  Future<void> remove(String key) => _prefs.remove(key);

  @override
  Future<Set<String>> keys() => _prefs.getKeys();
}

/// Almacenamiento en memoria para pruebas, con fallos configurables.
class MemoryBackend implements KeyValueBackend {
  final data = <String, String>{};

  /// Si es true, las lecturas o escrituras fallan como un disco con problemas.
  bool failReads = false;
  bool failWrites = false;

  /// Si se indica, las escrituras guardan solo esta cantidad de caracteres
  /// (simula una escritura interrumpida).
  int? truncateWritesTo;

  @override
  Future<String?> read(String key) async {
    if (failReads) throw StateError('lectura fallida');
    return data[key];
  }

  @override
  Future<void> write(String key, String value) async {
    if (failWrites) throw StateError('escritura fallida');
    final limit = truncateWritesTo;
    data[key] = limit == null || limit >= value.length ? value : value.substring(0, limit);
  }

  @override
  Future<void> remove(String key) async {
    if (failWrites) throw StateError('escritura fallida');
    data.remove(key);
  }

  @override
  Future<Set<String>> keys() async {
    if (failReads) throw StateError('lectura fallida');
    return data.keys.toSet();
  }
}
