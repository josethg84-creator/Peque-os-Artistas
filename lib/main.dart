import 'package:flutter/material.dart';

import 'app.dart';
import 'learning/audio/learning_audio.dart';
import 'learning/learning_controller.dart';
import 'learning/learning_store.dart';
import 'persistence/creation_store.dart';
import 'persistence/key_value_backend.dart';
import 'services/catalog_service.dart';
import 'services/drawing_loader.dart';

void main() {
  // Necesario antes de usar plugins (almacenamiento) fuera de runApp.
  WidgetsFlutterBinding.ensureInitialized();
  // Un único almacenamiento local para creaciones y progreso de aprendizaje.
  final storage = SharedPreferencesBackend();
  final learning = LearningController(LearningStore(storage))..load();
  runApp(
    PequenosArtistasApp(
      catalogService: CatalogService(),
      drawingLoader: DrawingLoader(),
      creationStore: KeyValueCreationStore(storage),
      learningController: learning,
      learningAudio: LearningAudio(
        effects: AudioPlayersSoundEffects(),
        narrator: DeviceTtsNarrator(),
        music: AudioPlayersMusic(),
        settings: () => learning.settings,
        // La música no empieza hasta conocer las preferencias guardadas.
        settingsReady: () => learning.isLoaded,
      ),
    ),
  );
}
