import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/phrases.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../../widgets/menu_tile.dart';
import '../../widgets/motion/celebration.dart';
import '../audio/learning_audio.dart';
import '../games/tracing.dart';
import '../learning_level.dart';
import '../rewards.dart';
import '../widgets/activity_complete.dart';
import '../widgets/feedback_panel.dart';
import 'quiz_game_screen.dart' show activityDonePhrase;

/// «Trazos y escritura»: líneas, letras, números y unir puntos.
class TracingGameScreen extends StatelessWidget {
  const TracingGameScreen({super.key});

  static const sections = [
    (TraceSection.lines, Icons.timeline_rounded, AppColors.coral),
    (TraceSection.letters, Icons.abc_rounded, AppColors.sky),
    (TraceSection.numbers, Icons.pin_rounded, AppColors.leaf),
    (TraceSection.dots, Icons.scatter_plot_rounded, AppColors.grape),
  ];

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: GameId.tracing.title,
      titleIcon: Icons.gesture_rounded,
      accent: AppColors.berry,
      backLabel: 'Volver a los juegos',
      body: AdaptiveGrid(
        itemCount: sections.length,
        minTileWidth: 200,
        maxColumns: 4,
        tileHeight: 200,
        itemBuilder: (context, i) {
          final (section, icon, color) = sections[i];
          return MenuTile(
            icon: icon,
            label: section.title,
            color: color,
            badge: '${traceItems(section).length} ejercicios',
            badgeIcon: Icons.format_list_numbered_rounded,
            fitLabel: true,
            onTap: () =>
                Navigator.of(context)
                    .push(MaterialPageRoute<void>(builder: (_) => TracingSectionScreen(section: section))),
          );
        },
      ),
    );
  }
}

/// Lista de ejercicios de una sección: se empieza por el que se elija.
class TracingSectionScreen extends StatelessWidget {
  const TracingSectionScreen({super.key, required this.section});

  final TraceSection section;

  @override
  Widget build(BuildContext context) {
    final items = traceItems(section);
    final big = section == TraceSection.letters || section == TraceSection.numbers;
    return KidScaffold(
      title: section.title,
      accent: AppColors.berry,
      backLabel: 'Volver',
      body: AdaptiveGrid(
        itemCount: items.length,
        minTileWidth: big ? 96 : 150,
        maxColumns: big ? 7 : 4,
        childAspectRatio: 1,
        itemBuilder: (context, i) {
          final item = items[i];
          return Semantics(
            button: true,
            label: item.spoken ?? item.label,
            excludeSemantics: true,
            onTap: () => _open(context, i),
            child: Material(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
              elevation: 1,
              child: InkWell(
                borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
                onTap: () => _open(context, i),
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: big
                      ? Center(
                          child: FittedBox(
                            child: Text(
                              item.label,
                              style: const TextStyle(
                                fontSize: 48,
                                fontWeight: FontWeight.w900,
                                color: AppColors.ink,
                              ),
                            ),
                          ),
                        )
                      : Column(
                          children: [
                            Expanded(
                              child: CustomPaint(size: Size.infinite, painter: _PreviewPainter(item)),
                            ),
                            Text(item.label, textAlign: TextAlign.center, maxLines: 2),
                          ],
                        ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  void _open(BuildContext context, int index) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => TracingPracticeScreen(section: section, start: index),
    ),
  );
}

/// Practica varios ejercicios seguidos (más cuanto más alto el nivel).
class TracingPracticeScreen extends StatefulWidget {
  const TracingPracticeScreen({super.key, required this.section, required this.start});

  final TraceSection section;
  final int start;

  @override
  State<TracingPracticeScreen> createState() => _TracingPracticeScreenState();
}

class _TracingPracticeScreenState extends State<TracingPracticeScreen> {
  late AppServices _services;
  late TraceDifficulty _difficulty;
  late List<TraceItem> _items;
  late int _index;
  late TraceEvaluator _eval;
  final _ink = <List<Offset>>[];
  int _done = 0;
  bool _started = false;
  bool _itemDone = false;
  bool _finished = false;
  bool _offPathWarned = false;
  List<Reward> _newRewards = const [];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _services = AppServices.of(context);
    if (!_started) {
      _started = true;
      _items = traceItems(widget.section);
      _index = widget.start;
      _newSession();
    }
  }

  TraceItem get _item => _items[_index % _items.length];

  void _newSession() {
    _difficulty = TraceDifficulty.of(_services.learning.settings.level);
    _done = 0;
    _finished = false;
    _newRewards = const [];
    _loadItem();
  }

  void _loadItem() {
    _eval = TraceEvaluator(_item, _difficulty);
    _ink.clear();
    _itemDone = false;
    _offPathWarned = false;
    _sayInstruction();
  }

  void _sayInstruction() {
    final item = _item;
    unawaited(_services.audio.say('${widget.section.instruction}. ${item.spoken ?? item.label}'));
  }

  int get _goal => min(_difficulty.itemsPerSession, _items.length);

  void _erase() => setState(() {
    _eval.reset();
    _ink.clear();
    _itemDone = false;
  });

  void _point(Offset p, {bool start = false}) {
    if (_itemDone) return;
    setState(() {
      if (start || _ink.isEmpty) _ink.add([]);
      _ink.last.add(p);
      _eval.addPoint(p);
    });
    if (_eval.isComplete) {
      setState(() => _itemDone = true);
      unawaited(_services.audio.play(SoundCue.correct));
      unawaited(_services.audio.sayOneOf(Phrases.traceDone));
    } else if (!_offPathWarned && _eval.mostlyOffPath) {
      _offPathWarned = true;
      unawaited(_services.audio.say(Phrases.traceFollow, mode: VoiceMode.ambient));
    }
  }

  Future<void> _next() async {
    _done++;
    if (_done >= _goal) {
      setState(() => _finished = true);
      unawaited(_services.audio.play(SoundCue.celebrate));
      unawaited(_services.audio.say(activityDonePhrase(_goal)));
      final earned = await _services.learning.recordSession(GameId.tracing, completed: true, points: _goal);
      if (mounted) setState(() => _newRewards = earned);
      return;
    }
    setState(() {
      _index++;
      _loadItem();
    });
  }

  @override
  void dispose() {
    unawaited(_services.audio.stopVoice());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final item = _item;
    return KidScaffold(
      title: widget.section.title,
      accent: AppColors.berry,
      backLabel: 'Volver',
      trailing: _finished
          ? null
          : KidIconButton(
              icon: Icons.cleaning_services_rounded,
              label: 'Borrar',
              color: AppColors.berry,
              onPressed: _erase,
            ),
      body: _finished
          ? ActivityComplete(
              stars: _goal,
              newRewards: _newRewards,
              onPlayAgain: () => setState(() {
                _index++;
                _newSession();
              }),
              onExit: () => Navigator.of(context).maybePop(),
            )
          : LayoutBuilder(
              builder: (context, constraints) {
                final side = min(
                  constraints.maxWidth - 2 * AppDimens.pagePadding,
                  constraints.maxHeight - 230,
                ).clamp(220.0, 560.0);
                return SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(
                    AppDimens.pagePadding,
                    0,
                    AppDimens.pagePadding,
                    AppDimens.pagePadding,
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Semantics(
                              header: true,
                              liveRegion: true,
                              child: Text(
                                item.isDots ? 'Une los puntos: ${item.label}' : item.label,
                                style: Theme.of(context).textTheme.headlineSmall,
                              ),
                            ),
                          ),
                          if (_services.learning.settings.voiceOn)
                            KidIconButton(
                              icon: Icons.volume_up_rounded,
                              label: 'Escuchar',
                              color: AppColors.berry,
                              size: 56,
                              onPressed: _sayInstruction,
                            ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Semantics(
                        label: 'Progreso del trazo',
                        value: '${(_eval.progress * 100).round()} %',
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: LinearProgressIndicator(
                            value: _eval.progress,
                            minHeight: 14,
                            color: AppColors.leaf,
                            backgroundColor: AppColors.leaf.withValues(alpha: 0.2),
                          ),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Text(
                          'Ejercicio ${_done + 1} de $_goal',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                      Center(
                        child: Container(
                          key: const ValueKey('lienzo-trazo'),
                          width: side,
                          height: side,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
                            border: Border.all(color: AppColors.berry.withValues(alpha: 0.5), width: 3),
                          ),
                          child: Semantics(
                            label: 'Zona para dibujar con el dedo: ${item.spoken ?? item.label}',
                            child: GestureDetector(
                              behavior: HitTestBehavior.opaque,
                              onPanStart: (d) => _point(d.localPosition / side, start: true),
                              onPanUpdate: (d) => _point(d.localPosition / side),
                              child: Stack(
                                children: [
                                  CustomPaint(
                                    size: Size.square(side),
                                    painter: _TracePainter(
                                      eval: _eval,
                                      ink: _ink,
                                      difficulty: _difficulty,
                                      done: _itemDone,
                                    ),
                                  ),
                                  if (_itemDone) const Positioned.fill(child: RisingStars()),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      if (_itemDone)
                        FeedbackPanel.success(
                          title: item.isDots
                              ? '¡Es ${item.spoken?.toLowerCase() ?? item.label}!'
                              : '¡Muy bien!',
                          message: item.isDots ? null : 'Completaste: ${item.label}',
                          actionLabel: _done + 1 >= _goal ? '¡Terminar!' : 'Siguiente',
                          onAction: _next,
                        )
                      else if (_eval.mostlyOffPath)
                        Text(Phrases.traceFollow, style: Theme.of(context).textTheme.titleMedium),
                    ],
                  ),
                );
              },
            ),
    );
  }
}

class _TracePainter extends CustomPainter {
  _TracePainter({required this.eval, required this.ink, required this.difficulty, required this.done});

  final TraceEvaluator eval;
  final List<List<Offset>> ink;
  final TraceDifficulty difficulty;
  final bool done;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width;
    final item = eval.item;
    Path pathOf(List<Offset> pts) {
      final p = Path()..moveTo(pts.first.dx * s, pts.first.dy * s);
      for (final q in pts.skip(1)) {
        p.lineTo(q.dx * s, q.dy * s);
      }
      return p;
    }

    final round = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    if (item.isDots) {
      _paintDots(canvas, s, pathOf, round);
    } else {
      // Guía: trazo ancho y suave; encima, lo ya cubierto en verde.
      for (final stroke in item.strokes) {
        canvas.drawPath(
          pathOf(stroke),
          round
            ..color = (done ? AppColors.leaf : AppColors.berry).withValues(alpha: done ? 0.35 : 0.16)
            ..strokeWidth = difficulty.guideWidth * s,
        );
        canvas.drawPath(
          pathOf(stroke),
          round
            ..color = AppColors.inkSoft.withValues(alpha: 0.35)
            ..strokeWidth = 2,
        );
      }
      final covered = Paint()..color = AppColors.leaf;
      for (var st = 0; st < eval.checkpoints.length; st++) {
        final cps = eval.checkpoints[st];
        for (var i = 0; i < cps.length; i++) {
          if (eval.isCovered(st, i)) canvas.drawCircle(cps[i] * s, s * 0.012, covered);
        }
      }
      // Dónde empezar cada trazo (y en qué orden, en los niveles bajos).
      for (final (n, stroke) in item.strokes.indexed) {
        final start = stroke.first * s;
        canvas.drawCircle(start, s * 0.03, Paint()..color = AppColors.leaf);
        if (difficulty.showStrokeOrder) {
          final tp = TextPainter(
            text: TextSpan(
              text: '${n + 1}',
              style: TextStyle(color: Colors.white, fontSize: s * 0.035, fontWeight: FontWeight.w900),
            ),
            textDirection: TextDirection.ltr,
          )..layout();
          tp.paint(canvas, start - Offset(tp.width / 2, tp.height / 2));
          // Flecha de dirección.
          if (stroke.length > 1) {
            final ahead = stroke[min(stroke.length - 1, max(1, stroke.length ~/ 6))] * s;
            final dir = ahead - start;
            if (dir.distance > 0) {
              final u = dir / dir.distance;
              final tip = start + u * s * 0.09;
              final side = Offset(-u.dy, u.dx) * s * 0.022;
              canvas.drawPath(
                Path()
                  ..moveTo(tip.dx, tip.dy)
                  ..lineTo(tip.dx - u.dx * s * 0.035 + side.dx, tip.dy - u.dy * s * 0.035 + side.dy)
                  ..lineTo(tip.dx - u.dx * s * 0.035 - side.dx, tip.dy - u.dy * s * 0.035 - side.dy)
                  ..close(),
                Paint()..color = AppColors.leaf,
              );
            }
          }
        }
      }
    }
    // Lo que dibuja el niño.
    for (final stroke in ink) {
      if (stroke.length < 2) {
        if (stroke.isNotEmpty) {
          canvas.drawCircle(stroke.first * s, s * 0.015, Paint()..color = AppColors.grape);
        }
        continue;
      }
      canvas.drawPath(
        pathOf(stroke),
        round
          ..color = AppColors.grape
          ..strokeWidth = s * 0.03,
      );
    }
  }

  void _paintDots(Canvas canvas, double s, Path Function(List<Offset>) pathOf, Paint round) {
    final dots = eval.item.dots;
    final next = eval.nextDot;
    if (done) {
      canvas.drawPath(
        pathOf(dots),
        round
          ..color = AppColors.leaf
          ..strokeWidth = s * 0.03,
      );
    } else if (next >= 2) {
      canvas.drawPath(
        pathOf(dots.sublist(0, next)),
        round
          ..color = AppColors.leaf
          ..strokeWidth = s * 0.022,
      );
    }
    // Un punto final igual al primero (figura cerrada) no se numera dos veces.
    final closed = (dots.first - dots.last).distance < 1e-6;
    for (var i = 0; i < dots.length - (closed ? 1 : 0); i++) {
      final reached = i < next;
      final isNext = i == next || (closed && next == dots.length - 1 && i == 0);
      final c = dots[i] * s;
      canvas.drawCircle(
        c,
        s * (isNext ? 0.04 : 0.028),
        Paint()..color = reached ? AppColors.leaf : (isNext ? AppColors.coral : AppColors.ink),
      );
      final tp = TextPainter(
        text: TextSpan(
          text: '${i + 1}',
          style: TextStyle(color: AppColors.ink, fontSize: s * 0.04, fontWeight: FontWeight.w800),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, c + Offset(s * 0.03, -s * 0.06));
    }
  }

  @override
  bool shouldRepaint(_TracePainter old) => true;
}

class _PreviewPainter extends CustomPainter {
  _PreviewPainter(this.item);

  final TraceItem item;

  @override
  void paint(Canvas canvas, Size size) {
    final s = min(size.width, size.height);
    final o = Offset((size.width - s) / 2, (size.height - s) / 2);
    final paint = Paint()
      ..color = AppColors.berry
      ..style = PaintingStyle.stroke
      ..strokeWidth = 4
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    for (final stroke in item.strokes) {
      final p = Path()..moveTo(o.dx + stroke.first.dx * s, o.dy + stroke.first.dy * s);
      for (final q in stroke.skip(1)) {
        p.lineTo(o.dx + q.dx * s, o.dy + q.dy * s);
      }
      canvas.drawPath(p, paint);
    }
  }

  @override
  bool shouldRepaint(_PreviewPainter old) => old.item != item;
}
