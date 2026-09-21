"""SKELETON #2 - experience replay.

WHY A BUFFER AT ALL
-------------------
Gradient descent assumes (roughly) independent, identically distributed
samples. A game produces the opposite: consecutive frames are nearly
identical and heavily correlated. Train on them in order and the network
chases its own tail (it gets very good at "the last 2 seconds" and forgets
everything else - catastrophic forgetting).

The fix (Mnih et al. 2013) is almost embarrassingly simple: store the last
N transitions in a big ring buffer and train on RANDOM minibatches drawn
from it. Old and new experience get mixed, correlations are broken, and
each interaction with the environment is reused many times (sample
efficiency).

WHAT IS A TRANSITION
--------------------
One step of experience, the atomic unit of RL data:

    (obs, action, reward, next_obs, done)

    obs       (4, 84, 84) uint8  - what the agent saw
    action    int                - which button it pressed
    reward    float              - what the env paid out
    next_obs  (4, 84, 84) uint8  - what it saw next
    done      bool               - did the EPISODE TERMINATE here?
              (store `terminated`, NOT `terminated or truncated`! A
              truncated episode did not really end - the value of the
              next state still exists and must be bootstrapped.)

MEMORY MATH (read before you allocate)
--------------------------------------
Store observations as uint8, convert to float only inside the network.
One obs = 4*84*84 bytes = 28 KB; a 100k-capacity buffer holds obs AND
next_obs -> ~5.6 GB naively, ~2.8 GB if you only store obs and read
next_obs as the following entry... Start simple: capacity 50_000 with both
arrays stored is ~2.8 GB - fine on most machines. Optimize later.

SUGGESTED IMPLEMENTATION
------------------------
Pre-allocated numpy arrays + a write cursor that wraps around (a ring):

    self.obs      = np.zeros((capacity, 4, 84, 84), dtype=np.uint8)
    self.actions  = np.zeros(capacity, dtype=np.int64)
    ...
    self.cursor, self.size = 0, 0

push():   write at cursor, cursor = (cursor + 1) % capacity,
          size = min(size + 1, capacity)
sample(): idx = rng.integers(0, self.size, batch_size) and return the
          slices (as torch tensors, ideally already on the right device).
"""

import numpy as np
import torch


class ReplayBuffer:
    def __init__(self, capacity: int, obs_shape=(4, 84, 84), device="cpu"):
        self.capacity = capacity
        self.device = device
        # TODO(you): pre-allocate the storage arrays (see module docstring).
        raise NotImplementedError("TODO: implement ReplayBuffer.__init__")

    def push(self, obs, action, reward, next_obs, done) -> None:
        """Store one transition, overwriting the oldest when full."""
        # TODO(you): write into the arrays at the cursor, advance, wrap.
        raise NotImplementedError("TODO: implement ReplayBuffer.push")

    def sample(self, batch_size: int):
        """Return a random minibatch as torch tensors:
        (obs, actions, rewards, next_obs, dones)."""
        # TODO(you): uniform random indices in [0, len(self)).
        # torch.from_numpy(...) is zero-copy from numpy - cheap.
        raise NotImplementedError("TODO: implement ReplayBuffer.sample")

    def __len__(self) -> int:
        # TODO(you): number of stored transitions (NOT the capacity).
        raise NotImplementedError("TODO: implement ReplayBuffer.__len__")
