import 'package:flutter/material.dart';

import 'app.dart';
import 'services/catalog_service.dart';
import 'services/drawing_loader.dart';
import 'persistence/creation_store.dart';
import 'persistence/key_value_backend.dart';

void main() {
  runApp(
    PequenosArtistasApp(
      catalogService: CatalogService(),
      drawingLoader: DrawingLoader(),
      creationStore: KeyValueCreationStore(SharedPreferencesBackend()),
    ),
  );
}
