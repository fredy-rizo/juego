"""Bucle principal, estados, reglas y pantallas de DINO RUSH."""
from __future__ import annotations

import asyncio
import math
import random

import pygame

from . import art
from .audio import Audio
from .config import (
    ACTIVE_ABILITIES,
    CORAL,
    CREAM,
    CYAN,
    DEEP_INK,
    FPS,
    GOLD,
    GROUND_Y,
    HEIGHT,
    INK,
    MUTED,
    PAPER,
    PIXELS_PER_METER,
    PLAYER_X,
    POWERUPS,
    POWER_COLORS,
    TEAL,
    TITLE,
    WIDTH,
    ZONE_INTROS,
    ZONES,
    level_target,
    speed_for_level,
)
from .entities import (
    FloatingText,
    Obstacle,
    Particle,
    Pickup,
    Player,
    make_coin_pop,
    make_crystal_pop,
    make_dust,
    make_landing_puff,
    make_level_confetti,
)
from .storage import load_save, write_save
from .utils import (
    clamp,
    draw_bar,
    draw_coin_icon,
    draw_heart,
    draw_keycap,
    draw_lightning,
    draw_panel,
    draw_text,
    draw_wrapped_text,
    fonts,
    shorten_number,
    zfill_score,
)
from .world import Background

MENU_ITEMS = [
    ("JUGAR", "play"),
    ("PODERES", "powers"),
    ("CONTROLES", "controls"),
    ("SALIR", "quit"),
]

PAUSE_ITEMS = [
    ("CONTINUAR", "resume"),
    ("REINICIAR", "restart"),
    ("SALIR AL MENÚ", "menu"),
]

GAMEOVER_ITEMS = [
    ("REINTENTAR", "retry"),
    ("MENÚ PRINCIPAL", "menu"),
]


def _roman(number: int) -> str:
    if number <= 1:
        return ""
    values = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    result = ""
    for value, symbol in values:
        while number >= value:
            result += symbol
            number -= value
    return result


class Game:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        pygame.display.set_caption(TITLE)

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.scene = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.fx = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.clock = pygame.time.Clock()
        self.running = True
        self.fullscreen = False
        self.windowed_size = (WIDTH, HEIGHT)
        self._display_scale = 1.0
        self._display_offset = (0, 0)

        self.save = load_save()
        self.audio = Audio(muted=bool(self.save.get("mute", False)))
        self.audio.play_music()
        self.dino = art.DinoArt()
        self.bg = Background()
        self.bg.set_zone(0)
        self.rng = random.Random()

        self.state = "menu"
        self.ui_time = 0.0
        self.menu_anim = 0.0
        self.menu_index = 0
        self.pause_index = 0
        self.gameover_index = 0
        self.gameover_ready = 0.0
        self.click_actions: list[tuple[pygame.Rect, str]] = []
        self.show_fps = False

        self.left_shade = self._make_left_shade()
        self.top_shade = self._make_hud_shade()
        self.bottom_shade = self._make_bottom_shade()
        self.slow_tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.slow_tint.fill((*POWER_COLORS["slow"], 32))
        self._menu_hero = [
            pygame.transform.scale(frame, (frame.get_width() * 2, frame.get_height() * 2))
            for frame in self.dino.run
        ]
        self._set_window_icon()
        if bool(self.save.get("fullscreen", False)):
            self.toggle_fullscreen()
        self._new_session()
        self.player.reset()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def _set_window_icon(self) -> None:
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.rect(icon, (26, 66, 59), (3, 9, 21, 16), border_radius=5)
        pygame.draw.rect(icon, (68, 200, 143), (5, 9, 17, 13), border_radius=4)
        pygame.draw.rect(icon, (68, 200, 143), (18, 5, 9, 12), border_radius=3)
        pygame.draw.rect(icon, (26, 66, 59), (24, 11, 6, 5), border_radius=2)
        pygame.draw.rect(icon, (246, 218, 160), (25, 12, 4, 3), border_radius=1)
        pygame.draw.rect(icon, (239, 87, 75), (17, 14, 9, 3))
        pygame.draw.rect(icon, (255, 255, 255), (21, 8, 3, 3))
        pygame.draw.rect(icon, (15, 24, 28), (22, 8, 1, 2))
        pygame.draw.rect(icon, (26, 66, 59), (7, 21, 4, 8))
        pygame.draw.rect(icon, (26, 66, 59), (16, 21, 4, 8))
        pygame.display.set_icon(icon)

    def _make_left_shade(self) -> pygame.Surface:
        surface = pygame.Surface((860, HEIGHT), pygame.SRCALPHA)
        for x in range(860):
            fade = (1.0 - x / 860) ** 1.5
            alpha = int(228 * fade)
            pygame.draw.line(surface, (7, 10, 16, alpha), (x, 0), (x, HEIGHT))
        return surface

    def _make_hud_shade(self) -> pygame.Surface:
        surface = pygame.Surface((WIDTH, 160), pygame.SRCALPHA)
        for y in range(160):
            alpha = int(105 * (1.0 - y / 160) ** 1.5)
            pygame.draw.line(surface, (8, 11, 16, alpha), (0, y), (WIDTH, y))
        return surface

    def _make_bottom_shade(self) -> pygame.Surface:
        surface = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
        for y in range(120):
            alpha = int(130 * (y / 120) ** 1.5)
            pygame.draw.line(surface, (7, 10, 15, alpha), (0, y), (WIDTH, y))
        return surface

    def _new_session(self) -> None:
        self.player = Player()
        self.obstacles: list[Obstacle] = []
        self.pickups: list[Pickup] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.toasts: list[dict] = []
        self.distance_m = 0.0
        self.bonus_score = 0
        self.coins_run = 0
        self.level = 1
        self.level_start_distance = 0.0
        self.level_goal = float(level_target(1))
        self.zone_index = 0
        self.hearts = 3
        self.max_hearts = 3
        self.energy = 55.0
        self.effects = {"shield": 0.0, "magnet": 0.0, "x2": 0.0, "wings": 0.0, "slow": 0.0}
        self.cooldowns = {"dash": 0.0, "shield": 0.0, "slow": 0.0}
        self.phoenix = False
        self.invincible = 0.0
        self.dash_time = 0.0
        self.shake_time = 0.0
        self.shake_strength = 0.0
        self.flash_time = 0.0
        self.flash_color = (255, 255, 255)
        self.play_time = 0.0
        self.level_banner_timer = 0.0
        self.level_banner_total = 1.0
        self.spawn_timer = 1.2
        self.coin_timer = 3.0
        self.powerup_timer = 7.0
        self.dust_timer = 0.0
        self.hint_text = ""
        self.hint_timer = 0.0
        self.seen_ptero = False
        self.seen_power = False
        self.abilities_used: set[str] = set()
        self.run_recorded = True
        self.session_active = False
        self.new_record = False
        self.game_over_reason = ""

    async def run(self) -> None:
        try:
            while self.running:
                raw_dt = self.clock.tick(FPS) / 1000.0
                dt = min(max(raw_dt, 0.0), 0.05)
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update(dt)
                self.render()
                self.present()
                # Cede control al navegador cada frame (necesario en pygbag/WASM).
                await asyncio.sleep(0)
        finally:
            if self.session_active and not self.run_recorded:
                self.finalize_run()
            self.save["mute"] = self.audio.muted
            write_save(self.save)
            pygame.quit()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            if self.session_active and not self.run_recorded:
                self.finalize_run()
            self.running = False
            return

        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            size = (max(640, event.w), max(360, event.h))
            self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.toggle_fullscreen()
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            muted = self.audio.toggle_mute()
            self.save["mute"] = muted
            write_save(self.save)
            if self.state == "playing":
                self._show_toast("SONIDO SILENCIADO" if muted else "SONIDO ACTIVADO", MUTED if muted else TEAL, "mute" if muted else "sound")
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_mouse_click(self._to_canvas(event.pos))
            return

        if event.type == pygame.MOUSEMOTION:
            pos = self._to_canvas(event.pos)
            for rect, action in self.click_actions:
                if rect.collidepoint(pos):
                    if action.startswith("menu:"):
                        self.menu_index = int(action.split(":")[1])
                    elif self.state == "paused" and action.startswith("pause:"):
                        self.pause_index = int(action.split(":")[1])
                    elif self.state == "gameover" and action.startswith("over:"):
                        self.gameover_index = int(action.split(":")[1])
                    break
            return

        if event.type != pygame.KEYDOWN:
            if event.type == pygame.KEYUP and self.state == "playing":
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.player.cut_jump()
            return

        if self.state == "menu":
            self._handle_menu_key(event.key)
        elif self.state in ("powers", "controls"):
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_BACKSPACE):
                self.audio.play("click")
                self.menu_index = 1 if self.state == "powers" else 2
                self.state = "menu"
        elif self.state == "playing":
            self._handle_playing_key(event.key)
        elif self.state == "paused":
            self._handle_pause_key(event.key)
        elif self.state == "gameover":
            self._handle_gameover_key(event.key)

    def _handle_menu_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(MENU_ITEMS)
            self.audio.play("click")
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(MENU_ITEMS)
            self.audio.play("click")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play("select")
            self._activate_action(MENU_ITEMS[self.menu_index][1])

    def _handle_playing_key(self, key: int) -> None:
        if key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
            self.player.queue_jump()
        elif key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            self.activate_ability("dash")
        elif key == pygame.K_e:
            self.activate_ability("shield")
        elif key == pygame.K_q:
            self.activate_ability("slow")
        elif key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = "paused"
            self.pause_index = 0
            self.audio.play("pause")
        elif key == pygame.K_r and self.player.on_ground:
            # Sin combo R todavía: reservado para futuras actualizaciones.
            pass

    def _handle_pause_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_w):
            self.pause_index = (self.pause_index - 1) % len(PAUSE_ITEMS)
            self.audio.play("click")
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.pause_index = (self.pause_index + 1) % len(PAUSE_ITEMS)
            self.audio.play("click")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.audio.play("select")
            self._activate_action(PAUSE_ITEMS[self.pause_index][1])
        elif key in (pygame.K_ESCAPE, pygame.K_p):
            self._resume()
        elif key == pygame.K_r:
            self.start_run()
        elif key == pygame.K_x:
            self._leave_to_menu()

    def _handle_gameover_key(self, key: int) -> None:
        if self.gameover_ready > 0:
            return
        if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.gameover_index = 1 - self.gameover_index
            self.audio.play("click")
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play("select")
            self._activate_action(GAMEOVER_ITEMS[self.gameover_index][1])
        elif key in (pygame.K_ESCAPE, pygame.K_x):
            self._activate_action("menu")

    def _handle_mouse_click(self, pos: tuple[int, int]) -> None:
        for rect, action in reversed(self.click_actions):
            if rect.collidepoint(pos):
                self.audio.play("select")
                self._activate_action(action)
                return

    def _activate_action(self, action: str) -> None:
        if action.startswith("ability:"):
            self.activate_ability(action.split(":", 1)[1])
            return
        if action.startswith("menu:"):
            self.menu_index = int(action.split(":")[1])
            action = MENU_ITEMS[self.menu_index][1]
        elif action.startswith("pause:"):
            self.pause_index = int(action.split(":")[1])
            action = PAUSE_ITEMS[self.pause_index][1]
        elif action.startswith("over:"):
            self.gameover_index = int(action.split(":")[1])
            action = GAMEOVER_ITEMS[self.gameover_index][1]

        if action == "play":
            self.start_run()
        elif action == "powers":
            self.state = "powers"
        elif action == "controls":
            self.state = "controls"
        elif action == "quit":
            if self.session_active and not self.run_recorded:
                self.finalize_run()
            self.running = False
        elif action == "back":
            self.state = "menu"
        elif action == "resume":
            self._resume()
        elif action == "restart":
            self.start_run()
        elif action == "menu":
            self._leave_to_menu()
        elif action == "retry":
            self.start_run()

    def _resume(self) -> None:
        if self.state == "paused":
            self.state = "playing"
            self.audio.play("select")

    def _leave_to_menu(self) -> None:
        if self.session_active and not self.run_recorded:
            self.finalize_run()
        self.session_active = False
        self.state = "menu"
        self.menu_index = 0
        self.player.reset()
        self.bg.set_zone(0)

    def _handle_quit(self) -> None:
        if self.session_active and not self.run_recorded:
            self.finalize_run()
        self.running = False

    # ------------------------------------------------------------------
    # Acciones de partida
    # ------------------------------------------------------------------
    def start_run(self) -> None:
        if self.session_active and not self.run_recorded:
            self.finalize_run()
        self._new_session()
        self.state = "playing"
        self.session_active = True
        self.run_recorded = False
        self.player.reset()
        self.bg.scroll = 0.0
        self.bg.time = 0.0
        self.bg.set_zone(0)
        self.level = 1
        self.distance_m = 0.0
        self.level_start_distance = 0.0
        self.level_goal = float(level_target(1))
        self.zone_index = 0
        self._begin_level(1, initial=True)
        self.pause_index = 0
        self.gameover_index = 0
        self._set_hint("ESPACIO para saltar · ABAJO para agacharse", 6.5)
        self.audio.play_music()

    def _begin_level(self, level: int, *, initial: bool = False) -> None:
        self.level = level
        self.zone_index = (level - 1) % len(ZONES)
        self.zone_index = self.zone_index if self.zone_index >= 0 else 0
        self.bg.set_zone(self.zone_index)
        self.level_start_distance = self.distance_m
        self.level_goal = self.distance_m + level_target(level)
        self.level_banner_timer = 2.55 if initial else 2.35
        self.level_banner_total = self.level_banner_timer
        self.spawn_timer = max(self.spawn_timer, 1.4 if initial else 1.5)
        self.coin_timer = max(self.coin_timer, 2.3)
        self.powerup_timer = max(self.powerup_timer, 5.8)
        self.player.invincible = 0.0
        if not initial:
            self.invincible = max(self.invincible, 1.1)
        self.wings_just_expired = False

    def _advance_level(self) -> None:
        completed = self.level
        self.bonus_score += 550 * completed
        self.hearts = min(self.max_hearts, self.hearts + 1)
        self.energy = min(100.0, self.energy + 26.0)
        for obstacle in self.obstacles:
            self.particles.extend(obstacle.explosion_particles(self.rng))
        self.obstacles.clear()
        self.invincible = max(self.invincible, 1.4)
        self.level = completed + 1
        self.zone_index = (self.level - 1) % len(ZONES)
        self.bg.set_zone(self.zone_index)
        self.level_start_distance = self.distance_m
        self.level_goal = self.distance_m + level_target(self.level)
        self.level_banner_timer = 2.35
        self.level_banner_total = 2.35
        self.spawn_timer = 1.55
        self.shake_time = 0.0
        self.flash_time = 0.17
        self.flash_color = ZONES[self.zone_index]["accent"]
        self.particles.extend(make_level_confetti(self.rng))
        self.audio.play("level_up")
        self._set_hint("Nivel superado: +1 corazón  ·  +26 energía", 3.4)

    def finalize_run(self) -> None:
        if self.run_recorded:
            return
        self.run_recorded = True
        previous_high = int(self.save.get("high_score", 0))
        score = self.score
        self.new_record = score > previous_high
        self.save["high_score"] = max(previous_high, score)
        self.save["best_distance"] = max(int(self.save.get("best_distance", 0)), int(self.distance_m))
        self.save["best_level"] = max(int(self.save.get("best_level", 1)), self.level)
        self.save["total_coins"] = int(self.save.get("total_coins", 0)) + self.coins_run
        self.save["games"] = int(self.save.get("games", 0)) + 1
        write_save(self.save)

    def _game_over(self) -> None:
        if self.state == "gameover":
            return
        self.state = "gameover"
        self.gameover_ready = 0.35
        self.gameover_index = 0
        self.game_over_reason = "Te quedaste sin corazones"
        self.audio.play("game_over")
        self.finalize_run()
        self.session_active = False

    def toggle_fullscreen(self) -> None:
        try:
            if self.fullscreen:
                self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                self.fullscreen = False
            else:
                self.windowed_size = self.screen.get_size()
                info = pygame.display.Info()
                self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
                self.fullscreen = True
            self.save["fullscreen"] = self.fullscreen
            write_save(self.save)
        except pygame.error:
            self.fullscreen = False

    # ------------------------------------------------------------------
    # Utilidades de sesión
    # ------------------------------------------------------------------
    @property
    def score(self) -> int:
        return int(self.distance_m * 10) + self.bonus_score

    @property
    def speed(self) -> float:
        base = speed_for_level(self.level)
        in_level = max(0.0, self.distance_m - self.level_start_distance)
        base += min(38.0, in_level * 0.055)
        if self.effects["slow"] > 0:
            base *= 0.52
        if self.dash_time > 0:
            base *= 1.42
        return base

    @property
    def base_speed(self) -> float:
        base = speed_for_level(self.level)
        in_level = max(0.0, self.distance_m - self.level_start_distance)
        return base + min(38.0, in_level * 0.055)

    def _zone_label(self) -> str:
        zone = ZONES[self.zone_index]["name"]
        cycle = (self.level - 1) // len(ZONES) + 1
        suffix = _roman(cycle)
        return f"{zone} · {suffix}" if suffix else zone

    def _set_hint(self, text: str, duration: float = 3.0) -> None:
        self.hint_text = text
        self.hint_timer = duration

    def _show_toast(
        self,
        text: str,
        color: tuple[int, int, int],
        icon: str | None = None,
        *,
        duration: float = 2.6,
    ) -> None:
        self.toasts.append({"text": text, "color": color, "icon": icon, "life": duration, "max_life": duration})
        if len(self.toasts) > 3:
            self.toasts.pop(0)

    def _add_text(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[int, int, int],
        *,
        size: int = 18,
        life: float = 0.85,
    ) -> None:
        self.floating_texts.append(FloatingText(text, x, y, color, size=size, life=life))

    def _add_particles(self, particles: list[Particle]) -> None:
        if len(self.particles) > 280:
            self.particles = self.particles[-220:]
        self.particles.extend(particles)

    # ------------------------------------------------------------------
    # Actualización
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.ui_time += dt
        self.gameover_ready = max(0.0, self.gameover_ready - dt)
        if self.state in ("menu", "powers", "controls"):
            self.bg.set_zone(0)
            self.bg.update(dt, 58.0 if self.state == "menu" else 22.0)
            self.menu_anim += dt
            return
        if self.state == "playing":
            self._update_playing(dt)
            return
        # Pausa y fin de partida congelan el mundo, pero permiten animar la interfaz.
        if self.state == "gameover":
            for toast in self.toasts:
                toast["life"] = max(0.0, toast["life"] - dt)
            self.toasts = [toast for toast in self.toasts if toast["life"] > 0]

    def _update_playing(self, dt: float) -> None:
        self.play_time += dt
        self.invincible = max(0.0, self.invincible - dt)
        self.dash_time = max(0.0, self.dash_time - dt)
        self.level_banner_timer = max(0.0, self.level_banner_timer - dt)
        self.shake_time = max(0.0, self.shake_time - dt)
        self.flash_time = max(0.0, self.flash_time - dt)
        self.hint_timer = max(0.0, self.hint_timer - dt)

        for name in self.effects:
            self.effects[name] = max(0.0, self.effects[name] - dt)
        for name in self.cooldowns:
            self.cooldowns[name] = max(0.0, self.cooldowns[name] - dt)
        self.energy = min(100.0, self.energy + 2.6 * dt)

        for toast in self.toasts:
            toast["life"] = max(0.0, toast["life"] - dt)
        self.toasts = [toast for toast in self.toasts if toast["life"] > 0]

        keys = pygame.key.get_pressed()
        duck_held = keys[pygame.K_DOWN] or keys[pygame.K_s]
        events = self.player.update(dt, duck_held, self.effects["wings"] > 0)
        self._handle_player_events(events)

        world_speed = self.speed
        self.distance_m += world_speed * dt / PIXELS_PER_METER
        self.bg.update(dt, world_speed)
        slow_factor = 0.52 if self.effects["slow"] > 0 else 1.0
        spawn_dt = dt * slow_factor

        for obstacle in self.obstacles:
            obstacle.update(dt, world_speed * (1.06 if obstacle.kind == "ptero_low" else 1.0))
        for pickup in self.pickups:
            target = (self.player.x, self.player.y - self.player.height / 2)
            pickup.update(dt, world_speed, target if self.effects["magnet"] > 0 else None)

        self._update_particles(dt)

        if self.level_banner_timer <= 0.85:
            self.spawn_timer -= spawn_dt
            self.coin_timer -= spawn_dt
            self.powerup_timer -= spawn_dt
            if self.spawn_timer <= 0:
                self._spawn_obstacle()
            if self.coin_timer <= 0:
                self._spawn_coin_pattern()
            if self.powerup_timer <= 0:
                self._spawn_powerup()

        self._update_dust(dt)
        self._check_pickup_collisions()
        self._check_obstacle_collisions()

        self.obstacles = [obstacle for obstacle in self.obstacles if not obstacle.offscreen]
        self.pickups = [pickup for pickup in self.pickups if not pickup.offscreen]

        if self.distance_m >= self.level_goal and self.state == "playing":
            self._advance_level()

        if self.hearts <= 0 and self.state == "playing":
            self._game_over()

    def _handle_player_events(self, events: list[str]) -> None:
        palette = ZONES[self.zone_index]
        for event in events:
            if event == "jump":
                self.audio.play("jump")
                self._add_particles(
                    [
                        make_dust(PLAYER_X - 8, GROUND_Y, self.rng, color=palette["ground_dark"])
                        for _ in range(3)
                    ]
                )
            elif event == "double_jump":
                self.audio.play("double_jump")
                self._add_text("¡DOBLE SALTO!", self.player.x + 20, self.player.y - 100, POWER_COLORS["wings"], size=16, life=0.7)
                for _ in range(8):
                    angle = self.rng.uniform(0, math.tau)
                    self._add_particles(
                        [
                            Particle(
                                self.player.x,
                                self.player.y - 25,
                                math.cos(angle) * self.rng.uniform(40, 130),
                                math.sin(angle) * self.rng.uniform(30, 110),
                                self.rng.uniform(0.25, 0.55),
                                POWER_COLORS["wings"],
                                self.rng.uniform(1.5, 3.2),
                                gravity=200,
                                shape="spark",
                            )
                        ]
                    )
            elif event == "land":
                self.audio.play("land")
                self._add_particles(make_landing_puff(self.player.x, GROUND_Y, self.rng, palette["ground_dark"]))
                self.shake_time = max(self.shake_time, 0.08)
                self.shake_strength = max(self.shake_strength, 2.5)

    def _update_dust(self, dt: float) -> None:
        palette = ZONES[self.zone_index]
        if self.player.on_ground:
            self.dust_timer -= dt
            if self.dust_timer <= 0:
                interval = 0.075 if self.player.ducking else 0.15
                self.dust_timer = interval
                self._add_particles([make_dust(self.player.x - 20, GROUND_Y, self.rng, color=palette["ground_dark"])])

    def _update_particles(self, dt: float) -> None:
        self.particles = [particle for particle in self.particles if particle.update(dt)]
        self.floating_texts = [text for text in self.floating_texts if text.update(dt)]

    # ------------------------------------------------------------------
    # Generación de obstáculos y objetos
    # ------------------------------------------------------------------
    def _spawn_obstacle(self) -> None:
        distance = self.distance_m
        options = [("cactus_small", 30), ("rock", 15)]
        if self.level >= 2 or distance > 140:
            options.append(("cactus_tall", 20))
        if self.level >= 2 or distance > 190:
            options.append(("ptero_low", 17))
        if self.level >= 2 or distance > 280:
            options.append(("cactus_pair", 19))
        if self.level >= 4:
            options.append(("rock_pair", 8))

        names = [name for name, _weight in options]
        weights = [weight for _name, weight in options]
        kind = self.rng.choices(names, weights=weights, k=1)[0]
        base_x = WIDTH + 80
        if kind == "cactus_pair":
            spacing = self.rng.uniform(45, 58)
            self.obstacles.append(Obstacle("cactus_small", base_x, self.zone_index))
            self.obstacles.append(Obstacle("cactus_small", base_x + spacing, self.zone_index, t=self.rng.random()))
        elif kind == "rock_pair":
            spacing = self.rng.uniform(54, 68)
            self.obstacles.append(Obstacle("rock", base_x, self.zone_index))
            self.obstacles.append(Obstacle("rock", base_x + spacing, self.zone_index, t=self.rng.random()))
        else:
            obstacle = Obstacle(kind, base_x, self.zone_index, t=self.rng.random())
            self.obstacles.append(obstacle)
            if kind == "ptero_low" and not self.seen_ptero:
                self.seen_ptero = True
                self._set_hint("ABAJO para esquivar al pterodáctilo", 3.2)

        difficulty = min(1.0, (self.level - 1) / 13 + distance / 7000)
        low = max(0.78, 1.58 - difficulty * 0.66)
        high = max(1.12, 2.3 - difficulty * 0.85)
        self.spawn_timer = self.rng.uniform(low, high)

    def _pickup_blocked(self, x: float, y: float) -> bool:
        for obstacle in self.obstacles:
            if abs(obstacle.x - x) < obstacle.hit_w / 2 + 18 and obstacle.rect.top - 18 < y < obstacle.rect.bottom + 14:
                return True
        return False

    def _spawn_coin_pattern(self) -> None:
        pattern = self.rng.choices(
            ["line", "arc", "high", "crystal_arc"],
            weights=[28, 33, 20, 19],
            k=1,
        )[0]
        base_x = WIDTH + 110
        coins: list[Pickup] = []
        crystal: Pickup | None = None
        if pattern == "line":
            for i in range(5):
                x = base_x + i * 38
                y = GROUND_Y - 88
                if not self._pickup_blocked(x, y):
                    coins.append(Pickup("coin", x, y, phase=i * 0.7))
        elif pattern == "arc":
            heights = [62, 102, 142, 162, 142, 102, 62]
            for i, height in enumerate(heights):
                x = base_x + i * 39
                y = GROUND_Y - height
                if not self._pickup_blocked(x, y):
                    coins.append(Pickup("coin", x, y, phase=i * 0.6))
        elif pattern == "high":
            for i in range(6):
                x = base_x + i * 36
                y = GROUND_Y - (150 + (i % 3) * 4)
                if not self._pickup_blocked(x, y):
                    coins.append(Pickup("coin", x, y, phase=i * 0.8))
        else:
            heights = [85, 125, 165, 190, 165, 125, 85]
            for i, height in enumerate(heights):
                x = base_x + i * 40
                y = GROUND_Y - height
                if not self._pickup_blocked(x, y):
                    coins.append(Pickup("coin", x, y, phase=i * 0.55))
            cx = base_x + 3 * 40
            cy = GROUND_Y - 190
            if not self._pickup_blocked(cx, cy):
                crystal = Pickup("crystal", cx, cy, phase=1.5)
        self.pickups.extend(coins)
        if crystal is not None:
            self.pickups.append(crystal)

        difficulty = min(1.0, (self.level - 1) / 15)
        self.coin_timer = self.rng.uniform(2.2, 3.8) - difficulty * 0.5

    def _spawn_powerup(self) -> None:
        if any(p.kind == "power" for p in self.pickups):
            self.powerup_timer = 0.7
            return
        names = []
        weights = []
        for name, data in POWERUPS.items():
            weight = data["weight"]
            if name == "phoenix" and self.phoenix:
                weight = 0
            if weight > 0:
                names.append(name)
                weights.append(weight)
        if not names:
            self.powerup_timer = 4.0
            return
        kind = self.rng.choices(names, weights=weights, k=1)[0]
        x = WIDTH + 80
        if self.obstacles and any(abs(ob.x - x) < 100 for ob in self.obstacles):
            x += 120
        y = GROUND_Y - self.rng.uniform(118, 180)
        self.pickups.append(Pickup("power", x, y, subtype=kind, phase=self.rng.random() * math.tau))
        self.powerup_timer = self.rng.uniform(10.5, 16.5)

    # ------------------------------------------------------------------
    # Colisiones y poderes
    # ------------------------------------------------------------------
    def _check_pickup_collisions(self) -> None:
        player_rect = self.player.rect.inflate(10, 6)
        remaining: list[Pickup] = []
        for pickup in self.pickups:
            if pickup.collision(player_rect):
                self._collect_pickup(pickup)
            else:
                remaining.append(pickup)
        self.pickups = remaining

    def _collect_pickup(self, pickup: Pickup) -> None:
        multiplier = 2 if self.effects["x2"] > 0 else 1
        self.audio.play("coin" if pickup.kind == "coin" else "crystal")
        if pickup.kind == "coin":
            points = 50 * multiplier
            self.bonus_score += points
            self.coins_run += 1
            self.energy = min(100.0, self.energy + 3.5)
            self._add_text(f"+{points}", pickup.x, pickup.y - 18, GOLD, size=15, life=0.65)
            self._add_particles(make_coin_pop(pickup.x, pickup.y, self.rng))
        elif pickup.kind == "crystal":
            self.bonus_score += 20 * multiplier
            self.energy = min(100.0, self.energy + 18.0)
            self._add_text(f"ENERGÍA +18", pickup.x, pickup.y - 24, CYAN, size=15, life=0.8)
            self._add_particles(make_crystal_pop(pickup.x, pickup.y, self.rng))
        else:
            self._apply_powerup(pickup.subtype)
            self._add_text(POWERUPS[pickup.subtype]["name"], pickup.x, pickup.y - 35, POWERUPS[pickup.subtype]["color"], size=16, life=1.0)
            self._add_particles(make_crystal_pop(pickup.x, pickup.y, self.rng))

    def _apply_powerup(self, kind: str) -> None:
        data = POWERUPS[kind]
        duration = data["duration"]
        color = data["color"]
        if kind == "phoenix":
            if self.phoenix:
                self.hearts = min(self.max_hearts, self.hearts + 1)
                self.bonus_score += 150
                self._show_toast("FÉNIX EXTRA · +1 CORAZÓN", color, "phoenix")
            else:
                self.phoenix = True
                self._show_toast("PLUMA FÉNIX · segunda oportunidad", color, "phoenix", duration=3.0)
        else:
            self.effects[kind] = max(self.effects[kind], duration)
            suffix = "s" if kind != "slow" else "s"
            self._show_toast(f"{data['name']} ACTIVADO · {int(math.ceil(duration))}{suffix}", color, data["icon"], duration=2.8)
        self.audio.play("power")
        self.flash_time = max(self.flash_time, 0.12)
        self.flash_color = color

    def activate_ability(self, kind: str) -> None:
        if self.state != "playing":
            return
        data = ACTIVE_ABILITIES[kind]
        if self.cooldowns[kind] > 0:
            self.audio.play("click")
            self._add_text("RECARGANDO", self.player.x, self.player.y - self.player.height - 24, MUTED, size=13, life=0.6)
            return
        if kind == "shield" and self.effects["shield"] > 0:
            self._add_text("ESCUDO ACTIVO", self.player.x, self.player.y - self.player.height - 24, POWER_COLORS["shield"], size=13, life=0.7)
            return
        if kind == "slow" and self.effects["slow"] > 0:
            self._add_text("TIEMPO YA RALENTIZADO", self.player.x, self.player.y - self.player.height - 24, POWER_COLORS["slow"], size=13, life=0.7)
            return
        if self.energy < data["cost"]:
            self.audio.play("click")
            self._add_text("SIN ENERGÍA", self.player.x, self.player.y - self.player.height - 24, CORAL, size=14, life=0.65)
            return

        self.energy -= data["cost"]
        self.cooldowns[kind] = data["cooldown"]
        self.abilities_used.add(kind)
        if kind == "dash":
            self.dash_time = 0.85
            self.invincible = max(self.invincible, 0.9)
            self.shake_time = max(self.shake_time, 0.16)
            self.shake_strength = max(self.shake_strength, 4)
            self.audio.play("dash")
            self._add_text("¡DASH!", self.player.x + 20, self.player.y - self.player.height - 10, POWER_COLORS["dash"], size=18, life=0.6)
            for _ in range(12):
                self._add_particles(
                    [
                        Particle(
                            self.player.x - self.rng.uniform(0, 50),
                            self.player.y - self.rng.uniform(10, self.player.height),
                            self.rng.uniform(-360, -100),
                            self.rng.uniform(-35, 35),
                            self.rng.uniform(0.18, 0.4),
                            POWER_COLORS["dash"],
                            self.rng.uniform(1.5, 3.8),
                            shape="line",
                        )
                    ]
                )
        elif kind == "shield":
            self.effects["shield"] = 11.0
            self.audio.play("shield")
            self._show_toast("ESCUDO ACTIVO · 11s", POWER_COLORS["shield"], "shield", duration=2.2)
        elif kind == "slow":
            self.effects["slow"] = 5.0
            self.audio.play("slow")
            self.flash_time = 0.13
            self.flash_color = POWER_COLORS["slow"]
            self._show_toast("TIEMPO LENTO · 5s", POWER_COLORS["slow"], "slow", duration=2.2)

    def _destroy_obstacle(self, obstacle: Obstacle, *, color: tuple[int, int, int] | None = None, award: int = 0) -> None:
        if obstacle in self.obstacles:
            self.obstacles.remove(obstacle)
        self._add_particles(obstacle.explosion_particles(self.rng))
        if award:
            self.bonus_score += award
            self._add_text(f"+{award}", obstacle.x, obstacle.y_center - 20, color or GOLD, size=14, life=0.6)

    def _check_obstacle_collisions(self) -> None:
        p_rect = self.player.rect.inflate(-8, -3)
        for obstacle in list(self.obstacles):
            if self.player.rect.left > obstacle.rect.right + 40 and not obstacle.passed:
                obstacle.passed = True
                self.bonus_score += 8 + self.level * 2
            if not p_rect.colliderect(obstacle.rect.inflate(-4, -4)):
                continue
            if self.dash_time > 0:
                self._destroy_obstacle(obstacle, color=POWER_COLORS["dash"], award=15)
                self.audio.play("smash")
            elif self.invincible > 0:
                continue
            elif self.effects["shield"] > 0:
                self.effects["shield"] = 0.0
                self.invincible = max(self.invincible, 0.85)
                self._destroy_obstacle(obstacle, color=POWER_COLORS["shield"], award=10)
                self.flash_time = 0.12
                self.flash_color = POWER_COLORS["shield"]
                self.shake_time = 0.18
                self.shake_strength = 6
                self.audio.play("shield_break")
                self._show_toast("ESCUDO DESTRUIDO", POWER_COLORS["shield"], "shield", duration=1.8)
            else:
                self._damage(obstacle)
                if self.state != "playing":
                    break

    def _damage(self, obstacle: Obstacle) -> None:
        self.hearts = max(0, self.hearts - 1)
        self.energy = max(0.0, self.energy - 22.0)
        self.invincible = 2.0
        self.shake_time = 0.38
        self.shake_strength = 14
        self.flash_time = 0.18
        self.flash_color = (255, 86, 76)
        self.audio.play("hit")
        self._add_text("-1 CORAZÓN", self.player.x, self.player.y - self.player.height - 30, CORAL, size=18, life=1.0)
        self._add_particles(obstacle.explosion_particles(self.rng))
        if obstacle in self.obstacles:
            self.obstacles.remove(obstacle)
        if self.hearts <= 0:
            if self.phoenix:
                self.phoenix = False
                self.hearts = 1
                self.invincible = 2.8
                self.flash_time = 0.45
                self.flash_color = POWER_COLORS["phoenix"]
                self.shake_time = 0.45
                self.shake_strength = 20
                self.audio.play("phoenix")
                self._show_toast("¡FÉNIX! VUELVES A LA VIDA", POWER_COLORS["phoenix"], "phoenix", duration=3.2)
                for _ in range(30):
                    angle = self.rng.uniform(0, math.tau)
                    self.particles.append(
                        Particle(
                            self.player.x,
                            self.player.y - 40,
                            math.cos(angle) * self.rng.uniform(70, 250),
                            math.sin(angle) * self.rng.uniform(70, 260) - 60,
                            self.rng.uniform(0.4, 1.0),
                            self.rng.choice([POWER_COLORS["phoenix"], GOLD, CREAM]),
                            self.rng.uniform(2, 5),
                            gravity=300,
                            shape=self.rng.choice(["spark", "square", "circle"]),
                        )
                    )
            else:
                self._game_over()

    def _update_toasts(self, dt: float) -> None:
        # Se mantiene por compatibilidad con versiones anteriores de la lógica.
        for toast in self.toasts:
            toast["life"] -= dt
        self.toasts = [toast for toast in self.toasts if toast["life"] > 0]

    # ------------------------------------------------------------------
    # Dibujado general
    # ------------------------------------------------------------------
    def render(self) -> None:
        self.click_actions.clear()
        if self.state in ("menu", "powers", "controls"):
            self._render_menu()
        else:
            self._render_game()

        if self.state == "paused":
            self._render_pause()
        elif self.state == "gameover":
            self._render_gameover()

        if self.show_fps:
            draw_text(
                self.canvas,
                f"{self.clock.get_fps():.0f} FPS",
                13,
                (12, HEIGHT - 16),
                CREAM,
                anchor="bottomleft",
                mono=True,
                shadow=DEEP_INK,
            )

        self.present()

    def present(self) -> None:
        window_w, window_h = self.screen.get_size()
        scale = min(window_w / WIDTH, window_h / HEIGHT)
        scale = max(0.1, scale)
        display_w = int(WIDTH * scale)
        display_h = int(HEIGHT * scale)
        offset = ((window_w - display_w) // 2, (window_h - display_h) // 2)
        self._display_scale = scale
        self._display_offset = offset
        if display_w == WIDTH and display_h == HEIGHT:
            self.screen.blit(self.canvas, (0, 0))
        else:
            self.screen.fill((5, 7, 11))
            scaled = pygame.transform.scale(self.canvas, (display_w, display_h))
            self.screen.blit(scaled, offset)
        pygame.display.flip()

    def _to_canvas(self, pos: tuple[int, int]) -> tuple[int, int]:
        scale = max(0.1, self._display_scale)
        x = (pos[0] - self._display_offset[0]) / scale
        y = (pos[1] - self._display_offset[1]) / scale
        return int(x), int(y)

    def _dim_overlay(self, alpha: int) -> pygame.Surface:
        if not hasattr(self, "_dim_cache"):
            self._dim_cache: dict[int, pygame.Surface] = {}
        if alpha not in self._dim_cache:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((6, 9, 14, alpha))
            self._dim_cache[alpha] = overlay
        return self._dim_cache[alpha]

    # ------------------------------------------------------------------
    # Menú principal y pantallas de información
    # ------------------------------------------------------------------
    def _render_menu(self) -> None:
        self.bg.draw(self.canvas)
        if self.state == "menu":
            self._draw_menu_hero()
        self.canvas.blit(self.left_shade, (0, 0))
        if self.state == "menu":
            self._draw_menu_content()
        else:
            self.canvas.blit(self._dim_overlay(232), (0, 0))
            if self.state == "powers":
                self._draw_powers_screen()
            else:
                self._draw_controls_screen()
        art.draw_vignette(self.canvas, 120 if self.state == "menu" else 80)

    def _draw_menu_hero(self) -> None:
        # Halos y objetos flotantes alrededor del protagonista.
        art.draw_glow(self.canvas, (958, 512), 95, ZONES[0]["sun_glow"], intensity=24)
        art.draw_power_orb(self.canvas, (810, 343 + math.sin(self.menu_anim * 1.9) * 7), "wings", self.menu_anim)
        art.draw_power_orb(self.canvas, (1136, 385 + math.sin(self.menu_anim * 1.7 + 1.3) * 8), "shield", self.menu_anim + 1.1)
        art.draw_crystal(self.canvas, (1080, 285 + math.sin(self.menu_anim * 2.2) * 5), self.menu_anim, phase=0.5)
        for i in range(5):
            x = 1018 + i * 32
            y = 494 + math.sin(self.menu_anim * 2 + i * 0.8) * (5 + i)
            draw_coin_icon(self.canvas, (x, y), 10, phase=self.menu_anim * 3 + i)

        # Sombra del héroe.
        shadow = pygame.Surface((230, 38), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (11, 13, 17, 110), (15, 12, 200, 16))
        self.canvas.blit(shadow, (844, GROUND_Y - 14))

        frame = self._menu_hero[int(self.menu_anim * 9) % len(self._menu_hero)]
        bob = -3 if int(self.menu_anim * 9) % 4 in (1, 3) else 0
        self.canvas.blit(frame, frame.get_rect(midbottom=(958, GROUND_Y + 8 + bob)))

        # Rastro de velocidad decorativo.
        for i in range(4):
            y = 470 + i * 23
            length = 42 + i * 18
            pygame.draw.line(self.canvas, (255, 213, 127), (1140 + i * 8, y), (1140 + i * 8 + length, y), 2)

    def _draw_menu_content(self) -> None:
        # Pequeño rótulo superior.
        pygame.draw.line(self.canvas, GOLD, (94, 108), (122, 108), 2)
        draw_text(self.canvas, "ARCADE PREHISTÓRICO", 13, (132, 100), GOLD, bold=True)

        # Título de dos colores.
        title_size = 104
        title_font = fonts().get(title_size, bold=True)
        dino_width = title_font.size("DINO")[0]
        draw_text(
            self.canvas,
            "DINO",
            title_size,
            (92, 124),
            CREAM,
            shadow=(7, 10, 17),
            shadow_offset=(5, 6),
        )
        draw_text(
            self.canvas,
            "RUSH",
            title_size,
            (92 + dino_width + 20, 124),
            GOLD,
            shadow=(7, 10, 17),
            shadow_offset=(5, 6),
        )
        pygame.draw.line(self.canvas, (255, 205, 92, 120), (96, 264), (535, 264), 2)
        draw_text(
            self.canvas,
            "PODERES DEL PASADO",
            18,
            (96, 278),
            PAPER,
        )

        start_y = 326
        for index, (label, _action) in enumerate(MENU_ITEMS):
            rect = pygame.Rect(94, start_y + index * 62, 424, 52)
            self._draw_menu_option(rect, label, index, index == self.menu_index)
            self.click_actions.append((rect, f"menu:{index}"))

        # Tarjeta de récords.
        card = pygame.Rect(94, 590, 424, 68)
        draw_panel(self.canvas, card, fill=(11, 15, 21, 178), border=(255, 255, 255, 20), radius=14)
        draw_text(self.canvas, "RÉCORD", 11, (card.x + 18, card.y + 12), MUTED)
        draw_text(
            self.canvas,
            zfill_score(int(self.save.get("high_score", 0)), 6),
            26,
            (card.x + 18, card.y + 28),
            GOLD,
            mono=True,
        )
        pygame.draw.line(self.canvas, (255, 255, 255, 28), (card.x + 215, card.y + 14), (card.x + 215, card.y + 54), 1)
        draw_text(self.canvas, "MEJOR NIVEL", 10, (card.x + 236, card.y + 12), MUTED)
        draw_text(self.canvas, f"{int(self.save.get('best_level', 1)):02d}", 20, (card.x + 236, card.y + 30), CREAM, mono=True)
        draw_text(self.canvas, "MONEDAS", 10, (card.x + 334, card.y + 12), MUTED)
        draw_text(self.canvas, shorten_number(int(self.save.get("total_coins", 0))), 20, (card.x + 334, card.y + 30), CREAM, mono=True)

        draw_text(
            self.canvas,
            "↑ ↓  ELEGIR      ENTER  CONFIRMAR      F11  PANTALLA COMPLETA",
            12,
            (94, 681),
            (223, 214, 194),
            shadow=(8, 10, 15),
        )
        draw_text(self.canvas, "v1.0 · PYTHON ARCADE", 11, (WIDTH - 28, 681), MUTED, anchor="topright", mono=True)
        if self.audio.available:
            icon = "mute" if self.audio.muted else "sound"
            art.draw_icon(self.canvas, icon, (WIDTH - 48, 645), 17, MUTED if self.audio.muted else PAPER)
            draw_text(self.canvas, "M", 11, (WIDTH - 34, 639), MUTED)

    def _draw_menu_option(self, rect: pygame.Rect, label: str, index: int, selected: bool) -> None:
        if selected:
            draw_panel(self.canvas, rect, fill=(*GOLD, 238), border=(255, 240, 190, 220), radius=12, border_width=1)
            pygame.draw.polygon(
                self.canvas,
                INK,
                [(rect.x + 20, rect.centery - 7), (rect.x + 31, rect.centery), (rect.x + 20, rect.centery + 7)],
            )
            draw_text(self.canvas, label, 22, (rect.x + 48, rect.centery), INK, anchor="midleft")
            draw_text(
                self.canvas,
                f"{index + 1:02d}",
                12,
                (rect.right - 18, rect.centery),
                (101, 78, 31),
                anchor="midright",
                mono=True,
            )
        else:
            draw_panel(self.canvas, rect, fill=(10, 14, 20, 190), border=(255, 255, 255, 24), radius=12, border_width=1)
            draw_text(self.canvas, label, 22, (rect.x + 48, rect.centery), CREAM, anchor="midleft")
            draw_text(
                self.canvas,
                f"{index + 1:02d}",
                12,
                (rect.right - 18, rect.centery),
                MUTED,
                anchor="midright",
                mono=True,
            )

    def _draw_back_button(self) -> None:
        rect = pygame.Rect(1034, 42, 202, 42)
        draw_panel(self.canvas, rect, fill=(16, 22, 31, 210), border=(255, 255, 255, 34), radius=10)
        draw_text(self.canvas, "ESC", 12, (rect.x + 18, rect.centery), GOLD, anchor="midleft", mono=True)
        draw_text(self.canvas, "VOLVER", 13, (rect.right - 18, rect.centery), CREAM, anchor="midright")
        self.click_actions.append((rect, "back"))

    def _draw_powers_screen(self) -> None:
        draw_text(self.canvas, "PODERES", 52, (46, 34), CREAM, shadow=(6, 9, 15), shadow_offset=(4, 5))
        draw_text(
            self.canvas,
            "Las habilidades gastan energía. Las mejoras aparecen flotando en el desierto.",
            15,
            (48, 96),
            PAPER,
        )
        self._draw_back_button()

        draw_text(self.canvas, "HABILIDADES ACTIVAS", 12, (46, 129), GOLD, shadow=None)
        pygame.draw.line(self.canvas, (255, 205, 92, 75), (46, 146), (270, 146), 1)
        for i, (kind, data) in enumerate(ACTIVE_ABILITIES.items()):
            rect = pygame.Rect(44 + i * 402, 158, 376, 150)
            self._draw_ability_info_card(rect, kind, data)

        draw_text(self.canvas, "MEJORAS QUE APARECEN", 12, (46, 327), GOLD, shadow=None)
        pygame.draw.line(self.canvas, (255, 205, 92, 75), (46, 344), (292, 344), 1)
        for i, (kind, data) in enumerate(POWERUPS.items()):
            column = i % 3
            row = i // 3
            rect = pygame.Rect(44 + column * 402, 358 + row * 126, 376, 112)
            self._draw_improvement_card(rect, kind, data)

        draw_text(
            self.canvas,
            "La energía se recarga sola y al recoger monedas. Atrae cristales para llenarla más rápido.",
            13,
            (WIDTH // 2, 631),
            MUTED,
            anchor="center",
        )
        draw_text(self.canvas, "ESC · VOLVER AL MENÚ", 12, (WIDTH // 2, 674), PAPER, anchor="center", mono=True)

    def _draw_ability_info_card(self, rect: pygame.Rect, kind: str, data: dict) -> None:
        color = data["color"]
        draw_panel(self.canvas, rect, fill=(19, 25, 35, 230), border=(*color, 85), radius=16)
        icon_center = (rect.x + 42, rect.y + 43)
        pygame.draw.circle(self.canvas, (9, 14, 20), icon_center, 27)
        pygame.draw.circle(self.canvas, (*color, 150), icon_center, 27, width=2)
        art.draw_icon(self.canvas, data["icon"], icon_center, 28, color)
        draw_text(self.canvas, data["name"], 19, (rect.x + 78, rect.y + 23), CREAM)
        key_w = fonts().get(11, bold=True).size(data["key"])[0]
        draw_keycap(
            self.canvas,
            data["key"],
            (rect.right - 16 - max(20, key_w // 2 + 11), rect.y + 31),
            size=10,
            color=color,
            bg=(9, 13, 19),
            border=(*color, 70),
            padding=(9, 4),
        )
        draw_wrapped_text(
            self.canvas,
            data["desc"],
            13,
            MUTED,
            pygame.Rect(rect.x + 78, rect.y + 54, rect.width - 96, 55),
            line_gap=2,
            bold=False,
        )
        draw_lightning(self.canvas, (rect.x + 30, rect.y + 122), 15)
        draw_text(self.canvas, f"{data['cost']} ENERGÍA", 12, (rect.x + 45, rect.y + 122), GOLD, anchor="midleft", mono=True)
        draw_text(self.canvas, f"RECARGA {data['cooldown']:.1f}s", 10, (rect.right - 16, rect.y + 122), MUTED, anchor="midright")

    def _draw_improvement_card(self, rect: pygame.Rect, kind: str, data: dict) -> None:
        color = data["color"]
        draw_panel(self.canvas, rect, fill=(17, 23, 32, 224), border=(*color, 58), radius=14)
        center = (rect.x + 37, rect.y + 42)
        pygame.draw.circle(self.canvas, (9, 13, 19), center, 23)
        pygame.draw.circle(self.canvas, (*color, 100), center, 23, width=2)
        art.draw_icon(self.canvas, data["icon"], center, 25, color)
        draw_text(self.canvas, data["name"], 16, (rect.x + 70, rect.y + 16), CREAM)
        duration = "1 uso" if kind == "phoenix" else f"{int(data['duration'])} s"
        draw_text(self.canvas, duration, 10, (rect.right - 14, rect.y + 18), color, anchor="topright", mono=True)
        draw_wrapped_text(
            self.canvas,
            data["desc"],
            12,
            MUTED,
            pygame.Rect(rect.x + 70, rect.y + 42, rect.width - 88, 56),
            line_gap=1,
            bold=False,
        )

    def _draw_controls_screen(self) -> None:
        draw_text(self.canvas, "CONTROLES", 52, (46, 34), CREAM, shadow=(6, 9, 15), shadow_offset=(4, 5))
        draw_text(
            self.canvas,
            "Todo se controla con el teclado. Aprende el ritmo, el resto es instinto.",
            15,
            (48, 96),
            PAPER,
        )
        self._draw_back_button()

        panels = [
            pygame.Rect(44, 142, 575, 468),
            pygame.Rect(645, 142, 591, 468),
        ]
        for panel in panels:
            draw_panel(self.canvas, panel, fill=(17, 22, 31, 226), border=(255, 255, 255, 20), radius=18)

        draw_text(self.canvas, "MOVIMIENTO", 12, (72, 166), GOLD)
        draw_text(self.canvas, "PODERES Y SISTEMA", 12, (673, 166), GOLD)

        left_rows = [
            ("ESPACIO", "Saltar. Mantén pulsado para alcanzar más altura."),
            ("ABAJO / S", "Agacharse. En el aire, activa una caída rápida."),
            ("ESPACIO ×2", "Doble salto. Requiere tener el poder ALAS activo."),
            ("F11", "Alternar entre ventana y pantalla completa."),
            ("M", "Silenciar o activar todos los sonidos."),
        ]
        right_rows = [
            ("SHIFT", "DASH · 25 de energía. Rompe obstáculos y te vuelve invulnerable."),
            ("E", "ESCUDO · 45 de energía. Una burbuja que absorbe un impacto."),
            ("Q", "TIEMPO LENTO · 60 de energía. Ralentiza el mundo durante 5 s."),
            ("P / ESC", "Pausar la partida."),
            ("R / X", "En pausa: reiniciar la carrera o volver al menú."),
        ]
        self._draw_control_rows(panels[0], left_rows)
        self._draw_control_rows(panels[1], right_rows)

        tip_rect = pygame.Rect(44, 626, 1192, 38)
        draw_panel(self.canvas, tip_rect, fill=(10, 14, 20, 185), border=(255, 205, 92, 32), radius=10)
        draw_text(
            self.canvas,
            "Las monedas recargan energía · Los cristales dan +18 · Cada nivel restaura un corazón",
            13,
            tip_rect.center,
            PAPER,
            anchor="center",
        )
        draw_text(self.canvas, "ESC · VOLVER AL MENÚ", 12, (WIDTH // 2, 690), MUTED, anchor="center", mono=True)

    def _draw_control_rows(self, panel: pygame.Rect, rows: list[tuple[str, str]]) -> None:
        for index, (key, description) in enumerate(rows):
            row_y = panel.y + 108 + index * 68
            if index > 0:
                pygame.draw.line(self.canvas, (255, 255, 255, 14), (panel.x + 22, row_y - 35), (panel.right - 22, row_y - 35), 1)
            key_font = fonts().get(10, bold=True)
            key_width = key_font.size(key)[0] + 22
            draw_keycap(
                self.canvas,
                key,
                (panel.x + 112, row_y),
                size=10,
                color=CREAM,
                bg=(39, 47, 60),
                border=(91, 103, 120),
                padding=(10, 6),
                min_width=min(148, key_width),
            )
            draw_wrapped_text(
                self.canvas,
                description,
                14,
                CREAM,
                pygame.Rect(panel.x + 206, row_y - 24, panel.width - 232, 48),
                line_gap=2,
                bold=False,
            )

    # ------------------------------------------------------------------
    # Escena de juego y HUD
    # ------------------------------------------------------------------
    def _render_game(self) -> None:
        self._draw_world_scene(self.scene)

        if self.shake_time > 0:
            phase = math.sin(self.ui_time * 87.0)
            phase_y = math.cos(self.ui_time * 121.0)
            decay = clamp(self.shake_time / 0.36, 0.0, 1.0)
            ox = int(phase * self.shake_strength * decay)
            oy = int(phase_y * self.shake_strength * 0.58 * decay)
        else:
            ox = oy = 0

        self.canvas.fill((6, 9, 13))
        self.canvas.blit(self.scene, (ox, oy))

        if self.effects["slow"] > 0:
            self.canvas.blit(self.slow_tint, (0, 0))
            blend = int(28 + math.sin(self.ui_time * 4) * 8)
            border = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(border, (*POWER_COLORS["slow"], blend), (0, 0, WIDTH, HEIGHT), width=8)
            self.canvas.blit(border, (0, 0))

        art.draw_vignette(self.canvas, 110)
        self.canvas.blit(self.bottom_shade, (0, HEIGHT - 120))
        self._draw_hud(self.canvas)
        self._draw_banner(self.canvas)
        self._draw_toasts(self.canvas)
        self._draw_hint(self.canvas)

        if self.flash_time > 0:
            alpha = int(112 * clamp(self.flash_time / 0.22, 0.0, 1.0))
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((*self.flash_color, alpha))
            self.canvas.blit(flash, (0, 0))

    def _draw_world_scene(self, surface: pygame.Surface) -> None:
        self.bg.draw(surface)
        for pickup in self.pickups:
            pickup.draw(surface)
        for obstacle in self.obstacles:
            obstacle.draw(surface)
        self.player.draw(
            surface,
            self.dino,
            time=self.bg.time,
            shield_time=self.effects["shield"],
            wings_time=self.effects["wings"],
            phoenix=self.phoenix,
            dash_time=self.dash_time,
            invincible=self.invincible,
            game_over=self.state == "gameover",
        )

        self.fx.fill((0, 0, 0, 0))
        for particle in self.particles:
            particle.draw(self.fx)
        surface.blit(self.fx, (0, 0))
        for text in self.floating_texts:
            text.draw(surface)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        surface.blit(self.top_shade, (0, 0))
        palette = ZONES[self.zone_index]

        # Corazones.
        pulse = 0.09 * max(0.0, math.sin(self.ui_time * 9.0)) if self.hearts == 1 else 0.0
        for index in range(self.max_hearts):
            draw_heart(
                surface,
                (41 + index * 33, 34),
                25,
                empty=index >= self.hearts,
                beat=pulse if index == 0 else 0.0,
            )

        # Barra de energía.
        draw_text(surface, "ENERGÍA", 10, (42, 56), PAPER, shadow=DEEP_INK)
        energy_color = CORAL if self.energy < 25 else TEAL
        draw_lightning(surface, (29, 83), 15, GOLD)
        draw_bar(surface, pygame.Rect(40, 76, 205, 14), self.energy / 100.0, energy_color, background=(10, 14, 20), border=None, radius=5, shimmer=True)
        draw_text(surface, f"{int(self.energy):02d}", 12, (258, 83), CREAM, anchor="midleft", mono=True, shadow=DEEP_INK)

        # Marcador central.
        draw_text(
            surface,
            zfill_score(self.score),
            41,
            (WIDTH // 2, 13),
            CREAM,
            anchor="midtop",
            mono=True,
            shadow=DEEP_INK,
            shadow_offset=(3, 3),
        )
        best_text = f"MEJOR {zfill_score(int(self.save.get('high_score', 0)))}"
        draw_text(surface, best_text, 11, (WIDTH // 2 - 55, 65), MUTED, anchor="topright", mono=True, shadow=DEEP_INK)
        draw_coin_icon(surface, (WIDTH // 2 - 38, 74), 8, phase=self.ui_time * 3)
        draw_text(surface, f"{self.coins_run:02d}", 12, (WIDTH // 2 - 25, 64), PAPER, mono=True, shadow=DEEP_INK)

        # Progreso de nivel.
        draw_text(surface, f"NIVEL {self.level:02d}", 19, (1248, 20), CREAM, anchor="topright", mono=True, shadow=DEEP_INK)
        target = max(1.0, self.level_goal - self.level_start_distance)
        progress = clamp((self.distance_m - self.level_start_distance) / target, 0.0, 1.0)
        draw_bar(surface, pygame.Rect(1022, 50, 226, 9), progress, palette["accent"], background=(9, 13, 19), border=None, radius=4, shimmer=True)
        draw_text(
            surface,
            f"{int(self.distance_m - self.level_start_distance):03d} / {int(target):03d} m",
            11,
            (1248, 64),
            PAPER,
            anchor="topright",
            mono=True,
            shadow=DEEP_INK,
        )
        zone_text = self._zone_label()
        draw_text(surface, zone_text, 10, (1248, 87), palette["accent"], anchor="topright", shadow=DEEP_INK)

        self._draw_active_effects(surface)
        self._draw_ability_cards(surface)
        draw_text(
            surface,
            "P  PAUSA      M  SONIDO      F11  PANTALLA",
            10,
            (WIDTH - 24, 679),
            MUTED,
            anchor="bottomright",
            mono=True,
            shadow=DEEP_INK,
            shadow_offset=(1, 1),
        )

    def _draw_active_effects(self, surface: pygame.Surface) -> None:
        specs: list[tuple[str, str, int, float, float]] = []
        if self.effects["shield"] > 0:
            specs.append(("shield", "ESCUDO", POWER_COLORS["shield"], self.effects["shield"], 11.0))
        if self.effects["magnet"] > 0:
            specs.append(("magnet", "IMÁN", POWER_COLORS["magnet"], self.effects["magnet"], 13.0))
        if self.effects["x2"] > 0:
            specs.append(("x2", "PUNTOS ×2", POWER_COLORS["x2"], self.effects["x2"], 12.0))
        if self.effects["wings"] > 0:
            specs.append(("wings", "ALAS", POWER_COLORS["wings"], self.effects["wings"], 16.0))
        if self.effects["slow"] > 0:
            specs.append(("slow", "TIEMPO", POWER_COLORS["slow"], self.effects["slow"], 5.0))
        if self.phoenix:
            specs.append(("phoenix", "FÉNIX", POWER_COLORS["phoenix"], -1.0, 1.0))
        if not specs:
            return

        font = fonts().get(10, bold=True)
        widths = []
        for kind, label, _color, remaining, _duration in specs:
            timer_text = "" if kind == "phoenix" else f"{remaining:04.1f}s"
            widths.append(30 + font.size(label)[0] + (font.size(timer_text)[0] + 14 if timer_text else 0))
        total_width = sum(widths) + (len(widths) - 1) * 7
        x = WIDTH // 2 - total_width // 2
        y = 108
        for (kind, label, color, remaining, duration), width in zip(specs, widths):
            rect = pygame.Rect(x, y, width, 29)
            draw_panel(surface, rect, fill=(10, 14, 20, 208), border=(*color, 88), radius=9, border_width=1)
            art.draw_icon(surface, kind, (rect.x + 16, rect.y + 14), 14, color)
            draw_text(surface, label, 10, (rect.x + 28, rect.y + 13), color, anchor="midleft")
            if kind != "phoenix":
                draw_text(surface, f"{remaining:04.1f}s", 10, (rect.right - 8, rect.y + 13), PAPER, anchor="midright", mono=True)
                fraction = clamp(remaining / duration, 0.0, 1.0)
                pygame.draw.rect(surface, color, (rect.x + 8, rect.bottom - 4, int((rect.width - 16) * fraction), 2), border_radius=1)
            x += width + 7

    def _draw_ability_cards(self, surface: pygame.Surface) -> None:
        for index, (kind, data) in enumerate(ACTIVE_ABILITIES.items()):
            rect = pygame.Rect(24 + index * 166, 638, 158, 60)
            blocked = (kind == "shield" and self.effects["shield"] > 0) or (kind == "slow" and self.effects["slow"] > 0)
            available = self.cooldowns[kind] <= 0 and self.energy >= data["cost"] and not blocked
            border_color = (*data["color"], 130 if available else 38)
            draw_panel(surface, rect, fill=(10, 14, 20, 218), border=border_color, radius=11, border_width=1)
            icon_color = data["color"] if available else (93, 102, 112)
            art.draw_icon(surface, data["icon"], (rect.x + 23, rect.y + 25), 17, icon_color)
            draw_text(surface, data["name"], 11, (rect.x + 39, rect.y + 9), CREAM if available else MUTED)
            draw_keycap(
                surface,
                data["key"],
                (rect.x + 56, rect.y + 41),
                size=8,
                color=CREAM if available else MUTED,
                bg=(32, 39, 49),
                border=(66, 77, 91),
                padding=(5, 3),
            )
            cost_color = GOLD if self.energy >= data["cost"] else (140, 99, 81)
            draw_lightning(surface, (rect.right - 34, rect.y + 40), 10, cost_color)
            draw_text(surface, str(data["cost"]), 10, (rect.right - 25, rect.y + 40), cost_color, anchor="midleft", mono=True)
            if self.cooldowns[kind] > 0:
                total = data["cooldown"] if data["cooldown"] > 0 else 1.0
                frac = 1.0 - clamp(self.cooldowns[kind] / total, 0.0, 1.0)
                pygame.draw.rect(surface, data["color"], (rect.x + 7, rect.bottom - 5, int((rect.width - 14) * frac), 2), border_radius=1)
                if self.cooldowns[kind] > 0.15:
                    draw_text(surface, f"{self.cooldowns[kind]:.1f}", 9, (rect.right - 9, rect.y + 10), MUTED, anchor="topright", mono=True)
            self.click_actions.append((rect, f"ability:{kind}"))

    def _draw_banner(self, surface: pygame.Surface) -> None:
        if self.level_banner_timer <= 0:
            return
        elapsed = self.level_banner_total - self.level_banner_timer
        fade_in = clamp(elapsed / 0.24, 0.0, 1.0)
        fade_out = clamp(self.level_banner_timer / 0.48, 0.0, 1.0)
        alpha = int(255 * min(fade_in, fade_out))
        if alpha <= 0:
            return

        panel_height = 168
        panel = pygame.Surface((WIDTH, panel_height), pygame.SRCALPHA)
        panel.fill((8, 12, 18, 174))
        pygame.draw.line(panel, (*ZONES[self.zone_index]["accent"], 200), (0, 1), (WIDTH, 1), 2)
        pygame.draw.line(panel, (*ZONES[self.zone_index]["accent"], 110), (0, panel_height - 1), (WIDTH, panel_height - 1), 1)

        cycle = (self.level - 1) // len(ZONES) + 1
        cycle_label = f"  ·  CICLO {_roman(cycle)}" if cycle > 1 else ""
        draw_text(
            panel,
            f"NIVEL {self.level:02d}{cycle_label}",
            12,
            (WIDTH // 2, 24),
            ZONES[self.zone_index]["accent"],
            anchor="center",
            mono=True,
        )
        draw_text(
            panel,
            self._zone_label(),
            43,
            (WIDTH // 2, 68),
            CREAM,
            anchor="center",
            shadow=(4, 7, 11),
            shadow_offset=(3, 3),
        )
        draw_text(
            panel,
            ZONE_INTROS[self.zone_index],
            15,
            (WIDTH // 2, 111),
            PAPER,
            anchor="center",
        )
        draw_text(
            panel,
            f"OBJETIVO  ·  {level_target(self.level)} m",
            10,
            (WIDTH // 2, 140),
            MUTED,
            anchor="center",
            mono=True,
        )
        panel.set_alpha(alpha)
        surface.blit(panel, (0, 178))

    def _draw_toasts(self, surface: pygame.Surface) -> None:
        if not self.toasts or self.level_banner_timer > 0:
            return
        for index, toast in enumerate(self.toasts[-3:]):
            alpha = int(255 * clamp(toast["life"] / 0.38, 0.0, 1.0))
            if alpha <= 0:
                continue
            font = fonts().get(13, bold=True)
            text_width = font.size(toast["text"])[0]
            width = min(700, text_width + (54 if toast["icon"] else 30))
            height = 32
            chip = pygame.Surface((width, height), pygame.SRCALPHA)
            color = toast["color"]
            pygame.draw.rect(chip, (10, 14, 20, 226), chip.get_rect(), border_radius=9)
            pygame.draw.rect(chip, (*color, 95), chip.get_rect(), width=1, border_radius=9)
            text_x = 15
            if toast["icon"]:
                art.draw_icon(chip, toast["icon"], (18, height // 2), 14, color)
                text_x = 34
            draw_text(chip, toast["text"], 13, (text_x, height // 2), color, anchor="midleft")
            chip.set_alpha(alpha)
            x = WIDTH // 2 - width // 2
            y = 152 + index * 38 - int((1.0 - clamp(toast["life"] / 0.4, 0.0, 1.0)) * 7)
            surface.blit(chip, (x, y))

    def _draw_hint(self, surface: pygame.Surface) -> None:
        if not self.hint_text or self.hint_timer <= 0 or self.level_banner_timer > 0:
            return
        alpha = int(255 * clamp(self.hint_timer / 0.45, 0.0, 1.0))
        font = fonts().get(12, bold=True)
        text_width = font.size(self.hint_text)[0]
        width = min(620, text_width + 42)
        pill = pygame.Surface((width, 30), pygame.SRCALPHA)
        pygame.draw.rect(pill, (10, 15, 21, 205), pill.get_rect(), border_radius=9)
        pygame.draw.rect(pill, (255, 255, 255, 28), pill.get_rect(), width=1, border_radius=9)
        draw_text(pill, self.hint_text, 12, (width // 2, 15), PAPER, anchor="center")
        pill.set_alpha(alpha)
        surface.blit(pill, (WIDTH // 2 - width // 2, 602))

    # ------------------------------------------------------------------
    # Pausa y fin de partida
    # ------------------------------------------------------------------
    def _render_pause(self) -> None:
        self.canvas.blit(self._dim_overlay(184), (0, 0))
        panel = pygame.Rect(330, 94, 620, 532)
        draw_panel(self.canvas, panel, fill=(16, 21, 30, 246), border=(255, 255, 255, 28), radius=22)
        draw_text(self.canvas, "PAUSA", 52, (WIDTH // 2, 127), CREAM, anchor="center", shadow=(5, 7, 12), shadow_offset=(3, 4))
        draw_text(self.canvas, "El desierto espera.", 14, (WIDTH // 2, 177), MUTED, anchor="center")
        pygame.draw.line(self.canvas, (255, 205, 92, 95), (385, 201), (895, 201), 1)

        stats = [
            ("PUNTOS", zfill_score(self.score)),
            ("DISTANCIA", f"{int(self.distance_m)} m"),
            ("NIVEL", f"{self.level:02d}"),
        ]
        for index, (label, value) in enumerate(stats):
            x = 390 + index * 184
            draw_text(self.canvas, label, 10, (x + 88, 219), MUTED, anchor="center")
            draw_text(self.canvas, value, 21, (x + 88, 236), CREAM, anchor="center", mono=True)

        for index, (label, action) in enumerate(PAUSE_ITEMS):
            rect = pygame.Rect(386, 284 + index * 66, 508, 54)
            self._draw_action_button(rect, label, f"pause:{index}", index == self.pause_index, selected_color=GOLD)
        draw_text(
            self.canvas,
            "P / ESC  continuar      M  sonido      F11  pantalla completa",
            11,
            (WIDTH // 2, 527),
            MUTED,
            anchor="center",
            mono=True,
        )
        draw_text(self.canvas, "X · SALIR AL MENÚ", 10, (WIDTH // 2, 564), (114, 122, 132), anchor="center", mono=True)
        draw_text(self.canvas, f"RÉCORD  {zfill_score(int(self.save.get('high_score', 0)))}", 11, (WIDTH // 2, 596), GOLD, anchor="center", mono=True)

    def _render_gameover(self) -> None:
        self.canvas.blit(self._dim_overlay(194), (0, 0))
        panel = pygame.Rect(210, 62, 860, 584)
        border_color = (*GOLD, 170) if self.new_record else (255, 255, 255, 30)
        draw_panel(self.canvas, panel, fill=(16, 21, 30, 248), border=border_color, radius=24)
        if self.new_record:
            pulse = (math.sin(self.ui_time * 4.0) + 1) / 2
            pygame.draw.rect(
                self.canvas,
                (255, 205, 92, int(40 + pulse * 65)),
                panel.inflate(6, 6),
                width=2,
                border_radius=27,
            )
        title = "¡NUEVO RÉCORD!" if self.new_record else "FIN DEL VIAJE"
        title_color = GOLD if self.new_record else CORAL
        draw_text(
            self.canvas,
            title,
            38,
            (WIDTH // 2, 94),
            title_color,
            anchor="center",
            shadow=(5, 7, 11),
            shadow_offset=(3, 4),
        )
        draw_text(self.canvas, "PUNTUACIÓN FINAL", 10, (WIDTH // 2, 136), MUTED, anchor="center")
        draw_text(
            self.canvas,
            zfill_score(self.score),
            58,
            (WIDTH // 2, 183),
            CREAM,
            anchor="center",
            mono=True,
            shadow=(8, 10, 15),
            shadow_offset=(3, 4),
        )

        stats = [
            ("DISTANCIA", f"{int(self.distance_m)} m", CREAM),
            ("NIVEL", f"{self.level:02d}", CREAM),
            ("MONEDAS", f"{self.coins_run}", GOLD),
            ("RÉCORD", zfill_score(int(self.save.get("high_score", 0))), GOLD if self.new_record else PAPER),
        ]
        for index, (label, value, color) in enumerate(stats):
            rect = pygame.Rect(246 + index * 203, 240, 184, 76)
            draw_panel(self.canvas, rect, fill=(10, 14, 20, 205), border=(255, 255, 255, 18), radius=12)
            draw_text(self.canvas, label, 9, (rect.centerx, rect.y + 14), MUTED, anchor="center")
            draw_text(self.canvas, value, 20, (rect.centerx, rect.y + 47), color, anchor="center", mono=True)

        draw_text(
            self.canvas,
            self.game_over_reason,
            12,
            (WIDTH // 2, 341),
            MUTED,
            anchor="center",
        )
        for index, (label, action) in enumerate(GAMEOVER_ITEMS):
            rect = pygame.Rect(370, 380 + index * 68, 540, 56)
            self._draw_action_button(
                rect,
                label,
                f"over:{index}",
                index == self.gameover_index,
                selected_color=CORAL if action == "retry" else GOLD,
            )
        draw_text(
            self.canvas,
            "↑ ↓  elegir      ENTER / ESPACIO  confirmar      ESC  menú",
            11,
            (WIDTH // 2, 609),
            MUTED,
            anchor="center",
            mono=True,
        )
        if self.gameover_ready > 0:
            draw_text(self.canvas, "…", 22, (WIDTH // 2, 634), MUTED, anchor="center")

    def _draw_action_button(
        self,
        rect: pygame.Rect,
        label: str,
        action: str,
        selected: bool,
        *,
        selected_color: tuple[int, int, int] = GOLD,
    ) -> None:
        if selected:
            draw_panel(self.canvas, rect, fill=(*selected_color, 235), border=(255, 248, 220, 210), radius=11, border_width=1)
            pygame.draw.polygon(
                self.canvas,
                INK,
                [(rect.x + 22, rect.centery - 7), (rect.x + 32, rect.centery), (rect.x + 22, rect.centery + 7)],
            )
            draw_text(self.canvas, label, 19, (rect.x + 48, rect.centery), INK, anchor="midleft")
        else:
            draw_panel(self.canvas, rect, fill=(11, 15, 21, 212), border=(255, 255, 255, 28), radius=11, border_width=1)
            draw_text(self.canvas, label, 19, (rect.x + 48, rect.centery), PAPER, anchor="midleft")
        self.click_actions.append((rect, action))

