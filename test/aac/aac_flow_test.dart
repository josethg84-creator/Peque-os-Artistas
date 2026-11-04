import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/aac/aac_catalog.dart';
import 'package:pequenos_artistas/aac/aac_controller.dart';
import 'package:pequenos_artistas/audio/app_audio.dart';
import 'package:pequenos_artistas/navigation/app_routes.dart';
import 'package:pequenos_artistas/persistence/key_value_backend.dart';

import '../test_helpers.dart';

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    // La rejilla se construye al desplazarse: se busca hacia arriba y hacia abajo.
    final scrollable = find.byType(Scrollable).last;
    try {
      await tester.scrollUntilVisible(finder, -250, scrollable: scrollable, maxScrolls: 20);
    } catch (_) {
      await tester.scrollUntilVisible(finder, 250, scrollable: scrollable);
    }
  }
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

Future<void> push(WidgetTester tester, String route, [Object? args]) async {
  tester.state<NavigatorState>(find.byType(Navigator)).pushNamed(route, arguments: args);
  await tester.pumpAndSettle();
}

List<String> get spoken => lastNarrator!.spoken;

Future<AacController> open(
  WidgetTester tester, {
  Size size = const Size(420, 900),
  VoiceInfo? voice,
  DateTime Function()? clock,
}) async {
  setScreenSize(tester, size);
  final aac = AacController(AacStore(MemoryBackend()), clock: clock);
  await aac.load();
  await pumpApp(tester, aac: aac, voice: voice);
  return aac;
}

void main() {
  final catalog = AacCatalog.parse(
    jsonDecode(File(AacCatalog.asset).readAsStringSync()) as Map<String, dynamic>,
  );

  testWidgets('tablero rápido: a un toque desde «Aprendo a Hablar», cada palabra se dice y se ve', (
    tester,
  ) async {
    await open(tester);
    await push(tester, AppRoutes.speech);
    await tapAndSettle(tester, find.bySemanticsLabel('Necesito decir algo'));
    for (final w in [
      'Sí',
      'No',
      'Ayuda',
      'Agua',
      'Baño',
      'Comer',
      'Dolor',
      'Más',
      'Terminé',
      'Para',
      'Quiero',
      'No quiero',
    ]) {
      await tapAndSettle(tester, find.bySemanticsLabel(w));
      expect(spoken.last, w);
      expect(find.bySemanticsLabel('Mensaje: $w'), findsOneWidget);
    }
    expect(lastRecorder, isNull, reason: 'el tablero no usa el micrófono');
    await tapAndSettle(tester, find.bySemanticsLabel('Repetir'));
    expect(spoken.last, 'No quiero');
    await tapAndSettle(tester, find.bySemanticsLabel('Despacio'));
    expect(lastNarrator!.slow.last, 'No quiero');
    await tapAndSettle(tester, find.bySemanticsLabel('Mostrar en grande'));
    expect(find.text('No quiero'), findsWidgets);
    await tapAndSettle(tester, find.byTooltip('Cerrar'));
  });

  testWidgets('las 10 categorías y cada uno de los pictogramas dice exactamente lo que muestra', (
    tester,
  ) async {
    await open(tester, size: const Size(800, 1280));
    await push(tester, AppRoutes.aac);
    var said = 0;
    for (final c in catalog.categories) {
      expect(find.bySemanticsLabel(c.name), findsWidgets, reason: c.name);
      await push(tester, AppRoutes.aacCategory, AacCategoryArgs(c.id));
      for (final pic in catalog.inCategory(c.id)) {
        final label = pic.label();
        final finder = find.bySemanticsLabel(label);
        if (finder.evaluate().isEmpty) {
          await tester.scrollUntilVisible(finder, 200, scrollable: find.byType(Scrollable).last);
        }
        await tester.tap(finder.last);
        await tester.pump();
        expect(spoken.last, label, reason: pic.id);
        said++;
      }
      tester.state<NavigatorState>(find.byType(Navigator)).pop();
      await tester.pumpAndSettle();
    }
    expect(said, catalog.active().length);
  });

  testWidgets('constructor: [YO]+[QUIERO]+[AGUA], escuchar, borrar, limpiar, favorita y volver a decirla', (
    tester,
  ) async {
    final aac = await open(tester);
    await push(tester, AppRoutes.aac);
    await tapAndSettle(tester, find.bySemanticsLabel('Construyo lo que quiero decir'));
    await tapAndSettle(tester, find.bySemanticsLabel('Yo'));
    expect(spoken.last, 'yo');
    await tapAndSettle(tester, find.bySemanticsLabel('Quiero'));
    await tapAndSettle(tester, find.bySemanticsLabel('Agua'));
    expect(find.bySemanticsLabel('Tu frase: Yo quiero agua.'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Escuchar frase'));
    expect(spoken.last, 'Yo quiero agua.');
    await tapAndSettle(tester, find.bySemanticsLabel('Guardar favorita'));
    expect(aac.prefs.favorites, ['Yo quiero agua.']);
    await tapAndSettle(tester, find.bySemanticsLabel('Borrar última'));
    expect(find.bySemanticsLabel('Tu frase: Yo quiero.'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Limpiar'));
    expect(find.bySemanticsLabel('Frase vacía'), findsOneWidget);

    // Otra frase eligiendo un grupo (sin límite de conceptos).
    await tapAndSettle(tester, find.bySemanticsLabel('Me duele'));
    await tapAndSettle(tester, find.bySemanticsLabel('Cabeza'));
    expect(find.bySemanticsLabel('Tu frase: Me duele la cabeza.'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Limpiar'));
    // Cualquier grupo se puede abrir: no hay límite de conceptos.
    await tapAndSettle(tester, find.text('Necesidades básicas'));
    await tapAndSettle(tester, find.bySemanticsLabel('Quiero ir al baño.'));
    expect(find.bySemanticsLabel('Tu frase: Quiero ir al baño.'), findsOneWidget);
    await tapAndSettle(tester, find.bySemanticsLabel('Volver a comenzar'));
    expect(find.bySemanticsLabel('Frase vacía'), findsOneWidget);

    tester.state<NavigatorState>(find.byType(Navigator)).pop();
    await tester.pumpAndSettle();
    await tapAndSettle(tester, find.bySemanticsLabel('Mis frases favoritas'));
    await tapAndSettle(tester, find.bySemanticsLabel('Yo quiero agua.'));
    expect(spoken.last, 'Yo quiero agua.');
    await tapAndSettle(tester, find.byTooltip('Quitar de favoritas: Yo quiero agua.'));
    await tapAndSettle(tester, find.text('Sí, quitar'));
    expect(aac.prefs.favorites, isEmpty);
  });

  testWidgets('emociones y necesidades: se dicen sin explicar por qué', (tester) async {
    await open(tester);
    await push(tester, AppRoutes.aac);
    await tapAndSettle(tester, find.bySemanticsLabel('Cómo me siento'));
    expect(find.textContaining('Todas las emociones están bien'), findsOneWidget);
    for (final t in ['Estoy triste.', 'Tengo miedo.', 'Necesito un abrazo.']) {
      await tapAndSettle(tester, find.bySemanticsLabel(t));
      expect(spoken.last, t);
    }
  });

  testWidgets('ajustes: confirmar antes de hablar, femenino, voz lenta y evitar toques dobles', (
    tester,
  ) async {
    var now = DateTime(2026, 11, 4, 10);
    final aac = await open(tester, clock: () => now);
    aac.update((p) {
      p.confirmBeforeSpeak = true;
      p.feminine = true;
      p.slowVoice = true;
    });
    await push(tester, AppRoutes.aacFeelings);
    final before = spoken.length;
    await tapAndSettle(tester, find.bySemanticsLabel('Estoy cansada.'));
    expect(spoken.length, before, reason: 'espera a «Decirlo»');
    await tapAndSettle(tester, find.bySemanticsLabel('Decir: Estoy cansada.'));
    expect(spoken.last, 'Estoy cansada.');
    expect(lastNarrator!.slow.last, 'Estoy cansada.');

    aac.update((p) {
      p.confirmBeforeSpeak = false;
      p.tapGuardMs = 1000;
    });
    await tester.pumpAndSettle();
    now = now.add(const Duration(seconds: 5));
    final n = spoken.length;
    await tester.tap(find.bySemanticsLabel('Estoy tranquila.'));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.tap(find.bySemanticsLabel('Estoy tranquila.'));
    await tester.pump();
    expect(spoken.length, n + 1, reason: 'el segundo toque inmediato se ignora');
  });

  testWidgets('sin voz o con el sonido apagado: la frase se ve y se avisa', (tester) async {
    await open(tester, voice: const VoiceInfo(available: false, description: 'Sin voz'));
    await push(tester, AppRoutes.aacQuick);
    await tapAndSettle(tester, find.bySemanticsLabel('Agua'));
    expect(find.bySemanticsLabel('Mensaje: Agua'), findsOneWidget);
    expect(find.textContaining('La voz no está disponible'), findsOneWidget);
  });

  testWidgets('aprender con Lolo es aparte: un error no bloquea nada y se puede ir al tablero', (
    tester,
  ) async {
    await open(tester);
    await push(tester, AppRoutes.aacLearn);
    final q = catalog.learn.firstWhere((l) => spoken.last == l.question);
    final wrong = catalog.byId(q.others.first)!.label();
    await tapAndSettle(tester, find.bySemanticsLabel(wrong));
    expect(spoken.last, '¡Casi! Prueba otra vez.');
    await tapAndSettle(tester, find.bySemanticsLabel(catalog.byId(q.answer)!.label()));
    expect(spoken.last, '¡Sí! Puedes decir: ${catalog.byId(q.answer)!.label()}');
    await tapAndSettle(tester, find.bySemanticsLabel('Ir al tablero'));
    expect(find.bySemanticsLabel('Necesito decir algo'), findsWidgets);
  });

  testWidgets('zona de adultos: ajustes, tablero rápido y borrar la personalización', (tester) async {
    final aac = await open(tester, size: const Size(800, 1280));
    aac.addFavorite('Hola.');
    await push(tester, AppRoutes.adultZone, const AdultZoneArgs.verified());
    final title = find.text('Quiero decir (comunicación con pictogramas)');
    await tester.scrollUntilVisible(title, 300, scrollable: find.byType(Scrollable).first);
    expect(find.textContaining('No es un tratamiento médico'), findsOneWidget);
    await tapAndSettle(tester, find.text('Grande'));
    expect(aac.prefs.tileSize, AacTileSize.large);
    await tapAndSettle(tester, find.widgetWithText(SwitchListTile, 'Alto contraste'));
    expect(aac.prefs.highContrast, isTrue);
    await tapAndSettle(tester, find.text('Elegir palabras del tablero rápido'));
    expect(find.text('Esencial: siempre visible'), findsWidgets);
    await tapAndSettle(tester, find.widgetWithText(CheckboxListTile, 'Te quiero.'));
    expect(aac.prefs.quickExtras, ['te_quiero']);
    await tapAndSettle(tester, find.text('Listo'));
    await tapAndSettle(tester, find.text('Borrar personalización'));
    await tapAndSettle(tester, find.text('Borrar'));
    expect(aac.prefs.favorites, isEmpty);
    expect(aac.prefs.highContrast, isFalse);
  });

  testWidgets('accesibilidad: botones con nombre y tamaño táctil suficiente', (tester) async {
    final handle = tester.ensureSemantics();
    await open(tester);
    for (final (route, args) in [
      (AppRoutes.aac, null),
      (AppRoutes.aacQuick, null),
      (AppRoutes.aacBuilder, null),
      (AppRoutes.aacFeelings, null),
      (AppRoutes.aacCategory, const AacCategoryArgs('necesidades')),
    ]) {
      await push(tester, route, args);
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      tester.state<NavigatorState>(find.byType(Navigator)).pop();
      await tester.pumpAndSettle();
    }
    handle.dispose();
  });
}
