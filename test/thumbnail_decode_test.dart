import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter_test/flutter_test.dart';

import 'test_helpers.dart';

/// Decodifica las 30 miniaturas con el decodificador nativo del motor de
/// Flutter (el mismo código que en Android), al tamaño que usan las tarjetas.
/// Añadida en la Fase 9: en el emulador Android sin aceleración, las miniaturas
/// no se veían («Could not decompress image»). Esta prueba demuestra que los
/// archivos son válidos para Flutter; el fallo es del entorno emulado.
void main() {
  testWidgets('las 30 miniaturas se decodifican con el motor de Flutter', (tester) async {
    final catalog = await tester.runAsync(() => realCatalogService().load());
    final drawings = catalog!.drawings;
    expect(drawings, hasLength(30));
    for (final d in drawings) {
      final bytes = File(d.thumbnailAsset!).readAsBytesSync();
      for (final width in [null, 128, 384]) {
        final image = await tester.runAsync(() async {
          final codec = await ui.instantiateImageCodec(bytes, targetWidth: width);
          return (await codec.getNextFrame()).image;
        });
        expect(image!.width, width ?? 512, reason: '${d.id} a ${width ?? 512} px');
        image.dispose();
      }
    }
  });
}
