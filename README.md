# Pequeños Artistas

Aplicación móvil de colorear para niños de 4 a 7 años (Flutter / Android).

- **Fase 1 (terminada):** colección de 30 dibujos para colorear y su catálogo.
- **Fase 2 (terminada):** interfaz y navegación de la app Flutter. El coloreado
  por regiones aún no funciona: la pantalla de coloreado es solo su diseño.

```
lib/          código de la aplicación Flutter (pantallas, componentes, servicios…)
test/         pruebas (flutter test)
android/      proyecto Android
assets/
  drawings/   animals/ vehicles/ dinosaurs/ fruits/ fantasy/   SVG con regiones rellenables
  previews/   PNG 1024x1024 de cada dibujo
  catalog/    catalog.json (30 entradas)
docs/         DIBUJOS.md (Fase 1), FASE2_INTERFAZ.md (Fase 2) y capturas
tools/        generación, render y control de calidad de los dibujos
```

Detalles en [docs/DIBUJOS.md](docs/DIBUJOS.md) y [docs/FASE2_INTERFAZ.md](docs/FASE2_INTERFAZ.md).

```bash
flutter pub get
flutter test
flutter run
```
