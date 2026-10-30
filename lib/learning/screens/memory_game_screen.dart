import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../models/drawing_catalog.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../theme/app_motion.dart';
import '../../widgets/drawing_thumbnail.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/learning_audio.dart';
import '../games/memory_game.dart';
import '../learning_content.dart';
import '../learning_level.dart';
import '../rewards.dart';
import '../widgets/activity_complete.dart';
import 'quiz_game_screen.dart' show activityDonePhrase;
import '../widgets/question_progress.dart';

/// «Une las parejas» con dibujos del catálogo. Sin tiempo ni penalizaciones.
class MemoryGameScreen extends StatefulWidget {
  const MemoryGameScreen({super.key, required this.catalog, this.seed});

  final DrawingCatalog catalog;
  final int? seed;

  /// Pausa antes de ocultar dos cartas que no coinciden.
  static const mismatchPause = Duration(milliseconds: 1200);

  @override
  State<MemoryGameScreen> createState() => _MemoryGameScreenState();
}

class _MemoryGameScreenState extends State<MemoryGameScreen> {
  late MemoryGame _game;
  late AppServices _services;
  bool _started = false;
  bool _finished = false;
  bool _recorded = false;
  int _rounds = 0;
  Timer? _hideTimer;
  List<Reward> _newRewards = const [];
  String? _message;

  /// Dibujos disponibles para las cartas (solo los que existen y tienen miniatura).
  List<String> get _faces =>
      memoryCardDrawings.where((id) => widget.catalog.byId(id)?.thumbnailAsset != null).toList();

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
    _hideTimer?.cancel();
    final level = _services.learning.settings.level;
    _game = MemoryGame(
      faces: _faces,
      pairs: min(pairsFor(level), _faces.length),
      random: widget.seed == null ? null : Random(widget.seed! + _rounds++),
    );
    _finished = false;
    _recorded = false;
    _newRewards = const [];
    _message = null;
    unawaited(_services.audio.say('Busca las parejas iguales'));
  }

  void _flip(MemoryCard card) {
    final result = _game.flip(card.id);
    if (result == FlipResult.ignored) return;
    final audio = _services.audio;
    setState(() => _message = null);
    switch (result) {
      case FlipResult.flipped:
        unawaited(audio.play(SoundCue.tap));
      case FlipResult.match:
        unawaited(audio.play(SoundCue.correct));
        setState(() => _message = '¡Pareja encontrada!');
        if (_game.isFinished) unawaited(_finish());
      case FlipResult.noMatch:
        unawaited(audio.play(SoundCue.tryAgain));
        setState(() => _message = '¡Casi! Inténtalo otra vez');
        _hideTimer = Timer(MemoryGameScreen.mismatchPause, () {
          if (!mounted) return;
          setState(() {
            _game.hideMismatch();
            _message = null;
          });
        });
      case FlipResult.ignored:
        break;
    }
  }

  Future<void> _finish() async {
    _recorded = true;
    unawaited(_services.audio.play(SoundCue.celebrate));
    unawaited(_services.audio.say(activityDonePhrase(_game.pairs)));
    final earned = await _services.learning.recordSession(
      GameId.memory,
      completed: true,
      points: _game.pairs,
    );
    if (!mounted) return;
    setState(() {
      _finished = true;
      _newRewards = earned;
    });
  }

  void _recordPartial() {
    if (_recorded || _game.matchedPairs == 0) return;
    _recorded = true;
    unawaited(_services.learning.recordSession(GameId.memory, completed: false, points: _game.matchedPairs));
  }

  @override
  void dispose() {
    _hideTimer?.cancel();
    _recordPartial();
    unawaited(_services.audio.stopVoice());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: GameId.memory.title,
      titleIcon: Icons.style_rounded,
      accent: AppColors.grape,
      backLabel: 'Volver a los juegos',
      trailing: _finished
          ? null
          : KidIconButton(
              icon: Icons.replay_rounded,
              label: 'Empezar de nuevo',
              color: AppColors.grape,
              onPressed: () {
                _recordPartial();
                setState(_newGame);
              },
            ),
      body: _finished
          ? ActivityComplete(
              stars: _game.pairs,
              newRewards: _newRewards,
              onPlayAgain: () => setState(_newGame),
              onExit: () => Navigator.of(context).maybePop(),
            )
          : _board(),
    );
  }

  Widget _board() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppDimens.pagePadding,
        4,
        AppDimens.pagePadding,
        AppDimens.pagePadding,
      ),
      child: Column(
        children: [
          QuestionProgress(done: _game.matchedPairs, total: _game.pairs, label: 'Pareja'),
          SizedBox(
            height: 44,
            child: Center(
              child: Semantics(
                liveRegion: true,
                child: Text(
                  _message ?? 'Busca las parejas iguales',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ),
          ),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final count = _game.cards.length;
                // Columnas que hacen las cartas lo más grandes posible.
                var bestSide = 0.0;
                for (var cols = 2; cols <= count; cols++) {
                  final rows = (count / cols).ceil();
                  final side = min(
                    (constraints.maxWidth - (cols - 1) * 12) / cols,
                    (constraints.maxHeight - (rows - 1) * 12) / rows,
                  );
                  if (side > bestSide) bestSide = side;
                }
                final side = bestSide.clamp(60.0, 260.0);
                return Center(
                  child: SingleChildScrollView(
                    child: Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      alignment: WrapAlignment.center,
                      children: [
                        for (final card in _game.cards)
                          SizedBox.square(
                            key: ValueKey('carta-${card.id}'),
                            dimension: side,
                            child: _CardView(card: card, catalog: widget.catalog, onTap: () => _flip(card)),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _CardView extends StatelessWidget {
  const _CardView({required this.card, required this.catalog, required this.onTap});

  static const flipDuration = Duration(milliseconds: 260);

  final MemoryCard card;
  final DrawingCatalog catalog;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final drawing = catalog.byId(card.face);
    final name = drawing?.name ?? card.face;
    final shown = card.faceUp || card.matched;
    final label = card.matched
        ? '$name, pareja encontrada'
        : (shown ? name : 'Carta ${card.id + 1}, boca abajo');
    final reduceMotion = AppMotion.reduced(context);
    Widget side(bool front) => Material(
      color: front ? AppColors.surface : AppColors.grape,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
        side: BorderSide(color: card.matched ? AppColors.leaf : Colors.white, width: card.matched ? 5 : 3),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
        // El toque depende del estado real de la carta, no de la animación:
        // una carta que se está dando la vuelta ya se puede volver a tocar.
        onTap: shown ? null : onTap,
        child: Stack(
          children: [
            Positioned.fill(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: front
                    ? DrawingThumbnail(asset: drawing?.thumbnailAsset)
                    : const FittedBox(child: Icon(Icons.question_mark_rounded, color: Colors.white)),
              ),
            ),
            if (card.matched)
              Positioned(
                top: 4,
                right: 4,
                child: Container(
                  decoration: const BoxDecoration(color: AppColors.leaf, shape: BoxShape.circle),
                  child: const Icon(Icons.check_rounded, color: Colors.white, size: 26),
                ),
              ),
          ],
        ),
      ),
    );
    return Semantics(
      button: !shown,
      label: label,
      excludeSemantics: true,
      onTap: shown ? null : onTap,
      // Giro de la carta: un único hijo que gira sobre el eje vertical; a mitad
      // de giro (de canto) se cambia la cara visible.
      child: TweenAnimationBuilder<double>(
        tween: Tween(end: shown ? 1 : 0),
        duration: reduceMotion ? Duration.zero : _CardView.flipDuration,
        curve: Curves.easeInOut,
        builder: (context, t, _) {
          final edge = (t - 0.5).abs() * 2; // 1 = de frente, 0 = de canto
          return Transform(
            alignment: Alignment.center,
            transform: Matrix4.identity()..scaleByDouble(0.2 + 0.8 * edge, 1, 1, 1),
            // Pequeño latido al encontrar la pareja (una vez).
            child: TweenAnimationBuilder<double>(
              key: ValueKey(card.matched),
              tween: Tween(begin: card.matched && !reduceMotion ? 1.12 : 1, end: 1),
              duration: const Duration(milliseconds: 420),
              curve: Curves.easeOutBack,
              builder: (context, scale, child) => Transform.scale(scale: scale, child: child),
              child: side(t >= 0.5),
            ),
          );
        },
      ),
    );
  }
}
