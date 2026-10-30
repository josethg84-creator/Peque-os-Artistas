# Auditoría de privacidad: versión 1.0.0 (versionCode 1)

Revisión técnica hecha el 29/10/2026 sobre el código, las dependencias y el manifiesto final
generado por Gradle para el AAB de lanzamiento. Sirve de base para el borrador de política y
para el formulario «Seguridad de los datos» de Play Console.

## Método

1. Dependencias directas (`pubspec.yaml`) y completas (`pubspec.lock`).
2. Búsqueda en `lib/` de red, URL, *sockets*, `dart:io` HTTP, `url_launcher`, anuncios,
   analíticas y Firebase.
3. Manifiesto final combinado (`build/app/intermediates/merged_manifests/release/...`):
   permisos, servicios, receptores y proveedores.
4. Revisión de qué guarda la app (`lib/persistence/`, `lib/learning/learning_store.dart`).
5. Prueba en ejecución: la versión web, servida en local, **no hizo ninguna petición fuera de
   su propio servidor** (Fase 8, Playwright). En Android, sin el permiso INTERNET, el sistema
   no permite conexiones de red.

## Resultados

| Pregunta | Resultado | Evidencia |
|---|---|---|
| ¿Recopila datos personales? | **No** | No hay formularios, cuentas ni campos de texto libres que se guarden. El campo de búsqueda filtra en memoria y no se guarda. |
| ¿Qué guarda en el dispositivo? | Dibujos (id del dibujo, colores por zona, fechas); progreso de juegos (partidas, estrellas, pegatinas, fechas); preferencias (nivel, silencio, música, efectos y voz con sus volúmenes) | `shared_preferences`, claves `creation.v2.*` y `learning.v1.*` |
| ¿Transmite información? | **No** | Sin permiso INTERNET; ningún código de red en `lib/` |
| ¿SDK de terceros que recojan datos? | **No** | Directas: `audioplayers` 6.8.1, `flutter_tts` 4.2.5, `shared_preferences` 2.5.6. Ninguna es SDK de anuncios, analítica ni errores. |
| ¿Analítica, anuncios, ID de publicidad (AAID)? | **No** | No hay `play-services-ads`, `firebase_*` ni `com.google.android.gms.permission.AD_ID` en el manifiesto final |
| ¿Permisos del dispositivo? | **Ninguno peligroso** | El único permiso es `…DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`: interno de AndroidX, propio de la app y sin diálogo para el usuario |
| ¿Internet en uso normal? | **No** | La app funciona totalmente sin conexión |
| ¿Datos de uso? | **No se envían.** Las estadísticas de juego solo se guardan en el propio dispositivo. | Ver arriba |
| ¿Se pueden borrar las creaciones? | **Sí**, una a una en «Mis dibujos» (con confirmación). Todo, borrando datos o desinstalando. | `saved_drawings_screen.dart`; prueba de borrado (Fase 5) |
| ¿Copia de seguridad en la nube? | **Desactivada** | `android:allowBackup="false"`, `fullBackupContent="false"` |
| ¿Enlaces externos? | **No** | No hay `url_launcher` ni enlaces en ninguna pantalla |
| ¿Contenido generado por usuarios compartible? | **No** | Los dibujos coloreados no salen del dispositivo |

## Matices que conviene conocer

- **`http` aparece en `pubspec.lock`** como dependencia indirecta de `audioplayers` (para
  reproducir sonidos desde URL). La app solo usa `AssetSource`, sonidos empaquetados. Además,
  sin el permiso INTERNET, Android bloquea cualquier conexión.
- **Voz (`flutter_tts`):** usa el motor de texto a voz del sistema, y desde la fase de sonido **solo una voz en español instalada que no necesita red** (en Android se comprueba `network_required`). La app le pasa solo frases
  fijas de instrucciones. El motor es otra app (por ejemplo, Speech Services by Google), con
  sus propios permisos y política. Esto está explicado en el borrador de política.
- **Transferencia entre dispositivos:** con targetSdk 31 o superior, `allowBackup=false`
  desactiva la copia en la nube, pero **no** la transferencia directa entre dispositivos (D2D)
  de algunos fabricantes. Riesgo bajo, porque solo hay dibujos y progreso. Si se quiere
  bloquear también, habría que añadir `android:dataExtractionRules`. No se ha cambiado.

## Implicaciones para Play Console

- **Seguridad de los datos:** con estas prácticas, la respuesta es «La app no recoge ni
  comparte datos de usuario». Google considera «recogida» solo la transmisión fuera del
  dispositivo; los datos guardados solo en el dispositivo no se declaran. **El propietario debe
  confirmarlo** al rellenar el formulario. Ver
  [`../store_listing/DECLARACIONES_PLAY_CONSOLE.md`](../store_listing/DECLARACIONES_PLAY_CONSOLE.md).
- **Política de Familias:** no hay SDK de anuncios, así que no aplica la lista de SDK
  autocertificados para Familias. Tampoco se transmiten identificadores ni ubicación.
