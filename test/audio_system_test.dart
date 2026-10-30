import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';
import 'package:pequenos_artistas/audio/phrases.dart';
import 'package:pequenos_artistas/coloring/coloring_canvas.dart';
import 'package:pequenos_artistas/coloring/engine/svg_drawing_parser.dart';
import 'package:pequenos_artistas/coloring/engine/vector_drawing.dart';
import 'package:pequenos_artistas/learning/learning_progress.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';
import 'package:pequenos_artistas/screens/sound_settings_screen.dart';

import 'test_helpers.dart';

/// Sistema de sonido: efectos, música por pantalla, voz, preferencias y ciclo
/// de vida de la app.
class _Rig {
  _Rig({LearningSettings settings = const LearningSettings(), bool ready = true}) {
    _settings = settings;
    _ready = ready;
    audio = LearningAudio(
      effects: effects,
      narrator: narrator,
      music: music,
      settings: () => _settings,
      settingsReady: () => _ready,
      clock: () => now,
      random: Random(1),
    );
  }

  late LearningSettings _settings;
  late bool _ready;
  DateTime now = DateTime(2026, 1, 1);
  final effects = RecordingSoundEffects();
  final narrator = RecordingNarrator();
  final music = RecordingMusic();
  late final LearningAudio audio;

  set settings(LearningSettings s) {
    _settings = s;
    audio.refresh();
  }

  LearningSettings get settings => _settings;

  void tick([Duration d = const Duration(seconds: 1)]) => now = now.add(d);
}

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

VectorDrawing platano() =>
    parseColoringSvg(File('assets/drawings/fruits/fruta_platano.svg').readAsStringSync());

void main() {
  group('recursos de audio', () {
    test('existen todos los efectos y las dos músicas, y son breves y ligeros', () {
      for (final cue in SoundCue.values) {
        for (var v = 0; v < cue.files.length; v++) {
          final file = File('assets/${cue.asset(v)}');
          expect(file.existsSync(), isTrue, reason: file.path);
          final bytes = file.readAsBytesSync();
          expect(String.fromCharCodes(bytes.sublist(0, 4)), 'RIFF', reason: file.path);
          // WAV mono 16 bits a 22 050 Hz: duración = datos / 44 100.
          final seconds = (bytes.length - 44) / 44100;
          expect(seconds, lessThan(2), reason: '${file.path}: efecto breve');
        }
      }
      for (final track in MusicTrack.values) {
        final file = File('assets/${track.asset}');
        expect(file.existsSync(), isTrue, reason: file.path);
        expect(String.fromCharCodes(file.readAsBytesSync().sublist(0, 4)), 'OggS');
        expect(file.lengthSync(), lessThan(400 * 1024), reason: 'optimizado para móvil');
      }
    });
  });

  group('efectos', () {
    test('el volumen es general × efectos; el silencio o el interruptor los callan', () async {
      final rig = _Rig(settings: const LearningSettings(masterVolume: 0.5, effectsVolume: 0.8));
      await rig.audio.play(SoundCue.tap);
      expect(rig.effects.volumes.single, closeTo(0.4, 1e-9));

      rig.settings = rig.settings.copyWith(muted: true);
      rig.tick();
      await rig.audio.play(SoundCue.tap);
      rig.settings = rig.settings.copyWith(muted: false, soundOn: false);
      rig.tick();
      await rig.audio.play(SoundCue.tap);
      rig.settings = rig.settings.copyWith(soundOn: true, effectsVolume: 0);
      rig.tick();
      await rig.audio.play(SoundCue.tap);
      expect(rig.effects.played, hasLength(1));
    });

    test('dos toques muy rápidos suenan una vez; con algo de pausa, dos', () async {
      final rig = _Rig();
      await rig.audio.play(SoundCue.pop);
      rig.tick(const Duration(milliseconds: 40));
      await rig.audio.play(SoundCue.pop);
      expect(rig.effects.played, hasLength(1));
      rig.tick(const Duration(milliseconds: 200));
      await rig.audio.play(SoundCue.pop);
      expect(rig.effects.played, hasLength(2));
    });

    test('las variantes no se repiten seguidas y cada color tiene su nota', () async {
      final rig = _Rig();
      for (var i = 0; i < 30; i++) {
        await rig.audio.play(SoundCue.pop);
        rig.tick();
      }
      for (var i = 1; i < rig.effects.variants.length; i++) {
        expect(rig.effects.variants[i], isNot(rig.effects.variants[i - 1]));
      }
      expect(rig.effects.variants.toSet(), hasLength(SoundCue.pop.files.length));

      await rig.audio.play(SoundCue.color, variant: 3);
      expect(rig.effects.variants.last, 3);
      expect(SoundCue.color.asset(3), 'audio/effects/color_4.wav');
    });
  });

  group('voz', () {
    test('una frase de ambiente no interrumpe otra narración; la de cola espera', () async {
      final rig = _Rig();
      final pending = rig.narrator.pending = Completer<void>();
      final first = rig.audio.say('Busca las parejas iguales');
      expect(rig.audio.isSpeaking, isTrue);
      await rig.audio.say('¡Sigue coloreando!', mode: VoiceMode.ambient); // descartada
      unawaited(rig.audio.say(Phrases.newSticker, mode: VoiceMode.queue)); // espera
      expect(rig.narrator.spoken, ['Busca las parejas iguales']);
      rig.narrator.pending = null;
      pending.complete();
      await first;
      expect(rig.narrator.spoken, ['Busca las parejas iguales', Phrases.newSticker]);
      expect(rig.audio.isSpeaking, isFalse);
    });

    test('los comentarios de ambiente no se repiten constantemente', () async {
      final rig = _Rig();
      await rig.audio.say('¡Qué bonito está quedando!', mode: VoiceMode.ambient);
      rig.tick(const Duration(seconds: 5));
      await rig.audio.say('¡Sigue coloreando!', mode: VoiceMode.ambient); // demasiado pronto
      rig.tick(LearningAudio.ambientCooldown);
      await rig.audio.say('¡Sigue coloreando!', mode: VoiceMode.ambient);
      expect(rig.narrator.spoken, ['¡Qué bonito está quedando!', '¡Sigue coloreando!']);
    });

    test('«sayOneOf» no repite la última frase de la lista', () async {
      final rig = _Rig();
      for (var i = 0; i < 12; i++) {
        await rig.audio.sayOneOf(Phrases.welcome);
      }
      for (var i = 1; i < rig.narrator.spoken.length; i++) {
        expect(rig.narrator.spoken[i], isNot(rig.narrator.spoken[i - 1]));
      }
    });

    test('voz desactivada, silencio total o volumen cero: no habla; el volumen se aplica', () async {
      final rig = _Rig(settings: const LearningSettings(masterVolume: 0.5, voiceVolume: 0.6));
      await rig.audio.say('Hola');
      expect(rig.narrator.volumes.single, closeTo(0.3, 1e-9));
      rig.settings = rig.settings.copyWith(voiceOn: false);
      await rig.audio.say('Uno');
      rig.settings = rig.settings.copyWith(voiceOn: true, muted: true);
      await rig.audio.say('Dos');
      rig.settings = rig.settings.copyWith(muted: false, voiceVolume: 0);
      await rig.audio.say('Tres');
      expect(rig.narrator.spoken, ['Hola']);
    });
  });

  group('música', () {
    test('la pantalla visible decide: menús, colorear y silencio en los juegos', () async {
      final rig = _Rig();
      final home = rig.audio.enterMusicZone(MusicTrack.main);
      expect(rig.music.playing, MusicTrack.main);
      final categories = rig.audio.enterMusicZone(MusicTrack.main);
      expect(rig.music.events.where((e) => e.startsWith('play')), hasLength(1), reason: 'no se reinicia');
      final game = rig.audio.enterMusicZone(null);
      expect(rig.music.playing, isNull);
      rig.audio.exitMusicZone(game);
      expect(rig.music.playing, MusicTrack.main);
      final coloring = rig.audio.enterMusicZone(MusicTrack.coloring);
      expect(rig.music.playing, MusicTrack.coloring);
      rig.audio.exitMusicZone(coloring);
      rig.audio.exitMusicZone(categories);
      expect(rig.music.playing, MusicTrack.main);
      rig.audio.exitMusicZone(home);
      expect(rig.music.playing, isNull);
    });

    test('se apaga, se silencia y se ajusta según las preferencias', () async {
      final rig = _Rig(settings: const LearningSettings(masterVolume: 0.8, musicVolume: 0.5));
      rig.audio.enterMusicZone(MusicTrack.main);
      expect(rig.music.volume, closeTo(0.4, 1e-9));
      rig.settings = rig.settings.copyWith(musicVolume: 0.25);
      expect(rig.music.volume, closeTo(0.2, 1e-9));
      rig.settings = rig.settings.copyWith(musicOn: false);
      expect(rig.music.playing, isNull);
      rig.settings = rig.settings.copyWith(musicOn: true, muted: true);
      expect(rig.music.playing, isNull);
      rig.settings = rig.settings.copyWith(muted: false);
      expect(rig.music.playing, MusicTrack.main);
    });

    test('baja mientras habla la voz y vuelve después', () async {
      final rig = _Rig(settings: const LearningSettings(musicVolume: 0.5));
      rig.audio.enterMusicZone(MusicTrack.main);
      final pending = rig.narrator.pending = Completer<void>();
      final speaking = rig.audio.say('¡Hola, pequeño artista!');
      expect(rig.music.volume, closeTo(0.5 * LearningAudio.duckFactor, 1e-9));
      pending.complete();
      await speaking;
      expect(rig.music.volume, closeTo(0.5, 1e-9));
    });

    test('en segundo plano se pausa y calla la voz; al volver continúa', () async {
      final rig = _Rig();
      rig.audio.enterMusicZone(MusicTrack.main);
      rig.audio.setForeground(false);
      expect(rig.music.playing, isNull);
      expect(rig.narrator.stops, 1);
      rig.audio.setForeground(true);
      expect(rig.music.playing, MusicTrack.main);
    });

    test('no empieza hasta conocer las preferencias guardadas', () async {
      final rig = _Rig(ready: false);
      rig.audio.enterMusicZone(MusicTrack.main);
      expect(rig.music.events, isEmpty);
      rig._ready = true;
      rig.audio.refresh();
      expect(rig.music.playing, MusicTrack.main);
    });

    test('al cerrar la app se liberan los reproductores', () async {
      final rig = _Rig();
      await rig.audio.dispose();
      expect(rig.music.releases, 1);
      expect(rig.effects.releases, 1);
    });
  });

  group('preferencias guardadas', () {
    test('datos antiguos o dañados toman valores por defecto', () {
      final old = LearningSettings.fromJson({'sound_on': false, 'voice_on': true, 'level': 'advanced'});
      expect(old.soundOn, isFalse);
      expect(old.musicOn, isTrue);
      expect(old.musicVolume, const LearningSettings().musicVolume);
      final bad = LearningSettings.fromJson({'music_volume': 'alto', 'master_volume': 7, 'muted': 'sí'});
      expect(bad.musicVolume, const LearningSettings().musicVolume);
      expect(bad.masterVolume, 1.0); // recortado a 0..1
      expect(bad.muted, isFalse);
      const custom = LearningSettings(muted: true, musicOn: false, masterVolume: 0.3, voiceVolume: 0.7);
      final round = LearningSettings.fromJson(custom.toJson());
      expect(round.toJson(), custom.toJson());
    });
  });

  group('en la app', () {
    testWidgets('música por pantalla: menús, colorear y silencio en los juegos', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      expect(lastMusic!.playing, MusicTrack.main);
      expect(lastNarrator!.spoken, isEmpty, reason: 'nada de voz automática al abrir');
      await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
      expect(lastSounds!.played.last, SoundCue.tap);
      await tapAndSettle(tester, find.bySemanticsLabel('Frutas, 5 dibujos'));
      expect(lastSounds!.played.last, SoundCue.category);
      expect(lastMusic!.events.where((e) => e.startsWith('play')), hasLength(1), reason: 'misma música');
      await tapAndSettle(tester, find.bySemanticsLabel('Plátano. Dificultad fácil'));
      expect(lastSounds!.played.last, SoundCue.open);
      expect(lastMusic!.playing, MusicTrack.coloring);
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
      expect(lastMusic!.playing, MusicTrack.main);
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a categorías'));
      await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
      await tapAndSettle(tester, find.bySemanticsLabel('Actividades'));
      expect(lastMusic!.playing, MusicTrack.main);
      await tapAndSettle(tester, find.bySemanticsLabel(RegExp('^Aprende los colores')));
      expect(lastMusic!.playing, isNull, reason: 'concentración');
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a los juegos'));
      expect(lastMusic!.playing, MusicTrack.main);
    });

    testWidgets('la app en segundo plano pausa la música y la recupera al volver', (tester) async {
      await pumpApp(tester);
      expect(lastMusic!.playing, MusicTrack.main);
      for (final s in [AppLifecycleState.inactive, AppLifecycleState.hidden, AppLifecycleState.paused]) {
        tester.binding.handleAppLifecycleStateChanged(s);
      }
      expect(lastMusic!.playing, isNull);
      for (final s in [AppLifecycleState.hidden, AppLifecycleState.inactive, AppLifecycleState.resumed]) {
        tester.binding.handleAppLifecycleStateChanged(s);
      }
      expect(lastMusic!.playing, MusicTrack.main);
    });

    testWidgets('tocar a los personajes del inicio saluda con voz (sin repetir la misma frase)', (
      tester,
    ) async {
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      for (var i = 0; i < 3; i++) {
        await tapAndSettle(tester, find.bySemanticsLabel('Un niño y una niña con pinceles y su perrito'));
      }
      expect(lastNarrator!.spoken, hasLength(3));
      expect(lastNarrator!.spoken.every(Phrases.welcome.contains), isTrue);
      expect(lastNarrator!.spoken[1], isNot(lastNarrator!.spoken[0]));
    });

    testWidgets('colorear: frase inicial, ánimo a la mitad y felicitación final', (tester) async {
      ColoringCanvas.resetSessionGreeting();
      setScreenSize(tester, const Size(420, 900));
      await pumpApp(tester);
      await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
      await tapAndSettle(tester, find.bySemanticsLabel('Frutas, 5 dibujos'));
      await tapAndSettle(tester, find.bySemanticsLabel('Plátano. Dificultad fácil'));
      expect(lastNarrator!.spoken, ['¡Elige tu color favorito!']);

      final d = platano();
      await tapAndSettle(tester, find.bySemanticsLabel('Amarillo'));
      expect(lastSounds!.played.last, SoundCue.color);
      expect(lastSounds!.variants.last, 2, reason: 'Amarillo es el tercer color');
      for (final r in ['platano', 'tallo']) {
        await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, r)));
        await tester.pumpAndSettle();
      }
      expect(lastNarrator!.spoken, hasLength(1), reason: 'el ánimo de ambiente no se repite enseguida');
      await tester.tapAt(screenPointOf(tester, d, interiorPoint(d, 'punta')));
      await tester.pumpAndSettle();
      expect(Phrases.drawingDone, contains(lastNarrator!.spoken.last));
    });

    testWidgets('«Sonido y música»: controles grandes y preferencias que se conservan', (tester) async {
      setScreenSize(tester, const Size(420, 900));
      final backend = MemoryBackend();
      await pumpApp(tester, learningBackend: backend);
      await tapAndSettle(tester, find.bySemanticsLabel('Configuración').first);
      expect(find.byType(SoundSettingsScreen), findsOneWidget);
      expect(find.text('Voz de prueba'), findsOneWidget); // estado real de la voz

      await tapAndSettle(tester, find.bySemanticsLabel('Música: activado'));
      expect(lastMusic!.playing, isNull);
      // Volumen de efectos: se arrastra el control hasta el mínimo.
      final effects = find.byType(Slider).at(2);
      await tester.ensureVisible(effects);
      await tester.drag(effects, const Offset(-400, 0));
      await tester.pumpAndSettle();

      // Cerrar y abrir la app con el mismo almacenamiento.
      await tester.pumpWidget(const SizedBox());
      await pumpApp(tester, learningBackend: backend);
      expect(lastMusic!.playing, isNull, reason: 'la música sigue apagada');
      await tapAndSettle(tester, find.bySemanticsLabel('Configuración').first);
      expect(find.bySemanticsLabel('Música: desactivado'), findsOneWidget);
      final slider = tester.widget<Slider>(find.byType(Slider).at(2));
      expect(slider.value, 0);
      // Con los efectos a cero, tocar botones no suena.
      lastSounds!.played.clear();
      await tapAndSettle(tester, find.bySemanticsLabel('Volver'));
      expect(lastSounds!.played, isEmpty);
    });
  });
}
