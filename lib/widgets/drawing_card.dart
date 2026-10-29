import 'package:flutter/material.dart';

import 'motion/pressable.dart';

import '../models/drawing.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import 'drawing_thumbnail.dart';

/// Tarjeta de un dibujo en la galería: miniatura, nombre y dificultad
/// (con estrellas además de texto, para no depender del color) y, si ya se
/// empezó a pintar, una insignia con un pincel.
class DrawingCard extends StatelessWidget {
  const DrawingCard({super.key, required this.drawing, required this.onTap, this.painted = false});

  final Drawing drawing;
  final VoidCallback onTap;

  /// Tiene colores guardados.
  final bool painted;

  static const paintedLabel = 'ya pintado';

  @override
  Widget build(BuildContext context) {
    final accent = drawing.category.color;
    return Pressable(
      child: Semantics(
        button: true,
        label: [
          '${drawing.name}. Dificultad ${drawing.difficulty.label.toLowerCase()}',
          if (painted) paintedLabel,
        ].join('. '),
        hint: 'Abre el dibujo para colorear',
        excludeSemantics: true,
        onTap: guardRoute(context, onTap),
        child: Material(
          color: AppColors.surface,
          elevation: 2,
          borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          child: InkWell(
            borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
            onTap: guardRoute(context, onTap),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: Stack(
                      children: [
                        Positioned.fill(child: DrawingThumbnail(asset: drawing.thumbnailAsset)),
                        if (painted) Positioned(top: 0, right: 0, child: _PaintedBadge(color: accent)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    drawing.name,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 2),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      for (var i = 0; i < 3; i++)
                        Icon(
                          i < drawing.difficulty.stars ? Icons.star_rounded : Icons.star_outline_rounded,
                          size: 22,
                          color: i < drawing.difficulty.stars ? accent : AppColors.inkSoft,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Pincel en un círculo: indica que el dibujo tiene colores guardados.
class _PaintedBadge extends StatelessWidget {
  const _PaintedBadge({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 3),
        boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 4, offset: Offset(0, 2))],
      ),
      child: const Icon(Icons.brush_rounded, color: Colors.white, size: 22),
    );
  }
}
