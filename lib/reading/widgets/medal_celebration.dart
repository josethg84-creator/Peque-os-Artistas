import 'dart:async';

import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../achievements.dart';
import '../reading_progress.dart';
import 'achievement_widgets.dart';

/// Muestra, encima de la pantalla actual, cada medalla recién conseguida:
/// la medalla, qué se consiguió y «Continuar aprendiendo». La animación es
/// breve y se quita con «Reducir animaciones»; la felicitación hablada se
/// puede apagar (perfil) y respeta el volumen de la voz.
class MedalCelebrationHost extends StatefulWidget {
  const MedalCelebrationHost({super.key, required this.child});
  final Widget child;

  @override
  State<MedalCelebrationHost> createState() => _MedalCelebrationHostState();
}

class _MedalCelebrationHostState extends State<MedalCelebrationHost> {
  ReadingController? _progress;
  MedalDef? _showing;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final p = AppServices.of(context).reading;
    if (!identical(p, _progress)) {
      _progress?.removeListener(_check);
      _progress = p..addListener(_check);
      WidgetsBinding.instance.addPostFrameCallback((_) => _check());
    }
  }

  @override
  void dispose() {
    _progress?.removeListener(_check);
    super.dispose();
  }

  void _check() {
    if (!mounted || _showing != null) return;
    final next = _progress!.takeCelebration();
    if (next == null) return;
    setState(() => _showing = next);
    if (_progress!.progress.achievements.profile.celebrationSound) {
      unawaited(
        AppServices.of(context).audio.say('¡Conseguiste la medalla ${next.name}! ${next.description}'),
      );
    }
  }

  void _close() {
    setState(() => _showing = null);
    WidgetsBinding.instance.addPostFrameCallback((_) => _check());
  }

  @override
  Widget build(BuildContext context) {
    final medal = _showing;
    return Stack(
      children: [
        widget.child,
        if (medal != null) ...[
          const ModalBarrier(color: Color(0x66000000), dismissible: false),
          Center(
            child: _CelebrationCard(medal: medal, onClose: _close),
          ),
        ],
      ],
    );
  }
}

class _CelebrationCard extends StatelessWidget {
  const _CelebrationCard({required this.medal, required this.onClose});
  final MedalDef medal;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    final still = MediaQuery.of(context).disableAnimations;
    final card = Material(
      color: Colors.transparent,
      child: Container(
        width: 340,
        margin: const EdgeInsets.all(16),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFFFFFBEA),
          borderRadius: BorderRadius.circular(30),
          border: Border.all(color: AppColors.sun, width: 4),
          boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 18, offset: Offset(0, 6))],
        ),
        child: Semantics(
          liveRegion: true,
          container: true,
          label: '¡Nueva medalla! ${medal.name}. ${medal.description}',
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ExcludeSemantics(
                child: Text('¡Nueva medalla!', style: fredoka(26, color: AppColors.ink)),
              ),
              const SizedBox(height: 10),
              MedalBadge(medal: medal, unlocked: true, size: 120),
              const SizedBox(height: 10),
              ExcludeSemantics(
                child: Text(
                  medal.name,
                  style: fredoka(24, color: AppColors.ink),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 6),
              ExcludeSemantics(
                child: Text(
                  medal.description,
                  style: Theme.of(context).textTheme.bodyLarge,
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.leaf,
                    minimumSize: const Size(0, 60),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
                  ),
                  onPressed: onClose,
                  icon: const Icon(Icons.arrow_forward_rounded),
                  label: Text('Continuar aprendiendo', style: fredoka(20, color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (still) return card;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.85, end: 1),
      duration: const Duration(milliseconds: 350),
      curve: Curves.easeOutBack,
      builder: (context, v, child) => Transform.scale(scale: v, child: child),
      child: card,
    );
  }
}
