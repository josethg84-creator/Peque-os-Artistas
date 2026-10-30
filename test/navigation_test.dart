import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/learning/learning_level.dart';
import 'package:pequenos_artistas/models/drawing_category.dart';
import 'package:pequenos_artistas/navigation/app_router.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/screens/categories_screen.dart';
import 'package:pequenos_artistas/screens/coloring_screen.dart';
import 'package:pequenos_artistas/screens/gallery_screen.dart';
import 'package:pequenos_artistas/screens/home_screen.dart';
import 'package:pequenos_artistas/widgets/drawing_card.dart';

import 'test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('el inicio muestra logo, subtítulo, personajes, tarjetas y barra inferior', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    expect(find.bySemanticsLabel('Pequeños Artistas'), findsOneWidget);
    expect(find.text('Un mundo de colores, juegos y creatividad'), findsOneWidget);
    expect(find.bySemanticsLabel('Un niño y una niña con pinceles y su perrito'), findsOneWidget);
    for (final label in ['Colorear', 'Mini Juegos', 'Actividades', 'Galería', 'Perfil', 'Logros']) {
      expect(find.bySemanticsLabel(label), findsOneWidget, reason: label);
    }
    // Configuración: arriba a la izquierda y en la barra inferior.
    expect(find.bySemanticsLabel('Configuración'), findsNWidgets(2));
    expect(find.bySemanticsLabel('Música activada'), findsOneWidget);
    expect(find.bySemanticsLabel('Zona para adultos'), findsOneWidget);
  });

  testWidgets('cada botón del inicio abre su pantalla y se puede volver', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    const destinations = {
      'Colorear': ('Elige una categoría', 'Volver al inicio'),
      'Mini Juegos': ('Mini juegos', 'Volver al inicio'),
      'Actividades': ('Actividades', 'Volver al inicio'),
      'Galería': ('Mis dibujos', 'Volver al inicio'),
      'Perfil': ('¡Hola, artista!', 'Volver al inicio'),
      'Logros': ('Mis premios', 'Volver'),
    };
    for (final MapEntry(key: button, value: (title, back)) in destinations.entries) {
      await tapAndSettle(tester, find.bySemanticsLabel(button));
      expect(find.byType(HomeScreen), findsNothing, reason: button);
      expect(find.text(title), findsWidgets, reason: button);
      await tapAndSettle(tester, find.bySemanticsLabel(back));
      expect(find.byType(HomeScreen), findsOneWidget, reason: button);
    }
    for (final settings in find.bySemanticsLabel('Configuración').evaluate().toList().indexed) {
      await tapAndSettle(tester, find.bySemanticsLabel('Configuración').at(settings.$1));
      expect(find.text('Sonido y música'), findsWidgets);
      await tapAndSettle(tester, find.bySemanticsLabel('Volver'));
      expect(find.byType(HomeScreen), findsOneWidget);
    }
  });

  testWidgets('el botón de música enciende y apaga la música', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Música activada'));
    expect(find.bySemanticsLabel('Música desactivada'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Música desactivada'));
    expect(find.bySemanticsLabel('Música activada'), findsOneWidget);
  });

  testWidgets('«¡Vamos a pintar!» (en Colorear) abre un dibujo fácil y se puede volver', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    await startPainting(tester);
    expect(find.byType(ColoringScreen), findsOneWidget);
    expect(find.text('Gato'), findsOneWidget);
    expect(find.bySemanticsLabel('Dibujo para colorear: Gato'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.byType(CategoriesScreen), findsOneWidget);
    // La siguiente pulsación propone otro dibujo fácil.
    await startPainting(tester);
    expect(find.text('Conejo'), findsOneWidget);
  });

  testWidgets('las cinco categorías abren su galería con el número correcto de dibujos', (tester) async {
    setScreenSize(tester, const Size(800, 1280));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
    expect(find.byType(CategoriesScreen), findsOneWidget);

    const expected = {
      DrawingCategory.animals: 11,
      DrawingCategory.vehicles: 5,
      DrawingCategory.dinosaurs: 5,
      DrawingCategory.fruits: 5,
      DrawingCategory.fantasy: 5,
    };
    for (final MapEntry(key: category, value: count) in expected.entries) {
      final card = find.bySemanticsLabel('${category.label}, $count dibujos');
      await tapAndSettle(tester, card);
      expect(find.byType(GalleryScreen), findsOneWidget, reason: category.label);
      final grid = find.byType(GridView);
      // Desplaza hasta el final para contar todas las tarjetas creadas.
      final seen = <String>{};
      for (var i = 0; i < 6; i++) {
        seen.addAll(tester.widgetList<DrawingCard>(find.byType(DrawingCard)).map((c) => c.drawing.id));
        await tester.drag(grid, const Offset(0, -400));
        await tester.pumpAndSettle();
      }
      expect(seen, hasLength(count), reason: category.label);
      await tapAndSettle(tester, find.bySemanticsLabel('Volver a categorías'));
      expect(find.byType(CategoriesScreen), findsOneWidget);
    }
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets('galería → dibujo → volver a la galería', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Colorear'));
    await tapAndSettle(tester, find.bySemanticsLabel('Frutas, 5 dibujos'));
    await tapAndSettle(tester, find.bySemanticsLabel('Fresa. Dificultad fácil'));
    expect(find.byType(ColoringScreen), findsOneWidget);
    expect(find.text('Fresa'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.byType(GalleryScreen), findsOneWidget);
  });

  testWidgets('Mis dibujos vacío ofrece ir a la galería', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Galería'));
    expect(find.text('¡Tu galería te espera!'), findsOneWidget);
    await tapAndSettle(tester, find.text('Ir a pintar'));
    expect(find.byType(CategoriesScreen), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets('«Actividades» y «Mini Juegos» muestran cada uno sus juegos', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    const groups = {
      'Actividades': [
        'Aprende los colores',
        'Descubre las formas',
        'Encuentra a los animales',
        'Trazos y escritura',
      ],
      'Mini Juegos': ['Une las parejas', 'Rompecabezas', 'Laberintos'],
    };
    for (final MapEntry(key: group, value: games) in groups.entries) {
      await tapAndSettle(tester, find.bySemanticsLabel(group));
      for (final title in GameId.values.map((g) => g.title)) {
        final tile = find.bySemanticsLabel(RegExp('^${RegExp.escape(title)}'));
        expect(tile, games.contains(title) ? findsOneWidget : findsNothing, reason: '$group: $title');
      }
      await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
      expect(find.byType(HomeScreen), findsOneWidget);
    }
  });

  testWidgets('«Perfil» muestra el progreso, los dibujos recientes y abre uno', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Perfil'));
    expect(find.text('¡Hola, artista!'), findsOneWidget);
    expect(find.bySemanticsLabel('Dibujos: 0'), findsOneWidget);
    expect(find.text('Aún no hay dibujos. ¡Pinta el primero!'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));

    // Se pinta una zona del gato y el panel lo refleja.
    await startPainting(tester);
    final gato = svgOf('animals', 'animal_gato');
    await tapAndSettle(tester, find.bySemanticsLabel('Rojo'));
    await tester.tapAt(screenPointOf(tester, gato, interiorPoint(gato, 'cabeza')));
    await tester.pump();
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    await tapAndSettle(tester, find.bySemanticsLabel('Perfil'));
    expect(find.bySemanticsLabel('Dibujos: 1'), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp(r'^Mini juegos probados: 0 de 3')), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp(r'^Actividades probadas: 0 de 4')), findsOneWidget);
    final recent = find.bySemanticsLabel(RegExp(r'^Gato\. '));
    await tapAndSettle(tester, recent);
    expect(find.byType(ColoringScreen), findsOneWidget);
    expect(find.text('Gato'), findsOneWidget);
  });

  testWidgets('la zona de adultos exige mantener pulsado y responder bien', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    final lock = find.bySemanticsLabel('Zona para adultos');

    // Un toque normal no abre nada.
    await tester.tap(lock);
    await tester.pumpAndSettle();
    expect(find.text('Solo para adultos'), findsNothing);

    // Respuesta incorrecta: se queda en el inicio.
    await tester.longPress(lock);
    await tester.pumpAndSettle();
    var (a, b) = _question(tester);
    final wrong = tester
        .widgetList<OutlinedButton>(find.byType(OutlinedButton))
        .map((w) => int.parse(((w.child as Text).data)!))
        .firstWhere((v) => v != a * b);
    await tapAndSettle(tester, find.text('$wrong'));
    expect(find.byType(HomeScreen), findsOneWidget);
    expect(find.text('Zona para adultos'), findsNothing);

    // Respuesta correcta: entra en la zona de adultos.
    await tester.longPress(lock);
    await tester.pumpAndSettle();
    (a, b) = _question(tester);
    await tapAndSettle(tester, find.widgetWithText(OutlinedButton, '${a * b}'));
    expect(find.text('Zona para adultos'), findsOneWidget);
    expect(find.textContaining('31 dibujos disponibles'), findsOneWidget);
    await tapAndSettle(tester, find.byTooltip('Salir al inicio'));
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets('las rutas desconocidas o sin argumentos llevan a una pantalla segura', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    final navigator = tester.state<NavigatorState>(find.byType(Navigator));
    for (final route in ['/no-existe', '/galeria', '/colorear', '/adultos']) {
      navigator.pushNamed(route);
      await tester.pumpAndSettle();
      expect(find.text('Ups, aquí no hay nada'), findsOneWidget, reason: route);
      await tapAndSettle(tester, find.text('Ir al inicio'));
      expect(find.byType(HomeScreen), findsOneWidget);
    }
  });

  testWidgets('un dibujo inexistente muestra un aviso amable', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    final navigator = tester.state<NavigatorState>(find.byType(Navigator));
    navigator.push(
      AppRouter.onGenerateRoute(
        const RouteSettings(name: AppRoutes.coloring, arguments: ColoringArgs('dibujo_inexistente')),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No encontramos este dibujo'), findsOneWidget);
    await tapAndSettle(tester, find.text('Ir al inicio'));
    expect(find.byType(HomeScreen), findsOneWidget);
  });
}

(int, int) _question(WidgetTester tester) {
  final text = tester.widget<Text>(find.textContaining('¿cuánto es')).data!;
  final match = RegExp(r'(\d+) × (\d+)').firstMatch(text)!;
  return (int.parse(match[1]!), int.parse(match[2]!));
}
