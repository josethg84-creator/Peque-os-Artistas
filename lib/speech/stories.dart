import 'speech_activities.dart';
import 'speech_content.dart';

/// Cuentos de «Lolo me cuenta un cuento» (`assets/speech/stories.json`).

class StoryCharacter {
  const StoryCharacter(this.name, this.picture);
  final String name;
  final SpeechPicture picture;
}

class StoryScene {
  const StoryScene(this.text, this.picture);
  final String text;

  /// Ilustración propia de la escena.
  final SpeechPicture picture;
}

class Story {
  const Story({
    required this.id,
    required this.title,
    required this.category,
    required this.cover,
    required this.characters,
    required this.scenes,
    required this.questions,
    required this.order,
  });

  final String id;
  final String title;
  final String category;
  final SpeechPicture cover;
  final List<StoryCharacter> characters;
  final List<StoryScene> scenes;

  /// Preguntas de comprensión (con dibujos).
  final List<QuizQuestion> questions;

  /// Índices de las escenas que se ordenan al final (en su orden correcto).
  final List<int> order;

  /// Todo el cuento seguido (para leerlo de una vez).
  String get fullText => scenes.map((s) => s.text).join(' ');

  static Story? fromJson(Map<String, dynamic> json) {
    final id = json['id'], title = json['title'], category = json['category'];
    final cover = SpeechPicture.fromJson(json['cover']);
    if (id is! String || title is! String || category is! String || cover == null) return null;
    final scenes = [
      for (final s in (json['scenes'] as List? ?? const []))
        if (s is Map<String, dynamic>)
          if ((s['text'], SpeechPicture.fromJson(s['picture'])) case (
            final String text,
            final SpeechPicture p,
          ))
            StoryScene(text, p),
    ];
    final questions = <QuizQuestion>[];
    for (final q in (json['questions'] as List? ?? const [])) {
      if (q is! Map<String, dynamic> || q['question'] is! String || q['answer'] is! int) continue;
      final options = [
        for (final o in (q['options'] as List? ?? const []))
          if (o is Map<String, dynamic>)
            if ((o['text'], SpeechPicture.fromJson(o['picture'])) case (
              final String text,
              final SpeechPicture p,
            ))
              QuizOption(label: text, picture: p),
      ];
      final answer = q['answer'] as int;
      if (options.length < 2 || answer < 0 || answer >= options.length) continue;
      questions.add(
        QuizQuestion(
          instruction: q['question'] as String,
          options: options,
          answer: answer,
          afterCorrect: '¡Sí! ${options[answer].label}.',
        ),
      );
    }
    final order = [
      for (final i in (json['order'] as List? ?? const []))
        if (i is int && i >= 0 && i < scenes.length) i,
    ];
    if (scenes.length < 3 || questions.isEmpty) return null;
    return Story(
      id: id,
      title: title,
      category: category,
      cover: cover,
      characters: [
        for (final c in (json['characters'] as List? ?? const []))
          if (c is Map<String, dynamic>)
            if ((c['name'], SpeechPicture.fromJson(c['picture'])) case (
              final String n,
              final SpeechPicture p,
            ))
              StoryCharacter(n, p),
      ],
      scenes: scenes,
      questions: questions,
      order: order.length >= 3 ? order : [0, scenes.length ~/ 2, scenes.length - 1],
    );
  }
}

List<Story> parseStories(Map<String, dynamic>? json) {
  final ids = <String>{};
  return [
    for (final s in (json?['stories'] as List? ?? const []))
      if (s is Map<String, dynamic>)
        if (Story.fromJson(s) case final story? when ids.add(story.id)) story,
  ];
}
