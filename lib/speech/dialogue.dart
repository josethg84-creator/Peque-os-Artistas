import 'package:flutter/painting.dart';

import 'speech_content.dart';

/// Conversaciones guiadas de «Hablemos con Lolo»: datos y motor.
///
/// Todo está predefinido y revisado en `assets/speech/conversations.json`
/// (no se usa inteligencia artificial ni servicios externos). Cada
/// conversación es un pequeño grafo: Lolo pregunta (un nodo), el niño elige
/// una tarjeta (una opción), Lolo responde y pasa a la pregunta siguiente.

class ConversationCategory {
  const ConversationCategory({required this.id, required this.name, required this.icon, required this.color});
  final String id;
  final String name;

  /// Pictograma de [SpeechIcons].
  final String icon;
  final Color color;
}

class DialogueOption {
  const DialogueOption({required this.text, required this.picture, required this.reply, this.next});

  /// Lo que «dice» el niño al elegir la tarjeta.
  final String text;
  final SpeechPicture picture;

  /// La reacción de Lolo.
  final String reply;

  /// La pregunta siguiente; `null` termina la conversación.
  final String? next;
}

class DialogueNode {
  const DialogueNode({required this.lolo, required this.options});

  /// Lo que pregunta Lolo.
  final String lolo;
  final List<DialogueOption> options;
}

class Conversation {
  const Conversation({
    required this.id,
    required this.category,
    required this.title,
    required this.picture,
    required this.start,
    required this.nodes,
    required this.goodbye,
  });

  final String id;
  final String category;
  final String title;
  final SpeechPicture picture;
  final String start;
  final Map<String, DialogueNode> nodes;

  /// Despedida de Lolo al terminar.
  final String goodbye;

  /// Problemas del contenido (vacío si está bien): nodos que no existen,
  /// preguntas sin opciones…
  List<String> validate() => [
    if (!nodes.containsKey(start)) '$id: no existe el nodo inicial «$start»',
    for (final MapEntry(key: k, value: n) in nodes.entries) ...[
      if (n.options.length < 2) '$id/$k: necesita al menos 2 respuestas',
      for (final o in n.options)
        if (o.next != null && !nodes.containsKey(o.next))
          '$id/$k: «${o.text}» lleva a «${o.next}», que no existe',
    ],
  ];

  static Conversation? fromJson(Map<String, dynamic> json) {
    final id = json['id'], category = json['category'], title = json['title'], start = json['start'];
    final picture = SpeechPicture.fromJson(json['picture']);
    final rawNodes = json['nodes'];
    if (id is! String || category is! String || title is! String || start is! String) return null;
    if (picture == null || rawNodes is! Map<String, dynamic>) return null;
    final nodes = <String, DialogueNode>{};
    for (final MapEntry(:key, :value) in rawNodes.entries) {
      if (value is! Map<String, dynamic> || value['lolo'] is! String) continue;
      nodes[key] = DialogueNode(
        lolo: value['lolo'] as String,
        options: [
          for (final o in (value['options'] as List? ?? const []))
            if (o is Map<String, dynamic>)
              if ((o['text'], o['reply'], SpeechPicture.fromJson(o['picture'])) case (
                final String text,
                final String reply,
                final SpeechPicture picture,
              ))
                DialogueOption(text: text, picture: picture, reply: reply, next: o['next'] as String?),
        ],
      );
    }
    final c = Conversation(
      id: id,
      category: category,
      title: title,
      picture: picture,
      start: start,
      nodes: nodes,
      goodbye: json['goodbye'] is String
          ? json['goodbye'] as String
          : '¡Gracias por hablar conmigo! ¡Hasta pronto!',
    );
    // Una conversación con errores no se muestra (no puede quedarse a medias).
    return c.validate().isEmpty ? c : null;
  }
}

/// Un intercambio ya hecho: lo que preguntó Lolo, lo que eligió el niño y lo
/// que respondió Lolo.
class DialogueExchange {
  const DialogueExchange(this.question, this.answer, this.reply);
  final String question;
  final DialogueOption answer;
  final String reply;
}

/// Una sesión de conversación. Es corta a propósito: como mucho
/// [maxExchanges] intercambios (por defecto 5), aunque el contenido tuviera un
/// bucle, y se puede terminar en cualquier momento.
class DialogueSession {
  DialogueSession(this.conversation, {this.maxExchanges = 5}) : _node = conversation.start;

  final Conversation conversation;
  final int maxExchanges;
  String? _node;
  final exchanges = <DialogueExchange>[];
  bool _endedEarly = false;

  /// La pregunta actual (`null` si ya terminó).
  DialogueNode? get current => _node == null ? null : conversation.nodes[_node];
  bool get finished => current == null;

  /// Se terminó con el botón «Terminar» (no al llegar al final).
  bool get endedEarly => _endedEarly;

  /// El niño elige la respuesta [index]. Devuelve la reacción de Lolo.
  String choose(int index) {
    final node = current;
    if (node == null) throw StateError('La conversación ya terminó');
    final option = node.options[index];
    exchanges.add(DialogueExchange(node.lolo, option, option.reply));
    _node = exchanges.length >= maxExchanges ? null : option.next;
    return option.reply;
  }

  /// Termina ahora (botón «Terminar»).
  void end() {
    if (_node != null) _endedEarly = true;
    _node = null;
  }
}

/// Lee `conversations.json`.
({List<ConversationCategory> categories, List<Conversation> conversations}) parseConversations(
  Map<String, dynamic>? json,
) {
  if (json == null) return (categories: const [], conversations: const []);
  final conversations = <Conversation>[];
  final ids = <String>{};
  for (final c in (json['conversations'] as List? ?? const [])) {
    if (c is Map<String, dynamic>) {
      final conv = Conversation.fromJson(c);
      if (conv != null && ids.add(conv.id)) conversations.add(conv);
    }
  }
  final categories = [
    for (final c in (json['categories'] as List? ?? const []))
      if (c is Map<String, dynamic>)
        if ((c['id'], c['name']) case (final String id, final String name))
          if (conversations.any((x) => x.category == id))
            ConversationCategory(
              id: id,
              name: name,
              icon: c['icon'] is String ? c['icon'] as String : 'star',
              color: parseColor(c['color']) ?? const Color(0xFF9B7BEA),
            ),
  ];
  return (categories: categories, conversations: conversations);
}
