import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'aac/aac_controller.dart';
import 'audio/web_speech.dart';
import 'app.dart';
import 'learning/audio/learning_audio.dart';
import 'learning/learning_controller.dart';
import 'learning/learning_store.dart';
import 'persistence/creation_store.dart';
import 'persistence/key_value_backend.dart';
import 'services/catalog_service.dart';
import 'services/drawing_loader.dart';
import 'speech/speech_progress.dart';

/// En la web, la voz habla directamente con el navegador ([WebSpeechNarrator]);
/// en el teléfono, con el motor de texto a voz del sistema.
Narrator _narrator() {
  final engine = kIsWeb ? browserSpeechEngine() : null;
  return engine != null ? WebSpeechNarrator(engine) : DeviceTtsNarrator();
}

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
      speechController: SpeechController(SpeechStore(storage))..load(),
      aacController: AacController(AacStore(storage))..load(),
      learningAudio: LearningAudio(
        effects: AudioPlayersSoundEffects(),
        narrator: _narrator(),
        music: AudioPlayersMusic(),
        settings: () => learning.settings,
        // La música no empieza hasta conocer las preferencias guardadas.
        settingsReady: () => learning.isLoaded,
      ),
    ),
  );
}
