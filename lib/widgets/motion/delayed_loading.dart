import 'dart:async';

import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_motion.dart';

/// Indicador de carga discreto que solo aparece si la espera supera [delay]:
/// en las cargas rápidas no hay parpadeo de un indicador que no hacía falta.
class DelayedLoading extends StatefulWidget {
  const DelayedLoading({super.key, required this.message, this.color = AppColors.coral});

  final String message;
  final Color color;

  static const delay = Duration(milliseconds: 300);

  @override
  State<DelayedLoading> createState() => _DelayedLoadingState();
}

class _DelayedLoadingState extends State<DelayedLoading> {
  Timer? _timer;
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    _timer = Timer(DelayedLoading.delay, () {
      if (mounted) setState(() => _visible = true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: AnimatedOpacity(
        opacity: _visible ? 1 : 0,
        duration: AppMotion.of(context, AppMotion.medium),
        child: Semantics(
          liveRegion: true,
          label: widget.message,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox.square(
                dimension: 48,
                child: CircularProgressIndicator(color: widget.color, strokeWidth: 5),
              ),
              const SizedBox(height: 14),
              ExcludeSemantics(
                child: Text(
                  widget.message,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.inkSoft),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
