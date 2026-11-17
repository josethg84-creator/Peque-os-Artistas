# «Aprendo a leer»: módulo de lectoescritura

Módulo nuevo para niños de 4 a 7 años, hecho por fases. Cada fase llega en su propia PR.

| Fase | Estado |
|---|---|
| A · Auditoría y arquitectura | Hecha (en el chat) |
| **B · Diseño visual y navegación** | **Hecha** (este documento) |
| C · Motor de audio y sílabas | Pendiente |
| D · Completar palabras | Pendiente |
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
