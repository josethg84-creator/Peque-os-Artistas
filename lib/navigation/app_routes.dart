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
