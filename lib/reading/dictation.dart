import 'dart:convert';
import 'dart:math';

import 'package:flutter/services.dart';

import '../speech/speech_content.dart';
import 'reading_content.dart';
import 'syllabifier.dart';

/// Contenido de «Escucho y escribo» (`assets/reading/dictations.json`,
/// generado y validado por `tools/reading/dictations.py` a partir de las
/// sílabas, palabras y oraciones de las fases anteriores).

enum DictationType {
  syllable('silaba'),
  word('palabra'),
  sentence('oracion');

  const DictationType(this.id);
  final String id;

  static DictationType? parse(Object? v) => values.where((t) => t.id == v).firstOrNull;
}

/// Cómo responde el niño.
enum DictationMode {
  /// Tocar tarjetas de sílabas (nivel 1 y 2).
  cards('tarjetas', 'Tocar tarjetas'),

  /// Escribir con el teclado del dispositivo.
  keyboard('teclado', 'Escribir con teclado'),

  /// Ordenar tarjetas de palabras (oraciones).
  order('ordenar', 'Ordenar palabras');

  const DictationMode(this.id, this.title);
  final String id;
  final String title;

  static DictationMode? parse(Object? v) => values.where((m) => m.id == v).firstOrNull;
}

class Dictation {
  const Dictation({
    required this.id,
    required this.type,
    required this.level,
    required this.difficulty,
    required this.text,
    required this.audio,
    required this.cards,
    required this.target,
    required this.modes,
    required this.countLabel,
    required this.firstHint,
    required this.model,
    required this.alternatives,
    required this.finalPeriodOptional,
    this.picture,
    this.example,
  });

  final String id;
  final DictationType type;

  /// 1 sílabas, 2 palabras, 3 oraciones.
  final int level;

  /// Dificultad dentro del nivel (para empezar por lo más fácil).
  final int difficulty;

  /// Texto correcto.
  final String text;
  final ReadingAudio audio;

  /// Imagen (palabra), escena (oración) o palabra de ejemplo (sílaba).
  final SpeechPicture? picture;
  final String? example;

  /// Tarjetas disponibles (con distractores) y las que forman la respuesta.
  final List<String> cards;
  final List<String> target;
  final List<DictationMode> modes;

  /// Pistas: «2 sílabas», la primera parte y el modelo para copiar.
  final String countLabel;
  final String firstHint;
  final String model;

  /// Otras grafías aceptadas (solo sílabas que suenan exactamente igual).
  final List<String> alternatives;
  final bool finalPeriodOptional;

  static Dictation? fromJson(Map<String, dynamic> d) {
    final type = DictationType.parse(d['type']);
    final audio = ReadingAudio.fromJson(d['audio']);
    if ((d['id'], d['text'], type, audio) case (
      final String id,
      final String text,
      final DictationType type,
      final ReadingAudio audio,
    )) {
      List<String> strings(Object? v) => [...(v is List ? v : const []).whereType<String>()];
      final hints = d['hints'] is Map<String, dynamic> ? d['hints'] as Map<String, dynamic> : const {};
      final validation = d['validation'] is Map<String, dynamic>
          ? d['validation'] as Map<String, dynamic>
          : const {};
      final scene = d['scene'];
      final target = strings(d['target']);
      if (target.isEmpty) return null;
      return Dictation(
        id: id,
        type: type,
        level: d['level'] is int ? d['level'] as int : 1,
        difficulty: d['difficulty'] is int ? d['difficulty'] as int : 1,
        text: text,
        audio: audio,
        picture: scene is Map
            ? SpeechPicture.fromJson({'scene': scene['bg'], 'items': scene['items']})
            : SpeechPicture.fromJson(d['picture']),
        example: d['example'] is String ? d['example'] as String : null,
        cards: strings(d['cards']),
        target: target,
        modes: [for (final m in strings(d['modes'])) ?DictationMode.parse(m)],
        countLabel: hints['count_label'] is String ? hints['count_label'] as String : '',
        firstHint: hints['first'] is String ? hints['first'] as String : target.first,
        model: hints['model'] is String ? hints['model'] as String : text,
        alternatives: strings(validation['alternatives']),
        finalPeriodOptional: validation['final_period'] == 'optional',
      );
    }
    return null;
  }
}

class DictationCatalog {
  DictationCatalog({required this.levelNames, required List<Dictation> dictations})
    : dictations = List.unmodifiable(dictations),
      byId = {for (final d in dictations) d.id: d};

  final Map<int, String> levelNames;
  final List<Dictation> dictations;
  final Map<String, Dictation> byId;

  static const path = 'assets/reading/dictations.json';
  static const levels = [1, 2, 3];

  List<Dictation> ofLevel(int level) => [
    for (final d in dictations)
      if (d.level == level) d,
  ];

  static DictationCatalog parse(Map<String, dynamic> json) => DictationCatalog(
    levelNames: {
      for (final l in (json['levels'] as List? ?? const []))
        if (l is Map<String, dynamic> && l['id'] is int && l['name'] is String)
          l['id'] as int: l['name'] as String,
    },
    dictations: [
      for (final d in (json['dictations'] as List? ?? const []))
        if (d is Map<String, dynamic>) ?Dictation.fromJson(d),
    ],
  );

  static final _cache = Expando<DictationCatalog>();

  static Future<DictationCatalog> load(AssetBundle bundle) async {
    final cached = _cache[bundle];
    if (cached != null) return cached;
    final bytes = await bundle.load(path);
    return _cache[bundle] = parse(
      jsonDecode(utf8.decode(bytes.buffer.asUint8List())) as Map<String, dynamic>,
    );
  }
}

// ---------------------------------------------------------------- corrección

/// Tipo de error encontrado (para explicarlo y para el progreso).
enum DictationIssue {
  none,
  empty,

  /// Falta, sobra o está mal puesta una tilde.
  accent,

  /// Las letras están bien pero los espacios no (palabras juntas o separadas).
  spaces,

  /// Una sola letra distinta, de más o de menos.
  letter,

  /// Alguna sílaba está mal (o faltan o sobran sílabas).
  syllable,

  /// En una oración: alguna palabra está mal, falta o sobra.
  word,

  /// Las tarjetas están, pero en otro orden.
  order,
}

class DictationResult {
  const DictationResult({
    required this.correct,
    required this.issue,
    required this.message,
    this.alternative = false,
    this.marked = const {},
    this.tip,
  });

  final bool correct;
  final DictationIssue issue;

  /// Explicación para el niño (y el adulto).
  final String message;

  /// Se aceptó una grafía alternativa que suena igual.
  final bool alternative;

  /// Partes del texto correcto que hay que revisar (sílabas en una palabra,
  /// palabras en una oración).
  final Set<int> marked;

  /// Consejo que no cuenta como error (mayúscula inicial, punto final).
  final String? tip;
}

/// Corrección pedagógica: no da por buena una respuesta con faltas, pero
/// explica qué tipo de error es. Se normalizan las mayúsculas y los espacios
/// de los extremos o repetidos; las tildes y las letras sí cuentan.
abstract final class DictationChecker {
  static const _accents = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u'};

  static String stripAccents(String s) => s.split('').map((c) => _accents[c] ?? c).join();

  static String _norm(String s) => s.trim().replaceAll(RegExp(r'\s+'), ' ').toLowerCase();

  static int distance(String a, String b) {
    final prev = List<int>.generate(b.length + 1, (i) => i);
    for (var i = 1; i <= a.length; i++) {
      var diag = prev[0];
      prev[0] = i;
      for (var j = 1; j <= b.length; j++) {
        final up = prev[j];
        prev[j] = min(min(prev[j] + 1, prev[j - 1] + 1), diag + (a[i - 1] == b[j - 1] ? 0 : 1));
        diag = up;
      }
    }
    return prev[b.length];
  }

  /// Comprueba lo escrito con el teclado.
  static DictationResult check(Dictation d, String input) {
    var answer = _norm(input);
    if (answer.isEmpty) {
      return const DictationResult(
        correct: false,
        issue: DictationIssue.empty,
        message: 'Escribe tu respuesta.',
      );
    }
    if (d.type == DictationType.sentence) return _sentence(d, input);
    final expected = _norm(d.text);
    if (answer == expected) return _ok();
    if (d.alternatives.contains(answer)) {
      return DictationResult(
        correct: true,
        issue: DictationIssue.none,
        alternative: true,
        message:
            '¡Excelente trabajo! «${answer.toUpperCase()}» suena igual. Hoy practicamos «${d.text.toUpperCase()}».',
      );
    }
    answer = answer.replaceAll('.', '');
    return _word(expected, answer);
  }

  static DictationResult _ok({String? tip}) =>
      DictationResult(correct: true, issue: DictationIssue.none, message: '¡Excelente trabajo!', tip: tip);

  /// Una sílaba o una palabra.
  static DictationResult _word(String expected, String answer) {
    final parts = Syllabifier.split(expected);
    Set<int> wrongSyllables() {
      final got = Syllabifier.split(answer.replaceAll(' ', ''));
      return {
        for (var i = 0; i < parts.length; i++)
          if (i >= got.length || got[i] != parts[i]) i,
      };
    }

    if (stripAccents(answer) == stripAccents(expected)) {
      final need = expected.split('').any(_accents.containsKey);
      final has = answer.split('').any(_accents.containsKey);
      final msg = need && !has
          ? 'Casi: falta la tilde. Escucha dónde suena más fuerte.'
          : !need && has
          ? 'Casi: esta palabra no lleva tilde.'
          : 'Casi: la tilde va en otra letra.';
      return DictationResult(
        correct: false,
        issue: DictationIssue.accent,
        message: msg,
        marked: wrongSyllables(),
      );
    }
    if (answer.replaceAll(' ', '') == expected.replaceAll(' ', '')) {
      return DictationResult(
        correct: false,
        issue: DictationIssue.spaces,
        message: expected.contains(' ')
            ? 'Casi: separa las palabras con un espacio.'
            : 'Casi: escribe todas las letras juntas, sin espacios.',
      );
    }
    final a = stripAccents(answer);
    final e = stripAccents(expected);
    if (distance(a, e) == 1) {
      final msg = a.length < e.length
          ? 'Casi: falta una letra.'
          : a.length > e.length
          ? 'Casi: sobra una letra.'
          : 'Casi: hay una letra que cambiar.';
      return DictationResult(
        correct: false,
        issue: DictationIssue.letter,
        message: msg,
        marked: wrongSyllables(),
      );
    }
    if (parts.length == 1) {
      return const DictationResult(
        correct: false,
        issue: DictationIssue.syllable,
        message: 'Esa no es la sílaba. Escucha otra vez.',
        marked: {0},
      );
    }
    final got = Syllabifier.split(answer.replaceAll(' ', ''));
    if (got.length != parts.length) {
      return DictationResult(
        correct: false,
        issue: DictationIssue.syllable,
        message: 'Escucha otra vez: la palabra tiene ${parts.length} sílabas y tú escribiste ${got.length}.',
        marked: wrongSyllables(),
      );
    }
    final wrong = wrongSyllables();
    return DictationResult(
      correct: false,
      issue: DictationIssue.syllable,
      message: wrong.length == 1
          ? 'Casi: revisa la sílaba ${parts[wrong.first].toUpperCase()}.'
          : 'Revisa las sílabas marcadas.',
      marked: wrong,
    );
  }

  /// Una oración: se compara palabra por palabra.
  static DictationResult _sentence(Dictation d, String input) {
    final raw = input.trim().replaceAll(RegExp(r'\s+'), ' ');
    final hasPeriod = raw.endsWith('.');
    String words(String s) => _norm(s).replaceAll(RegExp(r'[.,;:!¡?¿]'), '').trim();
    final expected = words(d.text).split(' ');
    final answerText = words(raw);
    final answer = answerText.isEmpty ? <String>[] : answerText.split(' ');
    String? tip;
    if (raw.isNotEmpty && raw[0] != raw[0].toUpperCase()) {
      tip = 'Recuerda: la oración empieza con mayúscula.';
    } else if (!hasPeriod && d.finalPeriodOptional) {
      tip = 'Recuerda: la oración termina con un punto.';
    }
    if (answer.join(' ') == expected.join(' ')) return _ok(tip: tip);
    if (answer.join() == expected.join()) {
      return DictationResult(
        correct: false,
        issue: DictationIssue.spaces,
        message: answer.length < expected.length
            ? 'Casi: separa las palabras con espacios. La oración tiene ${expected.length} palabras.'
            : 'Casi: hay una palabra separada que va junta.',
      );
    }
    if (answer.length == expected.length) {
      final wrong = {
        for (var i = 0; i < expected.length; i++)
          if (answer[i] != expected[i]) i,
      };
      if (wrong.every((i) => stripAccents(answer[i]) == stripAccents(expected[i]))) {
        return DictationResult(
          correct: false,
          issue: DictationIssue.accent,
          message: wrong.length == 1
              ? 'Casi: revisa la tilde de una palabra.'
              : 'Casi: revisa las tildes de las palabras marcadas.',
          marked: wrong,
        );
      }
      final sameWords = ([...answer]..sort()).join(' ') == ([...expected]..sort()).join(' ');
      if (sameWords) {
        return DictationResult(
          correct: false,
          issue: DictationIssue.order,
          message: 'Las palabras están bien, pero en otro orden. Escucha otra vez.',
          marked: wrong,
        );
      }
      return DictationResult(
        correct: false,
        issue: DictationIssue.word,
        message: wrong.length == 1 ? 'Casi: revisa la palabra marcada.' : 'Revisa las palabras marcadas.',
        marked: wrong,
      );
    }
    return DictationResult(
      correct: false,
      issue: DictationIssue.word,
      message: answer.length < expected.length
          ? 'Falta alguna palabra: la oración tiene ${expected.length} palabras.'
          : 'Sobra alguna palabra: la oración tiene ${expected.length} palabras.',
      marked: {
        for (var i = 0; i < expected.length; i++)
          if (i >= answer.length || answer[i] != expected[i]) i,
      },
    );
  }

  /// Comprueba lo formado con tarjetas.
  static DictationResult checkCards(Dictation d, List<String> built) {
    if (built.isEmpty) {
      return const DictationResult(
        correct: false,
        issue: DictationIssue.empty,
        message: 'Toca las tarjetas.',
      );
    }
    if (built.join(' ') == d.target.join(' ')) return _ok();
    final marked = {
      for (var i = 0; i < d.target.length; i++)
        if (i >= built.length || built[i] != d.target[i]) i,
    };
    final sameCards = ([...built]..sort()).join(' ') == ([...d.target]..sort()).join(' ');
    if (sameCards) {
      return DictationResult(
        correct: false,
        issue: DictationIssue.order,
        message: d.type == DictationType.sentence
            ? 'Las palabras están bien, pero en otro orden.'
            : 'Las sílabas están bien, pero en otro orden.',
        marked: marked,
      );
    }
    if (d.type == DictationType.syllable) {
      return const DictationResult(
        correct: false,
        issue: DictationIssue.syllable,
        message: 'Esa no es la sílaba. Escucha otra vez.',
        marked: {0},
      );
    }
    return DictationResult(
      correct: false,
      issue: d.type == DictationType.sentence ? DictationIssue.word : DictationIssue.syllable,
      message: built.length != d.target.length
          ? 'Escucha otra vez: ${d.type == DictationType.sentence ? 'son' : 'tiene'} ${d.countLabel}.'
          : 'Casi: revisa las tarjetas marcadas.',
      marked: marked,
    );
  }
}

/// Nombre de cada letra (para decir una pista con la voz sin que lea una
/// letra suelta de forma rara).
const letterNames = {
  'a': 'a',
  'b': 'be',
  'c': 'ce',
  'd': 'de',
  'e': 'e',
  'f': 'efe',
  'i': 'i',
  'l': 'ele',
  'm': 'eme',
  'n': 'ene',
  'o': 'o',
  'p': 'pe',
  'q': 'cu',
  's': 'ese',
  't': 'te',
  'u': 'u',
};

// ---------------------------------------------------------------- partida

/// Un dictado en juego: respuesta, intentos y pistas progresivas.
class DictationRound {
  DictationRound(this.dictation, this.mode, {Random? random}) {
    bank = [for (var i = 0; i < dictation.cards.length; i++) i]..shuffle(random ?? Random());
  }

  final Dictation dictation;
  final DictationMode mode;

  /// Tarjetas por colocar (índices de [Dictation.cards]) y colocadas.
  late List<int> bank;
  final placed = <int>[];

  /// Lo escrito con el teclado.
  String typed = '';

  int attempts = 0;
  bool solved = false;
  DictationResult? last;

  /// Pistas usadas (0 a 4): 1 audio lento, 2 cuántas sílabas, 3 la primera,
  /// 4 modelo para copiar.
  int hints = 0;
  static const maxHints = 4;

  /// Errores por tipo (para el progreso).
  final issues = <DictationIssue>[];

  List<String> get built => [for (final i in placed) dictation.cards[i]];

  /// Para las tarjetas de sílabas: una sola tarjeta (se cambia al tocar otra).
  bool get singleCard => dictation.type == DictationType.syllable;

  void place(int card) {
    if (solved || !bank.contains(card)) return;
    if (singleCard && placed.isNotEmpty) bank.add(placed.removeLast());
    bank.remove(card);
    placed.add(card);
  }

  void unplace(int slot) {
    if (solved || slot < 0 || slot >= placed.length) return;
    bank.add(placed.removeAt(slot));
  }

  bool get ready => mode == DictationMode.keyboard ? typed.trim().isNotEmpty : placed.isNotEmpty;

  DictationResult check() {
    attempts++;
    final r = mode == DictationMode.keyboard
        ? DictationChecker.check(dictation, typed)
        : DictationChecker.checkCards(dictation, built);
    last = r;
    if (r.correct) {
      solved = true;
    } else {
      issues.add(r.issue);
    }
    return r;
  }

  /// Siguiente pista (devuelve cuál se dio, de 1 a 4).
  int nextHint() {
    if (hints < maxHints) hints++;
    // En tarjetas, la pista 3 coloca la primera parte (no en sílabas, donde
    // sería la respuesta entera).
    if (hints >= 3 && mode != DictationMode.keyboard && dictation.target.length > 1) _placeFirst();
    last = null;
    return hints;
  }

  /// En tarjetas, la pista 3 coloca la primera tarjeta correcta.
  void _placeFirst() {
    final first = dictation.target.first;
    if (placed.isNotEmpty && dictation.cards[placed.first] == first) return;
    while (placed.isNotEmpty) {
      bank.add(placed.removeLast());
    }
    final i = bank.firstWhere((c) => dictation.cards[c] == first, orElse: () => -1);
    if (i >= 0) place(i);
  }

  /// Acertado sin ninguna pista ni error.
  bool get independent => solved && hints == 0;
  bool get firstTry => solved && attempts == 1 && hints == 0;
}
