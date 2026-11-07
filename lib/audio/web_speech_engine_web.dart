import 'dart:js_interop';

import 'package:web/web.dart' as web;

import 'web_speech.dart';

SpeechEngine? createBrowserSpeechEngine() {
  try {
    return _BrowserSpeechEngine(web.window.speechSynthesis);
  } catch (_) {
    return null; // navegador sin síntesis de voz
  }
}

class _BrowserSpeechEngine implements SpeechEngine {
  _BrowserSpeechEngine(this._synth) {
    // Algunos navegadores solo cargan las voces cuando alguien las pide.
    _synth.getVoices();
  }

  final web.SpeechSynthesis _synth;

  /// Chrome puede liberar una frase que nadie sujeta y no avisar al terminar.
  final _alive = <web.SpeechSynthesisUtterance>{};

  List<web.SpeechSynthesisVoice> _raw() => _synth.getVoices().toDart;

  @override
  List<EngineVoice> voices() => [
    for (final v in _raw()) EngineVoice(name: v.name, lang: v.lang, local: v.localService),
  ];

  @override
  void speak(
    String text, {
    required EngineVoice voice,
    required double rate,
    required double pitch,
    required double volume,
    required void Function(String? error) onDone,
  }) {
    final u = web.SpeechSynthesisUtterance(text)
      ..lang = voice.lang
      ..rate = rate
      ..pitch = pitch
      ..volume = volume;
    for (final v in _raw()) {
      if (v.name == voice.name && v.lang == voice.lang) {
        u.voice = v;
        break;
      }
    }
    var reported = false;
    void done(String? error) {
      _alive.remove(u);
      if (reported) return;
      reported = true;
      onDone(error);
    }

    u.onend = ((web.Event _) => done(null)).toJS;
    u.onerror = ((web.SpeechSynthesisErrorEvent e) => done(e.error)).toJS;
    _alive.add(u);
    try {
      _synth.speak(u);
    } catch (_) {
      done('synthesis-failed');
    }
  }

  @override
  void cancel() => _synth.cancel();

  @override
  bool get speaking => _synth.speaking || _synth.pending;

  @override
  void keepAlive() {
    _synth.pause();
    _synth.resume();
  }
}
