import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

/// Las palabras de un grupo, una a una: la ilustración, la palabra escrita y
/// botones grandes para escucharla (normal o despacio) y pasar a otra. Se
/// puede deslizar con el dedo. Cada palabra se dice sola al aparecer.
class WordsScreen extends StatelessWidget {
  const WordsScreen({super.key, required this.categoryId});

  final String categoryId;

  @override
  Widget build(BuildContext context) {
    return SpeechContentBuilder(
      builder: (context, content) {
        final category = content.categories.where((c) => c.id == categoryId).firstOrNull;
        if (category == null) {
          return KidScaffold(
            title: 'Mis primeras palabras',
            accent: speechAccent,
            body: const Center(child: Text('No encontramos este grupo de palabras.')),
          );
        }
        return _WordsPager(category: category);
      },
    );
  }
}

class _WordsPager extends StatefulWidget {
  const _WordsPager({required this.category});

  final WordCategory category;

  @override
  State<_WordsPager> createState() => _WordsPagerState();
}

class _WordsPagerState extends State<_WordsPager> {
  final _pages = PageController();
  int _index = 0;
  bool _finished = false;

  List<SpeechWord> get _words => widget.category.words;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _say(slow: false);
    });
  }

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  void _say({required bool slow}) {
    final word = _words[_index];
    speak(context, word.text, slow: slow);
    AppServices.of(context).speech.markWordHeard(word.id);
  }

  void _goTo(int i) {
    if (i < 0) return;
    if (i >= _words.length) {
      setState(() => _finished = true);
      speak(context, '¡Muy bien! Escuchaste todas las palabras de ${widget.category.name.toLowerCase()}.');
      return;
    }
    _pages.animateToPage(i, duration: const Duration(milliseconds: 320), curve: Curves.easeOutCubic);
  }

  void _restart() {
    setState(() {
      _finished = false;
      _index = 0;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _pages.jumpToPage(0);
      _say(slow: false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.category;
    return KidScaffold(
      title: c.name,
      titleIcon: SpeechIcons.byName[c.icon],
      accent: Color.lerp(c.color, Colors.black, 0.1)!,
      backLabel: 'Volver a los grupos',
      body: _finished ? _done(c) : _pager(c),
    );
  }

  Widget _done(WordCategory c) => Center(
    child: Padding(
      padding: const EdgeInsets.all(AppDimens.pagePadding),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          LoloBubble(text: '¡Muy bien! Escuchaste todas las palabras de ${c.name.toLowerCase()}.', size: 90),
          const SizedBox(height: 24),
          Wrap(
            spacing: 16,
            runSpacing: 12,
            alignment: WrapAlignment.center,
            children: [
              SpeechActionButton(
                icon: Icons.replay_rounded,
                label: 'Otra vez',
                color: c.color,
                onPressed: _restart,
              ),
              SpeechActionButton(
                icon: Icons.apps_rounded,
                label: 'Otros grupos',
                color: speechAccent,
                onPressed: () => Navigator.of(context).maybePop(),
              ),
            ],
          ),
        ],
      ),
    ),
  );

  Widget _pager(WordCategory c) {
    final buttons = [
      SpeechActionButton(
        icon: Icons.arrow_back_rounded,
        label: 'Anterior',
        color: AppColors.inkSoft,
        onPressed: _index == 0 ? null : () => _goTo(_index - 1),
      ),
      SpeechActionButton(
        icon: Icons.volume_up_rounded,
        label: 'Escuchar',
        color: const Color(0xFF29B6F6),
        onPressed: () => _say(slow: false),
      ),
      SpeechActionButton(
        icon: Icons.slow_motion_video_rounded,
        label: 'Despacio',
        color: const Color(0xFFAB47BC),
        onPressed: () => _say(slow: true),
      ),
      SpeechActionButton(
        icon: Icons.arrow_forward_rounded,
        label: 'Siguiente',
        color: speechAccent,
        onPressed: () => _goTo(_index + 1),
      ),
    ];
    final pager = PageView.builder(
      controller: _pages,
      itemCount: _words.length,
      onPageChanged: (i) {
        setState(() => _index = i);
        _say(slow: false);
      },
      itemBuilder: (context, i) => _WordCard(
        word: _words[i],
        color: c.color,
        onTap: () {
          if (i == _index) _say(slow: false);
        },
      ),
    );
    final counter = Semantics(
      label: 'Palabra ${_index + 1} de ${_words.length}',
      excludeSemantics: true,
      child: Text('${_index + 1} / ${_words.length}', style: fredoka(18, color: AppColors.inkSoft)),
    );
    return LayoutBuilder(
      builder: (context, box) {
        if (box.maxWidth > box.maxHeight * 1.2) {
          return Row(
            children: [
              Expanded(child: pager),
              SizedBox(
                width: 260,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    children: [
                      counter,
                      const SizedBox(height: 8),
                      GridView.count(
                        crossAxisCount: 2,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        mainAxisSpacing: 12,
                        crossAxisSpacing: 12,
                        childAspectRatio: 1.15,
                        children: buttons,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        }
        return Column(
          children: [
            Expanded(child: pager),
            counter,
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
              child: Row(
                children: [
                  for (final (i, b) in buttons.indexed) ...[
                    if (i > 0) const SizedBox(width: 8),
                    Expanded(child: b),
                  ],
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

/// La tarjeta de una palabra: ilustración grande y la palabra en mayúsculas.
class _WordCard extends StatelessWidget {
  const _WordCard({required this.word, required this.color, required this.onTap});

  final SpeechWord word;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ink = Color.lerp(color, const Color(0xFF2A2350), 0.7)!;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Semantics(
        button: true,
        label: word.text,
        hint: 'Toca para escuchar la palabra',
        excludeSemantics: true,
        onTap: onTap,
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(32),
              border: Border.all(color: color.withValues(alpha: 0.7), width: 5),
              boxShadow: [
                BoxShadow(
                  color: Color.lerp(color, Colors.black, 0.15)!.withValues(alpha: 0.6),
                  offset: const Offset(0, 6),
                ),
                const BoxShadow(color: Color(0x22000000), blurRadius: 14, offset: Offset(0, 10)),
              ],
            ),
            child: Column(
              children: [
                Expanded(
                  child: Center(
                    child: SpeechPictureView(picture: word.picture, tint: color),
                  ),
                ),
                const SizedBox(height: 8),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(word.text.toUpperCase(), style: fredoka(56, color: ink)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
