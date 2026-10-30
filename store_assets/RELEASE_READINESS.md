# Preparación para Google Play: Pequeños Artistas 1.0.0

**Fecha de revisión:** 29/10/2026 · **Commit base:** rama `claude/awesome-newton-ettb3r`
(Fase 9)

**Conclusión: todavía NO está lista para enviarse.** La app y los recursos están preparados y
verificados. Faltan pasos que solo puede dar el propietario:

- la clave de subida;
- la cuenta de desarrollador;
- el correo de contacto;
- la URL pública de la política de privacidad;
- los formularios de Play Console;
- las pruebas obligatorias para cuentas personales nuevas.

**No se ha publicado ni subido nada a Google Play ni a ningún servicio externo.**

Leyenda:

- ✅ COMPLETADO Y VERIFICADO
- 🟡 PENDIENTE
- ⛔ BLOQUEADO
- ➖ NO APLICA, con justificación

## Estructura de `store_assets/`

```
store_assets/
├── RELEASE_READINESS.md            ← este informe
├── SIGNING.md                      ← cómo crear y usar la clave de subida
├── icon/play_store_icon_512.png
├── feature_graphic/feature_graphic_1024x500.png
├── screenshots/                    ← phone/ (8), phone_extra/ (3), android_emulator/, README.md
├── store_listing/                  ← FICHA_GOOGLE_PLAY.md, textos .txt, DECLARACIONES_PLAY_CONSOLE.md
└── privacy/                        ← privacy_policy_draft.md, AUDITORIA_PRIVACIDAD.md, REVISION_POLITICA_FAMILIAS.md
```

## A. Aplicación

| Punto | Estado | Detalle |
|---|---|---|
| Nombre visible en el móvil | ✅ | «Pequeños Artistas» (`android:label`); comprobado en el APK con `aapt2`. |
| Nombre de la ficha | 🟡 | «Pequeños Artistas: Colorea y Aprende» tiene **36 caracteres** y Play admite **30**. Propuesta: «Pequeños Artistas: Colorea» (26). Decide el propietario. Existe otra app llamada «Pequeño Artista»: ver `store_listing/FICHA_GOOGLE_PLAY.md`. |
| Identificador del paquete | 🟡 | `com.pequenosartistas.pequenos_artistas`. Es válido, pero **no se podrá cambiar después de la primera publicación**. No se ha tocado. El propietario debe confirmarlo o cambiarlo **antes** de la primera subida. |
| Versión | ✅ | `1.0.0+1` (versionName 1.0.0, versionCode 1), comprobada en el manifiesto final. Cada nueva subida necesita un versionCode mayor (`version:` en `pubspec.yaml`). |
| API objetivo | ✅ | **targetSdk 36** (Android 16), compileSdk 36, minSdk 24 (Android 7.0). Cumple la regla vigente: desde el 31/08/2026, las apps nuevas y las actualizaciones deben apuntar a la API 36 o superior (developer.android.com, consultado el 29/10/2026). |
| Permisos | ✅ | Ningún permiso peligroso y **sin INTERNET**. Solo hay un permiso interno de AndroidX. |
| Icono de lanzamiento | 🟡 | Icono adaptativo (Android 8+), con la paleta sobre fondo crema y dentro de la zona segura (comprobado con máscaras circular y redondeada), más un icono clásico para Android 7. Incluido en el APK. **No se pudo ver en el lanzador del emulador** (pantalla negra): hay que mirarlo en un móvil. |
| Pantalla de inicio | ✅ | Fondo crema con la paleta, en lugar de la pantalla blanca. **Vista en el emulador Android 16.** |
| Estado del APK | ✅ / 🟡 | `app-release.apk`, 53,5 MB, compilado con el código final de la Fase 9. **Se instaló y abrió en un emulador Android 16** (pantalla de carga e inicio correctos). Solo sirve para pruebas: está firmado con la clave de depuración. |
| Miniaturas en Android | ⛔ hasta probarlo en un móvil | En el emulador sin aceleración, las miniaturas de la galería no se decodifican («Could not decompress image»). Los archivos son válidos (`test/thumbnail_decode_test.dart`) y la causa probable es el emulador. **Antes de publicar, hay que comprobar en un móvil real que se ven.** Detalle en `screenshots/android_emulator/README.md`. |
| Estado del AAB | ✅ / 🟡 | `app-release.aab`, 52,5 MB. Compila correctamente; el manifiesto final está comprobado y el AAB contiene `arm64-v8a`, `armeabi-v7a` y `x86_64`. **Está firmado con la clave de depuración, así que Play lo rechazaría:** hay que recompilarlo con la clave de subida. No se ha podido usar bundletool (la descarga se denegó en este entorno). |
| Firma | 🟡 | No hay clave de subida. `build.gradle.kts` ya la lee de `android/key.properties` si existe, y las claves están excluidas de git. Pasos en [SIGNING.md](SIGNING.md). |
| Secretos en el repositorio | ✅ | No hay `.jks`, `.keystore` ni `key.properties` en git. Están añadidos a `.gitignore`. |
| Pruebas automáticas | ✅ | `flutter analyze` sin avisos; `flutter test`: 280 pruebas superadas (incluye el sistema de sonido). |
| Prueba en un dispositivo real | 🟡 | No hay dispositivo en este entorno. El emulador sin aceleración solo permitió comprobar la instalación, la pantalla de carga y el inicio. **El propietario debe probarla en un móvil real**: miniaturas, colorear, guardar, juegos, voz y sonido (checklists de `docs/FASE5_GUARDADO.md` y `docs/FASE7_ANIMACIONES.md`). |
| Tamaño de descarga | 🟡 | Con AAB, Google genera APK por arquitectura. El APK arm64 equivalente pesa unos 19 MB (Fase 8). La cifra exacta la mostrará Play Console. |

## B. Recursos de la ficha

| Punto | Estado | Detalle |
|---|---|---|
| Icono de 512 × 512 | ✅ | `icon/play_store_icon_512.png`: 512 × 512, PNG de 32 bits (RGBA opaco), 70 KB (límite: 1 MB). Logo de la app, sin textos ni insignias. |
| Imagen destacada de 1024 × 500 | ✅ | `feature_graphic/feature_graphic_1024x500.png`: 1024 × 500, PNG RGB de 24 bits sin transparencia, 137 KB. Ilustraciones reales de la app (`tools/store_art_test.dart`) y fuente Roboto. Sin premios ni sellos. |
| Capturas de pantalla | ✅ / 🟡 | 8 de teléfono (más 3 extra) a 1080 × 2160, RGB, reales y recorridas jugando. Proceden de la **build web** del mismo código, porque el emulador era demasiado lento. Ver `screenshots/README.md`. Conviene repetirlas en un móvil real. |
| Capturas de tableta | 🟡 | No hechas. Son opcionales, pero recomendables si se quiere aparecer bien en tabletas (la app se adapta a ellas). |
| Nombre y descripción breve | 🟡 | Redactados y medidos: 26/30 y 78/80. **Falta la aprobación del propietario.** |
| Descripción completa | 🟡 | Redactada (2156/4000, con la música y los sonidos) y contrastada con el código. Falta la aprobación del propietario. |
| Categoría y etiquetas | 🟡 | Propuesta: «Educación» (alternativa: «Arte y diseño») y etiquetas de colorear y educación infantil. Las elige el propietario en Play Console. |
| Idioma principal | 🟡 | Propuesta: Español (Latinoamérica), `es-419`. |

## C. Privacidad y políticas

| Punto | Estado | Detalle |
|---|---|---|
| Auditoría de privacidad | ✅ | `privacy/AUDITORIA_PRIVACIDAD.md`. No se recogen ni transmiten datos; no hay SDK, anuncios ni AAID; todo es local. |
| Política de privacidad redactada | 🟡 | `privacy/privacy_policy_draft.md`: borrador fiel a la auditoría. Faltan el responsable, el contacto y la **revisión legal**. |
| URL pública de la política | ⛔ | **Bloqueado hasta que el propietario la publique.** No se ha inventado ninguna URL ni se ha publicado nada. |
| Declaración de seguridad de los datos | 🟡 | La información está preparada en `store_listing/DECLARACIONES_PLAY_CONSOLE.md` §7. La declara el propietario. |
| Público objetivo | 🟡 | Tramos «5 años o menos» y «6 a 8 años». Lo confirma el propietario. |
| Cuestionario de clasificación de contenido | 🟡 | Datos preparados (§4). Lo rellena el propietario; la clasificación la asigna IARC. |
| Revisión de la Política de Familias | ✅ / 🟡 | `privacy/REVISION_POLITICA_FAMILIAS.md`: no se detecta ningún incumplimiento técnico. Hecha **sin poder abrir la página oficial**, así que el propietario debe leer la versión vigente. |
| Anuncios y compras | ➖ | La app no tiene anuncios ni compras (verificado en las dependencias y el manifiesto). |

## D. Cuenta y publicación

| Punto | Estado | Detalle |
|---|---|---|
| Cuenta de desarrollador de Google Play | ⛔ | No consta que exista. La crea el propietario (pago único y verificación de identidad). |
| Datos de contacto | ⛔ | Faltan el correo de contacto (obligatorio), el nombre visible del desarrollador y, si se piden, la dirección y el teléfono. No se ha inventado nada. |
| Verificación de identidad | 🟡 | Google pide verificar la identidad del titular, y la de la organización si es una cuenta de empresa. Lo hace el propietario. |
| Pruebas previas | 🟡 | Las **cuentas personales nuevas** deben hacer una **prueba cerrada** antes de poder publicar en producción: al menos 12 testers durante 14 días seguidos, según la ayuda de Play Console consultada por búsqueda. **Confirma la regla vigente en Play Console**; para cuentas de organización no aplica. |
| Configuración de la ficha | 🟡 | Textos y recursos listos para subir. |
| Revisión final del propietario | 🟡 | Revisar todos los textos, la política, las capturas y el nombre, y probar en un móvil real. |

## Riesgos y bloqueos

0. **Miniaturas en Android (crítico):** comprobar en un móvil real que la galería muestra las miniaturas. En el emulador no se veían; la causa probable es el entorno emulado.
0b. **Derechos de las imágenes de «Catalogo Imagenes/»:** 8 animales (7 sustituidos y la cebra) proceden de imágenes subidas por el propietario. Antes de publicar, confirma que puedes usarlas comercialmente (si se generaron con una herramienta de IA, revisa sus condiciones de uso).
1. **Firma:** sin clave de subida, Play rechaza el AAB. Si se pierde la clave de subida, se
   puede restablecer con Play App Signing, pero conviene hacer una copia de seguridad.
2. **Nombre:** el nombre propuesto no cabe en 30 caracteres, y «Pequeño Artista» ya existe.
3. **Identificador del paquete:** es permanente tras la primera publicación. Decídelo ahora.
4. **Pruebas cerradas:** si la cuenta es personal y nueva, añaden al menos 14 días antes de
   producción.
5. **Verificación limitada:** este entorno no tiene acceso a `support.google.com` ni a
   `play.google.com`, ni dispositivo físico. Hay que repasar las políticas vigentes y probar
   en un móvil real antes de enviar.
6. **Voz:** depende del motor de texto a voz del móvil. En el emulador tardó en arrancar y la
   app siguió funcionando sin voz, sin errores. Prueba con la voz en español instalada.
7. **Transferencia entre dispositivos (D2D):** `allowBackup=false` no la desactiva del todo
   en Android 12+. El riesgo es bajo porque solo hay dibujos y progreso; ver la auditoría.

## Pasos en Play Console (cuando el propietario lo decida)

1. Crear la cuenta de desarrollador y verificar la identidad.
2. Crear la app: nombre, idioma predeterminado `es-419`, «Aplicación», «Gratuita». Ojo: una
   app gratuita **no puede pasar a ser de pago**.
3. Rellenar «Contenido de la aplicación» con `store_listing/DECLARACIONES_PLAY_CONSOLE.md`:
   1. política de privacidad (URL);
   2. acceso a la app;
   3. anuncios;
   4. clasificación de contenido;
   5. público objetivo;
   6. seguridad de los datos;
   7. ID de publicidad;
   8. apps gubernamentales, de noticias y de salud.
4. Rellenar la ficha principal: textos de `store_listing/`, icono, imagen destacada y
   capturas. Añadir los datos de contacto.
5. Crear la clave de subida ([SIGNING.md](SIGNING.md)), compilar el AAB firmado y comprobar
   la firma.
6. Subirlo a **Pruebas internas** y después a **Prueba cerrada**. Si la cuenta es personal y
   nueva, mantener al menos 12 testers durante 14 días.
7. Revisar el informe previo al lanzamiento (*pre-launch report*) de Play Console.
8. Solicitar el acceso a producción si aplica, enviar a revisión y publicar.

**Ninguno de estos pasos se ha hecho desde aquí.**
