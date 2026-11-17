# «Aprendo a leer»: módulo de lectoescritura

Módulo nuevo para niños de 4 a 7 años, hecho por fases. Cada fase llega en su propia PR.

| Fase | Estado |
|---|---|
| A · Auditoría y arquitectura | Hecha (en el chat) |
| **B · Diseño visual y navegación** | **Hecha** (este documento) |
| **C · Motor de audio y sílabas** | **Hecha, con la voz del dispositivo; faltan grabaciones e imágenes** (ver abajo) |
| **D · Completa las palabras** | **Hecha**: 100 de 118 palabras jugables; 18 esperan su ilustración |
| E · Lectura guiada | Pendiente |
| F · Dictados | Pendiente |
| G · Progreso y recompensas | Pendiente |
| H · Pruebas, optimización y despliegue | Pendiente |

## Navegación

Menú principal → «Aprendo a Hablar» → sección **«Aprendo a leer»** → actividad. Se vuelve con
«Volver» o con «Ir al inicio». El inicio no se ha tocado.

| Ruta | Pantalla |
|---|---|
| `/leer` | Principal: Lolo, «¡Vamos a aprender juntos!», progreso y las 4 tarjetas |
| `/leer/silabas` | A · Aprendo las sílabas: familia, sílabas, palabra de ejemplo, audio y navegación |
| `/leer/completa` | B · Completo palabras: imagen, palabra con hueco, opciones, «Comprobar» y «Continuar» |
| `/leer/oraciones` | C · Leo oraciones: ilustración, oración grande, «Leer», «Despacio», tocar palabras y «Siguiente oración» |
| `/leer/dictado` | D · Escucho y escribo: nivel, «Escuchar», formar con tarjetas, borrar y «Comprobar» |

## Código

- `lib/reading/reading_activities.dart`: las 4 actividades (título, color, ruta, imagen).
- `lib/reading/reading_demo.dart`: **datos de demostración**. Las pantallas lo indican con el
  distintivo «Demostración». El contenido real irá en `assets/reading/*.json` (Fase C y siguientes).
- `lib/reading/widgets/reading_widgets.dart`, componentes:
  - tarjeta de actividad e ilustración;
  - barra de progreso;
  - tarjeta de sílaba y palabra por sílabas con hueco;
  - botones de audio;
  - anterior/siguiente;
  - felicitación y «Casi»;
  - distintivo de demostración, botón «Inicio» y Lolo.
- `lib/reading/screens/`: las 5 pantallas.
- Se reutilizan componentes que ya existían:
  - `KidScaffold`, `HomeMenuCard`, `AdaptiveSliverGrid`;
  - `SpeechActionButton`, `BigActionButton`, `KidIconButton`;
  - `LoloBubble`, `SpeechPictureView`, `ConfettiBurst`;
  - la voz de `LearningAudio`.

## Límites de esta fase

- El audio usa la voz de la app (síntesis). Las grabaciones de sílabas y el motor de lectura
  llegan en la Fase C.
- «Comprobar» compara con la respuesta de la demostración. La evaluación definitiva (con
  ortografía y tildes) llega en las Fases D y F.
- El progreso que se ve es de la sesión y no se guarda. Llega en la Fase G.

## Recursos pendientes

- Ilustraciones 3D del módulo: ver `assets/images/aprendo_leer/README.md`.
- Imágenes 3D para las palabras y oraciones: con el contenido de las Fases C y D.
- Grabaciones de sílabas y sonidos: decisión D2 de la auditoría.

## Fase C · Motor de audio y sílabas

### Contenido (`assets/reading/syllables.json`)

- Lo genera `tools/reading/syllables.py`.
- **Vocales y 10 familias:** M, P, S, L, T, N, D, F, C·Q (CA CO CU QUE QUI) y B. Son 55 sílabas, cada
  una con:
  - id, texto y familia;
  - audio (grabación o voz) y velocidades normal y lenta;
  - palabra de ejemplo, imagen y nivel.
- **Separación silábica validada dos veces**, por dos silabeadores independientes:
  `tools/reading/syllabify.py` y `lib/reading/syllabifier.dart`. Este último tiene 67 casos de
  prueba (diptongos, hiatos, ch, ll, rr, qu, gu, güe y grupos pl, br…).
- Cada palabra de ejemplo empieza por su sílaba. La excepción anotada es FU → «fue-go» (diptongo).
- **Niveles:**
  1. Inicial: vocales y sílabas directas («Escucha y encuentra»).
  2. Intermedio: sílaba, imagen y palabra («Une sílaba y palabra»).
  3. Avanzado: inversas y trabadas. Está **bloqueado** hasta que llegue su contenido.

### Motor de audio (`lib/reading/audio/reading_voice.dart`)

1. **Grabación validada**, si existe `assets/audio/reading/<silabas|palabras|letras>/<id>.mp3`. En
   modo lento suena al 70 %, sin cambiar el tono.
2. Si no hay grabación o falla, **voz del dispositivo**:
   - con el texto en minúsculas («ma», nunca «MA», para que no lo deletree);
   - en la web, con la voz propia del navegador de la versión anterior;
   - prefiere voces de Latinoamérica.
3. Si tampoco hay voz o el sonido está apagado, un **aviso visible**. La actividad sigue
   funcionando con la vista.

Además:

- Un sonido nuevo corta el anterior, sea grabación o voz.
- Al salir de la pantalla se libera el reproductor.
- No pide micrófono.
- Las actividades de «Aprendo a leer» van **sin música de fondo**.

### Juegos (`lib/reading/syllable_games.dart`)

- **Escucha y encuentra:**
  - 8 preguntas por partida, sin repetir la misma sílaba seguida;
  - la respuesta cambia de sitio;
  - las otras opciones acaban en la misma vocal (MA / PA / SA).
  - Al fallar se oye «Vamos a intentarlo otra vez», se puede volver a escuchar y se sigue.
  - Al acertar se oye «¡Muy bien!».
- **Une sílaba y palabra:**
  - solo palabras con imagen;
  - las otras opciones no están en la palabra.
  - Al acertar se oye «pe. pelota» y «¡Muy bien!».
- Las dos pantallas muestran un resumen final con las estrellas acertadas a la primera. El progreso
  se guarda en la Fase G.

### Pendiente

- **Grabaciones:** 0 de 120 (10 letras, 55 sílabas y 55 palabras). La lista y las instrucciones
  están en `assets/audio/reading/README.md`. Hasta entonces, todo suena con la voz del dispositivo,
  que **hay que escuchar en dispositivos reales**: en este entorno no se puede oír.
- **Ilustraciones de palabras:** faltan 19. La lista está en
  `assets/images/aprendo_leer/palabras/README.md`.

## Fase D · Completa las palabras

### Catálogo (`assets/reading/complete_words.json`)

- Lo genera `tools/reading/words.py`.
- **118 palabras** en 9 categorías, repartidas por nivel:
  - nivel 1 (dos sílabas directas): 42;
  - nivel 2 (tres o más sílabas): 38;
  - nivel 3 (trabadas, diptongos o una sílaba): 38.
- El nivel lo calculan reglas fijas, no se pone a mano.
- La separación la validan los dos silabeadores (Python y Dart).
- **Un ejercicio por palabra**, con id, palabra, sílabas, sílaba que falta, posición, opciones,
  respuesta, imagen, audio, nivel y categoría.
- Las opciones falsas cumplen estas reglas:
  - tienen la **misma forma** que la respuesta: directa con directa, trabada con trabada, vocal
    con vocal;
  - **no suenan igual** que la respuesta en español latinoamericano (SA/ZA, BA/VA, LLA/YA);
  - **no forman otra palabra conocida** (PA-TO / GA-TO);
  - no están ya en la palabra.
- Todo esto se comprueba al generar el catálogo y otra vez en las pruebas.
- **100 palabras tienen imagen** y se juegan. 18 esperan su ilustración y no entran en los juegos.
  La lista está en `assets/images/aprendo_leer/palabras/README.md`.

### Juego (`/leer/completa` y `/leer/completa/juego`)

- **Tres modos:**
  - **Elige la sílaba**;
  - **Arrastra la sílaba**: se arrastra al hueco, o se toca;
  - **Ordena la palabra**: se tocan las tarjetas en orden y se puede quitar la última.
- Hay 8 palabras por partida; primero las que aún no se han hecho.
- **Pistas:**
  - escuchar la palabra despacio;
  - escuchar la sílaba que falta (o la primera);
  - la primera letra en el hueco y, si se vuelve a pedir, se resalta la respuesta.
  - Tras dos intentos fallidos se quita una opción.
- Al fallar no hay castigo: «¡Casi! Escucha otra vez y prueba de nuevo». No se avanza sin acertar.
- Al acertar se oye la palabra completa y «¡Muy bien!».
- **Niveles:** el 2 y el 3 se abren al completar 8 palabras del anterior.

### Progreso (`reading.v1.state`)

- Es una clave propia, con checksum y copia de seguridad, el mismo método que el resto de la app.
  No toca el progreso de otros módulos.
- Guarda:
  - las palabras completadas en cada modo;
  - las acertadas a la primera y las hechas con pista;
  - las respuestas correctas y los intentos.
- El nivel alcanzado y los ejercicios pendientes se calculan a partir de esos datos.
