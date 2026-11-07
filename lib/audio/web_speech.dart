import 'dart:async';

import 'app_audio.dart';
import 'web_speech_engine_stub.dart' if (dart.library.js_interop) 'web_speech_engine_web.dart';

/// Una voz del navegador.
class EngineVoice {
  const EngineVoice({required this.name, required this.lang, this.local = false});
  final String name;
  final String lang;

  /// La voz funciona sin conexión (no es una voz «en línea»).
  final bool local;
}

/// Lo mínimo de `window.speechSynthesis` que necesita [WebSpeechNarrator].
/// Cada [speak] usa una frase NUEVA del navegador y avisa una sola vez con
/// [onDone] (`null` si terminó bien; si no, el error del navegador).
abstract interface class SpeechEngine {
  List<EngineVoice> voices();
  void speak(
    String text, {
    required EngineVoice voice,
    required double rate,
    required double pitch,
    required double volume,
    required void Function(String? error) onDone,
  });
  void cancel();
  bool get speaking;

  /// Truco para Chrome: pausar y seguir evita que corte las frases largas.
  void keepAlive();
}

/// El motor del navegador, o `null` fuera de la web.
SpeechEngine? browserSpeechEngine() => createBrowserSpeechEngine();

/// Voz de la versión web, hablando directamente con el navegador.
///
/// Sustituye a `flutter_tts` en la web, que reutiliza una sola frase: si se
/// cortaba una frase para decir otra (al pulsar «Escuchar» o al cambiar de
/// pregunta), el navegador aún no había avisado del corte, la nueva frase se
/// descartaba sin decirse y su espera no terminaba nunca. Aquí cada frase es
/// nueva, su espera siempre termina (bien, con error o por tiempo), y si una voz
/// en línea falla se prueba con otra voz en español.
class WebSpeechNarrator implements Narrator {
  WebSpeechNarrator(
    this._engine, {
    this.voicesWait = const Duration(seconds: 3),
    this.pauseAfterCancel = const Duration(milliseconds: 80),
    this.keepAliveEvery = const Duration(seconds: 10),
  });

  final SpeechEngine _engine;

  /// El navegador carga su lista de voces un momento después de abrir la página.
  final Duration voicesWait;

  /// Chrome a veces ignora una frase pedida justo después de cortar otra.
  final Duration pauseAfterCancel;
  final Duration keepAliveEvery;

  static const rate = 0.92;
  static const pitch = 1.0;

  /// Errores por los que se prueba otra voz (la voz en línea no responde, etc.).
  static const voiceErrors = {'network', 'synthesis-failed', 'synthesis-unavailable', 'voice-unavailable'};

  double _volume = 1;
  EngineVoice? _voice;
  final _badVoices = <String>{};
  Completer<void>? _current;
  int _turn = 0;
  Future<VoiceInfo>? _ready;

  /// Voces en español, de la mejor a la peor, sin las que ya fallaron.
  List<EngineVoice> _spanish() {
    final list = [
      for (final v in _engine.voices())
        if (v.lang.toLowerCase().replaceAll('_', '-').startsWith('es') && !_badVoices.contains(v.name)) v,
    ];
    final order = <EngineVoice>[];
    var rest = [...list];
    while (rest.isNotEmpty) {
      final best = DeviceTtsNarrator.chooseVoice([
        for (final v in rest) {'name': v.name, 'locale': v.lang},
      ])!;
      final pick = rest.firstWhere((v) => v.name == best['name']);
      order.add(pick);
      rest = [...rest]..remove(pick);
    }
    return order;
  }

  @override
  Future<VoiceInfo> voice() {
    final ready = _ready;
    if (ready != null) return ready;
    final pending = _ready = _findVoice();
    pending.then((info) {
      if (!info.available) _ready = null; // se vuelve a mirar la próxima vez
    });
    return pending;
  }

  Future<VoiceInfo> _findVoice() async {
    const step = Duration(milliseconds: 200);
    var waits = voicesWait.inMilliseconds ~/ step.inMilliseconds;
    var voices = _spanish();
    if (voices.isEmpty && _badVoices.isNotEmpty) {
      _badVoices.clear(); // todas fallaron alguna vez: se vuelve a probar con todas
      voices = _spanish();
    }
    while (voices.isEmpty && waits-- > 0) {
      await Future<void>.delayed(step);
      voices = _spanish();
    }
    if (voices.isEmpty) {
      return const VoiceInfo(
        available: false,
        description:
            'Este navegador no tiene una voz en español. Prueba con Chrome, Edge o Safari, '
            'o instala una voz en español en el sistema.',
      );
    }
    final v = _voice = voices.first;
    return VoiceInfo(
      available: true,
      description:
          'Voz del navegador en español: ${v.name} (${v.lang}).'
          '${v.local ? '' : ' Esta voz necesita conexión; si falla, se usa otra voz en español.'}',
    );
  }

  @override
  Future<void> speak(String text, {bool slow = false}) async {
    if (text.trim().isEmpty) return;
    if (!(await voice()).available) return;
    final turn = ++_turn;
    if (_current != null || _engine.speaking) {
      _finishCurrent();
      _engine.cancel();
      await Future<void>.delayed(pauseAfterCancel);
      if (turn != _turn) return; // otra frase la sustituyó mientras tanto
    }
    var tries = 0;
    while (true) {
      final voice = _voice;
      if (voice == null) return;
      final error = await _say(text, voice, slow ? rate * DeviceTtsNarrator.slowFactor : rate);
      if (turn != _turn || error == null || !voiceErrors.contains(error) || ++tries > 2) return;
      // La voz no funciona (por ejemplo, una voz en línea sin conexión): otra.
      _badVoices.add(voice.name);
      final others = _spanish();
      if (others.isEmpty) return;
      _voice = others.first;
      _ready = null;
    }
  }

  Future<String?> _say(String text, EngineVoice voice, double rate) {
    final done = _current = Completer<void>();
    String? error;
    Timer? alive;
    // Seguridad: la espera termina aunque el navegador no avise nunca.
    final limit = Timer(Duration(seconds: 4 + text.length ~/ 6), () {
      if (!done.isCompleted) done.complete();
    });
    if (!voice.local) {
      alive = Timer.periodic(keepAliveEvery, (_) {
        if (!done.isCompleted && _engine.speaking) _engine.keepAlive();
      });
    }
    _engine.speak(
      text,
      voice: voice,
      rate: rate,
      pitch: pitch,
      volume: _volume,
      onDone: (e) {
        error = e;
        if (!done.isCompleted) done.complete();
      },
    );
    return done.future
        .whenComplete(() {
          limit.cancel();
          alive?.cancel();
          if (identical(_current, done)) _current = null;
        })
        .then((_) => error);
  }

  void _finishCurrent() {
    final c = _current;
    _current = null;
    if (c != null && !c.isCompleted) c.complete();
  }

  @override
  Future<void> stop() async {
    _turn++;
    if (_current == null && !_engine.speaking) return;
    _finishCurrent();
    _engine.cancel();
  }

  @override
  Future<void> setVolume(double volume) async => _volume = volume;
}
