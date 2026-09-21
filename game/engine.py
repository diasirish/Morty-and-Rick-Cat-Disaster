"""The deterministic, frame-based game engine.

========================== WHERE THE RL COMES IN ===========================
This file IS the "world" your agent lives in, but it knows nothing about RL,
pygame windows, sounds or wall-clock time. It exposes exactly the interface
a reinforcement-learning environment needs:

    engine = GameEngine(GameConfig())
    engine.reset(seed=123)              # reproducible episode start
    events = engine.step(Action.LEFT)   # advance EXACTLY one frame

* `step` takes one of the 6 button combinations (Action) - this is the
  agent's entire action space, the same "buttons" a human plays with.
* `step` returns a list of Events (CAT_KILLED, DOG_DIED, ...). The RL env
  (rl/env.py) converts those events into scalar rewards via RewardConfig,
  and the audio layer (game/audio.py) converts the same events into sounds.
  One simulation, two consumers.
* The pixel observation is NOT produced here - game/render.py draws this
  engine's state onto a surface, and rl/env.py downscales that surface.
  Engine = dynamics, Renderer = observation function.
* All randomness flows through one seeded np.random.Generator, and all
  timers count frames, so the simulation is exactly reproducible and can
  run thousands of frames per second headless (no display, no sleeping).

Per-frame update order inside `step` (fixed; tests rely on it):
    1. intro script (Aunt Larissa places the food; actions are ignored)
    2. difficulty ramp (every `speed_increase_frames`)
    3. apply the action (move with wall clamps; bark if cooldown elapsed)
    4. advance bark projectiles
    5. bark <-> cat collisions (a bark dies on its first hit - by design)
    6. cat movement (delegated to game/patterns.py)
    7. boss spawn, then regular cat spawn (timer with gaussian jitter)
    8. food collision (a cat that eats the food grows: health 1 -> 9)
    9. dog <-> cat collision -> DOG_DIED, episode over
============================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, IntEnum, auto

import numpy as np

from .config import GameConfig
from .entities import (
    BOSS_H,
    BOSS_W,
    ENLARGE_SCALE,
    ENLARGED_CAT_HEALTH,
    FOOD_W,
    LARISSA_H,
    LARISSA_W,
    N_CAT_COLORS,
    VERTICAL_MOVE,
    BarkState,
    CatState,
    DogState,
    FoodState,
    LarissaState,
)
from .patterns import PatternCtx, roll_pattern, update_cat

# How Larissa moves during the intro (pixels per frame; scripted, not tunable
# from the options menu on purpose - it is decoration, not gameplay).
LARISSA_SPEED = 3.0
LARISSA_PAUSE_FRAMES = 30

DOG_Y = 400          # the dog's fixed row (it only moves horizontally)
CAT_SPAWN_Y = 40     # cats appear at this height
BOSS_SPAWN_X, BOSS_SPAWN_Y = 10, 140


class Action(IntEnum):
    """The agent's buttons. Discrete(6) in the RL env."""
    NOOP = 0
    LEFT = 1
    RIGHT = 2
    BARK = 3
    LEFT_BARK = 4
    RIGHT_BARK = 5


class EventType(Enum):
    ROUND_STARTED = auto()   # intro finished (or frame 1 when intro disabled)
    FOOD_PLACED = auto()     # Larissa set the bowl down
    BARK_FIRED = auto()
    CAT_KILLED = auto()
    CAT_ATE_FOOD = auto()    # a cat reached the bowl and grew
    BOSS_SPAWNED = auto()
    BOSS_HIT = auto()
    BOSS_KILLED = auto()     # the win condition
    DOG_DIED = auto()        # the loss condition


@dataclass(frozen=True)
class Event:
    type: EventType
    x: float = 0.0           # where it happened (useful for reward shaping)
    y: float = 0.0


class GameEngine:
    def __init__(self, config: GameConfig | None = None, character: str = "morty"):
        self.config = config or GameConfig()
        # Cosmetic only: selects which sprite/bark sound the render/audio
        # layers use. Morty and Rick share every gameplay stat.
        self.character = character
        self.reset()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self, seed: int | None = None) -> None:
        """Start a fresh episode. Same seed => identical episode."""
        cfg = self.config
        self.rng = np.random.default_rng(seed)
        self.frame = 0
        self.done = False
        self.won = False
        self.cat_speed = cfg.cat_speed
        self.cat_timer = cfg.initial_cat_timer
        self.dog = DogState(x=cfg.screen_width // 2, y=DOG_Y)
        self.cats: list[CatState] = []
        self.barks: list[BarkState] = []

        food_y = DOG_Y - cfg.food_levels_before_dog * VERTICAL_MOVE
        self.food = FoodState(
            x=cfg.food_x - FOOD_W // 2,
            y=food_y,
            present=not cfg.intro_enabled,
        )

        ground_y = DOG_Y + self.dog.height  # both stand on the same floor
        if cfg.intro_enabled:
            self.phase = "intro"
            self.larissa = LarissaState(x=-float(LARISSA_W), y=ground_y - float(LARISSA_H))
        else:
            self.phase = "playing"
            self.larissa = None
        self._round_started_emitted = False

    @property
    def score(self) -> int:
        return self.dog.cats_destroyed

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def step(self, action: Action) -> list[Event]:
        """Advance the world by exactly one frame and report what happened."""
        events: list[Event] = []
        if self.done:
            return events
        self.frame += 1

        if self.phase == "intro":
            self._intro_step(events)
            return events

        if not self._round_started_emitted:
            self._round_started_emitted = True
            events.append(Event(EventType.ROUND_STARTED))

        cfg = self.config

        # 2. difficulty ramp: the same log curve as the original, now clamped
        if self.frame % cfg.speed_increase_frames == 0 and self.cat_speed < cfg.max_cat_speed:
            self.cat_speed = min(
                self.cat_speed + math.log(self.cat_speed + 1), cfg.max_cat_speed
            )

        # 3. the agent's action
        self._apply_action(action, events)

        # 4. + 5. barks fly, then hit things
        self._advance_barks()
        self._bark_collisions(events)
        if self.dog.destroyed_boss:
            self.done = True
            self.won = True
            return events

        # 6. cats fly their patterns
        ctx = PatternCtx(
            dog_x=self.dog.x,
            dog_y=self.dog.y,
            global_speed=self.cat_speed,
            screen_width=cfg.screen_width,
            screen_height=cfg.screen_height,
        )
        for cat in self.cats:
            update_cat(cat, ctx)
        # a diver that misses the dog exits the bottom of the screen: cull it
        # (only divers can do this; sweepers always cross the dog's column)
        self.cats = [c for c in self.cats if c.y <= cfg.screen_height]

        # 7. spawns
        self._spawns(events)

        # 8. + 9. food, then the fatal check
        self._food_collisions(events)
        self._dog_collision(events)
        return events

    def snapshot(self) -> dict:
        """Full serializable state - used by determinism tests."""
        return {
            "frame": self.frame,
            "phase": self.phase,
            "done": self.done,
            "won": self.won,
            "cat_speed": round(self.cat_speed, 6),
            "cat_timer": round(float(self.cat_timer), 6),
            "dog": (round(self.dog.x, 4), self.dog.bark_cooldown_remaining,
                    self.dog.cats_destroyed, self.dog.facing),
            "cats": [
                (cat.pattern_id, round(cat.x, 4), round(cat.y, 4),
                 cat.health, cat.direction, cat.enlarged, cat.is_boss)
                for cat in self.cats
            ],
            "barks": [
                [(round(px, 4), round(py, 4)) for px, py in bark.projectiles]
                for bark in self.barks
            ],
            "food": (self.food.present, self.food.x, self.food.y),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _intro_step(self, events: list[Event]) -> None:
        """Larissa walks in, sets the bowl down, walks back out."""
        lar = self.larissa
        lar.frame_counter += 1
        target_x = self.config.food_x - lar.width / 2
        if lar.carrying_food:
            if lar.x < target_x:
                lar.x = min(lar.x + LARISSA_SPEED, target_x)
                lar.direction = "right"
            elif lar.pause_remaining == 0:
                lar.pause_remaining = LARISSA_PAUSE_FRAMES
            else:
                lar.pause_remaining -= 1
                if lar.pause_remaining == LARISSA_PAUSE_FRAMES // 2:
                    lar.carrying_food = False
                    self.food.present = True
                    events.append(Event(EventType.FOOD_PLACED, self.food.x, self.food.y))
        else:
            lar.x -= LARISSA_SPEED
            lar.direction = "left"
            if lar.x < -lar.width:
                lar.active = False
                self.phase = "playing"

    def _apply_action(self, action: Action, events: list[Event]) -> None:
        cfg = self.config
        dog = self.dog
        if action in (Action.LEFT, Action.LEFT_BARK):
            if dog.x - cfg.dog_speed >= 0:
                dog.x -= cfg.dog_speed
                dog.facing = "left"
        elif action in (Action.RIGHT, Action.RIGHT_BARK):
            if dog.x + dog.width + cfg.dog_speed <= cfg.screen_width:
                dog.x += cfg.dog_speed
                dog.facing = "right"

        if dog.bark_cooldown_remaining > 0:
            dog.bark_cooldown_remaining -= 1
        if action in (Action.BARK, Action.LEFT_BARK, Action.RIGHT_BARK):
            if dog.bark_cooldown_remaining == 0:
                self.barks.append(BarkState(
                    projectiles=[(dog.x + 20, dog.y + 10 - i * 10) for i in range(8)],
                    speed=cfg.bark_speed,
                ))
                dog.bark_cooldown_remaining = cfg.bark_cooldown_frames
                events.append(Event(EventType.BARK_FIRED, dog.x, dog.y))

    def _advance_barks(self) -> None:
        for bark in self.barks:
            bark.projectiles = [(px, py - bark.speed) for px, py in bark.projectiles]
            if not any(py > 0 for _, py in bark.projectiles):
                bark.active = False
        self.barks = [b for b in self.barks if b.active]

    def _bark_collisions(self, events: list[Event]) -> None:
        # Faithful port of the original rule set: a bark "dies" on its first
        # hit, but the remaining projectiles of that same bark may still
        # connect with OTHER cats during this same frame. It reads like a
        # bug, plays like a feature (rare satisfying double-kills).
        for bark in self.barks:
            if not bark.active:
                continue
            for px, py in bark.projectiles:
                for cat in self.cats:
                    if (cat.active
                            and cat.x < px < cat.x + cat.width
                            and cat.y < py < cat.y + cat.height):
                        bark.active = False
                        cat.health -= 1
                        if cat.is_boss:
                            events.append(Event(EventType.BOSS_HIT, cat.x, cat.y))
                            if cat.health <= 0:
                                cat.active = False
                                self.dog.destroyed_boss = True
                                events.append(Event(EventType.BOSS_KILLED, cat.x, cat.y))
                        elif cat.health <= 0:
                            cat.active = False
                            self.dog.cats_destroyed += 1
                            events.append(Event(EventType.CAT_KILLED, cat.x, cat.y))
                        break
        self.cats = [cat for cat in self.cats if cat.active]
        self.barks = [b for b in self.barks if b.active]

    def _boss_exists(self) -> bool:
        return any(cat.is_boss and cat.active for cat in self.cats)

    def _spawns(self, events: list[Event]) -> None:
        cfg = self.config
        if self.dog.cats_destroyed >= cfg.cats_before_boss and not self._boss_exists() \
                and not self.dog.destroyed_boss:
            self.cats.append(CatState(
                x=BOSS_SPAWN_X, y=BOSS_SPAWN_Y, width=BOSS_W, height=BOSS_H,
                health=cfg.boss_health, is_boss=True, speed=cfg.boss_speed,
            ))
            events.append(Event(EventType.BOSS_SPAWNED, BOSS_SPAWN_X, BOSS_SPAWN_Y))
            return

        if self.cat_timer <= 0 and not self._boss_exists():
            # Anti-camping spawn bias: some cats spawn near the dog's column,
            # so loitering anywhere steadily attracts company.
            if self.rng.uniform() < cfg.spawn_target_bias:
                x = float(np.clip(self.rng.normal(self.dog.x, 80.0),
                                  40, cfg.screen_width - 20))
            else:
                x = float(self.rng.uniform(40, cfg.screen_width - 20))
            pattern_id, params = roll_pattern(self.rng, self.dog.cats_destroyed, cfg)
            self.cats.append(CatState(
                x=int(x), y=CAT_SPAWN_Y,
                direction="left" if self.rng.uniform() < 0.5 else "right",
                pattern_id=pattern_id, pattern_params=params,
                color_id=int(self.rng.integers(0, N_CAT_COLORS)),
            ))
            self.cat_timer = cfg.cat_spawn_interval + self.rng.normal(0, cfg.cat_spawn_noise_std)
        else:
            self.cat_timer -= 1

    def _food_collisions(self, events: list[Event]) -> None:
        food = self.food
        if not food.present:
            return
        for cat in self.cats:
            if cat.enlarged or cat.is_boss:
                continue
            if (cat.x < food.x + food.width and cat.x + cat.width > food.x
                    and cat.y < food.y + food.height and cat.y + cat.height > food.y):
                old_height = cat.height
                cat.enlarged = True
                cat.width = int(cat.width * ENLARGE_SCALE)
                cat.height = int(cat.height * ENLARGE_SCALE)
                cat.y -= cat.height - old_height  # grow upward, keep feet level
                cat.health = ENLARGED_CAT_HEALTH
                events.append(Event(EventType.CAT_ATE_FOOD, cat.x, cat.y))

    def _dog_collision(self, events: list[Event]) -> None:
        dog = self.dog
        for cat in self.cats:
            same_level = cat.y >= dog.y - VERTICAL_MOVE
            overlaps_x = cat.x < dog.x + dog.width and cat.x + cat.width > dog.x
            if same_level and overlaps_x:
                dog.alive = False
                self.done = True
                events.append(Event(EventType.DOG_DIED, dog.x, dog.y))
                return
