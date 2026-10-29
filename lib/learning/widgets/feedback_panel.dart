import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';

/// Mensaje tras responder. Positivo al acertar (con explicación y botón para
/// seguir, sin prisa) y neutro al fallar («¡Inténtalo otra vez!»).
class FeedbackPanel extends StatelessWidget {
  const FeedbackPanel.success({
    super.key,
    required this.title,
    this.message,
    required this.actionLabel,
    required this.onAction,
  }) : success = true;

  const FeedbackPanel.tryAgain({super.key})
    : success = false,
      title = '¡Inténtalo otra vez!',
      message = null,
      actionLabel = null,
      onAction = null;

  final bool success;
  final String title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final color = success ? AppColors.leaf : AppColors.sky;
    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.16),
          borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          border: Border.all(color: color, width: 2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  success ? Icons.star_rounded : Icons.refresh_rounded,
                  color: success ? AppColors.sun : color,
                  size: 40,
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(title, style: Theme.of(context).textTheme.headlineSmall)),
              ],
            ),
            if (message != null) ...[
              const SizedBox(height: 6),
              Text(message!, style: Theme.of(context).textTheme.titleMedium),
            ],
            if (actionLabel != null) ...[
              const SizedBox(height: 10),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: AppColors.leaf),
                onPressed: onAction,
                icon: const Icon(Icons.arrow_forward_rounded, size: 30),
                label: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
