import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../widgets/big_action_button.dart';
import '../rewards.dart';
import 'reward_sticker.dart';

/// Pantalla de actividad completada: celebración breve, estrellas ganadas,
/// pegatinas nuevas y botones para repetir o volver.
class ActivityComplete extends StatelessWidget {
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

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          TweenAnimationBuilder<double>(
            tween: Tween(begin: reduceMotion ? 1 : 0.6, end: 1),
            duration: const Duration(milliseconds: 500),
            curve: Curves.elasticOut,
            builder: (context, scale, child) => Transform.scale(scale: scale, child: child),
            child: const Icon(Icons.emoji_events_rounded, size: 120, color: AppColors.sun),
          ),
          Semantics(
            header: true,
            liveRegion: true,
            child: Text(
              '¡Excelente trabajo!',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ),
          const SizedBox(height: 8),
          Semantics(
            label: 'Ganaste $stars estrellas',
            excludeSemantics: true,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.star_rounded, color: AppColors.sun, size: 40),
                Text('+$stars', style: Theme.of(context).textTheme.headlineSmall),
              ],
            ),
          ),
          if (newRewards.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text('¡Pegatina nueva!', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Wrap(
              spacing: 16,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                for (final r in newRewards)
                  SizedBox(width: 120, child: RewardSticker(reward: r, earned: true)),
              ],
            ),
          ],
          const SizedBox(height: 20),
          Text('¿Jugamos otra vez?', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          BigActionButton(
            label: 'Jugar otra vez',
            icon: Icons.replay_rounded,
            color: AppColors.leaf,
            onPressed: onPlayAgain,
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(minimumSize: const Size(200, 64)),
            onPressed: onExit,
            icon: const Icon(Icons.apps_rounded, size: 28),
            label: const Text('Otros juegos', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
          ),
        ],
      ),
    );
  }
}
