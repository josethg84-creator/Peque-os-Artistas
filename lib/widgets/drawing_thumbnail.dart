import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Miniatura de un dibujo. Si la imagen no existe o no se puede cargar,
/// muestra un marcador temporal claramente identificado en lugar de fallar.
class DrawingThumbnail extends StatelessWidget {
  const DrawingThumbnail({super.key, required this.asset, this.fit = BoxFit.contain});

  /// Ruta verificada del PNG, o `null` si no está disponible.
  final String? asset;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) {
    final path = asset;
    if (path == null) return const MissingImagePlaceholder();
    return Image.asset(
      path,
      fit: fit,
      // Las miniaturas no necesitan la resolución completa (1024 px).
      cacheWidth: 512,
      excludeFromSemantics: true,
      errorBuilder: (_, _, _) => const MissingImagePlaceholder(),
    );
  }
}

/// Marcador visual para imágenes todavía no disponibles.
class MissingImagePlaceholder extends StatelessWidget {
  const MissingImagePlaceholder({super.key});

  static const label = 'Imagen pendiente';

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFFF1EEF6),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.inkSoft, width: 2),
        ),
        alignment: Alignment.center,
        padding: const EdgeInsets.all(8),
        child: const FittedBox(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.image_not_supported_rounded, size: 48, color: AppColors.inkSoft),
              SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.inkSoft),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
