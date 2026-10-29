import 'package:flutter/material.dart';

import '../models/drawing_catalog.dart';
import '../services/app_services.dart';
import 'motion/delayed_loading.dart';

/// Carga el catálogo una sola vez (el servicio lo guarda en caché) y muestra
/// un indicador mientras tanto.
class CatalogBuilder extends StatefulWidget {
  const CatalogBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, DrawingCatalog catalog) builder;

  @override
  State<CatalogBuilder> createState() => _CatalogBuilderState();
}

class _CatalogBuilderState extends State<CatalogBuilder> {
  Future<DrawingCatalog>? _future;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _future ??= AppServices.of(context).catalog.load();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<DrawingCatalog>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const DelayedLoading(message: 'Preparando tus colores…');
        }
        return widget.builder(context, snapshot.data ?? DrawingCatalog.empty);
      },
    );
  }
}
