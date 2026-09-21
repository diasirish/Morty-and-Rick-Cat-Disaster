"""Engine invariants: determinism, frame-based timers, anti-camping.

These tests run with NO pygame at all - that is the point of the engine
split. If an import of pygame sneaks into game/engine.py, game/entities.py,
game/patterns.py or game/config.py, the purity test below fails.
"""

import os
import subprocess
import sys

import pytest

from game.config import GameConfig
from game.engine import Action, EventType, GameEngine


def make_engine(seed=0, **overrides):
    cfg = GameConfig(intro_enabled=False, **overrides)
    eng = GameEngine(cfg)
    eng.reset(seed=seed)
    return eng


def scripted_actions(n, seed=7):
    """A fixed pseudo-random action script (independent of the engine RNG)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    return [Action(int(a)) for a in rng.integers(0, 6, size=n)]


# ---------------------------------------------------------------------------
# Purity / no-pygame
# ---------------------------------------------------------------------------

def test_engine_does_not_import_pygame():
    # run in a clean interpreter: this test must not depend on what the
    # rest of the suite already imported into this process
    code = (
        "import sys; import game.engine, game.entities, game.patterns, "
        "game.config; sys.exit(1 if 'pygame' in sys.modules else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code],
                            cwd=os.path.dirname(os.path.dirname(__file__)))
    assert result.returncode == 0, "the pure engine modules must not pull in pygame"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_seed_same_trajectory():
    actions = scripted_actions(3000)
    a, b = make_engine(seed=123), make_engine(seed=123)
    for i, act in enumerate(actions):
        a.step(act)
        b.step(act)
        if i % 100 == 0:
            assert a.snapshot() == b.snapshot(), f"diverged at frame {i}"
    assert a.snapshot() == b.snapshot()


def test_different_seeds_diverge():
    actions = scripted_actions(1500)
    a, b = make_engine(seed=1), make_engine(seed=2)
    for act in actions:
        a.step(act)
        b.step(act)
    assert a.snapshot() != b.snapshot()


def test_reset_restores_initial_state():
    eng = make_engine(seed=5)
    first = eng.snapshot()
    for act in scripted_actions(500):
        eng.step(act)
    eng.reset(seed=5)
    assert eng.snapshot() == first


# ---------------------------------------------------------------------------
# Frame-based timers (the ms -> frames conversion)
# ---------------------------------------------------------------------------

def test_bark_cooldown_is_18_frames():
    eng = make_engine(seed=0)
    events = eng.step(Action.BARK)                       # frame 1: allowed
    assert any(e.type == EventType.BARK_FIRED for e in events)
    for _ in range(17):                                  # frames 2..18: blocked
        events = eng.step(Action.BARK)
        assert not any(e.type == EventType.BARK_FIRED for e in events)
    events = eng.step(Action.BARK)                       # frame 19 = 18 later
    assert any(e.type == EventType.BARK_FIRED for e in events)


def test_speed_ramp_ticks_at_exact_frames():
    eng = make_engine(seed=0)
    base = eng.cat_speed
    for _ in range(499):
        eng.step(Action.NOOP)
    assert eng.cat_speed == base, "no ramp before frame 500"
    eng.step(Action.NOOP)
    assert eng.cat_speed > base, "ramp exactly at frame 500"
    assert eng.cat_speed <= eng.config.max_cat_speed


def test_speed_never_exceeds_max():
    eng = make_engine(seed=0, spawn_target_bias=0.0)
    for _ in range(20000):
        eng.step(Action.NOOP)
        if eng.done:
            eng.reset(seed=eng.frame)
    assert eng.cat_speed <= eng.config.max_cat_speed


# ---------------------------------------------------------------------------
# Gameplay invariants
# ---------------------------------------------------------------------------

def test_dog_stays_inside_walls():
    eng = make_engine(seed=0)
    for _ in range(400):
        eng.step(Action.LEFT)
        if eng.done:
            pytest.skip("died before reaching the wall (unlucky seed)")
    assert eng.dog.x >= 0
    eng.reset(seed=0)
    for _ in range(400):
        eng.step(Action.RIGHT)
        if eng.done:
            pytest.skip("died before reaching the wall (unlucky seed)")
    assert eng.dog.x + eng.dog.width <= eng.config.screen_width


def test_cat_collision_kills_dog():
    eng = make_engine(seed=42)
    for _ in range(60000):
        eng.step(Action.NOOP)  # stand still and do nothing: certain death
        if eng.done:
            break
    assert eng.done and not eng.won


def test_intro_places_food_then_round_starts():
    cfg = GameConfig(intro_enabled=True)
    eng = GameEngine(cfg)
    eng.reset(seed=0)
    assert eng.phase == "intro"
    assert not eng.food.present
    seen = set()
    for _ in range(1000):
        for e in eng.step(Action.NOOP):
            seen.add(e.type)
        if eng.phase == "playing" and EventType.ROUND_STARTED in seen:
            break
    assert EventType.FOOD_PLACED in seen
    assert EventType.ROUND_STARTED in seen
    assert eng.food.present
    assert eng.frame < 250, "intro should be a few seconds, not longer"
    assert len(eng.cats) == 0 or eng.frame > 170, "no cats during the intro"


# ---------------------------------------------------------------------------
# Anti-degenerate-policy regression: the corner camper must lose
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("corner", [Action.LEFT, Action.RIGHT])
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_corner_camper_dies(corner, seed):
    """Hold one edge and bark on cooldown - the old degenerate near-win.

    With spawn bias + divers this policy must die within 6000 frames
    (2 simulated minutes). If this test starts failing after tuning
    pattern weights, the RL problem has regressed to triviality.
    """
    eng = make_engine(seed=seed)
    bark_corner = Action.LEFT_BARK if corner == Action.LEFT else Action.RIGHT_BARK
    for _ in range(6000):
        eng.step(bark_corner)
        if eng.done:
            break
    assert eng.done and not eng.won, "corner camping must not survive/win"
