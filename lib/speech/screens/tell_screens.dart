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
import '../widgets/order_pictures.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _tellColor = Color(0xFFFFA726);
const _ink = Color(0xFF7A4100);

/// «Ahora cuéntamelo tú»: las secuencias de dibujos.
class TellListScreen extends StatelessWidget {
  const TellListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Ahora cuéntamelo tú',
      titleIcon: Icons.photo_library_rounded,
      accent: _tellColor,
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
                  child: LoloBubble(text: '¡Ahora tú eres quien cuenta la historia!', size: 60),
                ),
              ),
              Expanded(
                child: AdaptiveGrid(
                  itemCount: content.tell.length,
                  minTileWidth: 160,
                  childAspectRatio: 0.9,
                  itemBuilder: (context, i) {
                    final t = content.tell[i];
                    return HomeMenuCard(
                      title: t.title,
                      subtitle: speech.progress.storiesTold.contains(t.id)
                          ? '¡Ya la contaste!'
                          : '${t.steps.length} dibujos',
                      color: const Color(0xFFFFE0B2),
                      art: Padding(
                        padding: const EdgeInsets.all(2),
                        child: SpeechPictureView(picture: t.steps.last.picture),
                      ),
                      onTap: () =>
                          Navigator.of(context)
                              .pushNamed(AppRoutes.speechTell, arguments: SpeechTellArgs(t.id)),
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

/// Una historia: mirar los dibujos, ordenarlos, contar cada uno eligiendo una
/// frase (con preguntas de Lolo), escuchar la historia completa y, si quiere,
/// grabarla con su voz.
class TellScreen extends StatelessWidget {
  const TellScreen({super.key, required this.sequenceId});

  final String sequenceId;

  @override
  Widget build(BuildContext context) {
    return SpeechContentBuilder(
      builder: (context, content) {
        final seq = content.tell.where((t) => t.id == sequenceId).firstOrNull;
        if (seq == null) {
          return KidScaffold(
            title: 'Ahora cuéntamelo tú',
            accent: _tellColor,
            body: const Center(child: Text('No encontramos esta historia.')),
          );
        }
        return _Tell(key: ValueKey(seq.id), seq: seq);
      },
    );
  }
}

enum _Stage { look, order, tell, story }

class _Tell extends StatefulWidget {
  const _Tell({super.key, required this.seq});

  final TellSequence seq;

  @override
  State<_Tell> createState() => _TellState();
}

class _TellState extends State<_Tell> {
  _Stage _stage = _Stage.look;
  bool _ordered = false;

  /// Paso que se está contando.
  int _step = 0;
  int _misses = 0;

  /// Frases elegidas por el niño, en orden.
  final _told = <String>[];

  TellSequence get _s => widget.seq;

  /// Las frases que se ofrecen en un paso: la suya y dos de otros pasos.
  late final List<List<String>> _options = [
    for (var i = 0; i < _s.steps.length; i++)
      () {
        final others = [
          for (var j = 0; j < _s.steps.length; j++)
            if (j != i) _s.steps[j].phrase,
        ]..shuffle(Random(_s.id.hashCode + i));
        return [_s.steps[i].phrase, ...others.take(2)]..shuffle(Random(_s.id.hashCode * 7 + i));
      }(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) speak(context, 'Mira bien los dibujos. ¿Qué crees que pasa?');
    });
  }

  void _toOrder() {
    setState(() => _stage = _Stage.order);
    speak(context, '¿Qué pasó primero? Toca los dibujos en orden.');
  }

  void _toTell() {
    setState(() {
      _stage = _Stage.tell;
      _step = 0;
    });
    speak(context, _s.steps.first.question);
  }

  void _choose(String phrase) {
    final audio = AppServices.of(context).audio;
    if (phrase == _s.steps[_step].phrase) {
      unawaited(audio.play(SoundCue.correct));
      speak(context, phrase);
      setState(() {
        _told.add(phrase);
        _misses = 0;
        _step++;
      });
      if (_step < _s.steps.length) {
        unawaited(audio.say(_s.steps[_step].question, mode: VoiceMode.queue));
      } else {
        _toStory();
      }
    } else {
      setState(() => _misses++);
      unawaited(audio.play(SoundCue.tryAgain));
      speak(context, _misses >= 2 ? 'Mira la frase que brilla.' : '¡Casi! Mira bien el dibujo.');
    }
  }

  void _toStory() {
    setState(() => _stage = _Stage.story);
    AppServices.of(context).speech.markStoryTold(_s.id);
    unawaited(AppServices.of(context).audio.play(SoundCue.celebrate));
    unawaited(
      AppServices.of(context).audio.say('¡Qué bien lo contaste! Escucha tu historia.', mode: VoiceMode.queue),
    );
  }

  Future<void> _listenStory() async {
    final audio = AppServices.of(context).audio;
    await audio.say(_told.join(' '));
    await audio.say(_s.ending, mode: VoiceMode.queue);
  }

  void _again() {
    setState(() {
      _stage = _Stage.look;
      _step = 0;
      _misses = 0;
      _told.clear();
      _ordered = false;
    });
    speak(context, 'Mira bien los dibujos. ¿Qué crees que pasa?');
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: _s.title,
      titleIcon: Icons.photo_library_rounded,
      accent: _tellColor,
      backLabel: 'Volver a las historias',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          _Steps(stage: _stage),
          const SizedBox(height: 10),
          ...switch (_stage) {
            _Stage.look => _look(),
            _Stage.order => _order(),
            _Stage.tell => _tell(),
            _Stage.story => _story(),
          },
        ],
      ),
    );
  }

  List<Widget> _look() {
    final shuffled = OrderPictures.shuffled(_s.steps.length, _s.id);
    return [
      const Align(
        alignment: Alignment.centerLeft,
        child: LoloBubble(text: 'Mira bien los dibujos. ¿Qué crees que pasa?', size: 56),
      ),
      const SizedBox(height: 12),
      LayoutBuilder(
        builder: (context, box) {
          final side = min(170.0, (box.maxWidth - 10) / 2);
          return Wrap(
            spacing: 10,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [
              for (final i in shuffled)
                Semantics(
                  label: 'Dibujo de la historia',
                  excludeSemantics: true,
                  child: SizedBox(
                    width: side,
                    height: side,
                    child: SpeechPictureView(picture: _s.steps[i].picture),
                  ),
                ),
            ],
          );
        },
      ),
      const SizedBox(height: 16),
      Center(
        child: SizedBox(
          width: 220,
          child: SpeechActionButton(
            icon: Icons.sort_rounded,
            label: '¡Vamos a ordenarlos!',
            color: _tellColor,
            onPressed: _toOrder,
          ),
        ),
      ),
    ];
  }

  List<Widget> _order() => [
    const Align(
      alignment: Alignment.centerLeft,
      child: LoloBubble(text: '¿Qué pasó primero? ¿Y después?', size: 56),
    ),
    const SizedBox(height: 12),
    OrderPictures(
      pictures: [for (final s in _s.steps) s.picture],
      labels: [for (final s in _s.steps) s.phrase],
      seed: _s.id,
      color: _tellColor,
      onDone: () => setState(() => _ordered = true),
    ),
    const SizedBox(height: 16),
    if (_ordered)
      Center(
        child: SizedBox(
          width: 220,
          child: SpeechActionButton(
            icon: Icons.record_voice_over_rounded,
            label: '¡Ahora cuéntalo!',
            color: speechAccent,
            onPressed: _toTell,
          ),
        ),
      ),
  ];

  List<Widget> _tell() {
    final step = _s.steps[_step];
    return [
      Row(
        children: [
          Expanded(child: LoloBubble(text: step.question, size: 52)),
          SizedBox(
            width: 96,
            child: SpeechActionButton(
              icon: Icons.volume_up_rounded,
              label: 'Escuchar',
              color: const Color(0xFF29B6F6),
              onPressed: () => speak(context, step.question),
            ),
          ),
        ],
      ),
      const SizedBox(height: 10),
      Center(
        child: Semantics(
          label: 'Dibujo ${_step + 1} de ${_s.steps.length}',
          excludeSemantics: true,
          child: SizedBox(width: 220, height: 220, child: SpeechPictureView(picture: step.picture)),
        ),
      ),
      const SizedBox(height: 12),
      for (final phrase in _options[_step])
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: _PhraseCard(
            text: phrase,
            highlight: _misses >= 2 && phrase == step.phrase,
            onTap: () => _choose(phrase),
          ),
        ),
      if (_told.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text('Tu historia hasta ahora:', style: fredoka(18, color: _ink)),
        Text(
          _told.join(' '),
          style: fredoka(20, color: _ink, weight: FontWeight.w500),
        ),
      ],
    ];
  }

  List<Widget> _story() => [
    const Align(
      alignment: Alignment.centerLeft,
      child: LoloBubble(text: '¡Qué bien lo contaste! Escucha tu historia.', size: 56),
    ),
    const SizedBox(height: 12),
    for (final (i, s) in _s.steps.indexed)
      Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            SizedBox(width: 90, height: 90, child: SpeechPictureView(picture: s.picture)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                '${i + 1}. ${_told[i]}',
                style: fredoka(20, color: _ink, weight: FontWeight.w500),
              ),
            ),
          ],
        ),
      ),
    Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _tellColor, width: 3),
      ),
      child: Semantics(
        label: 'Tu historia: ${_s.ending}',
        excludeSemantics: true,
        child: Text(
          _s.ending,
          textAlign: TextAlign.center,
          style: fredoka(24, color: _ink),
        ),
      ),
    ),
    const SizedBox(height: 14),
    Wrap(
      spacing: 10,
      runSpacing: 10,
      alignment: WrapAlignment.center,
      children: [
        SizedBox(
          width: 150,
          child: SpeechActionButton(
            icon: Icons.volume_up_rounded,
            label: 'Escuchar mi historia',
            color: const Color(0xFF29B6F6),
            onPressed: () => unawaited(_listenStory()),
          ),
        ),
        if (practiceAllowed(context))
          SizedBox(
            width: 150,
            child: SpeechActionButton(
              icon: Icons.mic_rounded,
              label: 'Grabar mi historia',
              color: const Color(0xFFE53950),
              onPressed: () => showPracticeSheet(context, _s.ending),
            ),
          ),
        SizedBox(
          width: 150,
          child: SpeechActionButton(
            icon: Icons.replay_rounded,
            label: 'Contar otra vez',
            color: _tellColor,
            onPressed: _again,
          ),
        ),
        SizedBox(
          width: 150,
          child: SpeechActionButton(
            icon: Icons.photo_library_rounded,
            label: 'Otra historia',
            color: speechAccent,
            onPressed: () => Navigator.of(context).maybePop(),
          ),
        ),
      ],
    ),
  ];
}

/// Los pasos de la actividad, arriba: mirar, ordenar, contar, escuchar.
class _Steps extends StatelessWidget {
  const _Steps({required this.stage});

  final _Stage stage;

  @override
  Widget build(BuildContext context) {
    const labels = ['Mirar', 'Ordenar', 'Contar', 'Escuchar'];
    return Semantics(
      label: 'Paso ${stage.index + 1} de 4: ${labels[stage.index]}',
      excludeSemantics: true,
      child: Row(
        children: [
          for (final (i, l) in labels.indexed) ...[
            if (i > 0)
              Expanded(
                child: Container(height: 3, color: i <= stage.index ? _tellColor : const Color(0xFFE6D3B5)),
              ),
            SizedBox(
              width: 60,
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 16,
                    backgroundColor: i <= stage.index ? _tellColor : const Color(0xFFE6D3B5),
                    child: Text('${i + 1}', style: fredoka(16, color: Colors.white)),
                  ),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(l, style: fredoka(13, color: i == stage.index ? _ink : AppColors.inkSoft)),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PhraseCard extends StatelessWidget {
  const _PhraseCard({required this.text, required this.highlight, required this.onTap});

  final String text;
  final bool highlight;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    button: true,
    label: text,
    excludeSemantics: true,
    onTap: onTap,
    child: GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: highlight ? const Color(0xFFFFF59D) : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: highlight ? AppColors.sun : _tellColor.withValues(alpha: 0.5),
            width: highlight ? 4 : 2.5,
          ),
          boxShadow: [BoxShadow(color: _tellColor.withValues(alpha: 0.3), offset: const Offset(0, 3))],
        ),
        child: Text(
          text,
          style: fredoka(22, color: _ink, weight: FontWeight.w500),
        ),
      ),
    ),
  );
}
