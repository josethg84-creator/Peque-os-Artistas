import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/phrases.dart';
import '../../coloring/engine/drawing_painter.dart';
import '../../coloring/engine/vector_drawing.dart';
import '../../coloring/palette.dart';
import '../../models/drawing.dart';
import '../../models/drawing_catalog.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../theme/app_motion.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../../widgets/motion/celebration.dart';
import '../../widgets/motion/delayed_loading.dart';
import '../audio/learning_audio.dart';
import '../games/puzzle_game.dart';
import '../learning_level.dart';
import '../rewards.dart';
import '../widgets/activity_complete.dart';
import '../widgets/question_progress.dart';
import 'quiz_game_screen.dart' show activityDonePhrase;

/// «Rompecabezas» con los dibujos del catálogo, coloreados. Las piezas se
/// arrastran a su casilla (o se toca una pieza y después la casilla). Una
/// pieza en el sitio equivocado vuelve a la bandeja, sin castigo.
class PuzzleGameScreen extends StatefulWidget {
  const PuzzleGameScreen({super.key, required this.catalog, this.seed});

  final DrawingCatalog catalog;
  final int? seed;

  @override
  State<PuzzleGameScreen> createState() => _PuzzleGameScreenState();
}

class _PuzzleGameScreenState extends State<PuzzleGameScreen> {
  late AppServices _services;
  late Random _random;
  late PuzzleGame _game;
  late Drawing _drawing;
  late Future<VectorDrawing> _vector;
  late LearningLevel _level;
  bool _started = false;
  bool _finished = false;
  List<Reward> _newRewards = const [];
  int? _selected;
  int? _justPlaced;
  int _misses = 0;
  String? _message;

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
    _level = _services.learning.settings.level;
    final options = widget.catalog.drawings;
    final previous = _started && _finished ? _drawing.id : null;
    final pool = options.where((d) => d.id != previous).toList();
    _drawing = pool[_random.nextInt(pool.length)];
    _vector = _services.drawings.load(_drawing.file)..ignore();
    _game = PuzzleGame(side: puzzleSideFor(_level), random: _random);
    _finished = false;
    _newRewards = const [];
    _selected = null;
    _justPlaced = null;
    _message = null;
    unawaited(_services.audio.say(Phrases.puzzleStart));
  }

  /// Estrellas al terminar: 3, 4 o 5 según el nivel.
  int get _stars => _game.side + 1;

  void _drop(int piece, int cell) {
    final result = _game.drop(piece, cell);
    if (result == DropResult.ignored) return;
    final audio = _services.audio;
    setState(() {
      _selected = null;
      if (result == DropResult.correct) {
        _justPlaced = piece;
        _message = null;
      } else {
        _misses++;
        _message = Phrases.puzzleWrong;
      }
    });
    if (result == DropResult.correct) {
      if (_game.isComplete) {
        unawaited(_finish());
      } else {
        unawaited(audio.play(SoundCue.correct));
      }
    } else {
      unawaited(audio.play(SoundCue.tryAgain));
    }
  }

  Future<void> _finish() async {
    setState(() => _finished = true);
    unawaited(_services.audio.play(SoundCue.celebrate));
    unawaited(_services.audio.say(activityDonePhrase(_stars)));
    final earned = await _services.learning.recordSession(GameId.puzzle, completed: true, points: _stars);
    if (mounted) setState(() => _newRewards = earned);
  }

  @override
  void dispose() {
    unawaited(_services.audio.stopVoice());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: GameId.puzzle.title,
      titleIcon: Icons.extension_rounded,
      accent: AppColors.sun,
      backLabel: 'Volver a los juegos',
      trailing: _finished
          ? null
          : KidIconButton(
              icon: Icons.shuffle_rounded,
              label: 'Otro dibujo',
              color: AppColors.sun,
              onPressed: () => setState(_newGame),
            ),
      body: _finished
          ? Stack(
              children: [
                ActivityComplete(
                  stars: _stars,
                  newRewards: _newRewards,
                  onPlayAgain: () => setState(_newGame),
                  onExit: () => Navigator.of(context).maybePop(),
                ),
              ],
            )
          : FutureBuilder<VectorDrawing>(
              future: _vector,
              builder: (context, snapshot) {
                final vector = snapshot.data;
                if (snapshot.hasError) {
                  // Dibujo que no se pudo abrir: se prueba con otro.
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    if (mounted) setState(_newGame);
                  });
                }
                if (vector == null) return const DelayedLoading(message: 'Preparando el rompecabezas…');
                return _board(vector);
              },
            ),
    );
  }

  Widget _board(VectorDrawing vector) {
    final painter = _CroppedPainter(
      DrawingPainter(drawing: vector, colors: _AutoColors(vector, _drawing.id)),
      vector,
    );
    final ghost = switch (_level) {
      LearningLevel.initial => 0.3,
      LearningLevel.intermediate => 0.14,
      LearningLevel.advanced => 0.0,
    };
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth > constraints.maxHeight * 1.1;
        final boardSide = wide
            ? min(constraints.maxHeight - 80, constraints.maxWidth * 0.55)
            : min(constraints.maxWidth - 2 * AppDimens.pagePadding, constraints.maxHeight * 0.52);
        final cell = boardSide / _game.side;
        final trayPiece = min(cell * 0.82, 110.0);
        final board = _Board(
          game: _game,
          painter: painter,
          cell: cell,
          ghostOpacity: ghost,
          justPlaced: _justPlaced,
          misses: _misses,
          onDrop: _drop,
          onTapCell: (c) {
            if (_selected != null) _drop(_selected!, c);
          },
        );
        final tray = Wrap(
          spacing: 10,
          runSpacing: 10,
          alignment: WrapAlignment.center,
          children: [
            for (final p in _game.tray)
              _TrayPiece(
                key: ValueKey('pieza-$p'),
                piece: p,
                side: _game.side,
                painter: painter,
                size: trayPiece,
                dragSize: cell,
                selected: _selected == p,
                onTap: () => setState(() => _selected = _selected == p ? null : p),
              ),
          ],
        );
        final header = Column(
          children: [
            QuestionProgress(done: _game.placedCount, total: _game.pieces, label: 'Pieza'),
            SizedBox(
              height: 34,
              child: Center(
                child: Semantics(
                  liveRegion: true,
                  child: Text(
                    _message ?? (_selected != null ? 'Ahora toca su casilla' : Phrases.puzzleStart),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ),
            ),
          ],
        );
        final content = wide
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  board,
                  const SizedBox(width: AppDimens.gap),
                  Expanded(
                    child: SingleChildScrollView(child: Column(children: [header, tray])),
                  ),
                ],
              )
            : Column(
                children: [
                  header,
                  board,
                  const SizedBox(height: AppDimens.gap),
                  tray,
                ],
              );
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            0,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          child: Center(child: content),
        );
      },
    );
  }
}

/// Pinta solo la parte del lienzo que ocupa el dibujo (con un pequeño margen):
/// sin el fondo vacío de alrededor, casi todas las piezas tienen dibujo y se
/// distinguen mejor.
class _CroppedPainter extends CustomPainter {
  _CroppedPainter(this.inner, VectorDrawing drawing) : view = _contentRect(drawing);

  final DrawingPainter inner;
  final Rect view;

  static Rect _contentRect(VectorDrawing d) {
    Rect? box;
    for (final r in d.regions) {
      if (r.id == VectorDrawing.backgroundId) continue;
      box = box == null ? r.bounds : box.expandToInclude(r.bounds);
    }
    final b = (box ?? d.viewBox).intersect(d.viewBox);
    final side = max(b.width, b.height) * 1.06;
    return Rect.fromCenter(center: b.center, width: side, height: side);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final vb = inner.drawing.viewBox;
    final k = size.width / view.width;
    canvas.save();
    canvas.clipRect(Offset.zero & size);
    canvas.translate(-(view.left - vb.left) * k, -(view.top - vb.top) * k);
    inner.paint(canvas, Size(vb.width * k, vb.height * k));
    canvas.restore();
  }

  @override
  bool shouldRepaint(_CroppedPainter old) => old.inner != inner;
}

/// Colores alegres y fijos para cada dibujo (el niño aún no lo ha pintado).
class _AutoColors extends ChangeNotifier implements RegionColors {
  _AutoColors(VectorDrawing drawing, String seed) {
    final palette = kidPalette
        .where((c) => !c.restoresOriginal && !{'Negro', 'Gris'}.contains(c.name))
        .toList();
    final offset = seed.codeUnits.fold<int>(0, (a, b) => a + b);
    for (final (i, r) in drawing.regions.indexed) {
      _map[r.id] = r.id == VectorDrawing.backgroundId
          ? const Color(0xFFFFF3D6)
          : palette[(i + offset) % palette.length].color;
    }
  }

  final _map = <String, Color>{};

  @override
  Color? colorOf(String regionId) => _map[regionId];
}

/// Recorte de la pieza [piece] de la imagen completa.
class _PieceImage extends StatelessWidget {
  const _PieceImage({required this.piece, required this.side, required this.painter, required this.size});

  final int piece;
  final int side;
  final CustomPainter painter;
  final double size;

  @override
  Widget build(BuildContext context) {
    final row = piece ~/ side, col = piece % side;
    final full = size * side;
    return SizedBox.square(
      dimension: size,
      child: ClipRect(
        child: OverflowBox(
          alignment: Alignment.topLeft,
          minWidth: full,
          maxWidth: full,
          minHeight: full,
          maxHeight: full,
          child: Transform.translate(
            offset: Offset(-col * size, -row * size),
            child: CustomPaint(size: Size.square(full), painter: painter),
          ),
        ),
      ),
    );
  }
}

class _TrayPiece extends StatelessWidget {
  const _TrayPiece({
    super.key,
    required this.piece,
    required this.side,
    required this.painter,
    required this.size,
    required this.dragSize,
    required this.selected,
    required this.onTap,
  });

  final int piece;
  final int side;
  final CustomPainter painter;
  final double size;
  final double dragSize;
  final bool selected;
  final VoidCallback onTap;

  Widget _framed(double s, {bool lifted = false}) => Container(
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: selected ? AppColors.ink : Colors.white, width: 3),
      boxShadow: [
        BoxShadow(color: const Color(0x33000000), blurRadius: lifted ? 14 : 4, offset: const Offset(0, 3)),
      ],
    ),
    child: ClipRRect(
      borderRadius: BorderRadius.circular(7),
      child: _PieceImage(piece: piece, side: side, painter: painter, size: s - 6),
    ),
  );

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: 'Pieza ${piece + 1}',
      hint: 'Toca y después toca su casilla, o arrástrala',
      excludeSemantics: true,
      onTap: onTap,
      child: Draggable<int>(
        data: piece,
        feedback: Material(color: Colors.transparent, child: _framed(dragSize, lifted: true)),
        childWhenDragging: Opacity(opacity: 0.25, child: _framed(size)),
        child: GestureDetector(onTap: onTap, child: _framed(size)),
      ),
    );
  }
}

class _Board extends StatelessWidget {
  const _Board({
    required this.game,
    required this.painter,
    required this.cell,
    required this.ghostOpacity,
    required this.justPlaced,
    required this.misses,
    required this.onDrop,
    required this.onTapCell,
  });

  final PuzzleGame game;
  final CustomPainter painter;
  final double cell;
  final double ghostOpacity;
  final int? justPlaced;
  final int misses;
  final void Function(int piece, int cell) onDrop;
  final ValueChanged<int> onTapCell;

  @override
  Widget build(BuildContext context) {
    final side = game.side;
    final reduced = AppMotion.reduced(context);
    return Shake(
      trigger: misses,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
          border: Border.all(color: AppColors.sun, width: 4),
        ),
        padding: const EdgeInsets.all(4),
        child: SizedBox.square(
          dimension: cell * side,
          child: Stack(
            children: [
              // Silueta de ayuda (más tenue en los niveles altos).
              if (ghostOpacity > 0)
                Opacity(
                  opacity: ghostOpacity,
                  child: CustomPaint(size: Size.square(cell * side), painter: painter),
                ),
              for (var i = 0; i < game.pieces; i++)
                Positioned(
                  left: (i % side) * cell,
                  top: (i ~/ side) * cell,
                  child: game.isPlaced(i)
                      ? TweenAnimationBuilder<double>(
                          // Al encajar: un pequeño salto.
                          key: ValueKey('colocada-$i-${justPlaced == i}'),
                          tween: Tween(begin: justPlaced == i && !reduced ? 1.18 : 1, end: 1),
                          duration: const Duration(milliseconds: 380),
                          curve: Curves.easeOutBack,
                          builder: (context, s, child) => Transform.scale(scale: s, child: child),
                          child: Semantics(
                            label: 'Casilla ${i + 1}: pieza colocada',
                            child: _PieceImage(piece: i, side: side, painter: painter, size: cell),
                          ),
                        )
                      : DragTarget<int>(
                          key: ValueKey('casilla-$i'),
                          onWillAcceptWithDetails: (_) => true,
                          onAcceptWithDetails: (d) => onDrop(d.data, i),
                          builder: (context, candidates, _) => Semantics(
                            button: true,
                            label: 'Casilla ${i + 1}',
                            excludeSemantics: true,
                            onTap: () => onTapCell(i),
                            child: GestureDetector(
                              onTap: () => onTapCell(i),
                              child: Container(
                                width: cell,
                                height: cell,
                                decoration: BoxDecoration(
                                  color: candidates.isNotEmpty ? AppColors.sun.withValues(alpha: 0.3) : null,
                                  border: Border.all(color: AppColors.inkSoft.withValues(alpha: 0.35)),
                                ),
                              ),
                            ),
                          ),
                        ),
                ),
              if (game.isComplete) const Positioned.fill(child: RisingStars()),
            ],
          ),
        ),
      ),
    );
  }
}
