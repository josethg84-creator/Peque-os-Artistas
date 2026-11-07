import 'dart:async';

import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/web_speech.dart';

/// Imita a Chrome: cancelar avisa «interrupted» un instante después, una frase
/// dura 1 s y la voz en línea puede fallar con «network».
class ChromeLikeEngine implements SpeechEngine {
  ChromeLikeEngine({List<EngineVoice>? voices, this.failVoice})
    : _voices = voices ?? [google, local, english];

  static const google = EngineVoice(name: 'Google español', lang: 'es-ES');
  static const local = EngineVoice(name: 'Microsoft Pablo', lang: 'es-ES', local: true);
  static const english = EngineVoice(name: 'Google US English', lang: 'en-US');

  List<EngineVoice> _voices;
  set voicesNow(List<EngineVoice> v) => _voices = v;
  final String? failVoice;
  final spoken = <String>[];
  final usedVoices = <String>[];
  final rates = <double>[];
  int keepAlives = 0;
  ({String text, void Function(String?) onDone, Timer timer})? _current;

  @override
  List<EngineVoice> voices() => _voices;

  @override
  void speak(
    String text, {
    required EngineVoice voice,
    required double rate,
    required double pitch,
    required double volume,
    required void Function(String? error) onDone,
  }) {
    usedVoices.add(voice.name);
    if (voice.name == failVoice) {
      scheduleMicrotask(() => onDone('network'));
      return;
    }
    spoken.add(text);
    rates.add(rate);
    final t = Timer(const Duration(seconds: 1), () {
      _current = null;
      onDone(null);
    });
    _current = (text: text, onDone: onDone, timer: t);
  }

  @override
  void cancel() {
    final c = _current;
    _current = null;
    if (c == null) return;
    c.timer.cancel();
    Timer(Duration.zero, () => c.onDone('interrupted')); // avisa tarde, como Chrome
  }

  @override
  bool get speaking => _current != null;

  @override
  void keepAlive() => keepAlives++;
}

void main() {
  test('cortar una frase para decir otra: se dicen todas (antes se perdía una de cada dos)', () {
    fakeAsync((async) {
      final engine = ChromeLikeEngine();
      final n = WebSpeechNarrator(engine);
      var done = 0;
      for (var i = 0; i < 4; i++) {
        n.speak('frase $i').then((_) => done++);
        async.elapse(const Duration(milliseconds: 300));
      }
      async.elapse(const Duration(seconds: 3));
      expect(engine.spoken, ['frase 0', 'frase 1', 'frase 2', 'frase 3']);
      expect(done, 4, reason: 'ninguna espera se queda colgada');
    });
  });

  test('elige la mejor voz en español y no una inglesa', () {
    fakeAsync((async) {
      final engine = ChromeLikeEngine();
      final n = WebSpeechNarrator(engine);
      n.speak('hola');
      async.elapse(const Duration(seconds: 2));
      expect(engine.usedVoices, ['Google español']);
    });
  });

  test('si la voz en línea falla (sin conexión), se repite con otra voz en español', () {
    fakeAsync((async) {
      final engine = ChromeLikeEngine(failVoice: 'Google español');
      final n = WebSpeechNarrator(engine);
      var finished = false;
      n.speak('perro').then((_) => finished = true);
      async.elapse(const Duration(seconds: 2));
      expect(engine.spoken, ['perro']);
      expect(engine.usedVoices, ['Google español', 'Microsoft Pablo']);
      expect(finished, isTrue);
      // Las siguientes frases ya van con la voz que funciona.
      n.speak('gato');
      async.elapse(const Duration(seconds: 2));
      expect(engine.usedVoices.last, 'Microsoft Pablo');
    });
  });

  test('las voces llegan tarde: se esperan; si no hay voz en español, se explica', () {
    fakeAsync((async) {
      final engine = ChromeLikeEngine(voices: []);
      final n = WebSpeechNarrator(engine);
      bool? available;
      n.voice().then((v) => available = v.available);
      async.elapse(const Duration(milliseconds: 500));
      engine.voicesNow = [ChromeLikeEngine.local];
      async.elapse(const Duration(seconds: 1));
      expect(available, isTrue);

      final none = WebSpeechNarrator(ChromeLikeEngine(voices: [ChromeLikeEngine.english]));
      String? why;
      none.voice().then((v) => why = v.available ? null : v.description);
      async.elapse(const Duration(seconds: 4));
      expect(why, contains('no tiene una voz en español'));
    });
  });

  test('«Despacio», parar y la espera de seguridad', () {
    fakeAsync((async) {
      final engine = ChromeLikeEngine();
      final n = WebSpeechNarrator(engine);
      n.speak('perro', slow: true);
      async.elapse(const Duration(seconds: 2));
      expect(engine.rates.single, lessThan(WebSpeechNarrator.rate));

      var stopped = false;
      n.speak('una frase larga').then((_) => stopped = true);
      async.elapse(const Duration(milliseconds: 200));
      n.stop();
      async.flushMicrotasks();
      expect(stopped, isTrue);
      expect(engine.speaking, isFalse);
    });
  });

  test('frases largas con voz en línea: se mantiene viva (truco de Chrome)', () {
    fakeAsync((async) {
      final engine = _SilentEngine();
      final n = WebSpeechNarrator(engine);
      var done = false;
      n.speak('x' * 120).then((_) => done = true);
      async.elapse(const Duration(seconds: 25));
      expect(engine.keepAlives, greaterThan(0));
      expect(done, isTrue, reason: 'aunque el navegador no avise nunca, la espera termina');
    });
  });
}

/// Un navegador que nunca avisa del final.
class _SilentEngine extends ChromeLikeEngine {
  @override
  void speak(
    String text, {
    required EngineVoice voice,
    required double rate,
    required double pitch,
    required double volume,
    required void Function(String? error) onDone,
  }) {
    spoken.add(text);
  }

  @override
  bool get speaking => true;
}
