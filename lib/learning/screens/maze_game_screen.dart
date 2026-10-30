import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/phrases.dart';
import '../../models/drawing_catalog.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../theme/app_motion.dart';
import '../../widgets/drawing_thumbnail.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../../widgets/motion/celebration.dart';
import '../audio/learning_audio.dart';
import '../games/maze.dart';
import '../learning_level.dart';
import '../rewards.dart';
import '../widgets/activity_complete.dart';
import '../widgets/instruction_card.dart';
import 'quiz_game_screen.dart' show activityDonePhrase;

/// «Laberintos»: llevar a un personaje hasta su meta arrastrando el dedo (o con
/// las flechas). Las paredes no se pueden atravesar; siempre hay un camino.
class MazeGameScreen extends StatefulWidget {
  const MazeGameScreen({super.key, required this.catalog, this.seed});

  final DrawingCatalog catalog;
  final int? seed;

  @override
  State<MazeGameScreen> createState() => _MazeGameScreenState();
}

class _MazeGameScreenState extends State<MazeGameScreen> with SingleTickerProviderStateMixin {
  late AppServices _services;
  late Random _random;
  late MazeGame _game;
  bool _started = false;
  bool _finished = false;
  int _round = 0;
  int _bumps = 0;
  List<Reward> _newRewards = const [];
  List<Cell> _hint = const [];

  /// La pista se ve unos segundos y se desvanece.
  late final AnimationController _hintFade = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 3),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _services = AppServices.of(context);
    if (!_started) {
      _started = true;
      _random = Random(widget.seed);
      _newGame();
    }
  }

  void _newGame() {
    final level = _services.learning.settings.level;
    final theme = MazeTheme.values[_round++ % MazeTheme.values.length];
    _game = MazeGame.random(level, theme, _random);
    _finished = false;
    _newRewards = const [];
    _hint = const [];
    _hintFade.value = 0;
    unawaited(_services.audio.say(theme.instruction));
  }

  int get _stars => switch (_services.learning.settings.level) {
    LearningLevel.initial => 3,
    LearningLevel.intermediate => 4,
    LearningLevel.advanced => 5,
  };

  void _handle(MoveResult result) {
    switch (result) {
      case MoveResult.goal:
        setState(() {});
        unawaited(_finish());
      case MoveResult.blocked:
        setState(() => _bumps++);
        unawaited(_services.audio.say(Phrases.mazeBump, mode: VoiceMode.ambient));
      case MoveResult.moved:
        setState(() {});
      case MoveResult.ignored:
        break;
    }
  }

  void _move(Dir d) => _handle(_game.move(d));

  void _dragTo(Offset local, double cell) {
    final target = (x: (local.dx / cell).floor(), y: (local.dy / cell).floor());
    if (!_game.maze.contains(target) || target == _game.position) return;
    _handle(_game.moveToward(target));
  }

  void _showHint() {
    setState(() => _hint = _game.hint());
    unawaited(_hintFade.forward(from: 0));
  }

  Future<void> _finish() async {
    unawaited(_services.audio.play(SoundCue.celebrate));
    unawaited(_services.audio.say('${_game.theme.success} ${activityDonePhrase(_stars)}'));
    // Un instante para ver al personaje en la meta antes de la felicitación.
    await Future<void>.delayed(const Duration(milliseconds: 900));
    if (!mounted) return;
    setState(() => _finished = true);
    final earned = await _services.learning.recordSession(GameId.maze, completed: true, points: _stars);
    if (mounted) setState(() => _newRewards = earned);
  }

  @override
  void dispose() {
    _hintFade.dispose();
    unawaited(_services.audio.stopVoice());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: GameId.maze.title,
      titleIcon: Icons.alt_route_rounded,
      accent: AppColors.sky,
      backLabel: 'Volver a los juegos',
      trailing: _finished
          ? null
          : KidIconButton(
              icon: Icons.replay_rounded,
              label: 'Empezar de nuevo',
              color: AppColors.sky,
              onPressed: () => setState(() {
                _game.reset();
                _hint = const [];
              }),
            ),
      body: _finished
          ? ActivityComplete(
              stars: _stars,
              newRewards: _newRewards,
              onPlayAgain: () => setState(_newGame),
              onExit: () => Navigator.of(context).maybePop(),
            )
          : _board(),
    );
  }

  Widget _board() {
    final theme = _game.theme;
    return LayoutBuilder(
      builder: (context, constraints) {
        final maze = _game.maze;
        final available = min(constraints.maxWidth - 2 * AppDimens.pagePadding, constraints.maxHeight - 250);
        final cell = (max(available, 200.0) / maze.cols).floorToDouble();
        final board = SizedBox(
          width: cell * maze.cols,
          height: cell * maze.rows,
          child: Semantics(
            label: '${theme.instruction}. Usa las flechas o arrastra el dedo.',
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onPanStart: (d) => _dragTo(d.localPosition, cell),
              onPanUpdate: (d) => _dragTo(d.localPosition, cell),
              child: AnimatedBuilder(
                animation: _hintFade,
                builder: (context, _) => Stack(
                  clipBehavior: Clip.none,
                  children: [
                    CustomPaint(
                      size: Size(cell * maze.cols, cell * maze.rows),
                      painter: _MazePainter(
                        game: _game,
                        cell: cell,
                        hint: _hint,
                        hintOpacity: _hintFade.isAnimating ? 1 - Curves.easeIn.transform(_hintFade.value) : 0,
                      ),
                    ),
                    _token(_game.goal, cell, _Goal(theme: theme, catalog: widget.catalog, size: cell * 0.8)),
                    AnimatedPositioned(
                      duration: AppMotion.of(context, const Duration(milliseconds: 140)),
                      left: _game.position.x * cell + cell * 0.08,
                      top: _game.position.y * cell + cell * 0.08,
                      child: Shake(
                        trigger: _bumps,
                        child: _Player(drawing: theme.player, catalog: widget.catalog, size: cell * 0.84),
                      ),
                    ),
                    if (_game.reached) const Positioned.fill(child: RisingStars()),
                  ],
                ),
              ),
            ),
          ),
        );
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            4,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          child: Column(
            children: [
              InstructionCard(
                text: theme.instruction,
                accent: AppColors.sky,
                onListen: _services.learning.settings.voiceOn
                    ? () => unawaited(_services.audio.say(theme.instruction))
                    : null,
              ),
              const SizedBox(height: 10),
              Center(child: board),
              const SizedBox(height: 12),
              _Controls(onMove: _move, onHint: _showHint),
            ],
          ),
        );
      },
    );
  }

  Widget _token(Cell c, double cell, Widget child) =>
      Positioned(left: c.x * cell + cell * 0.1, top: c.y * cell + cell * 0.1, child: child);
}

class _Controls extends StatelessWidget {
  const _Controls({required this.onMove, required this.onHint});

  final ValueChanged<Dir> onMove;
  final VoidCallback onHint;

  @override
  Widget build(BuildContext context) {
    Widget arrow(Dir d, IconData icon, String label) =>
        KidIconButton(icon: icon, label: label, color: AppColors.sky, size: 60, onPressed: () => onMove(d));
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 10,
      runSpacing: 10,
      children: [
        arrow(Dir.left, Icons.arrow_back_rounded, 'Mover a la izquierda'),
        arrow(Dir.up, Icons.arrow_upward_rounded, 'Mover arriba'),
        arrow(Dir.down, Icons.arrow_downward_rounded, 'Mover abajo'),
        arrow(Dir.right, Icons.arrow_forward_rounded, 'Mover a la derecha'),
        KidIconButton(
          icon: Icons.lightbulb_rounded,
          label: 'Pista',
          color: AppColors.sun,
          size: 60,
          showLabel: true,
          onPressed: onHint,
        ),
      ],
    );
  }
}

class _Player extends StatelessWidget {
  const _Player({required this.drawing, required this.catalog, required this.size});

  final String drawing;
  final DrawingCatalog catalog;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    padding: EdgeInsets.all(size * 0.06),
    decoration: BoxDecoration(
      color: Colors.white,
      shape: BoxShape.circle,
      border: Border.all(color: AppColors.coral, width: 3),
      boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 4, offset: Offset(0, 2))],
    ),
    child: ClipOval(child: DrawingThumbnail(asset: catalog.byId(drawing)?.thumbnailAsset)),
  );
}

class _Goal extends StatelessWidget {
  const _Goal({required this.theme, required this.catalog, required this.size});

  final MazeTheme theme;
  final DrawingCatalog catalog;
  final double size;

  @override
  Widget build(BuildContext context) {
    final drawing = theme.goalDrawing;
    final Widget content = drawing != null
        ? ClipOval(child: DrawingThumbnail(asset: catalog.byId(drawing)?.thumbnailAsset))
        : FittedBox(
            child: Icon(
              switch (theme) {
                MazeTheme.car => Icons.flag_rounded,
                MazeTheme.butterfly => Icons.local_florist_rounded,
                _ => Icons.diamond_rounded,
              },
              color: switch (theme) {
                MazeTheme.car => AppColors.coral,
                MazeTheme.butterfly => AppColors.berry,
                _ => AppColors.sun,
              },
            ),
          );
    return Semantics(
      label: 'Meta',
      child: Container(
        width: size,
        height: size,
        padding: EdgeInsets.all(size * 0.08),
        decoration: BoxDecoration(color: AppColors.sun.withValues(alpha: 0.25), shape: BoxShape.circle),
        child: content,
      ),
    );
  }
}

class _MazePainter extends CustomPainter {
  _MazePainter({required this.game, required this.cell, required this.hint, required this.hintOpacity});

  final MazeGame game;
  final double cell;
  final List<Cell> hint;
  final double hintOpacity;

  Offset _center(Cell c) => Offset((c.x + 0.5) * cell, (c.y + 0.5) * cell);

  @override
  void paint(Canvas canvas, Size size) {
    final maze = game.maze;
    canvas.drawRRect(
      RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(8)),
      Paint()..color = const Color(0xFFEAF6FF),
    );
    // Pista: el camino hasta la meta, en puntos amarillos.
    if (hintOpacity > 0 && hint.length > 1) {
      final dot = Paint()..color = AppColors.sun.withValues(alpha: hintOpacity);
      for (final c in hint) {
        canvas.drawCircle(_center(c), cell * 0.12, dot);
      }
    }
    // Rastro del camino recorrido.
    if (game.trail.length > 1) {
      final path = Path()..moveTo(_center(game.trail.first).dx, _center(game.trail.first).dy);
      for (final c in game.trail.skip(1)) {
        path.lineTo(_center(c).dx, _center(c).dy);
      }
      canvas.drawPath(
        path,
        Paint()
          ..color = AppColors.coral.withValues(alpha: 0.55)
          ..style = PaintingStyle.stroke
          ..strokeWidth = cell * 0.22
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round,
      );
    }
    // Salida.
    canvas.drawCircle(
      _center(game.start),
      cell * 0.18,
      Paint()..color = AppColors.leaf.withValues(alpha: 0.6),
    );
    // Paredes.
    final wall = Paint()
      ..color = AppColors.ink
      ..strokeWidth = max(4.0, cell * 0.1)
      ..strokeCap = StrokeCap.round;
    for (var y = 0; y < maze.rows; y++) {
      for (var x = 0; x < maze.cols; x++) {
        final c = (x: x, y: y);
        final l = x * cell, t = y * cell, r = l + cell, b = t + cell;
        if (maze.hasWall(c, Dir.up)) canvas.drawLine(Offset(l, t), Offset(r, t), wall);
        if (maze.hasWall(c, Dir.left)) canvas.drawLine(Offset(l, t), Offset(l, b), wall);
        if (y == maze.rows - 1 && maze.hasWall(c, Dir.down)) {
          canvas.drawLine(Offset(l, b), Offset(r, b), wall);
        }
        if (x == maze.cols - 1 && maze.hasWall(c, Dir.right)) {
          canvas.drawLine(Offset(r, t), Offset(r, b), wall);
        }
      }
    }
  }

  @override
  bool shouldRepaint(_MazePainter old) => true;
}
