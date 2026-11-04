import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/aac/aac_controller.dart';
import 'package:pequenos_artistas/coloring/engine/drawing_painter.dart';
import 'package:pequenos_artistas/learning/learning_controller.dart';
import 'package:pequenos_artistas/learning/learning_store.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/creation_store.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/screens/coloring_screen.dart';
import 'package:pequenos_artistas/speech/speech_progress.dart';
import 'package:pequenos_artistas/speech/voice_practice.dart';

import 'test_helpers.dart';

/// Recorridos de la Fase 7 (candidata a lanzamiento). Los demás recorridos
/// (A–K) ya tienen sus pruebas; la tabla está en store_assets/TESTING_CHECKLIST.md.

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(finder, 250, scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

Future<void> push(WidgetTester tester, String route, [Object? args]) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
  await tester.pumpAndSettle();
}

Future<void> home(WidgetTester tester) async {
  tester.state<NavigatorState>(find.byType(Navigator)).popUntil((r) => r.isFirst);
  await tester.pumpAndSettle();
}

/// Los cuatro almacenes de la app, como el disco del teléfono.
class Disk {
  final creations = MemoryBackend();
  final learning = MemoryBackend();
  final speech = MemoryBackend();
  final aac = MemoryBackend();
}

/// Abre la app sobre [disk], como al tocar su icono.
Future<({SpeechController speech, AacController aac, LearningController learning})> openApp(
  WidgetTester tester,
  Disk disk,
) async {
  final speech = SpeechController(SpeechStore(disk.speech), recorder: () => FakeVoiceRecorder());
  final aac = AacController(AacStore(disk.aac));
  final learning = LearningController(LearningStore(disk.learning));
  await speech.load();
  await aac.load();
  await pumpApp(
    tester,
    store: KeyValueCreationStore(disk.creations),
    speech: speech,
    aac: aac,
    learning: learning,
  );
  return (speech: speech, aac: aac, learning: learning);
}

/// Cierra la app (la saca de la pantalla y deja terminar los guardados).
Future<void> closeApp(WidgetTester tester) async {
  await tester.pumpWidget(const SizedBox());
  await tester.pump(const Duration(seconds: 1));
}

Color? canvasColor(WidgetTester tester, String region) =>
    (tester.widget<CustomPaint>(drawingCanvasFinder).painter! as DrawingPainter).colors.colorOf(region);

void main() {
  testWidgets('L: lo hecho en cada módulo sigue ahí al cerrar y volver a abrir la app', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final disk = Disk();
    var app = await openApp(tester, disk);

    // A · colorear el gato.
    final gato = svgOf('animals', 'animal_gato');
    await openCat(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Naranja'));
    await tester.tapAt(screenPointOf(tester, gato, interiorPoint(gato, 'cuerpo')));
    await tester.pump();
    await home(tester);

    // D · escuchar una palabra.
    await push(tester, AppRoutes.speechWords, const SpeechWordsArgs('animales'));
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
    expect(lastNarrator!.spoken.last, 'perro');
    await home(tester);

    // H · frase con pictogramas guardada como favorita.
    await push(tester, AppRoutes.aac);
    await tapAndSettle(tester, find.bySemanticsLabel('Construyo lo que quiero decir'));
    for (final p in ['Yo', 'Quiero', 'Agua']) {
      await tapAndSettle(tester, find.bySemanticsLabel(p));
    }
    await tapAndSettle(tester, find.bySemanticsLabel('Guardar favorita'));
    await home(tester);

    // K · ajuste de un adulto.
    await push(tester, AppRoutes.adultZone, const AdultZoneArgs.verified());
    await tapAndSettle(tester, find.text('Reducir animaciones'));
    expect(app.learning.settings.reduceMotion, isTrue);

    await closeApp(tester);
    app = await openApp(tester, disk);

    expect(app.speech.progress.wordsHeard, contains('perro'));
    expect(app.aac.prefs.favorites, ['Yo quiero agua.']);
    expect(app.learning.settings.reduceMotion, isTrue);
    await openMyGallery(tester);
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Gato\. ')));
    expect(find.byType(ColoringScreen), findsOneWidget);
    expect(canvasColor(tester, 'cuerpo'), const Color(0xFFFF8F00));
  });

  testWidgets('L: borrar la personalización de «Quiero decir» no toca dibujos ni progreso', (tester) async {
    setScreenSize(tester, const Size(420, 900));
    final disk = Disk();
    var app = await openApp(tester, disk);
    app.aac.addFavorite('Hola.');
    await push(tester, AppRoutes.speechWords, const SpeechWordsArgs('animales'));
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
    await app.aac.clearAll();
    await closeApp(tester);

    app = await openApp(tester, disk);
    expect(app.aac.prefs.favorites, isEmpty);
    expect(app.speech.progress.wordsHeard, contains('perro'));
  });
}
