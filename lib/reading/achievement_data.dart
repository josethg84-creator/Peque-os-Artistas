// Datos de la Fase 7 (logros) dentro del progreso de «Aprendo a leer».
// Todo se guarda solo en el dispositivo, en la misma clave que el resto del
// progreso de lectura; no hay cuentas ni datos personales.

/// Módulos de «Aprendo a leer».
abstract final class ReadingModule {
  static const syllables = 'silabas';
  static const words = 'palabras';
  static const sentences = 'oraciones';
  static const dictation = 'dictado';
  static const all = [syllables, words, sentences, dictation];
}

/// Respuestas a una sílaba en los juegos de sílabas.
class SyllableStat {
  SyllableStat({this.attempts = 0, this.correct = 0, this.firstTry = 0});

  /// Toques en total (aciertos y errores).
  int attempts;

  /// Veces que se acertó.
  int correct;

  /// Veces que se acertó al primer toque.
  int firstTry;

  int get errors => attempts - correct;

  Map<String, dynamic> toJson() => {'a': attempts, 'c': correct, 'f': firstTry};

  static SyllableStat fromJson(Object? json) {
    int n(Object? v) => v is int && v >= 0 ? v : 0;
    if (json is! Map) return SyllableStat();
    return SyllableStat(attempts: n(json['a']), correct: n(json['c']), firstTry: n(json['f']));
  }
}

/// Un motivo por el que se ganaron estrellas. La clave lo identifica: el
/// mismo motivo nunca da estrellas dos veces.
class RewardEvent {
  const RewardEvent({required this.stars, required this.reason, required this.date});
  final int stars;

  /// Explicación («Completaste PATO»).
  final String reason;

  /// AAAA-MM-DD.
  final String date;

  Map<String, dynamic> toJson() => {'s': stars, 'r': reason, 'd': date};

  static RewardEvent? fromJson(Object? json) {
    if (json is! Map || json['s'] is! int) return null;
    return RewardEvent(
      stars: json['s'] as int,
      reason: json['r'] is String ? json['r'] as String : '',
      date: json['d'] is String ? json['d'] as String : '',
    );
  }
}

/// Perfil del niño: solo un apodo opcional, un avatar de la app y
/// preferencias. Nunca nombre completo, foto, edad exacta ni dirección.
class ReadingProfile {
  ReadingProfile({this.alias = '', this.avatar = 'lolo', this.celebrationSound = true});

  /// Apodo opcional (máximo [maxAlias] caracteres).
  String alias;

  /// Uno de [avatars].
  String avatar;

  /// La felicitación de las medallas se oye (se puede apagar).
  bool celebrationSound;

  static const maxAlias = 16;
  static const avatars = ['lolo', 'nina', 'nino', 'robot', 'dragon'];

  /// Deja el apodo dentro de los límites: sin saltos de línea ni símbolos raros.
  static String cleanAlias(String s) {
    final t = s.replaceAll(RegExp(r'[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-]'), '').replaceAll(RegExp(r'\s+'), ' ').trim();
    return t.length > maxAlias ? t.substring(0, maxAlias).trim() : t;
  }

  Map<String, dynamic> toJson() => {'alias': alias, 'avatar': avatar, 'celebration_sound': celebrationSound};

  static ReadingProfile fromJson(Object? json) {
    if (json is! Map) return ReadingProfile();
    final avatar = json['avatar'];
    return ReadingProfile(
      alias: json['alias'] is String ? cleanAlias(json['alias'] as String) : '',
      avatar: avatars.contains(avatar) ? avatar as String : 'lolo',
      celebrationSound: json['celebration_sound'] != false,
    );
  }
}

/// Lo que guarda la Fase 7.
class AchievementData {
  AchievementData({
    Set<String>? syllablesHeard,
    Map<String, SyllableStat>? syllableStats,
    Set<String>? overcome,
    Map<String, RewardEvent>? rewards,
    Map<String, String>? medals,
    Map<String, Map<String, int>>? days,
    Map<String, String>? lastActivity,
    ReadingProfile? profile,
  }) : syllablesHeard = syllablesHeard ?? {},
       syllableStats = syllableStats ?? {},
       overcome = overcome ?? {},
       rewards = rewards ?? {},
       medals = medals ?? {},
       days = days ?? {},
       lastActivity = lastActivity ?? {},
       profile = profile ?? ReadingProfile();

  /// Sílabas (id) escuchadas tocándolas en «Aprendo las sílabas».
  final Set<String> syllablesHeard;

  /// Sílaba (id) → respuestas en los juegos de sílabas.
  final Map<String, SyllableStat> syllableStats;

  /// Ejercicios resueltos tras 2 errores o más («Superé un desafío»).
  final Set<String> overcome;

  /// Clave → estrellas ganadas (registro de eventos, sin duplicados).
  final Map<String, RewardEvent> rewards;

  /// Medalla → fecha en que se consiguió (AAAA-MM-DD).
  final Map<String, String> medals;

  /// Día (AAAA-MM-DD) → módulo → acciones registradas ese día.
  final Map<String, Map<String, int>> days;

  /// Módulo → último día con actividad.
  final Map<String, String> lastActivity;

  final ReadingProfile profile;

  /// Se guardan como mucho estos días de historial.
  static const keepDays = 120;

  int get stars => rewards.values.fold(0, (n, e) => n + e.stars);

  Map<String, dynamic> toJson() {
    List<String> sorted(Iterable<String> s) => s.toList()..sort();
    return {
      'syllables_heard': sorted(syllablesHeard),
      'syllable_stats': {for (final k in sorted(syllableStats.keys)) k: syllableStats[k]!.toJson()},
      'overcome': sorted(overcome),
      'rewards': {for (final k in sorted(rewards.keys)) k: rewards[k]!.toJson()},
      'medals': {for (final k in sorted(medals.keys)) k: medals[k]},
      'days': {
        for (final d in sorted(days.keys)) d: {for (final m in sorted(days[d]!.keys)) m: days[d]![m]},
      },
      'last_activity': {for (final k in sorted(lastActivity.keys)) k: lastActivity[k]},
      'profile': profile.toJson(),
    };
  }

  static AchievementData fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return AchievementData();
    Set<String> strings(Object? v) => {...(v is List ? v : const []).whereType<String>()};
    Map<String, String> stringMap(Object? v) => {
      if (v is Map)
        for (final e in v.entries)
          if (e.key is String && e.value is String) e.key as String: e.value as String,
    };
    return AchievementData(
      syllablesHeard: strings(json['syllables_heard']),
      syllableStats: {
        if (json['syllable_stats'] case final Map<String, dynamic> m)
          for (final e in m.entries) e.key: SyllableStat.fromJson(e.value),
      },
      overcome: strings(json['overcome']),
      rewards: {
        if (json['rewards'] case final Map<String, dynamic> m)
          for (final e in m.entries) e.key: ?RewardEvent.fromJson(e.value),
      },
      medals: stringMap(json['medals']),
      days: {
        if (json['days'] case final Map<String, dynamic> m)
          for (final e in m.entries)
            if (e.value is Map)
              e.key: {
                for (final x in (e.value as Map).entries)
                  if (x.key is String && x.value is int) x.key as String: x.value as int,
              },
      },
      lastActivity: stringMap(json['last_activity']),
      profile: ReadingProfile.fromJson(json['profile']),
    );
  }
}
