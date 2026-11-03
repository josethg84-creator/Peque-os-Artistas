import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_activities.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

/// Pantalla común de las actividades con preguntas («Completa la oración»,
/// «¿Pregunta o afirmación?», «Juegos de verbos», «Escucho y comprendo»).
///
/// Cada pregunta se dice en voz alta y se puede volver a escuchar. Un error no
/// castiga: Lolo anima y, al segundo intento, la respuesta correcta brilla.
class SpeechQuizScreen extends StatelessWidget {
  const SpeechQuizScreen({super.key, required this.quiz, this.seed});

  final SpeechQuizKind quiz;

  /// Para las pruebas: preguntas siempre iguales.
  final int? seed;

  static const icons = {
    SpeechQuizKind.complete: Icons.edit_note_rounded,
    SpeechQuizKind.questionOrStatement: Icons.help_center_rounded,
    SpeechQuizKind.verbs: Icons.directions_run_rounded,
    SpeechQuizKind.comprehension: Icons.hearing_rounded,
  };

  static const routes = {
    SpeechQuizKind.complete: AppRoutes.speechComplete,
    SpeechQuizKind.questionOrStatement: AppRoutes.speechQuestion,
    SpeechQuizKind.verbs: AppRoutes.speechVerbGames,
    SpeechQuizKind.comprehension: AppRoutes.speechListen,
  };

  static const colors = {
    SpeechQuizKind.complete: Color(0xFF26A69A),
    SpeechQuizKind.questionOrStatement: Color(0xFF7E57C2),
    SpeechQuizKind.verbs: Color(0xFFFFA726),
    SpeechQuizKind.comprehension: Color(0xFFFF8A65),
  };

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: quiz.title,
      titleIcon: icons[quiz],
      accent: colors[quiz]!,
      body: SpeechContentBuilder(
        builder: (context, content) => SpeechQuizBody(
          build: (random) => quiz.build(content, random),
          seed: seed,
          color: colors[quiz]!,
          repeatRoute: routes[quiz],
          onFinished: () => AppServices.of(context).speech.markActivityDone(quiz.kind),
        ),
      ),
    );
  }
}

/// Las preguntas, una a una, con sus respuestas en tarjetas. Se reutiliza en
/// todas las actividades con preguntas (también en los cuentos y en «Escucho
/// y respondo»).
class SpeechQuizBody extends StatefulWidget {
  const SpeechQuizBody({
    super.key,
    required this.build,
    required this.color,
    this.seed,
    this.onFinished,
    this.onAnswered,
    this.finishedExtra,
    this.slowButton = false,
    this.repeatRoute,
  });

  /// Crea las preguntas (con el azar dado, para poder repetirlas en pruebas).
  final List<QuizQuestion> Function(Random random) build;
  final Color color;
  final int? seed;

  /// Al terminar todas las preguntas.
  final VoidCallback? onFinished;

  /// Al acertar cada pregunta (su índice).
  final void Function(int index)? onAnswered;

  /// Algo más en la pantalla final (por ejemplo, ordenar las escenas).
  final Widget? finishedExtra;

  /// Botón «Despacio» para volver a oír la pregunta lentamente.
  final bool slowButton;

  /// Si se indica, pedir «Escuchar» o «Despacio» se anota en el progreso de
  /// esa actividad (para ofrecer más práctica; nunca penaliza).
  final String? repeatRoute;

  @override
  State<SpeechQuizBody> createState() => _QuizState();
}

class _QuizState extends State<SpeechQuizBody> {
  late Random _random = Random(widget.seed);
  late List<QuizQuestion> _questions = widget.build(_random);
  int _index = 0;
  int _misses = 0;
  bool _solved = false;
  final _wrong = <int>{};

  /// Pasos ya tocados de una instrucción en orden.
  int _step = 0;

  QuizQuestion get _q => _questions[_index];
  bool get _finished => _index >= _questions.length;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _ask());
  }

  void _ask({bool slow = false}) {
    if (!mounted || _finished) return;
    speak(context, _q.speech, slow: slow);
  }

  void _repeat({bool slow = false}) {
    if (widget.repeatRoute case final route?) AppServices.of(context).speech.markRepeat(route);
    _ask(slow: slow);
  }

  int get _expected => _q.steps?[_step] ?? _q.answer;

  void _answer(int i) {
    if (_solved || _finished) return;
    final audio = AppServices.of(context).audio;
    final steps = _q.steps;
    if (steps != null && i == _expected && _step < steps.length - 1) {
      // Un paso bien hecho de la instrucción: falta el siguiente.
      setState(() {
        _step++;
        _misses = 0;
        _wrong.clear();
      });
      unawaited(audio.play(SoundCue.correct));
      speak(context, '¡Bien! ¿Y después?');
      return;
    }
    // Tocar otra vez un paso ya hecho no cuenta como error.
    if (steps != null && steps.take(_step).contains(i)) return;
    if (i == _expected) {
      setState(() => _solved = true);
      AppServices.of(context).speech.markAnswer();
      widget.onAnswered?.call(_index);
      unawaited(audio.play(SoundCue.correct));
      speak(context, _q.afterCorrect ?? '¡Muy bien!');
    } else {
      setState(() {
        _misses++;
        _wrong.add(i);
      });
      unawaited(audio.play(SoundCue.tryAgain));
      speak(context, _misses >= 2 ? 'Mira, la que brilla es la correcta.' : '¡Casi! Prueba otra vez.');
    }
  }

  void _next() {
    setState(() {
      _index++;
      _misses = 0;
      _solved = false;
      _wrong.clear();
      _step = 0;
    });
    if (_finished) {
      widget.onFinished?.call();
      unawaited(AppServices.of(context).audio.play(SoundCue.celebrate));
      speak(context, '¡Terminaste! ¡Qué bien lo has hecho!');
    } else {
      _ask();
    }
  }

  void _again() {
    setState(() {
      _random = Random(widget.seed == null ? null : widget.seed! + 1);
      _questions = widget.build(_random);
      _index = 0;
      _misses = 0;
      _solved = false;
      _wrong.clear();
      _step = 0;
    });
    _ask();
  }

  @override
  Widget build(BuildContext context) {
    if (_questions.isEmpty) return const Center(child: Text('Todavía no hay preguntas para esta actividad.'));
    if (_finished) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const LoloBubble(text: '¡Terminaste! ¡Qué bien lo has hecho!', size: 90),
              if (widget.finishedExtra case final extra?) ...[const SizedBox(height: 16), extra],
              const SizedBox(height: 24),
              Wrap(
                spacing: 16,
                runSpacing: 12,
                alignment: WrapAlignment.center,
                children: [
                  SizedBox(
                    width: 150,
                    child: SpeechActionButton(
                      icon: Icons.replay_rounded,
                      label: 'Jugar otra vez',
                      color: widget.color,
                      onPressed: _again,
                    ),
                  ),
                  SizedBox(
                    width: 150,
                    child: SpeechActionButton(
                      icon: Icons.apps_rounded,
                      label: 'Otras actividades',
                      color: speechAccent,
                      onPressed: () => Navigator.of(context).maybePop(),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }
    final q = _q;
    final text = Theme.of(context).textTheme;
    final ink = Color.lerp(widget.color, const Color(0xFF2A2350), 0.6)!;
    return LayoutBuilder(
      builder: (context, box) {
        final columns = q.options.length == 2 ? 2 : (box.maxWidth > 560 ? 3 : (q.options.length > 3 ? 2 : 3));
        final tile = min(220.0, (box.maxWidth - 32 - (columns - 1) * 12) / columns);
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            Row(
              children: [
                Expanded(
                  child: Semantics(
                    header: true,
                    child: Text(q.instruction, style: text.titleLarge?.copyWith(color: ink)),
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 96,
                  child: SpeechActionButton(
                    icon: Icons.volume_up_rounded,
                    label: 'Escuchar',
                    color: const Color(0xFF29B6F6),
                    onPressed: _repeat,
                  ),
                ),
                if (widget.slowButton) ...[
                  const SizedBox(width: 8),
                  SizedBox(
                    width: 96,
                    child: SpeechActionButton(
                      icon: Icons.slow_motion_video_rounded,
                      label: 'Despacio',
                      color: const Color(0xFF7E57C2),
                      onPressed: () => _repeat(slow: true),
                    ),
                  ),
                ],
              ],
            ),
            Text(
              'Pregunta ${_index + 1} de ${_questions.length}',
              style: fredoka(16, color: AppColors.inkSoft),
            ),
            if (q.scene case final scene?) ...[
              const SizedBox(height: 12),
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Semantics(
                    container: true,
                    image: true,
                    label: 'Dibujo para mirar',
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(24),
                      child: SpeechPictureView(picture: scene, tint: widget.color),
                    ),
                  ),
                ),
              ),
            ],
            if (q.steps case final steps?)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  _solved ? '¡Hecho en orden!' : 'Paso ${_step + 1} de ${steps.length}',
                  style: fredoka(18, color: ink),
                ),
              ),
            if (q.prompt != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: widget.color.withValues(alpha: 0.5), width: 3),
                ),
                child: Text(
                  _solved && q.afterCorrect != null && q.prompt!.contains('___')
                      ? q.afterCorrect!
                      : q.prompt!,
                  textAlign: TextAlign.center,
                  style: fredoka(30, color: ink),
                ),
              ),
            ],
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                for (final (i, o) in q.options.indexed)
                  SizedBox(
                    width: tile,
                    child: _OptionCard(
                      option: o,
                      color: widget.color,
                      order: switch (q.steps?.indexOf(i)) {
                        final k? when k >= 0 && (k < _step || _solved) => k + 1,
                        _ => null,
                      },
                      state: _solved && i == q.answer || (q.steps?.take(_step).contains(i) ?? false)
                          ? _OptionState.right
                          : _wrong.contains(i)
                          ? _OptionState.wrong
                          : (_misses >= 2 && i == _expected ? _OptionState.hint : _OptionState.normal),
                      onTap: () => _answer(i),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            if (_solved)
              Center(
                child: SizedBox(
                  width: 200,
                  child: SpeechActionButton(
                    icon: Icons.arrow_forward_rounded,
                    label: _index == _questions.length - 1 ? 'Terminar' : 'Siguiente',
                    color: speechAccent,
                    onPressed: _next,
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

enum _OptionState { normal, right, wrong, hint }

class _OptionCard extends StatelessWidget {
  const _OptionCard({
    required this.option,
    required this.color,
    required this.state,
    required this.onTap,
    this.order,
  });

  final QuizOption option;

  /// En una instrucción en orden: el número del paso ya hecho.
  final int? order;
  final Color color;
  final _OptionState state;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final border = switch (state) {
      _OptionState.right => const Color(0xFF43A047),
      _OptionState.hint => AppColors.sun,
      _OptionState.wrong => const Color(0xFFBDBDBD),
      _OptionState.normal => color.withValues(alpha: 0.55),
    };
    final ink = Color.lerp(color, const Color(0xFF2A2350), 0.6)!;
    final picture = option.picture;
    final badge = option.badge;
    return Semantics(
      container: true,
      button: true,
      label: order == null ? option.label : '${option.label}, paso $order',
      selected: state == _OptionState.right,
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: state == _OptionState.wrong ? 0.45 : 1,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: state == _OptionState.right ? const Color(0xFFE8F5E9) : Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: border, width: state == _OptionState.normal ? 3 : 6),
              boxShadow: [
                BoxShadow(color: border.withValues(alpha: 0.5), offset: const Offset(0, 4)),
                const BoxShadow(color: Color(0x1A000000), blurRadius: 8, offset: Offset(0, 6)),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (picture != null)
                  Stack(
                    children: [
                      SpeechPictureView(picture: picture, tint: color),
                      if (badge != null)
                        Positioned(
                          right: 0,
                          bottom: 0,
                          width: 54,
                          height: 54,
                          child: Container(
                            decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                            padding: const EdgeInsets.all(2),
                            child: SpeechPictureView(picture: badge, tint: color),
                          ),
                        ),
                      if (order != null)
                        Positioned(
                          left: 0,
                          top: 0,
                          child: Container(
                            width: 40,
                            height: 40,
                            alignment: Alignment.center,
                            decoration: const BoxDecoration(color: Color(0xFF43A047), shape: BoxShape.circle),
                            child: Text('$order', style: fredoka(24, color: Colors.white)),
                          ),
                        ),
                    ],
                  )
                else
                  AspectRatio(
                    aspectRatio: 1.6,
                    child: Center(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(option.glyph ?? option.label, style: fredoka(48, color: ink)),
                      ),
                    ),
                  ),
                if (option.showLabel &&
                    (picture != null || option.glyph != null && option.glyph != option.label))
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(option.label, style: fredoka(22, color: ink)),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
