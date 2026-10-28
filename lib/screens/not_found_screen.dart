import 'package:flutter/material.dart';

import '../navigation/app_router.dart';
import '../widgets/empty_state.dart';

/// Destino seguro para rutas desconocidas o mal formadas.
class NotFoundScreen extends StatelessWidget {
  const NotFoundScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: EmptyState(
          icon: Icons.explore_off_rounded,
          title: 'Ups, aquí no hay nada',
          actionLabel: 'Ir al inicio',
          onAction: () => AppRouter.goHome(context),
        ),
      ),
    );
  }
}
