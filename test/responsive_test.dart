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
