import pygame
import math


class Character:
    def __init__(self, x, y, speed, color):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = color
        self.width = 20
        self.height = 20

    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))


class Bark:
    def __init__(self, x, y, speed):
        # Initial positions of projectiles are spaced vertically
        self.projectiles = [(x, y - i * 10) for i in range(8)]
        self.speed = speed
        self.active = True

    def move(self):
        # Update all projectiles to move upward
        self.projectiles = [(px, py - self.speed) for px, py in self.projectiles]

    def draw(self, screen):
        if self.active:
            for px, py in self.projectiles:
                pygame.draw.circle(screen, (255, 255, 0), (px, py), 5)

class Food:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 20
        self.height = 20

    def draw(self, screen):
        pygame.draw.rect(screen, (100, 255, 100), (self.x, self.y, self.width, self.height))


class Dog(Character):
    def __init__(self, x, y, speed, color):
        super().__init__(x, y, speed, color)
        self.barks = []
        self.bark_cooldown = 350  # Cooldown in milliseconds (1.5 seconds)
        self.last_bark_time = pygame.time.get_ticks() - self.bark_cooldown  # Initialize to allow immediate bark
        self.cats_destroyed = 0
        self.destroyed_boss = False

    def bark(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_bark_time > self.bark_cooldown:
            self.barks.append(Bark(self.x + 20, self.y + 10, 15))
            self.last_bark_time = current_time

    def update_barks(self):
        for bark in self.barks:
            bark.move()
            # Deactivate bark if all projectiles are off screen
            if not any(py > 0 for _, py in bark.projectiles):
                bark.active = False
        # Filter out inactive barks
        self.barks = [bark for bark in self.barks if bark.active]

    def draw(self, screen):
        super().draw(screen)
        for bark in self.barks:
            bark.draw(screen)

class Cat(Character):
    def __init__(self, x, y, color, speed):
        super().__init__(x, y, speed, color)
        self.active = True
        self.direction = 'left'
        self.vertical_move = 50
        self.enlarged = False


    def descend(self, global_speed, screen_width, screen_height):
        if not self.active:
            return

        if self.direction == 'left':
            if self.x - global_speed > 10:
                self.x -= global_speed
            else:
                self.y += self.vertical_move
                self.direction = 'right'
        elif self.direction == 'right':
            if self.x + global_speed < screen_width - self.width - 10:
                self.x += global_speed
            else:
                self.y += self.vertical_move
                self.direction = 'left'

        if self.enlarged and self.y > screen_height * 3 / 4:
            self.active = True  # Allows enlarged cats to go lower
                    
        if self.y > screen_height * 3 / 4:
            if self.enlarged:
                self.active = True
            else:
                self.active = False

    def draw(self, screen):
        if self.active:
            super().draw(screen)

    def check_food(self, food):
        if not self.enlarged and self.x < food.x + food.width and self.x + self.width > food.x and self.y < food.y + food.height and self.y + self.height > food.y:
            self.enlarged = True
            self.width *= 2
            self.height *= 2


class BossCat(Cat):
    def __init__(self, x, y, color, speed, health):
        super().__init__(x, y, color, speed)
        self.health = health
        # self.width = x*2
        # self.height = y*2

    def hit_by_bark(self):
        self.health -= 1
        if self.health <= 0:
            self.active = False