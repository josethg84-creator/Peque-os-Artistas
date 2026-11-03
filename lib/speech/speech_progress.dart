import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../persistence/creation.dart';
import '../persistence/key_value_backend.dart';
import 'mission.dart';
import 'speech_content.dart';
import 'speech_preferences.dart';

export 'speech_preferences.dart';
import 'voice_practice.dart';

/// Lo que el niño ha hecho de verdad en «Aprendo a Hablar». No es una
/// evaluación del lenguaje: solo cuenta actividades realizadas.
class SpeechProgress {
  SpeechProgress({
    Set<String>? wordsHeard,
    Set<String>? phrasesHeard,
    Set<String>? phrasesOrdered,
    Set<String>? practiceDays,
    Set<String>? verbsHeard,
    Set<String>? sentencesBuilt,
    Set<String>? sentencesOrdered,
    Map<String, int>? activitiesDone,
    this.recordings = 0,
    this.micAllowed = true,
    Set<String>? conversationsDone,
    Set<String>? storiesHeard,
    Set<String>? storiesQuizzed,
    Set<String>? storiesTold,
    Set<String>? expressionsPracticed,
    Set<String>? listeningDone,
    this.answers = 0,
    this.stars = 0,
    SpeechPreferences? preferences,
    Map<String, int>? visits,
    Map<String, int>? repeats,
    this.today,
    Set<String>? storiesBuilt,
    Set<String>? syllablesDone,
  }) : preferences = preferences ?? SpeechPreferences(),
       visits = visits ?? {},
       repeats = repeats ?? {},
       storiesBuilt = storiesBuilt ?? {},
       syllablesDone = syllablesDone ?? {},
       conversationsDone = conversationsDone ?? {},
       storiesHeard = storiesHeard ?? {},
       storiesQuizzed = storiesQuizzed ?? {},
       storiesTold = storiesTold ?? {},
       expressionsPracticed = expressionsPracticed ?? {},
       listeningDone = listeningDone ?? {},
       wordsHeard = wordsHeard ?? {},
       phrasesHeard = phrasesHeard ?? {},
       phrasesOrdered = phrasesOrdered ?? {},
       practiceDays = practiceDays ?? {},
       verbsHeard = verbsHeard ?? {},
       sentencesBuilt = sentencesBuilt ?? {},
       sentencesOrdered = sentencesOrdered ?? {},
       activitiesDone = activitiesDone ?? {};

  static const formatVersion = 1;

  /// Palabras que ha escuchado al menos una vez (ids).
  final Set<String> wordsHeard;

  /// Frases que ha escuchado al menos una vez (ids).
  final Set<String> phrasesHeard;

  /// Frases que ha ordenado él mismo (ids).
  final Set<String> phrasesOrdered;

  /// Días en que practicó (AAAA-MM-DD, hora local).
  final Set<String> practiceDays;

  /// Verbos cuya conjugación ha escuchado (ids).
  final Set<String> verbsHeard;

  /// Oraciones distintas que ha construido él mismo (el texto).
  final Set<String> sentencesBuilt;

  /// Oraciones de «Ordena la oración» que ha ordenado (el texto).
  final Set<String> sentencesOrdered;

  /// Veces que ha terminado cada actividad (ordenar, completar, verbos…).
  final Map<String, int> activitiesDone;

  /// Veces que ha practicado con su voz. Solo el número: las grabaciones no
  /// se guardan.
  int recordings;

  /// Un adulto puede desactivar la práctica con el micrófono.
  bool micAllowed;

  /// Fase 3: conversaciones terminadas con Lolo (ids).
  final Set<String> conversationsDone;

  /// Cuentos escuchados hasta el final (ids).
  final Set<String> storiesHeard;

  /// Cuentos cuyas preguntas de comprensión ha respondido (ids).
  final Set<String> storiesQuizzed;

  /// Historias de «Ahora cuéntamelo tú» que ha construido (ids).
  final Set<String> storiesTold;

  /// Necesidades y emociones que ha escuchado o construido (ids).
  final Set<String> expressionsPracticed;

  /// Ejercicios de «Escucho y respondo» resueltos (ids).
  final Set<String> listeningDone;

  /// Preguntas de comprensión respondidas (cuentos y ejercicios).
  int answers;

  /// Estrellas ganadas en «Aprendo a Hablar».
  int stars;

  /// Fase 4: ajustes del adulto.
  final SpeechPreferences preferences;

  /// Veces que ha abierto cada actividad (por ruta): sus favoritas.
  final Map<String, int> visits;

  /// Veces que ha pedido repetir en cada actividad (por ruta). Pedir repetir
  /// es bueno: sirve para ofrecer más práctica, nunca para penalizar.
  final Map<String, int> repeats;

  /// Lo hecho hoy («Mi aventura de hoy»).
  DailyRecord? today;

  /// Historias creadas en «Mi historia» (el texto).
  final Set<String> storiesBuilt;

  /// Palabras de «Palmas y sílabas» resueltas (ids).
  final Set<String> syllablesDone;

  Map<String, dynamic> toJson() => {
    'format_version': formatVersion,
    'words_heard': wordsHeard.toList()..sort(),
    'phrases_heard': phrasesHeard.toList()..sort(),
    'phrases_ordered': phrasesOrdered.toList()..sort(),
    'practice_days': practiceDays.toList()..sort(),
    'verbs_heard': verbsHeard.toList()..sort(),
    'sentences_built': sentencesBuilt.toList()..sort(),
    'sentences_ordered': sentencesOrdered.toList()..sort(),
    'activities_done': Map.fromEntries(
      activitiesDone.entries.toList()..sort((a, b) => a.key.compareTo(b.key)),
    ),
    'recordings': recordings,
    'mic_allowed': micAllowed,
    'conversations_done': conversationsDone.toList()..sort(),
    'stories_heard': storiesHeard.toList()..sort(),
    'stories_quizzed': storiesQuizzed.toList()..sort(),
    'stories_told': storiesTold.toList()..sort(),
    'expressions_practiced': expressionsPracticed.toList()..sort(),
    'listening_done': listeningDone.toList()..sort(),
    'answers': answers,
    'stars': stars,
    'preferences': preferences.toJson(),
    'visits': _sorted(visits),
    'repeats': _sorted(repeats),
    'today': today?.toJson(),
    'stories_built': storiesBuilt.toList()..sort(),
    'syllables_done': syllablesDone.toList()..sort(),
  };

  static Map<String, int> _sorted(Map<String, int> m) =>
      Map.fromEntries(m.entries.toList()..sort((a, b) => a.key.compareTo(b.key)));

  static Map<String, int> _counts(Object? json) => {
    if (json case final Map<String, dynamic> m)
      for (final MapEntry(:key, :value) in m.entries)
        if (value is int) key: value,
  };

  static SpeechProgress fromJson(Map<String, dynamic> json) {
    Set<String> set(String key) => {...(json[key] as List? ?? const []).whereType<String>()};
    return SpeechProgress(
      wordsHeard: set('words_heard'),
      phrasesHeard: set('phrases_heard'),
      phrasesOrdered: set('phrases_ordered'),
      practiceDays: set('practice_days'),
      verbsHeard: set('verbs_heard'),
      sentencesBuilt: set('sentences_built'),
      sentencesOrdered: set('sentences_ordered'),
      activitiesDone: {
        if (json['activities_done'] case final Map<String, dynamic> m)
          for (final MapEntry(:key, :value) in m.entries)
            if (value is int) key: value,
      },
      recordings: json['recordings'] is int ? json['recordings'] as int : 0,
      micAllowed: json['mic_allowed'] is bool ? json['mic_allowed'] as bool : true,
      conversationsDone: set('conversations_done'),
      storiesHeard: set('stories_heard'),
      storiesQuizzed: set('stories_quizzed'),
      storiesTold: set('stories_told'),
      expressionsPracticed: set('expressions_practiced'),
      listeningDone: set('listening_done'),
      answers: json['answers'] is int ? json['answers'] as int : 0,
      stars: json['stars'] is int ? json['stars'] as int : 0,
      preferences: SpeechPreferences.fromJson(json['preferences']),
      visits: _counts(json['visits']),
      repeats: _counts(json['repeats']),
      today: DailyRecord.fromJson(json['today']),
      storiesBuilt: set('stories_built'),
      syllablesDone: set('syllables_done'),
    );
  }
}

/// Claves de lo hecho hoy.
abstract final class Daily {
  static const words = 'palabras';
  static const sentences = 'oraciones';
  static const verbs = 'verbos';
  static const stories = 'cuentos';
  static const conversations = 'conversaciones';
  static const sounds = 'sonidos';
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
  SpeechController(
    this._store, {
    AssetBundle? bundle,
    DateTime Function()? clock,
    VoiceRecorder Function()? recorder,
  }) : _bundle = bundle ?? rootBundle,
       _clock = clock ?? DateTime.now,
       newRecorder = recorder ?? DeviceVoiceRecorder.new;

  /// Crea la grabadora de «Practicar» (una por ventana, que se libera al cerrarla).
  final VoiceRecorder Function() newRecorder;

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

  void markWordHeard(String id) => _record(() => _progress.wordsHeard.add(id) | _bump(Daily.words));
  void markVerbHeard(String id) => _record(() => _progress.verbsHeard.add(id) | _bump(Daily.verbs));
  void markSentenceBuilt(String text) =>
      _record(() => _progress.sentencesBuilt.add(text) | _bump(Daily.sentences));
  void markSentenceOrdered(String text) => _record(() => _progress.sentencesOrdered.add(text));
  void markActivityDone(String kind) => _record(() {
    _progress.activitiesDone[kind] = (_progress.activitiesDone[kind] ?? 0) + 1;
    return true;
  });
  void markRecording() => _record(() {
    _progress.recordings++;
    return true;
  });

  /// Fase 3. Cada actividad terminada da estrellas (solo la primera vez que
  /// se termina cada conversación, cuento o historia, para no inflarlas).
  void markConversationDone(String id) => _record(() {
    _bump(Daily.conversations);
    if (!_progress.conversationsDone.add(id)) return true;
    _progress.stars += 1;
    return true;
  });
  void markStoryHeard(String id) => _record(() {
    _bump(Daily.stories);
    if (!_progress.storiesHeard.add(id)) return true;
    _progress.stars += 1;
    return true;
  });
  void markStoryQuizzed(String id) => _record(() {
    if (!_progress.storiesQuizzed.add(id)) return true;
    _progress.stars += 2;
    return true;
  });
  void markStoryTold(String id) => _record(() {
    _bump(Daily.stories);
    if (!_progress.storiesTold.add(id)) return true;
    _progress.stars += 2;
    return true;
  });
  void markExpressionPracticed(String id) => _record(() => _progress.expressionsPracticed.add(id));

  /// Un ejercicio de «Escucho y respondo» resuelto (sin estrella: la estrella
  /// llega al terminar el nivel).
  void markListeningDone(String id) => _record(() => _progress.listeningDone.add(id));

  /// Un nivel de «Escucho y respondo» terminado: una estrella la primera vez.
  void markListeningLevel(int level) => _record(() {
    final key = 'escucho_nivel_$level';
    final first = !_progress.activitiesDone.containsKey(key);
    _progress.activitiesDone[key] = (_progress.activitiesDone[key] ?? 0) + 1;
    if (first) _progress.stars += 1;
    return true;
  });
  void markAnswer() => _record(() {
    _progress.answers++;
    return true;
  });

  /// Fase 4. Una historia creada en «Mi historia»: cuenta como historia y
  /// como oración del día; una estrella la primera vez que se crea cada una.
  void markStoryBuilt(String text) => _record(() {
    _bump(Daily.stories);
    _bump(Daily.sentences);
    if (_progress.storiesBuilt.add(text)) _progress.stars += 1;
    return true;
  });

  /// Una palabra de «Palmas y sílabas» resuelta.
  void markSyllables(String id) => _record(() => _progress.syllablesDone.add(id) | _bump(Daily.sounds));

  /// Una ronda de un juego de sonidos (empieza, rimas, encuentro).
  void markSoundGame() => _record(() => _bump(Daily.sounds));

  /// Se abrió una actividad (para conocer sus favoritas).
  void markVisit(String route) => _record(() {
    _progress.visits[route] = (_progress.visits[route] ?? 0) + 1;
    return true;
  });

  /// Pidió repetir (escuchar otra vez) en una actividad.
  void markRepeat(String route) => _record(() {
    _progress.repeats[route] = (_progress.repeats[route] ?? 0) + 1;
    return true;
  });

  /// Lo hecho hoy (vacío si aún no ha hecho nada hoy).
  DailyRecord get today {
    final day = _dayKey(_clock());
    final t = _progress.today;
    return t != null && t.day == day ? t : DailyRecord(day: day);
  }

  DailyRecord _todayForWrite() {
    final t = today;
    _progress.today = t;
    return t;
  }

  /// La primera vez que se completa la aventura de hoy, se anota (para las
  /// medallas). No hay rachas: los días sin aventura no cuentan en contra.
  bool _adventureDone() {
    final t = _progress.today;
    if (t == null || t.day != _dayKey(_clock()) || t.counts.containsKey(_adventureKey)) return false;
    if (!DailyMission.complete(t)) return false;
    t.counts[_adventureKey] = 1;
    _progress.activitiesDone['aventura'] = (_progress.activitiesDone['aventura'] ?? 0) + 1;
    _progress.stars += 1;
    return true;
  }

  static const _adventureKey = '_aventura';

  bool _bump(String key) {
    final t = _todayForWrite();
    t.counts[key] = t.count(key) + 1;
    return true;
  }

  /// Saltar una misión de hoy (o volver a ponerla). Saltar no tiene castigo.
  void setMissionSkipped(String id, bool skipped) => _record(() {
    final t = _todayForWrite();
    return skipped ? t.skipped.add(id) : t.skipped.remove(id);
  });

  /// Cambia los ajustes del adulto.
  void updatePreferences(void Function(SpeechPreferences p) change) {
    change(_progress.preferences);
    notifyListeners();
    unawaited(_save());
  }

  /// Desde cuándo se usa el módulo en esta sesión (para sugerir un descanso).
  DateTime? _sessionStart;
  Duration get sessionTime => _sessionStart == null ? Duration.zero : _clock().difference(_sessionStart!);

  /// Lo llama el menú de «Aprendo a Hablar» al abrirse.
  void startSession() => _sessionStart ??= _clock();

  /// Activa o desactiva la práctica con el micrófono (zona de adultos).
  void setMicAllowed(bool allowed) {
    if (_progress.micAllowed == allowed) return;
    _progress.micAllowed = allowed;
    notifyListeners();
    unawaited(_save());
  }

  void markPhraseHeard(String id) => _record(() => _progress.phrasesHeard.add(id));
  void markPhraseOrdered(String id) => _record(() => _progress.phrasesOrdered.add(id));

  static String _dayKey(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  void _record(bool Function() change) {
    final changed = change() | _progress.practiceDays.add(_dayKey(_clock())) | _adventureDone();
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
