import 'dart:async';

import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/practice_sheet.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';

const _verbColor = Color(0xFFFFA726);

/// «Aprendo los verbos»: los 15 verbos y sus juegos.
class VerbsScreen extends StatelessWidget {
  const VerbsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Aprendo los verbos',
      titleIcon: Icons.directions_run_rounded,
      accent: _verbColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: speech,
          builder: (context, _) => AdaptiveGrid(
            itemCount: content.verbs.length + 1,
            minTileWidth: 150,
            childAspectRatio: 0.9,
            itemBuilder: (context, i) {
              if (i == 0) {
                return HomeMenuCard(
                  title: 'Juegos de verbos',
                  subtitle: '¡A jugar con los verbos!',
                  color: const Color(0xFFFFD27A),
                  art: const Icon(Icons.extension_rounded, size: 72, color: Colors.white),
                  onTap: () => Navigator.of(context).pushNamed(AppRoutes.speechVerbGames),
                );
              }
              final v = content.verbs[i - 1];
              final heard = speech.progress.verbsHeard.contains(v.id);
              return HomeMenuCard(
                title: v.infinitive.toUpperCase(),
                subtitle: heard ? '¡Ya lo practicaste!' : 'Yo ${v.form(VerbPerson.yo)}',
                color: const Color(0xFFFFE0B2),
                art: Padding(
                  padding: const EdgeInsets.all(4),
                  child: SpeechPictureView(picture: v.picture, tint: _verbColor),
                ),
                onTap: () =>
                    Navigator.of(context).pushNamed(AppRoutes.speechVerb, arguments: SpeechVerbArgs(v.id)),
              );
            },
          ),
        ),
      ),
    );
  }
}

/// Un verbo: su dibujo y el presente con oraciones («Yo como una manzana.»).
/// Cada línea se escucha al tocarla; «Escuchar todo» las dice seguidas.
class VerbScreen extends StatelessWidget {
  const VerbScreen({super.key, required this.verbId});

  final String verbId;

  @override
  Widget build(BuildContext context) {
    return SpeechContentBuilder(
      builder: (context, content) {
        final i = content.verbs.indexWhere((v) => v.id == verbId);
        if (i < 0) {
          return KidScaffold(
            title: 'Aprendo los verbos',
            accent: _verbColor,
            body: const Center(child: Text('No encontramos este verbo.')),
          );
        }
        return _VerbView(verbs: content.verbs, start: i);
      },
    );
  }
}

class _VerbView extends StatefulWidget {
  const _VerbView({required this.verbs, required this.start});

  final List<SpeechVerb> verbs;
  final int start;

  @override
  State<_VerbView> createState() => _VerbViewState();
}

class _VerbViewState extends State<_VerbView> {
  late int _index = widget.start;
  VerbPerson? _speaking;

  SpeechVerb get _v => widget.verbs[_index];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _sayVerb();
    });
  }

  void _sayVerb({bool slow = false}) {
    speak(context, _v.infinitive, slow: slow);
    AppServices.of(context).speech.markVerbHeard(_v.id);
  }

  void _sayLine(VerbPerson p) {
    setState(() => _speaking = p);
    speak(context, _v.sentence(p));
    AppServices.of(context).speech.markVerbHeard(_v.id);
  }

  Future<void> _sayAll() async {
    final audio = AppServices.of(context).audio;
    AppServices.of(context).speech.markVerbHeard(_v.id);
    final verb = _v;
    for (final p in VerbPerson.values) {
      if (!mounted || verb != _v) return;
      setState(() => _speaking = p);
      await audio.say(verb.sentence(p));
    }
    if (mounted) setState(() => _speaking = null);
  }

  void _go(int delta) {
    final i = _index + delta;
    if (i < 0 || i >= widget.verbs.length) return;
    setState(() {
      _index = i;
      _speaking = null;
    });
    _sayVerb();
  }

  @override
  Widget build(BuildContext context) {
    final v = _v;
    final ink = Color.lerp(_verbColor, const Color(0xFF2A2350), 0.65)!;
    return KidScaffold(
      title: v.infinitive[0].toUpperCase() + v.infinitive.substring(1),
      titleIcon: Icons.directions_run_rounded,
      accent: _verbColor,
      backLabel: 'Volver a los verbos',
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          Row(
            children: [
              SizedBox(
                width: 120,
                height: 120,
                child: SpeechPictureView(picture: v.picture, tint: _verbColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Semantics(
                      header: true,
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(v.infinitive.toUpperCase(), style: fredoka(44, color: ink)),
                      ),
                    ),
                    Text('Así se dice ahora (presente):', style: Theme.of(context).textTheme.bodyLarge),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          for (final p in VerbPerson.values) ...[
            _VerbLine(person: p, verb: v, speaking: _speaking == p, onTap: () => _sayLine(p)),
            const SizedBox(height: 8),
          ],
          const SizedBox(height: 8),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            alignment: WrapAlignment.center,
            children: [
              SizedBox(
                width: 96,
                child: SpeechActionButton(
                  icon: Icons.arrow_back_rounded,
                  label: 'Anterior',
                  color: AppColors.inkSoft,
                  onPressed: _index == 0 ? null : () => _go(-1),
                ),
              ),
              SizedBox(
                width: 120,
                child: SpeechActionButton(
                  icon: Icons.playlist_play_rounded,
                  label: 'Escuchar todo',
                  color: const Color(0xFF29B6F6),
                  onPressed: () => unawaited(_sayAll()),
                ),
              ),
              SizedBox(
                width: 96,
                child: SpeechActionButton(
                  icon: Icons.slow_motion_video_rounded,
                  label: 'Despacio',
                  color: const Color(0xFFAB47BC),
                  onPressed: () => _sayVerb(slow: true),
                ),
              ),
              if (practiceAllowed(context))
                SizedBox(
                  width: 96,
                  child: SpeechActionButton(
                    icon: Icons.mic_rounded,
                    label: 'Practicar',
                    color: const Color(0xFFE53950),
                    onPressed: () => showPracticeSheet(context, v.sentence(_speaking ?? VerbPerson.yo)),
                  ),
                ),
              SizedBox(
                width: 96,
                child: SpeechActionButton(
                  icon: Icons.arrow_forward_rounded,
                  label: 'Siguiente',
                  color: speechAccent,
                  onPressed: _index == widget.verbs.length - 1 ? null : () => _go(1),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Una línea de la conjugación: la persona, la oración con el verbo resaltado.
class _VerbLine extends StatelessWidget {
  const _VerbLine({required this.person, required this.verb, required this.speaking, required this.onTap});

  final VerbPerson person;
  final SpeechVerb verb;
  final bool speaking;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ink = Color.lerp(_verbColor, const Color(0xFF2A2350), 0.65)!;
    final base = fredoka(24, color: ink, weight: FontWeight.w500);
    return Semantics(
      container: true,
      button: true,
      label: verb.sentence(person),
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: speaking ? const Color(0xFFFFF3E0) : Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: speaking ? _verbColor : _verbColor.withValues(alpha: 0.35),
              width: speaking ? 4 : 2,
            ),
          ),
          child: Row(
            children: [
              SizedBox(
                width: 52,
                height: 52,
                child: SpeechPictureView(picture: IconPicture(person.icon, null), tint: _verbColor),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text.rich(
                  TextSpan(
                    style: base,
                    children: [
                      TextSpan(text: '${person.label} '),
                      TextSpan(
                        text: verb.form(person),
                        style: fredoka(26, color: const Color(0xFFE65100)),
                      ),
                      TextSpan(text: ' ${verb.complement}.'),
                    ],
                  ),
                ),
              ),
              Icon(Icons.volume_up_rounded, color: _verbColor.withValues(alpha: 0.8)),
            ],
          ),
        ),
      ),
    );
  }
}
