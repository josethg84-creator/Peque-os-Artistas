import 'package:flutter/widgets.dart';

import '../../theme/app_motion.dart';

/// Envuelve un elemento táctil para darle respuesta inmediata al pulsar (se
/// encoge un poco) sin interceptar el toque: el hijo sigue gestionándolo.
/// Las acciones duplicadas se evitan con [guardRoute].
class Pressable extends StatefulWidget {
  const Pressable({super.key, required this.child, this.scale = 0.94, this.enabled = true});

  final Widget child;
  final double scale;
  final bool enabled;

  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable> {
  bool _down = false;

  void _set(bool down) {
    if (_down != down && mounted) setState(() => _down = down);
  }

  @override
  Widget build(BuildContext context) {
    final reduced = AppMotion.reduced(context);
    return Listener(
      onPointerDown: widget.enabled ? (_) => _set(true) : null,
      onPointerUp: (_) => _set(false),
      onPointerCancel: (_) => _set(false),
      child: AnimatedScale(
        scale: _down && !reduced ? widget.scale : 1,
        duration: AppMotion.fast,
        curve: AppMotion.standard,
        child: widget.child,
      ),
    );
  }
}

/// Devuelve [action] protegida: solo se ejecuta si la pantalla que contiene
/// [context] sigue en primer plano. Así, un segundo toque mientras ya se abre
/// (o se cierra) otra pantalla no abre una segunda ni vuelve atrás dos veces,
/// sin frenar los toques rápidos normales (deshacer, colores…).
VoidCallback? guardRoute(BuildContext context, VoidCallback? action) {
  if (action == null) return null;
  return () {
    final route = ModalRoute.of(context);
    if (route != null && !route.isCurrent) return;
    action();
  };
}
