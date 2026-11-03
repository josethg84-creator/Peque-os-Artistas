import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../speech_progress.dart';
import '../word_games.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';
import 'speech_quiz_screen.dart';

const wordGamesColor = Color(0xFF5C9DED);
const soundsColor = Color(0xFF7CB342);

/// Elegir el nivel (fácil, medio, difícil). Empieza en el de los ajustes y se
/// puede cambiar siempre: ningún nivel está bloqueado.
class LevelPicker extends StatelessWidget {
  const LevelPicker({super.key, required this.level, required this.onChanged, required this.color});

  final int level;
  final ValueChanged<int> onChanged;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: [
        for (final l in [1, 2, 3])
          Semantics(
            container: true,
            button: true,
            selected: l == level,
            label: 'Nivel ${SpeechPreferences.levelName(l)}',
            excludeSemantics: true,
            onTap: () => onChanged(l),
            child: GestureDetector(
              onTap: () => onChanged(l),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                constraints: const BoxConstraints(minWidth: 96, minHeight: 56),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: l == level ? color : Colors.white,
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(color: color, width: 3),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (var k = 0; k < l; k++)
                      Icon(Icons.star_rounded, size: 22, color: l == level ? Colors.white : AppColors.sun),
                    const SizedBox(width: 6),
                    Flexible(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          SpeechPreferences.levelName(l),
                          style: fredoka(18, color: l == level ? Colors.white : const Color(0xFF2A2350)),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// Un menú de juegos con nivel (lo usan «Juegos de palabras» y «Sílabas y sonidos»).
class _GamesHub extends StatefulWidget {
  const _GamesHub({
    required this.title,
    required this.icon,
    required this.color,
    required this.lolo,
    required this.games,
  });

  final String title;
  final IconData icon;
  final Color color;
  final String lolo;

  /// (título, subtítulo, icono, color, ruta, juego).
  final List<(String, String, IconData, Color, String, String)> games;

  @override
  State<_GamesHub> createState() => _GamesHubState();
}

class _GamesHubState extends State<_GamesHub> {
  int? _level;

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    final level = _level ?? speech.progress.preferences.level;
    return KidScaffold(
      title: widget.title,
      titleIcon: widget.icon,
      accent: widget.color,
      backLabel: 'Volver a Aprendo a Hablar',
      body: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Align(
                  alignment: Alignment.centerLeft,
                  child: LoloBubble(text: widget.lolo, size: 56),
                ),
                const SizedBox(height: 10),
                LevelPicker(level: level, color: widget.color, onChanged: (l) => setState(() => _level = l)),
              ]),
            ),
          ),
          AdaptiveSliverGrid(
            itemCount: widget.games.length,
            minTileWidth: 170,
            childAspectRatio: 1,
            itemBuilder: (context, i) {
              final (title, subtitle, icon, color, route, game) = widget.games[i];
              final key = WordGame.byId(game)?.progressKey ?? 'juego_$game';
              final played = speech.progress.activitiesDone[key] ?? 0;
              return HomeMenuCard(
                title: title,
                subtitle: played > 0 ? '$subtitle · ¡Jugado $played!' : subtitle,
                color: color,
                art: SpeechActivityArt(icon: icon, color: color),
                onTap: () {
                  speech.markVisit(route);
                  Navigator.of(context).pushNamed(route, arguments: SpeechGameArgs(game, level: level));
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

/// «Juegos de palabras»: relacionar palabra e imagen, ordenar por grupos y
/// completar frases con el vocabulario.
class WordGamesScreen extends StatelessWidget {
  const WordGamesScreen({super.key});

  @override
  Widget build(BuildContext context) => const _GamesHub(
    title: 'Juegos de palabras',
    icon: Icons.extension_rounded,
    color: wordGamesColor,
    lolo: '¡Juguemos con las palabras! Elige el nivel y el juego.',
    games: [
      (
        '¿Cuál es?',
        'Toca el dibujo',
        Icons.touch_app_rounded,
        Color(0xFF9FC5F8),
        AppRoutes.speechWordGame,
        'cual',
      ),
      (
        '¿De qué grupo es?',
        'Ordena por grupos',
        Icons.category_rounded,
        Color(0xFFFFCC80),
        AppRoutes.speechWordGame,
        'grupo',
      ),
      (
        'Completa la frase',
        'Falta una palabra',
        Icons.edit_note_rounded,
        Color(0xFFA5D6A7),
        AppRoutes.speechWordGame,
        'frase',
      ),
    ],
  );
}

/// «Sílabas y sonidos»: conciencia fonológica, siempre tocando (sin
/// reconocimiento de voz).
class SoundsScreen extends StatelessWidget {
  const SoundsScreen({super.key});

  @override
  Widget build(BuildContext context) => const _GamesHub(
    title: 'Sílabas y sonidos',
    icon: Icons.music_note_rounded,
    color: soundsColor,
    lolo: '¡Vamos a escuchar los sonidos de las palabras!',
    games: [
      (
        'Palmas y sílabas',
        'Una palma por sílaba',
        Icons.sign_language_rounded,
        Color(0xFFC5E1A5),
        AppRoutes.speechClaps,
        'palmas',
      ),
      (
        '¿Con qué empieza?',
        'Empiezan igual',
        Icons.first_page_rounded,
        Color(0xFFFFE082),
        AppRoutes.speechSoundGame,
        'empieza',
      ),
      (
        'Palabras que riman',
        'Gato, pato…',
        Icons.music_note_rounded,
        Color(0xFFF8BBD0),
        AppRoutes.speechSoundGame,
        'rimas',
      ),
      (
        'Escucho y encuentro',
        'Oye y toca',
        Icons.hearing_rounded,
        Color(0xFFB3E5FC),
        AppRoutes.speechSoundGame,
        'encuentro',
      ),
    ],
  );
}

/// Una ronda de un juego de palabras o de sonidos.
class WordGameScreen extends StatelessWidget {
  const WordGameScreen({super.key, required this.game, this.level, this.seed, this.route});

  final WordGame game;
  final int? level;
  final int? seed;

  /// La ruta por la que se abrió (para anotar las repeticiones).
  final String? route;

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    final level = this.level ?? speech.progress.preferences.level;
    final sound = game == WordGame.empieza || game == WordGame.rimas || game == WordGame.encuentro;
    final color = sound ? soundsColor : wordGamesColor;
    return KidScaffold(
      title: game.title,
      titleIcon: sound ? Icons.music_note_rounded : Icons.extension_rounded,
      accent: color,
      backLabel: sound ? 'Volver a Sílabas y sonidos' : 'Volver a Juegos de palabras',
      body: SpeechContentBuilder(
        builder: (context, content) => SpeechQuizBody(
          seed: seed,
          color: color,
          slowButton: true,
          repeatRoute: route ?? (sound ? AppRoutes.speechSoundGame : AppRoutes.speechWordGame),
          build: (Random r) => buildWordGame(game, content, r, level: level),
          onFinished: () {
            speech.markActivityDone(game.progressKey);
            if (sound) speech.markSoundGame();
          },
        ),
      ),
    );
  }
}

/// «Palmas y sílabas»: Lolo dice una palabra; el niño da una palma por sílaba
/// y luego toca «¡Listo!». Al acertar (o si se equivoca, para aprender) se ven
/// y se oyen las sílabas: MA-RI-PO-SA.
class ClapsScreen extends StatefulWidget {
  const ClapsScreen({super.key, this.level, this.seed});

  final int? level;
  final int? seed;

  @override
  State<ClapsScreen> createState() => _ClapsScreenState();
}

class _ClapsScreenState extends State<ClapsScreen> {
  List<SpeechWord>? _words;
  int _index = 0;
  int _claps = 0;

  /// Las sílabas a la vista (tras comprobar).
  bool _shown = false;
  bool _right = false;
  int? _level;

  SpeechWord get _w => _words![_index];
  bool get _finished => _words != null && _index >= _words!.length;

  void _start(SpeechContent content, int level) {
    _words = clapWords(content, Random(widget.seed), level: level);
    _index = 0;
    _reset();
    WidgetsBinding.instance.addPostFrameCallback((_) => _say());
  }

  void _reset() {
    _claps = 0;
    _shown = false;
    _right = false;
  }

  void _say() {
    if (!mounted || _finished || _words!.isEmpty) return;
    speak(context, 'Escucha: ${_w.text}. Da una palma por cada sílaba.');
  }

  void _syllables() {
    AppServices.of(context).speech.markRepeat(AppRoutes.speechClaps);
    speak(context, '${_w.syllables.join(', ')}. ${_w.text}.', slow: true);
  }

  void _clap() {
    if (_shown) return;
    setState(() => _claps++);
    unawaited(AppServices.of(context).audio.play(SoundCue.tap));
  }

  void _check() {
    final n = _w.syllables.length;
    final audio = AppServices.of(context).audio;
    final syllables = _w.syllables.join(', ');
    if (_claps == n) {
      setState(() {
        _shown = true;
        _right = true;
      });
      AppServices.of(context).speech
        ..markSyllables(_w.id)
        ..markAnswer();
      unawaited(audio.play(SoundCue.correct));
      speak(context, '¡Muy bien! $syllables. ¡$n ${n == 1 ? 'palma' : 'palmas'}!');
    } else {
      setState(() {
        _shown = true;
        _claps = 0;
      });
      unawaited(audio.play(SoundCue.tryAgain));
      speak(context, '¡Casi! Escucha otra vez: $syllables. Ahora da tú las palmas.');
    }
  }

  void _retry() => setState(_reset);

  void _next() {
    setState(() {
      _index++;
      _reset();
    });
    if (_finished) {
      AppServices.of(context).speech.markActivityDone('juego_palmas');
      unawaited(AppServices.of(context).audio.play(SoundCue.celebrate));
      speak(context, '¡Terminaste! ¡Qué bien escuchas las sílabas!');
    } else {
      _say();
    }
  }

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Palmas y sílabas',
      titleIcon: Icons.sign_language_rounded,
      accent: soundsColor,
      backLabel: 'Volver a Sílabas y sonidos',
      body: SpeechContentBuilder(
        builder: (context, content) {
          final level = _level ?? widget.level ?? speech.progress.preferences.level;
          if (_words == null) _start(content, level);
          if (_words!.isEmpty) return const Center(child: Text('Todavía no hay palabras para este nivel.'));
          if (_finished) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const LoloBubble(text: '¡Terminaste! ¡Qué bien escuchas las sílabas!', size: 90),
                    const SizedBox(height: 20),
                    LevelPicker(
                      level: level,
                      color: soundsColor,
                      onChanged: (l) => setState(() {
                        _level = l;
                        _start(content, l);
                      }),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: 170,
                      child: SpeechActionButton(
                        icon: Icons.replay_rounded,
                        label: 'Jugar otra vez',
                        color: soundsColor,
                        onPressed: () => setState(() => _start(content, level)),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }
          final w = _w;
          final n = w.syllables.length;
          final ink = Color.lerp(soundsColor, const Color(0xFF2A2350), 0.65)!;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            children: [
              Text(
                'Palabra ${_index + 1} de ${_words!.length}',
                style: fredoka(16, color: AppColors.inkSoft),
              ),
              const SizedBox(height: 8),
              Center(
                child: SizedBox.square(
                  dimension: 170,
                  child: Semantics(
                    container: true,
                    label: w.text,
                    excludeSemantics: true,
                    child: SpeechPictureView(picture: w.picture, tint: soundsColor),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Semantics(
                container: true,
                liveRegion: true,
                label: _shown ? 'Sílabas: ${w.syllables.join(' - ')}' : 'Palabra: ${w.text}',
                excludeSemantics: true,
                child: Center(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      _shown ? w.syllables.map((s) => s.toUpperCase()).join(' - ') : w.text.toUpperCase(),
                      style: fredoka(44, color: ink),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              // Las palmas dadas.
              Semantics(
                container: true,
                label: 'Palmas: $_claps',
                excludeSemantics: true,
                child: Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 6,
                  children: [
                    for (var k = 0; k < (_shown && _right ? n : _claps); k++)
                      const Icon(Icons.sign_language_rounded, color: Color(0xFFFFA000), size: 40),
                    if (_claps == 0 && !(_shown && _right))
                      Text('Toca la mano grande', style: fredoka(18, color: AppColors.inkSoft)),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              if (!_shown)
                Center(
                  child: Semantics(
                    container: true,
                    button: true,
                    label: 'Dar una palma',
                    excludeSemantics: true,
                    onTap: _clap,
                    child: GestureDetector(
                      onTap: _clap,
                      child: Container(
                        width: 140,
                        height: 140,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: const RadialGradient(colors: [Color(0xFFFFE082), Color(0xFFFFB300)]),
                          border: Border.all(color: Colors.white, width: 5),
                          boxShadow: const [
                            BoxShadow(color: Color(0x33000000), blurRadius: 12, offset: Offset(0, 6)),
                          ],
                        ),
                        child: const Icon(Icons.sign_language_rounded, size: 80, color: Colors.white),
                      ),
                    ),
                  ),
                ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 12,
                runSpacing: 10,
                alignment: WrapAlignment.center,
                children: [
                  SizedBox(
                    width: 120,
                    child: SpeechActionButton(
                      icon: Icons.volume_up_rounded,
                      label: 'Escuchar',
                      color: const Color(0xFF29B6F6),
                      onPressed: () {
                        speech.markRepeat(AppRoutes.speechClaps);
                        _say();
                      },
                    ),
                  ),
                  SizedBox(
                    width: 120,
                    child: SpeechActionButton(
                      icon: Icons.slow_motion_video_rounded,
                      label: 'Sílabas',
                      semanticLabel: 'Escuchar las sílabas despacio',
                      color: const Color(0xFF7E57C2),
                      onPressed: _syllables,
                    ),
                  ),
                  if (!_shown)
                    SizedBox(
                      width: 120,
                      child: SpeechActionButton(
                        icon: Icons.check_rounded,
                        label: '¡Listo!',
                        color: soundsColor,
                        onPressed: _claps == 0 ? null : _check,
                      ),
                    )
                  else if (_right)
                    SizedBox(
                      width: 120,
                      child: SpeechActionButton(
                        icon: Icons.arrow_forward_rounded,
                        label: _index == _words!.length - 1 ? 'Terminar' : 'Siguiente',
                        color: speechAccent,
                        onPressed: _next,
                      ),
                    )
                  else
                    SizedBox(
                      width: 120,
                      child: SpeechActionButton(
                        icon: Icons.replay_rounded,
                        label: 'Otra vez',
                        semanticLabel: 'Dar las palmas otra vez',
                        color: soundsColor,
                        onPressed: _retry,
                      ),
                    ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}
