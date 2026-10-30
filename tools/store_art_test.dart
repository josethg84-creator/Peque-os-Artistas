// Renderiza, con los componentes reales de la app, las ilustraciones que se usan
// en la imagen destacada de Google Play (store_assets/feature_graphic/).
//
// Uso (desde la raíz): flutter test tools/store_art_test.dart
// Deja PNG en build/store_art/. No forma parte de la batería de pruebas.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/coloring/engine/drawing_painter.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/palette.dart';
import 'package:pequenos_artistas/widgets/mascot.dart';

class _Colors extends ChangeNotifier implements RegionColors {
  _Colors(this.map);
  final Map<String, Color> map;
  @override
  Color? colorOf(String regionId) => map[regionId];
}

Color c(String name) => kidPalette.firstWhere((p) => p.name == name).color;

const cream = Color(0xFFFFF8EC);

final drawings = <String, (String, Map<String, Color>)>{
  'dinosaurio': (
    'assets/drawings/dinosaurs/dinosaurio_01.svg',
    {
      'fondo': cream,
      for (final r in ['pierna_trasera', 'cola', 'cuello', 'cuerpo', 'cabeza', 'brazo', 'pierna'])
        r: c('Verde claro'),
      'pie_trasero': c('Verde'),
      'pie': c('Verde'),
      'barriga': c('Amarillo'),
      'mancha_1': c('Verde'),
      'mancha_2': c('Verde'),
    },
  ),
  'mariposa': (
    'assets/drawings/animals/animal_mariposa.svg',
    {
      'fondo': cream,
      'ala_superior_izquierda': c('Celeste'),
      'ala_superior_derecha': c('Celeste'),
      'ala_inferior_izquierda': c('Rosa'),
      'ala_inferior_derecha': c('Rosa'),
      'mancha_superior_izquierda': c('Amarillo'),
      'mancha_superior_derecha': c('Amarillo'),
      'mancha_inferior_izquierda': c('Morado'),
      'mancha_inferior_derecha': c('Morado'),
      'antena_izquierda': c('Morado'),
      'antena_derecha': c('Morado'),
      'cuerpo': c('Morado'),
      'cabeza': c('Morado'),
    },
  ),
  'avion': (
    'assets/drawings/vehicles/vehiculo_avion.svg',
    {
      'fondo': cream,
      'nube_1': Colors.white,
      'nube_2': Colors.white,
      'ala_trasera': c('Rojo'),
      'cola': c('Rojo'),
      'fuselaje': c('Naranja'),
      'cabina': c('Celeste'),
      for (var i = 1; i <= 4; i++) 'ventanilla_$i': c('Celeste'),
      'estabilizador': c('Rojo'),
      'ala': c('Rojo'),
    },
  ),
};

Future<void> capture(WidgetTester tester, Widget child, Size size, String out) async {
  final key = GlobalKey();
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  await tester.pumpWidget(
    Directionality(
      textDirection: TextDirection.ltr,
      child: Center(child: RepaintBoundary(key: key, child: child)),
    ),
  );
  await tester.pump();
  await tester.runAsync(() async {
    final boundary = key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    final image = await boundary.toImage(pixelRatio: 1);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    File(out)
      ..createSync(recursive: true)
      ..writeAsBytesSync(bytes!.buffer.asUint8List());
  });
}

void main() {
  testWidgets('ilustraciones para la ficha de Google Play', (tester) async {
    addTearDown(tester.view.reset);
    await capture(
      tester,
      const SizedBox(width: 372, height: 600, child: Mascot(size: 600, waves: 0)),
      const Size(800, 800),
      'build/store_art/mascota.png',
    );
    for (final MapEntry(key: name, value: (file, colors)) in drawings.entries) {
      final drawing = parseColoringSvg(File(file).readAsStringSync());
      await capture(
        tester,
        SizedBox.square(
          dimension: 900,
          child: CustomPaint(painter: DrawingPainter(drawing: drawing, colors: _Colors(colors))),
        ),
        const Size(1000, 1000),
        'build/store_art/$name.png',
      );
    }
  });
}
