import '../navigation/app_routes.dart';
import 'recommendations.dart';
import 'speech_content.dart';
import 'speech_progress.dart';

/// Una misión de «Mi aventura de hoy». Todas son opcionales: se pueden hacer
/// en cualquier orden o saltar, sin rachas ni castigos.
class MissionTask {
  const MissionTask(this.id, this.title, this.lolo, this.goal, this.dailyKey);

  final String id;
  final String title;

  /// Lo que dice Lolo al proponerla.
  final String lolo;

  /// Cuántas veces hay que hacerlo hoy.
  final int goal;

  /// Qué cuenta (claves de [Daily]).
  final String dailyKey;
}

abstract final class DailyMission {
  static const tasks = [
    MissionTask('palabras', 'Escucha 3 palabras', '¡Escuchemos tres palabras!', 3, Daily.words),
    MissionTask('oraciones', 'Construye 2 frases', '¡Formemos dos frases!', 2, Daily.sentences),
    MissionTask('verbo', 'Practica un verbo', '¡Practiquemos un verbo!', 1, Daily.verbs),
    MissionTask('cuento', 'Escucha una historia', '¡Escuchemos una historia corta!', 1, Daily.stories),
    MissionTask('charla', 'Charla con Lolo', '¡Charlemos un ratito!', 1, Daily.conversations),
  ];

  /// Lo hecho de una misión (sin pasarse de la meta).
  static int progress(DailyRecord today, MissionTask t) => today.count(t.dailyKey).clamp(0, t.goal);

  static bool done(DailyRecord today, MissionTask t) => today.count(t.dailyKey) >= t.goal;

  static bool skipped(DailyRecord today, MissionTask t) => !done(today, t) && today.skipped.contains(t.id);

  static int doneCount(DailyRecord today) => tasks.where((t) => done(today, t)).length;

  /// Terminada: hizo al menos una y las demás las hizo o las saltó.
  static bool complete(DailyRecord today) =>
      doneCount(today) > 0 && tasks.every((t) => done(today, t) || today.skipped.contains(t.id));

  /// A dónde lleva cada misión (la actividad más adecuada según su progreso).
  static (String, Object?) destination(MissionTask t, SpeechProgress p, SpeechContent c) {
    switch (t.id) {
      case 'palabras':
        final favorite = favoriteWordCategory(p, c);
        final cat = (favorite != null && favorite.words.any((w) => !p.wordsHeard.contains(w.id)))
            ? favorite
            : c.categories.where((x) => x.words.any((w) => !p.wordsHeard.contains(w.id))).firstOrNull ??
                  c.categories.firstOrNull;
        return cat == null
            ? (AppRoutes.speechWordGroups, null)
            : (AppRoutes.speechWords, SpeechWordsArgs(cat.id));
      case 'oraciones':
        return (AppRoutes.speechBuilder, null);
      case 'verbo':
        final verb = c.verbs.where((v) => !p.verbsHeard.contains(v.id)).firstOrNull ?? c.verbs.firstOrNull;
        return verb == null ? (AppRoutes.speechVerbs, null) : (AppRoutes.speechVerb, SpeechVerbArgs(verb.id));
      case 'cuento':
        // Una historia breve: el cuento más corto que aún no ha escuchado.
        final pool = c.stories.where((s) => !p.storiesHeard.contains(s.id)).toList();
        final list = (pool.isEmpty ? c.stories : pool).toList()
          ..sort((a, b) => a.fullText.length.compareTo(b.fullText.length));
        return list.isEmpty
            ? (AppRoutes.speechStories, null)
            : (AppRoutes.speechStory, SpeechStoryArgs(list.first.id));
      default:
        final conv =
            c.conversations.where((x) => !p.conversationsDone.contains(x.id)).firstOrNull ??
            c.conversations.firstOrNull;
        return conv == null
            ? (AppRoutes.speechConversations, null)
            : (AppRoutes.speechConversation, SpeechConversationArgs(conv.id));
    }
  }
}
