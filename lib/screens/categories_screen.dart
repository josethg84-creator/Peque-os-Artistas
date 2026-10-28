import 'package:flutter/material.dart';

import '../models/drawing_category.dart';
import '../navigation/app_routes.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/category_card.dart';
import '../widgets/kid_scaffold.dart';

/// Las cinco categorías de dibujos.
class CategoriesScreen extends StatelessWidget {
  const CategoriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Elige una categoría',
      titleIcon: Icons.photo_library_rounded,
      backLabel: 'Volver al inicio',
      body: CatalogBuilder(
        builder: (context, catalog) => AdaptiveGrid(
          itemCount: DrawingCategory.values.length,
          minTileWidth: 200,
          childAspectRatio: 0.95,
          itemBuilder: (context, index) {
            final category = DrawingCategory.values[index];
            final drawings = catalog.byCategory(category);
            final cover =
                catalog.byId(category.coverDrawingId)?.previewAsset ??
                drawings.where((d) => d.previewAvailable).firstOrNull?.previewAsset;
            return CategoryCard(
              category: category,
              count: drawings.length,
              coverAsset: cover,
              onTap: () =>
                  Navigator.of(context).pushNamed(AppRoutes.gallery, arguments: GalleryArgs(category)),
            );
          },
        ),
      ),
    );
  }
}
