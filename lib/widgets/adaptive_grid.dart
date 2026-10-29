import 'package:flutter/material.dart';

import '../theme/app_dimens.dart';

/// Rejilla que calcula cuántas columnas caben según el ancho disponible,
/// para adaptarse a teléfonos, tabletas y orientación horizontal.
class AdaptiveGrid extends StatelessWidget {
  const AdaptiveGrid({
    super.key,
    required this.itemCount,
    required this.itemBuilder,
    this.minTileWidth = 170,
    this.maxColumns = 5,
    this.childAspectRatio = 0.85,
    this.tileHeight,
  });

  final int itemCount;
  final IndexedWidgetBuilder itemBuilder;
  final double minTileWidth;
  final int maxColumns;
  final double childAspectRatio;

  /// Altura fija de cada tarjeta (escalada con el texto). Si se indica,
  /// sustituye a [childAspectRatio]; útil para tarjetas con mucho texto.
  final double? tileHeight;

  static int columnsFor(double width, double minTileWidth, int maxColumns) =>
      (width / minTileWidth).floor().clamp(2, maxColumns);

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = columnsFor(constraints.maxWidth, minTileWidth, maxColumns);
        // Con texto ampliado, las tarjetas necesitan más altura.
        final textScale = MediaQuery.textScalerOf(context).scale(1).clamp(1.0, 1.6);
        return GridView.builder(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            8,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            mainAxisSpacing: AppDimens.gap,
            crossAxisSpacing: AppDimens.gap,
            childAspectRatio: childAspectRatio / textScale,
            mainAxisExtent: tileHeight == null ? null : tileHeight! * textScale,
          ),
          itemCount: itemCount,
          itemBuilder: itemBuilder,
        );
      },
    );
  }
}

/// Versión en sliver de [AdaptiveGrid], para listas con cabecera desplazable.
class AdaptiveSliverGrid extends StatelessWidget {
  const AdaptiveSliverGrid({
    super.key,
    required this.itemCount,
    required this.itemBuilder,
    this.minTileWidth = 170,
    this.maxColumns = 5,
    this.childAspectRatio = 0.85,
    this.tileHeight,
  });

  final int itemCount;
  final IndexedWidgetBuilder itemBuilder;
  final double minTileWidth;
  final int maxColumns;
  final double childAspectRatio;

  /// Altura fija (escalada con el texto); sustituye a [childAspectRatio].
  final double? tileHeight;

  @override
  Widget build(BuildContext context) {
    final textScale = MediaQuery.textScalerOf(context).scale(1).clamp(1.0, 1.6);
    return SliverLayoutBuilder(
      builder: (context, constraints) => SliverPadding(
        padding: const EdgeInsets.fromLTRB(
          AppDimens.pagePadding,
          8,
          AppDimens.pagePadding,
          AppDimens.pagePadding,
        ),
        sliver: SliverGrid.builder(
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: AdaptiveGrid.columnsFor(
              constraints.crossAxisExtent - 2 * AppDimens.pagePadding,
              minTileWidth,
              maxColumns,
            ),
            mainAxisSpacing: AppDimens.gap,
            crossAxisSpacing: AppDimens.gap,
            childAspectRatio: childAspectRatio / textScale,
            mainAxisExtent: tileHeight == null ? null : tileHeight! * textScale,
          ),
          itemCount: itemCount,
          itemBuilder: itemBuilder,
        ),
      ),
    );
  }
}
