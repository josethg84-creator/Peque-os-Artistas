import 'package:flutter/material.dart';

import '../navigation/app_routes.dart';
import '../learning/learning_level.dart';
import '../services/app_services.dart';
import '../widgets/catalog_builder.dart';

/// Panel infantil de progreso. Los datos proceden del almacenamiento local.
class KidProgressScreen extends StatelessWidget {
  const KidProgressScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final learning = AppServices.of(context).learning;
    return Scaffold(
      backgroundColor: const Color(0xFFFFF2FA),
      appBar: AppBar(
        backgroundColor: const Color(0xFFFFF2FA),
        title: const Text('¡Hola, artista! 🌟', style: TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF8C339D))),
      ),
      body: ListenableBuilder(
        listenable: learning,
        builder: (context, _) => CatalogBuilder(
          builder: (context, catalog) => LayoutBuilder(
            builder: (context, box) => ListView(
              padding: const EdgeInsets.all(18),
              children: [
                const Text('¡Qué bien lo estás haciendo!', textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 23, color: Color(0xFF9A398E), fontWeight: FontWeight.w900)),
                const SizedBox(height: 18),
                Wrap(spacing: 12, runSpacing: 12, alignment: WrapAlignment.center, children: [
                  _Stat(icon: Icons.star_rounded, label: 'Estrellas', count: learning.progress.stars, color: const Color(0xFFFFD56C)),
                  _Stat(icon: Icons.emoji_events_rounded, label: 'Logros', count: learning.progress.rewards.length, color: const Color(0xFFFFB9DC)),
                  _Stat(icon: Icons.brush_rounded, label: 'Dibujos disponibles', count: catalog.drawings.length, color: const Color(0xFFB9DEFF)),
                ]),
                const SizedBox(height: 20),
                _Panel(
                  title: '🎨 Tus aventuras',
                  child: Column(children: [
                    for (final game in GameId.values)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 7),
                        child: Row(children: [
                          const Icon(Icons.extension_rounded, color: Color(0xFF7C70DE)),
                          const SizedBox(width: 10),
                          Expanded(child: Text(game.title, style: const TextStyle(fontWeight: FontWeight.w700))),
                          Text('${learning.progress.game(game).sessions} partidas', style: const TextStyle(color: Color(0xFF7B638A))),
                        ]),
                      ),
                  ]),
                ),
                const SizedBox(height: 16),
                _Panel(title: '🏆 Tus premios', child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${learning.progress.rewards.length} recompensas conseguidas', style: const TextStyle(fontSize: 17)),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: () => Navigator.of(context).pushNamed(AppRoutes.rewards),
                      icon: const Icon(Icons.stars_rounded),
                      label: const Text('Ver mis premios'),
                    ),
                  ],
                )),
                const SizedBox(height: 16),
                _Panel(title: '✨ ¡Sigue jugando!', child: Column(children: [
                  const Text('Descubre nuevos dibujos y gana más estrellas.'),
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    onPressed: () => Navigator.of(context).pushNamed(AppRoutes.activities),
                    icon: const Icon(Icons.extension_rounded),
                    label: const Text('Jugar ahora'),
                  ),
                ])),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.icon, required this.label, required this.count, required this.color});
  final IconData icon;
  final String label;
  final int count;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    width: 145,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24),
      boxShadow: [BoxShadow(color: color.withValues(alpha: .45), blurRadius: 12, offset: const Offset(0, 5))]),
    child: Column(children: [
      Icon(icon, color: color, size: 40),
      Text('$count', style: const TextStyle(fontSize: 29, fontWeight: FontWeight.w900, color: Color(0xFF7E398C))),
      Text(label, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700)),
    ]),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child});
  final String title;
  final Widget child;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(17),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(25),
      boxShadow: const [BoxShadow(color: Color(0x19B78CCF), blurRadius: 16, offset: Offset(0, 6))]),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900, color: Color(0xFF5A3B96))),
      const SizedBox(height: 12), child,
    ]),
  );
}
