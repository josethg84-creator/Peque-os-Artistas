import 'dart:convert';
import 'dart:math';

import 'package:flutter/services.dart';

import '../speech/speech_content.dart';
import 'reading_content.dart';

/// Contenido de «Leo mis primeras oraciones» (`assets/reading/sentences.json`,
/// generado y validado por `tools/reading/sentences.py`). Solo datos y reglas
/// de los juegos: las pantallas no deciden nada del contenido.

/// Una palabra de la oración, tal como se ve (sin el punto final).
class SentenceWord {
  const SentenceWord({required this.text, this.clip});
  final String text;

  /// Grabación de la palabra sola, si existe.
  final String? clip;

  /// Sonido de la palabra sola (en minúsculas para que la voz no la deletree).
  ReadingAudio get audio => ReadingAudio(clip: clip, tts: text.toLowerCase());
}

class SentenceQuestion {
  const SentenceQuestion({
    required this.text,
    required this.options,
    required this.answer,
    required this.hintWord,
    required this.explanation,
  });

  final String text;

  /// Opciones con su imagen; [answer] es la correcta.
  final List<({String text, SpeechPicture picture})> options;
  final int answer;

  /// Palabra de la oración que responde (se resalta como pista).
  final int hintWord;
  final String explanation;
}

class ReadingSentence {
  const ReadingSentence({
    required this.id,
    required this.text,
    required this.level,
    required this.families,
    required this.words,
    required this.scene,
    required this.image,
    required this.imageReady,
    required this.clip,
    required this.wordMs,
    required this.question,
    required this.orderable,
    required this.listenOptions,
  });

  final String id;
  final String text;
  final int level;

  /// Familias silábicas de la Fase 3 que aparecen (la primera, la más usada).
  final List<String> families;
  final List<SentenceWord> words;

  /// Ilustración provisional (escena con dibujos de la app).
  final SpeechPicture scene;

  /// Ilustración 3D definitiva y si ya existe.
  final String image;
  final bool imageReady;

  /// Grabación de la oración y, si se midieron sobre ella, los milisegundos en
  /// que empieza cada palabra (para resaltarlas).
  final String? clip;
  final List<int>? wordMs;

  final SentenceQuestion question;

  /// Se puede usar en «Ordena la oración» (una sola forma correcta).
  final bool orderable;

  /// Otras dos oraciones con escenas claramente distintas.
  final List<String> listenOptions;

  /// La ilustración que se muestra: la 3D si existe; si no, la escena.
  SpeechPicture get picture => imageReady ? ImagePicture(image) : scene;

  /// Sonido de la oración completa.
  ReadingAudio get audio => ReadingAudio(clip: clip, tts: text);

  /// Piezas para ordenar: las palabras tal como se ven, con la mayúscula y el
  /// punto final como pistas.
  List<String> get pieces => [
    for (final (i, w) in words.indexed) i == words.length - 1 ? '${w.text}.' : w.text,
  ];

  /// Posición (en caracteres de [text]) donde empieza cada palabra.
  List<int> get wordStarts {
    final starts = <int>[];
    var from = 0;
    for (final w in words) {
      final i = text.indexOf(w.text, from);
      starts.add(i < 0 ? from : i);
      from = (i < 0 ? from : i) + w.text.length;
    }
    return starts;
  }

  /// Qué palabra empieza en (o contiene) el carácter [charIndex].
  int wordAt(int charIndex) {
    final starts = wordStarts;
    var found = 0;
    for (var i = 0; i < starts.length; i++) {
      if (starts[i] <= charIndex) found = i;
    }
    return found;
  }

  /// Qué palabra suena en el milisegundo [ms] de la grabación (con [wordMs]).
  int? wordAtMs(int ms) {
    final t = wordMs;
    if (t == null) return null;
    int? found;
    for (var i = 0; i < t.length; i++) {
      if (t[i] <= ms) found = i;
    }
    return found;
  }

  static ReadingSentence? fromJson(Map<String, dynamic> s) {
    if ((s['id'], s['text'], s['level'], s['question']) case (
      final String id,
      final String text,
      final int level,
      final Map<String, dynamic> q,
    )) {
      final options = [
        for (final o in (q['options'] as List? ?? const []))
          if (o is Map<String, dynamic> && o['text'] is String)
            if (SpeechPicture.fromJson(o['picture']) case final p?) (text: o['text'] as String, picture: p),
      ];
      final words = [
        for (final w in (s['words'] as List? ?? const []))
          if (w is Map<String, dynamic> && w['text'] is String)
            SentenceWord(text: w['text'] as String, clip: w['clip'] is String ? w['clip'] as String : null),
      ];
      final answer = q['answer'];
      final hint = q['hint_word'];
      if (options.length < 2 || answer is! int || answer >= options.length || words.isEmpty) return null;
      final audio = s['audio'] is Map<String, dynamic> ? s['audio'] as Map<String, dynamic> : const {};
      final ms = audio['word_ms'];
      final scene = s['scene'] is Map<String, dynamic>
          ? SpeechPicture.fromJson({
              'scene': (s['scene'] as Map)['bg'],
              'items': (s['scene'] as Map)['items'],
            })
          : null;
      return ReadingSentence(
        id: id,
        text: text,
        level: level,
        families: [...(s['families'] as List? ?? const []).whereType<String>()],
        words: words,
        scene: scene ?? const ScenePicture('jardin', []),
        image: s['image'] is String ? s['image'] as String : '',
        imageReady: s['image_ready'] == true,
        clip: audio['clip'] is String ? audio['clip'] as String : null,
        wordMs: ms is List && ms.length == words.length && ms.every((x) => x is int)
            ? [...ms.cast<int>()]
            : null,
        question: SentenceQuestion(
          text: q['text'] is String ? q['text'] as String : '',
          options: options,
          answer: answer,
          hintWord: hint is int && hint < words.length ? hint : 0,
          explanation: q['explanation'] is String ? q['explanation'] as String : '',
        ),
        orderable: s['order'] == true,
        listenOptions: [...(s['listen_options'] as List? ?? const []).whereType<String>()],
      );
    }
    return null;
  }
}

class SentenceCatalog {
  SentenceCatalog({required this.levelNames, required List<ReadingSentence> sentences})
    : sentences = List.unmodifiable(sentences),
      byId = {for (final s in sentences) s.id: s};

  final Map<int, String> levelNames;
  final List<ReadingSentence> sentences;
  final Map<String, ReadingSentence> byId;

  static const path = 'assets/reading/sentences.json';
  static const levels = [1, 2, 3, 4];

  List<ReadingSentence> ofLevel(int level) => [
    for (final s in sentences)
      if (s.level == level) s,
  ];

  static SentenceCatalog parse(Map<String, dynamic> json) => SentenceCatalog(
    levelNames: {
      for (final l in (json['levels'] as List? ?? const []))
        if (l is Map<String, dynamic> && l['id'] is int && l['name'] is String)
          l['id'] as int: l['name'] as String,
    },
    sentences: [
      for (final s in (json['sentences'] as List? ?? const []))
        if (s is Map<String, dynamic>) ?ReadingSentence.fromJson(s),
    ],
  );

  static final _cache = Expando<SentenceCatalog>();

  /// Carga el contenido (una sola vez por paquete de recursos).
  static Future<SentenceCatalog> load(AssetBundle bundle) async {
    final cached = _cache[bundle];
    if (cached != null) return cached;
    final bytes = await bundle.load(path);
    return _cache[bundle] = parse(
      jsonDecode(utf8.decode(bytes.buffer.asUint8List())) as Map<String, dynamic>,
    );
  }
}

/// Una pregunta de comprensión en juego: opciones barajadas, intentos y pistas.
/// Sin castigos: tras un error se puede volver a escuchar, ver la pista
/// (la palabra que responde, resaltada) y volver a intentarlo.
class ComprehensionRound {
  ComprehensionRound(this.sentence, {Random? random}) {
    order = [for (var i = 0; i < sentence.question.options.length; i++) i]..shuffle(random ?? Random());
  }

  final ReadingSentence sentence;
  late final List<int> order;

  /// Opciones en el orden en que se muestran.
  List<({String text, SpeechPicture picture})> get options => [
    for (final i in order) sentence.question.options[i],
  ];

  /// Índice (en [options]) de la correcta.
  int get correctIndex => order.indexOf(sentence.question.answer);

  int wrongAttempts = 0;
  bool solved = false;
  bool usedHint = false;

  /// Opciones ya descartadas (se ven atenuadas y marcadas con una cruz).
  final wrong = <int>{};

  /// Comprueba una opción. Devuelve si es la correcta.
  bool choose(int index) {
    if (solved) return true;
    if (index == correctIndex) {
      solved = true;
      return true;
    }
    wrongAttempts++;
    wrong.add(index);
    return false;
  }

  /// Acertó sin errores ni pistas.
  bool get firstTry => solved && wrongAttempts == 0 && !usedHint;
}

/// «Ordena la oración»: palabras desordenadas que se colocan tocándolas o
/// arrastrándolas. Se acepta cualquier orden que forme EXACTAMENTE la oración
/// (si una palabra se repite, da igual cuál de las dos se use).
class OrderRound {
  OrderRound(this.sentence, {Random? random}) {
    final r = random ?? Random();
    final pieces = sentence.pieces;
    final idx = [for (var i = 0; i < pieces.length; i++) i];
    // Siempre desordenadas (si se puede).
    for (var tries = 0; tries < 20; tries++) {
      idx.shuffle(r);
      if (pieces.length < 2 || [for (final i in idx) pieces[i]].join(' ') != pieces.join(' ')) break;
    }
    bank = idx;
    placed = [];
  }

  final ReadingSentence sentence;

  /// Índices de [ReadingSentence.pieces] aún por colocar, en el orden en que se ven.
  late List<int> bank;

  /// Índices ya colocados, en orden.
  late List<int> placed;

  int wrongAttempts = 0;
  bool usedHint = false;

  List<String> get pieces => sentence.pieces;
  bool get complete => bank.isEmpty;

  void place(int piece) {
    if (!bank.remove(piece)) return;
    placed.add(piece);
  }

  /// Devuelve la pieza colocada en [slot] al banco.
  void unplace(int slot) {
    if (slot < 0 || slot >= placed.length) return;
    bank.add(placed.removeAt(slot));
  }

  /// La oración formada es la correcta.
  bool check() {
    final ok = complete && [for (final i in placed) pieces[i]].join(' ') == pieces.join(' ');
    if (!ok && complete) wrongAttempts++;
    return ok;
  }

  /// Pista: deja bien colocadas las palabras del principio que ya están bien y
  /// coloca la siguiente correcta.
  void hint() {
    usedHint = true;
    final target = pieces;
    var good = 0;
    while (good < placed.length && pieces[placed[good]] == target[good]) {
      good++;
    }
    while (placed.length > good) {
      bank.add(placed.removeLast());
    }
    if (good >= target.length) return;
    final next = bank.firstWhere((i) => pieces[i] == target[good], orElse: () => -1);
    if (next >= 0) place(next);
  }

  bool get firstTry => wrongAttempts == 0 && !usedHint;
}

/// «Escucha y selecciona»: se oye la oración y se elige su ilustración entre
/// tres claramente distintas.
class ListenSelectRound {
  ListenSelectRound(this.sentence, SentenceCatalog content, {Random? random}) {
    final others = [for (final id in sentence.listenOptions) ?content.byId[id]];
    choices = [sentence, ...others]..shuffle(random ?? Random());
  }

  final ReadingSentence sentence;
  late final List<ReadingSentence> choices;

  int get correctIndex => choices.indexOf(sentence);
  int wrongAttempts = 0;
  final wrong = <int>{};
  bool solved = false;

  bool choose(int index) {
    if (solved) return true;
    if (index == correctIndex) return solved = true;
    wrongAttempts++;
    wrong.add(index);
    return false;
  }

  bool get firstTry => solved && wrongAttempts == 0;
}
