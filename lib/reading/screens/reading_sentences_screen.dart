import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../reading_activities.dart';
import '../reading_progress.dart';
import '../sentences.dart';
import '../widgets/reading_widgets.dart';

/// Actividades con oraciones.
enum SentenceActivity {
  read('Leer oraciones', Icons.menu_book_rounded),
  question('¿Qué entendiste?', Icons.quiz_rounded),
  order('Ordena la oración', Icons.sort_rounded),
  listen('Escucha y elige', Icons.hearing_rounded);

  const SentenceActivity(this.title, this.icon);
  final String title;
  final IconData icon;

  /// Modo con el que se guarda en el progreso.
  String get mode => switch (this) {
    read => 'leer',
    question => ReadingController.sentenceQuestionMode,
    order => ReadingController.sentenceOrderMode,
    listen => ReadingController.sentenceListenMode,
  };

  String get instruction => switch (this) {
    read => 'Escucha la oración, sigue cada palabra y toca las que quieras oír.',
    question => 'Lee la oración y elige la respuesta.',
    order => 'Ordena las palabras para formar la oración.',
    listen => 'Escucha la oración y elige su dibujo.',
  };
}

/// Lector: nivel y oración por la que empezar.
class SentenceReaderArgs {
  const SentenceReaderArgs({required this.level, this.index = 0});
  final int level;
  final int index;
}

/// Juegos con oraciones: un nivel, o una sola oración ([sentenceId]).
class SentenceGameArgs {
  const SentenceGameArgs({required this.activity, this.level = 1, this.sentenceId});
  final SentenceActivity activity;
  final int level;
  final String? sentenceId;
}

/// Carga el catálogo de oraciones.
class SentenceCatalogBuilder extends StatefulWidget {
  const SentenceCatalogBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, SentenceCatalog content) builder;

  @override
  State<SentenceCatalogBuilder> createState() => _SentenceCatalogBuilderState();
}

class _SentenceCatalogBuilderState extends State<SentenceCatalogBuilder> {
  Future<SentenceCatalog>? _future;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _future ??= SentenceCatalog.load(DefaultAssetBundle.of(context));
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<SentenceCatalog>(
      future: _future,
      builder: (context, snapshot) {
        final content = snapshot.data;
        if (content != null) return widget.builder(context, content);
        if (snapshot.hasError) return const Center(child: Text('No pudimos abrir las oraciones.'));
        return const Center(child: CircularProgressIndicator());
      },
    );
  }
}

/// Un nivel de oraciones está abierto (el 1 siempre; los demás al resolver
/// [ReadingController.unlockAfter] preguntas del anterior).
bool sentenceLevelOpen(SentenceCatalog content, ReadingController progress, int level) =>
    progress.sentenceLevelOpen(level, (l) => content.ofLevel(l).map((s) => s.id));

/// Pantalla C · «Leo mis primeras oraciones»: elegir nivel y actividad, con el
/// progreso guardado.
class ReadingSentencesScreen extends StatefulWidget {
  const ReadingSentencesScreen({super.key});

  static const title = 'Leo mis primeras oraciones';
  static const color = Color(0xFF8E6BE0);

  @override
  State<ReadingSentencesScreen> createState() => _ReadingSentencesScreenState();
}

class _ReadingSentencesScreenState extends State<ReadingSentencesScreen> {
  int _level = 1;

  static const color = ReadingSentencesScreen.color;

  void _open(SentenceCatalog content, SentenceActivity a) {
    final nav = Navigator.of(context);
    if (a == SentenceActivity.read) {
      final progress = AppServices.of(context).reading;
      final list = content.ofLevel(_level);
      // Empieza por la primera que aún no se ha escuchado.
      final start = list.indexWhere((s) => !progress.progress.sentencesHeard.contains(s.id));
      nav.pushNamed(
        AppRoutes.readingSentencesRead,
        arguments: SentenceReaderArgs(level: _level, index: start < 0 ? 0 : start),
      );
    } else {
      nav.pushNamed(
        AppRoutes.readingSentencesGame,
        arguments: SentenceGameArgs(activity: a, level: _level),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final progress = AppServices.of(context).reading;
    return KidScaffold(
      title: ReadingSentencesScreen.title,
      titleIcon: ReadingActivities.sentences.icon,
      accent: color,
      trailing: const ReadingHomeButton(),
      body: SentenceCatalogBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: progress,
          builder: (context, _) {
            final p = progress.progress;
            final all = content.sentences.map((s) => s.id).toSet();
            final heard = p.sentencesHeard.intersection(all).length;
            final readAlone = p.sentencesReadAlone.intersection(all).length;
            final correct = p.questionsCorrect.intersection(all).length;
            final open = sentenceLevelOpen(content, progress, _level);
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
                      const ReadingLolo(text: '¡Vamos a leer oraciones! Escucha, lee y responde.'),
                      const SizedBox(height: 12),
                      ReadingProgressBar(
                        done: correct,
                        total: content.sentences.length,
                        label: 'Preguntas acertadas',
                        color: color,
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 10,
                        runSpacing: 8,
                        children: [
                          _Stat(icon: Icons.hearing_rounded, text: 'Escuchadas: $heard'),
                          _Stat(icon: Icons.auto_stories_rounded, text: 'Leídas sin ayuda: $readAlone'),
                          _Stat(
                            icon: Icons.touch_app_rounded,
                            text: 'Palabras tocadas: ${p.wordsPlayed.length}',
                          ),
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
                          for (final level in SentenceCatalog.levels)
                            _LevelCard(
                              level: level,
                              name: content.levelNames[level] ?? '',
                              selected: level == _level,
                              unlocked: sentenceLevelOpen(content, progress, level),
                              done: progress.sentencesDone(content.ofLevel(level).map((s) => s.id)),
                              total: content.ofLevel(level).length,
                              onTap: () => setState(() => _level = level),
                            ),
                        ],
                      ),
                      const SizedBox(height: 22),
                      Text('Elige qué hacer', style: fredoka(22, color: AppColors.ink)),
                      const SizedBox(height: 10),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          for (final (i, a) in SentenceActivity.values.indexed)
                            SizedBox(
                              width: 270,
                              child: BigActionButton(
                                label: a.title,
                                icon: a.icon,
                                color: const [
                                  AppColors.sky,
                                  AppColors.grape,
                                  AppColors.leaf,
                                  AppColors.coral,
                                ][i],
                                onPressed: open ? () => _open(content, a) : null,
                              ),
                            ),
                        ],
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
    decoration: BoxDecoration(color: const Color(0xFFF1EBFF), borderRadius: BorderRadius.circular(16)),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 20, color: ReadingSentencesScreen.color),
        const SizedBox(width: 6),
        Flexible(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
      ],
    ),
  );
}

class _LevelCard extends StatelessWidget {
  const _LevelCard({
    required this.level,
    required this.name,
    required this.selected,
    required this.unlocked,
    required this.done,
    required this.total,
    required this.onTap,
  });

  final int level;
  final String name;
  final bool selected;
  final bool unlocked;
  final int done;
  final int total;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    const color = ReadingSentencesScreen.color;
    final label = unlocked
        ? 'Nivel $level: $name. $done de $total oraciones.'
        : 'Nivel $level: $name. Se abre al responder ${ReadingController.unlockAfter} preguntas del nivel ${level - 1}.';
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
                unlocked ? (selected ? Icons.check_circle_rounded : Icons.star_rounded) : Icons.lock_rounded,
                color: unlocked ? (selected ? color : AppColors.sun) : AppColors.inkSoft,
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
                          : 'Responde ${ReadingController.unlockAfter} del nivel ${level - 1}',
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
