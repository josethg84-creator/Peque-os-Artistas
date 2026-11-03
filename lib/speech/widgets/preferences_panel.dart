import 'package:flutter/material.dart';

import '../recommendations.dart';
import '../speech_content.dart';
import '../speech_progress.dart';

/// Ajustes de «Aprendo a Hablar» para adultos (dentro de la zona de adultos,
/// protegida por su acceso). Solo orientan las propuestas: no bloquean nada.
class SpeechPreferencesPanel extends StatelessWidget {
  const SpeechPreferencesPanel({super.key, required this.speech, this.content});

  final SpeechController speech;
  final SpeechContent? content;

  @override
  Widget build(BuildContext context) {
    final p = speech.progress.preferences;
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
    final content = this.content;
    final suggestions = content == null
        ? const <Recommendation>[]
        : recommendActivities(speech.progress, content, now: DateTime.now(), sessionTime: speech.sessionTime);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        title('Edad orientativa', 'Sirve para proponer contenido; el niño puede usar cualquier actividad.'),
        Wrap(
          spacing: 8,
          runSpacing: 4,
          children: [
            for (final age in SpeechPreferences.ageRanges)
              ChoiceChip(
                label: Text('$age años'),
                selected: p.ageRange == age,
                onSelected: (on) => speech.updatePreferences((x) {
                  x.ageRange = on ? age : null;
                  if (on) x.level = SpeechPreferences.suggestedLevel(age);
                }),
              ),
          ],
        ),
        title('Nivel de partida', 'Se puede cambiar en cualquier momento, aquí o dentro de cada juego.'),
        Wrap(
          spacing: 8,
          children: [
            for (final level in [1, 2, 3])
              ChoiceChip(
                label: Text(SpeechPreferences.levelName(level)),
                selected: p.level == level,
                onSelected: (_) => speech.updatePreferences((x) => x.level = level),
              ),
          ],
        ),
        if (content != null) ...[
          title('Grupos de palabras favoritos', 'Lolo propondrá antes estas palabras.'),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final c in content.categories)
                FilterChip(
                  label: Text(c.name),
                  selected: p.favoriteCategories.contains(c.id),
                  onSelected: (on) => speech.updatePreferences(
                    (x) => on ? x.favoriteCategories.add(c.id) : x.favoriteCategories.remove(c.id),
                  ),
                ),
            ],
          ),
        ],
        title('Duración sugerida', 'Al pasar este tiempo, Lolo propone un descanso (no corta nada).'),
        Wrap(
          spacing: 8,
          children: [
            for (final m in SpeechPreferences.minuteOptions)
              ChoiceChip(
                label: Text('$m min'),
                selected: p.minutes == m,
                onSelected: (_) => speech.updatePreferences((x) => x.minutes = m),
              ),
          ],
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Narración más lenta'),
          subtitle: const Text('Lolo habla más despacio en todo el módulo.'),
          value: p.slowVoice,
          onChanged: (v) => speech.updatePreferences((x) => x.slowVoice = v),
        ),
        if (suggestions.isNotEmpty) ...[
          title('Lo que Lolo propone hoy y por qué'),
          for (final r in suggestions)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('• ${r.title}: ${r.reason}')),
        ],
      ],
    );
  }
}
