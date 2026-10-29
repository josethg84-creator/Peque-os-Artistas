import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';

/// Puntos de progreso: «Pregunta 2 de 5». Los hechos llevan una estrella.
class QuestionProgress extends StatelessWidget {
  const QuestionProgress({super.key, required this.done, required this.total, this.label = 'Pregunta'});

  final int done;
  final int total;
  final String label;

  @override
  Widget build(BuildContext context) {
    final current = (done + 1).clamp(1, total);
    return Semantics(
      label: '$label $current de $total',
      excludeSemantics: true,
      child: Wrap(
        alignment: WrapAlignment.center,
        spacing: 6,
        runSpacing: 6,
        children: [
          for (var i = 0; i < total; i++)
            Icon(
              i < done
                  ? Icons.star_rounded
                  : (i == done ? Icons.radio_button_checked_rounded : Icons.circle_outlined),
              size: 30,
              color: i < done ? AppColors.sun : AppColors.inkSoft,
            ),
        ],
      ),
    );
  }
}
