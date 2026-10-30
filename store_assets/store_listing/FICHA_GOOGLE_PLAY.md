# Ficha de Google Play: Pequeños Artistas

> **Borrador para revisar.** Los textos describen solo funciones comprobadas en el código y
> en las pruebas (Fases 1 a 8). Los campos marcados como **PENDIENTE** debe completarlos el
> propietario: no se han inventado nombres legales, correos ni direcciones.

**Idioma principal propuesto:** Español (Latinoamérica), `es-419`. Cubre Perú y el resto de
Hispanoamérica. Si se quiere publicar también en España, se puede añadir una traducción
`es-ES`; en ese caso, conviene revisar giros como «toque» o «borrador».

Textos listos para copiar y pegar en Play Console:

| Campo | Archivo | Caracteres | Límite |
|---|---|---|---|
| Nombre de la app | [`title_es-419.txt`](title_es-419.txt) | 26 | 30 |
| Descripción breve | [`short_description_es-419.txt`](short_description_es-419.txt) | 78 | 80 |
| Descripción completa | [`full_description_es-419.txt`](full_description_es-419.txt) | 2156 | 4000 |

Los recuentos se han medido con Python (caracteres Unicode). Los límites de 30, 80 y 4000
caracteres son los de la ayuda de Play Console; consultados mediante búsqueda web, porque
desde este entorno no se puede abrir `support.google.com`.

## 1. Nombre

El nombre provisional **«Pequeños Artistas: Colorea y Aprende» tiene 36 caracteres** y
**supera el límite de 30** de Google Play, así que no se puede usar tal cual.

| Propuesta | Caracteres | Comentario |
|---|---|---|
| **Pequeños Artistas: Colorea** (recomendada) | 26 | Corta y clara. «Aprende» pasa a la descripción breve. |
| Pequeños Artistas: Colorear | 27 | Variante con verbo en infinitivo. |
| Pequeños Artistas | 17 | La más limpia; coincide con el nombre del icono en el móvil. |

**Comprobación de disponibilidad (parcial):**

- En Google Play no existe una ventanilla oficial de «nombre disponible»: el nombre no es
  exclusivo. Lo que sí debe evitarse es confundir a los usuarios con otra app o marca.
- Una búsqueda web (29/10/2026) **no encontró ninguna app publicada con el nombre exacto
  «Pequeños Artistas»**.
- Sí existe **«Pequeño Artista»** (singular, `com.pequenioartista.app`), otra app familiar de
  colorear y dibujo. El parecido es alto.
- No se pudo buscar directamente en Google Play: `play.google.com` está bloqueado en este
  entorno.
- **PENDIENTE (propietario):**
  1. Buscar en Google Play desde un móvil «Pequeños Artistas» y «Pequeño Artista».
  2. Valorar el riesgo de confusión con «Pequeño Artista».
  3. Si se va a usar como marca comercial, consultar el registro de marcas de INDECOPI (Perú).

  Si el parecido preocupa, un nombre más distintivo sería, por ejemplo, «Pequeños Artistas
  con Pincelín».

El **nombre comercial** (ficha) y el **identificador del paquete** son cosas distintas:

- Nombre bajo el icono en el móvil: «Pequeños Artistas» (`android:label`). No cambia.
- Identificador: `com.pequenosartistas.pequenos_artistas`. **No se ha cambiado.** Una vez
  publicada la primera versión, ya no se puede cambiar. Ver
  [RELEASE_READINESS.md](../RELEASE_READINESS.md).

## 2. Descripción breve (78/80)

> Colorea 31 dibujos y aprende colores, formas y animales jugando. Sin conexión.

## 3. Descripción completa

Está en [`full_description_es-419.txt`](full_description_es-419.txt). Cada afirmación se ha
contrastado con el código:

| Afirmación | Dónde se comprueba |
|---|---|
| 31 dibujos en 5 categorías y 3 dificultades | `assets/catalog/catalog.json`, `test/catalog_integrity_test.dart` |
| Toque para pintar, borrador, deshacer, rehacer, limpiar | `lib/coloring/`, `test/coloring/` |
| Búsqueda y filtros por categoría y dificultad | `lib/screens/search_screen.dart` |
| Guardado automático y «Mis dibujos» (continuar, otra versión, borrar) | `lib/persistence/`, `lib/screens/saved_drawings_screen.dart` |
| 4 minijuegos y 3 niveles | `lib/learning/` (Fase 6) |
| Voz opcional con la voz del dispositivo | `flutter_tts`: usa solo una voz en español instalada (sin red); ver `docs/FASE_SONIDO.md` |
| Música original y opcional, silencio en los juegos, volúmenes independientes | `lib/audio/`, `assets/audio/LICENCIAS.md`, `test/audio_system_test.dart` |
| 7 pegatinas | `lib/learning/rewards.dart` |
| Sin anuncios ni compras | No hay SDK de anuncios ni de facturación (`pubspec.lock`) |
| Sin cuentas, registro ni chat | No existe ninguna pantalla de cuenta o chat |
| Funciona sin Internet; no pide acceso a Internet | Manifiesto final sin `android.permission.INTERNET` |
| Zona para adultos con verificación | `lib/widgets/adult_gate.dart` |
| Reducir animaciones | Fase 7: `AppMotion.reduced` |

**No se afirma** que la app mejore resultados escolares ni la inteligencia, ni que tenga
avales, premios o certificaciones.

## 4. Categoría y etiquetas

- **Tipo:** Aplicación (no «Juego»). Es sobre todo una herramienta para colorear con
  actividades.
- **Categoría propuesta:** **Educación**. Alternativa: **Arte y diseño**.
  **PENDIENTE:** decide el propietario.
- **Etiquetas:** Play Console solo deja elegir de su propia lista (hasta 5). Propuestas, para
  buscar en esa lista:
  - «Colorear»;
  - «Dibujo»;
  - «Educativo»;
  - «Niños» o «Familia»;
  - «Aprendizaje temprano».

  No se han podido comprobar los nombres exactos de las etiquetas.

## 5. Datos de contacto (Play Console → Ficha de Play Store → Detalles de contacto)

| Campo | Estado |
|---|---|
| Nombre del desarrollador (visible en Play) | **PENDIENTE:** el nombre de la cuenta de desarrollador. |
| Correo de contacto (obligatorio) | **PENDIENTE:** proporcionado por el propietario. |
| Sitio web (opcional) | **PENDIENTE.** Existe una versión web en Vercel (Fase 8) si el propietario la ha desplegado; la URL no se conoce. |
| Teléfono (opcional) | **PENDIENTE / opcional.** |
| Dirección física | **PENDIENTE.** Google la pide y la muestra en ciertos casos (p. ej., cuentas de organización o apps de pago). |
| URL de la política de privacidad (obligatoria para apps con público infantil) | **PENDIENTE:** el borrador está en [`../privacy/privacy_policy_draft.md`](../privacy/privacy_policy_draft.md) y aún no está publicado. |

## 6. Edad recomendada y público

- Público objetivo de la app: **niños de 4 a 7 años**, con acompañamiento de adultos.
- En Play Console (Público objetivo y contenido), los tramos de edad son fijos. Los que
  corresponden son **«5 años o menos»** y **«6 a 8 años»**.
- La clasificación de contenido (IARC) sale del cuestionario oficial. Ver
  [`DECLARACIONES_PLAY_CONSOLE.md`](DECLARACIONES_PLAY_CONSOLE.md).

## 7. Recursos gráficos

| Recurso | Archivo | Comprobado |
|---|---|---|
| Icono de la ficha | `store_assets/icon/play_store_icon_512.png` | 512 × 512, PNG 32 bits, opaco, 70 KB |
| Imagen destacada | `store_assets/feature_graphic/feature_graphic_1024x500.png` | 1024 × 500, PNG 24 bits sin transparencia, 137 KB |
| Capturas | `store_assets/screenshots/` | Ver [`../screenshots/README.md`](../screenshots/README.md) |
