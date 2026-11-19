import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../achievement_data.dart';
import '../reading_activities.dart';
import '../widgets/reading_widgets.dart';

/// «Aprendo a leer»: Lolo, el progreso y las cuatro actividades.
class ReadingHubScreen extends StatelessWidget {
  const ReadingHubScreen({super.key});

  static const greeting = '¡Vamos a aprender juntos!';

  @override
  Widget build(BuildContext context) {
    final progress = AppServices.of(context).reading;
    return KidScaffold(
      title: 'Aprendo a leer',
      titleIcon: Icons.auto_stories_rounded,
      accent: ReadingActivities.accent,
      backLabel: 'Volver',
      trailing: const ReadingHomeButton(),
      body: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(AppDimens.pagePadding, 0, AppDimens.pagePadding, 12),
            sliver: SliverList(
              delegate: SliverChildListDelegate.fixed([
                const ReadingLolo(text: greeting),
                const SizedBox(height: 14),
                // Actividades con algo hecho, a partir del progreso guardado.
                ListenableBuilder(
                  listenable: progress,
                  builder: (context, _) {
                    final a = progress.progress.achievements;
                    final started = ReadingModule.all.where(a.lastActivity.containsKey).length;
                    return Column(
                      children: [
                        ReadingProgressBar(done: started, total: 4, label: 'Actividades empezadas'),
                        const SizedBox(height: 12),
                        Wrap(
                          alignment: WrapAlignment.center,
                          spacing: 12,
                          runSpacing: 12,
                          children: [
                            SizedBox(
                              width: 260,
                              child: BigActionButton(
                                label: 'Mis logros',
                                icon: Icons.emoji_events_rounded,
                                color: AppColors.sun,
                                onPressed: () =>
                                    Navigator.of(context).pushNamed(AppRoutes.readingAchievements),
                              ),
                            ),
                            SizedBox(
                              width: 260,
                              child: BigActionButton(
                                label: 'Mi camino',
                                icon: Icons.route_rounded,
                                color: AppColors.leaf,
                                onPressed: () => Navigator.of(context).pushNamed(AppRoutes.readingPath),
                              ),
                            ),
                          ],
                        ),
                      ],
                    );
                  },
                ),
              ]),
            ),
          ),
          AdaptiveSliverGrid(
            itemCount: ReadingActivities.all.length,
            minTileWidth: 160,
            maxColumns: 4,
            childAspectRatio: 0.95,
            itemBuilder: (context, i) {
              final a = ReadingActivities.all[i];
              return ReadingActivityCard(activity: a, onTap: () => Navigator.of(context).pushNamed(a.route));
            },
          ),
          const SliverToBoxAdapter(child: SizedBox(height: AppDimens.pagePadding)),
        ],
      ),
    );
  }
}
