import 'package:flutter/material.dart';

import '../navigation/app_routes.dart';
import '../services/app_services.dart';
import '../widgets/adult_gate.dart';

/// Inicio infantil inspirado en la referencia pastel de Pequeños Artistas.
/// Los controles siguen usando los servicios y rutas originales.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  static const _blue = Color(0xFFB8E9FF);
  static const _pink = Color(0xFFFFC3E3);
  static const _mint = Color(0xFFC5F7C9);
  static const _lilac = Color(0xFFE2CBFF);

  Future<void> _openAdultZone(BuildContext context) async {
    final navigator = Navigator.of(context);
    if (await showAdultGate(context)) {
      navigator.pushNamed(AppRoutes.adultZone, arguments: const AdultZoneArgs.verified());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: LayoutBuilder(builder: (context, bounds) {
        final landscape = bounds.maxWidth > 700 && bounds.maxWidth > bounds.maxHeight;
        return Container(
          decoration: const BoxDecoration(gradient: LinearGradient(
            begin: Alignment.topCenter, end: Alignment.bottomCenter,
            colors: [Color(0xFF75D4FF), Color(0xFFFFDFF4), Color(0xFFFFE1A2)],
          )),
          child: Stack(children: [
            const Positioned(top: 110, right: -35, child: Icon(Icons.cloud_rounded, color: Color(0xCCFFFFFF), size: 165)),
            const Positioned(top: 200, left: -40, child: Icon(Icons.cloud_rounded, color: Color(0xAAFFFFFF), size: 125)),
            const Positioned(top: 230, right: 12, child: Icon(Icons.auto_awesome_rounded, color: Color(0xFFFFF5A1), size: 55)),
            SafeArea(child: Center(child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(15, 75, 15, 22),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Column(children: [
                  _Hero(compact: landscape),
                  const SizedBox(height: 24),
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisSpacing: 14,
                    mainAxisSpacing: 14,
                    childAspectRatio: landscape ? 2.1 : 1.3,
                    children: [
                      _MenuCard(title: 'Colorear', subtitle: '¡Dibuja y da vida!', icon: Icons.palette_rounded,
                        background: _blue, ink: const Color(0xFF0756A5),
                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.categories)),
                      _MenuCard(title: 'Mini Juegos', subtitle: '¡Aprende jugando!', icon: Icons.extension_rounded,
                        background: _pink, ink: const Color(0xFF7A1779),
                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.activities)),
                      _MenuCard(title: 'Actividades', subtitle: '¡Descubre y aprende!', icon: Icons.lightbulb_rounded,
                        background: _mint, ink: const Color(0xFF136552),
                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.activities)),
                      _MenuCard(title: 'Galería', subtitle: '¡Tus obras de arte!', icon: Icons.photo_library_rounded,
                        background: _lilac, ink: const Color(0xFF49228E),
                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.savedDrawings)),
                    ],
                  ),
                  const SizedBox(height: 25),
                  Row(children: [
                    Expanded(child: _BottomAction(label: 'Perfil', icon: Icons.face_rounded,
                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.kidProgress))),
                    const SizedBox(width: 8),
                    Expanded(child: _BottomAction(label: 'Logros', icon: Icons.star_rounded,
                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.rewards))),
                    const SizedBox(width: 8),
                    Expanded(child: _BottomAction(label: 'Configuración', icon: Icons.settings_rounded,
                        onTap: () => Navigator.of(context).pushNamed(AppRoutes.soundSettings))),
                  ]),
                ]),
              ),
            ))),
            Positioned(top: 8, left: 12, child: SafeArea(child: _TopControl(
              icon: Icons.settings_rounded, tooltip: 'Configuración de sonido',
              onTap: () => Navigator.of(context).pushNamed(AppRoutes.soundSettings)))),
            Positioned(top: 8, right: 12, child: SafeArea(child: Row(mainAxisSize: MainAxisSize.min, children: [
              _SoundButton(),
              const SizedBox(width: 8),
              _TopControl(icon: Icons.lock_rounded, tooltip: 'Adultos: mantener pulsado',
                onLongPress: () => _openAdultZone(context)),
            ]))),
          ]),
        );
      }),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.compact});
  final bool compact;
  @override
  Widget build(BuildContext context) => Column(children: [
    Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
      decoration: BoxDecoration(color: const Color(0xF2FFFFFF), borderRadius: BorderRadius.circular(45),
        boxShadow: const [BoxShadow(color: Color(0x227B4AC0), blurRadius: 19, offset: Offset(0, 8))]),
      child: Column(children: [
        const Icon(Icons.star_rounded, size: 53, color: Color(0xFFFFC82D)),
        FittedBox(fit: BoxFit.scaleDown, child: Text('Pequeños', style: TextStyle(
          fontSize: compact ? 40 : 49, fontWeight: FontWeight.w900, color: const Color(0xFF1976D2),
          shadows: const [Shadow(color: Color(0x663984E8), offset: Offset(2, 4), blurRadius: 4)]))),
        FittedBox(fit: BoxFit.scaleDown, child: Text('Artistas 🎨', style: TextStyle(
          fontSize: compact ? 42 : 52, fontWeight: FontWeight.w900, color: const Color(0xFFFF4081),
          shadows: const [Shadow(color: Color(0x44C12865), offset: Offset(2, 4), blurRadius: 4)]))),
      ]),
    ),
    const SizedBox(height: 12),
    Container(padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 18),
      decoration: BoxDecoration(color: const Color(0xFFFFE9F6), borderRadius: BorderRadius.circular(35)),
      child: const Text('Un mundo de colores, juegos y creatividad', textAlign: TextAlign.center,
        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Color(0xFFC32875)))),
    SizedBox(height: compact ? 12 : 24),
    Container(height: compact ? 105 : 168, width: double.infinity,
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xAAFFFFFF), Color(0x88FFEDFF)]),
        borderRadius: BorderRadius.circular(90)),
      child: const Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
        _Character(icon: Icons.face_rounded, color: Color(0xFF46B9FF), label: '¡Vamos!'),
        _Character(icon: Icons.pets_rounded, color: Color(0xFFFFBB60), label: '¡Guau!'),
        _Character(icon: Icons.face_3_rounded, color: Color(0xFFFF8DC4), label: '¡A pintar!'),
      ]),
    ),
  ]);
}

class _Character extends StatelessWidget {
  const _Character({required this.icon, required this.color, required this.label});
  final IconData icon;
  final Color color;
  final String label;
  @override
  Widget build(BuildContext context) => Flexible(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
    Icon(icon, size: 75, color: color, shadows: const [Shadow(color: Colors.white, blurRadius: 7)]),
    Text(label, style: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF6A397E))),
  ]));
}

class _MenuCard extends StatelessWidget {
  const _MenuCard({required this.title, required this.subtitle, required this.icon,
    required this.background, required this.ink, required this.onTap});
  final String title, subtitle;
  final IconData icon;
  final Color background, ink;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Material(color: Colors.transparent, child: InkWell(
    borderRadius: BorderRadius.circular(28), onTap: onTap,
    child: Ink(decoration: BoxDecoration(
      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight,
        colors: [background.withValues(alpha: .85), background]),
      borderRadius: BorderRadius.circular(28),
      border: Border.all(color: const Color(0xE6FFFFFF), width: 4),
      boxShadow: const [BoxShadow(color: Color(0x33835C69), blurRadius: 12, offset: Offset(0, 6))]),
      child: Padding(padding: const EdgeInsets.all(8), child: Column(
        mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, color: ink, size: 50),
          const SizedBox(height: 6),
          FittedBox(fit: BoxFit.scaleDown, child: Text(title, style: TextStyle(fontSize: 25, fontWeight: FontWeight.w900, color: ink))),
          FittedBox(fit: BoxFit.scaleDown, child: Text(subtitle, style: TextStyle(fontSize: 13, color: ink, fontWeight: FontWeight.w600))),
        ])),
    ),
  ));
}

class _BottomAction extends StatelessWidget {
  const _BottomAction({required this.label, required this.icon, required this.onTap});
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => Material(color: Colors.white, borderRadius: BorderRadius.circular(28),
    elevation: 3, child: InkWell(onTap: onTap, borderRadius: BorderRadius.circular(28),
      child: Padding(padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 4),
        child: Column(children: [Icon(icon, color: const Color(0xFF278FCD), size: 29),
          FittedBox(fit: BoxFit.scaleDown, child: Text(label, style: const TextStyle(
            color: Color(0xFF164B8D), fontSize: 15, fontWeight: FontWeight.w900)))]))));
}

class _TopControl extends StatelessWidget {
  const _TopControl({required this.icon, required this.tooltip, this.onTap, this.onLongPress});
  final IconData icon;
  final String tooltip;
  final VoidCallback? onTap, onLongPress;
  @override
  Widget build(BuildContext context) => Tooltip(message: tooltip, child: Material(
    color: const Color(0xFFE8F6FF), shape: const CircleBorder(), elevation: 4,
    child: InkWell(customBorder: const CircleBorder(), onTap: onTap, onLongPress: onLongPress,
      child: Padding(padding: const EdgeInsets.all(12),
        child: Icon(icon, color: const Color(0xFF168ED1), size: 25)))));
}

class _SoundButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;
    return ListenableBuilder(listenable: learning, builder: (context, _) {
      final enabled = !learning.settings.muted;
      return _TopControl(icon: enabled ? Icons.music_note_rounded : Icons.music_off_rounded,
        tooltip: enabled ? 'Silenciar' : 'Activar sonido',
        onTap: () => learning.updateSettings(learning.settings.copyWith(muted: enabled)));
    });
  }
}
