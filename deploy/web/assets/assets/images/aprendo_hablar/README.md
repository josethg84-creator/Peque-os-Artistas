# Imágenes — Aprendo a Hablar

Ilustraciones 3D de las tarjetas del menú «Aprendo a Hablar». Deben ser **WebP** con estos nombres exactos:

| Tarjeta | Archivo |
|---|---|
| Mis primeras palabras | `mis_primeras_palabras.webp` |
| Aprendo frases | `aprendo_frases.webp` |
| Juegos de palabras | `juegos_de_palabras.webp` |
| Construyo oraciones | `construyo_oraciones.webp` |
| Mi historia | `mi_historia.webp` |
| Yo puedo expresarme | `yo_puedo_expresarme.webp` |
| Aprendo los verbos | `aprendo_los_verbos.webp` |

## Ya está conectado

- La carpeta está registrada en `pubspec.yaml` (`flutter.assets`).
- Cada tarjeta (`SpeechActivity.image` en `lib/speech/screens/speech_hub_screen.dart`) muestra
  su imagen con `Image.asset` y `BoxFit.contain`, a la escala de la tarjeta en teléfonos y tabletas.
- **Mientras falte un archivo, esa tarjeta sigue mostrando su icono actual.** En cuanto se sube
  el WebP con el nombre correcto, aparece la ilustración: no hay que tocar el código.

## Recomendaciones

- Fondo transparente y la figura centrada, con algo de margen.
- Formato cuadrado, de 512 × 512 px (sobra para tabletas) y, a ser posible, de menos de 100 KB
  cada una.
- La prueba `test/speech/speech_card_images_test.dart` comprueba que los archivos subidos son
  WebP válidos.

## Ilustraciones 3D adicionales pendientes de cargar

**Ya están cargadas (05/11/2026).** Se recibieron como tarjetas completas, con marco, título y
subtítulo dibujados. Para no repetir el título (que sigue siendo un widget de Flutter), se recortó
solo la ilustración y se completó hasta 512 × 512 con su propio fondo desenfocado.

- `hablemos_con_lolo.webp`
- `lolo_me_cuenta_un_cuento.webp`
- `ahora_cuentamelo_tu.webp`
- `silabas_y_sonidos.webp`
- `escucho_y_respondo.webp`

Los archivos WEBP deben subirse a esta misma carpeta. Mantener los títulos y enlaces de las tarjetas como widgets Flutter, no como áreas táctiles sobre la imagen.
