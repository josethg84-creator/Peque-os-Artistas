import 'package:flutter/widgets.dart';

/// Tiempos y curvas comunes de la app: breves y consistentes.
abstract final class AppMotion {
  static const fast = Duration(milliseconds: 120);
  static const medium = Duration(milliseconds: 240);
  static const slow = Duration(milliseconds: 380);

  static const standard = Curves.easeOutCubic;
  static const bounce = Curves.easeOutBack;

  /// El sistema pide reducir el movimiento (ajuste de accesibilidad).
  static bool reduced(BuildContext context) => MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  /// [d] o cero si hay que reducir el movimiento.
  static Duration of(BuildContext context, Duration d) => reduced(context) ? Duration.zero : d;
}
