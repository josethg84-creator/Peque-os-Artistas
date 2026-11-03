import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';
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

List<String> get spoken => lastNarrator!.spoken;

Future<SpeechController> openApp(WidgetTester tester, {Size size = const Size(420, 900)}) async {
  setScreenSize(tester, size);
  final speech = SpeechController(
    SpeechStore(MemoryBackend()),
    recorder: () => lastRecorder = FakeVoiceRecorder(),
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
  group('Etapa A · Hablemos con Lolo', () {
    testWidgets('desde el menú: categorías, conversaciones y una charla completa con estrella', (
      tester,
    ) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speech);
      await tapAndSettle(tester, find.bySemanticsLabel('Hablemos con Lolo'));
      expect(find.bySemanticsLabel('Saludos y despedidas'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('Saludos y despedidas'));
      await tapAndSettle(tester, find.bySemanticsLabel('¡Hola, Lolo!'));
      expect(spoken.last, '¡Hola! ¿Cómo estás hoy?');
      expect(lastMusic!.playing, isNull, reason: 'sin música para oír bien a Lolo');

      await tapAndSettle(tester, find.bySemanticsLabel('Repetir'));
      expect(spoken.last, '¡Hola! ¿Cómo estás hoy?');
      spoken.clear();
      await tapAndSettle(tester, find.bySemanticsLabel('Estoy feliz.'));
      // Lolo reacciona a la tarjeta elegida y hace la pregunta siguiente.
      expect(spoken, ['¡Qué alegría! Me gusta verte feliz.', '¿Quieres jugar conmigo?']);
      expect(find.bySemanticsLabel('Tú: Estoy feliz.'), findsOneWidget);

      await tapAndSettle(tester, find.bySemanticsLabel('¡Sí, quiero jugar!'));
      await tapAndSettle(tester, find.bySemanticsLabel('¡Hasta mañana!'));
      expect(spoken.last, '¡Hasta la próxima! Me encantó saludarte.');
      expect(find.bySemanticsLabel('¡Ganaste una estrella!'), findsOneWidget);
      expect(speech.progress.conversationsDone, {'saludo_hola'});
      expect(speech.progress.stars, 1);

      // Otra vez: la misma conversación no vuelve a dar estrella.
      await tapAndSettle(tester, find.bySemanticsLabel('Hablar otra vez'));
      expect(spoken.last, '¡Hola! ¿Cómo estás hoy?');
      for (final a in ['Estoy cansado.', 'Ahora no, gracias.', '¡Adiós, Lolo!']) {
        await tapAndSettle(tester, find.bySemanticsLabel(a));
      }
      expect(speech.progress.stars, 1);

      await tapAndSettle(tester, find.bySemanticsLabel('Otra conversación'));
      expect(find.text('¡Ya hablamos!'), findsOneWidget);
    });

    testWidgets('una rama: si está triste, Lolo consuela antes de seguir; «Terminar» sale sin estrella', (
      tester,
    ) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speechConversation, const SpeechConversationArgs('saludo_hola'));
      await tapAndSettle(tester, find.bySemanticsLabel('Estoy triste.'));
      expect(spoken.last, '¿Quieres que hagamos algo juntos para sentirnos mejor?');
      await tapAndSettle(tester, find.bySemanticsLabel('Respirar despacio.'));
      expect(spoken.last, '¿Quieres jugar conmigo?');
      await tapAndSettle(tester, find.bySemanticsLabel('Terminar'));
      expect(spoken.last, '¡Hasta la próxima! Me encantó saludarte.');
      expect(find.bySemanticsLabel('¡Ganaste una estrella!'), findsNothing);
      expect(speech.progress.conversationsDone, isEmpty);
    });

    testWidgets('el niño puede practicar su respuesta con la voz (sin que Lolo la interprete)', (
      tester,
    ) async {
      await openApp(tester);
      await push(tester, AppRoutes.speechConversation, const SpeechConversationArgs('amigo_mejor'));
      await tapAndSettle(tester, find.bySemanticsLabel('Jugar.'));
      await tapAndSettle(tester, find.byTooltip('Practicar diciéndolo con tu voz'));
      expect(spoken.last, 'Escucha y repite: Jugar.');
      expect(lastRecorder!.permissionRequests, 0);
    });
  });

  group('Etapa B · Lolo me cuenta un cuento', () {
    testWidgets('el cuento se lee solo, escena a escena, y al final se gana una estrella', (tester) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speech);
      await tapAndSettle(tester, find.bySemanticsLabel('Lolo me cuenta un cuento'));
      expect(find.bySemanticsLabel('Toby y la pelota roja'), findsOneWidget);
      spoken.clear();
      await tapAndSettle(tester, find.bySemanticsLabel('Toby y la pelota roja'));
      expect(spoken, [
        'Toby es un perro pequeño y juguetón.',
        'Una mañana, Toby encontró una pelota roja.',
        'Toby llevó la pelota al jardín.',
        'Su amiga Luna llegó para jugar con él.',
        'Los dos jugaron felices toda la tarde.',
      ]);
      expect(find.bySemanticsLabel(RegExp('^Escena 5 de 5')), findsOneWidget);
      expect(speech.progress.storiesHeard, {'toby_pelota'});
      expect(speech.progress.stars, 1);
      expect(lastMusic!.playing, isNull);

      // Controles: anterior, repetir escena y despacio.
      await tapAndSettle(tester, find.bySemanticsLabel('Anterior'));
      expect(spoken.last, 'Su amiga Luna llegó para jugar con él.');
      await tapAndSettle(tester, find.bySemanticsLabel('Repetir escena'));
      expect(spoken.last, 'Su amiga Luna llegó para jugar con él.');
      await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
      expect(lastNarrator!.slow, ['Su amiga Luna llegó para jugar con él.']);
    });

    testWidgets('pausar y continuar la narración', (tester) async {
      await openApp(tester);
      await push(tester, AppRoutes.speechStory, const SpeechStoryArgs('pipo_nadar'));
      // La voz tarda en terminar esta escena.
      final pending = Completer<void>();
      lastNarrator!.pending = pending;
      // (Al abrirlo se leyó entero: estamos en la última escena.)
      await tester.tap(find.bySemanticsLabel('Anterior'));
      await tester.pump();
      await tester.pump();
      expect(find.bySemanticsLabel('Pausar'), findsOneWidget);
      await tester.tap(find.bySemanticsLabel('Pausar'));
      await tester.pump();
      expect(lastNarrator!.stops, greaterThan(0));
      expect(find.bySemanticsLabel('Continuar'), findsOneWidget);
      lastNarrator!.pending = null;
      pending.complete();
      await tester.pumpAndSettle();
      // Seguir en pausa aunque la frase interrumpida termine tarde.
      expect(find.bySemanticsLabel('Continuar'), findsOneWidget);
      spoken.clear();
      await tapAndSettle(tester, find.bySemanticsLabel('Continuar'));
      expect(spoken.first, 'Pipo metió una patita, luego la otra… ¡y empezó a flotar!');
    });

    testWidgets('preguntas del cuento con dibujos y ordenar tres escenas', (tester) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speechStoryQuiz, const SpeechStoryArgs('toby_pelota'));
      expect(spoken.last, '¿Cómo se llamaba el perro?');
      await tapAndSettle(tester, find.bySemanticsLabel('Bruno'));
      expect(spoken.last, '¡Casi! Prueba otra vez.');
      await tapAndSettle(tester, find.bySemanticsLabel('Toby'));
      expect(spoken.last, '¡Sí! Toby.');
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      await tapAndSettle(tester, find.bySemanticsLabel('Roja'));
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      await tapAndSettle(tester, find.bySemanticsLabel('En el jardín'));
      await tapAndSettle(tester, find.bySemanticsLabel('Terminar'));
      expect(speech.progress.storiesQuizzed, {'toby_pelota'});
      expect(speech.progress.answers, 3);
      expect(speech.progress.stars, 2);

      await tapAndSettle(tester, find.bySemanticsLabel('Ordena las escenas'));
      for (final t in [
        'Toby es un perro pequeño y juguetón.',
        'Toby llevó la pelota al jardín.',
        'Los dos jugaron felices toda la tarde.',
      ]) {
        await tapAndSettle(tester, find.bySemanticsLabel(t));
      }
      expect(find.text('¡Muy bien!'), findsOneWidget);
      expect(speech.progress.activitiesDone['ordenar_escenas'], 1);
    });
  });

  group('Etapa C · Yo puedo expresarme', () {
    testWidgets('necesidades, emociones y la frase quién + qué siente + por qué', (tester) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speech);
      await tapAndSettle(tester, find.bySemanticsLabel('Yo puedo expresarme'));
      await tapAndSettle(tester, find.bySemanticsLabel('Necesito…'));
      expect(spoken.last, 'Quiero tomar agua.');
      await tapAndSettle(tester, find.bySemanticsLabel('Siguiente'));
      expect(spoken.last, 'Tengo hambre.');
      expect(speech.progress.expressionsPracticed, {'necesidad:tomar_agua', 'necesidad:hambre'});
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a Yo puedo expresarme'));

      await tapAndSettle(tester, find.bySemanticsLabel('Cómo me siento'));
      expect(spoken.last, 'Todas las emociones son importantes. ¡Está bien decir cómo nos sentimos!');
      await tapAndSettle(tester, find.bySemanticsLabel('Tristeza'));
      await tapAndSettle(tester, find.bySemanticsLabel('Estoy triste porque extraño a mi amigo.'));
      expect(spoken.last, 'Estoy triste porque extraño a mi amigo.');
      await tapAndSettle(tester, find.bySemanticsLabel('Construye tu frase'));

      expect(spoken.last, '¿Quién?');
      await tapAndSettle(tester, find.bySemanticsLabel('Yo (niña)'));
      await tapAndSettle(tester, find.bySemanticsLabel('contenta'));
      expect(spoken.last, 'Yo estoy contenta… ¿Por qué?');
      await tapAndSettle(tester, find.bySemanticsLabel('porque es mi cumpleaños'));
      expect(spoken.last, 'Yo estoy contenta porque es mi cumpleaños.');
      expect(find.bySemanticsLabel('Tu frase: Yo estoy contenta porque es mi cumpleaños.'), findsOneWidget);
      expect(speech.progress.expressionsPracticed, contains('frase:yo_nina:alegria:cumple'));
      await tapAndSettle(tester, find.bySemanticsLabel('Otra frase'));
      await tapAndSettle(tester, find.bySemanticsLabel('Papá'));
      await tapAndSettle(tester, find.bySemanticsLabel('enojado'));
      await tapAndSettle(tester, find.bySemanticsLabel('porque se cayó su torre'));
      expect(spoken.last, 'Papá está enojado porque se cayó su torre.');
    });
  });

  group('Etapa D · Ahora cuéntamelo tú', () {
    testWidgets('mirar, ordenar, contar con frases, escuchar la historia y grabarla', (tester) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speechTellList);
      await tapAndSettle(tester, find.bySemanticsLabel('La semilla mágica'));
      expect(spoken.last, 'Mira bien los dibujos. ¿Qué crees que pasa?');
      expect(find.bySemanticsLabel('Paso 1 de 4: Mirar'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a ordenarlos!'));
      expect(find.bySemanticsLabel('¡Ahora cuéntalo!'), findsNothing, reason: 'primero hay que ordenar');
      const phrases = [
        'Una niña encuentra una semilla.',
        'La niña planta la semilla.',
        'La niña riega la planta.',
        '¡Aparece una flor!',
      ];
      for (final p in phrases) {
        await tapAndSettle(tester, find.bySemanticsLabel(p));
      }
      await tapAndSettle(tester, find.bySemanticsLabel('¡Ahora cuéntalo!'));
      expect(spoken.last, '¿Qué encuentra la niña?');

      // Contar: una frase equivocada no castiga; la correcta avanza.
      final wrong = find.bySemanticsLabel(
        RegExp(r'^(La niña planta la semilla\.|La niña riega la planta\.|¡Aparece una flor!)$'),
      );
      await tapAndSettle(tester, wrong.first);
      expect(spoken.last, '¡Casi! Mira bien el dibujo.');
      for (final p in phrases) {
        await tapAndSettle(tester, find.bySemanticsLabel(p));
      }
      expect(
        find.bySemanticsLabel('Tu historia: La niña plantó una semilla, la regó y creció una flor.'),
        findsOneWidget,
      );
      expect(speech.progress.storiesTold, {'semilla'});
      expect(speech.progress.stars, 2);

      spoken.clear();
      await tapAndSettle(tester, find.bySemanticsLabel('Escuchar mi historia'));
      expect(spoken, [phrases.join(' '), 'La niña plantó una semilla, la regó y creció una flor.']);
      await tapAndSettle(tester, find.bySemanticsLabel('Grabar mi historia'));
      expect(spoken.last, 'Escucha y repite: La niña plantó una semilla, la regó y creció una flor.');
    });
  });

  group('Etapa E · Escucho y respondo', () {
    final listening = ListeningContent.fromJson(
      jsonDecode(File(SpeechContent.listeningAsset).readAsStringSync()) as Map<String, dynamic>,
    );

    testWidgets('desde el menú: niveles, una ronda completa con despacio, error amable y estrella', (
      tester,
    ) async {
      final speech = await openApp(tester);
      await push(tester, AppRoutes.speech);
      await tapAndSettle(tester, find.bySemanticsLabel('Escucho y respondo'));
      expect(find.bySemanticsLabel(RegExp(r'^Nivel 1')), findsOneWidget);
      expect(find.bySemanticsLabel(RegExp(r'^Escucha y señala')), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^Nivel 3')));

      var answered = 0;
      while (answered < 8) {
        final asked = spoken.last;
        final e = listening.ofLevel(3).firstWhere((x) => x.toQuestion().speech == asked);
        expect(e.level, 3);
        if (answered == 0) {
          // Despacio: la misma frase, más lenta.
          await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
          expect(spoken.last, asked);
          expect(lastNarrator!.slow.last, asked);
          // Un error no castiga.
          final wrong = [for (var i = 0; i < e.options.length; i++) i]
              .firstWhere((i) => !(e.steps ?? [e.answer]).contains(i));
          await tapAndSettle(tester, find.bySemanticsLabel(e.options[wrong].label));
          expect(spoken.last, '¡Casi! Prueba otra vez.');
        }
        for (final i in e.steps ?? [e.answer]) {
          await tapAndSettle(tester, find.bySemanticsLabel(e.options[i].label).first);
        }
        expect(spoken.last, e.toQuestion().afterCorrect);
        answered++;
        await tapAndSettle(tester, find.bySemanticsLabel(answered == 8 ? 'Terminar' : 'Siguiente'));
      }
      expect(answered, 8);
      expect(find.text('¡Terminaste! ¡Qué bien lo has hecho!'), findsOneWidget);
      expect(speech.progress.listeningDone, hasLength(8));
      expect(speech.progress.activitiesDone['escucho_nivel_3'], 1);
      expect(speech.progress.stars, 1);
      expect(speech.progress.answers, 8);
    });

    testWidgets('instrucción de dos pasos: hay que tocar en orden', (tester) async {
      await openApp(tester);
      await push(tester, AppRoutes.speechListeningLevel, const SpeechListeningArgs(3));
      // Se busca una ronda que empiece con una instrucción.
      var guard = 0;
      while (!spoken.last.startsWith('Escucha bien: Toca') &&
          !spoken.last.startsWith('Escucha bien: Primero toca') &&
          guard++ < 10) {
        final e = listening.ofLevel(3).firstWhere((x) => x.toQuestion().speech == spoken.last);
        for (final i in e.steps ?? [e.answer]) {
          await tapAndSettle(tester, find.bySemanticsLabel(e.options[i].label).first);
        }
        await tapAndSettle(tester, find.bySemanticsLabel(RegExp(r'^(Siguiente|Terminar)$')));
      }
      final e = listening.ofLevel(3).firstWhere((x) => x.toQuestion().speech == spoken.last);
      expect(e.steps, isNotNull);
      expect(find.text('Paso 1 de 2'), findsOneWidget);
      // El segundo primero: no vale.
      await tapAndSettle(tester, find.bySemanticsLabel(e.options[e.steps![1]].label));
      expect(spoken.last, '¡Casi! Prueba otra vez.');
      await tapAndSettle(tester, find.bySemanticsLabel(e.options[e.steps![0]].label));
      expect(spoken.last, '¡Bien! ¿Y después?');
      expect(find.text('Paso 2 de 2'), findsOneWidget);
      expect(find.bySemanticsLabel('${e.options[e.steps![0]].label}, paso 1'), findsOneWidget);
      await tapAndSettle(tester, find.bySemanticsLabel(e.options[e.steps![1]].label));
      expect(spoken.last, '¡Muy bien! Lo hiciste en orden.');
      expect(find.text('¡Hecho en orden!'), findsOneWidget);
    });
  });
}
