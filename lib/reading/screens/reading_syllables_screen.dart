import 'dart:async';

import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/reading_voice.dart';
import '../reading_activities.dart';
import '../reading_content.dart';
import '../widgets/reading_widgets.dart';

/// Pantalla A · «Aprendo las sílabas»: vocales y 10 familias, cada sílaba con
/// su sonido (normal y despacio), su palabra de ejemplo y su imagen, y los
/// juegos «Escucha y encuentra» y «Une sílaba y palabra».
class ReadingSyllablesScreen extends StatelessWidget {
  const ReadingSyllablesScreen({super.key});

  static const color = Color(0xFF4FA8F0);

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: ReadingActivities.syllables.title,
      titleIcon: Icons.abc_rounded,
      accent: color,
      trailing: const ReadingHomeButton(),
      body: ReadingContentBuilder(builder: (context, content) => _SyllablesView(content: content)),
    );
  }
}

class _SyllablesView extends StatefulWidget {
  const _SyllablesView({required this.content});

  final ReadingContent content;

  @override
  State<_SyllablesView> createState() => _SyllablesViewState();
}

class _SyllablesViewState extends State<_SyllablesView> {
  ReadingVoice? _voice;
  int _family = 0;
  int _syllable = 0;
  bool _picked = false;

  ReadingContent get content => widget.content;
  SyllableFamily get family => content.families[_family];
  List<ReadingSyllable> get syllables => content.syllablesOf(family);
  ReadingSyllable get syllable => syllables[_syllable];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _voice ??= ReadingVoice(AppServices.of(context).audio);
  }

  @override
  void dispose() {
    _voice?.dispose(); // libera el reproductor al salir
    super.dispose();
  }

  void _play(ReadingAudio audio, [ReadingSpeed speed = ReadingSpeed.normal]) =>
      unawaited(_voice!.play(audio, speed: speed));

  void _pickFamily(int i) {
    setState(() {
      _family = i;
      _syllable = 0;
      _picked = false;
    });
    // Se oye el nombre de la letra y después sus cinco sílabas.
    unawaited(_voice!.playAll([?family.letterAudio, for (final s in syllables) s.audio]));
  }

  void _pickSyllable(int i) {
    setState(() {
      _syllable = i;
      _picked = true;
    });
    _play(syllable.audio);
  }

  void _openGame(String route) =>
      Navigator.of(context).pushNamed(route, arguments: ReadingGameArgs(familyId: family.id));

  @override
  Widget build(BuildContext context) {
    final word = content.wordOf(syllable);
    final color = family.color;
    return LayoutBuilder(
      builder: (context, box) {
        final wide = box.maxWidth >= 760;
        final cardSize = ((wide ? box.maxWidth / 2 : box.maxWidth) - 2 * AppDimens.pagePadding - 4 * 10) / 5;
        final syllableSize = cardSize.clamp(58.0, 104.0);
        final picker = Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Elige una familia', style: fredoka(18, color: AppColors.ink)),
            const SizedBox(height: 8),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final (i, f) in content.families.indexed)
                  _FamilyChip(family: f, selected: i == _family, onTap: () => _pickFamily(i)),
              ],
            ),
            const SizedBox(height: 16),
            Wrap(
              alignment: WrapAlignment.center,
              spacing: 10,
              runSpacing: 10,
              children: [
                for (final (i, s) in syllables.indexed)
                  SyllableCard(
                    text: s.text,
                    selected: _picked && i == _syllable,
                    color: Color.lerp(color, Colors.black, 0.15)!,
                    size: syllableSize,
                    onTap: () => _pickSyllable(i),
                  ),
              ],
            ),
            if (family.letterAudio case final letter?) ...[
              const SizedBox(height: 12),
              KidIconButton(
                icon: Icons.record_voice_over_rounded,
                label: 'Escuchar el nombre de la letra ${family.letter}',
                color: AppColors.grape,
                showLabel: true,
                onPressed: () => _play(letter),
              ),
            ],
          ],
        );
        final example = _ExampleCard(
          key: ValueKey(syllable.id),
          syllable: syllable,
          word: word,
          color: color,
          onSyllable: (speed) => _play(syllable.audio, speed),
          onWord: (speed) {
            if (word != null) _play(word.audio, speed);
          },
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
              ReadingVoiceNotice(voice: _voice!),
              const ReadingLolo(text: 'Toca una sílaba para escucharla.'),
              const SizedBox(height: 12),
              if (wide)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: picker),
                    const SizedBox(width: 20),
                    Expanded(child: example),
                  ],
                )
              else ...[
                picker,
                const SizedBox(height: 16),
                example,
              ],
              const SizedBox(height: 14),
              ReadingStepNav(
                index: _syllable,
                total: syllables.length,
                onPrevious: _syllable > 0 ? () => _pickSyllable(_syllable - 1) : null,
                onNext: _syllable < syllables.length - 1 ? () => _pickSyllable(_syllable + 1) : null,
              ),
              const SizedBox(height: 18),
              _Levels(content: content, onGame: _openGame),
            ],
          ),
        );
      },
    );
  }
}

class _FamilyChip extends StatelessWidget {
  const _FamilyChip({required this.family, required this.selected, required this.onTap});

  final SyllableFamily family;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final strong = Color.lerp(family.color, Colors.black, 0.25)!;
    return Semantics(
      button: true,
      selected: selected,
      label: family.isVowels ? 'Las vocales' : 'Familia de la ${family.letter}',
      excludeSemantics: true,
      onTap: onTap,
      child: ChoiceChip(
        label: Text(family.letter, style: fredoka(22, color: selected ? Colors.white : AppColors.ink)),
        selected: selected,
        selectedColor: strong,
        backgroundColor: Color.lerp(family.color, Colors.white, 0.7),
        showCheckmark: false,
        materialTapTargetSize: MaterialTapTargetSize.padded,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: StadiumBorder(side: BorderSide(color: strong.withValues(alpha: 0.6), width: 2)),
        onSelected: (_) => onTap(),
      ),
    );
  }
}

/// La sílaba en grande, su sonido y la palabra de ejemplo con su imagen.
class _ExampleCard extends StatelessWidget {
  const _ExampleCard({
    super.key,
    required this.syllable,
    required this.word,
    required this.color,
    required this.onSyllable,
    required this.onWord,
  });

  final ReadingSyllable syllable;
  final ReadingWord? word;
  final Color color;
  final void Function(ReadingSpeed) onSyllable;
  final void Function(ReadingSpeed) onWord;

  @override
  Widget build(BuildContext context) {
    final w = word;
    final strong = Color.lerp(color, Colors.black, 0.3)!;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: color, width: 3),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Semantics(
            label: 'La sílaba ${syllable.text}',
            excludeSemantics: true,
            child: Text(syllable.text.toUpperCase(), style: fredoka(76, color: strong)),
          ),
          ReadingPlayButtons(onPlay: onSyllable, semanticSuffix: ' la sílaba', color: strong),
          if (w != null) ...[
            const SizedBox(height: 14),
            SizedBox(
              height: 150,
              child: ReadingWordPicture(word: w, color: color),
            ),
            const SizedBox(height: 10),
            SyllableWord(syllables: w.syllables, highlight: 0, color: color, size: 50),
            if (w.note case final note?) ...[
              const SizedBox(height: 6),
              Text(note, style: Theme.of(context).textTheme.bodySmall, textAlign: TextAlign.center),
            ],
            const SizedBox(height: 10),
            ReadingPlayButtons(
              onPlay: onWord,
              listenLabel: 'Palabra',
              semanticSuffix: ' la palabra ${w.text}',
              color: AppColors.leaf,
            ),
          ],
        ],
      ),
    );
  }
}

/// Los tres niveles: el inicial y el intermedio con su juego; el avanzado,
/// bloqueado hasta que llegue su contenido.
class _Levels extends StatelessWidget {
  const _Levels({required this.content, required this.onGame});

  final ReadingContent content;
  final void Function(String route) onGame;

  static const _games = {1: AppRoutes.readingListenFind, 2: AppRoutes.readingMatchWord};
  static const _labels = {1: 'Escucha y encuentra', 2: 'Une sílaba y palabra'};
  static const _icons = {1: Icons.hearing_rounded, 2: Icons.image_search_rounded};

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('Juega con las sílabas', style: fredoka(22, color: AppColors.ink)),
        const SizedBox(height: 10),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final l in content.levels)
              SizedBox(
                width: 290,
                child: l.locked || _games[l.id] == null
                    ? _LockedLevel(level: l)
                    : Column(
                        children: [
                          Text(
                            'Nivel ${l.name.toLowerCase()} · ${l.description}',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 6),
                          BigActionButton(
                            label: _labels[l.id]!,
                            icon: _icons[l.id]!,
                            color: l.id == 1 ? AppColors.sky : AppColors.leaf,
                            onPressed: () => onGame(_games[l.id]!),
                          ),
                        ],
                      ),
              ),
          ],
        ),
      ],
    );
  }
}

class _LockedLevel extends StatelessWidget {
  const _LockedLevel({required this.level});

  final ReadingLevel level;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Nivel ${level.name.toLowerCase()}: ${level.description}. Todavía no está disponible.',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFF1EEF8),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: const Color(0xFFD1C4E9), width: 2),
        ),
        child: Row(
          children: [
            const Icon(Icons.lock_rounded, color: AppColors.inkSoft, size: 30),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Nivel ${level.name.toLowerCase()}\n${level.description}',
                style: fredoka(16, color: AppColors.inkSoft),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Familia con la que empieza un juego (o todas).
class ReadingGameArgs {
  const ReadingGameArgs({this.familyId});
  final String? familyId;
}
