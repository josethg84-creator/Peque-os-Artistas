import 'speech_content.dart';
import 'speech_progress.dart';

/// Lo hecho en la fase 3 de «Aprendo a Hablar» (conversaciones, cuentos,
/// expresarse, contar historias y escuchar), con sus totales. Lo usan «Mi
/// progreso», el panel del niño y la zona de adultos. Solo cuenta actividades;
/// no es una evaluación del habla.
class SpeechPhase3Summary {
  SpeechPhase3Summary(SpeechProgress p, SpeechContent c)
    : conversations = c.conversations.where((x) => p.conversationsDone.contains(x.id)).length,
      conversationsTotal = c.conversations.length,
      storiesHeard = c.stories.where((s) => p.storiesHeard.contains(s.id)).length,
      storiesQuizzed = c.stories.where((s) => p.storiesQuizzed.contains(s.id)).length,
      storiesTotal = c.stories.length,
      told = c.tell.where((t) => p.storiesTold.contains(t.id)).length,
      tellTotal = c.tell.length,
      needs = c.expressions.needs.where((n) => p.expressionsPracticed.contains('necesidad:${n.id}')).length,
      needsTotal = c.expressions.needs.length,
      emotions = c.expressions.emotions
          .where((e) => p.expressionsPracticed.contains('emocion:${e.id}'))
          .length,
      emotionsTotal = c.expressions.emotions.length,
      feelingSentences = p.expressionsPracticed.where((x) => x.startsWith('frase:')).length,
      listening = c.listening.exercises.where((e) => p.listeningDone.contains(e.id)).length,
      listeningTotal = c.listening.exercises.length,
      listeningLevels = c.listening.levels
          .where((l) => p.activitiesDone.containsKey('escucho_nivel_${l.level}'))
          .length,
      listeningLevelsTotal = c.listening.levels.length,
      answers = p.answers,
      stars = p.stars;

  final int conversations, conversationsTotal;
  final int storiesHeard, storiesQuizzed, storiesTotal;
  final int told, tellTotal;
  final int needs, needsTotal, emotions, emotionsTotal, feelingSentences;
  final int listening, listeningTotal, listeningLevels, listeningLevelsTotal;
  final int answers, stars;

  /// Para la zona de adultos.
  List<String> get adultLines => [
    'Conversaciones con Lolo: $conversations de $conversationsTotal.',
    'Cuentos escuchados: $storiesHeard de $storiesTotal; con las preguntas respondidas: $storiesQuizzed.',
    'Historias contadas por el niño («Ahora cuéntamelo tú»): $told de $tellTotal.',
    'Expresarse: $needs de $needsTotal necesidades y $emotions de $emotionsTotal emociones; '
        '$feelingSentences frase(s) sobre cómo se siente.',
    'Escucho y respondo: $listening de $listeningTotal ejercicios y $listeningLevels de '
        '$listeningLevelsTotal niveles terminados.',
    'Respuestas acertadas en total: $answers. Estrellas de Aprendo a Hablar: $stars.',
  ];
}

/// Una recompensa de «Mis aventuras con Lolo». Se gana haciendo cosas, nunca
/// se pierde, y no compara al niño con nadie.
class SpeechMedal {
  const SpeechMedal(this.id, this.title, this.icon, this.progress, this.goal);

  final String id;
  final String title;

  /// Nombre de un icono de Material (ver `SpeechIcons.lookup`).
  final String icon;
  final int progress;
  final int goal;

  bool get earned => progress >= goal;
}

List<SpeechMedal> speechMedals(SpeechProgress p) => [
  SpeechMedal('palabras', 'Primeras palabras', 'abc', p.wordsHeard.length, 10),
  SpeechMedal('vocabulario', 'Coleccionista de palabras', 'auto_stories', p.wordsHeard.length, 50),
  SpeechMedal('oraciones', 'Constructor de oraciones', 'construction', p.sentencesBuilt.length, 3),
  SpeechMedal('verbos', 'Amigo de los verbos', 'run', p.verbsHeard.length, 5),
  SpeechMedal('charlas', 'Gran conversador', 'friends', p.conversationsDone.length, 3),
  SpeechMedal('cuentos', 'Oyente de cuentos', 'menu_book', p.storiesHeard.length, 3),
  SpeechMedal('historias', 'Cuentacuentos', 'star', p.storiesBuilt.length + p.storiesTold.length, 2),
  SpeechMedal('silabas', 'Palmas y sílabas', 'sign_language', p.syllablesDone.length, 5),
  SpeechMedal('aventura', 'Aventurero', 'looks', p.activitiesDone['aventura'] ?? 0, 1),
];

/// Lo hecho en la fase 4 (aventuras, sonidos, juegos de palabras e historias
/// inventadas), para la zona de adultos. Solo describe actividades: no
/// interpreta resultados ni clasifica el desarrollo del lenguaje.
List<String> speechPhase4AdultLines(SpeechProgress p, {required List<String> favorites}) {
  int done(String key) => p.activitiesDone[key] ?? 0;
  final prefs = p.preferences;
  final medals = speechMedals(p).where((m) => m.earned).map((m) => m.title).toList();
  return [
    'Aventuras de hoy completadas (en total): ${done('aventura')}.',
    'Sílabas y sonidos: ${p.syllablesDone.length} palabra(s) con palmas; rondas de «¿Con qué empieza?» '
        '${done('juego_empieza')}, de rimas ${done('juego_rimas')} y de «Escucho y encuentro» ${done('juego_encuentro')}.',
    'Juegos de palabras: «¿Cuál es?» ${done('juego_cual')}, «¿De qué grupo es?» ${done('juego_grupo')} y '
        '«Completa la frase» ${done('juego_frase')}.',
    'Historias inventadas en «Mi historia»: ${p.storiesBuilt.length}.',
    if (favorites.isNotEmpty) 'Actividades que más abre: ${favorites.join(', ')}.',
    if (medals.isNotEmpty) 'Recompensas: ${medals.join(', ')}.',
    'Ajustes: edad orientativa ${prefs.ageRange == null ? 'sin indicar' : '${prefs.ageRange} años'}, '
        'nivel ${SpeechPreferences.levelName(prefs.level).toLowerCase()}, ${prefs.minutes} minutos sugeridos, '
        'narración ${prefs.slowVoice ? 'más lenta' : 'a velocidad habitual'}.',
  ];
}
