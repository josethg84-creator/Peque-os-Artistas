import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter/material.dart';

import '../speech/speech_content.dart';

/// Contenido real de «Aprendo a leer» (`assets/reading/syllables.json`, generado
/// y validado por `tools/reading/syllables.py`). Solo datos: las pantallas y
/// los juegos lo leen de aquí.

/// Dónde está el sonido de algo: una grabación validada (si la hay) y el texto
/// que dice la voz del dispositivo si no.
class ReadingAudio {
  const ReadingAudio({this.clip, required this.tts});

  /// Ruta del archivo grabado, o `null` si aún no se ha grabado.
  final String? clip;

  /// Texto para la voz del dispositivo (en minúsculas: «ma», nunca «MA»).
  final String tts;

  bool get recorded => clip != null;

  static ReadingAudio? fromJson(Object? json) {
    if (json is! Map<String, dynamic> || json['tts'] is! String) return null;
    return ReadingAudio(
      clip: json['clip'] is String ? json['clip'] as String : null,
      tts: json['tts'] as String,
    );
  }
}

class ReadingLevel {
  const ReadingLevel({required this.id, required this.name, required this.description, required this.locked});
  final int id;
  final String name;
  final String description;

  /// Aún no disponible (llegará en fases siguientes).
  final bool locked;
}

class SyllableFamily {
  const SyllableFamily({
    required this.id,
    required this.letter,
    required this.color,
    required this.level,
    required this.syllableIds,
    this.letterName,
    this.letterAudio,
  });

  final String id;

  /// Lo que se ve en el selector («M», «A E I O U», «C · Q»).
  final String letter;
  final Color color;
  final int level;
  final List<String> syllableIds;

  /// Nombre de la letra («eme»), si es una consonante.
  final String? letterName;
  final ReadingAudio? letterAudio;

  bool get isVowels => id == 'vocales';
}

class ReadingSyllable {
  const ReadingSyllable({
    required this.id,
    required this.text,
    required this.familyId,
    required this.level,
    required this.audio,
    required this.wordId,
    this.speeds = const ['normal', 'lenta'],
  });

  final String id;
  final String text;
  final String familyId;
  final int level;
  final ReadingAudio audio;
  final List<String> speeds;
  final String wordId;
}

class ReadingWord {
  const ReadingWord({
    required this.id,
    required this.text,
    required this.syllables,
    required this.level,
    required this.audio,
    required this.image,
    this.picture,
    this.imageReady = false,
    this.note,
    this.category,
  });

  final String id;
  final String text;
  final List<String> syllables;
  final int level;
  final ReadingAudio audio;

  /// Dibujo o icono de la app que la representa sin ambigüedad (si lo hay).
  final SpeechPicture? picture;

  /// Ruta de su ilustración 3D definitiva y si ya existe.
  final String image;
  final bool imageReady;

  /// Aclaración para el adulto (p. ej., diptongos).
  final String? note;

  /// Categoría («animales», «comida»…), si la tiene.
  final String? category;

  static ReadingWord? fromJson(Map<String, dynamic> w) {
    if ((w['id'], w['text'], w['image'], ReadingAudio.fromJson(w['audio'])) case (
      final String id,
      final String text,
      final String image,
      final ReadingAudio audio,
    )) {
      return ReadingWord(
        id: id,
        text: text,
        syllables: [...(w['syllables'] as List? ?? const []).whereType<String>()],
        level: w['level'] is int ? w['level'] as int : 2,
        audio: audio,
        image: image,
        imageReady: w['image_ready'] == true,
        picture: SpeechPicture.fromJson(w['picture']),
        note: w['note'] is String ? w['note'] as String : null,
        category: w['category'] is String ? w['category'] as String : null,
      );
    }
    return null;
  }

  /// Tiene una imagen que la representa: se puede usar en juegos de imagen.
  bool get hasPicture => imageReady || picture != null;
}

class ReadingContent {
  ReadingContent({
    required this.levels,
    required this.families,
    required List<ReadingSyllable> syllables,
    required List<ReadingWord> words,
  }) : syllables = {for (final s in syllables) s.id: s},
       words = {for (final w in words) w.id: w};

  final List<ReadingLevel> levels;
  final List<SyllableFamily> families;
  final Map<String, ReadingSyllable> syllables;
  final Map<String, ReadingWord> words;

  static const path = 'assets/reading/syllables.json';

  List<ReadingSyllable> syllablesOf(SyllableFamily f) => [for (final id in f.syllableIds) ?syllables[id]];

  ReadingWord? wordOf(ReadingSyllable s) => words[s.wordId];
  SyllableFamily? familyOf(ReadingSyllable s) => families.where((f) => f.id == s.familyId).firstOrNull;

  static ReadingContent parse(Map<String, dynamic> json) {
    List<Map<String, dynamic>> list(String key) => [
      for (final x in (json[key] as List? ?? const []))
        if (x is Map<String, dynamic>) x,
    ];
    return ReadingContent(
      levels: [
        for (final l in list('levels'))
          if (l['id'] is int && l['name'] is String)
            ReadingLevel(
              id: l['id'] as int,
              name: l['name'] as String,
              description: l['description'] is String ? l['description'] as String : '',
              locked: l['locked'] == true,
            ),
      ],
      families: [
        for (final f in list('families'))
          if (f['id'] is String && f['letter'] is String)
            SyllableFamily(
              id: f['id'] as String,
              letter: f['letter'] as String,
              color: parseColor(f['color']) ?? const Color(0xFF8FCBFF),
              level: f['level'] is int ? f['level'] as int : 1,
              syllableIds: [...(f['syllables'] as List? ?? const []).whereType<String>()],
              letterName: f['letter_name'] is String ? f['letter_name'] as String : null,
              letterAudio: ReadingAudio.fromJson(f['letter_audio']),
            ),
      ],
      syllables: [
        for (final s in list('syllables'))
          if ((s['id'], s['text'], s['family'], s['word'], ReadingAudio.fromJson(s['audio'])) case (
            final String id,
            final String text,
            final String family,
            final String word,
            final ReadingAudio audio,
          ))
            ReadingSyllable(
              id: id,
              text: text,
              familyId: family,
              level: s['level'] is int ? s['level'] as int : 1,
              audio: audio,
              wordId: word,
              speeds: [
                ...(s['speeds'] as List? ?? const ['normal', 'lenta']).whereType<String>(),
              ],
            ),
      ],
      words: [for (final w in list('words')) ?ReadingWord.fromJson(w)],
    );
  }

  /// Contenido ya cargado, por paquete de recursos. Se guarda el resultado
  /// (no la carga en curso) para que una carga a medias no se quede colgada.
  static final _cache = Expando<ReadingContent>();

  /// Carga el contenido (una sola vez por paquete de recursos).
  static Future<ReadingContent> load(AssetBundle bundle) async {
    final cached = _cache[bundle];
    if (cached != null) return cached;
    // Se decodifica aquí (no con loadString, que usa otro isolate con archivos
    // grandes), como el contenido de «Aprendo a Hablar».
    final bytes = await bundle.load(path);
    return _cache[bundle] = parse(
      jsonDecode(utf8.decode(bytes.buffer.asUint8List())) as Map<String, dynamic>,
    );
  }
}
