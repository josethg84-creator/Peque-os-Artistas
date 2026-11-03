import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../speech_content.dart';
import 'speech_widgets.dart';

class WordChip extends StatelessWidget {
  const WordChip({
    super.key,
    required this.text,
    required this.onTap,
    this.semanticsLabel,
    this.color = const Color(0xFFF06292),
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

/// Ordenar una frase u oración: las palabras aparecen desordenadas y el niño
/// las toca en orden. Una palabra equivocada no castiga: tiembla un poco y Lolo anima; tras
/// dos intentos, la palabra que va se ilumina para ayudar.
class OrderWords extends StatefulWidget {
  const OrderWords({
    super.key,
    required this.text,
    required this.seed,
    required this.onDone,
    required this.onNext,
    this.nextLabel = 'Otra frase',
  });

  /// La frase completa, con su puntuación.
  final String text;

  /// Para desordenar siempre igual la misma frase.
  final String seed;
  final VoidCallback onDone;
  final VoidCallback? onNext;

  /// Texto del botón para seguir («Otra frase», «Otra oración»).
  final String nextLabel;

  @override
  State<OrderWords> createState() => OrderWordsState();
}

class OrderWordsState extends State<OrderWords> {
  late final List<String> _words = SpeechPhrase(
    id: widget.seed,
    text: widget.text,
    picture: const SwatchPicture(Color(0xFFFFFFFF)),
  ).words;

  /// Orden en que se muestran las tarjetas (índices de [_words]).
  late final List<int> _shuffled = shuffledOrder(_words, widget.seed);
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
        speak(context, widget.text);
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
          label: _done ? 'Frase ordenada: ${widget.text}' : 'Llevas: ${_words.take(_placed).join(' ')}',
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
                      ? WordChip(text: _words[i], onTap: null, color: const Color(0xFF26A69A))
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
                    label: widget.nextLabel,
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
                  WordChip(
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
