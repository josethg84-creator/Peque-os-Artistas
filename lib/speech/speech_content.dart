import 'dart:convert';

import 'package:flutter/material.dart';

import 'dialogue.dart';
import 'expressions.dart';
import 'stories.dart';
import 'listening.dart';
import 'my_story.dart';
import 'phonology.dart';
import 'speech_icons_extra.dart';
import 'tell.dart';

export 'dialogue.dart';
export 'expressions.dart';
export 'stories.dart';
export 'listening.dart';
export 'my_story.dart';
export 'phonology.dart';
export 'tell.dart';

/// Contenido de «Aprendo a Hablar»: palabras por categorías y frases cortas.
///
/// Vive en `assets/speech/*.json`, así que el catálogo se amplía editando esos
/// archivos, sin tocar el código. Lo que no se reconoce (una categoría sin
/// palabras, un dibujo desconocido…) se descarta sin romper la pantalla.
class SpeechContent {
  const SpeechContent({
    required this.categories,
    required this.phrases,
    this.verbs = const [],
    this.sentences = const SentenceContent(),
    this.conversationCategories = const [],
    this.conversations = const [],
    this.stories = const [],
    this.expressions = const ExpressionContent(),
    this.tell = const [],
    this.listening = const ListeningContent(),
    this.phonology = const PhonologyContent(),
    this.myStory = const MyStoryContent(),
  });

  static const wordsAsset = 'assets/speech/words.json';
  static const phrasesAsset = 'assets/speech/phrases.json';
  static const verbsAsset = 'assets/speech/verbs.json';
  static const sentencesAsset = 'assets/speech/sentences.json';
  static const conversationsAsset = 'assets/speech/conversations.json';
  static const storiesAsset = 'assets/speech/stories.json';
  static const expressionsAsset = 'assets/speech/expressions.json';
  static const tellAsset = 'assets/speech/tell.json';
  static const listeningAsset = 'assets/speech/listening.json';
  static const vocabularyAsset = 'assets/speech/vocabulary.json';
  static const phonologyAsset = 'assets/speech/phonology.json';
  static const myStoryAsset = 'assets/speech/mystory.json';

  final List<WordCategory> categories;
  final List<SpeechPhrase> phrases;
  final List<SpeechVerb> verbs;
  final SentenceContent sentences;

  /// «Hablemos con Lolo».
  final List<ConversationCategory> conversationCategories;
  final List<Conversation> conversations;

  /// «Lolo me cuenta un cuento».
  final List<Story> stories;

  /// «Yo puedo expresarme».
  final ExpressionContent expressions;

  /// «Ahora cuéntamelo tú».
  final List<TellSequence> tell;

  /// «Escucho y respondo».
  final ListeningContent listening;

  /// «Sílabas y sonidos».
  final PhonologyContent phonology;

  /// «Mi historia».
  final MyStoryContent myStory;

  List<SpeechWord> get words => [for (final c in categories) ...c.words];

  SpeechWord? word(String id) {
    for (final c in categories) {
      for (final w in c.words) {
        if (w.id == id) return w;
      }
    }
    return null;
  }

  static Future<SpeechContent> load(AssetBundle bundle) async {
    // Se decodifica aquí (no con loadString) para no depender de un isolate.
    Future<Map<String, dynamic>> read(String key) async =>
        jsonDecode(utf8.decode((await bundle.load(key)).buffer.asUint8List())) as Map<String, dynamic>;
    return parse(
      await read(wordsAsset),
      await read(phrasesAsset),
      verbs: await read(verbsAsset),
      sentences: await read(sentencesAsset),
      conversations: await read(conversationsAsset),
      stories: await read(storiesAsset),
      expressions: await read(expressionsAsset),
      tell: await read(tellAsset),
      listening: await read(listeningAsset),
      vocabulary: await read(vocabularyAsset),
      phonology: await read(phonologyAsset),
      myStory: await read(myStoryAsset),
    );
  }

  static SpeechContent parse(
    Map<String, dynamic> words,
    Map<String, dynamic> phrases, {
    Map<String, dynamic>? verbs,
    Map<String, dynamic>? sentences,
    Map<String, dynamic>? conversations,
    Map<String, dynamic>? stories,
    Map<String, dynamic>? expressions,
    Map<String, dynamic>? tell,
    Map<String, dynamic>? listening,
    Map<String, dynamic>? vocabulary,
    Map<String, dynamic>? phonology,
    Map<String, dynamic>? myStory,
  }) {
    final dialogue = parseConversations(conversations);
    final seen = <String>{};
    final categories = <WordCategory>[];
    for (final c in (words['categories'] as List? ?? const [])) {
      if (c is! Map<String, dynamic>) continue;
      final list = <SpeechWord>[];
      for (final w in (c['words'] as List? ?? const [])) {
        final word = w is Map<String, dynamic> ? SpeechWord.fromJson(w) : null;
        if (word != null && seen.add(word.id)) list.add(word);
      }
      final category = WordCategory.fromJson(c, list);
      if (category != null) categories.add(category);
    }
    if (vocabulary != null) _mergeVocabulary(categories, seen, vocabulary);
    final phraseList = <SpeechPhrase>[];
    final phraseIds = <String>{};
    for (final p in (phrases['phrases'] as List? ?? const [])) {
      final phrase = p is Map<String, dynamic> ? SpeechPhrase.fromJson(p) : null;
      if (phrase != null && phraseIds.add(phrase.id)) phraseList.add(phrase);
    }
    final verbIds = <String>{};
    return SpeechContent(
      categories: categories,
      phrases: phraseList,
      verbs: [
        for (final v in (verbs?['verbs'] as List? ?? const []))
          if (v is Map<String, dynamic>)
            if (SpeechVerb.fromJson(v) case final verb? when verbIds.add(verb.id)) verb,
      ],
      sentences: sentences == null ? const SentenceContent() : SentenceContent.fromJson(sentences),
      conversationCategories: dialogue.categories,
      conversations: dialogue.conversations,
      stories: parseStories(stories),
      expressions: ExpressionContent.fromJson(expressions),
      tell: parseTell(tell),
      listening: ListeningContent.fromJson(listening),
      phonology: PhonologyContent.fromJson(phonology),
      myStory: MyStoryContent.fromJson(myStory),
    );
  }
}

/// Fase 4: añade el banco de vocabulario a los grupos (y crea los grupos
/// nuevos). Las palabras repetidas o mal escritas se descartan.
void _mergeVocabulary(List<WordCategory> categories, Set<String> seen, Map<String, dynamic> json) {
  final pronunciation = json['pronunciation'];
  if (pronunciation is Map<String, dynamic>) {
    for (final (i, c) in categories.indexed) {
      categories[i] = WordCategory(
        id: c.id,
        name: c.name,
        color: c.color,
        icon: c.icon,
        words: [
          for (final w in c.words)
            if (pronunciation[w.id] case final String p when p.replaceAll('-', '') == w.text.toLowerCase())
              w.copyWith(pronunciation: p)
            else
              w,
        ],
      );
    }
  }
  final byCategory = <String, List<SpeechWord>>{};
  for (final w in (json['words'] as List? ?? const [])) {
    if (w is! Map<String, dynamic> || w['category'] is! String) continue;
    final word = SpeechWord.fromJson(w);
    if (word != null && seen.add(word.id)) (byCategory[w['category'] as String] ??= []).add(word);
  }
  for (final (i, c) in categories.indexed) {
    final more = byCategory.remove(c.id);
    if (more != null) {
      categories[i] = WordCategory(
        id: c.id,
        name: c.name,
        color: c.color,
        icon: c.icon,
        words: [...c.words, ...more],
      );
    }
  }
  for (final c in (json['categories'] as List? ?? const [])) {
    if (c is! Map<String, dynamic>) continue;
    final more = byCategory.remove(c['id']);
    if (more == null) continue;
    final category = WordCategory.fromJson(c, more);
    if (category != null) categories.add(category);
  }
}

/// Las personas de la conjugación, en orden.
enum VerbPerson {
  yo('Yo', 'me'),
  tu('Tú', 'you'),
  el('Él', 'he'),
  ella('Ella', 'she'),
  nosotros('Nosotros', 'we');

  const VerbPerson(this.label, this.icon);
  final String label;

  /// Pictograma de [SpeechIcons].
  final String icon;
}

/// Un verbo con su presente (yo, tú, él/ella, nosotros) y un complemento para
/// formar oraciones de ejemplo («Yo como una manzana»).
class SpeechVerb {
  const SpeechVerb({
    required this.id,
    required this.infinitive,
    required this.picture,
    required this.present,
    required this.gerund,
    required this.complement,
  });

  final String id;
  final String infinitive;
  final SpeechPicture picture;

  /// Formas del presente: `yo`, `tu`, `el` (también para «ella») y `nosotros`.
  final Map<String, String> present;

  /// «comiendo» (para «¿Quién está comiendo?»).
  final String gerund;
  final String complement;

  String form(VerbPerson p) =>
      present[switch (p) {
        VerbPerson.yo => 'yo',
        VerbPerson.tu => 'tu',
        VerbPerson.el || VerbPerson.ella => 'el',
        VerbPerson.nosotros => 'nosotros',
      }]!;

  /// «Yo como una manzana.»
  String sentence(VerbPerson p) => '${p.label} ${form(p)} $complement.';

  static SpeechVerb? fromJson(Map<String, dynamic> json) {
    final id = json['id'], inf = json['infinitive'], ger = json['gerund'];
    final picture = SpeechPicture.fromJson(json['picture']);
    final present = json['present'];
    if (id is! String || inf is! String || ger is! String || picture == null || present is! Map) return null;
    final forms = {
      for (final k in const ['yo', 'tu', 'el', 'nosotros'])
        if (present[k] case final String f) k: f,
    };
    if (forms.length != 4) return null;
    return SpeechVerb(
      id: id,
      infinitive: inf,
      picture: picture,
      present: forms,
      gerund: ger,
      complement: json['complement'] is String ? json['complement'] as String : '',
    );
  }
}

/// Un trozo de oración con su ilustración (un sujeto o un complemento).
class SentencePiece {
  const SentencePiece({required this.id, required this.text, required this.picture});
  final String id;
  final String text;
  final SpeechPicture picture;

  static SentencePiece? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final id = json['id'] ?? json['text'], text = json['text'];
    final picture = SpeechPicture.fromJson(json['picture']);
    if (id is! String || text is! String || picture == null) return null;
    return SentencePiece(id: id, text: text, picture: picture);
  }
}

/// Una acción del constructor: el verbo conjugado («come») y sus complementos.
class SentenceAction {
  const SentenceAction({required this.verbId, required this.text, required this.complements});
  final String verbId;
  final String text;
  final List<SentencePiece> complements;
}

/// Una oración para ordenar, con su ilustración.
class OrderSentence {
  const OrderSentence({required this.text, required this.picture});
  final String text;
  final SpeechPicture picture;

  List<String> get words => SpeechPhrase(id: text, text: text, picture: picture).words;
}

/// «El niño come una ___»: la palabra que falta y las opciones con dibujo.
class CompleteItem {
  const CompleteItem({
    required this.before,
    required this.answer,
    required this.after,
    required this.options,
  });
  final String before;
  final String answer;
  final String after;
  final List<SentencePiece> options;

  String get full => '$before $answer$after';
}

/// Contenido de «Construyo oraciones».
class SentenceContent {
  const SentenceContent({
    this.subjects = const [],
    this.actions = const [],
    this.order = const [],
    this.complete = const [],
  });

  final List<SentencePiece> subjects;
  final List<SentenceAction> actions;
  final List<OrderSentence> order;
  final List<CompleteItem> complete;

  static SentenceContent fromJson(Map<String, dynamic> json) {
    List<Map<String, dynamic>> list(Object? v) => [
      ...(v as List? ?? const []).whereType<Map<String, dynamic>>(),
    ];
    return SentenceContent(
      subjects: [for (final s in list(json['subjects'])) ?SentencePiece.fromJson(s)],
      actions: [
        for (final a in list(json['actions']))
          if (a['verb'] case final String verb)
            if (a['text'] case final String text)
              SentenceAction(
                verbId: verb,
                text: text,
                complements: [for (final c in list(a['complements'])) ?SentencePiece.fromJson(c)],
              ),
      ],
      order: [
        for (final o in list(json['order']))
          if (o['text'] case final String text)
            if (SpeechPicture.fromJson(o['picture']) case final picture?)
              OrderSentence(text: text, picture: picture),
      ],
      complete: [
        for (final c in list(json['complete']))
          if ((c['before'], c['answer']) case (final String before, final String answer))
            CompleteItem(
              before: before,
              answer: answer,
              after: c['after'] is String ? c['after'] as String : '',
              options: [for (final o in list(c['options'])) ?SentencePiece.fromJson(o)],
            ),
      ],
    );
  }
}

class WordCategory {
  const WordCategory({
    required this.id,
    required this.name,
    required this.color,
    required this.icon,
    required this.words,
  });

  final String id;
  final String name;
  final Color color;

  /// Nombre de un icono de [SpeechIcons].
  final String icon;
  final List<SpeechWord> words;

  static WordCategory? fromJson(Map<String, dynamic> json, List<SpeechWord> words) {
    final id = json['id'], name = json['name'];
    if (id is! String || name is! String || words.isEmpty) return null;
    return WordCategory(
      id: id,
      name: name,
      color: parseColor(json['color']) ?? const Color(0xFF9B7BEA),
      icon: json['icon'] is String ? json['icon'] as String : 'star',
      words: words,
    );
  }
}

class SpeechWord {
  const SpeechWord({
    required this.id,
    required this.text,
    required this.picture,
    this.article,
    this.pronunciation,
    this.example,
    this.level = 1,
  });

  final String id;

  /// Cómo se escribe y se dice («perro», «mamá»).
  final String text;

  /// «el», «la», «los», «las» (para las oraciones de entregas posteriores).
  final String? article;
  final SpeechPicture picture;

  /// Fase 4: cómo se pronuncia, por sílabas («ma-ri-po-sa»).
  final String? pronunciation;

  /// Una frase de ejemplo con la palabra («La jirafa tiene el cuello largo.»).
  final String? example;

  /// Nivel orientativo (1 a 3).
  final int level;

  /// Las sílabas («ma», «ri», «po», «sa»), si se conocen.
  List<String> get syllables => [
    for (final s in (pronunciation ?? '').split(RegExp(r'[-\s]+')))
      if (s.isNotEmpty) s,
  ];

  /// La palabra con su artículo («la jirafa»).
  String get withArticle => article == null ? text : '$article $text';

  SpeechWord copyWith({String? pronunciation}) => SpeechWord(
    id: id,
    text: text,
    picture: picture,
    article: article,
    pronunciation: pronunciation ?? this.pronunciation,
    example: example,
    level: level,
  );

  static SpeechWord? fromJson(Map<String, dynamic> json) {
    final id = json['id'], text = json['text'];
    final picture = SpeechPicture.fromJson(json['picture']);
    if (id is! String || text is! String || text.trim().isEmpty || picture == null) return null;
    final pronunciation = json['pronunciation'];
    final level = json['level'];
    return SpeechWord(
      id: id,
      text: text.trim(),
      article: json['article'] is String ? json['article'] as String : null,
      picture: picture,
      // La pronunciación debe corresponder a la palabra (sin guiones).
      pronunciation: pronunciation is String && pronunciation.replaceAll('-', '') == text.trim().toLowerCase()
          ? pronunciation
          : null,
      example: json['example'] is String ? json['example'] as String : null,
      level: level is int && level >= 1 && level <= 3 ? level : 1,
    );
  }
}

class SpeechPhrase {
  const SpeechPhrase({required this.id, required this.text, required this.picture});

  final String id;

  /// La frase con su puntuación («Hola, ¿cómo estás?»).
  final String text;
  final SpeechPicture picture;

  /// Palabras sueltas, sin signos de puntuación («Hola», «cómo», «estás»).
  List<String> get words => [
    for (final w in text.split(RegExp(r'\s+')))
      if (w.replaceAll(_punctuation, '').isNotEmpty) w.replaceAll(_punctuation, ''),
  ];

  static final _punctuation = RegExp(r'[.,;:¿?¡!«»"]');

  static SpeechPhrase? fromJson(Map<String, dynamic> json) {
    final id = json['id'], text = json['text'];
    final picture = SpeechPicture.fromJson(json['picture']);
    if (id is! String || text is! String || text.trim().isEmpty || picture == null) return null;
    return SpeechPhrase(id: id, text: text.trim(), picture: picture);
  }
}

/// Qué ilustración acompaña a una palabra o frase.
sealed class SpeechPicture {
  const SpeechPicture();

  static SpeechPicture? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    return switch (json) {
      {'image': final String path} => ImagePicture(path),
      {'lolo': true} => const LoloPicture(),
      {'kid': final Map<String, dynamic> k} => KidPicture(
        girl: k['girl'] == true,
        shirt: parseColor(k['shirt']) ?? const Color(0xFF64B5F6),
        hair: parseColor(k['hair']) ?? const Color(0xFF7B4A2E),
        emotion: k['emotion'] is String ? k['emotion'] as String : 'feliz',
        armsUp: k['arms_up'] == true,
      ),
      {'scene': final String bg} => ScenePicture(bg, [
        for (final item in (json['items'] as List? ?? const []))
          if (item is Map<String, dynamic>)
            if (SpeechPicture.fromJson(item['p']) case final p?)
              SceneItem(
                p,
                x: (item['x'] as num?)?.toDouble() ?? 0.5,
                y: (item['y'] as num?)?.toDouble() ?? 0.6,
                size: (item['s'] as num?)?.toDouble() ?? 0.4,
              ),
      ]),
      {'drawing': final String id} => DrawingPicture(id, colors: _colorMap(json['colors'])),
      {'emotion': final String e} when FacePictogram.emotions.contains(e) => EmotionPicture(e),
      {'body': final String b} when FacePictogram.bodyParts.contains(b) => BodyPicture(b),
      {'swatch': final Object c} when parseColor(c) != null => SwatchPicture(parseColor(c)!),
      {'icon': final String name} when SpeechIcons.lookup(name) != null => IconPicture(
        name,
        parseColor(json['color']),
      ),
      _ => null,
    };
  }
}

/// Lolo, la mascota.
class LoloPicture extends SpeechPicture {
  const LoloPicture();
}

/// Un niño o una niña con una emoción (personaje de cuentos y conversaciones).
class KidPicture extends SpeechPicture {
  const KidPicture({
    this.girl = false,
    this.shirt = const Color(0xFF64B5F6),
    this.hair = const Color(0xFF7B4A2E),
    this.emotion = 'feliz',
    this.armsUp = false,
  });
  final bool girl;
  final Color shirt;
  final Color hair;
  final String emotion;
  final bool armsUp;
}

/// Un elemento colocado en una escena: [x] e [y] son el centro y [size] el
/// ancho, en fracciones de la escena.
class SceneItem {
  const SceneItem(this.picture, {this.x = 0.5, this.y = 0.6, this.size = 0.4});
  final SpeechPicture picture;
  final double x;
  final double y;
  final double size;
}

/// Una escena ilustrada: un fondo (jardín, casa, noche…) y personajes u
/// objetos encima. Cada escena es una ilustración independiente y vectorial.
class ScenePicture extends SpeechPicture {
  const ScenePicture(this.background, this.items);
  final String background;
  final List<SceneItem> items;
}

/// Imagen propia (PNG o similar) incluida en los recursos de la app.
class ImagePicture extends SpeechPicture {
  const ImagePicture(this.path);
  final String path;
}

Map<String, Color> _colorMap(Object? json) => {
  if (json is Map<String, dynamic>)
    for (final MapEntry(:key, :value) in json.entries) key: ?parseColor(value),
};

/// Un dibujo del catálogo de colorear, pintado con colores alegres. [colors]
/// fija el color real de algunas zonas (la manzana roja, el plátano amarillo);
/// una clave terminada en `*` vale para todas las zonas que empiezan así
/// (`uva_*`). Las demás zonas reciben colores alegres automáticos.
class DrawingPicture extends SpeechPicture {
  const DrawingPicture(this.drawingId, {this.colors = const {}});
  final String drawingId;
  final Map<String, Color> colors;

  Color? colorFor(String regionId) {
    final exact = colors[regionId];
    if (exact != null) return exact;
    for (final MapEntry(:key, :value) in colors.entries) {
      if (key.endsWith('*') && regionId.startsWith(key.substring(0, key.length - 1))) return value;
    }
    return null;
  }
}

/// Una carita con una emoción.
class EmotionPicture extends SpeechPicture {
  const EmotionPicture(this.emotion);
  final String emotion;
}

/// Un niño con una parte del cuerpo resaltada.
class BodyPicture extends SpeechPicture {
  const BodyPicture(this.part);
  final String part;
}

/// Una mancha de pintura de un color.
class SwatchPicture extends SpeechPicture {
  const SwatchPicture(this.color);
  final Color color;
}

/// Un pictograma sobre una baldosa de color.
class IconPicture extends SpeechPicture {
  const IconPicture(this.name, this.color);
  final String name;
  final Color? color;
  IconData get icon => SpeechIcons.lookup(name)!;
}

/// Nombres de emociones y partes del cuerpo que saben dibujar los pictogramas.
abstract final class FacePictogram {
  static const emotions = {
    'feliz',
    'triste',
    'enojado',
    'asustado',
    'sorprendido',
    'cansado',
    'tranquilo',
    'aburrido',
    'enfermo',
    'carinoso',
    'emocionado',
  };
  static const bodyParts = {
    'cabeza',
    'pelo',
    'ojos',
    'nariz',
    'boca',
    'orejas',
    'brazos',
    'manos',
    'piernas',
    'pies',
  };
}

/// Iconos que se pueden nombrar desde el JSON (los de Material, que vienen con
/// la app y funcionan sin conexión).
abstract final class SpeechIcons {
  /// Un icono por su nombre corto o por su nombre de Material (los del banco
  /// de vocabulario, en [extraSpeechIcons]).
  static IconData? lookup(String name) => byName[name] ?? extraSpeechIcons[name];

  static const byName = <String, IconData>{
    'family': Icons.family_restroom,
    'pets': Icons.pets,
    'food': Icons.restaurant,
    'toys': Icons.toys,
    'body': Icons.accessibility_new,
    'palette': Icons.palette,
    'home': Icons.home,
    'actions': Icons.directions_run,
    'emotions': Icons.emoji_emotions,
    'nature': Icons.park,
    'star': Icons.star,
    'woman': Icons.woman,
    'man': Icons.man,
    'child_care': Icons.child_care,
    'boy': Icons.boy,
    'girl': Icons.girl,
    'elderly': Icons.elderly,
    'elderly_woman': Icons.elderly_woman,
    'friends': Icons.diversity_3,
    'teacher': Icons.cast_for_education,
    'bread': Icons.bakery_dining,
    'egg': Icons.egg,
    'icecream': Icons.icecream,
    'cake': Icons.cake,
    'water': Icons.water_drop,
    'ball': Icons.sports_soccer,
    'robot': Icons.smart_toy,
    'puzzle': Icons.extension,
    'bike': Icons.pedal_bike,
    'skateboard': Icons.skateboarding,
    'bed': Icons.bed,
    'chair': Icons.chair,
    'table': Icons.table_restaurant,
    'door': Icons.door_front_door,
    'window': Icons.window,
    'lamp': Icons.lightbulb,
    'book': Icons.menu_book,
    'clock': Icons.schedule,
    'glass': Icons.local_drink,
    'eat': Icons.restaurant,
    'drink': Icons.emoji_food_beverage,
    'sleep': Icons.bedtime,
    'run': Icons.directions_run,
    'walk': Icons.directions_walk,
    'swim': Icons.pool,
    'play': Icons.toys,
    'paint': Icons.brush,
    'read': Icons.auto_stories,
    'sing': Icons.mic,
    'sun': Icons.wb_sunny,
    'moon': Icons.nightlight_round,
    'cloud': Icons.cloud,
    'flower': Icons.local_florist,
    'tree': Icons.park,
    'mountain': Icons.landscape,
    'sea': Icons.waves,
    'snow': Icons.ac_unit,
    'fire': Icons.local_fire_department,
    'help': Icons.volunteer_activism,
    'hurt': Icons.healing,
    'love': Icons.favorite,
    'wave': Icons.waving_hand,
    // Verbos.
    'jump': Icons.sports_gymnastics,
    'dance': Icons.music_note,
    'look': Icons.visibility,
    'talk': Icons.record_voice_over,
    'open': Icons.meeting_room,
    'close': Icons.door_front_door,
    // Fase 3.
    'thumb_up': Icons.thumb_up,
    'school': Icons.school,
    'blocks': Icons.widgets,
    'soup': Icons.soup_kitchen,
    'pizza': Icons.local_pizza,
    'salad': Icons.eco,
    'gift': Icons.card_giftcard,
    'rest': Icons.weekend,
    'wash': Icons.wash,
    'bath': Icons.bathtub,
    'towel': Icons.dry,
    'toilet': Icons.wc,
    'jacket': Icons.checkroom,
    'hot': Icons.thermostat,
    'shirt': Icons.checkroom,
    'dress': Icons.checkroom,
    'shoes': Icons.do_not_step,
    'idea': Icons.lightbulb,
    'pencil': Icons.edit,
    'abc': Icons.abc,
    'numbers': Icons.pin,
    'search': Icons.search,
    'circle': Icons.circle,
    'square': Icons.square,
    'zoom_in': Icons.zoom_in,
    'zoom_out': Icons.zoom_out,
    'seed': Icons.grain,
    'plant': Icons.spa,
    'sprout': Icons.grass,
    'watering': Icons.water_drop,
    'umbrella': Icons.umbrella,
    'tooth': Icons.clean_hands,
    'bus': Icons.directions_bus,
    'shop': Icons.storefront,
    'money': Icons.savings,
    'phone': Icons.phone,
    'heart': Icons.favorite,
    'map': Icons.map,
    'camera': Icons.photo_camera,
    'bird': Icons.flutter_dash,
    'bug': Icons.bug_report,
    'music': Icons.music_note,
    'home2': Icons.house,
    'tent': Icons.cabin,
    'boat': Icons.sailing,
    'key': Icons.key,
    'lock': Icons.lock,
    'mail': Icons.mail,
    'sleepz': Icons.snooze,
    'clean': Icons.cleaning_services,
    'trash': Icons.delete,
    'recycle': Icons.recycling,
    'hospital': Icons.local_hospital,
    'doctor': Icons.medical_services,
    'cookie': Icons.cookie,
    'juice': Icons.local_bar,
    'milk': Icons.water_drop,
    'carrot': Icons.eco,
    'fish': Icons.set_meal,
    'apple': Icons.apple,
    'sandwich': Icons.lunch_dining,
    'spoon': Icons.restaurant,
    'paint2': Icons.palette,
    'glasses': Icons.visibility,
    'light': Icons.light_mode,
    'dark': Icons.dark_mode,
    'rain': Icons.thunderstorm,
    'wind': Icons.air,
    'leaf': Icons.eco,
    'sad': Icons.sentiment_dissatisfied,
    'happy': Icons.sentiment_satisfied,
    'arrow': Icons.arrow_forward,
    'place': Icons.place,
    'first': Icons.looks_one,
    'second': Icons.looks_two,
    'third': Icons.looks_3,
    'fourth': Icons.looks_4,
    'rainbow': Icons.looks,
    'hearing': Icons.hearing,
    'tv': Icons.tv,
    'backpack': Icons.backpack,
    // Personas (yo, tú, él, ella, nosotros).
    'me': Icons.emoji_people,
    'you': Icons.person,
    'he': Icons.boy,
    'she': Icons.girl,
    'we': Icons.groups,
  };
}

Color? parseColor(Object? value) {
  if (value is! String) return null;
  final hex = value.replaceFirst('#', '');
  if (!RegExp(r'^[0-9a-fA-F]{6}$').hasMatch(hex)) return null;
  return Color(0xFF000000 | int.parse(hex, radix: 16));
}
