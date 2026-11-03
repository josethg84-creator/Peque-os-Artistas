import 'speech_content.dart';

/// «Mi historia» (`assets/speech/mystory.json`): el niño elige personaje,
/// lugar, acción, objeto y final, y la app arma la historia con la gramática
/// española (artículos, «al»/«a la», «lo»/«la», contento/contenta).

/// Un sustantivo con su género («un conejo», «la tortuga»).
class StoryNoun {
  const StoryNoun({
    required this.id,
    required this.noun,
    required this.feminine,
    required this.picture,
    this.kind,
  });

  final String id;
  final String noun;
  final bool feminine;
  final SpeechPicture picture;

  /// En los objetos: «comida», «juguete», «planta», «cosa».
  final String? kind;

  String get indefinite => '${feminine ? 'una' : 'un'} $noun';
  String get definite => '${feminine ? 'la' : 'el'} $noun';

  static StoryNoun? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final id = json['id'], noun = json['noun'], feminine = json['feminine'];
    final picture = SpeechPicture.fromJson(json['picture']);
    if (id is! String || noun is! String || feminine is! bool || picture == null) return null;
    return StoryNoun(
      id: id,
      noun: noun,
      feminine: feminine,
      picture: picture,
      kind: json['kind'] is String ? json['kind'] as String : null,
    );
  }
}

class StoryPlace {
  const StoryPlace({required this.id, required this.noun, required this.feminine, required this.scene});

  final String id;
  final String noun;
  final bool feminine;

  /// Fondo de la escena.
  final String scene;

  /// «al bosque», «a la playa» (a + el = al).
  String get destination => feminine ? 'a la $noun' : 'al $noun';

  SpeechPicture get picture => ScenePicture(scene, const []);

  static StoryPlace? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final id = json['id'], noun = json['noun'], feminine = json['feminine'], scene = json['scene'];
    if (id is! String || noun is! String || feminine is! bool || scene is! String) return null;
    return StoryPlace(id: id, noun: noun, feminine: feminine, scene: scene);
  }
}

class StoryAction {
  const StoryAction({
    required this.id,
    required this.verb,
    required this.prep,
    required this.picture,
    required this.objects,
  });

  final String id;

  /// En infinitivo («buscar»).
  final String verb;

  /// Preposición que pide el verbo («jugar con»); vacía si no hace falta.
  final String prep;
  final SpeechPicture picture;

  /// Tipos de objeto que tienen sentido con esta acción.
  final List<String> objects;

  /// «buscar una zanahoria», «jugar con una pelota».
  String phrase(StoryNoun object) =>
      prep.isEmpty ? '$verb ${object.indefinite}' : '$verb $prep ${object.indefinite}';

  /// La pregunta de Lolo para elegir el objeto.
  String get question => prep.isEmpty ? '¿Qué fue a $verb?' : '¿${_cap(prep)} qué fue a $verb?';

  bool fits(StoryNoun object) => objects.contains(object.kind);

  static StoryAction? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final id = json['id'], verb = json['verb'];
    final picture = SpeechPicture.fromJson(json['picture']);
    final objects = [...(json['objects'] as List? ?? const []).whereType<String>()];
    if (id is! String || verb is! String || picture == null || objects.isEmpty) return null;
    return StoryAction(
      id: id,
      verb: verb,
      prep: json['prep'] is String ? json['prep'] as String : '',
      picture: picture,
      objects: objects,
    );
  }
}

class StoryEnding {
  const StoryEnding({required this.id, required this.template, required this.picture});

  final String id;

  /// Con {el}, {contento} y {lo}.
  final String template;
  final SpeechPicture picture;

  String text(StoryNoun character, StoryNoun object) => _cap(
    template
        .replaceAll('{el}', character.definite)
        .replaceAll('{contento}', character.feminine ? 'contenta' : 'contento')
        .replaceAll('{lo}', object.feminine ? 'la' : 'lo'),
  );

  static StoryEnding? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final id = json['id'], template = json['template'];
    final picture = SpeechPicture.fromJson(json['picture']);
    if (id is! String || template is! String || picture == null) return null;
    return StoryEnding(id: id, template: template, picture: picture);
  }
}

/// Mayúscula en la primera letra (también tras «¡» o «¿»).
String _cap(String s) {
  final i = s.indexOf(RegExp(r'[^¡¿]'));
  if (i < 0) return s;
  return '${s.substring(0, i)}${s[i].toUpperCase()}${s.substring(i + 1)}';
}

/// La historia elegida.
class MyStory {
  const MyStory({
    required this.character,
    required this.place,
    required this.action,
    required this.object,
    required this.ending,
  });

  final StoryNoun character;
  final StoryPlace place;
  final StoryAction action;
  final StoryNoun object;
  final StoryEnding ending;

  /// «Un conejo fue al bosque a buscar una zanahoria.»
  String get firstSentence =>
      _cap('${character.indefinite} fue ${place.destination} a ${action.phrase(object)}.');

  String get lastSentence => ending.text(character, object);

  String get text => '$firstSentence $lastSentence';

  /// La escena: el lugar, el personaje y el objeto.
  SpeechPicture get scene => ScenePicture(place.scene, [
    SceneItem(character.picture, x: 0.36, y: 0.64, size: 0.42),
    SceneItem(object.picture, x: 0.75, y: 0.76, size: 0.22),
  ]);
}

/// Lo que se va diciendo mientras se elige («Un conejo fue al bosque a…»).
String storySoFar({StoryNoun? character, StoryPlace? place, StoryAction? action, StoryNoun? object}) {
  if (character == null) return '';
  final parts = [character.indefinite];
  if (place != null) parts.add('fue ${place.destination}');
  if (action != null) parts.add('a ${action.verb}${action.prep.isEmpty ? '' : ' ${action.prep}'}');
  if (object != null) parts.add(object.indefinite);
  return _cap(parts.join(' ')) + (object == null ? '…' : '.');
}

class MyStoryContent {
  const MyStoryContent({
    this.characters = const [],
    this.places = const [],
    this.actions = const [],
    this.objects = const [],
    this.endings = const [],
  });

  final List<StoryNoun> characters;
  final List<StoryPlace> places;
  final List<StoryAction> actions;
  final List<StoryNoun> objects;
  final List<StoryEnding> endings;

  bool get isEmpty =>
      characters.isEmpty || places.isEmpty || actions.isEmpty || objects.isEmpty || endings.isEmpty;

  /// Los objetos que tienen sentido con la acción.
  List<StoryNoun> objectsFor(StoryAction action) => [
    for (final o in objects)
      if (action.fits(o)) o,
  ];

  factory MyStoryContent.fromJson(Map<String, dynamic>? json) {
    List<T> list<T>(String key, T? Function(Object?) parse) => [
      for (final x in (json?[key] as List? ?? const [])) ?parse(x),
    ];
    final objects = list('objects', StoryNoun.fromJson);
    return MyStoryContent(
      characters: list('characters', StoryNoun.fromJson),
      places: list('places', StoryPlace.fromJson),
      // Solo acciones que tengan algún objeto posible.
      actions: [
        for (final a in list('actions', StoryAction.fromJson))
          if (objects.any(a.fits)) a,
      ],
      objects: objects,
      endings: list('endings', StoryEnding.fromJson),
    );
  }
}
