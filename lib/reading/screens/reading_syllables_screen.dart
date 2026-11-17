import 'dart:async';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/kid_scaffold.dart';
import '../reading_activities.dart';
import '../reading_demo.dart';
import '../widgets/reading_widgets.dart';

/// Pantalla A · «Aprendo las sílabas»: familia, sílabas y su palabra de
/// ejemplo. (Fase 2: datos de demostración.)
class ReadingSyllablesScreen extends StatefulWidget {
  const ReadingSyllablesScreen({super.key});

  @override
  State<ReadingSyllablesScreen> createState() => _ReadingSyllablesScreenState();
}

class _ReadingSyllablesScreenState extends State<ReadingSyllablesScreen> {
  static const color = Color(0xFF4FA8F0);
  int _family = 0;
  int _syllable = 0;

  DemoFamily get family => ReadingDemo.families[_family];
  DemoSyllable get syllable => family.syllables[_syllable];

  void _say(String text) => unawaited(AppServices.of(context).audio.say(text));

  void _pickFamily(int i) {
    setState(() {
      _family = i;
      _syllable = 0;
    });
    _say('La ${family.letter.toLowerCase()}: ${family.syllables.map((s) => s.text).join(', ')}.');
  }

  void _pickSyllable(int i) {
    setState(() => _syllable = i);
    _say(syllable.text);
  }

  @override
  Widget build(BuildContext context) {
    final example = syllable.example;
    final highlight = example.syllables.indexWhere((s) => _plain(s) == syllable.text);
    return KidScaffold(
      title: ReadingActivities.syllables.title,
      titleIcon: Icons.abc_rounded,
      accent: color,
      badge: const DemoBadge(),
      trailing: const ReadingHomeButton(),
      body: LayoutBuilder(
        builder: (context, box) {
          final wide = box.maxWidth >= 760;
          final cardSize = (box.maxWidth - 2 * AppDimens.pagePadding - 4 * 10) / 5;
          final syllableSize = cardSize.clamp(56.0, wide ? 110.0 : 84.0);
          final picker = Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _FamilyPicker(selected: _family, onPick: _pickFamily, color: color),
              const SizedBox(height: 16),
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (final (i, s) in family.syllables.indexed)
                    SyllableCard(
                      text: s.text,
                      selected: i == _syllable,
                      color: color,
                      size: syllableSize,
                      onTap: () => _pickSyllable(i),
                    ),
                ],
              ),
            ],
          );
          final exampleCard = _ExampleCard(
            key: ValueKey(syllable.text),
            syllable: syllable.text,
            word: example,
            highlight: highlight < 0 ? null : highlight,
            color: color,
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
                const ReadingLolo(text: 'Toca una sílaba para escucharla.'),
                const SizedBox(height: 12),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: picker),
                      const SizedBox(width: 20),
                      Expanded(child: exampleCard),
                    ],
                  )
                else ...[
                  picker,
                  const SizedBox(height: 16),
                  exampleCard,
                ],
                const SizedBox(height: 16),
                ReadingStepNav(
                  index: _syllable,
                  total: family.syllables.length,
                  onPrevious: _syllable > 0 ? () => _pickSyllable(_syllable - 1) : null,
                  onNext: _syllable < family.syllables.length - 1 ? () => _pickSyllable(_syllable + 1) : null,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Quita la tilde para comparar «mú» con «mu».
String _plain(String s) => s
    .toLowerCase()
    .replaceAll('á', 'a')
    .replaceAll('é', 'e')
    .replaceAll('í', 'i')
    .replaceAll('ó', 'o')
    .replaceAll('ú', 'u');

class _FamilyPicker extends StatelessWidget {
  const _FamilyPicker({required this.selected, required this.onPick, required this.color});

  final int selected;
  final ValueChanged<int> onPick;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('Elige una letra', style: fredoka(18, color: AppColors.ink)),
        const SizedBox(height: 8),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final (i, f) in ReadingDemo.families.indexed)
              Semantics(
                button: true,
                selected: i == selected,
                label: 'Familia de la ${f.letter}',
                excludeSemantics: true,
                onTap: () => onPick(i),
                child: ChoiceChip(
                  label: Text(
                    f.letter,
                    style: fredoka(24, color: i == selected ? Colors.white : AppColors.ink),
                  ),
                  selected: i == selected,
                  selectedColor: AppColors.grape,
                  backgroundColor: Colors.white,
                  showCheckmark: false,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  shape: StadiumBorder(
                    side: BorderSide(color: AppColors.grape.withValues(alpha: 0.5), width: 2),
                  ),
                  onSelected: (_) => onPick(i),
                ),
              ),
          ],
        ),
      ],
    );
  }
}

/// La sílaba en grande, su palabra de ejemplo con dibujo y los botones de audio.
class _ExampleCard extends StatelessWidget {
  const _ExampleCard({
    super.key,
    required this.syllable,
    required this.word,
    required this.highlight,
    required this.color,
  });

  final String syllable;
  final DemoWord word;
  final int? highlight;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: Color.lerp(color, Colors.white, 0.4)!, width: 3),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(syllable.toUpperCase(), style: fredoka(72, color: color)),
          ReadingAudioButtons(text: syllable),
          const SizedBox(height: 14),
          SizedBox(
            height: 140,
            child: Semantics(
              label: 'Dibujo: ${word.text}',
              excludeSemantics: true,
              child: SpeechPictureView(picture: word.picture, tint: color),
            ),
          ),
          const SizedBox(height: 8),
          SyllableWord(syllables: word.syllables, highlight: highlight, color: color, size: 52),
          const SizedBox(height: 10),
          ReadingAudioButtons(text: word.text, listenLabel: 'Palabra'),
        ],
      ),
    );
  }
}
