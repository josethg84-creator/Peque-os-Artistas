import 'dart:convert';
import 'dart:math';

import 'package:flutter/services.dart';

import 'reading_content.dart';

/// «Completa las palabras»: catálogo de palabras y ejercicios
/// (`assets/reading/complete_words.json`, generado y validado por
/// `tools/reading/words.py`). Solo datos y lógica, sin pantallas.

/// Los tres modos de juego, de menos a más difícil.
enum CompleteMode {
  choose('elige', 'Elige la sílaba', 'Toca la sílaba que falta.'),
  drag('arrastra', 'Arrastra la sílaba', 'Arrastra la sílaba al hueco (o tócala).'),
  order('ordena', 'Ordena la palabra', 'Toca las sílabas en orden.');

  const CompleteMode(this.id, this.title, this.instruction);
  final String id;
  final String title;
  final String instruction;
}

class CompleteExercise {
  const CompleteExercise({
    required this.id,
    required this.wordId,
    required this.level,
    required this.category,
    required this.syllables,
    required this.missing,
    required this.answer,
    required this.options,
    required this.orderable,
  });

  final String id;
  final String wordId;
  final int level;
  final String category;
  final List<String> syllables;

  /// Posición de la sílaba que falta.
  final int missing;
  final String answer;

  /// Opciones (incluye [answer] una sola vez).
  final List<String> options;

  /// Sirve para el modo «Ordena la palabra» (dos sílabas o más).
  final bool orderable;

  bool isRight(String option) => option == answer;

  static CompleteExercise? fromJson(Map<String, dynamic> e) {
    if ((e['id'], e['word'], e['answer'], e['missing']) case (
      final String id,
      final String word,
      final String answer,
      final int missing,
    )) {
      return CompleteExercise(
        id: id,
        wordId: word,
        level: e['level'] is int ? e['level'] as int : 1,
        category: e['category'] is String ? e['category'] as String : '',
        syllables: [...(e['syllables'] as List? ?? const []).whereType<String>()],
        missing: missing,
        answer: answer,
        options: [...(e['options'] as List? ?? const []).whereType<String>()],
        orderable: e['order'] == true,
      );
    }
    return null;
  }
}

class CompleteWordsContent {
  CompleteWordsContent({required List<ReadingWord> words, required this.exercises})
    : words = {for (final w in words) w.id: w};

  final Map<String, ReadingWord> words;
  final List<CompleteExercise> exercises;

  static const path = 'assets/reading/complete_words.json';
  static const levels = [1, 2, 3];
  static const levelNames = {1: 'Dos sílabas', 2: 'Palabras largas', 3: 'Sílabas difíciles'};

  ReadingWord wordOf(CompleteExercise e) => words[e.wordId]!;

  /// Ejercicios jugables (su palabra tiene imagen) de un nivel y modo.
  List<CompleteExercise> playable(int level, CompleteMode mode) => [
    for (final e in exercises)
      if (e.level == level &&
          (words[e.wordId]?.hasPicture ?? false) &&
          (mode != CompleteMode.order || e.orderable))
        e,
  ];

  /// Los que esperan su ilustración (no se juegan todavía).
  List<CompleteExercise> get pendingImage => [
    for (final e in exercises)
      if (!(words[e.wordId]?.hasPicture ?? false)) e,
  ];

  /// [count] ejercicios para una partida: primero los que aún no se han hecho
  /// en ese modo, en orden aleatorio.
  List<CompleteExercise> session(
    int level,
    CompleteMode mode, {
    required bool Function(CompleteExercise) done,
    required Random random,
    int count = 8,
  }) {
    final all = playable(level, mode);
    final fresh = [...all.where((e) => !done(e))]..shuffle(random);
    final old = [...all.where(done)]..shuffle(random);
    return [...fresh, ...old].take(count).toList();
  }

  static CompleteWordsContent parse(Map<String, dynamic> json) {
    List<Map<String, dynamic>> list(String key) => [
      for (final x in (json[key] as List? ?? const []))
        if (x is Map<String, dynamic>) x,
    ];
    return CompleteWordsContent(
      words: [for (final w in list('words')) ?ReadingWord.fromJson(w)],
      exercises: [for (final e in list('exercises')) ?CompleteExercise.fromJson(e)],
    );
  }

  static final _cache = Expando<CompleteWordsContent>();

  static Future<CompleteWordsContent> load(AssetBundle bundle) async {
    final cached = _cache[bundle];
    if (cached != null) return cached;
    final bytes = await bundle.load(path);
    return _cache[bundle] = parse(
      jsonDecode(utf8.decode(bytes.buffer.asUint8List())) as Map<String, dynamic>,
    );
  }
}

/// Estado de un ejercicio en juego, con las pistas. Las pistas ayudan sin
/// castigar: tras dos intentos fallidos se quita una opción equivocada.
class CompleteRound {
  CompleteRound(this.exercise, this.mode, Random random)
    : options = [...exercise.options],
      pieces = [for (final (i, s) in exercise.syllables.indexed) (i, s)] {
    if (mode == CompleteMode.order) {
      // Barajadas, nunca ya en orden.
      do {
        pieces.shuffle(random);
      } while (pieces.length > 1 && pieces.map((p) => p.$1).toList().join() == _ordered);
    }
  }

  final CompleteExercise exercise;
  final CompleteMode mode;

  /// Opciones que quedan (modos «elige» y «arrastra»).
  final List<String> options;

  /// Tarjetas de sílaba (modo «ordena»): (posición original, texto).
  final List<(int, String)> pieces;

  String get _ordered => [for (var i = 0; i < exercise.syllables.length; i++) i].join();

  /// Lo elegido para el hueco («elige» y «arrastra»).
  String? chosen;

  /// Tarjetas colocadas, en orden («ordena»).
  final placed = <int>[];

  int wrongAttempts = 0;
  bool solved = false;

  /// Pistas usadas (cuenta como «con ayuda» en el progreso).
  bool usedHints = false;

  /// Pista visual: la primera letra de la sílaba que falta.
  bool showFirstLetter = false;

  /// Ayuda explícita: se resalta la opción correcta (o la siguiente tarjeta).
  bool revealAnswer = false;

  bool get ready => mode == CompleteMode.order ? placed.length == pieces.length : chosen != null;

  /// La palabra tal como la ha formado el niño («ordena»).
  List<String> get built => [for (final i in placed) pieces.firstWhere((p) => p.$1 == i).$2];

  /// La siguiente tarjeta correcta (para la ayuda en «ordena»).
  int? get nextPiece {
    for (var i = 0; i < exercise.syllables.length; i++) {
      if (i >= placed.length) return i;
      if (built[i] != exercise.syllables[i]) return null;
    }
    return null;
  }

  /// Comprueba. Si no es correcta, deja intentarlo de nuevo.
  bool check() {
    final right = mode == CompleteMode.order
        ? built.join('|') == exercise.syllables.join('|')
        : chosen == exercise.answer;
    if (right) {
      solved = true;
    } else {
      wrongAttempts++;
      chosen = null;
      placed.clear();
      // Tras dos intentos, una opción equivocada menos (nunca menos de dos).
      if (wrongAttempts >= 2 && options.length > 2) {
        final wrong = options.where((o) => o != exercise.answer).toList();
        options.remove(wrong.last);
      }
    }
    return right;
  }
}
