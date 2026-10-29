import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../services/app_services.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/learning_audio.dart';
import '../games/quiz_game.dart';
import '../learning_content.dart';
import '../learning_level.dart';
import '../quiz_specs.dart';
import '../rewards.dart';
import '../widgets/activity_complete.dart';
import '../widgets/answer_option.dart';
import '../widgets/feedback_panel.dart';
import '../widgets/instruction_card.dart';
import '../widgets/question_progress.dart';

/// Pantalla común de los juegos de preguntas (colores, formas y animales).
class QuizGameScreen<T> extends StatefulWidget {
  const QuizGameScreen({super.key, required this.spec, this.seed});

  final QuizSpec<T> spec;

  /// Semilla para resultados reproducibles en pruebas.
  final int? seed;

  @override
  State<QuizGameScreen<T>> createState() => _QuizGameScreenState<T>();
}

class _QuizGameScreenState<T> extends State<QuizGameScreen<T>> {
  static const _praise = ['¡Muy bien!', '¡Lo encontraste!', '¡Genial!', '¡Excelente!'];

  late QuizGame<T> _game;
  late LearningLevel _level;
  bool _showTryAgain = false;
  bool _finished = false;
  bool _recorded = false;
  List<Reward> _newRewards = const [];
  late AppServices _services;
  bool _started = false;
  int _rounds = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _services = AppServices.of(context);
    if (!_started) {
      _started = true;
      _newGame();
    }
  }

  void _newGame() {
    _level = _services.learning.settings.level;
    final size = quizSizeFor(_level);
    final pool = widget.spec.pool(_level);
    _game = QuizGame<T>(
      pool: pool,
      optionCount: size.options.clamp(2, pool.length),
      questionCount: size.questions,
      preferredDistractors: _level == LearningLevel.advanced ? (t, _) => widget.spec.similarTo(t) : null,
      random: widget.seed == null ? null : Random(widget.seed! + _rounds++),
    );
    _finished = false;
    _recorded = false;
    _showTryAgain = false;
    _newRewards = const [];
    _sayInstruction();
  }

  void _sayInstruction() => unawaited(_services.audio.say(widget.spec.instruction(_game.question.target)));

  void _choose(T option) {
    final result = _game.answer(option);
    if (result == AnswerResult.ignored) return;
    final audio = _services.audio;
    setState(() => _showTryAgain = result == AnswerResult.tryAgain);
    if (result == AnswerResult.correct) {
      unawaited(audio.play(SoundCue.correct));
      unawaited(
        audio.say(
          '${_praise[_game.index % _praise.length]} ${widget.spec.explanation(_game.question.target)}',
        ),
      );
    } else {
      unawaited(audio.play(SoundCue.tryAgain));
      unawaited(audio.say('¡Inténtalo otra vez!'));
    }
  }

  Future<void> _next() async {
    if (_game.isFinished) {
      setState(() => _finished = true);
      unawaited(_services.audio.play(SoundCue.celebrate));
      unawaited(_services.audio.say('¡Excelente trabajo! ¿Jugamos otra vez?'));
      _recorded = true;
      final earned = await _services.learning.recordSession(
        widget.spec.game,
        completed: true,
        points: _game.questionCount,
      );
      if (mounted) setState(() => _newRewards = earned);
      return;
    }
    setState(() {
      _game.next();
      _showTryAgain = false;
    });
    _sayInstruction();
  }

  void _restart() {
    _recordPartial();
    setState(_newGame);
  }

  /// Si se sale a mitad de partida, se guardan las preguntas acertadas.
  void _recordPartial() {
    if (_recorded || _finished) return;
    final points = _game.index + (_game.answered ? 1 : 0);
    if (points > 0) {
      unawaited(_services.learning.recordSession(widget.spec.game, completed: false, points: points));
    }
    _recorded = true;
  }

  @override
  void dispose() {
    _recordPartial();
    unawaited(_services.audio.stopVoice());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final spec = widget.spec;
    return KidScaffold(
      title: spec.game.title,
      titleIcon: spec.icon,
      accent: spec.accent,
      backLabel: 'Volver a los juegos',
      trailing: _finished
          ? null
          : KidIconButton(
              icon: Icons.replay_rounded,
              label: 'Empezar de nuevo',
              color: spec.accent,
              onPressed: _restart,
            ),
      body: _finished
          ? ActivityComplete(
              stars: _game.questionCount,
              newRewards: _newRewards,
              onPlayAgain: () => setState(_newGame),
              onExit: () => Navigator.of(context).maybePop(),
            )
          : _question(context),
    );
  }

  Widget _question(BuildContext context) {
    final spec = widget.spec;
    final q = _game.question;
    final voiceOn = _services.learning.settings.voiceOn;
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth > 700;
        final columns = q.options.length == 3 ? (constraints.maxWidth < 330 ? 2 : 3) : (wide ? 4 : 2);
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            4,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              QuestionProgress(done: _game.index + (_game.answered ? 1 : 0), total: _game.questionCount),
              const SizedBox(height: 10),
              InstructionCard(
                text: spec.instruction(q.target),
                visual: spec.prompt(context, q.target, _level),
                accent: spec.accent,
                onListen: voiceOn ? _sayInstruction : null,
              ),
              const SizedBox(height: 14),
              GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: columns,
                mainAxisSpacing: 14,
                crossAxisSpacing: 14,
                childAspectRatio: spec.caption(q.target, _level) != null ? 0.82 : 1,
                children: [
                  for (final (i, option) in q.options.indexed)
                    AnswerOption(
                      key: ValueKey('${_game.index}-${spec.name(option)}'),
                      label: spec.name(option),
                      caption: spec.caption(option, _level),
                      accent: spec.accent,
                      state: _stateOf(option),
                      onTap: _game.answered ? null : () => _choose(option),
                      child: spec.option(context, option, _level, i),
                    ),
                ],
              ),
              const SizedBox(height: 14),
              if (_game.answered)
                FeedbackPanel.success(
                  title: _praise[_game.index % _praise.length],
                  message: spec.explanation(q.target),
                  actionLabel: _game.isLastQuestion ? '¡Terminar!' : 'Siguiente',
                  onAction: _next,
                )
              else if (_showTryAgain)
                const FeedbackPanel.tryAgain(),
            ],
          ),
        );
      },
    );
  }

  OptionState _stateOf(T option) {
    if (_game.answered) return option == _game.question.target ? OptionState.correct : OptionState.faded;
    return _game.wrongAnswers.contains(option) ? OptionState.wrong : OptionState.idle;
  }
}
