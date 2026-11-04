import 'aac_catalog.dart';

/// Une los pictogramas de la barra en una frase en buen español, sin
/// corregir al niño: cualquier combinación vale y se dice tal cual, solo se
/// añaden los artículos y las contracciones que hacen falta.
///
/// [YO] + [QUIERO] + [AGUA] → «Yo quiero agua.»
/// [QUIERO] + [IR] + [PARQUE] → «Quiero ir al parque.»
/// [ME DUELE] + [CABEZA] → «Me duele la cabeza.»
/// [QUIERO] + [JUGAR] + [CON] + [MI] + [PERRO] → «Quiero jugar con mi perro.»
String composePhrase(List<Pictogram> tokens, {bool feminine = false}) {
  if (tokens.isEmpty) return '';
  final words = <String>[];
  Pictogram? prev;
  var question = false;
  for (final t in tokens) {
    var w = t.word(feminine: feminine).trim();
    switch (t.kind) {
      case PictogramKind.frase:
        // Una frase hecha entra entera, sin su punto final.
        w = w.replaceAll(RegExp(r'[.!]+$'), '');
        if (w.startsWith('¿') && words.isEmpty) question = true;
        w = w.replaceAll(RegExp(r'[¿?]'), '');
      case PictogramKind.pregunta:
        if (words.isEmpty) question = true;
        w = w.replaceAll(RegExp(r'[¿?]'), '').toLowerCase();
      case PictogramKind.sustantivo:
        final afterDeterminer = prev?.kind == PictogramKind.determinante;
        final article = afterDeterminer ? null : t.article;
        // «ir» + lugar → «ir al parque», «ir a casa».
        final needsA = t.place && prev != null && prev.takesA;
        final afterA = prev?.id == 'a';
        if (article == 'el' && (needsA || afterA)) {
          if (afterA) words.removeLast();
          w = 'al $w';
        } else {
          w = [if (needsA) 'a', ?article, w].join(' ');
        }
      default:
        break;
    }
    if (w.isNotEmpty) words.add(w);
    prev = t;
  }
  var sentence = words.join(' ').replaceAll(RegExp(r'\s+'), ' ').trim();
  if (sentence.isEmpty) return '';
  sentence = capitalize(sentence);
  if (question) return '¿$sentence?';
  return RegExp(r'[.!?]$').hasMatch(sentence) ? sentence : '$sentence.';
}

/// Sugerencias para el siguiente pictograma: los relacionados con el último
/// o, si no hay, unos de uso frecuente según el tipo. Nunca impiden elegir
/// cualquier otro.
List<Pictogram> suggestNext(AacCatalog catalog, List<Pictogram> tokens, {int max = 8}) {
  if (tokens.isEmpty) return catalog.resolve(catalog.start).take(max).toList();
  final last = tokens.last;
  final out = <Pictogram>[...catalog.resolve(last.related)];
  if (out.length < max) {
    final more = switch (last.kind) {
      PictogramKind.pronombre => ['quiero', 'estoy', 'tengo', 'necesito', 'me_gusta', 'no_quiero'],
      PictogramKind.verbo => ['jugar', 'comer', 'agua', 'ir', 'descansar_v', 'mama', 'con'],
      PictogramKind.determinante => ['perro', 'gato', 'mama', 'papa', 'pelota', 'casa'],
      PictogramKind.preposicion => ['mi', 'mama', 'papa', 'amigo', 'parque', 'casa'],
      _ => ['y', 'con', 'mas', 'ahora', 'despues'],
    };
    out.addAll(catalog.resolve(more));
  }
  final seen = <String>{};
  return [
    for (final p in out)
      if (p.active && seen.add(p.id)) p,
  ].take(max).toList();
}
