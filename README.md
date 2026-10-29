# Pequeños Artistas

Aplicación móvil de colorear para niños de 4 a 7 años (Flutter / Android).

- **Fase 1 (terminada):** colección de 30 dibujos para colorear y su catálogo.
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

```
lib/          código de la aplicación Flutter (pantallas, componentes, servicios…)
test/         pruebas (flutter test)
android/      proyecto Android
assets/
  drawings/   animals/ vehicles/ dinosaurs/ fruits/ fantasy/   SVG con regiones rellenables
  thumbnails/ miniaturas PNG 512x512 que usa la app
  sounds/     efectos de sonido WAV propios (tools/make_sounds.py)
  previews/   PNG 1024x1024 para control de calidad (no se empaquetan)
  catalog/    catalog.json (30 entradas)
docs/         DIBUJOS.md (Fase 1), FASE2_INTERFAZ.md, FASE3_MOTOR.md, FASE4_COLECCION.md, FASE5_GUARDADO.md, FASE6_APRENDER.md, FASE7_ANIMACIONES.md y capturas
tools/        generación, render y control de calidad de los dibujos
```

Detalles en [docs/DIBUJOS.md](docs/DIBUJOS.md), [docs/FASE2_INTERFAZ.md](docs/FASE2_INTERFAZ.md), [docs/FASE3_MOTOR.md](docs/FASE3_MOTOR.md), [docs/FASE4_COLECCION.md](docs/FASE4_COLECCION.md), [docs/FASE5_GUARDADO.md](docs/FASE5_GUARDADO.md), [docs/FASE6_APRENDER.md](docs/FASE6_APRENDER.md) y [docs/FASE7_ANIMACIONES.md](docs/FASE7_ANIMACIONES.md).

```bash
flutter pub get
flutter test
flutter run
```
