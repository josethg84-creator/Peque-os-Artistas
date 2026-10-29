import 'package:flutter/material.dart';

/// Transición entre pantallas: desvanecimiento con un leve desplazamiento
/// hacia arriba (sin giros ni zooms que mareen). Con movimiento reducido,
/// solo un desvanecimiento muy corto.
class KidPageTransitionsBuilder extends PageTransitionsBuilder {
  const KidPageTransitionsBuilder();

  @override
  Duration get transitionDuration => const Duration(milliseconds: 280);

  @override
  Duration get reverseTransitionDuration => const Duration(milliseconds: 220);

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    final reduced = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final curved = CurvedAnimation(
      parent: animation,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
    if (reduced) return FadeTransition(opacity: curved, child: child);
    return FadeTransition(
      opacity: curved,
      child: SlideTransition(
        position: Tween(begin: const Offset(0, 0.04), end: Offset.zero).animate(curved),
        child: child,
      ),
    );
  }
}
