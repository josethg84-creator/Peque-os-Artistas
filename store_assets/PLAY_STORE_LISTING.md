# Ficha de Google Play: Pequeños Artistas 1.0.0

> **Borrador para revisar.** Los textos describen solo funciones comprobadas en el código y en
> las pruebas (Fases 1 a 7 de «Aprendo a Hablar»). Los campos marcados como **PENDIENTE** los
> completa el propietario: no se han inventado nombres legales, correos ni direcciones.

**Idioma principal propuesto:** Español (Latinoamérica), `es-419`. Si se publica también en
España, se puede añadir `es-ES` revisando giros como «toque» o «borrador».

## 1. Textos listos para Play Console

| Campo | Archivo | Caracteres | Límite |
|---|---|---|---|
| Nombre de la app | [`store_listing/title_es-419.txt`](store_listing/title_es-419.txt) | 17 | 30 |
| Descripción breve | [`store_listing/short_description_es-419.txt`](store_listing/short_description_es-419.txt) | 75 | 80 |
| Descripción completa | [`store_listing/full_description_es-419.txt`](store_listing/full_description_es-419.txt) | 2533 | 4000 |
| Novedades de la versión | [`store_listing/whats_new_es-419.txt`](store_listing/whats_new_es-419.txt) | 313 | 500 |

Los caracteres se han contado con Python (caracteres Unicode). Los límites de 30, 80, 4000 y
500 son los de la ayuda de Play Console, consultados con búsqueda web: desde este entorno no se
puede abrir `support.google.com`. **Compruébalos al pegar los textos.**

## 2. Nombre

| Propuesta | Caracteres | Comentario |
|---|---|---|
| **Pequeños Artistas** (recomendada) | 17 | Coincide con el nombre bajo el icono. Ya no describe solo «colorear», porque la app también trae «Aprendo a Hablar» y «Quiero decir». |
| Pequeños Artistas: Colorea | 26 | La propuesta anterior; se queda corta para la app actual. |
| Pequeños Artistas y Lolo | 24 | Más distintivo frente a apps parecidas. |

- Una búsqueda web (29/10/2026) no encontró ninguna app con el nombre exacto «Pequeños
  Artistas». Existe **«Pequeño Artista»** (singular, `com.pequenioartista.app`), también de
  colorear.
- **PENDIENTE (propietario):** buscar en Google Play desde un móvil, valorar el riesgo de
  confusión y, si se usa como marca, consultar INDECOPI (Perú).
- El identificador `com.pequenosartistas.pequenos_artistas` **no se ha cambiado** y no se podrá
  cambiar tras la primera publicación.

## 3. Descripción breve (75/80)

> Colorea, juega y aprende palabras con Lolo. Con pictogramas y sin conexión.

## 4. Descripción completa: de dónde sale cada afirmación

| Afirmación | Comprobación |
|---|---|
| 59 dibujos en 7 categorías | `assets/catalog/catalog.json`, `test/catalog_integrity_test.dart` |
| Paleta de 24 colores, zoom, borrador, deshacer, rehacer | `lib/coloring/`, `test/coloring/palette_test.dart` |
| Guardado automático y galería | `lib/persistence/`, `test/persistence/` |
| Minijuegos con 3 niveles, sin tiempo ni castigo | `lib/learning/`, `test/learning/` |
| Más de 300 palabras (100 básicas + 213 del vocabulario ampliado) | `assets/speech/words.json`, `assets/speech/vocabulary.json` |
| 40 conversaciones con Lolo | `assets/speech/conversations.json` |
| 20 cuentos con preguntas | `assets/speech/stories.json` |
| 56 ejercicios de «Escucho y respondo» | `assets/speech/listening.json` |
| Sílabas, sonidos, rimas y juegos de palabras | `lib/speech/phonology.dart`, `lib/speech/word_games.dart` |
| «Mi aventura de hoy» | `lib/speech/mission.dart`, `test/speech/phase4_flow_test.dart` |
| Practicar: la grabación no se guarda ni se envía | `lib/speech/voice_practice.dart`, `test/speech/speech_flow2_test.dart`, [PRIVACY_AUDIT.md](PRIVACY_AUDIT.md) |
| 203 pictogramas en 10 categorías | `assets/aac/pictograms.json`, `test/aac/aac_catalog_test.dart` |
| «Necesito decir algo» a un toque desde el inicio | `lib/screens/home/illustrated_home_cover.dart`, `test/phase6_integration_test.dart` |
| Comunicarse no da ni pide premios | `test/phase6_integration_test.dart` (recorrido E) |
| Voz del dispositivo en español | `lib/audio/app_audio.dart` (`flutter_tts`) |
| Sin anuncios, compras, cuentas, chat ni enlaces | `pubspec.lock`, manifiesto final, [PRIVACY_AUDIT.md](PRIVACY_AUDIT.md) |
| No pide acceso a Internet | Manifiesto final sin `android.permission.INTERNET` (`aapt2 dump badging`) |
| Zona para adultos con verificación | `lib/widgets/adult_gate.dart`, `lib/screens/adult_zone_screen.dart` |

**No se afirma** que la app diagnostique, trate, mejore el habla o el rendimiento escolar, ni que
tenga avales o certificaciones. La descripción dice expresamente que **no es una herramienta
médica ni terapéutica**. «Quiero decir» se presenta como un tablero de pictogramas para
practicar, no como un sistema clínico de comunicación aumentativa.

## 5. Categoría, etiquetas y público

- **Tipo:** Aplicación. **Categoría propuesta:** Educación (alternativa: Arte y diseño).
  **PENDIENTE:** decide el propietario.
- **Etiquetas** (de la lista de Play, hasta 5): colorear, educativo, niños o familia,
  aprendizaje temprano, lenguaje. No se han podido comprobar los nombres exactos.
- **Público objetivo:** niños de 4 a 7 años, con un adulto. Tramos de Play: **«5 años o menos»**
  y **«6 a 8 años»**. Ver [store_listing/DECLARACIONES_PLAY_CONSOLE.md](store_listing/DECLARACIONES_PLAY_CONSOLE.md).

## 6. Datos de contacto

| Campo | Estado |
|---|---|
| Nombre del desarrollador | **PENDIENTE** |
| Correo de contacto (obligatorio) | **PENDIENTE** |
| Sitio web (opcional) | Existe la versión web https://peque-artistas.vercel.app. **PENDIENTE:** el propietario decide si la enlaza. |
| URL de la política de privacidad (obligatoria) | **PENDIENTE:** borrador en [privacy/privacy_policy_draft.md](privacy/privacy_policy_draft.md). |

## 7. Recursos gráficos

| Recurso | Archivo | Comprobado |
|---|---|---|
| Icono | `icon/play_store_icon_512.png` | 512 × 512, PNG de 32 bits |
| Imagen destacada (recomendada) | `promo/feature_graphic_1024x500_v2.png` | 1024 × 500, PNG de 24 bits, sin transparencia. Usa la ilustración real del inicio. |
| Imagen destacada (anterior) | `feature_graphic/feature_graphic_1024x500.png` | Estilo plano anterior; se conserva como alternativa. |
| Capturas de teléfono | `screenshots/phone/`, `screenshots/phone_v2/` | 1080 × 2160 |
| Capturas de tableta | `screenshots/tablet/` | 1600 × 2560 |
| Imágenes promocionales | `promo/promo_*_1080x2160.png` | Capturas reales enmarcadas, con título. Valen como capturas de teléfono. |

Selección propuesta de 8 capturas de teléfono, en orden: ver
[screenshots/README.md](screenshots/README.md).
