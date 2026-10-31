import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../services/app_services.dart';

/// Pantalla ilustrada original. Los controles siguen siendo widgets accesibles
/// encima del WEBP; no se incrustan interacciones dentro de la imagen.
class IllustratedHomeCover extends StatelessWidget {
  const IllustratedHomeCover({super.key, required this.onAdultAccess});

  final VoidCallback onAdultAccess;

  static const artwork = 'assets/ui/pequenos_artistas_inicio.webp';

  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;
    void open(String route) => Navigator.of(context).pushNamed(route);

    return Scaffold(
      backgroundColor: const Color(0xFF89D7FF),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, box) {
            final width = box.maxWidth.clamp(0.0, 680.0).toDouble();
            final height = width * 1.5; // Imagen original 2:3.
            return Center(
              child: SingleChildScrollView(
                child: SizedBox(
                  width: width,
                  height: height,
                  child: Stack(
                    children: [
                      Positioned.fill(
                        child: Image.asset(
                          artwork,
                          fit: BoxFit.fill,
                          filterQuality: FilterQuality.medium,
                          errorBuilder: (context, error, stackTrace) => const Center(
                            child: Text('Pequeños Artistas',
                              style: TextStyle(fontSize: 30, fontWeight: FontWeight.w900)),
                          ),
                        ),
                      ),
                      _CoverButton(
                        label: 'Configuración de sonido; mantén pulsado para la zona de adultos',
                        left: .02, top: .01, width: .12, height: .07,
                        onPressed: () => open(AppRoutes.soundSettings),
                        onLongPress: onAdultAccess,
                      ),
                      ListenableBuilder(
                        listenable: learning,
                        builder: (context, _) {
                          final enabled = learning.settings.musicOn && !learning.settings.muted;
                          return _CoverButton(
                            label: enabled ? 'Desactivar música' : 'Activar música',
                            left: .865, top: .01, width: .12, height: .07,
                            onPressed: () => learning.updateSettings(
                              learning.settings.copyWith(
                                musicOn: !enabled,
                                muted: enabled ? learning.settings.muted : false,
                              ),
                            ),
                          );
                        },
                      ),
                      _CoverButton(label: 'Colorear', left: .055, top: .52, width: .44, height: .165,
                        onPressed: () => open(AppRoutes.categories)),
                      _CoverButton(label: 'Mini Juegos', left: .515, top: .52, width: .43, height: .165,
                        onPressed: () => open(AppRoutes.miniGames)),
                      _CoverButton(label: 'Actividades', left: .055, top: .69, width: .44, height: .165,
                        onPressed: () => open(AppRoutes.activities)),
                      _CoverButton(label: 'Galería', left: .515, top: .69, width: .43, height: .165,
                        onPressed: () => open(AppRoutes.savedDrawings)),
                      _CoverButton(label: 'Perfil', left: .055, top: .885, width: .28, height: .075,
                        onPressed: () => open(AppRoutes.profile)),
                      _CoverButton(label: 'Logros', left: .37, top: .885, width: .27, height: .075,
                        onPressed: () => open(AppRoutes.rewards)),
                      _CoverButton(label: 'Configuración', left: .665, top: .885, width: .31, height: .075,
                        onPressed: () => open(AppRoutes.soundSettings)),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _CoverButton extends StatelessWidget {
  const _CoverButton({
    required this.label,
    required this.left,
    required this.top,
    required this.width,
    required this.height,
    required this.onPressed,
    this.onLongPress,
  });

  final String label;
  final double left, top, width, height;
  final VoidCallback onPressed;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) => Positioned.fill(
    child: LayoutBuilder(
      builder: (context, box) => Stack(children: [
        Positioned(
          left: box.maxWidth * left,
          top: box.maxHeight * top,
          width: box.maxWidth * width,
          height: box.maxHeight * height,
          child: Semantics(
            label: label,
            button: true,
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: onPressed,
              onLongPress: onLongPress,
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ]),
    ),
  );
}
