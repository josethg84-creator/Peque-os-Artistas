import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../persistence/creation.dart';
import '../persistence/key_value_backend.dart';
import 'achievement_data.dart';
import 'achievements.dart';

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
    AchievementData? achievements,
    this.schema = currentSchema,
  }) : dictations = dictations ?? {},
       achievements = achievements ?? AchievementData(),
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

  // ------------------------------------------------ logros (Fase 7)

  /// Perfil, sílabas, estrellas, medallas e historial por días.
  final AchievementData achievements;

  /// Versión de los datos: 1 = guardados antes de la Fase 7 (sin logros);
  /// al cargarlos se calculan sus estrellas y medallas una sola vez.
  int schema;
  static const currentSchema = 2;

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
    'schema': schema,
    'achievements': achievements.toJson(),
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
      achievements: AchievementData.fromJson(json['achievements']),
      schema: json['schema'] is int ? json['schema'] as int : 1,
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

  /// Copia intacta de lo guardado antes de la Fase 7 (formato 1), hecha una
  /// sola vez antes de convertirlo: si algo fallara, se puede recuperar.
  static const migrationBackupKey = '$key.formato1';

  /// Formato actual (2: Fase 7). Se siguen leyendo los datos en formato 1.
  static const formatVersion = 2;
  static const readableVersions = {1, 2};

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
      if (json is! Map<String, dynamic> || !readableVersions.contains(json['format_version'])) return null;
      final payload = {...json}..remove('checksum');
      if (json['checksum'] != Creation.checksumOf(payload)) return null;
      return ReadingProgress.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  Future<ReadingProgress> load() async {
    final raw = await backend.read(key);
    final p = decode(raw) ?? decode(await backend.read(backupKey));
    if (p == null) return ReadingProgress();
    // Antes de convertir datos del formato 1, se guarda una copia intacta.
    if (p.schema < ReadingProgress.currentSchema &&
        raw != null &&
        await backend.read(migrationBackupKey) == null) {
      await backend.write(migrationBackupKey, raw);
    }
    return p;
  }

  /// Lo guardado antes de la Fase 7, si se hizo la copia (para recuperarlo).
  Future<ReadingProgress?> loadMigrationBackup() async => decode(await backend.read(migrationBackupKey));

  Future<void> save(ReadingProgress p) async {
    final current = await backend.read(key);
    if (decode(current) != null) await backend.write(backupKey, current!);
    await backend.write(key, encode(p));
  }

  Future<void> clear() async {
    await backend.remove(key);
    await backend.remove(backupKey);
    await backend.remove(migrationBackupKey);
  }
}

/// Lleva el progreso de «Aprendo a leer» y lo guarda al momento.
class ReadingController extends ChangeNotifier {
  ReadingController(this._store, {DateTime Function()? clock, this.celebrations = true})
    : _clock = clock ?? DateTime.now;

  /// Mostrar la celebración de las medallas nuevas (las medallas se guardan
  /// igual; las pruebas de otras pantallas la desactivan para no taparlas).
  final bool celebrations;

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
    if (_progress.schema < ReadingProgress.currentSchema) {
      _migrate();
      unawaited(_save());
    }
    notifyListeners();
  }();

  /// Convierte datos de antes de la Fase 7: calcula las estrellas y medallas
  /// que ya se habían ganado (sin celebraciones), sin borrar nada.
  void _migrate() {
    final p = _progress;
    for (final e in p.completed.entries) {
      for (final mode in e.value) {
        final k = ReadingProgress.key(mode, e.key);
        _award('hecho:$k', StarRules.complete, 'Progreso anterior');
        if (p.firstTry.contains(k) && !p.withHints.contains(k)) {
          _award('solo:$k', StarRules.independent, 'Progreso anterior, sin pistas');
        }
      }
    }
    for (final id in p.sentencesHeard) {
      _award('hecho:escuchar:$id', StarRules.complete, 'Progreso anterior');
    }
    for (final e in p.dictations.entries) {
      if (e.value.correct) _award('hecho:dictado:${e.key}', StarRules.complete, 'Progreso anterior');
      if (e.value.independent) {
        _award('solo:dictado:${e.key}', StarRules.independent, 'Progreso anterior, sin pistas');
      }
    }
    _checkMedals(celebrate: false);
    p.schema = ReadingProgress.currentSchema;
  }

  /// Recupera la copia hecha antes de la Fase 7 (zona de adultos). Devuelve
  /// `false` si no hay copia.
  Future<bool> restoreMigrationBackup() async {
    final backup = await _store.loadMigrationBackup();
    if (backup == null) return false;
    _progress = backup;
    _migrate();
    _changed();
    return true;
  }

  // ------------------------------------------------ logros (Fase 7)

  /// Modos de «Completo palabras».
  static const wordModes = {'elige', 'arrastra', 'ordena'};

  /// Módulo al que pertenece un modo de juego.
  static String moduleOf(String mode) => switch (mode) {
    'elige' || 'arrastra' || 'ordena' => ReadingModule.words,
    sentenceQuestionMode || sentenceOrderMode || sentenceListenMode || 'escuchar' => ReadingModule.sentences,
    'dictado' => ReadingModule.dictation,
    _ => ReadingModule.syllables,
  };

  String _today() {
    final n = _clock();
    return '${n.year.toString().padLeft(4, '0')}-${n.month.toString().padLeft(2, '0')}-${n.day.toString().padLeft(2, '0')}';
  }

  /// Anota actividad en un módulo (para el historial y «Aprendo cada día»).
  void _touch(String module) {
    final a = _progress.achievements;
    final today = _today();
    final day = a.days[today] ??= {};
    day[module] = (day[module] ?? 0) + 1;
    a.lastActivity[module] = today;
    if (a.days.length > AchievementData.keepDays) {
      final keys = a.days.keys.toList()..sort();
      for (final k in keys.take(a.days.length - AchievementData.keepDays)) {
        a.days.remove(k);
      }
    }
  }

  /// Da estrellas por un motivo, una sola vez (la clave lo identifica).
  /// Devuelve si se dieron.
  bool _award(String key, int stars, String reason) {
    final r = _progress.achievements.rewards;
    if (r.containsKey(key)) return false;
    r[key] = RewardEvent(stars: stars, reason: reason, date: _today());
    return true;
  }

  /// Estrellas por esfuerzo: acertar algo que antes costó (una vez al día por
  /// módulo).
  void _effort(String module) =>
      _award('esfuerzo:${_today()}:$module', StarRules.effort, 'Volviste a practicar algo que costaba');

  int get stars => _progress.achievements.stars;

  final _celebrations = <MedalDef>[];

  /// Medallas recién conseguidas que aún no se han celebrado.
  List<MedalDef> get pendingCelebrations => List.unmodifiable(_celebrations);

  /// Saca la siguiente medalla por celebrar.
  MedalDef? takeCelebration() {
    if (_celebrations.isEmpty) return null;
    final m = _celebrations.removeAt(0);
    notifyListeners();
    return m;
  }

  void _checkMedals({bool celebrate = true}) {
    for (final m in Medals.newlyEarned(_progress)) {
      _progress.achievements.medals[m.id] = _today();
      if (celebrate && celebrations) _celebrations.add(m);
    }
  }

  /// Una sílaba tocada para oírla en «Aprendo las sílabas».
  void recordSyllableHeard(String syllableId) {
    _touch(ReadingModule.syllables);
    _progress.achievements.syllablesHeard.add(syllableId);
    _changed();
  }

  /// Un toque en un juego de sílabas ([game]: «escucha_encuentra» o
  /// «une_palabra»). [firstTry]: acertada al primer toque de la pregunta;
  /// [mistakes]: errores en esta pregunta antes de acertarla.
  void recordSyllableAnswer(
    String syllableId, {
    required String game,
    required bool correct,
    bool firstTry = false,
    int mistakes = 0,
  }) {
    _touch(ReadingModule.syllables);
    final stat = _progress.achievements.syllableStats[syllableId] ??= SyllableStat();
    final hadErrors = stat.errors > 0;
    stat.attempts++;
    if (correct) {
      stat.correct++;
      if (firstTry) stat.firstTry++;
      final k = '$game:$syllableId';
      _award('hecho:$k', StarRules.complete, 'Acertaste la sílaba ${syllableId.toUpperCase()}');
      if (firstTry) {
        _award('solo:$k', StarRules.independent, 'Sílaba ${syllableId.toUpperCase()} a la primera');
      }
      if (mistakes >= 2) _progress.achievements.overcome.add(k);
      if (hadErrors) _effort(ReadingModule.syllables);
    }
    _changed();
  }

  /// Se terminó una partida completa de un módulo.
  void recordSeries(String module) {
    final today = _today();
    final done = _progress.achievements.rewards.keys.where((k) => k.startsWith('serie:$today:')).length;
    if (done < StarRules.maxSeriesPerDay) {
      _award('serie:$today:${done + 1}', StarRules.series, 'Terminaste una partida');
    }
    _touch(module);
    _changed();
  }

  void setAlias(String alias) {
    _progress.achievements.profile.alias = ReadingProfile.cleanAlias(alias);
    _changed();
  }

  void setAvatar(String avatar) {
    if (!ReadingProfile.avatars.contains(avatar)) return;
    _progress.achievements.profile.avatar = avatar;
    _changed();
  }

  void setCelebrationSound(bool on) {
    _progress.achievements.profile.celebrationSound = on;
    _changed();
  }

  /// Cada «Comprobar».
  void recordAttempt({required bool correct}) {
    _touch(ReadingModule.words);
    _progress.attempts++;
    if (correct) _progress.correctAnswers++;
    _changed();
  }

  /// Un ejercicio terminado en un modo.
  /// [mistakes]: errores antes de resolverlo (2 o más: «Superé un desafío»).
  void recordCompleted(
    String exerciseId,
    String mode, {
    required bool firstTry,
    required bool usedHints,
    int mistakes = 0,
  }) {
    final module = moduleOf(mode);
    _touch(module);
    (_progress.completed[exerciseId] ??= {}).add(mode);
    final k = ReadingProgress.key(mode, exerciseId);
    final hadHints = _progress.withHints.contains(k);
    if (firstTry) _progress.firstTry.add(k);
    if (usedHints) _progress.withHints.add(k);
    _award('hecho:$k', StarRules.complete, 'Completaste una actividad');
    if (firstTry && !usedHints) {
      _award('solo:$k', StarRules.independent, 'Lo resolviste sin pistas');
      if (hadHints) _effort(module);
    }
    if (mistakes >= 2) _progress.achievements.overcome.add(k);
    _changed();
  }

  // ------------------------------------------------ oraciones (Fase 5)

  /// Una oración escuchada entera.
  void recordSentenceHeard(String sentenceId) {
    _touch(ReadingModule.sentences);
    _progress.sentencesHeard.add(sentenceId);
    _award('hecho:escuchar:$sentenceId', StarRules.complete, 'Escuchaste una oración entera');
    _changed();
  }

  /// Una palabra tocada para oírla.
  void recordWordPlayed(String word) {
    _touch(ReadingModule.sentences);
    _progress.wordsPlayed.add(word.toLowerCase());
    _changed();
  }

  /// Un intento en una actividad de oraciones.
  void recordSentenceAttempt() {
    _touch(ReadingModule.sentences);
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
    int mistakes = 0,
  }) {
    _progress.questionsAnswered.add(sentenceId);
    _progress.questionsCorrect.add(sentenceId);
    if (!listenedFirst) _progress.sentencesReadAlone.add(sentenceId);
    recordCompleted(
      sentenceId,
      sentenceQuestionMode,
      firstTry: firstTry,
      usedHints: usedHints,
      mistakes: mistakes,
    );
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
    _touch(ReadingModule.dictation);
    final r = _progress.dictations[id] ??= DictationRecord(type: type, level: level, mode: mode);
    final hadErrors = r.errors.isNotEmpty;
    r
      ..mode = mode
      ..attempts += 1
      ..hints = hints > r.hints ? hints : r.hints
      ..date = _today();
    if (correct) {
      r.correct = true;
      if (hints == 0) r.independent = true;
      _award('hecho:dictado:$id', StarRules.complete, 'Acertaste un dictado');
      if (hints == 0) _award('solo:dictado:$id', StarRules.independent, 'Dictado sin pistas');
      if (r.attempts >= 3) _progress.achievements.overcome.add('dictado:$id');
      if (hadErrors) _effort(ReadingModule.dictation);
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
    _checkMedals();
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
    _celebrations.clear();
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
