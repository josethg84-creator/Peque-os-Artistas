import '../learning/learning_level.dart';
import '../models/drawing_category.dart';

/// Nombres de las rutas de la aplicación.
abstract final class AppRoutes {
  static const home = '/';
  static const categories = '/categorias';
  static const gallery = '/galeria';
  static const coloring = '/colorear';
  static const savedDrawings = '/mis-dibujos';
  static const activities = '/actividades';
  static const adultZone = '/adultos';
  static const search = '/buscar';
  static const learningGame = '/aprender';
  static const rewards = '/premios';
  static const soundSettings = '/sonido';
  static const miniGames = '/minijuegos';
  static const profile = '/perfil';

  // «Aprendo a Hablar».
  static const speech = '/hablar';
  static const speechWordGroups = '/hablar/palabras';
  static const speechWords = '/hablar/palabras/grupo';
  static const speechPhrases = '/hablar/frases';
  static const speechProgress = '/hablar/progreso';
  static const speechSentences = '/hablar/oraciones';
  static const speechBuilder = '/hablar/oraciones/construir';
  static const speechOrder = '/hablar/oraciones/ordenar';
  static const speechComplete = '/hablar/oraciones/completar';
  static const speechQuestion = '/hablar/oraciones/pregunta';
  static const speechVerbs = '/hablar/verbos';
  static const speechVerb = '/hablar/verbos/verbo';
  static const speechVerbGames = '/hablar/verbos/juegos';
  static const speechListen = '/hablar/escucho';
  static const speechConversations = '/hablar/conversaciones';
  static const speechConversationList = '/hablar/conversaciones/categoria';
  static const speechConversation = '/hablar/conversaciones/conversacion';
  static const speechStories = '/hablar/cuentos';
  static const speechStory = '/hablar/cuentos/cuento';
  static const speechStoryQuiz = '/hablar/cuentos/preguntas';
  static const speechStoryOrder = '/hablar/cuentos/ordenar';
  static const speechExpress = '/hablar/expresarme';
  static const speechNeeds = '/hablar/expresarme/necesito';
  static const speechEmotions = '/hablar/expresarme/emociones';
  static const speechEmotion = '/hablar/expresarme/emocion';
  static const speechExpressBuilder = '/hablar/expresarme/frase';
  static const speechTellList = '/hablar/cuentamelo';
  static const speechTell = '/hablar/cuentamelo/historia';
  static const speechListening = '/hablar/responder';
  static const speechListeningLevel = '/hablar/responder/nivel';

  // Fase 4.
  static const speechMission = '/hablar/aventura';
  static const speechSounds = '/hablar/sonidos';
  static const speechClaps = '/hablar/sonidos/palmas';
  static const speechSoundGame = '/hablar/sonidos/juego';
  static const speechWordGames = '/hablar/palabras/juegos';
  static const speechWordGame = '/hablar/palabras/juego';
  static const speechMyStory = '/hablar/mi-historia';

  // Fase 5: «Quiero decir» (comunicación aumentativa).
  static const aac = '/quiero-decir';
  static const aacCategory = '/quiero-decir/categoria';
  static const aacQuick = '/quiero-decir/rapido';
  static const aacBuilder = '/quiero-decir/construir';
  static const aacFeelings = '/quiero-decir/emociones';
  static const aacFavorites = '/quiero-decir/favoritas';
  static const aacLearn = '/quiero-decir/aprender';
}

/// Argumento de [AppRoutes.aacCategory].
class AacCategoryArgs {
  const AacCategoryArgs(this.categoryId);
  final String categoryId;
}

/// Argumento de los juegos con nivel (sílabas, sonidos y palabras).
class SpeechGameArgs {
  const SpeechGameArgs(this.game, {this.level});

  /// Qué juego («empieza», «rimas», «encuentro», «cual», «grupo», «frase»).
  final String game;

  /// Nivel (1 a 3); si es `null`, el de los ajustes.
  final int? level;
}

/// Argumento de [AppRoutes.speechListeningLevel].
class SpeechListeningArgs {
  const SpeechListeningArgs(this.level);
  final int level;
}

/// Argumento de [AppRoutes.speechTell].
class SpeechTellArgs {
  const SpeechTellArgs(this.sequenceId);
  final String sequenceId;
}

/// Argumento de [AppRoutes.speechEmotion].
class SpeechEmotionArgs {
  const SpeechEmotionArgs(this.emotionId);
  final String emotionId;
}

/// Argumento de las pantallas de un cuento.
class SpeechStoryArgs {
  const SpeechStoryArgs(this.storyId);
  final String storyId;
}

/// Argumento de una categoría de conversaciones.
class SpeechCategoryArgs {
  const SpeechCategoryArgs(this.categoryId);
  final String categoryId;
}

/// Argumento de [AppRoutes.speechConversation].
class SpeechConversationArgs {
  const SpeechConversationArgs(this.conversationId);
  final String conversationId;
}

/// Argumento de [AppRoutes.speechVerb]: el verbo.
class SpeechVerbArgs {
  const SpeechVerbArgs(this.verbId);
  final String verbId;
}

/// Argumento de [AppRoutes.speechWords]: el grupo de palabras.
class SpeechWordsArgs {
  const SpeechWordsArgs(this.categoryId);
  final String categoryId;
}

/// Argumento de [AppRoutes.gallery].
class GalleryArgs {
  const GalleryArgs(this.category);
  final DrawingCategory category;
}

/// Argumento de [AppRoutes.coloring].
class ColoringArgs {
  /// Sin más datos se continúa la creación más reciente del dibujo (o se
  /// empieza una). [creationId] abre una creación concreta; [startNew] empieza
  /// una nueva desde el dibujo original.
  const ColoringArgs(this.drawingId, {this.creationId, this.startNew = false});
  final String drawingId;
  final String? creationId;
  final bool startNew;
}

/// Argumento de [AppRoutes.adultZone]: solo se concede tras la verificación.
class AdultZoneArgs {
  const AdultZoneArgs.verified();
}

/// Argumento de [AppRoutes.learningGame].
class LearningGameArgs {
  const LearningGameArgs(this.game);
  final GameId game;
}
