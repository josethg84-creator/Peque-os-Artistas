# Fase 6 — Integración, optimización, accesibilidad y pruebas

Revisión técnica y funcional de toda la app **Pequeños Artistas**, hecha sobre el código real
(rama `fase-6/integracion`, a partir de `55b9b15`). No se ha creado una app nueva ni se ha
quitado ninguna función.

> Pequeños Artistas es una app educativa y de juego. **No es una herramienta de diagnóstico ni
> de tratamiento clínico.** «Quiero decir» es un apoyo a la comunicación.

## 1. Inventario y matriz de integración

Estados: ✅ funciona y tiene pruebas · ⚠️ funciona, con limitación conocida · ⏳ pendiente
fuera de este entorno.

| Funcionalidad | Implementación encontrada | Estado | Dependencias | Problemas detectados | Acción |
|---|---|---|---|---|---|
| Pantalla principal | `screens/home_screen.dart`, `screens/home/illustrated_home_cover.dart` (tu ilustración con zonas táctiles) | ✅ | `assets/ui/…webp` | «Aprendo a Hablar» solo era una insignia pequeña; no había acceso directo al tablero de comunicación | Accesos grandes en el espacio libre (fase 6) |
| Catálogo de dibujos | `services/catalog_service.dart`, `assets/catalog/catalog.json` (59) | ✅ | SVG, miniaturas | — | — |
| Motor de coloreado | `coloring/` (análisis SVG, relleno por zonas, zoom) | ✅ | — | — | — |
| Guardado y galería | `persistence/creation_store.dart`, `screens/saved_drawings_screen.dart` | ✅ | shared_preferences | — | — |
| Mini juegos | `learning/games/`, `learning/screens/` (7 juegos) | ✅ | audio | — | — |
| Actividades educativas | `learning/screens/learning_hub_screen.dart` | ✅ | — | — | — |
| Aprendo a Hablar | `speech/` | ✅ | `assets/speech/` | Menú de 14 tarjetas sin agrupar | Áreas con título (fase 6) |
| Vocabulario y frases | `speech/screens/words_screen.dart`, `phrases_screen.dart` (313 palabras) | ✅ | — | — | — |
| Constructor de oraciones | `speech/screens/sentences_screens.dart` | ✅ | — | — | — |
| Verbos | `speech/screens/verbs_screens.dart` (15 verbos) | ✅ | — | — | — |
| Comprensión oral | `speech/screens/listening_screens.dart` (56 ejercicios) | ✅ | — | — | — |
| Conversaciones con Lolo | `speech/dialogue.dart`, `conversation_screens.dart` (40) | ✅ | — | — | — |
| Cuentos interactivos | `speech/stories.dart`, `story_screens.dart` (20) | ⚠️ | voz | La lectura seguía al volver atrás | La voz se calla al cerrar la pantalla (fase 6) |
| Historias personalizadas | `speech/my_story.dart`, `my_story_screen.dart` | ✅ | — | — | — |
| Aprendizaje adaptativo | `speech/recommendations.dart`, `mission.dart` | ✅ | progreso local | — | — |
| Juegos de sílabas | `speech/word_games.dart`, `word_game_screens.dart` | ✅ | — | — | — |
| Pictogramas | `aac/` (203 pictogramas) | ✅ | `assets/aac/` | Contaba el uso también de necesidades, salud y emociones | Ya no lo cuenta (fase 6) |
| Tablero rápido | `aac/screens/aac_screens.dart` (`AacQuickScreen`) | ✅ | — | Desde el inicio hacían falta 2 toques | A un toque desde el inicio (fase 6) |
| Configuración | `screens/sound_settings_screen.dart`, zona de adultos | ✅ | — | Faltaba reducir animaciones | Añadido (fase 6) |
| Audio | `audio/app_audio.dart` (`LearningAudio`: voz, efectos y música), `music_zone.dart` | ✅ | flutter_tts, audioplayers | Ver la auditoría de audio | — |
| Progreso | `LearningProgress`, `SpeechProgress`, `AacPreferences`, creaciones | ✅ | — | No había una vista conjunta | `services/progress_overview.dart` (fase 6) |
| Recompensas | `learning/rewards.dart`, estrellas y medallas de habla | ✅ | — | — | Separadas de la comunicación |
| Zona para adultos | `screens/adult_zone_screen.dart` + `widgets/adult_gate.dart` | ✅ | — | El resumen tapaba el aviso de datos dañados | Reordenado (fase 6) |

**Arquitectura actual:** las pantallas leen los servicios de `AppServices`. Son
`CatalogService`, `DrawingLoader`, `CreationStore`, `LearningController`, `LearningAudio`,
`SpeechController` y `AacController`, cada uno con su propio almacén local y clave propia.
Contenido, lógica y pantallas están separados (JSON en `assets/`, funciones puras y widgets).
Las rutas están en `navigation/app_routes.dart` (57) y en `app_router.dart`, que muestra una
pantalla amable para cualquier ruta desconocida o sin datos.

## 2. Navegación

- **Inicio** (tu ilustración, sin redibujarla): Colorear, Mini Juegos, Actividades, Galería
  (Mis Dibujos), Perfil, Logros (Mis Logros) y Configuración vienen de la imagen. «Aprendo a
  Hablar» y **«Necesito decir algo»** van ahora en botones grandes en el espacio libre: debajo de
  la ilustración en teléfonos y al lado en tabletas horizontales. Si no sobra espacio, queda la
  insignia de Lolo.
  - Las palabras «Actividades» y «Galería» están dibujadas en la imagen: para cambiarlas haría
    falta otra versión de la ilustración.
- **Aprendo a Hablar**, en áreas con título dentro de la misma pantalla, sin menús nuevos:
  - Aprendo palabras.
  - Formo oraciones.
  - Practico verbos.
  - Converso con Lolo.
  - Escucho cuentos.
  - Juegos de lenguaje.
  - Quiero decir.
  - Mis aventuras.
  - Arriba siguen «Necesito decir algo», «Mi aventura de hoy» y las sugerencias de Lolo.

## 3. Auditoría de audio

| Requisito | Resultado |
|---|---|
| Un coordinador de audio | ✅ Voz, efectos y música pasan por `LearningAudio` (las pantallas no crean reproductores propios). La grabación usa `VoiceRecorder` solo dentro de «Practicar». |
| Dos voces a la vez | ✅ Cada frase nueva interrumpe la anterior; la cola solo guarda la última. |
| Música durante la voz | ✅ Baja al 30 % mientras habla y se calla en las pantallas de lenguaje y comunicación. |
| Silencio | ✅ Volumen general a 0 = nada suena; «Quiero decir» lo avisa y muestra la frase. |
| Velocidad de voz | ✅ Botón «Despacio» en todo el módulo, voz lenta en los ajustes de «Aprendo a Hablar» y de «Quiero decir». |
| Errores del TTS | ✅ Se capturan; si no hay voz en español, la app lo explica y sigue funcionando con texto. |
| Voces en español | ✅ Elige es-PE, es-419, es-US, es-MX… y descarta voces que necesitan red (`network_required`). |
| Micrófono | ✅ Solo en «Practicar»: el permiso se pide al pulsar «Grabar», sin permiso se explica, y un adulto puede ocultarlo. |
| Cancelar al salir | ✅ Corregido: al cerrar una pantalla se calla su voz (los juegos ya lo hacían). |
| Ciclo de vida | ✅ En segundo plano se pausa la música y se calla la voz; se recupera al volver. |
| Liberar recursos | ✅ Reproductores y grabadoras se liberan; las grabaciones se borran al cerrar. |
| Sin conexión | ⚠️ En Android, con voz en español **instalada**, según lo que informa el sistema. En web, algunas voces del navegador necesitan red: la app lo dice. **No se ha verificado en un dispositivo real.** |

## 4. Auditoría de accesibilidad

- ✅ Botones grandes. Las pruebas usan las guías de Flutter (48 × 48 y etiquetas) en las
  pantallas de las fases 4 y 5.
- ✅ Etiquetas semánticas en tarjetas, botones y mensajes. Corregido: las tarjetas que estaban
  apareciendo con animación quedaban ocultas al lector de pantalla.
- ✅ Texto ampliado hasta el 160 %. La prueba de tamaños recorre 5 pantallas × 2 tamaños de letra.
- ✅ Alto contraste, tamaño de pictogramas y de texto, y evitar toques sin querer en «Quiero
  decir».
- ✅ **Reducir animaciones** (nuevo), además del ajuste «Quitar animaciones» del sistema.
- ✅ Sin actividades cronometradas obligatorias. La grabación de «Practicar» dura 6 s como
  máximo y se puede parar antes.
- ✅ Repetir instrucciones en todas las actividades. Hay alternativas sin micrófono y sin
  conexión.
- ✅ Un mismo concepto tiene el mismo dibujo en todas las pantallas. El tablero nunca exige
  un nivel ni estrellas.
- ⏳ Falta probarlo con TalkBack en un teléfono real.

## 5. Auditoría de seguridad y privacidad

- **Permisos del APK** (comprobado en el manifiesto final): solo `RECORD_AUDIO`, más uno
  interno de AndroidX. **No pide INTERNET.**
- **Dependencias:**
  - `audioplayers`: efectos y música locales.
  - `flutter_tts`: voz del dispositivo.
  - `record` y `path_provider`: grabación temporal.
  - `shared_preferences`: almacenamiento local.
  - `web`: grabación en el navegador.
  - Ninguna es de analítica, publicidad ni red.
- **Enlaces externos y servicios analíticos:** no hay. **Perfiles y chat:** tampoco.
- **Grabaciones:** solo en memoria o en un archivo temporal, se borran al cerrar y no se
  envían. Ningún servicio externo las recibe.
- **Recomendaciones:** solo usan datos educativos guardados en el dispositivo, con reglas fijas,
  sin IA ni red.
- **Comunicación:** no guarda datos médicos. Desde esta fase no cuenta el uso de necesidades,
  salud ni emociones. Se borra con «Borrar personalización».
- **Distribución infantil (Google Play, Familias):**
  - la declaración del micrófono y de «Seguridad de los datos» se prepara en
    `store_assets/store_listing/DECLARACIONES_PLAY_CONSOLE.md`;
  - la política de privacidad la debe publicar el responsable de la app;
  - no se ha publicado nada, no se han creado claves de firma y la compilación de prueba está
    firmada con la clave de depuración.

## 6. Pruebas automatizadas

`flutter test`: **507 pruebas, todas pasan**. Cubren, entre otros:

| Pedido | Dónde |
|---|---|
| 1 · Navegación entre módulos | `phase6_integration_test.dart`, `navigation_test.dart`, `responsive_test.dart` |
| 2 · Carga de catálogos | `catalog_*`, `speech/*_test`, `aac/aac_catalog_test.dart` |
| 3 · Gramática de oraciones | `aac/aac_catalog_test.dart` (constructor), `speech/my_story_test.dart` |
| 4 · Conjugaciones | `speech/speech_activities_test.dart` |
| 5 · Conversaciones | `speech/dialogue_test.dart` |
| 6 · Cuentos | `speech/stories_test.dart`, `phase3_flow_test.dart` |
| 7–8 · Guardado y recuperación | `persistence/*`, `speech/speech_progress_test.dart`, `aac/aac_controller_test.dart` |
| 9–10 · Tableros y frases | `aac/aac_flow_test.dart` (los 203 pictogramas dicen lo que muestran) |
| 11–12 · Permisos y sin micrófono | `speech/speech_flow2_test.dart` (sin permiso), `aac/aac_flow_test.dart` |
| 13 · Rutas y archivos inexistentes | `phase6_integration_test.dart`, `catalog_*` |
| 14 · Preferencias antiguas | `phase6_integration_test.dart` (progreso de la 1.ª entrega, ajustes sin campos nuevos) |
| 15 · Datos dañados | `phase6_integration_test.dart`, `persistence/*`, `aac/aac_controller_test.dart` |

## 7. Compilaciones (ejecutadas en este entorno)

| Orden | Resultado |
|---|---|
| `flutter pub get` | ✅ |
| `flutter analyze` | ✅ sin incidencias |
| `flutter test` | ✅ 507 pruebas |
| `flutter build web --release` | ✅ (`deploy/web`) |
| `flutter build apk --release` | ✅ `app-release.apk`, **62,6 MB** universal (3 arquitecturas; por dispositivo unos 19–20 MB). Firmado con la clave de **depuración** (no hay `key.properties`): **solo para pruebas internas**. |
| `flutter build appbundle --release` | ✅ `app-release.aab`, **60,5 MB** (Google Play entrega a cada teléfono solo su arquitectura). Firmado con la clave de **depuración**: no sirve para publicar sin la clave de subida del responsable. |

Aviso del compilador: `flutter_tts` usa el plugin de Kotlin antiguo. Funciona hoy, pero una
versión futura de Flutter lo rechazará; habrá que actualizar el plugin cuando publique una
versión compatible.

## 8. Rendimiento (medido)

- **Dentro del APK**, por arquitectura:
  - motor de Flutter: 11,8 MB (arm64);
  - código de la app: 7,3 MB;
  - recursos: 7,7 MB.
- **Fuera del APK:**
  - las vistas previas de 1024 px (5,7 MB) no se incluyen;
  - `Catalogo Imagenes/` (73 MB) solo está en el repositorio.
- **Decodificación de imágenes:**
  - las miniaturas se decodifican al tamaño de la tarjeta (`cacheWidth`);
  - los dibujos se analizan una vez y se guardan en una caché de 6;
  - los catálogos JSON se cargan una sola vez y bajo demanda.
- **Listas largas:** todas se construyen al desplazarse (`builder` y slivers).
- **Animaciones:** solo las primeras 12 tarjetas entran animadas. Todas se pueden desactivar.
- **Memoria y fluidez:** no se han podido medir en un teléfono de gama básica. ⏳

## 9. Pruebas en dispositivos

**Ninguna se ha hecho todavía**: este entorno no tiene teléfonos ni tabletas físicas. Solo se ha
probado con pruebas automáticas y con un navegador automatizado.

| Comprobar | Android pequeño (≈ 5") | Android grande (≈ 6,7") | Tableta Android | Navegador móvil | Navegador escritorio |
|---|---|---|---|---|---|
| Portada e imágenes | ⏳ | ⏳ | ⏳ | ⏳ (automático: ✅) | ⏳ (automático: ✅) |
| Controles táctiles | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Sonido y voz | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Micrófono | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Rendimiento | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Navegación | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Pictogramas | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Guardar progreso | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Cerrar y reabrir | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

## 10. Recorridos principales (experiencia de usuario)

| Recorrido | Cómo se comprueba | Estado |
|---|---|---|
| A · Colorear y guardar | `persistence/persistence_flow_test.dart`, `coloring/*` | ✅ |
| B · Escuchar una palabra y construir una oración | `speech/speech_flow_test.dart`, `speech_flow2_test.dart` | ✅ |
| C · Conversar con Lolo | `speech/phase3_flow_test.dart`, `phase4_flow_test.dart` | ✅ |
| D · Escuchar un cuento | `speech/phase3_flow_test.dart` | ✅ |
| E · Decir «Necesito ayuda» | `phase6_integration_test.dart` (desde el inicio y desde el tablero) | ✅ |
| F · Un adulto revisa el progreso | `phase6_integration_test.dart` | ✅ |

Todas las pantallas tienen botón para volver y estados de carga, vacío y error, que revisan
`empty_states_test.dart` y las pruebas de cada módulo.

## 11. Problemas detectados y soluciones aplicadas

1. La voz de un cuento o de una actividad seguía sonando al volver atrás. **Solución:** un
   observador de navegación calla la voz al cerrar cualquier pantalla (no al cerrar diálogos).
2. Las tarjetas que estaban apareciendo con animación quedaban ocultas al lector de pantalla.
   **Solución:** `alwaysIncludeSemantics`.
3. Al pasar a secciones, las animaciones de entrada se reiniciaban en cada sección.
   **Solución:** el orden ahora es continuo en toda la pantalla.
4. No había acceso directo al tablero desde el inicio. **Solución:** «Necesito decir algo» a un
   toque.
5. «Quiero decir» contaba el uso de pictogramas sensibles. **Solución:** ya no se cuenta.
6. Los textos sobre voz sin conexión eran demasiado rotundos. **Solución:** ahora se matizan.
7. No había forma de reducir las animaciones desde la app. **Solución:** nuevo ajuste.
8. No había una vista conjunta del progreso. **Solución:** «Resumen de todo lo hecho», sin
   migrar datos.

## 12. Riesgos restantes

- **Sin pruebas en dispositivos reales:**
  - voz sin conexión;
  - micrófono;
  - TalkBack;
  - rendimiento en gama básica;
  - cierre y reapertura reales.
- **Firma:** el APK está firmado con la clave de depuración. Para publicar hace falta la clave
  de subida del responsable, que no se crea aquí.
- **`flutter_tts`:** el aviso del plugin de Kotlin puede romper la compilación con una versión
  futura de Flutter.
- **Textos de la portada:** «Actividades» y «Galería» están dibujados en la imagen.
- **Pictogramas genéricos:** algunos son iconos genéricos (p. ej., personas). Conviene validar su
  claridad con familias y, si hace falta, dibujarlos.
- **Web:**
  - la voz depende del navegador;
  - algunas voces necesitan conexión;
  - grabar requiere permiso del navegador.
- **Política de privacidad y publicación:** son tareas del responsable (ver `store_assets/`).

## 13. Pruebas con familias

Ver [GUIA_PRUEBAS_FAMILIAS.md](GUIA_PRUEBAS_FAMILIAS.md). **No se ha hecho ninguna prueba con
familias.**
