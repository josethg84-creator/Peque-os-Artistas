import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../audio/app_audio.dart';
import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../theme/app_colors.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../aac_catalog.dart';

const aacColor = Color(0xFF26A69A);
const aacInk = Color(0xFF1F2A44);

/// Carga el catálogo de pictogramas (una vez) y construye con él.
class AacCatalogBuilder extends StatelessWidget {
  const AacCatalogBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, AacCatalog catalog) builder;

  @override
  Widget build(BuildContext context) {
    final aac = AppServices.of(context).aac;
    return FutureBuilder<AacCatalog>(
      future: aac.catalog(),
      builder: (context, snapshot) {
        final c = snapshot.data;
        if (c != null) {
          return ListenableBuilder(listenable: aac, builder: (context, _) => builder(context, c));
        }
        if (snapshot.hasError) return const Center(child: Text('No se pudieron cargar los pictogramas.'));
        return const Center(child: CircularProgressIndicator());
      },
    );
  }
}

/// Dice [text] con la voz de la app (una sola voz a la vez: la nueva frase
/// interrumpe la anterior) y lo muestra en grande. Lo que se ve es lo que se
/// dice.
void aacSay(BuildContext context, String text, {bool slow = false}) {
  final services = AppServices.of(context);
  services.aac
    ..pending.value = null
    ..message.value = text;
  unawaited(services.audio.say(text, slow: slow || services.aac.prefs.slowVoice));
}

/// Tocar un pictograma: según los ajustes, lo dice al momento, espera a
/// «Decirlo» o solo lo muestra.
void aacTap(BuildContext context, String text, {String? id}) {
  final aac = AppServices.of(context).aac;
  if (!aac.acceptTap()) return;
  if (id != null) aac.markUsed(id);
  final p = aac.prefs;
  if (p.confirmBeforeSpeak) {
    aac
      ..message.value = text
      ..pending.value = text;
  } else if (p.speakOnTap) {
    aacSay(context, text);
  } else {
    aac.message.value = text;
  }
}

/// La frase en grande, arriba de cada tablero, con Repetir, Despacio y
/// «Mostrar en grande» (para enseñarla a otra persona). Si la voz no está
/// disponible o el sonido está apagado, lo explica: la frase sigue a la vista.
class AacMessageBar extends StatelessWidget {
  const AacMessageBar({super.key, this.placeholder = 'Toca un dibujo para decirlo.'});

  final String placeholder;

  @override
  Widget build(BuildContext context) {
    final services = AppServices.of(context);
    final aac = services.aac;
    final high = aac.prefs.highContrast;
    return ListenableBuilder(
      listenable: Listenable.merge([aac.message, aac.pending]),
      builder: (context, _) {
        final msg = aac.message.value;
        final pending = aac.pending.value;
        final silent = services.audio.voiceVolume <= 0;
        return Container(
          margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
          padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(
              color: high ? Colors.black : aacColor.withValues(alpha: 0.6),
              width: high ? 4 : 3,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Semantics(
                      liveRegion: true,
                      label: msg == null ? placeholder : 'Mensaje: $msg',
                      excludeSemantics: true,
                      child: Text(
                        msg ?? placeholder,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: fredoka(
                          msg == null ? 20 : 30,
                          color: msg == null ? AppColors.inkSoft : aacInk,
                        ),
                      ),
                    ),
                  ),
                  if (msg != null && pending == null) ...[
                    _BarButton(
                      icon: Icons.replay_rounded,
                      label: 'Repetir',
                      onTap: () => aacSay(context, msg),
                    ),
                    _BarButton(
                      icon: Icons.slow_motion_video_rounded,
                      label: 'Despacio',
                      onTap: () => aacSay(context, msg, slow: true),
                    ),
                    _BarButton(
                      icon: Icons.fullscreen_rounded,
                      label: 'Mostrar en grande',
                      onTap: () => showAacBigMessage(context, msg),
                    ),
                  ],
                ],
              ),
              if (pending != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 10,
                    runSpacing: 8,
                    children: [
                      SizedBox(
                        width: 170,
                        child: SpeechActionButton(
                          icon: Icons.record_voice_over_rounded,
                          label: 'Decirlo',
                          semanticLabel: 'Decir: $pending',
                          color: aacColor,
                          onPressed: () => aacSay(context, pending),
                        ),
                      ),
                      SizedBox(
                        width: 140,
                        child: SpeechActionButton(
                          icon: Icons.close_rounded,
                          label: 'Cancelar',
                          color: const Color(0xFF90A4AE),
                          onPressed: () {
                            aac
                              ..pending.value = null
                              ..message.value = null;
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              if (silent)
                const _Note(
                  'El sonido está apagado: la frase se ve aquí. Un adulto puede activarlo en «Sonido y música».',
                )
              else
                FutureBuilder<VoiceInfo>(
                  future: services.audio.voiceInfo(),
                  builder: (context, s) => s.data?.available == false
                      ? const _Note(
                          'La voz no está disponible en este dispositivo: la frase se ve aquí y se puede mostrar en grande.',
                        )
                      : const SizedBox.shrink(),
                ),
            ],
          ),
        );
      },
    );
  }
}

class _Note extends StatelessWidget {
  const _Note(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 6),
    child: Row(
      children: [
        const Icon(Icons.info_outline_rounded, size: 20, color: AppColors.inkSoft),
        const SizedBox(width: 6),
        Expanded(child: Text(text, style: Theme.of(context).textTheme.bodySmall)),
      ],
    ),
  );
}

class _BarButton extends StatelessWidget {
  const _BarButton({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    button: true,
    label: label,
    excludeSemantics: true,
    onTap: onTap,
    child: Tooltip(
      message: label,
      child: InkResponse(
        onTap: onTap,
        radius: 30,
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Container(
            width: 48,
            height: 48,
            decoration: const BoxDecoration(color: Color(0xFFE0F2F1), shape: BoxShape.circle),
            child: Icon(icon, color: aacColor, size: 28),
          ),
        ),
      ),
    ),
  );
}

/// La frase a pantalla completa, con letras muy grandes.
Future<void> showAacBigMessage(BuildContext context, String text) => showDialog<void>(
  context: context,
  builder: (context) => Dialog.fullscreen(
    backgroundColor: Colors.white,
    child: SafeArea(
      child: Column(
        children: [
          Align(
            alignment: Alignment.topRight,
            child: IconButton(
              iconSize: 44,
              tooltip: 'Cerrar',
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.close_rounded),
            ),
          ),
          Expanded(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 900),
                    child: Text(
                      text,
                      textAlign: TextAlign.center,
                      style: fredoka(72, color: aacInk),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
  ),
);

/// Una tarjeta de pictograma: dibujo grande y su texto. Un toque la dice.
class PictogramCard extends StatelessWidget {
  const PictogramCard({
    super.key,
    required this.pictogram,
    required this.onTap,
    this.compact = false,
    this.selected = false,
  });

  final Pictogram pictogram;
  final VoidCallback onTap;
  final bool compact;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final prefs = AppServices.of(context).aac.prefs;
    final label = pictogram.label(feminine: prefs.feminine);
    final high = prefs.highContrast;
    final color = pictogram.color;
    return Semantics(
      container: true,
      button: true,
      selected: selected,
      label: label,
      excludeSemantics: true,
      onTap: onTap,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(22),
          onTap: onTap,
          child: Ink(
            padding: EdgeInsets.all(compact ? 6 : 8),
            decoration: BoxDecoration(
              color: selected ? Color.lerp(color, Colors.white, 0.75) : Colors.white,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: high ? Colors.black : color, width: high ? 4 : 3.5),
              boxShadow: high
                  ? null
                  : [
                      BoxShadow(color: color.withValues(alpha: 0.35), offset: const Offset(0, 4)),
                      const BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 5)),
                    ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Expanded(
                  child: SpeechPictureView(picture: pictogram.picture, tint: color),
                ),
                const SizedBox(height: 4),
                SizedBox(
                  width: double.infinity,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      label,
                      textAlign: TextAlign.center,
                      style: high
                          ? fredoka((compact ? 15 : 20) * prefs.textScale, color: Colors.black)
                          : fredoka((compact ? 15 : 20) * prefs.textScale, color: aacInk),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Rejilla de pictogramas según los ajustes (tamaño, columnas y orden).
class PictogramGrid extends StatelessWidget {
  const PictogramGrid({
    super.key,
    required this.pictograms,
    this.onTap,
    this.sort = true,
    this.padding,
    this.shrinkWrap = false,
  });

  final List<Pictogram> pictograms;

  /// Por defecto, decir la tarjeta.
  final void Function(Pictogram p)? onTap;
  final bool sort;
  final EdgeInsets? padding;

  /// Dentro de otra lista que se desplaza (pantallas bajas).
  final bool shrinkWrap;

  @override
  Widget build(BuildContext context) {
    final aac = AppServices.of(context).aac;
    final prefs = aac.prefs;
    final list = sort ? aac.sorted(pictograms) : pictograms;
    return LayoutBuilder(
      builder: (context, box) {
        final cols = prefs.columns > 0
            ? prefs.columns
            : max(2, min(8, (box.maxWidth / prefs.tileSize.minWidth).floor()));
        final scale = prefs.textScale.clamp(1.0, 1.5);
        return GridView.builder(
          shrinkWrap: shrinkWrap,
          physics: shrinkWrap ? const NeverScrollableScrollPhysics() : null,
          padding: padding ?? const EdgeInsets.fromLTRB(12, 4, 12, 24),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: cols,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.85 / scale.toDouble(),
          ),
          itemCount: list.length,
          itemBuilder: (context, i) {
            final p = list[i];
            return PictogramCard(
              pictogram: p,
              onTap: () =>
                  onTap != null ? onTap!(p) : aacTap(context, p.label(feminine: prefs.feminine), id: p.id),
            );
          },
        );
      },
    );
  }
}

/// Botón grande de acceso («Necesito decir algo», «Construyo…»).
class AacShortcut extends StatelessWidget {
  const AacShortcut({
    super.key,
    required this.title,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String title;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      button: true,
      label: title,
      excludeSemantics: true,
      onTap: onTap,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: onTap,
          child: Ink(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [Color.lerp(color, Colors.white, 0.35)!, color]),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: Colors.white, width: 3),
              boxShadow: [
                BoxShadow(color: Color.lerp(color, Colors.black, 0.25)!, offset: const Offset(0, 4)),
              ],
            ),
            child: Row(
              children: [
                Icon(icon, color: Colors.white, size: 40),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(title, style: fredoka(21, color: Colors.white)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// El acceso al tablero rápido desde el menú de «Aprendo a Hablar».
class QuickSayBanner extends StatelessWidget {
  const QuickSayBanner({super.key});

  @override
  Widget build(BuildContext context) => AacShortcut(
    title: 'Necesito decir algo',
    icon: Icons.campaign_rounded,
    color: const Color(0xFFEF6C57),
    onTap: () => Navigator.of(context).pushNamed(AppRoutes.aacQuick),
  );
}

/// Sonido de pulsación discreto (para el constructor).
void aacClick(BuildContext context) => unawaited(AppServices.of(context).audio.play(SoundCue.tap));
