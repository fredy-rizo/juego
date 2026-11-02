"""Fondo procedural con parallax, clima y suelo por zonas."""
from __future__ import annotations

import math
import random

import pygame

from .art import draw_glow, glow_surface
from .config import GROUND_Y, HEIGHT, WIDTH, ZONES
from .utils import clamp, lerp_color


def _lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return lerp_color(color, (255, 255, 255), amount)


def _darken(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return lerp_color(color, (0, 0, 0), amount)


class Background:
    """Cielo, montañas, suelo y partículas ambientales."""

    def __init__(self) -> None:
        self.zone = 0
        self.scroll = 0.0
        self.time = 0.0
        self._gradients: dict[int, pygame.Surface] = {}
        self._ridges: dict[tuple[int, int], pygame.Surface] = {}
        self._grounds: dict[int, pygame.Surface] = {}
        self._cloud_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._stars = self._make_stars()
        self._clouds = self._make_clouds()
        self._weather = self._make_weather()
        self._props = self._make_props()

    # ------------------------------------------------------------------
    # Actualización
    # ------------------------------------------------------------------
    def set_zone(self, zone: int) -> None:
        self.zone = zone % len(ZONES)

    def update(self, dt: float, speed: float) -> None:
        self.time += dt
        self.scroll += speed * dt

    # ------------------------------------------------------------------
    # Generadores
    # ------------------------------------------------------------------
    def _gradient(self, zone: int) -> pygame.Surface:
        if zone not in self._gradients:
            palette = ZONES[zone]
            surface = pygame.Surface((WIDTH, HEIGHT))
            for y in range(HEIGHT):
                t = y / (GROUND_Y + 20)
                color = lerp_color(palette["sky_top"], palette["sky_bottom"], clamp(t, 0.0, 1.0))
                pygame.draw.line(surface, color, (0, y), (WIDTH, y))
            # Grano casi imperceptible para evitar un degradado demasiado plano.
            rng = random.Random(900 + zone)
            for _ in range(170):
                x = rng.randrange(WIDTH)
                y = rng.randrange(0, GROUND_Y)
                tint = lerp_color(palette["sky_top"], palette["sky_bottom"], y / GROUND_Y)
                tint = _lighten(tint, 0.08)
                pygame.draw.circle(surface, tint, (x, y), 1)
            self._gradients[zone] = surface
        return self._gradients[zone]

    def _make_ridge_surface(self, zone: int, layer: int) -> pygame.Surface:
        """Genera una capa de silueta con un perfil repetible."""
        palette = ZONES[zone]
        key = (zone, layer)
        if key in self._ridges:
            return self._ridges[key]

        rng = random.Random(310 + zone * 17 + layer * 91)
        width = 2300
        if layer == 0:
            color = palette["far"]
            height = 330
            step = 110
            low, high = 150, 255
        elif layer == 1:
            color = palette["mid"]
            height = 255
            step = 125
            low, high = 105, 205
        else:
            color = palette["near"]
            height = 180
            step = 45
            low, high = 95, 160

        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        top_points: list[tuple[int, int]] = []

        if layer == 0:
            # Montañas angulosas.
            count = width // step + 1
            values = [rng.randint(low, high) for _ in range(count)]
            values[0] = values[-1] = rng.randint(low, high)
            for i, value in enumerate(values):
                x = i * step
                y = value
                if i not in (0, count - 1) and i % 2 == 0:
                    y = max(low, value - rng.randint(10, 38))
                top_points.append((x, y))
        elif layer == 1:
            # Mesetas y colinas amplias.
            count = width // step + 1
            values = [rng.randint(low, high) for _ in range(count)]
            values[0] = values[-1] = values[0]
            x = 0
            for i, value in enumerate(values):
                tx = i * step
                top_points.append((tx, value))
                if i < count - 1:
                    # Pequeña plataforma plana que recuerda a un cañón.
                    top_points.append((tx + step // 2, value))
        else:
            # Dunas suaves periódicas.
            base = 118
            phase = rng.random() * math.tau
            for x in range(0, width + 1, 20):
                angle = math.tau * x / width
                y = (
                    base
                    - math.sin(angle * 2 + phase) * 24
                    - math.sin(angle * 5 + phase * 1.7) * 9
                    - math.sin(angle * 11 + phase * 0.6) * 3
                )
                top_points.append((x, int(y)))

        polygon = top_points + [(width, height), (0, height)]
        pygame.draw.polygon(surface, color, polygon)

        # Borde iluminado por la atmósfera.
        edge = _lighten(color, 0.14 if layer < 2 else 0.22)
        pygame.draw.lines(surface, edge, False, top_points, 2)

        # Textura interior discreta.
        texture_color = _lighten(color, 0.055)
        for _ in range(30 if layer == 0 else 20):
            x = rng.randrange(width)
            y = rng.randrange(low + 20, height - 4)
            length = rng.randrange(20, 80)
            pygame.draw.line(surface, texture_color, (x, y), (x + length, y), 1)

        self._ridges[key] = surface
        return surface

    def _make_stars(self) -> list[list[tuple[float, float, float, float]]]:
        all_stars = []
        for zone, palette in enumerate(ZONES):
            rng = random.Random(77 + zone)
            stars = []
            count = 100 if palette["night"] else 0
            for _ in range(count):
                stars.append((rng.uniform(0, WIDTH), rng.uniform(20, 420), rng.uniform(1, 2.7), rng.random() * math.tau))
            all_stars.append(stars)
        return all_stars

    def _make_clouds(self) -> list[list[dict]]:
        clouds = []
        for zone in range(len(ZONES)):
            rng = random.Random(410 + zone)
            items = []
            for i in range(5):
                items.append(
                    {
                        "x": rng.uniform(-100, WIDTH),
                        "y": rng.uniform(90, 300),
                        "scale": rng.uniform(0.55, 1.2),
                        "speed": rng.uniform(4, 13),
                        "alpha": rng.randint(28, 65) if not ZONES[zone]["night"] else rng.randint(18, 38),
                    }
                )
            clouds.append(items)
        return clouds

    def _make_weather(self) -> list[list[dict]]:
        weather = []
        for zone, palette in enumerate(ZONES):
            rng = random.Random(880 + zone)
            items = []
            kind = palette["weather"]
            count = {"dust": 42, "sand": 55, "fireflies": 34, "embers": 44}[kind]
            for i in range(count):
                items.append(
                    {
                        "x": rng.uniform(0, WIDTH),
                        "y": rng.uniform(110, GROUND_Y - 8),
                        "phase": rng.random() * math.tau,
                        "speed": rng.uniform(0.35, 1.3),
                        "size": rng.uniform(1.0, 3.4),
                    }
                )
            weather.append(items)
        return weather

    def _make_props(self) -> dict[int, list[dict]]:
        props: dict[int, list[dict]] = {}
        for zone in range(len(ZONES)):
            rng = random.Random(230 + zone)
            items = []
            for _ in range(12):
                items.append(
                    {
                        "x": rng.uniform(0, 1800),
                        "height": rng.uniform(24, 82),
                        "width": rng.uniform(10, 34),
                        "kind": rng.choice(["cactus", "rock"]),
                        "layer": rng.random(),
                    }
                )
            props[zone] = items
        return props

    def _cloud_surface(self, zone: int, scale: float, alpha: int) -> pygame.Surface:
        key = (zone, round(scale * 100), alpha)
        if key in self._cloud_cache:
            return self._cloud_cache[key]
        width = int(260 * scale)
        height = int(80 * scale)
        color = ZONES[zone]["cloud"]
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        blobs = [
            (0.22, 0.62, 0.27, 0.24),
            (0.42, 0.50, 0.33, 0.32),
            (0.62, 0.57, 0.30, 0.28),
            (0.80, 0.64, 0.22, 0.20),
        ]
        for bx, by, bw, bh in blobs:
            rect = pygame.Rect(int(bx * width), int(by * height), int(bw * width), int(bh * height))
            pygame.draw.ellipse(surface, (*color, alpha), rect)
        self._cloud_cache[key] = surface
        return surface

    # ------------------------------------------------------------------
    # Dibujado
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        palette = ZONES[self.zone]
        surface.blit(self._gradient(self.zone), (0, 0))
        self._draw_stars(surface)
        self._draw_celestial(surface)
        self._draw_clouds(surface)
        self._draw_layer(surface, 0, parallax=0.06, y_bottom=GROUND_Y + 8)
        self._draw_birds(surface)
        self._draw_layer(surface, 1, parallax=0.16, y_bottom=GROUND_Y + 10)
        self._draw_props(surface)
        self._draw_layer(surface, 2, parallax=0.30, y_bottom=GROUND_Y + 12)
        self._draw_ground(surface)
        self._draw_weather(surface)

    def _draw_stars(self, surface: pygame.Surface) -> None:
        palette = ZONES[self.zone]
        if not palette["night"]:
            return
        for i, (x, y, size, phase) in enumerate(self._stars[self.zone]):
            twinkle = (math.sin(self.time * 1.6 + phase) + 1) / 2
            color = lerp_color(_darken(palette["sky_top"], 0.05), (255, 251, 224), 0.18 + twinkle * 0.55)
            pygame.draw.circle(surface, color, (round(x), round(y)), max(1, int(round(size * (0.65 + twinkle * 0.5)))))
            if i % 17 == 0:
                pygame.draw.line(surface, (*color,), (x - 3, y), (x + 3, y), 1)
                pygame.draw.line(surface, (*color,), (x, y - 3), (x, y + 3), 1)

    def _draw_celestial(self, surface: pygame.Surface) -> None:
        palette = ZONES[self.zone]
        if self.zone == 2:
            center = (1000, 157)
            radius = 43
        elif self.zone == 3:
            center = (945, 184)
            radius = 57
        else:
            center = (980, 206 - self.zone * 15)
            radius = 56
        draw_glow(surface, center, int(radius * 2.7), palette["sun_glow"], intensity=50)
        pygame.draw.circle(surface, palette["sun"], center, radius)
        if self.zone == 2:
            # Cráteres suaves del satélite.
            for dx, dy, r in ((-14, -10, 5), (9, 8, 7), (18, -12, 4), (-5, 16, 3)):
                pygame.draw.circle(surface, _darken(palette["sun"], 0.12), (center[0] + dx, center[1] + dy), r)
        elif self.zone == 3:
            pygame.draw.circle(surface, _lighten(palette["sun"], 0.22), (center[0] - 12, center[1] - 10), 31)
            for dx, dy in ((-15, 4), (8, 18), (20, -4)):
                pygame.draw.circle(surface, palette["sun"], (center[0] + dx, center[1] + dy), 4)
        else:
            pygame.draw.circle(surface, _lighten(palette["sun"], 0.36), (center[0] - 14, center[1] - 12), 27)

    def _draw_clouds(self, surface: pygame.Surface) -> None:
        for i, cloud in enumerate(self._clouds[self.zone]):
            span = WIDTH + 500
            x = (cloud["x"] - self.scroll * 0.025 - self.time * cloud["speed"] + 200) % span - 250
            y = cloud["y"] + math.sin(self.time * 0.22 + i) * 3
            image = self._cloud_surface(self.zone, cloud["scale"], cloud["alpha"])
            surface.blit(image, (round(x), round(y)))

    def _draw_layer(self, surface: pygame.Surface, layer: int, *, parallax: float, y_bottom: int) -> None:
        ridge = self._make_ridge_surface(self.zone, layer)
        width = ridge.get_width()
        offset = (self.scroll * parallax) % width
        x = -offset
        y = y_bottom - ridge.get_height()
        while x < WIDTH:
            surface.blit(ridge, (round(x), y))
            x += width

    def _draw_props(self, surface: pygame.Surface) -> None:
        """Siluetas lejanas: cactus, rocas, helechos o árboles quemados."""
        palette = ZONES[self.zone]
        color = _darken(palette["near"], 0.14)
        if self.zone == 2:
            color = _darken(palette["near"], 0.24)
        span = 1800
        for prop in self._props[self.zone]:
            x = (prop["x"] - self.scroll * (0.33 + prop["layer"] * 0.05) + 200) % (span + 200) - 150
            base_y = GROUND_Y - 34 - prop["layer"] * 10
            height = prop["height"]
            width = prop["width"]
            if prop["kind"] == "cactus":
                trunk = pygame.Rect(int(x), int(base_y - height), max(4, int(width * 0.28)), int(height))
                pygame.draw.rect(surface, color, trunk, border_radius=3)
                arm_y = int(base_y - height * 0.55)
                pygame.draw.rect(surface, color, (trunk.left - int(width * 0.42), arm_y, int(width * 0.45), max(3, int(height * 0.11))), border_radius=2)
                pygame.draw.rect(surface, color, (trunk.left - int(width * 0.42), arm_y - int(height * 0.18), max(3, int(width * 0.12)), int(height * 0.2)), border_radius=2)
                pygame.draw.rect(surface, color, (trunk.right - 2, arm_y + 5, int(width * 0.38), max(3, int(height * 0.1))), border_radius=2)
                pygame.draw.rect(surface, color, (trunk.right + int(width * 0.25), arm_y - int(height * 0.12), max(3, int(width * 0.12)), int(height * 0.16)), border_radius=2)
            elif self.zone == 2:
                # Helechos grandes.
                stem_h = height * 0.75
                pygame.draw.line(surface, color, (x, base_y), (x, base_y - stem_h), max(2, int(width * 0.1)))
                for i in range(5):
                    ly = base_y - stem_h * (0.3 + i * 0.15)
                    reach = width * (0.75 - i * 0.08)
                    pygame.draw.line(surface, color, (x, ly), (x - reach, ly - 13), max(2, int(width * 0.08)))
                    pygame.draw.line(surface, color, (x, ly), (x + reach, ly - 13), max(2, int(width * 0.08)))
            else:
                # Rocas o troncos secos.
                points = [
                    (x - width * 0.5, base_y),
                    (x - width * 0.35, base_y - height * 0.35),
                    (x - width * 0.1, base_y - height * 0.55),
                    (x + width * 0.3, base_y - height * 0.4),
                    (x + width * 0.5, base_y),
                ]
                pygame.draw.polygon(surface, color, points)

    def _draw_birds(self, surface: pygame.Surface) -> None:
        if self.zone not in (0, 1):
            return
        color = _darken(ZONES[self.zone]["far"], 0.1)
        for i in range(3):
            x = (230 + i * 330 - self.scroll * 0.09 - self.time * 5) % (WIDTH + 220) - 100
            y = 135 + i * 47 + math.sin(self.time * 0.9 + i) * 4
            flap = math.sin(self.time * 5 + i) * 4
            pygame.draw.lines(surface, color, False, [(x - 10, y), (x, y + flap), (x + 10, y)], 2)
            pygame.draw.lines(surface, color, False, [(x - 7, y - 3), (x, y + flap), (x + 7, y - 3)], 1)

    def _make_ground_tile(self, zone: int) -> pygame.Surface:
        if zone in self._grounds:
            return self._grounds[zone]
        palette = ZONES[zone]
        width = 1600
        height = HEIGHT - GROUND_Y + 12
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill(palette["ground"])
        pygame.draw.rect(surface, palette["ground_dark"], (0, 0, width, 8))
        pygame.draw.line(surface, palette["line"], (0, 0), (width, 0), 3)
        pygame.draw.rect(surface, _lighten(palette["ground"], 0.08), (0, 8, width, 3))
        pygame.draw.rect(surface, _darken(palette["ground"], 0.11), (0, height - 40, width, 40))

        rng = random.Random(1210 + zone)
        for _ in range(120):
            x = rng.randrange(width)
            y = rng.randrange(18, height - 12)
            length = rng.randrange(2, 22)
            color = _lighten(palette["ground"], 0.09) if rng.random() > 0.45 else _darken(palette["ground"], 0.10)
            pygame.draw.line(surface, color, (x, y), (x + length, y), 1)
        for _ in range(30):
            x = rng.randrange(width)
            y = rng.randrange(24, height - 18)
            size = rng.randrange(2, 5)
            pygame.draw.circle(surface, _darken(palette["ground"], 0.16), (x, y), size)

        # Decoración característica de cada zona.
        decor = palette["decor"]
        for _ in range(34):
            x = rng.randrange(40, width - 40)
            if decor == "cactus":
                if rng.random() < 0.55:
                    pygame.draw.line(surface, _darken(palette["ground"], 0.34), (x, 16), (x, 28), 2)
                    for j in range(2):
                        pygame.draw.line(surface, _darken(palette["ground"], 0.32), (x, 23 + j * 4), (x - 6, 18 + j * 3), 2)
                        pygame.draw.line(surface, _darken(palette["ground"], 0.32), (x, 26 + j * 3), (x + 7, 22 + j * 2), 2)
                else:
                    pygame.draw.ellipse(surface, _darken(palette["ground"], 0.2), (x, 18, 8, 4))
            elif decor == "rocks":
                pygame.draw.polygon(
                    surface,
                    _darken(palette["ground"], 0.18),
                    [(x, 18), (x + 5, 13), (x + 11, 17), (x + 9, 21), (x + 2, 22)],
                )
            elif decor == "ferns":
                pygame.draw.line(surface, _darken(palette["ground"], 0.42), (x, 28), (x, 15), 2)
                for j in range(3):
                    pygame.draw.line(surface, _darken(palette["ground"], 0.4), (x, 20 + j * 2), (x - 6, 16 + j * 2), 2)
                    pygame.draw.line(surface, _darken(palette["ground"], 0.4), (x, 21 + j * 2), (x + 7, 17 + j * 2), 2)
                if rng.random() < 0.45:
                    pygame.draw.circle(surface, (*ZONES[zone]["accent"],), (x + rng.randrange(-4, 5), rng.randrange(16, 25)), 2)
            else:
                points = [(x, 30), (x + 4, 22), (x + 10, 26), (x + 13, 18), (x + 18, 24)]
                pygame.draw.lines(surface, palette["line"], False, points, 2)
                if rng.random() < 0.5:
                    pygame.draw.circle(surface, palette["accent"], (x + 8, rng.randrange(16, 27)), 2)

        self._grounds[zone] = surface
        return surface

    def _draw_ground(self, surface: pygame.Surface) -> None:
        palette = ZONES[self.zone]
        ground = self._make_ground_tile(self.zone)
        offset = self.scroll % ground.get_width()
        x = -offset
        while x < WIDTH:
            surface.blit(ground, (round(x), GROUND_Y))
            x += ground.get_width()

        # Línea y guiones que comunican velocidad.
        pygame.draw.line(surface, palette["line"], (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        pygame.draw.line(surface, _lighten(palette["ground"], 0.18), (0, GROUND_Y + 4), (WIDTH, GROUND_Y + 4), 1)
        dash_color = _lighten(palette["ground"], 0.14 if self.zone != 3 else 0.32)
        spacing = 175
        offset = (self.scroll * 1.05) % spacing
        for i in range(9):
            x = int(i * spacing - offset)
            width = 24 + (i * 7) % 30
            pygame.draw.rect(surface, dash_color, (x, GROUND_Y + 20 + (i % 2) * 8, width, 3), border_radius=2)

    def _draw_weather(self, surface: pygame.Surface) -> None:
        palette = ZONES[self.zone]
        kind = palette["weather"]
        particles = self._weather[self.zone]
        if kind == "dust":
            color = _lighten(palette["accent"], 0.15)
            for p in particles:
                x = (p["x"] - self.scroll * 0.16 - self.time * 10 * p["speed"]) % (WIDTH + 20) - 10
                y = p["y"] + math.sin(self.time * 1.3 + p["phase"]) * 6
                pygame.draw.circle(surface, color, (round(x), round(y)), max(1, int(p["size"])))
        elif kind == "sand":
            color = _lighten(palette["cloud"], 0.1)
            for p in particles:
                x = (p["x"] - self.scroll * 0.62 - self.time * 100 * p["speed"]) % (WIDTH + 130) - 65
                y = p["y"] + math.sin(self.time * 2 + p["phase"]) * 3
                length = 8 + p["size"] * 4
                pygame.draw.line(surface, color, (x, y), (x + length, y), max(1, int(p["size"] / 2)))
        elif kind == "fireflies":
            halo = glow_surface(12, palette["accent"], 70)
            for p in particles:
                x = (p["x"] + math.sin(self.time * 0.4 + p["phase"]) * 42 - self.scroll * 0.12) % WIDTH
                y = p["y"] + math.cos(self.time * 0.7 + p["phase"]) * 18
                pulse = (math.sin(self.time * 2.2 + p["phase"] * 2.5) + 1) / 2
                if pulse > 0.32:
                    radius = 2 + pulse * 2
                    surface.blit(halo, halo.get_rect(center=(round(x), round(y))))
                    pygame.draw.circle(surface, (225, 255, 215), (round(x), round(y)), int(radius))
        else:  # embers
            halo = glow_surface(9, palette["accent"], 80)
            for p in particles:
                rise = self.time * (18 + p["speed"] * 24) + p["phase"] * 50
                x = (p["x"] + math.sin(self.time + p["phase"]) * 12 - self.scroll * 0.2) % WIDTH
                y = GROUND_Y - (rise % 520)
                flicker = 0.55 + 0.45 * abs(math.sin(self.time * 4 + p["phase"]))
                color = lerp_color((255, 92, 43), palette["accent"], flicker)
                surface.blit(halo, halo.get_rect(center=(round(x), round(y))))
                pygame.draw.circle(surface, color, (round(x), round(y)), max(1, int(p["size"] * 0.7)))
