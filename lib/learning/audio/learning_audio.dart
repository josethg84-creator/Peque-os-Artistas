import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_tts/flutter_tts.dart';

import '../learning_progress.dart';

enum SoundCue {
  tap('sounds/tap.wav'),
  select('sounds/select.wav'),
  pop('sounds/pop.wav'),
  correct('sounds/correct.wav'),
  tryAgain('sounds/try_again.wav'),
  saved('sounds/saved.wav'),
  celebrate('sounds/celebrate.wav', important: true),
  reward('sounds/reward.wav', important: true);

  const SoundCue(this.asset, {this.important = false});

  /// Ruta dentro de `assets/` (archivos generados por tools/make_sounds.py).
  final String asset;

  /// Las celebraciones no se cortan con un toque.
  final bool important;
}

/// Reproduce efectos de sonido locales.
abstract interface class SoundEffects {
  Future<void> play(SoundCue cue);

  /// Libera los reproductores (se vuelven a crear si hacen falta).
  Future<void> release();
}

/// Lee textos en voz alta.
abstract interface class Narrator {
  Future<void> speak(String text);
  Future<void> stop();
}

/// Efectos con `audioplayers`: UN solo reproductor de baja latencia, creado
/// al primer uso. Cada efecto detiene el anterior, así nunca suenan varios a
/// la vez. Volumen moderado.
class AudioPlayersSoundEffects implements SoundEffects {
  static const volume = 0.5;
  AudioPlayer? _player;

  @override
  Future<void> play(SoundCue cue) async {
    final player = _player ??= AudioPlayer()..setPlayerMode(PlayerMode.lowLatency);
    await player.stop();
    await player.play(AssetSource(cue.asset), volume: volume);
  }

  @override
  Future<void> release() async {
    final player = _player;
    _player = null;
    await player?.dispose();
  }
}

/// Voz con el motor de texto a voz del propio dispositivo (`flutter_tts`).
/// No descarga nada: usa las voces instaladas. Si no hay voz en español, la
/// lectura simplemente no suena (la app sigue funcionando con texto e iconos).
class DeviceTtsNarrator implements Narrator {
  final _tts = FlutterTts();
  Future<bool>? _ready;

  Future<bool> _init() async {
    for (final lang in const ['es-ES', 'es-MX', 'es-US', 'es']) {
      final available = await _tts.isLanguageAvailable(lang);
      if (available == true || available == 1) {
        await _tts.setLanguage(lang);
        await _tts.setSpeechRate(0.42); // Pausada.
        await _tts.setPitch(1.08); // Amable.
        await _tts.setVolume(0.9);
        return true;
      }
    }
    return false;
  }

  @override
  Future<void> speak(String text) async {
    if (!await (_ready ??= _init())) return;
    await _tts.stop();
    await _tts.speak(text);
  }

  @override
  Future<void> stop() async {
    if (_ready == null) return;
    await _tts.stop();
  }
}

/// Punto único de audio de «Aprender jugando»: respeta las preferencias del
/// niño (sonidos y voz por separado) y nunca deja que un fallo de audio
/// interrumpa el juego.
class LearningAudio {
  LearningAudio({
    required this.effects,
    required this.narrator,
    required this.settings,
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now;

  final SoundEffects effects;
  final Narrator narrator;
  final LearningSettings Function() settings;
  final DateTime Function() _clock;
  DateTime? _importantUntil;

  /// Tiempo durante el que una celebración no se interrumpe con un toque.
  static const importantWindow = Duration(milliseconds: 900);

  Future<void> play(SoundCue cue) async {
    if (!settings().soundOn) return;
    final now = _clock();
    if (!cue.important && _importantUntil != null && now.isBefore(_importantUntil!)) return;
    if (cue.important) _importantUntil = now.add(importantWindow);
    try {
      await effects.play(cue);
    } catch (_) {
      // Sin sonido no pasa nada: hay respuesta visual.
    }
  }

  Future<void> say(String text) async {
    if (!settings().voiceOn) return;
    try {
      await narrator.speak(text);
    } catch (_) {}
  }

  Future<void> stopVoice() async {
    try {
      await narrator.stop();
    } catch (_) {}
  }

  /// Al salir de «Aprender jugando»: calla la voz y libera los reproductores.
  Future<void> release() async {
    await stopVoice();
    try {
      await effects.release();
    } catch (_) {}
  }
}

/// Sin audio (pruebas o dispositivos sin soporte). Registra lo que se pidió.
class RecordingSoundEffects implements SoundEffects {
  final played = <SoundCue>[];
  int releases = 0;

  @override
  Future<void> play(SoundCue cue) async => played.add(cue);

  @override
  Future<void> release() async => releases++;
}

class RecordingNarrator implements Narrator {
  final spoken = <String>[];
  int stops = 0;

  @override
  Future<void> speak(String text) async => spoken.add(text);

  @override
  Future<void> stop() async => stops++;
}
