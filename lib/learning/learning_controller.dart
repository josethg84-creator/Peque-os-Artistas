import 'package:flutter/foundation.dart';

import 'learning_level.dart';
import 'learning_progress.dart';
import 'learning_store.dart';
import 'rewards.dart';

/// Estado global de «Aprender jugando»: preferencias, progreso y premios.
///
/// Se carga una vez y se guarda después de cada cambio (terminar o abandonar
/// una partida, cambiar una preferencia), que son acciones poco frecuentes.
/// Si el almacenamiento falla, el juego sigue funcionando con los datos en
/// memoria y se reintenta en el siguiente guardado.
class LearningController extends ChangeNotifier {
  LearningController(this._store, {DateTime Function()? clock}) : _clock = clock ?? DateTime.now;

  final LearningStore _store;
  final DateTime Function() _clock;
  LearningProgress _progress = LearningProgress();
  bool _loaded = false;
  bool _saveFailed = false;
  bool _recovered = false;
  bool _damaged = false;
  Future<void>? _loading;

  LearningProgress get progress => _progress;
  LearningSettings get settings => _progress.settings;
  bool get isLoaded => _loaded;
  bool get saveFailed => _saveFailed;

  /// Información para la zona de adultos.
  bool get recoveredFromBackup => _recovered;
  bool get startedFromDamagedData => _damaged;

  Future<void> load() => _loading ??= _load();

  Future<void> _load() async {
    try {
      final result = await _store.load();
      _progress = result.progress;
      _recovered = result.recovered;
      _damaged = result.damaged;
    } catch (_) {
      // Sin acceso al almacenamiento: se juega con valores por defecto.
    }
    _loaded = true;
    notifyListeners();
  }

  Future<void> _save() async {
    try {
      await _store.save(_progress);
      _saveFailed = false;
    } catch (_) {
      _saveFailed = true;
    }
    notifyListeners();
  }

  Future<void> updateSettings(LearningSettings settings) async {
    _progress = _progress.copyWith(settings: settings);
    notifyListeners();
    await _save();
  }

  /// Registra una partida (terminada o no). [points] son las preguntas
  /// acertadas o parejas encontradas. Devuelve los premios NUEVOS conseguidos:
  /// un premio ya obtenido nunca se vuelve a conceder ni se pierde.
  Future<List<Reward>> recordSession(GameId game, {required bool completed, required int points}) async {
    if (!completed && points <= 0) return const [];
    final now = _clock();
    final games = Map.of(_progress.games)
      ..[game] = _progress.game(game).add(completed: completed, questions: points, at: now);
    var next = _progress.copyWith(games: games, stars: _progress.stars + points, lastActivity: now);
    final earned = <Reward>[];
    final owned = Map.of(next.rewards);
    for (final r in rewards) {
      if (!owned.containsKey(r.id) && r.isEarned(next)) {
        owned[r.id] = now;
        earned.add(r);
      }
    }
    next = next.copyWith(rewards: owned);
    _progress = next;
    notifyListeners();
    await _save();
    return earned;
  }
}
