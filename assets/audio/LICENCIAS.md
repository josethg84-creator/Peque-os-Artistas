# Audio de Pequeños Artistas: origen y licencias

**Todo el audio es original.** Lo genera desde cero `tools/make_audio.py`: sumas de senoides
que imitan marimba, xilófono, campanitas y un piano suave.

- No contiene grabaciones, muestras ni bancos de sonidos.
- No hay audio descargado de Internet ni piezas de terceros.
- No hay voces ni letras.

Los derechos son del propietario del proyecto, igual que el resto del código, y se puede
usar en una aplicación comercial sin pagar licencias a terceros.

| Carpeta | Contenido | Formato |
|---|---|---|
| `music/main_theme.ogg` | Tema de inicio y menús: marimba y campanitas, 96 bpm, do mayor, bucle de 16 compases (40 s) | Ogg Vorbis mono, 32 kHz, q3 (130 KB) |
| `music/coloring_theme.ogg` | Tema para colorear: piano suave y campanitas, 76 bpm, fa mayor, bucle de 16 compases (50,5 s) | Ogg Vorbis mono, 32 kHz, q3 (211 KB) |
| `effects/*.wav` | 27 efectos breves (0,07–1,7 s) con variantes | WAV mono, 16 bits, 22 050 Hz (624 KB en total) |

**Narración:** la app no incluye grabaciones de voz. Usa la voz de texto a voz instalada en el
dispositivo (ver `docs/FASE_SONIDO.md`).

Para regenerar todo, ejecuta desde la raíz (necesita numpy y ffmpeg):

```bash
python3 tools/make_audio.py
```
