import 'dart:math';
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../audio/phrases.dart';
import '../../audio/app_audio.dart';
import '../../audio/ui_sounds.dart';
import '../../aac/widgets/aac_widgets.dart';
import '../../navigation/app_routes.dart';
import '../../services/app_services.dart';
import '../../theme/app_motion.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../widgets/motion/pressable.dart';

/// Inicio con la ilustración original completa (`assets/ui/`). Lo que se ve es
/// la imagen tal cual, sin deformar; encima van zonas táctiles transparentes,
/// colocadas en proporción a la imagen, que hacen funcionar cada botón dibujado.
///
/// Si la imagen no se puede cargar se muestra [fallback] (el inicio vectorial).
class IllustratedHomeCover extends StatefulWidget {
  const IllustratedHomeCover({super.key, required this.onAdultAccess, required this.fallback});

  final VoidCallback onAdultAccess;
  final WidgetBuilder fallback;

  static const artwork = 'assets/ui/pequenos_artistas_inicio.webp';

  /// Proporción alto/ancho de la ilustración (1024 × 1536).
  static const aspect = 1.5;

  /// Ancho de la ilustración según el espacio disponible: llena el ancho en
  /// teléfonos verticales, cabe entera en tabletas y monitores, y en pantallas
  /// muy bajas (teléfono horizontal) no baja de 360 y se desplaza.
  static double artWidth(Size box) =>
      min(min(box.width, 720.0), max(box.height / aspect, min(box.width, 360.0)));

  @override
  State<IllustratedHomeCover> createState() => _IllustratedHomeCoverState();
}

class _IllustratedHomeCoverState extends State<IllustratedHomeCover> {
  bool _failed = false;

  @override
  Widget build(BuildContext context) {
    if (_failed) return widget.fallback(context);
    final learning = AppServices.of(context).learning;
    void open(String route) => Navigator.of(context).pushNamed(route);

    final art = Image.asset(
      IllustratedHomeCover.artwork,
      fit: BoxFit.fill, // la caja ya tiene la proporción exacta de la imagen
      filterQuality: FilterQuality.medium,
      gaplessPlayback: true,
      errorBuilder: (context, error, stackTrace) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) setState(() => _failed = true);
        });
        return const SizedBox.expand();
      },
    );

    return Scaffold(
      backgroundColor: const Color(0xFF8FD3FF),
      body: Stack(
        children: [
          // Fondo: la misma ilustración, ampliada y desenfocada, para rellenar
          // los lados en tabletas y monitores sin bandas de color plano.
          Positioned.fill(
            child: ExcludeSemantics(
              child: ImageFiltered(
                imageFilter: ImageFilter.blur(sigmaX: 28, sigmaY: 28),
                child: Image.asset(IllustratedHomeCover.artwork, fit: BoxFit.cover, errorBuilder: _empty),
              ),
            ),
          ),
          Positioned.fill(child: ColoredBox(color: Colors.white.withValues(alpha: 0.18))),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, box) {
                final width = IllustratedHomeCover.artWidth(box.biggest);
                final height = width * IllustratedHomeCover.aspect;
                return SingleChildScrollView(
                  child: ConstrainedBox(
                    constraints: BoxConstraints(minHeight: box.maxHeight),
                    child: Center(
                      child: _withQuickAccess(
                        box,
                        width,
                        height,
                        _Entrance(
                          child: SizedBox(
                            width: width,
                            height: height,
                            child: Stack(
                              children: [
                                Positioned.fill(
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(width < box.maxWidth ? 28 : 0),
                                    child: ExcludeSemantics(
                                      // En teléfonos muy alargados sobra alto: los bordes de
                                      // arriba y abajo se funden con el fondo, sin corte brusco.
                                      child: width >= box.maxWidth && height < box.maxHeight - 24
                                          ? ShaderMask(
                                              blendMode: BlendMode.dstIn,
                                              shaderCallback: (r) => const LinearGradient(
                                                begin: Alignment.topCenter,
                                                end: Alignment.bottomCenter,
                                                colors: [
                                                  Colors.transparent,
                                                  Colors.white,
                                                  Colors.white,
                                                  Colors.transparent,
                                                ],
                                                stops: [0, 0.035, 0.975, 1],
                                              ).createShader(r),
                                              child: art,
                                            )
                                          : art,
                                    ),
                                  ),
                                ),
                                // Logo y subtítulo: ya están dibujados; solo se anuncian.
                                _Zone.label(
                                  rect: const Rect.fromLTWH(.29, .03, .56, .15),
                                  label: 'Pequeños Artistas',
                                  header: true,
                                ),
                                _Zone.label(
                                  rect: const Rect.fromLTWH(.2, .19, .61, .04),
                                  label: 'Un mundo de colores, juegos y creatividad',
                                ),
                                // La estrella sonriente guarda la zona para adultos:
                                // un toque no hace nada; hay que mantenerla pulsada.
                                _Zone(
                                  rect: const Rect.fromLTWH(.15, .06, .145, .1),
                                  label: 'Zona para adultos',
                                  hint: 'Mantén pulsado para entrar',
                                  shape: _Shape.circle,
                                  onLongPress: widget.onAdultAccess,
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.25, .245, .5, .26),
                                  label: 'Un niño y una niña con pinceles y su perrito',
                                  hint: 'Toca para que te saluden',
                                  glow: false,
                                  onTap: () => AppServices.of(context).audio.sayOneOf(Phrases.welcome),
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.032, .016, .093, .062),
                                  label: 'Configuración',
                                  shape: _Shape.circle,
                                  route: true,
                                  onTap: () => open(AppRoutes.soundSettings),
                                ),
                                ListenableBuilder(
                                  listenable: learning,
                                  builder: (context, _) {
                                    final s = learning.settings;
                                    final on = s.musicOn && !s.muted;
                                    return _Zone(
                                      rect: const Rect.fromLTWH(.885, .016, .093, .062),
                                      label: on ? 'Música activada' : 'Música desactivada',
                                      hint: on
                                          ? 'Toca para apagar la música'
                                          : 'Toca para encender la música',
                                      shape: _Shape.circle,
                                      onTap: () => learning.updateSettings(
                                        s.copyWith(musicOn: !on, muted: on ? s.muted : false),
                                      ),
                                    );
                                  },
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.062, .522, .436, .163),
                                  label: 'Colorear',
                                  hint: '¡Dibuja y da vida!',
                                  route: true,
                                  onTap: () => open(AppRoutes.categories),
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.516, .522, .424, .163),
                                  label: 'Mini Juegos',
                                  hint: '¡Aprende jugando!',
                                  route: true,
                                  onTap: () => open(AppRoutes.miniGames),
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.062, .695, .436, .161),
                                  label: 'Actividades',
                                  hint: '¡Descubre y aprende!',
                                  route: true,
                                  onTap: () => open(AppRoutes.activities),
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.516, .695, .424, .161),
                                  label: 'Galería',
                                  hint: '¡Tus obras de arte!',
                                  route: true,
                                  onTap: () => open(AppRoutes.savedDrawings),
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.062, .882, .282, .072),
                                  label: 'Perfil',
                                  shape: _Shape.pill,
                                  route: true,
                                  onTap: () => open(AppRoutes.profile),
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.368, .882, .265, .072),
                                  label: 'Logros',
                                  shape: _Shape.pill,
                                  route: true,
                                  onTap: () => open(AppRoutes.rewards),
                                ),
                                _Zone(
                                  rect: const Rect.fromLTWH(.656, .882, .3, .072),
                                  label: 'Configuración',
                                  shape: _Shape.pill,
                                  route: true,
                                  onTap: () => open(AppRoutes.soundSettings),
                                ),
                                // «Aprendo a Hablar»: Lolo en el cielo, junto al arcoíris
                                // (una sección nueva que no está en la ilustración). Si
                                // caben los accesos grandes junto a la imagen, van allí.
                                if (!_hasQuickAccess(box, width, height))
                                  Positioned(
                                    left: width * .8,
                                    top: height * .14,
                                    width: width * .195,
                                    height: height * .125,
                                    child: _SpeechBadge(onTap: () => open(AppRoutes.speech)),
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  /// Accesos grandes a «Aprendo a Hablar» y «Necesito decir algo» en el espacio
  /// que sobra alrededor de la ilustración (sin tocar la imagen). Si no sobra
  /// espacio, queda la insignia de Lolo sobre la ilustración.
  static bool _below(BoxConstraints box, double height) =>
      box.maxHeight - height >= (_narrowBelow(box) ? 150 : 96);

  /// Debajo de la ilustración caben dos botones; si son estrechos, el dibujo
  /// va encima del texto y necesitan más alto.
  static bool _narrowBelow(BoxConstraints box) =>
      (box.maxWidth - 2 * 12 - 10) / 2 - 2 * 14 - 2 * 3 < AacShortcut.narrowWidth;
  static bool _beside(BoxConstraints box, double width) => box.maxWidth - width >= 2 * 200;
  static bool _hasQuickAccess(BoxConstraints box, double width, double height) =>
      _below(box, height) || _beside(box, width);

  Widget _withQuickAccess(BoxConstraints box, double width, double height, Widget art) {
    void open(String route) => Navigator.of(context).pushNamed(route);
    Widget button(String title, IconData icon, Color color, String route) =>
        AacShortcut(title: title, icon: icon, color: color, onTap: () => open(route));
    final talk = button(
      'Aprendo a Hablar',
      Icons.record_voice_over_rounded,
      const Color(0xFF2E9E57),
      AppRoutes.speech,
    );
    final say = button(
      'Necesito decir algo',
      Icons.campaign_rounded,
      const Color(0xFFEF6C57),
      AppRoutes.aacQuick,
    );
    if (_below(box, height)) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          art,
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            child: SizedBox(
              width: width,
              child: Row(
                children: [
                  Expanded(child: talk),
                  const SizedBox(width: 10),
                  Expanded(child: say),
                ],
              ),
            ),
          ),
        ],
      );
    }
    if (_beside(box, width)) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          art,
          const SizedBox(width: 16),
          SizedBox(
            width: 190,
            child: Column(mainAxisSize: MainAxisSize.min, children: [talk, const SizedBox(height: 12), say]),
          ),
        ],
      );
    }
    return art;
  }

  static Widget _empty(BuildContext context, Object error, StackTrace? stack) => const SizedBox();
}

/// Acceso a «Aprendo a Hablar»: Lolo dentro de un círculo con relieve y la
/// etiqueta «¡A hablar!». Se escala con la ilustración.
class _SpeechBadge extends StatelessWidget {
  const _SpeechBadge({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final action = guardRoute(context, withSound(context, SoundCue.tap, onTap));
    return Semantics(
      button: true,
      label: 'Aprendo a Hablar',
      hint: 'Palabras y frases con Lolo',
      excludeSemantics: true,
      onTap: action,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: Pressable(
          scale: 0.9,
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: action,
            child: LayoutBuilder(
              builder: (context, box) {
                final d = min(box.maxWidth, box.maxHeight * 0.78);
                return Column(
                  children: [
                    Container(
                      width: d,
                      height: d,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: const LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [Color(0xFFE9FFF0), Color(0xFFB5F0C8)],
                        ),
                        border: Border.all(color: Colors.white, width: max(2, d * 0.05)),
                        boxShadow: [
                          const BoxShadow(color: Color(0xFF7BCB95), offset: Offset(0, 3)),
                          BoxShadow(
                            color: const Color(0x33000000),
                            blurRadius: d * 0.15,
                            offset: Offset(0, d * 0.08),
                          ),
                        ],
                      ),
                      padding: EdgeInsets.all(d * 0.06),
                      child: const Lolo(waves: 3),
                    ),
                    Expanded(
                      child: FittedBox(
                        child: Container(
                          margin: const EdgeInsets.only(top: 2),
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFF43C46A), width: 2),
                          ),
                          child: const Text(
                            '¡A hablar!',
                            style: TextStyle(
                              fontFamily: 'Fredoka',
                              fontWeight: FontWeight.w700,
                              fontVariations: [FontVariation('wght', 700)],
                              color: Color(0xFF2E7D4F),
                            ),
                          ),
                        ),
                      ),
                    ),
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

/// Aparición suave de la ilustración al abrir la app.
class _Entrance extends StatelessWidget {
  const _Entrance({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (AppMotion.reduced(context)) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 550),
      curve: Curves.easeOutCubic,
      builder: (context, t, child) => Opacity(
        opacity: t,
        child: Transform.scale(scale: 0.96 + 0.04 * t, child: child),
      ),
      child: child,
    );
  }
}

enum _Shape { card, pill, circle }

/// Zona táctil transparente sobre un botón dibujado en la ilustración.
/// [rect] va en fracciones del ancho y el alto de la imagen. Al pulsar se
/// ilumina con un brillo blanco con la forma del botón y suena un clic.
class _Zone extends StatefulWidget {
  const _Zone({
    required this.rect,
    required this.label,
    this.hint,
    this.onTap,
    this.onLongPress,
    this.shape = _Shape.card,
    this.route = false,
    this.glow = true,
  }) : header = false;

  /// Solo para el lector de pantalla (textos que ya están en la imagen).
  const _Zone.label({required this.rect, required this.label, this.header = false})
    : hint = null,
      onTap = null,
      onLongPress = null,
      shape = _Shape.card,
      route = false,
      glow = false;

  final Rect rect;
  final String label;
  final String? hint;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final _Shape shape;

  /// Abre una pantalla: se evita abrir dos con un doble toque.
  final bool route;
  final bool glow;
  final bool header;

  @override
  State<_Zone> createState() => _ZoneState();
}

class _ZoneState extends State<_Zone> {
  bool _down = false;

  void _press(bool down) {
    if (_down != down) setState(() => _down = down);
  }

  @override
  Widget build(BuildContext context) {
    final w = widget;
    VoidCallback? tap;
    if (w.onTap != null) {
      tap = withSound(context, SoundCue.tap, w.onTap);
      if (w.route) tap = guardRoute(context, tap);
    }
    final interactive = tap != null || w.onLongPress != null;

    return Positioned.fill(
      child: LayoutBuilder(
        builder: (context, box) {
          final r = Rect.fromLTWH(
            box.maxWidth * w.rect.left,
            box.maxHeight * w.rect.top,
            box.maxWidth * w.rect.width,
            box.maxHeight * w.rect.height,
          );
          final radius = switch (w.shape) {
            _Shape.circle => r.shortestSide / 2,
            _Shape.pill => r.height / 2,
            _Shape.card => r.width * 0.1,
          };
          Widget zone = Semantics(
            container: true,
            button: interactive,
            header: w.header,
            label: w.label,
            hint: w.hint,
            excludeSemantics: true,
            onTap: tap,
            onLongPress: w.onLongPress,
            child: const SizedBox.expand(),
          );
          if (interactive) {
            zone = MouseRegion(
              cursor: SystemMouseCursors.click,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapDown: (_) => _press(true),
                onTapUp: (_) => _press(false),
                onTapCancel: () => _press(false),
                onTap: tap,
                onLongPress: w.onLongPress,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 120),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(radius),
                    color: Colors.white.withValues(alpha: _down && w.glow ? 0.28 : 0),
                    boxShadow: [
                      if (_down && w.glow)
                        BoxShadow(
                          color: Colors.white.withValues(alpha: 0.7),
                          blurRadius: 18,
                          spreadRadius: 2,
                        ),
                    ],
                  ),
                  child: zone,
                ),
              ),
            );
          }
          return Stack(
            children: [Positioned.fromRect(rect: r, child: zone)],
          );
        },
      ),
    );
  }
}
