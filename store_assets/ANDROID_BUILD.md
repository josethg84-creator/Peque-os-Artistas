# Compilación de Android: Pequeños Artistas 1.0.0

## Configuración revisada (Fase 7, 04/11/2026)

| Punto | Valor | Dónde |
|---|---|---|
| applicationId y namespace | `com.pequenosartistas.pequenos_artistas` | `android/app/build.gradle.kts`. **No se podrá cambiar tras la primera publicación.** |
| Versión | `1.0.0+1`: versionName 1.0.0, versionCode 1 | `pubspec.yaml` (`version:`). Cada subida a Play necesita un versionCode mayor. |
| compileSdk / targetSdk | **36** (Android 16) | Valores por defecto de Flutter 3.47.8; comprobados en el APK con `aapt2` |
| minSdk | **24** (Android 7.0) | Por defecto de Flutter |
| Nombre visible | «Pequeños Artistas» | `android:label` |
| Permisos | `RECORD_AUDIO` (opcional, para «Practicar») y uno interno de AndroidX. **Sin INTERNET.** | `AndroidManifest.xml`; comprobado en el APK |
| Micrófono como característica | `android.hardware.microphone` con `required="false"` (**nuevo en la Fase 7**): la app no se oculta en dispositivos sin micrófono | `AndroidManifest.xml` |
| Copias y transferencia | `allowBackup=false`, `fullBackupContent=false` y `dataExtractionRules` que excluye todo (**nuevo en la Fase 7**) | `res/xml/data_extraction_rules.xml` |
| Icono | Adaptativo (Android 8+) e icono clásico | `res/mipmap-*` |
| Pantalla de carga | Fondo crema con la paleta | `res/drawable*/launch_*` |
| Arquitecturas | `arm64-v8a`, `armeabi-v7a`, `x86_64` | |
| Firma de lanzamiento | Clave de subida si existe `android/key.properties`; si no, **clave de depuración** | `build.gradle.kts`, [SIGNING.md](SIGNING.md) |

**Regla de la API objetivo:** desde el 31/08/2026, las apps nuevas y las actualizaciones deben
apuntar a la API 36 o superior (developer.android.com, consultado con búsqueda web). targetSdk 36
cumple. **No se ha cambiado ningún SDK** en esta fase.

## Resultados exactos de las órdenes (04/11/2026)

Entorno: Flutter 3.47.8, Android SDK build-tools 36.0.0, Linux, rama `release/fase-7`.

| Orden | Resultado |
|---|---|
| `flutter clean` | Correcto (borra `build/`, `.dart_tool/`) |
| `flutter pub get` | «Got dependencies!» y «9 packages have newer versions incompatible with dependency constraints» |
| `flutter analyze` | «No issues found!» |
| `flutter test` | «All tests passed!»: **511** pruebas |
| `flutter build apk --release` | `✓ Built build/app/outputs/flutter-apk/app-release.apk (62.6MB)` |
| `flutter build appbundle --release` | `✓ Built build/app/outputs/bundle/release/app-release.aab (60.6MB)` |

**Avisos de la compilación** (no son errores):

- «Your app uses the following plugins that apply Kotlin Gradle Plugin (KGP): flutter_tts… upgrade
  to a version that supports Built-in Kotlin». Habrá que actualizar `flutter_tts` cuando haya una
  versión compatible y probarla. Ver [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
- «Font asset MaterialIcons-Regular.otf was tree-shaken»: es normal.

Comprobaciones del APK (`aapt2 dump badging` y `dump xmltree`):

```
package: name='com.pequenosartistas.pequenos_artistas' versionCode='1' versionName='1.0.0'
minSdkVersion:'24'
targetSdkVersion:'36'
uses-permission: name='android.permission.RECORD_AUDIO'
uses-permission: name='com.pequenosartistas.pequenos_artistas.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION'
uses-feature-not-required: name='android.hardware.microphone'
allowBackup=false · dataExtractionRules=@xml/data_extraction_rules
```

Firma: `apksigner verify --print-certs` → `CN=Android Debug`. **Es la clave de depuración:
sirve para probar, pero Google Play lo rechazaría.**

Las sumas SHA-256 de los paquetes de esta compilación están en la descripción de la PR. Los
paquetes no se suben a git, porque se generan.

## Tamaño

- El APK universal (62,6 MB) lleva las tres arquitecturas.
- Con el AAB, Google Play entrega a cada móvil solo la suya.
- Estimación para un móvil `arm64-v8a`:
  - `libflutter.so` 11,8 MB;
  - `libapp.so` 7,3 MB;
  - recursos (unos 13 MB sin comprimir: miniaturas, vistas previas y dibujos).
- Esto da del orden de 25–30 MB descomprimidos. **La cifra real la dará Play Console**: no se ha
  podido usar `bundletool` en este entorno.
- `BUNDLE-METADATA/…/*.sym` (símbolos de depuración) va dentro del AAB, pero no se descarga a los
  móviles.

## Cómo compilar la versión para Play (propietario)

1. Crear la clave de subida y `android/key.properties`: [SIGNING.md](SIGNING.md). **Nunca** subas
   `key.properties`, `*.jks` ni contraseñas a GitHub (ya están en `.gitignore`).
2. Subir `version:` en `pubspec.yaml` si ya se subió antes un AAB con ese versionCode.
3. Compilar:

   ```bash
   flutter clean
   ```

   ```bash
   flutter pub get
   ```

   ```bash
   flutter test
   ```

   ```bash
   flutter build appbundle --release
   ```

4. Comprobar que la firma **no** es `CN=Android Debug`:

   ```bash
   jarsigner -verify -verbose -certs build/app/outputs/bundle/release/app-release.aab | grep "X.509" | head -1
   ```

5. Subir el AAB **a una pista de prueba interna**, no a producción. Ver
   [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md).

Opcional, para probar sin Play:

```bash
flutter build apk --release
```

Se instala con `adb install build/app/outputs/flutter-apk/app-release.apk`.
