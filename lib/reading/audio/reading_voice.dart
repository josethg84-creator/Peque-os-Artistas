import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';

import '../../audio/app_audio.dart';
import '../reading_content.dart';
import '../sentences.dart';

/// Velocidad de reproducción.
enum ReadingSpeed { normal, slow }

/// Cómo se resaltaron las palabras de la última oración.
enum SentenceHighlight {
  /// Grabación con los tiempos de cada palabra medidos sobre ella.
  recordedTimes,

  /// La voz del dispositivo avisó de verdad de cada palabra que empezaba.
  voiceEvents,

  /// Lectura lenta palabra por palabra: cada palabra se dice por separado y se
  /// resalta mientras suena.
  wordByWord,

  /// Sin resaltado sincronizado (la voz no avisa de las palabras y no hay
  /// tiempos medidos). No se simula con temporizadores.
  none,
}

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
  /// [onPosition] recibe la posición de la grabación mientras suena.
  Future<void> play(
    String assetPath, {
    required double rate,
    required double volume,
    void Function(Duration position)? onPosition,
  });
  Future<void> stop();
  Future<void> dispose();
}

/// Grabaciones con `audioplayers` (Android, iPhone y navegador).
class AudioPlayersClipPlayer implements ClipPlayer {
  AudioPlayer? _player;
  Completer<void>? _done;

  static const maxLength = Duration(seconds: 15);

  @override
  Future<void> play(
    String assetPath, {
    required double rate,
    required double volume,
    void Function(Duration position)? onPosition,
  }) async {
    final player = _player ??= AudioPlayer()..setReleaseMode(ReleaseMode.stop);
    await stop();
    final done = _done = Completer<void>();
    final sub = player.onPlayerComplete.listen((_) {
      if (!done.isCompleted) done.complete();
    });
    final pos = onPosition == null
        ? null
        : player.onPositionChanged.listen((p) {
            if (!done.isCompleted) onPosition(p);
          });
    try {
      await player.setPlaybackRate(rate);
      // AssetSource ya antepone «assets/».
      await player.play(AssetSource(assetPath.replaceFirst('assets/', '')), volume: volume);
      await done.future.timeout(maxLength, onTimeout: () {});
    } finally {
      await sub.cancel();
      await pos?.cancel();
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

  /// Cómo se resaltó la última oración (para explicarlo en pantalla).
  SentenceHighlight? lastHighlight;

  /// Lee una oración completa resaltando cada palabra mientras suena, por este
  /// orden de preferencia:
  /// 1. grabación con los tiempos de cada palabra medidos sobre ella;
  /// 2. lento: palabra por palabra (cada palabra suena sola y se resalta);
  /// 3. la voz del dispositivo, si avisa de verdad de cada palabra;
  /// 4. si no avisa, se lee sin resaltar ([SentenceHighlight.none]).
  ///
  /// [onWord] recibe la palabra que suena (o `null` al terminar). Devuelve
  /// `true` si la oración sonó entera (sin cortarla ni quedarse sin voz).
  Future<bool> playSentence(
    ReadingSentence sentence, {
    ReadingSpeed speed = ReadingSpeed.normal,
    required void Function(int? word) onWord,
  }) async {
    final turn = ++_turn;
    await _stopSources();
    if (_audio.voiceVolume <= 0) {
      _set(
        ReadingVoiceStatus.muted,
        why: 'El sonido está apagado. Un adulto puede encenderlo en los ajustes.',
      );
      return false;
    }
    _set(ReadingVoiceStatus.playing);
    final slow = speed == ReadingSpeed.slow;
    var ok = false;
    void word(int? i) {
      if (turn == _turn && !_disposed) onWord(i);
    }

    try {
      final clip = sentence.clip;
      var played = false;
      if (clip != null && (!slow || sentence.wordMs != null)) {
        try {
          final times = sentence.wordMs;
          lastHighlight = times == null ? SentenceHighlight.none : SentenceHighlight.recordedTimes;
          await _clips.play(
            clip,
            rate: slow ? slowRate : 1.0,
            volume: _audio.voiceVolume,
            onPosition: times == null ? null : (p) => word(sentence.wordAtMs(p.inMilliseconds)),
          );
          played = true;
          ok = turn == _turn;
        } catch (e) {
          lastClipError = e; // se usa la voz del dispositivo
        }
      }
      if (!played && slow) {
        lastHighlight = SentenceHighlight.wordByWord;
        for (final (i, w) in sentence.words.indexed) {
          if (turn != _turn) return false;
          word(i);
          final c = w.clip;
          var done = false;
          if (c != null) {
            try {
              await _clips.play(c, rate: slowRate, volume: _audio.voiceVolume);
              done = true;
            } catch (e) {
              lastClipError = e;
            }
          }
          if (!done && !await _speak(w.audio.tts, slow: true, turn: turn)) return false;
        }
        ok = turn == _turn;
      } else if (!played) {
        final info = await _audio.voiceInfo();
        if (turn != _turn) return false;
        if (!info.available) {
          _set(ReadingVoiceStatus.noVoice, why: info.description);
          return false;
        }
        var events = 0;
        await _audio.say(
          sentence.text,
          onBoundary: (c) {
            if (turn != _turn) return;
            events++;
            word(sentence.wordAt(c));
          },
        );
        if (turn == _turn) {
          lastHighlight = events > 0 ? SentenceHighlight.voiceEvents : SentenceHighlight.none;
          ok = true;
        }
      }
      return ok;
    } finally {
      word(null);
      if (turn == _turn && _status == ReadingVoiceStatus.playing) _set(ReadingVoiceStatus.idle);
    }
  }

  /// Dice una palabra sílaba a sílaba («pe… lo… ta»): cada sílaba suena por
  /// separado (grabación si la hay; si no, la voz del dispositivo en
  /// minúsculas) y [onSyllable] recibe la que suena (o `null` al terminar).
  /// Devuelve `true` si sonaron todas (sin cortarla).
  Future<bool> playSyllables(
    List<ReadingAudio> syllables, {
    ReadingSpeed speed = ReadingSpeed.normal,
    void Function(int? syllable)? onSyllable,
  }) async {
    if (syllables.isEmpty) return false;
    final turn = ++_turn;
    await _stopSources();
    if (_audio.voiceVolume <= 0) {
      _set(
        ReadingVoiceStatus.muted,
        why: 'El sonido está apagado. Un adulto puede encenderlo en los ajustes.',
      );
      return false;
    }
    _set(ReadingVoiceStatus.playing);
    final slow = speed == ReadingSpeed.slow;
    void mark(int? i) {
      if (turn == _turn && !_disposed) onSyllable?.call(i);
    }

    try {
      for (final (i, s) in syllables.indexed) {
        if (turn != _turn) return false;
        mark(i);
        var done = false;
        if (s.clip case final clip?) {
          try {
            await _clips.play(clip, rate: slow ? slowRate : 1.0, volume: _audio.voiceVolume);
            done = true;
          } catch (e) {
            lastClipError = e;
          }
        }
        if (!done && !await _speak(s.tts.toLowerCase(), slow: slow, turn: turn)) return false;
      }
      return turn == _turn;
    } finally {
      mark(null);
      if (turn == _turn && _status == ReadingVoiceStatus.playing) _set(ReadingVoiceStatus.idle);
    }
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

  /// Posiciones que se anuncian mientras «suena» una grabación.
  List<Duration> positions = const [];

  @override
  Future<void> play(
    String assetPath, {
    required double rate,
    required double volume,
    void Function(Duration position)? onPosition,
  }) async {
    if (fail) throw StateError('no se pudo reproducir $assetPath');
    played.add((assetPath, rate));
    if (onPosition != null) {
      for (final p in positions) {
        onPosition(p);
        await Future<void>.delayed(Duration.zero);
      }
    }
  }

  @override
  Future<void> stop() async => stops++;

  @override
  Future<void> dispose() async => disposed = true;
}
