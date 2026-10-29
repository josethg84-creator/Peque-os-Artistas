import 'package:flutter/material.dart';

import 'app.dart';
import 'services/catalog_service.dart';
import 'services/drawing_loader.dart';
import 'services/progress_store.dart';

void main() {
  runApp(
    PequenosArtistasApp(
      catalogService: CatalogService(),
      drawingLoader: DrawingLoader(),
      progressStore: SharedPreferencesProgressStore(),
    ),
  );
}
