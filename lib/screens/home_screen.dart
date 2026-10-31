import 'package:flutter/material.dart';

import '../navigation/app_routes.dart';
import '../services/app_services.dart';
import '../widgets/adult_gate.dart';

/// Portada con ilustración original. Los botones son zonas táctiles reales,
/// no parte de una imagen que se espere que responda por sí sola.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  static const imagePath = 'assets/ui/pequenos_artistas_inicio.webp';

  Future<void> _openAdultZone(BuildContext context) async {
    final navigator = Navigator.of(context);
    if (await showAdultGate(context)) {
      navigator.pushNamed(AppRoutes.adultZone, arguments: const AdultZoneArgs.verified());
    }
  }

  void _navigate(BuildContext context, String route) =>
      Navigator.of(context).pushNamed(route);

  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;

    return Scaffold(
      backgroundColor: const Color(0xFFBCEBFF),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            // La referencia original tiene proporción 1024:1536 (2:3).
            // En móviles pequeños se desplaza verticalmente sin recortar botones.
            final width = constraints.maxWidth < 640 ? constraints.maxWidth : 640.0;
            final canvasHeight = width * 1.5;

            return Center(
              child: SingleChildScrollView(
                child: SizedBox(
                  width: width,
                  height: canvasHeight,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Image.asset(
                        imagePath,
                        fit: BoxFit.fill,
                        filterQuality: FilterQuality.high,
                        errorBuilder: (context, error, stack) =>
                            _FallbackCover(onTap: (route) => _navigate(context, route)),
                      ),
                      _Hotspot(
                        label: 'Ajustes de sonido. Mantener pulsado para zona de adultos.',
                        x: .015, y: .005, w: .13, h: .08,
                        onTap: () => _navigate(context, AppRoutes.soundSettings),
                        onLongPress: () => _openAdultZone(context),
                      ),
                      ListenableBuilder(
                        listenable: learning,
                        builder: (context, _) => _Hotspot(
                          label: learning.settings.muted ? 'Activar música y sonido' : 'Silenciar música y sonido',
                          x: .865, y: .005, w: .12, h: .08,
                          onTap: () => learning.updateSettings(
                            learning.settings.copyWith(muted: !learning.settings.muted)),
                        ),
                      ),
                      _Hotspot(label: 'Colorear', x: .06, y: .515, w: .44, h: .175,
                        onTap: () => _navigate(context, AppRoutes.categories)),
                      _Hotspot(label: 'Mini juegos', x: .51, y: .515, w: .44, h: .175,
                        onTap: () => _navigate(context, AppRoutes.activities)),
                      _Hotspot(label: 'Actividades educativas', x: .06, y: .692, w: .44, h: .175,
                        onTap: () => _navigate(context, AppRoutes.activities)),
                      _Hotspot(label: 'Galería de mis dibujos', x: .51, y: .692, w: .44, h: .175,
                        onTap: () => _navigate(context, AppRoutes.savedDrawings)),
                      _Hotspot(label: 'Mi perfil y progreso', x: .04, y: .88, w: .29, h: .085,
                        onTap: () => _navigate(context, AppRoutes.kidProgress)),
                      _Hotspot(label: 'Mis logros', x: .355, y: .88, w: .285, h: .085,
                        onTap: () => _navigate(context, AppRoutes.rewards)),
                      _Hotspot(label: 'Configuración', x: .655, y: .88, w: .325, h: .085,
                        onTap: () => _navigate(context, AppRoutes.soundSettings)),
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

/// Posiciones proporcionales a la portada. A diferencia de la imagen, estas
/// superficies son accesibles y permiten navegar con un toque.
class _Hotspot extends StatelessWidget {
  const _Hotspot({
    required this.label,
    required this.x, required this.y, required this.w, required this.h,
    required this.onTap,
    this.onLongPress,
  });

  final String label;
  final double x, y, w, h;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) => Positioned.fill(
    child: LayoutBuilder(
      builder: (context, size) => Stack(children: [
        Positioned(
          left: size.maxWidth * x,
          top: size.maxHeight * y,
          width: size.maxWidth * w,
          height: size.maxHeight * h,
          child: Semantics(
            button: true,
            label: label,
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: onTap,
              onLongPress: onLongPress,
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ]),
    ),
  );
}

/// Diseño funcional de reserva cuando aún no se ha añadido el archivo WEBP.
class _FallbackCover extends StatelessWidget {
  const _FallbackCover({required this.onTap});
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.fromLTRB(14, 80, 14, 18),
    decoration: const BoxDecoration(gradient: LinearGradient(
      begin: Alignment.topCenter, end: Alignment.bottomCenter,
      colors: [Color(0xFF84D9FF), Color(0xFFFFDEF3), Color(0xFFFFE5AB)],
    )),
    child: Column(children: [
      const Icon(Icons.star_rounded, color: Color(0xFFFFC536), size: 55),
      const FittedBox(child: Text('Pequeños Artistas', style: TextStyle(
        color: Color(0xFF8B39CB), fontSize: 36, fontWeight: FontWeight.w900))),
      const SizedBox(height: 8),
      const Text('Un mundo de colores, juegos y creatividad',
        textAlign: TextAlign.center, style: TextStyle(
          color: Color(0xFFC4317A), fontSize: 15, fontWeight: FontWeight.w800)),
      const Spacer(),
      const Icon(Icons.palette_rounded, size: 88, color: Color(0xFFFA73A8)),
      const Spacer(),
      _FallbackRow(
        first: 'Colorear', second: 'Mini Juegos',
        firstColor: const Color(0xFFBDEBFF), secondColor: const Color(0xFFFFC8E7),
        firstTap: () => onTap(AppRoutes.categories), secondTap: () => onTap(AppRoutes.activities)),
      const SizedBox(height: 12),
      _FallbackRow(
        first: 'Actividades', second: 'Galería',
        firstColor: const Color(0xFFCAF8CA), secondColor: const Color(0xFFE6D3FF),
        firstTap: () => onTap(AppRoutes.activities), secondTap: () => onTap(AppRoutes.savedDrawings)),
      const Spacer(),
      Row(children: [
        for (final item in [
          ('Perfil', AppRoutes.kidProgress),
          ('Logros', AppRoutes.rewards),
          ('Config.', AppRoutes.soundSettings),
        ]) Expanded(child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 3),
          child: FilledButton(onPressed: () => onTap(item.$2), child: Text(item.$1)),
        )),
      ]),
    ]),
  );
}

class _FallbackRow extends StatelessWidget {
  const _FallbackRow({
    required this.first, required this.second,
    required this.firstColor, required this.secondColor,
    required this.firstTap, required this.secondTap,
  });
  final String first, second;
  final Color firstColor, secondColor;
  final VoidCallback firstTap, secondTap;

  @override
  Widget build(BuildContext context) => Row(children: [
    for (final item in [(first, firstColor, firstTap), (second, secondColor, secondTap)])
      Expanded(child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 5),
        child: Material(color: item.$2, borderRadius: BorderRadius.circular(24),
          child: InkWell(onTap: item.$3, borderRadius: BorderRadius.circular(24),
            child: SizedBox(height: 90, child: Center(child: Text(item.$1,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)))))),
      )),
  ]);
}
