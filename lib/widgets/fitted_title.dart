import 'package:flutter/material.dart';

/// Título que usa el primer estilo de [styles] con el que cabe entero en
/// [maxLines] líneas sin partir ninguna palabra (en teléfonos estrechos, un
/// título largo como «Encuentra a los animales» baja de tamaño en lugar de
/// cortarse a mitad de palabra). Si no cabe con ninguno, usa el último con
/// puntos suspensivos.
class FittedTitle extends StatelessWidget {
  const FittedTitle(this.text, {super.key, required this.styles, this.maxLines = 2, this.textAlign});

  final String text;
  final List<TextStyle?> styles;
  final int maxLines;
  final TextAlign? textAlign;

  static bool fits(String text, TextStyle? style, double maxWidth, int maxLines, TextScaler scaler) {
    final direction = TextDirection.ltr;
    // Ninguna palabra puede ser más ancha que la línea.
    for (final word in text.split(RegExp(r'\s+'))) {
      final p = TextPainter(
        text: TextSpan(text: word, style: style),
        textDirection: direction,
        textScaler: scaler,
      )..layout();
      if (p.width > maxWidth) return false;
    }
    final p = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: direction,
      textScaler: scaler,
      maxLines: maxLines,
    )..layout(maxWidth: maxWidth);
    return !p.didExceedMaxLines;
  }

  @override
  Widget build(BuildContext context) {
    final scaler = MediaQuery.textScalerOf(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final style = styles.firstWhere(
          (s) => fits(text, s, constraints.maxWidth, maxLines, scaler),
          orElse: () => styles.last,
        );
        return Text(
          text,
          maxLines: maxLines,
          overflow: TextOverflow.ellipsis,
          style: style,
          textAlign: textAlign,
        );
      },
    );
  }
}
