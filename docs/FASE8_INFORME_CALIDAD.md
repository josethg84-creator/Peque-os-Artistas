# Fase 8 · Informe de calidad, optimización y preparación para producción

Rama: `fase-8-calidad` · Vista previa de Vercel: despliegue `dpl_GaU3qoKf7XfXxgjM4YidnkeDxpeu` (READY, privada).
**No se ha fusionado ni desplegado en producción.** Fecha: 2026-11-19.

## A. Resumen ejecutivo

- Se auditaron el código, los recursos, el audio, el contenido pedagógico, la accesibilidad, el diseño
  adaptable, la seguridad, el rendimiento y Vercel.
- **No se encontraron errores críticos.** Se corrigieron 9 problemas:
  - de accesibilidad: el contraste de los botones grandes en toda la app y las áreas táctiles de la portada;
  - de seguridad: los encabezados HTTP;
  - de limpieza: código sin usar, datos duplicados y una pregunta poco natural.
- **Pruebas:** `flutter analyze` sin avisos y **824 pruebas automatizadas aprobadas** (72 más que antes de esta fase).
- **Queda sin verificar algo esencial para una app de lectura:** la pronunciación real de la voz del
  dispositivo y el funcionamiento en móviles reales. Por eso la recomendación es **APTO CON OBSERVACIONES**,
  no «APTO».

## B. Problemas detectados y corregidos

| # | Nivel | Problema (evidencia) | Corrección |
|---|---|---|---|
| 1 | Alto | Texto blanco sobre botones grandes de colores claros. Contraste medido de 1,54:1 a 2,57:1 con la pauta automática de Flutter; WCAG pide 3:1 para texto grande. Afectaba a toda la app. | `BigActionButton` usa texto oscuro cuando el blanco no llega a 3:1 (`AppColors.onColor`). Resultado: 4,57:1 a 7,64:1. |
| 2 | Medio | Portada: botón «Configuración» de 38 × 38 px (mínimo 48 × 48) y una zona táctil sin etiqueta para el lector de pantalla. | Zona táctil mínima de 48 × 48 sin mover el dibujo; el gesto ya no crea un nodo duplicado sin etiqueta. |
| 3 | Medio | Tarjetas de «Quiero decir»: contraste de 2,85:1. «Probar la voz»: 2,57:1. | El fondo se oscurece lo justo para el texto blanco; «Probar la voz» usa la tinta oscura. |
| 4 | Medio | Sin encabezados de seguridad HTTP. | `vercel.json`: `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy`. Verificados en la vista previa. |
| 5 | Bajo | «?» de «Une sílaba y palabra» con contraste de 2,90:1. | Color de tinta (> 7:1). |
| 6 | Bajo | Código sin usar en «Aprendo a leer»: datos de demostración, `DemoBadge`, `ReadingAudioButtons`. | Eliminado, junto con sus pruebas. |
| 7 | Bajo | `dictations.json` repetía los mismos criterios 200 veces. | Criterios una sola vez: de 220 KB a 148 KB (−33 %). |
| 8 | Bajo | Pregunta poco natural: «Hoy hace sol» → «¿Qué hace hoy?». | «¿Qué tiempo hace hoy?». |
| 9 | Bajo | Faltaban pruebas de accesibilidad, de tamaños extremos, de audio al salir de una pantalla, de recursos ilegibles y de rutas sin datos. | 72 pruebas nuevas (ver D). |

## C. Problemas pendientes y nivel de riesgo

| Nivel | Problema | Por qué sigue pendiente | Qué hace falta |
|---|---|---|---|
| **Alto** | La pronunciación de la voz sintética no está verificada. No hay ninguna grabación. | Hay que oírla en dispositivos reales. Que la síntesis funcione no demuestra que pronuncie bien. | Revisión humana con `docs/AUDIO_REVISION_HUMANA.md`. Mejor aún: grabar las 120 + 105 frases pedidas. |
| **Alto** | No se ha probado en móviles ni tabletas reales (Android, iPhone, Safari). | No hay dispositivos en este entorno. El navegador de pruebas tampoco puede abrir `vercel.app` (bloqueado por la política de red). | Prueba manual en al menos un Android de gama media y un iPhone. |
| Medio | «Completo palabras», nivel 1: **17 de 33** palabras usan letras aún no enseñadas (gato, vaca, loro, perro, gallo, hada, piña, silla, taza, vaso, llave, ducha, carro, rojo, rosa, niño, niña). | Es una decisión pedagógica: cambiar los niveles alteraría el progreso guardado. | Decidir si se reordenan o se marcan como «palabras de vista». |
| Medio | Ilustraciones 3D pendientes: 105 de oraciones, 31 de palabras, 12 de medallas y las del módulo. Ahora se usan dibujos e iconos de la app, marcados como «provisional». | No se inventan imágenes. | Encargar las ilustraciones según las listas `README.md` de cada carpeta. |
| Medio | Algunos iconos provisionales pueden ser ambiguos: «sueño» (luna con estrellas), «hambre» (cubiertos), «foco» (lámpara) y los personajes de las escenas. | Lo tiene que juzgar una persona. | Revisarlos con un adulto o docente. |
| Medio | Vulnerabilidades de las dependencias: no comprobadas. | `api.osv.dev` está bloqueado por la política de red del entorno. | Permitir ese dominio o ejecutar `osv-scanner` en otro equipo. |
| Bajo | Sin política CSP. | Flutter web necesita `wasm-unsafe-eval` y otros ajustes; añadirla sin probarla en el navegador puede romper la carga. | Probarla en la vista previa desde un equipo con acceso. |
| Bajo | Navegación con teclado físico y lectores de pantalla reales (TalkBack, VoiceOver) no probados. | Las pruebas automáticas cubren etiquetas, áreas táctiles y contraste, pero no el uso real. | Prueba manual. |
| Bajo | El plugin web de `flutter_tts` no es compatible con compilar a WebAssembly (avisos de la compilación). | No afecta: la app compila a JavaScript y en la web usa su propia voz (`WebSpeechNarrator`). | Ninguna por ahora. |
| Bajo | Código sin usar en los módulos originales (`SilentMusic`, `showAacBigMessage`, `AppLogo`). | No se tocaron módulos originales sin necesidad. | Limpieza opcional. |
| Bajo | `assets/images/home/personajes.png` está referenciada pero no existe. | Es opcional: ya existe la portada vectorial de reserva. | Ninguna. |

## D. Resultados de pruebas por módulo (matriz de calidad)

Estados: **APROBADO** · **FALLIDO** · **BLOQUEADO** · **NO PROBADO**.

Salvo que se diga otra cosa:
- «Prueba automatizada» = `flutter test`, con voz y audio simulados que registran lo que se dice.
- «Chromium» = la web compilada, abierta en Chromium con `speechSynthesis` simulado.

### Aprendo las sílabas

| Funcionalidad | Prueba | Resultado | Evidencia | Error | Corrección | Estado |
|---|---|---|---|---|---|---|
| Letras y sílabas suenan, en minúsculas | Automatizada y Chromium | Se dice «ma» y «eme» | `syllables_phase3_test.dart` | — | — | APROBADO |
| Pronunciación correcta | — | — | Requiere oído humano | — | — | **NO PROBADO** |
| Lento y normal | Automatizada | Lento a 0,62× (voz) y 0,7× (grabación) | `syllables_phase3_test.dart` | — | — | APROBADO |
| Selección de respuestas | Automatizada | Error amable y acierto | «Escucha y encuentra» | — | — | APROBADO |
| Asociación con imágenes | Automatizada | Todas las imágenes existen | `syllables_phase3_test.dart` | — | — | APROBADO |
| Registro de progreso | Automatizada | 2 intentos, 1 acierto | `achievements_phase7_test.dart` | — | — | APROBADO |
| Accesibilidad (3 pautas) | Automatizada | Pasan | `accessibility_phase8_test.dart` | Contraste del «?» | Color de tinta | APROBADO |

### Completo palabras

| Funcionalidad | Prueba | Resultado | Evidencia | Error | Corrección | Estado |
|---|---|---|---|---|---|---|
| División silábica | Automatizada (67 casos) y generador Python | Coinciden | `syllabifier_test.dart` | — | — | APROBADO |
| Seleccionar sílabas | Automatizada | Acierto y error | `complete_words_test.dart` | — | — | APROBADO |
| Arrastrar y soltar | Automatizada, con gesto real | Se coloca | `complete_words_test.dart` | — | — | APROBADO |
| Alternativa por toque | Automatizada | Funciona | `complete_words_test.dart` | — | — | APROBADO |
| Corrección y pistas | Automatizada | Primera letra, revelar, quitar opción | `complete_words_test.dart` | — | — | APROBADO |
| Reproducción de palabras | Automatizada | Funciona | `complete_words_test.dart` | — | — | APROBADO |
| Dificultad progresiva | Revisión con script | 17 de 33 palabras del nivel 1 con letras no enseñadas | Script de la Fase 8 | Pedagógico | Pendiente (C) | **FALLIDO** (pedagógico) |

### Leo oraciones

| Funcionalidad | Prueba | Resultado | Evidencia | Error | Corrección | Estado |
|---|---|---|---|---|---|---|
| Reproducción de oraciones y de palabras | Automatizada y Chromium | Funciona | `sentences_phase5_test.dart` | — | — | APROBADO |
| Resaltado sincronizado | Automatizada y Chromium con eventos `onboundary` simulados | Resalta «mamá» mientras suena | Capturas de la Fase 5 | — | — | APROBADO (simulado) |
| Resaltado con voces reales | — | — | Sin dispositivo | — | — | **NO PROBADO** |
| Modo sin sincronización | Automatizada y Chromium | Aviso, sin temporizadores | `sentences_phase5_test.dart` | — | — | APROBADO |
| Comprensión, ordenar, escuchar y elegir | Automatizada | Funcionan | `sentences_phase5_test.dart` | — | — | APROBADO |
| Ortografía y tildes de las 105 oraciones | Revisión manual completa | Sin faltas | Este informe | Una pregunta poco natural | Corregida | APROBADO |

### Escucho y escribo

| Funcionalidad | Prueba | Resultado | Evidencia | Error | Corrección | Estado |
|---|---|---|---|---|---|---|
| Dictado de sílabas, palabras y oraciones | Automatizada | Funciona | `dictation_phase6_test.dart` | — | — | APROBADO |
| Teclado (incluidas á é í ó ú ñ) | Automatizada y Chromium, escribiendo de verdad | Funciona | Capturas de la Fase 6 | — | — | APROBADO |
| Tarjetas y ordenar | Automatizada | Funciona | `dictation_phase6_test.dart` | — | — | APROBADO |
| Validación ortográfica | Automatizada | Distingue tilde, letra, sílaba, espacios, palabra y orden | `dictation_phase6_test.dart` | — | — | APROBADO |
| Pistas y repetición del audio | Automatizada | Funciona | `dictation_phase6_test.dart` | — | — | APROBADO |

### Mis logros y progreso

| Funcionalidad | Prueba | Resultado | Evidencia | Error | Corrección | Estado |
|---|---|---|---|---|---|---|
| Registro y estadísticas | Automatizada | Funciona | `achievements_phase7_test.dart` | — | — | APROBADO |
| Estrellas, medallas, sin duplicados | Automatizada | Funciona | `achievements_phase7_test.dart` | — | — | APROBADO |
| Persistencia entre sesiones | Automatizada y Chromium (recarga) | 4 estrellas y 1 medalla siguen | Capturas de la Fase 7 | — | — | APROBADO |
| Migración de datos y copia | Automatizada | Funciona | `achievements_phase7_test.dart` | — | — | APROBADO |
| Datos dañados → copia de seguridad | Automatizada | Funciona | `achievements_phase7_test.dart` | — | — | APROBADO |
| Separación de perfiles | — | La app no tiene perfiles múltiples ni cuentas | Auditoría de la Fase 7 | — | — | **NO PROBADO** (no existe la función) |
| Separación de datos entre módulos | Automatizada | Borrar lectura no toca lo demás | `achievements_phase7_test.dart` | — | — | APROBADO |
| Recomendaciones | Automatizada | Basadas en reglas y con evidencia | `achievements_phase7_test.dart` | — | — | APROBADO |

### Panel para adultos

| Funcionalidad | Prueba | Resultado | Evidencia | Error | Corrección | Estado |
|---|---|---|---|---|---|---|
| Acceso solo verificado | Automatizada | Sin verificar → «No encontrado» | `achievements_phase7_test.dart` y `robustness_phase8_test.dart` | — | — | APROBADO |
| Datos reales, perfil y borrar | Automatizada | Funciona | `achievements_phase7_test.dart` | — | — | APROBADO |

### Transversal

| Funcionalidad | Prueba | Resultado | Evidencia | Error | Corrección | Estado |
|---|---|---|---|---|---|---|
| Sin regresiones en los módulos originales | Batería completa | 824 / 824 | `flutter test` | — | — | APROBADO |
| Accesibilidad, 20 pantallas de lectura | Pautas de Flutter: áreas táctiles, etiquetas y contraste | Pasan tras corregir | `accessibility_phase8_test.dart` | Contraste | B1 y B5 | APROBADO |
| Accesibilidad, 13 pantallas originales | Mismas pautas | Pasan tras corregir | `accessibility_main_screens_test.dart` | Áreas táctiles, etiqueta, contraste | B1, B2 y B3 | APROBADO |
| Lectores de pantalla y teclado físico | — | — | Sin dispositivo | — | — | **NO PROBADO** |
| Diseño adaptable | Automatizada: 320 × 568 (×1,3), 360 × 720 (×1 y ×1,3), 412 × 915, 740 × 360 horizontal, 800 × 1280, 1280 × 800 (×1,6) y 1366 × 768 | Sin desbordamientos | Pruebas de las Fases 5–8 | — | — | APROBADO |
| Movimiento reducido | Automatizada | Celebración sin animación | `achievements_phase7_test.dart` | — | — | APROBADO |
| Audio: sin superposiciones | Automatizada | Un sonido corta al anterior | `syllables_phase3_test.dart` | — | — | APROBADO |
| Audio al cambiar de pantalla | Automatizada | La voz se calla y nada falla después | `robustness_phase8_test.dart` | — | — | APROBADO |
| Audio no disponible o silenciado | Automatizada | Aviso; la actividad sigue | Fases 3 y 5 | — | — | APROBADO |
| Audio en navegadores móviles | — | — | Sin dispositivo | — | — | **NO PROBADO** |
| Recursos referenciados | Script sobre todos los JSON y el código | Todos existen, salvo una imagen opcional con reserva | Script de la Fase 8 | — | — | APROBADO |
| Recursos que no se pueden leer | Automatizada | Mensaje claro, sin bloqueo | `robustness_phase8_test.dart` | — | — | APROBADO |
| Rutas sin datos o inexistentes | Automatizada | «No encontrado» con salida | `robustness_phase8_test.dart` | — | — | APROBADO |

## E. Rendimiento (medido, no estimado)

**Cómo se midió:** compilación de producción servida en local, **sin compresión**, en Chromium headless, con viewport de 412 × 915.
«Primer fotograma» = desde la navegación hasta que Flutter crea su capa accesible.

| Ruta | CPU | Primer fotograma | Transferido | Memoria JS |
|---|---|---|---|---|
| `/` | normal | 1606 ms | 9770 KB | 21 MB |
| `/` | 4× más lenta (simula gama media) | 3894 ms | 9770 KB | 21 MB |
| `/leer` | normal | 2053 ms | 9849 KB | 23 MB |
| `/leer` | 4× más lenta | 4953 ms | 9849 KB | 26 MB |

**Tamaños (compilación de producción):**

| Archivo | Tamaño | Comprimido con gzip (medido) |
|---|---|---|
| `main.dart.js` | 3699 KB | 1102 KB |
| `canvaskit/chromium/canvaskit.wasm` | 5302 KB | 2069 KB |

Vercel sirve con compresión Brotli: `content-encoding: br`, comprobado en la vista previa.
Iconos: se recortan automáticamente (de 1645 KB a 72 KB).

**No medido:**
- la carga a través de Internet desde Vercel: el navegador de este entorno no puede abrir `vercel.app`;
- un dispositivo real de gama media.

**Optimizaciones aplicadas:**
- `dictations.json`: −33 %.
- Se mantiene:
  - `--no-web-resources-cdn` (el motor se sirve desde el propio dominio);
  - la caché de un día para el motor gráfico;
  - `no-cache` para los archivos de arranque.

**No aplicadas, y por qué:**
- La carga diferida de módulos obligaría a cambiar el enrutado. El código de «Aprendo a leer» es una parte pequeña de `main.dart.js`; lo que más pesa es el motor de Flutter, que no se puede diferir.
- No hay imágenes pesadas: la mayor es la portada, en WebP, de 185 KB.

## F. Recursos gráficos y de audio

| Recurso | Estado |
|---|---|
| Grabaciones | **0**: 120 de sílabas, letras y palabras, y 105 de oraciones, pendientes. Todo suena con la voz del dispositivo, y la app lo indica cuando no hay grabación. |
| Pronunciación | Sin verificar: lista para revisión humana en `docs/AUDIO_REVISION_HUMANA.md` (55 sílabas, 10 nombres de letra, 24 palabras con diptongos o tildes, 11 nombres propios, entonación de preguntas). |
| Ilustraciones 3D | 0 de las nuevas (oraciones, palabras pendientes, medallas y módulo). Se usan dibujos e iconos de la app, marcados como provisionales. Listas en los `README.md` de cada carpeta. |
| Referencias rotas | 0, salvo una imagen opcional que ya tiene reserva. |

## G. Seguridad y privacidad

| Comprobación | Resultado | Estado |
|---|---|---|
| Secretos en el código o en archivos del repositorio (claves, almacenes de firma, `.env`) | Ninguno | APROBADO |
| Llamadas de red, analítica, publicidad o terceros | Ninguna en `lib/`; todo es local | APROBADO |
| Registros (`print`, `debugPrint`) con datos del niño | Ninguno | APROBADO |
| Datos personales | Solo un apodo opcional, limitado a letras y 16 caracteres; sin fotos ni nombre completo | APROBADO |
| Panel adulto | Verificación previa; la ruta sin verificar lleva a «No encontrado» | APROBADO |
| Permisos de Android | Solo `RECORD_AUDIO`, para la práctica de voz de «Aprendo a Hablar», que ya existía | APROBADO |
| Encabezados HTTP | Añadidos y verificados en la vista previa | APROBADO |
| Vulnerabilidades de dependencias | `api.osv.dev` bloqueado en este entorno | **BLOQUEADO** |
| CSP | No configurada | Pendiente (Bajo) |

## H. Compilación

- `flutter analyze`: **No issues found!**
- `flutter test`: **824 pruebas aprobadas, 0 fallidas.**
- `flutter build web --release --no-web-resources-cdn`: **correcta**, con avisos solo del plugin `flutter_tts` sobre WebAssembly, que no afectan (ver C).

## I. Vercel

| Comprobación | Resultado | Estado |
|---|---|---|
| Despliegue de vista previa de esta rama | READY | APROBADO |
| `index.html` y `flutter_bootstrap.js` | 200, Brotli, `no-cache`, motor local | APROBADO |
| Catálogo `dictations.json` | 200, `application/json` | APROBADO |
| Encabezados de seguridad | Presentes | APROBADO |
| Variables de entorno | No se necesita ninguna; sitio estático | APROBADO |
| Producción actual (Fase G) | READY; no se ha tocado | — |
| Carga completa en un navegador desde la vista previa | El navegador del entorno no puede abrir `vercel.app` | **BLOQUEADO** |

## J. Recomendación final: **APTO CON OBSERVACIONES**

**A favor** (con evidencia):
- no hay errores críticos conocidos;
- 824 pruebas automatizadas aprobadas y el análisis está limpio;
- la compilación es correcta y la vista previa de Vercel está en READY con los encabezados verificados;
- las actividades validan las respuestas;
- el progreso persiste y las recompensas no se duplican;
- la accesibilidad automática pasa en 33 pantallas;
- no se envían datos a terceros.

**Por qué no es «APTO»:** faltan dos verificaciones críticas para una app que enseña a leer.
1. Nadie ha escuchado todavía la pronunciación de la voz del dispositivo. No hay grabaciones.
2. No se ha probado en móviles reales.

Hasta hacer esas dos comprobaciones (C, riesgo Alto), no se debe presentar el módulo como terminado
para familias. La decisión pedagógica sobre el nivel 1 de «Completo palabras» también conviene tomarla antes.
