import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
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
  testWidgets('el inicio muestra nombre, bienvenida, botón principal y accesos', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    expect(find.text('Pequeños Artistas'), findsOneWidget);
    expect(find.text('¡Hola! ¿Qué quieres pintar hoy?'), findsOneWidget);
    expect(find.bySemanticsLabel('¡Vamos a pintar!'), findsOneWidget);
    expect(find.bySemanticsLabel('Galería'), findsOneWidget);
    expect(find.bySemanticsLabel('Actividades. Pronto'), findsOneWidget);
    expect(find.bySemanticsLabel('Mis dibujos'), findsOneWidget);
    expect(find.bySemanticsLabel('Zona para adultos'), findsOneWidget);
  });

  testWidgets('«¡Vamos a pintar!» abre un dibujo con un solo toque y se puede volver', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
    expect(find.byType(ColoringScreen), findsOneWidget);
    expect(find.text('Gato'), findsOneWidget);
    expect(find.bySemanticsLabel('Dibujo para colorear: Gato'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a la galería'));
    expect(find.byType(HomeScreen), findsOneWidget);
    // La siguiente pulsación propone otro dibujo fácil.
    await tapAndSettle(tester, find.bySemanticsLabel('¡Vamos a pintar!'));
    expect(find.text('Elefante'), findsOneWidget);
  });

  testWidgets('las cinco categorías abren su galería con el número correcto de dibujos', (tester) async {
    setScreenSize(tester, const Size(800, 1280));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Galería'));
    expect(find.byType(CategoriesScreen), findsOneWidget);

    const expected = {
      DrawingCategory.animals: 10,
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
    await tapAndSettle(tester, find.bySemanticsLabel('Galería'));
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
    await tapAndSettle(tester, find.bySemanticsLabel('Mis dibujos'));
    expect(find.text('Aquí verás tus dibujos'), findsOneWidget);
    await tapAndSettle(tester, find.text('Ir a la galería'));
    expect(find.byType(CategoriesScreen), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    expect(find.byType(HomeScreen), findsOneWidget);
  });

  testWidgets('las actividades están marcadas como «Pronto» y avisan al tocarlas', (tester) async {
    setScreenSize(tester, const Size(400, 860));
    await pumpApp(tester);
    await tapAndSettle(tester, find.bySemanticsLabel('Actividades. Pronto'));
    expect(find.bySemanticsLabel('Los colores. Pronto'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Los colores. Pronto'));
    expect(find.text('¡Esta actividad llegará muy pronto!'), findsOneWidget);
    await tapAndSettle(tester, find.text('Vale'));
    await tapAndSettle(tester, find.bySemanticsLabel('Volver al inicio'));
    expect(find.byType(HomeScreen), findsOneWidget);
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
    expect(find.textContaining('30 dibujos disponibles'), findsOneWidget);
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
