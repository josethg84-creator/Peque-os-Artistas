# Quiero decir — comunicación aumentativa con pictogramas (fase 5 de «Aprendo a Hablar»)

«Quiero decir» es un tablero de comunicación con pictogramas y voz en español, dentro de
Pequeños Artistas. Sirve para que un niño desde los 4 años pueda decir lo que necesita, lo que
siente y lo que quiere tocando dibujos.

> Es un **apoyo a la comunicación**. No es un tratamiento médico, no evalúa al niño y no
> sustituye la valoración de un profesional.

## Cómo se llega

- Desde «Aprendo a Hablar», arriba del todo: **«Necesito decir algo»** (tablero rápido, a un
  toque) y **«Quiero decir»** (el tablero completo).
- No pide estrellas, actividades terminadas, cuentas, conexión ni micrófono. El tablero del niño
  nunca pide la verificación de adultos; solo los ajustes están en la zona de adultos.

## Qué incluye

| Pedido | Estado |
|---|---|
| 1 · «Quiero decir»: tablero con 10 categorías, tarjetas grandes, frase e ilustración, voz al tocar | Hecho |
| 2 · Pictogramas con id, categoría, texto, ilustración, texto para voz, color, orden, activo y relacionados; 150 o más | Hecho: **203 pictogramas** (`assets/aac/pictograms.json`) |
| 3 · «Construyo lo que quiero decir»: barra, Escuchar frase, Borrar última, Limpiar, Volver a comenzar, Guardar favorita, sugerencias | Hecho |
| 4 · «Necesito decir algo»: Sí, No, Ayuda, Agua, Baño, Comer, Dolor, Más, Terminé, Para, Quiero, No quiero | Hecho; un adulto puede añadir palabras, las esenciales no se pueden quitar |
| 5 · Personalización | Hecho (ver «Ajustes») |
| 6 · Voz | Se reutiliza el sistema de voz de la app (ver «Voz») |
| 7 · Emociones y necesidades | Hecho: «Cómo me siento», sin respuestas buenas ni malas |
| 8 · «Aprendo a comunicarme con Lolo» | Hecho, separado del tablero |
| 13 · Pruebas | Ver abajo. **Falta probar en un teléfono Android real.** |

### Pictogramas

Cada pictograma del JSON tiene: `id`, `category`, `text` (lo que se ve), `speech` (lo que se
dice: siempre el mismo texto), `picture` (la ilustración), `color` (el de su categoría),
`order`, `active`, `related` (sugerencias del constructor), `kind` (tipo gramatical) y, si es un
sustantivo, `article`.

Las ilustraciones son dibujos propios (caritas de emociones, partes del cuerpo, niños), dibujos
del catálogo de colorear o pictogramas de Material (licencia Apache 2.0). No hay emojis ni
archivos de audio inventados. Como la app es vectorial, `picture` no es una ruta de imagen: es
la referencia al dibujo (`{"drawing": "animal_perro"}`, `{"icon": "water_drop"}`,
`{"emotion": "triste"}`, `{"body": "cabeza"}`…). También acepta una imagen propia con
`{"image": "assets/…png"}`. El generador `tools/aac/pictograms.py` comprueba cada referencia y
la prueba `test/aac/aac_catalog_test.dart` lo vuelve a comprobar.

Un mismo concepto tiene el mismo dibujo en todas las pantallas (tablero, constructor, tablero
rápido, emociones y juego).

`{o|a}` marca las palabras que cambian con el género: con el ajuste «Frases en femenino»,
«Estoy cansad{o|a}.» se ve y se dice «Estoy cansada.».

### El constructor

Une las piezas en buen español sin corregir al niño: cualquier combinación vale y se dice tal
cual. Solo pone los artículos y las contracciones que hacen falta.

- [YO] + [QUIERO] + [AGUA] → «Yo quiero agua.»
- [QUIERO] + [JUGAR] + [CON] + [MI] + [PERRO] → «Quiero jugar con mi perro.»
- [QUIERO] + [IR] + [PARQUE] → «Quiero ir al parque.»
- [ME DUELE] + [CABEZA] → «Me duele la cabeza.»
- [NO QUIERO] + [COMER] → «No quiero comer.»

Las sugerencias son los pictogramas relacionados con la última pieza. Siempre se puede abrir
cualquier categoría.

### Ajustes (zona de adultos)

Tamaño de los pictogramas, columnas, orden (catálogo, alfabético o los más usados), tamaño del
texto, alto contraste, decir al tocar, confirmar antes de hablar («Decirlo»), voz más lenta,
volumen de la voz, frases en femenino, evitar toques sin querer (ignora un segundo toque
demasiado rápido), categorías frecuentes, palabras del tablero rápido y **«Borrar
personalización»**.

### Voz

- Se usa la voz del dispositivo, la misma que el resto de la app. Habla una sola frase a la
  vez: una nueva interrumpe la anterior.
- Hay botones para repetir al momento, decirlo despacio y mostrar la frase a pantalla completa.
- Si el sonido está apagado o el dispositivo no tiene voz en español, la frase se sigue viendo
  en grande y un aviso lo explica.
- Sin conexión, en Android funciona si la voz en español está instalada en el dispositivo.

## Privacidad

- Todo se guarda **solo en el dispositivo**, en la clave `aac.v1.state`: ajustes, frases
  favoritas, palabras añadidas al tablero rápido y cuántas veces se usa cada tarjeta. Este
  último dato solo sirve para ordenarlas y **no se cuenta** en las categorías sensibles:
  necesidades, salud y emociones (fase 6).
- No se guarda información médica ni diagnóstica. No hay publicidad, chat, perfiles, envío de
  datos ni micrófono.
- Un adulto puede borrarlo todo con «Borrar personalización».
- La comunicación no da estrellas ni depende de ellas: «Quiero decir» va aparte del progreso.

## Arquitectura

```
lib/aac/
  aac_catalog.dart        pictogramas, categorías, tableros y juego (lectura tolerante del JSON)
  phrase_composer.dart    constructor de frases y sugerencias (funciones puras)
  aac_controller.dart     ajustes, favoritas, uso, mensaje en pantalla y almacenamiento local
  aac_icons.dart          iconos de Material del catálogo (generado)
  widgets/aac_widgets.dart       tarjeta, rejilla, barra de mensaje, voz, accesos
  widgets/aac_settings_panel.dart  ajustes en la zona de adultos
  screens/aac_screens.dart       Quiero decir, categorías, tablero rápido, emociones, favoritas, juego
  screens/aac_builder_screen.dart  Construyo lo que quiero decir
assets/aac/pictograms.json  (tools/aac/pictograms.py)
```

`AacController` está en `AppServices`, aparte de `SpeechController` (progreso y estrellas).

## Pruebas

- `test/aac/aac_catalog_test.dart`:
  - catálogo: 203 pictogramas sin descartes, 10 categorías, campos completos, «lo que se ve es
    lo que se dice», relacionados y dibujos válidos, tablero rápido y datos dañados;
  - constructor: los ejemplos, artículos, género, preguntas y combinaciones al azar.
- `test/aac/aac_controller_test.dart`: guardar y recuperar, favoritas, borrar la
  personalización, datos dañados y toques involuntarios.
- `test/aac/aac_flow_test.dart`:
  - tablero rápido desde «Aprendo a Hablar», sin micrófono;
  - **cada uno de los 203 pictogramas dice exactamente lo que muestra**;
  - constructor completo y favoritas;
  - emociones, confirmar antes de hablar, femenino, voz lenta y toques dobles;
  - sin voz;
  - juego con Lolo;
  - zona de adultos;
  - guías de accesibilidad de Flutter (tamaño táctil y etiquetas).
- `test/responsive_test.dart`: las 8 pantallas nuevas sin desbordamientos en 5 tamaños, con texto
  normal y al 160 %.

## Pendiente

- Probar en un teléfono Android real (voz instalada, sin conexión, lector de pantalla TalkBack).
- Pictogramas dibujados a mano para los conceptos que hoy usan un icono genérico.
