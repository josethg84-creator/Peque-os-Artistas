import 'speech_content.dart';

/// «Ahora cuéntamelo tú» (`assets/speech/tell.json`): secuencias de dibujos
/// que el niño ordena y cuenta eligiendo frases.

class TellStep {
  const TellStep({required this.picture, required this.phrase, required this.question});
  final SpeechPicture picture;

  /// Lo que pasa en el dibujo («La niña planta la semilla.»).
  final String phrase;

  /// La pregunta de Lolo para ayudar a contarlo.
  final String question;
}

class TellSequence {
  const TellSequence({required this.id, required this.title, required this.steps, required this.ending});
  final String id;
  final String title;

  /// En su orden correcto.
  final List<TellStep> steps;

  /// La historia en una oración («La niña plantó una semilla, la regó…»).
  final String ending;

  /// La historia completa, paso a paso.
  String get story => steps.map((s) => s.phrase).join(' ');

  static TellSequence? fromJson(Map<String, dynamic> json) {
    final id = json['id'], title = json['title'], ending = json['ending'];
    if (id is! String || title is! String || ending is! String) return null;
    final steps = [
      for (final s in (json['steps'] as List? ?? const []))
        if (s is Map<String, dynamic>)
          if ((SpeechPicture.fromJson(s['picture']), s['phrase'], s['question']) case (
            final SpeechPicture picture,
            final String phrase,
            final String question,
          ))
            TellStep(picture: picture, phrase: phrase, question: question),
    ];
    if (steps.length < 3 || steps.length > 4) return null;
    return TellSequence(id: id, title: title, steps: steps, ending: ending);
  }
}

List<TellSequence> parseTell(Map<String, dynamic>? json) {
  final ids = <String>{};
  return [
    for (final s in (json?['sequences'] as List? ?? const []))
      if (s is Map<String, dynamic>)
        if (TellSequence.fromJson(s) case final seq? when ids.add(seq.id)) seq,
  ];
}
