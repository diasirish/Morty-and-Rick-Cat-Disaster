"""Environment factory + wrapper playground.

`make_env` is COMPLETE - use it everywhere you need an env.
`RewardShapingWrapper` at the bottom is a SKELETON left for your
experiments once you have a baseline agent training.
"""

import gymnasium as gym
from gymnasium.wrappers import FrameStackObservation

from .env import CatDisasterEnv


def make_env(render=False, frame_stack=4, seed=None, **env_kwargs):
    """Build the standard training environment.

    Why the frame stack: one grayscale frame is a snapshot - it cannot tell
    the network whether a cat is sweeping left or right, or how fast it is
    falling. Stacking the last `frame_stack` observations along a leading
    axis turns the observation into a short movie clip:

        single frame: (84, 84)        -> stacked: (4, 84, 84)

    Conveniently, (4, 84, 84) is exactly a 4-channel image, so a standard
    Conv2d(4, ...) input layer consumes it directly. This is the same
    arrangement the classic DQN Atari work used.

    Args:
        render: True opens a real window and draws every step - "learning
            mode WITH visualization". False runs headless at full speed.
        frame_stack: number of recent frames stacked (0/None disables).
        seed: passed to the first reset() for reproducible experiments.
        env_kwargs: forwarded to CatDisasterEnv (obs_size, frame_skip,
            reward_config, character, ...).
    """
    env = CatDisasterEnv(render_mode="human" if render else None, **env_kwargs)
    if frame_stack:
        env = FrameStackObservation(env, stack_size=frame_stack)
    if seed is not None:
        env.reset(seed=seed)
        env.action_space.seed(seed)
    return env


class RewardShapingWrapper(gym.RewardWrapper):
    """SKELETON - your reward-design playground.

    The base env already pays out RewardConfig values per event. Sometimes
    you want shaping that depends on STATE rather than events, e.g.:

      * a small bonus for being far from the nearest cat (survival shaping)
      * a penalty for hugging the screen edges (anti-camping shaping)
      * reward clipping to [-1, 1] (stabilizes DQN on varied magnitudes)

    Wrap it around make_env's output:

        env = RewardShapingWrapper(make_env())

    NOTE: `self.env.unwrapped.engine` gives you the full game state (dog and
    cat positions, etc.). Using it for REWARDS is fine and standard - the
    reward function is part of the problem definition, and is only needed at
    training time. Feeding it to the POLICY as an observation would be
    cheating against the "pixels only" premise.
    """

    def reward(self, reward):
        # TODO(you): reshape the scalar. Examples to try (one at a time!):
        #   1. clip:        return max(-1.0, min(1.0, reward))
        #   2. edge tax:    dog = self.env.unwrapped.engine.dog
        #                   if dog.x < 50 or dog.x > 526: reward -= 0.01
        #   3. proximity:   penalize the agent when a cat is within N px
        #                   of the dog (look at engine.cats).
        # Watch training curves before/after - that is the lesson.
        return reward
