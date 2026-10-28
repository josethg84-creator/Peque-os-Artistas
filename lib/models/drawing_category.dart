import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Las cinco categorías de la colección. [id] coincide con el campo
/// `category` del catálogo JSON de la Fase 1.
enum DrawingCategory {
  animals('animales', 'Animales', Icons.pets_rounded, AppColors.coral, 'animal_gato'),
  vehicles('vehiculos', 'Vehículos', Icons.directions_car_rounded, AppColors.sky, 'vehiculo_autobus'),
  dinosaurs('dinosaurios', 'Dinosaurios', Icons.park_rounded, AppColors.leaf, 'dinosaurio_01'),
  fruits('frutas', 'Frutas', Icons.local_florist_rounded, AppColors.berry, 'fruta_manzana'),
  fantasy('fantasia', 'Fantasía', Icons.auto_awesome_rounded, AppColors.grape, 'fantasia_unicornio');

  const DrawingCategory(this.id, this.label, this.icon, this.color, this.coverDrawingId);

  final String id;
  final String label;
  final IconData icon;
  final Color color;

  /// Dibujo que ilustra la tarjeta de la categoría.
  final String coverDrawingId;

  static DrawingCategory? fromId(String? id) {
    for (final c in values) {
      if (c.id == id) return c;
    }
    return null;
  }
}
