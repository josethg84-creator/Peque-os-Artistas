import 'package:flutter/material.dart';

import '../coloring/color_palette_bar.dart';
import '../coloring/coloring_canvas.dart';
import '../coloring/coloring_controller.dart';
import '../coloring/coloring_toolbar.dart';
import '../models/drawing.dart';
import '../navigation/app_router.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/empty_state.dart';
import '../widgets/kid_icon_button.dart';

/// Pantalla de coloreado (estructura visual; el motor llega en la Fase 3).
class ColoringScreen extends StatefulWidget {
  const ColoringScreen({super.key, required this.drawingId});

  final String drawingId;

  @override
  State<ColoringScreen> createState() => _ColoringScreenState();
}

class _ColoringScreenState extends State<ColoringScreen> {
  final _controller = ColoringController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: CatalogBuilder(
          builder: (context, catalog) {
            final drawing = catalog.byId(widget.drawingId);
            if (drawing == null) {
              return EmptyState(
                icon: Icons.search_off_rounded,
                title: 'No encontramos este dibujo',
                message: 'Elige otro en la galería.',
                actionLabel: 'Ir al inicio',
                onAction: () => AppRouter.goHome(context),
              );
            }
            return ListenableBuilder(
              listenable: _controller,
              builder: (context, _) => _ColoringLayout(drawing: drawing, controller: _controller),
            );
          },
        ),
      ),
    );
  }
}

class _ColoringLayout extends StatelessWidget {
  const _ColoringLayout({required this.drawing, required this.controller});

  final Drawing drawing;
  final ColoringController controller;

  @override
  Widget build(BuildContext context) {
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
        final title = Semantics(
          header: true,
          child: Text(
            drawing.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        );

        if (landscape) {
          return Row(
            children: [
              _Panel(
                child: Column(
                  children: [
                    Padding(padding: const EdgeInsets.all(8), child: back),
                    Expanded(
                      child: SingleChildScrollView(
                        child: ColoringToolbar(controller: controller, axis: Axis.vertical),
                      ),
                    ),
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
                child: ColorPaletteBar(controller: controller, axis: Axis.vertical),
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
                  const SizedBox(width: AppDimens.minTouchTarget + 12),
                ],
              ),
            ),
            Expanded(child: canvas),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: ColoringToolbar(controller: controller),
            ),
            _Panel(child: ColorPaletteBar(controller: controller)),
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
