import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../persistence/key_value_backend.dart';
import 'aac_catalog.dart';

/// Tamaño de las tarjetas del tablero.
enum AacTileSize {
  small('Pequeño', 120),
  medium('Mediano', 160),
  large('Grande', 210);

  const AacTileSize(this.label, this.minWidth);
  final String label;

  /// Ancho mínimo de cada tarjeta (lógico).
  final double minWidth;
}

/// Orden de las tarjetas.
enum AacOrder {
  catalog('Como en el catálogo'),
  alphabetical('Alfabético'),
  frequent('Las más usadas primero');

  const AacOrder(this.label);
  final String label;
}

/// Ajustes de «Quiero decir». Solo los cambia un adulto, desde la zona de
/// adultos; el tablero del niño siempre se puede abrir sin verificación.
class AacPreferences {
  AacPreferences({
    this.tileSize = AacTileSize.medium,
    this.columns = 0,
    this.order = AacOrder.catalog,
    List<String>? favorites,
    Set<String>? frequentCategories,
    this.slowVoice = false,
    this.highContrast = false,
    this.textScale = 1.0,
    this.speakOnTap = true,
    this.confirmBeforeSpeak = false,
    this.tapGuardMs = 0,
    this.feminine = false,
    List<String>? quickExtras,
    Map<String, int>? usage,
  }) : favorites = favorites ?? [],
       frequentCategories = frequentCategories ?? {},
       quickExtras = quickExtras ?? [],
       usage = usage ?? {};

  static const columnOptions = [0, 2, 3, 4, 5];
  static const textScales = [1.0, 1.25, 1.5];
  static const tapGuards = [0, 500, 1000];

  AacTileSize tileSize;

  /// Columnas fijas (0: automáticas según la pantalla).
  int columns;
  AacOrder order;

  /// Frases favoritas guardadas (el texto, tal como se dice).
  final List<String> favorites;

  /// Categorías que aparecen primero.
  final Set<String> frequentCategories;

  /// Voz más lenta.
  bool slowVoice;

  /// Bordes y textos negros sobre blanco.
  bool highContrast;

  /// Tamaño del texto de las tarjetas (1, 1,25 o 1,5).
  double textScale;

  /// Decir la frase al tocar la tarjeta.
  bool speakOnTap;

  /// Pedir confirmación («Decirlo») antes de hablar.
  bool confirmBeforeSpeak;

  /// Ignora un segundo toque más rápido que esto (pulsaciones involuntarias).
  int tapGuardMs;

  /// Frases en femenino («Estoy cansada»).
  bool feminine;

  /// Pictogramas que el adulto añade al tablero rápido (las palabras
  /// esenciales siempre están).
  final List<String> quickExtras;

  /// Veces que se ha usado cada pictograma (solo para ordenar por uso; no se
  /// envía a ningún sitio).
  final Map<String, int> usage;

  Map<String, dynamic> toJson() => {
    'tile_size': tileSize.name,
    'columns': columns,
    'order': order.name,
    'favorites': favorites,
    'frequent_categories': frequentCategories.toList()..sort(),
    'slow_voice': slowVoice,
    'high_contrast': highContrast,
    'text_scale': textScale,
    'speak_on_tap': speakOnTap,
    'confirm_before_speak': confirmBeforeSpeak,
    'tap_guard_ms': tapGuardMs,
    'feminine': feminine,
    'quick_extras': quickExtras,
    'usage': Map.fromEntries(usage.entries.toList()..sort((a, b) => a.key.compareTo(b.key))),
  };

  static AacPreferences fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return AacPreferences();
    T pick<T>(List<T> values, Object? v, T fallback) => values.contains(v) ? v as T : fallback;
    final scale = (json['text_scale'] as num?)?.toDouble();
    return AacPreferences(
      tileSize: AacTileSize.values.firstWhere(
        (t) => t.name == json['tile_size'],
        orElse: () => AacTileSize.medium,
      ),
      columns: pick(columnOptions, json['columns'], 0),
      order: AacOrder.values.firstWhere((o) => o.name == json['order'], orElse: () => AacOrder.catalog),
      favorites: [...(json['favorites'] as List? ?? const []).whereType<String>()],
      frequentCategories: {...(json['frequent_categories'] as List? ?? const []).whereType<String>()},
      slowVoice: json['slow_voice'] == true,
      highContrast: json['high_contrast'] == true,
      textScale: textScales.contains(scale) ? scale! : 1.0,
      speakOnTap: json['speak_on_tap'] != false,
      confirmBeforeSpeak: json['confirm_before_speak'] == true,
      tapGuardMs: pick(tapGuards, json['tap_guard_ms'], 0),
      feminine: json['feminine'] == true,
      quickExtras: [...(json['quick_extras'] as List? ?? const []).whereType<String>()],
      usage: {
        if (json['usage'] case final Map<String, dynamic> m)
          for (final MapEntry(:key, :value) in m.entries)
            if (value is int) key: value,
      },
    );
  }
}

/// Guarda los ajustes en el almacenamiento local (clave propia, con copia de
/// seguridad). Nada sale del dispositivo.
class AacStore {
  AacStore(this.backend);

  static const key = 'aac.v1.state';
  static const backupKey = '$key.bak';

  final KeyValueBackend backend;

  static AacPreferences? decode(String? raw) {
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw);
      return json is Map<String, dynamic> && json['format_version'] == 1
          ? AacPreferences.fromJson(json)
          : null;
    } catch (_) {
      return null;
    }
  }

  Future<AacPreferences> load() async =>
      decode(await backend.read(key)) ?? decode(await backend.read(backupKey)) ?? AacPreferences();

  Future<void> save(AacPreferences p) async {
    final current = await backend.read(key);
    if (decode(current) != null) await backend.write(backupKey, current!);
    await backend.write(key, jsonEncode({'format_version': 1, ...p.toJson()}));
  }

  Future<void> clear() async {
    await backend.remove(key);
    await backend.remove(backupKey);
  }
}

/// «Quiero decir»: catálogo, ajustes, favoritos y el mensaje en pantalla.
/// Va aparte del progreso y de las estrellas: comunicarse nunca depende de
/// haber jugado ni da puntos.
class AacController extends ChangeNotifier {
  AacController(this._store, {AssetBundle? bundle, DateTime Function()? clock})
    : _bundle = bundle ?? rootBundle,
      _clock = clock ?? DateTime.now;

  final AacStore _store;
  final AssetBundle _bundle;
  final DateTime Function() _clock;

  AacPreferences _prefs = AacPreferences();
  AacPreferences get prefs => _prefs;

  Future<AacCatalog>? _catalog;
  Future<AacCatalog> catalog() => _catalog ??= AacCatalog.load(_bundle);

  /// Lo último que se dijo o se va a decir (se muestra en grande).
  final message = ValueNotifier<String?>(null);

  /// Con «confirmar antes de hablar»: la frase elegida espera a «Decirlo».
  final pending = ValueNotifier<String?>(null);

  Future<void>? _loading;
  Future<void> load() => _loading ??= () async {
    try {
      _prefs = await _store.load();
    } catch (_) {
      // Sin almacenamiento el tablero funciona igual.
    }
    notifyListeners();
  }();

  void update(void Function(AacPreferences p) change) {
    change(_prefs);
    notifyListeners();
    unawaited(_save());
  }

  DateTime? _lastTap;

  /// `false` si el toque llega demasiado pronto tras el anterior (ajuste
  /// contra pulsaciones involuntarias).
  bool acceptTap() {
    final now = _clock();
    final guard = Duration(milliseconds: _prefs.tapGuardMs);
    if (guard > Duration.zero && _lastTap != null && now.difference(_lastTap!) < guard) return false;
    _lastTap = now;
    return true;
  }

  void markUsed(String id) => update((p) => p.usage[id] = (p.usage[id] ?? 0) + 1);

  bool isFavorite(String phrase) => _prefs.favorites.contains(phrase);
  void addFavorite(String phrase) => update((p) {
    if (!p.favorites.contains(phrase)) p.favorites.insert(0, phrase);
  });
  void removeFavorite(String phrase) => update((p) => p.favorites.remove(phrase));

  /// Ordena tarjetas según el ajuste.
  List<Pictogram> sorted(List<Pictogram> list) {
    final out = [...list];
    switch (_prefs.order) {
      case AacOrder.catalog:
        break;
      case AacOrder.alphabetical:
        out.sort((a, b) => a.label().toLowerCase().compareTo(b.label().toLowerCase()));
      case AacOrder.frequent:
        out.sort((a, b) => (_prefs.usage[b.id] ?? 0).compareTo(_prefs.usage[a.id] ?? 0));
    }
    return out;
  }

  /// Borra toda la personalización (zona de adultos).
  Future<void> clearAll() async {
    _prefs = AacPreferences();
    message.value = null;
    pending.value = null;
    notifyListeners();
    // Espera a que termine un guardado en curso para que no lo vuelva a escribir.
    while (_saving != null) {
      await _saving;
    }
    try {
      await _store.clear();
    } catch (_) {}
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
          await _store.save(_prefs);
        } catch (_) {}
      } while (_dirty);
    } finally {
      _saving = null;
      done.complete();
    }
  }

  @override
  void dispose() {
    message.dispose();
    pending.dispose();
    super.dispose();
  }
}
