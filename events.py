from characters import BossCat

def check_collisions(dog, cats):
    for bark in dog.barks:
        if bark.active:
            for px, py in bark.projectiles:
                for cat in cats:
                    if cat.active and cat.x < px < cat.x + cat.width and cat.y < py < cat.y + cat.height:
                        bark.active = False
                        if isinstance(cat, BossCat):
                            cat.hit_by_bark()
                            if cat.health <= 0:
                                dog.destroyed_boss = True
                        else:
                            cat.active = False                        
                            dog.cats_destroyed += 1
                        break  # Stop checking if bark has already hit a cat
    return [cat for cat in cats if cat.active]

def boss_exists(cats):
    for cat in cats:
        if isinstance(cat, BossCat) and cat.active:
            return True
    return False

def boss_is_dead(cats):
    for cat in cats:
        if isinstance(cat, BossCat):
            boss_is_dead = not cat.active
            return boss_is_dead
