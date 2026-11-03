import 'speech_activities.dart';
import 'speech_content.dart';

/// «Escucho y respondo» (`assets/speech/listening.json`): ejercicios de
/// comprensión oral en niveles. Se oye una frase (o se mira un dibujo) y se
/// responde tocando un dibujo; las instrucciones de dos pasos se tocan en orden.

enum ListeningType {
  quien('quien', '¿Quién?'),
  donde('donde', '¿Dónde?'),
  objeto('objeto', '¿Para qué sirve?'),
  secuencia('secuencia', '¿Qué pasa antes y después?'),
  instruccion('instruccion', 'Instrucciones de dos pasos'),
  emocion('emocion', '¿Cómo se siente?'),
  escena('escena', 'Mira el dibujo');

  const ListeningType(this.id, this.title);
  final String id;
  final String title;

  static ListeningType? byId(Object? id) {
    for (final t in values) {
      if (t.id == id) return t;
    }
    return null;
  }
}

class ListeningLevel {
  const ListeningLevel(this.level, this.title, this.subtitle);
  final int level;
  final String title;
  final String subtitle;
}

class ListeningExercise {
  const ListeningExercise({
    required this.id,
    required this.level,
    required this.type,
    required this.say,
    required this.question,
    required this.options,
    required this.answer,
    this.steps,
    this.scene,
  });

  final String id;
  final int level;
  final ListeningType type;

  /// Lo que se escucha («El gato duerme en la cama.»).
  final String say;

  /// La pregunta («¿Quién duerme?»).
  final String question;
  final List<QuizOption> options;
  final int answer;
  final List<int>? steps;
  final SpeechPicture? scene;

  /// Lo que dice Lolo al presentarlo: la frase y la pregunta (en una
  /// instrucción, solo la instrucción).
  String get spoken => steps != null ? say : '$say $question';

  QuizQuestion toQuestion() => QuizQuestion(
    instruction: steps != null ? say : question,
    spoken: steps != null ? 'Escucha bien: $say' : (scene != null ? spoken : 'Escucha bien: $spoken'),
    options: options,
    answer: answer,
    scene: scene,
    steps: steps,
    afterCorrect: steps != null ? '¡Muy bien! Lo hiciste en orden.' : '¡Sí! ${options[answer].label}.',
  );

  static ListeningExercise? fromJson(Map<String, dynamic> json) {
    final id = json['id'], level = json['level'], say = json['say'], question = json['question'];
    final type = ListeningType.byId(json['type']);
    if (id is! String || level is! int || say is! String || question is! String || type == null) return null;
    final options = [
      for (final o in (json['options'] as List? ?? const []))
        if (o is Map<String, dynamic>)
          if ((o['text'], SpeechPicture.fromJson(o['picture'])) case (
            final String text,
            final SpeechPicture p,
          ))
            QuizOption(label: text, picture: p),
    ];
    if (options.length < 2 || options.length != (json['options'] as List).length) return null;
    final rawSteps = json['steps'];
    List<int>? steps;
    if (rawSteps is List) {
      steps = [
        for (final i in rawSteps)
          if (i is int && i >= 0 && i < options.length) i,
      ];
      final valid =
          steps.length >= 2 && steps.length == rawSteps.length && steps.toSet().length == steps.length;
      if (!valid) return null;
    }
    final answer = steps?.last ?? json['answer'];
    if (answer is! int || answer < 0 || answer >= options.length) return null;
    final scene = json['scene'] == null ? null : SpeechPicture.fromJson(json['scene']);
    if (json['scene'] != null && scene == null) return null;
    return ListeningExercise(
      id: id,
      level: level,
      type: type,
      say: say,
      question: question,
      options: options,
      answer: answer,
      steps: steps,
      scene: scene,
    );
  }
}

class ListeningContent {
  const ListeningContent({this.levels = const [], this.exercises = const []});

  final List<ListeningLevel> levels;
  final List<ListeningExercise> exercises;

  List<ListeningExercise> ofLevel(int level) => [
    for (final e in exercises)
      if (e.level == level) e,
  ];

  factory ListeningContent.fromJson(Map<String, dynamic>? json) {
    final ids = <String>{};
    final exercises = [
      for (final e in (json?['exercises'] as List? ?? const []))
        if (e is Map<String, dynamic>)
          if (ListeningExercise.fromJson(e) case final ex? when ids.add(ex.id)) ex,
    ];
    final levels = [
      for (final l in (json?['levels'] as List? ?? const []))
        if (l is Map<String, dynamic>)
          if ((l['level'], l['title'], l['subtitle']) case (final int n, final String t, final String s))
            if (exercises.any((e) => e.level == n)) ListeningLevel(n, t, s),
    ];
    return ListeningContent(levels: levels, exercises: exercises);
  }
}
