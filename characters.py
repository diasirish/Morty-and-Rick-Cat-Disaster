import pygame
import math


class Character:
    def __init__(self, x, y, speed, color):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = color
        self.width = 40
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
        self.bark_sound = pygame.mixer.Sound('sounds/woof_morty_1.wav')
        self.bark_sound.play()

    def move(self):
        # Update all projectiles to move upward
        self.projectiles = [(px, py - self.speed) for px, py in self.projectiles]

    def draw(self, screen):
        if self.active:
            for px, py in self.projectiles:
                pygame.draw.circle(screen, (255, 255, 0), (px, py), 5)


class Food:
    def __init__(self, x, y, image_path=None, sound_path=None, scale=1.0):
        self.image = None
        self.sound = None
        if image_path:
            try:
                self.image = pygame.image.load(image_path)
            except pygame.error:
                self.image = None
        if self.image:
            if scale != 1.0:
                new_width = max(1, int(self.image.get_width() * scale))
                new_height = max(1, int(self.image.get_height() * scale))
                self.image = pygame.transform.scale(self.image, (new_width, new_height))
            self.width = self.image.get_width()
            self.height = self.image.get_height()
        else:
            self.width = 20
            self.height = 20
        self.x = x
        self.y = y
        if sound_path:
            self.sound = pygame.mixer.Sound(sound_path)

    def play_sound(self):
        if self.sound:
            self.sound.play()

    def draw(self, screen):
        if self.image:
            screen.blit(self.image, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (100, 255, 100), (self.x, self.y, self.width, self.height))


class Dog(Character):
    def __init__(self, x, y, speed, color, bark_speed):
        super().__init__(x, y, speed, color)
        self.barks = []
        self.bark_speed = bark_speed
        self.bark_cooldown = 350  # Cooldown in milliseconds (1.5 seconds)
        self.last_bark_time = pygame.time.get_ticks() - self.bark_cooldown  # Initialize to allow immediate bark
        self.cats_destroyed = 0
        self.image = pygame.image.load('visuals/Morty_64x60.png')
        self.destroyed_boss = False
        self.position = 'right'

    def draw_img(self, screen):
        if self.position == 'left':
            flipped_image = pygame.transform.flip(self.image, True, False)
            screen.blit(flipped_image, (self.x, self.y))
        else:
            screen.blit(self.image, (self.x, self.y))

    def bark(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_bark_time > self.bark_cooldown:
            self.barks.append(Bark(self.x + 20, self.y + 10, self.bark_speed))
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
    VERTICAL_MOVE = 50
    ENLARGE_SCALE = 1.5

    def __init__(self, x, y, color, speed):
        super().__init__(x, y, speed, color)
        self.active = True
        self.direction = 'left'
        self.vertical_move = Cat.VERTICAL_MOVE
        self.enlarged = False
        self.image = pygame.image.load('visuals/Cat_ex1_64x57_right.png')
        self.health = 1

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

    def draw(self, screen):
        if self.direction == 'left':
            flipped_image = pygame.transform.flip(self.image, True, False)
            screen.blit(flipped_image, (self.x, self.y))
        else:
            screen.blit(self.image, (self.x, self.y))

    def hit_by_bark(self):
        self.health -= 1
        if self.health <= 0:
            self.active = False

    def check_food(self, food):
        if not self.enlarged and self.x < food.x + food.width and self.x + self.width > food.x and self.y < food.y + food.height and self.y + self.height > food.y:
            self.enlarged = True
            food.play_sound()
            old_image_height = self.image.get_height()
            self.width = int(self.width * Cat.ENLARGE_SCALE)
            self.height = int(self.height * Cat.ENLARGE_SCALE)
            print('Collision Detected')
            new_image_width = int(self.image.get_width() * Cat.ENLARGE_SCALE)
            new_image_height = int(self.image.get_height() * Cat.ENLARGE_SCALE)
            self.image = pygame.transform.scale(self.image, (new_image_width, new_image_height))
            self.y -= (new_image_height - old_image_height)
            self.health = 9


class BossCat(Cat):
    def __init__(self, x, y, color, speed, health):
        super().__init__(x, y, color, speed)
        self.health = health
        self.width = 60
        self.height = 60

    def hit_by_bark(self):
        self.health -= 1
        if self.health <= 0:
            self.active = False
