import 'dart:async';

import 'package:flutter/material.dart';

import '../audio/phrases.dart';
import '../models/drawing_catalog.dart';
import '../navigation/app_routes.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/adult_gate.dart';
import '../widgets/app_logo.dart';
import '../widgets/big_action_button.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/doodle_background.dart';
import '../widgets/kid_icon_button.dart';
import '../widgets/mascot.dart';
import '../widgets/menu_tile.dart';

/// Pantalla de inicio: el botón principal abre un dibujo para colorear con un
/// solo toque; debajo están la galería, las actividades y «Mis dibujos».
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  /// Cada pulsación de «¡Vamos a pintar!» propone el siguiente dibujo fácil.
  int _suggestion = 0;

  void _startPainting(DrawingCatalog catalog) {
    final options = catalog.suggestions;
    if (options.isEmpty) {
      Navigator.of(context).pushNamed(AppRoutes.categories);
      return;
    }
    final drawing = options[_suggestion % options.length];
    _suggestion++;
    Navigator.of(context).pushNamed(AppRoutes.coloring, arguments: ColoringArgs(drawing.id));
  }

  Future<void> _openAdultZone() async {
    final navigator = Navigator.of(context);
    if (await showAdultGate(context)) {
      navigator.pushNamed(AppRoutes.adultZone, arguments: const AdultZoneArgs.verified());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: DoodleBackground(
        child: SafeArea(
          child: CatalogBuilder(
            builder: (context, catalog) => LayoutBuilder(
              builder: (context, constraints) {
                final wide = constraints.maxWidth > constraints.maxHeight && constraints.maxWidth >= 600;
                final header = _Header(compact: wide && constraints.maxHeight < 500);
                final actions = _Actions(onStart: () => _startPainting(catalog));
                return Stack(
                  children: [
                    Center(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(
                          AppDimens.pagePadding,
                          64,
                          AppDimens.pagePadding,
                          AppDimens.pagePadding,
                        ),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: AppDimens.maxContentWidth),
                          child: wide
                              ? Row(
                                  children: [
                                    Expanded(flex: 4, child: header),
                                    const SizedBox(width: AppDimens.gapLarge),
                                    Expanded(flex: 5, child: actions),
                                  ],
                                )
                              : Column(
                                  children: [
                                    header,
                                    const SizedBox(height: AppDimens.gapLarge),
                                    actions,
                                  ],
                                ),
                        ),
                      ),
                    ),
                    const Positioned(top: 8, left: 8, child: _SoundControls()),
                    Positioned(top: 8, right: 8, child: _AdultAccessButton(onConfirmed: _openAdultZone)),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Column(
      children: [
        AppLogo(size: compact ? 96 : 140),
        const SizedBox(height: 8),
        Semantics(
          header: true,
          child: Text(
            'Pequeños Artistas',
            textAlign: TextAlign.center,
            style: text.displaySmall?.copyWith(color: AppColors.coral),
          ),
        ),
        const SizedBox(height: 6),
        const SizedBox(height: 4),
        MascotBubble(
          text: '¡Hola! ¿Qué quieres pintar hoy?',
          size: compact ? 56 : 76,
          // La voz solo saluda si el niño toca a Pincelín: nada automático.
          onTap: () => unawaited(AppServices.of(context).audio.sayOneOf(Phrases.welcome)),
        ),
      ],
    );
  }
}

class _Actions extends StatelessWidget {
  const _Actions({required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    final navigator = Navigator.of(context);
    List<Widget> tiles({required bool horizontal}) => [
      MenuTile(
        icon: Icons.photo_library_rounded,
        label: 'Galería',
        horizontal: horizontal,
        color: AppColors.sky,
        semanticsHint: 'Elige un dibujo por categoría',
        onTap: () => navigator.pushNamed(AppRoutes.categories),
      ),
      MenuTile(
        icon: Icons.extension_rounded,
        label: 'Aprender jugando',
        horizontal: horizontal,
        color: AppColors.leaf,
        onTap: () => navigator.pushNamed(AppRoutes.activities),
      ),
      MenuTile(
        icon: Icons.collections_rounded,
        label: 'Mis dibujos',
        horizontal: horizontal,
        color: AppColors.grape,
        onTap: () => navigator.pushNamed(AppRoutes.savedDrawings),
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        BigActionButton(label: '¡Vamos a pintar!', icon: Icons.brush_rounded, onPressed: onStart),
        const SizedBox(height: AppDimens.gapLarge),
        LayoutBuilder(
          builder: (context, constraints) {
            // Tres tarjetas en fila si caben; si no, en columna y en formato horizontal.
            if (constraints.maxWidth >= 420) {
              return IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final (i, tile) in tiles(horizontal: false).indexed) ...[
                      if (i > 0) const SizedBox(width: AppDimens.gap),
                      Expanded(child: tile),
                    ],
                  ],
                ),
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final (i, tile) in tiles(horizontal: true).indexed) ...[
                  if (i > 0) const SizedBox(height: 12),
                  tile,
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

/// Silencio total de un toque (música, efectos y voz) y acceso a «Sonido y
/// música» para ajustar cada cosa por separado.
class _SoundControls extends StatelessWidget {
  const _SoundControls();

  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;
    return ListenableBuilder(
      listenable: learning,
      builder: (context, _) {
        final on = !learning.settings.muted;
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            KidIconButton(
              icon: on ? Icons.volume_up_rounded : Icons.volume_off_rounded,
              label: on ? 'Sonidos activados' : 'Sonidos desactivados',
              color: on ? AppColors.sky : AppColors.inkSoft,
              size: 52,
              selected: on,
              onPressed: () => learning.updateSettings(learning.settings.copyWith(muted: on)),
            ),
            const SizedBox(width: 8),
            KidIconButton(
              icon: Icons.tune_rounded,
              label: 'Sonido y música',
              color: AppColors.grape,
              size: 52,
              onPressed: () => Navigator.of(context).pushNamed(AppRoutes.soundSettings),
            ),
          ],
        );
      },
    );
  }
}

/// Acceso discreto para adultos: hay que mantenerlo pulsado y después
/// superar la verificación.
class _AdultAccessButton extends StatelessWidget {
  const _AdultAccessButton({required this.onConfirmed});

  final VoidCallback onConfirmed;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Zona para adultos',
      hint: 'Mantén pulsado para entrar',
      excludeSemantics: true,
      onLongPress: onConfirmed,
      child: Tooltip(
        message: 'Adultos: mantén pulsado',
        triggerMode: TooltipTriggerMode.tap,
        child: GestureDetector(
          onLongPress: onConfirmed,
          child: Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.inkSoft.withValues(alpha: 0.35), width: 2),
            ),
            child: Icon(Icons.lock_rounded, color: AppColors.inkSoft.withValues(alpha: 0.6), size: 24),
          ),
        ),
      ),
    );
  }
}
