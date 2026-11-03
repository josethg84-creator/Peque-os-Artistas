import 'dart:async';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../voice_practice.dart';
import 'speech_widgets.dart';

/// ¿Se puede practicar con el micrófono? (Un adulto lo puede desactivar.)
bool practiceAllowed(BuildContext context) => AppServices.of(context).speech.progress.micAllowed;

/// Abre «Practicar»: Lolo dice [text], el niño se graba, se escucha y puede
/// repetirlo. La grabación se borra al cerrar. No se puntúa la pronunciación.
Future<void> showPracticeSheet(BuildContext context, String text) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  showDragHandle: true,
  backgroundColor: const Color(0xFFFFF8EC),
  builder: (_) => PracticeSheet(text: text),
);

enum _Stage { ready, recording, recorded, denied, failed }

class PracticeSheet extends StatefulWidget {
  const PracticeSheet({super.key, required this.text});

  final String text;

  /// Una grabación termina sola a los [maxLength].
  static const maxLength = Duration(seconds: 6);

  static const encouragement = '¡Muy bien por intentarlo!';

  @override
  State<PracticeSheet> createState() => _PracticeSheetState();
}

class _PracticeSheetState extends State<PracticeSheet> with SingleTickerProviderStateMixin {
  late VoiceRecorder _recorder;
  late final AnimationController _timer = AnimationController(vsync: this, duration: PracticeSheet.maxLength)
    ..addStatusListener((s) {
      if (s == AnimationStatus.completed && _stage == _Stage.recording) unawaited(_stop());
    });
  _Stage _stage = _Stage.ready;
  VoiceClip? _clip;
  bool _busy = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_greeted) {
      _recorder = AppServices.of(context).speech.newRecorder();
      _greeted = true;
      speak(context, 'Escucha y repite: ${widget.text}');
    }
  }

  bool _greeted = false;

  @override
  void dispose() {
    _timer.dispose();
    final clip = _clip;
    final recorder = _recorder;
    // La grabación no se guarda: se borra al cerrar.
    unawaited(() async {
      if (clip != null) await recorder.discard(clip);
      await recorder.dispose();
    }());
    super.dispose();
  }

  Future<void> _record() async {
    if (_busy) return;
    _busy = true;
    try {
      final audio = AppServices.of(context).audio;
      final allowed = await _recorder.requestPermission();
      if (!mounted) return;
      if (!allowed) {
        setState(() => _stage = _Stage.denied);
        return;
      }
      await audio.stopVoice();
      final old = _clip;
      _clip = null;
      if (old != null) await _recorder.discard(old);
      await _recorder.start();
      if (!mounted) return;
      setState(() => _stage = _Stage.recording);
      _timer.forward(from: 0);
    } catch (_) {
      if (mounted) setState(() => _stage = _Stage.failed);
    } finally {
      _busy = false;
    }
  }

  Future<void> _stop() async {
    if (_stage != _Stage.recording) return;
    _timer.stop();
    try {
      final clip = await _recorder.stop();
      if (!mounted) return;
      if (clip == null) {
        setState(() => _stage = _Stage.failed);
        return;
      }
      _clip = clip;
      setState(() => _stage = _Stage.recorded);
      AppServices.of(context).speech.markRecording();
      unawaited(AppServices.of(context).audio.play(SoundCue.star));
      speak(context, PracticeSheet.encouragement);
    } catch (_) {
      if (mounted) setState(() => _stage = _Stage.failed);
    }
  }

  Future<void> _playMine() async {
    final clip = _clip;
    if (clip == null) return;
    await AppServices.of(context).audio.stopVoice();
    await _recorder.play(clip);
  }

  void _listenLolo() {
    unawaited(_recorder.stopPlaying());
    speak(context, widget.text);
  }

  @override
  Widget build(BuildContext context) {
    final bubble = switch (_stage) {
      _Stage.ready => 'Escucha y repite: «${widget.text}». Toca el micrófono para grabar tu voz.',
      _Stage.recording => '¡Te escucho! Di «${widget.text}».',
      _Stage.recorded => '${PracticeSheet.encouragement} ¿Quieres escuchar tu voz?',
      _Stage.denied => 'Para grabar tu voz, un adulto tiene que permitir el micrófono. ¡También puedes repetirlo en voz alta conmigo!',
      _Stage.failed => 'No pude grabar esta vez. ¿Lo intentamos otra vez?',
    };
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              widget.text.toUpperCase(),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: LoloBubble(text: bubble, size: 60),
            ),
            const SizedBox(height: 18),
            if (_stage == _Stage.recording) ...[
              _MicButton(label: 'Parar', icon: Icons.stop_rounded, color: AppColors.coral, onTap: _stop),
              const SizedBox(height: 12),
              AnimatedBuilder(
                animation: _timer,
                builder: (context, _) => ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: _timer.value,
                    minHeight: 10,
                    color: AppColors.coral,
                    backgroundColor: AppColors.coral.withValues(alpha: 0.2),
                  ),
                ),
              ),
            ] else
              _MicButton(
                label: _stage == _Stage.recorded ? 'Grabar otra vez' : 'Grabar',
                icon: Icons.mic_rounded,
                color: const Color(0xFFE53950),
                onTap: _record,
              ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                SizedBox(
                  width: 150,
                  child: SpeechActionButton(
                    icon: Icons.volume_up_rounded,
                    label: 'Escuchar a Lolo',
                    color: const Color(0xFF29B6F6),
                    onPressed: _stage == _Stage.recording ? null : _listenLolo,
                  ),
                ),
                if (_stage == _Stage.recorded)
                  SizedBox(
                    width: 150,
                    child: SpeechActionButton(
                      icon: Icons.hearing_rounded,
                      label: 'Escuchar mi voz',
                      color: const Color(0xFF26A69A),
                      onPressed: _playMine,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              'Tu voz no se guarda ni se envía: se borra al cerrar.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _MicButton extends StatelessWidget {
  const _MicButton({required this.label, required this.icon, required this.color, required this.onTap});

  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      button: true,
      label: label,
      excludeSemantics: true,
      onTap: onTap,
      child: GestureDetector(
        onTap: onTap,
        child: Column(
          children: [
            Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color.lerp(color, Colors.white, 0.35)!, color],
                ),
                border: Border.all(color: Colors.white, width: 4),
                boxShadow: [
                  BoxShadow(color: Color.lerp(color, Colors.black, 0.25)!, offset: const Offset(0, 5)),
                  const BoxShadow(color: Color(0x33000000), blurRadius: 12, offset: Offset(0, 8)),
                ],
              ),
              child: Icon(icon, color: Colors.white, size: 52),
            ),
            const SizedBox(height: 6),
            Text(label, style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      ),
    );
  }
}
