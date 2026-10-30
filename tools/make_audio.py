#!/usr/bin/env python3
"""Genera TODO el audio de Pequeños Artistas: efectos (WAV) y música (Ogg Vorbis).

Todo se sintetiza desde cero en este script (marimba, xilófono, campanitas y
piano suave hechos con sumas de senoides): no hay muestras, bancos de sonidos ni
archivos de Internet, así que el audio es original y puede distribuirse con la
app sin licencias de terceros.

Criterios:
- Efectos breves, a -12 dBFS como máximo, sin chasquidos, con 2-3 variantes
  para que no suenen siempre iguales.
- Música instrumental tranquila (sin voces), dinámica constante y bucle exacto:
  las colas de las notas del final se suman al principio, así el salto del
  final al inicio no se oye.

Uso (desde la raíz): python3 tools/make_audio.py   (necesita numpy y ffmpeg)
"""

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EFFECTS = ROOT / "assets" / "audio" / "effects"
MUSIC = ROOT / "assets" / "audio" / "music"
FX_RATE = 22050
MUSIC_RATE = 32000

NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    """'A4' -> 440 Hz."""
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[pitch] + 12 * (octave + 1) - 69) / 12)


# ---------------------------------------------------------------- instrumentos
def _voice(freq, dur, rate, partials, attack=0.004):
    """Suma de parciales (ratio, amplitud, caída por segundo) con ataque suave."""
    t = np.arange(int(dur * rate)) / rate
    out = np.zeros_like(t)
    for ratio, amp, decay in partials:
        f = freq * ratio
        if f >= rate / 2:
            continue
        out += amp * np.sin(2 * np.pi * f * t) * np.exp(-decay * t)
    env = np.minimum(1.0, t / attack)
    # Final suave para que ninguna nota acabe en seco.
    tail = min(len(t), int(0.03 * rate))
    env[-tail:] *= np.linspace(1, 0, tail)
    return out * env


def marimba(freq, dur, rate):
    k = 2.2 + freq / 400  # las notas agudas se apagan antes
    return _voice(freq, dur, rate, [(1, 1.0, k), (3.93, 0.18, k * 4), (9.2, 0.05, k * 9)])


def xylophone(freq, dur, rate):
    k = 5 + freq / 300
    return _voice(freq, dur, rate, [(1, 1.0, k), (3.0, 0.25, k * 2.5), (6.2, 0.08, k * 5)], attack=0.002)


def bell(freq, dur, rate):
    return _voice(freq, dur, rate, [(1, 1.0, 2.2), (2.76, 0.45, 3.5), (5.40, 0.22, 5.5), (8.93, 0.10, 8)], attack=0.003)


def piano(freq, dur, rate):
    k = 1.4 + freq / 900
    partials = [(n, 1 / n ** 1.8, k * (1 + 0.35 * n)) for n in range(1, 7)]
    return _voice(freq, dur, rate, partials, attack=0.008)


def soft_tick(freq, dur, rate):
    return _voice(freq, dur, rate, [(1, 1.0, 45), (2.0, 0.2, 70)], attack=0.002)


# ---------------------------------------------------------------- efectos
def render(events, total, rate=FX_RATE, peak_db=-12):
    """events: (instrumento, nota o Hz, inicio s, duración s, ganancia)."""
    buf = np.zeros(int(total * rate))
    for inst, note, start, dur, gain in events:
        f = hz(note) if isinstance(note, str) else note
        v = inst(f, dur, rate) * gain
        a = int(start * rate)
        b = min(len(buf), a + len(v))
        buf[a:b] += v[: b - a]
    fade = int(0.015 * rate)
    buf[-fade:] *= np.linspace(1, 0, fade)
    return buf / (np.abs(buf).max() or 1) * 10 ** (peak_db / 20)


def save_wav(path, samples, rate):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data)
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB  {len(samples) / rate:.2f} s")


M, X, B, P, T = marimba, xylophone, bell, piano, soft_tick
PENTATONIC = ["C5", "D5", "E5", "G5", "A5", "C6", "D6", "E6"]

EFFECTS_SPEC = {
    # Pulsar un botón: clic suave (dos variantes de altura).
    "click_1": ([(T, 1400, 0, 0.05, 1)], 0.07),
    "click_2": ([(T, 1250, 0, 0.05, 1)], 0.07),
    # Elegir algo dentro de una herramienta (borrador): tic muy breve.
    "select_1": ([(X, "E6", 0, 0.08, 1)], 0.1),
    # Seleccionar una categoría: tres notas alegres de marimba.
    "category_1": ([(M, "C5", 0, 0.2, 1), (M, "E5", 0.07, 0.2, 1), (M, "G5", 0.14, 0.35, 1)], 0.5),
    "category_2": ([(M, "D5", 0, 0.2, 1), (M, "G5", 0.07, 0.2, 1), (M, "A5", 0.14, 0.35, 1)], 0.5),
    # Abrir un dibujo: campanita.
    "open_1": ([(B, "A5", 0, 0.7, 1), (B, "E6", 0.06, 0.6, 0.5)], 0.75),
    "open_2": ([(B, "G5", 0, 0.7, 1), (B, "D6", 0.06, 0.6, 0.5)], 0.75),
    # Colorear una zona: «pop» suave de marimba (tres alturas).
    "fill_1": ([(M, "G4", 0, 0.16, 1)], 0.18),
    "fill_2": ([(M, "A4", 0, 0.16, 1)], 0.18),
    "fill_3": ([(M, "C5", 0, 0.16, 1)], 0.18),
    # Guardar: dos notas que suben y una campanita.
    "saved_1": ([(M, "G4", 0, 0.2, 1), (M, "C5", 0.1, 0.3, 1), (B, "C6", 0.16, 0.5, 0.35)], 0.6),
    # Respuesta correcta: campanitas alegres.
    "correct_1": ([(B, "C6", 0, 0.45, 1), (B, "E6", 0.09, 0.45, 0.9), (B, "G6", 0.18, 0.6, 0.8)], 0.8),
    "correct_2": ([(B, "D6", 0, 0.45, 1), (B, "G6", 0.09, 0.45, 0.9), (B, "B6", 0.18, 0.6, 0.7)], 0.8),
    # Respuesta incorrecta: neutro y amable (dos notas graves que bajan un poco).
    "try_again_1": ([(M, "E4", 0, 0.25, 0.9), (M, "D4", 0.16, 0.3, 0.8)], 0.5),
    "try_again_2": ([(M, "G4", 0, 0.25, 0.9), (M, "E4", 0.16, 0.3, 0.8)], 0.5),
    # Completar un juego o un dibujo: pequeña celebración.
    "celebrate_1": ([(M, "C5", 0, 0.25, 1), (M, "E5", 0.11, 0.25, 1), (M, "G5", 0.22, 0.25, 1),
                     (M, "C6", 0.33, 0.6, 1), (B, "E6", 0.33, 0.8, 0.45)], 1.15),
    "celebrate_2": ([(M, "D5", 0, 0.25, 1), (M, "F#5", 0.11, 0.25, 1), (M, "A5", 0.22, 0.25, 1),
                     (M, "D6", 0.33, 0.6, 1), (B, "F#6", 0.33, 0.8, 0.45)], 1.15),
    # Obtener estrellas: brillo mágico (glissando rápido de campanitas).
    "star_1": ([(B, n, i * 0.045, 0.5, 0.75) for i, n in enumerate(["C6", "E6", "G6", "C7", "E7"])], 0.8),
    # Desbloquear una pegatina: celebración especial más larga.
    "reward_1": ([(M, "C5", 0.00, 0.3, 1), (M, "E5", 0.12, 0.3, 1), (M, "G5", 0.24, 0.3, 1),
                  (M, "C6", 0.36, 0.3, 1), (M, "E6", 0.52, 0.9, 1), (B, "G6", 0.52, 1.0, 0.5),
                  (B, "C7", 0.70, 0.9, 0.35), (M, "C4", 0.52, 0.9, 0.5)], 1.7),
}
# Elegir un color: nota corta de xilófono, una por color (escala pentatónica,
# así cualquier secuencia de colores suena bien).
for i, n in enumerate(PENTATONIC, start=1):
    EFFECTS_SPEC[f"color_{i}"] = ([(X, n, 0, 0.22, 1)], 0.25)


# ---------------------------------------------------------------- música
def render_loop(events, beats, bpm, rate=MUSIC_RATE, peak_db=-7):
    """Bucle exacto de [beats] tiempos: lo que sobra al final vuelve al principio."""
    spb = 60 / bpm
    length = int(round(beats * spb * rate))
    buf = np.zeros(length + rate * 4)
    for inst, note, beat, dur_beats, gain in events:
        v = inst(hz(note), dur_beats * spb + 0.6, rate) * gain
        a = int(round(beat * spb * rate))
        buf[a:a + len(v)] += v
    loop = buf[:length].copy()
    loop[: len(buf) - length] += buf[length:]  # colas al principio: sin corte
    return loop / np.abs(loop).max() * 10 ** (peak_db / 20)


def chord_events(chords, inst, beat_offset, octave_notes, gain, pattern):
    """Acompañamiento: cada acorde dura 4 tiempos y se toca con un patrón."""
    ev = []
    for bar, chord in enumerate(chords):
        notes = octave_notes[chord]
        for step, (beat, idx, dur) in enumerate(pattern):
            ev.append((inst, notes[idx % len(notes)], beat_offset + bar * 4 + beat, dur, gain))
    return ev


def main_theme():
    """Pantalla principal y menús: alegre y tranquila (marimba, 96 bpm, do mayor)."""
    chords = ["C", "Am", "F", "G", "C", "Am", "F", "G", "F", "G", "Em", "Am", "F", "G", "C", "C"]
    voicing = {"C": ["C3", "G3", "C4", "E4"], "Am": ["A2", "E3", "A3", "C4"], "F": ["F2", "C3", "F3", "A3"],
               "G": ["G2", "D3", "G3", "B3"], "Em": ["E3", "B3", "E4", "G4"]}
    # Bajo suave en el 1 y el 3; arpegio de marimba en corcheas tranquilas.
    ev = chord_events(chords, M, 0, voicing, 0.55, [(0, 0, 1.6), (2, 1, 1.6)])
    ev += chord_events(chords, M, 0, voicing, 0.28, [(1, 2, 0.6), (1.5, 3, 0.6), (3, 2, 0.6), (3.5, 3, 0.6)])
    melody = [
        # (tiempo, nota, duración) en 16 compases; frases de 4 compases con respiraciones.
        (0, "E5", 1), (1, "G5", 1), (2, "A5", 1.5), (3.5, "G5", 0.5), (4, "E5", 2), (6, "D5", 2),
        (8, "C5", 1), (9, "D5", 1), (10, "E5", 1), (11, "G5", 1), (12, "D5", 3),
        (16, "E5", 1), (17, "G5", 1), (18, "A5", 1.5), (19.5, "C6", 0.5), (20, "A5", 2), (22, "G5", 2),
        (24, "A5", 1), (25, "G5", 1), (26, "E5", 1), (27, "D5", 1), (28, "C5", 3),
        (32, "A5", 1), (33, "C6", 1), (34, "A5", 2), (36, "B5", 1), (37, "D6", 1), (38, "B5", 2),
        (40, "G5", 1), (41, "B5", 1), (42, "G5", 2), (44, "A5", 1), (45, "E5", 1), (46, "C5", 2),
        (48, "A5", 1), (49, "G5", 1), (50, "E5", 1), (51, "G5", 1), (52, "D5", 1), (53, "E5", 1), (54, "G5", 2),
        (56, "E5", 1), (57, "D5", 1), (58, "C5", 4),
    ]
    ev += [(M, n, b, d, 0.8) for b, n, d in melody]
    # Campanitas ocasionales que «brillan» al final de cada frase.
    ev += [(B, n, b, 2, 0.16) for b, n in [(7, "G6"), (15, "D6"), (23, "C7"), (31, "E6"), (47, "E6"), (62, "C7")]]
    return render_loop(ev, 64, 96)


def coloring_theme():
    """Colorear: más lenta y suave (piano y campanitas, 76 bpm, fa mayor)."""
    chords = ["F", "Dm", "Bb", "C", "F", "Dm", "Bb", "C", "Bb", "C", "Am", "Dm", "Bb", "C", "F", "F"]
    voicing = {"F": ["F3", "C4", "F4", "A4"], "Dm": ["D3", "A3", "D4", "F4"], "Bb": ["A#2", "F3", "A#3", "D4"],
               "C": ["C3", "G3", "C4", "E4"], "Am": ["A2", "E3", "A3", "C4"]}
    ev = chord_events(chords, P, 0, voicing, 0.45, [(0, 0, 3.5)])
    ev += chord_events(chords, P, 0, voicing, 0.22, [(1, 1, 1), (2, 2, 1), (3, 3, 1)])
    melody = [
        (0, "A5", 2), (2, "C6", 2), (4, "A5", 2), (6, "G5", 2), (8, "F5", 2), (10, "G5", 1), (11, "A5", 1), (12, "G5", 4),
        (16, "A5", 2), (18, "C6", 2), (20, "D6", 2), (22, "C6", 2), (24, "A#5", 2), (26, "A5", 2), (28, "G5", 4),
        (32, "F5", 2), (34, "G5", 2), (36, "A5", 2), (38, "C6", 2), (40, "A5", 2), (42, "G5", 2), (44, "F5", 2), (46, "D5", 2),
        (48, "F5", 2), (50, "G5", 2), (52, "A5", 2), (54, "G5", 2), (56, "F5", 6),
    ]
    ev += [(B, n, b, d, 0.42) for b, n, d in melody]
    return render_loop(ev, 64, 76, peak_db=-8)


def save_ogg(path, samples, rate):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        save_wav_raw(tmp.name, samples, rate)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name, "-c:a", "libvorbis",
                        "-q:a", "3", "-ac", "1", str(path)], check=True)
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB  {len(samples) / rate:.1f} s (bucle)")


def save_wav_raw(name, samples, rate):
    data = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(name, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data)


if __name__ == "__main__":
    for name, (events, total) in EFFECTS_SPEC.items():
        save_wav(EFFECTS / f"{name}.wav", render(events, total), FX_RATE)
    save_ogg(MUSIC / "main_theme.ogg", main_theme(), MUSIC_RATE)
    save_ogg(MUSIC / "coloring_theme.ogg", coloring_theme(), MUSIC_RATE)
