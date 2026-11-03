import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/order_words.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _sentenceColor = Color(0xFF26A69A);

/// «Construyo oraciones»: sus cuatro actividades.
class SentencesHubScreen extends StatelessWidget {
  const SentencesHubScreen({super.key});

  static const activities = [
    (
      'Construye una oración',
      '¿Quién? ¿Qué hace? ¿Qué?',
      Icons.view_week_rounded,
      Color(0xFF8EDDB8),
      AppRoutes.speechBuilder,
    ),
    (
      'Ordena la oración',
      '¡De 3, 4 y más palabras!',
      Icons.sort_rounded,
      Color(0xFF8FCBFF),
      AppRoutes.speechOrder,
    ),
    (
      'Completa la oración',
      '¿Qué palabra falta?',
      Icons.edit_note_rounded,
      Color(0xFFFFD27A),
      AppRoutes.speechComplete,
    ),
    (
      '¿Pregunta o afirmación?',
      '¿Lleva signos de pregunta?',
      Icons.help_center_rounded,
      Color(0xFFC3A9F5),
      AppRoutes.speechQuestion,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Construyo oraciones',
      titleIcon: Icons.view_week_rounded,
      accent: _sentenceColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: LoloBubble(text: '¡Vamos a juntar palabras para formar oraciones!', size: 60),
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

/// Constructor visual: se elige quién, qué hace y qué, con dibujos, y Lolo dice
/// la oración completa («El niño come una manzana.»).
class SentenceBuilderScreen extends StatelessWidget {
  const SentenceBuilderScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Construye una oración',
      titleIcon: Icons.view_week_rounded,
      accent: _sentenceColor,
      body: SpeechContentBuilder(builder: (context, content) => _Builder(content: content)),
    );
  }
}

class _Builder extends StatefulWidget {
  const _Builder({required this.content});

  final SpeechContent content;

  @override
  State<_Builder> createState() => _BuilderState();
}

class _BuilderState extends State<_Builder> {
  SentencePiece? _subject;
  SentenceAction? _action;
  SentencePiece? _complement;

  SentenceContent get _s => widget.content.sentences;

  String get _sentence => '${_subject!.text} ${_action!.text} ${_complement!.text}.';

  SpeechPicture _actionPicture(SentenceAction a) =>
      widget.content.verbs.where((v) => v.id == a.verbId).firstOrNull?.picture ??
      const IconPicture('star', null);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) speak(context, '¿Quién?');
    });
  }

  void _pickSubject(SentencePiece s) {
    setState(() => _subject = s);
    speak(context, '${s.text}… ¿Qué hace?');
  }

  void _pickAction(SentenceAction a) {
    setState(() => _action = a);
    speak(context, '${_subject!.text} ${a.text}… ¿Qué?');
  }

  void _pickComplement(SentencePiece c) {
    setState(() => _complement = c);
    speak(context, _sentence);
    AppServices.of(context).speech.markSentenceBuilt(_sentence);
  }

  void _restart() {
    setState(() {
      _subject = null;
      _action = null;
      _complement = null;
    });
    speak(context, '¿Quién?');
  }

  @override
  Widget build(BuildContext context) {
    final subject = _subject, action = _action, complement = _complement;
    final steps = Row(
      children: [
        for (final (i, (label, picture, text)) in [
          ('¿Quién?', subject?.picture, subject?.text),
          ('¿Qué hace?', action == null ? null : _actionPicture(action), action?.text),
          ('¿Qué?', complement?.picture, complement?.text),
        ].indexed) ...[
          if (i > 0) const Icon(Icons.chevron_right_rounded, color: AppColors.inkSoft),
          Expanded(
            child: _Slot(label: label, picture: picture, text: text),
          ),
        ],
      ],
    );

    final (String title, List<Widget> choices) = switch ((subject, action, complement)) {
      (null, _, _) => (
        '¿Quién?',
        [
          for (final s in _s.subjects)
            _Choice(text: s.text, picture: s.picture, onTap: () => _pickSubject(s)),
        ],
      ),
      (_, null, _) => (
        '¿Qué hace?',
        [
          for (final a in _s.actions)
            _Choice(text: a.text, picture: _actionPicture(a), onTap: () => _pickAction(a)),
        ],
      ),
      (_, final a?, null) => (
        '¿Qué?',
        [
          for (final c in a.complements)
            _Choice(text: c.text, picture: c.picture, onTap: () => _pickComplement(c)),
        ],
      ),
      _ => ('', const <Widget>[]),
    };

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        steps,
        const SizedBox(height: 16),
        if (complement != null) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: _sentenceColor.withValues(alpha: 0.6), width: 4),
            ),
            child: Semantics(
              label: 'Tu oración: $_sentence',
              excludeSemantics: true,
              child: Text(
                _sentence,
                textAlign: TextAlign.center,
                style: fredoka(32, color: const Color(0xFF1B5E57)),
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
                width: 150,
                child: SpeechActionButton(
                  icon: Icons.add_rounded,
                  label: 'Nueva oración',
                  color: speechAccent,
                  onPressed: _restart,
                ),
              ),
            ],
          ),
        ] else ...[
          Semantics(
            header: true,
            child: Text(title, style: fredoka(28, color: const Color(0xFF1B5E57))),
          ),
          const SizedBox(height: 8),
          LayoutBuilder(
            builder: (context, box) {
              final columns = box.maxWidth > 560 ? 4 : 3;
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

/// Casilla de la oración: el dibujo y la palabra elegidos, o la pregunta.
class _Slot extends StatelessWidget {
  const _Slot({required this.label, required this.picture, required this.text});

  final String label;
  final SpeechPicture? picture;
  final String? text;

  @override
  Widget build(BuildContext context) {
    final p = picture;
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: p == null ? const Color(0xFFFFF8EC) : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: p == null ? const Color(0xFFE6D3B5) : _sentenceColor, width: 2.5),
      ),
      child: Column(
        children: [
          SizedBox(
            height: 64,
            child: p == null
                ? const Icon(Icons.help_outline_rounded, size: 40, color: Color(0xFFD7C3A0))
                : SpeechPictureView(picture: p, tint: _sentenceColor),
          ),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(text ?? label, style: fredoka(18, color: const Color(0xFF1B5E57))),
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
  Widget build(BuildContext context) {
    return Semantics(
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
            border: Border.all(color: _sentenceColor.withValues(alpha: 0.45), width: 3),
            boxShadow: [BoxShadow(color: _sentenceColor.withValues(alpha: 0.35), offset: const Offset(0, 4))],
          ),
          child: Column(
            children: [
              SpeechPictureView(picture: picture, tint: _sentenceColor),
              const SizedBox(height: 4),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(text, style: fredoka(20, color: const Color(0xFF1B5E57))),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// «Ordena la oración»: de 3 palabras, después de 4 y después de 5 o más. Se
/// empieza por la primera que aún no se ha ordenado, así se avanza solo.
class OrderSentencesScreen extends StatelessWidget {
  const OrderSentencesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Ordena la oración',
      titleIcon: Icons.sort_rounded,
      accent: _sentenceColor,
      body: SpeechContentBuilder(builder: (context, content) => _OrderSentences(content: content)),
    );
  }
}

class _OrderSentences extends StatefulWidget {
  const _OrderSentences({required this.content});

  final SpeechContent content;

  @override
  State<_OrderSentences> createState() => _OrderSentencesState();
}

class _OrderSentencesState extends State<_OrderSentences> {
  /// Las oraciones de menos a más palabras.
  late final List<OrderSentence> _list = [...widget.content.sentences.order]
    ..sort((a, b) => a.words.length.compareTo(b.words.length));
  late int _index;
  bool _done = false;

  @override
  void initState() {
    super.initState();
    // Sin crear dependencia (estamos en initState): solo se lee el progreso al abrir.
    final ordered = context.getInheritedWidgetOfExactType<AppServices>()!.speech.progress.sentencesOrdered;
    final next = _list.indexWhere((s) => !ordered.contains(s.text));
    _index = next < 0 ? 0 : next;
    WidgetsBinding.instance.addPostFrameCallback((_) => _intro());
  }

  OrderSentence get _s => _list[_index];

  static int levelOf(OrderSentence s) => switch (s.words.length) {
    <= 3 => 1,
    4 => 2,
    _ => 3,
  };

  void _intro() {
    if (mounted) speak(context, 'Toca las palabras en orden. Nivel ${levelOf(_s)}.');
  }

  void _ordered() {
    setState(() => _done = true);
    final speech = AppServices.of(context).speech;
    speech.markSentenceOrdered(_s.text);
    speech.markActivityDone('ordenar');
  }

  void _next() {
    setState(() {
      _index = (_index + 1) % _list.length;
      _done = false;
    });
    _intro();
  }

  @override
  Widget build(BuildContext context) {
    if (_list.isEmpty) return const Center(child: Text('Todavía no hay oraciones.'));
    final s = _s;
    final level = levelOf(s);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        Row(
          children: [
            Semantics(
              container: true,
              label: 'Nivel $level',
              excludeSemantics: true,
              child: Row(
                children: [
                  for (var i = 1; i <= 3; i++)
                    Icon(
                      i <= level ? Icons.star_rounded : Icons.star_outline_rounded,
                      color: AppColors.sun,
                      size: 32,
                    ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '${s.words.length} palabras · ${_index + 1} de ${_list.length}',
                style: fredoka(18, color: AppColors.inkSoft),
              ),
            ),
            SizedBox(
              width: 96,
              child: SpeechActionButton(
                icon: Icons.volume_up_rounded,
                label: 'Escuchar',
                color: const Color(0xFF29B6F6),
                onPressed: () => speak(context, s.text),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Center(
          child: SizedBox(
            width: 200,
            height: 200,
            child: SpeechPictureView(picture: s.picture, tint: _sentenceColor),
          ),
        ),
        const SizedBox(height: 12),
        OrderWords(
          key: ValueKey(s.text),
          text: s.text,
          seed: s.text,
          onDone: _ordered,
          onNext: _next,
          nextLabel: 'Otra oración',
        ),
        if (_done && practiceAllowed(context)) ...[
          const SizedBox(height: 12),
          Center(
            child: SizedBox(
              width: 150,
              child: SpeechActionButton(
                icon: Icons.mic_rounded,
                label: 'Practicar',
                color: const Color(0xFFE53950),
                onPressed: () => showPracticeSheet(context, s.text),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
