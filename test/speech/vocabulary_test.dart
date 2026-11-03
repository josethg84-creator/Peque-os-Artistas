import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/speech/speech_content.dart';
import 'package:pequenos_artistas/speech/word_games.dart';

import 'content_fixture.dart';

void main() {
  late SpeechContent content;
  setUpAll(() async => content = await fullContent());
  final raw = jsonDecode(File(SpeechContent.vocabularyAsset).readAsStringSync()) as Map<String, dynamic>;
  final rawWords = (raw['words'] as List).cast<Map<String, dynamic>>();
  final old = jsonDecode(File(SpeechContent.wordsAsset).readAsStringSync()) as Map<String, dynamic>;
  final oldIds = {
    for (final c in (old['categories'] as List)) ...[for (final w in (c['words'] as List)) w['id'] as String],
  };

  test('al menos 200 palabras nuevas, sin repetir las existentes', () {
    expect(rawWords.length, greaterThanOrEqualTo(200));
    final ids = rawWords.map((w) => w['id']).toSet();
    expect(ids, hasLength(rawWords.length));
    expect(ids.intersection(oldIds), isEmpty);
    expect(content.words.map((w) => w.id).toSet(), hasLength(content.words.length));
    expect(content.words.length, oldIds.length + rawWords.length, reason: 'ninguna se descarta');
  });

  test('cada palabra tiene id, texto, categoría, ilustración, pronunciación, ejemplo y nivel', () {
    final cats = {for (final c in content.categories) c.id};
    for (final w in rawWords) {
      expect(cats, contains(w['category']), reason: w['id'] as String);
      final word = SpeechWord.fromJson(w)!;
      expect(word.pronunciation, isNotNull, reason: word.id);
      expect(word.pronunciation!.replaceAll('-', ''), word.text.toLowerCase());
      expect(word.example, isNotNull);
      expect(word.example!.toLowerCase(), contains(word.text.toLowerCase()), reason: word.id);
      expect(word.example, matches(RegExp(r'^[A-ZÁÉÍÓÚÑ¡¿].*[.!?]$')), reason: word.id);
      expect(word.level, inInclusiveRange(1, 3));
    }
  });

  test('los diez temas pedidos, con los grupos nuevos', () {
    final names = content.categories.map((c) => c.id).toList();
    for (final t in [
      'animales',
      'hogar',
      'escuela',
      'transporte',
      'alimentos',
      'familia',
      'naturaleza',
      'emociones',
      'acciones',
      'objetos',
    ]) {
      expect(names, contains(t));
      expect(
        content.categories.firstWhere((c) => c.id == t).words.length,
        greaterThanOrEqualTo(20),
        reason: t,
      );
    }
    expect(SpeechIcons.lookup('directions_bus'), isNotNull);
  });

  test('sílabas: mamá, pelota y mariposa como en el ejemplo', () {
    SpeechWord w(String id) => content.words.firstWhere((x) => x.id == id);
    expect(w('mama').syllables, ['ma', 'má']);
    expect(w('pelota').syllables, ['pe', 'lo', 'ta']);
    expect(w('mariposa').syllables, ['ma', 'ri', 'po', 'sa']);
    expect(w('estrella_mar').syllables, ['es', 'tre', 'lla', 'de', 'mar']);
    // Una pronunciación que no corresponde a la palabra se descarta.
    expect(
      SpeechWord.fromJson({
        'id': 'x',
        'text': 'sol',
        'pronunciation': 'lu-na',
        'picture': {'icon': 'sun'},
      })!.pronunciation,
      isNull,
    );
  });

  test('palmas: las palabras de cada nivel tienen las sílabas que tocan', () {
    for (final level in [1, 2, 3]) {
      final words = clapWords(content, Random(1), level: level);
      expect(words, hasLength(6));
      for (final w in words) {
        final n = w.syllables.length;
        expect(level == 1 ? n <= 2 : (level == 2 ? n == 3 : n >= 4), isTrue, reason: '${w.text} $n');
      }
    }
  });

  group('juegos', () {
    for (final game in WordGame.values) {
      test('${game.title}: preguntas válidas y repetibles', () {
        final a = buildWordGame(game, content, Random(7), level: 2);
        final b = buildWordGame(game, content, Random(7), level: 2);
        expect(a, hasLength(6));
        expect(a.map((q) => q.speech), b.map((q) => q.speech));
        for (final q in a) {
          expect(q.answer, inInclusiveRange(0, q.options.length - 1));
          expect(q.options.map((o) => o.label).toSet(), hasLength(q.options.length), reason: q.speech);
          expect(q.options.every((o) => o.picture != null), isTrue);
        }
      });
    }

    test('completar la frase: el hueco va donde estaba la palabra', () {
      final jirafa = content.words.firstWhere((w) => w.id == 'jirafa');
      expect(blankOut(jirafa), 'La ___ tiene el cuello muy largo.');
      for (final q in buildWordGame(WordGame.frase, content, Random(3), level: 1)) {
        expect(q.prompt, contains('___'));
        expect(
          q.afterCorrect!.replaceFirst(q.options[q.answer].label, '___').toLowerCase(),
          q.prompt!.toLowerCase(),
        );
      }
    });

    test('sonidos: «¿Qué palabra empieza como mamá?» y las rimas', () {
      final byId = {for (final w in content.words) w.id: w};
      for (final s in content.phonology.starts) {
        final t = byId[s.target]!, a = byId[s.answer]!;
        String plain(String x) => x
            .replaceAll('á', 'a')
            .replaceAll('é', 'e')
            .replaceAll('í', 'i')
            .replaceAll('ó', 'o')
            .replaceAll('ú', 'u')
            .substring(0, 2);
        expect(plain(a.syllables.first), plain(t.syllables.first), reason: '${t.text} ${a.text}');
        for (final o in s.others) {
          expect(byId[o]!.text.substring(0, 2), isNot(t.text.substring(0, 2)), reason: o);
        }
      }
      for (final s in content.phonology.rhymes) {
        String end(String t) => t.substring(t.length - 2);
        expect(end(byId[s.answer]!.text), end(byId[s.target]!.text), reason: s.answer);
      }
      final q = buildWordGame(WordGame.empieza, content, Random(1), count: 20);
      expect(q.map((x) => x.instruction), contains('¿Qué palabra empieza como mamá?'));
      final r = buildWordGame(WordGame.rimas, content, Random(1), count: 20);
      final gato = r.firstWhere((x) => x.instruction == '¿Qué palabra rima con gato?');
      expect(gato.options[gato.answer].label, 'pato');
      expect(gato.speech, contains('Escucha:'));
    });

    test('«Escucho y encuentro» no muestra el nombre: hay que oírlo', () {
      for (final q in buildWordGame(WordGame.encuentro, content, Random(2))) {
        expect(q.options.every((o) => !o.showLabel), isTrue);
        expect(q.speech, startsWith('Escucha y encuentra: '));
      }
    });
  });
}
