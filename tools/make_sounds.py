#!/usr/bin/env python3
"""Genera los efectos de sonido de «Aprender jugando» (WAV mono, 22 050 Hz).

Son tonos sinusoidales suaves creados desde cero por este script: no proceden
de bancos de sonidos ni de Internet, así que pueden distribuirse con la app.
Volumen máximo -12 dBFS, ataques y finales suaves (sin chasquidos) y duración
breve para no resultar estridentes ni repetitivos.

Uso: python3 tools/make_sounds.py
"""

import math
import struct
import wave
from pathlib import Path

RATE = 22050
PEAK = 10 ** (-12 / 20)  # -12 dBFS
OUT = Path(__file__).resolve().parent.parent / "assets" / "sounds"


def note(freq, start, length, gain=1.0, harmonic=0.15):
    return (freq, start, length, gain, harmonic)


def render(notes, total):
    samples = [0.0] * int(total * RATE)
    for freq, start, length, gain, harmonic in notes:
        first = int(start * RATE)
        count = int(length * RATE)
        attack = int(0.008 * RATE)
        for i in range(count):
            t = i / RATE
            # Envolvente: ataque corto y caída exponencial suave.
            env = min(1.0, i / attack) * math.exp(-4.0 * t / length)
            s = math.sin(2 * math.pi * freq * t) + harmonic * math.sin(4 * math.pi * freq * t)
            if first + i < len(samples):
                samples[first + i] += gain * env * s
    # Final suave para evitar chasquidos.
    fade = int(0.02 * RATE)
    for i in range(fade):
        samples[-1 - i] *= i / fade
    top = max(abs(s) for s in samples) or 1.0
    return [s / top * PEAK for s in samples]


def save(name, samples):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in samples))
    print(f"{path.relative_to(OUT.parent.parent)}  {path.stat().st_size // 1024} KB  {len(samples) / RATE:.2f} s")


SOUNDS = {
    # Toque al elegir una opción o girar una tarjeta: muy corto y suave.
    "tap": ([note(880, 0, 0.07, harmonic=0.05)], 0.09),
    # Acierto: dos notas ascendentes (do-mi).
    "correct": ([note(1046.5, 0, 0.16), note(1318.5, 0.12, 0.28)], 0.42),
    # Error: neutro y grave, nada de «zumbidos» de castigo.
    "try_again": ([note(392, 0, 0.18, gain=0.8, harmonic=0.0), note(349.2, 0.14, 0.22, gain=0.8, harmonic=0.0)], 0.38),
    # Elegir un color: un «tic» agudo y muy breve.
    "select": ([note(1318.5, 0, 0.06, gain=0.7, harmonic=0.0)], 0.08),
    # Rellenar una zona: «pop» suave y grave, casi imperceptible.
    "pop": ([note(587.3, 0, 0.09, gain=0.8, harmonic=0.3)], 0.11),
    # Guardado manual: dos notas descendentes suaves (sol-do).
    "saved": ([note(784.0, 0, 0.14, gain=0.8), note(523.3, 0.1, 0.22, gain=0.8)], 0.34),
    # Pegatina nueva: arpegio brillante algo más largo que la celebración.
    "reward": ([
        note(659.3, 0.00, 0.22), note(784.0, 0.10, 0.22), note(1046.5, 0.20, 0.25),
        note(1318.5, 0.32, 0.3), note(1568.0, 0.44, 0.6), note(2093.0, 0.44, 0.6, gain=0.35),
    ], 1.1),
    # Celebración al terminar: arpegio do-mi-sol-do.
    "celebrate": ([
        note(523.3, 0.00, 0.25), note(659.3, 0.12, 0.25), note(784.0, 0.24, 0.3),
        note(1046.5, 0.38, 0.55), note(1318.5, 0.38, 0.55, gain=0.5),
    ], 0.95),
}

if __name__ == "__main__":
    for name, (notes, total) in SOUNDS.items():
        save(name, render(notes, total))
