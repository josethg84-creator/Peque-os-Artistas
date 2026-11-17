import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../complete_words.dart';
import '../reading_activities.dart';
import '../reading_progress.dart';
import '../widgets/reading_widgets.dart';
import 'complete_words_game_screen.dart';

/// Pantalla B · «Completa las palabras»: elegir nivel y modo, con el progreso
/// guardado. Los niveles se abren al completar ejercicios del anterior.
class ReadingWordsScreen extends StatefulWidget {
  const ReadingWordsScreen({super.key});

  @override
  State<ReadingWordsScreen> createState() => _ReadingWordsScreenState();
}

class _ReadingWordsScreenState extends State<ReadingWordsScreen> {
  int _level = 1;

  static const color = CompleteWordsGameScreen.color;

  @override
  Widget build(BuildContext context) {
    final progress = AppServices.of(context).reading;
    return KidScaffold(
      title: CompleteWordsGameScreen.title,
      titleIcon: ReadingActivities.words.icon,
      accent: color,
      trailing: const ReadingHomeButton(),
      body: CompleteWordsBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: progress,
          builder: (context, _) {
            final playable = [
              for (final e in content.exercises)
                if (content.words[e.wordId]?.hasPicture ?? false) e,
            ];
            final done = playable.where((e) => progress.progress.completed[e.id]?.isNotEmpty ?? false).length;
            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                AppDimens.pagePadding,
                0,
                AppDimens.pagePadding,
                AppDimens.pagePadding,
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 900),
                  child: Column(
                    children: [
                      const ReadingLolo(text: CompleteWordsGameScreen.instruction),
                      const SizedBox(height: 12),
                      ReadingProgressBar(
                        done: done,
                        total: playable.length,
                        label: 'Palabras completadas',
                        color: color,
                      ),
                      const SizedBox(height: 18),
                      Text('Elige un nivel', style: fredoka(22, color: AppColors.ink)),
                      const SizedBox(height: 10),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          for (final level in CompleteWordsContent.levels)
                            _LevelCard(
                              level: level,
                              selected: level == _level,
                              unlocked: levelUnlocked(content, progress, level),
                              done: completedInLevel(content, progress, level),
                              total: playable.where((e) => e.level == level).length,
                              onTap: () => setState(() => _level = level),
                            ),
                        ],
                      ),
                      const SizedBox(height: 22),
                      Text('Elige cómo jugar', style: fredoka(22, color: AppColors.ink)),
                      const SizedBox(height: 10),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          for (final (i, mode) in CompleteMode.values.indexed)
                            SizedBox(
                              width: 270,
                              child: BigActionButton(
                                label: mode.title,
                                icon: const [
                                  Icons.touch_app_rounded,
                                  Icons.pan_tool_alt_rounded,
                                  Icons.sort_rounded,
                                ][i],
                                color: const [AppColors.sky, AppColors.grape, AppColors.leaf][i],
                                onPressed: levelUnlocked(content, progress, _level)
                                    ? () => Navigator.of(context).pushNamed(
                                        AppRoutes.readingWordsGame,
                                        arguments: CompleteGameArgs(level: _level, mode: mode),
                                      )
                                    : null,
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _LevelCard extends StatelessWidget {
  const _LevelCard({
    required this.level,
    required this.selected,
    required this.unlocked,
    required this.done,
    required this.total,
    required this.onTap,
  });

  final int level;
  final bool selected;
  final bool unlocked;
  final int done;
  final int total;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final name = CompleteWordsContent.levelNames[level]!;
    const color = CompleteWordsGameScreen.color;
    final label = unlocked
        ? 'Nivel $level: $name. $done de $total palabras.'
        : 'Nivel $level: $name. Se abre al completar ${ReadingController.unlockAfter} palabras del nivel ${level - 1}.';
    return Semantics(
      button: true,
      selected: selected,
      enabled: unlocked,
      label: label,
      excludeSemantics: true,
      onTap: unlocked ? onTap : null,
      child: GestureDetector(
        onTap: unlocked ? onTap : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 250,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: !unlocked
                ? const Color(0xFFF1EEF8)
                : selected
                ? Color.lerp(color, Colors.white, 0.55)
                : Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: unlocked ? color : const Color(0xFFD1C4E9), width: selected ? 4 : 2),
          ),
          child: Row(
            children: [
              Icon(
                unlocked ? Icons.star_rounded : Icons.lock_rounded,
                color: unlocked ? AppColors.sun : AppColors.inkSoft,
                size: 34,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Nivel $level', style: fredoka(20, color: AppColors.ink)),
                    Text(name, style: Theme.of(context).textTheme.bodyMedium),
                    Text(
                      unlocked
                          ? '$done de $total'
                          : 'Completa ${ReadingController.unlockAfter} del nivel ${level - 1}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
