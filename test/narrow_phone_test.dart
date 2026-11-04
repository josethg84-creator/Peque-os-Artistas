import 'package:flutter/material.dart';

import 'dart:io';

import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/aac/widgets/aac_widgets.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/widgets/fitted_title.dart';

import 'test_helpers.dart';

/// Teléfonos de 360 dp de ancho (muy comunes): los títulos no se cortan a mitad
/// de palabra y la barra de herramientas de colorear se ve entera. Errores
/// encontrados al preparar las capturas de Google Play (Fase 9).
/// Las pruebas usan por defecto una fuente de cuadrados, mucho más ancha que la real:
/// aquí se carga Roboto para medir los textos como en un Android.
Future<void> loadRoboto() async {
  final loader = FontLoader('Roboto');
  for (final w in ['Regular', 'Medium', 'Bold', 'Black']) {
    loader.addFont(Future.value(ByteData.sublistView(File('test/fonts/Roboto-$w.ttf').readAsBytesSync())));
  }
  await loader.load();
  // La fuente real de los botones del inicio.
  await (FontLoader(
    'Fredoka',
  )..addFont(Future.value(ByteData.sublistView(File('assets/fonts/Fredoka.ttf').readAsBytesSync())))).load();
}

void main() {
  setUpAll(loadRoboto);

  test('FittedTitle baja de tamaño antes que partir una palabra', () {
    const big = TextStyle(fontSize: 30), small = TextStyle(fontSize: 10);
    expect(FittedTitle.fits('Encuentra', big, 200, 2, TextScaler.noScaling), isFalse); // 9×30 > 200
    expect(FittedTitle.fits('Encuentra', small, 200, 2, TextScaler.noScaling), isTrue);
  });

  final screens = <String, (String, Object?)>{
    'Aprende los colores': (AppRoutes.learningGame, const LearningGameArgs(GameId.colors)),
    'Descubre las formas': (AppRoutes.learningGame, const LearningGameArgs(GameId.shapes)),
    'Encuentra a los animales': (AppRoutes.learningGame, const LearningGameArgs(GameId.animals)),
    'Elige una categoría': (AppRoutes.categories, null),
  };
  for (final MapEntry(key: title, value: (route, args)) in screens.entries) {
    testWidgets('360 dp: el título «$title» no se corta', (tester) async {
      setScreenSize(tester, const Size(360, 720));
      await pumpApp(tester);
      tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
      await tester.pumpAndSettle();
      final paragraph = tester.renderObject<RenderParagraph>(
        find.descendant(of: find.byType(FittedTitle), matching: find.text(title)),
      );
      expect(paragraph.didExceedMaxLines, isFalse);
    });
  }

  testWidgets('360 dp: la barra de herramientas de colorear se ve entera', (tester) async {
    setScreenSize(tester, const Size(360, 720));
    await pumpApp(tester);
    tester
        .state<NavigatorState>(find.byType(Navigator))
        .pushNamed(AppRoutes.coloring, arguments: const ColoringArgs('animal_gato'));
    await tester.pumpAndSettle();
    final screen = Offset.zero & const Size(360, 720);
    for (final label in ['Borrador', 'Deshacer', 'Rehacer', 'Limpiar']) {
      final rect = tester.getRect(find.bySemanticsLabel(label));
      expect(
        screen.contains(rect.topLeft) && screen.contains(rect.bottomRight - const Offset(1, 1)),
        isTrue,
        reason: '$label: $rect',
      );
      expect(rect.width, greaterThanOrEqualTo(48), reason: 'objetivo táctil de $label');
    }
  });

  testWidgets('360 dp: los accesos grandes del inicio no parten las palabras (Fase 7)', (tester) async {
    setScreenSize(tester, const Size(360, 720));
    await pumpApp(tester);
    for (final label in ['Aprendo a Hablar', 'Necesito decir algo']) {
      final button = find.widgetWithText(AacShortcut, label);
      expect(button, findsOneWidget, reason: label);
      final text = tester.renderObject<RenderParagraph>(
        find.descendant(of: button, matching: find.text(label)),
      );
      for (final word in label.split(' ')) {
        final painter = TextPainter(
          text: TextSpan(text: word, style: text.text.style),
          textDirection: TextDirection.ltr,
          textScaler: text.textScaler,
        )..layout();
        expect(painter.width, lessThanOrEqualTo(text.size.width), reason: '«$word» de «$label» cabe entera');
      }
    }
  });
}
