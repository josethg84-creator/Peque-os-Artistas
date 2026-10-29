import 'package:flutter/material.dart';

import '../models/drawing_category.dart';
import '../navigation/app_routes.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/category_card.dart';
import '../theme/app_colors.dart';
import '../widgets/kid_icon_button.dart';
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
      trailing: KidIconButton(
        icon: Icons.search_rounded,
        label: 'Buscar dibujos',
        color: AppColors.sun,
        onPressed: () => Navigator.of(context).pushNamed(AppRoutes.search),
      ),
      body: CatalogBuilder(
        builder: (context, catalog) => AdaptiveGrid(
          itemCount: DrawingCategory.values.length,
          minTileWidth: 200,
          childAspectRatio: 0.95,
          itemBuilder: (context, index) {
            final category = DrawingCategory.values[index];
            final drawings = catalog.byCategory(category);
            final cover =
                catalog.byId(category.coverDrawingId)?.thumbnailAsset ??
                drawings.where((d) => d.thumbnailAvailable).firstOrNull?.thumbnailAsset;
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
