import 'dart:ui';

import 'learning_level.dart';

/// Un color que se aprende. [article] permite frases como «el color rojo».
class LearnColor {
  const LearnColor(this.id, this.name, this.color);
  final String id;
  final String name;
  final Color color;
}

/// Los 11 colores del juego. Los seis primeros son los del nivel inicial.
const learnColors = <LearnColor>[
  LearnColor('rojo', 'Rojo', Color(0xFFE53935)),
  LearnColor('azul', 'Azul', Color(0xFF1E57C8)),
  LearnColor('amarillo', 'Amarillo', Color(0xFFFFD600)),
  LearnColor('verde', 'Verde', Color(0xFF2E9D3A)),
  LearnColor('naranja', 'Naranja', Color(0xFFFF8F00)),
  LearnColor('morado', 'Morado', Color(0xFF8E44AD)),
  LearnColor('rosa', 'Rosa', Color(0xFFF06292)),
  LearnColor('celeste', 'Celeste', Color(0xFF4FC3F7)),
  LearnColor('marron', 'Marrón', Color(0xFF8D5524)),
  LearnColor('negro', 'Negro', Color(0xFF212121)),
  LearnColor('blanco', 'Blanco', Color(0xFFFFFFFF)),
];

/// Colores que se parecen: en el nivel avanzado se usan como distractores.
const similarColors = <String, List<String>>{
  'rojo': ['rosa', 'naranja', 'marron'],
  'rosa': ['rojo', 'morado'],
  'azul': ['celeste', 'morado'],
  'celeste': ['azul', 'blanco'],
  'naranja': ['amarillo', 'rojo', 'marron'],
  'amarillo': ['naranja', 'blanco'],
  'verde': ['celeste', 'amarillo'],
  'morado': ['azul', 'rosa'],
  'marron': ['naranja', 'negro'],
  'negro': ['marron', 'azul'],
  'blanco': ['amarillo', 'celeste'],
};

List<LearnColor> colorsFor(LearningLevel level) =>
    level == LearningLevel.initial ? learnColors.take(6).toList() : learnColors;

enum ShapeKind { circle, square, triangle, rectangle, oval, star, heart }

class LearnShape {
  const LearnShape(this.kind, this.name, this.article, this.explanation);
  final ShapeKind kind;
  final String name;

  /// «el» o «la», para «¿Dónde está el triángulo?».
  final String article;
  final String explanation;

  String get id => kind.name;
  String get withArticle => '$article ${name.toLowerCase()}';
}

const learnShapes = <LearnShape>[
  LearnShape(ShapeKind.circle, 'Círculo', 'el', 'El círculo es redondo y no tiene esquinas.'),
  LearnShape(ShapeKind.square, 'Cuadrado', 'el', 'El cuadrado tiene 4 lados iguales.'),
  LearnShape(ShapeKind.triangle, 'Triángulo', 'el', 'El triángulo tiene 3 lados y 3 puntas.'),
  LearnShape(
    ShapeKind.rectangle,
    'Rectángulo',
    'el',
    'El rectángulo tiene 4 lados: dos largos y dos cortos.',
  ),
  LearnShape(ShapeKind.oval, 'Óvalo', 'el', 'El óvalo es redondo y alargado, como un huevo.'),
  LearnShape(ShapeKind.star, 'Estrella', 'la', 'La estrella tiene 5 puntas.'),
  LearnShape(ShapeKind.heart, 'Corazón', 'el', 'El corazón tiene dos curvas arriba y una punta abajo.'),
];

/// Formas que se confunden entre sí (nivel avanzado).
const similarShapes = <ShapeKind, List<ShapeKind>>{
  ShapeKind.circle: [ShapeKind.oval],
  ShapeKind.oval: [ShapeKind.circle],
  ShapeKind.square: [ShapeKind.rectangle],
  ShapeKind.rectangle: [ShapeKind.square],
  ShapeKind.triangle: [ShapeKind.star],
  ShapeKind.star: [ShapeKind.triangle],
  ShapeKind.heart: [ShapeKind.circle],
};

/// En el nivel inicial solo se usan las formas más distintas entre sí.
List<LearnShape> shapesFor(LearningLevel level) => level == LearningLevel.initial
    ? learnShapes
          .where(
            (s) => const {
              ShapeKind.circle,
              ShapeKind.square,
              ShapeKind.triangle,
              ShapeKind.star,
              ShapeKind.heart,
            }.contains(s.kind),
          )
          .toList()
    : learnShapes;

/// Animales del catálogo (ids de la Fase 4) con una frase sencilla.
class LearnAnimal {
  const LearnAnimal(this.drawingId, this.name, this.article, this.fact);
  final String drawingId;
  final String name;
  final String article;
  final String fact;

  String get withArticle => '$article ${name.toLowerCase()}';
}

const learnAnimals = <LearnAnimal>[
  LearnAnimal('animal_gato', 'Gato', 'el', 'El gato dice «miau» y le encanta dormir.'),
  LearnAnimal('animal_perro', 'Perro', 'el', 'El perro mueve la cola cuando está contento.'),
  LearnAnimal('animal_conejo', 'Conejo', 'el', 'El conejo tiene orejas largas y salta mucho.'),
  LearnAnimal('animal_leon', 'León', 'el', 'El león tiene una gran melena y ruge fuerte.'),
  LearnAnimal('animal_elefante', 'Elefante', 'el', 'El elefante usa su trompa para beber agua.'),
  LearnAnimal('animal_jirafa', 'Jirafa', 'la', 'La jirafa tiene el cuello muy largo.'),
  LearnAnimal('animal_oso', 'Oso', 'el', 'Al oso le gusta mucho la miel.'),
  LearnAnimal('animal_mariposa', 'Mariposa', 'la', 'La mariposa tiene alas de muchos colores.'),
  LearnAnimal('animal_pez', 'Pez', 'el', 'El pez vive en el agua y nada con sus aletas.'),
  LearnAnimal('animal_tortuga', 'Tortuga', 'la', 'La tortuga lleva su casa en la espalda.'),
];

/// Configuración de cada nivel: opciones por pregunta y preguntas por partida.
({int options, int questions}) quizSizeFor(LearningLevel level) => switch (level) {
  LearningLevel.initial => (options: 3, questions: 4),
  LearningLevel.intermediate => (options: 4, questions: 5),
  LearningLevel.advanced => (options: 4, questions: 6),
};

/// Parejas del juego de memoria por nivel: 2, 4 y 6.
int pairsFor(LearningLevel level) => switch (level) {
  LearningLevel.initial => 2,
  LearningLevel.intermediate => 4,
  LearningLevel.advanced => 6,
};

/// Dibujos del catálogo que se usan como cartas (variados y fáciles de distinguir).
const memoryCardDrawings = <String>[
  'animal_gato',
  'animal_pez',
  'fruta_manzana',
  'vehiculo_barco',
  'dinosaurio_05',
  'fantasia_robot',
  'animal_mariposa',
  'fruta_fresa',
  'vehiculo_tren',
  'animal_elefante',
  'fantasia_unicornio',
  'fruta_uvas',
];
