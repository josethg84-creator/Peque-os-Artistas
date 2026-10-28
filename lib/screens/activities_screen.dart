import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../widgets/adaptive_grid.dart';
import '../widgets/kid_scaffold.dart';
import '../widgets/menu_tile.dart';

/// Secciones iniciales de actividades educativas. Todavía no tienen
/// contenido: cada tarjeta está marcada como «Pronto».
class ActivitiesScreen extends StatelessWidget {
  const ActivitiesScreen({super.key});

  static const sections = [
    (Icons.palette_rounded, 'Los colores', AppColors.coral),
    (Icons.category_rounded, 'Las formas', AppColors.sky),
    (Icons.looks_3_rounded, 'Cuenta y pinta', AppColors.leaf),
    (Icons.gesture_rounded, 'Une los puntos', AppColors.grape),
  ];

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Actividades',
      titleIcon: Icons.extension_rounded,
      accent: AppColors.leaf,
      backLabel: 'Volver al inicio',
      body: AdaptiveGrid(
        itemCount: sections.length,
        minTileWidth: 200,
        maxColumns: 4,
        tileHeight: 210,
        itemBuilder: (context, index) {
          final (icon, label, color) = sections[index];
          return MenuTile(
            icon: icon,
            label: label,
            color: color,
            badge: 'Pronto',
            onTap: () => _showComingSoon(context, label),
          );
        },
      ),
    );
  }

  static void _showComingSoon(BuildContext context, String label) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: const Icon(Icons.construction_rounded, size: 48, color: AppColors.sun),
        title: Text(label, textAlign: TextAlign.center),
        content: const Text('¡Esta actividad llegará muy pronto!', textAlign: TextAlign.center),
        actions: [
          FilledButton.icon(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.check_rounded),
            label: const Text('Vale'),
          ),
        ],
      ),
    );
  }
}
