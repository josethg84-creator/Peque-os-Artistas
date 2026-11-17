import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../dictation.dart';
import '../reading_activities.dart';
import '../reading_progress.dart';
import '../widgets/reading_widgets.dart';

/// Partida de dictados: nivel y modo de respuesta.
class DictationArgs {
  const DictationArgs({required this.level, required this.mode});
  final int level;
  final DictationMode mode;
}

/// Carga el catálogo de dictados.
class DictationCatalogBuilder extends StatefulWidget {
  const DictationCatalogBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, DictationCatalog catalog) builder;

  @override
  State<DictationCatalogBuilder> createState() => _DictationCatalogBuilderState();
}

class _DictationCatalogBuilderState extends State<DictationCatalogBuilder> {
  Future<DictationCatalog>? _future;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _future ??= DictationCatalog.load(DefaultAssetBundle.of(context));
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<DictationCatalog>(
      future: _future,
      builder: (context, snapshot) {
        final catalog = snapshot.data;
        if (catalog != null) return widget.builder(context, catalog);
        if (snapshot.hasError) return const Center(child: Text('No pudimos abrir los dictados.'));
        return const Center(child: CircularProgressIndicator());
      },
    );
  }
}

/// Modos de respuesta de cada nivel: en sílabas y palabras, tarjetas o
/// teclado; en oraciones, ordenar o teclado. El teclado nunca es obligatorio.
List<DictationMode> modesForLevel(int level) => level == 3
    ? const [DictationMode.order, DictationMode.keyboard]
    : const [DictationMode.cards, DictationMode.keyboard];

bool dictationLevelOpen(DictationCatalog catalog, ReadingController progress, int level) =>
    progress.dictationLevelOpen(level, (l) => catalog.ofLevel(l).map((d) => d.id));

/// Pantalla D · «Escucho y escribo»: elegir nivel y cómo responder.
class ReadingDictationScreen extends StatefulWidget {
  const ReadingDictationScreen({super.key});

  static const title = 'Escucho y escribo';
  static const color = Color(0xFF3DBE8B);

  @override
  State<ReadingDictationScreen> createState() => _ReadingDictationScreenState();
}

class _ReadingDictationScreenState extends State<ReadingDictationScreen> {
  int _level = 1;
  static const color = ReadingDictationScreen.color;

  static const _levelIcons = [Icons.abc_rounded, Icons.spellcheck_rounded, Icons.notes_rounded];

  @override
  Widget build(BuildContext context) {
    final progress = AppServices.of(context).reading;
    return KidScaffold(
      title: ReadingDictationScreen.title,
      titleIcon: ReadingActivities.dictation.icon,
      accent: color,
      trailing: const ReadingHomeButton(),
      body: DictationCatalogBuilder(
        builder: (context, catalog) => ListenableBuilder(
          listenable: progress,
          builder: (context, _) {
            final records = progress.progress.dictations;
            final ids = catalog.dictations.map((d) => d.id).toSet();
            final done = records.keys.where(ids.contains).length;
            final correct = records.entries.where((e) => ids.contains(e.key) && e.value.correct).length;
            final alone = records.entries.where((e) => ids.contains(e.key) && e.value.independent).length;
            final open = dictationLevelOpen(catalog, progress, _level);
            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                AppDimens.pagePadding,
                0,
                AppDimens.pagePadding,
                AppDimens.pagePadding,
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 900),
                  child: Column(
                    children: [
                      const ReadingLolo(text: 'Escucha con atención y escribe lo que oyes.'),
                      const SizedBox(height: 12),
                      ReadingProgressBar(
                        done: correct,
                        total: catalog.dictations.length,
                        label: 'Dictados acertados',
                        color: color,
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 10,
                        runSpacing: 8,
                        children: [
                          _Stat(icon: Icons.edit_note_rounded, text: 'Hechos: $done'),
                          _Stat(icon: Icons.star_rounded, text: 'Sin pistas: $alone'),
                        ],
                      ),
                      const SizedBox(height: 18),
                      Text('Elige un nivel', style: fredoka(22, color: AppColors.ink)),
                      const SizedBox(height: 10),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          for (final level in DictationCatalog.levels)
                            _LevelCard(
                              level: level,
                              icon: _levelIcons[level - 1],
                              name: catalog.levelNames[level] ?? '',
                              selected: level == _level,
                              unlocked: dictationLevelOpen(catalog, progress, level),
                              done: progress.dictationsCorrect(catalog.ofLevel(level).map((d) => d.id)),
                              total: catalog.ofLevel(level).length,
                              onTap: () => setState(() => _level = level),
                            ),
                        ],
                      ),
                      const SizedBox(height: 22),
                      Text('Elige cómo responder', style: fredoka(22, color: AppColors.ink)),
                      const SizedBox(height: 10),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          for (final mode in modesForLevel(_level))
                            SizedBox(
                              width: 270,
                              child: BigActionButton(
                                label: mode.title,
                                icon: switch (mode) {
                                  DictationMode.cards => Icons.touch_app_rounded,
                                  DictationMode.order => Icons.sort_rounded,
                                  DictationMode.keyboard => Icons.keyboard_rounded,
                                },
                                color: mode == DictationMode.keyboard ? AppColors.grape : AppColors.sky,
                                onPressed: open
                                    ? () => Navigator.of(context).pushNamed(
                                        AppRoutes.readingDictationGame,
                                        arguments: DictationArgs(level: _level, mode: mode),
                                      )
                                    : null,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Si todavía no conoces bien las letras, usa las tarjetas.',
                        style: Theme.of(context).textTheme.bodyMedium,
                        textAlign: TextAlign.center,
                      ),
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

class _Stat extends StatelessWidget {
  const _Stat({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
    decoration: BoxDecoration(color: const Color(0xFFE6F7EF), borderRadius: BorderRadius.circular(16)),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 20, color: ReadingDictationScreen.color),
        const SizedBox(width: 6),
        Flexible(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
      ],
    ),
  );
}

class _LevelCard extends StatelessWidget {
  const _LevelCard({
    required this.level,
    required this.icon,
    required this.name,
    required this.selected,
    required this.unlocked,
    required this.done,
    required this.total,
    required this.onTap,
  });

  final int level;
  final IconData icon;
  final String name;
  final bool selected;
  final bool unlocked;
  final int done;
  final int total;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    const color = ReadingDictationScreen.color;
    final label = unlocked
        ? 'Nivel $level: $name. $done de $total acertados.'
        : 'Nivel $level: $name. Se abre al acertar ${ReadingController.unlockAfter} dictados del nivel ${level - 1}.';
    return Semantics(
      button: true,
      selected: selected,
      enabled: unlocked,
      label: label,
      excludeSemantics: true,
      onTap: unlocked ? onTap : null,
      child: GestureDetector(
        onTap: unlocked ? onTap : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 250,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: !unlocked
                ? const Color(0xFFF1EEF8)
                : selected
                ? Color.lerp(color, Colors.white, 0.7)
                : Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: unlocked ? color : const Color(0xFFD1C4E9), width: selected ? 4 : 2),
          ),
          child: Row(
            children: [
              Icon(
                unlocked ? (selected ? Icons.check_circle_rounded : icon) : Icons.lock_rounded,
                color: unlocked ? color : AppColors.inkSoft,
                size: 34,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Nivel $level', style: fredoka(20, color: AppColors.ink)),
                    Text(name, style: Theme.of(context).textTheme.bodyMedium),
                    Text(
                      unlocked
                          ? '$done de $total'
                          : 'Acierta ${ReadingController.unlockAfter} del nivel ${level - 1}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
