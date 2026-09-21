"""Cat movement patterns - the "quirks" that make the game RL-worthy.

Old 8-bit games never used per-frame randomness: an enemy rolled its
personality once (at spawn) and then behaved deterministically. We do the
same. `roll_pattern` consumes the engine's seeded RNG exactly once per cat;
`update_cat` is a pure function of (cat state, context) per frame. Given the
same seed, every cat flies the same path - which is what makes whole episodes
reproducible for RL training and tests.

Why this matters for RL: with only the classic zigzag, the optimal policy
degenerates into "stand in a corner, bark on cooldown". The pattern mix
(see GameConfig.pattern_weights_by_wave) breaks that:

  zigzag - the classic sweep, now with a per-cat turn margin so the safe
           columns differ between cats.
  sine   - bobs vertically while sweeping; barks timed for a fixed height miss.
  pauser - Space-Invaders stutter (move / freeze / double-speed burst);
           breaks metronomic bark timing.

Two more exist but are NOT in the default rotation (they broke the game's
descend-at-the-edges rhythm in playtesting - re-enable via
GameConfig.pattern_weights_by_wave if you want a nastier RL problem):

  diver  - locks onto the dog's column and dive-bombs it.
  hopper - descends a half-row every fixed distance travelled instead of at
           screen edges, so it occupies off-grid heights.
"""

import math
from dataclasses import dataclass

from .entities import VERTICAL_MOVE


@dataclass
class PatternCtx:
    """Per-frame context handed to every pattern update."""
    dog_x: float
    dog_y: float
    global_speed: float
    screen_width: int
    screen_height: int


# ---------------------------------------------------------------------------
# Spawn-time rolls
# ---------------------------------------------------------------------------

def roll_pattern(rng, kills, config):
    """Pick a pattern id + its frozen parameters for a freshly spawned cat.

    `rng` is the engine's np.random.Generator - the ONLY source of
    randomness in the simulation. `kills` selects the wave weight table.
    """
    weights = config.pattern_weights_by_wave[0][1]
    for min_kills, table in config.pattern_weights_by_wave:
        if kills >= min_kills:
            weights = table
    names = list(weights.keys())
    probs = [weights[n] for n in names]
    total = sum(probs)
    probs = [p / total for p in probs]
    pattern_id = names[rng.choice(len(names), p=probs)]

    margin = float(rng.uniform(10, 70))
    if pattern_id == "zigzag":
        params = {"margin": margin}
    elif pattern_id == "sine":
        params = {
            "margin": margin,
            "amplitude": float(rng.uniform(4, 10)),
            "period": 100.0,
            "phase": float(rng.uniform(0, 2 * math.pi)),
            "base_y": None,  # filled on first update
        }
    elif pattern_id == "diver":
        params = {
            "margin": margin,
            "trigger_y": 190.0,   # below the 3rd cat row
            "lock_range": 48.0,   # horizontal distance that arms the dive
            "target_x": None,     # dog's x, frozen at the moment of lock-on
        }
    elif pattern_id == "pauser":
        params = {"margin": margin, "offset": int(rng.integers(0, 80))}
    elif pattern_id == "hopper":
        params = {"margin": float(rng.uniform(10, 30)), "travelled": 0.0}
    else:
        raise ValueError(f"unknown pattern {pattern_id!r}")
    return pattern_id, params


# ---------------------------------------------------------------------------
# Per-frame updates (each mutates cat.x / cat.y / cat.direction exactly once)
# ---------------------------------------------------------------------------

def _sweep(cat, ctx, speed, margin, descend=VERTICAL_MOVE):
    """Shared horizontal sweep: move, and at the margin descend + flip."""
    if cat.direction == "left":
        if cat.x - speed > margin:
            cat.x -= speed
        else:
            cat.y += descend
            cat.direction = "right"
    else:
        if cat.x + speed < ctx.screen_width - cat.width - margin:
            cat.x += speed
        else:
            cat.y += descend
            cat.direction = "left"


def _update_zigzag(cat, ctx, speed):
    _sweep(cat, ctx, speed, cat.pattern_params.get("margin", 10.0))


def _update_sine(cat, ctx, speed):
    p = cat.pattern_params
    if p["base_y"] is None:
        p["base_y"] = cat.y
    # sweep operates on the base row; the visible y bobs around it
    cat.y = p["base_y"]
    _sweep(cat, ctx, speed, p["margin"])
    p["base_y"] = cat.y
    angle = 2 * math.pi * cat.phase_counter / p["period"] + p["phase"]
    cat.y = p["base_y"] + p["amplitude"] * math.sin(angle)


def _update_diver(cat, ctx, speed):
    p = cat.pattern_params
    if p["target_x"] is None:
        # cruise like a zigzag until low enough and near the dog's column
        cat_center = cat.x + cat.width / 2
        dog_center = ctx.dog_x + 32
        if cat.y >= p["trigger_y"] and abs(cat_center - dog_center) <= p["lock_range"]:
            p["target_x"] = ctx.dog_x  # lock NOW; the dive itself never re-aims
        else:
            _sweep(cat, ctx, speed, p["margin"])
            return
    dive_speed = speed * 1.5
    dx = p["target_x"] - cat.x
    step = max(-dive_speed, min(dive_speed, dx))
    cat.x += step
    cat.y += dive_speed
    if abs(step) > 0.1:
        cat.direction = "left" if step < 0 else "right"


def _update_pauser(cat, ctx, speed):
    p = cat.pattern_params
    tick = (cat.phase_counter + p["offset"]) % 80
    if tick < 40:
        effective = speed          # cruise
    elif tick < 60:
        effective = 0.0            # freeze
    else:
        effective = speed * 2.0    # burst
    if effective > 0:
        _sweep(cat, ctx, effective, p["margin"])


def _update_hopper(cat, ctx, speed):
    p = cat.pattern_params
    # flip at edges WITHOUT descending; descent comes from distance travelled
    if cat.direction == "left":
        if cat.x - speed > p["margin"]:
            cat.x -= speed
        else:
            cat.direction = "right"
    else:
        if cat.x + speed < ctx.screen_width - cat.width - p["margin"]:
            cat.x += speed
        else:
            cat.direction = "left"
    p["travelled"] += speed
    if p["travelled"] >= 120.0:
        p["travelled"] -= 120.0
        cat.y += VERTICAL_MOVE // 2


_PATTERNS = {
    "zigzag": _update_zigzag,
    "sine": _update_sine,
    "diver": _update_diver,
    "pauser": _update_pauser,
    "hopper": _update_hopper,
}


def update_cat(cat, ctx):
    """Advance one cat by one frame. The boss always flies the classic
    wall-to-wall zigzag (it is a tank, not a trickster) at its own speed."""
    if not cat.active:
        return
    speed = cat.speed if cat.speed > 0 else ctx.global_speed
    if cat.is_boss:
        _sweep(cat, ctx, speed, 10.0)
    else:
        _PATTERNS[cat.pattern_id](cat, ctx, speed)
    cat.phase_counter += 1
