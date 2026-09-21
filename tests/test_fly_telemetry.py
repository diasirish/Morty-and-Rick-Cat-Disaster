import numpy as np

from fly_demo import FlyController
from game.config import GameConfig
from game.engine import Action, GameEngine


def test_telemetry_keeps_early_substep_spikes_and_counts_repeats():
    class Brain:
        dt = 0.02
        calls = 0
        def step(self, inject):
            samples = ([2, 4], [4], [], [3])
            fired = np.array(samples[self.calls], dtype=int)
            self.calls += 1
            return fired
        def reset(self, seed):
            self.calls = 0

    controller = FlyController.__new__(FlyController)
    controller.brain = Brain()
    controller.inputs = [[np.array([0]), np.array([1])]] * 2
    controller.outputs = [[np.array([2]), np.array([3])]] * 2
    controller.rates = np.zeros((2, 2))
    controller._clear_telemetry()
    engine = GameEngine(GameConfig(intro_enabled=False))
    engine.reset(seed=0)
    controller.act(engine)
    np.testing.assert_array_equal(controller.last_spikes, [2, 3, 4])
    assert controller.spike_count == 4
    assert controller.sample_seconds == 0.08
    assert controller.telemetry_tick == 1
    controller.reset(0)
    assert not controller.last_spikes.size
    assert not controller.last_drive.any()
    assert not controller.rates.any()
    assert controller.spike_count == controller.telemetry_tick == 0
    assert controller.last_action == Action.NOOP
