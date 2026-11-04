import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_dimens.dart';
import '../../theme/app_colors.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../../widgets/motion/delayed_loading.dart';
import '../recommendations.dart';
import '../speech_content.dart';
import '../speech_progress.dart';
import '../speech_summary.dart';
import '../widgets/speech_widgets.dart';
import '../../aac/widgets/aac_widgets.dart';
import 'mission_screen.dart';

/// Una actividad del menú. Las que llegarán en entregas posteriores se
/// muestran como «Muy pronto»: al tocarlas, Lolo lo explica.
class SpeechActivity {
  const SpeechActivity(this.title, this.subtitle, this.icon, this.color, this.route, {this.image});
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;

  /// Ilustración 3D de la tarjeta (WEBP en [imageFolder]). Mientras el archivo
  /// no exista, la tarjeta muestra [icon].
  final String? image;

  static const imageFolder = 'assets/images/aprendo_hablar/';

  /// `null` mientras no esté disponible.
  final String? route;

  bool get available => route != null;
}

/// Menú de «Aprendo a Hablar»: el saludo de Lolo, «Mi aventura de hoy»,
/// sus sugerencias y todas las actividades.
class SpeechHubScreen extends StatefulWidget {
  const SpeechHubScreen({super.key});

  static const activities = [
    SpeechActivity(
      'Mis primeras palabras',
      '¡Escucha y aprende!',
      Icons.abc_rounded,
      Color(0xFF8FCBFF),
      AppRoutes.speechWordGroups,
      image: '${SpeechActivity.imageFolder}mis_primeras_palabras.webp',
    ),
    SpeechActivity(
      'Aprendo frases',
      '¡Frases para cada día!',
      Icons.chat_bubble_rounded,
      Color(0xFFFFA8C8),
      AppRoutes.speechPhrases,
      image: '${SpeechActivity.imageFolder}aprendo_frases.webp',
    ),
    SpeechActivity(
      'Construyo oraciones',
      '¡Junta palabras!',
      Icons.view_week_rounded,
      Color(0xFF8EDDB8),
      AppRoutes.speechSentences,
      image: '${SpeechActivity.imageFolder}construyo_oraciones.webp',
    ),
    SpeechActivity(
      'Aprendo los verbos',
      '¡Como, comes, come!',
      Icons.directions_run_rounded,
      Color(0xFFFFD27A),
      AppRoutes.speechVerbs,
      image: '${SpeechActivity.imageFolder}aprendo_los_verbos.webp',
    ),
    SpeechActivity(
      'Hablemos con Lolo',
      '¡Conversa con Lolo!',
      Icons.forum_rounded,
      Color(0xFFC3A9F5),
      AppRoutes.speechConversations,
    ),
    SpeechActivity(
      'Escucho y respondo',
      '¡56 juegos para escuchar!',
      Icons.hearing_rounded,
      Color(0xFFFFBE98),
      AppRoutes.speechListening,
    ),
    SpeechActivity(
      'Lolo me cuenta un cuento',
      '¡20 cuentos con voz!',
      Icons.auto_stories_rounded,
      Color(0xFF86DCE0),
      AppRoutes.speechStories,
    ),
    SpeechActivity(
      'Yo puedo expresarme',
      '¡Necesito… y siento…!',
      Icons.emoji_emotions_rounded,
      Color(0xFFFFB3C7),
      AppRoutes.speechExpress,
      image: '${SpeechActivity.imageFolder}yo_puedo_expresarme.webp',
    ),
    SpeechActivity(
      'Ahora cuéntamelo tú',
      '¡Ordena y cuenta!',
      Icons.photo_library_rounded,
      Color(0xFFFFCC80),
      AppRoutes.speechTellList,
    ),
    SpeechActivity(
      'Sílabas y sonidos',
      '¡Palmas, rimas y más!',
      Icons.music_note_rounded,
      Color(0xFFB0E57C),
      AppRoutes.speechSounds,
    ),
    SpeechActivity(
      'Juegos de palabras',
      '¡Más de 300 palabras!',
      Icons.extension_rounded,
      Color(0xFF9FC5F8),
      AppRoutes.speechWordGames,
      image: '${SpeechActivity.imageFolder}juegos_de_palabras.webp',
    ),
    SpeechActivity(
      'Mi historia',
      '¡Inventa tu cuento!',
      Icons.menu_book_rounded,
      Color(0xFFF7B2D9),
      AppRoutes.speechMyStory,
      image: '${SpeechActivity.imageFolder}mi_historia.webp',
    ),
    SpeechActivity(
      'Quiero decir',
      '¡Tablero con dibujos y voz!',
      Icons.grid_view_rounded,
      Color(0xFF80CBC4),
      AppRoutes.aac,
    ),
    SpeechActivity(
      'Mis aventuras con Lolo',
      '¡Mira lo que aprendiste!',
      Icons.insights_rounded,
      Color(0xFFFF9E9E),
      AppRoutes.speechProgress,
    ),
  ];

  /// Las áreas del menú (en este orden) y sus actividades, por título. Son
  /// secciones con título en la misma pantalla: no añaden menús.
  static const sections = <(String, IconData, List<String>)>[
    (
      'Aprendo palabras',
      Icons.abc_rounded,
      ['Mis primeras palabras', 'Aprendo frases', 'Juegos de palabras'],
    ),
    (
      'Formo oraciones',
      Icons.view_week_rounded,
      ['Construyo oraciones', 'Mi historia', 'Yo puedo expresarme'],
    ),
    ('Practico verbos', Icons.directions_run_rounded, ['Aprendo los verbos']),
    ('Converso con Lolo', Icons.forum_rounded, ['Hablemos con Lolo']),
    ('Escucho cuentos', Icons.auto_stories_rounded, ['Lolo me cuenta un cuento', 'Ahora cuéntamelo tú']),
    ('Juegos de lenguaje', Icons.music_note_rounded, ['Sílabas y sonidos', 'Escucho y respondo']),
    ('Quiero decir', Icons.grid_view_rounded, ['Quiero decir']),
    ('Mis aventuras', Icons.insights_rounded, ['Mis aventuras con Lolo']),
  ];

  /// Cuántas tarjetas hay antes del área [title].
  static int sectionOffset(String title) {
    var n = 0;
    for (final (t, _, names) in sections) {
      if (t == title) return n;
      n += names.length;
    }
    return n;
  }

  static const comingSoon = '¡Esta actividad llegará muy pronto! Mientras, juguemos con las demás.';

  @override
  State<SpeechHubScreen> createState() => _SpeechHubScreenState();
}

class _SpeechHubScreenState extends State<SpeechHubScreen> {
  @override
  void initState() {
    super.initState();
    context.getInheritedWidgetOfExactType<AppServices>()?.speech.startSession();
  }

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Aprendo a Hablar',
      titleIcon: Icons.record_voice_over_rounded,
      accent: speechAccent,
      backLabel: 'Volver al inicio',
      body: CustomScrollView(
        slivers: [
          const SliverPadding(
            padding: EdgeInsets.fromLTRB(AppDimens.pagePadding, 0, AppDimens.pagePadding, 8),
            sliver: SliverList(
              delegate: SliverChildListDelegate.fixed([
                Align(
                  alignment: Alignment.centerLeft,
                  child: LoloBubble(text: '¡Hola! Soy Lolo. ¿Aprendemos a hablar juntos?', size: 64),
                ),
                SizedBox(height: 8),
                // Comunicar algo, siempre a un toque (fase 5).
                QuickSayBanner(),
                SizedBox(height: 10),
                MissionBanner(),
                SizedBox(height: 10),
                LoloSuggestions(),
              ]),
            ),
          ),
          for (final (title, icon, names) in SpeechHubScreen.sections) ...[
            // Si la única tarjeta se llama como el área, basta la tarjeta.
            if (!(names.length == 1 && names.first == title))
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(AppDimens.pagePadding, 14, AppDimens.pagePadding, 0),
                sliver: SliverToBoxAdapter(
                  child: _SectionTitle(title: title, icon: icon),
                ),
              ),
            AdaptiveSliverGrid(
              itemCount: names.length,
              indexOffset: SpeechHubScreen.sectionOffset(title),
              minTileWidth: 170,
              childAspectRatio: 1.05,
              itemBuilder: (context, i) {
                final a = SpeechHubScreen.activities.firstWhere((x) => x.title == names[i]);
                final route = a.route;
                return HomeMenuCard(
                  title: a.title,
                  subtitle: a.subtitle,
                  color: a.color,
                  art: SpeechActivityArt(icon: a.icon, color: a.color, image: a.image),
                  badge: a.available ? null : 'Muy pronto',
                  dimmed: !a.available,
                  opensRoute: a.available,
                  onTap: route != null
                      ? () {
                          speech.markVisit(route);
                          Navigator.of(context).pushNamed(route);
                        }
                      : () => _soon(context),
                );
              },
            ),
          ],
        ],
      ),
    );
  }

  static void _soon(BuildContext context) {
    speak(context, SpeechHubScreen.comingSoon);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text(SpeechHubScreen.comingSoon)));
  }
}

/// «Lolo te propone»: hasta tres sugerencias según su progreso y los ajustes
/// (ver `recommendActivities`). Se pueden ignorar: todo el menú sigue abierto.
class LoloSuggestions extends StatelessWidget {
  const LoloSuggestions({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return FutureBuilder<SpeechContent>(
      future: speech.content(),
      builder: (context, snapshot) {
        final content = snapshot.data;
        if (content == null) return const SizedBox.shrink();
        return ListenableBuilder(
          listenable: speech,
          builder: (context, _) {
            final list = recommendActivities(
              speech.progress,
              content,
              now: DateTime.now(),
              sessionTime: speech.sessionTime,
            );
            if (list.isEmpty) return const SizedBox.shrink();
            return Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: const Color(0xFFB9E6C9), width: 3),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Semantics(
                    header: true,
                    child: Text('Lolo te propone', style: fredoka(20, color: const Color(0xFF2E7D4F))),
                  ),
                  const SizedBox(height: 6),
                  for (final r in list) _Suggestion(recommendation: r),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _Suggestion extends StatelessWidget {
  const _Suggestion({required this.recommendation});

  final Recommendation recommendation;

  @override
  Widget build(BuildContext context) {
    final r = recommendation;
    void tap() {
      final route = r.route;
      if (route == null) {
        speak(context, r.lolo);
        return;
      }
      AppServices.of(context).speech.markVisit(route);
      speak(context, r.lolo);
      Navigator.of(context).pushNamed(route, arguments: r.args);
    }

    return Semantics(
      container: true,
      button: true,
      label: r.lolo,
      excludeSemantics: true,
      onTap: tap,
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: tap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
          child: Row(
            children: [
              Icon(
                r.route == null ? Icons.bedtime_rounded : Icons.play_circle_fill_rounded,
                color: speechAccent,
                size: 40,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(r.lolo, style: fredoka(18, color: const Color(0xFF2A2350))),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Dibujo de una actividad: su ilustración 3D si tiene una ([image]) o, si no
/// (o mientras el archivo no esté), su icono blanco con sombra, como en las
/// tarjetas del inicio. Se adapta al espacio de la tarjeta.
class SpeechActivityArt extends StatelessWidget {
  const SpeechActivityArt({super.key, required this.icon, required this.color, this.image});

  final IconData icon;
  final Color color;
  final String? image;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        final side = box.biggest.shortestSide;
        final fallback = Center(
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
        final asset = image;
        if (asset == null || !side.isFinite || side <= 0) return fallback;
        // Se decodifica al tamaño en pantalla (no al del archivo) para ahorrar memoria.
        final pixels = (side * MediaQuery.devicePixelRatioOf(context)).ceil();
        // Las ilustraciones son cuadradas y con fondo: esquinas redondeadas,
        // como las tarjetas, para que encajen en ellas.
        return Center(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(side * 0.18),
            child: SizedBox.square(
              dimension: side,
              child: Image.asset(
                asset,
                fit: BoxFit.contain,
                cacheWidth: pixels,
                filterQuality: FilterQuality.medium,
                excludeFromSemantics: true, // la tarjeta ya dice su título
                gaplessPlayback: true,
                errorBuilder: (context, error, stack) => fallback,
              ),
            ),
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
      title: 'Mis aventuras con Lolo',
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
                    text: words + phrases + p.stars + p.answers == 0
                        ? '¡Vamos a escuchar tus primeras palabras!'
                        : '¡Qué bien lo estás haciendo!',
                    size: 60,
                  ),
                ),
                const SizedBox(height: 12),
                _Rewards(progress: p),
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
                Semantics(header: true, child: Text('Conversaciones y cuentos', style: text.titleLarge)),
                const SizedBox(height: 4),
                ...() {
                  final f = SpeechPhase3Summary(p, content);
                  return [
                    _Counter(
                      icon: Icons.star_rounded,
                      color: const Color(0xFFFFC93C),
                      label: 'Estrellas ganadas',
                      done: f.stars,
                    ),
                    _Counter(
                      icon: Icons.forum_rounded,
                      color: const Color(0xFF9575CD),
                      label: 'Conversaciones con Lolo',
                      done: f.conversations,
                      total: f.conversationsTotal,
                    ),
                    _Counter(
                      icon: Icons.auto_stories_rounded,
                      color: const Color(0xFF26C6DA),
                      label: 'Cuentos escuchados',
                      done: f.storiesHeard,
                      total: f.storiesTotal,
                    ),
                    _Counter(
                      icon: Icons.quiz_rounded,
                      color: const Color(0xFF26A69A),
                      label: 'Cuentos con preguntas respondidas',
                      done: f.storiesQuizzed,
                      total: f.storiesTotal,
                    ),
                    _Counter(
                      icon: Icons.photo_library_rounded,
                      color: const Color(0xFFFFA726),
                      label: 'Historias que contaste',
                      done: f.told,
                      total: f.tellTotal,
                    ),
                    _Counter(
                      icon: Icons.favorite_rounded,
                      color: const Color(0xFFF06292),
                      label: 'Emociones exploradas',
                      done: f.emotions,
                      total: f.emotionsTotal,
                    ),
                    _Counter(
                      icon: Icons.back_hand_rounded,
                      color: const Color(0xFF4FA8F0),
                      label: 'Necesidades practicadas',
                      done: f.needs,
                      total: f.needsTotal,
                    ),
                    _Counter(
                      icon: Icons.hearing_rounded,
                      color: const Color(0xFFFF8A65),
                      label: 'Ejercicios de escucha',
                      done: f.listening,
                      total: f.listeningTotal,
                    ),
                    _Counter(
                      icon: Icons.check_circle_rounded,
                      color: const Color(0xFF43A047),
                      label: 'Respuestas acertadas',
                      done: f.answers,
                    ),
                  ];
                }(),
                const SizedBox(height: 8),
                Semantics(header: true, child: Text('Sonidos, juegos e historias', style: text.titleLarge)),
                const SizedBox(height: 4),
                _Counter(
                  icon: Icons.menu_book_rounded,
                  color: const Color(0xFFEC407A),
                  label: 'Historias que inventaste',
                  done: p.storiesBuilt.length,
                ),
                _Counter(
                  icon: Icons.sign_language_rounded,
                  color: const Color(0xFF7CB342),
                  label: 'Palabras con palmas y sílabas',
                  done: p.syllablesDone.length,
                ),
                _Counter(
                  icon: Icons.extension_rounded,
                  color: const Color(0xFF5C9DED),
                  label: 'Juegos de palabras y sonidos',
                  done: p.activitiesDone.entries
                      .where((e) => e.key.startsWith('juego_'))
                      .fold(0, (a, e) => a + e.value),
                ),
                _Counter(
                  icon: Icons.looks_rounded,
                  color: const Color(0xFF7E57C2),
                  label: 'Aventuras completadas',
                  done: p.activitiesDone['aventura'] ?? 0,
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

/// Estrellas, recompensas y actividades favoritas.
class _Rewards extends StatelessWidget {
  const _Rewards({required this.progress});

  final SpeechProgress progress;

  @override
  Widget build(BuildContext context) {
    final medals = speechMedals(progress);
    final favorites = favoriteActivities(progress);
    final earned = medals.where((m) => m.earned).length;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(26),
        boxShadow: const [BoxShadow(color: Color(0x1A000000), blurRadius: 10, offset: Offset(0, 4))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            container: true,
            label: 'Estrellas: ${progress.stars}. Recompensas: $earned de ${medals.length}',
            excludeSemantics: true,
            child: Row(
              children: [
                const Icon(Icons.star_rounded, color: AppColors.sun, size: 44),
                Text('${progress.stars}', style: fredoka(34, color: const Color(0xFF2A2350))),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Recompensas: $earned de ${medals.length}',
                    style: fredoka(20, color: AppColors.inkSoft),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [for (final m in medals) _Medal(medal: m)],
          ),
          if (favorites.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('Tus favoritas', style: fredoka(20, color: const Color(0xFF2A2350))),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                for (final f in favorites)
                  Semantics(
                    container: true,
                    label: 'Favorita: $f',
                    excludeSemantics: true,
                    child: Chip(
                      avatar: const Icon(Icons.favorite_rounded, color: Color(0xFFE91E63), size: 20),
                      label: Text(f),
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _Medal extends StatelessWidget {
  const _Medal({required this.medal});

  final SpeechMedal medal;

  @override
  Widget build(BuildContext context) {
    final m = medal;
    final color = m.earned ? const Color(0xFFFFB300) : const Color(0xFFCFD8DC);
    return Semantics(
      container: true,
      label: m.earned ? 'Recompensa: ${m.title}' : '${m.title}: ${m.progress.clamp(0, m.goal)} de ${m.goal}',
      excludeSemantics: true,
      child: SizedBox(
        width: 96,
        child: Column(
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(colors: [Color.lerp(color, Colors.white, 0.5)!, color]),
                border: Border.all(color: Colors.white, width: 3),
                boxShadow: [BoxShadow(color: color.withValues(alpha: 0.6), offset: const Offset(0, 3))],
              ),
              child: Icon(SpeechIcons.lookup(m.icon) ?? Icons.star_rounded, color: Colors.white, size: 34),
            ),
            const SizedBox(height: 4),
            Text(
              m.title,
              textAlign: TextAlign.center,
              maxLines: 2,
              style: fredoka(13, color: m.earned ? const Color(0xFF2A2350) : AppColors.inkSoft),
            ),
            if (!m.earned)
              Text(
                '${m.progress.clamp(0, m.goal)} / ${m.goal}',
                style: fredoka(12, color: AppColors.inkSoft),
              ),
          ],
        ),
      ),
    );
  }
}

/// Título de un área del menú («Aprendo palabras», «Quiero decir»…).
class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.icon});

  final String title;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Semantics(
    header: true,
    child: Row(
      children: [
        Icon(icon, color: speechAccent, size: 30),
        const SizedBox(width: 8),
        Expanded(
          child: Text(title, style: fredoka(24, color: const Color(0xFF2A2350))),
        ),
      ],
    ),
  );
}
