import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';

/// Voz del dispositivo con el canal de `flutter_tts` simulado (como en un
/// Android): qué voz se elige, cuándo se habla y que un «no hay voz» no sea
/// definitivo (en la web las voces llegan un momento después de abrir).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('flutter_tts');
  late List<MethodCall> calls;
  late List<Map<String, String>> voices;

  setUp(() {
    calls = [];
    voices = [];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel, (
      call,
    ) async {
      calls.add(call);
      return switch (call.method) {
        'getVoices' => voices,
        'isLanguageInstalled' || 'isLanguageAvailable' => false,
        _ => 1,
      };
    });
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel, null);
  });

  List<String> spoken() => [
    for (final c in calls)
      if (c.method == 'speak') c.arguments as String,
  ];

  test('sin voz no habla, pero lo vuelve a intentar y habla cuando aparece', () async {
    var now = DateTime(2026, 1, 1);
    final narrator = DeviceTtsNarrator(clock: () => now);

    await narrator.speak('¿Dónde está el círculo?');
    expect(spoken(), isEmpty);
    expect((await narrator.voice()).available, isFalse);

    // Llegan las voces (el navegador terminó de cargarlas, o se instaló una).
    voices = [
      {'name': 'es-es-red', 'locale': 'es-ES', 'network_required': '1', 'features': ''},
      {'name': 'es-us-local', 'locale': 'es-US', 'network_required': '0', 'features': ''},
    ];
    now = now.add(DeviceTtsNarrator.retryAfter);
    await narrator.speak('¿Dónde está el círculo?');
    expect(spoken(), ['¿Dónde está el círculo?']);
    final voice = calls.lastWhere((c) => c.method == 'setVoice').arguments as Map;
    expect(voice['name'], 'es-us-local', reason: 'la voz que necesita Internet se descarta');
    expect((await narrator.voice()).description, contains('sin conexión'));

    // Una vez encontrada, no se vuelve a buscar.
    final searches = calls.where((c) => c.method == 'getVoices').length;
    await narrator.speak('¿Dónde está el triángulo?');
    expect(calls.where((c) => c.method == 'getVoices').length, searches);
    expect(spoken(), hasLength(2));
  });

  test('solo hay voces que necesitan Internet o sin instalar: no habla', () async {
    voices = [
      {'name': 'red', 'locale': 'es-US', 'network_required': '1', 'features': ''},
      {'name': 'sin-instalar', 'locale': 'es-MX', 'network_required': '0', 'features': 'notInstalled'},
    ];
    final narrator = DeviceTtsNarrator();
    await narrator.speak('Hola');
    expect(spoken(), isEmpty);
    expect((await narrator.voice()).available, isFalse);
  });
}
