import 'dart:math';

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Verificación para adultos: una multiplicación con cuatro respuestas.
/// Devuelve `true` solo si se elige la respuesta correcta.
Future<bool> showAdultGate(BuildContext context, {Random? random}) async {
  final rnd = random ?? Random();
  final a = 6 + rnd.nextInt(4); // 6..9
  final b = 6 + rnd.nextInt(4);
  final answer = a * b;
  final options = <int>{answer};
  while (options.length < 4) {
    final delta = (rnd.nextInt(5) + 1) * (rnd.nextBool() ? 1 : -1);
    options.add(answer + delta);
  }
  final shuffled = options.toList()..shuffle(rnd);

  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      icon: const Icon(Icons.lock_rounded, color: AppColors.adultAccent, size: 36),
      title: const Text('Solo para adultos'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Para continuar, responde: ¿cuánto es $a × $b?', textAlign: TextAlign.center),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            alignment: WrapAlignment.center,
            children: [
              for (final option in shuffled)
                OutlinedButton(
                  style: OutlinedButton.styleFrom(minimumSize: const Size(72, 56)),
                  onPressed: () => Navigator.of(context).pop(option == answer),
                  child: Text('$option', style: const TextStyle(fontSize: 20)),
                ),
            ],
          ),
        ],
      ),
      actions: [TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar'))],
    ),
  );
  return result ?? false;
}
