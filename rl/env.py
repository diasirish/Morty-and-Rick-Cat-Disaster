"""CatDisasterEnv - the Gymnasium environment. THIS FILE IS COMPLETE.

================== HOW THE RL PLUGS INTO THE GAME ==========================

An RL problem needs four things; here is where each one comes from:

  OBSERVATION  "what the agent sees"
      The rendered game frame (game/render.py draws the engine state onto a
      640x480 surface) downscaled to `obs_size` (default 84x84) and converted
      to grayscale uint8. Exactly what you asked for: the agent's input is
      the VISUAL of the map, the same picture a human sees - no cheating
      with hidden coordinates.

  ACTION  "the buttons"
      Discrete(6) = the engine's Action enum:
      0 NOOP, 1 LEFT, 2 RIGHT, 3 BARK, 4 LEFT+BARK, 5 RIGHT+BARK.
      A human playing with the keyboard produces the very same 6 values
      (see keys_to_action in main.py).

  REWARD  "the objective"
      The engine emits Events (CAT_KILLED, DOG_DIED, ...); this env converts
      them to scalars using RewardConfig (game/config.py). Tuning those
      numbers is reward design - half the craft of RL. Start with the
      defaults, then experiment.

  EPISODE  "when does it end"
      terminated = the dog died (loss) or the boss died (win).
      truncated  = `max_episode_frames` reached without either - the env
      cuts the episode short, the task itself did not end (this distinction
      matters for bootstrapping the value of the final state).

Two performance conventions borrowed from the Atari literature:

  frame_skip   Each env.step() repeats your action for 4 engine frames and
               returns only the final picture. The game does not change
               much in 1/50 s; deciding every 4th frame is ~4x cheaper and
               usually LEARNS BETTER (actions have visible consequences).

  frame stack  A single frame cannot show velocity (is the cat moving left
               or right?). rl/wrappers.py stacks the last 4 observations
               into a (4, 84, 84) array so the network can infer motion.
               See make_env().

Headless trick: when render_mode != "human" we initialize SDL with its
"dummy" video driver - pygame happily draws onto offscreen surfaces with no
window, no GPU, no vsync. That is the whole difference between "learning
mode with visualization" and "learning mode without": the same env, with or
without a real window.
============================================================================
"""

from __future__ import annotations

import os

import gymnasium as gym
import numpy as np
import pygame
from gymnasium import spaces

from game.assets import Assets
from game.config import GameConfig, RewardConfig
from game.engine import Action, EventType, GameEngine
from game.render import Renderer

# Event -> RewardConfig attribute
_REWARDED_EVENTS = {
    EventType.CAT_KILLED: "cat_kill",
    EventType.BOSS_HIT: "boss_hit",
    EventType.BOSS_KILLED: "boss_kill",
    EventType.DOG_DIED: "death",
    EventType.BARK_FIRED: "bark_fired",
}


class CatDisasterEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 50}

    def __init__(
        self,
        render_mode: str | None = None,
        obs_size: tuple[int, int] = (84, 84),
        grayscale: bool = True,
        frame_skip: int = 4,
        max_episode_frames: int = 9000,   # 3 simulated minutes at 50 FPS
        config: GameConfig | None = None,
        reward_config: RewardConfig | None = None,
        character: str = "morty",
    ):
        super().__init__()
        if config is None:
            # RL episodes skip Aunt Larissa's walk-in by default: the food
            # simply exists at frame 0, so no dead unactionable frames.
            config = GameConfig(intro_enabled=False)
        self.config = config
        self.reward_config = reward_config or RewardConfig()
        self.render_mode = render_mode
        self.obs_size = obs_size
        self.grayscale = grayscale
        self.frame_skip = frame_skip
        self.max_episode_frames = max_episode_frames

        self._init_pygame()
        self.engine = GameEngine(config, character)
        self.assets = Assets()
        self.renderer = Renderer(self.assets, config)
        self._window = None

        h, w = obs_size
        shape = (h, w) if grayscale else (h, w, 3)
        self.observation_space = spaces.Box(0, 255, shape=shape, dtype=np.uint8)
        self.action_space = spaces.Discrete(len(Action))

    # ------------------------------------------------------------------

    def _init_pygame(self):
        """Init pygame; with no real window when training headless."""
        if pygame.display.get_surface() is not None:
            return  # something already set up a display (e.g. --render mode)
        if self.render_mode != "human":
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        if self.render_mode == "human":
            self._open_window()
        else:
            # a 1x1 hidden surface so .convert_alpha() works headlessly
            pygame.display.set_mode((1, 1))

    def _open_window(self):
        self._window = pygame.display.set_mode(
            (self.config.screen_width, self.config.screen_height))
        pygame.display.set_caption("Cat Disaster - agent view")

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(self, *, seed: int | None = None, options=None):
        super().reset(seed=seed)  # seeds self.np_random
        # Derive the engine seed from gymnasium's RNG: reset(seed=k) is
        # fully reproducible, while reset() keeps episodes varied.
        engine_seed = int(self.np_random.integers(0, 2**31 - 1))
        self.engine.reset(seed=engine_seed)
        obs = self._observation()
        if self.render_mode == "human":
            self._render_human()
        return obs, self._info([])

    def step(self, action):
        action = Action(int(action))
        reward = 0.0
        events = []
        for _ in range(self.frame_skip):
            frame_events = self.engine.step(action)
            events.extend(frame_events)
            reward += self.reward_config.per_frame
            for event in frame_events:
                attr = _REWARDED_EVENTS.get(event.type)
                if attr is not None:
                    reward += getattr(self.reward_config, attr)
            if self.engine.done:
                break

        terminated = self.engine.done
        truncated = not terminated and self.engine.frame >= self.max_episode_frames
        obs = self._observation()
        if self.render_mode == "human":
            self._render_human()
        return obs, reward, terminated, truncated, self._info(events)

    def render(self):
        if self.render_mode == "rgb_array":
            return self._rgb_frame()
        if self.render_mode == "human":
            self._render_human()
        return None

    def close(self):
        if self._window is not None:
            pygame.display.quit()
            self._window = None

    # ------------------------------------------------------------------
    # Observation pipeline: engine state -> pixels
    # ------------------------------------------------------------------

    def _rgb_frame(self):
        """Full-resolution RGB frame (H, W, 3) uint8."""
        surface = self.renderer.draw(self.engine)
        return np.transpose(pygame.surfarray.array3d(surface), (1, 0, 2))

    def _observation(self):
        surface = self.renderer.draw(self.engine)
        h, w = self.obs_size
        small = pygame.transform.smoothscale(surface, (w, h))
        rgb = np.transpose(pygame.surfarray.array3d(small), (1, 0, 2))
        if not self.grayscale:
            return rgb.astype(np.uint8)
        gray = rgb @ np.array([0.299, 0.587, 0.114])
        return gray.astype(np.uint8)

    def _render_human(self):
        if self._window is None:
            self._open_window()
        self._window.blit(self.renderer.draw(self.engine), (0, 0))
        pygame.event.pump()  # keep the window responsive
        pygame.display.flip()

    # ------------------------------------------------------------------

    def _info(self, events):
        return {
            "score": self.engine.score,
            "frame": self.engine.frame,
            "won": self.engine.won,
            "events": [e.type.name for e in events],
        }
