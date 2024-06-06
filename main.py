import pygame
from characters import Cat, Dog

def check_collisions(dog, cats):
    for bark in dog.barks:
        if bark.active:
            for cat in cats:
                # Simple collision detection: Check if bark and cat overlap
                if (cat.x < bark.x < cat.x + cat.width) and (cat.y < bark.y < cat.y + cat.height):
                    cat.active = False  # Mark the cat as inactive
                    bark.active = False  # Deactivate bark after hitting a cat

    # Filter out inactive cats
    return [cat for cat in cats if cat.active]

def main():
    pygame.init()
    screen_width = 640
    screen_height = 480
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption('Morty & Rick: Cat Disaster')

    dog = Dog(320, 440, 4, (255, 0, 0))
    cats = []  # Start with no cats on the screen
    cat_spawn_interval = 200  # Number of frames between each new cat spawn
    cat_timer = cat_spawn_interval  # Initialize timer to spawn the first cat immediately

    clock = pygame.time.Clock()
    running = True
    while running:
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

        dog.update_barks(screen_height)  # Update to handle barks moving up
        cats = check_collisions(dog, cats)

        # Cat spawning logic
        if cat_timer <= 0:
            cats.append(Cat(screen_width - 20, 0, 1, (0, 0, 255)))  # Spawn new cat at the right upper corner
            cat_timer = cat_spawn_interval  # Reset timer
        else:
            cat_timer -= 1  # Decrement timer each frame

        for cat in cats:
            cat.descend(screen_width, screen_height)

        screen.fill((0, 0, 0))
        dog.draw(screen)
        for cat in cats:
            cat.draw(screen)

        pygame.display.flip()
        clock.tick(50)

    pygame.quit()

if __name__ == "__main__":
    main()