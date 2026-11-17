import 'dart:async';

import 'package:flutter/material.dart';

import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../reading_activities.dart';
import '../reading_demo.dart';
import '../widgets/reading_widgets.dart';

/// Pantalla B · «Completo palabras»: la imagen, la palabra con un hueco y las
/// sílabas para completarla. (Fase 2: datos de demostración; la evaluación
/// definitiva y la dificultad progresiva llegan en la Fase D.)
class ReadingWordsScreen extends StatefulWidget {
  const ReadingWordsScreen({super.key});

  @override
  State<ReadingWordsScreen> createState() => _ReadingWordsScreenState();
}

enum _Check { none, right, notYet }

class _ReadingWordsScreenState extends State<ReadingWordsScreen> {
  static const color = Color(0xFFF59E3D);
  int _index = 0;
  String? _picked;
  _Check _check = _Check.none;

  DemoCompleteWord get item => ReadingDemo.words[_index];

  void _say(String text) => unawaited(AppServices.of(context).audio.say(text));

  void _pick(String option) {
    setState(() {
      _picked = option;
      _check = _Check.none;
    });
    _say(option);
  }

  void _verify() {
    final right = _picked == item.answer;
    setState(() => _check = right ? _Check.right : _Check.notYet);
    _say(right ? '¡Muy bien! ${item.word.text}.' : '¡Casi! Prueba con otra sílaba.');
  }

  void _next() {
    setState(() {
      _index = (_index + 1) % ReadingDemo.words.length;
      _picked = null;
      _check = _Check.none;
    });
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: ReadingActivities.words.title,
      titleIcon: Icons.extension_rounded,
      accent: color,
      badge: const DemoBadge(),
      trailing: const ReadingHomeButton(),
      body: LayoutBuilder(
        builder: (context, box) {
          final wide = box.maxWidth >= 760;
          final picture = SizedBox(
            height: wide ? 260 : 190,
            child: Semantics(
              label: 'Dibujo de la palabra',
              excludeSemantics: true,
              child: SpeechPictureView(picture: item.word.picture, tint: color),
            ),
          );
          final play = Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SyllableWord(
                syllables: item.word.syllables,
                missing: item.missing,
                filled: _picked,
                color: color,
                size: wide ? 76 : 60,
              ),
              const SizedBox(height: 12),
              ReadingAudioButtons(text: item.word.text, listenLabel: 'Palabra'),
              const SizedBox(height: 16),
              Text('¿Qué sílaba falta?', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 10),
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 12,
                runSpacing: 12,
                children: [
                  for (final o in item.options)
                    SyllableCard(
                      text: o,
                      color: color,
                      selected: o == _picked,
                      size: wide ? 96 : 78,
                      onTap: _check == _Check.right ? null : () => _pick(o),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              if (_check == _Check.right)
                ReadingCelebration(text: '¡Muy bien! ${item.word.text.toUpperCase()}')
              else if (_check == _Check.notYet)
                const ReadingTryAgain(text: '¡Casi! Prueba con otra sílaba.'),
              const SizedBox(height: 16),
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 12,
                runSpacing: 12,
                children: [
                  SizedBox(
                    width: 260,
                    child: BigActionButton(
                      label: 'Comprobar',
                      icon: Icons.check_rounded,
                      color: AppColors.leaf,
                      onPressed: _picked == null || _check == _Check.right ? null : _verify,
                    ),
                  ),
                  SizedBox(
                    width: 260,
                    child: BigActionButton(
                      label: 'Continuar',
                      icon: Icons.arrow_forward_rounded,
                      color: AppColors.sky,
                      onPressed: _next,
                    ),
                  ),
                ],
              ),
            ],
          );
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(
              AppDimens.pagePadding,
              0,
              AppDimens.pagePadding,
              AppDimens.pagePadding,
            ),
            child: Column(
              children: [
                ReadingProgressBar(
                  done: _index,
                  total: ReadingDemo.words.length,
                  label: 'Palabras',
                  color: color,
                ),
                const SizedBox(height: 12),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(child: picture),
                      const SizedBox(width: 20),
                      Expanded(child: play),
                    ],
                  )
                else ...[
                  picture,
                  const SizedBox(height: 12),
                  play,
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}
