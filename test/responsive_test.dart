import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';
import 'package:pequenos_artistas/models/drawing_category.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';

import 'test_helpers.dart';

/// Recorre las pantallas en varios tamaños y escalas de texto. Cualquier
/// desbordamiento de diseño (overflow) hace fallar la prueba.
void main() {
  const sizes = {
    'teléfono pequeño': Size(320, 568),
    'teléfono': Size(360, 740),
    'teléfono horizontal': Size(740, 360),
    'tableta vertical': Size(800, 1280),
    'tableta horizontal': Size(1280, 800),
  };
  final routes = <String, (String, Object?)>{
    'inicio': (AppRoutes.home, null),
    'categorías': (AppRoutes.categories, null),
    'galería': (AppRoutes.gallery, const GalleryArgs(DrawingCategory.animals)),
    'coloreado': (AppRoutes.coloring, const ColoringArgs('animal_jirafa')),
    'mis dibujos': (AppRoutes.savedDrawings, null),
    'actividades': (AppRoutes.activities, null),
    'mini juegos': (AppRoutes.miniGames, null),
    'perfil': (AppRoutes.profile, null),
    'sonido y música': (AppRoutes.soundSettings, null),
    'aprendo a hablar': (AppRoutes.speech, null),
    'grupos de palabras': (AppRoutes.speechWordGroups, null),
    'palabras del cuerpo': (AppRoutes.speechWords, const SpeechWordsArgs('cuerpo')),
    'palabras de emociones': (AppRoutes.speechWords, const SpeechWordsArgs('emociones')),
    'frases': (AppRoutes.speechPhrases, null),
    'progreso del habla': (AppRoutes.speechProgress, null),
    'oraciones': (AppRoutes.speechSentences, null),
    'construir oración': (AppRoutes.speechBuilder, null),
    'ordenar oración': (AppRoutes.speechOrder, null),
    'completar oración': (AppRoutes.speechComplete, null),
    'pregunta o afirmación': (AppRoutes.speechQuestion, null),
    'verbos': (AppRoutes.speechVerbs, null),
    'verbo comer': (AppRoutes.speechVerb, const SpeechVerbArgs('comer')),
    'juegos de verbos': (AppRoutes.speechVerbGames, null),
    'escucho y comprendo': (AppRoutes.speechListen, null),
    'conversaciones': (AppRoutes.speechConversations, null),
    'conversaciones de saludo': (AppRoutes.speechConversationList, const SpeechCategoryArgs('saludos')),
    'conversación': (AppRoutes.speechConversation, const SpeechConversationArgs('saludo_hola')),
    'cuentos': (AppRoutes.speechStories, null),
    'cuento': (AppRoutes.speechStory, const SpeechStoryArgs('toby_pelota')),
    'preguntas del cuento': (AppRoutes.speechStoryQuiz, const SpeechStoryArgs('toby_pelota')),
    'ordenar el cuento': (AppRoutes.speechStoryOrder, const SpeechStoryArgs('toby_pelota')),
    'expresarme': (AppRoutes.speechExpress, null),
    'necesidades': (AppRoutes.speechNeeds, null),
    'emociones': (AppRoutes.speechEmotions, null),
    'emoción tristeza': (AppRoutes.speechEmotion, const SpeechEmotionArgs('tristeza')),
    'frase de emociones': (AppRoutes.speechExpressBuilder, null),
    'cuéntamelo': (AppRoutes.speechTellList, null),
    'historia semilla': (AppRoutes.speechTell, const SpeechTellArgs('semilla')),
    'escucho y respondo': (AppRoutes.speechListening, null),
    'escucho nivel 3': (AppRoutes.speechListeningLevel, const SpeechListeningArgs(3)),
    'mi aventura de hoy': (AppRoutes.speechMission, null),
    'sílabas y sonidos': (AppRoutes.speechSounds, null),
    'palmas difícil': (AppRoutes.speechClaps, const SpeechGameArgs('palmas', level: 3)),
    'rimas': (AppRoutes.speechSoundGame, const SpeechGameArgs('rimas')),
    'empieza': (AppRoutes.speechSoundGame, const SpeechGameArgs('empieza')),
    'escucho y encuentro': (AppRoutes.speechSoundGame, const SpeechGameArgs('encuentro', level: 3)),
    'juegos de palabras': (AppRoutes.speechWordGames, null),
    'de qué grupo es': (AppRoutes.speechWordGame, const SpeechGameArgs('grupo', level: 2)),
    'completa la frase': (AppRoutes.speechWordGame, const SpeechGameArgs('frase', level: 3)),
    'palabras de transporte': (AppRoutes.speechWords, const SpeechWordsArgs('transporte')),
    'mi historia': (AppRoutes.speechMyStory, null),
    'conversación adaptativa': (AppRoutes.speechConversation, const SpeechConversationArgs('elige_animal')),
    'búsqueda': (AppRoutes.search, null),
    'premios': (AppRoutes.rewards, null),
    'colores': (AppRoutes.learningGame, const LearningGameArgs(GameId.colors)),
    'formas': (AppRoutes.learningGame, const LearningGameArgs(GameId.shapes)),
    'animales': (AppRoutes.learningGame, const LearningGameArgs(GameId.animals)),
    'parejas': (AppRoutes.learningGame, const LearningGameArgs(GameId.memory)),
    'rompecabezas': (AppRoutes.learningGame, const LearningGameArgs(GameId.puzzle)),
    'laberintos': (AppRoutes.learningGame, const LearningGameArgs(GameId.maze)),
    'trazos': (AppRoutes.learningGame, const LearningGameArgs(GameId.tracing)),
    'adultos': (AppRoutes.adultZone, const AdultZoneArgs.verified()),
  };

  for (final textScale in [1.0, 1.6]) {
    for (final MapEntry(key: sizeName, value: size) in sizes.entries) {
      testWidgets('$sizeName, texto ×$textScale: sin desbordamientos', (tester) async {
        setScreenSize(tester, size, textScale: textScale);
        await pumpApp(tester);
        final navigator = tester.state<NavigatorState>(find.byType(Navigator));
        for (final MapEntry(key: name, value: (route, args)) in routes.entries) {
          if (route != AppRoutes.home) {
            navigator.pushNamed(route, arguments: args);
            await tester.pumpAndSettle();
          }
          expect(tester.takeException(), isNull, reason: name);
          expect(find.text('Ups, aquí no hay nada'), findsNothing, reason: name);
          if (route != AppRoutes.home) {
            navigator.pop();
            await tester.pumpAndSettle();
          }
        }
      });
    }
  }
}
