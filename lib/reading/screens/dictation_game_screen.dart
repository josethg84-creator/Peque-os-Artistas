import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../learning/widgets/question_progress.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_dimens.dart';
import '../../widgets/big_action_button.dart';
import '../../widgets/kid_icon_button.dart';
import '../../widgets/kid_scaffold.dart';
import '../audio/reading_voice.dart';
import '../dictation.dart';
import '../reading_content.dart';
import '../reading_progress.dart';
import '../syllabifier.dart';
import '../widgets/reading_widgets.dart';
import '../widgets/sentence_widgets.dart';
import 'reading_dictation_screen.dart';

/// Partida de «Escucho y escribo»: 8 dictados de un nivel con un modo de
/// respuesta. Sin castigos: tras un error se puede volver a escuchar, pedir
/// pistas y corregir la respuesta.
class DictationGameScreen extends StatelessWidget {
  const DictationGameScreen({super.key, required this.args, this.seed});

  final DictationArgs args;

  /// Para pruebas: orden fijo.
  final int? seed;

  static const praise = '¡Excelente trabajo!';
  static const tryAgain = 'Vamos a intentarlo otra vez';
  static const sessionLength = 8;

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: ReadingDictationScreen.title,
      titleIcon: Icons.edit_rounded,
      accent: ReadingDictationScreen.color,
      trailing: const ReadingHomeButton(),
      body: DictationCatalogBuilder(
        builder: (context, catalog) => _Game(catalog: catalog, args: args, seed: seed),
      ),
    );
  }
}

class _Game extends StatefulWidget {
  const _Game({required this.catalog, required this.args, this.seed});

  final DictationCatalog catalog;
  final DictationArgs args;
  final int? seed;

  @override
  State<_Game> createState() => _GameState();
}

class _GameState extends State<_Game> {
  static const color = ReadingDictationScreen.color;

  ReadingVoice? _voice;
  late ReadingController _progress;
  late Random _random;
  late List<Dictation> _list;
  late DictationRound _round;
  final _text = TextEditingController();
  final _focus = FocusNode();
  int _index = 0;
  int _alone = 0;
  bool _finished = false;

  DictationMode get mode => widget.args.mode;
  Dictation get dictation => _round.dictation;

  String get instruction => switch ((widget.args.level, mode)) {
    (_, DictationMode.keyboard) => 'Escucha y escribe lo que oyes.',
    (1, _) => 'Escucha y toca la sílaba que oyes.',
    (2, _) => 'Escucha y forma la palabra con las sílabas.',
    _ => 'Escucha y ordena las palabras de la oración.',
  };

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_voice != null) return;
    final services = AppServices.of(context);
    _voice = ReadingVoice(services.audio);
    _progress = services.reading;
    _random = Random(widget.seed);
    _start();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _list.isEmpty) return;
      // Instrucción por voz y, a continuación, el dictado.
      unawaited(
        _voice!.playAll([ReadingAudio(tts: instruction.replaceAll(RegExp(r'\.$'), '')), dictation.audio]),
      );
    });
  }

  @override
  void dispose() {
    _voice?.dispose();
    _text.dispose();
    _focus.dispose();
    super.dispose();
  }

  void _start() {
    final all = [...widget.catalog.ofLevel(widget.args.level)]..shuffle(_random);
    bool done(Dictation d) => _progress.progress.dictations[d.id]?.correct ?? false;
    // Primero los que aún no se han acertado, de los más fáciles a los más difíciles.
    all.sort((a, b) {
      final byDone = (done(a) ? 1 : 0) - (done(b) ? 1 : 0);
      return byDone != 0 ? byDone : a.difficulty - b.difficulty;
    });
    _list = all.take(DictationGameScreen.sessionLength).toList();
    _index = 0;
    _alone = 0;
    _finished = false;
    if (_list.isNotEmpty) _newRound();
  }

  void _newRound() {
    _round = DictationRound(_list[_index], mode, random: _random);
    _text.clear();
  }

  void _listen([ReadingSpeed speed = ReadingSpeed.normal]) =>
      unawaited(_voice!.play(dictation.audio, speed: speed));

  void _place(int card) {
    if (_round.solved) return;
    setState(() {
      _round.place(card);
      _round.last = null;
    });
    unawaited(_voice!.play(ReadingAudio(tts: dictation.cards[card].replaceAll('.', '').toLowerCase())));
  }

  void _unplace(int slot) {
    setState(() {
      _round.unplace(slot);
      _round.last = null;
    });
  }

  void _hint() {
    final n = _round.nextHint();
    setState(() {});
    switch (n) {
      case 1:
        _listen(ReadingSpeed.slow);
      case 2:
        unawaited(_voice!.sayText('Tiene ${dictation.countLabel}.'));
      case 3:
        final first = dictation.firstHint.toLowerCase();
        unawaited(
          dictation.type == DictationType.syllable
              ? _voice!.sayText('Empieza con la letra ${letterNames[first] ?? first}.')
              : _voice!.playAll([const ReadingAudio(tts: 'Empieza así'), ReadingAudio(tts: first)]),
        );
      default:
        unawaited(_voice!.sayText('Mira cómo se escribe.'));
    }
  }

  void _check() {
    if (_round.solved || !_round.ready) return;
    final r = _round.check();
    _progress.recordDictation(
      dictation.id,
      type: dictation.type.id,
      level: dictation.level,
      mode: mode.id,
      correct: r.correct,
      hints: _round.hints,
      error: r.correct ? null : r.issue.name,
    );
    setState(() {});
    if (r.correct) {
      if (_round.independent) _alone++;
      HapticFeedback.lightImpact();
      unawaited(_voice!.playAll([const ReadingAudio(tts: '¡Excelente trabajo!'), dictation.audio]));
    } else {
      unawaited(_voice!.sayText('${DictationGameScreen.tryAgain}. ${r.message}'));
    }
  }

  void _next() {
    unawaited(_voice!.stop());
    if (_index == _list.length - 1) {
      setState(() => _finished = true);
      unawaited(_voice!.sayText('¡Terminaste! ¡Qué bien lo has hecho!'));
      return;
    }
    setState(() {
      _index++;
      _newRound();
    });
    _listen();
  }

  void _again() {
    setState(_start);
    _listen();
  }

  @override
  Widget build(BuildContext context) {
    if (_list.isEmpty) return const Center(child: Text('Todavía no hay dictados en este nivel.'));
    return LayoutBuilder(
      builder: (context, box) {
        final wide = box.maxWidth >= 760;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            AppDimens.pagePadding,
            0,
            AppDimens.pagePadding,
            AppDimens.pagePadding,
          ),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 860),
              child: _finished ? _summary() : _play(wide),
            ),
          ),
        );
      },
    );
  }

  Widget _summary() => Column(
    children: [
      const SizedBox(height: 20),
      const ReadingCelebration(text: '¡Terminaste! ¡Qué bien lo has hecho!'),
      const SizedBox(height: 16),
      Semantics(
        label: 'Acertaste $_alone de ${_list.length} sin pistas',
        excludeSemantics: true,
        child: QuestionProgress(done: _alone, total: _list.length, label: 'Estrella'),
      ),
      const SizedBox(height: 20),
      Wrap(
        alignment: WrapAlignment.center,
        spacing: 12,
        runSpacing: 12,
        children: [
          SizedBox(
            width: 260,
            child: BigActionButton(
              label: 'Jugar otra vez',
              icon: Icons.replay_rounded,
              color: AppColors.sky,
              onPressed: _again,
            ),
          ),
          SizedBox(
            width: 260,
            child: BigActionButton(
              label: 'Volver',
              icon: Icons.arrow_back_rounded,
              color: AppColors.grape,
              onPressed: () => Navigator.of(context).maybePop(),
            ),
          ),
        ],
      ),
    ],
  );

  Widget _play(bool wide) {
    final r = _round;
    final picture = dictation.type == DictationType.syllable ? null : dictation.picture;
    return Column(
      children: [
        ReadingVoiceNotice(voice: _voice!),
        Text(
          instruction,
          style: fredoka(22, color: AppColors.ink),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        ReadingProgressBar(done: _index, total: _list.length, label: 'Dictado', color: color),
        const SizedBox(height: 10),
        if (!dictation.audio.recorded) const _AudioSource(),
        if (picture != null) ...[
          const SizedBox(height: 8),
          Semantics(
            image: true,
            label: dictation.type == DictationType.word
                ? 'Imagen de la palabra'
                : 'Ilustración de la oración',
            excludeSemantics: true,
            child: SizedBox(
              height: wide ? 170 : 130,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(22),
                child: SpeechPictureView(picture: picture, tint: color),
              ),
            ),
          ),
        ],
        const SizedBox(height: 10),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 10,
          runSpacing: 10,
          children: [
            _AudioButton(
              icon: Icons.volume_up_rounded,
              label: 'Escuchar',
              semantic: 'Escuchar el dictado',
              color: AppColors.sky,
              onPressed: () => _listen(),
            ),
            _AudioButton(
              icon: Icons.slow_motion_video_rounded,
              label: 'Lento',
              semantic: 'Escuchar el dictado despacio',
              color: AppColors.grape,
              onPressed: () => _listen(ReadingSpeed.slow),
            ),
            _AudioButton(
              icon: Icons.stop_rounded,
              label: 'Parar',
              semantic: 'Parar el audio',
              color: AppColors.coral,
              onPressed: () => unawaited(_voice!.stop()),
            ),
          ],
        ),
        const SizedBox(height: 14),
        if (mode == DictationMode.keyboard) _keyboard(wide) else _cards(wide),
        if (r.hints >= 2) _hintPanel(),
        const SizedBox(height: 12),
        if (r.solved) ..._solvedFeedback() else if (r.last != null) _wrongFeedback(r.last!),
        const SizedBox(height: 12),
        if (!r.solved)
          Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 12,
            runSpacing: 12,
            children: [
              KidIconButton(
                icon: Icons.lightbulb_rounded,
                label: r.hints >= DictationRound.maxHints
                    ? 'Pistas usadas'
                    : 'Pista ${r.hints + 1} de ${DictationRound.maxHints}',
                color: AppColors.sun,
                showLabel: true,
                onPressed: r.hints >= DictationRound.maxHints ? null : _hint,
              ),
              SizedBox(
                width: 260,
                child: BigActionButton(
                  label: 'Comprobar',
                  icon: Icons.check_rounded,
                  color: AppColors.leaf,
                  onPressed: r.ready ? _check : null,
                ),
              ),
            ],
          )
        else
          SizedBox(
            width: 260,
            child: BigActionButton(
              label: _index == _list.length - 1 ? 'Terminar' : 'Siguiente',
              icon: Icons.arrow_forward_rounded,
              color: AppColors.sky,
              onPressed: _next,
            ),
          ),
      ],
    );
  }

  // ---------------------------------------------------------- tarjetas
  Widget _cards(bool wide) {
    final r = _round;
    final sentence = dictation.type == DictationType.sentence;
    final marked = r.last?.marked ?? const <int>{};
    Widget card(String text, {VoidCallback? onTap, bool flagged = false, bool solved = false}) {
      final c = solved ? AppColors.leaf : color;
      final child = sentence
          ? WordChip(text: text, color: c, onTap: onTap)
          : SyllableCard(text: text, color: c, size: wide ? 84 : 72, selected: solved, onTap: onTap);
      if (!flagged) return child;
      return _Flagged(child: child);
    }

    return Column(
      children: [
        Semantics(
          container: true,
          label: r.placed.isEmpty
              ? 'Tu respuesta: vacía'
              : 'Tu respuesta: ${r.built.join(sentence ? ' ' : '')}',
          child: Container(
            width: double.infinity,
            constraints: const BoxConstraints(minHeight: 96),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF1FBF6),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: r.solved ? AppColors.leaf : color, width: r.solved ? 5 : 3),
            ),
            child: r.placed.isEmpty
                ? Center(
                    child: Text(
                      sentence ? 'Toca las palabras en orden' : 'Toca las sílabas',
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  )
                : Wrap(
                    alignment: WrapAlignment.center,
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final (slot, i) in r.placed.indexed)
                        card(
                          dictation.cards[i],
                          flagged: marked.contains(slot),
                          solved: r.solved,
                          onTap: r.solved ? null : () => _unplace(slot),
                        ),
                    ],
                  ),
          ),
        ),
        if (!r.solved && r.placed.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              'Toca una tarjeta de tu respuesta para quitarla.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        const SizedBox(height: 14),
        if (!r.solved)
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 12,
            runSpacing: 12,
            children: [for (final i in r.bank) card(dictation.cards[i], onTap: () => _place(i))],
          ),
      ],
    );
  }

  // ---------------------------------------------------------- teclado
  Widget _keyboard(bool wide) {
    final r = _round;
    return Column(
      children: [
        Semantics(
          textField: true,
          label: 'Escribe aquí lo que escuchas',
          child: TextField(
            controller: _text,
            focusNode: _focus,
            enabled: !r.solved,
            autocorrect: false,
            enableSuggestions: false,
            textCapitalization: TextCapitalization.none,
            keyboardType: TextInputType.text,
            textInputAction: TextInputAction.done,
            textAlign: TextAlign.center,
            style: fredoka(wide ? 40 : 32, color: AppColors.ink),
            decoration: InputDecoration(
              hintText: 'Escribe aquí',
              filled: true,
              fillColor: r.solved ? const Color(0xFFE8F8EE) : Colors.white,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(24),
                borderSide: const BorderSide(color: color, width: 3),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(24),
                borderSide: const BorderSide(color: AppColors.sky, width: 4),
              ),
              disabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(24),
                borderSide: const BorderSide(color: AppColors.leaf, width: 5),
              ),
            ),
            onChanged: (v) => setState(() {
              r.typed = v;
              r.last = null;
            }),
            onSubmitted: (_) => _check(),
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final c in const ['á', 'é', 'í', 'ó', 'ú', 'ñ'])
              _LetterKey(letter: c, onTap: r.solved ? null : () => _insert(c)),
          ],
        ),
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            'Letras con tilde y la ñ, por si no están en tu teclado.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ),
      ],
    );
  }

  void _insert(String c) {
    final sel = _text.selection;
    final t = _text.text;
    final start = sel.isValid ? sel.start : t.length;
    final end = sel.isValid ? sel.end : t.length;
    final next = t.replaceRange(start, end, c);
    _text.value = TextEditingValue(
      text: next,
      selection: TextSelection.collapsed(offset: start + c.length),
    );
    setState(() {
      _round.typed = next;
      _round.last = null;
    });
  }

  // ---------------------------------------------------------- pistas
  Widget _hintPanel() {
    final r = _round;
    final d = dictation;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF8E1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.sun, width: 2),
      ),
      child: Column(
        children: [
          Semantics(
            label: 'Pista: tiene ${d.countLabel}',
            excludeSemantics: true,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.lightbulb_rounded, color: Color(0xFFF9A825)),
                const SizedBox(width: 6),
                Flexible(
                  child: Text('Tiene ${d.countLabel}', style: fredoka(20, color: AppColors.ink)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 6,
            runSpacing: 6,
            children: [
              for (var i = 0; i < _countOf(d); i++)
                Container(
                  constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.sun, width: 2),
                  ),
                  child: Center(
                    widthFactor: 1,
                    heightFactor: 1,
                    child: Text(
                      i == 0 && r.hints >= 3 ? _firstShown(d) : '',
                      style: fredoka(22, color: AppColors.ink),
                    ),
                  ),
                ),
            ],
          ),
          if (r.hints >= 3)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Semantics(
                label: 'Pista: empieza por ${d.firstHint}',
                excludeSemantics: true,
                child: Text('Empieza por «${_firstShown(d)}»', style: Theme.of(context).textTheme.bodyLarge),
              ),
            ),
          if (r.hints >= 4) ...[
            const SizedBox(height: 8),
            if (d.type == DictationType.syllable && d.example != null)
              Text('Como en «${d.example}»', style: Theme.of(context).textTheme.bodyLarge),
            Semantics(
              label: 'Pista: así se escribe, ${d.model}',
              excludeSemantics: true,
              child: Container(
                margin: const EdgeInsets.only(top: 6),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFFBDBDBD), width: 2, style: BorderStyle.solid),
                ),
                child: Column(
                  children: [
                    Text('Mira cómo se escribe:', style: Theme.of(context).textTheme.bodySmall),
                    Text(
                      d.type == DictationType.sentence ? d.model : d.model.toUpperCase(),
                      textAlign: TextAlign.center,
                      style: fredoka(30, color: AppColors.inkSoft),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  int _countOf(Dictation d) => switch (d.type) {
    DictationType.syllable => d.text.length,
    _ => d.target.length,
  };

  String _firstShown(Dictation d) =>
      d.type == DictationType.sentence ? d.firstHint : d.firstHint.toUpperCase();

  // ---------------------------------------------------------- corrección
  List<Widget> _solvedFeedback() {
    final r = _round;
    final d = dictation;
    return [
      const ReadingCelebration(text: DictationGameScreen.praise),
      const SizedBox(height: 10),
      Semantics(
        label: 'Respuesta correcta: ${d.text}',
        excludeSemantics: true,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFFE8F8EE),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.leaf, width: 4),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.check_circle_rounded, color: AppColors.leaf, size: 34),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  d.type == DictationType.sentence ? d.text : d.text.toUpperCase(),
                  style: fredoka(32, color: AppColors.ink),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
        ),
      ),
      if (r.last?.alternative ?? false) ...[
        const SizedBox(height: 6),
        Text(r.last!.message, style: Theme.of(context).textTheme.bodyLarge, textAlign: TextAlign.center),
      ],
      if (r.last?.tip case final tip?) ...[
        const SizedBox(height: 6),
        Text(tip, style: Theme.of(context).textTheme.bodyLarge, textAlign: TextAlign.center),
      ],
      if (r.hints > 0) ...[
        const SizedBox(height: 6),
        Text(
          'Lo lograste con ${r.hints == 1 ? 'una pista' : '${r.hints} pistas'}. ¡La próxima vez, sin ayuda!',
          style: Theme.of(context).textTheme.bodyMedium,
          textAlign: TextAlign.center,
        ),
      ],
      const SizedBox(height: 8),
      KidIconButton(
        icon: Icons.volume_up_rounded,
        label: 'Escuchar la respuesta',
        color: AppColors.sky,
        showLabel: true,
        onPressed: () => _listen(),
      ),
    ];
  }

  Widget _wrongFeedback(DictationResult result) {
    final r = _round;
    // Lo escrito, por sílabas (palabras) o por palabras (oraciones), con las
    // partes que hay que revisar marcadas (con icono, no solo color).
    final typedParts = mode != DictationMode.keyboard
        ? const <String>[]
        : dictation.type == DictationType.sentence
        ? r.typed.trim().split(RegExp(r'\s+'))
        : Syllabifier.split(r.typed.trim().toLowerCase().replaceAll(' ', ''));
    return Column(
      children: [
        const ReadingTryAgain(text: DictationGameScreen.tryAgain),
        const SizedBox(height: 8),
        Semantics(
          liveRegion: true,
          label: result.message,
          excludeSemantics: true,
          child: Text(
            result.message,
            style: fredoka(19, color: AppColors.ink),
            textAlign: TextAlign.center,
          ),
        ),
        if (typedParts.length > 1 && result.marked.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final (i, p) in typedParts.indexed)
                result.marked.contains(i) ? _Flagged(child: _Part(text: p)) : _Part(text: p),
            ],
          ),
        ],
        const SizedBox(height: 6),
        Text(
          'Intento ${r.attempts}. Puedes escuchar otra vez, pedir una pista o corregir.',
          style: Theme.of(context).textTheme.bodyMedium,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _Part extends StatelessWidget {
  const _Part({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
    child: Text(text, style: fredoka(24, color: AppColors.ink)),
  );
}

/// Marca una parte que hay que revisar: borde, subrayado y un signo (no solo color).
class _Flagged extends StatelessWidget {
  const _Flagged({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    hint: 'Hay que revisarla',
    child: Stack(
      clipBehavior: Clip.none,
      children: [
        Container(
          padding: const EdgeInsets.only(bottom: 4),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: AppColors.coral, width: 5)),
          ),
          child: child,
        ),
        const Positioned(
          right: -8,
          top: -10,
          child: Icon(Icons.error_rounded, color: AppColors.coral, size: 24),
        ),
      ],
    ),
  );
}

class _AudioButton extends StatelessWidget {
  const _AudioButton({
    required this.icon,
    required this.label,
    required this.semantic,
    required this.color,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final String semantic;
  final Color color;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 106,
    child: SpeechActionButton(
      icon: icon,
      label: label,
      semanticLabel: semantic,
      color: color,
      onPressed: onPressed,
    ),
  );
}

class _LetterKey extends StatelessWidget {
  const _LetterKey({required this.letter, required this.onTap});
  final String letter;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: 'Escribir $letter',
    excludeSemantics: true,
    onTap: onTap,
    child: Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          width: 52,
          height: 52,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: ReadingDictationScreen.color, width: 2),
          ),
          child: Text(letter, style: fredoka(26, color: AppColors.ink)),
        ),
      ),
    ),
  );
}

/// Indica que el dictado se oye con la voz del dispositivo porque aún no hay
/// grabación.
class _AudioSource extends StatelessWidget {
  const _AudioSource();

  static const text = 'Sin grabación: se oye con la voz del dispositivo.';

  @override
  Widget build(BuildContext context) => Semantics(
    label: text,
    excludeSemantics: true,
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: const Color(0xFFF1F1F1), borderRadius: BorderRadius.circular(12)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.record_voice_over_outlined, size: 18, color: AppColors.inkSoft),
          const SizedBox(width: 6),
          Flexible(child: Text(text, style: Theme.of(context).textTheme.bodySmall)),
        ],
      ),
    ),
  );
}
