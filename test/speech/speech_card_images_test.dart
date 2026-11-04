import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/screens/speech_hub_screen.dart';

import '../test_helpers.dart';

/// Ilustraciones 3D de las tarjetas de «Aprendo a Hablar».
const expected = {
  'Mis primeras palabras': 'mis_primeras_palabras.webp',
  'Aprendo frases': 'aprendo_frases.webp',
  'Juegos de palabras': 'juegos_de_palabras.webp',
  'Construyo oraciones': 'construyo_oraciones.webp',
  'Mi historia': 'mi_historia.webp',
  'Yo puedo expresarme': 'yo_puedo_expresarme.webp',
  'Aprendo los verbos': 'aprendo_los_verbos.webp',
  'Hablemos con Lolo': 'hablemos_con_lolo.webp',
  'Lolo me cuenta un cuento': 'lolo_me_cuenta_un_cuento.webp',
  'Ahora cuéntamelo tú': 'ahora_cuentamelo_tu.webp',
  'Sílabas y sonidos': 'silabas_y_sonidos.webp',
  'Escucho y respondo': 'escucho_y_respondo.webp',
};

void main() {
  test('las tarjetas con ilustración apuntan a su WEBP y las demás conservan su icono', () {
    for (final a in SpeechHubScreen.activities) {
      final file = expected[a.title];
      expect(a.image, file == null ? isNull : '${SpeechActivity.imageFolder}$file', reason: a.title);
    }
    final pubspec = File('pubspec.yaml').readAsStringSync();
    expect(pubspec, contains('    - ${SpeechActivity.imageFolder}\n'));
  });

  test('las imágenes que ya estén en la carpeta son WEBP válidos', () {
    for (final name in expected.values) {
      final file = File('${SpeechActivity.imageFolder}$name');
      if (!file.existsSync()) continue; // aún no subida: la tarjeta usa su icono
      final head = file.readAsBytesSync().take(12).toList();
      expect(String.fromCharCodes(head.take(4)), 'RIFF', reason: name);
      expect(String.fromCharCodes(head.skip(8)), 'WEBP', reason: name);
    }
  });

  for (final size in const [Size(360, 720), Size(420, 900), Size(800, 1280), Size(1280, 800)]) {
    testWidgets(
      'menú a ${size.width.toInt()}×${size.height.toInt()}: imagen con BoxFit.contain, títulos y subtítulos',
      (tester) async {
        setScreenSize(tester, size);
        await pumpApp(tester);
        await tester.tap(find.bySemanticsLabel('Aprendo a Hablar').first);
        await tester.pumpAndSettle();
        for (final MapEntry(key: title, value: file) in expected.entries) {
          final card = find.bySemanticsLabel(RegExp('^${RegExp.escape(title)}'));
          await tester.scrollUntilVisible(card, 250, scrollable: find.byType(Scrollable).first);
          final activity = SpeechHubScreen.activities.firstWhere((a) => a.title == title);
          expect(find.text(activity.subtitle), findsOneWidget, reason: title);
          final image = tester.widget<Image>(
            find.byWidgetPredicate(
              (w) =>
                  w is Image &&
                  w.image is ResizeImage &&
                  '${(w.image as ResizeImage).imageProvider}'.contains(file),
            ),
          );
          expect(image.fit, BoxFit.contain, reason: title);
          final box = tester.getRect(find.byWidget(image));
          expect(box.width, greaterThan(40), reason: '$title se ve con un tamaño útil');
          expect(tester.takeException(), isNull);
        }
      },
    );
  }

  testWidgets('si falta el archivo, la tarjeta muestra su icono (sin emojis ni huecos)', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: SizedBox(
          width: 120,
          height: 120,
          child: SpeechActivityArt(
            icon: Icons.abc_rounded,
            color: Color(0xFF8FCBFF),
            image: 'assets/images/aprendo_hablar/no_existe.webp',
          ),
        ),
      ),
    );
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 200)));
    await tester.pump();
    expect(find.byIcon(Icons.abc_rounded), findsOneWidget);
  });
}
