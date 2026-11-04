# Pequeños Artistas

Aplicación móvil de colorear para niños de 4 a 7 años (Flutter / Android).

- **Fase 1 (terminada):** colección de 30 dibujos para colorear y su catálogo. Hoy son 59 en 7
  categorías: 57 proceden de las imágenes de `Catalogo Imagenes/` (ver docs/DIBUJOS.md).
- **Fase 2 (terminada):** interfaz y navegación de la app Flutter.
- **Fase 3 (terminada):** motor real de coloreado por regiones vectoriales,
  deshacer/rehacer/limpiar y guardado local del progreso («Mis dibujos»).
- **Fase 4 (terminada):** los 30 dibujos integrados y validados, miniaturas
  ligeras, galería con indicador de «pintado», búsqueda y filtros.
- **Fase 5 (terminada):** guardado local seguro de las creaciones (con copia de
  seguridad y migración), «Mis dibujos» con miniaturas, progreso, nueva versión
  y borrado con confirmación. Sin cuentas ni conexión.
- **Fase 6 (terminada):** «Aprender jugando»: colores, formas, animales y parejas
  en tres niveles, sonidos y voz con controles, estrellas y pegatinas.
- **Fase 7 (terminada):** animaciones y transiciones suaves, relleno animado al
  colorear, celebraciones, la mascota Pincelín, sonidos con prioridad, estados de
  carga y vacíos amables, y respeto de «reducir movimiento».
- **Fase 8 (terminada):** versión web publicable (Vercel) y APK de Android.
- **Fase especial de sonido (terminada):** música de fondo original y opcional
  (silencio en los juegos), 27 efectos con variantes, voz que no se interrumpe ni se
  repite, pantalla «Sonido y música» con volúmenes independientes y pausa en segundo
  plano. Ver [docs/FASE_SONIDO.md](docs/FASE_SONIDO.md).
- **Juegos nuevos (terminados):** rompecabezas (4, 9 o 16 piezas), laberintos con recorridos
  generados y comprobados, y trazos y escritura (líneas, letras, números y unir puntos). Ver
  [docs/FASE_JUEGOS.md](docs/FASE_JUEGOS.md).
- **Nuevo inicio (terminado):** pantalla de inicio rediseñada (logo multicolor, niños con
  pinceles y perrito, tarjetas Colorear, Mini Juegos, Actividades y Galería, barra con
  Perfil, Logros y Configuración) y panel del niño. Ver [docs/FASE_INICIO.md](docs/FASE_INICIO.md).
- **Aprendo a Hablar (entregas 1 a 4):** módulo de lenguaje con Lolo el lorito: 100 palabras
  y 12 frases con voz en español (normal y despacio), construir y ordenar oraciones, los 15
  verbos en presente, «Practicar» con la propia voz (opcional, sin guardar ni enviar nada),
  36 conversaciones con Lolo, 20 cuentos narrados con preguntas, emociones y necesidades,
  8 historias para ordenar y contar, 56 ejercicios de «Escucho y respondo» y, en la 4.ª,
  sugerencias de Lolo según el progreso local, «Mi aventura de hoy», juegos de sílabas y rimas,
  313 palabras con sílabas y ejemplos, «Mi historia» y ajustes para adultos. Ver [docs/FASE_HABLAR.md](docs/FASE_HABLAR.md).
- **Quiero decir (fase 5, comunicación aumentativa):** tablero de comunicación con 203
  pictogramas y voz en español, tablero rápido «Necesito decir algo», constructor de frases,
  emociones, favoritas y ajustes para adultos. Funciona sin conexión, sin micrófono y sin
  estrellas. Ver [docs/FASE_CAA.md](docs/FASE_CAA.md).
- **Fase 6 (integración y pruebas):** navegación unificada, voz que se calla al salir, reducir
  animaciones, resumen de todo el progreso y auditorías de audio, accesibilidad y privacidad.
  Ver [docs/FASE6_INTEGRACION.md](docs/FASE6_INTEGRACION.md) y la
  [guía de pruebas con familias](docs/GUIA_PRUEBAS_FAMILIAS.md).
- **Fase 7 de «Aprendo a Hablar» (lanzamiento, sin publicar):** versión candidata para prueba
  interna o cerrada en Google Play. Incluye:
  - auditoría final y correcciones (inicio en teléfonos de 360 dp, micrófono opcional en Play,
    sin transferencia de datos entre teléfonos, barrido de grabaciones olvidadas);
  - capturas nuevas y de tableta, imágenes promocionales y ficha actualizada;
  - privacidad revisada y pruebas de los recorridos A–L.

  Ver [RELEASE_READINESS.md](store_assets/RELEASE_READINESS.md),
  [KNOWN_ISSUES.md](store_assets/KNOWN_ISSUES.md),
  [TESTING_CHECKLIST.md](store_assets/TESTING_CHECKLIST.md),
  [ANDROID_BUILD.md](store_assets/ANDROID_BUILD.md) y la
  [guía para adultos](docs/GUIA_ADULTOS.md).
- **Fase 9 (preparación, sin publicar):** recursos y documentación para Google Play en
  [`store_assets/`](store_assets/RELEASE_READINESS.md): icono, imagen destacada, capturas,
  textos de la ficha, borrador de política de privacidad, auditoría de privacidad,
  declaraciones de Play Console y firma. Ver
  [store_assets/RELEASE_READINESS.md](store_assets/RELEASE_READINESS.md).

```
lib/          código de la aplicación Flutter (pantallas, componentes, servicios…)
test/         pruebas (flutter test)
android/      proyecto Android
assets/
  drawings/   animals/ vehicles/ dinosaurs/ fruits/ fantasy/   SVG con regiones rellenables
  thumbnails/ miniaturas PNG 512x512 que usa la app
  audio/      música (Ogg) y efectos (WAV) originales (tools/make_audio.py, ver LICENCIAS.md)
  previews/   PNG 1024x1024 para control de calidad (no se empaquetan)
  catalog/    catalog.json (59 entradas)
web/          index.html, manifest e iconos de la versión web
deploy/web/   versión web ya compilada (la que publica Vercel, ver vercel.json)
store_assets/ recursos y documentos para Google Play (Fase 9, actualizados en la Fase 7)
docs/         DIBUJOS.md (Fase 1), FASE2_INTERFAZ.md, FASE3_MOTOR.md, FASE4_COLECCION.md, FASE5_GUARDADO.md, FASE6_APRENDER.md, FASE7_ANIMACIONES.md y capturas
tools/        generación, render y control de calidad de los dibujos
```

Detalles en [docs/DIBUJOS.md](docs/DIBUJOS.md), [docs/FASE2_INTERFAZ.md](docs/FASE2_INTERFAZ.md), [docs/FASE3_MOTOR.md](docs/FASE3_MOTOR.md), [docs/FASE4_COLECCION.md](docs/FASE4_COLECCION.md), [docs/FASE5_GUARDADO.md](docs/FASE5_GUARDADO.md), [docs/FASE6_APRENDER.md](docs/FASE6_APRENDER.md) y [docs/FASE7_ANIMACIONES.md](docs/FASE7_ANIMACIONES.md).

```bash
flutter pub get
flutter test
flutter run
```

## Versión web (Vercel)

`deploy/web/` contiene la app ya compilada para web (sin dependencias externas:
el motor gráfico va incluido, no se descarga de ningún CDN). `vercel.json` le dice
a Vercel que publique esa carpeta tal cual, sin compilar nada.

Para actualizarla tras cambiar el código:

```bash
bash tools/build_web.sh
```

y subir (commit y push) la carpeta `deploy/web/`.

