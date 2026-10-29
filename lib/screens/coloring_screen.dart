import 'package:flutter/material.dart';

import '../coloring/color_palette_bar.dart';
import '../coloring/coloring_canvas.dart';
import '../coloring/coloring_controller.dart';
import '../coloring/coloring_toolbar.dart';
import '../coloring/save_indicator.dart';
import '../models/drawing.dart';
import '../models/drawing_catalog.dart';
import '../navigation/app_router.dart';
import '../navigation/app_routes.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/drawing_thumbnail.dart';
import '../widgets/empty_state.dart';
import '../widgets/kid_icon_button.dart';

/// Pantalla de coloreado de un dibujo del catálogo.
class ColoringScreen extends StatelessWidget {
  const ColoringScreen({super.key, required this.drawingId, this.creationId, this.startNew = false});

  final String drawingId;
  final String? creationId;
  final bool startNew;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: CatalogBuilder(
          builder: (context, catalog) {
            final drawing = catalog.byId(drawingId);
            if (drawing == null) {
              return EmptyState(
                icon: Icons.search_off_rounded,
                title: 'No encontramos este dibujo',
                message: 'Elige otro en la galería.',
                actionLabel: 'Ir al inicio',
                onAction: () => AppRouter.goHome(context),
              );
            }
            // La clave garantiza un estado nuevo para cada dibujo.
            return _ColoringSession(
              key: ValueKey((drawing.id, creationId, startNew)),
              drawing: drawing,
              catalog: catalog,
              creationId: creationId,
              startNew: startNew,
            );
          },
        ),
      ),
    );
  }
}

/// Una sesión de coloreado: crea el controlador del dibujo, lo carga y guarda
/// el progreso al salir o cuando la aplicación pasa a segundo plano.
class _ColoringSession extends StatefulWidget {
  const _ColoringSession({
    super.key,
    required this.drawing,
    required this.catalog,
    this.creationId,
    this.startNew = false,
  });

  final Drawing drawing;
  final DrawingCatalog catalog;
  final String? creationId;
  final bool startNew;

  @override
  State<_ColoringSession> createState() => _ColoringSessionState();
}

class _ColoringSessionState extends State<_ColoringSession> {
  ColoringController? _controller;
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();
    _lifecycle = AppLifecycleListener(onHide: () => _controller?.save());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_controller == null) {
      final services = AppServices.of(context);
      _controller = ColoringController(
        drawingId: widget.drawing.id,
        file: widget.drawing.file,
        loader: services.drawings,
        store: services.creations,
        creationId: widget.creationId,
        startNew: widget.startNew,
      )..load();
    }
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _confirmClear() async {
    final controller = _controller!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        icon: const Icon(Icons.delete_outline_rounded, size: 48, color: AppColors.coral),
        title: const Text('¿Borrar todos los colores?', textAlign: TextAlign.center),
        actionsAlignment: MainAxisAlignment.spaceEvenly,
        actions: [
          KidIconButton(
            icon: Icons.close_rounded,
            label: 'No, seguir pintando',
            color: AppColors.inkSoft,
            showLabel: true,
            onPressed: () => Navigator.of(context).pop(false),
          ),
          KidIconButton(
            icon: Icons.check_rounded,
            label: 'Sí, borrar',
            color: AppColors.coral,
            showLabel: true,
            onPressed: () => Navigator.of(context).pop(true),
          ),
        ],
      ),
    );
    if (confirmed == true) controller.clear();
  }

  void _chooseAnotherDrawing() {
    final others = widget.catalog.byCategory(widget.drawing.category).where((d) => d.id != widget.drawing.id);
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(sheetContext).height * 0.7),
          child: GridView.extent(
            shrinkWrap: true,
            maxCrossAxisExtent: 150,
            padding: const EdgeInsets.all(16),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            children: [
              for (final d in others)
                Semantics(
                  button: true,
                  label: d.name,
                  excludeSemantics: true,
                  child: Material(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
                    elevation: 1,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
                      onTap: () {
                        Navigator.of(sheetContext).pop();
                        // Sustituye la pantalla: el dibujo actual se guarda
                        // al cerrarse y el nuevo empieza con su propio estado.
                        Navigator.of(context)
                            .pushReplacementNamed(AppRoutes.coloring, arguments: ColoringArgs(d.id));
                      },
                      child: Padding(
                        padding: const EdgeInsets.all(8),
                        child: DrawingThumbnail(asset: d.thumbnailAsset),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _ColoringLayout(
      drawing: widget.drawing,
      controller: _controller!,
      onClear: _confirmClear,
      onChangeDrawing: _chooseAnotherDrawing,
    );
  }
}

class _ColoringLayout extends StatelessWidget {
  const _ColoringLayout({
    required this.drawing,
    required this.controller,
    required this.onClear,
    required this.onChangeDrawing,
  });

  final Drawing drawing;
  final ColoringController controller;
  final VoidCallback onClear;
  final VoidCallback onChangeDrawing;

  @override
  Widget build(BuildContext context) {
    // Solo la paleta y las herramientas escuchan al controlador: un toque en
    // el dibujo no reconstruye la pantalla entera.
    Widget toolbar(Axis axis) => ListenableBuilder(
      listenable: controller,
      builder: (_, _) => ColoringToolbar(controller: controller, onClear: onClear, axis: axis),
    );
    Widget palette(Axis axis) => ListenableBuilder(
      listenable: controller,
      builder: (_, _) => ColorPaletteBar(controller: controller, axis: axis),
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final landscape = constraints.maxWidth > constraints.maxHeight;
        final canvas = Padding(
          padding: const EdgeInsets.all(12),
          child: ColoringCanvas(drawing: drawing, controller: controller),
        );
        final back = KidIconButton(
          icon: Icons.arrow_back_rounded,
          label: 'Volver a la galería',
          color: drawing.category.color,
          onPressed: () => Navigator.of(context).maybePop(),
        );
        final change = KidIconButton(
          icon: Icons.grid_view_rounded,
          label: 'Otro dibujo',
          color: AppColors.sun,
          onPressed: onChangeDrawing,
        );
        final title = Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Semantics(
              header: true,
              child: Text(
                drawing.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            ListenableBuilder(
              listenable: controller,
              builder: (_, _) => SaveIndicator(controller: controller),
            ),
          ],
        );

        if (landscape) {
          return Row(
            children: [
              _Panel(
                child: Column(
                  children: [
                    Padding(padding: const EdgeInsets.all(8), child: back),
                    Expanded(child: SingleChildScrollView(child: toolbar(Axis.vertical))),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  children: [
                    Padding(padding: const EdgeInsets.only(top: 8), child: title),
                    Expanded(child: canvas),
                  ],
                ),
              ),
              _Panel(
                child: Column(
                  children: [
                    Padding(padding: const EdgeInsets.all(8), child: change),
                    Expanded(child: palette(Axis.vertical)),
                  ],
                ),
              ),
            ],
          );
        }
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(AppDimens.pagePadding, 12, AppDimens.pagePadding, 0),
              child: Row(
                children: [
                  back,
                  const SizedBox(width: 12),
                  Expanded(child: title),
                  const SizedBox(width: 12),
                  change,
                ],
              ),
            ),
            Expanded(child: canvas),
            SingleChildScrollView(scrollDirection: Axis.horizontal, child: toolbar(Axis.horizontal)),
            _Panel(child: palette(Axis.horizontal)),
          ],
        );
      },
    );
  }
}

/// Fondo suave para agrupar la paleta y las herramientas.
class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
      ),
      child: child,
    );
  }
}
