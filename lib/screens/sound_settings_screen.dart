import 'dart:async';

import 'package:flutter/material.dart';

import '../audio/app_audio.dart';
import '../audio/phrases.dart';
import '../learning/learning_progress.dart';
import '../services/app_services.dart';
import '../theme/app_colors.dart';
import '../theme/app_dimens.dart';
import '../widgets/kid_scaffold.dart';

/// «Sonido y música»: silencio total, volumen general y música, efectos y voz
/// por separado, cada uno con interruptor y volumen. Controles grandes; los
/// cambios se oyen al momento y se guardan al soltar el control.
class SoundSettingsScreen extends StatelessWidget {
  const SoundSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final services = AppServices.of(context);
    final learning = services.learning;
    final audio = services.audio;
    return KidScaffold(
      title: 'Sonido y música',
      titleIcon: Icons.tune_rounded,
      accent: AppColors.sky,
      body: ListenableBuilder(
        listenable: learning,
        builder: (context, _) {
          final s = learning.settings;
          void update(LearningSettings next, {bool save = true}) =>
              unawaited(learning.updateSettings(next, save: save));
          return ListView(
            padding: const EdgeInsets.fromLTRB(
              AppDimens.pagePadding,
              4,
              AppDimens.pagePadding,
              AppDimens.pagePadding,
            ),
            children: [
              _ChannelCard(
                icon: s.muted ? Icons.volume_off_rounded : Icons.volume_up_rounded,
                title: 'Todo el sonido',
                color: AppColors.coral,
                on: !s.muted,
                onToggle: (on) => update(s.copyWith(muted: !on)),
                volumeLabel: 'Volumen general',
                volume: s.masterVolume,
                onVolume: (v, {required save}) => update(s.copyWith(masterVolume: v), save: save),
                onVolumeDone: () => unawaited(audio.play(SoundCue.correct)),
              ),
              _ChannelCard(
                icon: Icons.music_note_rounded,
                title: 'Música',
                color: AppColors.grape,
                on: s.musicOn,
                enabled: !s.muted,
                onToggle: (on) => update(s.copyWith(musicOn: on)),
                volume: s.musicVolume,
                onVolume: (v, {required save}) => update(s.copyWith(musicVolume: v), save: save),
                note:
                    'Suena en los menús y al colorear. En los juegos se calla para que el niño se concentre.',
              ),
              _ChannelCard(
                icon: Icons.notifications_active_rounded,
                title: 'Efectos',
                color: AppColors.leaf,
                on: s.soundOn,
                enabled: !s.muted,
                onToggle: (on) => update(s.copyWith(soundOn: on)),
                volume: s.effectsVolume,
                onVolume: (v, {required save}) => update(s.copyWith(effectsVolume: v), save: save),
                onVolumeDone: () => unawaited(audio.play(SoundCue.correct)),
              ),
              _ChannelCard(
                icon: Icons.record_voice_over_rounded,
                title: 'Voz',
                color: AppColors.sun,
                on: s.voiceOn,
                enabled: !s.muted,
                onToggle: (on) => update(s.copyWith(voiceOn: on)),
                volume: s.voiceVolume,
                onVolume: (v, {required save}) => update(s.copyWith(voiceVolume: v), save: save),
                onVolumeDone: () => unawaited(audio.sayOneOf(Phrases.welcome)),
                extra: _VoiceStatus(audio: audio),
              ),
            ],
          );
        },
      ),
    );
  }
}

typedef _VolumeChanged = void Function(double value, {required bool save});

class _ChannelCard extends StatelessWidget {
  const _ChannelCard({
    required this.icon,
    required this.title,
    required this.color,
    required this.on,
    required this.onToggle,
    required this.volume,
    required this.onVolume,
    this.enabled = true,
    this.volumeLabel,
    this.onVolumeDone,
    this.note,
    this.extra,
  });

  final IconData icon;
  final String title;
  final Color color;
  final bool on;
  final bool enabled;
  final ValueChanged<bool> onToggle;
  final String? volumeLabel;
  final double volume;
  final _VolumeChanged onVolume;
  final VoidCallback? onVolumeDone;
  final String? note;
  final Widget? extra;

  @override
  Widget build(BuildContext context) {
    final active = enabled && on;
    final text = Theme.of(context).textTheme;
    return Card(
      // Cada control se anuncia por separado al lector de pantalla.
      semanticContainer: false,
      margin: const EdgeInsets.only(bottom: AppDimens.gap),
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDimens.radiusLarge),
        side: BorderSide(color: color.withValues(alpha: 0.5), width: 2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: active ? 1 : 0.3),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, color: Colors.white, size: 30),
                ),
                const SizedBox(width: 12),
                Expanded(child: Text(title, style: text.titleLarge)),
                Semantics(
                  label: '$title: ${on ? 'activado' : 'desactivado'}',
                  toggled: on,
                  enabled: enabled,
                  excludeSemantics: true,
                  onTap: enabled ? () => onToggle(!on) : null,
                  child: Transform.scale(
                    scale: 1.35,
                    child: Switch(value: on, activeTrackColor: color, onChanged: enabled ? onToggle : null),
                  ),
                ),
                const SizedBox(width: 8),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Icon(Icons.volume_mute_rounded, color: AppColors.inkSoft.withValues(alpha: active ? 1 : 0.4)),
                Expanded(
                  child: SliderTheme(
                    data: SliderTheme.of(context).copyWith(
                      trackHeight: 14,
                      thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 16),
                      overlayShape: const RoundSliderOverlayShape(overlayRadius: 28),
                      activeTrackColor: color,
                      thumbColor: color,
                      inactiveTrackColor: color.withValues(alpha: 0.2),
                    ),
                    child: Slider(
                      value: volume,
                      divisions: 10,
                      label: '${(volume * 100).round()} %',
                      semanticFormatterCallback: (v) =>
                          '${volumeLabel ?? 'Volumen de ${title.toLowerCase()}'}: ${(v * 100).round()} %',
                      onChanged: active ? (v) => onVolume(v, save: false) : null,
                      onChangeEnd: active
                          ? (v) {
                              onVolume(v, save: true);
                              onVolumeDone?.call();
                            }
                          : null,
                    ),
                  ),
                ),
                Icon(Icons.volume_up_rounded, color: AppColors.inkSoft.withValues(alpha: active ? 1 : 0.4)),
              ],
            ),
            if (note != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(note!, style: text.bodyMedium?.copyWith(color: AppColors.inkSoft)),
              ),
            ?extra,
          ],
        ),
      ),
    );
  }
}

/// Explica qué voz hay en el dispositivo (o por qué no habla) y permite probarla.
class _VoiceStatus extends StatefulWidget {
  const _VoiceStatus({required this.audio});

  final LearningAudio audio;

  @override
  State<_VoiceStatus> createState() => _VoiceStatusState();
}

class _VoiceStatusState extends State<_VoiceStatus> {
  late final Future<VoiceInfo> _info = widget.audio.voiceInfo()..ignore();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<VoiceInfo>(
      future: _info,
      builder: (context, snapshot) {
        final info = snapshot.data;
        if (info == null) return const SizedBox(height: 8);
        return Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    info.available ? Icons.check_circle_rounded : Icons.info_rounded,
                    color: info.available ? AppColors.leaf : AppColors.inkSoft,
                    size: 22,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      info.description,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.inkSoft),
                    ),
                  ),
                ],
              ),
              if (info.available) ...[
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size(160, 52)),
                    onPressed: () => unawaited(widget.audio.sayOneOf(Phrases.welcome)),
                    icon: const Icon(Icons.play_arrow_rounded, size: 28),
                    label: const Text('Probar la voz'),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}
