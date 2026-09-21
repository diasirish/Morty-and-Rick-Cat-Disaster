"""Inference - mode (c). THIS FILE IS COMPLETE.

Watch a trained policy play, no learning, (almost) no exploration:

    python -m rl.play --checkpoint runs/dqn/model.pt
    python -m rl.play --random-agent          # watch the baseline flail
    python -m rl.play --checkpoint runs/dqn/model.pt --episodes 10 --eps 0.0

A tiny epsilon (default 0.01) is kept during inference on purpose: a fully
deterministic policy can wedge itself into a corner-loop forever; a 1%
random twitch breaks such cycles. Set --eps 0 to see the pure argmax policy.
"""

import argparse
import time

from .agent import DQNAgent, RandomAgent
from .wrappers import make_env


def parse_args():
    parser = argparse.ArgumentParser(description="Watch a trained agent play")
    parser.add_argument("--checkpoint", default=None,
                        help="path to a model.pt saved by rl.train")
    parser.add_argument("--random-agent", action="store_true")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--eps", type=float, default=0.01,
                        help="residual exploration during inference")
    parser.add_argument("--fps", type=int, default=12,
                        help="env steps per second to render (12 steps * "
                             "frame_skip 4 = real-time 50 fps)")
    parser.add_argument("--character", default="morty", choices=["morty", "rick"])
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.random_agent and not args.checkpoint:
        raise SystemExit("either --checkpoint <path> or --random-agent is required")

    env = make_env(render=True, seed=args.seed, character=args.character)
    if args.random_agent:
        agent = RandomAgent(seed=args.seed)
    else:
        agent = DQNAgent(eps_start=args.eps, eps_end=args.eps)
        agent.load(args.checkpoint)

    min_dt = 1.0 / args.fps if args.fps else 0.0
    for episode in range(1, args.episodes + 1):
        obs, _ = env.reset()
        ep_return, done = 0.0, False
        while not done:
            t0 = time.perf_counter()
            action = agent.select_action(obs, step=10**9)  # fully annealed eps
            obs, reward, terminated, truncated, info = env.step(action)
            ep_return += reward
            done = terminated or truncated
            sleep = min_dt - (time.perf_counter() - t0)
            if sleep > 0:
                time.sleep(sleep)
        outcome = "WON" if info["won"] else ("died" if terminated else "timed out")
        print(f"episode {episode}: return {ep_return:7.2f}  "
              f"score {info['score']:3d}  {outcome}")
    env.close()


if __name__ == "__main__":
    main()
