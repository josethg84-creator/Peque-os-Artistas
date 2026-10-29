import 'package:flutter/material.dart';

import 'navigation/app_router.dart';
import 'navigation/app_routes.dart';
import 'services/app_services.dart';
import 'services/catalog_service.dart';
import 'services/drawing_loader.dart';
import 'services/progress_store.dart';
import 'theme/app_theme.dart';

class PequenosArtistasApp extends StatelessWidget {
  const PequenosArtistasApp({
    super.key,
    required this.catalogService,
    required this.drawingLoader,
    required this.progressStore,
  });

  final CatalogService catalogService;
  final DrawingLoader drawingLoader;
  final ProgressStore progressStore;

  /// Se respeta el tamaño de texto del sistema, con un tope para que las
  /// pantallas sigan siendo usables.
  static const maxTextScale = 1.6;

  @override
  Widget build(BuildContext context) {
    return AppServices(
      catalog: catalogService,
      drawings: drawingLoader,
      progress: progressStore,
      child: MaterialApp(
        title: 'Pequeños Artistas',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        initialRoute: AppRoutes.home,
        onGenerateRoute: AppRouter.onGenerateRoute,
        builder: (context, child) =>
            MediaQuery.withClampedTextScaling(maxScaleFactor: maxTextScale, child: child!),
      ),
    );
  }
}
