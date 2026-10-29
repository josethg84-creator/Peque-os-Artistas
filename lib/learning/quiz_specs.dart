import 'package:flutter/material.dart';

import '../coloring/engine/drawing_painter.dart';
import '../coloring/engine/vector_drawing.dart';
import '../models/drawing_catalog.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../widgets/drawing_thumbnail.dart';
import 'learning_content.dart';
import 'learning_level.dart';
import 'widgets/shape_view.dart';

/// Lo que diferencia a cada juego de preguntas: los elementos, cómo se
/// pregunta, cómo se dibuja cada opción y qué se explica al acertar. La
/// pantalla y el motor ([QuizGame]) son los mismos para los tres juegos.
abstract class QuizSpec<T> {
  const QuizSpec();

  GameId get game;
  Color get accent;
  IconData get icon;
  List<T> pool(LearningLevel level);
  List<T> similarTo(T target) => const [];
  String instruction(T target);
  String name(T item);
  String explanation(T target);
  Widget? prompt(BuildContext context, T target, LearningLevel level) => null;
  Widget option(BuildContext context, T item, LearningLevel level, int index);

  /// Texto visible bajo la opción (null = sin texto).
  String? caption(T item, LearningLevel level) => null;
}

class ColorsSpec extends QuizSpec<LearnColor> {
  const ColorsSpec();

  @override
  GameId get game => GameId.colors;
  @override
  Color get accent => AppColors.coral;
  @override
  IconData get icon => Icons.palette_rounded;
  @override
  List<LearnColor> pool(LearningLevel level) => colorsFor(level);
  @override
  List<LearnColor> similarTo(LearnColor target) => [
    for (final id in similarColors[target.id] ?? const <String>[]) learnColors.firstWhere((c) => c.id == id),
  ];
  @override
  String instruction(LearnColor target) => 'Encuentra el color ${target.name.toLowerCase()}';
  @override
  String name(LearnColor item) => item.name;
  @override
  String explanation(LearnColor target) => 'Este es el color ${target.name.toLowerCase()}.';

  /// El nombre siempre se muestra: así la respuesta no depende solo del color.
  @override
  String? caption(LearnColor item, LearningLevel level) => item.name;

  @override
  Widget option(BuildContext context, LearnColor item, LearningLevel level, int index) => AspectRatio(
    aspectRatio: 1,
    child: DecoratedBox(
      decoration: BoxDecoration(
        color: item.color,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.ink.withValues(alpha: 0.35), width: 3),
      ),
      child: const Icon(Icons.brush_rounded, color: Colors.transparent),
    ),
  );
}

class ShapesSpec extends QuizSpec<LearnShape> {
  const ShapesSpec();

  /// Colores variados para las opciones: el color no da pistas.
  static const _colors = [
    AppColors.coral,
    AppColors.sky,
    AppColors.leaf,
    AppColors.grape,
    AppColors.sun,
    AppColors.berry,
  ];

  @override
  GameId get game => GameId.shapes;
  @override
  Color get accent => AppColors.sky;
  @override
  IconData get icon => Icons.category_rounded;
  @override
  List<LearnShape> pool(LearningLevel level) => shapesFor(level);
  @override
  List<LearnShape> similarTo(LearnShape target) => [
    for (final k in similarShapes[target.kind] ?? const <ShapeKind>[])
      learnShapes.firstWhere((s) => s.kind == k),
  ];
  @override
  String instruction(LearnShape target) => '¿Dónde está ${target.withArticle}?';
  @override
  String name(LearnShape item) => item.name;
  @override
  String explanation(LearnShape target) => target.explanation;

  /// Niveles inicial e intermedio: se muestra el contorno como modelo.
  @override
  Widget? prompt(BuildContext context, LearnShape target, LearningLevel level) =>
      level == LearningLevel.advanced ? null : ShapeView(kind: target.kind, outline: true);

  @override
  Widget option(BuildContext context, LearnShape item, LearningLevel level, int index) =>
      ShapeView(kind: item.kind, color: _colors[index % _colors.length]);
}

class AnimalsSpec extends QuizSpec<LearnAnimal> {
  const AnimalsSpec(this.catalog);

  final DrawingCatalog catalog;

  @override
  GameId get game => GameId.animals;
  @override
  Color get accent => AppColors.leaf;
  @override
  IconData get icon => Icons.pets_rounded;

  /// Solo animales cuyo dibujo existe en el catálogo.
  @override
  List<LearnAnimal> pool(LearningLevel level) =>
      learnAnimals.where((a) => catalog.byId(a.drawingId) != null).toList();
  @override
  String instruction(LearnAnimal target) => '¿Dónde está ${target.withArticle}?';
  @override
  String name(LearnAnimal item) => item.name;
  @override
  String explanation(LearnAnimal target) => target.fact;

  @override
  Widget option(BuildContext context, LearnAnimal item, LearningLevel level, int index) {
    final drawing = catalog.byId(item.drawingId)!;
    // Nivel avanzado: siluetas hechas con el propio dibujo vectorial.
    if (level == LearningLevel.advanced) return AnimalSilhouette(file: drawing.file);
    return DrawingThumbnail(asset: drawing.thumbnailAsset);
  }
}

/// Silueta de un dibujo del catálogo: todas sus zonas (salvo el fondo) en un
/// color oscuro, con el mismo pintor que el lienzo. No se duplican imágenes.
class AnimalSilhouette extends StatefulWidget {
  const AnimalSilhouette({super.key, required this.file});

  final String file;

  @override
  State<AnimalSilhouette> createState() => _AnimalSilhouetteState();
}

class _AnimalSilhouetteState extends State<AnimalSilhouette> {
  Future<VectorDrawing>? _vector;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _vector ??= AppServices.of(context).drawings.load(widget.file);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<VectorDrawing>(
      future: _vector,
      builder: (context, snapshot) {
        final vector = snapshot.data;
        if (vector == null) {
          return snapshot.hasError ? const MissingImagePlaceholder() : const SizedBox.shrink();
        }
        final colors = {
          for (final r in vector.regions)
            if (r.id != VectorDrawing.backgroundId) r.id: const Color(0xFF3B3355),
        };
        return AspectRatio(
          aspectRatio: 1,
          child: CustomPaint(
            painter: DrawingPainter(drawing: vector, colors: FixedRegionColors(colors)),
          ),
        );
      },
    );
  }
}
