# Nueva pantalla de inicio

Rediseño de la pantalla de inicio a partir de la imagen de referencia: estilo infantil
pastel con relieve, cielo, nubes, arcoíris y flores; logo multicolor; un niño y una niña
con pinceles y su perrito; cuatro tarjetas grandes y una barra inferior. No se ha creado
una app nueva: todo usa las pantallas y servicios que ya existían.

## Qué hay en el inicio y adónde lleva

| Elemento | Dónde | Abre |
|---|---|---|
| Botón redondo azul (engranaje) | Arriba a la izquierda | «Sonido y música» (`/sonido`) |
| Candado (mantener pulsado) | Arriba | Pregunta para adultos → zona para adultos (como antes) |
| Botón redondo rosa (nota musical) | Arriba a la derecha | Enciende o apaga la música; si estaba todo silenciado, vuelve a activar el sonido |
| Logo «Pequeños Artistas» y subtítulo | Centro | — |
| Niño, niña y perrito | Centro | Al tocarlos saludan con voz (frases de bienvenida sin repetir) |
| **Colorear** (azul, paleta) | Tarjeta 1 | «Elige una categoría» (`/categorias`) |
| **Mini Juegos** (rosa, puzle) | Tarjeta 2 | Une las parejas, Rompecabezas y Laberintos (`/minijuegos`) |
| **Actividades** (menta, libro y bombilla) | Tarjeta 3 | Colores, Formas, Animales y Trazos (`/actividades`) |
| **Galería** (lila, cuadro) | Tarjeta 4 | «Mis dibujos» (`/mis-dibujos`) |
| **Perfil** | Barra inferior | Panel del niño «¡Hola, artista!» (`/perfil`) |
| **Logros** | Barra inferior | «Mis premios» (`/premios`) |
| **Configuración** | Barra inferior | «Sonido y música» (`/sonido`) |

Ningún botón está sin función. Todos suenan al tocarlos (si el sonido está activado),
se encogen un poco al pulsarlos, evitan abrir dos pantallas con un doble toque y tienen
etiqueta para el lector de pantalla.

### Cambios de sitio respecto al inicio anterior

- **«¡Vamos a pintar!»** (abre al momento el siguiente dibujo fácil) se ha movido al
  principio de «Colorear», encima de las categorías. Funciona igual que antes.
- **«Sonidos activados»** (silencio total) está ahora en «Configuración» como «Todo el
  sonido». En el inicio queda el botón de música, como en la referencia.
- «Aprender jugando» se divide en **Actividades** y **Mini Juegos**, con el mismo menú,
  los mismos niveles y los mismos ajustes de sonido y voz.
- La antigua «Galería» (las categorías) es ahora **Colorear**, y «Mis dibujos» se abre
  desde **Galería** («¡Tus obras de arte!»), como en la referencia.

## Panel del niño («Perfil»)

Corresponde al «Panel para niños» de la segunda imagen. Solo lee lo que la app ya guarda
en el dispositivo; no pide nombre ni foto ni ningún dato personal:

- Estrellas, pegatinas conseguidas y número de dibujos.
- «Tu progreso»: dibujos terminados (de 31), mini juegos probados (de 3) y actividades
  probadas (de 4).
- «Tus logros»: las pegatinas conseguidas, con «Ver todos».
- «Tus dibujos recientes»: miniaturas de los últimos dibujos; al tocar uno se sigue
  pintando. «Ver todos» abre «Mis dibujos».
- «¡Sigue jugando!»: la próxima pegatina y cómo conseguirla.

## Animaciones

- Entrada escalonada de las partes del inicio (barra, logo, personajes, tarjetas, barra
  inferior) y aparición con rebote de los personajes.
- Destellos y estrellas que flotan suavemente tres veces y se quedan quietos (no hay
  animaciones infinitas que gasten batería).
- Escala al pulsar, transiciones suaves entre pantallas y sonidos opcionales.
- Con «reducir movimiento» del sistema, todo aparece directamente, sin animar.

## Diseño adaptable

- Teléfono vertical: todo en una columna; si la pantalla es baja, el tablero de tarjetas
  se encoge antes que los personajes y, en último caso, la pantalla se desplaza.
- Teléfono horizontal y tableta (ancho ≥ 700): logo y personajes a la izquierda;
  tarjetas y barra inferior a la derecha.
- Los textos se reducen en vez de cortarse. En botones estrechos de la barra inferior el
  icono va encima del texto para que este se lea bien.
- Las pruebas comprueban que no hay desbordamientos en 320 × 568, 360 × 740, 740 × 360,
  800 × 1280 y 1280 × 800, con texto normal y con texto al 160 %.

## Recursos gráficos

### Usados

| Recurso | Origen | Licencia |
|---|---|---|
| Cielo, nubes, arcoíris, colinas, flores, manchas de pintura | Dibujados con código (`lib/screens/home/home_art.dart`) | Originales del proyecto |
| Niño, niña y perrito con pinceles | Dibujados con código (`CharactersPainter`) | Originales del proyecto |
| Iconos de las tarjetas (paleta, puzle, libro con bombilla, cuadro), estrella y engranaje | Dibujados con código (`HomeIconPainter`) | Originales del proyecto |
| Pincelín (botón «Perfil») | Mascota ya existente en la app | Original del proyecto |
| Tipografía **Fredoka** (`assets/fonts/Fredoka.ttf`) | [google/fonts](https://github.com/google/fonts/tree/main/ofl/fredoka) | SIL Open Font License 1.1 (`assets/fonts/Fredoka-OFL.txt`) |

No se usan emojis, imágenes de terceros ni paquetes nuevos.

### Que faltan (opcional)

La referencia muestra personajes con **ilustración 3D profesional**. Esos archivos no
existen en el repositorio y no se han inventado rutas. Los personajes actuales son
vectores originales que imitan ese estilo. Para cambiarlos por una ilustración
profesional (propia o con licencia compatible):

1. Guardar la imagen como `assets/images/home/personajes.png` (PNG con fondo
   transparente, proporción aproximada 360 × 230, por ejemplo 1440 × 920 px).
2. Añadir la carpeta en `pubspec.yaml`, dentro de `flutter: assets:`:
   `- assets/images/home/`
3. No hace falta tocar el código: el inicio comprueba si existe
   `HomeScreen.heroAsset` y, si está, la muestra en lugar de los vectores (con la
   misma animación, el mismo saludo al tocar y la misma etiqueta de accesibilidad).

## Archivos

Nuevos:

- `lib/screens/home/home_art.dart`: ilustraciones del inicio (escena, personajes, iconos).
- `lib/screens/home/home_widgets.dart`: logo, botones de esquina, tarjetas, botones de la
  barra inferior y destellos.
- `lib/screens/child_panel_screen.dart`: panel «Perfil».
- `lib/widgets/creation_thumbnail.dart`: miniatura de un dibujo guardado (compartida por
  «Mis dibujos» y el panel).
- `assets/fonts/Fredoka.ttf` y `assets/fonts/Fredoka-OFL.txt`.

Modificados:

- `lib/screens/home_screen.dart`: nueva pantalla de inicio.
- `lib/screens/categories_screen.dart`: botón «¡Vamos a pintar!».
- `lib/learning/screens/learning_hub_screen.dart`: grupos «Actividades» y «Mini juegos».
- `lib/learning/screens/rewards_screen.dart`: botón «Volver» genérico (se abre desde
  varios sitios).
- `lib/navigation/app_routes.dart`, `lib/navigation/app_router.dart`: rutas
  `/minijuegos` y `/perfil`.
- `lib/screens/saved_drawings_screen.dart`: usa la miniatura compartida.
- `pubspec.yaml`: tipografía Fredoka.
- Pruebas actualizadas a los nuevos recorridos y pruebas nuevas del inicio, el panel,
  los grupos de juegos y el botón de música.
- `store_assets/screenshots/phone/01_inicio.png` y `02_categorias.png`: capturas nuevas.
- `deploy/web/`: versión web recompilada.
