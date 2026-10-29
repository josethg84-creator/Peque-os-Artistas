import 'package:flutter/widgets.dart';

import '../services/app_services.dart';
import '../services/progress_store.dart';

/// Proporciona los ids de los dibujos que tienen colores guardados y se
/// actualiza cuando el almacén avisa de un cambio. Mientras carga, o si el
/// almacén falla, entrega un conjunto vacío (sin indicadores).
class SavedIdsBuilder extends StatefulWidget {
  const SavedIdsBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, Set<String> savedIds) builder;

  @override
  State<SavedIdsBuilder> createState() => _SavedIdsBuilderState();
}

class _SavedIdsBuilderState extends State<SavedIdsBuilder> {
  ProgressStore? _store;
  Set<String> _ids = const {};

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_store == null) {
      _store = AppServices.of(context).progress..changes.addListener(_load);
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final all = await _store!.loadAll();
      if (!mounted) return;
      setState(() {
        _ids = {for (final p in all) p.drawingId};
      });
    } catch (_) {
      // Sin indicadores: no impide usar la galería.
    }
  }

  @override
  void dispose() {
    _store?.changes.removeListener(_load);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.builder(context, _ids);
}
