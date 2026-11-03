import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../../widgets/motion/delayed_loading.dart';
import '../speech_content.dart';
import '../widgets/speech_widgets.dart';

/// Una actividad del menú. Las que llegarán en entregas posteriores se
/// muestran como «Muy pronto»: al tocarlas, Lolo lo explica.
class SpeechActivity {
  const SpeechActivity(this.title, this.subtitle, this.icon, this.color, this.route);
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;

  /// `null` mientras no esté disponible.
  final String? route;

  bool get available => route != null;
}

/// Menú de «Aprendo a Hablar».
class SpeechHubScreen extends StatelessWidget {
  const SpeechHubScreen({super.key});

  static const activities = [
    SpeechActivity(
      'Mis primeras palabras',
      '¡Escucha y aprende!',
      Icons.abc_rounded,
      Color(0xFF8FCBFF),
      AppRoutes.speechWordGroups,
    ),
    SpeechActivity(
      'Aprendo frases',
      '¡Frases para cada día!',
      Icons.chat_bubble_rounded,
      Color(0xFFFFA8C8),
      AppRoutes.speechPhrases,
    ),
    SpeechActivity(
      'Construyo oraciones',
      '¡Junta palabras!',
      Icons.view_week_rounded,
      Color(0xFF8EDDB8),
      AppRoutes.speechSentences,
    ),
    SpeechActivity(
      'Aprendo los verbos',
      '¡Como, comes, come!',
      Icons.directions_run_rounded,
      Color(0xFFFFD27A),
      AppRoutes.speechVerbs,
    ),
    SpeechActivity('Hablemos juntos', 'Muy pronto', Icons.forum_rounded, Color(0xFFC3A9F5), null),
    SpeechActivity(
      'Escucho y comprendo',
      '¡Escucha y señala!',
      Icons.hearing_rounded,
      Color(0xFFFFBE98),
      AppRoutes.speechListen,
    ),
    SpeechActivity('Cuentos interactivos', 'Muy pronto', Icons.auto_stories_rounded, Color(0xFF86DCE0), null),
    SpeechActivity(
      'Mi progreso',
      '¡Mira lo que aprendiste!',
      Icons.insights_rounded,
      Color(0xFFFF9E9E),
      AppRoutes.speechProgress,
    ),
  ];

  static const comingSoon = '¡Esta actividad llegará muy pronto! Mientras, juguemos con las demás.';

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Aprendo a Hablar',
      titleIcon: Icons.record_voice_over_rounded,
      accent: speechAccent,
      backLabel: 'Volver al inicio',
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(AppDimens.pagePadding, 0, AppDimens.pagePadding, 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: LoloBubble(text: '¡Hola! Soy Lolo. ¿Aprendemos a hablar juntos?', size: 64),
            ),
          ),
          Expanded(
            child: AdaptiveGrid(
              itemCount: activities.length,
              minTileWidth: 170,
              childAspectRatio: 1.05,
              itemBuilder: (context, i) {
                final a = activities[i];
                final route = a.route;
                return HomeMenuCard(
                  title: a.title,
                  subtitle: a.subtitle,
                  color: a.color,
                  art: _ActivityArt(icon: a.icon, color: a.color),
                  badge: a.available ? null : 'Muy pronto',
                  dimmed: !a.available,
                  opensRoute: a.available,
                  onTap: route != null ? () => Navigator.of(context).pushNamed(route) : () => _soon(context),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  static void _soon(BuildContext context) {
    speak(context, comingSoon);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text(comingSoon)));
  }
}

/// Icono grande de una actividad, blanco con sombra (como en las tarjetas del inicio).
class _ActivityArt extends StatelessWidget {
  const _ActivityArt({required this.icon, required this.color});

  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        final side = box.biggest.shortestSide;
        return Center(
          child: Icon(
            icon,
            size: side * 0.9,
            color: Colors.white,
            shadows: [
              Shadow(
                color: Color.lerp(color, Colors.black, 0.35)!,
                offset: Offset(0, side * 0.05),
                blurRadius: 2,
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Carga el contenido de «Aprendo a Hablar» y lo pasa a [builder].
class SpeechContentBuilder extends StatefulWidget {
  const SpeechContentBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, SpeechContent content) builder;

  @override
  State<SpeechContentBuilder> createState() => _SpeechContentBuilderState();
}

class _SpeechContentBuilderState extends State<SpeechContentBuilder> {
  Future<SpeechContent>? _future;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _future ??= AppServices.of(context).speech.content();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<SpeechContent>(
      future: _future,
      builder: (context, snapshot) {
        final content = snapshot.data;
        if (content != null) return widget.builder(context, content);
        if (snapshot.hasError) {
          return const Center(child: Text('No pudimos abrir las palabras. Inténtalo de nuevo más tarde.'));
        }
        return const DelayedLoading(message: 'Preparando las palabras…', color: speechAccent);
      },
    );
  }
}

/// Los grupos de palabras (Familia, Animales…), con lo escuchado de cada uno.
class WordGroupsScreen extends StatelessWidget {
  const WordGroupsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Mis primeras palabras',
      titleIcon: Icons.abc_rounded,
      accent: speechAccent,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: speech,
          builder: (context, _) => AdaptiveGrid(
            itemCount: content.categories.length,
            minTileWidth: 160,
            childAspectRatio: 0.95,
            itemBuilder: (context, i) {
              final c = content.categories[i];
              final heard = c.words.where((w) => speech.progress.wordsHeard.contains(w.id)).length;
              return HomeMenuCard(
                title: c.name,
                subtitle: '$heard de ${c.words.length} escuchadas',
                color: Color.lerp(c.color, Colors.white, 0.25)!,
                art: Padding(
                  padding: const EdgeInsets.all(4),
                  child: SpeechPictureView(picture: c.words.first.picture, tint: c.color),
                ),
                onTap: () =>
                    Navigator.of(context).pushNamed(AppRoutes.speechWords, arguments: SpeechWordsArgs(c.id)),
              );
            },
          ),
        ),
      ),
    );
  }
}

/// «Mi progreso»: lo que se ha hecho de verdad en este dispositivo.
class SpeechProgressScreen extends StatelessWidget {
  const SpeechProgressScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    final text = Theme.of(context).textTheme;
    return KidScaffold(
      title: 'Mi progreso',
      titleIcon: Icons.insights_rounded,
      accent: speechAccent,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: speech,
          builder: (context, _) {
            final p = speech.progress;
            final words = content.words.where((w) => p.wordsHeard.contains(w.id)).length;
            final phrases = content.phrases.where((f) => p.phrasesHeard.contains(f.id)).length;
            final ordered = content.phrases.where((f) => p.phrasesOrdered.contains(f.id)).length;
            final days = speech.daysPracticedThisWeek();
            return ListView(
              padding: const EdgeInsets.fromLTRB(
                AppDimens.pagePadding,
                0,
                AppDimens.pagePadding,
                AppDimens.pagePadding,
              ),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: LoloBubble(
                    text: words + phrases == 0
                        ? '¡Vamos a escuchar tus primeras palabras!'
                        : '¡Qué bien lo estás haciendo!',
                    size: 60,
                  ),
                ),
                const SizedBox(height: 12),
                _Counter(
                  icon: Icons.abc_rounded,
                  color: const Color(0xFF4FA8F0),
                  label: 'Palabras escuchadas',
                  done: words,
                  total: content.words.length,
                ),
                _Counter(
                  icon: Icons.chat_bubble_rounded,
                  color: const Color(0xFFF06292),
                  label: 'Frases escuchadas',
                  done: phrases,
                  total: content.phrases.length,
                ),
                _Counter(
                  icon: Icons.sort_rounded,
                  color: const Color(0xFF26A69A),
                  label: 'Frases ordenadas',
                  done: ordered,
                  total: content.phrases.length,
                ),
                _Counter(
                  icon: Icons.calendar_month_rounded,
                  color: const Color(0xFFFFA726),
                  label: 'Días de práctica esta semana',
                  done: days,
                  total: 7,
                ),
                _Counter(
                  icon: Icons.sort_rounded,
                  color: const Color(0xFF26A69A),
                  label: 'Oraciones ordenadas',
                  done: content.sentences.order.where((o) => p.sentencesOrdered.contains(o.text)).length,
                  total: content.sentences.order.length,
                ),
                _Counter(
                  icon: Icons.directions_run_rounded,
                  color: const Color(0xFFFFA726),
                  label: 'Verbos trabajados',
                  done: content.verbs.where((v) => p.verbsHeard.contains(v.id)).length,
                  total: content.verbs.length,
                ),
                _Counter(
                  icon: Icons.view_week_rounded,
                  color: const Color(0xFF8EDDB8),
                  label: 'Oraciones construidas',
                  done: p.sentencesBuilt.length,
                ),
                _Counter(
                  icon: Icons.emoji_events_rounded,
                  color: const Color(0xFFFFC93C),
                  label: 'Actividades terminadas',
                  done: p.activitiesDone.values.fold(0, (a, b) => a + b),
                ),
                _Counter(
                  icon: Icons.mic_rounded,
                  color: const Color(0xFFE53950),
                  label: 'Veces que practicaste con tu voz',
                  done: p.recordings,
                ),
                const SizedBox(height: 8),
                Semantics(header: true, child: Text('Palabras por grupo', style: text.titleLarge)),
                const SizedBox(height: 4),
                for (final c in content.categories)
                  _Counter(
                    color: c.color,
                    label: c.name,
                    done: c.words.where((w) => p.wordsHeard.contains(w.id)).length,
                    total: c.words.length,
                    compact: true,
                  ),
                const SizedBox(height: 12),
                Text(
                  'Para los adultos: aquí solo se cuentan las actividades hechas en este dispositivo. '
                  'No es una evaluación del habla ni del lenguaje, y no sustituye la opinión de un profesional.',
                  style: text.bodySmall,
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _Counter extends StatelessWidget {
  const _Counter({
    this.icon,
    required this.color,
    required this.label,
    required this.done,
    this.total,
    this.compact = false,
  });

  final IconData? icon;
  final Color color;
  final String label;
  final int done;

  /// Sin total, solo se muestra el número (oraciones construidas…).
  final int? total;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Semantics(
      container: true,
      label: total == null ? '$label: $done' : '$label: $done de $total',
      excludeSemantics: true,
      child: Container(
        margin: EdgeInsets.only(bottom: compact ? 6 : 10),
        padding: EdgeInsets.all(compact ? 8 : 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
          boxShadow: const [BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 3))],
        ),
        child: Row(
          children: [
            if (icon != null) ...[Icon(icon, color: color, size: 34), const SizedBox(width: 10)],
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: compact ? text.titleSmall : text.titleMedium),
                  if (total case final total?) ...[
                    const SizedBox(height: 4),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: LinearProgressIndicator(
                        value: total == 0 ? 0 : done / total,
                        minHeight: compact ? 8 : 12,
                        color: color,
                        backgroundColor: color.withValues(alpha: 0.18),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 10),
            Text(total == null ? '$done' : '$done/$total', style: text.titleMedium),
          ],
        ),
      ),
    );
  }
}
