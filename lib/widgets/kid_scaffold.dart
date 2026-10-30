import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import 'doodle_background.dart';
import 'fitted_title.dart';
import 'kid_icon_button.dart';

/// Estructura común de las pantallas infantiles: cabecera con botón grande de
/// volver, título corto y contenido centrado con ancho máximo.
class KidScaffold extends StatelessWidget {
  const KidScaffold({
    super.key,
    required this.title,
    required this.body,
    this.backLabel = 'Volver',
    this.onBack,
    this.titleIcon,
    this.accent = AppColors.coral,
    this.badge,
    this.trailing,
  });

  final String title;
  final Widget body;
  final String backLabel;

  /// Por defecto, vuelve a la pantalla anterior.
  final VoidCallback? onBack;
  final IconData? titleIcon;
  final Color accent;

  /// Marca opcional bajo el título (p. ej. «En construcción»).
  final Widget? badge;

  /// Acción opcional a la derecha del título (p. ej. «Buscar»).
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    // En teléfonos estrechos el icono decorativo del título deja su sitio al
    // texto (el título es más importante y no debe cortarse).
    final showIcon = titleIcon != null && MediaQuery.sizeOf(context).width >= 400;
    return Scaffold(
      body: DoodleBackground(
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: AppDimens.maxContentWidth),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(AppDimens.pagePadding, 12, AppDimens.pagePadding, 8),
                    child: Row(
                      children: [
                        KidIconButton(
                          icon: Icons.arrow_back_rounded,
                          label: backLabel,
                          color: accent,
                          onPressed: onBack ?? () => Navigator.of(context).maybePop(),
                        ),
                        const SizedBox(width: AppDimens.gap),
                        if (showIcon) ...[Icon(titleIcon, color: accent, size: 36), const SizedBox(width: 8)],
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Semantics(
                                header: true,
                                child: FittedTitle(
                                  title,
                                  styles: [
                                    Theme.of(context).textTheme.headlineMedium,
                                    Theme.of(context).textTheme.headlineSmall,
                                    Theme.of(context).textTheme.titleLarge,
                                  ],
                                ),
                              ),
                              if (badge != null) ...[const SizedBox(height: 4), badge!],
                            ],
                          ),
                        ),
                        if (trailing != null) ...[const SizedBox(width: AppDimens.gap), trailing!],
                      ],
                    ),
                  ),
                  Expanded(child: body),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
