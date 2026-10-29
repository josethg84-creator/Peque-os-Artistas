import 'package:flutter/material.dart';

import '../models/drawing_category.dart';
import '../navigation/app_routes.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/drawing_card.dart';
import '../widgets/empty_state.dart';
import '../widgets/kid_scaffold.dart';
import '../widgets/saved_ids_builder.dart';

/// Dibujos de una categoría, leídos del catálogo de la Fase 1.
class GalleryScreen extends StatelessWidget {
  const GalleryScreen({super.key, required this.category});

  final DrawingCategory category;

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: category.label,
      titleIcon: category.icon,
      accent: category.color,
      backLabel: 'Volver a categorías',
      body: CatalogBuilder(
        builder: (context, catalog) {
          final drawings = catalog.byCategory(category);
          if (drawings.isEmpty) {
            return EmptyState(
              icon: Icons.palette_rounded,
              color: category.color,
              title: 'Todavía no hay dibujos aquí',
              message: '¡Pronto llegarán dibujos nuevos!',
              actionLabel: 'Ver categorías',
              actionIcon: Icons.photo_library_rounded,
              onAction: () => Navigator.of(context).maybePop(),
            );
          }
          return SavedIdsBuilder(
            builder: (context, saved) => AdaptiveGrid(
              itemCount: drawings.length,
              itemBuilder: (context, index) {
                final drawing = drawings[index];
                return DrawingCard(
                  drawing: drawing,
                  painted: saved.contains(drawing.id),
                  onTap: () =>
                      Navigator.of(context)
                          .pushNamed(AppRoutes.coloring, arguments: ColoringArgs(drawing.id)),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
