import 'dart:math';

import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../widgets/adaptive_grid.dart';
import '../../widgets/kid_scaffold.dart';
import '../speech_content.dart';
import '../widgets/speech_widgets.dart';
import 'speech_hub_screen.dart';
import 'speech_quiz_screen.dart';

const _listenColor = Color(0xFFFF8A65);

/// «Escucho y respondo»: los niveles (de más fácil a más difícil) y el juego
/// de la fase 2 «Escucha y señala».
class ListeningHubScreen extends StatelessWidget {
  const ListeningHubScreen({super.key});

  static const _levelColors = [Color(0xFFFFCCBC), Color(0xFFFFE0B2), Color(0xFFF8BBD0)];
  static const _levelIcons = [
    Icons.hearing_rounded,
    Icons.psychology_rounded,
    Icons.format_list_numbered_rounded,
  ];

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return KidScaffold(
      title: 'Escucho y respondo',
      titleIcon: Icons.hearing_rounded,
      accent: _listenColor,
      backLabel: 'Volver a Aprendo a Hablar',
      body: SpeechContentBuilder(
        builder: (context, content) => ListenableBuilder(
          listenable: speech,
          builder: (context, _) {
            final levels = content.listening.levels;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Padding(
                  padding: EdgeInsets.fromLTRB(16, 0, 16, 8),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: LoloBubble(text: 'Escucha con atención y toca la respuesta.', size: 60),
                  ),
                ),
                Expanded(
                  child: AdaptiveGrid(
                    itemCount: levels.length + 1,
                    minTileWidth: 170,
                    childAspectRatio: 1,
                    itemBuilder: (context, i) {
                      if (i == levels.length) {
                        return HomeMenuCard(
                          title: 'Escucha y señala',
                          subtitle: 'Oye una palabra y tócala',
                          art: const SpeechActivityArt(
                            icon: Icons.touch_app_rounded,
                            color: Color(0xFFB3E5FC),
                          ),
                          color: const Color(0xFFB3E5FC),
                          onTap: () => Navigator.of(context).pushNamed(AppRoutes.speechListen),
                        );
                      }
                      final level = levels[i];
                      final all = content.listening.ofLevel(level.level);
                      final done = all.where((e) => speech.progress.listeningDone.contains(e.id)).length;
                      return HomeMenuCard(
                        title: level.title,
                        subtitle: '${level.subtitle} · $done de ${all.length}',
                        art: SpeechActivityArt(
                          icon: _levelIcons[i % _levelIcons.length],
                          color: _levelColors[i % _levelColors.length],
                        ),
                        color: _levelColors[i % _levelColors.length],
                        badge: speech.progress.activitiesDone.containsKey('escucho_nivel_${level.level}')
                            ? '¡Superado!'
                            : null,
                        onTap: () => Navigator.of(context).pushNamed(
                          AppRoutes.speechListeningLevel,
                          arguments: SpeechListeningArgs(level.level),
                        ),
                      );
                    },
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

/// Una ronda de un nivel: [count] ejercicios al azar del nivel, mezclando
/// tipos. Cada frase se puede oír otra vez, también despacio.
class ListeningScreen extends StatelessWidget {
  const ListeningScreen({super.key, required this.level, this.seed, this.count = 8});

  final int level;

  /// Para las pruebas: siempre los mismos ejercicios.
  final int? seed;
  final int count;

  @override
  Widget build(BuildContext context) {
    final speech = AppServices.of(context).speech;
    return SpeechContentBuilder(
      builder: (context, content) {
        final info = content.listening.levels.where((l) => l.level == level).firstOrNull;
        var round = <ListeningExercise>[];
        return KidScaffold(
          title: info == null ? 'Escucho y respondo' : 'Escucho y respondo · ${info.title}',
          titleIcon: Icons.hearing_rounded,
          accent: _listenColor,
          backLabel: 'Volver a los niveles',
          body: SpeechQuizBody(
            seed: seed,
            color: _listenColor,
            slowButton: true,
            repeatRoute: AppRoutes.speechListeningLevel,
            build: (Random random) {
              round = pickRound(content.listening.ofLevel(level), random, count);
              return [for (final e in round) e.toQuestion()];
            },
            onAnswered: (i) {
              if (i < round.length) speech.markListeningDone(round[i].id);
            },
            onFinished: () => speech.markListeningLevel(level),
          ),
        );
      },
    );
  }

  /// Elige [count] ejercicios mezclando los tipos (no dos seguidos del mismo
  /// tipo cuando se puede).
  static List<ListeningExercise> pickRound(List<ListeningExercise> all, Random random, int count) {
    final pool = [...all]..shuffle(random);
    final round = <ListeningExercise>[];
    while (round.length < count && pool.isNotEmpty) {
      final k = pool.indexWhere((e) => round.isEmpty || e.type != round.last.type);
      round.add(pool.removeAt(k < 0 ? 0 : k));
    }
    return round;
  }
}
