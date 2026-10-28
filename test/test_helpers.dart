import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/app.dart';
import 'package:pequenos_artistas/services/catalog_service.dart';

/// Bundle en memoria para controlar exactamente qué recursos existen.
class MemoryBundle extends CachingAssetBundle {
  MemoryBundle(this.files);

  final Map<String, String> files;

  @override
  Future<ByteData> load(String key) async {
    final content = files[key];
    if (content == null) throw FlutterError('Recurso no encontrado: $key');
    return ByteData.sublistView(Uint8List.fromList(utf8.encode(content)));
  }
}

/// Lista real de archivos de `assets/` en el disco (rutas relativas).
Set<String> diskAssets() =>
    Directory('assets')
        .listSync(recursive: true)
        .whereType<File>()
        .map((f) => f.path.replaceAll('\\', '/'))
        .toSet();

String realCatalogJson() => File(CatalogService.catalogPath).readAsStringSync();

/// Servicio con el catálogo real de la Fase 1 y los archivos reales del disco.
CatalogService realCatalogService() {
  final json = realCatalogJson();
  final assets = diskAssets();
  return CatalogService(
    bundle: MemoryBundle({CatalogService.catalogPath: json}),
    assetLister: () async => assets,
  );
}

/// Servicio con un catálogo y una lista de recursos inventados.
CatalogService fakeCatalogService(String json, Set<String> assets) =>
    CatalogService(bundle: MemoryBundle({CatalogService.catalogPath: json}), assetLister: () async => assets);

Future<void> pumpApp(WidgetTester tester, {CatalogService? service}) async {
  await tester.pumpWidget(PequenosArtistasApp(catalogService: service ?? realCatalogService()));
  await tester.pumpAndSettle();
}

void setScreenSize(WidgetTester tester, Size size, {double textScale = 1.0}) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}
