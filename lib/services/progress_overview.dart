import '../aac/aac_controller.dart';
import '../learning/learning_level.dart';
import '../learning/learning_progress.dart';
import '../speech/speech_progress.dart';

/// Vista integrada de lo hecho en toda la app, leída de los almacenes de cada
/// módulo tal como están (sin migrar ni copiar datos). Solo cuenta
/// actividades; no evalúa al niño. La comunicación («Quiero decir») no
/// depende de nada de esto.
class ProgressOverview {
  const ProgressOverview({
    required this.drawingsSaved,
    required this.drawingsFinished,
    required this.miniGamesPlayed,
    required this.gameStars,
    required this.wordsPracticed,
    required this.sentencesBuilt,
    required this.storiesHeard,
    required this.conversationsDone,
    required this.phonologyActivities,
    required this.speechStars,
    required this.favoritePhrases,
  });

  factory ProgressOverview.from({
    required int drawingsSaved,
    required int drawingsFinished,
    required LearningProgress learning,
    required SpeechProgress speech,
    required AacPreferences aac,
  }) {
    int done(String key) => speech.activitiesDone[key] ?? 0;
    return ProgressOverview(
      drawingsSaved: drawingsSaved,
      drawingsFinished: drawingsFinished,
      miniGamesPlayed: GameId.values.fold(0, (n, g) => n + learning.game(g).sessions),
      gameStars: learning.stars,
      wordsPracticed: speech.wordsHeard.length,
      sentencesBuilt: speech.sentencesBuilt.length + speech.storiesBuilt.length,
      storiesHeard: speech.storiesHeard.length,
      conversationsDone: speech.conversationsDone.length,
      phonologyActivities:
          speech.syllablesDone.length +
          done('juego_palmas') +
          done('juego_empieza') +
          done('juego_rimas') +
          done('juego_encuentro'),
      speechStars: speech.stars,
      favoritePhrases: aac.favorites.length,
    );
  }

  final int drawingsSaved;
  final int drawingsFinished;
  final int miniGamesPlayed;
  final int gameStars;
  final int wordsPracticed;
  final int sentencesBuilt;
  final int storiesHeard;
  final int conversationsDone;
  final int phonologyActivities;
  final int speechStars;
  final int favoritePhrases;

  /// Líneas para la zona de adultos.
  List<String> get lines => [
    'Dibujos guardados: $drawingsSaved (terminados: $drawingsFinished).',
    'Partidas de mini juegos: $miniGamesPlayed · estrellas de juegos: $gameStars.',
    'Palabras practicadas: $wordsPracticed · oraciones e historias construidas: $sentencesBuilt.',
    'Cuentos escuchados: $storiesHeard · conversaciones terminadas: $conversationsDone.',
    'Actividades de sílabas y sonidos: $phonologyActivities · estrellas de «Aprendo a Hablar»: $speechStars.',
    'Frases favoritas de «Quiero decir»: $favoritePhrases.',
  ];
}
