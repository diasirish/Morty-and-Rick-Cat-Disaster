def check_collisions(dog, cats):
    for bark in dog.barks:
        if bark.active:
            for px, py in bark.projectiles:
                for cat in cats:
                    if cat.active and cat.x < px < cat.x + cat.width and cat.y < py < cat.y + cat.height:
                        cat.active = False
                        bark.active = False
                        break  # Stop checking if bark has already hit a cat
    return [cat for cat in cats if cat.active]
