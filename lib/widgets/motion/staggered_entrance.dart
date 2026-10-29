import 'package:flutter/widgets.dart';

import '../../theme/app_motion.dart';

/// Aparición suave (desvanecimiento y un leve desplazamiento hacia arriba) con
/// un pequeño retraso según la posición, para que las tarjetas entren en
/// orden. Solo anima la primera vez; no bloquea los toques; con movimiento
/// reducido aparece directamente.
class StaggeredEntrance extends StatefulWidget {
  const StaggeredEntrance({super.key, required this.index, required this.child});

  final int index;
  final Widget child;

  /// Retraso entre tarjetas y retraso máximo (no se hace esperar al niño).
  static const step = Duration(milliseconds: 45);
  static const maxDelay = Duration(milliseconds: 270);

  /// Solo las primeras tarjetas (las visibles al abrir la pantalla) entran
  /// animadas; las que aparecen al desplazarse se muestran sin más.
  static const animatedItems = 12;

  static Widget wrap(int index, Widget child) =>
      index < animatedItems ? StaggeredEntrance(index: index, child: child) : child;

  @override
  State<StaggeredEntrance> createState() => _StaggeredEntranceState();
}

class _StaggeredEntranceState extends State<StaggeredEntrance> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: AppMotion.slow);
  late Animation<double> _t = CurvedAnimation(parent: _c, curve: AppMotion.standard);
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (AppMotion.reduced(context)) {
      _c.value = 1;
      return;
    }
    final delay = StaggeredEntrance.step * widget.index;
    final capped = delay > StaggeredEntrance.maxDelay ? StaggeredEntrance.maxDelay : delay;
    // El retraso forma parte de la propia animación (sin temporizadores).
    final total = capped + AppMotion.slow;
    _c.duration = total;
    final start = capped.inMicroseconds / total.inMicroseconds;
    _t = CurvedAnimation(
      parent: _c,
      curve: Interval(start, 1, curve: AppMotion.standard),
    );
    _c.forward();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _t,
      child: widget.child,
      builder: (context, child) => Opacity(
        opacity: _t.value,
        child: Transform.translate(offset: Offset(0, (1 - _t.value) * 18), child: child),
      ),
    );
  }
}
