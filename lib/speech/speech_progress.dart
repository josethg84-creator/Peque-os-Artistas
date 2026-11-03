import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../persistence/creation.dart';
import '../persistence/key_value_backend.dart';
import 'speech_content.dart';

/// Lo que el niño ha hecho de verdad en «Aprendo a Hablar». No es una
/// evaluación del lenguaje: solo cuenta actividades realizadas.
class SpeechProgress {
  SpeechProgress({
    Set<String>? wordsHeard,
    Set<String>? phrasesHeard,
    Set<String>? phrasesOrdered,
    Set<String>? practiceDays,
  }) : wordsHeard = wordsHeard ?? {},
       phrasesHeard = phrasesHeard ?? {},
       phrasesOrdered = phrasesOrdered ?? {},
       practiceDays = practiceDays ?? {};

  static const formatVersion = 1;

  /// Palabras que ha escuchado al menos una vez (ids).
  final Set<String> wordsHeard;

  /// Frases que ha escuchado al menos una vez (ids).
  final Set<String> phrasesHeard;

  /// Frases que ha ordenado él mismo (ids).
  final Set<String> phrasesOrdered;

  /// Días en que practicó (AAAA-MM-DD, hora local).
  final Set<String> practiceDays;

  Map<String, dynamic> toJson() => {
    'format_version': formatVersion,
    'words_heard': wordsHeard.toList()..sort(),
    'phrases_heard': phrasesHeard.toList()..sort(),
    'phrases_ordered': phrasesOrdered.toList()..sort(),
    'practice_days': practiceDays.toList()..sort(),
  };

  static SpeechProgress fromJson(Map<String, dynamic> json) {
    Set<String> set(String key) => {...(json[key] as List? ?? const []).whereType<String>()};
    return SpeechProgress(
      wordsHeard: set('words_heard'),
      phrasesHeard: set('phrases_heard'),
      phrasesOrdered: set('phrases_ordered'),
      practiceDays: set('practice_days'),
    );
  }
}

/// Guarda el progreso en el almacenamiento local de la app (clave propia
/// `speech.v1.state`, con suma de verificación y copia de seguridad). Nada sale
/// del dispositivo.
class SpeechStore {
  SpeechStore(this.backend);

  static const key = 'speech.v1.state';
  static const backupKey = '$key.bak';

  final KeyValueBackend backend;

  static String encode(SpeechProgress progress) {
    final payload = progress.toJson();
    return jsonEncode({...payload, 'checksum': Creation.checksumOf(payload)});
  }

  static SpeechProgress? decode(String? raw) {
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw);
      if (json is! Map<String, dynamic> || json['format_version'] != SpeechProgress.formatVersion) {
        return null;
      }
      final payload = Map<String, dynamic>.of(json)..remove('checksum');
      if (json['checksum'] != Creation.checksumOf(payload)) return null;
      return SpeechProgress.fromJson(payload);
    } catch (_) {
      return null;
    }
  }

  /// El progreso guardado, la copia de seguridad si el principal está dañado,
  /// o uno vacío.
  Future<SpeechProgress> load() async =>
      decode(await backend.read(key)) ?? decode(await backend.read(backupKey)) ?? SpeechProgress();

  Future<void> save(SpeechProgress progress) async {
    final current = await backend.read(key);
    if (decode(current) != null) await backend.write(backupKey, current!);
    await backend.write(key, encode(progress));
  }
}

/// Contenido y progreso de «Aprendo a Hablar».
class SpeechController extends ChangeNotifier {
  SpeechController(this._store, {AssetBundle? bundle, DateTime Function()? clock})
    : _bundle = bundle ?? rootBundle,
      _clock = clock ?? DateTime.now;

  final SpeechStore _store;
  final AssetBundle _bundle;
  final DateTime Function() _clock;

  SpeechProgress _progress = SpeechProgress();
  SpeechProgress get progress => _progress;

  Future<SpeechContent>? _content;
  Future<void>? _loading;
  bool _saveFailed = false;
  bool get saveFailed => _saveFailed;

  /// El contenido (se lee una vez).
  Future<SpeechContent> content() => _content ??= SpeechContent.load(_bundle);

  Future<void> load() => _loading ??= () async {
    try {
      _progress = await _store.load();
    } catch (_) {
      // Sin almacenamiento se practica igual, con el progreso en memoria.
    }
    notifyListeners();
  }();

  void markWordHeard(String id) => _record(() => _progress.wordsHeard.add(id));
  void markPhraseHeard(String id) => _record(() => _progress.phrasesHeard.add(id));
  void markPhraseOrdered(String id) => _record(() => _progress.phrasesOrdered.add(id));

  static String _dayKey(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  void _record(bool Function() change) {
    final changed = change() | _progress.practiceDays.add(_dayKey(_clock()));
    if (!changed) return;
    notifyListeners();
    unawaited(_save());
  }

  Future<void>? _saving;
  bool _dirty = false;

  /// Guarda sin solapar escrituras: si llega otro cambio mientras se guarda,
  /// se vuelve a guardar al terminar.
  Future<void> _save() async {
    if (_saving != null) {
      _dirty = true;
      return _saving;
    }
    final completer = Completer<void>();
    _saving = completer.future;
    try {
      do {
        _dirty = false;
        try {
          await _store.save(_progress);
          _saveFailed = false;
        } catch (_) {
          _saveFailed = true;
        }
      } while (_dirty);
    } finally {
      _saving = null;
      completer.complete();
    }
  }

  /// Días distintos en que practicó en los últimos 7 días (hoy incluido).
  int daysPracticedThisWeek() {
    final today = _clock();
    var n = 0;
    for (var i = 0; i < 7; i++) {
      if (_progress.practiceDays.contains(_dayKey(today.subtract(Duration(days: i))))) n++;
    }
    return n;
  }
}
