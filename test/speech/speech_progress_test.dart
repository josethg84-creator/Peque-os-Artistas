import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/speech/speech_progress.dart';

void main() {
  test('el progreso se guarda y se recupera tal cual', () async {
    final backend = MemoryBackend();
    var now = DateTime(2026, 11, 3, 10);
    final c = SpeechController(SpeechStore(backend), clock: () => now);
    await c.load();
    c
      ..markWordHeard('perro')
      ..markWordHeard('perro')
      ..markWordHeard('gato')
      ..markPhraseHeard('quiero_agua')
      ..markPhraseOrdered('quiero_agua');
    now = DateTime(2026, 11, 5, 18);
    c.markWordHeard('vaca');
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);

    final again = SpeechController(SpeechStore(backend), clock: () => now);
    await again.load();
    expect(again.progress.wordsHeard, {'perro', 'gato', 'vaca'});
    expect(again.progress.phrasesHeard, {'quiero_agua'});
    expect(again.progress.phrasesOrdered, {'quiero_agua'});
    expect(again.progress.practiceDays, {'2026-11-03', '2026-11-05'});
    expect(again.daysPracticedThisWeek(), 2);
    now = DateTime(2026, 11, 12);
    expect(again.daysPracticedThisWeek(), 0);
  });

  test('si el guardado principal se daña, se usa la copia de seguridad', () async {
    final backend = MemoryBackend();
    final c = SpeechController(SpeechStore(backend));
    await c.load();
    c.markWordHeard('perro');
    await Future<void>.delayed(Duration.zero);
    c.markWordHeard('gato');
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);
    backend.data[SpeechStore.key] = '{"format_version":1,"words_heard":["perro"';
    final again = SpeechController(SpeechStore(backend));
    await again.load();
    expect(again.progress.wordsHeard, contains('perro'));
    // Un dato alterado no pasa la suma de verificación.
    expect(SpeechStore.decode(SpeechStore.encode(again.progress).replaceAll('perro', 'pato')), isNull);
  });

  test('sin almacenamiento se puede practicar igual', () async {
    final backend = MemoryBackend()
      ..failReads = true
      ..failWrites = true;
    final c = SpeechController(SpeechStore(backend));
    await c.load();
    c.markWordHeard('perro');
    await Future<void>.delayed(Duration.zero);
    expect(c.progress.wordsHeard, {'perro'});
    expect(c.saveFailed, isTrue);
  });
}
