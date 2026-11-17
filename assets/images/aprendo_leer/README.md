# Imágenes — Aprendo a leer

Ilustraciones 3D propias del módulo «Aprendo a leer». **Aún no hay ninguna**: mientras tanto
las tarjetas usan ilustraciones que ya tiene la app (de «Aprendo a Hablar»).

| Archivo | Dónde se ve | Qué debe mostrar | Color de fondo |
|---|---|---|---|
| `aprendo_las_silabas.webp` | Tarjeta «Aprendo las sílabas» | Letras grandes y bloques del abecedario | Celeste |
| `completo_palabras.webp` | Tarjeta «Completo palabras» | Una manzana, letras y piezas para completar palabras | Amarillo o naranja pastel |
| `leo_oraciones.webp` | Tarjeta «Leo oraciones» | Un libro abierto y un niño leyendo | Morado pastel |
| `escucho_y_escribo.webp` | Tarjeta «Escucho y escribo» y pantalla de dictado | Un lápiz, un cuaderno y unos audífonos | Verde pastel |
| `companero.webp` | Pantalla principal (junto al saludo) | Un personaje infantil 3D amigable (o Lolo en 3D) | Transparente |

Recomendaciones:

- Cuadradas, 512 × 512 px, WEBP, **sin texto dibujado** (el título lo pone la app).
- Figura centrada, fondo limpio y suave.
- Se pueden mandar por el chat; si se suben a GitHub, comprobar que no pesen 0 bytes.

Cuando lleguen, se registra la carpeta en `pubspec.yaml` y se cambia `image` por `plannedImage` en
`lib/reading/reading_activities.dart`.
