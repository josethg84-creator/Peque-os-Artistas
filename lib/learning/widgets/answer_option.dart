import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';

enum OptionState { idle, correct, wrong, faded }

/// Botón de respuesta grande. El estado se indica con iconos (✓ / ✗) y
/// opacidad, no solo con colores. Las animaciones son breves y no bloquean.
class AnswerOption extends StatelessWidget {
  const AnswerOption({
    super.key,
    required this.label,
    required this.child,
    required this.onTap,
    this.state = OptionState.idle,
    this.caption,
    this.accent = AppColors.sky,
  });

  /// Nombre para lectores de pantalla.
  final String label;
  final Widget child;

  /// Texto visible bajo la imagen (p. ej. el nombre del color).
  final String? caption;
  final VoidCallback? onTap;
  final OptionState state;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    final duration = reduceMotion ? Duration.zero : const Duration(milliseconds: 220);
    final (border, width) = switch (state) {
      OptionState.correct => (AppColors.leaf, 6.0),
      OptionState.wrong => (AppColors.inkSoft, 3.0),
      _ => (accent.withValues(alpha: 0.6), 3.0),
    };
    final stateText = switch (state) {
      OptionState.correct => ', correcto',
      OptionState.wrong => ', inténtalo con otra',
      _ => '',
    };
    return Semantics(
      button: true,
      enabled: onTap != null,
      label: '$label$stateText',
      excludeSemantics: true,
      child: AnimatedOpacity(
        duration: duration,
        opacity: switch (state) {
          OptionState.wrong => 0.45,
          OptionState.faded => 0.35,
          _ => 1,
        },
        child: AnimatedScale(
          duration: duration,
          curve: Curves.easeOutBack,
          scale: state == OptionState.correct ? 1.05 : 1,
          child: Material(
            color: AppColors.surface,
            elevation: state == OptionState.correct ? 4 : 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
              side: BorderSide(color: border, width: width),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
              onTap: onTap,
              child: Stack(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      children: [
                        Expanded(child: Center(child: child)),
                        if (caption != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              child: Text(
                                caption!,
                                style: const TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.ink,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (state == OptionState.correct)
                    const Positioned(
                      top: 6,
                      right: 6,
                      child: _Badge(icon: Icons.check_rounded, color: AppColors.leaf),
                    ),
                  if (state == OptionState.wrong)
                    const Positioned(
                      top: 6,
                      right: 6,
                      child: _Badge(icon: Icons.close_rounded, color: AppColors.inkSoft),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.icon, required this.color});

  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    width: 36,
    height: 36,
    decoration: BoxDecoration(
      color: color,
      shape: BoxShape.circle,
      border: Border.all(color: Colors.white, width: 3),
    ),
    child: Icon(icon, color: Colors.white, size: 22),
  );
}
