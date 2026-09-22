from types import SimpleNamespace
import numpy as np
import pygame
import pytest
from fly_panel import BrainPanel
from game.engine import Action


@pytest.mark.parametrize('design',['original','backyard','midnight'])
def test_graph_is_visible_on_repeated_frames_and_theme_switch(design,monkeypatch):
    monkeypatch.setenv('SDL_VIDEODRIVER','dummy')
    monkeypatch.setenv('SDL_AUDIODRIVER','dummy')
    pygame.init()
    pygame.display.set_mode((1060,480))
    brain=SimpleNamespace(n=12,side=np.array(['L','R']*6),
                          cell_type=np.array(['test']*12),
                          indptr=np.arange(13),indices=np.roll(np.arange(12),1))
    groups=[[np.array([0]),np.array([1])],[np.array([2]),np.array([3])]]
    ctrl=SimpleNamespace(brain=brain,inputs=groups,outputs=groups,
                         telemetry_tick=1,last_spikes=np.arange(12),
                         last_drive=np.zeros((2,2)),rates=np.zeros((2,2)),
                         spike_count=12,sample_seconds=.08,last_action=Action.NOOP)
    monkeypatch.setattr('fly_panel.time.monotonic',lambda:10.0)
    panel=BrainPanel(ctrl,design)
    for theme in [design,'original',design]:
        panel.design=theme
        for _ in range(3):
            surface=panel.draw()
            # At every sampled, firing neuron's location, the bright dot must
            # remain visible above the final theme's screen/background.
            assert all(sum(surface.get_at(point)[:3])>250 for point in panel.points)
    pygame.display.quit()
