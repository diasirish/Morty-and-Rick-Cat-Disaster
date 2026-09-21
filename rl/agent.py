"""SKELETON #3 - the agent (the algorithm itself).

This is where the actual reinforcement LEARNING lives. The train loop
(rl/train.py) is already wired to call exactly three things:

    agent.select_action(obs, step)   every env step
    agent.observe(transition)        every env step
    agent.update(step)               every env step (you decide inside
                                     whether this step actually trains)

Fill in DQNAgent below and `python -m rl.train` starts learning. The
RandomAgent at the bottom is complete - it is the pipeline smoke test
(`--random-agent`) and your baseline to beat.

THE DQN RECIPE (deep Q-learning with the two classic stabilizers)
-----------------------------------------------------------------
You maintain TWO copies of the QNetwork:

    online network  - the one you train and act with
    target network  - a frozen snapshot, refreshed from the online one
                      every `target_update_every` steps

Why two? The Bellman update regresses Q(s,a) toward a target computed from
Q(s',·). If the same moving network appears on both sides, you are chasing
a target that shifts with every gradient step - training oscillates or
explodes. Freezing the bootstrap side is what made DQN work.

ACTING: epsilon-greedy
----------------------
    with probability eps:  random action          (explore)
    otherwise:             argmax_a Q_online(s)   (exploit)

Anneal eps linearly from eps_start (1.0) to eps_end (~0.05) over
eps_decay_steps (~100k), then keep it at eps_end. Without exploration the
agent can never discover that, say, killing the boss pays +10.

LEARNING: one gradient step (inside update())
---------------------------------------------
    1. (obs, a, r, next_obs, done) = buffer.sample(batch_size)
    2. prediction:  q = Q_online(obs).gather(1, a)          # Q of taken action
    3. target (no grad!):
           y = r                                  where done
           y = r + gamma * max_a' Q_target(next_obs)   elsewhere
       i.e.  y = r + gamma * (1 - done) * Q_target(next_obs).max(dim=1)
    4. loss = HuberLoss(q, y)     (smooth_l1 - more robust than MSE here)
    5. optimizer.zero_grad(); loss.backward(); optimizer.step()

Standard hyperparameters that work on this game's scale:
    gamma=0.99, lr=1e-4 (Adam), batch_size=32, buffer capacity 50_000,
    learning_starts=5_000 (fill the buffer before training),
    train_every=4 (one gradient step per 4 env steps),
    target_update_every=2_000.

UPGRADE PATH once vanilla DQN learns: Double DQN (one-line target change),
dueling heads (networks.py), prioritized replay (replay_buffer.py), then
rewrite the whole agent as PPO for a policy-gradient perspective.
"""

from __future__ import annotations

import numpy as np
import torch


class DQNAgent:
    def __init__(
        self,
        n_actions: int = 6,
        device: str | None = None,
        gamma: float = 0.99,
        lr: float = 1e-4,
        batch_size: int = 32,
        buffer_capacity: int = 50_000,
        learning_starts: int = 5_000,
        train_every: int = 4,
        target_update_every: int = 2_000,
        eps_start: float = 1.0,
        eps_end: float = 0.05,
        eps_decay_steps: int = 100_000,
    ):
        self.n_actions = n_actions
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.gamma = gamma
        self.batch_size = batch_size
        self.learning_starts = learning_starts
        self.train_every = train_every
        self.target_update_every = target_update_every
        self.eps_start, self.eps_end = eps_start, eps_end
        self.eps_decay_steps = eps_decay_steps
        self.rng = np.random.default_rng(0)

        # TODO(you):
        #   1. build self.online = QNetwork(n_actions).to(self.device)
        #   2. build self.target as a copy:
        #        self.target = QNetwork(n_actions).to(self.device)
        #        self.target.load_state_dict(self.online.state_dict())
        #        self.target.eval()
        #   3. self.optimizer = torch.optim.Adam(self.online.parameters(), lr=lr)
        #   4. self.buffer = ReplayBuffer(buffer_capacity, device=self.device)
        raise NotImplementedError("TODO: implement DQNAgent.__init__")

    # ------------------------------------------------------------------

    def epsilon(self, step: int) -> float:
        """Linear anneal: eps_start -> eps_end over eps_decay_steps."""
        frac = min(1.0, step / self.eps_decay_steps)
        return self.eps_start + frac * (self.eps_end - self.eps_start)

    def select_action(self, obs: np.ndarray, step: int) -> int:
        """Epsilon-greedy over the online network's Q-values.

        obs arrives as uint8 (4, 84, 84) - one observation, no batch dim.
        """
        # TODO(you):
        #   if self.rng.uniform() < self.epsilon(step): random action
        #   else:
        #       with torch.no_grad():
        #           t = torch.from_numpy(np.asarray(obs))[None].to(self.device)
        #           return int(self.online(t).argmax(dim=1).item())
        raise NotImplementedError("TODO: implement DQNAgent.select_action")

    def observe(self, obs, action, reward, next_obs, terminated) -> None:
        """Store a transition. Remember: pass `terminated`, not truncated."""
        # TODO(you): self.buffer.push(...)
        raise NotImplementedError("TODO: implement DQNAgent.observe")

    def update(self, step: int) -> float | None:
        """Maybe do one gradient step; return the loss (or None if skipped).

        Skip when: buffer smaller than learning_starts, or
                   step % train_every != 0.
        Also: every target_update_every steps, copy online -> target.
        """
        # TODO(you): the 5-line recipe from the module docstring.
        raise NotImplementedError("TODO: implement DQNAgent.update")

    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        # TODO(you): torch.save(self.online.state_dict(), path)
        raise NotImplementedError("TODO: implement DQNAgent.save")

    def load(self, path: str) -> None:
        # TODO(you): load the state dict into self.online (and self.target),
        # map_location=self.device so checkpoints move between machines.
        raise NotImplementedError("TODO: implement DQNAgent.load")


class RandomAgent:
    """Fully working baseline: mashes random buttons.

    Two jobs: (1) smoke-test the entire pipeline before you write any RL
    (`python -m rl.train --random-agent`), and (2) set the score to beat -
    if your DQN does not clearly outperform this, something is wrong.
    """

    def __init__(self, n_actions: int = 6, seed: int = 0):
        self.n_actions = n_actions
        self.rng = np.random.default_rng(seed)

    def select_action(self, obs, step) -> int:
        return int(self.rng.integers(self.n_actions))

    def observe(self, *args) -> None:
        pass

    def update(self, step) -> None:
        return None

    def save(self, path) -> None:
        pass

    def load(self, path) -> None:
        pass
