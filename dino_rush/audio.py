"""Audio procedural: efectos y música generados sin archivos externos."""
from __future__ import annotations

import array
import math
import random
from typing import Iterable

import pygame

SAMPLE_RATE = 44100

Note = tuple[float, float, float, str, float]  # inicio, frecuencia, duración, onda, volumen


def midi(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


class Audio:
    """Genera y reproduce sonidos chiptune. Falla de forma silenciosa."""

    def __init__(self, muted: bool = False) -> None:
        self.available = False
        self.muted = muted
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music: pygame.mixer.Sound | None = None
        self.music_channel: pygame.mixer.Channel | None = None
        self._rng = random.Random(440)

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.music_channel = pygame.mixer.Channel(0)
            self._build_effects()
            self._build_music()
            self.available = True
        except Exception:
            # El juego funciona igual si no hay dispositivo de sonido.
            self.available = False
            return

        self.set_muted(muted)

    # ------------------------------------------------------------------
    # Síntesis
    # ------------------------------------------------------------------
    def _render(self, notes: Iterable[Note], *, duration: float | None = None, peak: float = 0.7) -> bytes:
        notes = list(notes)
        total = duration or max(start + length for start, _freq, length, _wave, _vol in notes) + 0.03
        count = max(1, int(total * SAMPLE_RATE))
        mix = [0.0] * count

        for start, frequency, length, wave, volume in notes:
            begin = int(start * SAMPLE_RATE)
            length_samples = min(int(length * SAMPLE_RATE), count - begin)
            if length_samples <= 0:
                continue
            phase = 0.0
            for i in range(length_samples):
                t = i / SAMPLE_RATE
                progress = i / max(1, length_samples - 1)
                envelope = min(1.0, i / (SAMPLE_RATE * 0.006))
                envelope *= min(1.0, (length_samples - i) / (SAMPLE_RATE * 0.035))
                phase += 2.0 * math.pi * frequency / SAMPLE_RATE
                if wave == "sine":
                    value = math.sin(phase)
                elif wave == "triangle":
                    value = (2.0 / math.pi) * math.asin(math.sin(phase))
                elif wave == "noise":
                    value = self._rng.uniform(-1.0, 1.0)
                elif wave == "softnoise":
                    value = self._rng.uniform(-1.0, 1.0) * 0.35
                else:
                    value = 1.0 if math.sin(phase) >= 0 else -1.0
                # Las ondas cuadradas pierden agudos desagradables con el tiempo.
                if wave == "square":
                    envelope *= 1.0 - 0.22 * progress
                mix[begin + i] += value * envelope * volume

        max_abs = max(1e-6, max(abs(x) for x in mix))
        scale = peak / max_abs
        pcm = array.array("h")
        for sample in mix:
            pcm.append(int(max(-1.0, min(1.0, sample * scale)) * 32767))
        if pygame.mixer.get_init() and pygame.mixer.get_init()[2] == 2:
            stereo = array.array("h", [0]) * (len(pcm) * 2)
            for i, sample in enumerate(pcm):
                stereo[2 * i] = sample
                stereo[2 * i + 1] = sample
            return stereo.tobytes()
        return pcm.tobytes()

    def _sound(self, notes: Iterable[Note], *, peak: float = 0.35) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(buffer=self._render(notes, peak=peak))

    # ------------------------------------------------------------------
    # Contenido
    # ------------------------------------------------------------------
    def _build_effects(self) -> None:
        self.sounds = {
            "jump": self._sound([(0.0, 300, 0.055, "square", 0.7), (0.045, 440, 0.10, "square", 0.55)], peak=0.32),
            "double_jump": self._sound(
                [(0.0, 520, 0.05, "square", 0.5), (0.04, 720, 0.06, "square", 0.5), (0.09, 940, 0.11, "sine", 0.45)],
                peak=0.3,
            ),
            "land": self._sound([(0.0, 105, 0.07, "triangle", 0.8), (0.015, 70, 0.045, "noise", 0.15)], peak=0.22),
            "coin": self._sound(
                [(0.0, 1050, 0.045, "sine", 0.6), (0.048, 1570, 0.09, "sine", 0.5)], peak=0.3
            ),
            "crystal": self._sound(
                [
                    (0.0, 780, 0.05, "sine", 0.5),
                    (0.045, 1170, 0.05, "sine", 0.45),
                    (0.09, 1560, 0.12, "sine", 0.4),
                ],
                peak=0.3,
            ),
            "power": self._sound(
                [
                    (0.0, midi(64), 0.07, "square", 0.38),
                    (0.065, midi(69), 0.07, "square", 0.38),
                    (0.13, midi(72), 0.07, "square", 0.38),
                    (0.195, midi(76), 0.18, "sine", 0.45),
                ],
                peak=0.34,
            ),
            "dash": self._sound(
                [
                    (0.0, 180, 0.22, "softnoise", 0.75),
                    (0.0, 330, 0.08, "triangle", 0.25),
                    (0.06, 520, 0.12, "triangle", 0.22),
                ],
                peak=0.28,
            ),
            "shield": self._sound(
                [
                    (0.0, midi(60), 0.20, "sine", 0.35),
                    (0.0, midi(67), 0.20, "sine", 0.25),
                    (0.05, midi(72), 0.26, "sine", 0.25),
                ],
                peak=0.28,
            ),
            "slow": self._sound(
                [
                    (0.0, 700, 0.10, "sine", 0.35),
                    (0.09, 520, 0.12, "sine", 0.32),
                    (0.20, 350, 0.18, "triangle", 0.3),
                    (0.33, 240, 0.24, "sine", 0.28),
                ],
                peak=0.28,
            ),
            "hit": self._sound(
                [
                    (0.0, 90, 0.15, "square", 0.5),
                    (0.0, 120, 0.12, "noise", 0.3),
                    (0.08, 60, 0.24, "triangle", 0.5),
                ],
                peak=0.4,
            ),
            "smash": self._sound(
                [
                    (0.0, 150, 0.08, "noise", 0.35),
                    (0.0, 260, 0.09, "square", 0.22),
                    (0.05, 120, 0.13, "triangle", 0.3),
                ],
                peak=0.25,
            ),
            "shield_break": self._sound(
                [
                    (0.0, 620, 0.08, "sine", 0.35),
                    (0.06, 460, 0.10, "sine", 0.3),
                    (0.13, 260, 0.18, "triangle", 0.3),
                    (0.0, 95, 0.10, "noise", 0.18),
                ],
                peak=0.27,
            ),
            "level_up": self._sound(
                [
                    (0.0, midi(62), 0.10, "square", 0.38),
                    (0.09, midi(65), 0.10, "square", 0.38),
                    (0.18, midi(69), 0.10, "square", 0.38),
                    (0.27, midi(74), 0.28, "sine", 0.45),
                    (0.27, midi(69), 0.28, "sine", 0.20),
                ],
                peak=0.36,
            ),
            "game_over": self._sound(
                [
                    (0.0, midi(57), 0.18, "triangle", 0.4),
                    (0.16, midi(53), 0.20, "triangle", 0.4),
                    (0.34, midi(48), 0.32, "triangle", 0.4),
                    (0.58, midi(45), 0.5, "sine", 0.35),
                ],
                peak=0.32,
            ),
            "click": self._sound([(0.0, 620, 0.035, "square", 0.35), (0.025, 820, 0.04, "square", 0.25)], peak=0.2),
            "select": self._sound([(0.0, 440, 0.04, "sine", 0.35), (0.04, 660, 0.08, "sine", 0.3)], peak=0.2),
            "heart": self._sound(
                [(0.0, 523, 0.07, "sine", 0.35), (0.07, 659, 0.07, "sine", 0.35), (0.14, 784, 0.16, "sine", 0.35)],
                peak=0.26,
            ),
            "phoenix": self._sound(
                [
                    (0.0, 220, 0.25, "softnoise", 0.55),
                    (0.05, midi(57), 0.3, "triangle", 0.25),
                    (0.20, midi(64), 0.35, "triangle", 0.3),
                    (0.38, midi(69), 0.55, "sine", 0.4),
                ],
                peak=0.32,
            ),
            "pause": self._sound([(0.0, 380, 0.06, "sine", 0.3), (0.06, 300, 0.08, "sine", 0.25)], peak=0.2),
        }

    def _build_music(self) -> None:
        """Un bucle suave de arpegio y bajo con sabor desértico."""
        beat = 60.0 / 104.0
        loop_beats = 16
        duration = beat * loop_beats
        notes: list[Note] = []

        # Acordes: Am - F - C - G, con un arpegio de corcheas.
        chords = [
            (midi(57), [midi(69), midi(72), midi(76), midi(72)]),
            (midi(53), [midi(65), midi(69), midi(72), midi(69)]),
            (midi(48), [midi(60), midi(64), midi(67), midi(64)]),
            (midi(55), [midi(62), midi(67), midi(71), midi(67)]),
        ]
        for bar, (bass_note, arp_notes) in enumerate(chords):
            bar_start = bar * 4 * beat
            notes.append((bar_start, bass_note / 2, beat * 3.4, "triangle", 0.055))
            notes.append((bar_start + beat * 2, bass_note, beat * 1.5, "triangle", 0.035))
            for step in range(8):
                start = bar_start + step * beat / 2
                freq = arp_notes[step % len(arp_notes)]
                # Las notas altas del arpegio suenan más suaves.
                notes.append((start, freq, beat * 0.42, "sine", 0.028 if step % 2 else 0.04))
            for step in range(4):
                start = bar_start + step * beat
                # Pulso grave sutil.
                notes.append((start, 58, 0.11, "sine", 0.05))
                if step % 2 == 0:
                    notes.append((start + beat / 2, 0, 0.055, "softnoise", 0.017))

        self.music = pygame.mixer.Sound(buffer=self._render(notes, duration=duration, peak=0.32))

    # ------------------------------------------------------------------
    # Reproducción
    # ------------------------------------------------------------------
    def play_music(self) -> None:
        if not self.available or self.music is None or self.music_channel is None:
            return
        try:
            if not self.music_channel.get_busy():
                self.music_channel.play(self.music, loops=-1, fade_ms=900)
                self.music_channel.set_volume(0.0 if self.muted else 0.23)
        except Exception:
            pass

    def play(self, name: str) -> None:
        if not self.available or self.muted:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        if not self.available:
            return
        try:
            if self.music_channel is not None:
                self.music_channel.set_volume(0.0 if muted else 0.23)
        except Exception:
            pass

    def toggle_mute(self) -> bool:
        self.set_muted(not self.muted)
        return self.muted
