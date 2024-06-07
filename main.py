import pygame
import math
import time
import numpy as np
from events import check_collisions
from characters import Dog, Cat

def main():
    pygame.init()
    screen_width = 640
    screen_height = 480
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('Morty & Rick: Cat Disaster')

    dog = Dog(320, 440, 4, (255, 0, 0))
    cats = []
    cat_spawn_interval = 200
    cat_timer = 20

    global_cat_speed = 1  # Initial speed for all cats
    max_cat_speed = 7.5
    last_speed_increase_time = pygame.time.get_ticks()
    speed_increase_interval = 10000  # in milliseconds

    clock = pygame.time.Clock()
    running = True
    while running:
        current_time = pygame.time.get_ticks()
        if current_time - last_speed_increase_time > speed_increase_interval:
            if global_cat_speed < max_cat_speed:
                global_cat_speed += math.log(global_cat_speed + 1)
            last_speed_increase_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            dog.move(-1, 0)
        if keys[pygame.K_RIGHT]:
            dog.move(1, 0)
        if keys[pygame.K_SPACE]:
            dog.bark()

        dog.update_barks()
        cats = check_collisions(dog, cats)

        for cat in cats:
            cat.descend(global_cat_speed, screen_width, screen_height)

        if cat_timer <= 0:
            cats.append(Cat(screen_width - 20, 0, (0, 0, 255), global_cat_speed))
            cat_timer = cat_spawn_interval + np.random.normal(0, 60)
        else:
            cat_timer -= 1

        screen.fill((0, 0, 0))
        dog.draw(screen)
        for cat in cats:
            cat.draw(screen)
        pygame.display.flip()
        clock.tick(50)

    pygame.quit()

if __name__ == "__main__":
    main()