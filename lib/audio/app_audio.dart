import 'dart:async';
import 'dart:math';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

import '../learning/learning_progress.dart';

/// Efectos de sonido. Cada uno tiene una o varias variantes (archivos de
/// `assets/audio/effects/`, generados por `tools/make_audio.py`) para que no
/// suene siempre exactamente igual.
enum SoundCue {
  /// Pulsar un botón: clic suave.
  tap(['click_1', 'click_2']),

  /// Elegir una herramienta (el borrador).
  select(['select_1']),

  /// Seleccionar una categoría.
  category(['category_1', 'category_2']),

  /// Abrir un dibujo: campanita.
  open(['open_1', 'open_2']),

  /// Elegir un color: una nota de xilófono por color (escala pentatónica).
  color(['color_1', 'color_2', 'color_3', 'color_4', 'color_5', 'color_6', 'color_7', 'color_8']),

  /// Colorear una zona.
  pop(['fill_1', 'fill_2', 'fill_3']),
  saved(['saved_1']),
  correct(['correct_1', 'correct_2']),
  tryAgain(['try_again_1', 'try_again_2']),

  /// Estrellas conseguidas: brillo mágico.
  star(['star_1']),
  celebrate(['celebrate_1', 'celebrate_2'], important: true),
  reward(['reward_1'], important: true);

  const SoundCue(this.files, {this.important = false});

  final List<String> files;

  /// Las celebraciones no se cortan con un toque.
  final bool important;

  /// Ruta dentro de `assets/`.
  String asset(int variant) => 'audio/effects/${files[variant % files.length]}.wav';
}

/// Música de fondo (bucles instrumentales de `assets/audio/music/`).
enum MusicTrack {
  /// Inicio y menús: alegre y tranquila.
  main('audio/music/main_theme.ogg'),

  /// Colorear: más lenta y suave.
  coloring('audio/music/coloring_theme.ogg');

  const MusicTrack(this.asset);
  final String asset;
}

/// Cómo se comporta una frase si ya se está hablando.
enum VoiceMode {
  /// Respuesta a algo que acaba de hacer el niño: corta la frase anterior.
  interrupt,

  /// Se dice al terminar la frase actual (sin cortarla).
  queue,

  /// Comentario de ambiente: se descarta si ya se está hablando, si es la misma
  /// frase de hace un momento o si hubo otro comentario hace poco.
  ambient,
}

/// Reproduce efectos de sonido locales.
abstract interface class SoundEffects {
  Future<void> play(SoundCue cue, {int variant = 0, double volume = 1});

  /// Libera los reproductores (se vuelven a crear si hacen falta).
  Future<void> release();
}

/// Música de fondo en bucle.
abstract interface class MusicPlayer {
  /// Empieza (o continúa) [track]. Si ya sonaba, solo ajusta el volumen.
  Future<void> play(MusicTrack track, {required double volume});
  Future<void> setVolume(double volume);
  Future<void> pause();
  Future<void> release();
}

/// Qué voz hay disponible en el dispositivo.
class VoiceInfo {
  const VoiceInfo({required this.available, required this.description});

  final bool available;

  /// Explicación para la pantalla de ajustes (incluye si funciona sin conexión).
  final String description;
}

/// Lee textos en voz alta. [speak] termina cuando acaba la frase.
abstract interface class Narrator {
  Future<void> speak(String text);
  Future<void> stop();
  Future<void> setVolume(double volume);
  Future<VoiceInfo> voice();
}

/// Efectos con `audioplayers`: UN solo reproductor de baja latencia. Cada efecto
/// detiene el anterior, así nunca suenan varios a la vez. No pide el «foco de
/// audio» de Android, para no pausar la música de la propia app.
class AudioPlayersSoundEffects implements SoundEffects {
  /// Escala del volumen final (los archivos ya están a -12 dBFS).
  static const baseVolume = 0.6;
  AudioPlayer? _player;

  static final _context = AudioContext(
    android: const AudioContextAndroid(
      audioFocus: AndroidAudioFocus.none,
      usageType: AndroidUsageType.game,
      contentType: AndroidContentType.sonification,
    ),
    // iOS: categoría «ambient», que respeta el interruptor de silencio.
    iOS: AudioContextIOS(category: AVAudioSessionCategory.ambient),
  );

  Future<AudioPlayer> _ready() async {
    final existing = _player;
    if (existing != null) return existing;
    final player = AudioPlayer();
    _player = player;
    await player.setPlayerMode(PlayerMode.lowLatency);
    await player.setAudioContext(_context);
    return player;
  }

  @override
  Future<void> play(SoundCue cue, {int variant = 0, double volume = 1}) async {
    final player = await _ready();
    await player.stop();
    await player.play(AssetSource(cue.asset(variant)), volume: volume * baseVolume);
  }

  @override
  Future<void> release() async {
    final player = _player;
    _player = null;
    await player?.dispose();
  }
}

/// Música con `audioplayers` en bucle continuo. Los cambios de volumen (entrar,
/// salir, bajar mientras habla la voz) son fundidos suaves, nunca saltos.
class AudioPlayersMusic implements MusicPlayer {
  /// La música va por debajo de los efectos y de la voz.
  static const baseVolume = 0.45;
  static const fade = Duration(milliseconds: 800);
  static const _step = Duration(milliseconds: 50);

  AudioPlayer? _player;
  MusicTrack? _track;
  bool _playing = false;
  double _volume = 0;
  Timer? _fader;

  static final _context = AudioContext(
    android: const AudioContextAndroid(
      usageType: AndroidUsageType.game,
      contentType: AndroidContentType.music,
    ),
    iOS: AudioContextIOS(category: AVAudioSessionCategory.ambient),
  );

  Future<AudioPlayer> _ready() async {
    final existing = _player;
    if (existing != null) return existing;
    final player = AudioPlayer();
    _player = player;
    await player.setAudioContext(_context);
    await player.setReleaseMode(ReleaseMode.loop);
    return player;
  }

  @override
  Future<void> play(MusicTrack track, {required double volume}) async {
    final player = await _ready();
    if (_track != track) {
      _fader?.cancel();
      await player.stop();
      _volume = 0;
      _track = track;
      await player.play(AssetSource(track.asset), volume: 0);
    } else if (!_playing) {
      await player.resume();
    }
    _playing = true;
    _fadeTo(volume * baseVolume);
  }

  @override
  Future<void> setVolume(double volume) async {
    if (_playing) _fadeTo(volume * baseVolume);
  }

  @override
  Future<void> pause() async {
    if (!_playing) return;
    _playing = false;
    _fadeTo(
      0,
      then: () {
        if (!_playing) unawaited(_player?.pause());
      },
    );
  }

  void _fadeTo(double target, {VoidCallback? then}) {
    _fader?.cancel();
    final steps = fade.inMilliseconds ~/ _step.inMilliseconds;
    final start = _volume;
    var i = 0;
    _fader = Timer.periodic(_step, (timer) {
      i++;
      _volume = start + (target - start) * (i / steps);
      unawaited(_player?.setVolume(_volume));
      if (i >= steps) {
        timer.cancel();
        then?.call();
      }
    });
  }

  @override
  Future<void> release() async {
    _fader?.cancel();
    final player = _player;
    _player = null;
    _track = null;
    _playing = false;
    await player?.dispose();
  }
}

/// Voz con el motor de texto a voz del propio dispositivo (`flutter_tts`).
///
/// Solo usa una voz en español **instalada en el dispositivo** (en Android se
/// descartan las que necesitan conexión). Si no hay ninguna, no habla y la
/// pantalla de ajustes lo explica. No es una voz infantil grabada: es la voz
/// sintética del sistema, algo más aguda y pausada.
class DeviceTtsNarrator implements Narrator {
  DeviceTtsNarrator({
    FlutterTts? tts,
    DateTime Function()? clock,
    this.voicesWait = const Duration(seconds: 2),
  }) : _tts = tts ?? FlutterTts(),
       _clock = clock ?? DateTime.now;

  final FlutterTts _tts;
  final DateTime Function() _clock;

  /// En la web, el navegador carga su lista de voces un momento después de
  /// abrir la página: se espera hasta este tiempo a que aparezca.
  final Duration voicesWait;

  /// Si no hay voz, se vuelve a comprobar pasado este tiempo (las voces de la
  /// web llegan tarde y en Android se puede instalar una con la app abierta).
  static const retryAfter = Duration(seconds: 5);

  /// Solo se guarda una voz encontrada; un «no hay voz» caduca.
  Future<VoiceInfo>? _ready;
  VoiceInfo? _lastFailure;
  DateTime? _failedAt;
  double _volume = 1;

  /// Preferencia de variantes de español (Perú y Latinoamérica primero).
  static const preferredLocales = ['es-PE', 'es-419', 'es-US', 'es-MX', 'es-CO', 'es-AR', 'es-ES'];

  Future<VoiceInfo> _init() async {
    try {
      await _tts.awaitSpeakCompletion(true);
      final voice = await _pickOfflineVoice();
      if (voice == null) {
        return const VoiceInfo(
          available: false,
          description:
              'Este dispositivo no tiene una voz en español instalada para usar sin conexión. '
              'Se puede instalar en los ajustes de «Texto a voz» del dispositivo.',
        );
      }
      final locale = voice['locale']!;
      await _tts.setLanguage(locale);
      if ((voice['name'] ?? '').isNotEmpty) await _tts.setVoice({'name': voice['name']!, 'locale': locale});
      await _tts.setSpeechRate(0.42); // Pausada.
      await _tts.setPitch(1.12); // Amable.
      await _tts.setVolume(_volume);
      return VoiceInfo(
        available: true,
        description: 'Voz del dispositivo en español ($locale), instalada: funciona sin conexión.',
      );
    } catch (_) {
      return const VoiceInfo(available: false, description: 'La voz del dispositivo no está disponible.');
    }
  }

  /// Busca una voz española que no necesite Internet.
  Future<List<Map<String, String>>> _voices() async {
    try {
      final raw = await _tts.getVoices;
      if (raw is List) {
        return [
          for (final v in raw)
            if (v is Map) {for (final e in v.entries) '${e.key}': '${e.value}'},
        ];
      }
    } catch (_) {}
    return const [];
  }

  Future<Map<String, String>?> _pickOfflineVoice() async {
    var voices = await _voices();
    // Web: la lista llega vacía hasta que el navegador termina de cargarla.
    final deadline = _clock().add(voicesWait);
    while (kIsWeb && voices.isEmpty && _clock().isBefore(deadline)) {
      await Future<void>.delayed(const Duration(milliseconds: 250));
      voices = await _voices();
    }
    final offline = voices.where((v) {
      final locale = (v['locale'] ?? '').replaceAll('_', '-');
      return locale.toLowerCase().startsWith('es') &&
          v['network_required'] != '1' &&
          !(v['features'] ?? '').contains('notInstalled');
    }).toList();
    if (offline.isNotEmpty) {
      int rank(Map<String, String> v) {
        final i = preferredLocales.indexOf((v['locale'] ?? '').replaceAll('_', '-'));
        return i < 0 ? preferredLocales.length : i;
      }

      offline.sort((a, b) => rank(a).compareTo(rank(b)));
      final v = offline.first;
      return {'name': v['name'] ?? '', 'locale': (v['locale'] ?? 'es-ES').replaceAll('_', '-')};
    }
    // Plataformas sin lista de voces: se comprueba el idioma instalado.
    for (final lang in preferredLocales) {
      try {
        final installed = defaultTargetPlatform == TargetPlatform.android
            ? await _tts.isLanguageInstalled(lang)
            : await _tts.isLanguageAvailable(lang);
        if (installed == true || installed == 1) return {'name': '', 'locale': lang};
      } catch (_) {}
    }
    return null;
  }

  @override
  Future<VoiceInfo> voice() async {
    final ready = _ready;
    if (ready != null) return ready;
    final failedAt = _failedAt;
    if (failedAt != null && _clock().difference(failedAt) < retryAfter) return _lastFailure!;
    final pending = _ready = _init();
    final info = await pending;
    if (!info.available) {
      // No se da por perdida: se vuelve a mirar más tarde.
      _ready = null;
      _lastFailure = info;
      _failedAt = _clock();
    }
    return info;
  }

  @override
  Future<void> speak(String text) async {
    if (!(await voice()).available) return;
    await _tts.stop();
    await _tts.speak(text);
  }

  @override
  Future<void> stop() async {
    if (_ready == null) return;
    await _tts.stop();
  }

  @override
  Future<void> setVolume(double volume) async {
    if (_volume == volume) return;
    _volume = volume;
    if (_ready != null && (await voice()).available) await _tts.setVolume(volume);
  }
}

/// Sin música (pruebas o plataformas sin audio).
class SilentMusic implements MusicPlayer {
  @override
  Future<void> play(MusicTrack track, {required double volume}) async {}
  @override
  Future<void> setVolume(double volume) async {}
  @override
  Future<void> pause() async {}
  @override
  Future<void> release() async {}
}

class _MusicZoneToken {
  _MusicZoneToken(this.track);
  final MusicTrack? track;
}

/// Punto único de audio de la app: efectos, música y voz.
///
/// - Respeta las preferencias guardadas (silencio total, interruptores y
///   volúmenes de música, efectos y voz).
/// - Nunca suenan dos efectos a la vez; las celebraciones no se cortan con un
///   toque; un toque repetido muy rápido no repite el sonido.
/// - La música depende de la pantalla visible ([enterMusicZone]): suena en los
///   menús y al colorear, y calla en los juegos que piden concentración. Baja
///   de volumen mientras habla la voz y se pausa con la app en segundo plano.
/// - Un fallo de audio nunca interrumpe la app.
class LearningAudio {
  LearningAudio({
    required this.effects,
    required this.narrator,
    required this.settings,
    MusicPlayer? music,
    bool Function()? settingsReady,
    DateTime Function()? clock,
    Random? random,
  }) : music = music ?? SilentMusic(),
       _settingsReady = settingsReady ?? (() => true),
       _clock = clock ?? DateTime.now,
       _random = random ?? Random();

  final SoundEffects effects;
  final Narrator narrator;
  final MusicPlayer music;
  final LearningSettings Function() settings;
  final bool Function() _settingsReady;
  final DateTime Function() _clock;
  final Random _random;

  /// Tiempo durante el que una celebración no se interrumpe con un toque.
  static const importantWindow = Duration(milliseconds: 900);

  /// El mismo efecto pedido dos veces más deprisa que esto suena una sola vez.
  static const repeatGap = Duration(milliseconds: 90);

  /// Una frase de ambiente no se repite antes de este tiempo.
  static const ambientCooldown = Duration(seconds: 20);

  /// Volumen relativo de la música mientras habla la voz.
  static const duckFactor = 0.3;

  /// Tiempo máximo que se espera a que termine una frase.
  static const maxUtterance = Duration(seconds: 12);

  // ---------------------------------------------------------------- volúmenes
  double get _master => settings().muted ? 0 : settings().masterVolume;

  /// Volumen efectivo (0-1) de cada canal.
  double get effectsVolume => settings().soundOn ? _master * settings().effectsVolume : 0;
  double get voiceVolume => settings().voiceOn ? _master * settings().voiceVolume : 0;
  double get musicVolume => settings().musicOn ? _master * settings().musicVolume : 0;

  // ---------------------------------------------------------------- efectos
  DateTime? _importantUntil;
  final _lastPlayed = <SoundCue, DateTime>{};
  final _lastVariant = <SoundCue, int>{};

  /// Reproduce [cue]. [variant] elige un archivo concreto (p. ej. la nota de
  /// cada color); si no se indica, se elige una variante distinta de la última.
  Future<void> play(SoundCue cue, {int? variant}) async {
    final volume = effectsVolume;
    if (volume <= 0) return;
    final now = _clock();
    if (!cue.important && _importantUntil != null && now.isBefore(_importantUntil!)) return;
    final last = _lastPlayed[cue];
    if (last != null && now.difference(last) < repeatGap) return;
    _lastPlayed[cue] = now;
    if (cue.important) _importantUntil = now.add(importantWindow);
    final v = variant ?? _nextVariant(cue);
    _lastVariant[cue] = v;
    try {
      await effects.play(cue, variant: v, volume: volume);
    } catch (_) {
      // Sin sonido no pasa nada: hay respuesta visual.
    }
  }

  int _nextVariant(SoundCue cue) {
    final n = cue.files.length;
    final last = _lastVariant[cue];
    if (n == 1 || last == null) return n == 1 ? 0 : _random.nextInt(n);
    return (last + 1 + _random.nextInt(n - 1)) % n;
  }

  // ---------------------------------------------------------------- voz
  bool _speaking = false;
  int _utterance = 0;
  String? _queued;
  DateTime? _lastAmbient;
  String? _lastText;
  DateTime? _lastTextAt;
  final _lastPhrase = <List<String>, int>{};

  bool get isSpeaking => _speaking;

  /// Dice [text] si la voz está activada (ver [VoiceMode]).
  Future<void> say(String text, {VoiceMode mode = VoiceMode.interrupt}) async {
    if (voiceVolume <= 0) return;
    final now = _clock();
    if (mode != VoiceMode.interrupt) {
      final recent = _lastTextAt != null && now.difference(_lastTextAt!) < ambientCooldown;
      if (text == _lastText && recent) return;
    }
    if (mode == VoiceMode.ambient) {
      if (_speaking) return;
      if (_lastAmbient != null && now.difference(_lastAmbient!) < ambientCooldown) return;
      _lastAmbient = now;
    }
    if (mode == VoiceMode.queue && _speaking) {
      _queued = text;
      return;
    }
    await _speak(text);
  }

  /// Dice una de las [options], sin repetir la última que se dijo de la lista.
  Future<void> sayOneOf(List<String> options, {VoiceMode mode = VoiceMode.interrupt}) {
    final last = _lastPhrase[options];
    var i = _random.nextInt(options.length);
    if (options.length > 1 && i == last) i = (i + 1) % options.length;
    _lastPhrase[options] = i;
    return say(options[i], mode: mode);
  }

  Future<void> _speak(String text) async {
    final id = ++_utterance;
    _lastText = text;
    _lastTextAt = _clock();
    _speaking = true;
    _queued = null;
    _applyMusic();
    try {
      await narrator.setVolume(voiceVolume);
      await narrator.speak(text).timeout(maxUtterance);
    } catch (_) {}
    if (id != _utterance) return; // otra frase la sustituyó
    _speaking = false;
    final next = _queued;
    _queued = null;
    if (next != null && voiceVolume > 0) {
      await _speak(next);
      return;
    }
    _applyMusic();
  }

  Future<void> stopVoice() async {
    _utterance++;
    _queued = null;
    final wasSpeaking = _speaking;
    _speaking = false;
    if (wasSpeaking) _applyMusic();
    try {
      await narrator.stop();
    } catch (_) {}
  }

  /// Qué voz hay en el dispositivo (para la pantalla de ajustes).
  Future<VoiceInfo> voiceInfo() async {
    try {
      return await narrator.voice();
    } catch (_) {
      return const VoiceInfo(available: false, description: 'La voz del dispositivo no está disponible.');
    }
  }

  // ---------------------------------------------------------------- música
  final _zones = <_MusicZoneToken>[];
  bool _foreground = true;
  bool _musicActive = false;
  MusicTrack? _musicTrack;
  double? _musicLevel;

  /// La pantalla que aparece pide [track] (o silencio con `null`). Gana la
  /// última zona abierta, que es la pantalla visible. Devuelve una ficha para
  /// [exitMusicZone].
  Object enterMusicZone(MusicTrack? track) {
    final zone = _MusicZoneToken(track);
    _zones.add(zone);
    _applyMusic();
    return zone;
  }

  void exitMusicZone(Object zone) {
    _zones.remove(zone);
    _applyMusic();
  }

  /// Música que corresponde a la pantalla visible.
  MusicTrack? get zoneTrack => _zones.isEmpty ? null : _zones.last.track;

  /// Se llama al cambiar las preferencias.
  void refresh() => _applyMusic();

  /// La app pasa a segundo plano (`false`) o vuelve (`true`).
  void setForeground(bool foreground) {
    if (_foreground == foreground) return;
    _foreground = foreground;
    if (!foreground) unawaited(stopVoice());
    _applyMusic();
  }

  void _applyMusic() {
    final track = zoneTrack;
    final base = musicVolume;
    final play = _settingsReady() && _foreground && track != null && base > 0;
    if (!play) {
      if (_musicActive) {
        _musicActive = false;
        _musicLevel = null;
        _safe(music.pause());
      }
      return;
    }
    final level = base * (_speaking ? duckFactor : 1);
    if (!_musicActive || _musicTrack != track) {
      _musicActive = true;
      _musicTrack = track;
      _musicLevel = level;
      _safe(music.play(track, volume: level));
    } else if (_musicLevel != level) {
      _musicLevel = level;
      _safe(music.setVolume(level));
    }
  }

  void _safe(Future<void> f) => unawaited(f.catchError((Object _) {}));

  // ---------------------------------------------------------------- recursos
  /// Al salir de «Aprender jugando»: calla la voz y libera los efectos.
  Future<void> release() async {
    await stopVoice();
    try {
      await effects.release();
    } catch (_) {}
  }

  /// Al cerrar la app: libera todo.
  Future<void> dispose() async {
    await release();
    try {
      await music.release();
    } catch (_) {}
  }
}

/// Sin audio (pruebas). Registra lo que se pidió.
class RecordingSoundEffects implements SoundEffects {
  final played = <SoundCue>[];
  final variants = <int>[];
  final volumes = <double>[];
  int releases = 0;

  @override
  Future<void> play(SoundCue cue, {int variant = 0, double volume = 1}) async {
    played.add(cue);
    variants.add(variant);
    volumes.add(volume);
  }

  @override
  Future<void> release() async => releases++;
}

class RecordingNarrator implements Narrator {
  RecordingNarrator({this.info = const VoiceInfo(available: true, description: 'Voz de prueba')});

  final VoiceInfo info;
  final spoken = <String>[];
  final volumes = <double>[];
  int stops = 0;

  /// Si no es `null`, [speak] espera a que se complete (para simular frases largas).
  Completer<void>? pending;

  @override
  Future<void> speak(String text) async {
    spoken.add(text);
    final p = pending;
    if (p != null) await p.future;
  }

  @override
  Future<void> stop() async => stops++;

  @override
  Future<void> setVolume(double volume) async => volumes.add(volume);

  @override
  Future<VoiceInfo> voice() async => info;
}

class RecordingMusic implements MusicPlayer {
  /// Pista que suena ahora (`null` si está en pausa).
  MusicTrack? playing;
  double volume = 0;
  final events = <String>[];
  int releases = 0;

  @override
  Future<void> play(MusicTrack track, {required double volume}) async {
    playing = track;
    this.volume = volume;
    events.add('play ${track.name} ${volume.toStringAsFixed(2)}');
  }

  @override
  Future<void> setVolume(double volume) async {
    this.volume = volume;
    events.add('volume ${volume.toStringAsFixed(2)}');
  }

  @override
  Future<void> pause() async {
    playing = null;
    events.add('pause');
  }

  @override
  Future<void> release() async => releases++;
}
