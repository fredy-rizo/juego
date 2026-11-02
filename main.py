#!/usr/bin/env python3
"""DINO RUSH: Poderes del Pasado.

Un runner arcade inspirado en el dinosaurio de Chrome, con zonas,
habilidades, mejoras, récords y sonido generado por código.

Ejecuta: python3 main.py
"""
from __future__ import annotations

import os


def main() -> int:
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

    try:
        import pygame
    except ModuleNotFoundError:
        print(
            "Falta pygame-ce.\n\n"
            "Instálalo con:\n"
            "    python3 -m pip install -r requirements.txt\n\n"
            "Si tu sistema bloquea la instalación global, crea un entorno virtual:\n"
            "    python3 -m venv .venv\n"
            "    . .venv/bin/activate\n"
            "    pip install -r requirements.txt\n"
        )
        return 1

    try:
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        from dino_rush.game import Game

        Game().run()
    except pygame.error as error:
        print(f"No se pudo iniciar la ventana o el audio: {error}")
        print("Comprueba que haya un entorno gráfico disponible.")
        return 1
    except KeyboardInterrupt:
        print("\nJuego cerrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
