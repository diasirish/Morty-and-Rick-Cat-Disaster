"""RL environment compliance, reproducibility and speed."""

import numpy as np
import pytest

from rl.env import CatDisasterEnv
from rl.wrappers import make_env


@pytest.fixture(scope="module")
def env():
    e = CatDisasterEnv()
    yield e
    e.close()


def test_gymnasium_compliance(env):
    from gymnasium.utils.env_checker import check_env
    check_env(env, skip_render_check=True)


def test_observation_shapes():
    cases = [
        (dict(grayscale=True, obs_size=(84, 84)), (84, 84)),
        (dict(grayscale=False, obs_size=(84, 84)), (84, 84, 3)),
        (dict(grayscale=True, obs_size=(120, 160)), (120, 160)),
    ]
    for kwargs, expected in cases:
        e = CatDisasterEnv(**kwargs)
        obs, _ = e.reset(seed=0)
        assert obs.shape == expected
        assert obs.dtype == np.uint8
        e.close()


def test_seeded_reset_is_pixel_identical(env):
    obs_a, _ = env.reset(seed=99)
    for _ in range(20):
        obs_step_a, *_ = env.step(1)
    obs_b, _ = env.reset(seed=99)
    for _ in range(20):
        obs_step_b, *_ = env.step(1)
    assert np.array_equal(obs_a, obs_b)
    assert np.array_equal(obs_step_a, obs_step_b)


def test_episode_terminates_or_truncates():
    e = CatDisasterEnv(max_episode_frames=2000)
    e.reset(seed=0)
    rng = np.random.default_rng(0)
    for _ in range(2000):
        _, _, terminated, truncated, info = e.step(int(rng.integers(0, 6)))
        if terminated or truncated:
            break
    assert terminated or truncated
    assert info["frame"] <= 2000 + e.frame_skip
    e.close()


def test_death_pays_death_reward():
    e = CatDisasterEnv()
    e.reset(seed=4)
    total_kill_reward = 0.0
    for _ in range(20000):
        _, reward, terminated, truncated, info = e.step(0)  # NOOP until death
        if terminated:
            assert reward <= e.reward_config.death + total_kill_reward + 1e-9
            assert "DOG_DIED" in info["events"]
            break
        if truncated:
            pytest.fail("standing still should end in death, not truncation")
    assert terminated
    e.close()


def test_frame_stack_wrapper_shape():
    e = make_env(frame_stack=4)
    obs, _ = e.reset(seed=0)
    assert obs.shape == (4, 84, 84), "stacked obs must be CNN-ready (C,H,W)"
    obs, *_ = e.step(3)
    assert obs.shape == (4, 84, 84)
    e.close()


def test_headless_speed():
    """Headless training must be comfortably faster than real time.

    Target: > 200 env steps/s (with frame_skip=4 that is > 800 simulated
    frames/s, i.e. > 16x real time). The engine alone does ~250k steps/s;
    rendering the observation dominates.
    """
    import time
    e = CatDisasterEnv()
    e.reset(seed=0)
    n = 600
    start = time.perf_counter()
    for i in range(n):
        _, _, terminated, truncated, _ = e.step(i % 6)
        if terminated or truncated:
            e.reset()
    rate = n / (time.perf_counter() - start)
    e.close()
    assert rate > 200, f"only {rate:.0f} env steps/s - headless path too slow"
