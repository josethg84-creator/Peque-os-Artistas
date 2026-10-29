import 'package:flutter/material.dart';

import '../learning/audio/learning_audio.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../theme/app_motion.dart';
import '../widgets/eraser_icon.dart';
import '../widgets/kid_icon_button.dart';
import 'coloring_controller.dart';

/// Herramientas: borrador, deshacer, rehacer y limpiar. Cada botón se
/// desactiva cuando no tiene efecto (nada que deshacer, nada que limpiar...).
class ColoringToolbar extends StatelessWidget {
  const ColoringToolbar({
    super.key,
    required this.controller,
    required this.onClear,
    this.axis = Axis.horizontal,
  });

  final ColoringController controller;

  /// Se llama al pulsar «Limpiar»; la pantalla pide confirmación.
  final VoidCallback onClear;
  final Axis axis;

  @override
  Widget build(BuildContext context) {
    final c = controller;
    final buttons = [
      _CurrentTool(controller: c),
      KidIconButton(
        icon: Icons.auto_fix_normal_rounded,
        iconWidget: const EraserIcon(),
        label: 'Borrador',
        color: AppColors.berry,
        showLabel: true,
        selected: c.tool == ColoringTool.eraser,
        onPressed: c.coloringEngineReady
            ? () {
                c.toggleEraser();
                AppServices.maybeOf(context)?.audio.play(SoundCue.select);
              }
            : null,
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
        onPressed: c.hasColoring ? onClear : null,
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

/// Muestra con qué se está pintando: el color (con su nombre, para no depender
/// solo del color) o el borrador. Cambia con una pequeña animación.
class _CurrentTool extends StatelessWidget {
  const _CurrentTool({required this.controller});

  final ColoringController controller;

  @override
  Widget build(BuildContext context) {
    final eraser = controller.tool == ColoringTool.eraser;
    final color = controller.color;
    final label = eraser ? 'Borrador' : color.name;
    return Semantics(
      label: eraser ? 'Usando el borrador' : 'Pintando con $label',
      excludeSemantics: true,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedSwitcher(
            duration: AppMotion.of(context, AppMotion.medium),
            transitionBuilder: (child, animation) => ScaleTransition(
              scale: CurvedAnimation(parent: animation, curve: AppMotion.bounce),
              child: child,
            ),
            child: Container(
              key: ValueKey(label),
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: eraser ? Colors.white : color.color,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.ink, width: 3),
              ),
              child: IconTheme(
                data: IconThemeData(
                  size: 32,
                  color: eraser || color.color.computeLuminance() > 0.5 ? AppColors.ink : Colors.white,
                ),
                child: eraser ? const EraserIcon() : const Icon(Icons.brush_rounded),
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AppColors.ink),
          ),
        ],
      ),
    );
  }
}
