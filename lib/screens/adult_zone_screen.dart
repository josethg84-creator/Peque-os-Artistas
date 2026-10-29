import 'package:flutter/material.dart';

import '../navigation/app_router.dart';
import '../services/catalog_service.dart';
import '../theme/app_theme.dart';
import '../widgets/catalog_builder.dart';

/// Zona para adultos, con estilo sobrio y separada de la navegación infantil.
/// No contiene enlaces externos, compras ni recogida de datos.
class AdultZoneScreen extends StatelessWidget {
  const AdultZoneScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: AppTheme.adult(),
      child: Builder(
        builder: (context) => Scaffold(
          appBar: AppBar(
            title: const Text('Zona para adultos'),
            leading: IconButton(
              tooltip: 'Salir al inicio',
              icon: const Icon(Icons.close_rounded),
              onPressed: () => AppRouter.goHome(context),
            ),
          ),
          body: CatalogBuilder(
            builder: (context, catalog) => ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const _Section(
                  icon: Icons.info_outline_rounded,
                  title: 'Acerca de la aplicación',
                  lines: [
                    'Pequeños Artistas · versión 1.0.0 (en desarrollo)',
                    'Aplicación de dibujo y coloreado para niños de 4 a 7 años.',
                  ],
                ),
                _Section(
                  icon: Icons.photo_library_outlined,
                  title: 'Colección de dibujos',
                  lines: [
                    '${catalog.drawings.length} dibujos disponibles '
                        '(${catalog.drawings.where((d) => !d.previewAvailable).length} sin vista previa).',
                    if (catalog.issues.isEmpty)
                      'El catálogo (${CatalogService.catalogPath}) se leyó sin incidencias.'
                    else ...[
                      'Incidencias del catálogo:',
                      ...catalog.issues.map((i) => '• $i'),
                    ],
                  ],
                ),
                const _Section(
                  icon: Icons.shield_outlined,
                  title: 'Privacidad y seguridad',
                  lines: [
                    'No se solicitan datos personales.',
                    'Sin publicidad, sin compras y sin chat.',
                    'Sin enlaces externos en las pantallas infantiles.',
                  ],
                ),
                const _Section(
                  icon: Icons.construction_outlined,
                  title: 'Estado del desarrollo',
                  lines: [
                    'El progreso de cada dibujo se guarda solo en este dispositivo.',
                    'Las actividades educativas son secciones provisionales.',
                    'Los ajustes (sonido, tiempo de uso…) aún no están disponibles.',
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.icon, required this.title, required this.lines});

  final IconData icon;
  final String title;
  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon),
                const SizedBox(width: 8),
                Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
              ],
            ),
            const SizedBox(height: 8),
            for (final line in lines) Padding(padding: const EdgeInsets.only(top: 4), child: Text(line)),
          ],
        ),
      ),
    );
  }
}
