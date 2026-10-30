import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/ui_sounds.dart';

import '../coloring/engine/drawing_painter.dart';
import '../coloring/engine/vector_drawing.dart';
import '../models/drawing.dart';
import '../models/drawing_catalog.dart';
import '../navigation/app_routes.dart';
import '../persistence/creation.dart';
import '../persistence/creation_store.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/empty_state.dart';
import '../widgets/motion/delayed_loading.dart';
import '../widgets/friendly_date.dart';
import '../widgets/kid_icon_button.dart';
import '../widgets/kid_scaffold.dart';

/// «Mis dibujos»: las creaciones guardadas en el dispositivo, de la más
/// reciente a la más antigua. Tocar una la abre para seguir pintando.
///
/// Solo se muestran creaciones válidas de dibujos que existen en el catálogo;
/// las dañadas o huérfanas no se enseñan al niño, pero tampoco se borran (la
/// zona para adultos las lista).
class SavedDrawingsScreen extends StatefulWidget {
  const SavedDrawingsScreen({super.key});

  @override
  State<SavedDrawingsScreen> createState() => _SavedDrawingsScreenState();
}

class _SavedDrawingsScreenState extends State<SavedDrawingsScreen> {
  Future<CreationReport>? _report;
  CreationStore? _store;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_store == null) {
      // Se recarga cada vez que se guarda o se borra algo.
      _store = AppServices.of(context).creations..changes.addListener(_reload);
      _report = _loadReport();
    }
  }

  @override
  void dispose() {
    _store?.changes.removeListener(_reload);
    super.dispose();
  }

  void _reload() {
    if (!mounted) return;
    setState(() {
      _report = _loadReport();
    });
  }

  /// El error se muestra en pantalla (FutureBuilder); `ignore` evita que se
  /// considere no gestionado mientras el catálogo aún está cargando.
  Future<CreationReport> _loadReport() => _store!.loadAll()..ignore();

  void _open(Creation creation) => Navigator.of(context)
      .pushNamed(AppRoutes.coloring, arguments: ColoringArgs(creation.drawingId, creationId: creation.id));

  void _startAgain(Drawing drawing) =>
      Navigator.of(context)
          .pushNamed(AppRoutes.coloring, arguments: ColoringArgs(drawing.id, startNew: true));

  Future<void> _delete(Drawing drawing, Creation creation) async {
    final messenger = ScaffoldMessenger.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Borrar este dibujo pintado?', textAlign: TextAlign.center),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox.square(
              dimension: 140,
              child: _CreationThumbnail(drawing: drawing, creation: creation),
            ),
            const SizedBox(height: 12),
            const Text(
              'El dibujo seguirá en la galería para pintarlo otra vez.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actionsAlignment: MainAxisAlignment.spaceEvenly,
        actions: [
          KidIconButton(
            icon: Icons.close_rounded,
            label: 'No, guardarlo',
            color: AppColors.leaf,
            showLabel: true,
            onPressed: () => Navigator.of(context).pop(false),
          ),
          KidIconButton(
            icon: Icons.delete_outline_rounded,
            label: 'Sí, borrar',
            color: AppColors.coral,
            showLabel: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _store!.delete(creation.id);
    } catch (_) {
      messenger.showSnackBar(const SnackBar(content: Text('No se pudo borrar. Inténtalo otra vez.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Mis dibujos',
      titleIcon: Icons.collections_rounded,
      accent: AppColors.grape,
      backLabel: 'Volver al inicio',
      body: CatalogBuilder(
        builder: (context, catalog) => FutureBuilder<CreationReport>(
          future: _report,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const DelayedLoading(message: 'Buscando tus dibujos…', color: AppColors.grape);
            }
            if (snapshot.hasError) {
              return EmptyState(
                icon: Icons.sd_card_alert_rounded,
                color: AppColors.grape,
                title: 'No pudimos abrir tus dibujos',
                message: 'Tus dibujos siguen guardados. Prueba otra vez.',
                actionLabel: 'Reintentar',
                actionIcon: Icons.refresh_rounded,
                onAction: _reload,
              );
            }
            final items = _visible(snapshot.data!, catalog);
            if (items.isEmpty) {
              return EmptyState(
                icon: Icons.palette_rounded,
                color: AppColors.grape,
                title: '¡Tu galería te espera!',
                message: 'Aquí aparecerán tus dibujos favoritos. ¡Pinta uno!',
                showMascot: true,
                actionLabel: 'Ir a pintar',
                actionIcon: Icons.brush_rounded,
                onAction: () => Navigator.of(context).pushReplacementNamed(AppRoutes.categories),
              );
            }
            return AdaptiveGrid(
              itemCount: items.length,
              minTileWidth: 220,
              maxColumns: 4,
              childAspectRatio: 0.66,
              itemBuilder: (context, index) {
                final (drawing, creation) = items[index];
                return _CreationCard(
                  key: ValueKey(creation.id),
                  drawing: drawing,
                  creation: creation,
                  onOpen: () => _open(creation),
                  onStartAgain: () => _startAgain(drawing),
                  onDelete: () => _delete(drawing, creation),
                );
              },
            );
          },
        ),
      ),
    );
  }

  static List<(Drawing, Creation)> _visible(CreationReport report, DrawingCatalog catalog) => [
    for (final c in report.creations)
      if (catalog.byId(c.drawingId) case final drawing? when c.regionColors.isNotEmpty) (drawing, c),
  ];
}

class _CreationCard extends StatelessWidget {
  const _CreationCard({
    super.key,
    required this.drawing,
    required this.creation,
    required this.onOpen,
    required this.onStartAgain,
    required this.onDelete,
  });

  final Drawing drawing;
  final Creation creation;
  final VoidCallback onOpen;
  final VoidCallback onStartAgain;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final done = creation.status == CreationStatus.completed;
    final date = friendlyDate(creation.updatedAt);
    return Material(
      color: AppColors.surface,
      elevation: 2,
      borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Semantics(
                button: true,
                label: '${drawing.name}. ${done ? '¡Terminado!' : 'Sin terminar'}. $date',
                hint: 'Sigue pintando',
                excludeSemantics: true,
                onTap: withSound(context, SoundCue.open, onOpen),
                child: InkWell(
                  borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
                  onTap: withSound(context, SoundCue.open, onOpen),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: Stack(
                          children: [
                            Positioned.fill(
                              child: _CreationThumbnail(drawing: drawing, creation: creation),
                            ),
                            if (done) const Positioned(top: 0, right: 0, child: _DoneBadge()),
                          ],
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        drawing.name,
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        date,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: AppColors.inkSoft, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 6),
                      _ProgressBar(creation: creation, color: drawing.category.color),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                KidIconButton(
                  icon: Icons.restart_alt_rounded,
                  label: 'Pintar otra vez',
                  color: AppColors.sky,
                  size: 52,
                  onPressed: onStartAgain,
                ),
                KidIconButton(
                  icon: Icons.delete_outline_rounded,
                  label: 'Borrar',
                  color: AppColors.coral,
                  size: 52,
                  onPressed: onDelete,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Barra de progreso amable: muestra lo pintado, sin puntuaciones.
class _ProgressBar extends StatelessWidget {
  const _ProgressBar({required this.creation, required this.color});

  final Creation creation;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final value = creation.progress;
    if (value == null) return const SizedBox(height: 14);
    return ClipRRect(
      borderRadius: BorderRadius.circular(7),
      child: LinearProgressIndicator(
        value: value,
        minHeight: 14,
        color: color,
        backgroundColor: color.withValues(alpha: 0.18),
        semanticsLabel: 'Zonas pintadas',
        semanticsValue: '${creation.paintedRegions} de ${creation.totalRegions}',
      ),
    );
  }
}

class _DoneBadge extends StatelessWidget {
  const _DoneBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.sun,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.ink, width: 1.5),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.emoji_events_rounded, size: 18, color: AppColors.ink),
          SizedBox(width: 4),
          Text(
            '¡Terminado!',
            style: TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink),
          ),
        ],
      ),
    );
  }
}

/// Miniatura de una creación: se reconstruye pintando el dibujo vectorial con
/// los colores guardados (no se guardan imágenes). Así siempre refleja el
/// último estado y no puede faltar ni estar desactualizada.
class _CreationThumbnail extends StatefulWidget {
  const _CreationThumbnail({required this.drawing, required this.creation});

  final Drawing drawing;
  final Creation creation;

  @override
  State<_CreationThumbnail> createState() => _CreationThumbnailState();
}

class _CreationThumbnailState extends State<_CreationThumbnail> {
  Future<VectorDrawing>? _vector;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _vector ??= AppServices.of(context).drawings.load(widget.drawing.file);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<VectorDrawing>(
      future: _vector,
      builder: (context, snapshot) {
        final vector = snapshot.data;
        if (vector == null) {
          return snapshot.hasError
              ? const Icon(Icons.broken_image_rounded, size: 48, color: AppColors.inkSoft)
              : const SizedBox.shrink();
        }
        return RepaintBoundary(
          child: CustomPaint(
            painter: DrawingPainter(drawing: vector, colors: FixedRegionColors(widget.creation.regionColors)),
          ),
        );
      },
    );
  }
}
