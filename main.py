import pygame
import math
import random
import time
import numpy as np
from events import check_collisions, boss_exists
from characters import Dog, Cat, Food, BossCat

def main():
    pygame.init()
    SCREEN_WIDTH = 640
    SCREEN_HEIGHT = 480

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Morty & Rick: Cat Disaster')

    CAT_SPAWN_INTERVAL = 150
    CAT_TIMER = 20
    CATS_BEFORE_BOSS = 1
    DOG_SPEED = 7
    GLOBAL_CAT_SPEED = 1  # Initial speed for all cats
    MAX_CAT_SPEED = 7.5
    BOSS_CAT_SPEED = 5
    BOSS_CAT_HEALTH = 8
    BARK_SPEED = 45

    dog = Dog(320, 400, DOG_SPEED, (255, 0, 0), BARK_SPEED)
    cats = []
    food = Food(580, 350)
    SPEED_INCREASE_INTERVAL = 10000  # in milliseconds

    clock = pygame.time.Clock()
    last_speed_increase_time = pygame.time.get_ticks()
    
    RUNNING = True
    while RUNNING:
        current_time = pygame.time.get_ticks()
        if current_time - last_speed_increase_time > SPEED_INCREASE_INTERVAL:
            if GLOBAL_CAT_SPEED < MAX_CAT_SPEED:
                GLOBAL_CAT_SPEED += math.log(GLOBAL_CAT_SPEED + 1)
            last_speed_increase_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                RUNNING = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            dog.move(-1, 0)
        if keys[pygame.K_RIGHT]:
            dog.move(1, 0)
        if keys[pygame.K_SPACE]:
            dog.bark()

        dog.update_barks()
        cats = check_collisions(dog, cats)

        # Check if boss is destroyed or all cats are gone
        if dog.destroyed_boss:
            print("Dog Wins")
            RUNNING = False


        for cat in cats:
            cat.descend(GLOBAL_CAT_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT)


        if dog.cats_destroyed == CATS_BEFORE_BOSS and not boss_exists(cats):
            # Spawn the boss cat
            boss = BossCat(10, 140, (200, 100, 50), BOSS_CAT_SPEED, BOSS_CAT_HEALTH)
            cats.append(boss)

        if CAT_TIMER <= 0 and not boss_exists(cats):
            cats.append(Cat(int(random.uniform(40, SCREEN_WIDTH - 20)), 40, (0, 0, 255), GLOBAL_CAT_SPEED))
            CAT_TIMER = CAT_SPAWN_INTERVAL + np.random.normal(0, 60)
        else:
            CAT_TIMER -= 1
        
        # Check if enlarged cat touches the dog
        for cat in cats:
            cat.check_food(food)  # Check interaction with food
            if cat.enlarged and pygame.Rect(cat.x, cat.y, cat.width, cat.height).colliderect(pygame.Rect(dog.x, dog.y, dog.width, dog.height)):
                print('Dog Dies')
                RUNNING = False     # Implement end_game function to handle game over


        screen.fill((0, 0, 0))
        dog.draw(screen)
        food.draw(screen)
        for cat in cats:
            cat.draw(screen)
        
    
        pygame.display.flip()
        clock.tick(50)

    pygame.quit()

if __name__ == "__main__":
    main()