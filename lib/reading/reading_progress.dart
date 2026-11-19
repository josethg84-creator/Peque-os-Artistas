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
    Set<String>? sentencesHeard,
    Set<String>? sentencesReadAlone,
    Set<String>? wordsPlayed,
    Set<String>? questionsAnswered,
    Set<String>? questionsCorrect,
    this.sentenceAttempts = 0,
    this.sentenceLevel = 1,
    Map<String, DictationRecord>? dictations,
  }) : dictations = dictations ?? {},
       completed = completed ?? {},
       firstTry = firstTry ?? {},
       withHints = withHints ?? {},
       sentencesHeard = sentencesHeard ?? {},
       sentencesReadAlone = sentencesReadAlone ?? {},
       wordsPlayed = wordsPlayed ?? {},
       questionsAnswered = questionsAnswered ?? {},
       questionsCorrect = questionsCorrect ?? {};

  /// Ejercicio → modos en que se completó («elige», «arrastra», «ordena»).
  final Map<String, Set<String>> completed;

  /// «modo:ejercicio» acertados a la primera.
  final Set<String> firstTry;

  /// «modo:ejercicio» completados usando alguna pista.
  final Set<String> withHints;

  /// Respuestas correctas e intentos (cada «Comprobar»).
  int correctAnswers;
  int attempts;

  // ------------------------------------------------ oraciones (Fase 5)

  /// Oraciones escuchadas enteras con «Escuchar».
  final Set<String> sentencesHeard;

  /// Oraciones LEÍDAS sin ayuda: se respondió bien su pregunta sin haber
  /// escuchado antes la oración. Escuchar no cuenta como leer.
  final Set<String> sentencesReadAlone;

  /// Palabras distintas que se han tocado para oírlas.
  final Set<String> wordsPlayed;

  /// Preguntas de comprensión respondidas y acertadas (por oración).
  final Set<String> questionsAnswered;
  final Set<String> questionsCorrect;

  /// Intentos en las actividades de oraciones (cada respuesta o «Comprobar»).
  int sentenceAttempts;

  /// Nivel de oraciones más alto abierto.
  int sentenceLevel;

  // ------------------------------------------------ dictados (Fase 6)

  /// Dictado → cómo fue (el último resultado y lo acumulado).
  final Map<String, DictationRecord> dictations;

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
    'sentences_heard': sentencesHeard.toList()..sort(),
    'sentences_read_alone': sentencesReadAlone.toList()..sort(),
    'words_played': wordsPlayed.toList()..sort(),
    'questions_answered': questionsAnswered.toList()..sort(),
    'questions_correct': questionsCorrect.toList()..sort(),
    'sentence_attempts': sentenceAttempts,
    'sentence_level': sentenceLevel,
    'dictations': {
      for (final e in (dictations.entries.toList()..sort((a, b) => a.key.compareTo(b.key))))
        e.key: e.value.toJson(),
    },
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
      // Campos de la Fase 5: si faltan (progreso guardado antes), empiezan vacíos.
      sentencesHeard: strings(json['sentences_heard']),
      sentencesReadAlone: strings(json['sentences_read_alone']),
      wordsPlayed: strings(json['words_played']),
      questionsAnswered: strings(json['questions_answered']),
      questionsCorrect: strings(json['questions_correct']),
      sentenceAttempts: count(json['sentence_attempts']),
      sentenceLevel: switch (json['sentence_level']) {
        final int l when l >= 1 && l <= 4 => l,
        _ => 1,
      },
      dictations: {
        if (json['dictations'] case final Map<String, dynamic> m)
          for (final e in m.entries) e.key: ?DictationRecord.fromJson(e.value),
      },
    );
  }
}

/// Cómo le fue a un dictado. Un acierto con pistas NO cuenta como acierto
/// sin ayuda ([independent]).
class DictationRecord {
  DictationRecord({
    required this.type,
    required this.level,
    required this.mode,
    this.attempts = 0,
    this.correct = false,
    this.independent = false,
    this.hints = 0,
    this.date = '',
    Map<String, int>? errors,
  }) : errors = errors ?? {};

  /// «silaba», «palabra» u «oracion».
  final String type;
  final int level;

  /// Último modo usado («tarjetas», «teclado», «ordenar»).
  String mode;

  /// Comprobaciones hechas en total.
  int attempts;

  /// Se acertó alguna vez.
  bool correct;

  /// Se acertó alguna vez sin pistas.
  bool independent;

  /// Máximo de pistas usadas en un mismo intento (0 a 4).
  int hints;

  /// Última vez (AAAA-MM-DD).
  String date;

  /// Errores por tipo («accent», «letter»…).
  final Map<String, int> errors;

  Map<String, dynamic> toJson() => {
    'type': type,
    'level': level,
    'mode': mode,
    'attempts': attempts,
    'correct': correct,
    'independent': independent,
    'hints': hints,
    'date': date,
    'errors': {for (final k in (errors.keys.toList()..sort())) k: errors[k]},
  };

  static DictationRecord? fromJson(Object? json) {
    if (json is! Map<String, dynamic> || json['type'] is! String) return null;
    int n(Object? v) => v is int && v >= 0 ? v : 0;
    return DictationRecord(
      type: json['type'] as String,
      level: n(json['level']),
      mode: json['mode'] is String ? json['mode'] as String : '',
      attempts: n(json['attempts']),
      correct: json['correct'] == true,
      independent: json['independent'] == true,
      hints: n(json['hints']),
      date: json['date'] is String ? json['date'] as String : '',
      errors: {
        if (json['errors'] case final Map<String, dynamic> m)
          for (final e in m.entries)
            if (e.value is int) e.key: e.value as int,
      },
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
  ReadingController(this._store, {DateTime Function()? clock}) : _clock = clock ?? DateTime.now;

  final ReadingStore _store;
  final DateTime Function() _clock;
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

  // ------------------------------------------------ oraciones (Fase 5)

  /// Una oración escuchada entera.
  void recordSentenceHeard(String sentenceId) {
    if (_progress.sentencesHeard.add(sentenceId)) _changed();
  }

  /// Una palabra tocada para oírla.
  void recordWordPlayed(String word) {
    if (_progress.wordsPlayed.add(word.toLowerCase())) _changed();
  }

  /// Un intento en una actividad de oraciones.
  void recordSentenceAttempt() {
    _progress.sentenceAttempts++;
    _changed();
  }

  /// Se respondió (bien o no) la pregunta de una oración.
  void recordQuestionAnswered(String sentenceId) {
    if (_progress.questionsAnswered.add(sentenceId)) _changed();
  }

  /// La pregunta de una oración se respondió bien. Si la oración no se había
  /// escuchado antes ([listenedFirst] falso), cuenta como leída sin ayuda.
  void recordQuestionSolved(
    String sentenceId, {
    required bool firstTry,
    required bool usedHints,
    required bool listenedFirst,
  }) {
    _progress.questionsAnswered.add(sentenceId);
    _progress.questionsCorrect.add(sentenceId);
    if (!listenedFirst) _progress.sentencesReadAlone.add(sentenceId);
    recordCompleted(sentenceId, sentenceQuestionMode, firstTry: firstTry, usedHints: usedHints);
  }

  /// Modos de las actividades de oraciones (para [completed]).
  static const sentenceQuestionMode = 'comprende';
  static const sentenceOrderMode = 'ordena_oracion';
  static const sentenceListenMode = 'escucha';

  /// Oraciones de un nivel con la pregunta resuelta.
  int sentencesDone(Iterable<String> sentenceIds) => completedIn(sentenceIds, sentenceQuestionMode);

  /// Un nivel de oraciones está abierto: el 1 siempre; los demás, al resolver
  /// [unlockAfter] preguntas del anterior.
  bool sentenceLevelOpen(int level, Iterable<String> Function(int level) idsOf) {
    if (level <= 1) return true;
    final open = sentencesDone(idsOf(level - 1)) >= unlockAfter && sentenceLevelOpen(level - 1, idsOf);
    if (open && level > _progress.sentenceLevel) {
      _progress.sentenceLevel = level;
      unawaited(_save());
    }
    return open;
  }

  // ------------------------------------------------ dictados (Fase 6)

  /// Una comprobación de un dictado (acertada o no).
  void recordDictation(
    String id, {
    required String type,
    required int level,
    required String mode,
    required bool correct,
    required int hints,
    String? error,
  }) {
    final r = _progress.dictations[id] ??= DictationRecord(type: type, level: level, mode: mode);
    final now = _clock();
    r
      ..mode = mode
      ..attempts += 1
      ..hints = hints > r.hints ? hints : r.hints
      ..date =
          '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
    if (correct) {
      r.correct = true;
      if (hints == 0) r.independent = true;
    }
    if (error != null) r.errors[error] = (r.errors[error] ?? 0) + 1;
    _changed();
  }

  /// Dictados acertados de [ids].
  int dictationsCorrect(Iterable<String> ids) =>
      ids.where((id) => _progress.dictations[id]?.correct ?? false).length;

  /// Un nivel de dictado está abierto: el 1 siempre; los demás al acertar
  /// [unlockAfter] dictados del anterior.
  bool dictationLevelOpen(int level, Iterable<String> Function(int level) idsOf) =>
      level <= 1 ||
      (dictationsCorrect(idsOf(level - 1)) >= unlockAfter && dictationLevelOpen(level - 1, idsOf));

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
