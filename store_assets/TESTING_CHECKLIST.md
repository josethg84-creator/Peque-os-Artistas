# Lista de pruebas de la versión candidata 1.0.0 (Fase 7)

Hay tres niveles:

1. **Pruebas automáticas.** Se ejecutan en cada cambio y son las únicas que se han hecho de verdad.
2. **Pruebas manuales en un dispositivo real.** **Ninguna está hecha todavía**, porque este entorno
   no tiene teléfono ni tableta.
3. **Prueba cerrada de Google Play** (12 testers durante 14 días). **No se ha hecho.**

## 1. Resultados automáticos (04/11/2026, rama `release/fase-7`)

| Orden | Resultado |
|---|---|
| `flutter clean` | Correcto |
| `flutter pub get` | Correcto (9 paquetes tienen versiones nuevas incompatibles con las restricciones; no se han actualizado) |
| `dart format --set-exit-if-changed lib test` | Sin cambios |
| `flutter analyze` | **No issues found!** |
| `flutter test` | **511 pruebas superadas**, 0 fallos |
| `flutter build apk --release` | Correcto. Ver [ANDROID_BUILD.md](ANDROID_BUILD.md) |
| `flutter build appbundle --release` | Correcto. Ver [ANDROID_BUILD.md](ANDROID_BUILD.md) |

## 2. Recorridos principales A–L

«Auto» indica qué prueba automática lo recorre de principio a fin, en la app montada con sus
pantallas reales y con audio y micrófono simulados. Ninguna prueba automática sustituye a probar
la voz, el sonido y el tacto en un dispositivo.

| | Recorrido | Auto | Prueba automática | En dispositivo |
|---|---|---|---|---|
| A | Colorear un dibujo | ✅ | `persistence/persistence_flow_test.dart` (1-3, 6); `coloring/` | ⬜ |
| B | Guardar y recuperar un dibujo | ✅ | `persistence_flow_test.dart` (1-3, 6, 11); `release_journeys_test.dart` (L) | ⬜ |
| C | Terminar un minijuego | ✅ | `learning/learning_games_flow_test.dart` («de principio a fin»); `speech/speech_flow2_test.dart` («fin de la actividad») | ⬜ |
| D | Escuchar una palabra | ✅ | `speech/speech_flow_test.dart` (palabras); `release_journeys_test.dart` | ⬜ voz real |
| E | Construir una oración | ✅ | `speech_flow2_test.dart` («constructor») | ⬜ voz real |
| F | Escuchar un cuento y responder | ✅ | `speech/phase3_flow_test.dart` («el cuento se lee solo…», «preguntas del cuento…») | ⬜ voz real |
| G | Conversar con Lolo | ✅ | `phase3_flow_test.dart` («una charla completa con estrella», «una rama…») | ⬜ |
| H | Frase con pictogramas | ✅ | `aac/aac_flow_test.dart` («constructor: [YO]+[QUIERO]+[AGUA]…») | ⬜ |
| I | «Necesito ayuda» en el tablero rápido | ✅ | `phase6_integration_test.dart` (E y «a un toque desde el inicio»); `aac_flow_test.dart` («tablero rápido») | ⬜ tiempo real hasta decirlo |
| J | Revisar el progreso | ✅ | `phase6_integration_test.dart` (F, vista integrada); `phase4_flow_test.dart` («resumen sin etiquetas diagnósticas») | ⬜ |
| K | Cambiar ajustes de audio | ✅ | `learning_games_flow_test.dart` («la voz se puede desactivar»); `audio_system_test.dart`; `aac_flow_test.dart` («sin voz o con el sonido apagado») | ⬜ volumen real |
| L | Cerrar y volver a abrir sin perder datos | ✅ | **Nuevo:** `release_journeys_test.dart` (dibujo, palabra, favorita y ajuste a la vez); `learning_games_flow_test.dart` («se conservan al cerrar») | ⬜ cierre real desde el sistema |

## 3. Pruebas manuales en un dispositivo real (pendientes)

Hazlas con el APK o con la versión de prueba interna. Marca cada casilla y anota el modelo.

### Bloqueantes antes de producción

- [ ] **Miniaturas de la galería y de «Mis dibujos» se ven** (en el emulador fallaron con
  «Could not decompress image»; ver [KNOWN_ISSUES.md](KNOWN_ISSUES.md), C2).
- [ ] La app se instala desde Play (prueba interna) firmada con la clave de subida.
- [ ] Icono en el lanzador (adaptativo, sin recortes) y pantalla de carga.
- [ ] **Micrófono:**
  - [ ] el permiso se pide solo al pulsar «Grabar»;
  - [ ] negar el permiso muestra el aviso amable;
  - [ ] la grabación suena;
  - [ ] tras cerrar la ventana, no queda ningún `practica_*` en la caché (Ajustes → Almacenamiento
    de la app: la caché no crece).
- [ ] **Voz:** con la voz en español instalada, se oyen palabras, cuentos y pictogramas; sin
  ella, se ve el aviso y la app no se bloquea.
- [ ] Modo avión: todo funciona.

### Recorridos A–L a mano

- [ ] A–L de la tabla anterior, en un teléfono y en una tableta.
- [ ] L: cerrar la app desde «Recientes» (no solo volver atrás) y reabrirla.
- [ ] I: medir cuánto se tarda desde el icono hasta oír «Ayuda».

### Matriz mínima de dispositivos

| Dispositivo | Android | Hecho | Notas |
|---|---|---|---|
| Teléfono de gama baja (2-3 GB de RAM) | 8–10 | ⬜ | Memoria, arranque y fluidez al colorear |
| Teléfono de gama media | 13–14 | ⬜ | |
| Teléfono reciente | 15–16 | ⬜ | API 36, permisos |
| Tableta de 8–10" | 12+ | ⬜ | Horizontal y vertical |
| Texto grande (Ajustes → tamaño de fuente máximo) | cualquiera | ⬜ | |
| TalkBack activado | cualquiera | ⬜ | Botones con nombre |

## 4. Pruebas con familias

Supervisadas, voluntarias y sin datos de los niños: ver
[`docs/GUIA_PRUEBAS_FAMILIAS.md`](../docs/GUIA_PRUEBAS_FAMILIAS.md) y la guía para adultos
[`docs/GUIA_ADULTOS.md`](../docs/GUIA_ADULTOS.md). **No se ha hecho ninguna sesión.**

## 5. Prueba cerrada de Google Play

Según la ayuda de Google (consultada con búsqueda web; `support.google.com` no se puede abrir
desde este entorno), las **cuentas personales** de desarrollador creadas después del 13/11/2023
deben hacer una prueba cerrada con **al menos 12 testers** que se hayan unido y sigan dentro
**durante 14 días seguidos** antes de poder pedir acceso a producción. Las cuentas de
organización no tienen este requisito. **Confírmalo en Play Console:** las cifras pueden cambiar.

Pasos (los hace el propietario; **no se ha hecho ninguno**):

1. Play Console → Probar y publicar → Pruebas → **Prueba interna**: subir el AAB firmado con la
   clave de subida y probarlo en tus dispositivos.
2. **Prueba cerrada:**
   - crear una pista y una lista de testers (correos de cuentas de Google de **adultos**);
   - compartir el enlace de participación.

   Los testers son los adultos, no los niños.
3. Pedir a cada tester:
   - que acepte la invitación e instale la app;
   - que la use de vez en cuando durante los 14 días, con esta lista y la guía para adultos;
   - que envíe sus comentarios **sin datos de los niños**.
4. Llevar un registro (sin datos personales):

   | Tester (código) | Fecha de alta | Dispositivo | Sigue a los 14 días | Problemas |
   |---|---|---|---|---|
   | — | — | — | — | **Pendiente: aún no hay testers** |

5. Al terminar, pedir acceso a producción en Play Console y responder a sus preguntas sobre la
   prueba.

> No se ha publicado nada ni se ha creado ninguna pista. Este documento no afirma que la prueba
> cerrada se haya hecho.
