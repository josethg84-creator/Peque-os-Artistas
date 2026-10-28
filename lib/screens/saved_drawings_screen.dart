import 'package:flutter/material.dart';

import '../navigation/app_routes.dart';
import '../theme/app_colors.dart';
import '../widgets/empty_state.dart';
import '../widgets/kid_scaffold.dart';
import '../widgets/menu_tile.dart';

/// Pantalla provisional: guardar dibujos todavía no está implementado.
class SavedDrawingsScreen extends StatelessWidget {
  const SavedDrawingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Mis dibujos',
      titleIcon: Icons.collections_rounded,
      accent: AppColors.grape,
      backLabel: 'Volver al inicio',
      badge: const ComingSoonBadge(text: 'En construcción'),
      body: EmptyState(
        icon: Icons.collections_rounded,
        color: AppColors.grape,
        title: 'Aquí verás tus dibujos',
        message: 'Muy pronto podrás guardar lo que pintes.',
        actionLabel: 'Ir a la galería',
        actionIcon: Icons.photo_library_rounded,
        onAction: () => Navigator.of(context).pushReplacementNamed(AppRoutes.categories),
      ),
    );
  }
}
