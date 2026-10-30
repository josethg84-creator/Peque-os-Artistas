import 'package:flutter/widgets.dart';

import '../services/app_services.dart';
import 'app_audio.dart';

/// Indica qué música corresponde a una pantalla (o silencio con `null`).
/// Mientras la pantalla está abierta su zona es la última, así que manda; al
/// cerrarla vuelve la música de la pantalla anterior.
class MusicZone extends StatefulWidget {
  const MusicZone({super.key, required this.track, required this.child});

  final MusicTrack? track;
  final Widget child;

  @override
  State<MusicZone> createState() => _MusicZoneState();
}

class _MusicZoneState extends State<MusicZone> {
  LearningAudio? _audio;
  Object? _zone;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_zone != null) return;
    _audio = AppServices.maybeOf(context)?.audio;
    _zone = _audio?.enterMusicZone(widget.track);
  }

  @override
  void dispose() {
    final zone = _zone;
    if (zone != null) _audio?.exitMusicZone(zone);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
