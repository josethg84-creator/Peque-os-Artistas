import '../speech/speech_content.dart';

/// ⚠️ DATOS DE DEMOSTRACIÓN (Fase 2 de «Aprendo a leer»).
///
/// Solo sirven para enseñar cómo se ven las pantallas. El contenido real
/// (10 familias, 100 palabras, 50 oraciones y 30 dictados, con la separación
/// silábica validada) llegará en las fases siguientes, en
/// `assets/reading/*.json`, generado y comprobado por `tools/reading/`.
/// Las pantallas muestran el distintivo «Demostración» mientras usen esto.
abstract final class ReadingDemo {
  static const families = [
    DemoFamily('M', [
      DemoSyllable('ma', DemoWord('mamá', ['ma', 'má'], {'icon': 'woman'})),
      DemoSyllable('me', DemoWord('mesa', ['me', 'sa'], {'icon': 'table'})),
      DemoSyllable('mi', DemoWord('micrófono', ['mi', 'cró', 'fo', 'no'], {'icon': 'mic'})),
      DemoSyllable('mo', DemoWord('mono', ['mo', 'no'], {'drawing': 'animal_mono'})),
      DemoSyllable('mu', DemoWord('música', ['mú', 'si', 'ca'], {'icon': 'music_note'})),
    ]),
    DemoFamily('P', [
      DemoSyllable('pa', DemoWord('pato', ['pa', 'to'], {'drawing': 'granja_patito'})),
      DemoSyllable('pe', DemoWord('perro', ['pe', 'rro'], {'drawing': 'animal_perro'})),
      DemoSyllable('pi', DemoWord('piña', ['pi', 'ña'], {'drawing': 'fruta_pina'})),
      DemoSyllable('po', DemoWord('poni', ['po', 'ni'], {'drawing': 'granja_poni'})),
      DemoSyllable('pu', DemoWord('pudín', ['pu', 'dín'], {'icon': 'cake'})),
    ]),
    DemoFamily('S', [
      DemoSyllable('sa', DemoWord('sala', ['sa', 'la'], {'icon': 'weekend'})),
      DemoSyllable('se', DemoWord('semilla', ['se', 'mi', 'lla'], {'icon': 'eco'})),
      DemoSyllable('si', DemoWord('silla', ['si', 'lla'], {'icon': 'chair'})),
      DemoSyllable('so', DemoWord('sopa', ['so', 'pa'], {'icon': 'soup_kitchen'})),
      DemoSyllable('su', DemoWord('suma', ['su', 'ma'], {'icon': 'add_circle'})),
    ]),
    DemoFamily('L', [
      DemoSyllable('la', DemoWord('lápiz', ['lá', 'piz'], {'icon': 'edit'})),
      DemoSyllable('le', DemoWord('león', ['le', 'ón'], {'drawing': 'animal_leon'})),
      DemoSyllable('li', DemoWord('libro', ['li', 'bro'], {'icon': 'menu_book'})),
      DemoSyllable('lo', DemoWord('loro', ['lo', 'ro'], {'lolo': true})),
      DemoSyllable('lu', DemoWord('luna', ['lu', 'na'], {'icon': 'moon'})),
    ]),
  ];

  /// «Completo palabras»: la palabra por sílabas, cuál falta y las opciones.
  static const words = [
    DemoCompleteWord(DemoWord('pato', ['pa', 'to'], {'drawing': 'granja_patito'}), 0, ['pa', 'ma', 'sa']),
    DemoCompleteWord(DemoWord('pelota', ['pe', 'lo', 'ta'], {'icon': 'ball'}), 0, ['me', 'pe', 'te']),
    DemoCompleteWord(DemoWord('mariposa', ['ma', 'ri', 'po', 'sa'], {'drawing': 'animal_mariposa'}), 2, [
      'po',
      'pa',
      'to',
      'mo',
    ]),
    DemoCompleteWord(DemoWord('manzana', ['man', 'za', 'na'], {'drawing': 'fruta_manzana'}), 0, [
      'pan',
      'man',
      'san',
    ]),
    DemoCompleteWord(DemoWord('elefante', ['e', 'le', 'fan', 'te'], {'drawing': 'animal_elefante'}), 2, [
      'fan',
      'ten',
      'ban',
    ]),
    DemoCompleteWord(DemoWord('mochila', ['mo', 'chi', 'la'], {'icon': 'backpack'}), 1, ['chi', 'che', 'ri']),
  ];

  static const sentences = [
    DemoSentence('Mi mamá me ama.', {'icon': 'woman'}),
    DemoSentence('La flor es roja.', {'icon': 'flower'}),
    DemoSentence('Mi papá me mima.', {'icon': 'man'}),
    DemoSentence('El gato toma leche.', {'drawing': 'animal_gato'}),
  ];

  /// Un ejemplo por nivel de dictado: lo que se escucha y sus sílabas.
  static const dictations = [
    DemoDictation(1, 'Sílabas', 'ma', ['ma'], ['ma', 'pa', 'sa']),
    DemoDictation(2, 'Palabras', 'mesa', ['me', 'sa'], ['sa', 'me', 'pa', 'lo']),
    DemoDictation(
      3,
      'Oraciones',
      'Mi mamá me ama.',
      ['Mi', 'mamá', 'me', 'ama.'],
      ['ama.', 'me', 'Mi', 'mamá'],
    ),
  ];
}

class DemoFamily {
  const DemoFamily(this.letter, this.syllables);
  final String letter;
  final List<DemoSyllable> syllables;
}

class DemoSyllable {
  const DemoSyllable(this.text, this.example);
  final String text;
  final DemoWord example;
}

class DemoWord {
  const DemoWord(this.text, this.syllables, this.pictureJson);
  final String text;
  final List<String> syllables;
  final Map<String, Object> pictureJson;

  SpeechPicture get picture => SpeechPicture.fromJson(pictureJson) ?? const IconPicture('star', null);
}

class DemoCompleteWord {
  const DemoCompleteWord(this.word, this.missing, this.options);
  final DemoWord word;

  /// Posición de la sílaba que falta.
  final int missing;
  final List<String> options;

  String get answer => word.syllables[missing];
}

class DemoSentence {
  const DemoSentence(this.text, this.pictureJson);
  final String text;
  final Map<String, Object> pictureJson;

  SpeechPicture get picture => SpeechPicture.fromJson(pictureJson) ?? const IconPicture('star', null);
  List<String> get words => text.split(' ');
}

class DemoDictation {
  const DemoDictation(this.level, this.levelName, this.spoken, this.pieces, this.cards);
  final int level;
  final String levelName;

  /// Lo que se dicta.
  final String spoken;

  /// Las piezas en orden (sílabas o palabras).
  final List<String> pieces;

  /// Las tarjetas que se ofrecen para formarlo (incluye distractores).
  final List<String> cards;

  /// Las sílabas se juntan en una palabra; las palabras, con espacios.
  String get joiner => level == 3 ? ' ' : '';
}
