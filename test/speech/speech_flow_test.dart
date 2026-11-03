import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/speech/screens/speech_hub_screen.dart';
import 'package:pequenos_artistas/speech/speech_progress.dart';
import 'package:pequenos_artistas/speech/voice_practice.dart';

import '../test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  // Las listas largas construyen sus tarjetas al desplazarse.
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(finder, 250, scrollable: find.byType(Scrollable).first);
  }
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<SpeechController> openHub(WidgetTester tester, {SpeechController? speech}) async {
  setScreenSize(tester, const Size(420, 900));
  final controller =
      speech ??
      SpeechController(SpeechStore(MemoryBackend()), recorder: () => lastRecorder = FakeVoiceRecorder());
  await controller.load();
  await pumpApp(tester, speech: controller);
  await tapAndSettle(tester, find.bySemanticsLabel('Aprendo a Hablar'));
  expect(find.byType(SpeechHubScreen), findsOneWidget);
  return controller;
}

List<String> get spoken => lastNarrator!.spoken;

void main() {
  testWidgets('el inicio abre «Aprendo a Hablar» con todas sus actividades y Lolo', (tester) async {
    await openHub(tester);
    expect(find.bySemanticsLabel(RegExp('^Lolo dice: ¡Hola! Soy Lolo')), findsOneWidget);
    for (final a in SpeechHubScreen.activities) {
      await tester.scrollUntilVisible(find.bySemanticsLabel(a.title), 200);
      expect(find.bySemanticsLabel(a.title), findsOneWidget, reason: a.title);
    }
    await tester.scrollUntilVisible(find.bySemanticsLabel(RegExp('^Lolo dice: ¡Hola! Soy Lolo')), -200);
    // Ya no queda ninguna «Muy pronto».
    expect(SpeechHubScreen.activities.every((a) => a.available), isTrue);
    // Tocar a Lolo repite su saludo.
    await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Lolo dice:')));
    expect(spoken.last, '¡Hola! Soy Lolo. ¿Aprendemos a hablar juntos?');
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    expect(find.byType(SpeechHubScreen), findsNothing);
  });

  testWidgets('palabras: escuchar, despacio, siguiente, deslizar y terminar el grupo', (tester) async {
    final speech = await openHub(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Mis primeras palabras'));
    // Fase 4: los grupos crecieron con el banco de vocabulario.
    expect(find.text('0 de 23 escuchadas'), findsWidgets);
    await tapAndSettle(tester, find.bySemanticsLabel('Animales'));

    // La palabra se dice sola al aparecer, sin música de fondo.
    expect(find.text('PERRO'), findsOneWidget);
    expect(spoken.last, 'perro');
    expect(lastMusic!.playing, isNull);

    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
    expect(spoken.last, 'perro');
    await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
    expect(lastNarrator!.slow, ['perro']);
    await tapAndSettle(tester, find.bySemanticsLabel('perro')); // tocar el dibujo
    expect(spoken.last, 'perro');

    await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
    expect(find.text('GATO'), findsOneWidget);
    expect(spoken.last, 'gato');
    await tester.fling(find.byType(PageView), const Offset(-300, 0), 1000);
    await tester.pumpAndSettle();
    expect(find.text('CONEJO'), findsOneWidget);
    expect(spoken.last, 'conejo');
    await tapAndSettle(tester, find.bySemanticsLabel('Anterior'));
    expect(spoken.last, 'gato');
    expect(speech.progress.wordsHeard, {'perro', 'gato', 'conejo'});

    for (var i = 0; i < 30; i++) {
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
    }
    expect(
      find.bySemanticsLabel(RegExp('^Lolo dice: ¡Muy bien! Escuchaste todas las palabras de animales')),
      findsOneWidget,
    );
    expect(speech.progress.wordsHeard, hasLength(31));
    await tapAndSettle(tester, find.bySemanticsLabel('Otra vez'));
    expect(find.text('PERRO'), findsOneWidget);
    expect(spoken.last, 'perro');

    await tapAndSettle(tester, find.bySemanticsLabel('Volver a los grupos'));
    expect(find.text('31 de 31 escuchadas'), findsOneWidget);
  });

  testWidgets('frases: escuchar entera o palabra a palabra, y ordenarla sin castigos', (tester) async {
    final speech = await openHub(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Aprendo frases'));
    expect(spoken.last, 'Quiero agua.');
    expect(lastMusic!.playing, isNull);
    await tapAndSettle(tester, find.bySemanticsLabel('agua'));
    expect(spoken.last, 'agua');
    await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
    expect(lastNarrator!.slow, ['Quiero agua.']);

    await tapAndSettle(tester, find.bySemanticsLabel('¡Ordénala tú!'));
    expect(spoken.last, 'Toca las palabras en orden para formar la frase.');
    lastSounds!.played.clear();
    // Una palabra equivocada: solo ánimo; a la segunda, la correcta brilla.
    await tapAndSettle(tester, find.bySemanticsLabel('agua'));
    expect(spoken.last, '¡Casi! ¿Cuál va ahora?');
    await tapAndSettle(tester, find.bySemanticsLabel('agua'));
    expect(spoken.last, 'Busca la palabra que brilla.');
    // Suena «inténtalo otra vez» (el mismo sonido no se repite seguido); nunca «correcto».
    expect(lastSounds!.played.toSet(), {SoundCue.tryAgain});
    expect(speech.progress.phrasesOrdered, isEmpty);

    await tapAndSettle(tester, find.bySemanticsLabel('Quiero'));
    expect(spoken.last, 'Quiero');
    await tapAndSettle(tester, find.bySemanticsLabel('agua'));
    expect(spoken.last, 'Quiero agua.');
    expect(find.text('¡Muy bien!'), findsOneWidget);
    expect(find.bySemanticsLabel('Frase ordenada: Quiero agua.'), findsOneWidget);
    expect(lastSounds!.played.last, SoundCue.celebrate);
    expect(speech.progress.phrasesOrdered, {'quiero_agua'});

    await tapAndSettle(tester, find.bySemanticsLabel('Otra frase'));
    expect(spoken.last, 'Tengo hambre.');
    expect(speech.progress.phrasesHeard, {'quiero_agua', 'tengo_hambre'});
  });

  testWidgets('«Mis aventuras con Lolo» muestra solo lo que se ha hecho de verdad', (tester) async {
    final backend = MemoryBackend();
    final previous = SpeechController(SpeechStore(backend), clock: () => DateTime.now());
    await previous.load();
    previous
      ..markWordHeard('perro')
      ..markWordHeard('mama')
      ..markPhraseHeard('quiero_agua');
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 10)));

    await openHub(tester, speech: SpeechController(SpeechStore(backend)));
    await tester.scrollUntilVisible(find.bySemanticsLabel('Mis aventuras con Lolo'), 200);
    await tapAndSettle(tester, find.bySemanticsLabel('Mis aventuras con Lolo'));
    expect(find.bySemanticsLabel('Palabras escuchadas: 2 de 313'), findsOneWidget);
    expect(find.bySemanticsLabel('Frases escuchadas: 1 de 12'), findsOneWidget);
    expect(find.bySemanticsLabel('Frases ordenadas: 0 de 12'), findsOneWidget);
    expect(find.bySemanticsLabel('Días de práctica esta semana: 1 de 7'), findsOneWidget);
    await tester.scrollUntilVisible(find.bySemanticsLabel('Familia: 1 de 23'), 150);
    expect(find.bySemanticsLabel('Familia: 1 de 23'), findsOneWidget);
    await tester.scrollUntilVisible(find.bySemanticsLabel('Animales: 1 de 31'), 150);
    expect(find.bySemanticsLabel('Animales: 1 de 31'), findsOneWidget);
    await tester.scrollUntilVisible(find.textContaining('No es una evaluación del habla'), 300);
    expect(find.textContaining('No es una evaluación del habla'), findsOneWidget);
  });
}
