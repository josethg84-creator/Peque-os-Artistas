import 'package:flutter/material.dart';

import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_scaffold.dart';
import '../aac_catalog.dart';
import '../phrase_composer.dart';
import '../widgets/aac_widgets.dart';

const _builderColor = Color(0xFF5C9DED);

/// «Construyo lo que quiero decir»: el niño junta pictogramas en una barra
/// ([YO] + [QUIERO] + [AGUA]) y la app dice la frase («Yo quiero agua.»).
/// Cualquier combinación vale: no se corrige al niño.
class AacBuilderScreen extends StatefulWidget {
  const AacBuilderScreen({super.key});

  @override
  State<AacBuilderScreen> createState() => _AacBuilderScreenState();
}

class _AacBuilderScreenState extends State<AacBuilderScreen> {
  final _tokens = <Pictogram>[];
  String? _category;
  final _grid = ScrollController();

  @override
  void dispose() {
    _grid.dispose();
    super.dispose();
  }

  bool get _feminine => AppServices.of(context).aac.prefs.feminine;
  String get _sentence => composePhrase(_tokens, feminine: _feminine);

  void _add(Pictogram p) {
    final aac = AppServices.of(context).aac;
    if (!aac.acceptTap()) return;
    aac.markUsed(p.id);
    setState(() => _tokens.add(p));
    aacClick(context);
    // Se oye cada pieza al ponerla (si el adulto no lo desactivó).
    if (aac.prefs.speakOnTap && !aac.prefs.confirmBeforeSpeak) aacSay(context, p.word(feminine: _feminine));
  }

  void _say() {
    if (_tokens.isEmpty) return;
    aacSay(context, _sentence);
  }

  void _undo() {
    if (_tokens.isEmpty) return;
    setState(_tokens.removeLast);
  }

  void _clear() => setState(_tokens.clear);

  void _restart() {
    setState(() {
      _tokens.clear();
      _category = null;
    });
    AppServices.of(context).aac.message.value = null;
    if (_grid.hasClients) _grid.jumpTo(0);
  }

  void _favorite() {
    if (_tokens.isEmpty) return;
    final aac = AppServices.of(context).aac;
    final s = _sentence;
    if (aac.isFavorite(s)) {
      aac.removeFavorite(s);
    } else {
      aac.addFavorite(s);
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text('Guardada en favoritas: $s')));
    }
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Construyo lo que quiero decir',
      titleIcon: Icons.view_week_rounded,
      accent: _builderColor,
      backLabel: 'Volver',
      body: AacCatalogBuilder(
        builder: (context, catalog) {
          final aac = AppServices.of(context).aac;
          final sentence = _sentence;
          final suggestions = suggestNext(catalog, _tokens);
          final pool = _category == null ? suggestions : catalog.inCategory(_category!);
          final bar = <Widget>[
            // La barra de comunicación.
            Container(
              margin: const EdgeInsets.fromLTRB(12, 0, 12, 6),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: aac.prefs.highContrast ? Colors.black : _builderColor, width: 3),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SizedBox(
                    height: 86,
                    child: _tokens.isEmpty
                        ? Center(
                            child: Text(
                              'Toca los dibujos para formar tu frase.',
                              style: fredoka(18, color: AppColors.inkSoft),
                            ),
                          )
                        : Semantics(
                            container: true,
                            label: 'Barra: ${_tokens.map((t) => t.word(feminine: _feminine)).join(', ')}',
                            excludeSemantics: true,
                            child: ListView.separated(
                              scrollDirection: Axis.horizontal,
                              itemCount: _tokens.length,
                              separatorBuilder: (_, _) => const SizedBox(width: 6),
                              itemBuilder: (context, i) => SizedBox(
                                width: 78,
                                child: PictogramCard(pictogram: _tokens[i], compact: true, onTap: _say),
                              ),
                            ),
                          ),
                  ),
                  const SizedBox(height: 6),
                  Semantics(
                    liveRegion: true,
                    label: sentence.isEmpty ? 'Frase vacía' : 'Tu frase: $sentence',
                    excludeSemantics: true,
                    child: Text(
                      sentence.isEmpty ? ' ' : sentence,
                      textAlign: TextAlign.center,
                      style: fredoka(28, color: aacInk),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    alignment: WrapAlignment.center,
                    children: [
                      _button(
                        Icons.volume_up_rounded,
                        'Escuchar frase',
                        const Color(0xFF29B6F6),
                        _tokens.isEmpty ? null : _say,
                      ),
                      _button(
                        Icons.backspace_rounded,
                        'Borrar última',
                        const Color(0xFFFFA726),
                        _tokens.isEmpty ? null : _undo,
                      ),
                      _button(
                        Icons.clear_all_rounded,
                        'Limpiar',
                        const Color(0xFF90A4AE),
                        _tokens.isEmpty ? null : _clear,
                      ),
                      _button(
                        Icons.restart_alt_rounded,
                        'Volver a comenzar',
                        const Color(0xFF7E57C2),
                        _restart,
                      ),
                      _button(
                        aac.isFavorite(sentence) ? Icons.star_rounded : Icons.star_border_rounded,
                        aac.isFavorite(sentence) ? 'Quitar favorita' : 'Guardar favorita',
                        const Color(0xFFFFA000),
                        _tokens.isEmpty ? null : _favorite,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            // Grupos: sugerencias (por defecto) o cualquier categoría.
            SizedBox(
              height: 64,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                children: [
                  _chip('Sugerencias', null, _builderColor),
                  for (final c in catalog.categories) _chip(c.name, c.id, c.color),
                ],
              ),
            ),
          ];
          return LayoutBuilder(
            builder: (context, box) {
              // En pantallas bajas (teléfono en horizontal) se desplaza todo.
              if (box.maxHeight < 640) {
                return ListView(
                  controller: _grid,
                  children: [
                    ...bar,
                    PictogramGrid(pictograms: pool, sort: _category != null, onTap: _add, shrinkWrap: true),
                  ],
                );
              }
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ...bar,
                  Expanded(
                    child: PictogramGrid(pictograms: pool, sort: _category != null, onTap: _add),
                  ),
                ],
              );
            },
          );
        },
      ),
    );
  }

  Widget _button(IconData icon, String label, Color color, VoidCallback? onTap) => SizedBox(
    width: 112,
    child: SpeechActionButton(icon: icon, label: label, color: color, onPressed: onTap),
  );

  Widget _chip(String label, String? id, Color color) {
    final selected = _category == id;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        selected: selected,
        selectedColor: Color.lerp(color, Colors.white, 0.55),
        side: BorderSide(color: color, width: 2),
        onSelected: (_) => setState(() => _category = id),
      ),
    );
  }
}
