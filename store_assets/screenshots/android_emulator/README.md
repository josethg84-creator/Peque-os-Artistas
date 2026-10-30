# Capturas del emulador Android 16 (solo verificación: no son para la ficha)

Emulador `system-images;android-36;google_apis;x86_64`, a 1080 × 2160 y 420 dpi, **sin
aceleración por hardware** (en este entorno no hay KVM). El APK es el de lanzamiento del
29/10/2026. Las capturas se han reducido a 540 × 1080.

| Captura | Qué demuestra |
|---|---|
| `01_pantalla_de_carga_android16.png` | La nueva pantalla de inicio (fondo crema y paleta) funciona en Android 16. |
| `02_inicio_android16.png` | El APK de lanzamiento se instala y abre en Android 16. El inicio se ve bien (mascota, botones, textos). |
| `03_categorias_android16_miniaturas_fallidas.png` | En este emulador las miniaturas muestran «Imagen pendiente». |
| `04_diagnostico_could_not_decompress.png` | Diagnóstico con una compilación de prueba (no publicada): el decodificador devuelve «Could not decompress image». |

## Investigación de las miniaturas

Todos los experimentos se hicieron en una copia temporal, fuera del repositorio:

1. PNG en escala de grises convertidas a RGBA: **siguen fallando**.
2. Sin redimensionar al decodificar (sin `cacheWidth`): **siguen fallando**.
3. Con Impeller desactivado (Skia): falla igual («Codec failed to produce an image»).
4. Los PNG dentro del APK son **idénticos byte a byte** a los originales y válidos.
5. `test/thumbnail_decode_test.dart` decodifica las 30 miniaturas a 3 tamaños con el
   decodificador nativo de Flutter (el mismo código del motor) en la CPU real de este
   servidor: **funciona**.

**Conclusión probable:** el emulador ejecuta la CPU x86 por software (QEMU TCG) y la
descompresión de imágenes falla en ese entorno. **No está demostrado en un móvil real.**

**Comprobación obligatoria antes de publicar:** instalar el APK en un Android físico y ver que
la galería muestra las miniaturas. Si fallaran también allí, sería un error bloqueante.

Además, el sistema del emulador dejó de responder varias veces por la lentitud: diálogos de
ANR y pantalla negra. Por eso no se pudieron hacer más capturas en Android ni comprobar el
icono en el lanzador.
