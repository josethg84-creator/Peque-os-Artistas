import 'package:flutter/material.dart';

import '../models/drawing.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import 'drawing_thumbnail.dart';

/// Tarjeta de un dibujo en la galería: miniatura, nombre y dificultad
/// (con estrellas además de texto, para no depender del color).
class DrawingCard extends StatelessWidget {
  const DrawingCard({super.key, required this.drawing, required this.onTap});

  final Drawing drawing;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final accent = drawing.category.color;
    return Semantics(
      button: true,
      label: '${drawing.name}. Dificultad ${drawing.difficulty.label.toLowerCase()}',
      hint: 'Abre el dibujo para colorear',
      excludeSemantics: true,
      child: Material(
        color: AppColors.surface,
        elevation: 2,
        borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(child: DrawingThumbnail(asset: drawing.previewAsset)),
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
    );
  }
}
