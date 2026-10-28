import 'package:flutter/widgets.dart';

import 'catalog_service.dart';

/// Pone los servicios compartidos al alcance de todas las pantallas.
class AppServices extends InheritedWidget {
  const AppServices({super.key, required this.catalog, required super.child});

  final CatalogService catalog;

  static AppServices of(BuildContext context) {
    final services = context.dependOnInheritedWidgetOfExactType<AppServices>();
    assert(services != null, 'AppServices no está en el árbol de widgets');
    return services!;
  }

  @override
  bool updateShouldNotify(AppServices oldWidget) => catalog != oldWidget.catalog;
}
