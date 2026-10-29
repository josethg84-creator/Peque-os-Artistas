import 'dart:math';

class MemoryCard {
  MemoryCard(this.id, this.face);

  /// Posición única de la carta.
  final int id;

  /// Lo que muestra (dos cartas con la misma cara forman pareja).
  final String face;
  bool faceUp = false;
  bool matched = false;
}

enum FlipResult { ignored, flipped, match, noMatch }

/// Lógica del juego «Une las parejas», sin temporizadores ni penalizaciones.
///
/// Se giran dos cartas: si coinciden quedan descubiertas; si no, quedan a la
/// vista hasta que la pantalla llama a [hideMismatch] tras una pausa breve.
/// Mientras tanto no se pueden girar otras cartas.
class MemoryGame {
  MemoryGame({required List<String> faces, required this.pairs, Random? random})
    : _random = random ?? Random() {
    if (faces.toSet().length < pairs) throw ArgumentError('Hacen falta $pairs caras distintas');
    _faces = faces.toSet().toList();
    restart();
  }

  final int pairs;
  final Random _random;
  late final List<String> _faces;
  late List<MemoryCard> cards;
  final _open = <MemoryCard>[];
  int _attempts = 0;

  int get attempts => _attempts;
  int get matchedPairs => cards.where((c) => c.matched).length ~/ 2;
  bool get isFinished => matchedPairs == pairs;

  /// Hay dos cartas distintas boca arriba esperando a ocultarse.
  bool get waitingToHide => _open.length == 2;

  void restart() {
    final chosen = ([..._faces]..shuffle(_random)).take(pairs).toList();
    final deck = [...chosen, ...chosen]..shuffle(_random);
    cards = [for (final (i, face) in deck.indexed) MemoryCard(i, face)];
    _open.clear();
    _attempts = 0;
  }

  FlipResult flip(int cardId) {
    final card = cards.firstWhere((c) => c.id == cardId);
    if (card.faceUp || card.matched || waitingToHide) return FlipResult.ignored;
    card.faceUp = true;
    _open.add(card);
    if (_open.length < 2) return FlipResult.flipped;
    _attempts++;
    final [a, b] = _open;
    if (a.face == b.face) {
      a.matched = b.matched = true;
      _open.clear();
      return FlipResult.match;
    }
    return FlipResult.noMatch;
  }

  /// Oculta las dos cartas que no coincidían.
  void hideMismatch() {
    if (!waitingToHide) return;
    for (final c in _open) {
      c.faceUp = false;
    }
    _open.clear();
  }
}
