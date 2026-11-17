import 'dart:math';

import 'package:flutter/widgets.dart' show StringCharacters;

import 'reading_content.dart';

/// Lógica de los juegos de sílabas (sin pantallas, para poder probarla).

/// «Escucha y encuentra»: suena [target]; hay que tocarla entre [options].
class ListenFindQuestion {
  const ListenFindQuestion(this.target, this.options);
  final ReadingSyllable target;
  final List<ReadingSyllable> options;
  bool isRight(ReadingSyllable s) => s.id == target.id;
}

/// «Une sílaba y palabra»: se ve [word]; hay que tocar su primera sílaba.
class MatchWordQuestion {
  const MatchWordQuestion(this.word, this.answer, this.options);
  final ReadingWord word;
  final ReadingSyllable answer;
  final List<ReadingSyllable> options;
  bool isRight(ReadingSyllable s) => s.id == answer.id;
}

abstract final class SyllableGames {
  static const optionCount = 3;

  static String _plain(String s) => s
      .toLowerCase()
      .replaceAll('á', 'a')
      .replaceAll('é', 'e')
      .replaceAll('í', 'i')
      .replaceAll('ó', 'o')
      .replaceAll('ú', 'u');

  static String _vowel(String syllable) => _plain(syllable).characters.last;

  /// Sílabas del nivel inicial (vocales y directas) de [familyId], o todas.
  static List<ReadingSyllable> pool(ReadingContent c, {String? familyId}) => [
    for (final f in c.families)
      if (familyId == null || f.id == familyId)
        for (final s in c.syllablesOf(f))
          if (s.level == 1) s,
  ];

  /// [count] preguntas sin repetir la misma sílaba dos veces seguidas. Las
  /// otras opciones terminan en la misma vocal (MA / PA / SA) para que haya que
  /// escuchar la consonante; si no hay bastantes, se completan con otras.
  static List<ListenFindQuestion> listenFind(
    ReadingContent c, {
    String? familyId,
    int count = 8,
    required Random random,
  }) {
    final targets = pool(c, familyId: familyId);
    final all = pool(c);
    if (targets.isEmpty) return const [];
    final order = _sequence(targets, count, random);
    final out = <ListenFindQuestion>[];
    int? lastIndex;
    for (final t in order) {
      final sameVowel = [
        for (final s in all)
          if (s.id != t.id && _vowel(s.text) == _vowel(t.text) && _plain(s.text) != _plain(t.text)) s,
      ]..shuffle(random);
      final others = [
        for (final s in all)
          if (s.id != t.id && _plain(s.text) != _plain(t.text) && !sameVowel.contains(s)) s,
      ]..shuffle(random);
      final distractors = [...sameVowel, ...others].take(optionCount - 1).toList();
      final options = _place([t, ...distractors], t, random, lastIndex);
      lastIndex = options.indexOf(t);
      out.add(ListenFindQuestion(t, options));
    }
    return out;
  }

  /// [count] palabras con imagen. Las otras opciones no aparecen en la palabra
  /// (para no confundir con PELOTA: LO, TA) y son de otras consonantes.
  static List<MatchWordQuestion> matchWord(
    ReadingContent c, {
    String? familyId,
    int count = 6,
    required Random random,
  }) {
    final pairs = <(ReadingWord, ReadingSyllable)>[
      for (final s in pool(c, familyId: familyId))
        if (c.wordOf(s) case final w? when w.hasPicture) (w, s),
    ];
    if (pairs.isEmpty) return const [];
    final all = pool(c);
    final order = _sequence(pairs, count, random);
    final out = <MatchWordQuestion>[];
    int? lastIndex;
    for (final (w, s) in order) {
      final inWord = {for (final x in w.syllables) _plain(x)};
      final candidates = [
        for (final o in all)
          if (o.id != s.id && !inWord.contains(_plain(o.text)) && o.familyId != s.familyId) o,
      ]..shuffle(random);
      final options = _place([s, ...candidates.take(optionCount - 1)], s, random, lastIndex);
      lastIndex = options.indexOf(s);
      out.add(MatchWordQuestion(w, s, options));
    }
    return out;
  }

  /// Orden aleatorio de [items] (repitiendo si hacen falta más), sin el mismo
  /// elemento dos veces seguidas.
  static List<T> _sequence<T>(List<T> items, int count, Random random) {
    final out = <T>[];
    while (out.length < count) {
      final round = [...items]..shuffle(random);
      if (out.isNotEmpty && round.length > 1 && round.first == out.last) {
        round.add(round.removeAt(0));
      }
      out.addAll(round);
    }
    return out.take(count).toList();
  }

  /// Baraja las opciones procurando que la correcta no quede en el mismo sitio
  /// que en la pregunta anterior (para que no sea predecible).
  static List<ReadingSyllable> _place(
    List<ReadingSyllable> options,
    ReadingSyllable answer,
    Random random,
    int? lastIndex,
  ) {
    final shuffled = [...options]..shuffle(random);
    if (lastIndex != null && shuffled.length > 1 && shuffled.indexOf(answer) == lastIndex) {
      final i = shuffled.indexOf(answer);
      final j = (i + 1 + random.nextInt(shuffled.length - 1)) % shuffled.length;
      shuffled[i] = shuffled[j];
      shuffled[j] = answer;
    }
    return shuffled;
  }
}
