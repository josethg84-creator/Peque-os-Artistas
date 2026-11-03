# Aprendo a Hablar — primera entrega

Módulo para niños desde los 4 años que enseña vocabulario y frases con voz en español,
dentro de la misma app y con su mismo estilo. Lo acompaña **Lolo**, un lorito original.

> Es un módulo educativo. **No evalúa el habla ni el lenguaje y no sustituye la valoración
> o la terapia de un profesional.**

## Qué incluye esta entrega

| Pedido para la 1.ª entrega | Estado |
|---|---|
| Menú «Aprendo a Hablar» con sus 8 actividades | ✅ Hecho. «Mis primeras palabras», «Aprendo frases» y «Mi progreso» funcionan; las otras 5 aparecen como **«Muy pronto»** (al tocarlas, Lolo explica que llegarán pronto: no son botones muertos) |
| Mascota visual | ✅ Lolo, dibujado con código en el mismo estilo 3D pastel; saluda con el ala y mueve el pico |
| Catálogo de 100 palabras | ✅ 10 grupos de 10: Familia, Animales, Alimentos, Juguetes, Partes del cuerpo, Colores, Objetos del hogar, Acciones, Emociones y Naturaleza |
| Audio en español | ✅ Con la voz de la app (velocidad normal y **despacio**, repetir, volumen de la voz en «Sonido y música») |
| Frases sencillas | ✅ 12 frases útiles (las 10 pedidas y «Hola, ¿cómo estás?» y «Buenas noches»), con escucha palabra a palabra y la actividad **«¡Ordénala tú!»** |
| Navegación funcional | ✅ Desde el inicio: Lolo junto al arcoíris («¡A hablar!») |
| Progreso local básico | ✅ Palabras y frases escuchadas, frases ordenadas y días de práctica de la semana |

### Cómo se usa

- **Inicio → Lolo («¡A hablar!»)**, en el cielo junto al arcoíris, abre el menú.
- **Mis primeras palabras → un grupo**: aparece la ilustración y la palabra en mayúsculas
  (PERRO), y Lolo la dice sola. Botones grandes: **Anterior**, **Escuchar**, **Despacio** y
  **Siguiente**; también se puede deslizar con el dedo o tocar el dibujo para oírla. Al final
  del grupo, Lolo felicita y ofrece «Otra vez» u «Otros grupos».
- **Aprendo frases**: la ilustración y la frase, con cada palabra como botón que se oye sola.
  **¡Ordénala tú!** desordena las palabras y el niño las toca en orden. Si se equivoca no hay
  castigo: suena «inténtalo otra vez», Lolo dice «¡Casi! ¿Cuál va ahora?» y, a la segunda, la
  palabra correcta brilla. Al terminar se oye la frase entera y «¡Muy bien!».
- **Mi progreso**: solo cuenta lo que se ha hecho de verdad en este dispositivo, con una nota
  para los adultos de que no es una evaluación.
- En estas actividades la música de fondo se calla para oír bien la voz.

### Lo que falta (entregas siguientes)

- **2.ª entrega:** construcción de oraciones, conjugación de verbos, actividades de
  comprensión y **grabación local opcional** (botón «Practicar»). No se ha añadido ningún
  permiso de micrófono todavía: se hará cuando se compruebe un paquete compatible con Android
  y web, con grabación solo local, sin subir nada y borrada por defecto.
- **3.ª entrega:** conversaciones guiadas con Lolo, cuentos narrados, panel de progreso
  ampliado (también en la zona de adultos), mejoras visuales y de accesibilidad.

## Voz

- Se reutiliza el sistema de voz de la app (texto a voz del dispositivo, en la web el del
  navegador), que ya elige la voz en español más natural disponible, **con prioridad para
  español de Perú y Latinoamérica**.
- **Despacio**: la misma voz al 62 % de su velocidad normal.
- Si el dispositivo no tiene una voz en español, «Sonido y música» lo explica y cómo
  instalarla; la palabra y la frase siguen escritas y todo se puede usar.
- **Sin conexión:** en Android depende de que la voz en español esté instalada en el
  dispositivo (lo indica «Sonido y música»). En la web, algunas voces del navegador (las de
  Google) necesitan conexión. **No se ha verificado en un dispositivo real** sin conexión en
  esta entrega.
- No hay audios grabados: solo la voz del sistema. Si más adelante se graban o generan audios
  con licencia que permita distribuirlos, se pueden añadir sin cambiar las pantallas.

## Privacidad

- No se usa el micrófono ni se graba nada en esta entrega.
- El progreso se guarda **solo en el dispositivo** (clave `speech.v1.state`, con suma de
  verificación y copia de seguridad). No hay cuentas, servidores, anuncios ni datos personales.

## Ilustraciones

| Tipo | Para | Origen |
|---|---|---|
| Dibujos de la app pintados | Animales, frutas, osito, coche, tren, avión y barco | Los dibujos del catálogo de colorear. Las frutas llevan sus colores reales (manzana roja, plátano amarillo…); los animales, colores alegres |
| Caritas | Emociones | Originales, dibujadas con código |
| Niño con la parte resaltada | Partes del cuerpo | Original, con código; un anillo rosa señala la parte |
| Mancha de pintura | Colores | Original, con código |
| Pictogramas en baldosas 3D | Familia, alimentos, juguetes, hogar, acciones, naturaleza y frases | Iconos de Material (incluidos en Flutter, licencia Apache 2.0) |
| Lolo | Mascota | Original, con código |

Todo es vectorial: se ve nítido a cualquier tamaño y funciona sin conexión.

**Para usar ilustraciones propias** (por ejemplo, unas 3D profesionales): guardar el PNG en
`assets/speech/img/` (y añadir esa carpeta en `pubspec.yaml`) y poner en la palabra
`"picture": {"image": "assets/speech/img/perro.png"}`.

## Ampliar el contenido sin tocar el código

`assets/speech/words.json` (palabras por grupos) y `assets/speech/phrases.json` (frases).
Cada palabra:

```json
{"id": "perro", "text": "perro", "article": "el", "picture": {"drawing": "animal_perro"}}
```

Tipos de `picture`:

- `{"drawing": "<id del catálogo>", "colors": {"zona": "#RRGGBB", "uva_*": "#RRGGBB"}}`
- `{"icon": "<nombre>", "color": "#RRGGBB"}` (nombres en `SpeechIcons`)
- `{"emotion": "feliz"}`
- `{"body": "ojos"}`
- `{"swatch": "#E53935"}`
- `{"image": "assets/..."}`

Lo que no se entienda (una ilustración desconocida, un id repetido, un grupo vacío) se
descarta sin romper la pantalla.

## Arquitectura

```
lib/speech/
  speech_content.dart      modelos (grupos, palabras, frases, ilustraciones) y lectura del JSON
  speech_progress.dart     progreso, almacenamiento local y SpeechController
  widgets/speech_art.dart  Lolo, caritas, cuerpo y manchas de color (dibujo vectorial)
  widgets/speech_widgets.dart  Lolo animado, bocadillo, ilustraciones y botones
  screens/speech_hub_screen.dart  menú, grupos de palabras y «Mi progreso»
  screens/words_screen.dart       palabras una a una
  screens/phrases_screen.dart     frases y «¡Ordénala tú!»
assets/speech/words.json, phrases.json
```

- Contenido, lógica, almacenamiento y pantallas están separados.
- `SpeechController` está en `AppServices`, como el resto de servicios.
- La voz «despacio» se añadió al sistema de audio común (`Narrator.speak(slow:)`).
- Rutas: `/hablar`, `/hablar/palabras`, `/hablar/palabras/grupo`, `/hablar/frases`,
  `/hablar/progreso`.

## Pruebas

- `test/speech/speech_content_test.dart`: 100 palabras en 10 grupos, ilustraciones válidas,
  dibujos existentes, colores reales de las frutas, 12 frases y lectura tolerante del JSON.
- `test/speech/speech_progress_test.dart`: guardar y recuperar, días de práctica, copia de
  seguridad ante datos dañados y uso sin almacenamiento.
- `test/speech/speech_flow_test.dart`: inicio → menú (8 actividades y «Muy pronto»), palabras
  (escuchar, despacio, siguiente, deslizar, terminar el grupo, música callada), frases
  (palabra a palabra, ordenar con errores sin castigo y con ayuda) y «Mi progreso».
- `test/responsive_test.dart`: las 6 pantallas nuevas sin desbordamientos en 5 tamaños, con
  texto normal y al 160 %.
