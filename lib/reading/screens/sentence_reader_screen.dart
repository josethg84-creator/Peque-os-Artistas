import 'dart:async';

import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/reading_voice.dart';
import '../reading_progress.dart';
import '../sentences.dart';
import '../widgets/reading_widgets.dart';
import '../widgets/sentence_widgets.dart';
import 'reading_sentences_screen.dart';

/// «Leo mis primeras oraciones»: ilustración, oración grande con cada palabra
/// resaltada mientras suena, velocidad normal o lenta, repetir, parar, oír
/// una palabra y pasar a la anterior o la siguiente.
class SentenceReaderScreen extends StatelessWidget {
  const SentenceReaderScreen({super.key, required this.args});

  final SentenceReaderArgs args;

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: ReadingSentencesScreen.title,
      titleIcon: Icons.menu_book_rounded,
      accent: ReadingSentencesScreen.color,
      trailing: const ReadingHomeButton(),
      body: SentenceCatalogBuilder(
        builder: (context, content) => _Reader(content: content, args: args),
      ),
    );
  }
}

class _Reader extends StatefulWidget {
  const _Reader({required this.content, required this.args});

  final SentenceCatalog content;
  final SentenceReaderArgs args;

  @override
  State<_Reader> createState() => _ReaderState();
}

class _ReaderState extends State<_Reader> {
  static const color = ReadingSentencesScreen.color;

  ReadingVoice? _voice;
  late ReadingController _progress;
  late List<ReadingSentence> _list;
  int _index = 0;
  ReadingSpeed _speed = ReadingSpeed.normal;

  /// Palabra que suena ahora.
  int? _highlight;

  /// Última palabra tocada (para «Escuchar palabra»).
  int? _selected;
  bool _playing = false;
  bool _played = false;

  ReadingSentence get sentence => _list[_index];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_voice != null) return;
    final services = AppServices.of(context);
    _voice = ReadingVoice(services.audio);
    _progress = services.reading;
    _list = widget.content.ofLevel(widget.args.level);
    _index = widget.args.index.clamp(0, _list.isEmpty ? 0 : _list.length - 1);
  }

  @override
  void dispose() {
    _voice?.dispose();
    super.dispose();
  }

  Future<void> _listen([ReadingSpeed? speed]) async {
    final s = sentence;
    setState(() {
      if (speed != null) _speed = speed;
      _playing = true;
      _played = true;
    });
    final heard = await _voice!.playSentence(
      s,
      speed: _speed,
      onWord: (i) {
        if (mounted) setState(() => _highlight = i);
      },
    );
    if (!mounted) return;
    if (heard) _progress.recordSentenceHeard(s.id);
    if (identical(s, sentence)) setState(() => _playing = false);
  }

  Future<void> _stop() async {
    await _voice!.stop();
    if (mounted) setState(() => _playing = false);
  }

  Future<void> _word(int i) async {
    final w = sentence.words[i];
    setState(() {
      _selected = i;
      _highlight = i;
      _playing = false;
    });
    _progress.recordWordPlayed(w.text);
    await _voice!.play(w.audio, speed: _speed);
    if (mounted && _highlight == i) setState(() => _highlight = null);
  }

  void _go(int delta) {
    unawaited(_voice!.stop());
    setState(() {
      _index = (_index + delta).clamp(0, _list.length - 1);
      _highlight = null;
      _selected = null;
      _playing = false;
      _played = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_list.isEmpty) return const Center(child: Text('Todavía no hay oraciones en este nivel.'));
    return LayoutBuilder(
      builder: (context, box) {
        final wide = box.maxWidth >= 760;
        final s = sentence;
        final picture = SizedBox(
          height: wide ? 260 : 190,
          child: SentencePicture(sentence: s, color: color),
        );
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
                  ReadingVoiceNotice(voice: _voice!),
                  Text(
                    'Nivel ${widget.args.level}: ${widget.content.levelNames[widget.args.level] ?? ''}',
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 6),
                  ReadingProgressBar(done: _index + 1, total: _list.length, label: 'Oración', color: color),
                  const SizedBox(height: 12),
                  picture,
                  const SizedBox(height: 14),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                      border: Border.all(color: Color.lerp(color, Colors.white, 0.4)!, width: 3),
                    ),
                    child: SentenceWords(
                      sentence: s,
                      color: color,
                      highlighted: _highlight,
                      fontSize: wide ? 46 : 34,
                      onTapWord: _word,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text('Toca una palabra para oírla.', style: Theme.of(context).textTheme.bodyMedium),
                  _HighlightNotice(voice: _voice!, speed: _speed, playing: _playing, played: _played),
                  const SizedBox(height: 12),
                  _SpeedSelector(speed: _speed, onChanged: (v) => setState(() => _speed = v)),
                  const SizedBox(height: 12),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      SizedBox(
                        width: 132,
                        child: SpeechActionButton(
                          icon: Icons.volume_up_rounded,
                          label: 'Escuchar',
                          semanticLabel: 'Escuchar la oración',
                          color: AppColors.sky,
                          onPressed: () => unawaited(_listen()),
                        ),
                      ),
                      SizedBox(
                        width: 132,
                        child: SpeechActionButton(
                          icon: Icons.replay_rounded,
                          label: 'Repetir',
                          semanticLabel: 'Repetir la oración',
                          color: AppColors.grape,
                          onPressed: _played ? () => unawaited(_listen()) : null,
                        ),
                      ),
                      SizedBox(
                        width: 132,
                        child: SpeechActionButton(
                          icon: Icons.record_voice_over_rounded,
                          label: 'Escuchar palabra',
                          semanticLabel: _selected == null
                              ? 'Escuchar palabra: primero toca una palabra'
                              : 'Escuchar la palabra ${s.words[_selected!].text}',
                          color: AppColors.leaf,
                          onPressed: _selected == null ? null : () => unawaited(_word(_selected!)),
                        ),
                      ),
                      SizedBox(
                        width: 132,
                        child: SpeechActionButton(
                          icon: Icons.stop_rounded,
                          label: 'Parar',
                          semanticLabel: 'Parar el audio',
                          color: AppColors.coral,
                          onPressed: _playing ? () => unawaited(_stop()) : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  ReadingStepNav(
                    index: _index,
                    total: _list.length,
                    onPrevious: _index > 0 ? () => _go(-1) : null,
                    onNext: _index < _list.length - 1 ? () => _go(1) : null,
                    nextLabel: 'Siguiente oración',
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: 280,
                    child: BigActionButton(
                      label: 'Responder la pregunta',
                      icon: Icons.quiz_rounded,
                      color: AppColors.leaf,
                      onPressed: () {
                        unawaited(_voice!.stop());
                        Navigator.of(context).pushNamed(
                          AppRoutes.readingSentencesGame,
                          arguments: SentenceGameArgs(
                            activity: SentenceActivity.question,
                            level: s.level,
                            sentenceId: s.id,
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Normal / Lento (con texto e icono, no solo color).
class _SpeedSelector extends StatelessWidget {
  const _SpeedSelector({required this.speed, required this.onChanged});

  final ReadingSpeed speed;
  final ValueChanged<ReadingSpeed> onChanged;

  @override
  Widget build(BuildContext context) {
    Widget option(ReadingSpeed v, String label, IconData icon) {
      final on = v == speed;
      return Semantics(
        button: true,
        selected: on,
        label: 'Velocidad $label',
        excludeSemantics: true,
        onTap: () => onChanged(v),
        child: GestureDetector(
          onTap: () => onChanged(v),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            constraints: const BoxConstraints(minHeight: 52),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            decoration: BoxDecoration(
              color: on ? Color.lerp(ReadingSentencesScreen.color, Colors.white, 0.75) : Colors.white,
              borderRadius: BorderRadius.circular(26),
              border: Border.all(color: ReadingSentencesScreen.color, width: on ? 4 : 2),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(on ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded, size: 22),
                const SizedBox(width: 6),
                Icon(icon, size: 24),
                const SizedBox(width: 6),
                Text(label, style: fredoka(20, color: AppColors.ink)),
              ],
            ),
          ),
        ),
      );
    }

    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 10,
      runSpacing: 10,
      children: [
        option(ReadingSpeed.normal, 'Normal', Icons.directions_walk_rounded),
        option(ReadingSpeed.slow, 'Lento', Icons.slow_motion_video_rounded),
      ],
    );
  }
}

/// Explica cómo se resaltan las palabras cuando la voz no lo permite.
class _HighlightNotice extends StatelessWidget {
  const _HighlightNotice({
    required this.voice,
    required this.speed,
    required this.playing,
    required this.played,
  });

  final ReadingVoice voice;
  final ReadingSpeed speed;
  final bool playing;
  final bool played;

  static const text =
      'Esta voz no avisa de qué palabra está diciendo, así que a velocidad normal no se resaltan. '
      'Con «Lento» se lee palabra por palabra y cada una se resalta mientras suena.';

  @override
  Widget build(BuildContext context) {
    if (!played || playing || voice.lastHighlight != SentenceHighlight.none || speed == ReadingSpeed.slow) {
      return const SizedBox.shrink();
    }
    return Semantics(
      liveRegion: true,
      label: text,
      excludeSemantics: true,
      child: Container(
        margin: const EdgeInsets.only(top: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFFE8F1FF),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.sky, width: 2),
        ),
        child: Row(
          children: [
            const Icon(Icons.info_outline_rounded, color: AppColors.sky),
            const SizedBox(width: 10),
            Expanded(child: Text(text, style: Theme.of(context).textTheme.bodyMedium)),
          ],
        ),
      ),
    );
  }
}
