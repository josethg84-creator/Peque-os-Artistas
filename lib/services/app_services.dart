import 'package:flutter/widgets.dart';

import 'catalog_service.dart';
import 'drawing_loader.dart';
import '../persistence/creation_store.dart';

/// Pone los servicios compartidos al alcance de todas las pantallas.
class AppServices extends InheritedWidget {
  const AppServices({
    super.key,
    required this.catalog,
    required this.drawings,
    required this.creations,
    required super.child,
  });

  final CatalogService catalog;
  final DrawingLoader drawings;
  final CreationStore creations;

  static AppServices of(BuildContext context) {
    final services = context.dependOnInheritedWidgetOfExactType<AppServices>();
    assert(services != null, 'AppServices no está en el árbol de widgets');
    return services!;
  }

  @override
  bool updateShouldNotify(AppServices oldWidget) =>
      catalog != oldWidget.catalog || drawings != oldWidget.drawings || creations != oldWidget.creations;
}
