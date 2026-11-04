import 'package:flutter/material.dart';

import '../../services/app_services.dart';
import '../aac_catalog.dart';
import '../aac_controller.dart';

/// Ajustes de «Quiero decir» en la zona de adultos. El tablero del niño
/// nunca pide verificación: solo estos ajustes están protegidos.
class AacSettingsPanel extends StatelessWidget {
  const AacSettingsPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final services = AppServices.of(context);
    final aac = services.aac;
    return FutureBuilder<AacCatalog>(
      future: aac.catalog(),
      builder: (context, snapshot) => ListenableBuilder(
        listenable: Listenable.merge([aac, services.learning]),
        builder: (context, _) => _panel(context, aac, snapshot.data),
      ),
    );
  }

  Widget _panel(BuildContext context, AacController aac, AacCatalog? catalog) {
    final p = aac.prefs;
    final learning = AppServices.of(context).learning;
    final text = Theme.of(context).textTheme;
    Widget title(String t, [String? help]) => Padding(
      padding: const EdgeInsets.only(top: 12, bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(t, style: text.titleSmall),
          if (help != null) Text(help, style: text.bodySmall),
        ],
      ),
    );
    Widget chips<T>(List<T> values, T selected, String Function(T) label, void Function(T) onSelect) => Wrap(
      spacing: 8,
      runSpacing: 4,
      children: [
        for (final v in values)
          ChoiceChip(
            label: Text(label(v)),
            selected: v == selected,
            onSelected: (_) => aac.update((_) => onSelect(v)),
          ),
      ],
    );
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.grid_view_outlined),
                const SizedBox(width: 8),
                Expanded(child: Text('Quiero decir (comunicación con pictogramas)', style: text.titleMedium)),
              ],
            ),
            const SizedBox(height: 6),
            const Text(
              'Es un apoyo a la comunicación con pictogramas y voz. No es un tratamiento médico ni sustituye '
              'una evaluación profesional. El niño puede usar el tablero siempre, sin verificación; estos '
              'ajustes se guardan solo en este dispositivo y no incluyen datos médicos.',
            ),
            title('Tamaño de los pictogramas'),
            chips(AacTileSize.values, p.tileSize, (v) => v.label, (v) => p.tileSize = v),
            title('Columnas'),
            chips(
              AacPreferences.columnOptions,
              p.columns,
              (v) => v == 0 ? 'Automáticas' : '$v',
              (v) => p.columns = v,
            ),
            title('Orden de las tarjetas'),
            chips(AacOrder.values, p.order, (v) => v.label, (v) => p.order = v),
            title('Tamaño del texto'),
            chips(
              AacPreferences.textScales,
              p.textScale,
              (v) => '${(v * 100).round()} %',
              (v) => p.textScale = v,
            ),
            title('Evitar toques sin querer', 'Ignora un segundo toque demasiado rápido.'),
            chips(
              AacPreferences.tapGuards,
              p.tapGuardMs,
              (v) => v == 0 ? 'No' : '${v / 1000} s',
              (v) => p.tapGuardMs = v,
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Decir la frase al tocar'),
              value: p.speakOnTap,
              onChanged: (v) => aac.update((x) => x.speakOnTap = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Confirmar antes de hablar'),
              subtitle: const Text('El dibujo tocado se muestra y se dice al pulsar «Decirlo».'),
              value: p.confirmBeforeSpeak,
              onChanged: (v) => aac.update((x) => x.confirmBeforeSpeak = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Voz más lenta'),
              value: p.slowVoice,
              onChanged: (v) => aac.update((x) => x.slowVoice = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Alto contraste'),
              subtitle: const Text('Bordes y textos negros sobre blanco.'),
              value: p.highContrast,
              onChanged: (v) => aac.update((x) => x.highContrast = v),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Frases en femenino'),
              subtitle: const Text('«Estoy cansada» en lugar de «Estoy cansado».'),
              value: p.feminine,
              onChanged: (v) => aac.update((x) => x.feminine = v),
            ),
            title('Volumen de la voz'),
            Slider(
              value: learning.settings.voiceVolume,
              label: '${(learning.settings.voiceVolume * 100).round()} %',
              divisions: 10,
              onChanged: (v) =>
                  learning.updateSettings(learning.settings.copyWith(voiceVolume: v), save: false),
              onChangeEnd: (v) => learning.updateSettings(learning.settings.copyWith(voiceVolume: v)),
            ),
            if (catalog != null) ...[
              title('Categorías frecuentes', 'Aparecen primero en «Quiero decir».'),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  for (final c in catalog.categories)
                    FilterChip(
                      label: Text(c.name),
                      selected: p.frequentCategories.contains(c.id),
                      onSelected: (on) => aac.update(
                        (x) => on ? x.frequentCategories.add(c.id) : x.frequentCategories.remove(c.id),
                      ),
                    ),
                ],
              ),
              title(
                'Tablero rápido «Necesito decir algo»',
                'Las ${catalog.quick.length} palabras esenciales están siempre. Puedes añadir las que más use.',
              ),
              Text(
                p.quickExtras.isEmpty
                    ? 'Sin palabras añadidas.'
                    : 'Añadidas: ${catalog.resolve(p.quickExtras).map((x) => x.label(feminine: p.feminine)).join(', ')}.',
              ),
              const SizedBox(height: 6),
              OutlinedButton.icon(
                onPressed: () => _chooseQuick(context, aac, catalog),
                icon: const Icon(Icons.playlist_add_rounded),
                label: const Text('Elegir palabras del tablero rápido'),
              ),
            ],
            title('Frases favoritas: ${p.favorites.length}'),
            const SizedBox(height: 8),
            FilledButton.tonalIcon(
              onPressed: () async {
                final ok = await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('¿Borrar la personalización de «Quiero decir»?'),
                    content: const Text(
                      'Se borran las frases favoritas, las palabras añadidas al tablero rápido, el uso de las '
                      'tarjetas y estos ajustes. Los pictogramas siguen disponibles.',
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('Cancelar'),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('Borrar'),
                      ),
                    ],
                  ),
                );
                if (ok == true) await aac.clearAll();
              },
              icon: const Icon(Icons.delete_sweep_outlined),
              label: const Text('Borrar personalización'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _chooseQuick(BuildContext context, AacController aac, AacCatalog catalog) => showDialog<void>(
    context: context,
    builder: (context) => ListenableBuilder(
      listenable: aac,
      builder: (context, _) => AlertDialog(
        title: const Text('Palabras del tablero rápido'),
        content: SizedBox(
          width: 420,
          height: 480,
          child: ListView(
            children: [
              // Primero las esenciales, que no se pueden quitar.
              for (final pic in catalog.resolve(catalog.quick))
                CheckboxListTile(
                  value: true,
                  onChanged: null,
                  title: Text(pic.label(feminine: aac.prefs.feminine)),
                  subtitle: const Text('Esencial: siempre visible'),
                ),
              for (final pic in catalog.active())
                if (!catalog.quick.contains(pic.id))
                  CheckboxListTile(
                    value: aac.prefs.quickExtras.contains(pic.id),
                    title: Text(pic.label(feminine: aac.prefs.feminine)),
                    onChanged: (on) => aac.update(
                      (x) => on == true ? x.quickExtras.add(pic.id) : x.quickExtras.remove(pic.id),
                    ),
                  ),
            ],
          ),
        ),
        actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Listo'))],
      ),
    ),
  );
}
