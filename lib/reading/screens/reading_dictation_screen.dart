import 'dart:async';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../reading_activities.dart';
import '../reading_demo.dart';
import '../widgets/reading_widgets.dart';

/// Pantalla D · «Escucho y escribo»: nivel, escuchar y formar la respuesta con
/// tarjetas. (Fase 2: un ejemplo por nivel; el teclado propio, la corrección de
/// ortografía y tildes y los 30 dictados llegan en la Fase F.)
class ReadingDictationScreen extends StatefulWidget {
  const ReadingDictationScreen({super.key});

  @override
  State<ReadingDictationScreen> createState() => _ReadingDictationScreenState();
}

class _ReadingDictationScreenState extends State<ReadingDictationScreen> {
  static const color = Color(0xFF3DBE8B);
  int _level = 0;
  final _built = <int>[]; // índices de las tarjetas usadas, en orden
  bool? _right;

  DemoDictation get item => ReadingDemo.dictations[_level];

  void _say(String text, {bool slow = false}) =>
      unawaited(AppServices.of(context).audio.say(text, slow: slow));

  void _pickLevel(int i) {
    setState(() {
      _level = i;
      _built.clear();
      _right = null;
    });
  }

  void _add(int card) {
    setState(() {
      _built.add(card);
      _right = null;
    });
    _say(item.cards[card].replaceAll('.', ''));
  }

  void _undo() {
    if (_built.isEmpty) return;
    setState(() {
      _built.removeLast();
      _right = null;
    });
  }

  void _verify() {
    final answer = [for (final i in _built) item.cards[i]];
    final right = answer.join(item.joiner) == item.pieces.join(item.joiner);
    setState(() => _right = right);
    _say(right ? '¡Muy bien!' : '¡Casi! Escucha otra vez y prueba de nuevo.');
  }

  @override
  Widget build(BuildContext context) {
    final answer = [for (final i in _built) item.cards[i]];
    return KidScaffold(
      title: ReadingActivities.dictation.title,
      titleIcon: Icons.edit_rounded,
      accent: color,
      badge: const DemoBadge(),
      trailing: const ReadingHomeButton(),
      body: SingleChildScrollView(
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
                _LevelPicker(selected: _level, onPick: _pickLevel, color: color),
                const SizedBox(height: 14),
                SizedBox(
                  height: 150,
                  child: ReadingArt(
                    image: ReadingActivities.dictation.image,
                    fallbackIcon: Icons.hearing_rounded,
                    color: color,
                  ),
                ),
                const SizedBox(height: 12),
                ReadingAudioButtons(text: item.spoken, color: color),
                const SizedBox(height: 16),
                Text('Forma lo que escuchaste:', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 10),
                _AnswerArea(pieces: answer, joiner: item.joiner, color: color),
                const SizedBox(height: 14),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    for (final (i, c) in item.cards.indexed)
                      SyllableCard(
                        text: c,
                        color: color,
                        size: 72,
                        onTap: _built.contains(i) || _right == true ? null : () => _add(i),
                        selected: _built.contains(i),
                      ),
                  ],
                ),
                const SizedBox(height: 14),
                if (_right == true)
                  const ReadingCelebration(text: '¡Muy bien! ¡Lo escribiste!')
                else if (_right == false)
                  const ReadingTryAgain(text: '¡Casi! Escucha otra vez y prueba de nuevo.'),
                const SizedBox(height: 14),
                Wrap(
                  alignment: WrapAlignment.center,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    KidIconButton(
                      icon: Icons.backspace_rounded,
                      label: 'Borrar la última',
                      color: AppColors.coral,
                      onPressed: _built.isEmpty || _right == true ? null : _undo,
                    ),
                    SizedBox(
                      width: 260,
                      child: BigActionButton(
                        label: 'Comprobar',
                        icon: Icons.check_rounded,
                        color: AppColors.leaf,
                        onPressed: _built.isEmpty || _right == true ? null : _verify,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _LevelPicker extends StatelessWidget {
  const _LevelPicker({required this.selected, required this.onPick, required this.color});

  final int selected;
  final ValueChanged<int> onPick;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final (i, d) in ReadingDemo.dictations.indexed)
          Semantics(
            button: true,
            selected: i == selected,
            label: 'Nivel ${d.level}: ${d.levelName}',
            excludeSemantics: true,
            onTap: () => onPick(i),
            child: ChoiceChip(
              label: Text(
                'Nivel ${d.level} · ${d.levelName}',
                style: fredoka(17, color: i == selected ? Colors.white : AppColors.ink),
              ),
              selected: i == selected,
              selectedColor: color,
              backgroundColor: Colors.white,
              showCheckmark: false,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              shape: StadiumBorder(side: BorderSide(color: color.withValues(alpha: 0.6), width: 2)),
              onSelected: (_) => onPick(i),
            ),
          ),
      ],
    );
  }
}

/// Lo que el niño va formando.
class _AnswerArea extends StatelessWidget {
  const _AnswerArea({required this.pieces, required this.joiner, required this.color});

  final List<String> pieces;
  final String joiner;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: pieces.isEmpty ? 'Tu respuesta: vacía' : 'Tu respuesta: ${pieces.join(joiner)}',
      excludeSemantics: true,
      child: Container(
        width: double.infinity,
        constraints: const BoxConstraints(minHeight: 84),
        padding: const EdgeInsets.all(12),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: color, width: 3),
        ),
        child: pieces.isEmpty
            ? Text('Toca las tarjetas', style: fredoka(22, color: AppColors.inkSoft))
            : Text(
                pieces.join(joiner).toUpperCase(),
                style: fredoka(38, color: AppColors.ink),
                textAlign: TextAlign.center,
              ),
      ),
    );
  }
}
