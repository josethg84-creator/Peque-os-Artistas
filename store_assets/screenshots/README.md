# Capturas para Google Play

## Qué hay

| Carpeta | Contenido |
|---|---|
| `phone/` | **8 capturas propuestas** para «Capturas de pantalla del teléfono», en el orden en que se subirían. |
| `phone_extra/` | 3 capturas alternativas (galería de animales, paleta, «Encuentra a los animales»). |
| `android_emulator/` | 4 capturas de verificación en un **emulador Android 16** con el APK de lanzamiento (no son para la ficha; ver su README). |

Todas las capturas son PNG de **1080 × 2160** (proporción 1:2), RGB de 24 bits sin
transparencia y de 120 a 280 KB. Las dimensiones y el formato se han comprobado con Pillow.

**Requisitos de Google Play para teléfonos** (consultados con búsqueda web, porque
`support.google.com` está bloqueado en este entorno; compruébalos en Play Console):

- De **2 a 8** capturas.
- JPEG o PNG de 24 bits sin transparencia.
- Lado mínimo de 320 px y máximo de 3840 px.
- El lado largo no puede medir más del doble que el corto.

1080 × 2160 cumple todo esto, justo en el límite de 2:1.

| Archivo | Muestra |
|---|---|
| `01_inicio.png` | Pantalla de inicio rediseñada: logo, niños con pinceles, perrito y las 4 tarjetas |
| `02_categorias.png` | «Colorear»: «¡Vamos a pintar!» y las 5 categorías |
| `03_colorear.png` | Editor con un dinosaurio coloreado, herramientas y paleta |
| `04_mis_dibujos.png` | «Mis dibujos» con 3 creaciones (una terminada) |
| `05_aprende_colores.png` | «Aprende los colores» |
| `06_descubre_formas.png` | «Descubre las formas» tras un acierto |
| `07_une_parejas.png` | «Une las parejas» durante un intento |
| `08_mis_premios.png` | Estrellas y pegatinas conseguidas |

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
