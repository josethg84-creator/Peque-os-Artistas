import 'dart:async';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../reading_activities.dart';
import '../reading_demo.dart';
import '../widgets/reading_widgets.dart';

/// Pantalla C · «Leo oraciones»: ilustración, oración grande, lectura normal y
/// lenta, y tocar cada palabra para oírla. (Fase 2: datos de demostración; el
/// resaltado de palabras sincronizado con la voz y las preguntas llegan en la
/// Fase E.)
class ReadingSentencesScreen extends StatefulWidget {
  const ReadingSentencesScreen({super.key});

  @override
  State<ReadingSentencesScreen> createState() => _ReadingSentencesScreenState();
}

class _ReadingSentencesScreenState extends State<ReadingSentencesScreen> {
  static const color = Color(0xFF8E6BE0);
  int _index = 0;

  DemoSentence get sentence => ReadingDemo.sentences[_index];

  void _say(String text) => unawaited(AppServices.of(context).audio.say(text));

  void _next() {
    setState(() => _index = (_index + 1) % ReadingDemo.sentences.length);
    _say(sentence.text);
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: ReadingActivities.sentences.title,
      titleIcon: Icons.menu_book_rounded,
      accent: color,
      badge: const DemoBadge(),
      trailing: const ReadingHomeButton(),
      body: LayoutBuilder(
        builder: (context, box) {
          final wide = box.maxWidth >= 760;
          final fontSize = wide ? 44.0 : 34.0;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(
              AppDimens.pagePadding,
              0,
              AppDimens.pagePadding,
              AppDimens.pagePadding,
            ),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 820),
                child: Column(
                  children: [
                    ReadingProgressBar(
                      done: _index,
                      total: ReadingDemo.sentences.length,
                      label: 'Oraciones',
                      color: color,
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      height: wide ? 240 : 180,
                      child: Semantics(
                        label: 'Ilustración de la oración',
                        excludeSemantics: true,
                        child: SpeechPictureView(picture: sentence.picture, tint: color),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(28),
                        border: Border.all(color: Color.lerp(color, Colors.white, 0.5)!, width: 3),
                      ),
                      child: Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 10,
                        runSpacing: 8,
                        children: [
                          for (final w in sentence.words)
                            _TapWord(word: w, size: fontSize, color: color, onTap: () => _say(_clean(w))),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('Toca una palabra para escucharla.', style: Theme.of(context).textTheme.bodyLarge),
                    const SizedBox(height: 14),
                    ReadingAudioButtons(text: sentence.text, listenLabel: 'Leer', color: color),
                    const SizedBox(height: 16),
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        SizedBox(
                          width: 260,
                          child: BigActionButton(
                            label: 'Escuchar otra vez',
                            icon: Icons.replay_rounded,
                            color: AppColors.sky,
                            onPressed: () => _say(sentence.text),
                          ),
                        ),
                        SizedBox(
                          width: 260,
                          child: BigActionButton(
                            label: 'Siguiente oración',
                            icon: Icons.arrow_forward_rounded,
                            color: AppColors.leaf,
                            onPressed: _next,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Quita la puntuación para decir solo la palabra.
String _clean(String w) => w.replaceAll(RegExp(r'[.,;:!?¡¿«»"]'), '');

class _TapWord extends StatelessWidget {
  const _TapWord({required this.word, required this.size, required this.color, required this.onTap});

  final String word;
  final double size;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: _clean(word),
      hint: 'Toca para escuchar la palabra',
      excludeSemantics: true,
      onTap: onTap,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            child: Text(word, style: fredoka(size, color: AppColors.ink)),
          ),
        ),
      ),
    );
  }
}
