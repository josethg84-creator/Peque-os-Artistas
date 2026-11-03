import 'dart:math';

import 'speech_content.dart';

/// Una opción de respuesta: con dibujo y/o un signo grande («¿?», «.»).
class QuizOption {
  const QuizOption({required this.label, this.picture, this.badge, this.glyph, this.showLabel = true});

  final String label;
  final SpeechPicture? picture;

  /// Dibujito pequeño en la esquina (la acción que hace la persona).
  final SpeechPicture? badge;

  /// Texto grande en lugar de dibujo («como», «¿?»).
  final String? glyph;

  /// En «escucha y señala» no se muestra el nombre: hay que oírlo.
  final bool showLabel;
}

/// Una pregunta. [instruction] se dice en voz alta y se muestra; [prompt] es
/// el texto grande opcional («El niño come una ___.»). [afterCorrect] se dice
/// al acertar (por ejemplo, la oración completa).
class QuizQuestion {
  const QuizQuestion({
    required this.instruction,
    required this.options,
    required this.answer,
    this.prompt,
    this.spoken,
    this.afterCorrect,
  });

  final String instruction;
  final String? prompt;

  /// Lo que se dice al presentar la pregunta (por defecto, [instruction]).
  final String? spoken;
  final List<QuizOption> options;
  final int answer;
  final String? afterCorrect;

  String get speech => spoken ?? instruction;
}

/// Actividades de «Aprendo a Hablar» con preguntas. [kind] es la clave del
/// progreso.
enum SpeechQuizKind {
  complete('completar', 'Completa la oración'),
  questionOrStatement('pregunta', '¿Pregunta o afirmación?'),
  verbs('verbos', 'Juegos de verbos'),
  comprehension('comprension', 'Escucho y comprendo');

  const SpeechQuizKind(this.kind, this.title);
  final String kind;
  final String title;

  List<QuizQuestion> build(SpeechContent c, Random r) => switch (this) {
    complete => completeQuestions(c, r),
    questionOrStatement => questionOrStatementQuestions(c, r),
    verbs => verbQuestions(c, r),
    comprehension => comprehensionQuestions(c, r),
  };
}

/// Pone la respuesta correcta entre las demás en un sitio al azar.
QuizQuestion _shuffled(Random r, QuizQuestion q) {
  final order = List.generate(q.options.length, (i) => i)..shuffle(r);
  return QuizQuestion(
    instruction: q.instruction,
    prompt: q.prompt,
    spoken: q.spoken,
    afterCorrect: q.afterCorrect,
    options: [for (final i in order) q.options[i]],
    answer: order.indexOf(q.answer),
  );
}

List<T> _pick<T>(Random r, List<T> list, int n) => ([...list]..shuffle(r)).take(n).toList();

/// «Completa la oración»: la palabra que falta, eligiendo entre dibujos.
List<QuizQuestion> completeQuestions(SpeechContent c, Random r, {int count = 6}) => [
  for (final item in _pick(r, c.sentences.complete, count))
    _shuffled(
      r,
      QuizQuestion(
        instruction: '¿Qué palabra falta?',
        prompt: '${item.before} ___${item.after}',
        spoken: '${item.before}… ¿Qué palabra falta?',
        options: [for (final o in item.options) QuizOption(label: o.text, picture: o.picture)],
        answer: item.options.indexWhere((o) => o.text == item.answer),
        afterCorrect: item.full,
      ),
    ),
];

/// «¿Pregunta o afirmación?»: se oye la oración (con su entonación) y se elige.
List<QuizQuestion> questionOrStatementQuestions(SpeechContent c, Random r, {int count = 6}) {
  final s = c.sentences;
  if (s.subjects.isEmpty || s.actions.isEmpty) return const [];
  const options = [QuizOption(label: 'Afirmación', glyph: '.'), QuizOption(label: 'Pregunta', glyph: '¿?')];
  // La mitad son preguntas, en orden al azar.
  final kinds = [for (var i = 0; i < count; i++) i.isOdd]..shuffle(r);
  return [
    for (final question in kinds)
      () {
        final subject = s.subjects[r.nextInt(s.subjects.length)];
        final action = s.actions[r.nextInt(s.actions.length)];
        final complement = action.complements[r.nextInt(action.complements.length)];
        final base = '${subject.text} ${action.text} ${complement.text}';
        final sentence = question ? '¿$base?' : '$base.';
        return QuizQuestion(
          instruction: '¿Es una pregunta o una afirmación?',
          prompt: sentence,
          spoken: '$sentence … ¿Es una pregunta o una afirmación?',
          options: options,
          answer: question ? 1 : 0,
          afterCorrect: question ? '¡Sí! Es una pregunta.' : '¡Sí! Es una afirmación.',
        );
      }(),
  ];
}

/// «Juegos de verbos»: completa con la forma del verbo, elige la acción,
/// ¿quién está…? y escucha y señala, mezclados.
List<QuizQuestion> verbQuestions(SpeechContent c, Random r, {int count = 8}) {
  final verbs = c.verbs;
  if (verbs.length < 3) return const [];
  final questions = <QuizQuestion>[];
  const persons = [VerbPerson.yo, VerbPerson.tu, VerbPerson.el, VerbPerson.ella, VerbPerson.nosotros];
  for (var i = 0; i < count; i++) {
    final three = _pick(r, verbs, 3);
    final v = three.first;
    switch (i % 4) {
      case 0: // Completa la oración con la forma correcta.
        final p = persons[r.nextInt(persons.length)];
        final forms = {v.form(p), ...persons.map(v.form)}.take(3).toList();
        questions.add(
          _shuffled(
            r,
            QuizQuestion(
              instruction: 'Completa la oración',
              prompt: '${p.label} ___ ${v.complement}.',
              spoken: '${p.label}… ${v.complement}. ¿Cuál va?',
              options: [for (final f in forms) QuizOption(label: f, glyph: f)],
              answer: 0,
              afterCorrect: v.sentence(p),
            ),
          ),
        );
      case 1: // Elige la acción (con el nombre escrito).
        questions.add(
          _shuffled(
            r,
            QuizQuestion(
              instruction: 'Elige la acción: ${v.infinitive}',
              spoken: 'Elige la acción: ${v.infinitive}',
              options: [for (final x in three) QuizOption(label: x.infinitive, picture: x.picture)],
              answer: 0,
              afterCorrect: '¡Muy bien! ${v.infinitive[0].toUpperCase()}${v.infinitive.substring(1)}.',
            ),
          ),
        );
      case 2: // ¿Quién está…?
        final people = _pick(r, const [VerbPerson.el, VerbPerson.ella, VerbPerson.nosotros], 3);
        const name = {
          VerbPerson.el: 'El niño',
          VerbPerson.ella: 'La niña',
          VerbPerson.nosotros: 'Los amigos',
        };
        questions.add(
          _shuffled(
            r,
            QuizQuestion(
              instruction: '¿Quién está ${v.gerund}?',
              options: [
                for (final (k, p) in people.indexed)
                  QuizOption(label: name[p]!, picture: IconPicture(p.icon, null), badge: three[k].picture),
              ],
              answer: 0,
              afterCorrect: people.first == VerbPerson.nosotros
                  ? 'Los amigos están ${v.gerund}.'
                  : '${name[people.first]} está ${v.gerund}.',
            ),
          ),
        );
      default: // Escucha y señala (sin el nombre escrito).
        questions.add(
          _shuffled(
            r,
            QuizQuestion(
              instruction: 'Escucha y señala',
              spoken: 'Escucha y señala: ${v.infinitive}',
              options: [
                for (final x in three) QuizOption(label: x.infinitive, picture: x.picture, showLabel: false),
              ],
              answer: 0,
              afterCorrect: '¡Sí! ${v.infinitive[0].toUpperCase()}${v.infinitive.substring(1)}.',
            ),
          ),
        );
    }
  }
  return questions;
}

/// «Escucho y comprendo»: se oye una palabra o una frase y se toca su dibujo.
List<QuizQuestion> comprehensionQuestions(SpeechContent c, Random r, {int count = 8}) {
  final questions = <QuizQuestion>[];
  final categories = c.categories.where((cat) => cat.words.length >= 3).toList();
  for (var i = 0; i < count; i++) {
    if (i.isOdd && c.phrases.length >= 3) {
      final three = _pick(r, c.phrases, 3);
      final p = three.first;
      questions.add(
        _shuffled(
          r,
          QuizQuestion(
            instruction: 'Escucha la frase y toca su dibujo',
            spoken: 'Escucha: ${p.text} ¿Qué dibujo va con la frase?',
            options: [for (final x in three) QuizOption(label: x.text, picture: x.picture, showLabel: false)],
            answer: 0,
            afterCorrect: p.text,
          ),
        ),
      );
    } else if (categories.isNotEmpty) {
      final cat = categories[r.nextInt(categories.length)];
      final three = _pick(r, cat.words, 3);
      final w = three.first;
      // Las cosas llevan artículo («¿Dónde está el perro?»); las acciones y
      // emociones no («Señala: correr»).
      final article = w.article;
      final ask = article == null
          ? 'Señala: ${w.text}'
          : (article.endsWith('s') ? '¿Dónde están $article ${w.text}?' : '¿Dónde está $article ${w.text}?');
      questions.add(
        _shuffled(
          r,
          QuizQuestion(
            instruction: ask,
            spoken: ask,
            options: [for (final x in three) QuizOption(label: x.text, picture: x.picture, showLabel: false)],
            answer: 0,
            afterCorrect: '¡Sí! ${w.text[0].toUpperCase()}${w.text.substring(1)}.',
          ),
        ),
      );
    }
  }
  return questions;
}
