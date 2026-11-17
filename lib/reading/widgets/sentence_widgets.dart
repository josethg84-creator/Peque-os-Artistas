import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../sentences.dart';

/// La oración en letra grande, palabra por palabra. Cada palabra se puede
/// tocar para oírla. La palabra que suena se marca con fondo, subrayado grueso
/// y letra algo mayor (no solo con color); la pista, con una bombilla.
class SentenceWords extends StatelessWidget {
  const SentenceWords({
    super.key,
    required this.sentence,
    required this.color,
    this.highlighted,
    this.hint,
    this.onTapWord,
    this.fontSize = 40,
  });

  final ReadingSentence sentence;
  final Color color;

  /// Palabra que suena ahora.
  final int? highlighted;

  /// Palabra que responde la pregunta (pista).
  final int? hint;
  final ValueChanged<int>? onTapWord;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final words = sentence.words;
    return Semantics(
      container: true,
      label: 'Oración: ${sentence.text}',
      child: Wrap(
        alignment: WrapAlignment.center,
        spacing: 6,
        runSpacing: 10,
        children: [
          for (final (i, w) in words.indexed)
            _WordTile(
              text: i == words.length - 1 ? '${w.text}.' : w.text,
              word: w.text,
              color: color,
              fontSize: fontSize,
              active: highlighted == i,
              hint: hint == i,
              onTap: onTapWord == null ? null : () => onTapWord!(i),
            ),
        ],
      ),
    );
  }
}

class _WordTile extends StatelessWidget {
  const _WordTile({
    required this.text,
    required this.word,
    required this.color,
    required this.fontSize,
    required this.active,
    required this.hint,
    required this.onTap,
  });

  final String text;
  final String word;
  final Color color;
  final double fontSize;
  final bool active;
  final bool hint;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final strong = Color.lerp(color, Colors.black, 0.35)!;
    return Semantics(
      button: onTap != null,
      selected: active,
      label: hint ? 'Palabra $word, pista' : 'Palabra $word',
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedScale(
          scale: active ? 1.12 : 1,
          duration: const Duration(milliseconds: 120),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 120),
            constraints: const BoxConstraints(minHeight: 48, minWidth: 48),
            padding: const EdgeInsets.fromLTRB(8, 2, 8, 0),
            decoration: BoxDecoration(
              color: active
                  ? const Color(0xFFFFF1A8)
                  : hint
                  ? const Color(0xFFFFF8E1)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(14),
              border: hint ? Border.all(color: AppColors.sun, width: 3) : null,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (hint) const Icon(Icons.lightbulb_rounded, color: Color(0xFFF9A825), size: 20),
                Text(
                  text,
                  style: fredoka(fontSize, weight: active ? FontWeight.w700 : FontWeight.w500, color: strong),
                ),
                // Subrayado grueso de la palabra que suena (además del color).
                AnimatedContainer(
                  duration: const Duration(milliseconds: 120),
                  height: 6,
                  width: active ? fontSize * 0.9 : 0,
                  margin: const EdgeInsets.only(bottom: 4),
                  decoration: BoxDecoration(color: strong, borderRadius: BorderRadius.circular(3)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Ilustración de la oración. Mientras no exista la ilustración 3D, es una
/// escena provisional hecha con dibujos de la app, y se indica.
class SentencePicture extends StatelessWidget {
  const SentencePicture({super.key, required this.sentence, required this.color, this.label});

  final ReadingSentence sentence;
  final Color color;

  /// Texto para lectores de pantalla.
  final String? label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      image: true,
      label: label ?? 'Ilustración de la oración',
      excludeSemantics: true,
      child: Stack(
        alignment: Alignment.center,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: SpeechPictureView(picture: sentence.picture, tint: color),
          ),
          if (!sentence.imageReady)
            Positioned(
              right: 6,
              bottom: 6,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text('Ilustración provisional', style: Theme.of(context).textTheme.bodySmall),
              ),
            ),
        ],
      ),
    );
  }
}

/// Tarjeta de una respuesta con imagen. Una opción descartada se atenúa y
/// lleva una cruz; la correcta, una marca de verificación (no solo color).
class AnswerCard extends StatelessWidget {
  const AnswerCard({
    super.key,
    required this.label,
    required this.child,
    required this.color,
    required this.onTap,
    this.text,
    this.wrong = false,
    this.right = false,
    this.width = 170,
  });

  final String label;
  final Widget child;
  final String? text;
  final Color color;
  final VoidCallback? onTap;
  final bool wrong;
  final bool right;
  final double width;

  @override
  Widget build(BuildContext context) {
    final state = right
        ? ', correcta'
        : wrong
        ? ', no es esta'
        : '';
    return Semantics(
      button: true,
      enabled: onTap != null,
      label: '$label$state',
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: Opacity(
          opacity: wrong ? 0.45 : 1,
          child: Container(
            width: width,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: right ? const Color(0xFFE8F8EE) : Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: right ? AppColors.leaf : Color.lerp(color, Colors.white, 0.3)!,
                width: right ? 5 : 3,
              ),
              boxShadow: const [BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 3))],
            ),
            child: Stack(
              children: [
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    child,
                    if (text != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        text!,
                        style: fredoka(24, color: AppColors.ink),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ],
                ),
                if (wrong || right)
                  Positioned(
                    right: 0,
                    top: 0,
                    child: Icon(
                      right ? Icons.check_circle_rounded : Icons.cancel_rounded,
                      color: right ? AppColors.leaf : AppColors.inkSoft,
                      size: 36,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Una palabra para «Ordena la oración» (se toca o se arrastra).
class WordChip extends StatelessWidget {
  const WordChip({super.key, required this.text, required this.color, this.onTap, this.glow = false});

  final String text;
  final Color color;
  final VoidCallback? onTap;
  final bool glow;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      button: onTap != null,
      label: 'Palabra ${text.replaceAll('.', '')}',
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 56, minWidth: 56),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: color, width: 3),
            boxShadow: [
              if (glow) const BoxShadow(color: AppColors.sun, blurRadius: 14, spreadRadius: 4),
              const BoxShadow(color: Color(0x14000000), blurRadius: 6, offset: Offset(0, 3)),
            ],
          ),
          child: Text(text, style: fredoka(28, color: Color.lerp(color, Colors.black, 0.4)!)),
        ),
      ),
    );
  }
}
