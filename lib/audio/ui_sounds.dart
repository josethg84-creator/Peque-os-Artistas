import 'dart:async';

import 'package:flutter/widgets.dart';

import '../services/app_services.dart';
import 'app_audio.dart';

/// Devuelve [action] precedida del efecto [cue] (o `null` si no hay acción, así
/// el botón sigue apareciendo desactivado).
VoidCallback? withSound(BuildContext context, SoundCue cue, VoidCallback? action, {int? variant}) {
  if (action == null) return null;
  return () {
    // Lectura puntual (sin dependencia): estamos en un toque, no en build.
    final audio = context.getInheritedWidgetOfExactType<AppServices>()?.audio;
    if (audio != null) unawaited(audio.play(cue, variant: variant));
    action();
  };
}
