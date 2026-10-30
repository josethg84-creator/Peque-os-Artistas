import 'package:flutter/material.dart';

import '../navigation/app_router.dart';
import '../learning/learning_controller.dart';
import '../learning/learning_level.dart';
import '../persistence/creation_store.dart';
import '../services/app_services.dart';
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
                    'Pequeños Artistas · versión 1.0.0',
                    'Aplicación de dibujo y coloreado para niños de 4 a 7 años.',
                  ],
                ),
                _Section(
                  icon: Icons.photo_library_outlined,
                  title: 'Colección de dibujos',
                  lines: [
                    '${catalog.drawings.length} dibujos disponibles '
                        '(${catalog.drawings.where((d) => !d.thumbnailAvailable).length} sin miniatura).',
                    if (catalog.issues.isEmpty)
                      'El catálogo (${CatalogService.catalogPath}) se leyó sin incidencias.'
                    else ...[
                      'Incidencias del catálogo:',
                      ...catalog.issues.map((i) => '• $i'),
                    ],
                  ],
                ),
                _StoredDataSection(catalogIds: {for (final d in catalog.drawings) d.id}),
                _LearningSection(learning: AppServices.of(context).learning),
                const _Section(
                  icon: Icons.shield_outlined,
                  title: 'Privacidad y seguridad',
                  lines: [
                    'No se piden datos personales ni se crean cuentas.',
                    'Sin publicidad, sin compras, sin chat y sin enlaces externos.',
                    'La aplicación no usa Internet: todo se guarda solo en este dispositivo.',
                    'Para borrar todos los datos: Ajustes de Android → Aplicaciones → '
                        'Pequeños Artistas → Almacenamiento → Borrar datos (o desinstalar la app).',
                  ],
                ),
                const _Section(
                  icon: Icons.tune_rounded,
                  title: 'Ajustes',
                  lines: [
                    'Sonido: botón del altavoz en la pantalla de inicio.',
                    'Nivel, sonidos y voz de los juegos: en «Aprender jugando».',
                    'Cada dibujo se puede borrar desde «Mis dibujos».',
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

/// Estado de las creaciones guardadas. Los datos dañados o de dibujos que ya no
/// existen se conservan; solo se borran si un adulto lo confirma aquí.
class _StoredDataSection extends StatefulWidget {
  const _StoredDataSection({required this.catalogIds});

  final Set<String> catalogIds;

  @override
  State<_StoredDataSection> createState() => _StoredDataSectionState();
}

class _StoredDataSectionState extends State<_StoredDataSection> {
  Future<CreationReport>? _report;

  CreationStore get _store => AppServices.of(context).creations;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _report ??= _store.loadAll();
  }

  Future<void> _discard(List<StoredProblem> problems) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Eliminar los datos dañados?'),
        content: Text(
          'Se eliminarán ${problems.length} registro(s) que no se pueden leer. '
          'Las creaciones válidas no se tocan. Esta acción no se puede deshacer.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Eliminar')),
        ],
      ),
    );
    if (ok != true) return;
    for (final p in problems) {
      try {
        await _store.discardProblem(p);
      } catch (_) {
        // Se mostrará de nuevo en el recuento.
      }
    }
    if (!mounted) return;
    setState(() {
      _report = _store.loadAll();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<CreationReport>(
      future: _report,
      builder: (context, snapshot) {
        final lines = <String>[
          'Las creaciones se guardan solo en este dispositivo, sin cuentas ni conexión a internet. '
              'Borrar los datos de la aplicación o desinstalarla las elimina.',
        ];
        final report = snapshot.data;
        if (snapshot.hasError) {
          lines.add('No se pudo leer el almacenamiento en este momento.');
        } else if (report != null) {
          final orphans = report.creations.where((c) => !widget.catalogIds.contains(c.drawingId)).length;
          lines.add('${report.creations.length} creación(es) guardada(s).');
          if (report.recovered.isNotEmpty) {
            lines.add('${report.recovered.length} recuperada(s) desde la copia de seguridad.');
          }
          if (orphans > 0) {
            lines.add('$orphans de dibujos que ya no están en el catálogo (se conservan, no se muestran).');
          }
          if (report.problems.isNotEmpty) {
            lines.add(
              '${report.problems.length} registro(s) dañado(s) o ilegible(s) (se conservan, no se muestran).',
            );
          }
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Section(icon: Icons.save_outlined, title: 'Dibujos guardados', lines: lines),
            if (report != null && report.problems.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: OutlinedButton.icon(
                  onPressed: () => _discard(report.problems),
                  icon: const Icon(Icons.delete_sweep_outlined),
                  label: Text('Eliminar datos dañados (${report.problems.length})'),
                ),
              ),
          ],
        );
      },
    );
  }
}

/// Resumen de «Aprender jugando» para las familias.
class _LearningSection extends StatelessWidget {
  const _LearningSection({required this.learning});

  final LearningController learning;

  @override
  Widget build(BuildContext context) {
    final p = learning.progress;
    final s = p.settings;
    return _Section(
      icon: Icons.school_outlined,
      title: 'Aprender jugando',
      lines: [
        'Nivel: ${s.level.label}. Sonidos: ${s.soundOn ? 'sí' : 'no'}. Voz: ${s.voiceOn ? 'sí' : 'no'}.',
        for (final g in GameId.values) '${g.title}: ${p.game(g).sessions} partida(s) terminada(s).',
        '${p.rewards.length} pegatina(s) y ${p.stars} estrella(s).',
        'La voz usa el motor de texto a voz del dispositivo (sin conexión); '
            'si no hay una voz en español instalada, no se oirá.',
        if (learning.recoveredFromBackup) 'El progreso se recuperó desde la copia de seguridad.',
        if (learning.startedFromDamagedData)
          'El progreso guardado estaba dañado: se empezó de cero (los datos dañados se conservan).',
        if (learning.saveFailed) 'El último guardado del progreso falló; se reintentará.',
      ],
    );
  }
}
