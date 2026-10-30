# Revisión frente a la Política de Familias de Google Play

> **Fuentes y limitación.** `support.google.com` (página oficial 9893335) está bloqueado en
> este entorno. Los requisitos se tomaron de los resultados de búsqueda que citan esa página y
> de la documentación de developer.android.com. **El propietario debe leer la versión vigente
> antes de enviar la app:**
> https://support.google.com/googleplay/android-developer/answer/9893335

| Requisito (resumen) | Situación en Pequeños Artistas | Estado |
|---|---|---|
| Contenido adecuado para niños: sin violencia, miedo, contenido sexual, etc. | 30 dibujos amables, sonidos suaves, mensajes positivos y sin castigos | Cumple; lo verificará Google |
| Política de privacidad que refleje las prácticas reales | Borrador hecho y aún no publicado | **PENDIENTE** |
| No transmitir identificadores del dispositivo, AAID ni ubicación de niños | No se transmite nada; sin permiso INTERNET ni SDK | Cumple (verificado en el código) |
| Solo SDK de anuncios autocertificados para Familias y sin anuncios personalizados | No hay anuncios ni SDK de anuncios | No aplica |
| SDK de terceros aptos para niños | Solo `audioplayers`, `flutter_tts` y `shared_preferences`, que funcionan dentro del dispositivo y no recogen datos | Cumple. **CONFIRMAR** con la lista de Google si la exige para otros SDK. |
| Compras y monetización claras, sin presionar a los niños | No hay compras ni monetización | No aplica |
| Enlaces externos y salida de la app protegidos | No hay enlaces externos; la zona de adultos no enlaza fuera | Cumple |
| Sin chat anónimo ni funciones sociales para niños | No hay chat ni funciones sociales | Cumple |
| Declarar bien el público objetivo | Tramos «5 años o menos» y «6 a 8 años» | **PENDIENTE** (lo declara el propietario) |
| No usar permisos o API restringidas para niños (ubicación precisa, etc.) | Ningún permiso peligroso | Cumple |
| Ficha (icono, imágenes, textos) adecuada para niños | Recursos originales y sin afirmaciones engañosas | Cumple; lo revisará Google |
| Cumplir las leyes de privacidad infantil (COPPA, RGPD, Ley 29733 en Perú…) | La app no recoge datos; el texto legal lo debe revisar el propietario | **PENDIENTE** (revisión legal) |

## Qué NO hacer en futuras versiones sin rehacer esta revisión

- Añadir analítica (Firebase Analytics, etc.), informes de errores o anuncios.
- Añadir el permiso INTERNET, enlaces externos, compras, cuentas, chat o compartir dibujos.
- Usar cámara, micrófono o ubicación.
