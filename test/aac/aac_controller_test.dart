import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/aac/aac_controller.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';

void main() {
  test('los ajustes y favoritas se guardan solo en el dispositivo y se recuperan', () async {
    final backend = MemoryBackend();
    final a = AacController(AacStore(backend));
    await a.load();
    a
      ..update((p) {
        p.tileSize = AacTileSize.large;
        p.columns = 3;
        p.order = AacOrder.frequent;
        p.highContrast = true;
        p.textScale = 1.5;
        p.confirmBeforeSpeak = true;
        p.tapGuardMs = 500;
        p.feminine = true;
        p.slowVoice = true;
        p.quickExtras.add('te_quiero');
        p.frequentCategories.add('comida');
      })
      ..addFavorite('Yo quiero agua.')
      ..markUsed('agua');
    await Future<void>.delayed(Duration.zero);
    final b = AacController(AacStore(backend));
    await b.load();
    expect(b.prefs.toJson(), a.prefs.toJson());
    expect(b.prefs.favorites, ['Yo quiero agua.']);
    expect(b.prefs.usage, {'agua': 1});
    expect(await backend.keys(), contains(AacStore.key));
  });

  test('favoritas sin repetir; borrar la personalización lo deja todo como al principio', () async {
    final backend = MemoryBackend();
    final a = AacController(AacStore(backend));
    await a.load();
    a
      ..addFavorite('Estoy feliz.')
      ..addFavorite('Estoy feliz.')
      ..addFavorite('Necesito ayuda.');
    expect(a.prefs.favorites, ['Necesito ayuda.', 'Estoy feliz.']);
    a.removeFavorite('Estoy feliz.');
    expect(a.isFavorite('Estoy feliz.'), isFalse);
    a.message.value = 'Hola.';
    await a.clearAll();
    expect(a.prefs.favorites, isEmpty);
    expect(a.message.value, isNull);
    expect(await backend.read(AacStore.key), isNull);
  });

  test('datos dañados: se usa la copia de seguridad o los valores por defecto', () async {
    final backend = MemoryBackend();
    await backend.write(AacStore.key, '{roto');
    final a = AacController(AacStore(backend));
    await a.load();
    expect(a.prefs.tileSize, AacTileSize.medium);
    expect(a.prefs.speakOnTap, isTrue);
    final odd = AacPreferences.fromJson({'columns': 99, 'text_scale': 7, 'tap_guard_ms': 3});
    expect((odd.columns, odd.textScale, odd.tapGuardMs), (0, 1.0, 0));
  });

  test('evitar toques sin querer: ignora el segundo toque demasiado rápido', () async {
    var now = DateTime(2026, 11, 4, 10);
    final a = AacController(AacStore(MemoryBackend()), clock: () => now);
    await a.load();
    expect(a.acceptTap(), isTrue);
    expect(a.acceptTap(), isTrue, reason: 'sin el ajuste, todo toque vale');
    a.update((p) => p.tapGuardMs = 1000);
    now = now.add(const Duration(seconds: 2));
    expect(a.acceptTap(), isTrue);
    now = now.add(const Duration(milliseconds: 300));
    expect(a.acceptTap(), isFalse);
    now = now.add(const Duration(milliseconds: 1200));
    expect(a.acceptTap(), isTrue);
  });
}
