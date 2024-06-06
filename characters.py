import pygame

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
        self.x = x
        self.y = y
        self.speed = speed  # This will now represent the vertical speed
        self.active = True

    def move(self):
        self.y -= self.speed  # Move the bark upwards

    def draw(self, screen):
        if self.active:
            pygame.draw.circle(screen, (255, 255, 0), (self.x, self.y), 5)  # Draw the bark as a small circle


class Dog(Character):
    def __init__(self, x, y, speed, color):
        super().__init__(x, y, speed, color)
        self.barks = []

    def bark(self):
        self.barks.append(Bark(self.x + 20, self.y + 10, 10))  # Barks move right from the dog's position

    def update_barks(self, screen_width):
        for bark in self.barks:
            bark.move()
            if bark.x > screen_width:  # Remove bark if it goes off screen
                bark.active = False
        self.barks = [bark for bark in self.barks if bark.active]

    def draw(self, screen):
        super().draw(screen)
        for bark in self.barks:
            bark.draw(screen)


class Cat(Character):
    def __init__(self, x, y, speed, color):
        super().__init__(x, y, speed, color)
        self.active = True
        self.direction = 'left'  # Start moving left initially
        self.vertical_move = 80  # Pixels to move down after reaching the screen edge

    def descend(self, screen_width, screen_height):
        if not self.active:
            return  # Skip processing if the cat is not active

        # Check the current direction and move accordingly
        if self.direction == 'left':
            if self.x - self.speed > 10:  # Move left
                self.move(-1, 0)
            else:  # Change direction to 'right' after hitting the left border
                self.move(0, self.vertical_move)
                self.direction = 'right'
        elif self.direction == 'right':
            if self.x + self.speed < screen_width - 10 - self.width:  # Move right
                self.move(1, 0)
            else:  # Change direction to 'left' after hitting the right border
                self.move(0, self.vertical_move)
                self.direction = 'left'

    def draw(self, screen):
        if self.active:
            super().draw(screen)