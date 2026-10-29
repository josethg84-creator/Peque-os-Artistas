import 'dart:math';

/// Resultado de elegir una opción.
enum AnswerResult { correct, tryAgain, ignored }

class QuizQuestion<T> {
  QuizQuestion(this.target, this.options);
  final T target;
  final List<T> options;
}

/// Motor de preguntas compartido por colores, formas y animales.
///
/// Cada pregunta tiene una respuesta correcta y varias opciones. Un error no
/// resta nada: la opción elegida se marca y el niño vuelve a intentarlo hasta
/// acertar. La partida termina tras [questionCount] preguntas acertadas.
class QuizGame<T> {
  QuizGame({
    required List<T> pool,
    required this.optionCount,
    required this.questionCount,
    List<T> Function(T target, List<T> pool)? preferredDistractors,
    Random? random,
  }) : _pool = List.unmodifiable(pool),
       _preferred = preferredDistractors,
       _random = random ?? Random() {
    if (pool.length < optionCount) {
      throw ArgumentError('No hay suficientes elementos para $optionCount opciones');
    }
    restart();
  }

  final List<T> _pool;
  final int optionCount;
  final int questionCount;
  final List<T> Function(T target, List<T> pool)? _preferred;
  final Random _random;

  late List<T> _targets;
  int _index = 0;
  late QuizQuestion<T> _question;
  final _wrong = <T>{};
  bool _answered = false;
  int _mistakes = 0;
  int _firstTry = 0;

  QuizQuestion<T> get question => _question;

  /// Índice de la pregunta actual (0..questionCount-1).
  int get index => _index;

  /// La pregunta actual ya se acertó (se muestra la explicación y «Siguiente»).
  bool get answered => _answered;
  bool get isLastQuestion => _index == questionCount - 1;
  bool get isFinished => _answered && isLastQuestion;

  /// Opciones ya intentadas sin acierto en esta pregunta.
  Set<T> get wrongAnswers => Set.unmodifiable(_wrong);

  /// Errores de la partida (solo informativo; nunca se penaliza).
  int get mistakes => _mistakes;

  /// Preguntas acertadas al primer intento.
  int get firstTryCorrect => _firstTry;

  void restart() {
    // Objetivos sin repetir mientras sea posible.
    final shuffled = [..._pool]..shuffle(_random);
    _targets = [for (var i = 0; i < questionCount; i++) shuffled[i % shuffled.length]];
    _index = 0;
    _mistakes = 0;
    _firstTry = 0;
    _prepare();
  }

  void _prepare() {
    final target = _targets[_index];
    final others = _pool.where((e) => e != target).toList()..shuffle(_random);
    final preferred = (_preferred?.call(target, _pool) ?? const []).where((e) => e != target).toList()
      ..shuffle(_random);
    final options = <T>[target];
    for (final e in [...preferred, ...others]) {
      if (options.length == optionCount) break;
      if (!options.contains(e)) options.add(e);
    }
    options.shuffle(_random);
    _question = QuizQuestion(target, List.unmodifiable(options));
    _wrong.clear();
    _answered = false;
  }

  AnswerResult answer(T option) {
    if (_answered || !_question.options.contains(option) || _wrong.contains(option)) {
      return AnswerResult.ignored;
    }
    if (option == _question.target) {
      _answered = true;
      if (_wrong.isEmpty) _firstTry++;
      return AnswerResult.correct;
    }
    _wrong.add(option);
    _mistakes++;
    return AnswerResult.tryAgain;
  }

  /// Pasa a la siguiente pregunta. Devuelve false si la partida ya terminó.
  bool next() {
    if (!_answered || isLastQuestion) return false;
    _index++;
    _prepare();
    return true;
  }
}
