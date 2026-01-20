import pygame
import math
import random
import time
import json
import os
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

def main():
    pygame.init()
    pygame.mixer.init()
    SCREEN_WIDTH = 640
    SCREEN_HEIGHT = 480

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Morty & Rick: Cat Disaster')

    background_image = pygame.image.load('visuals/Background_v2_640x480.png')
    font = pygame.font.Font(None, 24)
    game_over_font = pygame.font.Font(None, 48)

    CAT_SPAWN_INTERVAL = 100
    CAT_TIMER = 20
    CATS_BEFORE_BOSS = 40
    DOG_SPEED = 7
    GLOBAL_CAT_SPEED = 2  # Initial speed for all cats
    MAX_CAT_SPEED = 7.5
    BOSS_CAT_SPEED = 5
    BOSS_CAT_HEALTH = 20
    BARK_SPEED = 45

    dog = Dog(320, 400, DOG_SPEED, (255, 0, 0), BARK_SPEED)
    cats = []
    FOOD_LEVELS_BEFORE_DOG = 4
    FOOD_X_OFFSET = -20
    food = Food(200 + FOOD_X_OFFSET, dog.y - (FOOD_LEVELS_BEFORE_DOG * Cat.VERTICAL_MOVE))
    SPEED_INCREASE_INTERVAL = 10000  # in milliseconds

    clock = pygame.time.Clock()
    last_speed_increase_time = pygame.time.get_ticks()
    start_sound = pygame.mixer.Sound('sounds/smw_power-up_appears.wav')
    start_sound.play()
    highscore = load_highscore(HIGHSCORE_PATH)
    game_over = False
    game_over_start = None

    RUNNING = True
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

        # Check if boss is destroyed or all cats are gone
        if dog.destroyed_boss:
            print("Dog Wins")
            if dog.cats_destroyed > highscore:
                highscore = dog.cats_destroyed
                save_highscore(HIGHSCORE_PATH, highscore)
            RUNNING = False


        if not game_over:
            for cat in cats:
                cat.descend(GLOBAL_CAT_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT)


        if not game_over:
            if dog.cats_destroyed == CATS_BEFORE_BOSS and not boss_exists(cats):
                # Spawn the boss cat
                boss = BossCat(10, 140, (200, 100, 50), BOSS_CAT_SPEED, BOSS_CAT_HEALTH)
                cats.append(boss)

        if not game_over:
            if CAT_TIMER <= 0 and not boss_exists(cats):
                cats.append(Cat(int(random.uniform(40, SCREEN_WIDTH - 20)), 40, (0, 0, 255), GLOBAL_CAT_SPEED))
                CAT_TIMER = CAT_SPAWN_INTERVAL + np.random.normal(0, 60)
            else:
                CAT_TIMER -= 1
        
        # Check if enlarged cat touches the dog
        if not game_over:
            for cat in cats:
                cat.check_food(food)  # Check interaction with food
                if DogCollision.collides(cat, dog):
                    print('Dog Dies')
                    game_over = True
                    game_over_start = current_time
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
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(game_over_text, text_rect)

    
        pygame.display.flip()
        clock.tick(50)

    pygame.quit()

if __name__ == "__main__":
    main()
