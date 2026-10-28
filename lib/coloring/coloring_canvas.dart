import 'package:flutter/material.dart';

import '../models/drawing.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/drawing_thumbnail.dart';
import 'coloring_controller.dart';

/// Área central del lienzo.
///
/// Por ahora muestra el dibujo de línea (PNG de la Fase 1) dentro de un marco
/// cuadrado y un aviso visible de que el coloreado aún no está disponible.
/// En la Fase 3, el contenido del marco se sustituirá por el motor que lee las
/// regiones del SVG ([Drawing.file]); el marco, el tamaño y el controlador
/// no cambian.
class ColoringCanvas extends StatelessWidget {
  const ColoringCanvas({super.key, required this.drawing, required this.controller});

  final Drawing drawing;
  final ColoringController controller;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: AspectRatio(
        aspectRatio: 1,
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
            border: Border.all(color: drawing.category.color, width: 6),
            boxShadow: const [BoxShadow(color: Color(0x22000000), blurRadius: 12, offset: Offset(0, 4))],
          ),
          clipBehavior: Clip.antiAlias,
          child: Stack(
            children: [
              Positioned.fill(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Semantics(
                    label: 'Dibujo para colorear: ${drawing.name}',
                    image: true,
                    child: DrawingThumbnail(asset: drawing.previewAsset),
                  ),
                ),
              ),
              if (!controller.coloringEngineReady)
                const Positioned(left: 12, right: 12, bottom: 12, child: _PreviewNotice()),
            ],
          ),
        ),
      ),
    );
  }
}

/// Aviso honesto: la pantalla es una vista previa sin coloreado real.
class _PreviewNotice extends StatelessWidget {
  const _PreviewNotice();

  static const text = 'Vista previa: pintar llegará pronto';

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.sun,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.ink, width: 1.5),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.construction_rounded, size: 20, color: AppColors.ink),
            SizedBox(width: 6),
            Flexible(
              child: Text(
                text,
                textAlign: TextAlign.center,
                style: TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
