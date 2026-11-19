import 'dart:math';

import 'package:flutter/material.dart';

import '../../services/app_services.dart';
import '../../theme/app_theme.dart';
import '../achievement_data.dart';
import '../achievements.dart';
import '../learning_report.dart';
import '../reading_progress.dart';
import '../widgets/achievement_widgets.dart';
import 'achievements_screen.dart';

/// Seguimiento de «Aprendo a leer» para adultos. Solo se abre desde la zona
/// para adultos (tras su verificación). Todo sale de lo registrado en este
/// dispositivo; no es un diagnóstico ni compara con otros niños.
class ReadingTrackingScreen extends StatelessWidget {
  const ReadingTrackingScreen({super.key});

  static const title = 'Seguimiento de «Aprendo a leer»';

  static const disclaimer =
      'Este resumen solo cuenta lo que se ha hecho en la app en este dispositivo. No es una evaluación '
      'ni un diagnóstico psicológico, médico o educativo, y no compara con otros niños. Cada niño aprende a su ritmo.';

  @override
  Widget build(BuildContext context) {
    final progress = AppServices.of(context).reading;
    return Theme(
      data: AppTheme.adult(),
      child: Builder(
        builder: (context) => Scaffold(
          appBar: AppBar(title: const Text(title)),
          body: ReadingCatalogsBuilder(
            builder: (context, catalogs) => ListenableBuilder(
              listenable: progress,
              builder: (context, _) {
                final r = ReadingReport(progress.progress, catalogs);
                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    const _Card(
                      icon: Icons.info_outline_rounded,
                      title: 'Antes de leer',
                      children: [Text(disclaimer)],
                    ),
                    _ProfileCard(progress: progress),
                    _SummaryCard(r: r),
                    for (final m in r.modules) _ModuleCard(m: m),
                    _RecommendationsCard(r: r),
                    _EvolutionCard(r: r),
                    _StarsCard(r: r),
                    _MedalsCard(r: r),
                    _DataCard(progress: progress),
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

class _Card extends StatelessWidget {
  const _Card({required this.icon, required this.title, required this.children});
  final IconData icon;
  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 12),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
            ],
          ),
          const SizedBox(height: 8),
          ...children,
        ],
      ),
    ),
  );
}

String _date(String? iso) => iso == null ? 'Sin actividad todavía' : humanDate(iso);

class _ProfileCard extends StatefulWidget {
  const _ProfileCard({required this.progress});
  final ReadingController progress;

  @override
  State<_ProfileCard> createState() => _ProfileCardState();
}

class _ProfileCardState extends State<_ProfileCard> {
  late final _alias = TextEditingController(text: widget.progress.progress.achievements.profile.alias);

  @override
  void dispose() {
    _alias.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final profile = widget.progress.progress.achievements.profile;
    return _Card(
      icon: Icons.face_rounded,
      title: 'Perfil del niño',
      children: [
        const Text(
          'Solo un apodo opcional y un avatar de la app. No pongas el nombre completo ni otros datos personales.',
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _alias,
          maxLength: ReadingProfile.maxAlias,
          decoration: const InputDecoration(labelText: 'Apodo (opcional)', border: OutlineInputBorder()),
          onSubmitted: widget.progress.setAlias,
          onChanged: widget.progress.setAlias,
        ),
        const SizedBox(height: 4),
        Text('Avatar', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final a in ReadingProfile.avatars)
              ChoiceChip(
                label: Text(avatarNames[a]!),
                avatar: SizedBox(width: 28, height: 28, child: AvatarView(avatar: a, size: 28)),
                selected: profile.avatar == a,
                onSelected: (_) => widget.progress.setAvatar(a),
              ),
          ],
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Felicitación hablada al conseguir una medalla'),
          subtitle: const Text('Si se apaga, la medalla se muestra sin voz.'),
          value: profile.celebrationSound,
          onChanged: widget.progress.setCelebrationSound,
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.r});
  final ReadingReport r;

  @override
  Widget build(BuildContext context) {
    final done = r.modules.fold(0, (n, m) => n + m.done);
    final mastered = r.modules.fold(0, (n, m) => n + m.mastered);
    final last = r.p.achievements.lastActivity.values.fold<String?>(
      null,
      (a, b) => a == null || b.compareTo(a) > 0 ? b : a,
    );
    return _Card(
      icon: Icons.summarize_rounded,
      title: 'Resumen',
      children: [
        Text('Actividades realizadas: $done · bien hechas: ${r.activitiesCompleted} · sin ayuda: $mastered.'),
        Text('Intentos registrados: ${r.attempts} · actividades con pistas: ${r.withHints}.'),
        Text(
          'Días con práctica: ${r.recentDays(AchievementData.keepDays).length} · última actividad: ${_date(last)}.',
        ),
        Text(
          'Estrellas: ${r.p.achievements.stars} · medallas: ${r.p.achievements.medals.length} de ${Medals.all.length}.',
        ),
        Text('Etapa del camino: ${r.currentStage.number} · ${r.currentStage.title}.'),
        const SizedBox(height: 6),
        const Text(
          '«Bien hechas» = completadas correctamente alguna vez. «Sin ayuda» = resueltas sin pistas '
          '(en oraciones: leídas antes de escucharlas). Completar no es lo mismo que dominar.',
        ),
      ],
    );
  }
}

class _ModuleCard extends StatelessWidget {
  const _ModuleCard({required this.m});
  final ModuleReport m;

  @override
  Widget build(BuildContext context) => _Card(
    icon: Icons.menu_book_rounded,
    title: m.title,
    children: [
      CountBar(value: m.correct, total: m.available, color: moduleColors[m.module]!, label: 'Bien hechas'),
      const SizedBox(height: 6),
      Text(
        'Disponibles: ${m.available} · realizadas: ${m.done} · bien hechas: ${m.correct} · sin ayuda: ${m.mastered}.',
      ),
      Text('${m.level}. Última actividad: ${_date(m.lastDate)}.'),
      Text(
        'Pendientes: ${m.pending}${m.pendingExamples.isEmpty ? '' : ' (por ejemplo: ${m.pendingExamples.join(', ')})'}.',
      ),
      if (m.toPractice.isNotEmpty) Text('Para practicar: ${m.toPractice.join('; ')}.'),
    ],
  );
}

class _RecommendationsCard extends StatelessWidget {
  const _RecommendationsCard({required this.r});
  final ReadingReport r;

  @override
  Widget build(BuildContext context) => _Card(
    icon: Icons.tips_and_updates_rounded,
    title: 'Áreas para reforzar y sugerencias',
    children: [
      const Text(
        'Cada sugerencia sale de una regla fija y de los datos que la activaron (sin inteligencia artificial).',
      ),
      const SizedBox(height: 6),
      for (final rec in r.recommendations)
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.arrow_right_rounded),
          title: Text(rec.forAdult),
          subtitle: Text('Por qué: ${rec.evidence}'),
        ),
    ],
  );
}

class _EvolutionCard extends StatelessWidget {
  const _EvolutionCard({required this.r});
  final ReadingReport r;

  @override
  Widget build(BuildContext context) {
    final days = r.recentDays();
    final top = days.fold(1, (n, d) => max(n, d.total));
    return _Card(
      icon: Icons.timeline_rounded,
      title: 'Evolución por fechas',
      children: [
        if (days.length < 2)
          const Text('Aún no hay datos suficientes: hacen falta al menos dos días con práctica.')
        else ...[
          const Text('Acciones registradas por día (últimos días con práctica).'),
          const SizedBox(height: 6),
          for (final d in days)
            Semantics(
              label: '${humanDate(d.date)}: ${d.total} acciones',
              excludeSemantics: true,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  children: [
                    SizedBox(width: 92, child: Text(d.date.substring(5))),
                    Expanded(
                      child: Row(
                        children: [
                          for (final mod in ReadingModule.all)
                            if ((d.byModule[mod] ?? 0) > 0)
                              Flexible(
                                flex: d.byModule[mod]!,
                                child: Container(height: 14, color: moduleColors[mod]),
                              ),
                          Flexible(flex: max(0, top - d.total), child: const SizedBox(height: 14)),
                        ],
                      ),
                    ),
                    SizedBox(width: 40, child: Text(' ${d.total}')),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 12,
            children: [
              for (final mod in ReadingModule.all)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(width: 12, height: 12, color: moduleColors[mod]),
                    const SizedBox(width: 4),
                    Text(ReadingReport.moduleTitles[mod]!),
                  ],
                ),
            ],
          ),
        ],
      ],
    );
  }
}

class _StarsCard extends StatelessWidget {
  const _StarsCard({required this.r});
  final ReadingReport r;

  @override
  Widget build(BuildContext context) {
    final events = r.p.achievements.rewards.entries.toList()
      ..sort((a, b) => b.value.date.compareTo(a.value.date));
    return _Card(
      icon: Icons.star_rounded,
      title: 'Estrellas: cómo se ganan',
      children: [
        for (final line in StarRules.description) Text('• $line'),
        const SizedBox(height: 8),
        Text('Últimas estrellas (${r.p.achievements.stars} en total):'),
        if (events.isEmpty) const Text('Todavía ninguna.'),
        for (final e in events.take(8)) Text('${e.value.date} · +${e.value.stars} · ${e.value.reason}'),
      ],
    );
  }
}

class _MedalsCard extends StatelessWidget {
  const _MedalsCard({required this.r});
  final ReadingReport r;

  @override
  Widget build(BuildContext context) {
    final got = r.p.achievements.medals;
    return _Card(
      icon: Icons.military_tech_rounded,
      title: 'Medallas',
      children: [
        for (final m in Medals.all)
          Text(
            got.containsKey(m.id)
                ? '✓ ${m.name} — ${humanDate(got[m.id]!)}'
                : '· ${m.name} — ${m.howTo} (${min(m.current(r.p), m.goal)} de ${m.goal})',
          ),
      ],
    );
  }
}

class _DataCard extends StatelessWidget {
  const _DataCard({required this.progress});
  final ReadingController progress;

  Future<void> _clear(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Borrar el progreso de «Aprendo a leer»?'),
        content: const Text(
          'Se borran actividades, estrellas, medallas, historial y perfil de lectura. '
          'No afecta a los dibujos ni a otras secciones. No se puede deshacer.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Borrar')),
        ],
      ),
    );
    if (ok ?? false) await progress.clearAll();
  }

  Future<void> _restore(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    final ok = await progress.restoreMigrationBackup();
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          ok ? 'Se recuperó la copia anterior a la actualización.' : 'No hay ninguna copia anterior.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => _Card(
    icon: Icons.shield_outlined,
    title: 'Datos y privacidad',
    children: [
      const Text(
        'Todo se guarda solo en este dispositivo (con copia de seguridad). No hay cuentas, no se envía nada a '
        'Internet y no hay clasificaciones ni perfiles públicos.',
      ),
      const SizedBox(height: 8),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          OutlinedButton.icon(
            onPressed: () => _restore(context),
            icon: const Icon(Icons.restore_rounded),
            label: const Text('Recuperar la copia anterior a la actualización'),
          ),
          FilledButton.tonalIcon(
            onPressed: () => _clear(context),
            icon: const Icon(Icons.delete_outline_rounded),
            label: const Text('Borrar el progreso de lectura'),
          ),
        ],
      ),
    ],
  );
}
