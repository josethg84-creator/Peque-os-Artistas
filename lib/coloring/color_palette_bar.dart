import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../learning/audio/learning_audio.dart';
import '../audio/ui_sounds.dart';
import '../theme/app_motion.dart';
import '../widgets/motion/pressable.dart';
import 'coloring_controller.dart';
import 'palette.dart';

/// Barra de colores desplazable, horizontal o vertical, en dos líneas para que
/// se vean muchos de los 24 colores a la vez (la primera mitad del arcoíris en
/// una y la segunda en la otra).
/// El color elegido se marca con un anillo y una palomita, no solo con color.
class ColorPaletteBar extends StatelessWidget {
  const ColorPaletteBar({super.key, required this.controller, this.axis = Axis.horizontal});

  final ColoringController controller;
  final Axis axis;

  static const swatchSize = 54.0;

  /// Líneas de colores (filas en horizontal, columnas en vertical).
  static const lines = 2;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Colores',
      container: true,
      child: SingleChildScrollView(
        scrollDirection: axis,
        padding: const EdgeInsets.all(8),
        child: Flex(
          direction: flipAxis(axis),
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            for (var line = 0; line < lines; line++)
              Flex(
                direction: axis,
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final (i, c) in kidPalette.indexed)
                    if (i * lines ~/ kidPalette.length == line)
                      Padding(
                        padding: const EdgeInsets.all(4),
                        child: _Swatch(
                          color: c,
                          selected: controller.tool == ColoringTool.paint && controller.color == c,
                          // Cada color tiene su nota (escala pentatónica): elegir colores
                          // suena como una pequeña melodía.
                          onTap: withSound(
                            context,
                            SoundCue.color,
                            () => controller.selectColor(c),
                            variant: i,
                          )!,
                        ),
                      ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _Swatch extends StatelessWidget {
  const _Swatch({required this.color, required this.selected, required this.onTap});

  final PaletteColor color;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final light = color.color.computeLuminance() > 0.5;
    return Semantics(
      button: true,
      selected: selected,
      label: color.restoresOriginal ? '${color.name}, sin pintar' : color.name,
      excludeSemantics: true,
      onTap: onTap,
      child: Tooltip(
        message: color.name,
        child: GestureDetector(
          onTap: onTap,
          child: Pressable(
            child: AnimatedScale(
              // El color elegido crece un poco (además del anillo y la palomita).
              scale: selected ? 1.1 : 1,
              duration: AppMotion.of(context, AppMotion.medium),
              curve: AppMotion.bounce,
              child: AnimatedContainer(
                duration: AppMotion.of(context, AppMotion.fast),
                width: ColorPaletteBar.swatchSize,
                height: ColorPaletteBar.swatchSize,
                decoration: BoxDecoration(
                  color: color.color,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: selected ? AppColors.ink : (light ? AppColors.inkSoft : Colors.white),
                    width: selected ? 5 : 3,
                  ),
                  boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 4, offset: Offset(0, 2))],
                ),
                child: selected
                    ? Icon(Icons.check_rounded, size: 30, color: light ? AppColors.ink : Colors.white)
                    : null,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
