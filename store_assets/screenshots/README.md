# Capturas para Google Play

## Qué hay

| Carpeta | Contenido |
|---|---|
| `phone/` | 8 capturas de colorear y minijuegos (Fase 9). `01_inicio.png` se **rehízo en la Fase 7** con el inicio actual (accesos «Aprendo a Hablar» y «Necesito decir algo»). |
| `phone_v2/` | **Fase 7:** 7 capturas de «Aprendo a Hablar» y «Quiero decir». |
| `phone_extra/` | Capturas alternativas (galería, paleta, juegos). |
| `tablet/` | **Fase 7:** 4 capturas de tableta de 10" en vertical (1600 × 2560). |
| `android_emulator/` | Verificación en un emulador Android 16; no son para la ficha (ver su README). |
| `../promo/` | Imágenes promocionales hechas con capturas reales enmarcadas, más la imagen destacada v2. |

Teléfono: PNG de **1080 × 2160** (360 × 720 dp con densidad 3). Tableta: **1600 × 2560**
(800 × 1280 dp con densidad 2). Todas son RGB de 24 bits sin transparencia, comprobado con
Pillow. Requisitos de Play (consultados con búsqueda web; compruébalos en Play Console): de 2 a 8
capturas por tipo, PNG o JPEG sin transparencia, lados de 320 a 3840 px y el lado largo como
máximo el doble del corto.

### Selección propuesta (8 capturas de teléfono)

1. `phone/01_inicio.png`: inicio.
2. `phone/03_colorear.png`: colorear.
3. `phone_v2/02_aprendo_a_hablar.png`: menú «Aprendo a Hablar».
4. `phone_v2/03_hablemos_con_lolo.png`: conversación con Lolo.
5. `phone_v2/04_cuento.png`: «Toby y la pelota roja».
6. `phone_v2/06_tablero_pictogramas.png`: frase «Yo quiero jugar» con pictogramas.
7. `phone/06_rompecabezas.png`: minijuego.
8. `phone/08_mis_premios.png`: estrellas y pegatinas.

En lugar de 3, 4 y 6, se pueden usar las tres imágenes de `../promo/`, que llevan título.

### Aviso sobre «La voz no está disponible»

En `phone_v2/05`, `07`, `08` y en las de tableta aparece el aviso «La voz no está disponible en
este dispositivo». Es real: el Chromium sin voces de este entorno no tiene texto a voz en
español. En un móvil con la voz instalada no sale. **No se ha borrado de las imágenes.** Para la
ficha conviene repetirlas en un móvil real o usar las que no lo muestran (selección de arriba).

### Tableta: limitación detectada

En una tableta en vertical, varias pantallas de «Aprendo a Hablar» (conversaciones, cuentos)
dejan mucho espacio vacío y las tarjetas se ven pequeñas. Por eso solo se proponen el inicio y
«Quiero decir». Ver [KNOWN_ISSUES.md](../KNOWN_ISSUES.md).

## Cómo se obtuvieron (importante)

- Son **capturas reales de la app**, del mismo código Flutter de la versión 1.0.0, compilado
  para web (`deploy/web`). Se manejó con Playwright en Chromium, a 360 × 720 dp con densidad 3.
- El recorrido fue real: se pintaron los dibujos, se jugaron las partidas y se ganaron las
  pegatinas. No hay datos personales.
- **Diferencia con un teléfono:** no aparece la barra de estado de Android. El resto de la
  interfaz es el mismo código.
- Se intentó capturar en un **emulador Android 16**, pero este entorno no tiene aceleración
  por hardware (no hay KVM). El emulador va extremadamente lento y el sistema llegó a dejar de
  responder. Ver `android_emulator/` y [RELEASE_READINESS.md](../RELEASE_READINESS.md).

**Recomendación:** antes de publicar, el propietario puede repetir estas capturas en un móvil
Android real (botón de encendido + bajar volumen), siguiendo el mismo orden. Si las capturas
web le parecen fieles, también puede usarlas tal cual.

## Errores encontrados gracias a las capturas (ya corregidos)

**Fase 7:** en el inicio, a 360 dp, los botones partían «Aprend|o a Hablar» y «Necesit|o
decir algo». Ahora, si el botón es estrecho, el dibujo va encima del texto
(`AacShortcut.narrowWidth`). Lo comprueba `test/narrow_phone_test.dart` midiendo con Fredoka.

Fase 9:

En teléfonos de 360 dp de ancho, muy comunes:

1. Los títulos se cortaban o partían palabras («Descubr / e las fo…», «Encuentr / a a los …»).
   Ahora `FittedTitle` reduce el tamaño de letra y el icono decorativo se oculta por debajo de
   400 dp.
2. La barra de herramientas de colorear salía cortada («Limpia…»). Ahora se ajusta al ancho y
   los botones siguen midiendo más de 48 dp.

Ambos casos están cubiertos por `test/narrow_phone_test.dart`, que mide los textos con
Roboto.

## Regenerar

1. `bash tools/build_web.sh`
2. Servir `deploy/web` y ejecutar el guion de Playwright descrito en la Fase 9. Es un
   recorrido por la galería, colorear, «Mis dibujos» y los minijuegos.
3. Fase 7: el recorrido de `phone_v2/` y `tablet/` usa rutas directas (`/#/hablar/cuentos`,
   `/#/quiero-decir`…) y toca las tarjetas como lo haría un niño.
4. Promocionales: `python3 tools/store_promo.py <carpeta de capturas de teléfono>`.
