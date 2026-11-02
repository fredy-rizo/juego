"""Entidades del juego: dinosaurio, obstáculos, coleccionables y partículas."""
from __future__ import annotations

import math
import random

import pygame

from . import art
from .config import (
    CREAM,
    GROUND_Y,
    PLAYER_X,
    POWER_COLORS,
    WIDTH,
    ZONES,
)
from .utils import clamp, draw_coin_icon, draw_heart, draw_text, lerp_color

# ---------------------------------------------------------------------------
# Partículas y textos flotantes
# ---------------------------------------------------------------------------


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity", "drag", "shape", "rotation")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: float,
        color: tuple[int, int, int],
        size: float,
        *,
        gravity: float = 0.0,
        drag: float = 0.0,
        shape: str = "circle",
        rotation: float = 0.0,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity
        self.drag = drag
        self.shape = shape
        self.rotation = rotation

    def update(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0:
            return False
        self.vy += self.gravity * dt
        if self.drag:
            factor = max(0.0, 1.0 - self.drag * dt)
            self.vx *= factor
            self.vy *= factor
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rotation += dt * 3.0
        return True

    def draw(self, surface: pygame.Surface) -> None:
        t = clamp(self.life / self.max_life, 0.0, 1.0)
        alpha = int(255 * (t**0.6))
        color = (*self.color, alpha)
        size = max(1, int(self.size * (0.4 + t * 0.6)))
        if self.shape == "square":
            rect = pygame.Rect(0, 0, size * 2, size * 2)
            rect.center = (int(self.x), int(self.y))
            pygame.draw.rect(surface, color, rect, border_radius=1)
        elif self.shape == "line":
            length = max(3, int(self.size * 4 * t))
            pygame.draw.line(surface, color, (self.x, self.y), (self.x + length, self.y), max(1, int(self.size)))
        elif self.shape == "spark":
            pygame.draw.line(surface, color, (self.x - self.size, self.y), (self.x + self.size, self.y), 1)
            pygame.draw.line(surface, color, (self.x, self.y - self.size), (self.x, self.y + self.size), 1)
        elif self.shape == "diamond":
            points = [(self.x, self.y - size * 1.4), (self.x + size, self.y), (self.x, self.y + size * 1.4), (self.x - size, self.y)]
            pygame.draw.polygon(surface, color, points)
        else:
            pygame.draw.circle(surface, color, (int(self.x), int(self.y)), size)


class FloatingText:
    def __init__(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[int, int, int],
        *,
        size: int = 20,
        life: float = 0.9,
        vy: float = -48.0,
        mono: bool = True,
    ) -> None:
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.vy = vy
        self.mono = mono

    def update(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0:
            return False
        self.y += self.vy * dt
        self.vy *= 0.98
        return True

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(255 * clamp(self.life / self.max_life, 0, 1) ** 0.5)
        draw_text(
            surface,
            self.text,
            self.size,
            (self.x, self.y),
            self.color,
            anchor="center",
            mono=self.mono,
            shadow=(8, 8, 12),
            alpha=alpha,
        )


# ---------------------------------------------------------------------------
# Dinosaurio
# ---------------------------------------------------------------------------
NORMAL_HEIGHT = 58
DUCK_HEIGHT = 35


class Player:
    GRAVITY = 2600.0
    FAST_FALL_GRAVITY = 3600.0
    JUMP_SPEED = -930.0
    AIR_JUMP_SPEED = -830.0

    def __init__(self) -> None:
        self.x = float(PLAYER_X)
        self.y = float(GROUND_Y)
        self.vy = 0.0
        self.on_ground = True
        self.ducking = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.air_jump_used = False
        self.anim_phase = 0.0
        self.ground_time = 0.0
        self.hurt = False
        self.fast_falling = False

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------
    def queue_jump(self) -> None:
        self.jump_buffer = 0.13

    def cut_jump(self) -> None:
        if self.vy < -260:
            self.vy *= 0.54

    @property
    def height(self) -> int:
        return DUCK_HEIGHT if self.ducking else NORMAL_HEIGHT

    @property
    def width(self) -> int:
        return 72 if self.ducking else 48

    @property
    def rect(self) -> pygame.Rect:
        width = self.width
        height = self.height
        rect = pygame.Rect(0, 0, width, height)
        rect.midbottom = (round(self.x), round(self.y))
        return rect

    @property
    def center(self) -> tuple[float, float]:
        return self.x, self.y - self.height / 2

    @property
    def airborne(self) -> bool:
        return not self.on_ground

    # ------------------------------------------------------------------
    # Física
    # ------------------------------------------------------------------
    def update(self, dt: float, duck_held: bool, wings_active: bool) -> list[str]:
        events: list[str] = []
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.ground_time = self.ground_time + dt if self.on_ground else 0.0

        if self.on_ground:
            self.coyote = 0.085
        else:
            self.coyote = max(0.0, self.coyote - dt)

        # El salto tiene prioridad sobre agacharse.
        if self.jump_buffer > 0:
            if self.on_ground or self.coyote > 0:
                self.vy = self.JUMP_SPEED
                self.on_ground = False
                self.ducking = False
                self.jump_buffer = 0.0
                self.air_jump_used = False
                events.append("jump")
            elif wings_active and not self.air_jump_used:
                self.vy = self.AIR_JUMP_SPEED
                self.air_jump_used = True
                self.jump_buffer = 0.0
                events.append("double_jump")

        # Agacharse en el suelo; en el aire, caída rápida.
        self.ducking = duck_held and self.on_ground
        self.fast_falling = duck_held and not self.on_ground
        if not self.on_ground:
            gravity = self.FAST_FALL_GRAVITY if self.fast_falling else self.GRAVITY
            self.vy += gravity * dt
            self.y += self.vy * dt
            if self.y >= GROUND_Y:
                self.y = float(GROUND_Y)
                self.vy = 0.0
                self.on_ground = True
                self.ducking = duck_held
                self.air_jump_used = False
                events.append("land")

        self.anim_phase += dt * (16.0 if self.on_ground and not self.ducking else 5.0)
        return events

    def reset(self) -> None:
        self.y = float(GROUND_Y)
        self.vy = 0.0
        self.on_ground = True
        self.ducking = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.air_jump_used = False
        self.anim_phase = 0.0
        self.ground_time = 0.0
        self.hurt = False

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def draw(
        self,
        surface: pygame.Surface,
        dino: art.DinoArt,
        *,
        time: float,
        shield_time: float,
        wings_time: float,
        phoenix: bool,
        dash_time: float,
        invincible: float,
        game_over: bool,
    ) -> None:
        feet_x = round(self.x)
        feet_y = round(self.y)
        airborne = not self.on_ground
        height_off_ground = GROUND_Y - self.y

        # Sombra en el suelo, más pequeña al elevarse.
        shadow_scale = clamp(1.0 - height_off_ground / 360.0, 0.35, 1.0)
        shadow = pygame.Surface((90, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (15, 19, 23, int(105 * shadow_scale)), (int(45 - 35 * shadow_scale), 7, int(70 * shadow_scale), int(10 * shadow_scale)))
        surface.blit(shadow, (feet_x - 45, GROUND_Y - 9))

        if wings_time > 0:
            wing_y = feet_y - self.height / 2 if airborne else feet_y - self.height - 13
            art.draw_wings(surface, (feet_x - 2, wing_y), time)
        if phoenix:
            art.draw_phoenix_aura(surface, (feet_x, feet_y - self.height / 2), time)
        if dash_time > 0:
            art.draw_speed_trail(surface, feet_x, feet_y - self.height, self.height, time, POWER_COLORS["dash"])

        if game_over:
            sprite = dino.hurt[0]
        elif self.ducking:
            sprite = dino.duck[int(self.anim_phase) % 2]
        elif airborne:
            sprite = dino.air[0 if self.vy < 100 else 1]
        else:
            sprite = dino.run[int(self.anim_phase) % 4]

        bob = 0
        if self.on_ground and not self.ducking:
            bob = -2 if int(self.anim_phase) % 4 in (1, 3) else 0
        pos = (feet_x, feet_y + bob)
        image = sprite
        if invincible > 0 and not game_over:
            # Parpadeo al recibir un golpe.
            if int(time * 20) % 2 == 0:
                image = sprite.copy()
                image.set_alpha(95)
        surface.blit(image, image.get_rect(midbottom=pos))

        if shield_time > 0:
            art.draw_shield_bubble(surface, (feet_x, feet_y - self.height / 2 - 1), 48, time)

        if game_over:
            # Estrellitas de aturdimiento.
            for i in range(3):
                angle = time * 2.2 + i * math.tau / 3
                sx = feet_x + math.cos(angle) * 32
                sy = feet_y - 78 + math.sin(angle) * 10
                draw_heart(surface, (sx, sy), 10, color=POWER_COLORS["x2"], empty=True)


# ---------------------------------------------------------------------------
# Obstáculos
# ---------------------------------------------------------------------------
class Obstacle:
    """Cactus, rocas y pterodáctilos con hitboxes algo indulgentes."""

    def __init__(self, kind: str, x: float, zone: int, *, t: float = 0.0) -> None:
        self.kind = kind
        self.x = float(x)
        self.zone = zone
        self.time = t
        self.passed = False
        self.hit_flash = 0.0
        self.destroyed = False
        self.rect = pygame.Rect(0, 0, 1, 1)
        if kind == "cactus_small":
            self.hit_w, self.hit_h = 30, 55
            self.y_center = GROUND_Y - self.hit_h / 2
        elif kind == "cactus_tall":
            self.hit_w, self.hit_h = 28, 79
            self.y_center = GROUND_Y - self.hit_h / 2
        elif kind == "rock":
            self.hit_w, self.hit_h = 56, 33
            self.y_center = GROUND_Y - self.hit_h / 2
        else:  # ptero_low
            self.hit_w, self.hit_h = 59, 36
            self.y_center = GROUND_Y - 67
        self._sync_rect()

    def _sync_rect(self) -> None:
        self.rect = pygame.Rect(0, 0, self.hit_w, self.hit_h)
        self.rect.center = (round(self.x), round(self.y_center))

    def update(self, dt: float, speed: float) -> None:
        self.x -= speed * dt
        self.time += dt
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self._sync_rect()

    @property
    def offscreen(self) -> bool:
        return self.x < -140

    @property
    def destructible(self) -> bool:
        return True

    def draw(self, surface: pygame.Surface) -> None:
        palette = ZONES[self.zone]
        # Sombra.
        if self.kind != "ptero_low":
            shadow = pygame.Surface((110, 22), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (15, 18, 22, 75), (5, 8, 70, 9))
            surface.blit(shadow, (self.x - 55, GROUND_Y - 8))

        if self.kind == "cactus_small":
            image = art.cactus_surface(self.zone, tall=False)
            surface.blit(image, image.get_rect(midbottom=(round(self.x), GROUND_Y + 3)))
        elif self.kind == "cactus_tall":
            image = art.cactus_surface(self.zone, tall=True)
            surface.blit(image, image.get_rect(midbottom=(round(self.x), GROUND_Y + 3)))
        elif self.kind == "rock":
            image = art.rock_surface(self.zone)
            surface.blit(image, image.get_rect(midbottom=(round(self.x), GROUND_Y + 4)))
        else:
            art.draw_ptero(surface, (self.x, self.y_center), self.zone, self.time)

        if self.hit_flash > 0:
            pygame.draw.rect(surface, (255, 255, 255), self.rect, width=2, border_radius=4)

    def explosion_particles(self, rng: random.Random) -> list[Particle]:
        palette = ZONES[self.zone]
        colors = [palette["accent"], palette["ground"], CREAM]
        if self.kind in ("cactus_small", "cactus_tall"):
            colors += [(74, 170, 119), (43, 112, 83)]
        elif self.kind == "rock":
            colors += [(138, 111, 92), (88, 68, 63)]
        else:
            colors += [(154, 91, 113), (117, 70, 99)]
        particles = []
        for _ in range(15):
            angle = rng.uniform(-math.pi, 0)
            speed = rng.uniform(80, 360)
            particles.append(
                Particle(
                    self.x + rng.uniform(-self.hit_w / 3, self.hit_w / 3),
                    self.y_center + rng.uniform(-self.hit_h / 3, self.hit_h / 3),
                    math.cos(angle) * speed,
                    math.sin(angle) * speed - 80,
                    rng.uniform(0.35, 0.8),
                    rng.choice(colors),
                    rng.uniform(2, 5),
                    gravity=900,
                    shape="square" if rng.random() < 0.5 else "circle",
                )
            )
        return particles


# ---------------------------------------------------------------------------
# Coleccionables
# ---------------------------------------------------------------------------
class Pickup:
    def __init__(self, kind: str, x: float, y: float, *, subtype: str = "", phase: float = 0.0) -> None:
        self.kind = kind
        self.subtype = subtype or kind
        self.x = float(x)
        self.base_y = float(y)
        self.y = float(y)
        self.phase = phase
        self.time = 0.0
        self.collected = False
        self.magnetized = False
        self.radius = 13 if kind == "coin" else 21 if kind == "crystal" else 27
        self.rotation = phase

    def update(self, dt: float, speed: float, magnet_target: tuple[float, float] | None = None) -> None:
        self.x -= speed * dt
        self.time += dt
        if magnet_target is not None and self.kind in ("coin", "crystal"):
            dx = magnet_target[0] - self.x
            dy = magnet_target[1] - self.y
            distance = math.hypot(dx, dy)
            if 0.0 < distance < 330.0:
                pull = 320.0 + (330.0 - distance) * 6.0
                step = min(distance, pull * dt)
                self.x += dx / distance * step
                self.y += dy / distance * step
                self.base_y = self.y
                self.magnetized = True
                return
        self.magnetized = False
        if self.kind == "coin":
            self.y = self.base_y + math.sin(self.time * 3.3 + self.phase) * 3
        elif self.kind == "crystal":
            self.y = self.base_y + math.sin(self.time * 2.6 + self.phase) * 5
        else:
            self.y = self.base_y + math.sin(self.time * 2.2 + self.phase) * 7

    @property
    def offscreen(self) -> bool:
        return self.x < -80

    def collision(self, rect: pygame.Rect) -> bool:
        closest_x = clamp(self.x, rect.left, rect.right)
        closest_y = clamp(self.y, rect.top, rect.bottom)
        dx = self.x - closest_x
        dy = self.y - closest_y
        return dx * dx + dy * dy <= (self.radius + 7) ** 2

    def draw(self, surface: pygame.Surface) -> None:
        if self.kind == "coin":
            draw_coin_icon(surface, (self.x, self.y), 13, phase=self.time * 5.6 + self.phase)
        elif self.kind == "crystal":
            art.draw_crystal(surface, (self.x, self.y), self.time, phase=self.phase)
        else:
            art.draw_power_orb(surface, (self.x, self.y), self.subtype, self.time)


# ---------------------------------------------------------------------------
# Ayudantes de efectos visuales
# ---------------------------------------------------------------------------


def make_dust(x: float, ground_y: float, rng: random.Random, *, color: tuple[int, int, int]) -> Particle:
    return Particle(
        x + rng.uniform(-17, 12),
        ground_y - rng.uniform(0, 7),
        rng.uniform(-150, -50),
        rng.uniform(-65, -5),
        rng.uniform(0.25, 0.55),
        lerp_color(color, (240, 225, 190), rng.uniform(0.0, 0.3)),
        rng.uniform(2, 4.8),
        gravity=80,
        drag=1.8,
    )


def make_landing_puff(x: float, ground_y: float, rng: random.Random, color: tuple[int, int, int]) -> list[Particle]:
    output = []
    for _ in range(10):
        output.append(
            Particle(
                x + rng.uniform(-22, 22),
                ground_y - rng.uniform(0, 8),
                rng.uniform(-190, 120),
                rng.uniform(-130, -25),
                rng.uniform(0.28, 0.6),
                lerp_color(color, (248, 236, 210), rng.uniform(0.1, 0.42)),
                rng.uniform(2.5, 6),
                gravity=380,
                drag=1.7,
            )
        )
    return output


def make_coin_pop(x: float, y: float, rng: random.Random) -> list[Particle]:
    output = []
    for i in range(7):
        angle = rng.uniform(0, math.tau)
        speed = rng.uniform(40, 150)
        output.append(
            Particle(
                x,
                y,
                math.cos(angle) * speed,
                math.sin(angle) * speed - 40,
                rng.uniform(0.25, 0.55),
                (255, 218, 104) if i % 3 else (255, 247, 197),
                rng.uniform(1.5, 3.5),
                gravity=300,
                shape="spark" if i % 2 else "circle",
            )
        )
    return output


def make_crystal_pop(x: float, y: float, rng: random.Random) -> list[Particle]:
    output = make_coin_pop(x, y, rng)
    for _ in range(7):
        output.append(
            Particle(
                x + rng.uniform(-12, 12),
                y + rng.uniform(-12, 12),
                rng.uniform(-100, 100),
                rng.uniform(-170, -30),
                rng.uniform(0.35, 0.8),
                (92, 231, 255) if rng.random() < 0.6 else (213, 255, 255),
                rng.uniform(2, 4),
                gravity=260,
                shape="diamond",
            )
        )
    return output


def make_level_confetti(rng: random.Random) -> list[Particle]:
    palette = [(255, 209, 92), (77, 228, 184), (255, 111, 97), (151, 177, 255), (251, 244, 218)]
    output = []
    for _ in range(70):
        output.append(
            Particle(
                rng.uniform(0, WIDTH),
                rng.uniform(-100, -10),
                rng.uniform(-70, 70),
                rng.uniform(70, 220),
                rng.uniform(1.3, 2.7),
                rng.choice(palette),
                rng.uniform(2, 5),
                gravity=80,
                drag=0.3,
                shape=rng.choice(["square", "diamond", "circle"]),
            )
        )
    return output
