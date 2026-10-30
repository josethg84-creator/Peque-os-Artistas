import 'package:flutter/material.dart';

import '../../widgets/motion/pressable.dart';

import '../../navigation/app_routes.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../learning_controller.dart';
import '../learning_level.dart';

/// Controles sencillos: nivel (tres botones con estrellas) y sonidos/voz
/// (interruptores con icono y texto). Se guardan al momento.
class LearningSettingsBar extends StatelessWidget {
  const LearningSettingsBar({super.key, required this.controller});

  final LearningController controller;

  @override
  Widget build(BuildContext context) {
    final s = controller.settings;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
      ),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        alignment: WrapAlignment.center,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          for (final level in LearningLevel.values)
            _Toggle(
              label: level.label,
              selected: s.level == level,
              color: AppColors.sun,
              leading: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (var i = 0; i < level.stars; i++)
                    Icon(
                      Icons.star_rounded,
                      size: 20,
                      color: s.level == level ? Colors.white : AppColors.sun,
                    ),
                ],
              ),
              semantics: 'Nivel ${level.label}',
              onTap: () => controller.updateSettings(s.copyWith(level: level)),
            ),
          _Toggle(
            label: s.soundOn ? 'Sonidos' : 'Sin sonidos',
            selected: s.soundOn,
            color: AppColors.sky,
            leading: Icon(s.soundOn ? Icons.music_note_rounded : Icons.music_off_rounded, size: 24),
            semantics: s.soundOn ? 'Sonidos activados' : 'Sonidos desactivados',
            onTap: () => controller.updateSettings(s.copyWith(soundOn: !s.soundOn)),
          ),
          _Toggle(
            label: s.voiceOn ? 'Voz' : 'Sin voz',
            selected: s.voiceOn,
            color: AppColors.grape,
            leading: Icon(
              s.voiceOn ? Icons.record_voice_over_rounded : Icons.voice_over_off_rounded,
              size: 24,
            ),
            semantics: s.voiceOn ? 'Voz activada' : 'Voz desactivada',
            onTap: () => controller.updateSettings(s.copyWith(voiceOn: !s.voiceOn)),
          ),
          _Toggle(
            label: 'Más ajustes',
            selected: false,
            color: AppColors.coral,
            leading: const Icon(Icons.tune_rounded, size: 24),
            semantics: 'Sonido y música: más ajustes',
            onTap: () => Navigator.of(context).pushNamed(AppRoutes.soundSettings),
          ),
        ],
      ),
    );
  }
}

class _Toggle extends StatelessWidget {
  const _Toggle({
    required this.label,
    required this.selected,
    required this.color,
    required this.leading,
    required this.semantics,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final Color color;
  final Widget leading;
  final String semantics;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fg = selected ? Colors.white : AppColors.ink;
    return Pressable(
      child: Semantics(
        button: true,
        selected: selected,
        label: semantics,
        excludeSemantics: true,
        onTap: onTap,
        child: Material(
          color: selected ? color : AppColors.surface,
          shape: StadiumBorder(side: BorderSide(color: selected ? AppColors.ink : color, width: 2)),
          child: InkWell(
            customBorder: const StadiumBorder(),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 56),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: IconTheme(
                  data: IconThemeData(color: fg),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      leading,
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          label,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: fg),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
