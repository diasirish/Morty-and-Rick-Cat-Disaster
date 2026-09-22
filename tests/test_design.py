import numpy as np
import pygame
import pytest

from game.assets import Assets
from game.config import GameConfig
from game.design import DesignRenderer, THEMES, design_loop, load_design, save_design
from game.engine import GameEngine
from game.render import Renderer
from fly_panel import FlyPanelEnv


@pytest.fixture(autouse=True)
def headless_display(monkeypatch):
    monkeypatch.setenv('SDL_VIDEODRIVER','dummy')
    monkeypatch.setenv('SDL_AUDIODRIVER','dummy')


def test_preferences_roundtrip_and_invalid_file(tmp_path):
    path=tmp_path/'design.json'
    assert load_design(path)=='backyard'
    save_design('midnight',path)
    assert load_design(path)=='midnight'
    path.write_text('broken')
    assert load_design(path)=='backyard'
    path.write_text('[]')
    assert load_design(path)=='backyard'


def test_original_is_pixel_identical_and_themes_are_spectator_only():
    env=FlyPanelEnv(None,design='original')
    try:
        env.reset(seed=0)
        expected=env._observation().copy()
        baseline=pygame.surfarray.array3d(Renderer(env.assets,env.config).draw(env.engine))
        original=pygame.surfarray.array3d(DesignRenderer(env.assets,env.config,'original').draw(env.engine))
        np.testing.assert_array_equal(baseline,original)
        for design in THEMES:
            env.set_design(design)
            env.render()
            np.testing.assert_array_equal(expected,env._observation())
        assert not np.array_equal(baseline,pygame.surfarray.array3d(env.view_renderer.draw(env.engine)))
    finally:
        env.close()


def test_menu_apply_cancel_and_quit(monkeypatch,tmp_path):
    pygame.init()
    screen=pygame.display.set_mode((640,480))
    path=tmp_path/'design.json'
    def key(k): return pygame.event.Event(pygame.KEYDOWN,key=k)
    monkeypatch.setattr(pygame.event,'get',lambda:[key(pygame.K_RIGHT),key(pygame.K_RETURN)])
    assert design_loop(screen,Assets(),'original',path)=='backyard'
    assert load_design(path)=='backyard'
    monkeypatch.setattr(pygame.event,'get',lambda:[key(pygame.K_RIGHT),key(pygame.K_ESCAPE)])
    assert design_loop(screen,Assets(),'backyard',path)=='backyard'
    assert load_design(path)=='backyard'
    monkeypatch.setattr(pygame.event,'get',lambda:[
        pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(450,90)),
        pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(470,440))])
    assert design_loop(screen,Assets(),'backyard',path)=='midnight'
    assert load_design(path)=='midnight'
    monkeypatch.setattr(pygame.event,'get',lambda:[pygame.event.Event(pygame.QUIT)])
    assert design_loop(screen,Assets(),'backyard',path)=='quit'
    pygame.display.quit()
