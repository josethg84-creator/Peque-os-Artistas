import 'dart:math';

import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../achievement_data.dart';
import '../achievements.dart';
import '../learning_report.dart';
import '../reading_progress.dart';
import '../widgets/achievement_widgets.dart';
import '../widgets/reading_widgets.dart';

const _accent = Color(0xFFF2A93B);

const moduleColors = {
  ReadingModule.syllables: Color(0xFF7FB2F0),
  ReadingModule.words: Color(0xFFF59E3D),
  ReadingModule.sentences: Color(0xFF8E6BE0),
  ReadingModule.dictation: Color(0xFF3DBE8B),
};

/// Escucha el progreso y carga los catálogos.
Widget _withReport(
  BuildContext context,
  Widget Function(BuildContext, ReadingReport, ReadingController) build,
) {
  final progress = AppServices.of(context).reading;
  return ReadingCatalogsBuilder(
    builder: (context, catalogs) => ListenableBuilder(
      listenable: progress,
      builder: (context, _) => build(context, ReadingReport(progress.progress, catalogs), progress),
    ),
  );
}

/// Un mensaje que anima, a partir de datos reales (nunca compara con nadie).
String motivation(ReadingReport r) {
  final p = r.p;
  final next = Medals.all.where((m) => !p.achievements.medals.containsKey(m.id)).toList()
    ..sort((a, b) => (b.current(p) / b.goal).compareTo(a.current(p) / a.goal));
  if (r.modules.every((m) => !m.started)) return '¡Hola! Empieza tu aventura con las vocales.';
  if (next.isNotEmpty) {
    final m = next.first;
    final left = m.goal - min(m.goal, m.current(p));
    if (left > 0 && left <= max(2, m.goal ~/ 3)) {
      return '¡Ya casi! Te ${left == 1 ? 'falta 1' : 'faltan $left'} para la medalla «${m.name}».';
    }
  }
  final days = r.recentDays(60).length;
  if (days >= 2) return '¡Has practicado $days días! Cada día aprendes algo nuevo.';
  return '¡Muy bien! Sigue practicando a tu ritmo.';
}

/// «Mis logros»: avatar y apodo, etapa, estrellas, medallas, actividades,
/// progreso por módulo y un consejo.
class MyAchievementsScreen extends StatelessWidget {
  const MyAchievementsScreen({super.key});

  static const title = 'Mis logros';

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: title,
      titleIcon: Icons.emoji_events_rounded,
      accent: _accent,
      trailing: const ReadingHomeButton(),
      body: _withReport(context, (context, r, progress) {
        final a = r.p.achievements;
        final alias = a.profile.alias;
        final stage = r.currentStage;
        final medals = a.medals.length;
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
                  Wrap(
                    alignment: WrapAlignment.center,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 16,
                    runSpacing: 10,
                    children: [
                      AvatarView(avatar: a.profile.avatar, size: 104),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            alias.isEmpty ? '¡Hola!' : '¡Hola, $alias!',
                            style: fredoka(28, color: AppColors.ink),
                          ),
                          Semantics(
                            label: 'Vas por la etapa ${stage.number}: ${stage.title}',
                            excludeSemantics: true,
                            child: Text(
                              'Etapa ${stage.number}: ${stage.title}',
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                          ),
                          const SizedBox(height: 6),
                          StarCount(stars: a.stars),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  ReadingLolo(text: motivation(r)),
                  const SizedBox(height: 12),
                  ReadingProgressBar(
                    done: r.activitiesCompleted,
                    total: r.activitiesAvailable,
                    label: 'Actividades bien hechas',
                    color: _accent,
                  ),
                  const SizedBox(height: 16),
                  Semantics(
                    label: 'Medallas: $medals de ${Medals.all.length}',
                    excludeSemantics: true,
                    child: Text(
                      'Medallas: $medals de ${Medals.all.length}',
                      style: fredoka(22, color: AppColors.ink),
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 120,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      children: [
                        // Primero las conseguidas.
                        for (final m in [
                          ...Medals.all.where((m) => a.medals.containsKey(m.id)),
                          ...Medals.all.where((m) => !a.medals.containsKey(m.id)),
                        ])
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 6),
                            child: Semantics(
                              label: '${m.name}: ${a.medals.containsKey(m.id) ? 'conseguida' : 'bloqueada'}',
                              excludeSemantics: true,
                              child: MedalBadge(medal: m, unlocked: a.medals.containsKey(m.id), size: 84),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      SizedBox(
                        width: 260,
                        child: BigActionButton(
                          label: 'Mis medallas',
                          icon: Icons.military_tech_rounded,
                          color: AppColors.sun,
                          onPressed: () => Navigator.of(context).pushNamed(AppRoutes.readingMedals),
                        ),
                      ),
                      SizedBox(
                        width: 260,
                        child: BigActionButton(
                          label: 'Mi camino',
                          icon: Icons.route_rounded,
                          color: AppColors.leaf,
                          onPressed: () => Navigator.of(context).pushNamed(AppRoutes.readingPath),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text('Mis actividades', style: fredoka(22, color: AppColors.ink)),
                  const SizedBox(height: 10),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      for (final m in r.modules)
                        ModuleProgressCard(
                          report: m,
                          color: moduleColors[m.module]!,
                          onTap: () => Navigator.of(context).pushNamed(m.route),
                        ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  _Suggestion(r.recommendations.first),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
}

class _Suggestion extends StatelessWidget {
  const _Suggestion(this.rec);
  final Recommendation rec;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: 'Para practicar: ${rec.forChild}',
    excludeSemantics: true,
    onTap: () => Navigator.of(context).pushNamed(rec.route),
    child: GestureDetector(
      onTap: () => Navigator.of(context).pushNamed(rec.route),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFE8F8EE),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: AppColors.leaf, width: 3),
        ),
        child: Row(
          children: [
            const Icon(Icons.tips_and_updates_rounded, color: AppColors.leaf, size: 34),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Para practicar', style: fredoka(18, color: AppColors.ink)),
                  Text(rec.forChild, style: Theme.of(context).textTheme.bodyLarge),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_rounded, color: AppColors.leaf),
          ],
        ),
      ),
    ),
  );
}

/// Colección de medallas: conseguidas (con fecha) y bloqueadas (con lo que
/// falta para conseguirlas).
class MedalsScreen extends StatelessWidget {
  const MedalsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Mis medallas',
      titleIcon: Icons.military_tech_rounded,
      accent: _accent,
      trailing: const ReadingHomeButton(),
      body: _withReport(context, (context, r, _) {
        final p = r.p;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            0,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1000),
              child: Wrap(
                alignment: WrapAlignment.center,
                spacing: 12,
                runSpacing: 12,
                children: [
                  for (final m in Medals.all)
                    _MedalCard(medal: m, date: p.achievements.medals[m.id], value: m.current(p)),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
}

String humanDate(String iso) {
  final parts = iso.split('-');
  if (parts.length != 3) return iso;
  const months = [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
  ];
  final m = int.tryParse(parts[1]) ?? 1;
  return '${int.tryParse(parts[2]) ?? parts[2]} de ${months[(m - 1).clamp(0, 11)]} de ${parts[0]}';
}

class _MedalCard extends StatelessWidget {
  const _MedalCard({required this.medal, required this.date, required this.value});
  final MedalDef medal;
  final String? date;
  final int value;

  @override
  Widget build(BuildContext context) {
    final unlocked = date != null;
    final label = unlocked
        ? '${medal.name}. Conseguida el ${humanDate(date!)}. ${medal.description}'
        : '${medal.name}. Bloqueada. ${medal.howTo} Llevas ${min(value, medal.goal)} de ${medal.goal}.';
    return Semantics(
      label: label,
      excludeSemantics: true,
      child: Container(
        width: 220,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: unlocked ? const Color(0xFFFFFBEA) : const Color(0xFFF6F4FA),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: unlocked ? medal.color : const Color(0xFFD1C4E9),
            width: unlocked ? 3 : 2,
          ),
        ),
        child: Column(
          children: [
            MedalBadge(medal: medal, unlocked: unlocked, size: 84),
            const SizedBox(height: 6),
            Text(
              medal.name,
              style: fredoka(18, color: AppColors.ink),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              unlocked ? medal.description : medal.howTo,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 6),
            if (unlocked)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.check_circle_rounded, color: AppColors.leaf, size: 18),
                  const SizedBox(width: 4),
                  Flexible(child: Text(humanDate(date!), style: Theme.of(context).textTheme.bodySmall)),
                ],
              )
            else
              CountBar(value: min(value, medal.goal), total: medal.goal, color: medal.color),
          ],
        ),
      ),
    );
  }
}

/// «Mi camino»: seis etapas con su avance real. Ninguna se bloquea: se puede
/// volver a cualquiera para practicar.
class LearningPathScreen extends StatelessWidget {
  const LearningPathScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Mi camino',
      titleIcon: Icons.route_rounded,
      accent: _accent,
      trailing: const ReadingHomeButton(),
      body: _withReport(context, (context, r, _) {
        final current = r.currentStage.number;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            0,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 700),
              child: Column(
                children: [
                  const ReadingLolo(text: 'Este es tu camino. Toca una etapa para practicar.'),
                  const SizedBox(height: 10),
                  for (final (i, s) in r.path.indexed) ...[
                    if (i > 0) _PathLink(done: r.path[i - 1].done, left: i.isOdd),
                    Align(
                      alignment: i.isEven ? const Alignment(-0.35, 0) : const Alignment(0.35, 0),
                      child: _StageCard(stage: s, current: s.number == current),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
}

class _PathLink extends StatelessWidget {
  const _PathLink({required this.done, required this.left});
  final bool done;
  final bool left;

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 34,
    child: Align(
      alignment: left ? const Alignment(-0.05, 0) : const Alignment(0.05, 0),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < 4; i++)
            Container(
              width: 10,
              height: 10,
              margin: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: done ? AppColors.leaf : const Color(0xFFD1C4E9),
              ),
            ),
        ],
      ),
    ),
  );
}

class _StageCard extends StatelessWidget {
  const _StageCard({required this.stage, required this.current});
  final PathStage stage;
  final bool current;

  @override
  Widget build(BuildContext context) {
    final s = stage;
    return Semantics(
      button: true,
      label:
          'Etapa ${s.number}: ${s.title}. ${s.status}. ${s.goalText}: ${min(s.value, s.goal)} de ${s.goal}.${current ? ' Estás aquí.' : ''}',
      excludeSemantics: true,
      onTap: () => Navigator.of(context).pushNamed(s.route),
      child: GestureDetector(
        onTap: () => Navigator.of(context).pushNamed(s.route),
        child: Container(
          width: 330,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: s.done ? const Color(0xFFE8F8EE) : Colors.white,
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: current ? AppColors.sun : s.color, width: current ? 5 : 3),
            boxShadow: const [BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 3))],
          ),
          child: Row(
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(shape: BoxShape.circle, color: s.color),
                child: Icon(s.done ? Icons.check_rounded : s.icon, color: Colors.white, size: 36),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Etapa ${s.number}', style: Theme.of(context).textTheme.bodySmall),
                    Text(s.title, style: fredoka(19, color: AppColors.ink)),
                    const SizedBox(height: 4),
                    CountBar(value: min(s.value, s.goal), total: s.goal, color: s.color),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Icon(
                          s.done
                              ? Icons.emoji_events_rounded
                              : current
                              ? Icons.place_rounded
                              : Icons.flag_outlined,
                          size: 18,
                          color: AppColors.inkSoft,
                        ),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            current && !s.done ? 'Estás aquí · ${s.goalText}' : '${s.status} · ${s.goalText}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      ],
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
