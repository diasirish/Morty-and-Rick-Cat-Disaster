"""Morty & Rick: Cat Disaster - the human-playable game.

This file is deliberately thin. All gameplay lives in game/engine.py (the
deterministic simulation), and this loop just feeds it keyboard actions and
shows the result:

    keyboard -> Action -> engine.step() -> events -> AudioPlayer
                                        -> state  -> Renderer -> window

The RL environment (rl/env.py) drives the very same engine and renderer -
an agent and a human literally play the same game with the same buttons.

Run:
    python main.py               # menus
    python main.py --game_only   # straight into a round
"""

import json
import os
import sys

import pygame

from game.assets import Assets
from game.audio import AudioPlayer
from game.config import GameConfig
from game.engine import Action, EventType, GameEngine
from game.design import DesignRenderer, load_design, design_loop
from game.ui import character_select_loop, menu_loop, options_loop

HIGHSCORE_PATH = "highscore.json"
GAME_OVER_LINGER_FRAMES = 350  # ~7 s at 50 FPS, the original linger


def load_highscore(path):
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return int(data.get("highscore", 0))
    except (OSError, ValueError, TypeError):
        return 0


def save_highscore(path, score):
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"highscore": score}, handle)
    except OSError:
        pass


def keys_to_action(keys):
    """Map held keys to the engine's discrete action space - the exact same
    6 'buttons' the RL agent gets."""
    left = keys[pygame.K_LEFT] or keys[pygame.K_a]
    right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
    bark = keys[pygame.K_SPACE]
    if left and not right:
        return Action.LEFT_BARK if bark else Action.LEFT
    if right and not left:
        return Action.RIGHT_BARK if bark else Action.RIGHT
    return Action.BARK if bark else Action.NOOP


def run_game(screen, config, highscore, character, assets, design="original"):
    engine = GameEngine(config, character)
    engine.reset()  # unseeded: every human round is fresh
    renderer = DesignRenderer(assets, config, design)
    audio = AudioPlayer(assets, character)
    clock = pygame.time.Clock()
    linger = GAME_OVER_LINGER_FRAMES

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return highscore, True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return highscore, False

        action = keys_to_action(pygame.key.get_pressed())
        events = engine.step(action)
        audio.handle(events)

        for event in events:
            if event.type in (EventType.DOG_DIED, EventType.BOSS_KILLED):
                if engine.score > highscore:
                    highscore = engine.score
                    save_highscore(HIGHSCORE_PATH, highscore)

        screen.blit(renderer.draw(engine, highscore), (0, 0))
        pygame.display.flip()
        clock.tick(config.fps)

        if engine.done:
            linger -= 1
            if linger <= 0:
                return highscore, False


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    game_only = "--game_only" in args

    pygame.init()
    pygame.mixer.init()

    config = GameConfig()
    screen = pygame.display.set_mode((config.screen_width, config.screen_height))
    pygame.display.set_caption("Morty & Rick: Cat Disaster")

    assets = Assets()
    font = pygame.font.Font(None, 24)
    title_font = pygame.font.Font(None, 48)
    highscore = load_highscore(HIGHSCORE_PATH)

    if game_only:
        run_game(screen, config, highscore, "morty", assets, load_design())
        pygame.quit()
        return

    running = True
    while running:
        design = load_design()
        choice = menu_loop(screen, font, title_font, assets, design)
        if choice == "start":
            character = character_select_loop(screen, font, title_font, assets, design)
            if character == "quit":
                running = False
            elif character is not None:
                highscore, quitting = run_game(screen, config, highscore, character, assets, design)
                if quitting:
                    running = False
        elif choice == "design":
            if design_loop(screen, assets, design) == "quit":
                running = False
        elif choice == "options":
            if options_loop(screen, font, title_font, config, design) == "quit":
                running = False
        else:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
