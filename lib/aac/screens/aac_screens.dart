import 'dart:math';

import 'package:flutter/material.dart';

import '../../navigation/app_routes.dart';
import '../../screens/home/home_widgets.dart';
import '../../services/app_services.dart';
import '../../speech/screens/speech_quiz_screen.dart';
import '../../speech/speech_activities.dart';
import '../../speech/speech_content.dart';
import '../../speech/widgets/speech_widgets.dart';
import '../../theme/app_colors.dart';
import '../../widgets/kid_scaffold.dart';
import '../aac_catalog.dart';
import '../widgets/aac_widgets.dart';

/// «Quiero decir»: el tablero de comunicación. Se abre siempre, sin
/// estrellas, sin actividades previas, sin cuentas y sin micrófono.
class AacHomeScreen extends StatelessWidget {
  const AacHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: 'Quiero decir',
      titleIcon: Icons.grid_view_rounded,
      accent: aacColor,
      backLabel: 'Volver',
      body: AacCatalogBuilder(
        builder: (context, catalog) {
          final prefs = AppServices.of(context).aac.prefs;
          final cats = [
            ...catalog.categories.where((c) => prefs.frequentCategories.contains(c.id)),
            ...catalog.categories.where((c) => !prefs.frequentCategories.contains(c.id)),
          ];
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const AacMessageBar(),
              Expanded(
                child: CustomScrollView(
                  slivers: [
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                      sliver: SliverToBoxAdapter(
                        child: LayoutBuilder(
                          builder: (context, box) {
                            final w = box.maxWidth > 600 ? (box.maxWidth - 10) / 2 : box.maxWidth;
                            Widget item(String t, IconData i, Color c, String route) => SizedBox(
                              width: w,
                              child: AacShortcut(
                                title: t,
                                icon: i,
                                color: c,
                                onTap: () => Navigator.of(context).pushNamed(route),
                              ),
                            );
                            return Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: [
                                item(
                                  'Necesito decir algo',
                                  Icons.campaign_rounded,
                                  const Color(0xFFEF6C57),
                                  AppRoutes.aacQuick,
                                ),
                                item(
                                  'Construyo lo que quiero decir',
                                  Icons.view_week_rounded,
                                  const Color(0xFF5C9DED),
                                  AppRoutes.aacBuilder,
                                ),
                                item(
                                  'Cómo me siento',
                                  Icons.favorite_rounded,
                                  const Color(0xFFF06292),
                                  AppRoutes.aacFeelings,
                                ),
                                item(
                                  'Mis frases favoritas',
                                  Icons.star_rounded,
                                  const Color(0xFFFFA000),
                                  AppRoutes.aacFavorites,
                                ),
                              ],
                            );
                          },
                        ),
                      ),
                    ),
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
                      sliver: SliverGrid.builder(
                        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                          maxCrossAxisExtent: 220,
                          mainAxisSpacing: 12,
                          crossAxisSpacing: 12,
                          childAspectRatio: 1.05,
                        ),
                        itemCount: cats.length,
                        itemBuilder: (context, i) => _CategoryCard(category: cats[i]),
                      ),
                    ),
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 24),
                      sliver: SliverToBoxAdapter(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(56)),
                              onPressed: () => Navigator.of(context).pushNamed(AppRoutes.aacLearn),
                              icon: const Icon(Icons.school_rounded),
                              label: const Text('Aprendo a comunicarme con Lolo (juego para practicar)'),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              'Para los adultos: «Quiero decir» es un apoyo a la comunicación. No es un tratamiento '
                              'ni sustituye la valoración de un profesional. Todo se guarda solo en este dispositivo.',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _CategoryCard extends StatelessWidget {
  const _CategoryCard({required this.category});

  final AacCategory category;

  @override
  Widget build(BuildContext context) {
    final high = AppServices.of(context).aac.prefs.highContrast;
    final c = category;
    void open() => Navigator.of(context).pushNamed(AppRoutes.aacCategory, arguments: AacCategoryArgs(c.id));
    return Semantics(
      container: true,
      button: true,
      label: c.name,
      excludeSemantics: true,
      onTap: open,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: open,
          child: Ink(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: high ? Colors.white : Color.lerp(c.color, Colors.white, 0.65),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: high ? Colors.black : c.color, width: high ? 4 : 3),
            ),
            child: Column(
              children: [
                Expanded(child: _CategoryArt(category: c)),
                const SizedBox(height: 6),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    c.name,
                    textAlign: TextAlign.center,
                    style: fredoka(20, color: aacInk),
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

/// Dibujo de una categoría: su ilustración 3D (con esquinas redondeadas) o,
/// si no tiene o no se puede abrir, su icono.
class _CategoryArt extends StatelessWidget {
  const _CategoryArt({required this.category});

  final AacCategory category;

  @override
  Widget build(BuildContext context) {
    final icon = FittedBox(
      child: Icon(
        SpeechIcons.lookup(category.icon) ?? Icons.star_rounded,
        color: Color.lerp(category.color, Colors.black, 0.25),
      ),
    );
    final image = category.image;
    if (image == null) return icon;
    return LayoutBuilder(
      builder: (context, box) {
        final side = box.biggest.shortestSide;
        if (!side.isFinite || side <= 0) return icon;
        return Center(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(side * 0.18),
            child: SizedBox.square(
              dimension: side,
              child: Image.asset(
                image,
                fit: BoxFit.contain,
                cacheWidth: (side * MediaQuery.devicePixelRatioOf(context)).ceil(),
                excludeFromSemantics: true,
                errorBuilder: (_, _, _) => icon,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Un tablero con barra de mensaje arriba (lo usan categorías, tablero rápido
/// y emociones).
class _Board extends StatelessWidget {
  const _Board({
    required this.title,
    required this.icon,
    required this.color,
    required this.pictograms,
    this.intro,
    this.sort = true,
  });

  final String title;
  final IconData icon;
  final Color color;
  final List<Pictogram> Function(AacCatalog c) pictograms;
  final String? intro;
  final bool sort;

  @override
  Widget build(BuildContext context) {
    return KidScaffold(
      title: title,
      titleIcon: icon,
      accent: color,
      backLabel: 'Volver',
      body: AacCatalogBuilder(
        builder: (context, catalog) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const AacMessageBar(),
            if (intro != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
                child: Text(intro!, style: fredoka(17, color: AppColors.inkSoft)),
              ),
            Expanded(
              child: PictogramGrid(pictograms: pictograms(catalog), sort: sort),
            ),
          ],
        ),
      ),
    );
  }
}

class AacCategoryScreen extends StatelessWidget {
  const AacCategoryScreen({super.key, required this.categoryId});

  final String categoryId;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<AacCatalog>(
      future: AppServices.of(context).aac.catalog(),
      builder: (context, snapshot) {
        final c = snapshot.data?.category(categoryId);
        return _Board(
          title: c?.name ?? 'Quiero decir',
          icon: Icons.grid_view_rounded,
          color: c?.color ?? aacColor,
          pictograms: (catalog) => catalog.inCategory(categoryId),
        );
      },
    );
  }
}

/// «Necesito decir algo»: las palabras esenciales, siempre visibles, y las
/// que un adulto añada. Funciona sin conexión.
class AacQuickScreen extends StatelessWidget {
  const AacQuickScreen({super.key});

  static List<Pictogram> board(AacCatalog catalog, List<String> extras) {
    final ids = <String>{...catalog.quick, ...extras};
    return catalog.resolve(ids);
  }

  @override
  Widget build(BuildContext context) {
    final aac = AppServices.of(context).aac;
    return _Board(
      title: 'Necesito decir algo',
      icon: Icons.campaign_rounded,
      color: const Color(0xFFEF6C57),
      sort: false,
      pictograms: (catalog) => board(catalog, aac.prefs.quickExtras),
    );
  }
}

/// Emociones y necesidades: se dicen sin tener que explicar por qué.
class AacFeelingsScreen extends StatelessWidget {
  const AacFeelingsScreen({super.key});

  @override
  Widget build(BuildContext context) => _Board(
    title: 'Cómo me siento',
    icon: Icons.favorite_rounded,
    color: const Color(0xFFF06292),
    sort: false,
    intro: 'Todas las emociones están bien. Toca cómo te sientes o lo que necesitas.',
    pictograms: (catalog) => catalog.resolve(catalog.feelings),
  );
}

/// Las frases guardadas desde el constructor.
class AacFavoritesScreen extends StatelessWidget {
  const AacFavoritesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final aac = AppServices.of(context).aac;
    return KidScaffold(
      title: 'Mis frases favoritas',
      titleIcon: Icons.star_rounded,
      accent: const Color(0xFFFFA000),
      backLabel: 'Volver',
      body: ListenableBuilder(
        listenable: aac,
        builder: (context, _) {
          final favs = aac.prefs.favorites;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const AacMessageBar(),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 24),
                  children: [
                    if (favs.isEmpty)
                      Padding(
                        padding: const EdgeInsets.all(12),
                        child: Text(
                          'Todavía no hay frases favoritas. Crea una en «Construyo lo que quiero decir» y toca «Guardar».',
                          textAlign: TextAlign.center,
                          style: fredoka(20, color: AppColors.inkSoft),
                        ),
                      ),
                    for (final f in favs)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: [
                            Expanded(
                              child: Semantics(
                                container: true,
                                button: true,
                                label: f,
                                excludeSemantics: true,
                                onTap: () => aacTap(context, f),
                                child: Material(
                                  color: Colors.transparent,
                                  child: InkWell(
                                    borderRadius: BorderRadius.circular(20),
                                    onTap: () => aacTap(context, f),
                                    child: Ink(
                                      padding: const EdgeInsets.all(16),
                                      decoration: BoxDecoration(
                                        color: Colors.white,
                                        borderRadius: BorderRadius.circular(20),
                                        border: Border.all(color: const Color(0xFFFFA000), width: 3),
                                      ),
                                      child: Row(
                                        children: [
                                          const Icon(
                                            Icons.record_voice_over_rounded,
                                            color: Color(0xFFFFA000),
                                            size: 34,
                                          ),
                                          const SizedBox(width: 12),
                                          Expanded(
                                            child: Text(f, style: fredoka(24, color: aacInk)),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            IconButton(
                              tooltip: 'Quitar de favoritas: $f',
                              iconSize: 32,
                              onPressed: () async {
                                final ok = await showDialog<bool>(
                                  context: context,
                                  builder: (context) => AlertDialog(
                                    title: const Text('¿Quitar esta frase de favoritas?'),
                                    content: Text(f),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(context, false),
                                        child: const Text('No'),
                                      ),
                                      FilledButton(
                                        onPressed: () => Navigator.pop(context, true),
                                        child: const Text('Sí, quitar'),
                                      ),
                                    ],
                                  ),
                                );
                                if (ok == true) aac.removeFavorite(f);
                              },
                              icon: const Icon(Icons.delete_outline_rounded),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

/// «Aprendo a comunicarme con Lolo»: un juego para conocer los pictogramas.
/// Está aparte del tablero: equivocarse aquí no impide usar ningún
/// pictograma para comunicarse.
class AacLearnScreen extends StatelessWidget {
  const AacLearnScreen({super.key, this.seed});

  final int? seed;

  static List<QuizQuestion> questions(AacCatalog c, Random r, {bool feminine = false, int count = 8}) {
    final items = [...c.learn]..shuffle(r);
    return [
      for (final item in items.take(count))
        if (c.byId(item.answer) case final answer?)
          () {
            final options = [answer, ...c.resolve(item.others)]..shuffle(r);
            final said = answer.label(feminine: feminine);
            return QuizQuestion(
              instruction: item.question,
              options: [
                for (final o in options)
                  QuizOption(
                    label: o.label(feminine: feminine),
                    picture: o.picture,
                  ),
              ],
              answer: options.indexOf(answer),
              afterCorrect: '¡Sí! Puedes decir: $said',
            );
          }(),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final aac = AppServices.of(context).aac;
    return KidScaffold(
      title: 'Aprendo a comunicarme',
      titleIcon: Icons.school_rounded,
      accent: const Color(0xFF7E57C2),
      backLabel: 'Volver',
      body: AacCatalogBuilder(
        builder: (context, catalog) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Row(
                children: [
                  Expanded(
                    // Con letra muy grande, el mensaje solo se oye: deja sitio a las respuestas.
                    child: MediaQuery.textScalerOf(context).scale(1) > 1.3
                        ? const SizedBox.shrink()
                        : const LoloBubble(
                            text: '¡Juguemos a conocer los dibujos para decir cosas!',
                            size: 52,
                          ),
                  ),
                  const SizedBox(width: 8),
                  SizedBox(
                    width: 130,
                    child: SpeechActionButton(
                      icon: Icons.grid_view_rounded,
                      label: 'Ir al tablero',
                      color: aacColor,
                      onPressed: () => Navigator.of(context).pushReplacementNamed(AppRoutes.aac),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: SpeechQuizBody(
                seed: seed,
                color: const Color(0xFF7E57C2),
                slowButton: true,
                build: (r) => questions(catalog, r, feminine: aac.prefs.feminine),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
