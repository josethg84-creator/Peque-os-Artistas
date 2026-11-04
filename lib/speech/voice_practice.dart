import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'voice_practice_files.dart' if (dart.library.js_interop) 'voice_practice_files_web.dart';

/// Una grabación de práctica: solo existe mientras está abierta la ventana de
/// «Practicar» (en memoria en la web, en la carpeta temporal de la app en el
/// teléfono) y se borra al cerrarla o al grabar otra vez.
class VoiceClip {
  const VoiceClip(this.source, this.duration);

  /// Ruta del archivo temporal o dirección `blob:` del navegador.
  final String source;
  final Duration duration;
}

/// Graba la voz del niño para que se escuche a sí mismo. No evalúa nada ni
/// envía nada: es solo un espejo de voz.
abstract interface class VoiceRecorder {
  /// Pide el permiso del micrófono (el sistema solo pregunta la primera vez).
  Future<bool> requestPermission();
  Future<void> start();

  /// Termina la grabación. `null` si no se grabó nada.
  Future<VoiceClip?> stop();
  Future<void> play(VoiceClip clip);
  Future<void> stopPlaying();

  /// Borra la grabación (el archivo temporal o la dirección del navegador).
  Future<void> discard(VoiceClip clip);
  Future<void> dispose();
}

/// Grabación real con `record` y reproducción con `audioplayers`.
class DeviceVoiceRecorder implements VoiceRecorder {
  DeviceVoiceRecorder();

  final AudioRecorder _recorder = AudioRecorder();
  AudioPlayer? _player;
  DateTime? _startedAt;

  @override
  Future<bool> requestPermission() async {
    try {
      return await _recorder.hasPermission();
    } catch (_) {
      return false;
    }
  }

  @override
  Future<void> start() async {
    // WAV en todas partes si se puede (sin pérdidas y fácil de reproducir); si
    // no, AAC en el teléfono u Opus en el navegador.
    final encoder = await _recorder.isEncoderSupported(AudioEncoder.wav)
        ? AudioEncoder.wav
        : (kIsWeb ? AudioEncoder.opus : AudioEncoder.aacLc);
    final path = kIsWeb ? '' : await _tempPath(encoder == AudioEncoder.wav ? 'wav' : 'm4a');
    await _recorder.start(RecordConfig(encoder: encoder, numChannels: 1), path: path);
    _startedAt = DateTime.now();
  }

  bool _swept = false;

  Future<String> _tempPath(String ext) async {
    final dir = await getTemporaryDirectory();
    if (!_swept) {
      _swept = true;
      await sweepStaleClips(dir.path);
    }
    return '${dir.path}/practica_${DateTime.now().millisecondsSinceEpoch}.$ext';
  }

  @override
  Future<VoiceClip?> stop() async {
    final source = await _recorder.stop();
    final started = _startedAt;
    _startedAt = null;
    if (source == null || source.isEmpty || started == null) return null;
    return VoiceClip(source, DateTime.now().difference(started));
  }

  @override
  Future<void> play(VoiceClip clip) async {
    final player = _player ??= AudioPlayer();
    await player.stop();
    await player.play(kIsWeb ? UrlSource(clip.source) : DeviceFileSource(clip.source));
  }

  @override
  Future<void> stopPlaying() async => _player?.stop();

  @override
  Future<void> discard(VoiceClip clip) => deleteClipSource(clip.source);

  @override
  Future<void> dispose() async {
    try {
      if (await _recorder.isRecording()) {
        final source = await _recorder.stop();
        if (source != null) await deleteClipSource(source);
      }
    } catch (_) {}
    await _recorder.dispose();
    await _player?.dispose();
  }
}

/// Para las pruebas: «graba» al instante y anota lo que pasa.
class FakeVoiceRecorder implements VoiceRecorder {
  FakeVoiceRecorder({this.permission = true});

  bool permission;
  int permissionRequests = 0;
  int recordings = 0;
  final played = <String>[];
  final discarded = <String>[];
  bool recording = false;
  bool disposed = false;

  @override
  Future<bool> requestPermission() async {
    permissionRequests++;
    return permission;
  }

  @override
  Future<void> start() async => recording = true;

  @override
  Future<VoiceClip?> stop() async {
    if (!recording) return null;
    recording = false;
    recordings++;
    return VoiceClip('memoria://grabacion_$recordings', const Duration(seconds: 2));
  }

  @override
  Future<void> play(VoiceClip clip) async => played.add(clip.source);

  @override
  Future<void> stopPlaying() async {}

  @override
  Future<void> discard(VoiceClip clip) async => discarded.add(clip.source);

  @override
  Future<void> dispose() async => disposed = true;
}
