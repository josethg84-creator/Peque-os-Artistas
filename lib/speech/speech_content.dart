import 'dart:convert';

import 'package:flutter/material.dart';

/// Contenido de «Aprendo a Hablar»: palabras por categorías y frases cortas.
///
/// Vive en `assets/speech/*.json`, así que el catálogo se amplía editando esos
/// archivos, sin tocar el código. Lo que no se reconoce (una categoría sin
/// palabras, un dibujo desconocido…) se descarta sin romper la pantalla.
class SpeechContent {
  const SpeechContent({required this.categories, required this.phrases});

  static const wordsAsset = 'assets/speech/words.json';
  static const phrasesAsset = 'assets/speech/phrases.json';

  final List<WordCategory> categories;
  final List<SpeechPhrase> phrases;

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
    return parse(await read(wordsAsset), await read(phrasesAsset));
  }

  static SpeechContent parse(Map<String, dynamic> words, Map<String, dynamic> phrases) {
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
    return SpeechContent(categories: categories, phrases: phraseList);
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
  };
}

Color? parseColor(Object? value) {
  if (value is! String) return null;
  final hex = value.replaceFirst('#', '');
  if (!RegExp(r'^[0-9a-fA-F]{6}$').hasMatch(hex)) return null;
  return Color(0xFF000000 | int.parse(hex, radix: 16));
}
