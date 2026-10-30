import 'dart:async';

import 'package:flutter/material.dart';

import 'learning/audio/learning_audio.dart';
import 'learning/learning_controller.dart';
import 'navigation/app_router.dart';
import 'navigation/app_routes.dart';
import 'services/app_services.dart';
import 'services/catalog_service.dart';
import 'services/drawing_loader.dart';
import 'persistence/creation_store.dart';
import 'theme/app_theme.dart';

class PequenosArtistasApp extends StatelessWidget {
  const PequenosArtistasApp({
    super.key,
    required this.catalogService,
    required this.drawingLoader,
    required this.creationStore,
    required this.learningController,
    required this.learningAudio,
  });

  final CatalogService catalogService;
  final DrawingLoader drawingLoader;
  final CreationStore creationStore;
  final LearningController learningController;
  final LearningAudio learningAudio;

  /// Se respeta el tamaño de texto del sistema, con un tope para que las
  /// pantallas sigan siendo usables.
  static const maxTextScale = 1.6;

  @override
  Widget build(BuildContext context) {
    return AppServices(
      catalog: catalogService,
      drawings: drawingLoader,
      creations: creationStore,
      learning: learningController,
      audio: learningAudio,
      child: _AudioBinding(
        audio: learningAudio,
        settings: learningController,
        child: MaterialApp(
          title: 'Pequeños Artistas',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          initialRoute: AppRoutes.home,
          onGenerateRoute: AppRouter.onGenerateRoute,
          builder: (context, child) =>
              MediaQuery.withClampedTextScaling(maxScaleFactor: maxTextScale, child: child!),
        ),
      ),
    );
  }
}

/// Conecta el audio con la app: aplica al momento los cambios de preferencias,
/// pausa la música y calla la voz cuando la app pasa a segundo plano (llamada,
/// otra app, pantalla apagada) y lo recupera al volver. Libera todo al cerrar.
class _AudioBinding extends StatefulWidget {
  const _AudioBinding({required this.audio, required this.settings, required this.child});

  final LearningAudio audio;
  final Listenable settings;
  final Widget child;

  @override
  State<_AudioBinding> createState() => _AudioBindingState();
}

class _AudioBindingState extends State<_AudioBinding> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    widget.settings.addListener(widget.audio.refresh);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        widget.audio.setForeground(true);
      case AppLifecycleState.paused || AppLifecycleState.hidden || AppLifecycleState.detached:
        widget.audio.setForeground(false);
      case AppLifecycleState.inactive:
        break; // Algo pasajero (p. ej. la persiana de notificaciones).
    }
  }

  @override
  void dispose() {
    widget.settings.removeListener(widget.audio.refresh);
    WidgetsBinding.instance.removeObserver(this);
    unawaited(widget.audio.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
