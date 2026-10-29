import 'package:flutter/material.dart';

import '../../widgets/catalog_builder.dart';
import '../learning_level.dart';
import '../quiz_specs.dart';
import 'memory_game_screen.dart';
import 'quiz_game_screen.dart';

/// Abre el minijuego indicado. Los que usan dibujos esperan al catálogo.
class LearningGameScreen extends StatelessWidget {
  const LearningGameScreen({super.key, required this.game, this.seed});

  final GameId game;
  final int? seed;

  @override
  Widget build(BuildContext context) => switch (game) {
    GameId.colors => QuizGameScreen(spec: const ColorsSpec(), seed: seed),
    GameId.shapes => QuizGameScreen(spec: const ShapesSpec(), seed: seed),
    GameId.animals => Scaffold(
      body: CatalogBuilder(
        builder: (context, catalog) => QuizGameScreen(spec: AnimalsSpec(catalog), seed: seed),
      ),
    ),
    GameId.memory => Scaffold(
      body: CatalogBuilder(
        builder: (context, catalog) => MemoryGameScreen(catalog: catalog, seed: seed),
      ),
    ),
  };
}
