import 'package:flutter/material.dart';

import '../navigation/app_routes.dart';

/// Una actividad de «Aprendo a leer».
class ReadingActivity {
  const ReadingActivity({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.route,
    required this.image,
    required this.plannedImage,
    required this.imageBrief,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  /// Color pastel de la tarjeta.
  final Color color;
  final String route;

  /// Ilustración 3D que se usa ahora (una de las que ya tiene la app).
  final String image;

  /// Dónde irá su ilustración propia cuando llegue (ver
  /// `assets/images/aprendo_leer/README.md`). Mientras no exista, se usa
  /// [image].
  final String plannedImage;

  /// Qué debe mostrar esa ilustración propia.
  final String imageBrief;
}

/// Las cuatro actividades del módulo, en orden.
abstract final class ReadingActivities {
  static const folder = 'assets/images/aprendo_leer/';
  static const _speech = 'assets/images/aprendo_hablar/';

  static const syllables = ReadingActivity(
    title: 'Aprendo las sílabas',
    subtitle: '¡MA, ME, MI, MO, MU!',
    icon: Icons.abc_rounded,
    color: Color(0xFF8FCBFF), // celeste
    route: AppRoutes.readingSyllables,
    image: '${_speech}mis_primeras_palabras.webp',
    plannedImage: '${folder}aprendo_las_silabas.webp',
    imageBrief: 'Letras grandes y bloques del abecedario',
  );

  static const words = ReadingActivity(
    title: 'Completo palabras',
    subtitle: '¡Busca la sílaba que falta!',
    icon: Icons.extension_rounded,
    color: Color(0xFFFFC27A), // naranja pastel
    route: AppRoutes.readingWords,
    image: '${_speech}juegos_de_palabras.webp',
    plannedImage: '${folder}completo_palabras.webp',
    imageBrief: 'Una manzana, letras y piezas para completar palabras',
  );

  static const sentences = ReadingActivity(
    title: 'Leo oraciones',
    subtitle: '¡Leemos juntos!',
    icon: Icons.menu_book_rounded,
    color: Color(0xFFC3A9F5), // morado pastel
    route: AppRoutes.readingSentences,
    image: '${_speech}lolo_me_cuenta_un_cuento.webp',
    plannedImage: '${folder}leo_oraciones.webp',
    imageBrief: 'Un libro abierto y un niño leyendo',
  );

  static const dictation = ReadingActivity(
    title: 'Escucho y escribo',
    subtitle: '¡Escucha y forma la palabra!',
    icon: Icons.edit_rounded,
    color: Color(0xFF8EDDB8), // verde pastel
    route: AppRoutes.readingDictation,
    image: '${_speech}escucho_y_respondo.webp',
    plannedImage: '${folder}escucho_y_escribo.webp',
    imageBrief: 'Un lápiz, un cuaderno y unos audífonos',
  );

  static const all = [syllables, words, sentences, dictation];

  /// Color de acento del módulo (barra de título, botones).
  static const accent = Color(0xFF5C8DF6);
}
