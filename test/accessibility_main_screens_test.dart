/// Fase 8: pautas de accesibilidad de Flutter (áreas táctiles, etiquetas y
/// contraste) en las pantallas principales de la app original.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';

import 'test_helpers.dart';

void main() {
  for (final r in [
    AppRoutes.home,
    AppRoutes.categories,
    AppRoutes.activities,
    AppRoutes.miniGames,
    AppRoutes.rewards,
    AppRoutes.savedDrawings,
    AppRoutes.soundSettings,
    AppRoutes.speech,
    AppRoutes.speechWordGroups,
    AppRoutes.speechSentences,
    AppRoutes.speechStories,
    AppRoutes.speechExpress,
    AppRoutes.speechSounds,
  ]) {
    for (final g in [androidTapTargetGuideline, labeledTapTargetGuideline, textContrastGuideline]) {
      testWidgets('$r ${g.description}', (tester) async {
        final s = tester.ensureSemantics();
        setScreenSize(tester, const Size(412, 915));
        await pumpApp(tester);
        if (r != AppRoutes.home) {
          tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(r);
          await tester.pumpAndSettle();
        }
        await expectLater(tester, meetsGuideline(g));
        s.dispose();
      });
    }
  }
}
