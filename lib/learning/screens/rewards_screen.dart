import 'package:flutter/material.dart';

import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/kid_scaffold.dart';
import '../rewards.dart';
import '../widgets/reward_sticker.dart';

/// «Mis premios»: estrellas acumuladas y pegatinas. Las que faltan se ven en
/// gris con una pista; no hay clasificaciones ni comparaciones.
class RewardsScreen extends StatelessWidget {
  const RewardsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;
    return KidScaffold(
      title: 'Mis premios',
      titleIcon: Icons.emoji_events_rounded,
      accent: AppColors.sun,
      backLabel: 'Volver a los juegos',
      body: ListenableBuilder(
        listenable: learning,
        builder: (context, _) {
          final progress = learning.progress;
          final earned = progress.rewards.length;
          return ListView(
            padding: const EdgeInsets.all(AppDimens.pagePadding),
            children: [
              Semantics(
                label: 'Tienes ${progress.stars} estrellas',
                excludeSemantics: true,
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.sun.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.star_rounded, color: AppColors.sun, size: 56),
                      const SizedBox(width: 8),
                      Text('${progress.stars}', style: Theme.of(context).textTheme.displaySmall),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                earned == 0 ? '¡Juega y consigue tu primera pegatina!' : '¡Mira todas tus pegatinas!',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 18,
                runSpacing: 18,
                alignment: WrapAlignment.center,
                children: [
                  for (final r in rewards)
                    SizedBox(
                      width: 130,
                      child: RewardSticker(reward: r, earned: progress.rewards.containsKey(r.id)),
                    ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}
