"""Frozen flybrain -> Morty. State-based demo, NOT a trained RL policy."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault("NUMBA_NUM_THREADS", "4")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import numpy as np

from game.engine import Action


def encode_scene(engine):
    """Hand-designed sensory interface. Uses coordinates, not image recognition.

    LC10a gets targets to pursue. LC4/LPLC2 get nearby threats. Each
    hemisphere receives only objects on its side of Morty's center.
    """
    drive = np.zeros((2, 2), dtype=float)  # side x (target, threat)
    dog = engine.dog
    for cat in engine.cats:
        if not cat.active:
            continue
        dx = cat.x + cat.width / 2 - (dog.x + dog.width / 2)
        gap = max(0, dog.y - cat.y - cat.height)
        target = 0.65 * (1 - min(gap / engine.config.screen_height, 1))
        threat = 0.85 * max(0, 1 - gap / 240) * max(0, 1 - abs(dx) / 200)
        sides = (0, 1) if abs(dx) < 24 else ((0,) if dx < 0 else (1,))
        for side in sides:
            drive[side] = np.maximum(drive[side], (target, threat))
    return drive


def decode_rates(rates):
    """Designer-chosen mapping: DNa02 -> steering, DNp01 -> bark.

    A fly does not bark. These bindings are the game's actuator adapter.
    All action decisions here use neural outputs only.
    """
    turn = rates[1, 0] - rates[0, 0]
    move = -1 if turn < -1 else (1 if turn > 1 else 0)
    bark = bool(max(rates[:, 1]) > 2)
    return {(-1, False): Action.LEFT, (1, False): Action.RIGHT,
            (0, False): Action.NOOP, (-1, True): Action.LEFT_BARK,
            (1, True): Action.RIGHT_BARK, (0, True): Action.BARK}[move, bark]


class FlyController:
    def __init__(self, data, seed=0):
        from flybrain import FlyBrain
        self.brain = FlyBrain(data=data, device="cpu", seed=seed)
        self.inputs = [[self.brain.cells(types, side=side)
                        for types in (["LC10a"], ["LC4", "LPLC2"])]
                       for side in ("L", "R")]
        self.outputs = [[self.brain.cells([kind], side=side)
                         for kind in ("DNa02", "DNp01")]
                        for side in ("L", "R")]
        if any(len(ids) == 0 for groups in (self.inputs, self.outputs)
               for row in groups for ids in row):
            raise RuntimeError("Brain data lacks required left/right neuron types")
        self.rates = np.zeros((2, 2))

    def reset(self, seed):
        self.brain.reset(seed)
        self.rates.fill(0)

    def act(self, engine, steps=4, blind=False):
        drive = np.zeros((2, 2)) if blind else encode_scene(engine)
        inject = [(self.inputs[s][k], drive[s, k])
                  for s in range(2) for k in range(2) if drive[s, k] > 0]
        decay = np.exp(-self.brain.dt / 0.12)
        for _ in range(steps):
            fired = self.brain.step(inject=inject)
            for s in range(2):
                for k in range(2):
                    fraction = np.isin(self.outputs[s][k], fired).mean()
                    self.rates[s, k] = (decay * self.rates[s, k]
                                       + (1 - decay) * fraction / self.brain.dt)
        return decode_rates(self.rates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=2250)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--controller", choices=["fly", "blind", "random"], default="fly")
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parent.parent / "fruit_fly" / "brain-data")
    parser.add_argument("--report", type=Path, default=Path("runs/fly-demo.json"))
    args = parser.parse_args()
    if args.episodes < 1 or args.max_steps < 1:
        parser.error("episodes and max-steps must be positive")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    import pygame
    from rl.env import CatDisasterEnv
    controller = None if args.controller == "random" else FlyController(args.data, args.seed)
    env = CatDisasterEnv(render_mode=None if args.headless else "human")
    results = []
    clock = pygame.time.Clock()
    try:
        for episode in range(args.episodes):
            seed = args.seed + episode
            _, info = env.reset(seed=seed)
            rng = np.random.default_rng(seed)
            if controller:
                controller.reset(seed)
            reward_sum, counts = 0.0, [0] * 6
            start = time.perf_counter()
            terminated = truncated = stopped = False
            for step in range(args.max_steps):
                if not args.headless:
                    stopped = any(e.type == pygame.QUIT or
                                  (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE)
                                  for e in pygame.event.get())
                    if stopped:
                        break
                action = (controller.act(env.engine, env.frame_skip, args.controller == "blind")
                          if controller else int(rng.integers(6)))
                counts[int(action)] += 1
                _, reward, terminated, truncated, info = env.step(action)
                reward_sum += reward
                if not args.headless:
                    rates = controller.rates.round(1).tolist() if controller else []
                    pygame.display.set_caption(f"Morty | {args.controller} | score {info['score']} | neural Hz {rates}")
                    clock.tick(12)
                if terminated or truncated:
                    break
            row = dict(seed=seed, score=info["score"], won=info["won"],
                       reward=reward_sum, steps=sum(counts), action_counts=counts,
                       terminated=terminated, truncated=truncated,
                       stopped=stopped, step_limit=not (terminated or truncated or stopped),
                       seconds=round(time.perf_counter() - start, 3))
            results.append(row)
            print(json.dumps(row), flush=True)
            if stopped:
                break
    finally:
        env.close()
        pygame.quit()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(dict(controller=args.controller,
        observation="engine coordinates; hand-designed encoder; frozen brain; no RL training",
        episodes=results), indent=2) + "\n")


if __name__ == "__main__":
    main()
