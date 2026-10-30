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

/// Preferencias que el niño (o un adulto) cambia con botones grandes: nivel de
/// los juegos y todo el sonido de la app (música, efectos y voz, cada uno con su
/// volumen, más un volumen general y un botón de silencio).
class LearningSettings {
  const LearningSettings({
    this.soundOn = true,
    this.voiceOn = true,
    this.level = LearningLevel.initial,
    this.muted = false,
    this.musicOn = true,
    this.masterVolume = 1.0,
    this.musicVolume = 0.5,
    this.effectsVolume = 0.8,
    this.voiceVolume = 1.0,
  });

  /// Efectos de sonido activados.
  final bool soundOn;
  final bool voiceOn;
  final LearningLevel level;

  /// Silencio total (botón del altavoz de la pantalla de inicio).
  final bool muted;
  final bool musicOn;

  /// Volúmenes de 0 a 1.
  final double masterVolume;
  final double musicVolume;
  final double effectsVolume;
  final double voiceVolume;

  LearningSettings copyWith({
    bool? soundOn,
    bool? voiceOn,
    LearningLevel? level,
    bool? muted,
    bool? musicOn,
    double? masterVolume,
    double? musicVolume,
    double? effectsVolume,
    double? voiceVolume,
  }) => LearningSettings(
    soundOn: soundOn ?? this.soundOn,
    voiceOn: voiceOn ?? this.voiceOn,
    level: level ?? this.level,
    muted: muted ?? this.muted,
    musicOn: musicOn ?? this.musicOn,
    masterVolume: masterVolume ?? this.masterVolume,
    musicVolume: musicVolume ?? this.musicVolume,
    effectsVolume: effectsVolume ?? this.effectsVolume,
    voiceVolume: voiceVolume ?? this.voiceVolume,
  );

  Map<String, Object> toJson() => {
    'sound_on': soundOn,
    'voice_on': voiceOn,
    'level': level.id,
    'muted': muted,
    'music_on': musicOn,
    'master_volume': masterVolume,
    'music_volume': musicVolume,
    'effects_volume': effectsVolume,
    'voice_volume': voiceVolume,
  };

  /// Acepta datos antiguos (sin los campos de sonido) o dañados: cada campo
  /// que falte o no sea válido toma su valor por defecto.
  static LearningSettings fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return const LearningSettings();
    const d = LearningSettings();
    bool flag(String key, bool fallback) => json[key] is bool ? json[key] as bool : fallback;
    double volume(String key, double fallback) {
      final v = json[key];
      return v is num && v.isFinite ? v.toDouble().clamp(0.0, 1.0) : fallback;
    }

    return LearningSettings(
      soundOn: flag('sound_on', d.soundOn),
      voiceOn: flag('voice_on', d.voiceOn),
      level: LearningLevel.fromId(json['level'] is String ? json['level'] as String : null),
      muted: flag('muted', d.muted),
      musicOn: flag('music_on', d.musicOn),
      masterVolume: volume('master_volume', d.masterVolume),
      musicVolume: volume('music_volume', d.musicVolume),
      effectsVolume: volume('effects_volume', d.effectsVolume),
      voiceVolume: volume('voice_volume', d.voiceVolume),
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
