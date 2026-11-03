import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../speech_content.dart';
import 'speech_widgets.dart';

/// Ordenar dibujos (escenas de un cuento, pasos de una historia): aparecen
/// desordenados y el niño los toca en orden; cada uno va a su casilla (1, 2,
/// 3…). Un error no castiga: Lolo anima y, al segundo intento, el que va brilla.
class OrderPictures extends StatefulWidget {
  const OrderPictures({
    super.key,
    required this.pictures,
    required this.labels,
    required this.seed,
    required this.onDone,
    this.color = const Color(0xFF26A69A),
  });

  /// En su orden correcto.
  final List<SpeechPicture> pictures;

  /// Lo que pasa en cada dibujo (se dice al colocarlo; también para el lector
  /// de pantalla).
  final List<String> labels;

  /// Para desordenar siempre igual.
  final String seed;
  final VoidCallback onDone;
  final Color color;

  /// Desordena sin dejar nunca el orden correcto.
  static List<int> shuffled(int n, String seed) {
    final order = List.generate(n, (i) => i);
    if (n < 2) return order;
    final random = Random(seed.codeUnits.fold<int>(11, (a, b) => a * 31 + b));
    do {
      order.shuffle(random);
    } while (List.generate(n, (i) => order[i] == i).every((x) => x));
    return order;
  }

  @override
  State<OrderPictures> createState() => _OrderPicturesState();
}

class _OrderPicturesState extends State<OrderPictures> {
  late final List<int> _order = OrderPictures.shuffled(widget.pictures.length, widget.seed);
  int _placed = 0;
  int _misses = 0;

  bool get _done => _placed == widget.pictures.length;

  void _tap(int i) {
    if (_done) return;
    final audio = AppServices.of(context).audio;
    if (i == _placed) {
      setState(() {
        _placed++;
        _misses = 0;
      });
      speak(context, widget.labels[i]);
      if (_done) {
        unawaited(audio.play(SoundCue.celebrate));
        widget.onDone();
      } else {
        unawaited(audio.play(SoundCue.correct));
      }
    } else {
      setState(() => _misses++);
      unawaited(audio.play(SoundCue.tryAgain));
      speak(
        context,
        _misses >= 2
            ? 'Mira el dibujo que brilla.'
            : '¡Casi! ¿Qué pasó ${_placed == 0 ? 'primero' : 'después'}?',
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final n = widget.pictures.length;
    return LayoutBuilder(
      builder: (context, box) {
        final side = min(150.0, (box.maxWidth - (n - 1) * 8) / n);
        Widget tile(int i, {required bool slot, bool highlight = false}) => Container(
          width: side,
          height: side,
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: highlight ? AppColors.sun : widget.color.withValues(alpha: 0.5),
              width: highlight ? 5 : 3,
            ),
          ),
          child: SpeechPictureView(picture: widget.pictures[i], tint: widget.color),
        );
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Las casillas, en orden.
            Semantics(
              container: true,
              label: _done ? 'Ordenado: ${widget.labels.join(' ')}' : 'Llevas $_placed de $n en orden',
              excludeSemantics: true,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: [
                  for (var k = 0; k < n; k++)
                    k < _placed
                        ? tile(k, slot: true)
                        : Container(
                            width: side,
                            height: side,
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFF8EC),
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(color: const Color(0xFFE6D3B5), width: 2),
                            ),
                            alignment: Alignment.center,
                            child: Text('${k + 1}', style: fredoka(40, color: const Color(0xFFD7C3A0))),
                          ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            if (_done)
              Text('¡Muy bien!', style: fredoka(30, color: widget.color))
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: [
                  for (final i in _order)
                    if (i >= _placed)
                      Semantics(
                        container: true,
                        button: true,
                        label: widget.labels[i],
                        excludeSemantics: true,
                        onTap: () => _tap(i),
                        child: GestureDetector(
                          onTap: () => _tap(i),
                          child: tile(i, slot: false, highlight: _misses >= 2 && i == _placed),
                        ),
                      ),
                ],
              ),
          ],
        );
      },
    );
  }
}
