import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import 'mascot.dart';

/// Mensaje amable para listas vacías o recursos ausentes, con una acción
/// opcional para continuar.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.actionLabel,
    this.actionIcon = Icons.home_rounded,
    this.onAction,
    this.color = AppColors.sky,
    this.showMascot = false,
  });

  final IconData icon;
  final String title;
  final String? message;
  final String? actionLabel;
  final IconData actionIcon;
  final VoidCallback? onAction;
  final Color color;

  /// Muestra a Pincelín junto al icono (estados vacíos amables).
  final bool showMascot;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDimens.pagePadding),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (showMascot) ...[const Mascot(size: 110, waves: 1), const SizedBox(width: 8)],
                  Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(color: color.withValues(alpha: 0.18), shape: BoxShape.circle),
                    child: Icon(icon, size: 64, color: color),
                  ),
                ],
              ),
              const SizedBox(height: AppDimens.gap),
              Text(title, textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
              if (message != null) ...[
                const SizedBox(height: 8),
                Text(
                  message!,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.inkSoft),
                ),
              ],
              if (actionLabel != null && onAction != null) ...[
                const SizedBox(height: AppDimens.gapLarge),
                FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: color),
                  onPressed: onAction,
                  icon: Icon(actionIcon, size: 28),
                  label: Text(actionLabel!),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
