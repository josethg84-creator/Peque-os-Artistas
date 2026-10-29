import 'package:flutter_test/flutter_test.dart';
import 'package:pequenos_artistas/main.dart' as app;
import 'package:pequenos_artistas/screens/home_screen.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

/// Arranca la app con el `main()` real (servicios reales; solo el
/// almacenamiento de la plataforma se simula en memoria).
void main() {
  testWidgets('main() arranca sin errores y muestra el inicio', (tester) async {
    SharedPreferencesAsyncPlatform.instance = InMemorySharedPreferencesAsync.empty();
    app.main();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.byType(HomeScreen), findsOneWidget);
    expect(find.text('Pequeños Artistas'), findsOneWidget);
  });
}
