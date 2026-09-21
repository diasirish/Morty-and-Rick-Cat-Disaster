"""Renderer: GameEngine state -> a pygame Surface.

This is the game's "observation function". It draws onto its OWN offscreen
surface and returns it, so the same code path serves two masters:

  * the human game blits the returned surface to the real window;
  * the RL env (rl/env.py) downscales the returned surface to a small
    uint8 array - the pixels the agent actually sees.

Nothing in here mutates game state, and there is no display requirement:
drawing to an offscreen Surface works under SDL's dummy video driver, which
is how headless training renders thousands of observations per second
without a window.
"""

from __future__ import annotations

import pygame

from .engine import GameEngine

HUD_COLOR = (255, 255, 255)
BARK_COLOR = (255, 255, 0)
BOSS_TINT = (255, 60, 60)

# Coat variants (multiplied over the white cat sprite). Index = CatState.color_id.
CAT_TINTS = [
    None,             # 0: the original white cat
    (255, 185, 115),  # 1: ginger
    (165, 165, 185),  # 2: smoky gray
    (150, 120, 95),   # 3: brown tabby
]


class Renderer:
    def __init__(self, assets, config):
        self.assets = assets
        self.config = config
        if not pygame.font.get_init():
            pygame.font.init()
        self.surface = pygame.Surface((config.screen_width, config.screen_height))
        self.hud_font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 48)
        self._boss_sprite_cache = {}
        self._cat_sprite_cache = {}

    # ------------------------------------------------------------------

    def draw(self, engine: GameEngine, highscore: int | None = None) -> pygame.Surface:
        s = self.surface
        s.fill((0, 0, 0))

        background = self.assets.image("background")
        if background is not None:
            s.blit(background, (0, 0))

        if engine.food.present:
            self._draw_food(s, engine.food)
        if engine.larissa is not None and engine.larissa.active:
            self._draw_larissa(s, engine.larissa)
        for cat in engine.cats:
            self._draw_cat(s, cat)
        self._draw_dog(s, engine)
        if self.config.barks_visible:
            for bark in engine.barks:
                for px, py in bark.projectiles:
                    pygame.draw.circle(s, BARK_COLOR, (int(px), int(py)), 5)

        self._draw_hud(s, engine, highscore)
        return s

    # ------------------------------------------------------------------

    def _draw_dog(self, s, engine):
        key = self.assets.character_sprite_key(engine.character)
        sprite = self.assets.image(key, flipped=engine.dog.facing == "left")
        if sprite is not None:
            s.blit(sprite, (engine.dog.x, engine.dog.y))
        else:
            pygame.draw.rect(s, (200, 120, 40),
                             (engine.dog.x, engine.dog.y,
                              engine.dog.width, engine.dog.height))

    def _draw_cat(self, s, cat):
        flipped = cat.direction == "left"
        if cat.is_boss:
            sprite = self._boss_sprite(flipped, (cat.width, cat.height))
        else:
            scale = (cat.width, cat.height) if cat.enlarged else None
            sprite = self._cat_sprite(cat.color_id, flipped, scale)
        if sprite is not None:
            s.blit(sprite, (cat.x, cat.y))
        else:
            pygame.draw.rect(s, (90, 90, 200), (cat.x, cat.y, cat.width, cat.height))
        if cat.is_boss:
            self._draw_boss_health(s, cat)

    def _cat_sprite(self, color_id, flipped, scale):
        """Coat-tinted cat sprite, cached per (color, direction, size)."""
        tint = CAT_TINTS[color_id % len(CAT_TINTS)]
        if tint is None:
            return self.assets.image("cat", flipped=flipped, scale=scale)
        key = (color_id, flipped, scale)
        if key not in self._cat_sprite_cache:
            base = self.assets.image("cat", flipped=flipped, scale=scale)
            if base is None:
                self._cat_sprite_cache[key] = None
            else:
                tinted = base.copy()
                tinted.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
                self._cat_sprite_cache[key] = tinted
        return self._cat_sprite_cache[key]

    def _boss_sprite(self, flipped, size):
        """The boss is the cat sprite scaled to its hitbox and tinted red,
        so it reads as 'dangerous' in a single glance (and a single pixel
        observation)."""
        key = (flipped, size)
        if key not in self._boss_sprite_cache:
            base = self.assets.image("cat", flipped=flipped, scale=size)
            if base is None:
                self._boss_sprite_cache[key] = None
            else:
                tinted = base.copy()
                tinted.fill(BOSS_TINT, special_flags=pygame.BLEND_RGB_MULT)
                self._boss_sprite_cache[key] = tinted
        return self._boss_sprite_cache[key]

    def _draw_boss_health(self, s, cat):
        full = self.config.boss_health
        frac = max(0.0, cat.health / full)
        bar_w, bar_h = cat.width, 6
        x, y = int(cat.x), int(cat.y) - 10
        pygame.draw.rect(s, (60, 60, 60), (x, y, bar_w, bar_h))
        pygame.draw.rect(s, (220, 40, 40), (x, y, int(bar_w * frac), bar_h))

    def _draw_food(self, s, food):
        sprite = self.assets.image("food")
        if sprite is not None:
            s.blit(sprite, (food.x, food.y))
        else:
            pygame.draw.rect(s, (100, 255, 100),
                             (food.x, food.y, food.width, food.height))

    def _draw_larissa(self, s, lar):
        frame_key = "larissa_f1" if (lar.frame_counter // 8) % 2 == 0 else "larissa_f2"
        sprite = self.assets.image(frame_key, flipped=lar.direction == "left")
        if sprite is not None:
            s.blit(sprite, (lar.x, lar.y))
        else:
            pygame.draw.rect(s, (200, 80, 160),
                             (lar.x, lar.y, lar.width, lar.height))
        if lar.carrying_food:
            bowl = self.assets.image("food")
            if bowl is not None:
                # in her hands: just past the leading edge, at arm height
                bowl_x = lar.x + (lar.width - 24 if lar.direction == "right" else -8)
                bowl_y = lar.y + int(lar.height * 0.48)
                s.blit(bowl, (bowl_x, bowl_y))

    def _draw_hud(self, s, engine, highscore):
        score = self.hud_font.render(
            f"Cats Destroyed: {engine.score}", True, HUD_COLOR)
        s.blit(score, (10, 10))
        if highscore is not None:
            hs = self.hud_font.render(f"Highscore: {highscore}", True, HUD_COLOR)
            s.blit(hs, (10, 30))
        if engine.done:
            if engine.won:
                text = self.big_font.render("You Win!", True, (80, 255, 80))
            else:
                text = self.big_font.render("Game Over", True, (255, 0, 0))
            rect = text.get_rect(center=(self.config.screen_width // 2,
                                         self.config.screen_height // 2))
            s.blit(text, rect)
