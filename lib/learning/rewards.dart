import 'package:flutter/material.dart';

import 'learning_level.dart';
import 'learning_progress.dart';

/// Un premio (pegatina). Celebra la participación, nunca exige perfección:
/// todos se consiguen terminando actividades, se cometan errores o no.
class Reward {
  const Reward(this.id, this.title, this.howTo, this.icon, this.color, this.isEarned);

  /// Identificador estable (se guarda en el progreso).
  final String id;
  final String title;

  /// Pista amable de cómo conseguirlo.
  final String howTo;
  final IconData icon;
  final Color color;
  final bool Function(LearningProgress progress) isEarned;
}

final rewards = <Reward>[
  Reward(
    'primera_actividad',
    'Primera actividad',
    'Termina una actividad',
    Icons.celebration_rounded,
    const Color(0xFFFF7A59),
    (p) => p.totalSessions >= 1,
  ),
  Reward(
    'explorador_colores',
    'Explorador de colores',
    'Juega a «Aprende los colores»',
    Icons.palette_rounded,
    const Color(0xFFE53935),
    (p) => p.game(GameId.colors).sessions >= 1,
  ),
  Reward(
    'experto_formas',
    'Experto en formas',
    'Juega a «Descubre las formas»',
    Icons.category_rounded,
    const Color(0xFF4FB3FF),
    (p) => p.game(GameId.shapes).sessions >= 1,
  ),
  Reward(
    'amigo_animales',
    'Amigo de los animales',
    'Juega a «Encuentra a los animales»',
    Icons.pets_rounded,
    const Color(0xFF5CC689),
    (p) => p.game(GameId.animals).sessions >= 1,
  ),
  Reward(
    'maestro_parejas',
    'Maestro de las parejas',
    'Juega a «Une las parejas»',
    Icons.style_rounded,
    const Color(0xFF9B7BEA),
    (p) => p.game(GameId.memory).sessions >= 1,
  ),
  Reward(
    'cinco_actividades',
    'Cinco actividades',
    'Termina cinco actividades',
    Icons.looks_5_rounded,
    const Color(0xFFFFC93C),
    (p) => p.totalSessions >= 5,
  ),
  Reward(
    'todos_los_juegos',
    'Gran explorador',
    'Juega a los cuatro juegos',
    Icons.emoji_events_rounded,
    const Color(0xFFFF6B8B),
    (p) => GameId.values.every((g) => p.game(g).sessions >= 1),
  ),
];

Reward? rewardById(String id) {
  for (final r in rewards) {
    if (r.id == id) return r;
  }
  return null;
}
