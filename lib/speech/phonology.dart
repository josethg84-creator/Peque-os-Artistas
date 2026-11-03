/// «Sílabas y sonidos» (`assets/speech/phonology.json`): parejas de palabras
/// que empiezan igual o que riman (por ids del vocabulario).
class SoundSet {
  const SoundSet({required this.target, required this.answer, required this.others});

  /// La palabra modelo («mamá»).
  final String target;

  /// La que empieza igual o rima («mariposa»).
  final String answer;

  /// Las que no («perro», «sol»).
  final List<String> others;

  static SoundSet? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final target = json['target'], answer = json['answer'];
    final others = [...(json['others'] as List? ?? const []).whereType<String>()];
    if (target is! String || answer is! String || others.isEmpty) return null;
    return SoundSet(target: target, answer: answer, others: others);
  }
}

class PhonologyContent {
  const PhonologyContent({this.starts = const [], this.rhymes = const []});

  final List<SoundSet> starts;
  final List<SoundSet> rhymes;

  factory PhonologyContent.fromJson(Map<String, dynamic>? json) => PhonologyContent(
    starts: [for (final s in (json?['starts'] as List? ?? const [])) ?SoundSet.fromJson(s)],
    rhymes: [for (final s in (json?['rhymes'] as List? ?? const [])) ?SoundSet.fromJson(s)],
  );
}
