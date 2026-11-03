import 'dart:async';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _storyColor = Color(0xFFEC407A);

/// «Mi historia»: el niño elige con dibujos quién, dónde, qué hace, con qué y
/// cómo termina; Lolo la cuenta con buena gramática. No se piden nombres,
/// fotos ni datos personales.
class MyStoryScreen extends StatefulWidget {
  const MyStoryScreen({super.key});

  @override
  State<MyStoryScreen> createState() => _MyStoryScreenState();
}

class _MyStoryScreenState extends State<MyStoryScreen> {
  StoryNoun? _character;
  StoryPlace? _place;
  StoryAction? _action;
  StoryNoun? _object;
  StoryEnding? _ending;

  static const _steps = ['Quién', 'Dónde', 'Qué hace', 'Con qué', 'Final'];

  int get _step => _character == null
      ? 0
      : _place == null
      ? 1
      : _action == null
      ? 2
      : _object == null
      ? 3
      : _ending == null
      ? 4
      : 5;

  MyStory? get _story => _ending == null
      ? null
      : MyStory(character: _character!, place: _place!, action: _action!, object: _object!, ending: _ending!);

  String _question() => switch (_step) {
    0 => '¿Quién está en tu historia?',
    1 => '¿Adónde fue ${_character!.definite}?',
    2 => '¿Qué fue a hacer?',
    3 => _action!.question,
    _ => '¿Cómo termina tu historia?',
  };

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) speak(context, '¡Vamos a inventar una historia! ${_question()}');
    });
  }

  void _choose(void Function() set, String said) {
    setState(set);
    final story = _story;
    if (story != null) {
      AppServices.of(context).speech.markStoryBuilt(story.text);
      unawaited(AppServices.of(context).audio.play(SoundCue.celebrate));
      speak(context, story.text);
    } else {
      speak(context, '$said. ${_question()}');
    }
  }

  void _back() {
    setState(() {
      switch (_step) {
        case 1:
          _character = null;
        case 2:
          _place = null;
        case 3:
          _action = null;
        case 4:
          _object = null;
        default:
          _ending = null;
      }
    });
    speak(context, _question());
  }

  void _restart() {
    setState(() {
      _character = null;
      _place = null;
      _action = null;
      _object = null;
      _ending = null;
    });
    speak(context, _question());
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Mi historia',
      titleIcon: Icons.menu_book_rounded,
      accent: _storyColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) {
          final c = content.myStory;
          if (c.isEmpty) return const Center(child: Text('Todavía no hay piezas para inventar historias.'));
          final story = _story;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            children: [
              _StepsBar(step: _step, labels: _steps),
              const SizedBox(height: 10),
              if (story == null) ..._choosing(c) else ..._result(story),
            ],
          );
        },
      ),
    );
  }

  List<Widget> _choosing(MyStoryContent c) {
    final soFar = storySoFar(character: _character, place: _place, action: _action, object: _object);
    final cards = <(String, SpeechPicture, VoidCallback)>[
      ...switch (_step) {
        0 => [
          for (final x in c.characters)
            (x.indefinite, x.picture, () => _choose(() => _character = x, x.indefinite)),
        ],
        1 => [
          for (final x in c.places)
            (x.destination, x.picture, () => _choose(() => _place = x, x.destination)),
        ],
        2 => [
          for (final x in c.actions)
            (
              'a ${x.verb}',
              x.picture,
              () => _choose(() {
                _action = x;
                if (_object != null && !x.fits(_object!)) _object = null;
              }, 'a ${x.verb}'),
            ),
        ],
        3 => [
          for (final x in c.objectsFor(_action!))
            (x.indefinite, x.picture, () => _choose(() => _object = x, x.indefinite)),
        ],
        _ => [
          for (final x in c.endings)
            (x.text(_character!, _object!), x.picture, () => _choose(() => _ending = x, '')),
        ],
      },
    ];
    final ending = _step == 4;
    return [
      Align(
        alignment: Alignment.centerLeft,
        child: LoloBubble(text: _question(), size: 56),
      ),
      if (soFar.isNotEmpty) ...[
        const SizedBox(height: 10),
        Semantics(
          container: true,
          label: 'Tu historia hasta ahora: $soFar',
          excludeSemantics: true,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: _storyColor.withValues(alpha: 0.5), width: 3),
            ),
            child: Text(
              soFar,
              textAlign: TextAlign.center,
              style: fredoka(24, color: const Color(0xFF6A1B4D)),
            ),
          ),
        ),
      ],
      const SizedBox(height: 12),
      LayoutBuilder(
        builder: (context, box) {
          final columns = ending ? (box.maxWidth > 560 ? 2 : 1) : (box.maxWidth > 560 ? 4 : 2);
          final w = (box.maxWidth - (columns - 1) * 12) / columns;
          return Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              for (final (label, picture, onTap) in cards)
                SizedBox(
                  width: w,
                  child: _ChoiceCard(label: label, picture: picture, onTap: onTap, wide: ending),
                ),
            ],
          );
        },
      ),
      if (_step > 0) ...[
        const SizedBox(height: 16),
        Center(
          child: SizedBox(
            width: 160,
            child: SpeechActionButton(
              icon: Icons.undo_rounded,
              label: 'Cambiar',
              semanticLabel: 'Cambiar lo último que elegí',
              color: AppColors.inkSoft,
              onPressed: _back,
            ),
          ),
        ),
      ],
    ];
  }

  List<Widget> _result(MyStory story) => [
    Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Semantics(
          container: true,
          image: true,
          label: 'Dibujo de tu historia',
          child: ClipRRect(
            borderRadius: BorderRadius.circular(28),
            child: SpeechPictureView(picture: story.scene, tint: _storyColor),
          ),
        ),
      ),
    ),
    const SizedBox(height: 12),
    Semantics(
      container: true,
      label: 'Tu historia: ${story.text}',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFFFF1F6),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: _storyColor, width: 3),
        ),
        child: Text(
          story.text,
          textAlign: TextAlign.center,
          style: fredoka(26, color: const Color(0xFF6A1B4D)),
        ),
      ),
    ),
    const SizedBox(height: 16),
    Wrap(
      spacing: 12,
      runSpacing: 12,
      alignment: WrapAlignment.center,
      children: [
        SizedBox(
          width: 140,
          child: SpeechActionButton(
            icon: Icons.volume_up_rounded,
            label: 'Escuchar',
            semanticLabel: 'Escuchar mi historia',
            color: const Color(0xFF29B6F6),
            onPressed: () {
              AppServices.of(context).speech.markRepeat(AppRoutes.speechMyStory);
              speak(context, story.text);
            },
          ),
        ),
        SizedBox(
          width: 140,
          child: SpeechActionButton(
            icon: Icons.slow_motion_video_rounded,
            label: 'Despacio',
            color: const Color(0xFFAB47BC),
            onPressed: () => speak(context, story.text, slow: true),
          ),
        ),
        SizedBox(
          width: 140,
          child: SpeechActionButton(
            icon: Icons.record_voice_over_rounded,
            label: 'Repite conmigo',
            color: const Color(0xFF26A69A),
            onPressed: () => speak(context, 'Repite conmigo: ${story.firstSentence}', slow: true),
          ),
        ),
        if (practiceAllowed(context))
          SizedBox(
            width: 140,
            child: SpeechActionButton(
              icon: Icons.mic_rounded,
              label: 'Grabarme',
              semanticLabel: 'Grabar mi historia',
              color: const Color(0xFFE53950),
              onPressed: () => showPracticeSheet(context, story.text),
            ),
          ),
        SizedBox(
          width: 140,
          child: SpeechActionButton(
            icon: Icons.auto_fix_high_rounded,
            label: 'Otra historia',
            color: _storyColor,
            onPressed: _restart,
          ),
        ),
      ],
    ),
  ];
}

class _StepsBar extends StatelessWidget {
  const _StepsBar({required this.step, required this.labels});

  final int step;
  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    final current = step.clamp(0, labels.length - 1);
    return Semantics(
      label: step >= labels.length
          ? 'Historia terminada'
          : 'Paso ${current + 1} de ${labels.length}: ${labels[current]}',
      excludeSemantics: true,
      child: Row(
        children: [
          for (final (i, l) in labels.indexed)
            Expanded(
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 15,
                    backgroundColor: i <= step ? _storyColor : const Color(0xFFF3D6E2),
                    child: i < step
                        ? const Icon(Icons.check_rounded, color: Colors.white, size: 18)
                        : Text('${i + 1}', style: fredoka(15, color: Colors.white)),
                  ),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      l,
                      style: fredoka(13, color: i == step ? const Color(0xFF6A1B4D) : AppColors.inkSoft),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _ChoiceCard extends StatelessWidget {
  const _ChoiceCard({required this.label, required this.picture, required this.onTap, this.wide = false});

  final String label;
  final SpeechPicture picture;
  final VoidCallback onTap;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    final text = Text(
      label,
      textAlign: wide ? TextAlign.start : TextAlign.center,
      style: fredoka(wide ? 20 : 22, color: const Color(0xFF6A1B4D)),
    );
    return Semantics(
      container: true,
      button: true,
      label: label,
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: _storyColor.withValues(alpha: 0.45), width: 3),
            boxShadow: [BoxShadow(color: _storyColor.withValues(alpha: 0.3), offset: const Offset(0, 4))],
          ),
          child: wide
              ? Row(
                  children: [
                    SizedBox.square(
                      dimension: 64,
                      child: SpeechPictureView(picture: picture, tint: _storyColor),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: text),
                  ],
                )
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SpeechPictureView(picture: picture, tint: _storyColor),
                    const SizedBox(height: 4),
                    FittedBox(fit: BoxFit.scaleDown, child: text),
                  ],
                ),
        ),
      ),
    );
  }
}
