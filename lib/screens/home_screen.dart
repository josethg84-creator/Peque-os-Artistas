import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../audio/phrases.dart';
import '../navigation/app_routes.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../widgets/adult_gate.dart';
import '../widgets/mascot.dart';
import '../widgets/motion/staggered_entrance.dart';
import 'home/home_art.dart';
import 'home/illustrated_home_cover.dart';
import 'home/home_widgets.dart';

/// Pantalla de inicio: logo, personajes y el menú principal (Colorear, Mini
/// juegos, Actividades y Galería), con Perfil, Logros y Configuración abajo.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  /// Ilustración profesional opcional de los personajes. Si se añade este
  /// archivo (y su carpeta en pubspec.yaml), sustituye a la versión vectorial.
  static const heroAsset = 'assets/images/home/personajes.png';

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Future<void> _openAdultZone() async {
    final navigator = Navigator.of(context);
    if (await showAdultGate(context)) {
      navigator.pushNamed(AppRoutes.adultZone, arguments: const AdultZoneArgs.verified());
    }
  }

  void _go(String route) => Navigator.of(context).pushNamed(route);

  @override
  Widget build(BuildContext context) {
    // La ilustración original es el inicio en todas las pantallas; el inicio
    // vectorial queda de reserva por si la imagen no se pudiera cargar.
    return IllustratedHomeCover(onAdultAccess: _openAdultZone, fallback: _vectorHome);
  }

  Widget _vectorHome(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFFF3E6),
      body: Stack(
        children: [
          const Positioned.fill(
            child: RepaintBoundary(child: CustomPaint(painter: SkyScenePainter())),
          ),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, box) {
                final wide = box.maxWidth > box.maxHeight && box.maxWidth >= 700;
                return wide ? _wide(box) : _portrait(box);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _topBar() => Padding(
    padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
    child: Row(
      children: [
        CornerButton(
          icon: Icons.settings_rounded,
          label: 'Configuración',
          colors: const [Color(0xFF7CC8FF), Color(0xFF3D8FE0)],
          onPressed: () => _go(AppRoutes.soundSettings),
        ),
        const Spacer(),
        _AdultAccessButton(onConfirmed: _openAdultZone),
        const SizedBox(width: 10),
        const _MusicButton(),
      ],
    ),
  );

  Widget _header(double titleSize) => Stack(
    clipBehavior: Clip.none,
    alignment: Alignment.center,
    children: [
      Padding(
        padding: EdgeInsets.symmetric(horizontal: titleSize * 0.9),
        child: RainbowTitle(size: titleSize),
      ),
      Positioned(
        left: 0,
        top: titleSize * 0.05,
        child: ExcludeSemantics(
          child: CustomPaint(size: Size.square(titleSize * 1.15), painter: const SmilingStarPainter()),
        ),
      ),
      Positioned(
        right: 0,
        top: titleSize * 0.3,
        child: ExcludeSemantics(
          child: CustomPaint(size: Size.square(titleSize * 1.2), painter: const TitleBrushPainter()),
        ),
      ),
      Positioned(
        left: titleSize * 1.4,
        top: -titleSize * 0.1,
        child: FloatingSparkle(size: titleSize * 0.32),
      ),
      Positioned(
        right: titleSize * 1.3,
        bottom: -titleSize * 0.05,
        child: FloatingSparkle(size: titleSize * 0.26, color: const Color(0xFFFF8FB8), delay: 0.4),
      ),
    ],
  );

  Widget _subtitle(double size) => Container(
    padding: EdgeInsets.symmetric(horizontal: size * 0.9, vertical: size * 0.35),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: 0.85),
      borderRadius: BorderRadius.circular(30),
      boxShadow: const [BoxShadow(color: Color(0x1F000000), blurRadius: 8, offset: Offset(0, 3))],
    ),
    child: Text(
      'Un mundo de colores, juegos y creatividad',
      textAlign: TextAlign.center,
      style: fredoka(size, weight: FontWeight.w600, color: const Color(0xFF7A4FD1)),
    ),
  );

  Widget _hero() => _Hero(onTap: () => unawaited(AppServices.of(context).audio.sayOneOf(Phrases.welcome)));

  Widget _board(double width) {
    final gap = width * 0.035;
    Widget card(String title, String subtitle, HomeIcon icon, Color color, String route) => Expanded(
      child: HomeMenuCard(
        title: title,
        subtitle: subtitle,
        icon: icon,
        color: color,
        onTap: () => _go(route),
      ),
    );
    return Container(
      padding: EdgeInsets.all(gap),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFFBE7C6), Color(0xFFF1D19F)],
        ),
        border: Border.all(color: const Color(0xFFFFF6E6), width: 3),
        boxShadow: const [
          BoxShadow(color: Color(0xFFD9B27A), offset: Offset(0, 6)),
          BoxShadow(color: Color(0x26000000), blurRadius: 16, offset: Offset(0, 10)),
        ],
      ),
      child: Column(
        children: [
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                card(
                  'Colorear',
                  '¡Dibuja y da vida!',
                  HomeIcon.palette,
                  const Color(0xFF8EC9FF),
                  AppRoutes.categories,
                ),
                SizedBox(width: gap),
                card(
                  'Mini Juegos',
                  '¡Aprende jugando!',
                  HomeIcon.puzzle,
                  const Color(0xFFFFA9CB),
                  AppRoutes.miniGames,
                ),
              ],
            ),
          ),
          SizedBox(height: gap * 1.3),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                card(
                  'Actividades',
                  '¡Descubre y aprende!',
                  HomeIcon.bookBulb,
                  const Color(0xFF92E2BC),
                  AppRoutes.activities,
                ),
                SizedBox(width: gap),
                card(
                  'Galería',
                  '¡Tus obras de arte!',
                  HomeIcon.frame,
                  const Color(0xFFC9AEFF),
                  AppRoutes.savedDrawings,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _bottomNav() => Row(
    children: [
      Expanded(
        flex: 3,
        child: BottomPillButton(
          label: 'Perfil',
          art: const Mascot(size: 38, waves: 0),
          onTap: () => _go(AppRoutes.profile),
        ),
      ),
      const SizedBox(width: 10),
      Expanded(
        flex: 3,
        child: BottomPillButton(
          label: 'Logros',
          art: const CustomPaint(painter: HomeIconPainter(HomeIcon.star)),
          onTap: () => _go(AppRoutes.rewards),
        ),
      ),
      const SizedBox(width: 10),
      Expanded(
        flex: 4,
        child: BottomPillButton(
          label: 'Configuración',
          art: const CustomPaint(painter: HomeIconPainter(HomeIcon.gear)),
          onTap: () => _go(AppRoutes.soundSettings),
        ),
      ),
    ],
  );

  Widget _portrait(BoxConstraints box) {
    final w = box.maxWidth;
    final content = min(w, 640.0);
    final titleSize = min(content * 0.125, 60.0);
    const navH = 72.0;
    // Lo fijo (barra superior, logo, subtítulo y barra inferior) va primero; el
    // tablero se encoge en pantallas bajas para que quepan los personajes.
    final fixed = 64 + titleSize * 1.95 + titleSize * 0.55 + 20 + navH + 24;
    final boardH = min((content - 32) * 0.86, max(250.0, box.maxHeight - fixed - 120));
    final heroH = (box.maxHeight - fixed - boardH).clamp(110.0, 330.0);
    final column = Column(
      children: [
        _topBar(),
        StaggeredEntrance(index: 0, child: _header(titleSize)),
        SizedBox(height: titleSize * 0.12),
        StaggeredEntrance(index: 1, child: _subtitle(max(13, titleSize * 0.3))),
        StaggeredEntrance(
          index: 2,
          child: SizedBox(height: heroH, width: content, child: _hero()),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: StaggeredEntrance(
            index: 3,
            child: SizedBox(height: boardH, child: _board(content - 32)),
          ),
        ),
        const SizedBox(height: 14),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
          child: StaggeredEntrance(index: 4, child: _bottomNav()),
        ),
      ],
    );
    return Center(
      child: SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: content),
          child: column,
        ),
      ),
    );
  }

  Widget _wide(BoxConstraints box) {
    final titleSize = min(box.maxHeight * 0.1, 64.0);
    return Column(
      children: [
        _topBar(),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Row(
              children: [
                Expanded(
                  flex: 5,
                  child: Column(
                    children: [
                      StaggeredEntrance(index: 0, child: _header(titleSize)),
                      SizedBox(height: titleSize * 0.1),
                      StaggeredEntrance(index: 1, child: _subtitle(max(13, titleSize * 0.3))),
                      Expanded(child: StaggeredEntrance(index: 2, child: _hero())),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  flex: 5,
                  child: Column(
                    children: [
                      Expanded(
                        child: LayoutBuilder(
                          builder: (context, c) => StaggeredEntrance(index: 3, child: _board(c.maxWidth)),
                        ),
                      ),
                      const SizedBox(height: 12),
                      StaggeredEntrance(index: 4, child: _bottomNav()),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// Personajes: ilustración profesional si existe; si no, la versión vectorial
/// original. Al tocarlos, saludan con la voz (si está activada).
class _Hero extends StatefulWidget {
  const _Hero({required this.onTap});

  final VoidCallback onTap;

  @override
  State<_Hero> createState() => _HeroState();
}

class _HeroState extends State<_Hero> {
  static Future<bool>? _hasAsset;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final bundle = DefaultAssetBundle.of(context);
    _hasAsset ??= AssetManifest.loadFromAssetBundle(bundle)
        .then((m) => m.listAssets().contains(HomeScreen.heroAsset))
        .catchError((Object _) => false);
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Un niño y una niña con pinceles y su perrito',
      hint: 'Toca para que te saluden',
      excludeSemantics: true,
      onTap: widget.onTap,
      child: GestureDetector(
        onTap: widget.onTap,
        child: FutureBuilder<bool>(
          future: _hasAsset,
          builder: (context, snapshot) {
            if (snapshot.data == true) {
              return Image.asset(HomeScreen.heroAsset, fit: BoxFit.contain);
            }
            return TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.85, end: 1),
              duration: const Duration(milliseconds: 600),
              curve: Curves.easeOutBack,
              builder: (context, s, child) =>
                  Transform.scale(scale: s, alignment: Alignment.bottomCenter, child: child),
              child: const CustomPaint(size: Size.infinite, painter: CharactersPainter()),
            );
          },
        ),
      ),
    );
  }
}

/// Música de fondo: un toque la enciende o la apaga.
class _MusicButton extends StatelessWidget {
  const _MusicButton();

  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;
    return ListenableBuilder(
      listenable: learning,
      builder: (context, _) {
        final s = learning.settings;
        final on = s.musicOn && !s.muted;
        return CornerButton(
          icon: on ? Icons.music_note_rounded : Icons.music_off_rounded,
          label: on ? 'Música activada' : 'Música desactivada',
          colors: on
              ? const [Color(0xFFFF9CC4), Color(0xFFE85C93)]
              : const [Color(0xFFC9C5D6), Color(0xFF8E89A3)],
          onPressed: () => learning.updateSettings(s.copyWith(musicOn: !on, muted: on ? s.muted : false)),
        );
      },
    );
  }
}

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
