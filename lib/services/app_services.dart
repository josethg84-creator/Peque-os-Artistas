import 'package:flutter/widgets.dart';

import 'catalog_service.dart';
import 'drawing_loader.dart';
import '../learning/audio/learning_audio.dart';
import '../learning/learning_controller.dart';
import '../persistence/creation_store.dart';

/// Pone los servicios compartidos al alcance de todas las pantallas.
class AppServices extends InheritedWidget {
  const AppServices({
    super.key,
    required this.catalog,
    required this.drawings,
    required this.creations,
    required this.learning,
    required this.audio,
    required super.child,
  });

  final CatalogService catalog;
  final DrawingLoader drawings;
  final CreationStore creations;

  /// Progreso, preferencias y premios de «Aprender jugando».
  final LearningController learning;
  final LearningAudio audio;

  /// Igual que [of], pero sin exigirlos (componentes que también se usan
  /// fuera de la app completa, p. ej. en pruebas).
  static AppServices? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AppServices>();

  static AppServices of(BuildContext context) {
    final services = context.dependOnInheritedWidgetOfExactType<AppServices>();
    assert(services != null, 'AppServices no está en el árbol de widgets');
    return services!;
  }

  @override
  bool updateShouldNotify(AppServices oldWidget) =>
      catalog != oldWidget.catalog ||
      drawings != oldWidget.drawings ||
      creations != oldWidget.creations ||
      learning != oldWidget.learning ||
      audio != oldWidget.audio;
}
