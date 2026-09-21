"""SKELETON #1 - the neural network. Start here.

This is the first of the three files you write yourself (the suggested
order: networks.py -> replay_buffer.py -> agent.py). Everything around them
(env, wrappers, train loop, inference) is finished and tested, so the moment
your three TODOs work, training runs end to end.

THE JOB OF THIS NETWORK
-----------------------
A Q-network is a function  Q(state) -> value of each button.
Given the stacked frames, it outputs 6 numbers: "if I press LEFT now (and
play well afterwards), how much total reward do I expect?" - one estimate
per action. The agent then simply presses the button with the largest value
(except when exploring; see agent.py).

TENSOR SHAPES, EXACTLY
----------------------
    input   (B, 4, 84, 84) float32 in [0, 1]
            B = batch size; 4 stacked grayscale frames = 4 input channels.
            (The train loop hands you uint8 [0,255]; the canonical place to
            divide by 255.0 is the first line of forward().)
    output  (B, 6) float32 - one Q-value per Action, NO activation on top
            (Q-values are unbounded; a softmax/sigmoid here is a classic bug).

THE CLASSIC ARCHITECTURE (Nature DQN, Mnih et al. 2015)
-------------------------------------------------------
    Conv2d(4,  32, kernel_size=8, stride=4)  + ReLU   -> (B, 32, 20, 20)
    Conv2d(32, 64, kernel_size=4, stride=2)  + ReLU   -> (B, 64,  9,  9)
    Conv2d(64, 64, kernel_size=3, stride=1)  + ReLU   -> (B, 64,  7,  7)
    Flatten                                            -> (B, 3136)
    Linear(3136, 512)                        + ReLU   -> (B, 512)
    Linear(512, n_actions)                            -> (B, 6)

It is fine to start with exactly this. Once it learns, experiment:
dueling heads, more/fewer filters, layer norm...
"""

import torch
import torch.nn as nn


class QNetwork(nn.Module):
    """Maps stacked frames to one Q-value per action."""

    def __init__(self, n_actions: int = 6, in_channels: int = 4):
        super().__init__()
        # TODO(you): build the layers described in the module docstring.
        # Tip: nn.Sequential keeps forward() to a few lines.
        raise NotImplementedError(
            "TODO: implement QNetwork.__init__ - see the architecture table "
            "in rl/networks.py's docstring"
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # TODO(you):
        #   1. x arrives as uint8 (B, 4, 84, 84); convert: x.float() / 255.0
        #   2. push through conv stack + linear head
        #   3. return raw (B, n_actions) values - no final activation!
        raise NotImplementedError("TODO: implement QNetwork.forward")
