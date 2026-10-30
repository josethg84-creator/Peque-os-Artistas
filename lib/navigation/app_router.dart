import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/music_zone.dart';
import '../learning/screens/learning_game_screen.dart';
import '../learning/screens/learning_hub_screen.dart';
import '../learning/screens/rewards_screen.dart';
import '../screens/adult_zone_screen.dart';
import '../screens/categories_screen.dart';
import '../screens/coloring_screen.dart';
import '../screens/gallery_screen.dart';
import '../screens/home_screen.dart';
import '../screens/kid_progress_screen.dart';
import '../screens/not_found_screen.dart';
import '../screens/saved_drawings_screen.dart';
import '../screens/search_screen.dart';
import '../screens/sound_settings_screen.dart';
import 'app_routes.dart';

/// Construye cada ruta validando sus argumentos. Una ruta desconocida o con
/// argumentos incorrectos lleva a [NotFoundScreen], que siempre ofrece volver
/// al inicio: nunca se muestra una pantalla vacía.
abstract final class AppRouter {
  static Route<void> onGenerateRoute(RouteSettings settings) {
    final args = settings.arguments;
    final Widget page = switch (settings.name) {
      AppRoutes.home => const HomeScreen(),
      AppRoutes.kidProgress => const KidProgressScreen(),
      AppRoutes.categories => const CategoriesScreen(),
      AppRoutes.gallery when args is GalleryArgs => GalleryScreen(category: args.category),
      AppRoutes.coloring when args is ColoringArgs => ColoringScreen(
        drawingId: args.drawingId,
        creationId: args.creationId,
        startNew: args.startNew,
      ),
      AppRoutes.savedDrawings => const SavedDrawingsScreen(),
      AppRoutes.activities => const LearningHubScreen(),
      AppRoutes.learningGame when args is LearningGameArgs => LearningGameScreen(game: args.game),
      AppRoutes.rewards => const RewardsScreen(),
      AppRoutes.search => const SearchScreen(),
      AppRoutes.adultZone when args is AdultZoneArgs => const AdultZoneScreen(),
      AppRoutes.soundSettings => const SoundSettingsScreen(),
      _ => const NotFoundScreen(),
    };
    return MaterialPageRoute<void>(
      settings: settings,
      builder: (_) => MusicZone(track: musicFor(settings.name, page), child: page),
    );
  }

  /// Música de cada pantalla: la misma en todos los menús (sin cambios
  /// innecesarios), una más suave al colorear y silencio en los juegos, que
  /// piden concentración y tienen instrucciones habladas.
  static MusicTrack? musicFor(String? route, Widget page) {
    if (page is LearningGameScreen) return null;
    if (page is ColoringScreen) return MusicTrack.coloring;
    return MusicTrack.main;
  }

  /// Vuelve al inicio desde cualquier pantalla.
  static void goHome(BuildContext context) => Navigator.of(context).popUntil((route) => route.isFirst);
}
