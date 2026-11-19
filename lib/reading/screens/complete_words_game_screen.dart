import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../learning/widgets/question_progress.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/reading_voice.dart';
import '../complete_words.dart';
import '../reading_content.dart';
import '../achievement_data.dart';
import '../reading_progress.dart';
import '../widgets/reading_widgets.dart';

class CompleteGameArgs {
  const CompleteGameArgs({required this.level, required this.mode});
  final int level;
  final CompleteMode mode;
}

/// Carga el catálogo de «Completa las palabras».
class CompleteWordsBuilder extends StatefulWidget {
  const CompleteWordsBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, CompleteWordsContent content) builder;

  @override
  State<CompleteWordsBuilder> createState() => _CompleteWordsBuilderState();
}

class _CompleteWordsBuilderState extends State<CompleteWordsBuilder> {
  Future<CompleteWordsContent>? _future;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _future ??= CompleteWordsContent.load(DefaultAssetBundle.of(context));
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<CompleteWordsContent>(
      future: _future,
      builder: (context, snapshot) {
        final content = snapshot.data;
        if (content != null) return widget.builder(context, content);
        if (snapshot.hasError) return const Center(child: Text('No pudimos abrir las palabras.'));
        return const Center(child: CircularProgressIndicator());
      },
    );
  }
}

/// Partida de «Completa las palabras» en un nivel y un modo.
class CompleteWordsGameScreen extends StatelessWidget {
  const CompleteWordsGameScreen({super.key, required this.args, this.seed});

  final CompleteGameArgs args;

  /// Para pruebas: orden fijo.
  final int? seed;

  static const title = 'Completa las palabras';
  static const instruction = 'Mira, escucha y completa.';
  static const praise = '¡Muy bien!';
  static const tryAgain = '¡Casi! Escucha otra vez y prueba de nuevo.';
  static const color = Color(0xFFF59E3D);

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: title,
      titleIcon: Icons.extension_rounded,
      accent: color,
      trailing: const ReadingHomeButton(),
      body: CompleteWordsBuilder(
        builder: (context, content) => _Game(content: content, args: args, seed: seed),
      ),
    );
  }
}

class _Game extends StatefulWidget {
  const _Game({required this.content, required this.args, this.seed});

  final CompleteWordsContent content;
  final CompleteGameArgs args;
  final int? seed;

  @override
  State<_Game> createState() => _GameState();
}

class _GameState extends State<_Game> {
  ReadingVoice? _voice;
  late ReadingController _progress;
  late Random _random;
  late List<CompleteExercise> _exercises;
  late CompleteRound _round;
  int _index = 0;
  int _firstTry = 0;
  bool _finished = false;
  bool _wrong = false;

  CompleteMode get mode => widget.args.mode;
  ReadingWord get word => widget.content.wordOf(_round.exercise);

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
      if (mounted && _exercises.isNotEmpty) _listen();
    });
  }

  @override
  void dispose() {
    _voice?.dispose();
    super.dispose();
  }

  void _start() {
    _exercises = widget.content.session(
      widget.args.level,
      mode,
      done: (e) => _progress.isCompleted(e.id, mode.id),
      random: _random,
    );
    _index = 0;
    _firstTry = 0;
    _finished = false;
    if (_exercises.isNotEmpty) _round = CompleteRound(_exercises.first, mode, _random);
  }

  void _listen([ReadingSpeed speed = ReadingSpeed.normal]) =>
      unawaited(_voice!.play(word.audio, speed: speed));

  void _hint(VoidCallback change) => setState(() {
    _round.usedHints = true;
    change();
  });

  void _slow() {
    _hint(() {});
    _listen(ReadingSpeed.slow);
  }

  void _hearMissing() {
    _hint(() {});
    final s = mode == CompleteMode.order ? _round.exercise.syllables.first : _round.exercise.answer;
    unawaited(_voice!.play(ReadingAudio(tts: s.toLowerCase())));
  }

  /// Primera vez: pista visual (primera letra / primera tarjeta); segunda:
  /// se resalta la respuesta.
  void _help() => _hint(() {
    if (mode != CompleteMode.order && !_round.showFirstLetter) {
      _round.showFirstLetter = true;
    } else {
      _round.revealAnswer = true;
    }
  });

  void _choose(String option) {
    if (_round.solved) return;
    setState(() {
      _round.chosen = option;
      _wrong = false;
    });
    unawaited(_voice!.play(ReadingAudio(tts: option.toLowerCase())));
  }

  void _place(int piece) {
    if (_round.solved || _round.placed.contains(piece)) return;
    setState(() {
      _round.placed.add(piece);
      _wrong = false;
    });
    final text = _round.pieces.firstWhere((p) => p.$1 == piece).$2;
    unawaited(_voice!.play(ReadingAudio(tts: text.toLowerCase())));
  }

  void _undo() {
    if (_round.placed.isEmpty) return;
    setState(() => _round.placed.removeLast());
  }

  void _check() {
    final right = _round.check();
    _progress.recordAttempt(correct: right);
    setState(() => _wrong = !right);
    if (right) {
      final firstTry = _round.wrongAttempts == 0;
      if (firstTry) _firstTry++;
      _progress.recordCompleted(
        _round.exercise.id,
        mode.id,
        firstTry: firstTry,
        usedHints: _round.usedHints,
        mistakes: _round.wrongAttempts,
      );
      unawaited(() async {
        await _voice!.play(word.audio); // la palabra completa
        await _voice!.sayText(CompleteWordsGameScreen.praise);
      }());
    } else {
      unawaited(_voice!.sayText(CompleteWordsGameScreen.tryAgain));
    }
  }

  void _next() {
    if (_index == _exercises.length - 1) {
      setState(() => _finished = true);
      _progress.recordSeries(ReadingModule.words);
      unawaited(_voice!.sayText('¡Terminaste! ¡Qué bien lo has hecho!'));
      return;
    }
    setState(() {
      _index++;
      _round = CompleteRound(_exercises[_index], mode, _random);
      _wrong = false;
    });
    _listen();
  }

  void _again() {
    setState(_start);
    _listen();
  }

  @override
  Widget build(BuildContext context) {
    if (_exercises.isEmpty) {
      return const Center(child: Text('Todavía no hay palabras con imagen en este nivel.'));
    }
    return ListenableBuilder(
      listenable: _progress,
      builder: (context, _) => LayoutBuilder(
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
      ),
    );
  }

  Widget _summary() {
    final level = widget.args.level;
    final nextOpen = level < 3 && levelUnlocked(widget.content, _progress, level + 1);
    return Column(
      children: [
        const SizedBox(height: 20),
        const ReadingCelebration(text: '¡Terminaste! ¡Qué bien lo has hecho!'),
        const SizedBox(height: 16),
        Semantics(
          label: 'Acertaste $_firstTry de ${_exercises.length} a la primera',
          excludeSemantics: true,
          child: QuestionProgress(done: _firstTry, total: _exercises.length, label: 'Estrella'),
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
            if (nextOpen)
              SizedBox(
                width: 260,
                child: BigActionButton(
                  label: 'Siguiente nivel',
                  icon: Icons.trending_up_rounded,
                  color: AppColors.leaf,
                  onPressed: () => Navigator.of(context).pushReplacement(
                    MaterialPageRoute<void>(
                      settings: RouteSettings(name: ModalRoute.of(context)?.settings.name),
                      builder: (_) => CompleteWordsGameScreen(
                        args: CompleteGameArgs(level: level + 1, mode: mode),
                      ),
                    ),
                  ),
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
    const color = CompleteWordsGameScreen.color;
    final r = _round;
    final picture = SizedBox(
      height: wide ? 250 : 180,
      child: ReadingWordPicture(word: word, color: color),
    );
    final controls = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        ReadingPlayButtons(
          onPlay: (speed) => speed == ReadingSpeed.slow ? _slow() : _listen(),
          semanticSuffix: ' la palabra',
          color: color,
        ),
        const SizedBox(height: 14),
        _wordRow(color),
      ],
    );
    return Column(
      children: [
        ReadingVoiceNotice(voice: _voice!),
        Text(CompleteWordsGameScreen.instruction, style: fredoka(22, color: AppColors.ink)),
        Text(mode.instruction, style: Theme.of(context).textTheme.bodyLarge, textAlign: TextAlign.center),
        const SizedBox(height: 8),
        ReadingProgressBar(done: _index, total: _exercises.length, label: 'Palabras', color: color),
        const SizedBox(height: 12),
        if (wide)
          Row(
            children: [
              Expanded(child: picture),
              const SizedBox(width: 20),
              Expanded(child: controls),
            ],
          )
        else ...[
          picture,
          const SizedBox(height: 10),
          controls,
        ],
        const SizedBox(height: 16),
        if (mode == CompleteMode.order) _pieces(color) else _options(color),
        const SizedBox(height: 14),
        if (r.solved)
          ReadingCelebration(text: '${CompleteWordsGameScreen.praise} ${word.text.toUpperCase()}')
        else if (_wrong)
          const ReadingTryAgain(text: CompleteWordsGameScreen.tryAgain),
        const SizedBox(height: 12),
        if (!r.solved) _hints(),
        const SizedBox(height: 12),
        Wrap(
          alignment: WrapAlignment.center,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
            if (mode == CompleteMode.order && !r.solved)
              KidIconButton(
                icon: Icons.backspace_rounded,
                label: 'Quitar la última',
                color: AppColors.coral,
                onPressed: r.placed.isEmpty ? null : _undo,
              ),
            if (!r.solved)
              SizedBox(
                width: 260,
                child: BigActionButton(
                  label: 'Comprobar',
                  icon: Icons.check_rounded,
                  color: AppColors.leaf,
                  onPressed: r.ready ? _check : null,
                ),
              )
            else
              SizedBox(
                width: 260,
                child: BigActionButton(
                  label: _index == _exercises.length - 1 ? 'Terminar' : 'Siguiente',
                  icon: Icons.arrow_forward_rounded,
                  color: AppColors.sky,
                  onPressed: _next,
                ),
              ),
          ],
        ),
      ],
    );
  }

  /// La palabra por sílabas con su hueco (o lo que se va formando).
  Widget _wordRow(Color color) {
    final r = _round;
    final syllables = r.exercise.syllables;
    if (mode == CompleteMode.order) {
      final built = r.solved ? syllables : r.built;
      return SyllableWord(
        syllables: [for (var i = 0; i < syllables.length; i++) i < built.length ? built[i] : '?'],
        color: color,
        size: 58,
      );
    }
    final filled = r.solved
        ? r.exercise.answer
        : r.chosen ?? (r.showFirstLetter ? '${r.exercise.answer.characters.first}…' : null);
    final row = SyllableWord(
      syllables: syllables,
      missing: r.exercise.missing,
      filled: filled,
      color: color,
      size: 58,
    );
    if (mode != CompleteMode.drag || r.solved) return row;
    return DragTarget<String>(
      onWillAcceptWithDetails: (_) => !r.solved,
      onAcceptWithDetails: (d) => _choose(d.data),
      builder: (context, candidates, _) => AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          color: candidates.isNotEmpty ? const Color(0xFFFFF3E0) : Colors.transparent,
        ),
        child: Semantics(
          container: true,
          label: 'Hueco para soltar la sílaba',
          child: Semantics(container: true, child: row),
        ),
      ),
    );
  }

  Widget _options(Color color) {
    final r = _round;
    final strong = Color.lerp(color, Colors.black, 0.2)!;
    Widget card(String o) {
      final highlighted = r.revealAnswer && o == r.exercise.answer;
      final tile = Container(
        decoration: highlighted
            ? BoxDecoration(
                borderRadius: BorderRadius.circular(30),
                boxShadow: const [BoxShadow(color: AppColors.sun, blurRadius: 14, spreadRadius: 4)],
              )
            : null,
        child: SyllableCard(
          text: o,
          color: strong,
          size: 90,
          selected: r.chosen == o || (r.solved && o == r.exercise.answer),
          onTap: r.solved ? null : () => _choose(o),
        ),
      );
      if (mode != CompleteMode.drag || r.solved) return tile;
      return Draggable<String>(
        data: o,
        feedback: Material(
          color: Colors.transparent,
          child: SyllableCard(text: o, color: strong, size: 90, onTap: null),
        ),
        childWhenDragging: Opacity(opacity: 0.3, child: tile),
        child: tile,
      );
    }

    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 14,
      runSpacing: 14,
      children: [for (final o in r.options) card(o)],
    );
  }

  Widget _pieces(Color color) {
    final r = _round;
    final strong = Color.lerp(color, Colors.black, 0.2)!;
    final next = r.revealAnswer ? r.nextPiece : null;
    final nextText = next == null ? null : r.exercise.syllables[next];
    int? highlight;
    if (nextText != null) {
      for (final p in r.pieces) {
        if (!r.placed.contains(p.$1) && p.$2 == nextText) {
          highlight = p.$1;
          break;
        }
      }
    }
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 14,
      runSpacing: 14,
      children: [
        for (final (i, text) in r.pieces)
          Opacity(
            opacity: r.placed.contains(i) ? 0.35 : 1,
            child: Container(
              decoration: highlight == i
                  ? BoxDecoration(
                      borderRadius: BorderRadius.circular(30),
                      boxShadow: const [BoxShadow(color: AppColors.sun, blurRadius: 14, spreadRadius: 4)],
                    )
                  : null,
              child: SyllableCard(
                text: text,
                color: strong,
                size: 86,
                onTap: r.solved || r.placed.contains(i) ? null : () => _place(i),
              ),
            ),
          ),
      ],
    );
  }

  Widget _hints() {
    final order = mode == CompleteMode.order;
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 10,
      runSpacing: 10,
      children: [
        KidIconButton(
          icon: Icons.slow_motion_video_rounded,
          label: 'Escuchar la palabra despacio',
          color: AppColors.grape,
          showLabel: true,
          onPressed: _slow,
        ),
        KidIconButton(
          icon: Icons.record_voice_over_rounded,
          label: order ? 'Escuchar la primera sílaba' : 'Escuchar la sílaba que falta',
          color: AppColors.sky,
          showLabel: true,
          onPressed: _hearMissing,
        ),
        KidIconButton(
          icon: Icons.lightbulb_rounded,
          label: 'Pista',
          color: AppColors.sun,
          showLabel: true,
          onPressed: _round.revealAnswer ? null : _help,
        ),
      ],
    );
  }
}

/// Un nivel está abierto si es el primero o si ya se completaron
/// [ReadingController.unlockAfter] ejercicios del anterior (en cualquier modo).
bool levelUnlocked(CompleteWordsContent content, ReadingController progress, int level) {
  if (level <= 1) return true;
  final previous = [
    for (final e in content.exercises)
      if (e.level == level - 1 && (content.words[e.wordId]?.hasPicture ?? false)) e.id,
  ];
  final need = min(ReadingController.unlockAfter, previous.length);
  final done = previous.where((id) => progress.progress.completed[id]?.isNotEmpty ?? false).length;
  return done >= need;
}

/// Ejercicios completados (en cualquier modo) de [level].
int completedInLevel(CompleteWordsContent content, ReadingController progress, int level) => [
  for (final e in content.exercises)
    if (e.level == level && (progress.progress.completed[e.id]?.isNotEmpty ?? false)) e,
].length;
