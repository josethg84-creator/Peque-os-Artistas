import 'dart:convert';

import 'package:flutter/services.dart';

import '../speech/speech_content.dart';

/// «Quiero decir»: catálogo de pictogramas de comunicación
/// (`assets/aac/pictograms.json`, generado por `tools/aac/pictograms.py`).
///
/// Es una herramienta de apoyo a la comunicación. No evalúa al niño, no es un
/// tratamiento y no depende de estrellas ni de actividades terminadas.

/// Tipo gramatical (para construir frases).
enum PictogramKind {
  frase,
  pronombre,
  verbo,
  sustantivo,
  adjetivo,
  determinante,
  preposicion,
  conjuncion,
  palabra,
  pregunta;

  static PictogramKind byName(Object? name) =>
      values.firstWhere((k) => k.name == name, orElse: () => PictogramKind.palabra);
}

/// Resuelve las formas «{o|a}» según el ajuste del adulto (masculino o
/// femenino): «Estoy cansad{o|a}.» → «Estoy cansada.».
String resolveGender(String text, {required bool feminine}) =>
    text.replaceAllMapped(RegExp(r'\{([^|{}]*)\|([^|{}]*)\}'), (m) => feminine ? m[2]! : m[1]!);

/// Primera letra en mayúscula (también tras «¿» o «¡»).
String capitalize(String s) {
  final i = s.indexOf(RegExp(r'[^¿¡\s]'));
  if (i < 0) return s;
  return '${s.substring(0, i)}${s[i].toUpperCase()}${s.substring(i + 1)}';
}

class Pictogram {
  const Pictogram({
    required this.id,
    required this.category,
    required this.text,
    required this.speech,
    required this.picture,
    required this.color,
    required this.order,
    required this.kind,
    this.active = true,
    this.related = const [],
    this.article,
    this.takesA = false,
    this.place = false,
  });

  final String id;
  final String category;

  /// Lo que se ve (con «{o|a}» si cambia con el género).
  final String text;

  /// Lo que se dice (en el catálogo es el mismo texto: lo que se ve es lo que
  /// se dice).
  final String speech;

  /// Ilustración: dibujo propio, del catálogo o pictograma de Material.
  final SpeechPicture picture;
  final Color color;
  final int order;
  final bool active;

  /// Pictogramas relacionados (sugerencias del constructor).
  final List<String> related;
  final PictogramKind kind;

  /// Artículo de un sustantivo («el», «la», «una»…); `null` si no lleva.
  final String? article;

  /// Verbos de movimiento («ir», «vamos»): «ir al parque».
  final bool takesA;

  /// Es un lugar.
  final bool place;

  /// Lo que se ve y se dice en la tarjeta (con mayúscula inicial).
  String label({bool feminine = false}) => capitalize(resolveGender(text, feminine: feminine));

  /// Texto en minúsculas para el constructor.
  String word({bool feminine = false}) => resolveGender(text, feminine: feminine);

  static Pictogram? fromJson(Map<String, dynamic> json) {
    final id = json['id'], category = json['category'], text = json['text'];
    final picture = SpeechPicture.fromJson(json['picture']);
    if (id is! String || category is! String || text is! String || text.trim().isEmpty || picture == null) {
      return null;
    }
    final speech = json['speech'];
    return Pictogram(
      id: id,
      category: category,
      text: text,
      // La voz dice lo mismo que se ve.
      speech: speech is String && speech == text ? speech : text,
      picture: picture,
      color: parseColor(json['color']) ?? const Color(0xFF90A4AE),
      order: json['order'] is int ? json['order'] as int : 0,
      active: json['active'] != false,
      related: [...(json['related'] as List? ?? const []).whereType<String>()],
      kind: PictogramKind.byName(json['kind']),
      article: json['article'] is String ? json['article'] as String : null,
      takesA: json['takes_a'] == true,
      place: json['place'] == true,
    );
  }
}

class AacCategory {
  const AacCategory({
    required this.id,
    required this.name,
    required this.color,
    required this.icon,
    this.order = 0,
  });
  final String id;
  final String name;
  final Color color;

  /// Nombre de un icono (ver [SpeechIcons.lookup]).
  final String icon;
  final int order;
}

/// Una pregunta de «Aprendo a comunicarme con Lolo».
class AacLearnItem {
  const AacLearnItem(this.question, this.answer, this.others);
  final String question;
  final String answer;
  final List<String> others;
}

class AacCatalog {
  AacCatalog({
    required this.categories,
    required List<Pictogram> pictograms,
    this.quick = const [],
    this.feelings = const [],
    this.start = const [],
    this.learn = const [],
  }) : pictograms = [...pictograms]..sort((a, b) => a.order.compareTo(b.order)),
       _byId = {for (final p in pictograms) p.id: p};

  static const asset = 'assets/aac/pictograms.json';

  final List<AacCategory> categories;
  final List<Pictogram> pictograms;
  final Map<String, Pictogram> _byId;

  /// Tablero rápido (palabras esenciales que no se pueden ocultar).
  final List<String> quick;

  /// Emociones y necesidades.
  final List<String> feelings;

  /// Primeras sugerencias del constructor.
  final List<String> start;
  final List<AacLearnItem> learn;

  Pictogram? byId(String id) => _byId[id];

  List<Pictogram> active() => [
    for (final p in pictograms)
      if (p.active) p,
  ];

  List<Pictogram> inCategory(String id) => [
    for (final p in pictograms)
      if (p.active && p.category == id) p,
  ];

  List<Pictogram> resolve(Iterable<String> ids) => [for (final id in ids) ?_byId[id]];

  AacCategory? category(String id) => categories.where((c) => c.id == id).firstOrNull;

  static Future<AacCatalog> load(AssetBundle bundle) async =>
      parse(jsonDecode(utf8.decode((await bundle.load(asset)).buffer.asUint8List())) as Map<String, dynamic>);

  /// Lo que no se entienda (un dibujo desconocido, un id repetido) se descarta
  /// sin romper el tablero.
  static AacCatalog parse(Map<String, dynamic> json) {
    final seen = <String>{};
    final pictograms = [
      for (final p in (json['pictograms'] as List? ?? const []))
        if (p is Map<String, dynamic>)
          if (Pictogram.fromJson(p) case final pic? when seen.add(pic.id)) pic,
    ];
    final categories = [
      for (final c in (json['categories'] as List? ?? const []))
        if (c is Map<String, dynamic> && c['id'] is String && c['name'] is String)
          AacCategory(
            id: c['id'] as String,
            name: c['name'] as String,
            color: parseColor(c['color']) ?? const Color(0xFF90A4AE),
            icon: c['icon'] is String ? c['icon'] as String : 'star',
            order: c['order'] is int ? c['order'] as int : 0,
          ),
    ]..sort((a, b) => a.order.compareTo(b.order));
    final boards = json['boards'] is Map<String, dynamic> ? json['boards'] as Map<String, dynamic> : const {};
    List<String> board(String key) => [
      for (final id in (boards[key] as List? ?? const []).whereType<String>())
        if (seen.contains(id)) id,
    ];
    return AacCatalog(
      categories: categories,
      pictograms: pictograms,
      quick: board('quick'),
      feelings: board('feelings'),
      start: board('start'),
      learn: [
        for (final l in (json['learn'] as List? ?? const []))
          if (l is Map<String, dynamic> && l['question'] is String && seen.contains(l['answer']))
            AacLearnItem(l['question'] as String, l['answer'] as String, [
              for (final o in (l['others'] as List? ?? const []).whereType<String>())
                if (seen.contains(o)) o,
            ]),
      ],
    );
  }
}
