"""Menus: main menu, character select, options.

Human-only screens - the RL environment never touches this module. The
options menu edits a GameConfig instance in place (attribute names match
game/config.py), so tweaks here flow straight into the engine.
"""

import pygame
from .design import THEMES, draw_menu

MENU_FPS = 30


def draw_centered_text(screen, font, text, y, color):
    surface = font.render(text, True, color)
    rect = surface.get_rect(center=(screen.get_width() // 2, y))
    screen.blit(surface, rect)


def _start_background(assets, screen):
    background = assets.image("start_screen")
    if background is None:
        return None
    return pygame.transform.scale(
        background, (screen.get_width(), screen.get_height()))


def menu_loop(screen, font, title_font, assets, design="original"):
    options = ["Start Game", "Designs", "Options", "Quit"]
    selected = 0
    clock = pygame.time.Clock()
    background = _start_background(assets, screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_ESCAPE:
                    return "quit"
                elif event.key == pygame.K_RETURN:
                    if options[selected] == "Start Game":
                        return "start"
                    if options[selected] == "Designs":
                        return "design"
                    if options[selected] == "Options":
                        return "options"
                    return "quit"

        if design != 'original':
            draw_menu(screen, assets, 'CAT DISASTER', options, selected, design)
        else:
            if background is not None:
                screen.blit(background, (0, 0))
            else:
                screen.fill((0, 0, 0))
            draw_centered_text(screen, title_font, "Morty & Rick: Cat Disaster", 120, (255, 255, 255))
            for index, label in enumerate(options):
                color = (255, 255, 0) if index == selected else (255, 255, 255)
                draw_centered_text(screen, font, label, 220 + index * 40, color)
            draw_centered_text(screen, font, "Use arrows or WASD, Enter to select", 420, (180, 180, 180))
        pygame.display.flip()
        clock.tick(MENU_FPS)


def character_select_loop(screen, font, title_font, assets, design="original"):
    options = ["Morty", "Rick"]
    selected = 0
    clock = pygame.time.Clock()
    background = _start_background(assets, screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    return options[selected].lower()
                elif event.key == pygame.K_ESCAPE:
                    return None

        if design != 'original':
            draw_menu(screen, assets, 'CHOOSE YOUR HERO', options, selected, design)
            for index, name in enumerate(options):
                sprite = assets.image('dog_' + name.lower())
                if sprite is not None:
                    screen.blit(pygame.transform.smoothscale(sprite, (40, 38)),
                                (screen.get_width() // 2 + 140, 172 + index * 46))
        else:
            if background is not None:
                screen.blit(background, (0, 0))
            else:
                screen.fill((0, 0, 0))
            draw_centered_text(screen, title_font, "Choose Your Character", 120, (255, 255, 255))
            for index, label in enumerate(options):
                color = (255, 255, 0) if index == selected else (255, 255, 255)
                y = 220 + index * 70
                draw_centered_text(screen, font, label, y, color)
                sprite = assets.image(f"dog_{label.lower()}")
                if sprite is not None:
                    rect = sprite.get_rect(center=(screen.get_width() // 2 - 120, y))
                    screen.blit(sprite, rect)
            draw_centered_text(screen, font, "Enter to start, Esc to go back", 420, (180, 180, 180))
        pygame.display.flip()
        clock.tick(MENU_FPS)


def format_setting_value(value):
    if isinstance(value, bool):
        return "On" if value else "Off"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


# (label, GameConfig attribute, step, min, max) - None attr = Back
OPTION_ROWS = [
    ("Cat spawn interval (frames)", "cat_spawn_interval", 10, 10, 400),
    ("Cats before boss", "cats_before_boss", 1, 1, 200),
    ("Dog speed", "dog_speed", 1, 1, 20),
    ("Initial cat speed", "cat_speed", 0.5, 0.5, 10),
    ("Max cat speed", "max_cat_speed", 0.5, 1, 20),
    ("Boss speed", "boss_speed", 0.5, 1, 20),
    ("Boss health", "boss_health", 1, 1, 100),
    ("Bark speed", "bark_speed", 1, 5, 100),
    ("Bark cooldown (frames)", "bark_cooldown_frames", 1, 5, 60),
    ("Speed-up interval (frames)", "speed_increase_frames", 50, 100, 3000),
    ("Spawn bias toward dog", "spawn_target_bias", 0.05, 0.0, 1.0),
    ("Barks visible", "barks_visible", 1, 0, 1),
    ("Auntie Larissa intro", "intro_enabled", 1, 0, 1),
    ("Back", None, 0, 0, 0),
]


def options_loop(screen, font, title_font, config, design="original"):
    selected = 0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(OPTION_ROWS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(OPTION_ROWS)
                elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    label, attr, step, min_value, max_value = OPTION_ROWS[selected]
                    if attr is not None:
                        current = getattr(config, attr)
                        if isinstance(current, bool):
                            setattr(config, attr, not current)
                        else:
                            delta = step if event.key in (pygame.K_RIGHT, pygame.K_d) else -step
                            value = clamp(current + delta, min_value, max_value)
                            setattr(config, attr, type(current)(value))
                            # keep the speed pair consistent
                            if attr == "cat_speed" and config.cat_speed > config.max_cat_speed:
                                config.max_cat_speed = config.cat_speed
                            if attr == "max_cat_speed" and config.max_cat_speed < config.cat_speed:
                                config.cat_speed = config.max_cat_speed
                elif event.key == pygame.K_RETURN:
                    if OPTION_ROWS[selected][1] is None:
                        return "back"
                elif event.key == pygame.K_ESCAPE:
                    return "back"

        screen.fill(THEMES[design].bg)
        draw_centered_text(screen, title_font, "Options", 50, THEMES[design].ink)
        start_y = 90
        for index, (label, attr, _, _, _) in enumerate(OPTION_ROWS):
            color = (255, 255, 0) if index == selected else (255, 255, 255)
            if attr is None:
                draw_centered_text(screen, font, label, start_y + index * 24, color)
            else:
                value = format_setting_value(getattr(config, attr))
                draw_centered_text(screen, font, f"{label}: {value}", start_y + index * 24, color)
        draw_centered_text(screen, font, "Left/Right to adjust, Enter/Esc to go back", 450, (180, 180, 180))
        pygame.display.flip()
        clock.tick(MENU_FPS)
