import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/kid_icon_button.dart';

/// Instrucción corta y grande, con un modelo visual opcional y un botón
/// «Escuchar» que la lee en voz alta (solo si la voz está activada).
class InstructionCard extends StatelessWidget {
  const InstructionCard({
    super.key,
    required this.text,
    this.visual,
    this.onListen,
    this.accent = AppColors.sky,
  });

  final String text;
  final Widget? visual;
  final VoidCallback? onListen;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
      ),
      child: Row(
        children: [
          if (visual != null) ...[SizedBox.square(dimension: 72, child: visual), const SizedBox(width: 12)],
          Expanded(
            child: Semantics(
              header: true,
              liveRegion: true,
              child: Text(text, style: Theme.of(context).textTheme.headlineSmall),
            ),
          ),
          if (onListen != null) ...[
            const SizedBox(width: 8),
            KidIconButton(
              icon: Icons.volume_up_rounded,
              label: 'Escuchar',
              color: accent,
              size: 56,
              onPressed: onListen,
            ),
          ],
        ],
      ),
    );
  }
}
