import 'package:flutter/material.dart';

import '../models/drawing_catalog.dart';
import '../models/drawing_category.dart';
import '../navigation/app_routes.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/category_card.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/big_action_button.dart';
import '../widgets/kid_icon_button.dart';
import '../widgets/kid_scaffold.dart';

/// Las cinco categorías de dibujos, con el atajo «¡Vamos a pintar!» arriba.
class CategoriesScreen extends StatelessWidget {
  const CategoriesScreen({super.key});

  /// Cada pulsación de «¡Vamos a pintar!» propone el siguiente dibujo fácil
  /// (se recuerda mientras la app está abierta, aunque se salga de la pantalla).
  static final _suggestion = Expando<int>();

  void _startPainting(BuildContext context, DrawingCatalog catalog) {
    final options = catalog.suggestions;
    final next = _suggestion[catalog] ?? 0;
    final drawing = options[next % options.length];
    _suggestion[catalog] = next + 1;
    Navigator.of(context).pushNamed(AppRoutes.coloring, arguments: ColoringArgs(drawing.id));
  }

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
        builder: (context, catalog) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (catalog.suggestions.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(AppDimens.pagePadding, 0, AppDimens.pagePadding, 8),
                child: BigActionButton(
                  label: '¡Vamos a pintar!',
                  icon: Icons.brush_rounded,
                  onPressed: () => _startPainting(context, catalog),
                ),
              ),
            Expanded(
              child: AdaptiveGrid(
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
          ],
        ),
      ),
    );
  }
}
