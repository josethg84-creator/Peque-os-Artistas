import 'dart:math';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/order_words.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _phraseColor = Color(0xFFF06292);

/// «Aprendo frases»: frases útiles para cada día, con su ilustración. Se
/// escuchan enteras (normal o despacio) o palabra a palabra tocando cada una,
/// y se pueden ordenar con tarjetas («¡Ordénala tú!»).
///
/// La misma pantalla sirve para «Necesito…» de «Yo puedo expresarme» con
/// [PhrasesScreen.needs].
class PhrasesScreen extends StatelessWidget {
  const PhrasesScreen({super.key}) : needs = false;

  /// Las necesidades de «Yo puedo expresarme».
  const PhrasesScreen.needs({super.key}) : needs = true;

  final bool needs;

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: needs ? 'Necesito…' : 'Aprendo frases',
      titleIcon: needs ? Icons.back_hand_rounded : Icons.chat_bubble_rounded,
      accent: _phraseColor,
      backLabel: needs ? 'Volver a Yo puedo expresarme' : 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => needs
            ? _PhrasesPager(
                phrases: content.expressions.needs,
                onHeard: (id) => speech.markExpressionPracticed('necesidad:$id'),
                onOrdered: (id) => speech.markExpressionPracticed('necesidad:$id'),
              )
            : _PhrasesPager(
                phrases: content.phrases,
                onHeard: speech.markPhraseHeard,
                onOrdered: speech.markPhraseOrdered,
              ),
      ),
    );
  }
}

class _PhrasesPager extends StatefulWidget {
  const _PhrasesPager({required this.phrases, required this.onHeard, required this.onOrdered});

  final List<SpeechPhrase> phrases;

  /// Se ha escuchado la frase (id) / se ha ordenado.
  final void Function(String id) onHeard;
  final void Function(String id) onOrdered;

  @override
  State<_PhrasesPager> createState() => _PhrasesPagerState();
}

class _PhrasesPagerState extends State<_PhrasesPager> {
  final _pages = PageController();
  int _index = 0;

  /// La frase actual se está ordenando con tarjetas.
  bool _ordering = false;

  SpeechPhrase get _phrase => widget.phrases[_index];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _say();
    });
  }

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  void _say({bool slow = false}) {
    speak(context, _phrase.text, slow: slow);
    widget.onHeard(_phrase.id);
  }

  void _goTo(int i) {
    if (i < 0 || i >= widget.phrases.length) return;
    _pages.animateToPage(i, duration: const Duration(milliseconds: 320), curve: Curves.easeOutCubic);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.phrases.isEmpty) return const Center(child: Text('Todavía no hay frases.'));
    final last = _index == widget.phrases.length - 1;
    final pager = PageView.builder(
      controller: _pages,
      itemCount: widget.phrases.length,
      // Mientras se ordena, no se cambia de frase sin querer.
      physics: _ordering ? const NeverScrollableScrollPhysics() : null,
      onPageChanged: (i) {
        setState(() {
          _index = i;
          _ordering = false;
        });
        _say();
      },
      itemBuilder: (context, i) => _PhraseCard(
        phrase: widget.phrases[i],
        ordering: _ordering && i == _index,
        onOrdered: () => widget.onOrdered(widget.phrases[i].id),
        onNext: last ? null : () => _goTo(i + 1),
      ),
    );
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
        onPressed: _say,
      ),
      SpeechActionButton(
        icon: Icons.slow_motion_video_rounded,
        label: 'Despacio',
        color: const Color(0xFFAB47BC),
        onPressed: () => _say(slow: true),
      ),
      if (practiceAllowed(context))
        SpeechActionButton(
          icon: Icons.mic_rounded,
          label: 'Practicar',
          color: const Color(0xFFE53950),
          onPressed: () => showPracticeSheet(context, _phrase.text),
        ),
      SpeechActionButton(
        icon: Icons.arrow_forward_rounded,
        label: 'Siguiente',
        color: speechAccent,
        onPressed: last ? null : () => _goTo(_index + 1),
      ),
    ];
    final order = SpeechActionButton(
      icon: _ordering ? Icons.visibility_rounded : Icons.sort_rounded,
      label: _ordering ? 'Ver la frase' : '¡Ordénala tú!',
      color: const Color(0xFF26A69A),
      onPressed: () {
        setState(() => _ordering = !_ordering);
        if (_ordering) speak(context, 'Toca las palabras en orden para formar la frase.');
      },
    );
    final counter = Semantics(
      label: 'Frase ${_index + 1} de ${widget.phrases.length}',
      excludeSemantics: true,
      child: Text('${_index + 1} / ${widget.phrases.length}', style: fredoka(18, color: AppColors.inkSoft)),
    );
    return LayoutBuilder(
      builder: (context, box) {
        if (box.maxWidth > box.maxHeight * 1.2) {
          // En horizontal, los botones a un lado.
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
                      const SizedBox(height: 12),
                      SizedBox(width: double.infinity, child: order),
                    ],
                  ),
                ),
              ),
            ],
          );
        }
        return _portrait(pager, counter, buttons, order);
      },
    );
  }

  Widget _portrait(Widget pager, Widget counter, List<Widget> buttons, Widget order) {
    return Column(
      children: [
        Expanded(child: pager),
        counter,
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Row(
            children: [
              for (final (i, b) in buttons.indexed) ...[
                if (i > 0) const SizedBox(width: 8),
                Expanded(child: b),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 14),
          child: SizedBox(width: double.infinity, child: order),
        ),
      ],
    );
  }
}

class _PhraseCard extends StatelessWidget {
  const _PhraseCard({
    required this.phrase,
    required this.ordering,
    required this.onOrdered,
    required this.onNext,
  });

  final SpeechPhrase phrase;
  final bool ordering;
  final VoidCallback onOrdered;
  final VoidCallback? onNext;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(32),
          border: Border.all(color: _phraseColor.withValues(alpha: 0.6), width: 5),
          boxShadow: [
            BoxShadow(color: _phraseColor.withValues(alpha: 0.45), offset: const Offset(0, 6)),
            const BoxShadow(color: Color(0x22000000), blurRadius: 14, offset: Offset(0, 10)),
          ],
        ),
        child: LayoutBuilder(
          builder: (context, box) {
            final words = ordering
                ? OrderWords(
                    key: ValueKey(phrase.id),
                    text: phrase.text,
                    seed: phrase.id,
                    onDone: onOrdered,
                    onNext: onNext,
                  )
                : _WordChips(phrase: phrase);
            final picture = SpeechPictureView(picture: phrase.picture, tint: _phraseColor);
            // Poco alto (teléfono pequeño o en horizontal): dibujo más pequeño y
            // la tarjeta se desplaza, sin cortar nada.
            if (box.maxHeight < 320) {
              return ListView(
                children: [
                  SizedBox(
                    height: max(90, box.maxHeight * 0.4),
                    child: Center(child: picture),
                  ),
                  const SizedBox(height: 8),
                  words,
                ],
              );
            }
            return Column(
              children: [
                Expanded(child: Center(child: picture)),
                const SizedBox(height: 10),
                words,
              ],
            );
          },
        ),
      ),
    );
  }
}

/// La frase escrita, con cada palabra como botón para escucharla sola.
class _WordChips extends StatelessWidget {
  const _WordChips({required this.phrase});

  final SpeechPhrase phrase;

  @override
  Widget build(BuildContext context) {
    final pieces = phrase.text.split(RegExp(r'\s+'));
    return Semantics(
      container: true,
      label: phrase.text,
      child: Wrap(
        alignment: WrapAlignment.center,
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final piece in pieces)
            WordChip(
              text: piece,
              semanticsLabel: piece.replaceAll(RegExp(r'[.,;:¿?¡!]'), ''),
              onTap: () => speak(context, piece.replaceAll(RegExp(r'[.,;:¿?¡!]'), '')),
            ),
        ],
      ),
    );
  }
}
