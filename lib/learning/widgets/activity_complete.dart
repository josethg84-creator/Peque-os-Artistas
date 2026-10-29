import 'dart:async';

import 'package:flutter/material.dart';

import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_motion.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/mascot.dart';
import '../../widgets/motion/celebration.dart';
import '../audio/learning_audio.dart';
import '../rewards.dart';
import 'reward_sticker.dart';

/// Pantalla de actividad completada: celebración breve, estrellas ganadas,
/// pegatinas nuevas y botones para repetir o volver.
///
/// Las estrellas suben siempre; el confeti y el sonido de premio solo cuando
/// llega una pegatina nueva (una vez: los premios ya conseguidos no se
/// vuelven a conceder, así que tampoco se vuelven a celebrar).
class ActivityComplete extends StatefulWidget {
  const ActivityComplete({
    super.key,
    required this.stars,
    required this.newRewards,
    required this.onPlayAgain,
    required this.onExit,
  });

  final int stars;
  final List<Reward> newRewards;
  final VoidCallback onPlayAgain;
  final VoidCallback onExit;

  static const messages = ['¡Lo has conseguido!', '¡Qué gran trabajo!', '¡Eres genial!', '¡Sigue así!'];

  @override
  State<ActivityComplete> createState() => _ActivityCompleteState();
}

class _ActivityCompleteState extends State<ActivityComplete> {
  /// Cambia el mensaje de la mascota en cada partida terminada.
  static int _shown = 0;
  late final String _message = ActivityComplete.messages[_shown++ % ActivityComplete.messages.length];

  @override
  void initState() {
    super.initState();
    if (widget.newRewards.isNotEmpty) _playReward();
  }

  @override
  void didUpdateWidget(ActivityComplete old) {
    super.didUpdateWidget(old);
    // Los premios llegan un instante después (se guardan antes de mostrarse).
    if (old.newRewards.isEmpty && widget.newRewards.isNotEmpty) _playReward();
  }

  void _playReward() {
    // Lectura puntual (sin dependencia): también vale desde initState.
    final audio = context.getInheritedWidgetOfExactType<AppServices>()?.audio;
    if (audio != null) unawaited(audio.play(SoundCue.reward));
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = AppMotion.reduced(context);
    final text = Theme.of(context).textTheme;
    return Stack(
      children: [
        SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              SizedBox(
                height: 130,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    TweenAnimationBuilder<double>(
                      tween: Tween(begin: reduceMotion ? 1 : 0.6, end: 1),
                      duration: const Duration(milliseconds: 500),
                      curve: Curves.elasticOut,
                      builder: (context, scale, child) => Transform.scale(scale: scale, child: child),
                      child: const Icon(Icons.emoji_events_rounded, size: 120, color: AppColors.sun),
                    ),
                    const Positioned.fill(child: RisingStars()),
                  ],
                ),
              ),
              Semantics(
                header: true,
                liveRegion: true,
                child: Text('¡Excelente trabajo!', textAlign: TextAlign.center, style: text.headlineMedium),
              ),
              const SizedBox(height: 8),
              Semantics(
                label: 'Ganaste ${widget.stars} estrellas',
                excludeSemantics: true,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.star_rounded, color: AppColors.sun, size: 40),
                    Text('+${widget.stars}', style: text.headlineSmall),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              MascotBubble(text: _message, size: 64, waves: 1),
              if (widget.newRewards.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text('¡Pegatina nueva!', style: text.titleLarge),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 16,
                  runSpacing: 12,
                  alignment: WrapAlignment.center,
                  children: [
                    for (final (i, r) in widget.newRewards.indexed)
                      TweenAnimationBuilder<double>(
                        tween: Tween(begin: reduceMotion ? 1 : 0, end: 1),
                        duration: const Duration(milliseconds: 700),
                        curve: Interval((i * 0.15).clamp(0.0, 0.6), 1, curve: Curves.elasticOut),
                        builder: (context, t, child) => Transform.scale(scale: t, child: child),
                        child: SizedBox(width: 120, child: RewardSticker(reward: r, earned: true)),
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 20),
              Text('¿Jugamos otra vez?', style: text.titleLarge),
              const SizedBox(height: 12),
              BigActionButton(
                label: 'Jugar otra vez',
                icon: Icons.replay_rounded,
                color: AppColors.leaf,
                onPressed: widget.onPlayAgain,
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(minimumSize: const Size(200, 64)),
                onPressed: widget.onExit,
                icon: const Icon(Icons.apps_rounded, size: 28),
                label: const Text(
                  'Otros juegos',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
        ),
        if (widget.newRewards.isNotEmpty) const Positioned.fill(child: ConfettiBurst()),
      ],
    );
  }
}
