import 'dart:convert';

import 'package:flutter/material.dart';

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
  });

  static const wordsAsset = 'assets/speech/words.json';
  static const phrasesAsset = 'assets/speech/phrases.json';
  static const verbsAsset = 'assets/speech/verbs.json';
  static const sentencesAsset = 'assets/speech/sentences.json';

  final List<WordCategory> categories;
  final List<SpeechPhrase> phrases;
  final List<SpeechVerb> verbs;
  final SentenceContent sentences;

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
    );
  }

  static SpeechContent parse(
    Map<String, dynamic> words,
    Map<String, dynamic> phrases, {
    Map<String, dynamic>? verbs,
    Map<String, dynamic>? sentences,
  }) {
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
    );
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
  const SpeechWord({required this.id, required this.text, required this.picture, this.article});

  final String id;

  /// Cómo se escribe y se dice («perro», «mamá»).
  final String text;

  /// «el», «la», «los», «las» (para las oraciones de entregas posteriores).
  final String? article;
  final SpeechPicture picture;

  static SpeechWord? fromJson(Map<String, dynamic> json) {
    final id = json['id'], text = json['text'];
    final picture = SpeechPicture.fromJson(json['picture']);
    if (id is! String || text is! String || text.trim().isEmpty || picture == null) return null;
    return SpeechWord(
      id: id,
      text: text.trim(),
      article: json['article'] is String ? json['article'] as String : null,
      picture: picture,
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
      {'drawing': final String id} => DrawingPicture(id, colors: _colorMap(json['colors'])),
      {'emotion': final String e} when FacePictogram.emotions.contains(e) => EmotionPicture(e),
      {'body': final String b} when FacePictogram.bodyParts.contains(b) => BodyPicture(b),
      {'swatch': final Object c} when parseColor(c) != null => SwatchPicture(parseColor(c)!),
      {'icon': final String name} when SpeechIcons.byName.containsKey(name) => IconPicture(
        name,
        parseColor(json['color']),
      ),
      _ => null,
    };
  }
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
  IconData get icon => SpeechIcons.byName[name]!;
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
