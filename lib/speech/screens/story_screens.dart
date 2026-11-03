import 'dart:async';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/order_pictures.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';
import 'speech_quiz_screen.dart';

const _storyColor = Color(0xFF26A69A);

/// «Lolo me cuenta un cuento»: los 20 cuentos.
class StoriesScreen extends StatelessWidget {
  const StoriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Lolo me cuenta un cuento',
      titleIcon: Icons.auto_stories_rounded,
      accent: _storyColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: speech,
          builder: (context, _) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: LoloBubble(text: '¿Qué cuento quieres que te cuente?', size: 60),
                ),
              ),
              Expanded(
                child: AdaptiveGrid(
                  itemCount: content.stories.length,
                  minTileWidth: 160,
                  childAspectRatio: 0.85,
                  itemBuilder: (context, i) {
                    final s = content.stories[i];
                    final heard = speech.progress.storiesHeard.contains(s.id);
                    return HomeMenuCard(
                      title: s.title,
                      subtitle: heard ? '¡Ya lo escuchaste!' : s.category,
                      color: const Color(0xFFB2DFDB),
                      art: Padding(
                        padding: const EdgeInsets.all(2),
                        child: SpeechPictureView(picture: s.cover),
                      ),
                      onTap: () =>
                          Navigator.of(context)
                              .pushNamed(AppRoutes.speechStory, arguments: SpeechStoryArgs(s.id)),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Busca el cuento y muestra [builder], o un aviso si no existe.
class _StoryLoader extends StatelessWidget {
  const _StoryLoader({required this.storyId, required this.builder});

  final String storyId;
  final Widget Function(BuildContext context, Story story) builder;

  @override
  Widget build(BuildContext context) {
    return SpeechContentBuilder(
      builder: (context, content) {
        final story = content.stories.where((s) => s.id == storyId).firstOrNull;
        if (story == null) {
          return KidScaffold(
            title: 'Cuentos',
            accent: _storyColor,
            body: const Center(child: Text('No encontramos este cuento.')),
          );
        }
        return builder(context, story);
      },
    );
  }
}

/// Un cuento, escena a escena. Controles: escuchar, pausar y continuar,
/// repetir la escena, despacio, anterior, siguiente y volver al catálogo.
///
/// Se resalta la escena que se está narrando (el texto entero de la escena,
/// no palabra a palabra: el motor de voz no da tiempos fiables por palabra).
/// «Continuar» vuelve a empezar la escena en pausa desde su principio.
class StoryScreen extends StatelessWidget {
  const StoryScreen({super.key, required this.storyId});

  final String storyId;

  @override
  Widget build(BuildContext context) => _StoryLoader(
    storyId: storyId,
    builder: (context, story) => _Reader(key: ValueKey(story.id), story: story),
  );
}

class _Reader extends StatefulWidget {
  const _Reader({super.key, required this.story});

  final Story story;

  @override
  State<_Reader> createState() => _ReaderState();
}

class _ReaderState extends State<_Reader> {
  int _scene = 0;
  bool _speaking = false;
  bool _paused = false;

  /// Leyendo todo el cuento seguido (pasa de escena sola).
  bool _reading = false;
  bool _finished = false;

  /// Cada narración tiene un número; si cambia, la anterior se dejó.
  int _turn = 0;

  Story get _s => widget.story;
  late LearningAudio _audio;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _audio = AppServices.of(context).audio;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) unawaited(_readFrom(0));
    });
  }

  @override
  void dispose() {
    _turn++;
    unawaited(_audio.stopVoice());
    super.dispose();
  }

  /// Narra una escena. Devuelve `false` si se interrumpió.
  Future<bool> _narrate(int scene, {bool slow = false}) async {
    final turn = ++_turn;
    setState(() {
      _scene = scene;
      _speaking = true;
      _paused = false;
    });
    await _audio.say(_s.scenes[scene].text, slow: slow);
    if (!mounted || turn != _turn) return false;
    setState(() => _speaking = false);
    if (scene == _s.scenes.length - 1) _end();
    return true;
  }

  /// Lee desde [scene] hasta el final, escena a escena.
  Future<void> _readFrom(int scene) async {
    _reading = true;
    for (var i = scene; i < _s.scenes.length; i++) {
      if (!await _narrate(i) || !_reading) return;
    }
    _reading = false;
  }

  void _end() {
    if (_finished) return;
    setState(() => _finished = true);
    AppServices.of(context).speech.markStoryHeard(_s.id);
    unawaited(_audio.play(SoundCue.star));
  }

  void _pause() {
    _turn++;
    unawaited(_audio.stopVoice());
    setState(() {
      _speaking = false;
      _paused = true;
    });
  }

  void _continue() {
    if (_reading) {
      unawaited(_readFrom(_scene));
    } else {
      unawaited(_narrate(_scene));
    }
  }

  void _goTo(int scene) {
    if (scene < 0 || scene >= _s.scenes.length) return;
    _reading = false;
    unawaited(_narrate(scene));
  }

  @override
  Widget build(BuildContext context) {
    final s = _s;
    final scene = s.scenes[_scene];
    final last = _scene == s.scenes.length - 1;
    final ink = Color.lerp(_storyColor, const Color(0xFF2A2350), 0.7)!;
    return KidScaffold(
      title: s.title,
      titleIcon: Icons.auto_stories_rounded,
      accent: _storyColor,
      backLabel: 'Volver al catálogo',
      body: LayoutBuilder(
        builder: (context, box) {
          final wide = box.maxWidth > box.maxHeight * 1.15;
          final picture = Semantics(
            label: 'Ilustración de la escena ${_scene + 1}',
            excludeSemantics: true,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: Container(
                key: ValueKey(_scene),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white, width: 4),
                  boxShadow: const [
                    BoxShadow(color: Color(0x22000000), blurRadius: 10, offset: Offset(0, 4)),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: SpeechPictureView(picture: scene.picture, tint: _storyColor),
                ),
              ),
            ),
          );
          final text = Semantics(
            container: true,
            label: 'Escena ${_scene + 1} de ${s.scenes.length}: ${scene.text}',
            excludeSemantics: true,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                // La escena que se narra se resalta.
                color: _speaking ? const Color(0xFFFFF59D) : Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _speaking ? AppColors.sun : _storyColor.withValues(alpha: 0.4),
                  width: 3,
                ),
              ),
              child: Text(
                scene.text,
                textAlign: TextAlign.center,
                style: fredoka(26, color: ink, weight: FontWeight.w500),
              ),
            ),
          );
          final dots = Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (var i = 0; i < s.scenes.length; i++)
                Container(
                  width: i == _scene ? 22 : 10,
                  height: 10,
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(
                    color: i == _scene ? _storyColor : _storyColor.withValues(alpha: 0.25),
                    borderRadius: BorderRadius.circular(5),
                  ),
                ),
            ],
          );
          Widget button(IconData icon, String label, Color color, VoidCallback? onPressed) => SizedBox(
            width: 96,
            child: SpeechActionButton(icon: icon, label: label, color: color, onPressed: onPressed),
          );
          final controls = Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              button(
                Icons.arrow_back_rounded,
                'Anterior',
                AppColors.inkSoft,
                _scene == 0 ? null : () => _goTo(_scene - 1),
              ),
              if (_speaking)
                button(Icons.pause_rounded, 'Pausar', const Color(0xFFFF7043), _pause)
              else if (_paused)
                button(Icons.play_arrow_rounded, 'Continuar', const Color(0xFF29B6F6), _continue)
              else
                button(Icons.volume_up_rounded, 'Escuchar', const Color(0xFF29B6F6), () => _goTo(_scene)),
              button(Icons.replay_rounded, 'Repetir escena', const Color(0xFF26A69A), () => _goTo(_scene)),
              button(Icons.slow_motion_video_rounded, 'Despacio', const Color(0xFFAB47BC), () {
                _reading = false;
                unawaited(_narrate(_scene, slow: true));
              }),
              button(
                Icons.arrow_forward_rounded,
                'Siguiente',
                speechAccent,
                last ? null : () => _goTo(_scene + 1),
              ),
            ],
          );
          final end = _finished
              ? Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Column(
                    children: [
                      const LoloBubble(text: '¡Fin! ¿Jugamos con el cuento?', size: 56),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        alignment: WrapAlignment.center,
                        children: [
                          SizedBox(
                            width: 150,
                            child: SpeechActionButton(
                              icon: Icons.quiz_rounded,
                              label: 'Preguntas del cuento',
                              color: const Color(0xFFFF8A65),
                              onPressed: () =>
                                  Navigator.of(context)
                                      .pushNamed(AppRoutes.speechStoryQuiz, arguments: SpeechStoryArgs(s.id)),
                            ),
                          ),
                          SizedBox(
                            width: 150,
                            child: SpeechActionButton(
                              icon: Icons.sort_rounded,
                              label: 'Ordena las escenas',
                              color: _storyColor,
                              onPressed: () => Navigator.of(context)
                                  .pushNamed(AppRoutes.speechStoryOrder, arguments: SpeechStoryArgs(s.id)),
                            ),
                          ),
                          if (practiceAllowed(context))
                            SizedBox(
                              width: 150,
                              child: SpeechActionButton(
                                icon: Icons.mic_rounded,
                                label: 'Cuéntalo tú',
                                color: const Color(0xFFE53950),
                                onPressed: () => showPracticeSheet(context, scene.text),
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                )
              : const SizedBox.shrink();
          if (wide) {
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: SizedBox(width: box.maxHeight - 40, height: box.maxHeight - 40, child: picture),
                ),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(4, 0, 16, 16),
                    children: [
                      text,
                      const SizedBox(height: 10),
                      dots,
                      const SizedBox(height: 10),
                      controls,
                      end,
                    ],
                  ),
                ),
              ],
            );
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [
              if (s.characters.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Semantics(
                    label: 'Personajes: ${s.characters.map((c) => c.name).join(', ')}',
                    excludeSemantics: true,
                    child: Wrap(
                      spacing: 10,
                      alignment: WrapAlignment.center,
                      children: [
                        for (final c in s.characters)
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              SizedBox(width: 36, height: 36, child: SpeechPictureView(picture: c.picture)),
                              const SizedBox(width: 4),
                              Text(c.name, style: fredoka(16, color: ink)),
                            ],
                          ),
                      ],
                    ),
                  ),
                ),
              Center(child: SizedBox(width: 320, height: 320, child: picture)),
              const SizedBox(height: 12),
              text,
              const SizedBox(height: 10),
              dots,
              const SizedBox(height: 12),
              controls,
              end,
            ],
          );
        },
      ),
    );
  }
}

/// Las preguntas de comprensión del cuento, con dibujos.
class StoryQuizScreen extends StatelessWidget {
  const StoryQuizScreen({super.key, required this.storyId});

  final String storyId;

  @override
  Widget build(BuildContext context) => _StoryLoader(
    storyId: storyId,
    builder: (context, story) => KidScaffold(
      title: 'Preguntas: ${story.title}',
      titleIcon: Icons.quiz_rounded,
      accent: const Color(0xFFFF8A65),
      body: SpeechQuizBody(
        build: (_) => story.questions,
        color: const Color(0xFFFF8A65),
        onFinished: () => AppServices.of(context).speech.markStoryQuizzed(story.id),
        finishedExtra: SizedBox(
          width: 190,
          child: SpeechActionButton(
            icon: Icons.sort_rounded,
            label: 'Ordena las escenas',
            color: _storyColor,
            onPressed: () =>
                Navigator.of(context)
                    .pushReplacementNamed(AppRoutes.speechStoryOrder, arguments: SpeechStoryArgs(story.id)),
          ),
        ),
      ),
    ),
  );
}

/// Ordenar tres escenas del cuento.
class StoryOrderScreen extends StatefulWidget {
  const StoryOrderScreen({super.key, required this.storyId});

  final String storyId;

  @override
  State<StoryOrderScreen> createState() => _StoryOrderScreenState();
}

class _StoryOrderScreenState extends State<StoryOrderScreen> {
  bool _done = false;

  @override
  Widget build(BuildContext context) => _StoryLoader(
    storyId: widget.storyId,
    builder: (context, story) {
      final scenes = [for (final i in story.order) story.scenes[i]];
      return KidScaffold(
        title: 'Ordena: ${story.title}',
        titleIcon: Icons.sort_rounded,
        accent: _storyColor,
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            const Align(
              alignment: Alignment.centerLeft,
              child: LoloBubble(text: '¿Qué pasó primero? Toca los dibujos en orden.', size: 56),
            ),
            const SizedBox(height: 12),
            OrderPictures(
              pictures: [for (final s in scenes) s.picture],
              labels: [for (final s in scenes) s.text],
              seed: story.id,
              color: _storyColor,
              onDone: () {
                setState(() => _done = true);
                AppServices.of(context).speech.markActivityDone('ordenar_escenas');
              },
            ),
            if (_done) ...[
              const SizedBox(height: 16),
              Center(
                child: SizedBox(
                  width: 190,
                  child: SpeechActionButton(
                    icon: Icons.auto_stories_rounded,
                    label: 'Otro cuento',
                    color: speechAccent,
                    onPressed: () =>
                        Navigator.of(context)
                            .popUntil((r) => r.settings.name == AppRoutes.speechStories || r.isFirst),
                  ),
                ),
              ),
            ],
          ],
        ),
      );
    },
  );
}
