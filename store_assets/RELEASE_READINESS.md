# Preparación para Google Play: Pequeños Artistas 1.0.0

**Revisión:** 04/11/2026, Fase 7 de «Aprendo a Hablar» (lanzamiento profesional). Rama
`release/fase-7`, basada en la Fase 6 (`4434f2a`).

## Conclusión

**Versión candidata para prueba interna o cerrada. NO está lista para producción.**

- **Hecho:**
  - el código compila;
  - 511 pruebas automáticas superadas y `flutter analyze` sin avisos;
  - la ficha, los recursos gráficos, la privacidad y la documentación están preparados y
    verificados.
- **Falta, y no se puede hacer desde aquí:**
  - firmar con la clave de subida;
  - probar en dispositivos reales (sobre todo las miniaturas, la voz y el micrófono);
  - publicar la política de privacidad;
  - rellenar los formularios de Play Console;
  - hacer la prueba cerrada si la cuenta es personal y nueva.
- La lista completa está en [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

**No se ha publicado nada en Google Play, no se ha creado ninguna clave y no se ha desplegado
nada en producción.**

Leyenda: ✅ hecho y verificado · 🟡 pendiente · ⛔ bloqueado · ➖ no aplica.

## Documentos

| Documento | Para qué |
|---|---|
| [RELEASE_READINESS.md](RELEASE_READINESS.md) | Este informe: auditoría y estado |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | Problemas críticos, importantes y menores; los corregidos |
| [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) | Resultados automáticos, recorridos A–L, pruebas en dispositivo y prueba cerrada |
| [ANDROID_BUILD.md](ANDROID_BUILD.md) | Configuración de Android, resultados exactos de las órdenes y cómo compilar |
| [SIGNING.md](SIGNING.md) | Clave de subida, sin secretos en el repositorio |
| [PLAY_STORE_LISTING.md](PLAY_STORE_LISTING.md) | Ficha: nombre, textos y recursos |
| [PRIVACY_AUDIT.md](PRIVACY_AUDIT.md) | Auditoría de privacidad y del micrófono |
| [store_listing/DECLARACIONES_PLAY_CONSOLE.md](store_listing/DECLARACIONES_PLAY_CONSOLE.md) | Datos para los formularios de «Contenido de la aplicación» |
| [privacy/privacy_policy_draft.md](privacy/privacy_policy_draft.md) | Borrador de la política de privacidad |
| [privacy/REVISION_POLITICA_FAMILIAS.md](privacy/REVISION_POLITICA_FAMILIAS.md) | Revisión frente a la Política de Familias |
| [../docs/GUIA_ADULTOS.md](../docs/GUIA_ADULTOS.md) | Guía de uso para adultos y testers |
| [../docs/GUIA_PRUEBAS_FAMILIAS.md](../docs/GUIA_PRUEBAS_FAMILIAS.md) | Sesiones supervisadas con familias |

## Auditoría final de módulos (Etapa 1)

| # | Módulo | Estado | Observaciones |
|---|---|---|---|
| 1 | Inicio y navegación | ✅ | **Corregido:** botones que partían palabras a 360 dp. Pruebas de navegación y de rutas inexistentes |
| 2 | Colorear (motor vectorial, 59 dibujos) | ✅ / ⛔ | Pruebas de todas las regiones y del tacto. Miniaturas en Android sin verificar (C2) |
| 3 | Guardado y galería | ✅ | Guardado automático, datos dañados, reinicio (L) |
| 4 | Minijuegos | ✅ | Recorridos completos, niveles y ajustes |
| 5 | Audio (música, efectos, voz) | ✅ / 🟡 | Simulado en las pruebas; falta oírlo en un dispositivo |
| 6 | Aprendo a Hablar: palabras, frases y oraciones | ✅ | |
| 7 | Conversaciones con Lolo | ✅ / 🟡 | En tableta, las tarjetas se ven pequeñas (I1) |
| 8 | Cuentos y «Escucho y respondo» | ✅ / 🟡 | Ídem en tableta |
| 9 | Sílabas, rimas, juegos de palabras, «Mi aventura de hoy», «Mi historia» | ✅ | |
| 10 | Micrófono («Practicar») | ✅ / 🟡 | **Corregido:** se barren las grabaciones olvidadas. Falta probarlo en un dispositivo |
| 11 | Quiero decir (203 pictogramas, tablero rápido, constructor) | ✅ | Comunicarse no depende de premios |
| 12 | Progreso, estrellas y resumen para adultos | ✅ | Sin etiquetas diagnósticas |
| 13 | Zona para adultos y ajustes | ✅ | |
| 14 | Accesibilidad (texto grande, lectores, reducir animaciones) | ✅ / 🟡 | Pruebas a ×1.6 y de etiquetas; falta TalkBack real |
| 15 | Privacidad, permisos y Android | ✅ | **Corregido:** micrófono no obligatorio y `dataExtractionRules` |

Ningún fallo crítico conocido está en el código. Los críticos (C1–C5) son externos.

## A. Aplicación y compilación

| Punto | Estado | Detalle |
|---|---|---|
| Identificador | 🟡 | `com.pequenosartistas.pequenos_artistas`. Es permanente tras la primera subida: el propietario debe confirmarlo |
| Versión | ✅ | 1.0.0 (versionCode 1) |
| API | ✅ | targetSdk 36, compileSdk 36, minSdk 24. Cumple la regla de API 36 desde el 31/08/2026 |
| Permisos | ✅ | Micrófono (opcional, `required="false"`) y uno interno; **sin INTERNET** |
| APK de lanzamiento | ✅ / 🟡 | 62,6 MB. Compila; firmado con la clave de depuración |
| AAB de lanzamiento | ✅ / 🟡 | 60,6 MB. Compila; firmado con la clave de depuración, **Play lo rechazaría** (C1) |
| Secretos en git | ✅ | Ninguno; `key.properties`, `*.jks` y `*.keystore` están en `.gitignore` |
| Pruebas automáticas | ✅ | 511 superadas; recorridos A–L cubiertos |
| Dispositivo real | ⛔ | Ninguna prueba (C2, C4) |

Detalle en [ANDROID_BUILD.md](ANDROID_BUILD.md).

## B. Ficha y recursos gráficos

| Punto | Estado | Detalle |
|---|---|---|
| Textos | 🟡 | Actualizados en la Fase 7 (17/30, 75/80, 2533/4000, novedades 313/500), sin afirmaciones terapéuticas. Falta la aprobación del propietario |
| Icono de 512 | ✅ | Sin cambios |
| Imagen destacada | ✅ | Nueva v2 con la ilustración real del inicio (`promo/`) |
| Capturas de teléfono | ✅ / 🟡 | Reales (web, mismo código), con 7 nuevas de la Fase 7 y una selección propuesta de 8. Conviene repetirlas en un móvil |
| Capturas de tableta | ✅ / 🟡 | 4 reales a 1600 × 2560 |
| Imágenes promocionales | ✅ | «Aprendo a Hablar», «Hablemos con Lolo» y «Quiero decir», hechas con capturas reales sin retocar |
| Pantalla de carga | ✅ | Sin cambios (vista en el emulador) |

## C. Privacidad y políticas (Etapas 4 y 5)

| Punto | Estado | Detalle |
|---|---|---|
| Auditoría | ✅ | [PRIVACY_AUDIT.md](PRIVACY_AUDIT.md), actualizada con «Quiero decir», el micrófono y la web |
| Política de privacidad | ⛔ | Borrador actualizado; faltan el responsable, el contacto, la revisión legal y la URL (C3) |
| Seguridad de los datos | 🟡 | Respuesta coherente: no se recogen ni se comparten datos (solo hay datos en el dispositivo). La confirma el propietario |
| Familias | 🟡 | Sin incumplimientos técnicos detectados. El micrófono de niños es información sensible: está explicado. Hay que leer la página vigente |
| Público objetivo | 🟡 | «5 años o menos» y «6 a 8 años» |
| Clasificación IARC | 🟡 | Datos preparados; el cuestionario lo rellena el propietario |
| Anuncios, compras, AAID | ➖ | No hay |

**Limitación:** `support.google.com` y `play.google.com` no se pueden abrir desde este entorno.
Las reglas se tomaron de búsquedas web y de developer.android.com. **El propietario debe revisar
las políticas vigentes antes de enviar.**

## D. Optimización (Etapa 7)

| Área | Revisión |
|---|---|
| Tamaño del AAB | Lo ocupan sobre todo el motor (`libflutter`, 8,6–13 MB por arquitectura), el código (`libapp`, unos 7,5 MB) y las imágenes (miniaturas 2,2 MB y vistas previas 5,7 MB). Play entrega solo la arquitectura de cada móvil |
| Imágenes | Las miniaturas y vistas previas ya están pre-renderizadas (no se generan al abrir) |
| Motor de colorear | Dibujos vectoriales; `DrawingLoader` guarda en caché los últimos dibujos abiertos (LRU). El lienzo y las miniaturas tienen `RepaintBoundary` |
| Animaciones | Se pueden reducir desde la zona de adultos y respetan el ajuste del sistema |
| Pictogramas | Iconos vectoriales del sistema (sin imágenes), con un catálogo JSON de 72 KB |
| Audio | Efectos cortos y música en bucle (980 KB en total); la voz es la del sistema |
| Arranque | Sin red ni descargas. El progreso, «Aprendo a Hablar» y «Quiero decir» se cargan en segundo plano, sin bloquear la primera pantalla |
| Sin conexión | Total en Android (sin permiso INTERNET) |

No se ha cambiado nada de esto en la Fase 7: no hay mediciones en un dispositivo que lo
justifiquen. Hay que medir el arranque y la memoria en un móvil de gama baja
([TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)).

## E. Cuenta y publicación

| Punto | Estado |
|---|---|
| Cuenta de desarrollador, verificación de identidad y datos de contacto | ⛔ Propietario |
| Clave de subida | ⛔ Propietario ([SIGNING.md](SIGNING.md)) |
| Prueba interna | 🟡 No hecha |
| Prueba cerrada (12 testers, 14 días, cuentas personales nuevas) | 🟡 **No hecha.** Instrucciones en [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) |
| Derechos de las imágenes de «Catalogo Imagenes/» | 🟡 El propietario debe confirmar que puede usarlas comercialmente |

## Pasos en Play Console (cuando el propietario lo decida)

1. Crear la cuenta de desarrollador y verificar la identidad.
2. Crear la app: nombre, idioma `es-419`, «Aplicación», «Gratuita». Una app gratuita no puede
   pasar a ser de pago.
3. «Contenido de la aplicación»: seguir
   [store_listing/DECLARACIONES_PLAY_CONSOLE.md](store_listing/DECLARACIONES_PLAY_CONSOLE.md).
4. Ficha: textos de `store_listing/`, icono, imagen destacada v2, capturas y contacto.
5. Clave de subida, AAB firmado y comprobación de la firma ([ANDROID_BUILD.md](ANDROID_BUILD.md)).
6. **Prueba interna** y luego **prueba cerrada** ([TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)).
7. Revisar el informe previo al lanzamiento.
8. Solo después, pedir acceso a producción y enviar a revisión.

**Ninguno de estos pasos se ha hecho desde aquí.**
