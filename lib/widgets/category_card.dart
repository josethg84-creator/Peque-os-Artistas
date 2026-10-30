import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/ui_sounds.dart';

import 'motion/pressable.dart';

import '../models/drawing_category.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import 'drawing_thumbnail.dart';

/// Tarjeta de categoría: ilustración, icono, nombre y número de dibujos.
class CategoryCard extends StatelessWidget {
  const CategoryCard({
    super.key,
    required this.category,
    required this.count,
    required this.coverAsset,
    required this.onTap,
  });

  final DrawingCategory category;
  final int count;
  final String? coverAsset;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final countText = count == 1 ? '1 dibujo' : '$count dibujos';
    return Pressable(
      child: Semantics(
        button: true,
        label: '${category.label}, $countText',
        excludeSemantics: true,
        onTap: guardRoute(context, withSound(context, SoundCue.category, onTap)),
        child: Material(
          color: category.color,
          borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          elevation: 2,
          child: InkWell(
            borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
            onTap: guardRoute(context, withSound(context, SoundCue.category, onTap)),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
                      ),
                      padding: const EdgeInsets.all(8),
                      child: coverAsset == null
                          ? Icon(category.icon, size: 72, color: category.color)
                          : DrawingThumbnail(asset: coverAsset),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                        child: Icon(category.icon, color: category.color, size: 22),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Se reduce un poco en tarjetas estrechas en lugar de cortarse.
                            FittedBox(
                              fit: BoxFit.scaleDown,
                              alignment: Alignment.centerLeft,
                              child: Text(
                                category.label,
                                maxLines: 1,
                                style: Theme.of(context).textTheme.titleLarge?.copyWith(color: Colors.white),
                              ),
                            ),
                            Text(
                              countText,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(color: AppColors.surface, fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
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
