# Problemas conocidos: versión candidata 1.0.0 (Fase 7, 04/11/2026)

Clasificación:

- **Crítico:** impide publicar en producción.
- **Importante:** conviene resolverlo antes o justo después de la primera versión.
- **Menor:** detalle.

«Externo» significa que no se puede resolver con código en este entorno: lo debe hacer el
propietario o hace falta un dispositivo real.

## Críticos (bloquean producción, no la prueba interna o cerrada)

| ID | Problema | Tipo | Qué hacer |
|---|---|---|---|
| C1 | El AAB y el APK están firmados con la **clave de depuración**, que Play rechaza | Externo | Crear la clave de subida ([SIGNING.md](SIGNING.md)) y recompilar |
| C2 | **Miniaturas sin verificar en Android real.** En el emulador Android 16 sin aceleración no se decodificaban («Could not decompress image»). Los archivos son válidos (`test/thumbnail_decode_test.dart`) y en la web se ven | Externo (dispositivo) | Comprobar en un móvil real. Si fallan, es un error crítico de código que hay que arreglar antes de publicar |
| C3 | **Política de privacidad sin publicar** y sin datos de contacto (nombre legal, correo) | Externo | Completar [privacy/privacy_policy_draft.md](privacy/privacy_policy_draft.md), revisarla legalmente y publicarla en una URL |
| C4 | **Ninguna prueba en un dispositivo real** (voz, micrófono, sonido, tacto, rendimiento) | Externo | [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md), sección 3 |
| C5 | **Prueba cerrada obligatoria** (12 testers, 14 días) si la cuenta es personal y nueva | Externo | [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md), sección 5 |

Ningún fallo crítico conocido está en el código. Aun así, C2 y C4 pueden descubrir alguno.
**Por eso esta versión es candidata para prueba interna o cerrada, no para producción.**

## Importantes

| ID | Problema | Estado |
|---|---|---|
| I1 | En una **tableta en vertical**, varias pantallas de «Aprendo a Hablar» (conversaciones, cuentos, menú) dejan mucho espacio vacío y las tarjetas se ven pequeñas. Se puede usar sin problemas, pero no aprovecha la pantalla | Abierto. No se ha cambiado en esta fase para no tocar 15 pantallas sin probarlas en una tableta real. Hay que hacer una rejilla adaptable por ancho |
| I2 | No hay un botón único «Borrar todos los datos» dentro de la app. Se borra por partes (dibujos, «Quiero decir») o desde los ajustes de Android | Abierto; está documentado en la política |
| I3 | `flutter_tts` usa el plugin de Kotlin antiguo (KGP); una versión futura de Flutter podría dejar de compilarlo | Abierto. Actualizar cuando haya una versión compatible, sin cambiar SDK a ciegas |
| I4 | 9 dependencias tienen versiones nuevas incompatibles con las restricciones actuales | Abierto. No se actualizan antes del lanzamiento para no introducir riesgos |
| I5 | El nombre se parece a otra app («Pequeño Artista») | Externo: decide el propietario ([PLAY_STORE_LISTING.md](PLAY_STORE_LISTING.md)) |
| I6 | En la web (no en Android) la voz depende del navegador; algunas voces del navegador funcionan en línea | Avisado en la zona de adultos y en la política |
| I7 | El tamaño de descarga real por arquitectura no se ha medido (sin `bundletool`) | Externo: lo muestra Play Console |

## Menores

| ID | Problema |
|---|---|
| M1 | En el constructor de frases a 360 dp, los rótulos de algunos botones («Volver a comenzar») salen en letra pequeña, aunque los botones miden 48 dp o más |
| M2 | Algunas capturas (`phone_v2/05`, `07`, `08`, tableta) muestran «La voz no está disponible», porque el navegador de este entorno no tiene voces. No se usan en la selección propuesta |
| M3 | La imagen destacada anterior (`feature_graphic/`) usa el estilo plano antiguo. La v2 (`promo/`) usa la ilustración actual |
| M4 | Durante la compilación aparece «Caught exception: Already watching path: …/android». Es un mensaje de la herramienta y no afecta al resultado |

## Corregidos en la Fase 7

| Gravedad | Problema | Corrección | Prueba |
|---|---|---|---|
| Importante | En teléfonos de 360 dp, los botones del inicio partían palabras («Aprend/o a Hablar», «Necesit/o decir algo») | `AacShortcut` pone el dibujo encima del texto cuando es estrecho, y el inicio deja más alto para ellos | `test/narrow_phone_test.dart` (mide con Fredoka; falla sin la corrección) |
| Importante | Play habría marcado el **micrófono como obligatorio** (por el permiso), ocultando la app en dispositivos sin micrófono | `uses-feature android.hardware.microphone required="false"` | `persistence_flow_test.dart` (12b) |
| Importante | Los datos (incluidas las frases favoritas) podían pasar a otro teléfono por transferencia directa (Android 12+) | `dataExtractionRules` excluye todo | `persistence_flow_test.dart` (12b) |
| Importante | Si la app se cerraba a mitad de una grabación, el archivo temporal podía quedarse en la caché | `sweepStaleClips` borra los `practica_*` antes de la siguiente grabación | `test/speech/voice_files_test.dart` |
| Importante | La ficha de Play estaba desactualizada (51 dibujos; no mencionaba «Aprendo a Hablar», «Quiero decir» ni el micrófono) | Textos nuevos | Recuento de caracteres en [PLAY_STORE_LISTING.md](PLAY_STORE_LISTING.md) |
| Crítico (web) | En la versión web la voz se perdía: al cortar una frase para decir otra («Escuchar», cambiar de pregunta), `flutter_tts` descartaba la nueva sin decirla; si la voz en línea fallaba, no se oía nada | Voz web propia (`lib/audio/web_speech.dart`): frase nueva cada vez, espera que siempre termina, otra voz en español si una falla y truco para frases largas en Chrome. En Android se sigue usando la voz del sistema | `test/web_speech_test.dart` y prueba en el navegador: 4 de 4 frases (antes 2 de 4) |
| Menor | La política, la auditoría y la revisión de Familias no mencionaban «Quiero decir», la versión web ni los SDK `record` y `path_provider` | Actualizadas | — |
