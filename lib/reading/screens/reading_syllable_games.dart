import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../learning/widgets/question_progress.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/reading_voice.dart';
import '../achievement_data.dart';
import '../reading_content.dart';
import '../reading_progress.dart';
import '../syllable_games.dart';
import '../widgets/reading_widgets.dart';
import 'reading_syllables_screen.dart';

/// Los dos juegos de sílabas. Errores sin castigo: se puede volver a escuchar
/// e intentar las veces que haga falta.
enum SyllableGame {
  listenFind('Escucha y encuentra', Icons.hearing_rounded, 'Escucha y toca la sílaba que oyes.'),
  matchWord('Une sílaba y palabra', Icons.image_search_rounded, '¿Con qué sílaba empieza?');

  const SyllableGame(this.title, this.icon, this.instruction);
  final String title;
  final IconData icon;
  final String instruction;
}

class SyllableGameScreen extends StatelessWidget {
  const SyllableGameScreen({super.key, required this.game, this.args = const ReadingGameArgs(), this.seed});

  final SyllableGame game;
  final ReadingGameArgs args;

  /// Para pruebas: orden fijo.
  final int? seed;

  static const praise = '¡Muy bien!';
  static const tryAgain = 'Vamos a intentarlo otra vez.';

  @override
  Widget build(BuildContext context) {
    const color = Color(0xFF4FA8F0);
    return KidScaffold(
      title: game.title,
      titleIcon: game.icon,
      accent: color,
      trailing: const ReadingHomeButton(),
      body: ReadingContentBuilder(
        builder: (context, content) =>
            _GameView(game: game, content: content, familyId: args.familyId, seed: seed),
      ),
    );
  }
}

class _GameView extends StatefulWidget {
  const _GameView({required this.game, required this.content, required this.familyId, this.seed});

  final SyllableGame game;
  final ReadingContent content;
  final String? familyId;
  final int? seed;

  @override
  State<_GameView> createState() => _GameViewState();
}

class _GameViewState extends State<_GameView> {
  ReadingVoice? _voice;
  late ReadingController _progress;
  late Random _random;
  late List<Object> _questions; // ListenFindQuestion o MatchWordQuestion
  String? _scope; // familia con la que se juega (null = todas)
  int _index = 0;
  final _tried = <String>{}; // opciones falladas en esta pregunta
  bool _solved = false;
  int _firstTry = 0;
  bool _finished = false;

  @override
  void initState() {
    super.initState();
    _random = Random(widget.seed);
    _start();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_voice == null) {
      _voice = ReadingVoice(AppServices.of(context).audio);
      _progress = AppServices.of(context).reading;
      // La primera pregunta se oye al entrar.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _playQuestion();
      });
    }
  }

  @override
  void dispose() {
    _voice?.dispose();
    super.dispose();
  }

  void _start() {
    final c = widget.content;
    _scope = widget.familyId;
    if (widget.game == SyllableGame.listenFind) {
      _questions = SyllableGames.listenFind(c, familyId: _scope, random: _random);
    } else {
      final inFamily = SyllableGames.matchWord(c, familyId: _scope, count: 6, random: _random);
      // Con menos de 3 palabras con imagen en la familia, se juega con todas.
      final distinct = {for (final q in inFamily) q.word.id};
      if (_scope != null && distinct.length < 3) {
        _scope = null;
        _questions = SyllableGames.matchWord(c, count: 6, random: _random);
      } else {
        _questions = inFamily;
      }
    }
    _index = 0;
    _tried.clear();
    _solved = false;
    _firstTry = 0;
    _finished = false;
  }

  Object get _q => _questions[_index];

  ReadingSyllable get _answer => switch (_q) {
    final ListenFindQuestion q => q.target,
    final MatchWordQuestion q => q.answer,
    _ => throw StateError('pregunta desconocida'),
  };

  List<ReadingSyllable> get _options => switch (_q) {
    final ListenFindQuestion q => q.options,
    final MatchWordQuestion q => q.options,
    _ => const [],
  };

  void _playQuestion([ReadingSpeed speed = ReadingSpeed.normal]) {
    final q = _q;
    if (q is ListenFindQuestion) unawaited(_voice!.play(q.target.audio, speed: speed));
    if (q is MatchWordQuestion) unawaited(_voice!.play(q.word.audio, speed: speed));
  }

  void _choose(ReadingSyllable s) {
    if (_solved) return;
    final game = widget.game == SyllableGame.listenFind ? 'escucha_encuentra' : 'une_palabra';
    _progress.recordSyllableAnswer(
      _answer.id,
      game: game,
      correct: s.id == _answer.id,
      firstTry: _tried.isEmpty,
      mistakes: _tried.length,
    );
    if (s.id == _answer.id) {
      setState(() {
        _solved = true;
        if (_tried.isEmpty) _firstTry++;
      });
      final q = _q;
      final word = q is MatchWordQuestion ? q.word : null;
      // «PE. PELOTA.» y después «¡Muy bien!» (o solo «¡Muy bien!»).
      unawaited(() async {
        if (word != null) await _voice!.playAll([s.audio, word.audio]);
        await _voice!.sayText(SyllableGameScreen.praise);
      }());
    } else {
      setState(() => _tried.add(s.id));
      unawaited(_voice!.sayText(SyllableGameScreen.tryAgain));
    }
  }

  void _next() {
    if (_index == _questions.length - 1) {
      setState(() => _finished = true);
      _progress.recordSeries(ReadingModule.syllables);
      unawaited(_voice!.sayText('¡Terminaste! ¡Qué bien lo has hecho!'));
      return;
    }
    setState(() {
      _index++;
      _tried.clear();
      _solved = false;
    });
    _playQuestion();
  }

  void _again() {
    setState(_start);
    _playQuestion();
  }

  @override
  Widget build(BuildContext context) {
    if (_questions.isEmpty) {
      return const Center(child: Text('Todavía no hay ejercicios para esta familia.'));
    }
    final family = _scope == null ? null : widget.content.families.where((f) => f.id == _scope).firstOrNull;
    final color = family?.color ?? const Color(0xFF8FCBFF);
    final strong = Color.lerp(color, Colors.black, 0.25)!;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppDimens.pagePadding,
        0,
        AppDimens.pagePadding,
        AppDimens.pagePadding,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: _finished ? _summary(strong) : _question(color, strong, family),
        ),
      ),
    );
  }

  Widget _summary(Color strong) {
    return Column(
      children: [
        const SizedBox(height: 20),
        const ReadingCelebration(text: '¡Terminaste! ¡Qué bien lo has hecho!'),
        const SizedBox(height: 16),
        Semantics(
          label: 'Acertaste $_firstTry de ${_questions.length} a la primera',
          excludeSemantics: true,
          child: QuestionProgress(done: _firstTry, total: _questions.length, label: 'Estrella'),
        ),
        const SizedBox(height: 20),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
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
                label: 'Volver a las sílabas',
                icon: Icons.abc_rounded,
                color: AppColors.leaf,
                onPressed: () => Navigator.of(context).maybePop(),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _question(Color color, Color strong, SyllableFamily? family) {
    final q = _q;
    final word = q is MatchWordQuestion ? q.word : null;
    return Column(
      children: [
        ReadingVoiceNotice(voice: _voice!),
        Text(
          family == null ? 'Todas las familias' : 'Familia ${family.letter}',
          style: fredoka(16, color: AppColors.inkSoft),
        ),
        const SizedBox(height: 6),
        QuestionProgress(done: _index, total: _questions.length),
        const SizedBox(height: 12),
        ReadingLolo(text: widget.game.instruction),
        const SizedBox(height: 12),
        if (word != null) ...[
          SizedBox(
            height: 180,
            child: ReadingWordPicture(word: word, color: color),
          ),
          const SizedBox(height: 8),
          if (_solved)
            SyllableWord(syllables: word.syllables, highlight: 0, color: color, size: 52)
          else
            Text('?', style: fredoka(40, color: strong)),
          const SizedBox(height: 8),
        ],
        ReadingPlayButtons(
          onPlay: _playQuestion,
          listenLabel: word == null ? 'Escuchar' : 'Palabra',
          semanticSuffix: word == null ? ' otra vez' : ' la palabra',
          color: strong,
        ),
        const SizedBox(height: 18),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 14,
          runSpacing: 14,
          children: [
            for (final o in _options)
              Opacity(
                opacity: _tried.contains(o.id) ? 0.45 : 1,
                child: SyllableCard(
                  text: o.text,
                  color: strong,
                  size: 96,
                  selected: _solved && o.id == _answer.id,
                  onTap: _solved || _tried.contains(o.id) ? null : () => _choose(o),
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),
        if (_solved)
          const ReadingCelebration(text: SyllableGameScreen.praise)
        else if (_tried.isNotEmpty)
          const ReadingTryAgain(text: SyllableGameScreen.tryAgain),
        const SizedBox(height: 14),
        if (_solved)
          SizedBox(
            width: 260,
            child: BigActionButton(
              label: _index == _questions.length - 1 ? 'Terminar' : 'Siguiente',
              icon: Icons.arrow_forward_rounded,
              color: AppColors.leaf,
              onPressed: _next,
            ),
          ),
      ],
    );
  }
}
