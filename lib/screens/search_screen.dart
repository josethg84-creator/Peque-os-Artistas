import 'package:flutter/material.dart';

import '../models/drawing.dart';
import '../models/drawing_category.dart';
import '../models/drawing_filter.dart';
import '../navigation/app_routes.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/drawing_card.dart';
import '../widgets/empty_state.dart';
import '../widgets/kid_scaffold.dart';
import '../widgets/saved_ids_builder.dart';

/// Todos los dibujos con búsqueda por nombre y filtros sencillos (categoría,
/// dificultad y orden). Los filtros son botones grandes con icono; escribir
/// es opcional.
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _text = TextEditingController();
  var _filter = const DrawingFilter();

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  void _update(DrawingFilter filter) => setState(() => _filter = filter);

  void _reset() {
    _text.clear();
    _update(const DrawingFilter());
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Buscar dibujos',
      titleIcon: Icons.search_rounded,
      accent: AppColors.sun,
      backLabel: 'Volver a categorías',
      body: CatalogBuilder(
        builder: (context, catalog) {
          final results = _filter.apply(catalog.drawings);
          return SavedIdsBuilder(
            builder: (context, saved) => CustomScrollView(
              slivers: [
                SliverToBoxAdapter(child: _controls(results.length)),
                if (results.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: EmptyState(
                      icon: Icons.search_off_rounded,
                      color: AppColors.sun,
                      title: 'No encontramos dibujos',
                      actionLabel: 'Quitar filtros',
                      actionIcon: Icons.filter_alt_off_rounded,
                      onAction: _reset,
                    ),
                  )
                else
                  AdaptiveSliverGrid(
                    itemCount: results.length,
                    itemBuilder: (context, index) {
                      final drawing = results[index];
                      return DrawingCard(
                        drawing: drawing,
                        painted: saved.contains(drawing.id),
                        onTap: () =>
                            Navigator.of(context)
                                .pushNamed(AppRoutes.coloring, arguments: ColoringArgs(drawing.id)),
                      );
                    },
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _controls(int count) {
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(AppDimens.pagePadding, 4, AppDimens.pagePadding, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _text,
            onChanged: (value) => _update(_filter.copyWith(query: value)),
            textInputAction: TextInputAction.search,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            decoration: InputDecoration(
              hintText: 'Escribe un nombre',
              prefixIcon: const Icon(Icons.search_rounded, size: 32),
              suffixIcon: _text.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: 'Borrar texto',
                      iconSize: 32,
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () {
                        _text.clear();
                        _update(_filter.copyWith(query: ''));
                      },
                    ),
              filled: true,
              fillColor: AppColors.surface,
              contentPadding: const EdgeInsets.symmetric(vertical: 18),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 12),
          _ChipRow(
            label: 'Categoría',
            chips: [
              _FilterChipData('Todos', Icons.apps_rounded, AppColors.inkSoft, _filter.category == null, () {
                _update(_filter.copyWith(category: () => null));
              }),
              for (final c in DrawingCategory.values)
                _FilterChipData(c.label, c.icon, c.color, _filter.category == c, () {
                  _update(_filter.copyWith(category: () => _filter.category == c ? null : c));
                }),
            ],
          ),
          _ChipRow(
            label: 'Dificultad',
            chips: [
              _FilterChipData(
                'Todas',
                Icons.star_outline_rounded,
                AppColors.inkSoft,
                _filter.difficulty == null,
                () {
                  _update(_filter.copyWith(difficulty: () => null));
                },
              ),
              for (final d in Difficulty.values)
                _FilterChipData(d.label, Icons.star_rounded, AppColors.sun, _filter.difficulty == d, () {
                  _update(_filter.copyWith(difficulty: () => _filter.difficulty == d ? null : d));
                }, stars: d.stars),
            ],
          ),
          _ChipRow(
            label: 'Orden',
            chips: [
              _FilterChipData(
                'Normal',
                Icons.grid_view_rounded,
                AppColors.inkSoft,
                _filter.sort == DrawingSort.catalog,
                () => _update(_filter.copyWith(sort: DrawingSort.catalog)),
              ),
              _FilterChipData(
                'A → Z',
                Icons.sort_by_alpha_rounded,
                AppColors.sky,
                _filter.sort == DrawingSort.alphabetical,
                () => _update(_filter.copyWith(sort: DrawingSort.alphabetical)),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Semantics(
              liveRegion: true,
              child: Text(
                count == 1 ? '1 dibujo' : '$count dibujos',
                style: text.titleMedium?.copyWith(color: AppColors.inkSoft),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterChipData {
  const _FilterChipData(this.label, this.icon, this.color, this.selected, this.onTap, {this.stars = 0});

  final String label;
  final IconData icon;
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  /// Para la dificultad: número de estrellas a mostrar en lugar del icono.
  final int stars;
}

/// Fila desplazable de botones grandes de filtro.
class _ChipRow extends StatelessWidget {
  const _ChipRow({required this.label, required this.chips});

  final String label;
  final List<_FilterChipData> chips;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      container: true,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            for (final chip in chips)
              Padding(
                padding: const EdgeInsets.only(right: 10),
                child: _BigChip(data: chip),
              ),
          ],
        ),
      ),
    );
  }
}

class _BigChip extends StatelessWidget {
  const _BigChip({required this.data});

  final _FilterChipData data;

  @override
  Widget build(BuildContext context) {
    final fg = data.selected ? Colors.white : AppColors.ink;
    return Semantics(
      button: true,
      selected: data.selected,
      label: data.label,
      excludeSemantics: true,
      child: Material(
        color: data.selected ? data.color : AppColors.surface,
        shape: StadiumBorder(
          side: BorderSide(
            color: data.selected ? AppColors.ink : data.color.withValues(alpha: 0.5),
            width: 2,
          ),
        ),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: data.onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 56),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (data.stars > 0)
                    for (var i = 0; i < data.stars; i++)
                      Icon(Icons.star_rounded, size: 22, color: data.selected ? Colors.white : AppColors.sun)
                  else
                    Icon(data.icon, size: 26, color: data.selected ? Colors.white : data.color),
                  const SizedBox(width: 6),
                  Text(
                    data.label,
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: fg),
                  ),
                  if (data.selected) ...[
                    const SizedBox(width: 4),
                    const Icon(Icons.check_rounded, size: 22, color: Colors.white),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
