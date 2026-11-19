import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../learning/widgets/question_progress.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/reading_voice.dart';
import '../achievement_data.dart';
import '../reading_progress.dart';
import '../sentences.dart';
import '../widgets/reading_widgets.dart';
import '../widgets/sentence_widgets.dart';
import 'reading_sentences_screen.dart';

/// Comprensión, «Ordena la oración» y «Escucha y elige». Sin castigos: tras un
/// error se puede volver a escuchar, pedir una pista y volver a intentarlo.
class SentenceGameScreen extends StatelessWidget {
  const SentenceGameScreen({super.key, required this.args, this.seed});

  final SentenceGameArgs args;

  /// Para pruebas: orden fijo.
  final int? seed;

  static const praise = '¡Muy bien!';
  static const tryAgain = '¡Casi! Escucha otra vez y vuelve a intentarlo.';

  /// Oraciones por partida.
  static const sessionLength = 8;

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: args.activity.title,
      titleIcon: args.activity.icon,
      accent: ReadingSentencesScreen.color,
      trailing: const ReadingHomeButton(),
      body: SentenceCatalogBuilder(
        builder: (context, content) => _Game(content: content, args: args, seed: seed),
      ),
    );
  }
}

class _Game extends StatefulWidget {
  const _Game({required this.content, required this.args, this.seed});

  final SentenceCatalog content;
  final SentenceGameArgs args;
  final int? seed;

  @override
  State<_Game> createState() => _GameState();
}

class _GameState extends State<_Game> {
  static const color = ReadingSentencesScreen.color;

  ReadingVoice? _voice;
  late ReadingController _progress;
  late Random _random;
  late List<ReadingSentence> _list;
  int _index = 0;
  int _firstTry = 0;
  bool _finished = false;
  bool _wrong = false;

  /// Se escuchó la oración (o alguna palabra) antes de responder: entonces no
  /// cuenta como leída sin ayuda.
  bool _listened = false;
  bool _showHint = false;
  int? _highlight;

  ComprehensionRound? _question;
  OrderRound? _order;
  ListenSelectRound? _pick;

  SentenceActivity get activity => widget.args.activity;
  ReadingSentence get sentence => _list[_index];
  bool get _solved => switch (activity) {
    SentenceActivity.question => _question!.solved,
    SentenceActivity.order => _order!.complete && !_wrong && _orderSolved,
    SentenceActivity.listen => _pick!.solved,
    SentenceActivity.read => true,
  };
  bool _orderSolved = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_voice != null) return;
    final services = AppServices.of(context);
    _voice = ReadingVoice(services.audio);
    _progress = services.reading;
    _random = Random(widget.seed);
    _start();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _list.isEmpty) return;
      if (activity == SentenceActivity.listen) _listen();
      if (activity == SentenceActivity.question) unawaited(_voice!.sayText(sentence.question.text));
    });
  }

  @override
  void dispose() {
    _voice?.dispose();
    super.dispose();
  }

  bool _fits(ReadingSentence s) => switch (activity) {
    SentenceActivity.order => s.orderable,
    SentenceActivity.listen => s.listenOptions.length == 2,
    _ => true,
  };

  void _start() {
    final one = widget.args.sentenceId == null ? null : widget.content.byId[widget.args.sentenceId];
    if (one != null) {
      _list = [one];
    } else {
      final all = [
        for (final s in widget.content.ofLevel(widget.args.level))
          if (_fits(s)) s,
      ]..shuffle(_random);
      // Primero las que aún no se han hecho en esta actividad.
      final pending = [
        for (final s in all)
          if (!_progress.isCompleted(s.id, activity.mode)) s,
      ];
      final done = [
        for (final s in all)
          if (_progress.isCompleted(s.id, activity.mode)) s,
      ];
      _list = [...pending, ...done].take(SentenceGameScreen.sessionLength).toList();
    }
    _index = 0;
    _firstTry = 0;
    _finished = false;
    if (_list.isNotEmpty) _newRound();
  }

  void _newRound() {
    final s = sentence;
    _wrong = false;
    _listened = false;
    _showHint = false;
    _highlight = null;
    _orderSolved = false;
    _question = activity == SentenceActivity.question ? ComprehensionRound(s, random: _random) : null;
    _order = activity == SentenceActivity.order ? OrderRound(s, random: _random) : null;
    _pick = activity == SentenceActivity.listen
        ? ListenSelectRound(s, widget.content, random: _random)
        : null;
  }

  void _listen([ReadingSpeed speed = ReadingSpeed.normal]) {
    _listened = true;
    final s = sentence;
    unawaited(() async {
      final heard = await _voice!.playSentence(
        s,
        speed: speed,
        onWord: (i) {
          if (mounted) setState(() => _highlight = i);
        },
      );
      if (heard && mounted) _progress.recordSentenceHeard(s.id);
    }());
  }

  void _sayWord(int i) {
    _listened = true;
    final w = sentence.words[i];
    _progress.recordWordPlayed(w.text);
    setState(() => _highlight = i);
    unawaited(() async {
      await _voice!.play(w.audio);
      if (mounted && _highlight == i) setState(() => _highlight = null);
    }());
  }

  void _solvedNow({required bool firstTry, required bool usedHints, int mistakes = 0}) {
    if (firstTry) _firstTry++;
    final s = sentence;
    if (activity == SentenceActivity.question) {
      _progress.recordQuestionSolved(
        s.id,
        firstTry: firstTry,
        usedHints: usedHints,
        listenedFirst: _listened,
        mistakes: mistakes,
      );
    } else {
      _progress.recordCompleted(
        s.id,
        activity.mode,
        firstTry: firstTry,
        usedHints: usedHints,
        mistakes: mistakes,
      );
    }
    unawaited(_voice!.sayText(SentenceGameScreen.praise));
  }

  // ------------------------------------------------------------ comprensión
  void _answer(int i) {
    final q = _question!;
    if (q.solved) return;
    _progress.recordSentenceAttempt();
    _progress.recordQuestionAnswered(sentence.id);
    final right = q.choose(i);
    setState(() => _wrong = !right);
    if (right) {
      _solvedNow(firstTry: q.firstTry, usedHints: q.usedHint, mistakes: q.wrongAttempts);
    } else {
      unawaited(_voice!.sayText(SentenceGameScreen.tryAgain));
    }
  }

  void _questionHint() {
    final q = _question!;
    setState(() {
      q.usedHint = true;
      _showHint = true;
    });
    _sayWord(sentence.question.hintWord);
  }

  // ------------------------------------------------------------ ordenar
  void _place(int piece) {
    final o = _order!;
    if (_orderSolved || !o.bank.contains(piece)) return;
    setState(() {
      o.place(piece);
      _wrong = false;
    });
    unawaited(_voice!.play(sentence.words[piece].audio));
  }

  void _unplace(int slot) {
    if (_orderSolved) return;
    setState(() {
      _order!.unplace(slot);
      _wrong = false;
    });
  }

  void _checkOrder() {
    final o = _order!;
    _progress.recordSentenceAttempt();
    final right = o.check();
    setState(() {
      _wrong = !right;
      _orderSolved = right;
    });
    if (right) {
      _solvedNow(firstTry: o.firstTry, usedHints: o.usedHint, mistakes: o.wrongAttempts);
      _listen();
    } else {
      unawaited(_voice!.sayText('¡Casi! Escucha la oración y ordénala otra vez.'));
    }
  }

  void _orderHint() {
    setState(() {
      _order!.hint();
      _wrong = false;
    });
  }

  // ------------------------------------------------------------ escuchar y elegir
  void _pickScene(int i) {
    final p = _pick!;
    if (p.solved) return;
    _progress.recordSentenceAttempt();
    final right = p.choose(i);
    setState(() => _wrong = !right);
    if (right) {
      _solvedNow(firstTry: p.firstTry, usedHints: p.wrongAttempts > 0, mistakes: p.wrongAttempts);
    } else {
      unawaited(_voice!.sayText('Esa no es. Escucha otra vez.'));
    }
  }

  void _next() {
    unawaited(_voice!.stop());
    if (_index == _list.length - 1) {
      setState(() => _finished = true);
      _progress.recordSeries(ReadingModule.sentences);
      unawaited(_voice!.sayText('¡Terminaste! ¡Qué bien lo has hecho!'));
      return;
    }
    setState(() {
      _index++;
      _newRound();
    });
    if (activity == SentenceActivity.listen) _listen();
    if (activity == SentenceActivity.question) unawaited(_voice!.sayText(sentence.question.text));
  }

  void _again() {
    setState(_start);
    if (activity == SentenceActivity.listen) _listen();
  }

  @override
  Widget build(BuildContext context) {
    if (_list.isEmpty) return const Center(child: Text('Todavía no hay oraciones para esta actividad.'));
    return LayoutBuilder(
      builder: (context, box) {
        final wide = box.maxWidth >= 760;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            0,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 900),
              child: _finished ? _summary() : _play(wide),
            ),
          ),
        );
      },
    );
  }

  Widget _summary() {
    final single = widget.args.sentenceId != null;
    return Column(
      children: [
        const SizedBox(height: 20),
        const ReadingCelebration(text: '¡Terminaste! ¡Qué bien lo has hecho!'),
        const SizedBox(height: 16),
        Semantics(
          label: 'Acertaste $_firstTry de ${_list.length} a la primera',
          excludeSemantics: true,
          child: QuestionProgress(done: _firstTry, total: _list.length, label: 'Estrella'),
        ),
        const SizedBox(height: 20),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
            if (!single)
              SizedBox(
                width: 260,
                child: BigActionButton(
                  label: 'Jugar otra vez',
                  icon: Icons.replay_rounded,
                  color: AppColors.sky,
                  onPressed: _again,
                ),
              ),
            SizedBox(
              width: 260,
              child: BigActionButton(
                label: 'Volver',
                icon: Icons.arrow_back_rounded,
                color: AppColors.grape,
                onPressed: () => Navigator.of(context).maybePop(),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _play(bool wide) {
    return Column(
      children: [
        ReadingVoiceNotice(voice: _voice!),
        Text(
          activity.instruction,
          style: fredoka(22, color: AppColors.ink),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        ReadingProgressBar(done: _index, total: _list.length, label: 'Oraciones', color: color),
        const SizedBox(height: 12),
        switch (activity) {
          SentenceActivity.order => _orderBody(wide),
          SentenceActivity.listen => _listenBody(wide),
          _ => _questionBody(wide),
        },
        const SizedBox(height: 14),
        if (_solved)
          ReadingCelebration(text: SentenceGameScreen.praise)
        else if (_wrong)
          const ReadingTryAgain(text: SentenceGameScreen.tryAgain),
        const SizedBox(height: 12),
        if (_solved)
          SizedBox(
            width: 260,
            child: BigActionButton(
              label: _index == _list.length - 1 ? 'Terminar' : 'Siguiente',
              icon: Icons.arrow_forward_rounded,
              color: AppColors.sky,
              onPressed: _next,
            ),
          ),
      ],
    );
  }

  Widget _listenButtons() => ReadingPlayButtons(
    onPlay: _listen,
    listenLabel: 'Escuchar',
    slowLabel: 'Lento',
    semanticSuffix: ' la oración',
    color: AppColors.sky,
  );

  Widget _questionBody(bool wide) {
    final q = _question!;
    final s = sentence;
    final cardWidth = wide ? 200.0 : 150.0;
    return Column(
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: Color.lerp(color, Colors.white, 0.4)!, width: 3),
          ),
          child: SentenceWords(
            sentence: s,
            color: color,
            highlighted: _highlight,
            hint: _showHint ? s.question.hintWord : null,
            fontSize: wide ? 42 : 32,
            onTapWord: _sayWord,
          ),
        ),
        if (q.solved) ...[
          const SizedBox(height: 12),
          SizedBox(
            height: wide ? 220 : 170,
            child: SentencePicture(sentence: s, color: color),
          ),
        ],
        const SizedBox(height: 14),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Flexible(
              child: Text(
                s.question.text,
                style: fredoka(26, color: AppColors.ink),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(width: 8),
            KidIconButton(
              icon: Icons.volume_up_rounded,
              label: 'Escuchar la pregunta',
              color: AppColors.sun,
              onPressed: () => unawaited(_voice!.sayText(s.question.text)),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final (i, o) in q.options.indexed)
              AnswerCard(
                label: 'Respuesta: ${o.text}',
                text: o.text,
                color: color,
                width: cardWidth,
                wrong: q.wrong.contains(i),
                right: q.solved && i == q.correctIndex,
                onTap: q.solved || q.wrong.contains(i) ? null : () => _answer(i),
                child: SizedBox(
                  height: cardWidth * 0.62,
                  child: SpeechPictureView(picture: o.picture, tint: color),
                ),
              ),
          ],
        ),
        if (q.solved) ...[
          const SizedBox(height: 12),
          Text(
            s.question.explanation,
            style: Theme.of(context).textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
        ] else if (_wrong || q.wrongAttempts > 0) ...[
          const SizedBox(height: 12),
          _listenButtons(),
          const SizedBox(height: 10),
          KidIconButton(
            icon: Icons.lightbulb_rounded,
            label: 'Pista',
            color: AppColors.sun,
            showLabel: true,
            onPressed: _showHint ? null : _questionHint,
          ),
        ] else ...[
          const SizedBox(height: 12),
          Text('¿Necesitas ayuda? Escucha la oración.', style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 6),
          _listenButtons(),
        ],
      ],
    );
  }

  Widget _orderBody(bool wide) {
    final o = _order!;
    final s = sentence;
    final built = [for (final i in o.placed) o.pieces[i]].join(' ');
    return Column(
      children: [
        SizedBox(
          height: wide ? 220 : 160,
          child: SentencePicture(sentence: s, color: color),
        ),
        const SizedBox(height: 10),
        _listenButtons(),
        const SizedBox(height: 14),
        DragTarget<int>(
          onWillAcceptWithDetails: (d) => !_orderSolved && o.bank.contains(d.data),
          onAcceptWithDetails: (d) => _place(d.data),
          builder: (context, candidates, _) => Semantics(
            container: true,
            label: o.placed.isEmpty ? 'Tu oración: vacía. Suelta aquí las palabras' : 'Tu oración: $built',
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              width: double.infinity,
              constraints: const BoxConstraints(minHeight: 90),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: candidates.isNotEmpty ? const Color(0xFFFFF3E0) : const Color(0xFFF6F2FF),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: _orderSolved ? AppColors.leaf : color,
                  width: _orderSolved ? 5 : 3,
                  style: BorderStyle.solid,
                ),
              ),
              child: o.placed.isEmpty
                  ? Center(
                      child: Text(
                        'Toca o arrastra las palabras aquí',
                        style: Theme.of(context).textTheme.bodyLarge,
                        textAlign: TextAlign.center,
                      ),
                    )
                  : Wrap(
                      alignment: WrapAlignment.center,
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final (slot, piece) in o.placed.indexed)
                          WordChip(
                            text: o.pieces[piece],
                            color: _orderSolved ? AppColors.leaf : color,
                            onTap: _orderSolved ? null : () => _unplace(slot),
                          ),
                      ],
                    ),
            ),
          ),
        ),
        if (!_orderSolved && o.placed.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              'Toca una palabra de tu oración para quitarla.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        const SizedBox(height: 14),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final piece in o.bank)
              Draggable<int>(
                data: piece,
                feedback: Material(
                  color: Colors.transparent,
                  child: WordChip(text: o.pieces[piece], color: color),
                ),
                childWhenDragging: Opacity(
                  opacity: 0.3,
                  child: WordChip(text: o.pieces[piece], color: color),
                ),
                child: WordChip(text: o.pieces[piece], color: color, onTap: () => _place(piece)),
              ),
          ],
        ),
        const SizedBox(height: 14),
        if (!_orderSolved)
          Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 12,
            runSpacing: 12,
            children: [
              KidIconButton(
                icon: Icons.lightbulb_rounded,
                label: 'Pista',
                color: AppColors.sun,
                showLabel: true,
                onPressed: _orderHint,
              ),
              SizedBox(
                width: 260,
                child: BigActionButton(
                  label: 'Comprobar',
                  icon: Icons.check_rounded,
                  color: AppColors.leaf,
                  onPressed: o.complete ? _checkOrder : null,
                ),
              ),
            ],
          ),
      ],
    );
  }

  Widget _listenBody(bool wide) {
    final p = _pick!;
    final size = wide ? 230.0 : 150.0;
    return Column(
      children: [
        _listenButtons(),
        const SizedBox(height: 14),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final (i, s) in p.choices.indexed)
              AnswerCard(
                label: 'Dibujo ${i + 1} de ${p.choices.length}',
                color: color,
                width: size + 20,
                wrong: p.wrong.contains(i),
                right: p.solved && i == p.correctIndex,
                onTap: p.solved || p.wrong.contains(i) ? null : () => _pickScene(i),
                child: SizedBox(
                  height: size,
                  child: SentencePicture(sentence: s, color: color),
                ),
              ),
          ],
        ),
        if (p.solved) ...[
          const SizedBox(height: 14),
          SentenceWords(
            sentence: p.sentence,
            color: color,
            highlighted: _highlight,
            fontSize: wide ? 40 : 30,
          ),
        ],
      ],
    );
  }
}
