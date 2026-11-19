# «Aprendo a leer»: módulo de lectoescritura

Módulo nuevo para niños de 4 a 7 años, hecho por fases. Cada fase llega en su propia PR.

| Fase | Estado |
|---|---|
| A · Auditoría y arquitectura | Hecha (en el chat) |
| **B · Diseño visual y navegación** | **Hecha** (este documento) |
| **C · Motor de audio y sílabas** | **Hecha, con la voz del dispositivo; faltan grabaciones e imágenes** (ver abajo) |
| **D · Completa las palabras** | **Hecha**: 100 de 118 palabras jugables; 18 esperan su ilustración |
| **E · Lectura guiada de oraciones** | **Hecha**: 105 oraciones con voz del dispositivo y escenas provisionales; faltan ilustraciones 3D y grabaciones |
| **F · Dictados (Escucho y escribo)** | **Hecha**: 200 dictados con voz del dispositivo; faltan grabaciones |
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
| `/leer/oraciones` | C · Leo mis primeras oraciones: nivel, progreso y actividades (Fase E) |
| `/leer/oraciones/leer` | Lector: ilustración, oración con resaltado, Normal/Lento, Escuchar, Repetir, Escuchar palabra, Parar, Anterior/Siguiente |
| `/leer/oraciones/juego` | «¿Qué entendiste?», «Ordena la oración» y «Escucha y elige» |
| `/leer/dictado` | D · Escucho y escribo: nivel (sílabas, palabras, oraciones) y modo de respuesta (Fase F) |
| `/leer/dictado/juego` | Dictado: escuchar, lento, parar, tarjetas / teclado / ordenar, pistas y corrección |

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

## Fase E · Lectura guiada de oraciones

### Catálogo (`assets/reading/sentences.json`)

Lo genera y valida `python3 tools/reading/sentences.py`. Las pantallas solo leen datos.

- **105 oraciones**: 26 de nivel 1, 27 de nivel 2, 26 de nivel 3 y 26 de nivel 4.
- Cada una tiene:
  - id, texto, nivel y familias silábicas que usa;
  - palabras (y grabación de cada palabra, si existe);
  - escena provisional e ilustración 3D (pendiente);
  - audio (grabación y tiempos por palabra, si existen; si no, voz del dispositivo);
  - pregunta, 3 opciones con imagen, respuesta, palabra-pista y explicación sencilla;
  - si vale para «Ordena» y las dos escenas de «Escucha y elige».
- **El nivel lo calculan reglas fijas** (si no coincide con el bloque donde está escrita, el
  generador falla):
  - **Nivel 1**: todas las sílabas se pueden leer con lo enseñado en la Fase C (vocales, familias
    M P S L T N D F C·Q B e inversas el, es, un…). Sin r, g, j, v, z, ñ, ll, ch, h, diptongos ni
    sílabas trabadas.
  - **Nivel 4**: alguna palabra con grupo consonántico (bl, tr, pr, fl…).
  - **Nivel 3**: sin grupos y 6 palabras o más (descriptivas).
  - **Nivel 2**: el resto (cortas, de todos los días).
  - Por eso «El conejo blanco…», «La mariposa vuela sobre las flores» o «trompa» están en el nivel
    4, y no en los primeros: «blanco», «flores» y «trompa» tienen grupos consonánticos.
- Validaciones:
  - separación silábica (la misma que comprueba la app);
  - 3 opciones distintas con imagen; la respuesta está en la oración y las falsas no;
  - «Ordena»: 3 a 7 palabras, sin «y» y sin adjetivos que puedan ir delante del nombre; la
    mayúscula inicial y el punto final se mantienen como pistas, y se acepta cualquier orden que
    forme exactamente la oración;
  - «Escucha y elige»: las otras dos escenas no comparten fondo ni dibujos con la correcta.

### Audio y resaltado (`ReadingVoice.playSentence`)

Se usa el motor de las fases anteriores (no hay otro). Las palabras se resaltan así, por orden:

1. **Grabación con tiempos medidos** (`assets/audio/reading/oraciones/<id>.json`): se resalta según
   la posición real del audio.
2. **Lento**: palabra por palabra. Cada palabra se dice sola y se resalta mientras suena.
3. **Voz del dispositivo que avisa de cada palabra**: Android (`setProgressHandler`) y navegadores
   con voces que lanzan `onboundary`. Se resalta cuando la voz avisa.
4. **Si la voz no avisa**: se lee entera sin resaltar y la pantalla lo explica (con «Lento» sí se
   resalta). Nunca se simula con temporizadores.

Cada sonido nuevo corta el anterior. Tocar una palabra la dice sola. No se usa el micrófono.

### Actividades

- **Lector**: ilustración, oración grande, Normal/Lento, «Escuchar», «Repetir», «Escuchar
  palabra», «Parar», «Anterior», «Siguiente» y «Responder la pregunta».
- **¿Qué entendiste?**: la oración (sin la ilustración, que daría la respuesta), la pregunta y 3
  tarjetas con imagen. Al fallar: la tarjeta se atenúa con una cruz, «¡Casi!», «Escuchar» y
  «Pista» (resalta y dice la palabra que responde). Al acertar: marca verde con ✓, ilustración y
  explicación. Sin castigos.
- **Ordena la oración**: tocar o arrastrar las palabras; tocar una colocada la devuelve; «Pista»
  coloca la siguiente correcta; «Comprobar».
- **Escucha y elige**: suena la oración y se elige entre 3 escenas claramente distintas.
- 8 oraciones por partida, primero las que aún no se han hecho.
- **Niveles**: el 2, 3 y 4 se abren al acertar 8 preguntas del anterior.

### Progreso (`reading.v1.state`, compatible con lo guardado antes)

- oraciones escuchadas enteras;
- oraciones **leídas sin ayuda**: se acertó su pregunta sin haberla escuchado ni tocado sus
  palabras antes (escuchar no cuenta como leer);
- palabras tocadas;
- preguntas respondidas y acertadas;
- intentos;
- actividades hechas con pista y a la primera;
- nivel de oraciones alcanzado.

### Pendiente

- **105 ilustraciones 3D**: lista en `assets/images/aprendo_leer/oraciones/README.md`. Mientras
  tanto se ve una escena provisional con dibujos de la app, marcada «Ilustración provisional».
- **105 grabaciones** (y sus tiempos por palabra): lista en `assets/audio/reading/oraciones/README.md`.
- Probar en dispositivos reales qué voces avisan de las palabras (en Chrome, las voces «Google» en
  línea no suelen avisar; las del sistema sí).

## Fase F · Dictados («Escucho y escribo»)

### Catálogo (`assets/reading/dictations.json`)

Lo genera y valida `python3 tools/reading/dictations.py` **a partir del contenido de las fases
anteriores** (no hay datos nuevos que puedan contradecirlos):

| Nivel | Dictados | De dónde salen |
|---|---|---|
| 1 · Escucho sílabas | 50 | Las 10 familias de la Fase C (M, P, S, L, T primero; luego N, D, F, C·Q, B) |
| 2 · Escucho palabras | 100 | Las 100 palabras con imagen de la Fase D, de fáciles a difíciles |
| 3 · Escucho oraciones | 50 | Oraciones de la Fase E con un único orden posible (16 + 16 + 8 + 10 por nivel) |

Cada dictado tiene id, tipo, nivel, dificultad, texto correcto, audio, imagen, tarjetas, pistas,
reglas de validación y criterios de evaluación.

- **Solución única**: en las tarjetas nunca hay dos que suenen igual (seseo, b/v, c/k/qu).
- **Alternativas explícitas**: en una sílaba aislada, SA/ZA, SE/CE, SI/CI, BA/VA, CA/KA, QUE/KE…
  suenan exactamente igual, así que con el teclado se aceptan y se dice cuál se practica
  («ZA suena igual. Hoy practicamos SA»). En palabras y oraciones no hay alternativas: la imagen
  deja claro qué palabra es (VACA, no BACA).

### Modos de respuesta

- **Tocar tarjetas** (sílabas y palabras) y **Ordenar palabras** (oraciones): todo táctil; tocar
  una tarjeta colocada la quita. Recomendado si el niño aún no conoce bien las letras.
- **Escribir con teclado**: el teclado del dispositivo (sin autocorrección ni sugerencias) y
  teclas grandes para «á é í ó ú ñ». Nunca es obligatorio.

### Audio

El motor de siempre (`ReadingVoice`): grabación si existe; si no, la voz del dispositivo, y la
pantalla lo indica («Sin grabación: se oye con la voz del dispositivo»). Escuchar, lento, parar,
instrucción por voz al empezar, pistas habladas y «Escuchar la respuesta» al terminar. Nunca
suenan dos cosas a la vez. No se usa el micrófono.

### Corrección (`DictationChecker`)

- Se normalizan las mayúsculas y los espacios de los extremos o repetidos. Las tildes y las
  letras **sí** cuentan.
- Tipos de error que se distinguen y se explican: **tilde** (falta, sobra o va en otra letra),
  **letra** (falta, sobra o hay que cambiar una), **sílaba** (cuáles, o cuántas faltan),
  **espacios** (palabras juntas o separadas), **palabra** (en oraciones: cuáles, faltan o sobran)
  y **orden**.
- En oraciones, la mayúscula inicial y el punto final no cuentan como error pero se recuerdan.
- Acierto: «¡Excelente trabajo!», felicitación hablada, la respuesta resaltada con ✓ y confeti.
- Error: «Vamos a intentarlo otra vez», el motivo, las partes marcadas (borde, subrayado e icono,
  no solo color) y se puede escuchar otra vez, pedir pistas y corregir sin borrar lo escrito.

### Pistas progresivas

1. Repetir el audio despacio.
2. Cuántas sílabas (letras en una sílaba, palabras en una oración), con casillas.
3. La primera sílaba (letra, o palabra); en tarjetas se coloca la primera (salvo en sílabas, donde
   sería la respuesta entera).
4. Ayuda visual: modelo para copiar (y la palabra de ejemplo en las sílabas).

Un acierto con pistas se guarda como acierto **con ayuda**, no como acierto sin ayuda.

### Progreso (`reading.v1.state`, campo `dictations`)

Por dictado: tipo, nivel, último modo, intentos, si se acertó, si se acertó sin pistas, máximo de
pistas, fecha (AAAA-MM-DD) y errores por tipo. Los niveles 2 y 3 se abren al acertar 8 dictados
del anterior. No toca nada de otros módulos ni de las otras actividades.

### Pendiente

- Grabaciones: los dictados usan las de sílabas, palabras y oraciones de las fases anteriores (aún
  no hay ninguna). Hay que **comprobar en dispositivos reales** que la voz del sistema pronuncia
  bien las sílabas sueltas.
