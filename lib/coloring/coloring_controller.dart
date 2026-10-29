import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/painting.dart';

import '../services/drawing_loader.dart';
import '../persistence/creation.dart';
import '../persistence/creation_store.dart';
import 'coloring_history.dart';
import 'engine/drawing_painter.dart';
import 'engine/vector_drawing.dart';
import 'palette.dart';

enum ColoringTool { paint, eraser }

/// Último relleno hecho con un toque (para la animación de relleno). No
/// afecta a los datos: el color ya está aplicado cuando se crea el evento.
class FillEvent {
  const FillEvent({required this.serial, required this.regionId, this.from, this.to, this.origin});

  final int serial;
  final String regionId;
  final Color? from;
  final Color? to;

  /// Punto tocado (coordenadas del dibujo), si se conoce.
  final Offset? origin;
}

enum ColoringStatus { loading, ready, error }

/// Estado del guardado automático, visible en la pantalla.
enum SaveState {
  /// Todo está guardado (o no hay nada que guardar).
  saved,

  /// Hay cambios que se guardarán en un momento.
  pending,

  /// La última escritura falló; se reintentará.
  failed,
}

/// Estado y lógica de una sesión de coloreado de UNA creación.
///
/// No depende de widgets: la pantalla lo crea al abrir un dibujo y lo
/// destruye al salir, así que los colores de un dibujo nunca pasan a otro.
/// Cada cambio se guarda automáticamente (con un pequeño retraso para agrupar
/// toques seguidos), al salir de la pantalla y cuando la app pasa a segundo
/// plano.
class ColoringController extends ChangeNotifier implements RegionColors {
  ColoringController({
    required this.drawingId,
    required this.file,
    required this._loader,
    required this._store,
    this.creationId,
    this.startNew = false,
    this.saveDelay = const Duration(milliseconds: 600),
    PaletteColor? initialColor,
  }) : _color = initialColor ?? kidPalette.first;

  /// Id del dibujo activo y ruta de su SVG.
  final String drawingId;
  final String file;

  /// Creación concreta que se quiere continuar (desde «Mis dibujos»). Si es
  /// null, se continúa la más reciente de este dibujo o se empieza una nueva.
  final String? creationId;

  /// Empezar una creación nueva desde el dibujo original.
  final bool startNew;
  final Duration saveDelay;
  final DrawingLoader _loader;
  final CreationStore _store;
  String? _activeCreationId;
  DateTime? _createdAt;
  SaveState _saveState = SaveState.saved;
  Future<void>? _saving;

  ColoringStatus _status = ColoringStatus.loading;
  String? _error;
  VectorDrawing? _drawing;
  PaletteColor _color;
  ColoringTool _tool = ColoringTool.paint;
  String? _selectedRegion;
  final _colors = <String, Color>{};
  final _history = ColoringHistory();
  bool _unsaved = false;
  Timer? _saveTimer;
  bool _disposed = false;

  ColoringStatus get status => _status;
  String? get errorMessage => _error;
  VectorDrawing? get drawing => _drawing;
  PaletteColor get color => _color;
  ColoringTool get tool => _tool;

  /// Última región tocada.
  String? get selectedRegion => _selectedRegion;

  /// Colores aplicados (solo las regiones pintadas).
  Map<String, Color> get regionColors => Map.unmodifiable(_colors);

  bool get coloringEngineReady => _status == ColoringStatus.ready;
  bool get canUndo => _history.canUndo;
  bool get canRedo => _history.canRedo;
  bool get hasColoring => _colors.isNotEmpty;

  /// Hay cambios que todavía no se han escrito en el almacenamiento.
  bool get hasUnsavedChanges => _unsaved;

  SaveState get saveState => _saveState;

  /// Id de la creación que se está pintando (disponible tras [load]).
  String? get activeCreationId => _activeCreationId;

  /// Zonas del dibujo sin contar el fondo.
  int get totalRegions => _drawing?.regions.where((r) => r.id != VectorDrawing.backgroundId).length ?? 0;

  @override
  Color? colorOf(String regionId) => _colors[regionId];

  /// Carga el dibujo y, si existe, el progreso guardado.
  Future<void> load() async {
    _status = ColoringStatus.loading;
    _error = null;
    _notify();
    try {
      final drawing = await _loader.load(file);
      final saved = await _findCreation();
      if (_disposed) return;
      _drawing = drawing;
      _colors.clear();
      _activeCreationId = saved?.id ?? _store.newCreationId(drawingId);
      _createdAt = saved?.createdAt;
      if (saved != null) {
        // Se ignoran regiones que ya no existen en el dibujo.
        for (final e in saved.regionColors.entries) {
          if (drawing.hasRegion(e.key)) _colors[e.key] = e.value;
        }
      }
      _status = ColoringStatus.ready;
    } on DrawingLoadException catch (e) {
      _status = ColoringStatus.error;
      _error = e.reason;
    } catch (e) {
      _status = ColoringStatus.error;
      _error = 'error inesperado';
    }
    _notify();
  }

  /// La creación a continuar. Un error de lectura no impide pintar: se
  /// empieza una creación nueva y los datos guardados no se tocan.
  Future<Creation?> _findCreation() async {
    if (startNew) return null;
    try {
      final c = creationId != null ? await _store.load(creationId!) : await _store.latestFor(drawingId);
      return c != null && c.drawingId == drawingId ? c : null;
    } catch (_) {
      return null;
    }
  }

  void selectColor(PaletteColor color) {
    if (_color == color && _tool == ColoringTool.paint) return;
    _color = color;
    _tool = ColoringTool.paint;
    _notify();
  }

  void toggleEraser() {
    _tool = _tool == ColoringTool.eraser ? ColoringTool.paint : ColoringTool.eraser;
    _notify();
  }

  /// Color que recibiría una región al tocarla (`null` = original).
  Color? get _paintValue => _tool == ColoringTool.eraser || _color.restoresOriginal ? null : _color.color;

  /// Pinta (o borra) la región [regionId]. Devuelve `true` si cambió algo.
  bool tapRegion(String regionId, {Offset? origin}) {
    final drawing = _drawing;
    if (drawing == null || !drawing.hasRegion(regionId)) return false;
    _selectedRegion = regionId;
    final before = _colors[regionId];
    final after = _paintValue;
    if (before == after) {
      _notify();
      return false;
    }
    final wasComplete = isComplete;
    _apply({regionId: after});
    _history.record(ColorEdit({regionId: (before, after)}));
    _lastFill = FillEvent(serial: ++_fillSerial, regionId: regionId, from: before, to: after, origin: origin);
    // Solo se celebra al pasar de «sin terminar» a «terminado» con un toque.
    if (!wasComplete && isComplete) _completionSerial++;
    _changed();
    return true;
  }

  /// Toca en coordenadas del viewBox; [tolerance] ayuda con zonas estrechas.
  String? tapAt(Offset viewBoxPoint, {double tolerance = 0}) {
    final id = _drawing?.hitTest(viewBoxPoint, tolerance: tolerance);
    if (id != null) tapRegion(id, origin: viewBoxPoint);
    return id;
  }

  int _fillSerial = 0;
  FillEvent? _lastFill;
  int _completionSerial = 0;

  /// Último relleno (para animarlo en la vista).
  FillEvent? get lastFill => _lastFill;

  /// Aumenta cada vez que un toque termina el dibujo.
  int get completionSerial => _completionSerial;

  /// Todas las zonas (sin contar el fondo) tienen color.
  bool get isComplete {
    final d = _drawing;
    if (d == null) return false;
    return d.regions.every((r) => r.id == VectorDrawing.backgroundId || _colors.containsKey(r.id));
  }

  void undo() {
    final edit = _history.undo();
    if (edit == null) return;
    _apply({for (final e in edit.changes.entries) e.key: e.value.$1});
    _changed();
  }

  void redo() {
    final edit = _history.redo();
    if (edit == null) return;
    _apply({for (final e in edit.changes.entries) e.key: e.value.$2});
    _changed();
  }

  /// Deja el dibujo como el original. Se puede deshacer.
  void clear() {
    if (_colors.isEmpty) return;
    _history.record(ColorEdit({for (final e in _colors.entries) e.key: (e.value, null)}));
    _apply({for (final id in _colors.keys.toList()) id: null});
    _changed();
  }

  void _apply(Map<String, Color?> values) {
    values.forEach((id, color) => color == null ? _colors.remove(id) : _colors[id] = color);
  }

  void _changed() {
    _unsaved = true;
    _saveState = SaveState.pending;
    _notify();
    _saveTimer?.cancel();
    _saveTimer = Timer(saveDelay, save);
  }

  /// Escribe la creación ahora (no espera al guardado automático). Una
  /// creación sin colores no se guarda: se borra su entrada, si existía.
  Future<void> save() async {
    _saveTimer?.cancel();
    // Si ya hay una escritura en marcha, se espera y se guarda lo que falte.
    while (_saving != null) {
      await _saving!.catchError((Object _) {});
    }
    if (!_unsaved || _status != ColoringStatus.ready) return;
    final id = _activeCreationId!;
    final colors = Map.of(_colors);
    _unsaved = false;
    final now = DateTime.now();
    final future = colors.isEmpty
        ? _store.delete(id)
        : _store.save(
            Creation(
              id: id,
              drawingId: drawingId,
              regionColors: colors,
              createdAt: _createdAt ??= now,
              updatedAt: now,
              totalRegions: totalRegions,
            ),
          );
    _saving = future;
    try {
      await future;
      if (!_unsaved) _saveState = SaveState.saved;
    } catch (_) {
      _unsaved = true; // Se reintentará en el próximo cambio, al salir o al tocar «Reintentar».
      _saveState = SaveState.failed;
    } finally {
      _saving = null;
    }
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _saveTimer?.cancel();
    // Lo pendiente se guarda al salir del dibujo.
    if (_unsaved) unawaited(save());
    super.dispose();
  }
}
