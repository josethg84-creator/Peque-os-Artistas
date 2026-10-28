import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import 'coloring_controller.dart';
import 'palette.dart';

/// Barra de colores desplazable, horizontal o vertical.
/// El color elegido se marca con un anillo y una palomita, no solo con color.
class ColorPaletteBar extends StatelessWidget {
  const ColorPaletteBar({super.key, required this.controller, this.axis = Axis.horizontal});

  final ColoringController controller;
  final Axis axis;

  static const swatchSize = 60.0;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Colores',
      container: true,
      child: SingleChildScrollView(
        scrollDirection: axis,
        padding: const EdgeInsets.all(8),
        child: Flex(
          direction: axis,
          children: [
            for (final c in kidPalette)
              Padding(
                padding: const EdgeInsets.all(5),
                child: _Swatch(
                  color: c,
                  selected: controller.tool == ColoringTool.paint && controller.color == c,
                  onTap: () => controller.selectColor(c),
                ),
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
      label: color.name,
      excludeSemantics: true,
      child: Tooltip(
        message: color.name,
        child: GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: ColorPaletteBar.swatchSize,
            height: ColorPaletteBar.swatchSize,
            decoration: BoxDecoration(
              color: color.color,
              shape: BoxShape.circle,
              border: Border.all(color: selected ? AppColors.ink : Colors.white, width: selected ? 5 : 3),
              boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 4, offset: Offset(0, 2))],
            ),
            child: selected
                ? Icon(Icons.check_rounded, size: 34, color: light ? AppColors.ink : Colors.white)
                : null,
          ),
        ),
      ),
    );
  }
}
