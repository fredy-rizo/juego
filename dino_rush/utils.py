"""Pequeñas utilidades compartidas: matemáticas, fuentes y textos."""
from __future__ import annotations

import math
import random
from collections import OrderedDict
from typing import Iterable

import pygame

from .config import CREAM

# ---------------------------------------------------------------------------
# Matemáticas
# ---------------------------------------------------------------------------


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def move_toward(value: float, target: float, amount: float) -> float:
    if value < target:
        return min(value + amount, target)
    return max(value - amount, target)


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def ease_in_out(t: float) -> float:
    return 0.5 - math.cos(math.pi * clamp(t, 0.0, 1.0)) / 2.0


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t, 0.0, 1.0)
    return (
        round(lerp(a[0], b[0], t)),
        round(lerp(a[1], b[1], t)),
        round(lerp(a[2], b[2], t)),
    )


def circle_rect_collide(cx: float, cy: float, radius: float, rect: pygame.Rect) -> bool:
    closest_x = clamp(cx, rect.left, rect.right)
    closest_y = clamp(cy, rect.top, rect.bottom)
    dx = cx - closest_x
    dy = cy - closest_y
    return dx * dx + dy * dy <= radius * radius


# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------
_UI_FONTS = ("dejavusans", "notosans", "liberationsans", "arial")
_MONO_FONTS = ("dejavusansmono", "notosansmono", "liberationmono", "consolas", "couriernew")


class Fonts:
    """Administra fuentes y guarda en caché los textos renderizados."""

    def __init__(self) -> None:
        self._fonts: dict[tuple[int, bool, bool], pygame.font.Font] = {}
        self._cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._cache_limit = 640

    def get(self, size: int, bold: bool = True, mono: bool = False) -> pygame.font.Font:
        key = (size, bold, mono)
        if key not in self._fonts:
            names = _MONO_FONTS if mono else _UI_FONTS
            path = None
            for name in names:
                path = pygame.font.match_font(name, bold=bold)
                if path:
                    break
            font = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
            font.set_bold(bold)
            self._fonts[key] = font
        return self._fonts[key]

    def render(
        self,
        text: str,
        size: int,
        color: tuple[int, int, int],
        bold: bool = True,
        mono: bool = False,
        shadow: tuple[int, int, int] | None = None,
        shadow_offset: tuple[int, int] = (2, 2),
    ) -> tuple[pygame.Surface, pygame.Surface | None]:
        key = (text, size, color, bold, mono, shadow, shadow_offset)
        if key in self._cache:
            self._cache.move_to_end(key)
            main, shadow_surface = self._cache[key]
            return main, shadow_surface

        font = self.get(size, bold=bold, mono=mono)
        main = font.render(text, True, color)
        shadow_surface = font.render(text, True, shadow) if shadow else None
        self._cache[key] = (main, shadow_surface)
        self._cache.move_to_end(key)
        if len(self._cache) > self._cache_limit:
            self._cache.popitem(last=False)
        return main, shadow_surface


_FONTS: Fonts | None = None


def fonts() -> Fonts:
    global _FONTS
    if _FONTS is None:
        _FONTS = Fonts()
    return _FONTS


def draw_text(
    surface: pygame.Surface,
    text: str,
    size: int,
    pos: tuple[float, float],
    color: tuple[int, int, int] = CREAM,
    *,
    anchor: str = "topleft",
    bold: bool = True,
    mono: bool = False,
    shadow: tuple[int, int, int] | None = None,
    shadow_offset: tuple[int, int] = (2, 2),
    alpha: int = 255,
) -> pygame.Rect:
    """Dibuja texto con sombra opcional y devuelve su rect."""
    main, shadow_surface = fonts().render(text, size, color, bold, mono, shadow, shadow_offset)
    rect = main.get_rect(**{anchor: (round(pos[0]), round(pos[1]))})
    if shadow_surface is not None:
        shadow_rect = shadow_surface.get_rect(**{anchor: (round(pos[0] + shadow_offset[0]), round(pos[1] + shadow_offset[1]))})
        if alpha < 255:
            shadow_surface.set_alpha(alpha)
        surface.blit(shadow_surface, shadow_rect)
    if alpha < 255:
        main = main.copy()
        main.set_alpha(alpha)
    surface.blit(main, rect)
    return rect


def draw_wrapped_text(
    surface: pygame.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    rect: pygame.Rect,
    line_gap: int = 4,
    *,
    bold: bool = False,
    mono: bool = False,
    shadow: tuple[int, int, int] | None = None,
) -> int:
    """Dibuja un texto ajustado a un ancho. Devuelve la altura utilizada."""
    font = fonts().get(size, bold=bold, mono=mono)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= rect.width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = rect.top
    for line in lines:
        draw_text(
            surface,
            line,
            size,
            (rect.left, y),
            color,
            bold=bold,
            mono=mono,
            shadow=shadow,
        )
        y += font.get_height() + line_gap
    return y - rect.top


# ---------------------------------------------------------------------------
# Formas de interfaz
# ---------------------------------------------------------------------------


def alpha_surface(size: tuple[int, int], color: tuple[int, ...]) -> pygame.Surface:
    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(color)
    return surface


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, ...] = (15, 19, 27, 210),
    border: tuple[int, ...] = (255, 255, 255, 25),
    radius: int = 18,
    border_width: int = 2,
) -> None:
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
    if border[3] > 0:
        pygame.draw.rect(panel, border, panel.get_rect(), width=border_width, border_radius=radius)
    surface.blit(panel, rect.topleft)


def draw_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fraction: float,
    color: tuple[int, int, int],
    *,
    background: tuple[int, int, int] = (10, 15, 21),
    border: tuple[int, int, int] | None = (255, 255, 255),
    radius: int = 7,
    shimmer: bool = False,
) -> None:
    fraction = clamp(fraction, 0.0, 1.0)
    pygame.draw.rect(surface, background, rect, border_radius=radius)
    if fraction > 0:
        fill_rect = pygame.Rect(rect.x, rect.y, max(4, int(rect.width * fraction)), rect.height)
        pygame.draw.rect(surface, color, fill_rect, border_radius=radius)
        if shimmer and fill_rect.width > 16:
            shine = pygame.Surface((fill_rect.width, max(2, fill_rect.height // 3)), pygame.SRCALPHA)
            shine.fill((*CREAM, 52))
            surface.blit(shine, (fill_rect.x + 3, fill_rect.y + 2))
    if border:
        pygame.draw.rect(surface, (*border, 70) if len(border) == 3 else border, rect, width=2, border_radius=radius)


def draw_keycap(
    surface: pygame.Surface,
    label: str,
    center: tuple[int, int],
    *,
    size: int = 13,
    color: tuple[int, int, int] = CREAM,
    bg: tuple[int, int, int] = (42, 49, 61),
    border: tuple[int, int, int] = (91, 103, 120),
    padding: tuple[int, int] = (10, 5),
    min_width: int = 0,
) -> pygame.Rect:
    font = fonts().get(size, bold=True)
    text_width, text_height = font.size(label)
    width = max(min_width, text_width + padding[0] * 2)
    height = text_height + padding[1] * 2
    rect = pygame.Rect(0, 0, width, height)
    rect.center = center
    pygame.draw.rect(surface, bg, rect, border_radius=6)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=6)
    draw_text(surface, label, size, rect.center, color, anchor="center")
    return rect


def draw_coin_icon(
    surface: pygame.Surface,
    center: tuple[float, float],
    radius: int,
    *,
    phase: float = 0.0,
) -> None:
    """Una moneda pixel-art que gira sobre su eje."""
    width = max(2, int(radius * (0.28 + 0.72 * abs(math.cos(phase)))))
    rect = pygame.Rect(0, 0, width, radius * 2)
    rect.center = (round(center[0]), round(center[1]))
    pygame.draw.ellipse(surface, (173, 111, 32), rect.inflate(4, 4))
    pygame.draw.ellipse(surface, (255, 199, 67), rect)
    inner = rect.inflate(-max(2, width // 3), -5)
    if inner.width > 1:
        pygame.draw.ellipse(surface, (255, 231, 130), inner, width=max(1, radius // 5))
    if width > radius:
        mark = pygame.Rect(0, 0, max(2, radius // 4), max(4, int(radius * 0.8)))
        mark.center = rect.center
        pygame.draw.rect(surface, (196, 133, 38), mark, border_radius=2)


def draw_heart(
    surface: pygame.Surface,
    center: tuple[float, float],
    size: int,
    *,
    color: tuple[int, int, int] = (255, 102, 113),
    empty: bool = False,
    beat: float = 0.0,
) -> None:
    size = max(8, int(size * (1.0 + beat)))
    x, y = center
    dark = (70, 40, 48) if empty else (119, 42, 48)
    fill = (52, 49, 54) if empty else color
    r = size // 4
    pygame.draw.circle(surface, dark, (round(x - r), round(y - r // 2)), r + 2)
    pygame.draw.circle(surface, dark, (round(x + r), round(y - r // 2)), r + 2)
    pygame.draw.polygon(
        surface,
        dark,
        [(x - size // 2 - 1, y - size // 5), (x + size // 2 + 1, y - size // 5), (x, y + size // 2 + 2)],
    )
    pygame.draw.circle(surface, fill, (round(x - r), round(y - r // 2)), r)
    pygame.draw.circle(surface, fill, (round(x + r), round(y - r // 2)), r)
    pygame.draw.polygon(
        surface,
        fill,
        [(x - size // 2, y - size // 5), (x + size // 2, y - size // 5), (x, y + size // 2)],
    )
    if not empty:
        pygame.draw.circle(surface, (255, 186, 183), (round(x - r + 1), round(y - r // 2 - 2)), max(1, r // 3))


def draw_lightning(
    surface: pygame.Surface,
    center: tuple[float, float],
    size: float,
    color: tuple[int, int, int] = (255, 213, 85),
) -> None:
    points = [
        (center[0] + size * 0.12, center[1] - size * 0.55),
        (center[0] - size * 0.38, center[1] + size * 0.08),
        (center[0] - size * 0.03, center[1] + size * 0.08),
        (center[0] - size * 0.12, center[1] + size * 0.55),
        (center[0] + size * 0.42, center[1] - size * 0.12),
        (center[0] + size * 0.05, center[1] - size * 0.12),
    ]
    pygame.draw.polygon(surface, color, points)


def jitter(amount: float, rng: random.Random | None = None) -> float:
    rng = rng or random
    return rng.uniform(-amount, amount)


def shorten_number(value: int) -> str:
    value = int(value)
    if value < 10_000:
        return f"{value:,}".replace(",", " ")
    if value < 1_000_000:
        return f"{value / 1000:.1f}K".replace(".", ",")
    return f"{value / 1_000_000:.1f}M".replace(".", ",")


def zfill_score(value: int, length: int = 6) -> str:
    """Relleno con ceros, pero sin cortar puntuaciones grandes."""
    text = str(max(0, int(value)))
    return text.zfill(length)


def point_in_any(pos: tuple[int, int], rects: Iterable[pygame.Rect]) -> bool:
    return any(rect.collidepoint(pos) for rect in rects)
