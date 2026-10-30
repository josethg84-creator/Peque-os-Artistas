import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/ui_sounds.dart';

import 'motion/pressable.dart';

import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';

/// Botón redondo grande con icono y, opcionalmente, una etiqueta corta debajo.
///
/// El significado nunca depende solo del color: siempre hay icono, y la
/// etiqueta o el tooltip describen la acción para los lectores de pantalla.
class KidIconButton extends StatelessWidget {
  const KidIconButton({
    super.key,
    required this.icon,
    required this.label,
    required this.onPressed,
    this.color = AppColors.sky,
    this.size = AppDimens.minTouchTarget,
    this.showLabel = false,
    this.selected = false,
    this.iconWidget,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final Color color;
  final double size;
  final bool showLabel;
  final bool selected;

  /// Sustituye a [icon] cuando hace falta un dibujo propio (p. ej. el borrador).
  final Widget? iconWidget;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null;
    final fg = enabled ? Colors.white : AppColors.inkSoft;
    final bg = enabled ? color : const Color(0xFFE4E1EA);
    final button = Pressable(
      enabled: onPressed != null,
      child: Semantics(
        button: true,
        enabled: enabled,
        selected: selected,
        label: label,
        excludeSemantics: true,
        onTap: guardRoute(context, withSound(context, SoundCue.tap, onPressed)),
        child: Tooltip(
          message: label,
          child: Material(
            color: bg,
            shape: CircleBorder(
              side: BorderSide(color: selected ? AppColors.ink : Colors.transparent, width: 4),
            ),
            elevation: enabled ? 2 : 0,
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: guardRoute(context, withSound(context, SoundCue.tap, onPressed)),
              child: SizedBox.square(
                dimension: size,
                child: Center(
                  child: IconTheme(
                    data: IconThemeData(color: fg, size: size * 0.5),
                    child: iconWidget ?? Icon(icon),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
    if (!showLabel) return button;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        button,
        const SizedBox(height: 4),
        ExcludeSemantics(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: enabled ? AppColors.ink : AppColors.inkSoft,
            ),
          ),
        ),
      ],
    );
  }
}
