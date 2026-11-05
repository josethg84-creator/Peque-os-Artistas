import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/aac/aac_catalog.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';
import 'package:pequenos_artistas/speech/widgets/speech_widgets.dart';

import '../test_helpers.dart';

const folder = 'assets/images/quiero_decir/';
const categoryImages = {
  'comida': 'comer',
  'personas': 'nino',
  'juegos': 'pelota',
  'actividades': 'pintar',
  'lugares': 'casa',
};
const pictogramImages = {
  'comer': 'comer',
  'casa': 'casa',
  'pintar': 'pintar',
  'yo': 'nino',
  'pelota': 'pelota',
};

AacCatalog realCatalog() => AacCatalog.parse(
  jsonDecode(File('assets/aac/pictograms.json').readAsStringSync()) as Map<String, dynamic>,
);

void main() {
  test('cinco categorías y cinco pictogramas usan su ilustración, con icono de reserva', () {
    final catalog = realCatalog();
    for (final c in catalog.categories) {
      final name = categoryImages[c.id];
      expect(c.image, name == null ? isNull : '$folder$name.webp', reason: c.id);
    }
    for (final MapEntry(key: id, value: name) in pictogramImages.entries) {
      final picture = catalog.pictograms.firstWhere((p) => p.id == id).picture;
      expect(picture, isA<ImagePicture>(), reason: id);
      picture as ImagePicture;
      expect(picture.path, '$folder$name.webp', reason: id);
      expect(picture.fallback, isNotNull, reason: '$id tiene icono por si falla la imagen');
    }
    expect(File('pubspec.yaml').readAsStringSync(), contains('    - $folder\n'));
  });

  test('las imágenes son WEBP válidos y ligeros', () {
    for (final name in {...categoryImages.values, ...pictogramImages.values}) {
      final file = File('$folder$name.webp');
      final bytes = file.readAsBytesSync();
      expect(String.fromCharCodes(bytes.take(4)), 'RIFF', reason: name);
      expect(String.fromCharCodes(bytes.skip(8).take(4)), 'WEBP', reason: name);
      expect(bytes.length, lessThan(100 * 1024), reason: name);
    }
  });

  for (final size in const [Size(360, 720), Size(1280, 800)]) {
    testWidgets(
      '${size.width.toInt()}×${size.height.toInt()}: las tarjetas de categoría muestran su ilustración',
      (tester) async {
        setScreenSize(tester, size);
        await pumpApp(tester);
        tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.aac);
        await tester.pumpAndSettle();
        for (final name in ['Comida y bebida', 'Familia y personas', 'Juegos', 'Actividades', 'Lugares']) {
          final card = find.bySemanticsLabel(name);
          await tester.scrollUntilVisible(card, 200, scrollable: find.byType(Scrollable).first);
          final images = find.descendant(of: card, matching: find.byType(Image));
          expect(images, findsOneWidget, reason: name);
          expect(tester.widget<Image>(images).fit, BoxFit.contain, reason: name);
          expect(find.text(name), findsOneWidget, reason: 'el título sigue siendo texto');
        }
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('el pictograma «pelota» se ve con su ilustración y se sigue diciendo', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.aac);
    await tester.pumpAndSettle();
    final juegos = find.bySemanticsLabel('Juegos');
    await tester.scrollUntilVisible(juegos, 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(juegos);
    await tester.pumpAndSettle();
    final pelota = find.bySemanticsLabel('Pelota');
    await tester.scrollUntilVisible(pelota, 200, scrollable: find.byType(Scrollable).last);
    expect(find.byWidgetPredicate((w) => w is SpeechPictureView && w.picture is ImagePicture), findsWidgets);
    await tester.tap(pelota.last);
    await tester.pump();
    expect(lastNarrator!.spoken.last.toLowerCase(), 'pelota');
  });

  testWidgets('si la imagen falta, el pictograma muestra su icono', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: SizedBox(
          width: 120,
          height: 120,
          child: SpeechPictureView(
            picture: ImagePicture(
              'assets/images/quiero_decir/no_existe.webp',
              fallback: IconPicture('house', null),
            ),
          ),
        ),
      ),
    );
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 200)));
    await tester.pump();
    expect(find.byIcon(Icons.house), findsOneWidget);
  });
}
