import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _phraseColor = Color(0xFFF06292);

/// «Aprendo frases»: frases útiles para cada día, con su ilustración. Se
/// escuchan enteras (normal o despacio) o palabra a palabra tocando cada una,
/// y se pueden ordenar con tarjetas («¡Ordénala tú!»).
class PhrasesScreen extends StatelessWidget {
  const PhrasesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Aprendo frases',
      titleIcon: Icons.chat_bubble_rounded,
      accent: _phraseColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(builder: (context, content) => _PhrasesPager(phrases: content.phrases)),
    );
  }
}

class _PhrasesPager extends StatefulWidget {
  const _PhrasesPager({required this.phrases});

  final List<SpeechPhrase> phrases;

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
    AppServices.of(context).speech.markPhraseHeard(_phrase.id);
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
        onOrdered: () => AppServices.of(context).speech.markPhraseOrdered(widget.phrases[i].id),
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
                ? _PhraseOrdering(key: ValueKey(phrase.id), phrase: phrase, onDone: onOrdered, onNext: onNext)
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
            _Chip(
              text: piece,
              semanticsLabel: piece.replaceAll(RegExp(r'[.,;:¿?¡!]'), ''),
              onTap: () => speak(context, piece.replaceAll(RegExp(r'[.,;:¿?¡!]'), '')),
            ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.text,
    required this.onTap,
    this.semanticsLabel,
    this.color = _phraseColor,
    this.highlighted = false,
  });

  final String text;
  final String? semanticsLabel;
  final VoidCallback? onTap;
  final Color color;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      button: onTap != null,
      label: semanticsLabel ?? text,
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          constraints: const BoxConstraints(minHeight: 52, minWidth: 52),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Color.lerp(color, Colors.white, highlighted ? 0.55 : 0.82),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: highlighted ? AppColors.sun : color.withValues(alpha: 0.6),
              width: highlighted ? 4 : 2.5,
            ),
            boxShadow: [BoxShadow(color: color.withValues(alpha: 0.35), offset: const Offset(0, 3))],
          ),
          child: Text(text, style: fredoka(28, color: Color.lerp(color, const Color(0xFF2A2350), 0.65)!)),
        ),
      ),
    );
  }
}

/// Ordenar la frase: las palabras aparecen desordenadas y el niño las toca en
/// orden. Una palabra equivocada no castiga: tiembla un poco y Lolo anima; tras
/// dos intentos, la palabra que va se ilumina para ayudar.
class _PhraseOrdering extends StatefulWidget {
  const _PhraseOrdering({super.key, required this.phrase, required this.onDone, required this.onNext});

  final SpeechPhrase phrase;
  final VoidCallback onDone;
  final VoidCallback? onNext;

  @override
  State<_PhraseOrdering> createState() => _PhraseOrderingState();
}

class _PhraseOrderingState extends State<_PhraseOrdering> {
  late final List<String> _words = widget.phrase.words;

  /// Orden en que se muestran las tarjetas (índices de [_words]).
  late final List<int> _shuffled = shuffledOrder(_words, widget.phrase.id);
  int _placed = 0;
  int _misses = 0;

  bool get _done => _placed == _words.length;

  /// Desordena siempre igual para la misma frase y nunca deja el orden correcto.
  static List<int> shuffledOrder(List<String> words, String seed) {
    final order = List.generate(words.length, (i) => i);
    if (words.length < 2) return order;
    final random = Random(seed.codeUnits.fold<int>(7, (a, b) => a * 31 + b));
    do {
      order.shuffle(random);
    } while (List.generate(words.length, (i) => words[order[i]]).join(' ') == words.join(' '));
    return order;
  }

  void _tap(int wordIndex) {
    if (_done) return;
    final audio = AppServices.maybeOf(context)?.audio;
    if (_words[wordIndex] == _words[_placed]) {
      setState(() {
        _placed++;
        _misses = 0;
      });
      if (_done) {
        unawaited(audio?.play(SoundCue.celebrate) ?? Future.value());
        speak(context, widget.phrase.text);
        widget.onDone();
      } else {
        unawaited(audio?.play(SoundCue.correct) ?? Future.value());
        speak(context, _words[wordIndex]);
      }
    } else {
      setState(() => _misses++);
      unawaited(audio?.play(SoundCue.tryAgain) ?? Future.value());
      speak(context, _misses >= 2 ? 'Busca la palabra que brilla.' : '¡Casi! ¿Cuál va ahora?');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // La frase que se va formando.
        Semantics(
          container: true,
          label: _done
              ? 'Frase ordenada: ${widget.phrase.text}'
              : 'Llevas: ${_words.take(_placed).join(' ')}',
          excludeSemantics: true,
          child: Container(
            constraints: const BoxConstraints(minHeight: 64),
            width: double.infinity,
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF8EC),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFFE6D3B5), width: 2),
            ),
            child: Wrap(
              alignment: WrapAlignment.center,
              spacing: 6,
              runSpacing: 6,
              children: [
                for (var i = 0; i < _words.length; i++)
                  i < _placed
                      ? _Chip(text: _words[i], onTap: null, color: const Color(0xFF26A69A))
                      : Container(
                          width: 52,
                          height: 48,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: const Color(0xFFE6D3B5), width: 2),
                          ),
                        ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        if (_done)
          Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 12,
            runSpacing: 8,
            children: [
              Text('¡Muy bien!', style: fredoka(30, color: const Color(0xFF26A69A))),
              if (widget.onNext != null)
                SizedBox(
                  width: 150,
                  child: SpeechActionButton(
                    icon: Icons.arrow_forward_rounded,
                    label: 'Otra frase',
                    color: speechAccent,
                    onPressed: widget.onNext,
                  ),
                ),
            ],
          )
        else
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final i in _shuffled)
                if (!_isPlaced(i))
                  _Chip(
                    text: _words[i],
                    onTap: () => _tap(i),
                    highlighted: _misses >= 2 && _words[i] == _words[_placed],
                  ),
            ],
          ),
      ],
    );
  }

  /// Una tarjeta ya colocada desaparece de abajo. Si una palabra se repite en
  /// la frase, cuenta cuántas veces se ha colocado ya.
  bool _isPlaced(int wordIndex) {
    final word = _words[wordIndex];
    final placedOfWord = _words.take(_placed).where((w) => w == word).length;
    final before = _shuffled.takeWhile((i) => i != wordIndex).where((i) => _words[i] == word).length;
    return before < placedOfWord;
  }
}
