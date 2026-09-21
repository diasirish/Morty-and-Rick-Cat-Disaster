import numpy as np

from fly_demo import FlyController, decode_rates, encode_scene
from game.config import GameConfig
from game.engine import Action, GameEngine
from game.entities import CatState


def test_sensory_input_tracks_target_side_and_ignores_dead_cats():
    engine = GameEngine(GameConfig(intro_enabled=False))
    engine.reset(seed=0)
    engine.dog.x = 300
    engine.cats = [CatState(x=180, y=engine.dog.y - 100)]
    left = encode_scene(engine)
    engine.cats[0].x = 420
    right = encode_scene(engine)
    np.testing.assert_allclose(left, right[::-1])
    assert left[0].sum() > 0 and left[1].sum() == 0
    engine.cats[0].active = False
    assert not encode_scene(engine).any()


def test_silent_outputs_cannot_move_or_bark():
    assert decode_rates(np.zeros((2, 2))) == Action.NOOP
    assert decode_rates(np.array([[10, 0], [0, 0]])) == Action.LEFT
    assert decode_rates(np.array([[0, 0], [10, 5]])) == Action.RIGHT_BARK


def test_controller_does_not_bypass_brain_to_act():
    class SilentBrain:
        dt = 0.02
        def step(self, inject):
            assert inject  # a cat is seen, but the brain does not respond
            return np.array([], dtype=int)

    controller = FlyController.__new__(FlyController)
    controller.brain = SilentBrain()
    controller.inputs = [[np.array([0]), np.array([1])]] * 2
    controller.outputs = [[np.array([2]), np.array([3])]] * 2
    controller.rates = np.zeros((2, 2))
    engine = GameEngine(GameConfig(intro_enabled=False))
    engine.reset(seed=0)
    engine.cats = [CatState(x=engine.dog.x + 100, y=engine.dog.y - 100)]
    assert controller.act(engine) == Action.NOOP
