import 'package:flutter/material.dart';

import '../widgets/motion/kid_page_transitions.dart';
import 'app_colors.dart';
import 'app_dimens.dart';

abstract final class AppTheme {
  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.coral,
      primary: AppColors.coral,
      secondary: AppColors.sky,
      surface: AppColors.surface,
      brightness: Brightness.light,
    );
    final base = ThemeData(colorScheme: scheme, useMaterial3: true);
    final text = base.textTheme.apply(bodyColor: AppColors.ink, displayColor: AppColors.ink);
    return base.copyWith(
      scaffoldBackgroundColor: AppColors.background,
      textTheme: text.copyWith(
        displaySmall: text.displaySmall?.copyWith(fontWeight: FontWeight.w800),
        headlineMedium: text.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
        headlineSmall: text.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
        titleLarge: text.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        titleMedium: text.titleMedium?.copyWith(fontWeight: FontWeight.w700),
      ),
      materialTapTargetSize: MaterialTapTargetSize.padded,
      // Transiciones suaves sin efectos intensos.
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: KidPageTransitionsBuilder(),
          TargetPlatform.iOS: KidPageTransitionsBuilder(),
          TargetPlatform.linux: KidPageTransitionsBuilder(),
          TargetPlatform.macOS: KidPageTransitionsBuilder(),
          TargetPlatform.windows: KidPageTransitionsBuilder(),
          TargetPlatform.fuchsia: KidPageTransitionsBuilder(),
        },
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(AppDimens.minTouchTarget, AppDimens.minTouchTarget),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimens.radiusMedium)),
          textStyle: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
        ),
      ),
      tooltipTheme: const TooltipThemeData(
        textStyle: TextStyle(fontSize: 16, color: Colors.white),
        waitDuration: Duration(milliseconds: 400),
      ),
      snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
    );
  }

  /// Tema neutro para la zona de adultos.
  static ThemeData adult() {
    return ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: AppColors.adultAccent),
      scaffoldBackgroundColor: AppColors.adultBackground,
      useMaterial3: true,
    );
  }
}
