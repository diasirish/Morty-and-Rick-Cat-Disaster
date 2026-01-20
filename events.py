from characters import BossCat, Cat

class DogCollision:
    @staticmethod
    def overlaps_x(cat, dog):
        return cat.x < dog.x + dog.width and cat.x + cat.width > dog.x

    @staticmethod
    def same_level(cat, dog):
        return cat.y >= dog.y - Cat.VERTICAL_MOVE

    @classmethod
    def collides(cls, cat, dog):
        return cls.same_level(cat, dog) and cls.overlaps_x(cat, dog)

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
                            cat.hit_by_bark()
                            if not cat.active:
                                dog.cats_destroyed += 1
                        break  # Stop checking if bark has already hit a cat
    return [cat for cat in cats if cat.active]

def boss_exists(cats):
    for cat in cats:
        if isinstance(cat, BossCat) and cat.active:
            return True
    return False
