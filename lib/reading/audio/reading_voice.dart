import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';

import '../../audio/app_audio.dart';
import '../reading_content.dart';

/// Velocidad de reproducción.
enum ReadingSpeed { normal, slow }

/// En qué está la voz de lectura (para que la pantalla lo muestre).
enum ReadingVoiceStatus {
  idle,
  playing,

  /// El sonido o la voz están apagados en los ajustes.
  muted,

  /// El dispositivo no tiene una voz en español y no hay grabación.
  noVoice,
}

/// Reproduce archivos de audio (grabaciones validadas de sílabas y palabras).
abstract interface class ClipPlayer {
  /// Termina cuando acaba el audio; lanza un error si no se puede reproducir.
  Future<void> play(String assetPath, {required double rate, required double volume});
  Future<void> stop();
  Future<void> dispose();
}

/// Grabaciones con `audioplayers` (Android, iPhone y navegador).
class AudioPlayersClipPlayer implements ClipPlayer {
  AudioPlayer? _player;
  Completer<void>? _done;

  static const maxLength = Duration(seconds: 8);

  @override
  Future<void> play(String assetPath, {required double rate, required double volume}) async {
    final player = _player ??= AudioPlayer()..setReleaseMode(ReleaseMode.stop);
    await stop();
    final done = _done = Completer<void>();
    final sub = player.onPlayerComplete.listen((_) {
      if (!done.isCompleted) done.complete();
    });
    try {
      await player.setPlaybackRate(rate);
      // AssetSource ya antepone «assets/».
      await player.play(AssetSource(assetPath.replaceFirst('assets/', '')), volume: volume);
      await done.future.timeout(maxLength, onTimeout: () {});
    } finally {
      await sub.cancel();
    }
  }

  @override
  Future<void> stop() async {
    final done = _done;
    _done = null;
    if (done != null && !done.isCompleted) done.complete();
    await _player?.stop();
  }

  @override
  Future<void> dispose() async {
    await stop();
    await _player?.dispose();
    _player = null;
  }
}

/// Motor de audio de «Aprendo a leer».
///
/// Estrategia: 1) grabación validada si existe (sílabas, letras y palabras);
/// 2) si no existe o falla, la voz del dispositivo con el texto en minúsculas
/// («ma», nunca «MA», para que no lo deletree); 3) si tampoco hay voz, lo
/// indica en [status] para que la pantalla muestre el aviso. Un sonido nuevo
/// siempre corta el anterior (grabación o voz): nunca se superponen.
class ReadingVoice extends ChangeNotifier {
  ReadingVoice(this._audio, {ClipPlayer? clips}) : _clips = clips ?? clipPlayerFactory();

  /// Las pruebas lo sustituyen por un reproductor simulado.
  static ClipPlayer Function() clipPlayerFactory = AudioPlayersClipPlayer.new;

  /// Velocidad de las grabaciones en modo lento (la voz del dispositivo usa la
  /// suya, ver [DeviceTtsNarrator.slowFactor]).
  static const slowRate = 0.7;

  final LearningAudio _audio;
  final ClipPlayer _clips;
  int _turn = 0;
  bool _disposed = false;

  ReadingVoiceStatus _status = ReadingVoiceStatus.idle;
  ReadingVoiceStatus get status => _status;

  /// Explicación para el adulto cuando [status] es [ReadingVoiceStatus.noVoice].
  String? message;

  /// La última vez que una grabación falló y se usó la voz del dispositivo.
  Object? lastClipError;

  void _set(ReadingVoiceStatus s, {String? why}) {
    if (_disposed) return;
    _status = s;
    message = why;
    notifyListeners();
  }

  /// Reproduce un sonido (corta el anterior).
  Future<void> play(ReadingAudio audio, {ReadingSpeed speed = ReadingSpeed.normal}) =>
      playAll([audio], speed: speed);

  /// Reproduce varios seguidos («pe… pelota»). Si todos van con la voz del
  /// dispositivo, se dicen en una sola frase con pausas.
  Future<void> playAll(List<ReadingAudio> sounds, {ReadingSpeed speed = ReadingSpeed.normal}) async {
    if (sounds.isEmpty) return;
    final turn = ++_turn;
    await _stopSources();
    if (_audio.voiceVolume <= 0) {
      _set(
        ReadingVoiceStatus.muted,
        why: 'El sonido está apagado. Un adulto puede encenderlo en los ajustes.',
      );
      return;
    }
    _set(ReadingVoiceStatus.playing);
    final slow = speed == ReadingSpeed.slow;
    if (sounds.every((s) => !s.recorded)) {
      await _speak(sounds.map((s) => s.tts).join('. '), slow: slow, turn: turn);
    } else {
      for (final s in sounds) {
        if (turn != _turn) return;
        final clip = s.clip;
        var ok = false;
        if (clip != null) {
          try {
            await _clips.play(clip, rate: slow ? slowRate : 1.0, volume: _audio.voiceVolume);
            ok = true;
          } catch (e) {
            lastClipError = e; // se usa la voz del dispositivo
          }
        }
        if (!ok && !await _speak(s.tts, slow: slow, turn: turn)) return;
      }
    }
    if (turn == _turn && _status == ReadingVoiceStatus.playing) _set(ReadingVoiceStatus.idle);
  }

  Future<bool> _speak(String text, {required bool slow, required int turn}) async {
    final info = await _audio.voiceInfo();
    if (turn != _turn) return false;
    if (!info.available) {
      _set(ReadingVoiceStatus.noVoice, why: info.description);
      return false;
    }
    await _audio.say(text, slow: slow);
    return turn == _turn;
  }

  /// Dice una frase de ánimo o instrucción («¡Muy bien!») con la voz.
  Future<void> sayText(String text) => playAll([ReadingAudio(tts: text)]);

  Future<void> _stopSources() async {
    try {
      await _clips.stop();
    } catch (_) {}
    await _audio.stopVoice();
  }

  /// Detiene lo que suene.
  Future<void> stop() async {
    _turn++;
    await _stopSources();
    if (_status == ReadingVoiceStatus.playing) _set(ReadingVoiceStatus.idle);
  }

  @override
  void dispose() {
    _turn++;
    _disposed = true;
    unawaited(_stopSources());
    unawaited(_clips.dispose());
    super.dispose();
  }
}

/// Reproductor simulado para las pruebas: anota lo que suena.
@visibleForTesting
class FakeClipPlayer implements ClipPlayer {
  FakeClipPlayer({this.fail = false});
  bool fail;
  final played = <(String, double)>[];
  int stops = 0;
  bool disposed = false;

  @override
  Future<void> play(String assetPath, {required double rate, required double volume}) async {
    if (fail) throw StateError('no se pudo reproducir $assetPath');
    played.add((assetPath, rate));
  }

  @override
  Future<void> stop() async => stops++;

  @override
  Future<void> dispose() async => disposed = true;
}
