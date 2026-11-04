# Auditoría de privacidad: Pequeños Artistas 1.0.0 (versionCode 1)

Revisión técnica actualizada el **04/11/2026** (Fase 7, rama `release/fase-7`) sobre el código,
las dependencias y el APK de lanzamiento. Sustituye a la auditoría anterior
(`privacy/AUDITORIA_PRIVACIDAD.md`, del 29/10/2026, anterior a «Quiero decir»). Sirve de base
para la [política de privacidad](privacy/privacy_policy_draft.md) y para las
[declaraciones de Play Console](store_listing/DECLARACIONES_PLAY_CONSOLE.md).

> **Esto no es asesoramiento legal ni una certificación.** No se afirma que la app «cumpla» la
> COPPA, el RGPD, la Ley 29733 ni ninguna otra norma: eso lo debe valorar el propietario, con
> asesoramiento si hace falta.

## Método

1. Dependencias directas (`pubspec.yaml`) y completas (`pubspec.lock`).
2. Búsqueda en `lib/` de red (`http`, `HttpClient`, `Socket`, `WebSocket`, `fetch`, `Uri.parse`
   con `http`), `url_launcher`, anuncios, analítica, Firebase e informes de errores.
3. Permisos del APK de lanzamiento con `aapt2 dump badging` (04/11/2026):
   - `android.permission.RECORD_AUDIO`;
   - `com.pequenosartistas.pequenos_artistas.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`
     (interno de AndroidX, sin diálogo).
   - **No hay `android.permission.INTERNET`.**
4. Qué se guarda y dónde (`lib/persistence/`, `lib/learning/learning_store.dart`,
   `lib/speech/speech_progress.dart`, `lib/aac/aac_controller.dart`).
5. Revisión línea a línea de la grabadora (`lib/speech/voice_practice.dart`,
   `voice_practice_files*.dart`) y de sus pruebas.

## Datos que guarda la app (solo en el dispositivo)

Todo va en `shared_preferences`, dentro del almacenamiento privado de la app.

| Clave | Contenido | Sensibilidad |
|---|---|---|
| `creation.v2.*` | Dibujos coloreados: id del dibujo, color de cada zona, fechas | Baja |
| `learning.v1.state` | Minijuegos: partidas, estrellas, pegatinas, nivel y ajustes de sonido, voz y animaciones | Baja |
| `speech.v1.state` (+ `.bak`) | «Aprendo a Hablar»: palabras y frases escuchadas, actividades hechas, estrellas, preferencias de nivel y de voz, misiones del día, historias inventadas con tarjetas, **cuántas** grabaciones se hicieron (no las grabaciones) | Baja-media: describe la práctica del niño |
| `aac.v1.state` (+ `.bak`) | «Quiero decir»: frases favoritas, preferencias del tablero y **cuántas veces se usó cada pictograma**, salvo los de «Necesidades», «Salud» y «Emociones», que no se cuentan nunca | Media: las frases favoritas pueden revelar necesidades del niño |

- No hay campos de texto libre que se guarden: la búsqueda filtra en memoria.
- Ningún dato lleva nombre, edad, foto, voz ni identificador del niño o del dispositivo.
- **Borrado:**
  - un dibujo, en la galería, con confirmación;
  - la personalización de «Quiero decir», desde la zona de adultos («Borrar personalización»);
  - todo, desde Android (Ajustes → Aplicaciones → Pequeños Artistas → Almacenamiento → Borrar
    datos) o desinstalando.
  - **No hay un botón único** «borrar todo» dentro de la app: ver [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Micrófono: verificación

| Pregunta | Resultado | Evidencia |
|---|---|---|
| ¿Cuándo se pide el permiso? | Solo al pulsar «Grabar» en «Practicar», nunca al abrir la app | `PracticeSheet`; prueba «el permiso se pide al pulsar «Grabar», no antes» (`test/speech/speech_flow2_test.dart`) |
| ¿Se graba en segundo plano o sin que se vea? | No. Solo con la ventana de práctica abierta, con una barra de 6 s visible y un máximo de 6 s | `PracticeSheet.maxLength` |
| ¿Dónde queda la grabación? | Teléfono: archivo `practica_<hora>.wav/.m4a` en la carpeta temporal de la app. Web: dirección `blob:` en memoria | `DeviceVoiceRecorder.start` |
| ¿Cuándo se borra? | Al grabar otra vez, al cerrar la ventana y al liberar la grabadora. **Nuevo en la Fase 7:** si la app se cerró a mitad, las que quedaran se borran antes de la siguiente grabación | `discard`, `dispose`, `sweepStaleClips`; `test/speech/voice_files_test.dart` |
| ¿Se envía, se analiza o se puntúa? | No. No hay red ni reconocimiento de voz: solo se reproduce para que el niño se escuche | Sin permiso INTERNET; sin paquetes de reconocimiento |
| ¿Se cuenta algo? | Solo el número de grabaciones hechas, para el resumen de adultos | `SpeechProgress.recordings` |
| ¿Si se deniega el permiso? | Mensaje amable («un adulto tiene que permitir el micrófono») y no se graba nada | prueba «practicar sin permiso» |
| ¿Un adulto lo puede quitar? | Sí: «Practicar con el micrófono» en la zona de adultos; el botón desaparece | prueba «un adulto puede quitar «Practicar»» |

## Red y terceros

| Pregunta | Resultado |
|---|---|
| ¿Transmite datos desde Android? | **No.** Sin permiso INTERNET el sistema no permite conexiones. No hay código de red en `lib/`. |
| ¿SDK que recojan datos? | **No.** Directas: `audioplayers`, `flutter_tts`, `shared_preferences`, `record`, `path_provider` y `web` (solo navegador). Ninguna es de anuncios, analítica ni errores. |
| ¿`http` en `pubspec.lock`? | Sí, como dependencia indirecta de `audioplayers`. La app solo reproduce sonidos empaquetados (`AssetSource`) y, sin INTERNET, no podría usarlo. |
| ¿ID de publicidad? | No: no está `com.google.android.gms.permission.AD_ID`. |
| ¿Voz? | `flutter_tts` usa el motor de texto a voz del sistema. En Android solo se elige una voz en español instalada que no necesite red. La app le pasa frases fijas y las frases de pictogramas que el niño toca. El motor es otra app, con su propia política. |
| ¿Enlaces externos, compras, chat, cuentas? | No hay. |

## Copias de seguridad y paso a otro teléfono

- `android:allowBackup="false"` y `fullBackupContent="false"`: sin copia en la nube.
- **Nuevo en la Fase 7:** `android:dataExtractionRules` excluye todos los datos de la copia en
  la nube y de la transferencia directa entre dispositivos (Android 12+). Así, las frases
  favoritas no pasan a otro teléfono al cambiar de móvil. Comprobado en
  `test/persistence/persistence_flow_test.dart` (12b).

## Versión web (https://peque-artistas.vercel.app)

- Es la misma app compilada para navegador; no es lo que se publica en Google Play.
- Los datos se guardan en el almacenamiento local del navegador. La grabación vive en memoria
  (`blob:`) y se libera al cerrar.
- Al descargar la página, **el alojamiento (Vercel) recibe la petición, como cualquier web**
  (dirección IP, navegador y fecha), según su propia política. La app no envía datos propios.
- En el navegador, la voz puede ser una voz en línea del propio navegador; la app lo avisa en
  la zona de adultos.
- Si se enlaza la web desde la ficha, la política de privacidad debe mencionarlo (el borrador
  ya lo hace).

## Implicaciones para Play Console

- **Seguridad de los datos.** Según la ayuda de Google (vista solo con búsqueda web), no se
  declaran como «recogidos» los datos a los que se accede solo en el dispositivo y que no salen
  de él. Con este análisis, la respuesta coherente es «no se recogen ni se comparten datos».
  **El propietario debe confirmarlo leyendo el formulario**, en especial para el audio.
- **Política de Familias.** Los datos del micrófono de niños se consideran información
  sensible. La app debe explicarlo con claridad en la política y en la ficha (ya lo hacen los
  borradores). Ver [privacy/REVISION_POLITICA_FAMILIAS.md](privacy/REVISION_POLITICA_FAMILIAS.md).
- **Cualquier SDK nuevo** (analítica, errores, anuncios) o el permiso INTERNET invalidan esta
  auditoría.
