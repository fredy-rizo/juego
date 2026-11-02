"""Arte procedural: dinosaurio, obstáculos, iconos y efectos."""
from __future__ import annotations

import math

import pygame

from .config import (
    CORAL,
    CREAM,
    CYAN,
    GOLD,
    POWER_COLORS,
    TEAL,
    WHITE,
    ZONES,
)
from .utils import draw_text

# ---------------------------------------------------------------------------
# Herramientas de pixel art
# ---------------------------------------------------------------------------


def _outlined(low: pygame.Surface, color: tuple[int, int, int], scale: int, pad: int = 1) -> pygame.Surface:
    """Añade un contorno de píxel y escala sin suavizado."""
    width, height = low.get_size()
    result = pygame.Surface((width + pad * 2, height + pad * 2), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(low)
    silhouette = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    for dx in (-pad, 0, pad):
        for dy in (-pad, 0, pad):
            if dx == 0 and dy == 0:
                continue
            result.blit(silhouette, (pad + dx, pad + dy))
    result.blit(low, (pad, pad))
    return pygame.transform.scale(result, (result.get_width() * scale, result.get_height() * scale))


def _low_surface(width: int, height: int) -> pygame.Surface:
    return pygame.Surface((width, height), pygame.SRCALPHA)


def _r(surface: pygame.Surface, color: tuple[int, ...], x: int, y: int, w: int, h: int) -> None:
    pygame.draw.rect(surface, color, (x, y, w, h))


_GLOW_CACHE: dict[tuple, pygame.Surface] = {}


def glow_surface(radius: int, color: tuple[int, int, int], intensity: int = 110) -> pygame.Surface:
    """Halo suave reutilizable con un degradado radial real."""
    key = (radius, color, intensity)
    if key not in _GLOW_CACHE:
        size = radius * 2 + 8
        base_size = 96
        base = pygame.Surface((base_size, base_size), pygame.SRCALPHA)
        center = (base_size - 1) / 2
        max_distance = base_size / 2
        for py in range(base_size):
            for px in range(base_size):
                distance = math.hypot(px - center, py - center) / max_distance
                if distance >= 1.0:
                    continue
                alpha = int(intensity * (1.0 - distance) ** 2.1)
                if alpha > 0:
                    base.set_at((px, py), (*color, alpha))
        surface = pygame.transform.smoothscale(base, (size, size))
        _GLOW_CACHE[key] = surface
    return _GLOW_CACHE[key]


_ADDITIVE_GLOW_CACHE: dict[tuple, pygame.Surface] = {}


def additive_glow_surface(radius: int, color: tuple[int, int, int], intensity: int = 110) -> pygame.Surface:
    """Halo para mezcla aditiva con el color ya multiplicado por su opacidad.

    BLEND_ADD ignora el canal alfa, así que el degradado debe guardarse en RGB.
    """
    key = (radius, color, intensity)
    if key not in _ADDITIVE_GLOW_CACHE:
        size = radius * 2 + 8
        base_size = 96
        base = pygame.Surface((base_size, base_size))
        base.fill((0, 0, 0))
        center = (base_size - 1) / 2
        max_distance = base_size / 2
        for py in range(base_size):
            for px in range(base_size):
                distance = math.hypot(px - center, py - center) / max_distance
                if distance >= 1.0:
                    continue
                factor = (intensity / 255.0) * (1.0 - distance) ** 2.1
                base.set_at(
                    (px, py),
                    (
                        int(color[0] * factor),
                        int(color[1] * factor),
                        int(color[2] * factor),
                    ),
                )
        _ADDITIVE_GLOW_CACHE[key] = pygame.transform.smoothscale(base, (size, size))
    return _ADDITIVE_GLOW_CACHE[key]


def draw_glow(
    surface: pygame.Surface,
    center: tuple[float, float],
    radius: int,
    color: tuple[int, int, int],
    *,
    intensity: int = 110,
) -> None:
    halo = additive_glow_surface(radius, color, intensity)
    surface.blit(halo, halo.get_rect(center=(round(center[0]), round(center[1]))), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------
# Dinosaurio
# ---------------------------------------------------------------------------
BODY_DARK = (26, 66, 59)
BODY = (68, 200, 143)
BODY_LIGHT = (134, 238, 182)
BODY_SHADE = (37, 139, 104)
BELLY = (246, 218, 160)
SCARF = (239, 87, 75)
SCARF_DARK = (171, 51, 55)
EYE = (15, 24, 28)
CLAW = (237, 225, 189)


class DinoArt:
    """Frames pre-renderizados del protagonista."""

    def __init__(self) -> None:
        self.run: list[pygame.Surface] = []
        self.air: list[pygame.Surface] = []
        self.duck: list[pygame.Surface] = []
        self.hurt: list[pygame.Surface] = []
        self._build()

    def _body(self) -> pygame.Surface:
        s = _low_surface(24, 24)
        # Cola
        _r(s, BODY_SHADE, 1, 13, 6, 3)
        _r(s, BODY, 2, 12, 5, 2)
        _r(s, BODY_DARK, 1, 15, 6, 1)
        # Cuerpo
        _r(s, BODY_SHADE, 5, 11, 10, 8)
        _r(s, BODY, 6, 11, 8, 7)
        _r(s, BODY_LIGHT, 7, 11, 4, 1)
        _r(s, BELLY, 8, 16, 6, 2)
        _r(s, BODY_DARK, 6, 18, 8, 1)
        # Cresta / espinas
        _r(s, SCARF_DARK, 7, 10, 1, 1)
        _r(s, GOLD, 9, 9, 1, 2)
        _r(s, SCARF_DARK, 11, 10, 1, 1)
        # Cuello y cabeza
        _r(s, BODY_SHADE, 12, 7, 7, 8)
        _r(s, BODY, 13, 5, 6, 8)
        _r(s, BODY_LIGHT, 14, 5, 4, 1)
        _r(s, BODY_SHADE, 15, 4, 4, 1)
        # Hocico
        _r(s, BODY_SHADE, 19, 8, 4, 4)
        _r(s, BODY, 19, 8, 3, 3)
        _r(s, BELLY, 19, 11, 3, 1)
        _r(s, EYE, 21, 9, 1, 1)
        # Ojo
        _r(s, WHITE, 17, 7, 2, 2)
        _r(s, EYE, 18, 7, 1, 1)
        # Sonrisa
        _r(s, EYE, 19, 11, 2, 1)
        # Brazo
        _r(s, BODY_SHADE, 14, 14, 3, 2)
        _r(s, BODY, 15, 14, 2, 1)
        _r(s, CLAW, 17, 14, 1, 1)
        # Bufanda
        _r(s, SCARF_DARK, 12, 10, 6, 2)
        _r(s, SCARF, 12, 10, 6, 1)
        _r(s, SCARF, 9, 11, 4, 1)
        _r(s, SCARF_DARK, 9, 12, 4, 1)
        return s

    def _add_legs(self, s: pygame.Surface, pose: int) -> None:
        # Cuatro poses de zancada. Cada pierna tiene una parte y un pie.
        back_x, front_x, back_lift, front_lift = [
            (6, 13, 0, 0),
            (7, 12, 1, 1),
            (6, 13, 0, 0),
            (5, 14, 1, 1),
        ][pose % 4]
        back_y = 18
        front_y = 18
        _r(s, BODY_SHADE, back_x, back_y, 2, 5 - back_lift)
        _r(s, BODY_DARK, back_x - 1, 22 - back_lift, 4, 1)
        _r(s, BODY_SHADE, front_x, front_y, 2, 5 - front_lift)
        _r(s, BODY_DARK, front_x, 22 - front_lift, 4, 1)

    def _run_sprite(self, pose: int) -> pygame.Surface:
        base = self._body()
        scarfx = [0, 1, 0, -1][pose % 4]
        _r(base, SCARF, 7 + scarfx, 12, 3, 1)
        self._add_legs(base, pose)
        return _outlined(base, BODY_DARK, 3)

    def _air_sprite(self, pose: int) -> pygame.Surface:
        base = self._body()
        # Patas recogidas en el salto.
        _r(base, BODY_SHADE, 8, 18, 4, 2)
        _r(base, BODY_DARK, 8, 20, 4, 1)
        _r(base, BODY_SHADE, 12, 18, 2, 2)
        _r(base, CLAW, 14, 18, 1, 1)
        _r(base, SCARF, 7, 11, 4, 1)
        _r(base, SCARF_DARK, 6, 12 + pose, 4, 1)
        return _outlined(base, BODY_DARK, 3)

    def _duck_sprite(self, pose: int) -> pygame.Surface:
        s = _low_surface(30, 16)
        # Cola
        _r(s, BODY_SHADE, 1, 6, 7, 3)
        _r(s, BODY, 2, 5, 6, 2)
        _r(s, BODY_DARK, 1, 9, 8, 1)
        # Cuerpo agachado
        _r(s, BODY_SHADE, 7, 7, 13, 7)
        _r(s, BODY, 8, 7, 11, 6)
        _r(s, BODY_LIGHT, 9, 7, 5, 1)
        _r(s, BELLY, 11, 12, 7, 2)
        # Cuello y cabeza baja
        _r(s, BODY_SHADE, 18, 5, 6, 7)
        _r(s, BODY, 19, 4, 5, 7)
        _r(s, BODY_SHADE, 22, 3, 3, 1)
        _r(s, BODY_SHADE, 24, 7, 4, 4)
        _r(s, BODY, 24, 7, 3, 3)
        _r(s, BELLY, 24, 10, 3, 1)
        _r(s, WHITE, 23, 5, 2, 2)
        _r(s, EYE, 24, 5, 1, 1)
        _r(s, EYE, 22, 10, 2, 1)
        # Bufanda
        _r(s, SCARF_DARK, 18, 9, 6, 2)
        _r(s, SCARF, 18, 9, 6, 1)
        _r(s, SCARF, 14 + pose, 10, 5, 1)
        # Patas en movimiento
        offset = 1 if pose else 0
        _r(s, BODY_SHADE, 9, 14, 3, 2)
        _r(s, BODY_DARK, 8 + offset, 15, 4, 1)
        _r(s, BODY_SHADE, 17, 14, 3, 2)
        _r(s, BODY_DARK, 16 + offset, 15, 4, 1)
        return _outlined(s, BODY_DARK, 3)

    def _hurt_sprite(self) -> pygame.Surface:
        base = self._body()
        _r(base, WHITE, 17, 7, 2, 2)
        _r(base, EYE, 17, 7, 1, 1)
        _r(base, EYE, 18, 8, 1, 1)
        _r(base, EYE, 21, 9, 1, 1)
        _r(base, EYE, 20, 9, 1, 1)
        self._add_legs(base, 0)
        return _outlined(base, BODY_DARK, 3)

    def _build(self) -> None:
        self.run = [self._run_sprite(i) for i in range(4)]
        self.air = [self._air_sprite(i) for i in range(2)]
        self.duck = [self._duck_sprite(i) for i in range(2)]
        self.hurt = [self._hurt_sprite()]


# ---------------------------------------------------------------------------
# Obstáculos
# ---------------------------------------------------------------------------
_CACTUS_CACHE: dict[tuple[int, str], pygame.Surface] = {}
_ROCK_CACHE: dict[int, pygame.Surface] = {}
_PTERO_CACHE: dict[tuple[int, int], pygame.Surface] = {}


def cactus_surface(zone: int, tall: bool = False) -> pygame.Surface:
    key = (zone, "tall" if tall else "small")
    if key in _CACTUS_CACHE:
        return _CACTUS_CACHE[key]
    if zone in (2,):
        body, shade, light, outline = (44, 145, 110), (22, 91, 76), (91, 213, 164), (9, 43, 37)
    elif zone == 3:
        body, shade, light, outline = (126, 121, 72), (70, 70, 43), (189, 177, 96), (35, 27, 24)
    else:
        body, shade, light, outline = (60, 147, 101), (29, 83, 63), (110, 203, 138), (18, 48, 37)
    flower = ZONES[zone]["accent"]
    if tall:
        s = _low_surface(16, 29)
        _r(s, shade, 4, 4, 7, 24)
        _r(s, body, 5, 4, 5, 23)
        _r(s, light, 6, 4, 2, 20)
        _r(s, shade, 6, 27, 3, 1)
        # Brazo izquierdo
        _r(s, shade, 1, 13, 5, 3)
        _r(s, body, 1, 13, 4, 2)
        _r(s, shade, 1, 8, 3, 6)
        _r(s, body, 1, 8, 2, 5)
        # Brazo derecho
        _r(s, shade, 9, 10, 5, 3)
        _r(s, body, 10, 10, 4, 2)
        _r(s, shade, 12, 6, 3, 5)
        _r(s, body, 12, 6, 2, 4)
        # Espinas
        for x, y in ((3, 7), (13, 5), (3, 16), (10, 13), (2, 21)):
            _r(s, light, x, y, 1, 1)
        # Flor
        _r(s, flower, 7, 1, 2, 2)
        _r(s, CREAM, 8, 1, 1, 1)
        _r(s, body, 6, 2, 1, 1)
        _r(s, body, 9, 2, 1, 1)
    else:
        s = _low_surface(16, 22)
        _r(s, shade, 6, 4, 5, 17)
        _r(s, body, 7, 4, 3, 16)
        _r(s, light, 7, 5, 1, 11)
        _r(s, shade, 3, 10, 4, 3)
        _r(s, body, 3, 10, 3, 2)
        _r(s, shade, 2, 7, 3, 4)
        _r(s, body, 2, 7, 2, 3)
        _r(s, shade, 10, 8, 4, 3)
        _r(s, body, 10, 8, 3, 2)
        _r(s, shade, 12, 4, 3, 5)
        _r(s, body, 12, 4, 2, 4)
        _r(s, flower, 7, 1, 2, 2)
        _r(s, CREAM, 8, 1, 1, 1)
        _r(s, light, 4, 12, 1, 1)
        _r(s, light, 12, 9, 1, 1)
    result = _outlined(s, outline, 3)
    _CACTUS_CACHE[key] = result
    return result


def rock_surface(zone: int) -> pygame.Surface:
    if zone in _ROCK_CACHE:
        return _ROCK_CACHE[zone]
    if zone == 2:
        dark, mid, light = (23, 39, 42), (55, 79, 79), (101, 132, 120)
    elif zone == 3:
        dark, mid, light = (44, 22, 27), (88, 45, 44), (139, 73, 52)
    else:
        dark, mid, light = (65, 47, 48), (118, 88, 76), (178, 137, 105)
    s = _low_surface(24, 14)
    pygame.draw.polygon(s, mid, [(2, 13), (1, 9), (5, 3), (12, 2), (19, 5), (23, 11), (22, 13)])
    pygame.draw.polygon(s, light, [(4, 8), (7, 4), (12, 3), (16, 4), (12, 8), (7, 10)])
    pygame.draw.polygon(s, dark, [(13, 8), (19, 6), (22, 12), (18, 13), (14, 12)])
    pygame.draw.polygon(s, dark, [(2, 10), (6, 9), (10, 13), (4, 13)])
    for x, y in ((8, 6), (15, 10), (18, 8), (5, 11)):
        _r(s, CREAM, x, y, 1, 1)
    result = _outlined(s, (25, 23, 28), 3)
    _ROCK_CACHE[zone] = result
    return result


def ptero_surface(zone: int, frame: int) -> pygame.Surface:
    key = (zone, frame % 4)
    if key in _PTERO_CACHE:
        return _PTERO_CACHE[key]

    if zone == 2:
        outline, body, shade, wing, light = (13, 23, 36), (74, 91, 125), (42, 51, 78), (73, 115, 129), (154, 206, 199)
    elif zone == 3:
        outline, body, shade, wing, light = (35, 13, 20), (114, 48, 52), (73, 27, 38), (151, 72, 62), (241, 135, 95)
    else:
        outline, body, shade, wing, light = (43, 27, 44), (117, 70, 99), (76, 41, 67), (154, 91, 113), (244, 185, 172)

    s = _low_surface(31, 20)
    wing_y = [1, 4, 8, 5][frame % 4]
    tip_x = [1, 0, 3, 2][frame % 4]
    # Ala trasera
    pygame.draw.polygon(s, shade, [(12, 9), (tip_x, wing_y + 2), (5, 11), (11, 12)])
    # Cuerpo
    pygame.draw.polygon(s, body, [(10, 10), (14, 7), (20, 8), (18, 13), (12, 13)])
    _r(s, light, 13, 8, 4, 1)
    _r(s, shade, 11, 12, 6, 1)
    # Cuello y cabeza
    _r(s, shade, 18, 7, 5, 4)
    _r(s, body, 19, 7, 4, 3)
    _r(s, body, 22, 6, 3, 3)
    # Pico
    pygame.draw.polygon(s, GOLD, [(25, 7), (30, 8), (25, 9)])
    _r(s, outline, 25, 8, 2, 1)
    # Cresta
    pygame.draw.polygon(s, light, [(21, 6), (20, 3), (24, 5), (25, 6)])
    # Ojo
    _r(s, CREAM, 23, 6, 1, 1)
    _r(s, outline, 23, 6, 1, 1)
    # Ala delantera
    pygame.draw.polygon(s, wing, [(13, 9), (tip_x + 1, wing_y + 1), (7, 8), (4, 11), (12, 12)])
    pygame.draw.polygon(s, light, [(13, 9), (tip_x + 2, wing_y + 2), (8, 9), (12, 11)])
    # Patas
    _r(s, shade, 13, 13, 2, 2)
    _r(s, shade, 16, 13, 2, 2)
    _r(s, outline, 12, 15, 3, 1)
    _r(s, outline, 16, 15, 3, 1)
    result = _outlined(s, outline, 3)
    # El obstáculo vuela hacia la izquierda, en dirección al jugador.
    result = pygame.transform.flip(result, True, False)
    _PTERO_CACHE[key] = result
    return result


# ---------------------------------------------------------------------------
# Iconos
# ---------------------------------------------------------------------------


def draw_icon(
    surface: pygame.Surface,
    kind: str,
    center: tuple[float, float],
    size: float,
    color: tuple[int, int, int],
    *,
    secondary: tuple[int, int, int] = CREAM,
) -> None:
    """Iconos vectoriales reutilizados por HUD, menús y orbes."""
    x, y = center
    s = size
    if kind == "heart":
        from .utils import draw_heart

        draw_heart(surface, center, int(size), color=color)
    elif kind == "shield":
        points = [
            (x, y - s * 0.48),
            (x + s * 0.44, y - s * 0.28),
            (x + s * 0.38, y + s * 0.12),
            (x, y + s * 0.5),
            (x - s * 0.38, y + s * 0.12),
            (x - s * 0.44, y - s * 0.28),
        ]
        pygame.draw.polygon(surface, color, points)
        inner = [
            (x, y - s * 0.31),
            (x + s * 0.24, y - s * 0.18),
            (x + s * 0.2, y + s * 0.08),
            (x, y + s * 0.29),
            (x - s * 0.2, y + s * 0.08),
            (x - s * 0.24, y - s * 0.18),
        ]
        pygame.draw.polygon(surface, secondary, inner)
        pygame.draw.line(
            surface,
            color,
            (x, y - s * 0.15),
            (x, y + s * 0.16),
            max(2, int(s * 0.09)),
        )
    elif kind == "magnet":
        thick = max(4, int(s * 0.26))
        rect = pygame.Rect(0, 0, int(s * 0.85), int(s * 0.8))
        rect.center = (round(x), round(y + s * 0.05))
        pygame.draw.arc(surface, color, rect, 0.15, math.pi - 0.15, thick)
        pygame.draw.line(surface, color, (x - s * 0.34, y - s * 0.32), (x - s * 0.34, y + s * 0.13), thick)
        pygame.draw.line(surface, color, (x + s * 0.34, y - s * 0.32), (x + s * 0.34, y + s * 0.13), thick)
        tip_w = max(3, int(s * 0.2))
        pygame.draw.rect(surface, secondary, (x - s * 0.45, y - s * 0.43, tip_w, s * 0.2), border_radius=2)
        pygame.draw.rect(surface, secondary, (x + s * 0.2, y - s * 0.43, tip_w, s * 0.2), border_radius=2)
    elif kind == "x2":
        draw_text(
            surface,
            "×2",
            max(10, int(s * 0.72)),
            (x, y),
            color,
            anchor="center",
            bold=True,
            shadow=None,
        )
    elif kind == "wings":
        left = [
            (x - s * 0.08, y),
            (x - s * 0.62, y - s * 0.35),
            (x - s * 0.43, y - s * 0.08),
            (x - s * 0.62, y + s * 0.12),
            (x - s * 0.38, y + s * 0.18),
            (x - s * 0.1, y + s * 0.28),
        ]
        right = [(2 * x - px, 2 * y - py) for px, py in left]
        pygame.draw.polygon(surface, color, left)
        pygame.draw.polygon(surface, color, right)
        pygame.draw.line(surface, secondary, (x - s * 0.1, y), (x - s * 0.45, y - s * 0.11), max(1, int(s * 0.06)))
        pygame.draw.line(surface, secondary, (x + s * 0.1, y), (x + s * 0.45, y - s * 0.11), max(1, int(s * 0.06)))
    elif kind == "slow":
        pygame.draw.rect(surface, color, (x - s * 0.3, y - s * 0.48, s * 0.6, s * 0.12), border_radius=2)
        pygame.draw.rect(surface, color, (x - s * 0.3, y + s * 0.36, s * 0.6, s * 0.12), border_radius=2)
        pygame.draw.polygon(
            surface,
            color,
            [(x - s * 0.25, y - s * 0.36), (x + s * 0.25, y - s * 0.36), (x, y + s * 0.02)],
        )
        pygame.draw.polygon(
            surface,
            color,
            [(x - s * 0.25, y + s * 0.35), (x + s * 0.25, y + s * 0.35), (x, y - s * 0.04)],
        )
        pygame.draw.polygon(
            surface,
            secondary,
            [(x - s * 0.13, y + s * 0.25), (x + s * 0.13, y + s * 0.25), (x, y + s * 0.04)],
        )
    elif kind == "phoenix":
        flame = [
            (x, y - s * 0.54),
            (x + s * 0.16, y - s * 0.22),
            (x + s * 0.42, y - s * 0.34),
            (x + s * 0.32, y + s * 0.05),
            (x + s * 0.16, y + s * 0.43),
            (x, y + s * 0.55),
            (x - s * 0.2, y + s * 0.34),
            (x - s * 0.4, y - s * 0.05),
            (x - s * 0.22, y - s * 0.2),
            (x - s * 0.12, y + s * 0.02),
            (x - s * 0.04, y - s * 0.3),
        ]
        pygame.draw.polygon(surface, color, flame)
        inner = [
            (x, y - s * 0.22),
            (x + s * 0.16, y + s * 0.16),
            (x, y + s * 0.42),
            (x - s * 0.17, y + s * 0.12),
        ]
        pygame.draw.polygon(surface, secondary, inner)
    elif kind == "dash":
        width = max(2, int(s * 0.1))
        for i in range(3):
            ox = -s * 0.3 + i * s * 0.26
            pygame.draw.lines(
                surface,
                color,
                False,
                [(x + ox - s * 0.08, y - s * 0.35), (x + ox + s * 0.16, y), (x + ox - s * 0.08, y + s * 0.35)],
                width,
            )
    elif kind == "crystal":
        points = [(x, y - s * 0.5), (x + s * 0.35, y - s * 0.1), (x, y + s * 0.5), (x - s * 0.35, y - s * 0.1)]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, secondary, [(x, y - s * 0.34), (x + s * 0.16, y - s * 0.08), (x, y + s * 0.3)])
    elif kind == "coin":
        pygame.draw.circle(surface, (118, 72, 26), (round(x), round(y)), int(s * 0.46))
        pygame.draw.circle(surface, GOLD, (round(x), round(y)), int(s * 0.38))
        pygame.draw.circle(surface, (255, 232, 143), (round(x), round(y)), int(s * 0.23), width=max(1, int(s * 0.06)))
    elif kind == "feather":
        pygame.draw.polygon(
            surface,
            color,
            [(x - s * 0.3, y + s * 0.4), (x - s * 0.05, y - s * 0.42), (x + s * 0.1, y + s * 0.2)],
        )
        pygame.draw.line(surface, secondary, (x - s * 0.28, y + s * 0.35), (x - s * 0.04, y - s * 0.3), 2)
    elif kind == "pause":
        pygame.draw.rect(surface, color, (x - s * 0.27, y - s * 0.4, s * 0.18, s * 0.8), border_radius=2)
        pygame.draw.rect(surface, color, (x + s * 0.09, y - s * 0.4, s * 0.18, s * 0.8), border_radius=2)
    elif kind == "sound":
        pygame.draw.polygon(
            surface,
            color,
            [(x - s * 0.38, y - s * 0.15), (x - s * 0.18, y - s * 0.15), (x + s * 0.05, y - s * 0.38), (x + s * 0.05, y + s * 0.38), (x - s * 0.18, y + s * 0.15), (x - s * 0.38, y + s * 0.15)],
        )
        pygame.draw.arc(surface, color, pygame.Rect(x - s * 0.05, y - s * 0.34, s * 0.5, s * 0.68), -0.8, 0.8, max(2, int(s * 0.08)))
        pygame.draw.arc(surface, color, pygame.Rect(x + s * 0.02, y - s * 0.5, s * 0.52, s), -0.65, 0.65, max(2, int(s * 0.07)))
    elif kind == "mute":
        pygame.draw.polygon(
            surface,
            color,
            [(x - s * 0.38, y - s * 0.15), (x - s * 0.18, y - s * 0.15), (x + s * 0.05, y - s * 0.38), (x + s * 0.05, y + s * 0.38), (x - s * 0.18, y + s * 0.15), (x - s * 0.38, y + s * 0.15)],
        )
        pygame.draw.line(surface, CORAL, (x + s * 0.14, y - s * 0.2), (x + s * 0.45, y + s * 0.2), max(2, int(s * 0.08)))
        pygame.draw.line(surface, CORAL, (x + s * 0.45, y - s * 0.2), (x + s * 0.14, y + s * 0.2), max(2, int(s * 0.08)))
    elif kind == "star":
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            radius = s * (0.5 if i % 2 == 0 else 0.22)
            points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
        pygame.draw.polygon(surface, color, points)
    else:
        pygame.draw.circle(surface, color, (round(x), round(y)), int(s * 0.35))


def draw_power_orb(
    surface: pygame.Surface,
    center: tuple[float, float],
    kind: str,
    time: float,
    *,
    collected: bool = False,
) -> None:
    x, y = center
    color = POWER_COLORS.get(kind, TEAL)
    draw_glow(surface, (x, y), 48, color, intensity=60)
    pulse = 1.0 + math.sin(time * 4.2) * 0.04
    radius = int(25 * pulse)
    pygame.draw.circle(surface, (13, 19, 27), (round(x), round(y)), radius + 4)
    pygame.draw.circle(surface, (*color,), (round(x), round(y)), radius, width=3)
    pygame.draw.circle(surface, (22, 30, 40), (round(x), round(y)), radius - 3)
    # Destellos orbitando.
    for i in range(3):
        angle = time * 1.8 + i * (math.tau / 3)
        sx = x + math.cos(angle) * (radius + 9)
        sy = y + math.sin(angle) * (radius + 9) * 0.7
        pygame.draw.circle(surface, CREAM, (round(sx), round(sy)), 2)
    draw_icon(surface, kind, (x, y), 28, color, secondary=CREAM)


def draw_crystal(
    surface: pygame.Surface,
    center: tuple[float, float],
    time: float,
    *,
    phase: float = 0.0,
) -> None:
    x, y = center
    bob = math.sin(time * 3.1 + phase) * 4
    draw_glow(surface, (x, y + bob), 30, CYAN, intensity=70)
    size = 23
    points = [(x, y - size + bob), (x + size * 0.7, y - size * 0.2 + bob), (x, y + size + bob), (x - size * 0.7, y - size * 0.2 + bob)]
    pygame.draw.polygon(surface, (22, 67, 83), [(px + 2, py + 3) for px, py in points])
    pygame.draw.polygon(surface, CYAN, points)
    pygame.draw.polygon(surface, (199, 252, 255), [(x, y - size + bob), (x + size * 0.24, y - size * 0.15 + bob), (x, y + size * 0.38 + bob)])
    pygame.draw.line(surface, WHITE, (x - 2, y - 12 + bob), (x - 2, y + 7 + bob), 2)
    if int(time * 4 + phase) % 3 == 0:
        sparkle = (x + 16, y - 18 + bob)
        pygame.draw.line(surface, CREAM, (sparkle[0] - 4, sparkle[1]), (sparkle[0] + 4, sparkle[1]), 1)
        pygame.draw.line(surface, CREAM, (sparkle[0], sparkle[1] - 4), (sparkle[0], sparkle[1] + 4), 1)


def draw_ptero(surface: pygame.Surface, center: tuple[float, float], zone: int, time: float, size: float = 1.0) -> None:
    frame = int(time * 9.0) % 4
    image = ptero_surface(zone, frame)
    if size != 1.0:
        image = pygame.transform.scale(image, (int(image.width * size), int(image.height * size)))
    surface.blit(image, image.get_rect(center=(round(center[0]), round(center[1]))))


def draw_shield_bubble(
    surface: pygame.Surface,
    center: tuple[float, float],
    radius: float,
    time: float,
    color: tuple[int, int, int] = POWER_COLORS["shield"],
) -> None:
    size = int(radius * 2 + 12)
    bubble = pygame.Surface((size, size), pygame.SRCALPHA)
    c = (size // 2, size // 2)
    pulse = 1.0 + math.sin(time * 5) * 0.025
    rr = int(radius * pulse)
    pygame.draw.circle(bubble, (*color, 30), c, rr)
    pygame.draw.circle(bubble, (*color, 160), c, rr, width=3)
    for i in range(3):
        start = time * 1.3 + i * 2.0
        rect = pygame.Rect(c[0] - rr, c[1] - rr, rr * 2, rr * 2)
        pygame.draw.arc(bubble, (*CREAM, 105), rect, start, start + 0.7, 2)
    pygame.draw.circle(bubble, (*CREAM, 180), (c[0] - rr // 2, c[1] - rr // 2), max(2, rr // 12))
    surface.blit(bubble, bubble.get_rect(center=(round(center[0]), round(center[1]))))


def draw_wings(
    surface: pygame.Surface,
    center: tuple[float, float],
    time: float,
    color: tuple[int, int, int] = POWER_COLORS["wings"],
) -> None:
    x, y = center
    flap = math.sin(time * 13.0) * 6
    overlay = pygame.Surface((124, 92), pygame.SRCALPHA)
    cx, cy = 62, 55
    for direction in (-1, 1):
        pts = [
            (cx + direction * 7, cy),
            (cx + direction * 44, cy - 26 + flap),
            (cx + direction * 31, cy - 5 + flap * 0.4),
            (cx + direction * 48, cy + 4 + flap),
            (cx + direction * 21, cy + 11),
        ]
        pygame.draw.polygon(overlay, (*color, 70), pts)
        pygame.draw.lines(overlay, (*CREAM, 120), False, pts, 2)
    surface.blit(overlay, overlay.get_rect(center=(round(x), round(y))))


def draw_speed_trail(surface: pygame.Surface, x: float, y: float, height: float, time: float, color: tuple[int, int, int]) -> None:
    overlay = pygame.Surface((240, int(height) + 50), pygame.SRCALPHA)
    local_x = 210
    for i in range(5):
        seed = (time * 9 + i * 1.7) % 3
        line_y = 20 + height * (0.18 + i * 0.16) + math.sin(time * 8 + i) * 3
        length = 35 + seed * 30
        pygame.draw.line(overlay, (*color, 35 + i * 8), (local_x - i * 13, line_y), (local_x - i * 13 - length, line_y), 2)
    surface.blit(overlay, overlay.get_rect(bottomright=(round(x) - 18, round(y) + 18)))


def draw_phoenix_aura(surface: pygame.Surface, center: tuple[float, float], time: float) -> None:
    x, y = center
    draw_glow(surface, (x, y + 12), 58, POWER_COLORS["phoenix"], intensity=50)
    overlay = pygame.Surface((170, 120), pygame.SRCALPHA)
    cx, cy = 85, 70
    for i in range(6):
        phase = time * 3.3 + i * 1.05
        fx = cx - 34 + i * 13 + math.sin(phase) * 5
        height = 14 + (math.sin(phase * 1.4) + 1) * 9
        fy = cy + 30
        pygame.draw.polygon(
            overlay,
            (*POWER_COLORS["phoenix"], 90),
            [(fx - 6, fy), (fx, fy - height), (fx + 5, fy)],
        )
        pygame.draw.polygon(
            overlay,
            (*GOLD, 70),
            [(fx - 2, fy), (fx, fy - height * 0.55), (fx + 2, fy)],
        )
    surface.blit(overlay, overlay.get_rect(center=(round(x), round(y) + 15)))


# ---------------------------------------------------------------------------
# Ambiente
# ---------------------------------------------------------------------------
_VIGNETTE: pygame.Surface | None = None


def vignette() -> pygame.Surface:
    global _VIGNETTE
    if _VIGNETTE is None:
        surface = pygame.Surface((1280, 720), pygame.SRCALPHA)
        for i in range(70):
            alpha = int((i / 70) ** 2.2 * 3.0)
            if alpha <= 0:
                continue
            rect = pygame.Rect(i, i, 1280 - 2 * i, 720 - 2 * i)
            pygame.draw.rect(surface, (5, 7, 12, alpha), rect, width=8)
        _VIGNETTE = surface
    return _VIGNETTE


def draw_vignette(surface: pygame.Surface, alpha: int = 170) -> None:
    v = vignette()
    v.set_alpha(alpha)
    surface.blit(v, (0, 0))


def draw_speed_dashes(
    surface: pygame.Surface,
    scroll: float,
    speed: float,
    ground_y: int,
    *,
    color: tuple[int, int, int],
    dash_color: tuple[int, int, int],
) -> None:
    """Detalles del suelo con sensación de velocidad."""
    spacing = 170
    offset = scroll % spacing
    y = ground_y + 19
    for i in range(9):
        x = int(i * spacing - offset)
        width = 26 + (i % 3) * 14
        pygame.draw.rect(surface, dash_color, (x, y + (i % 2) * 8, width, 3), border_radius=2)
    pygame.draw.line(surface, color, (0, ground_y), (1280, ground_y), 4)

