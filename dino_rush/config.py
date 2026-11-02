"""Constantes, paletas y datos de diseño del juego."""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Ventana y ritmo
# ---------------------------------------------------------------------------
TITLE = "DINO RUSH · Poderes del Pasado"
WIDTH = 1280
HEIGHT = 720
FPS = 60
GROUND_Y = 588
PLAYER_X = 205

PIXELS_PER_METER = 20.0
BASE_SPEED = 380.0
MAX_SPEED = 760.0
SPEED_PER_LEVEL = 20.0

# ---------------------------------------------------------------------------
# Colores de interfaz
# ---------------------------------------------------------------------------
INK = (22, 27, 38)
DEEP_INK = (12, 15, 22)
CREAM = (249, 242, 220)
PAPER = (227, 219, 193)
MUTED = (154, 159, 164)
GOLD = (255, 205, 92)
GOLD_DARK = (170, 119, 42)
TEAL = (77, 228, 184)
CYAN = (97, 218, 255)
CORAL = (255, 111, 97)
PURPLE = (187, 137, 255)
GREEN = (79, 198, 116)
WHITE = (255, 255, 255)

POWER_COLORS = {
    "dash": (92, 224, 255),
    "shield": (113, 209, 255),
    "slow": (197, 147, 255),
    "magnet": (255, 129, 178),
    "x2": (255, 209, 94),
    "wings": (255, 171, 95),
    "phoenix": (255, 107, 74),
}

# ---------------------------------------------------------------------------
# Zonas visuales
# ---------------------------------------------------------------------------
ZONES = [
    {
        "name": "DUNAS DORADAS",
        "tag": "El sol despierta sobre la arena.",
        "sky_top": (57, 51, 99),
        "sky_bottom": (244, 171, 101),
        "sun": (255, 228, 154),
        "sun_glow": (255, 187, 111),
        "far": (121, 78, 100),
        "mid": (174, 97, 89),
        "near": (94, 60, 79),
        "ground": (219, 165, 102),
        "ground_dark": (169, 113, 72),
        "line": (94, 60, 54),
        "accent": (255, 205, 104),
        "cloud": (255, 224, 195),
        "night": False,
        "weather": "dust",
        "decor": "cactus",
    },
    {
        "name": "CAÑÓN CARMESÍ",
        "tag": "El viento ruge entre las rocas.",
        "sky_top": (48, 30, 64),
        "sky_bottom": (207, 86, 69),
        "sun": (255, 198, 108),
        "sun_glow": (255, 139, 87),
        "far": (91, 46, 63),
        "mid": (143, 59, 55),
        "near": (72, 32, 47),
        "ground": (188, 101, 73),
        "ground_dark": (135, 65, 58),
        "line": (63, 28, 37),
        "accent": (255, 157, 82),
        "cloud": (255, 186, 148),
        "night": False,
        "weather": "sand",
        "decor": "rocks",
    },
    {
        "name": "SELVA NOCTURNA",
        "tag": "La noche esconde criaturas antiguas.",
        "sky_top": (6, 10, 30),
        "sky_bottom": (28, 53, 79),
        "sun": (226, 237, 255),
        "sun_glow": (126, 166, 208),
        "far": (22, 35, 58),
        "mid": (20, 55, 58),
        "near": (11, 33, 39),
        "ground": (29, 65, 58),
        "ground_dark": (19, 44, 41),
        "line": (8, 24, 24),
        "accent": (128, 246, 199),
        "cloud": (72, 105, 128),
        "night": True,
        "weather": "fireflies",
        "decor": "ferns",
    },
    {
        "name": "VOLCÁN RUGIENTE",
        "tag": "Sobrevive al corazón de la tierra.",
        "sky_top": (25, 9, 27),
        "sky_bottom": (119, 37, 36),
        "sun": (255, 120, 74),
        "sun_glow": (255, 80, 50),
        "far": (56, 23, 36),
        "mid": (91, 28, 35),
        "near": (39, 15, 24),
        "ground": (70, 36, 38),
        "ground_dark": (43, 22, 26),
        "line": (255, 112, 63),
        "accent": (255, 157, 80),
        "cloud": (116, 55, 52),
        "night": True,
        "weather": "embers",
        "decor": "lava",
    },
]

ZONE_INTROS = [
    "Salta los cactus. El viaje apenas comienza.",
    "Los pterodáctilos han despertado. ¡Agáchate!",
    "La oscuridad trae nuevas sombras. Mantén el ritmo.",
    "El suelo arde. Usa tus poderes y resiste.",
]

LEVEL_TARGET_BASE = 350
LEVEL_TARGET_STEP = 40
LEVEL_TARGET_MAX = 650


def level_target(level: int) -> int:
    """Metros necesarios para superar un nivel."""
    return min(LEVEL_TARGET_MAX, LEVEL_TARGET_BASE + (level - 1) * LEVEL_TARGET_STEP)


def speed_for_level(level: int) -> float:
    return min(MAX_SPEED, BASE_SPEED + (level - 1) * SPEED_PER_LEVEL)


# ---------------------------------------------------------------------------
# Habilidades y mejoras
# ---------------------------------------------------------------------------
# Habilidades activas que consumen la barra de energía.
ACTIVE_ABILITIES = {
    "dash": {
        "name": "DASH",
        "key": "SHIFT",
        "cost": 25,
        "cooldown": 2.2,
        "color": POWER_COLORS["dash"],
        "icon": "dash",
        "desc": "Rompe obstáculos y atraviesa el peligro.",
    },
    "shield": {
        "name": "ESCUDO",
        "key": "E",
        "cost": 45,
        "cooldown": 2.5,
        "color": POWER_COLORS["shield"],
        "icon": "shield",
        "desc": "Una burbuja que absorbe un golpe.",
    },
    "slow": {
        "name": "TIEMPO LENTO",
        "key": "Q",
        "cost": 60,
        "cooldown": 1.0,
        "color": POWER_COLORS["slow"],
        "icon": "slow",
        "desc": "Ralentiza el mundo durante 5 segundos.",
    },
}

# Mejoras que aparecen flotando en el escenario.
POWERUPS = {
    "shield": {
        "name": "ESCUDO",
        "color": POWER_COLORS["shield"],
        "duration": 12.0,
        "desc": "Absorbe el próximo impacto.",
        "icon": "shield",
        "weight": 18,
    },
    "magnet": {
        "name": "IMÁN",
        "color": POWER_COLORS["magnet"],
        "duration": 13.0,
        "desc": "Atrae monedas a tu alrededor.",
        "icon": "magnet",
        "weight": 18,
    },
    "x2": {
        "name": "PUNTOS X2",
        "color": POWER_COLORS["x2"],
        "duration": 12.0,
        "desc": "Duplica los puntos que consigues.",
        "icon": "x2",
        "weight": 17,
    },
    "wings": {
        "name": "ALAS",
        "color": POWER_COLORS["wings"],
        "duration": 16.0,
        "desc": "Desbloquea un doble salto.",
        "icon": "wings",
        "weight": 17,
    },
    "slow": {
        "name": "RELOJ DE ARENA",
        "color": POWER_COLORS["slow"],
        "duration": 5.0,
        "desc": "Ralentiza el tiempo al instante.",
        "icon": "slow",
        "weight": 12,
    },
    "phoenix": {
        "name": "PLUMA FÉNIX",
        "color": POWER_COLORS["phoenix"],
        "duration": 0.0,
        "desc": "Te devuelve a la vida una vez.",
        "icon": "phoenix",
        "weight": 5,
    },
}

# ---------------------------------------------------------------------------
# Guardado
# ---------------------------------------------------------------------------
DEFAULT_SAVE = {
    "high_score": 0,
    "best_distance": 0,
    "best_level": 1,
    "total_coins": 0,
    "games": 0,
    "mute": False,
    "fullscreen": False,
}

SAVE_PATH = Path.home() / ".dino_rush_save.json"

# ---------------------------------------------------------------------------
# Tutorial y textos breves
# ---------------------------------------------------------------------------
TUTORIAL_TIPS = [
    "ESPACIO para saltar. Mantén pulsado para llegar más alto.",
    "ABAJO para agacharte y esquivar a los pterodáctilos.",
    "Recoge monedas para llenar tu energía y usa SHIFT, E o Q.",
]
