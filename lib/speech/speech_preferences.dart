/// Ajustes de «Aprendo a Hablar» que configura un adulto (zona de adultos).
/// Sirven para proponer contenido, nunca para bloquearlo: el niño puede usar
/// cualquier actividad y cualquier nivel.
class SpeechPreferences {
  SpeechPreferences({
    this.ageRange,
    this.level = 1,
    Set<String>? favoriteCategories,
    this.minutes = 10,
    this.slowVoice = false,
  }) : favoriteCategories = favoriteCategories ?? {};

  /// Edades orientativas que se pueden elegir.
  static const ageRanges = ['3-4', '4-5', '5-6', '6-7'];

  /// Minutos sugeridos por sesión.
  static const minuteOptions = [5, 10, 15, 20];

  /// Nivel de partida que se propone para cada edad (se puede cambiar).
  static int suggestedLevel(String ageRange) => switch (ageRange) {
    '3-4' || '4-5' => 1,
    '5-6' => 2,
    _ => 3,
  };

  /// «4-5»: solo orienta qué proponer.
  String? ageRange;

  /// Nivel de complejidad (1 fácil, 2 medio, 3 difícil). Se puede cambiar
  /// en cualquier momento, aquí o dentro de cada juego.
  int level;

  /// Ids de grupos de palabras que más le gustan.
  final Set<String> favoriteCategories;

  /// Duración sugerida de una sesión: Lolo propone descansar, sin cortar nada.
  int minutes;

  /// Narración más lenta en todo el módulo.
  bool slowVoice;

  static String levelName(int level) => switch (level) {
    1 => 'Fácil',
    2 => 'Medio',
    _ => 'Difícil',
  };

  Map<String, dynamic> toJson() => {
    'age_range': ageRange,
    'level': level,
    'favorite_categories': favoriteCategories.toList()..sort(),
    'minutes': minutes,
    'slow_voice': slowVoice,
  };

  static SpeechPreferences fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return SpeechPreferences();
    final age = json['age_range'];
    final level = json['level'];
    final minutes = json['minutes'];
    return SpeechPreferences(
      ageRange: ageRanges.contains(age) ? age as String : null,
      level: level is int && level >= 1 && level <= 3 ? level : 1,
      favoriteCategories: {...(json['favorite_categories'] as List? ?? const []).whereType<String>()},
      minutes: minutes is int && minuteOptions.contains(minutes) ? minutes : 10,
      slowVoice: json['slow_voice'] == true,
    );
  }
}

/// Lo hecho hoy (para «Mi aventura de hoy»). Se reinicia cada día: no hay
/// rachas ni nada que se pierda.
class DailyRecord {
  DailyRecord({required this.day, Map<String, int>? counts, Set<String>? skipped})
    : counts = counts ?? {},
      skipped = skipped ?? {};

  /// AAAA-MM-DD.
  final String day;

  /// Veces que hizo hoy cada cosa (palabras, oraciones, verbos, cuentos…).
  final Map<String, int> counts;

  /// Misiones que decidió saltar hoy.
  final Set<String> skipped;

  int count(String key) => counts[key] ?? 0;

  Map<String, dynamic> toJson() => {
    'day': day,
    'counts': Map.fromEntries(counts.entries.toList()..sort((a, b) => a.key.compareTo(b.key))),
    'skipped': skipped.toList()..sort(),
  };

  static DailyRecord? fromJson(Object? json) {
    if (json is! Map<String, dynamic> || json['day'] is! String) return null;
    return DailyRecord(
      day: json['day'] as String,
      counts: {
        if (json['counts'] case final Map<String, dynamic> m)
          for (final MapEntry(:key, :value) in m.entries)
            if (value is int) key: value,
      },
      skipped: {...(json['skipped'] as List? ?? const []).whereType<String>()},
    );
  }
}
