import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/speech/screens/speech_hub_screen.dart';
import 'package:pequenos_artistas/speech/screens/speech_quiz_screen.dart';
import 'package:pequenos_artistas/speech/speech_activities.dart';
import 'package:pequenos_artistas/speech/speech_progress.dart';
import 'package:pequenos_artistas/speech/voice_practice.dart';
import 'package:pequenos_artistas/speech/widgets/practice_sheet.dart';

import '../test_helpers.dart';
import 'speech_activities_test.dart' show realContent;

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

List<String> get spoken => lastNarrator!.spoken;

Future<SpeechController> openApp(WidgetTester tester, {FakeVoiceRecorder Function()? recorder}) async {
  setScreenSize(tester, const Size(420, 900));
  final speech = SpeechController(
    SpeechStore(MemoryBackend()),
    recorder: () => lastRecorder = recorder?.call() ?? FakeVoiceRecorder(),
  );
  await speech.load();
  await pumpApp(tester, speech: speech);
  return speech;
}

Future<void> push(WidgetTester tester, String route, [Object? args]) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('el menú tiene todas las actividades de las fases 2 y 3, sin «Muy pronto»', (tester) async {
    await openApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Aprendo a Hablar'));
    for (final t in [
      'Construyo oraciones',
      'Aprendo los verbos',
      'Hablemos con Lolo',
      'Escucho y respondo',
      'Lolo me cuenta un cuento',
      'Yo puedo expresarme',
      'Ahora cuéntamelo tú',
    ]) {
      await tester.scrollUntilVisible(find.bySemanticsLabel(t), 200);
      expect(find.bySemanticsLabel(t), findsOneWidget, reason: t);
    }
    expect(SpeechHubScreen.activities.where((a) => !a.available), isEmpty);
  });

  testWidgets('constructor: quién, qué hace y qué, y Lolo dice la oración', (tester) async {
    final speech = await openApp(tester);
    await push(tester, AppRoutes.speechBuilder);
    expect(spoken.last, '¿Quién?');
    await tapAndSettle(tester, find.bySemanticsLabel('El niño'));
    expect(spoken.last, 'El niño… ¿Qué hace?');
    await tapAndSettle(tester, find.bySemanticsLabel('come'));
    expect(spoken.last, 'El niño come… ¿Qué?');
    await tapAndSettle(tester, find.bySemanticsLabel('una manzana'));
    expect(spoken.last, 'El niño come una manzana.');
    expect(find.bySemanticsLabel('Tu oración: El niño come una manzana.'), findsOneWidget);
    expect(speech.progress.sentencesBuilt, {'El niño come una manzana.'});
    await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
    expect(lastNarrator!.slow, ['El niño come una manzana.']);
    await tapAndSettle(tester, find.bySemanticsLabel('Nueva oración'));
    expect(spoken.last, '¿Quién?');
    await tapAndSettle(tester, find.bySemanticsLabel('El perro'));
    await tapAndSettle(tester, find.bySemanticsLabel('juega con'));
    await tapAndSettle(tester, find.bySemanticsLabel('la pelota'));
    expect(spoken.last, 'El perro juega con la pelota.');
    expect(speech.progress.sentencesBuilt, hasLength(2));
    expect(lastMusic!.playing, isNull);
  });

  testWidgets('ordena la oración: empieza por 3 palabras y avanza a la siguiente', (tester) async {
    final speech = await openApp(tester);
    await push(tester, AppRoutes.speechOrder);
    expect(spoken.last, 'Toca las palabras en orden. Nivel 1.');
    expect(find.bySemanticsLabel('Nivel 1'), findsOneWidget);
    for (final w in ['El', 'perro', 'corre']) {
      await tapAndSettle(tester, find.bySemanticsLabel(w));
    }
    expect(spoken.last, 'El perro corre.');
    expect(speech.progress.sentencesOrdered, {'El perro corre.'});
    expect(speech.progress.activitiesDone['ordenar'], 1);
    await tapAndSettle(tester, find.bySemanticsLabel('Otra oración'));
    expect(find.bySemanticsLabel('Escuchar'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
    expect(spoken.last, 'La niña salta.');

    // Al volver, se sigue por la primera que falta.
    await tapAndSettle(tester, find.bySemanticsLabel('Volver'));
    await push(tester, AppRoutes.speechOrder);
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar'));
    expect(spoken.last, 'La niña salta.');
  });

  testWidgets('completa la oración: errores sin castigo, ayuda y fin de la actividad', (tester) async {
    final speech = await openApp(tester);
    final questions = SpeechQuizKind.complete.build(realContent(), Random(4));
    tester
        .state<NavigatorState>(find.byType(Navigator))
        .push(
          MaterialPageRoute<void>(
            builder: (_) => const SpeechQuizScreen(quiz: SpeechQuizKind.complete, seed: 4),
          ),
        );
    await tester.pumpAndSettle();
    expect(spoken.last, questions.first.speech);

    final first = questions.first;
    final wrong = [
      for (final (i, o) in first.options.indexed)
        if (i != first.answer) o.label,
    ];
    lastSounds!.played.clear();
    await tapAndSettle(tester, find.bySemanticsLabel(wrong[0]));
    expect(spoken.last, '¡Casi! Prueba otra vez.');
    await tapAndSettle(tester, find.bySemanticsLabel(wrong[1]));
    expect(spoken.last, 'Mira, la que brilla es la correcta.');
    expect(lastSounds!.played.toSet(), {SoundCue.tryAgain});
    expect(find.bySemanticsLabel('Siguiente'), findsNothing);

    for (final (i, q) in questions.indexed) {
      await tapAndSettle(tester, find.bySemanticsLabel(q.options[q.answer].label));
      expect(spoken.last, q.afterCorrect);
      await tapAndSettle(tester, find.bySemanticsLabel(i == questions.length - 1 ? 'Terminar' : 'Siguiente'));
    }
    expect(spoken.last, '¡Terminaste! ¡Qué bien lo has hecho!');
    expect(speech.progress.activitiesDone['completar'], 1);
    expect(find.bySemanticsLabel('Jugar otra vez'), findsOneWidget);
  });

  testWidgets('verbos: conjugación que se escucha línea a línea o entera', (tester) async {
    final speech = await openApp(tester);
    await push(tester, AppRoutes.speechVerbs);
    await tapAndSettle(tester, find.bySemanticsLabel('COMER'));
    expect(spoken.last, 'comer');
    await tapAndSettle(tester, find.bySemanticsLabel('Tú comes una manzana.'));
    expect(spoken.last, 'Tú comes una manzana.');
    spoken.clear();
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar todo'));
    expect(spoken, [
      'Yo como una manzana.',
      'Tú comes una manzana.',
      'Él come una manzana.',
      'Ella come una manzana.',
      'Nosotros comemos una manzana.',
    ]);
    await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
    expect(spoken.last, 'beber');
    expect(speech.progress.verbsHeard, {'comer', 'beber'});
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a los verbos'));
    expect(find.text('¡Ya lo practicaste!'), findsNWidgets(2));
  });

  testWidgets('practicar: grabar, escucharse, repetir, y la grabación se borra al cerrar', (tester) async {
    final speech = await openApp(tester);
    await push(tester, AppRoutes.speechWords, const SpeechWordsArgs('animales'));
    await tapAndSettle(tester, find.bySemanticsLabel('Practicar'));
    expect(find.byType(PracticeSheet), findsOneWidget);
    expect(spoken.last, 'Escucha y repite: perro');
    final rec = lastRecorder!;
    expect(rec.permissionRequests, 0, reason: 'el permiso se pide al pulsar «Grabar», no antes');

    // Mientras graba hay una barra de 6 s: se avanza fotograma a fotograma.
    await tester.tap(find.bySemanticsLabel('Grabar'));
    for (var i = 0; i < 5; i++) {
      await tester.pump();
    }
    expect(rec.permissionRequests, 1);
    expect(rec.recording, isTrue);
    expect(find.bySemanticsLabel(RegExp('^Lolo dice: ¡Te escucho!')), findsOneWidget);
    await tester.tap(find.bySemanticsLabel('Parar'));
    await tester.pumpAndSettle();
    expect(spoken.last, PracticeSheet.encouragement);
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar mi voz'));
    expect(rec.played, ['memoria://grabacion_1']);
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar a Lolo'));
    expect(spoken.last, 'perro');

    // Otra vez: la grabación anterior se borra; termina sola a los 6 segundos.
    await tester.tap(find.bySemanticsLabel('Grabar otra vez'));
    await tester.pump();
    await tester.pump();
    expect(rec.discarded, ['memoria://grabacion_1']);
    await tester.pump(PracticeSheet.maxLength);
    await tester.pumpAndSettle();
    expect(find.bySemanticsLabel('Escuchar mi voz'), findsOneWidget);
    expect(speech.progress.recordings, 2);

    // Al cerrar se borra la última y se libera la grabadora.
    await tester.tapAt(const Offset(10, 10));
    await tester.pumpAndSettle();
    expect(find.byType(PracticeSheet), findsNothing);
    expect(rec.discarded, ['memoria://grabacion_1', 'memoria://grabacion_2']);
    expect(rec.disposed, isTrue);
  });

  testWidgets('practicar sin permiso: mensaje amable y nada se graba', (tester) async {
    final speech = await openApp(tester, recorder: () => FakeVoiceRecorder(permission: false));
    await push(tester, AppRoutes.speechPhrases);
    await tapAndSettle(tester, find.bySemanticsLabel('Practicar'));
    await tapAndSettle(tester, find.bySemanticsLabel('Grabar'));
    expect(find.bySemanticsLabel(RegExp('un adulto tiene que permitir el micrófono')), findsOneWidget);
    expect(lastRecorder!.recordings, 0);
    expect(speech.progress.recordings, 0);
  });

  testWidgets('un adulto puede quitar «Practicar» desde la zona de adultos', (tester) async {
    final speech = await openApp(tester);
    await push(tester, AppRoutes.adultZone, const AdultZoneArgs.verified());
    final toggle = find.widgetWithText(SwitchListTile, 'Practicar con el micrófono');
    await tester.scrollUntilVisible(toggle, 300);
    expect(find.text('Practicar con el micrófono'), findsOneWidget);
    await tapAndSettle(tester, toggle);
    expect(speech.progress.micAllowed, isFalse);
    await tapAndSettle(tester, find.byTooltip('Salir al inicio'));
    await push(tester, AppRoutes.speechWords, const SpeechWordsArgs('animales'));
    expect(find.bySemanticsLabel('Practicar'), findsNothing);
    expect(find.bySemanticsLabel('Escuchar'), findsOneWidget);
  });
}
