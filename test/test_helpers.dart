import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/app.dart';
import 'package:pequenos_artistas/learning/audio/learning_audio.dart';
import 'package:pequenos_artistas/learning/learning_controller.dart';
import 'package:pequenos_artistas/learning/learning_store.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/coloring/engine/drawing_painter.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';
import 'package:pequenos_artistas/services/catalog_service.dart';
import 'package:pequenos_artistas/services/drawing_loader.dart';
import 'package:pequenos_artistas/persistence/creation.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';

/// Bundle que sirve los textos de [files] y, si [fromDisk], los archivos
/// reales del proyecto. Lee de forma síncrona para funcionar dentro de las
/// pruebas de widgets (que usan un reloj simulado).
class MemoryBundle extends CachingAssetBundle {
  MemoryBundle(this.files, {this.fromDisk = false});

  final Map<String, String> files;
  final bool fromDisk;

  @override
  Future<ByteData> load(String key) async {
    final content = files[key];
    if (content != null) return ByteData.sublistView(Uint8List.fromList(utf8.encode(content)));
    final file = File(key);
    if (fromDisk && file.existsSync()) return ByteData.sublistView(file.readAsBytesSync());
    throw FlutterError('Recurso no encontrado: $key');
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

/// Cargador de dibujos que lee los SVG reales (y [extra], si se indica).
DrawingLoader diskDrawingLoader([Map<String, String> extra = const {}]) =>
    DrawingLoader(bundle: MemoryBundle(extra, fromDisk: true));

/// Audio simulado de la última app montada (para comprobar sonidos y voz).
RecordingSoundEffects? lastSounds;
RecordingNarrator? lastNarrator;
RecordingMusic? lastMusic;

Future<void> pumpApp(
  WidgetTester tester, {
  CatalogService? service,
  DrawingLoader? loader,
  CreationStore? store,
  LearningController? learning,
  KeyValueBackend? learningBackend,
}) async {
  final controller = learning ?? LearningController(LearningStore(learningBackend ?? MemoryBackend()));
  await controller.load();
  final sounds = lastSounds = RecordingSoundEffects();
  final narrator = lastNarrator = RecordingNarrator();
  final music = lastMusic = RecordingMusic();
  await tester.pumpWidget(
    PequenosArtistasApp(
      catalogService: service ?? realCatalogService(),
      drawingLoader: loader ?? diskDrawingLoader(),
      creationStore: store ?? InMemoryCreationStore(),
      learningController: controller,
      learningAudio: LearningAudio(
        effects: sounds,
        narrator: narrator,
        music: music,
        settings: () => controller.settings,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void setScreenSize(WidgetTester tester, Size size, {double textScale = 1.0}) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}

/// Un punto (en coordenadas del dibujo) claramente dentro de la región [id]
/// tal como se ve: el punto y sus vecinos a [margin] unidades la tocan.
Offset interiorPoint(VectorDrawing drawing, String id, {double step = 8, double margin = 12}) {
  Offset? fallback;
  final box = drawing.region(id)!.bounds.intersect(drawing.viewBox);
  for (var y = box.top + step / 2; y < box.bottom; y += step) {
    for (var x = box.left + step / 2; x < box.right; x += step) {
      final p = Offset(x, y);
      if (drawing.regionAt(p) != id) continue;
      fallback ??= p;
      final ok = [for (var k = 0; k < 8; k++) p + Offset.fromDirection(k * 3.14159265 / 4, margin)]
          .every((q) => drawing.regionAt(q) == id);
      if (ok) return p;
    }
  }
  if (fallback == null) throw StateError('La región $id no es visible');
  return fallback;
}

/// El lienzo interactivo en pantalla.
final drawingCanvasFinder = find.byWidgetPredicate((w) => w is CustomPaint && w.painter is DrawingPainter);

/// Posición global en pantalla de un punto del dibujo.
Offset screenPointOf(WidgetTester tester, VectorDrawing drawing, Offset viewBoxPoint) {
  final box = tester.getRect(drawingCanvasFinder);
  final t = DrawingPainter.fit(drawing.viewBox, box.size);
  return box.topLeft + t.offset + viewBoxPoint * t.scale;
}

/// Colores guardados de la creación más reciente de un dibujo (en hexadecimal).
Future<Map<String, String>?> savedHex(CreationStore store, String drawingId) async {
  final c = await store.latestFor(drawingId);
  return c?.regionColors.map((k, v) => MapEntry(k, Creation.colorToHex(v)));
}

/// Dibujo vectorial real de la colección.
VectorDrawing svgOf(String folder, String id) =>
    parseColoringSvg(File('assets/drawings/$folder/$id.svg').readAsStringSync());

/// «¡Vamos a pintar!» (dentro de «Colorear»): abre el siguiente dibujo fácil.
/// Desde el inicio entra antes en «Colorear».
Future<void> startPainting(WidgetTester tester) async {
  final button = find.bySemanticsLabel('¡Vamos a pintar!');
  if (button.evaluate().isEmpty) {
    await tester.tap(find.bySemanticsLabel('Colorear'));
    await tester.pumpAndSettle();
  }
  await tester.tap(button);
  await tester.pumpAndSettle();
}

/// Abre «Galería» (los dibujos guardados) del inicio. Si se está en
/// «Colorear» (a donde se vuelve tras «¡Vamos a pintar!»), vuelve antes al inicio.
Future<void> openMyGallery(WidgetTester tester) async {
  final home = find.bySemanticsLabel('Volver al inicio');
  if (home.evaluate().isNotEmpty) {
    await tester.tap(home);
    await tester.pumpAndSettle();
  }
  await tester.tap(find.bySemanticsLabel('Galería'));
  await tester.pumpAndSettle();
}
