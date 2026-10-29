import 'package:flutter/services.dart';

import '../coloring/engine/svg_drawing_parser.dart';
import '../coloring/engine/svg_path_parser.dart';
import '../coloring/engine/vector_drawing.dart';

/// No se pudo cargar un dibujo (archivo ausente o con formato no válido).
class DrawingLoadException implements Exception {
  DrawingLoadException(this.file, this.reason);
  final String file;
  final String reason;

  @override
  String toString() => 'No se pudo cargar $file: $reason';
}

/// Carga y analiza los SVG de los dibujos. Guarda en memoria los últimos
/// [cacheSize] dibujos para que volver a abrirlos sea instantáneo sin
/// acumular memoria (cada dibujo ocupa unas decenas de KB).
class DrawingLoader {
  DrawingLoader({AssetBundle? bundle, this.cacheSize = 6}) : _bundle = bundle ?? rootBundle;

  final AssetBundle _bundle;
  final int cacheSize;
  final _cache = <String, Future<VectorDrawing>>{};

  Future<VectorDrawing> load(String file) {
    final cached = _cache.remove(file);
    if (cached != null) {
      _cache[file] = cached; // Pasa a ser el más reciente.
      return cached;
    }
    final future = _load(file);
    _cache[file] = future;
    // Un fallo no se guarda: se podrá reintentar.
    future.then<void>(
      (_) {},
      onError: (Object _) {
        if (identical(_cache[file], future)) _cache.remove(file);
      },
    );
    while (_cache.length > cacheSize) {
      _cache.remove(_cache.keys.first);
    }
    return future;
  }

  Future<VectorDrawing> _load(String file) async {
    final String source;
    try {
      source = await _bundle.loadString(file, cache: false);
    } catch (_) {
      throw DrawingLoadException(file, 'el archivo no existe');
    }
    try {
      return parseColoringSvg(source);
    } on DrawingFormatException catch (e) {
      throw DrawingLoadException(file, e.message);
    }
  }
}
