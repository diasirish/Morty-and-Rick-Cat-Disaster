# Morty & Rick: Cat Disaster

A pygame arcade game - and a Gym-style reinforcement-learning environment.

Play as Morty (or Rick), barking at waves of cats descending across the
backyard. Aunt Larissa drops off a bowl of cat food at the start of every
round; any cat that reaches it grows huge and takes 9 barks to bring down.
Survive 40 kills and the boss cat appears - destroy it to win. Later waves
mix in quirky cat flight patterns (sine-weavers and stutter-steppers, with
dive-bombers and staircase-hoppers available but off by default), and some
cats deliberately spawn near wherever you are standing, so camping in a
corner does not work. That last part is on purpose:
this game doubles as an RL environment, and the quirks exist so an agent has
to actually learn something.

## Play it yourself

```bash
python3 -m venv .venv && source .venv/bin/activate   # or: uv venv
pip install -r requirements.txt
python main.py              # menus (character select: Morty or Rick)
python main.py --game_only  # straight into a round
```

Move with arrows or A/D, bark with Space, Esc quits a round.

## Reinforcement learning

The point of this repo: train an agent to break the game, writing the RL
algorithms yourself. The environment side is **done and tested**; the
learning side is **three skeleton files you implement**.

### The three modes

```bash
python -m rl.train --render          # (a) learning mode WITH visualization
python -m rl.train                   # (b) learning mode, headless (~120x real time)
python -m rl.play --checkpoint runs/dqn/model.pt   # (c) inference: watch it play

python -m rl.train --random-agent --render   # smoke test - works before any RL is written
python -m rl.play  --random-agent            # watch the random baseline flail
```

Training logs land in `runs/<name>/episodes.csv` (watch live with
`tail -f`); checkpoints in `runs/<name>/model.pt`.

### What the agent gets

* **Observation:** the rendered game frame, downscaled to 84x84 grayscale
  pixels - the same picture a human sees. With the standard frame-stack
  wrapper, the network input is a `(4, 84, 84)` uint8 array.
* **Actions:** the 6 buttons - NOOP, LEFT, RIGHT, BARK, LEFT+BARK,
  RIGHT+BARK. Identical to the keyboard mapping in `main.py`.
* **Reward:** +1 per cat killed, +0.5 per boss hit, +10 boss kill,
  -10 death (all tunable in `RewardConfig`, `game/config.py`).

### Where the RL comes in - a file map

Read these in order; each file's docstring continues the story:

| file | status | what it is |
|---|---|---|
| `game/engine.py` | done | the deterministic world: `step(action) -> events`, no pygame, no wall-clock |
| `game/render.py` | done | state -> pixels (the observation function) |
| `rl/env.py` | done | the Gymnasium env: observation/action/reward/episode glue |
| `rl/wrappers.py` | done | `make_env()` factory + a reward-shaping skeleton for later |
| `rl/train.py` | done | the canonical act/observe/learn loop, logging, checkpoints |
| `rl/play.py` | done | inference runner |
| `rl/networks.py` | **you, step 1** | the Q-network (architecture spelled out in the docstring) |
| `rl/replay_buffer.py` | **you, step 2** | experience replay (why + how in the docstring) |
| `rl/agent.py` | **you, step 3** | DQN itself: epsilon-greedy + Bellman update + target network |

The moment your three TODOs stop raising `NotImplementedError`,
`python -m rl.train` learns end to end. Beat the `--random-agent`
baseline first, then beat the game.

### Tests

```bash
python -m pytest          # engine determinism, env compliance, speed floors
```

Notable invariants: same seed = pixel-identical episodes; the
"stand-in-a-corner-and-bark" policy provably dies (that regression test is
what keeps the RL problem interesting).

## Project layout

```
main.py                  human game (thin driver of the engine)
game/                    engine, entities, cat patterns, renderer, audio, menus, config
rl/                      Gymnasium env + training/inference + your skeletons
tools/generate_assets.py regenerates derived art/sounds (background, Rick, Larissa...)
tests/                   engine + env test suites
```

Asset note: `Background_v4_doom` (the active backdrop), `Background_v3`,
`Rick_64x60`, `Larissa_*`, `food_32` and `woof_rick_1.wav` are generated
from the originals by `tools/generate_assets.py` - tweak the script and
re-run rather than editing them by hand. To switch back to the daylight
backdrop, reorder the `background` candidates in `game/assets.py`.
Cat coat colors (white/ginger/gray/brown) are rolled per spawn by the
engine and tinted in `game/render.py` (`CAT_TINTS`).
