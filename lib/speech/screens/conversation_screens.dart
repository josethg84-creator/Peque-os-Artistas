import 'dart:async';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_art.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _chatColor = Color(0xFF7E57C2);

/// «Hablemos con Lolo»: las categorías de conversación.
class ConversationsHubScreen extends StatelessWidget {
  const ConversationsHubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Hablemos con Lolo',
      titleIcon: Icons.forum_rounded,
      accent: _chatColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: speech,
          builder: (context, _) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: LoloBubble(text: '¿De qué quieres que hablemos hoy?', size: 60),
                ),
              ),
              Expanded(
                child: AdaptiveGrid(
                  itemCount: content.conversationCategories.length,
                  minTileWidth: 160,
                  childAspectRatio: 0.95,
                  itemBuilder: (context, i) {
                    final c = content.conversationCategories[i];
                    final all = content.conversations.where((x) => x.category == c.id);
                    final done = all.where((x) => speech.progress.conversationsDone.contains(x.id)).length;
                    return HomeMenuCard(
                      title: c.name,
                      subtitle: '$done de ${all.length} conversaciones',
                      color: Color.lerp(c.color, Colors.white, 0.2)!,
                      art: Padding(
                        padding: const EdgeInsets.all(6),
                        child: SpeechPictureView(
                          picture: IconPicture(c.icon, Color.lerp(c.color, Colors.black, 0.35)),
                          tint: c.color,
                        ),
                      ),
                      onTap: () => Navigator.of(context)
                          .pushNamed(AppRoutes.speechConversationList, arguments: SpeechCategoryArgs(c.id)),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Las conversaciones de una categoría.
class ConversationListScreen extends StatelessWidget {
  const ConversationListScreen({super.key, required this.categoryId});

  final String categoryId;

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return SpeechContentBuilder(
      builder: (context, content) {
        final category = content.conversationCategories.where((c) => c.id == categoryId).firstOrNull;
        final list = content.conversations.where((c) => c.category == categoryId).toList();
        return KidScaffold(
          title: category?.name ?? 'Hablemos con Lolo',
          titleIcon: Icons.forum_rounded,
          accent: _chatColor,
          backLabel: 'Volver a las conversaciones',
          body: ListenableBuilder(
            listenable: speech,
            builder: (context, _) => AdaptiveGrid(
              itemCount: list.length,
              minTileWidth: 170,
              childAspectRatio: 0.95,
              itemBuilder: (context, i) {
                final c = list[i];
                final done = speech.progress.conversationsDone.contains(c.id);
                return HomeMenuCard(
                  title: c.title,
                  subtitle: done ? '¡Ya hablamos!' : '¡Vamos a hablar!',
                  color: Color.lerp(category?.color ?? _chatColor, Colors.white, 0.3)!,
                  art: Padding(
                    padding: const EdgeInsets.all(4),
                    child: SpeechPictureView(picture: c.picture),
                  ),
                  onTap: () =>
                      Navigator.of(context)
                          .pushNamed(AppRoutes.speechConversation, arguments: SpeechConversationArgs(c.id)),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

/// Una conversación con Lolo. Lolo pregunta con voz; el niño responde
/// tocando una tarjeta (con dibujo y texto). No se usa el reconocimiento de
/// voz: Lolo responde a la tarjeta elegida. Con «Practicar», el niño puede
/// decir su respuesta con su voz para escucharse (no se interpreta).
class ConversationScreen extends StatelessWidget {
  const ConversationScreen({super.key, required this.conversationId});

  final String conversationId;

  @override
  Widget build(BuildContext context) {
    return SpeechContentBuilder(
      builder: (context, content) {
        final c = content.conversations.where((x) => x.id == conversationId).firstOrNull;
        if (c == null) {
          return KidScaffold(
            title: 'Hablemos con Lolo',
            accent: _chatColor,
            body: const Center(child: Text('No encontramos esta conversación.')),
          );
        }
        return _Chat(key: ValueKey(c.id), conversation: c);
      },
    );
  }
}

class _Chat extends StatefulWidget {
  const _Chat({super.key, required this.conversation});

  final Conversation conversation;

  @override
  State<_Chat> createState() => _ChatState();
}

class _ChatState extends State<_Chat> {
  late DialogueSession _session = DialogueSession(widget.conversation);
  final _scroll = ScrollController();
  bool _rewarded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _ask());
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _ask() {
    final node = _session.current;
    if (node != null && mounted) speak(context, node.lolo);
  }

  void _choose(int i) {
    final audio = SpeechVoice.of(context);
    final reply = _session.choose(i);
    setState(() {});
    unawaited(audio.say(reply));
    final next = _session.current;
    if (next != null) {
      unawaited(audio.say(next.lolo, mode: VoiceMode.queue));
    } else {
      _finish();
    }
    _scrollDown();
  }

  void _finish() {
    final audio = SpeechVoice.of(context);
    unawaited(audio.say(widget.conversation.goodbye, mode: VoiceMode.queue));
    if (!_session.endedEarly && !_rewarded) {
      _rewarded = true;
      AppServices.of(context).speech.markConversationDone(widget.conversation.id);
      unawaited(audio.play(SoundCue.star));
    }
  }

  void _end() {
    setState(_session.end);
    speak(context, widget.conversation.goodbye);
    _scrollDown();
  }

  void _restart() {
    setState(() => _session = DialogueSession(widget.conversation));
    _ask();
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        unawaited(
          _scroll.animateTo(
            _scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          ),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.conversation;
    final node = _session.current;
    return KidScaffold(
      title: c.title,
      titleIcon: Icons.forum_rounded,
      accent: _chatColor,
      backLabel: 'Volver a las conversaciones',
      body: LayoutBuilder(
        builder: (context, box) {
          final columns = box.maxWidth > 620 ? 4 : 2;
          final cardWidth = (box.maxWidth - 32 - (columns - 1) * 10) / columns;
          return ListView(
            controller: _scroll,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [
              Center(
                child: SizedBox(width: 150, height: 150, child: SpeechPictureView(picture: c.picture)),
              ),
              const SizedBox(height: 8),
              for (final e in _session.exchanges) ...[
                _Bubble(text: e.question, fromLolo: true),
                _Bubble(
                  text: e.answer.text,
                  fromLolo: false,
                  picture: e.answer.picture,
                  onPractice: practiceAllowed(context)
                      ? () => showPracticeSheet(context, e.answer.text)
                      : null,
                ),
                _Bubble(text: e.reply, fromLolo: true),
              ],
              if (node != null) ...[
                _Bubble(text: node.lolo, fromLolo: true, big: true),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  alignment: WrapAlignment.center,
                  children: [
                    for (final (i, o) in node.options.indexed)
                      SizedBox(
                        width: cardWidth,
                        child: _AnswerCard(option: o, onTap: () => _choose(i)),
                      ),
                  ],
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  alignment: WrapAlignment.center,
                  children: [
                    SizedBox(
                      width: 130,
                      child: SpeechActionButton(
                        icon: Icons.replay_rounded,
                        label: 'Repetir',
                        color: const Color(0xFF29B6F6),
                        onPressed: _ask,
                      ),
                    ),
                    SizedBox(
                      width: 130,
                      child: SpeechActionButton(
                        icon: Icons.slow_motion_video_rounded,
                        label: 'Despacio',
                        color: const Color(0xFFAB47BC),
                        onPressed: () => speak(context, node.lolo, slow: true),
                      ),
                    ),
                    SizedBox(
                      width: 130,
                      child: SpeechActionButton(
                        icon: Icons.waving_hand_rounded,
                        label: 'Terminar',
                        color: AppColors.inkSoft,
                        onPressed: _end,
                      ),
                    ),
                  ],
                ),
              ] else ...[
                _Bubble(text: c.goodbye, fromLolo: true, big: true),
                if (_rewarded)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Semantics(
                      label: '¡Ganaste una estrella!',
                      excludeSemantics: true,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.star_rounded, color: AppColors.sun, size: 44),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              '¡Ganaste una estrella!',
                              style: fredoka(24, color: const Color(0xFF8D6E00)),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  alignment: WrapAlignment.center,
                  children: [
                    SizedBox(
                      width: 150,
                      child: SpeechActionButton(
                        icon: Icons.replay_rounded,
                        label: 'Hablar otra vez',
                        color: _chatColor,
                        onPressed: _restart,
                      ),
                    ),
                    SizedBox(
                      width: 150,
                      child: SpeechActionButton(
                        icon: Icons.forum_rounded,
                        label: 'Otra conversación',
                        color: speechAccent,
                        onPressed: () => Navigator.of(context).maybePop(),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

/// Un globo de la conversación: Lolo a la izquierda, el niño a la derecha.
class _Bubble extends StatelessWidget {
  const _Bubble({
    required this.text,
    required this.fromLolo,
    this.picture,
    this.big = false,
    this.onPractice,
  });

  final String text;
  final bool fromLolo;
  final SpeechPicture? picture;
  final bool big;
  final VoidCallback? onPractice;

  @override
  Widget build(BuildContext context) {
    final style = fredoka(big ? 24 : 20, weight: FontWeight.w500, color: const Color(0xFF3B3355));
    final bubble = Flexible(
      child: Semantics(
        container: true,
        label: fromLolo ? 'Lolo: $text' : 'Tú: $text',
        excludeSemantics: true,
        child: GestureDetector(
          onTap: fromLolo ? () => speak(context, text) : null,
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 4),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: fromLolo ? Colors.white : const Color(0xFFEDE7F6),
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(20),
                topRight: const Radius.circular(20),
                bottomLeft: Radius.circular(fromLolo ? 4 : 20),
                bottomRight: Radius.circular(fromLolo ? 20 : 4),
              ),
              border: Border.all(
                color: fromLolo
                    ? LoloPainter.green.withValues(alpha: 0.5)
                    : _chatColor.withValues(alpha: 0.4),
                width: 2,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (picture case final p?) ...[
                  SizedBox(
                    width: 44,
                    height: 44,
                    child: SpeechPictureView(picture: p, tint: _chatColor),
                  ),
                  const SizedBox(width: 8),
                ],
                Flexible(child: Text(text, style: style)),
              ],
            ),
          ),
        ),
      ),
    );
    return Row(
      mainAxisAlignment: fromLolo ? MainAxisAlignment.start : MainAxisAlignment.end,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        if (fromLolo) ...[Lolo(size: big ? 56 : 40, waves: big ? 1 : 0), const SizedBox(width: 6)],
        bubble,
        if (!fromLolo && onPractice != null)
          IconButton(
            tooltip: 'Practicar diciéndolo con tu voz',
            onPressed: onPractice,
            icon: const Icon(Icons.mic_rounded, color: Color(0xFFE53950)),
          ),
      ],
    );
  }
}

/// Tarjeta de respuesta: dibujo grande y la frase.
class _AnswerCard extends StatelessWidget {
  const _AnswerCard({required this.option, required this.onTap});

  final DialogueOption option;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      button: true,
      label: option.text,
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: _chatColor.withValues(alpha: 0.45), width: 3),
            boxShadow: [BoxShadow(color: _chatColor.withValues(alpha: 0.3), offset: const Offset(0, 4))],
          ),
          child: Column(
            children: [
              SizedBox(
                height: 86,
                child: SpeechPictureView(picture: option.picture, tint: _chatColor),
              ),
              const SizedBox(height: 4),
              Text(
                option.text,
                textAlign: TextAlign.center,
                style: fredoka(18, color: const Color(0xFF4527A0)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
