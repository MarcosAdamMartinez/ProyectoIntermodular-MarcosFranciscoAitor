import pygame
import random
from src.utils.settings import load_sprite

# Sprites y colores de fallback por mundo (3 variantes cada uno)
ROCK_SPRITES = {
    1: {
        1: ("assets/sprites/objects/rock1.png",       (120, 110, 100)),
        2: ("assets/sprites/objects/rock2.png",       (90,  90,  95)),
        3: ("assets/sprites/objects/rock3.png",       (100, 85,  75)),
    },
    2: {
        1: ("assets/sprites/objects/rock_w2_1.png",   (60,  80, 130)),
        2: ("assets/sprites/objects/rock_w2_2.png",   (80, 100, 150)),
        3: ("assets/sprites/objects/rock_w2_3.png",   (50,  60, 110)),
    },
    3: {
        1: ("assets/sprites/objects/rock_w3_1.png",   (140,  30,  10)),
        2: ("assets/sprites/objects/rock_w3_2.png",   (110,  20,   0)),
        3: ("assets/sprites/objects/rock_w3_3.png",   (160,  60,  10)),
    }
}

# clase que representa una roca decorativo con colisión
class Rock(pygame.sprite.Sprite):
    # inicializamos la roca: cargamos sprite, calculamos rectángulo de colisión
    def __init__(self, pos, world=1):
        super().__init__()

        rock_variant = random.randint(1, 3)

        # tamaño aleatorio para que no todas las rocas sean iguales
        size = random.randint(65, 115)
        w = size
        h = int(size * 0.75)

        # elegimos sprite según el mundo actual, con fallback al mundo 1
        world_rocks = ROCK_SPRITES.get(world, ROCK_SPRITES[1])
        sprite_path, fallback_color = world_rocks[rock_variant]

        self.image = load_sprite(sprite_path, (w, h), fallback_color)

        # hit_rect reducido centrado en la base visual de la roca
        hx = int(w * 0.60)
        hy = int(h * 0.55)
        self.hit_rect = pygame.Rect(0, 0, hx, hy)

        self.hit_rect.center = (int(pos[0]), int(pos[1]) + h // 25)

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)