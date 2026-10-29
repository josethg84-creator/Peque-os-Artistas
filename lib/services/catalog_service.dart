import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/drawing.dart';
import '../models/drawing_catalog.dart';
import '../models/drawing_category.dart';

/// Lee `assets/catalog/catalog.json` y comprueba que los archivos existan.
///
/// Nunca lanza excepciones hacia la interfaz: un catálogo ausente o dañado
/// produce un [DrawingCatalog] vacío con la incidencia descrita, y las
/// entradas inválidas se descartan una a una.
class CatalogService {
  CatalogService({AssetBundle? bundle, this._assetLister}) : _bundle = bundle ?? rootBundle;

  static const catalogPath = 'assets/catalog/catalog.json';

  final AssetBundle _bundle;
  final Future<Set<String>> Function()? _assetLister;
  Future<DrawingCatalog>? _cache;

  Future<DrawingCatalog> load() => _cache ??= _load();

  Future<DrawingCatalog> _load() async {
    final String raw;
    try {
      raw = await _bundle.loadString(catalogPath);
    } catch (_) {
      return DrawingCatalog(drawings: const [], issues: const ['No se encontró $catalogPath']);
    }
    final Set<String> assets;
    try {
      assets = await (_assetLister?.call() ?? _listBundleAssets());
    } catch (_) {
      return DrawingCatalog(drawings: const [], issues: const ['No se pudo leer la lista de recursos']);
    }
    return parse(raw, assets);
  }

  Future<Set<String>> _listBundleAssets() async {
    final manifest = await AssetManifest.loadFromAssetBundle(_bundle);
    return manifest.listAssets().toSet();
  }

  /// Convierte el JSON en un catálogo. [assets] son las rutas que existen.
  static DrawingCatalog parse(String raw, Set<String> assets) {
    final issues = <String>[];
    final Object? data;
    try {
      data = jsonDecode(raw);
    } on FormatException {
      return DrawingCatalog(drawings: const [], issues: const ['El catálogo no es un JSON válido']);
    }
    final list = data is Map<String, dynamic> ? data['drawings'] : null;
    if (list is! List) {
      return DrawingCatalog(
        drawings: const [],
        issues: const ['El catálogo no contiene la lista "drawings"'],
      );
    }

    final drawings = <Drawing>[];
    final seen = <String>{};
    for (final (index, entry) in list.indexed) {
      if (entry is! Map<String, dynamic>) {
        issues.add('Entrada $index: formato inválido');
        continue;
      }
      final id = _text(entry['id']);
      final name = _text(entry['name']);
      final file = _text(entry['file']);
      final category = DrawingCategory.fromId(_text(entry['category']));
      final difficulty = Difficulty.fromId(_text(entry['difficulty']));
      final label = id ?? 'entrada $index';
      if (id == null || name == null || file == null) {
        issues.add('$label: faltan id, nombre o archivo');
        continue;
      }
      if (category == null) {
        issues.add('$label: categoría desconocida "${entry['category']}"');
        continue;
      }
      if (!seen.add(id)) {
        issues.add('$label: id duplicado');
        continue;
      }
      if (!_isSafePath(file) || !assets.contains(file)) {
        issues.add('$label: no existe el archivo $file');
        continue;
      }
      // `preview` es el nombre del campo en la versión 1 del catálogo.
      final thumbnail = _text(entry['thumbnail']) ?? _text(entry['preview']);
      final thumbnailOk = thumbnail != null && _isSafePath(thumbnail) && assets.contains(thumbnail);
      if (thumbnail == null) {
        issues.add('$label: no tiene miniatura');
      } else if (!thumbnailOk) {
        issues.add('$label: falta la miniatura $thumbnail');
      }
      if (difficulty == null) {
        issues.add('$label: dificultad desconocida "${entry['difficulty']}" (se usa fácil)');
      }
      drawings.add(
        Drawing(
          id: id,
          name: name,
          category: category,
          file: file,
          thumbnail: thumbnail,
          thumbnailAvailable: thumbnailOk,
          difficulty: difficulty ?? Difficulty.easy,
          recommendedAge: _text(entry['recommended_age']) ?? '4-7',
          description: _text(entry['description']) ?? '',
          regions: entry['regions'] is int ? entry['regions'] as int : null,
        ),
      );
    }
    return DrawingCatalog(drawings: drawings, issues: issues);
  }

  static String? _text(Object? v) => v is String && v.trim().isNotEmpty ? v.trim() : null;

  static bool _isSafePath(String path) =>
      path.startsWith('assets/') && !path.contains('..') && !path.contains('\\') && !path.contains('://');
}
