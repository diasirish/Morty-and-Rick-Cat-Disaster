"""Pure game-state objects.

No pygame imports here, on purpose: these dataclasses ARE the game state.
The renderer reads them to draw a frame, the RL environment reads the drawn
frame as its observation, and tests can snapshot them directly. If you can
serialize everything in this file, you can serialize the whole game.

Hitboxes match sprite sizes (the original used a 40x20 hitbox under a 64x57
cat sprite; with pixel observations the agent sees sprites, so collision
boxes now agree with what is drawn).
"""

from dataclasses import dataclass, field

# Nominal sprite/hitbox sizes (pixels)
DOG_W, DOG_H = 64, 60
CAT_W, CAT_H = 64, 57
BOSS_W, BOSS_H = 60, 60
FOOD_W, FOOD_H = 32, 32
LARISSA_W, LARISSA_H = 120, 180

VERTICAL_MOVE = 50      # pixels a cat descends per row change
ENLARGE_SCALE = 1.5     # size multiplier when a cat eats the food
ENLARGED_CAT_HEALTH = 9 # barks needed to down a fed cat
N_CAT_COLORS = 4        # coat variants a cat can spawn with (render.py maps them)


@dataclass
class DogState:
    x: float
    y: float
    width: int = DOG_W
    height: int = DOG_H
    facing: str = "right"               # which way the sprite looks
    bark_cooldown_remaining: int = 0    # frames until the next bark is allowed
    cats_destroyed: int = 0
    destroyed_boss: bool = False
    alive: bool = True


@dataclass
class BarkState:
    """One bark = a column of 8 projectiles travelling upward together."""
    projectiles: list                   # [(x, y), ...]
    speed: float
    active: bool = True


@dataclass
class CatState:
    x: float
    y: float
    width: int = CAT_W
    height: int = CAT_H
    health: int = 1
    active: bool = True
    direction: str = "left"             # current horizontal heading
    enlarged: bool = False
    is_boss: bool = False
    color_id: int = 0                   # coat variant, rolled at spawn
    speed: float = 0.0                  # per-cat speed; 0 means "use global"
    pattern_id: str = "zigzag"
    pattern_params: dict = field(default_factory=dict)  # rolled once at spawn
    phase_counter: int = 0              # frames since spawn (drives patterns)


@dataclass
class FoodState:
    x: float
    y: float
    width: int = FOOD_W
    height: int = FOOD_H
    present: bool = True                # False until Larissa places it


@dataclass
class LarissaState:
    """Aunt Larissa, the round-intro NPC. Scripted, never controllable."""
    x: float
    y: float
    width: int = LARISSA_W
    height: int = LARISSA_H
    direction: str = "right"
    carrying_food: bool = True
    pause_remaining: int = 0            # frames left standing at the drop spot
    frame_counter: int = 0              # drives the 2-frame walk animation
    active: bool = True
