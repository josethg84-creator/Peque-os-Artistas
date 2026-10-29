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

/// «Aprender jugando»: los cuatro minijuegos, el nivel y los sonidos.
class LearningHubScreen extends StatefulWidget {
  const LearningHubScreen({super.key});

  static const games = [
    (GameId.colors, Icons.palette_rounded, AppColors.coral),
    (GameId.shapes, Icons.category_rounded, AppColors.sky),
    (GameId.animals, Icons.pets_rounded, AppColors.leaf),
    (GameId.memory, Icons.style_rounded, AppColors.grape),
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
    return KidScaffold(
      title: 'Aprender jugando',
      titleIcon: Icons.extension_rounded,
      accent: AppColors.leaf,
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
              itemCount: LearningHubScreen.games.length,
              minTileWidth: 200,
              maxColumns: 4,
              tileHeight: 220,
              itemBuilder: (context, i) {
                final (game, icon, color) = LearningHubScreen.games[i];
                final played = learning.progress.game(game).sessions;
                return MenuTile(
                  icon: icon,
                  label: game.title,
                  color: color,
                  badge: played > 0 ? (played == 1 ? 'Jugado 1 vez' : 'Jugado $played veces') : null,
                  onTap: () {
                    unawaited(AppServices.of(context).audio.play(SoundCue.tap));
                    Navigator.of(context)
                        .pushNamed(AppRoutes.learningGame, arguments: LearningGameArgs(game));
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
