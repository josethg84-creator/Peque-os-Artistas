import 'package:flutter/material.dart';

import '../coloring/engine/drawing_painter.dart';
import '../coloring/engine/vector_drawing.dart';
import '../models/drawing.dart';
import '../navigation/app_routes.dart';
import '../services/app_services.dart';
import '../services/progress_store.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/empty_state.dart';
import '../widgets/kid_scaffold.dart';

/// Dibujos empezados, con sus colores guardados, del más reciente al más
/// antiguo. Al tocar uno se sigue pintando donde se dejó.
class SavedDrawingsScreen extends StatefulWidget {
  const SavedDrawingsScreen({super.key});

  @override
  State<SavedDrawingsScreen> createState() => _SavedDrawingsScreenState();
}

class _SavedDrawingsScreenState extends State<SavedDrawingsScreen> {
  Future<List<SavedProgress>>? _saved;
  ProgressStore? _store;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_store == null) {
      // Se recarga cada vez que se guarda un dibujo (p. ej. al volver de pintar).
      _store = AppServices.of(context).progress..changes.addListener(_reload);
      _saved = _load();
    }
  }

  @override
  void dispose() {
    _store?.changes.removeListener(_reload);
    super.dispose();
  }

  Future<List<SavedProgress>> _load() => _store!.loadAll().catchError((Object _) => <SavedProgress>[]);

  void _reload() {
    if (!mounted) return;
    setState(() {
      _saved = _load();
    });
  }

  void _open(Drawing drawing) =>
      Navigator.of(context).pushNamed(AppRoutes.coloring, arguments: ColoringArgs(drawing.id));

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Mis dibujos',
      titleIcon: Icons.collections_rounded,
      accent: AppColors.grape,
      backLabel: 'Volver al inicio',
      body: CatalogBuilder(
        builder: (context, catalog) => FutureBuilder<List<SavedProgress>>(
          future: _saved,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator(color: AppColors.grape));
            }
            final items = [
              for (final p in snapshot.data ?? const <SavedProgress>[])
                if (catalog.byId(p.drawingId) case final drawing?) (drawing, p),
            ];
            if (items.isEmpty) {
              return EmptyState(
                icon: Icons.collections_rounded,
                color: AppColors.grape,
                title: 'Aquí verás tus dibujos',
                message: 'Pinta un dibujo y aparecerá aquí.',
                actionLabel: 'Ir a la galería',
                actionIcon: Icons.photo_library_rounded,
                onAction: () => Navigator.of(context).pushReplacementNamed(AppRoutes.categories),
              );
            }
            return AdaptiveGrid(
              itemCount: items.length,
              itemBuilder: (context, index) {
                final (drawing, progress) = items[index];
                return _SavedCard(drawing: drawing, progress: progress, onTap: () => _open(drawing));
              },
            );
          },
        ),
      ),
    );
  }
}

class _SavedCard extends StatefulWidget {
  const _SavedCard({required this.drawing, required this.progress, required this.onTap});

  final Drawing drawing;
  final SavedProgress progress;
  final VoidCallback onTap;

  @override
  State<_SavedCard> createState() => _SavedCardState();
}

class _SavedCardState extends State<_SavedCard> {
  Future<VectorDrawing>? _vector;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _vector ??= AppServices.of(context).drawings.load(widget.drawing.file);
  }

  @override
  Widget build(BuildContext context) {
    final drawing = widget.drawing;
    return Semantics(
      button: true,
      label: '${drawing.name}, pintado',
      hint: 'Sigue pintando',
      excludeSemantics: true,
      child: Material(
        color: AppColors.surface,
        elevation: 2,
        borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          onTap: widget.onTap,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: FutureBuilder<VectorDrawing>(
                    future: _vector,
                    builder: (context, snapshot) {
                      final vector = snapshot.data;
                      if (vector == null) {
                        return snapshot.hasError
                            ? const Icon(Icons.broken_image_rounded, size: 48, color: AppColors.inkSoft)
                            : const SizedBox.shrink();
                      }
                      return CustomPaint(
                        painter: DrawingPainter(
                          drawing: vector,
                          colors: FixedRegionColors(widget.progress.regionColors),
                        ),
                      );
                    },
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
              ],
            ),
          ),
        ),
      ),
    );
  }
}
