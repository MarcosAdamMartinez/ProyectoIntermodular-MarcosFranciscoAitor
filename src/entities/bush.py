# importamos pygame para los sprites y random para variar el tamaño
import pygame
import random
from src.utils.settings import load_sprite

# sprite y color de fallback por mundo; cada mundo tiene su tipo de arbusto
BUSH_SPRITES = {
    1: ("assets/sprites/objects/bush.png",    (34, 139,  34)),
    2: ("assets/sprites/objects/bush_w2.png", (60, 100, 160)),
    3: ("assets/sprites/objects/bush_w3.png", (100,  20,   0)),
}


# clase que representa un arbusto/árbol decorativo con colisión en la base del tronco
class Bush(pygame.sprite.Sprite):
    # inicializamos el arbusto: cargamos sprite, calculamos rectángulo de colisión
    def __init__(self, pos, world=1):
        super().__init__()

        # tamaño aleatorio para que no todos los arbustos sean iguales
        size = random.randint(70, 120)

        # elegimos sprite según el mundo actual, con fallback al mundo 1
        sprite_path, fallback_color = BUSH_SPRITES.get(world, BUSH_SPRITES[1])
        self.image = load_sprite(sprite_path, (size + 40, size), fallback_color)

        # rect general del sprite centrado en la posición dada
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)

        # hit_rect pequeño para que solo colisione con la base del tronco, no con las ramas
        trunk_w = int((size + 40) * 0.18)
        trunk_h = int(size * 0.22)
        self.hit_rect = pygame.Rect(0, 0, trunk_w, trunk_h)

        # get_bounding_rect ignora el fondo transparente y nos da el área real del dibujo
        bounding_rect = self.image.get_bounding_rect()

        # trasladamos la posición visual del bounding_rect a coordenadas reales del mundo
        visual_centerx = self.rect.left + bounding_rect.centerx
        visual_bottom = self.rect.top + bounding_rect.bottom

        # anclamos la colisión a la base real del dibujo, no al borde del PNG completo
        self.hit_rect.midbottom = (visual_centerx, visual_bottom)