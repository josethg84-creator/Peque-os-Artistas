/// Separación en sílabas del español escrito (para comprobar el contenido de
/// «Aprendo a leer» y, en fases siguientes, para generar ejercicios).
///
/// Reglas:
/// - «ch», «ll» y «rr» son una sola consonante; «qu» y «gu» delante de e/i
///   también (la u no suena). En «güe/güi» la ü sí es vocal.
/// - Diptongo: vocal abierta (a, e, o) + cerrada átona (i, u), o al revés, o
///   dos cerradas distintas (iu, ui). Hiato: dos abiertas, o una cerrada con
///   tilde (í, ú) junto a otra vocal.
/// - La «y» es vocal al final de palabra o entre consonantes; si no, consonante.
/// - Entre vocales: una consonante va con la siguiente; dos se separan salvo
///   los grupos pl, bl, cl, gl, fl, pr, br, tr, dr, cr, gr, fr (y kl, kr), que
///   van juntos con la siguiente; con tres o cuatro, el grupo inseparable (o
///   la última consonante) pasa a la siguiente sílaba.
/// La «h» se trata como consonante y «tl» se separa (at-las); no se tienen en
/// cuenta los prefijos (sub-, des-…): esas palabras se revisan a mano.
abstract final class Syllabifier {
  static const _strong = {'a', 'e', 'o', 'á', 'é', 'ó', 'í', 'ú'};
  static const _weak = {'i', 'u', 'ü'};
  static const _clusters = {
    'pl',
    'bl',
    'cl',
    'gl',
    'fl',
    'kl',
    'pr',
    'br',
    'tr',
    'dr',
    'cr',
    'gr',
    'fr',
    'kr',
  };

  static bool _isVowelChar(String c) => _strong.contains(c) || _weak.contains(c);

  /// Separa [word] (una sola palabra, sin espacios) en sílabas, conservando
  /// mayúsculas y tildes.
  static List<String> split(String word) {
    final tokens = _tokens(word);
    if (tokens.isEmpty) return const [];
    // Núcleos: grupos de vocales seguidas que forman una sílaba.
    final groups = <List<_Token>>[]; // alternancia: consonantes / núcleo
    final isNucleus = <bool>[];
    for (final t in tokens) {
      final last = groups.isEmpty ? null : groups.last;
      final lastIsNucleus = isNucleus.isNotEmpty && isNucleus.last;
      if (t.vowel) {
        if (last != null && lastIsNucleus && _joins(last.last, t)) {
          last.add(t);
        } else {
          groups.add([t]);
          isNucleus.add(true);
        }
      } else {
        if (last != null && !lastIsNucleus) {
          last.add(t);
        } else {
          groups.add([t]);
          isNucleus.add(false);
        }
      }
    }
    final syllables = <String>[];
    var current = StringBuffer();
    var seenNucleus = false;
    for (var g = 0; g < groups.length; g++) {
      final group = groups[g];
      if (isNucleus[g]) {
        if (seenNucleus) {
          // Dos núcleos seguidos (hiato): nueva sílaba.
          syllables.add(current.toString());
          current = StringBuffer();
        }
        for (final t in group) {
          current.write(t.text);
        }
        seenNucleus = true;
        continue;
      }
      // Consonantes.
      final hasNextNucleus = g + 1 < groups.length;
      if (!seenNucleus || !hasNextNucleus) {
        for (final t in group) {
          current.write(t.text);
        }
        continue;
      }
      final keep = _consonantsThatStay(group);
      for (final t in group.take(keep)) {
        current.write(t.text);
      }
      syllables.add(current.toString());
      current = StringBuffer();
      seenNucleus = false;
      for (final t in group.skip(keep)) {
        current.write(t.text);
      }
    }
    if (current.isNotEmpty) {
      if (seenNucleus || syllables.isEmpty) {
        syllables.add(current.toString());
      } else {
        syllables[syllables.length - 1] += current.toString();
      }
    }
    return syllables;
  }

  /// Cuántas consonantes de un grupo entre vocales se quedan en la sílaba
  /// anterior.
  static int _consonantsThatStay(List<_Token> group) {
    final n = group.length;
    if (n == 1) return 0;
    bool cluster(int i) => _clusters.contains('${group[i].lower}${group[i + 1].lower}');
    if (n == 2) return cluster(0) ? 0 : 1;
    if (n == 3) return cluster(1) ? 1 : 2;
    return n - 2; // cuatro: abs-trac-to
  }

  /// Si la vocal [b] forma diptongo con la anterior [a].
  static bool _joins(_Token a, _Token b) {
    final x = a.lower, y = b.lower;
    final xWeak = _weak.contains(x), yWeak = _weak.contains(y);
    if (!xWeak && !yWeak) return false; // dos abiertas o con tilde: hiato
    if (xWeak && yWeak) return x != y || x == 'ü'; // iu, ui, üi
    return true; // abierta + cerrada átona (í y ú cuentan como abiertas)
  }

  static List<_Token> _tokens(String word) {
    final chars = word.split('');
    final lower = word.toLowerCase().split('');
    final out = <_Token>[];
    var i = 0;
    while (i < chars.length) {
      final c = lower[i];
      final next = i + 1 < lower.length ? lower[i + 1] : '';
      final after = i + 2 < lower.length ? lower[i + 2] : '';
      final pair = '$c$next';
      if (pair == 'ch' || pair == 'll' || pair == 'rr') {
        out.add(_Token(chars[i] + chars[i + 1], pair, false));
        i += 2;
        continue;
      }
      if ((c == 'q' || c == 'g') &&
          next == 'u' &&
          (after == 'e' || after == 'i' || after == 'é' || after == 'í')) {
        out.add(_Token(chars[i] + chars[i + 1], pair, false));
        i += 2;
        continue;
      }
      if (c == 'y') {
        final nextIsVowel = _isVowelChar(next);
        final atEnd = next.isEmpty;
        final vowel = atEnd || !nextIsVowel && i > 0 && !_isVowelChar(lower[i - 1]);
        out.add(_Token(chars[i], vowel ? 'i' : 'y', vowel));
        i++;
        continue;
      }
      out.add(_Token(chars[i], c, _isVowelChar(c)));
      i++;
    }
    return out;
  }
}

class _Token {
  _Token(this.text, this.lower, this.vowel);
  final String text;
  final String lower;
  final bool vowel;
}
