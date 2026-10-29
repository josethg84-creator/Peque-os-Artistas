import 'learning_level.dart';

/// Progreso de un minijuego.
class GameProgress {
  const GameProgress({this.sessions = 0, this.questions = 0, this.lastPlayed});

  /// Partidas terminadas.
  final int sessions;

  /// Preguntas acertadas o parejas encontradas en total.
  final int questions;
  final DateTime? lastPlayed;

  GameProgress add({required bool completed, required int questions, required DateTime at}) => GameProgress(
    sessions: sessions + (completed ? 1 : 0),
    questions: this.questions + questions,
    lastPlayed: at,
  );

  Map<String, Object?> toJson() => {
    'sessions': sessions,
    'questions': questions,
    'last_played': lastPlayed?.toUtc().toIso8601String(),
  };

  static GameProgress fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return const GameProgress();
    int count(Object? v) => v is int && v >= 0 ? v : 0;
    return GameProgress(
      sessions: count(json['sessions']),
      questions: count(json['questions']),
      lastPlayed: _date(json['last_played']),
    );
  }
}

/// Preferencias que el niño (o un adulto) cambia con botones grandes.
class LearningSettings {
  const LearningSettings({this.soundOn = true, this.voiceOn = true, this.level = LearningLevel.initial});

  final bool soundOn;
  final bool voiceOn;
  final LearningLevel level;

  LearningSettings copyWith({bool? soundOn, bool? voiceOn, LearningLevel? level}) => LearningSettings(
    soundOn: soundOn ?? this.soundOn,
    voiceOn: voiceOn ?? this.voiceOn,
    level: level ?? this.level,
  );

  Map<String, Object> toJson() => {'sound_on': soundOn, 'voice_on': voiceOn, 'level': level.id};

  static LearningSettings fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return const LearningSettings();
    return LearningSettings(
      soundOn: json['sound_on'] is bool ? json['sound_on'] as bool : true,
      voiceOn: json['voice_on'] is bool ? json['voice_on'] as bool : true,
      level: LearningLevel.fromId(json['level'] is String ? json['level'] as String : null),
    );
  }
}

/// Todo lo que se guarda de «Aprender jugando». Inmutable.
class LearningProgress {
  LearningProgress({
    this.settings = const LearningSettings(),
    Map<GameId, GameProgress> games = const {},
    Map<String, DateTime> rewards = const {},
    this.stars = 0,
    this.lastActivity,
  }) : games = Map.unmodifiable(games),
       rewards = Map.unmodifiable(rewards);

  static const formatVersion = 1;

  final LearningSettings settings;
  final Map<GameId, GameProgress> games;

  /// Premios conseguidos (id → fecha). Un mapa: no puede haber duplicados.
  final Map<String, DateTime> rewards;

  /// Estrellas acumuladas: una por pregunta acertada o pareja encontrada.
  final int stars;
  final DateTime? lastActivity;

  GameProgress game(GameId id) => games[id] ?? const GameProgress();
  int get totalSessions => games.values.fold(0, (a, g) => a + g.sessions);

  LearningProgress copyWith({
    LearningSettings? settings,
    Map<GameId, GameProgress>? games,
    Map<String, DateTime>? rewards,
    int? stars,
    DateTime? lastActivity,
  }) => LearningProgress(
    settings: settings ?? this.settings,
    games: games ?? this.games,
    rewards: rewards ?? this.rewards,
    stars: stars ?? this.stars,
    lastActivity: lastActivity ?? this.lastActivity,
  );

  Map<String, Object?> toJson() => {
    'format_version': formatVersion,
    'settings': settings.toJson(),
    'games': {for (final e in games.entries) e.key.id: e.value.toJson()},
    'rewards': {for (final e in rewards.entries) e.key: e.value.toUtc().toIso8601String()},
    'stars': stars,
    'last_activity': lastActivity?.toUtc().toIso8601String(),
  };

  /// Lee el progreso de forma tolerante: los campos ausentes o no válidos toman
  /// su valor por defecto en lugar de perder todo lo demás.
  static LearningProgress fromJson(Map<String, dynamic> json) {
    final games = <GameId, GameProgress>{};
    final rawGames = json['games'];
    if (rawGames is Map<String, dynamic>) {
      for (final e in rawGames.entries) {
        final id = GameId.fromId(e.key);
        if (id != null) games[id] = GameProgress.fromJson(e.value);
      }
    }
    final earned = <String, DateTime>{};
    final rawRewards = json['rewards'];
    if (rawRewards is Map<String, dynamic>) {
      for (final e in rawRewards.entries) {
        final at = _date(e.value);
        if (at != null) earned[e.key] = at;
      }
    }
    final stars = json['stars'];
    return LearningProgress(
      settings: LearningSettings.fromJson(json['settings']),
      games: games,
      rewards: earned,
      stars: stars is int && stars >= 0 ? stars : 0,
      lastActivity: _date(json['last_activity']),
    );
  }
}

/// Fecha guardada como texto ISO; cualquier otro tipo cuenta como ausente.
DateTime? _date(Object? value) => value is String ? DateTime.tryParse(value) : null;
