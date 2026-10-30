import 'package:flutter/material.dart';

import '../learning/rewards.dart';
import '../learning/screens/learning_hub_screen.dart';
import '../learning/widgets/reward_sticker.dart';
import '../models/drawing_catalog.dart';
import '../navigation/app_routes.dart';
import '../persistence/creation.dart';
import '../persistence/creation_store.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/catalog_builder.dart';
import '../widgets/creation_thumbnail.dart';
import '../widgets/friendly_date.dart';
import '../widgets/kid_scaffold.dart';
import '../widgets/mascot.dart';
import '../widgets/motion/delayed_loading.dart';

/// «Perfil»: el panel del niño con su progreso, sus logros y sus últimos
/// dibujos. Solo lee lo que ya guarda la app en el dispositivo.
class ChildPanelScreen extends StatefulWidget {
  const ChildPanelScreen({super.key});

  @override
  State<ChildPanelScreen> createState() => _ChildPanelScreenState();
}

class _ChildPanelScreenState extends State<ChildPanelScreen> {
  Future<CreationReport>? _report;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _report ??= AppServices.of(context).creations.loadAll()..ignore();
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: '¡Hola, artista!',
      titleIcon: Icons.face_rounded,
      accent: AppColors.grape,
      backLabel: 'Volver al inicio',
      body: CatalogBuilder(
        builder: (context, catalog) => FutureBuilder<CreationReport>(
          future: _report,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const DelayedLoading(message: 'Preparando tu panel…', color: AppColors.grape);
            }
            final creations = snapshot.data?.creations ?? const <Creation>[];
            return ListenableBuilder(
              listenable: AppServices.of(context).learning,
              builder: (context, _) => _content(context, catalog, creations),
            );
          },
        ),
      ),
    );
  }

  Widget _content(BuildContext context, DrawingCatalog catalog, List<Creation> creations) {
    final progress = AppServices.of(context).learning.progress;
    final earned = [
      for (final r in rewards)
        if (progress.rewards.containsKey(r.id)) r,
    ];
    final finished = {
      for (final c in creations)
        if (c.status == CreationStatus.completed && catalog.byId(c.drawingId) != null) c.drawingId,
    };
    int played(HubGroup g) => g.members.where((id) => progress.game(id).sessions > 0).length;
    final next = rewards.where((r) => !progress.rewards.containsKey(r.id)).firstOrNull;
    final text = Theme.of(context).textTheme;

    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppDimens.pagePadding,
        0,
        AppDimens.pagePadding,
        AppDimens.pagePadding,
      ),
      children: [
        const MascotBubble(text: '¡Qué bien lo estás haciendo!', size: 56, waves: 1),
        const SizedBox(height: 6),
        Text(
          'Aquí puedes ver tu progreso y todo lo que has creado.',
          style: text.titleMedium?.copyWith(color: AppColors.inkSoft),
        ),
        const SizedBox(height: AppDimens.gap),
        Row(
          children: [
            Expanded(
              child: _Stat(
                icon: Icons.star_rounded,
                color: AppColors.sun,
                value: progress.stars,
                label: 'Estrellas',
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _Stat(
                icon: Icons.emoji_events_rounded,
                color: AppColors.coral,
                value: earned.length,
                label: 'Logros',
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _Stat(
                icon: Icons.photo_library_rounded,
                color: AppColors.grape,
                value: creations.length,
                label: 'Dibujos',
              ),
            ),
          ],
        ),
        const SizedBox(height: AppDimens.gap),
        _Section(
          icon: Icons.trending_up_rounded,
          title: 'Tu progreso',
          child: Column(
            children: [
              _ProgressRow(
                icon: Icons.palette_rounded,
                color: AppColors.sky,
                label: 'Dibujos terminados',
                done: finished.length,
                total: catalog.drawings.length,
              ),
              _ProgressRow(
                icon: Icons.extension_rounded,
                color: AppColors.berry,
                label: 'Mini juegos probados',
                done: played(HubGroup.games),
                total: HubGroup.games.members.length,
              ),
              _ProgressRow(
                icon: Icons.lightbulb_rounded,
                color: AppColors.leaf,
                label: 'Actividades probadas',
                done: played(HubGroup.activities),
                total: HubGroup.activities.members.length,
              ),
            ],
          ),
        ),
        _Section(
          icon: Icons.emoji_events_rounded,
          title: 'Tus logros',
          action: TextButton(
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.rewards),
            child: const Text('Ver todos'),
          ),
          child: earned.isEmpty
              ? Text('Juega a cualquier juego para ganar tu primera pegatina.', style: text.bodyLarge)
              : SizedBox(
                  height: 130,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      for (final r in earned)
                        Padding(
                          padding: const EdgeInsets.only(right: 10),
                          child: SizedBox(width: 96, child: RewardSticker(reward: r, earned: true, size: 64)),
                        ),
                    ],
                  ),
                ),
        ),
        _Section(
          icon: Icons.photo_library_rounded,
          title: 'Tus dibujos recientes',
          action: TextButton(
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.savedDrawings),
            child: const Text('Ver todos'),
          ),
          child: creations.isEmpty
              ? Text('Aún no hay dibujos. ¡Pinta el primero!', style: text.bodyLarge)
              : SizedBox(
                  height: 150,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      for (final c in creations.take(8))
                        if (catalog.byId(c.drawingId) case final drawing?)
                          Padding(
                            padding: const EdgeInsets.only(right: 10),
                            child: Semantics(
                              button: true,
                              label: '${drawing.name}. ${friendlyDate(c.updatedAt)}',
                              excludeSemantics: true,
                              onTap: () => _open(context, c),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
                                onTap: () => _open(context, c),
                                child: Container(
                                  width: 110,
                                  padding: const EdgeInsets.all(6),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(AppDimens.radiusMedium),
                                    border: Border.all(
                                      color: AppColors.grape.withValues(alpha: 0.3),
                                      width: 2,
                                    ),
                                  ),
                                  child: Column(
                                    children: [
                                      Expanded(
                                        child: CreationThumbnail(drawing: drawing, creation: c),
                                      ),
                                      Text(
                                        drawing.name,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: text.labelLarge,
                                      ),
                                      Text(friendlyDate(c.updatedAt), style: text.bodySmall),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                    ],
                  ),
                ),
        ),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFFFFE3EC), Color(0xFFFFF3D6)]),
            borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          ),
          child: Row(
            children: [
              const Icon(Icons.card_giftcard_rounded, color: AppColors.berry, size: 48),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('¡Sigue jugando!', style: text.titleLarge?.copyWith(color: AppColors.berry)),
                    Text(
                      next == null
                          ? '¡Tienes todas las pegatinas! Sigue creando dibujos.'
                          : 'Próxima pegatina: «${next.title}». ${next.howTo}.',
                      style: text.bodyLarge,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _open(BuildContext context, Creation c) =>
      Navigator.of(context)
          .pushNamed(AppRoutes.coloring, arguments: ColoringArgs(c.drawingId, creationId: c.id));
}

class _Stat extends StatelessWidget {
  const _Stat({required this.icon, required this.color, required this.value, required this.label});

  final IconData icon;
  final Color color;
  final int value;
  final String label;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: '$label: $value',
    excludeSemantics: true,
    child: Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
        boxShadow: const [BoxShadow(color: Color(0x1A000000), blurRadius: 8, offset: Offset(0, 3))],
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 36),
          FittedBox(child: Text('$value', style: Theme.of(context).textTheme.headlineMedium)),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelLarge,
          ),
        ],
      ),
    ),
  );
}

class _Section extends StatelessWidget {
  const _Section({required this.icon, required this.title, required this.child, this.action});

  final IconData icon;
  final String title;
  final Widget child;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: AppDimens.gap),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
      boxShadow: const [BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 3))],
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: AppColors.grape),
            const SizedBox(width: 8),
            Expanded(
              child: Semantics(
                header: true,
                child: Text(title, style: Theme.of(context).textTheme.titleLarge),
              ),
            ),
            ?action,
          ],
        ),
        const SizedBox(height: 8),
        child,
      ],
    ),
  );
}

class _ProgressRow extends StatelessWidget {
  const _ProgressRow({
    required this.icon,
    required this.color,
    required this.label,
    required this.done,
    required this.total,
  });

  final IconData icon;
  final Color color;
  final String label;
  final int done;
  final int total;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: '$label: $done de $total',
    excludeSemantics: true,
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, color: color, size: 30),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: total == 0 ? 0 : done / total,
                    minHeight: 12,
                    color: color,
                    backgroundColor: color.withValues(alpha: 0.18),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text('$done/$total', style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    ),
  );
}
