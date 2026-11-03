import 'dart:math';

import 'speech_activities.dart';
import 'speech_content.dart';

/// Juegos con el vocabulario (fase 4): relacionar palabra e imagen, ordenar
/// por grupos, completar frases y los juegos de sonidos. Funciones puras: con
/// la misma semilla, las mismas preguntas. No se usa reconocimiento de voz:
/// el niño siempre responde tocando.
enum WordGame {
  cual('cual', '¿Cuál es?'),
  grupo('grupo', '¿De qué grupo es?'),
  frase('frase', 'Completa la frase'),
  encuentro('encuentro', 'Escucho y encuentro'),
  empieza('empieza', '¿Con qué empieza?'),
  rimas('rimas', 'Palabras que riman');

  const WordGame(this.id, this.title);
  final String id;
  final String title;

  static WordGame? byId(String id) {
    for (final g in values) {
      if (g.id == id) return g;
    }
    return null;
  }

  /// Clave del progreso al terminar una ronda.
  String get progressKey => 'juego_$id';
}

/// Las palabras de un nivel (si son pocas, se completan con las de niveles
/// más fáciles: nunca se impide practicar lo sencillo).
List<(SpeechWord, WordCategory)> wordsForLevel(SpeechContent c, int level) {
  final all = [
    for (final cat in c.categories)
      for (final w in cat.words) (w, cat),
  ];
  final exact = [
    for (final e in all)
      if (e.$1.level == level) e,
  ];
  if (exact.length >= 12) return exact;
  return [
    for (final e in all)
      if (e.$1.level <= level) e,
  ];
}

/// «¿Dónde está la jirafa?» o «Señala: correr» (sin artículo).
String pointAt(SpeechWord w) => w.article == null ? 'Señala: ${w.text}' : '¿Dónde está ${w.withArticle}?';

List<QuizQuestion> buildWordGame(WordGame game, SpeechContent c, Random r, {int level = 1, int count = 6}) {
  return switch (game) {
    WordGame.cual || WordGame.encuentro => _find(c, r, level, count, hideLabels: game == WordGame.encuentro),
    WordGame.grupo => _group(c, r, level, count),
    WordGame.frase => _sentence(c, r, level, count),
    WordGame.empieza => _sounds(c, r, count, rhyme: false),
    WordGame.rimas => _sounds(c, r, count, rhyme: true),
  };
}

List<(SpeechWord, WordCategory)> _pick(List<(SpeechWord, WordCategory)> pool, Random r, int count) =>
    ([...pool]..shuffle(r)).take(count).toList();

/// Palabras de otros grupos (para que el dibujo no se confunda).
List<SpeechWord> _distractors(SpeechContent c, Random r, WordCategory not, SpeechWord target, int n) {
  final pool = [
    for (final cat in c.categories)
      if (cat.id != not.id)
        for (final w in cat.words)
          if (w.text != target.text) w,
  ]..shuffle(r);
  final seen = <String>{};
  return [
    for (final w in pool)
      if (seen.add(w.text)) w,
  ].take(n).toList();
}

List<QuizQuestion> _find(SpeechContent c, Random r, int level, int count, {required bool hideLabels}) => [
  for (final (w, cat) in _pick(wordsForLevel(c, level), r, count))
    () {
      final options = [w, ..._distractors(c, r, cat, w, level == 1 ? 2 : 3)]..shuffle(r);
      return QuizQuestion(
        instruction: hideLabels ? 'Escucha y encuentra' : pointAt(w),
        spoken: hideLabels ? 'Escucha y encuentra: ${w.text}' : pointAt(w),
        options: [
          for (final o in options) QuizOption(label: o.text, picture: o.picture, showLabel: !hideLabels),
        ],
        answer: options.indexOf(w),
        afterCorrect: '¡Sí! ${w.withArticle[0].toUpperCase()}${w.withArticle.substring(1)}.',
      );
    }(),
];

List<QuizQuestion> _group(SpeechContent c, Random r, int level, int count) => [
  for (final (w, cat) in _pick(wordsForLevel(c, level), r, count))
    () {
      final others = ([...c.categories.where((x) => x.id != cat.id)]..shuffle(r)).take(2);
      final options = [cat, ...others]..shuffle(r);
      return QuizQuestion(
        instruction: '¿En qué grupo va ${w.withArticle}?',
        scene: w.picture,
        options: [for (final o in options) QuizOption(label: o.name, picture: IconPicture(o.icon, o.color))],
        answer: options.indexOf(cat),
        afterCorrect:
            '¡Sí! ${w.text[0].toUpperCase()}${w.text.substring(1)} va en ${cat.name.toLowerCase()}.',
      );
    }(),
];

/// La frase de ejemplo con un hueco donde va la palabra.
String? blankOut(SpeechWord w) {
  final example = w.example;
  if (example == null) return null;
  final i = example.toLowerCase().indexOf(w.text.toLowerCase());
  if (i < 0) return null;
  return '${example.substring(0, i)}___${example.substring(i + w.text.length)}';
}

List<QuizQuestion> _sentence(SpeechContent c, Random r, int level, int count) {
  final pool = [
    for (final e in wordsForLevel(c, level))
      if (blankOut(e.$1) != null) e,
  ];
  return [
    for (final (w, cat) in _pick(pool, r, count))
      () {
        final options = [w, ..._distractors(c, r, cat, w, 2)]..shuffle(r);
        final prompt = blankOut(w)!;
        return QuizQuestion(
          instruction: 'Completa la frase',
          prompt: prompt,
          spoken: 'Completa la frase: ${prompt.replaceAll('___', '...')}',
          options: [for (final o in options) QuizOption(label: o.text, picture: o.picture)],
          answer: options.indexOf(w),
          afterCorrect: w.example,
        );
      }(),
  ];
}

List<QuizQuestion> _sounds(SpeechContent c, Random r, int count, {required bool rhyme}) {
  final byId = {for (final w in c.words) w.id: w};
  final sets = [...(rhyme ? c.phonology.rhymes : c.phonology.starts)]..shuffle(r);
  final out = <QuizQuestion>[];
  for (final s in sets) {
    final target = byId[s.target], answer = byId[s.answer];
    final others = [for (final id in s.others) ?byId[id]];
    if (target == null || answer == null || others.length != s.others.length) continue;
    final options = [answer, ...others]..shuffle(r);
    final listen = 'Escucha: ${options.map((o) => o.text).join(', ')}.';
    final syllable = target.syllables.firstOrNull;
    out.add(
      QuizQuestion(
        instruction: rhyme
            ? '¿Qué palabra rima con ${target.text}?'
            : '¿Qué palabra empieza como ${target.text}?',
        spoken: rhyme
            ? '¿Qué palabra rima con ${target.text}? $listen'
            : '¿Qué palabra empieza como ${target.text}? ${syllable == null ? '' : '$syllable... '}$listen',
        scene: target.picture,
        options: [for (final o in options) QuizOption(label: o.text, picture: o.picture)],
        answer: options.indexOf(answer),
        afterCorrect: rhyme
            ? '¡Sí! ${target.text}, ${answer.text}. ¡Riman!'
            : '¡Sí! ${target.text}, ${answer.text}. Empiezan igual${syllable == null ? '' : ': $syllable'}.',
      ),
    );
    if (out.length == count) break;
  }
  return out;
}

/// «Palmas y sílabas»: palabras de una sola pieza con sílabas conocidas,
/// según el nivel (1: una o dos sílabas; 2: tres; 3: cuatro o más).
List<SpeechWord> clapWords(SpeechContent c, Random r, {int level = 1, int count = 6}) {
  bool fits(int n) => switch (level) {
    1 => n <= 2,
    2 => n == 3,
    _ => n >= 4,
  };
  final seen = <String>{};
  final pool = [
    for (final w in c.words)
      if (w.pronunciation != null && !w.text.contains(' ') && fits(w.syllables.length) && seen.add(w.text)) w,
  ]..shuffle(r);
  return pool.take(count).toList();
}
