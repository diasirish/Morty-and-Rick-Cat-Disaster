"""Game configuration.

Everything in here is expressed in FRAMES, not milliseconds. The engine
advances in fixed steps of exactly one frame; one frame == 1/fps seconds when
played by a human at real time, but the RL training loop can run frames as
fast as the CPU allows. That is what makes headless training possible: there
is no wall-clock anywhere in the simulation.

Conversions from the original (wall-clock) game, at the canonical 50 FPS:
    bark cooldown      350 ms  -> 18 frames
    speed-up interval  10000 ms -> 500 frames
"""

from dataclasses import dataclass, field


def _default_pattern_weights():
    """Cat movement pattern mix as the round progresses, keyed by kill count.

    Each entry: (min_kills, {pattern_name: weight}). The last entry whose
    min_kills <= current kill count is used. Early game is pure zigzag (the
    classic behavior, easy to read); later waves mix in quirkier 8-bit
    patterns so a single memorized response stops working.

    All defaults keep the classic rhythm: cats only descend at screen
    edges. Two extra patterns exist in game/patterns.py but are OUT of the
    default rotation by design ("diver" plunges at the dog, "hopper"
    staircases down mid-screen) - both broke the game's feel in playtesting.
    Add them back here if you want a meaner RL problem.
    """
    return (
        (0, {"zigzag": 1.0}),
        (10, {"zigzag": 0.7, "sine": 0.3}),
        (20, {"zigzag": 0.45, "sine": 0.3, "pauser": 0.25}),
    )


@dataclass
class GameConfig:
    # --- screen / timing ---
    screen_width: int = 640
    screen_height: int = 480
    fps: int = 50                       # canonical simulation rate (human play)

    # --- spawning ---
    cat_spawn_interval: int = 100       # frames between spawns (was already frame-based)
    cat_spawn_noise_std: float = 60.0   # gaussian jitter on the spawn timer, in frames
    initial_cat_timer: int = 20         # frames before the very first cat
    cats_before_boss: int = 40          # kills required before the boss appears

    # --- speeds (pixels per frame) ---
    dog_speed: float = 7.0
    cat_speed: float = 2.0              # initial global cat speed
    max_cat_speed: float = 7.5
    boss_speed: float = 5.0
    boss_health: int = 20
    bark_speed: float = 45.0

    # --- frame-based timers (were milliseconds in the original) ---
    bark_cooldown_frames: int = 18      # was 350 ms
    speed_increase_frames: int = 500    # was 10000 ms

    # --- food placement ---
    food_levels_before_dog: int = 4     # food sits this many cat-rows above the dog
    food_x: int = 180                   # center x of the food (was FOOD_X_BASE + FOOD_X_OFFSET)

    # --- rendering toggles ---
    # Draw the bark projectiles? Turning this off is a fun RL twist: the
    # agent can no longer SEE its own shots in the observation and must
    # learn the bark timing/trajectory implicitly (partial observability).
    barks_visible: bool = True

    # --- round intro ---
    # Aunt Larissa walks in and places the cat food before the round starts.
    # The RL env disables this by default (the food simply exists at frame 0)
    # so episodes don't begin with ~170 unactionable frames.
    intro_enabled: bool = True

    # --- anti-camping quirks ---
    # With this probability a new cat spawns near the dog's current column
    # (Normal(dog.x, 80) clipped to the screen) instead of uniformly. Cats
    # statistically come to wherever the agent loiters, so parking in a
    # corner is not a winning policy.
    spawn_target_bias: float = 0.35

    pattern_weights_by_wave: tuple = field(default_factory=_default_pattern_weights)


@dataclass
class RewardConfig:
    """Reward signal for the RL environment, accumulated from engine events.

    This is THE experimentation surface for reward design. Each knob exists
    to fight a specific degenerate policy:

      cat_kill   - the main objective signal. Too low relative to `death`
                   and the agent learns pure dodging instead of attacking.
      boss_hit   - dense shaping for the boss fight; without it the agent
                   only sees a reward 20 hits later (sparse-reward problem).
      boss_kill  - the jackpot; winning must dominate farming.
      death      - must be painful, but if it dwarfs everything else the
                   agent becomes a coward that never approaches cats.
      per_frame  - 0 by default. A small negative value punishes stalling
                   (e.g. dodging forever without engaging the boss); a small
                   positive value rewards survival. Both have side effects -
                   try them and watch what behavior they buy you.
      bark_fired - 0 by default. A tiny negative value discourages spamming
                   bark on cooldown regardless of aim.
    """
    cat_kill: float = 1.0
    boss_hit: float = 0.5
    boss_kill: float = 10.0
    death: float = -10.0
    per_frame: float = 0.0
    bark_fired: float = 0.0
