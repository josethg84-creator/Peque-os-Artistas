import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _expressColor = Color(0xFFEC407A);
const _ink = Color(0xFF880E4F);

/// Lolo lo dice al entrar en las emociones: ninguna es buena ni mala.
const allEmotionsMatter = 'Todas las emociones son importantes. ¡Está bien decir cómo nos sentimos!';

/// «Yo puedo expresarme»: necesidades, emociones y construir una frase.
class ExpressHubScreen extends StatelessWidget {
  const ExpressHubScreen({super.key});

  static const activities = [
    (
      'Necesito…',
      '¡Pide lo que necesitas!',
      Icons.back_hand_rounded,
      Color(0xFFFFA8C8),
      AppRoutes.speechNeeds,
    ),
    (
      'Cómo me siento',
      '¡Pon nombre a tus emociones!',
      Icons.emoji_emotions_rounded,
      Color(0xFFFFD27A),
      AppRoutes.speechEmotions,
    ),
    (
      'Construye tu frase',
      'Quién + qué siente + por qué',
      Icons.view_week_rounded,
      Color(0xFF8EDDB8),
      AppRoutes.speechExpressBuilder,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Yo puedo expresarme',
      titleIcon: Icons.record_voice_over_rounded,
      accent: _expressColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: LoloBubble(
                text: '¡Vamos a aprender a decir lo que necesitamos y lo que sentimos!',
                size: 60,
              ),
            ),
          ),
          Expanded(
            child: AdaptiveGrid(
              itemCount: activities.length,
              minTileWidth: 170,
              childAspectRatio: 1.05,
              itemBuilder: (context, i) {
                final (title, subtitle, icon, color, route) = activities[i];
                return HomeMenuCard(
                  title: title,
                  subtitle: subtitle,
                  color: color,
                  art: Icon(icon, size: 72, color: Colors.white),
                  onTap: () => Navigator.of(context).pushNamed(route),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// Las siete emociones.
class EmotionsScreen extends StatefulWidget {
  const EmotionsScreen({super.key});

  @override
  State<EmotionsScreen> createState() => _EmotionsScreenState();
}

class _EmotionsScreenState extends State<EmotionsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) speak(context, allEmotionsMatter);
    });
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Cómo me siento',
      titleIcon: Icons.emoji_emotions_rounded,
      accent: _expressColor,
      backLabel: 'Volver a Yo puedo expresarme',
      body: SpeechContentBuilder(
        builder: (context, content) => LayoutBuilder(
          builder: (context, box) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // En pantallas muy bajas, el mensaje solo se oye (no tapa las tarjetas).
              if (box.maxHeight > 520 || MediaQuery.textScalerOf(context).scale(1) < 1.3)
                const Padding(
                  padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: LoloBubble(text: allEmotionsMatter, size: 56),
                  ),
                ),
              Expanded(
                child: AdaptiveGrid(
                  itemCount: content.expressions.emotions.length,
                  minTileWidth: 150,
                  childAspectRatio: 0.9,
                  itemBuilder: (context, i) {
                    final e = content.expressions.emotions[i];
                    return HomeMenuCard(
                      title: e.name,
                      subtitle: 'Estoy ${e.masculine}',
                      color: const Color(0xFFFFE0EC),
                      art: SpeechPictureView(
                        picture: KidPicture(
                          girl: i.isOdd,
                          emotion: e.face,
                          shirt: i.isOdd ? const Color(0xFFF48FB1) : const Color(0xFF64B5F6),
                        ),
                      ),
                      onTap: () =>
                          Navigator.of(context)
                              .pushNamed(AppRoutes.speechEmotion, arguments: SpeechEmotionArgs(e.id)),
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

/// Una emoción: el personaje, cómo se dice y frases de ejemplo que se
/// escuchan al tocarlas.
class EmotionScreen extends StatelessWidget {
  const EmotionScreen({super.key, required this.emotionId});

  final String emotionId;

  @override
  Widget build(BuildContext context) {
    return SpeechContentBuilder(
      builder: (context, content) {
        final list = content.expressions.emotions;
        final i = list.indexWhere((e) => e.id == emotionId);
        if (i < 0) {
          return KidScaffold(
            title: 'Cómo me siento',
            accent: _expressColor,
            body: const Center(child: Text('No encontramos esta emoción.')),
          );
        }
        final e = list[i];
        final speech = AppServices.of(context).speech;
        void say(String text, {bool slow = false}) {
          speak(context, text, slow: slow);
          speech.markExpressionPracticed('emocion:${e.id}');
        }

        return KidScaffold(
          title: e.name,
          titleIcon: Icons.emoji_emotions_rounded,
          accent: _expressColor,
          backLabel: 'Volver a las emociones',
          body: ListView(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [
              Row(
                children: [
                  SizedBox(
                    width: 120,
                    height: 120,
                    child: SpeechPictureView(
                      picture: KidPicture(emotion: e.face, armsUp: e.face == 'feliz'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 120,
                    height: 120,
                    child: SpeechPictureView(
                      picture: KidPicture(girl: true, emotion: e.face, shirt: const Color(0xFFF48FB1)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Semantics(
                header: true,
                child: Text(e.name.toUpperCase(), style: fredoka(40, color: _ink)),
              ),
              Text(
                e.masculine == e.feminine
                    ? 'Estoy ${e.masculine}.'
                    : 'Estoy ${e.masculine}. / Estoy ${e.feminine}.',
                style: fredoka(24, color: _ink, weight: FontWeight.w500),
              ),
              const SizedBox(height: 12),
              for (final ex in e.examples)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _SpeakLine(text: ex, onTap: () => say(ex)),
                ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                alignment: WrapAlignment.center,
                children: [
                  SizedBox(
                    width: 120,
                    child: SpeechActionButton(
                      icon: Icons.volume_up_rounded,
                      label: 'Escuchar',
                      color: const Color(0xFF29B6F6),
                      onPressed: () => say('${e.name}. Estoy ${e.masculine}.'),
                    ),
                  ),
                  SizedBox(
                    width: 120,
                    child: SpeechActionButton(
                      icon: Icons.slow_motion_video_rounded,
                      label: 'Despacio',
                      color: const Color(0xFFAB47BC),
                      onPressed: () => say(e.examples.first, slow: true),
                    ),
                  ),
                  if (practiceAllowed(context))
                    SizedBox(
                      width: 120,
                      child: SpeechActionButton(
                        icon: Icons.mic_rounded,
                        label: 'Practicar',
                        color: const Color(0xFFE53950),
                        onPressed: () => showPracticeSheet(context, e.examples.first),
                      ),
                    ),
                  SizedBox(
                    width: 150,
                    child: SpeechActionButton(
                      icon: Icons.view_week_rounded,
                      label: 'Construye tu frase',
                      color: const Color(0xFF26A69A),
                      onPressed: () => Navigator.of(context).pushNamed(AppRoutes.speechExpressBuilder),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SpeakLine extends StatelessWidget {
  const _SpeakLine({required this.text, required this.onTap});

  final String text;
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
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: _expressColor.withValues(alpha: 0.4), width: 2),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                text,
                style: fredoka(22, color: _ink, weight: FontWeight.w500),
              ),
            ),
            Icon(Icons.volume_up_rounded, color: _expressColor.withValues(alpha: 0.8)),
          ],
        ),
      ),
    ),
  );
}

/// Constructor QUIÉN + QUÉ SIENTE + POR QUÉ: «Yo estoy feliz porque juego con
/// mi perro.», con el género y la persona correctos.
class ExpressBuilderScreen extends StatelessWidget {
  const ExpressBuilderScreen({super.key});

  @override
  Widget build(BuildContext context) => KidScaffold(
    title: 'Construye tu frase',
    titleIcon: Icons.view_week_rounded,
    accent: _expressColor,
    backLabel: 'Volver',
    body: SpeechContentBuilder(builder: (context, content) => _ExpressBuilder(content: content.expressions)),
  );
}

class _ExpressBuilder extends StatefulWidget {
  const _ExpressBuilder({required this.content});

  final ExpressionContent content;

  @override
  State<_ExpressBuilder> createState() => _ExpressBuilderState();
}

class _ExpressBuilderState extends State<_ExpressBuilder> {
  ExpressionWho? _who;
  EmotionInfo? _emotion;
  EmotionReason? _reason;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) speak(context, '¿Quién?');
    });
  }

  String get _sentence => ExpressionContent.sentence(_who!, _emotion!, _reason!);

  String _form(EmotionInfo e) => (_who?.feminine ?? false) ? e.feminine : e.masculine;

  void _restart() {
    setState(() {
      _who = null;
      _emotion = null;
      _reason = null;
    });
    speak(context, '¿Quién?');
  }

  @override
  Widget build(BuildContext context) {
    final who = _who, emotion = _emotion, reason = _reason;
    final (String title, List<Widget> choices) = switch ((who, emotion, reason)) {
      (null, _, _) => (
        '¿Quién?',
        [
          for (final w in widget.content.who)
            _Choice(
              text: w.firstPerson ? '${w.text} (${w.feminine ? 'niña' : 'niño'})' : w.text,
              picture: w.picture,
              onTap: () {
                setState(() => _who = w);
                speak(context, '${w.text}… ¿Qué siente?');
              },
            ),
        ],
      ),
      (final w?, null, _) => (
        '¿Qué siente?',
        [
          for (final e in widget.content.emotions)
            _Choice(
              text: _form(e),
              picture: KidPicture(
                girl: w.feminine,
                emotion: e.face,
                shirt: w.feminine ? const Color(0xFFF48FB1) : const Color(0xFF64B5F6),
              ),
              onTap: () {
                setState(() => _emotion = e);
                speak(context, '${w.text} ${w.verb} ${_form(e)}… ¿Por qué?');
              },
            ),
        ],
      ),
      (final w?, final e?, null) => (
        '¿Por qué?',
        [
          for (final r in e.reasons)
            _Choice(
              text: w.firstPerson ? r.me : r.other,
              picture: r.picture,
              onTap: () {
                setState(() => _reason = r);
                speak(context, _sentence);
                AppServices.of(context).speech.markExpressionPracticed('frase:${w.id}:${e.id}:${r.id}');
              },
            ),
        ],
      ),
      _ => ('', const <Widget>[]),
    };

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        Row(
          children: [
            Expanded(
              child: _Slot(label: 'Quién', text: who?.text, picture: who?.picture),
            ),
            const Icon(Icons.add_rounded, color: AppColors.inkSoft),
            Expanded(
              child: _Slot(
                label: 'Qué siente',
                text: emotion == null ? null : _form(emotion),
                picture: emotion == null
                    ? null
                    : KidPicture(girl: who?.feminine ?? false, emotion: emotion.face),
              ),
            ),
            const Icon(Icons.add_rounded, color: AppColors.inkSoft),
            Expanded(
              child: _Slot(
                label: 'Por qué',
                text: reason == null ? null : 'porque…',
                picture: reason?.picture,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (reason != null) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: _expressColor.withValues(alpha: 0.6), width: 4),
            ),
            child: Semantics(
              label: 'Tu frase: $_sentence',
              excludeSemantics: true,
              child: Text(
                _sentence,
                textAlign: TextAlign.center,
                style: fredoka(28, color: _ink),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [
              SizedBox(
                width: 110,
                child: SpeechActionButton(
                  icon: Icons.volume_up_rounded,
                  label: 'Escuchar',
                  color: const Color(0xFF29B6F6),
                  onPressed: () => speak(context, _sentence),
                ),
              ),
              SizedBox(
                width: 110,
                child: SpeechActionButton(
                  icon: Icons.slow_motion_video_rounded,
                  label: 'Despacio',
                  color: const Color(0xFFAB47BC),
                  onPressed: () => speak(context, _sentence, slow: true),
                ),
              ),
              if (practiceAllowed(context))
                SizedBox(
                  width: 110,
                  child: SpeechActionButton(
                    icon: Icons.mic_rounded,
                    label: 'Practicar',
                    color: const Color(0xFFE53950),
                    onPressed: () => showPracticeSheet(context, _sentence),
                  ),
                ),
              SizedBox(
                width: 140,
                child: SpeechActionButton(
                  icon: Icons.add_rounded,
                  label: 'Otra frase',
                  color: speechAccent,
                  onPressed: _restart,
                ),
              ),
            ],
          ),
        ] else ...[
          Semantics(
            header: true,
            child: Text(title, style: fredoka(28, color: _ink)),
          ),
          const SizedBox(height: 8),
          LayoutBuilder(
            builder: (context, box) {
              final columns = box.maxWidth > 560 ? 4 : (choices.length > 4 ? 3 : 2);
              final w = (box.maxWidth - (columns - 1) * 10) / columns;
              return Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [for (final c in choices) SizedBox(width: w, child: c)],
              );
            },
          ),
        ],
      ],
    );
  }
}

class _Slot extends StatelessWidget {
  const _Slot({required this.label, required this.text, required this.picture});

  final String label;
  final String? text;
  final SpeechPicture? picture;

  @override
  Widget build(BuildContext context) {
    final p = picture;
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: p == null ? const Color(0xFFFFF8EC) : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: p == null ? const Color(0xFFE6D3B5) : _expressColor, width: 2.5),
      ),
      child: Column(
        children: [
          SizedBox(
            height: 60,
            child: p == null
                ? const Icon(Icons.help_outline_rounded, size: 38, color: Color(0xFFD7C3A0))
                : SpeechPictureView(picture: p, tint: _expressColor),
          ),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(text ?? label, style: fredoka(17, color: _ink)),
          ),
        ],
      ),
    );
  }
}

class _Choice extends StatelessWidget {
  const _Choice({required this.text, required this.picture, required this.onTap});

  final String text;
  final SpeechPicture picture;
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
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: _expressColor.withValues(alpha: 0.45), width: 3),
          boxShadow: [BoxShadow(color: _expressColor.withValues(alpha: 0.3), offset: const Offset(0, 4))],
        ),
        child: Column(
          children: [
            SizedBox(
              height: 80,
              child: SpeechPictureView(picture: picture, tint: _expressColor),
            ),
            const SizedBox(height: 4),
            Text(
              text,
              textAlign: TextAlign.center,
              style: fredoka(18, color: _ink),
            ),
          ],
        ),
      ),
    ),
  );
}
