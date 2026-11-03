import 'speech_content.dart';

/// «Yo puedo expresarme» (`assets/speech/expressions.json`): necesidades,
/// emociones y el constructor QUIÉN + QUÉ SIENTE + POR QUÉ. Las emociones no se
/// presentan como buenas o malas: todas son importantes.

/// Un motivo, en primera persona («porque juego con mi perro») y para otra
/// persona («porque juega con su perro»).
class EmotionReason {
  const EmotionReason({required this.id, required this.me, required this.other, required this.picture});
  final String id;
  final String me;
  final String other;
  final SpeechPicture picture;
}

class EmotionInfo {
  const EmotionInfo({
    required this.id,
    required this.name,
    required this.face,
    required this.masculine,
    required this.feminine,
    required this.examples,
    required this.reasons,
  });

  final String id;

  /// «Alegría».
  final String name;

  /// Emoción del dibujo de la cara (`feliz`, `triste`…).
  final String face;

  /// «contento» / «contenta».
  final String masculine;
  final String feminine;

  /// Frases de ejemplo («Estoy contento porque voy a jugar.»).
  final List<String> examples;
  final List<EmotionReason> reasons;
}

/// QUIÉN siente: «Yo», «Mi amigo», «Mamá»…
class ExpressionWho {
  const ExpressionWho({
    required this.id,
    required this.text,
    required this.verb,
    required this.feminine,
    required this.firstPerson,
    required this.picture,
  });
  final String id;
  final String text;

  /// «estoy» o «está».
  final String verb;
  final bool feminine;
  final bool firstPerson;
  final SpeechPicture picture;
}

class ExpressionContent {
  const ExpressionContent({this.needs = const [], this.emotions = const [], this.who = const []});

  final List<SpeechPhrase> needs;
  final List<EmotionInfo> emotions;
  final List<ExpressionWho> who;

  /// «Yo estoy feliz porque juego con mi perro.», con el género y la persona
  /// correctos.
  static String sentence(ExpressionWho who, EmotionInfo emotion, EmotionReason reason) =>
      '${who.text} ${who.verb} ${who.feminine ? emotion.feminine : emotion.masculine} '
      '${who.firstPerson ? reason.me : reason.other}.';

  static ExpressionContent fromJson(Map<String, dynamic>? json) {
    if (json == null) return const ExpressionContent();
    List<Map<String, dynamic>> list(Object? v) => [
      ...(v as List? ?? const []).whereType<Map<String, dynamic>>(),
    ];
    return ExpressionContent(
      needs: [for (final n in list(json['needs'])) ?SpeechPhrase.fromJson(n)],
      emotions: [
        for (final e in list(json['emotions']))
          if ((e['id'], e['name'], e['face'], e['masculine'], e['feminine']) case (
            final String id,
            final String name,
            final String face,
            final String masculine,
            final String feminine,
          ))
            EmotionInfo(
              id: id,
              name: name,
              face: face,
              masculine: masculine,
              feminine: feminine,
              examples: [...(e['examples'] as List? ?? const []).whereType<String>()],
              reasons: [
                for (final r in list(e['reasons']))
                  if ((r['id'], r['me'], r['other'], SpeechPicture.fromJson(r['picture'])) case (
                    final String rid,
                    final String me,
                    final String other,
                    final SpeechPicture picture,
                  ))
                    EmotionReason(id: rid, me: me, other: other, picture: picture),
              ],
            ),
      ],
      who: [
        for (final w in list(json['who']))
          if ((w['id'], w['text'], w['verb'], SpeechPicture.fromJson(w['picture'])) case (
            final String id,
            final String text,
            final String verb,
            final SpeechPicture picture,
          ))
            ExpressionWho(
              id: id,
              text: text,
              verb: verb,
              feminine: w['feminine'] == true,
              firstPerson: w['first_person'] == true,
              picture: picture,
            ),
      ],
    );
  }
}
