import '../navigation/app_routes.dart';
import 'speech_content.dart';
import 'speech_progress.dart';

/// Una sugerencia de Lolo. [reason] explica a los adultos por qué se propone
/// (las reglas son fijas y no usan servicios externos ni inteligencia
/// artificial: con los mismos datos, la misma sugerencia).
class Recommendation {
  const Recommendation({
    required this.id,
    required this.title,
    required this.lolo,
    required this.reason,
    this.route,
    this.args,
  });

  final String id;

  /// Nombre corto de la actividad («Palabras de animales»).
  final String title;

  /// Lo que dice Lolo («¡Hoy podemos aprender nuevas palabras de animales!»).
  final String lolo;

  /// Por qué (para los adultos).
  final String reason;

  /// A dónde lleva (`null` en la sugerencia de descansar).
  final String? route;
  final Object? args;

  @override
  String toString() => id;
}

/// Nombres de las actividades por ruta (para hablar de ellas).
const speechActivityTitles = <String, String>{
  AppRoutes.speechWordGroups: 'Mis primeras palabras',
  AppRoutes.speechWords: 'Mis primeras palabras',
  AppRoutes.speechPhrases: 'Aprendo frases',
  AppRoutes.speechSentences: 'Construyo oraciones',
  AppRoutes.speechBuilder: 'Construye una oración',
  AppRoutes.speechOrder: 'Ordena la oración',
  AppRoutes.speechComplete: 'Completa la oración',
  AppRoutes.speechQuestion: '¿Pregunta o afirmación?',
  AppRoutes.speechVerbs: 'Aprendo los verbos',
  AppRoutes.speechVerbGames: 'Juegos de verbos',
  AppRoutes.speechListen: 'Escucha y señala',
  AppRoutes.speechConversations: 'Hablemos con Lolo',
  AppRoutes.speechStories: 'Lolo me cuenta un cuento',
  AppRoutes.speechExpress: 'Yo puedo expresarme',
  AppRoutes.speechTellList: 'Ahora cuéntamelo tú',
  AppRoutes.speechListening: 'Escucho y respondo',
  AppRoutes.speechListeningLevel: 'Escucho y respondo',
  AppRoutes.speechSounds: 'Sílabas y sonidos',
  AppRoutes.speechClaps: 'Palmas y sílabas',
  AppRoutes.speechSoundGame: 'Sílabas y sonidos',
  AppRoutes.speechWordGames: 'Juegos de palabras',
  AppRoutes.speechWordGame: 'Juegos de palabras',
  AppRoutes.speechMyStory: 'Mi historia',
  AppRoutes.speechMission: 'Mi aventura de hoy',
};

/// Las actividades que más ha abierto (de más a menos; empate: por nombre).
List<String> favoriteActivities(SpeechProgress p, {int max = 3}) {
  final byTitle = <String, int>{};
  for (final MapEntry(:key, :value) in p.visits.entries) {
    final title = speechActivityTitles[key];
    if (title != null && title != 'Mi aventura de hoy') byTitle[title] = (byTitle[title] ?? 0) + value;
  }
  final list = byTitle.entries.toList()
    ..sort((a, b) => b.value != a.value ? b.value.compareTo(a.value) : a.key.compareTo(b.key));
  return [for (final e in list.take(max)) e.key];
}

/// El grupo de palabras que se propone: el favorito que eligió un adulto o,
/// si no hay, el que más ha escuchado (empate: el primero del menú).
WordCategory? favoriteWordCategory(SpeechProgress p, SpeechContent c) {
  for (final cat in c.categories) {
    if (p.preferences.favoriteCategories.contains(cat.id)) return cat;
  }
  WordCategory? best;
  var most = 0;
  for (final cat in c.categories) {
    final n = cat.words.where((w) => p.wordsHeard.contains(w.id)).length;
    if (n > most) {
      most = n;
      best = cat;
    }
  }
  return best;
}

/// El nivel de «Escucho y respondo» que toca: el siguiente al último
/// terminado o, si no hay, el de los ajustes.
int nextListeningLevel(SpeechProgress p) {
  var done = 0;
  for (var l = 1; l <= 3; l++) {
    if (p.activitiesDone.containsKey('escucho_nivel_$l')) done = l;
  }
  return done == 0 ? p.preferences.level : (done + 1).clamp(1, 3);
}

/// Sugerencias de Lolo según el progreso local y los ajustes del adulto.
///
/// Reglas (en este orden):
/// 1. Si ya pasó el tiempo sugerido, proponer un descanso (sin cortar nada).
/// 2. Si ha pedido repetir mucho una actividad, ofrecer más práctica de ella.
/// 3. Palabras nuevas de su grupo favorito (o sus primeras palabras).
/// 4. Oraciones: la primera, otra más o una historia con sus oraciones.
/// 5. El resto (cuentos, escucha, sílabas, conversaciones, verbos, historias)
///    rota según el día, para variar sin azar.
List<Recommendation> recommendActivities(
  SpeechProgress p,
  SpeechContent c, {
  required DateTime now,
  Duration sessionTime = Duration.zero,
  int max = 3,
}) {
  final out = <Recommendation>[];
  final prefs = p.preferences;

  if (sessionTime.inMinutes >= prefs.minutes) {
    out.add(
      Recommendation(
        id: 'descanso',
        title: 'Un descanso',
        lolo: '¡Qué bien lo estamos haciendo! ¿Descansamos un poquito? Luego seguimos.',
        reason: 'Ya pasaron los ${prefs.minutes} minutos sugeridos en los ajustes.',
      ),
    );
  }

  // Más práctica de lo que pide repetir (nunca es un castigo).
  final repeated =
      p.repeats.entries.where((e) => e.value >= 3 && speechActivityTitles.containsKey(e.key)).toList()
        ..sort((a, b) => b.value != a.value ? b.value.compareTo(a.value) : a.key.compareTo(b.key));
  if (repeated.isNotEmpty) {
    final route = repeated.first.key;
    final title = speechActivityTitles[route]!;
    out.add(
      Recommendation(
        id: 'repetir:$route',
        title: title,
        lolo: '¡Vamos a practicar más «$title»! Puedes escuchar todas las veces que quieras.',
        reason: 'Pidió escuchar otra vez ${repeated.first.value} veces en «$title».',
        route: route == AppRoutes.speechWords ? AppRoutes.speechWordGroups : route,
        args: route == AppRoutes.speechListeningLevel ? SpeechListeningArgs(nextListeningLevel(p)) : null,
      ),
    );
  }

  // Palabras.
  final favorite = favoriteWordCategory(p, c);
  if (p.wordsHeard.isEmpty && c.categories.isNotEmpty) {
    final first = favorite ?? c.categories.first;
    out.add(
      Recommendation(
        id: 'palabras:${first.id}',
        title: 'Palabras: ${first.name}',
        lolo: '¡Vamos a escuchar tus primeras palabras!',
        reason: 'Todavía no ha escuchado palabras.',
        route: AppRoutes.speechWords,
        args: SpeechWordsArgs(first.id),
      ),
    );
  } else if (favorite != null) {
    final heard = favorite.words.where((w) => p.wordsHeard.contains(w.id)).length;
    final chosen = prefs.favoriteCategories.contains(favorite.id);
    if (heard < favorite.words.length) {
      out.add(
        Recommendation(
          id: 'palabras:${favorite.id}',
          title: 'Palabras: ${favorite.name}',
          lolo: '¡Hoy podemos aprender nuevas palabras de ${favorite.name.toLowerCase()}!',
          reason: chosen
              ? 'Es un grupo favorito elegido en los ajustes.'
              : 'Es el grupo que más ha practicado ($heard palabras).',
          route: AppRoutes.speechWords,
          args: SpeechWordsArgs(favorite.id),
        ),
      );
    } else {
      out.add(
        Recommendation(
          id: 'juegos_palabras:${favorite.id}',
          title: 'Juegos de palabras',
          lolo: '¡Ya conoces todas las palabras de ${favorite.name.toLowerCase()}! ¿Jugamos con ellas?',
          reason: 'Escuchó todas las palabras de ${favorite.name}.',
          route: AppRoutes.speechWordGames,
        ),
      );
    }
  }

  // Oraciones.
  final built = p.sentencesBuilt.length;
  out.add(switch (built) {
    0 => const Recommendation(
      id: 'oracion:primera',
      title: 'Construye una oración',
      lolo: '¡Vamos a formar tu primera oración!',
      reason: 'Todavía no ha construido oraciones.',
      route: AppRoutes.speechBuilder,
    ),
    < 3 => Recommendation(
      id: 'oracion:otra',
      title: 'Construye una oración',
      lolo: '¡Vamos a formar otra oración!',
      reason: 'Ha construido $built oración(es).',
      route: AppRoutes.speechBuilder,
    ),
    _ => Recommendation(
      id: 'oracion:historia',
      title: 'Mi historia',
      lolo: '¡Vamos a formar una oración más larga e inventar una historia!',
      reason: 'Ya construye oraciones sencillas ($built distintas).',
      route: AppRoutes.speechMyStory,
    ),
  });

  // El resto rota según el día (sin azar: el mismo día, lo mismo).
  final rest = <Recommendation>[];
  final story = c.stories.where((s) => !p.storiesHeard.contains(s.id)).firstOrNull;
  if (story != null) {
    rest.add(
      Recommendation(
        id: 'cuento:${story.id}',
        title: story.title,
        lolo: '¿Escuchamos el cuento «${story.title}»?',
        reason: 'Es el siguiente cuento que aún no ha escuchado.',
        route: AppRoutes.speechStory,
        args: SpeechStoryArgs(story.id),
      ),
    );
  }
  final level = nextListeningLevel(p);
  rest.add(
    Recommendation(
      id: 'escucha:$level',
      title: 'Escucho y respondo · Nivel $level',
      lolo: '¡Juguemos a «Escucho y respondo», nivel $level!',
      reason: p.activitiesDone.keys.any((k) => k.startsWith('escucho_nivel_'))
          ? 'Es el nivel siguiente al último que terminó.'
          : 'Es el nivel elegido en los ajustes.',
      route: AppRoutes.speechListeningLevel,
      args: SpeechListeningArgs(level),
    ),
  );
  rest.add(
    Recommendation(
      id: 'palmas',
      title: 'Palmas y sílabas',
      lolo: '¡Vamos a dar palmas con las sílabas!',
      reason: p.syllablesDone.isEmpty
          ? 'Todavía no ha jugado con sílabas.'
          : 'Para seguir jugando con los sonidos.',
      route: AppRoutes.speechClaps,
      args: SpeechGameArgs('palmas', level: prefs.level),
    ),
  );
  final conversation = c.conversations.where((x) => !p.conversationsDone.contains(x.id)).firstOrNull;
  if (conversation != null) {
    rest.add(
      Recommendation(
        id: 'conversacion:${conversation.id}',
        title: conversation.title,
        lolo: '¿Charlamos? «${conversation.title}».',
        reason: 'Es la siguiente conversación que aún no ha hecho.',
        route: AppRoutes.speechConversation,
        args: SpeechConversationArgs(conversation.id),
      ),
    );
  }
  final verb = c.verbs.where((v) => !p.verbsHeard.contains(v.id)).firstOrNull;
  if (verb != null) {
    rest.add(
      Recommendation(
        id: 'verbo:${verb.id}',
        title: 'El verbo ${verb.infinitive}',
        lolo: '¡Aprendamos el verbo ${verb.infinitive}!',
        reason: 'Es el siguiente verbo que aún no ha practicado.',
        route: AppRoutes.speechVerb,
        args: SpeechVerbArgs(verb.id),
      ),
    );
  }
  final tell = c.tell.where((t) => !p.storiesTold.contains(t.id)).firstOrNull;
  if (tell != null) {
    rest.add(
      Recommendation(
        id: 'cuentamelo:${tell.id}',
        title: tell.title,
        lolo: '¿Me cuentas la historia «${tell.title}»?',
        reason: 'Es la siguiente historia que aún no ha contado.',
        route: AppRoutes.speechTell,
        args: SpeechTellArgs(tell.id),
      ),
    );
  }
  if (rest.isNotEmpty) {
    final shift = _dayNumber(now) % rest.length;
    out.addAll([...rest.skip(shift), ...rest.take(shift)]);
  }

  final seen = <String>{};
  return [
    for (final r in out)
      if (seen.add(r.id)) r,
  ].take(max).toList();
}

int _dayNumber(DateTime d) =>
    DateTime.utc(d.year, d.month, d.day).millisecondsSinceEpoch ~/ Duration.millisecondsPerDay;
