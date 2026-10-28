import 'package:flutter/material.dart';

import 'app.dart';
import 'services/catalog_service.dart';

void main() {
  runApp(PequenosArtistasApp(catalogService: CatalogService()));
}
