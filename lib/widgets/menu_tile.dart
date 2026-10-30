import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/ui_sounds.dart';

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
    this.semanticsHint,
    this.horizontal = false,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  final String? badge;
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

  Widget _label(BuildContext context, TextAlign align) => Text(
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
      if (badge != null) ...[const SizedBox(height: 6), ComingSoonBadge(text: badge!)],
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
            if (badge != null) ...[const SizedBox(height: 4), ComingSoonBadge(text: badge!)],
          ],
        ),
      ),
    ],
  );
}

/// Marca visible para secciones provisionales o todavía no disponibles.
class ComingSoonBadge extends StatelessWidget {
  const ComingSoonBadge({super.key, this.text = 'Pronto'});

  final String text;

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
          const Icon(Icons.construction_rounded, size: 16, color: AppColors.ink),
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
