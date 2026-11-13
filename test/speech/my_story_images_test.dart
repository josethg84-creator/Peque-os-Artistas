import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';
import 'package:pequenos_artistas/speech/widgets/speech_widgets.dart';

import '../test_helpers.dart';

const withCard = {'oso', 'dragon', 'mariposa', 'conejo', 'nina'};

MyStoryContent realStory() => MyStoryContent.fromJson(
  jsonDecode(File('assets/speech/mystory.json').readAsStringSync()) as Map<String, dynamic>,
);

void main() {
  test('cinco personajes tienen su ilustración de tarjeta; en la escena siguen con su dibujo', () {
    final story = realStory();
    for (final c in story.characters) {
      if (withCard.contains(c.id)) {
        final card = c.card;
        expect(card, isA<ImagePicture>(), reason: c.id);
        final path = (card! as ImagePicture).path;
        expect(path, 'assets/images/mi_historia/${c.id}.webp');
        final bytes = File(path).readAsBytesSync();
        expect(String.fromCharCodes(bytes.skip(8).take(4)), 'WEBP', reason: path);
        expect(c.picture, isNot(isA<ImagePicture>()), reason: 'la escena usa el dibujo, no la foto');
      } else {
        expect(c.card, isNull, reason: c.id);
        expect(c.cardPicture, same(c.picture));
      }
    }
    expect(File('pubspec.yaml').readAsStringSync(), contains('    - assets/images/mi_historia/\n'));
  });

  testWidgets('la tarjeta «un oso» muestra la ilustración y se sigue eligiendo', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    await pumpApp(tester);
    tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(AppRoutes.speechMyStory);
    await tester.pumpAndSettle();
    final oso = find.bySemanticsLabel('un oso');
    await tester.scrollUntilVisible(oso, 200, scrollable: find.byType(Scrollable).first);
    final pictures = tester.widgetList<SpeechPictureView>(find.byType(SpeechPictureView));
    expect(
      pictures.where((p) => p.picture is ImagePicture).map((p) => (p.picture as ImagePicture).path),
      containsAll(['assets/images/mi_historia/oso.webp', 'assets/images/mi_historia/conejo.webp']),
    );
    await tester.tap(oso);
    await tester.pumpAndSettle();
    expect(lastNarrator!.spoken.last, startsWith('un oso.'));
    expect(tester.takeException(), isNull);
  });
}
