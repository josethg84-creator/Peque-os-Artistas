import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_scaffold.dart';
import '../../widgets/motion/pressable.dart';
import '../mission.dart';
import '../speech_progress.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _missionColor = Color(0xFF7E57C2);

/// Colores del arcoíris, uno por misión.
const rainbowColors = [
  Color(0xFFEF5350),
  Color(0xFFFFA726),
  Color(0xFFFFEE58),
  Color(0xFF66BB6A),
  Color(0xFF42A5F5),
];

const _taskIcons = {
  'palabras': Icons.abc_rounded,
  'oraciones': Icons.view_week_rounded,
  'verbo': Icons.directions_run_rounded,
  'cuento': Icons.auto_stories_rounded,
  'charla': Icons.forum_rounded,
};

/// Arcoíris de la aventura: cada misión hecha pinta su franja; las saltadas
/// quedan suaves (sin nada que se pierda).
class RainbowPainter extends CustomPainter {
  const RainbowPainter({required this.done, required this.skipped});

  final List<bool> done;
  final List<bool> skipped;

  @override
  void paint(Canvas canvas, Size size) {
    final n = done.length;
    // El arco cabe siempre en su caja (ancho y alto).
    final outer = min(size.width / 2, size.height * 0.92);
    final band = outer / (n + 2);
    final center = Offset(size.width / 2, size.height - band * 0.5);
    for (var i = 0; i < n; i++) {
      final r = outer - band * (i + 0.5);
      if (r <= 0) continue;
      final color = rainbowColors[i % rainbowColors.length];
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = band * 0.9
        ..strokeCap = StrokeCap.round
        // Hecha: su color. Pendiente: el mismo color muy suave. Saltada: casi invisible.
        ..color = done[i]
            ? color
            : (skipped[i] ? color.withValues(alpha: 0.1) : Color.lerp(color, Colors.white, 0.72)!);
      canvas.drawArc(Rect.fromCircle(center: center, radius: r), pi, pi, false, paint);
    }
    // Nubes en los extremos.
    final cloud = Paint()..color = Colors.white;
    for (final x in [size.width / 2 - outer + band * 1.2, size.width / 2 + outer - band * 1.2]) {
      canvas.drawCircle(Offset(x, center.dy - band * 0.2), band * 1.1, cloud);
      canvas.drawCircle(Offset(x - band, center.dy), band * 0.8, cloud);
      canvas.drawCircle(Offset(x + band, center.dy), band * 0.8, cloud);
    }
  }

  @override
  bool shouldRepaint(RainbowPainter old) =>
      old.done.toString() != done.toString() || old.skipped.toString() != skipped.toString();
}

class _Rainbow extends StatelessWidget {
  const _Rainbow({required this.today, this.height = 120});

  final DailyRecord today;
  final double height;

  @override
  Widget build(BuildContext context) {
    final tasks = DailyMission.tasks;
    final n = DailyMission.doneCount(today);
    return Semantics(
      container: true,
      label: 'Arcoíris: $n de ${tasks.length} misiones hechas',
      excludeSemantics: true,
      child: SizedBox(
        height: height,
        child: CustomPaint(
          size: Size.infinite,
          painter: RainbowPainter(
            done: [for (final t in tasks) DailyMission.done(today, t)],
            skipped: [for (final t in tasks) DailyMission.skipped(today, t)],
          ),
        ),
      ),
    );
  }
}

/// Tarjeta ancha del menú que abre «Mi aventura de hoy».
class MissionBanner extends StatelessWidget {
  const MissionBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return ListenableBuilder(
      listenable: speech,
      builder: (context, _) {
        final today = speech.today;
        final n = DailyMission.doneCount(today);
        final total = DailyMission.tasks.length;
        final label = DailyMission.complete(today) ? '¡Aventura completada!' : '$n de $total misiones';
        return Semantics(
          container: true,
          button: true,
          label: 'Mi aventura de hoy. $label',
          excludeSemantics: true,
          onTap: () => _open(context),
          child: Pressable(
            scale: 0.97,
            child: GestureDetector(
              onTap: () => _open(context),
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 10, 12, 10),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(colors: [Color(0xFFF3E5F5), Color(0xFFE1F5FE)]),
                  borderRadius: BorderRadius.circular(28),
                  border: Border.all(color: Colors.white, width: 3),
                  boxShadow: const [
                    BoxShadow(color: Color(0x33B39DDB), offset: Offset(0, 5)),
                    BoxShadow(color: Color(0x1A000000), blurRadius: 10, offset: Offset(0, 6)),
                  ],
                ),
                child: Row(
                  children: [
                    SizedBox(width: 92, child: _Rainbow(today: today, height: 52)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Mi aventura de hoy', style: fredoka(22, color: const Color(0xFF4A2C8A))),
                          Text(label, style: fredoka(16, color: AppColors.inkSoft)),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right_rounded, size: 36, color: _missionColor),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  static void _open(BuildContext context) {
    AppServices.of(context).speech.markVisit(AppRoutes.speechMission);
    Navigator.of(context).pushNamed(AppRoutes.speechMission);
  }
}

/// «Mi aventura de hoy»: cinco misiones cortas y opcionales.
class MissionScreen extends StatefulWidget {
  const MissionScreen({super.key});

  @override
  State<MissionScreen> createState() => _MissionScreenState();
}

class _MissionScreenState extends State<MissionScreen> {
  bool _celebrated = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final today = AppServices.of(context).speech.today;
      _celebrated = DailyMission.complete(today);
      speak(context, _celebrated ? _doneText : _intro);
    });
  }

  static const _intro =
      '¡Hola! Esta es tu aventura de hoy. Elige la misión que quieras. También puedes saltarla.';
  static const _doneText = '¡Completaste tu aventura de hoy! ¡El arcoíris brilla!';

  void _check(DailyRecord today) {
    if (_celebrated || !DailyMission.complete(today)) return;
    _celebrated = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      unawaited(AppServices.of(context).audio.play(SoundCue.celebrate));
      speak(context, _doneText);
    });
  }

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Mi aventura de hoy',
      titleIcon: Icons.wb_twilight_rounded,
      accent: _missionColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: speech,
          builder: (context, _) {
            final today = speech.today;
            _check(today);
            final complete = DailyMission.complete(today);
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: LoloBubble(text: complete ? _doneText : _intro, size: 56),
                ),
                const SizedBox(height: 8),
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: _Rainbow(today: today, height: 130),
                  ),
                ),
                Text(
                  'Unos ${speech.progress.preferences.minutes} minutos. Puedes elegir el orden o saltar las que quieras.',
                  textAlign: TextAlign.center,
                  style: fredoka(16, color: AppColors.inkSoft),
                ),
                const SizedBox(height: 12),
                for (final (i, t) in DailyMission.tasks.indexed)
                  _TaskCard(
                    task: t,
                    color: rainbowColors[i],
                    today: today,
                    onGo: () {
                      final (route, args) = DailyMission.destination(t, speech.progress, content);
                      speech.markVisit(route);
                      speak(context, t.lolo);
                      Navigator.of(context).pushNamed(route, arguments: args);
                    },
                    onSkip: (skip) => speech.setMissionSkipped(t.id, skip),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _TaskCard extends StatelessWidget {
  const _TaskCard({
    required this.task,
    required this.color,
    required this.today,
    required this.onGo,
    required this.onSkip,
  });

  final MissionTask task;
  final Color color;
  final DailyRecord today;
  final VoidCallback onGo;
  final ValueChanged<bool> onSkip;

  @override
  Widget build(BuildContext context) {
    final done = DailyMission.done(today, task);
    final skipped = DailyMission.skipped(today, task);
    final progress = DailyMission.progress(today, task);
    final ink = Color.lerp(color, const Color(0xFF2A2350), 0.7)!;
    final status = done ? '¡Hecho!' : (skipped ? 'Saltada' : '$progress de ${task.goal}');
    return Opacity(
      opacity: skipped ? 0.6 : 1,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: done ? Color.lerp(color, Colors.white, 0.8) : Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: color.withValues(alpha: 0.7), width: 3),
          boxShadow: [BoxShadow(color: color.withValues(alpha: 0.35), offset: const Offset(0, 4))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(
              container: true,
              label: '${task.title}: $status',
              excludeSemantics: true,
              child: Row(
                children: [
                  Container(
                    width: 60,
                    height: 60,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [Color.lerp(color, Colors.white, 0.3)!, color],
                      ),
                      border: Border.all(color: Colors.white, width: 3),
                      boxShadow: [BoxShadow(color: color.withValues(alpha: 0.5), offset: const Offset(0, 3))],
                    ),
                    child: Icon(_taskIcons[task.id] ?? Icons.star_rounded, color: Colors.white, size: 34),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(task.title, style: fredoka(22, color: ink)),
                        Row(
                          children: [
                            for (var k = 0; k < task.goal; k++)
                              Padding(
                                padding: const EdgeInsets.only(right: 4),
                                child: Icon(
                                  k < progress ? Icons.star_rounded : Icons.star_outline_rounded,
                                  color: k < progress ? AppColors.sun : const Color(0xFFD1C4E9),
                                  size: 26,
                                ),
                              ),
                            const SizedBox(width: 4),
                            Flexible(
                              child: Text(status, style: fredoka(16, color: AppColors.inkSoft)),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  if (done) const Icon(Icons.check_circle_rounded, color: Color(0xFF43A047), size: 36),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              alignment: WrapAlignment.end,
              children: [
                SizedBox(
                  width: 150,
                  child: SpeechActionButton(
                    icon: done ? Icons.replay_rounded : Icons.play_arrow_rounded,
                    label: done ? 'Otra vez' : '¡Vamos!',
                    semanticLabel: done ? 'Otra vez: ${task.title}' : '¡Vamos! ${task.title}',
                    color: color == rainbowColors[2] ? const Color(0xFFF9A825) : color,
                    onPressed: onGo,
                  ),
                ),
                if (!done)
                  SizedBox(
                    width: 150,
                    child: SpeechActionButton(
                      icon: skipped ? Icons.undo_rounded : Icons.skip_next_rounded,
                      label: skipped ? 'Volver a ponerla' : 'Saltar',
                      semanticLabel: skipped ? 'Volver a ponerla: ${task.title}' : 'Saltar: ${task.title}',
                      color: const Color(0xFF90A4AE),
                      onPressed: () => onSkip(!skipped),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
