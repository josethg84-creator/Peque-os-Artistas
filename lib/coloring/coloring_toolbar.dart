import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../widgets/eraser_icon.dart';
import '../widgets/kid_icon_button.dart';
import 'coloring_controller.dart';

/// Herramientas: borrador, deshacer, rehacer y limpiar.
/// Los botones sin efecto todavía (Fase 3) aparecen desactivados.
class ColoringToolbar extends StatelessWidget {
  const ColoringToolbar({super.key, required this.controller, this.axis = Axis.horizontal});

  final ColoringController controller;
  final Axis axis;

  @override
  Widget build(BuildContext context) {
    final c = controller;
    final buttons = [
      KidIconButton(
        icon: Icons.auto_fix_normal_rounded,
        iconWidget: const EraserIcon(),
        label: 'Borrador',
        color: AppColors.berry,
        showLabel: true,
        selected: c.tool == ColoringTool.eraser,
        onPressed: c.toggleEraser,
      ),
      KidIconButton(
        icon: Icons.undo_rounded,
        label: 'Deshacer',
        color: AppColors.sky,
        showLabel: true,
        onPressed: c.canUndo ? c.undo : null,
      ),
      KidIconButton(
        icon: Icons.redo_rounded,
        label: 'Rehacer',
        color: AppColors.sky,
        showLabel: true,
        onPressed: c.canRedo ? c.redo : null,
      ),
      KidIconButton(
        icon: Icons.delete_outline_rounded,
        label: 'Limpiar',
        color: AppColors.coral,
        showLabel: true,
        onPressed: c.hasColoring ? c.clear : null,
      ),
    ];
    return Flex(
      direction: axis,
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      mainAxisSize: MainAxisSize.min,
      children: [for (final b in buttons) Padding(padding: const EdgeInsets.all(6), child: b)],
    );
  }
}
