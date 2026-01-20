import pygame
import math
import random
import time
import json
import os
import sys
import numpy as np
from events import check_collisions, boss_exists, DogCollision
from characters import Dog, Cat, Food, BossCat

HIGHSCORE_PATH = "highscore.json"
GAME_OVER_DELAY_MS = 7000

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

def draw_centered_text(screen, font, text, y, color):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(screen.get_width() // 2, y))
    screen.blit(text_surface, text_rect)

def menu_loop(screen, font, title_font):
    options = ["Start Game", "Options", "Quit"]
    selected = 0
    clock = pygame.time.Clock()
    background = pygame.image.load("visuals/Start_Screen.jpg")
    background = pygame.transform.scale(background, (screen.get_width(), screen.get_height()))

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
                    if options[selected] == "Start Game":
                        return "start"
                    if options[selected] == "Options":
                        return "options"
                    return "quit"

        screen.blit(background, (0, 0))
        draw_centered_text(screen, title_font, "Morty & Rick: Cat Disaster", 120, (255, 255, 255))
        for index, label in enumerate(options):
            color = (255, 255, 0) if index == selected else (255, 255, 255)
            draw_centered_text(screen, font, label, 220 + index * 40, color)
        draw_centered_text(screen, font, "Use arrows or WASD, Enter to select", 420, (180, 180, 180))
        pygame.display.flip()
        clock.tick(30)

def character_select_loop(screen, font, title_font):
    options = ["Morty"]
    selected = 0
    clock = pygame.time.Clock()
    background = pygame.image.load("visuals/Start_Screen.jpg")
    background = pygame.transform.scale(background, (screen.get_width(), screen.get_height()))

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
                    return options[selected]
                elif event.key == pygame.K_ESCAPE:
                    return None

        screen.blit(background, (0, 0))
        draw_centered_text(screen, title_font, "Choose Your Character", 120, (255, 255, 255))
        for index, label in enumerate(options):
            color = (255, 255, 0) if index == selected else (255, 255, 255)
            draw_centered_text(screen, font, label, 220 + index * 40, color)
        draw_centered_text(screen, font, "Enter to start, Esc to go back", 420, (180, 180, 180))
        pygame.display.flip()
        clock.tick(30)

def format_setting_value(value):
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.1f}"
    return str(value)

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def options_loop(screen, font, title_font, settings):
    options = [
        ("Cat spawn interval", "CAT_SPAWN_INTERVAL", 10, 10, 400),
        ("Cats before boss", "CATS_BEFORE_BOSS", 1, 1, 200),
        ("Dog speed", "DOG_SPEED", 1, 1, 20),
        ("Initial cat speed", "GLOBAL_CAT_SPEED", 0.5, 0.5, 10),
        ("Max cat speed", "MAX_CAT_SPEED", 0.5, 1, 20),
        ("Boss cat speed", "BOSS_CAT_SPEED", 0.5, 1, 20),
        ("Boss cat health", "BOSS_CAT_HEALTH", 1, 1, 100),
        ("Bark speed", "BARK_SPEED", 1, 5, 100),
        ("Food levels before dog", "FOOD_LEVELS_BEFORE_DOG", 1, 1, 10),
        ("Food X offset", "FOOD_X_OFFSET", 10, -200, 200),
        ("Food X base", "FOOD_X_BASE", 10, 0, 640),
        ("Speed increase interval", "SPEED_INCREASE_INTERVAL", 500, 1000, 60000),
        ("Back", None, 0, 0, 0),
    ]
    selected = 0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    label, key, step, min_value, max_value = options[selected]
                    if key is not None:
                        delta = step if event.key in (pygame.K_RIGHT, pygame.K_d) else -step
                        new_value = settings[key] + delta
                        settings[key] = clamp(new_value, min_value, max_value)
                        if key == "GLOBAL_CAT_SPEED" and settings[key] > settings["MAX_CAT_SPEED"]:
                            settings["MAX_CAT_SPEED"] = settings[key]
                        if key == "MAX_CAT_SPEED" and settings[key] < settings["GLOBAL_CAT_SPEED"]:
                            settings["GLOBAL_CAT_SPEED"] = settings[key]
                elif event.key == pygame.K_RETURN:
                    if options[selected][1] is None:
                        return "back"
                elif event.key == pygame.K_ESCAPE:
                    return "back"

        screen.fill((0, 0, 0))
        draw_centered_text(screen, title_font, "Options", 80, (255, 255, 255))
        start_y = 140
        for index, (label, key, _, _, _) in enumerate(options):
            color = (255, 255, 0) if index == selected else (255, 255, 255)
            if key is None:
                draw_centered_text(screen, font, label, start_y + index * 28, color)
            else:
                value = format_setting_value(settings[key])
                draw_centered_text(screen, font, f"{label}: {value}", start_y + index * 28, color)
        draw_centered_text(screen, font, "Left/Right to adjust, Enter/Esc to go back", 440, (180, 180, 180))
        pygame.display.flip()
        clock.tick(30)

def run_game(screen, settings, highscore, character):
    screen_width = screen.get_width()
    screen_height = screen.get_height()
    background_image = pygame.image.load('visuals/Background_v2_640x480.png')
    font = pygame.font.Font(None, 24)
    game_over_font = pygame.font.Font(None, 48)
    game_over_sound = pygame.mixer.Sound('sounds/puppy_crying.mp3')

    CAT_SPAWN_INTERVAL = int(settings["CAT_SPAWN_INTERVAL"])
    CAT_TIMER = 20
    CATS_BEFORE_BOSS = int(settings["CATS_BEFORE_BOSS"])
    DOG_SPEED = settings["DOG_SPEED"]
    GLOBAL_CAT_SPEED = settings["GLOBAL_CAT_SPEED"]
    MAX_CAT_SPEED = settings["MAX_CAT_SPEED"]
    BOSS_CAT_SPEED = settings["BOSS_CAT_SPEED"]
    BOSS_CAT_HEALTH = int(settings["BOSS_CAT_HEALTH"])
    BARK_SPEED = settings["BARK_SPEED"]
    FOOD_LEVELS_BEFORE_DOG = int(settings["FOOD_LEVELS_BEFORE_DOG"])
    FOOD_X_OFFSET = int(settings["FOOD_X_OFFSET"])
    FOOD_X_BASE = int(settings["FOOD_X_BASE"])
    SPEED_INCREASE_INTERVAL = int(settings["SPEED_INCREASE_INTERVAL"])

    dog = Dog(screen_width // 2, 400, DOG_SPEED, (255, 0, 0), BARK_SPEED)
    cats = []
    food = Food(
        FOOD_X_BASE + FOOD_X_OFFSET,
        dog.y - (FOOD_LEVELS_BEFORE_DOG * Cat.VERTICAL_MOVE),
        image_path="visuals/8853301006071_compressed copy.jpg",
        sound_path="sounds/smw_power-up_appears.wav",
        scale=0.1,
    )
    food.x -= food.width // 2
    start_sound = pygame.mixer.Sound('sounds/dog-howl-352680.mp3')

    clock = pygame.time.Clock()
    last_speed_increase_time = pygame.time.get_ticks()
    start_sound.play()
    game_over = False
    game_over_start = None
    game_over_sound_played = False

    RUNNING = True
    quitting = False
    while RUNNING:
        current_time = pygame.time.get_ticks()
        if not game_over:
            if current_time - last_speed_increase_time > SPEED_INCREASE_INTERVAL:
                if GLOBAL_CAT_SPEED < MAX_CAT_SPEED:
                    GLOBAL_CAT_SPEED += math.log(GLOBAL_CAT_SPEED + 1)
                last_speed_increase_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                RUNNING = False
                quitting = True

        if not game_over:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                dog.move(-1, 0)
                dog.position = 'left'
            if keys[pygame.K_RIGHT]:
                dog.move(1, 0)
                dog.position = 'right'
            if keys[pygame.K_SPACE]:
                dog.bark()

        if not game_over:
            dog.update_barks()
            cats = check_collisions(dog, cats)

        if dog.destroyed_boss:
            print("Dog Wins")
            if dog.cats_destroyed > highscore:
                highscore = dog.cats_destroyed
                save_highscore(HIGHSCORE_PATH, highscore)
            RUNNING = False

        if not game_over:
            for cat in cats:
                cat.descend(GLOBAL_CAT_SPEED, screen_width, screen_height)

        if not game_over:
            if dog.cats_destroyed == CATS_BEFORE_BOSS and not boss_exists(cats):
                boss = BossCat(10, 140, (200, 100, 50), BOSS_CAT_SPEED, BOSS_CAT_HEALTH)
                cats.append(boss)

        if not game_over:
            if CAT_TIMER <= 0 and not boss_exists(cats):
                cats.append(Cat(int(random.uniform(40, screen_width - 20)), 40, (0, 0, 255), GLOBAL_CAT_SPEED))
                CAT_TIMER = CAT_SPAWN_INTERVAL + np.random.normal(0, 60)
            else:
                CAT_TIMER -= 1

        if not game_over:
            for cat in cats:
                cat.check_food(food)
                if DogCollision.collides(cat, dog):
                    print('Dog Dies')
                    game_over = True
                    game_over_start = current_time
                    if not game_over_sound_played:
                        game_over_sound.play()
                        game_over_sound_played = True
                    if dog.cats_destroyed > highscore:
                        highscore = dog.cats_destroyed
                        save_highscore(HIGHSCORE_PATH, highscore)
                    break

        if game_over and game_over_start is not None:
            if current_time - game_over_start >= GAME_OVER_DELAY_MS:
                RUNNING = False

        screen.fill((0, 0, 0))
        screen.blit(background_image, (0, 0))
        food.draw(screen)
        for cat in cats:
            cat.draw(screen)
        dog.draw_img(screen)
        score_text = font.render(f"Cats Destroyed: {dog.cats_destroyed}", True, (255, 255, 255))
        highscore_text = font.render(f"Highscore: {highscore}", True, (255, 255, 255))
        screen.blit(score_text, (10, 10))
        screen.blit(highscore_text, (10, 30))
        if game_over:
            game_over_text = game_over_font.render("Game Over", True, (255, 0, 0))
            text_rect = game_over_text.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(game_over_text, text_rect)

        pygame.display.flip()
        clock.tick(50)

    return highscore, quitting

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    game_only = "--game_only" in args

    pygame.init()
    pygame.mixer.init()
    SCREEN_WIDTH = 640
    SCREEN_HEIGHT = 480

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Morty & Rick: Cat Disaster')

    font = pygame.font.Font(None, 24)
    title_font = pygame.font.Font(None, 48)

    settings = {
        "CAT_SPAWN_INTERVAL": 100,
        "CATS_BEFORE_BOSS": 40,
        "DOG_SPEED": 7,
        "GLOBAL_CAT_SPEED": 2.0,
        "MAX_CAT_SPEED": 7.5,
        "BOSS_CAT_SPEED": 5.0,
        "BOSS_CAT_HEALTH": 20,
        "BARK_SPEED": 45,
        "FOOD_LEVELS_BEFORE_DOG": 4,
        "FOOD_X_OFFSET": -20,
        "FOOD_X_BASE": 200,
        "SPEED_INCREASE_INTERVAL": 10000,
    }
    highscore = load_highscore(HIGHSCORE_PATH)

    RUNNING = True
    if game_only:
        _, quitting = run_game(screen, settings, highscore, "Morty")
        if quitting:
            RUNNING = False
    while RUNNING and not game_only:
        choice = menu_loop(screen, font, title_font)
        if choice == "start":
            character = character_select_loop(screen, font, title_font)
            if character == "quit":
                RUNNING = False
                continue
            if character is None:
                continue
            highscore, quitting = run_game(screen, settings, highscore, character)
            if quitting:
                RUNNING = False
        elif choice == "options":
            if options_loop(screen, font, title_font, settings) == "quit":
                RUNNING = False
        else:
            RUNNING = False

    pygame.quit()

if __name__ == "__main__":
    main()
