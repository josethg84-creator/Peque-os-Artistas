import 'dart:async';

import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../../widgets/menu_tile.dart';
import '../audio/learning_audio.dart';
import '../learning_level.dart';
import '../widgets/learning_settings_bar.dart';

/// Las dos secciones de juegos del inicio.
enum HubGroup {
  activities('Actividades', Icons.lightbulb_rounded, AppColors.leaf, [
    GameId.colors,
    GameId.shapes,
    GameId.animals,
    GameId.tracing,
  ]),
  games('Mini juegos', Icons.extension_rounded, AppColors.berry, [GameId.memory, GameId.puzzle, GameId.maze]);

  const HubGroup(this.title, this.icon, this.color, this.members);
  final String title;
  final IconData icon;
  final Color color;
  final List<GameId> members;
}

/// «Actividades» o «Mini juegos»: sus juegos, el nivel y los sonidos.
class LearningHubScreen extends StatefulWidget {
  const LearningHubScreen({super.key, this.group = HubGroup.activities});

  final HubGroup group;

  static const games = [
    (GameId.colors, Icons.palette_rounded, AppColors.coral),
    (GameId.shapes, Icons.category_rounded, AppColors.sky),
    (GameId.animals, Icons.pets_rounded, AppColors.leaf),
    (GameId.memory, Icons.style_rounded, AppColors.grape),
    (GameId.puzzle, Icons.extension_rounded, AppColors.sun),
    (GameId.maze, Icons.alt_route_rounded, AppColors.sky),
    (GameId.tracing, Icons.gesture_rounded, AppColors.berry),
  ];

  @override
  State<LearningHubScreen> createState() => _LearningHubScreenState();
}

class _LearningHubScreenState extends State<LearningHubScreen> {
  late LearningAudio _audio;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _audio = AppServices.of(context).audio;
  }

  @override
  void dispose() {
    // Al salir de «Aprender jugando» se liberan los reproductores de audio.
    unawaited(_audio.release());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;
    final group = widget.group;
    final games = [
      for (final g in LearningHubScreen.games)
        if (group.members.contains(g.$1)) g,
    ];
    return KidScaffold(
      title: group.title,
      titleIcon: group.icon,
      accent: group.color,
      backLabel: 'Volver al inicio',
      trailing: KidIconButton(
        icon: Icons.emoji_events_rounded,
        label: 'Mis premios',
        color: AppColors.sun,
        onPressed: () => Navigator.of(context).pushNamed(AppRoutes.rewards),
      ),
      body: ListenableBuilder(
        listenable: learning,
        builder: (context, _) => CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(AppDimens.pagePadding, 4, AppDimens.pagePadding, 0),
              sliver: SliverToBoxAdapter(child: LearningSettingsBar(controller: learning)),
            ),
            AdaptiveSliverGrid(
              itemCount: games.length,
              minTileWidth: 200,
              maxColumns: 4,
              tileHeight: 220,
              itemBuilder: (context, i) {
                final (game, icon, color) = games[i];
                final played = learning.progress.game(game).sessions;
                return MenuTile(
                  icon: icon,
                  label: game.title,
                  color: color,
                  fitLabel: true,
                  badge: played > 0 ? (played == 1 ? 'Jugado 1 vez' : 'Jugado $played veces') : null,
                  // MenuTile ya suena al tocarlo.
                  onTap: () =>
                      Navigator.of(context)
                          .pushNamed(AppRoutes.learningGame, arguments: LearningGameArgs(game)),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
