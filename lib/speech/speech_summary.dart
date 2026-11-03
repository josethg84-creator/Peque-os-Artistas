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
