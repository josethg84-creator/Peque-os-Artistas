import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import 'coloring_controller.dart';

/// Indicador pequeño del guardado automático, bajo el título. Si un guardado
/// falla, se convierte en un botón «Reintentar»; si hay cambios pendientes,
/// tocarlo los guarda en el acto. Ocupa siempre la misma altura para que el
/// dibujo no salte.
class SaveIndicator extends StatelessWidget {
  const SaveIndicator({super.key, required this.controller});

  final ColoringController controller;

  static const height = 32.0;

  @override
  Widget build(BuildContext context) {
    final c = controller;
    final (IconData icon, String text, Color color)? content = switch (c.saveState) {
      _ when !c.coloringEngineReady => null,
      SaveState.failed => (Icons.refresh_rounded, 'No se guardó · Reintentar', AppColors.coral),
      SaveState.pending => (Icons.more_horiz_rounded, 'Guardando…', AppColors.inkSoft),
      SaveState.saved when c.hasColoring => (Icons.check_circle_rounded, 'Guardado', AppColors.leaf),
      SaveState.saved => null,
    };
    if (content == null) return const SizedBox(height: height);
    final (icon, text, color) = content;
    return SizedBox(
      height: height,
      child: Semantics(
        button: c.saveState != SaveState.saved,
        liveRegion: true,
        label: text,
        excludeSemantics: true,
        child: TextButton.icon(
          style: TextButton.styleFrom(
            foregroundColor: color,
            padding: const EdgeInsets.symmetric(horizontal: 10),
            minimumSize: const Size(0, height),
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          onPressed: c.saveState == SaveState.saved ? null : c.save,
          icon: Icon(icon, size: 20, color: color),
          label: Text(
            text,
            style: TextStyle(fontWeight: FontWeight.w700, color: color),
          ),
        ),
      ),
    );
  }
}
