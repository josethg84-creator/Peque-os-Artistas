import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/ui_sounds.dart';

import 'fitted_title.dart';
import 'motion/pressable.dart';

import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';

/// Tarjeta grande y táctil con icono, título y una marca opcional
/// (por ejemplo, «Pronto»).
class MenuTile extends StatelessWidget {
  const MenuTile({
    super.key,
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
    this.badge,
    this.badgeIcon = Icons.star_rounded,
    this.fitLabel = false,
    this.semanticsHint,
    this.horizontal = false,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  final String? badge;

  /// Icono de la marca (por defecto, una estrella: «Jugado 3 veces»).
  final IconData badgeIcon;

  /// El título baja de tamaño antes que partir una palabra larga. Solo en
  /// rejillas: no admite medidas intrínsecas (IntrinsicHeight).
  final bool fitLabel;
  final String? semanticsHint;

  /// Disposición en fila (icono a la izquierda), más baja: para teléfonos.
  final bool horizontal;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      child: Semantics(
        button: true,
        label: badge == null ? label : '$label. $badge',
        hint: semanticsHint,
        excludeSemantics: true,
        onTap: guardRoute(context, withSound(context, SoundCue.tap, onTap)),
        child: Material(
          color: color.withValues(alpha: 0.16),
          borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          child: InkWell(
            borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
            onTap: guardRoute(context, withSound(context, SoundCue.tap, onTap)),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: horizontal ? 88 : 120),
              child: Padding(
                padding: EdgeInsets.all(horizontal ? 12 : AppDimens.gap),
                child: horizontal ? _row(context) : _column(context),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _icon() => Container(
    width: 64,
    height: 64,
    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    child: Icon(icon, color: Colors.white, size: 36),
  );

  Widget _label(BuildContext context, TextAlign align) => fitLabel
      // Baja de tamaño antes que partir una palabra («Rompecabezas»).
      ? FittedTitle(
          label,
          textAlign: align,
          styles: [
            Theme.of(context).textTheme.titleLarge,
            Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
          ],
        )
      : Text(
          label,
          textAlign: align,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.titleLarge,
        );

  Widget _column(BuildContext context) => Column(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      _icon(),
      const SizedBox(height: 8),
      _label(context, TextAlign.center),
      if (badge != null) ...[const SizedBox(height: 6), ComingSoonBadge(text: badge!, icon: badgeIcon)],
    ],
  );

  Widget _row(BuildContext context) => Row(
    children: [
      _icon(),
      const SizedBox(width: AppDimens.gap),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _label(context, TextAlign.start),
            if (badge != null) ...[const SizedBox(height: 4), ComingSoonBadge(text: badge!, icon: badgeIcon)],
          ],
        ),
      ),
    ],
  );
}

/// Marca pequeña bajo el título de una tarjeta. El icono de obras queda solo
/// para lo que de verdad no está disponible todavía («Pronto»).
class ComingSoonBadge extends StatelessWidget {
  const ComingSoonBadge({super.key, this.text = 'Pronto', this.icon = Icons.construction_rounded});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.sun,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.ink, width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppColors.ink),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              text,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }
}
