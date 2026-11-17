import 'package:flutter/material.dart';

import '../../theme/app_dimens.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../reading_activities.dart';
import '../widgets/reading_widgets.dart';

/// «Aprendo a leer»: Lolo, el progreso y las cuatro actividades.
class ReadingHubScreen extends StatelessWidget {
  const ReadingHubScreen({super.key});

  static const greeting = '¡Vamos a aprender juntos!';

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Aprendo a leer',
      titleIcon: Icons.auto_stories_rounded,
      accent: ReadingActivities.accent,
      backLabel: 'Volver',
      trailing: const ReadingHomeButton(),
      body: CustomScrollView(
        slivers: [
          const SliverPadding(
            padding: EdgeInsets.fromLTRB(AppDimens.pagePadding, 0, AppDimens.pagePadding, 12),
            sliver: SliverList(
              delegate: SliverChildListDelegate.fixed([
                ReadingLolo(text: greeting),
                SizedBox(height: 14),
                // El progreso real se guarda a partir de la Fase G.
                ReadingProgressBar(done: 0, total: 4, label: 'Mis actividades'),
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
