import 'package:flutter/material.dart';

import 'reading_progress.dart';

/// Reglas de las estrellas (Fase 7). Premian el esfuerzo y la participación,
/// nunca se comparan con otros niños y no crecen sin límite: cada motivo tiene
/// una clave única y repetir el mismo ejercicio no da más estrellas.
abstract final class StarRules {
  /// Completar (o acertar) una actividad por primera vez.
  static const complete = 1;

  /// Acertarla sin pistas (además de lo anterior), una sola vez.
  static const independent = 2;

  /// Terminar una partida completa (serie), con un máximo al día.
  static const series = 1;
  static const maxSeriesPerDay = 3;

  /// Practicar algo que costaba (acertar lo que antes se falló), una vez al
  /// día por módulo.
  static const effort = 1;

  /// Explicación para la zona de adultos.
  static const description = [
    'Completar una actividad por primera vez: $complete estrella.',
    'Resolverla sin pistas (una sola vez por actividad): $independent estrellas más.',
    'Terminar una partida completa: $series estrella (como mucho $maxSeriesPerDay al día).',
    'Volver a practicar y acertar algo que antes costó: $effort estrella (una vez al día por actividad).',
    'Repetir un ejercicio ya hecho no da más estrellas. No hay clasificaciones.',
  ];
}

/// Familia de una sílaba por su id («ma» → «m», «que» → «c», «a» → «vocales»).
String familyOfSyllable(String id) {
  if (id.startsWith('qu')) return 'c';
  if ('aeiou'.contains(id[0])) return 'vocales';
  return id[0];
}

/// Una medalla: condición comprobable sobre el progreso guardado.
class MedalDef {
  const MedalDef({
    required this.id,
    required this.name,
    required this.description,
    required this.howTo,
    required this.icon,
    required this.color,
    required this.condition,
    required this.goal,
    required this.current,
  });

  final String id;
  final String name;

  /// Qué significa (para el niño).
  final String description;

  /// Cómo se consigue (condición explicada).
  final String howTo;
  final IconData icon;
  final Color color;
  final bool Function(ReadingProgress p) condition;

  /// Cuánto falta: objetivo y valor actual (para la barra de la medalla).
  final int goal;
  final int Function(ReadingProgress p) current;

  /// Ilustración 3D (pendiente mientras no exista el archivo).
  String get image => 'assets/images/aprendo_leer/medallas/$id.webp';
}

int _syllablesCorrect(ReadingProgress p) =>
    p.achievements.syllableStats.values.where((s) => s.correct > 0).length;

int _familiesExplored(ReadingProgress p) => {
  for (final id in p.achievements.syllablesHeard) familyOfSyllable(id),
  for (final e in p.achievements.syllableStats.entries)
    if (e.value.correct > 0) familyOfSyllable(e.key),
}.length;

int _wordsCompleted(ReadingProgress p) =>
    p.completed.entries.where((e) => e.value.any(ReadingController.wordModes.contains)).length;

int _dictationsCorrect(ReadingProgress p) => p.dictations.values.where((d) => d.correct).length;
int _dictationsIndependent(ReadingProgress p) => p.dictations.values.where((d) => d.independent).length;

int _activeDays(ReadingProgress p) =>
    p.achievements.days.values.where((m) => m.values.any((n) => n > 0)).length;

int _modulesWithSuccess(ReadingProgress p) => [
  _syllablesCorrect(p) > 0,
  _wordsCompleted(p) > 0,
  p.sentencesHeard.isNotEmpty || p.questionsCorrect.isNotEmpty,
  _dictationsCorrect(p) > 0,
].where((x) => x).length;

abstract final class Medals {
  static final all = <MedalDef>[
    MedalDef(
      id: 'primera_silaba',
      name: 'Mi primera sílaba',
      description: '¡Encontraste tu primera sílaba!',
      howTo: 'Acierta una sílaba en «Escucha y encuentra» o «Une sílaba y palabra».',
      icon: Icons.abc_rounded,
      color: const Color(0xFFF48FB1),
      goal: 1,
      current: _syllablesCorrect,
      condition: (p) => _syllablesCorrect(p) >= 1,
    ),
    MedalDef(
      id: 'explorador_letras',
      name: 'Explorador de letras',
      description: 'Visitaste muchas familias de letras.',
      howTo: 'Escucha o acierta sílabas de 5 familias distintas (vocales, M, P, S…).',
      icon: Icons.explore_rounded,
      color: const Color(0xFF81D4FA),
      goal: 5,
      current: _familiesExplored,
      condition: (p) => _familiesExplored(p) >= 5,
    ),
    MedalDef(
      id: 'maestro_silabas',
      name: 'Maestro de sílabas',
      description: '¡Conoces muchísimas sílabas!',
      howTo: 'Acierta 40 sílabas distintas en los juegos de sílabas.',
      icon: Icons.school_rounded,
      color: const Color(0xFFCE93D8),
      goal: 40,
      current: _syllablesCorrect,
      condition: (p) => _syllablesCorrect(p) >= 40,
    ),
    MedalDef(
      id: 'completo_palabras',
      name: 'Completo mis palabras',
      description: 'Completaste muchas palabras.',
      howTo: 'Completa 20 palabras distintas en «Completo palabras».',
      icon: Icons.extension_rounded,
      color: const Color(0xFFFFCC80),
      goal: 20,
      current: _wordsCompleted,
      condition: (p) => _wordsCompleted(p) >= 20,
    ),
    MedalDef(
      id: 'primera_oracion',
      name: 'Mi primera oración',
      description: '¡Escuchaste tu primera oración entera!',
      howTo: 'Escucha una oración completa o responde bien su pregunta.',
      icon: Icons.menu_book_rounded,
      color: const Color(0xFFB39DDB),
      goal: 1,
      current: (p) => p.sentencesHeard.length + p.questionsCorrect.length,
      condition: (p) => p.sentencesHeard.isNotEmpty || p.questionsCorrect.isNotEmpty,
    ),
    MedalDef(
      id: 'gran_lector',
      name: 'Gran lector',
      description: 'Lees oraciones tú solo.',
      howTo: 'Lee 10 oraciones sin ayuda: responde bien su pregunta sin escucharla antes.',
      icon: Icons.auto_stories_rounded,
      color: const Color(0xFF80CBC4),
      goal: 10,
      current: (p) => p.sentencesReadAlone.length,
      condition: (p) => p.sentencesReadAlone.length >= 10,
    ),
    MedalDef(
      id: 'comprendo',
      name: 'Comprendo lo que leo',
      description: 'Entiendes lo que lees.',
      howTo: 'Responde bien 10 preguntas de «¿Qué entendiste?».',
      icon: Icons.lightbulb_rounded,
      color: const Color(0xFFFFE082),
      goal: 10,
      current: (p) => p.questionsCorrect.length,
      condition: (p) => p.questionsCorrect.length >= 10,
    ),
    MedalDef(
      id: 'primer_dictado',
      name: 'Mi primer dictado',
      description: '¡Escribiste lo que escuchaste!',
      howTo: 'Acierta un dictado en «Escucho y escribo».',
      icon: Icons.edit_rounded,
      color: const Color(0xFFA5D6A7),
      goal: 1,
      current: _dictationsCorrect,
      condition: (p) => _dictationsCorrect(p) >= 1,
    ),
    MedalDef(
      id: 'buen_escritor',
      name: 'Buen escritor',
      description: 'Escribes muy bien tú solo.',
      howTo: 'Acierta 10 dictados sin pistas.',
      icon: Icons.draw_rounded,
      color: const Color(0xFF9FA8DA),
      goal: 10,
      current: _dictationsIndependent,
      condition: (p) => _dictationsIndependent(p) >= 10,
    ),
    MedalDef(
      id: 'aprendo_cada_dia',
      name: 'Aprendo cada día',
      description: 'Practicas muchos días.',
      howTo: 'Practica en 5 días distintos.',
      icon: Icons.calendar_month_rounded,
      color: const Color(0xFFFFAB91),
      goal: 5,
      current: _activeDays,
      condition: (p) => _activeDays(p) >= 5,
    ),
    MedalDef(
      id: 'supere_desafio',
      name: 'Superé un desafío',
      description: 'No te rendiste y lo lograste.',
      howTo: 'Resuelve un ejercicio después de equivocarte 2 veces o más.',
      icon: Icons.emoji_events_rounded,
      color: const Color(0xFFFFD54F),
      goal: 1,
      current: (p) => p.achievements.overcome.length,
      condition: (p) => p.achievements.overcome.isNotEmpty,
    ),
    MedalDef(
      id: 'pequeno_gran_artista',
      name: 'Pequeño gran artista',
      description: 'Aprendiste en las cuatro actividades.',
      howTo: 'Logra algo en las 4 actividades: sílabas, palabras, oraciones y dictados.',
      icon: Icons.palette_rounded,
      color: const Color(0xFF90CAF9),
      goal: 4,
      current: _modulesWithSuccess,
      condition: (p) => _modulesWithSuccess(p) >= 4,
    ),
  ];

  static MedalDef? byId(String id) => all.where((m) => m.id == id).firstOrNull;

  /// Medallas cuya condición se cumple y aún no estaban conseguidas.
  static List<MedalDef> newlyEarned(ReadingProgress p) => [
    for (final m in all)
      if (!p.achievements.medals.containsKey(m.id) && m.condition(p)) m,
  ];
}
