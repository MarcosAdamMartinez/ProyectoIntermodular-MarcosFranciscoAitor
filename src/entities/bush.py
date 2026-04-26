import pygame
import random
from src.utils.settings import load_sprite

# Sprite y color de fallback por mundo (un solo tipo de arbusto/árbol por mundo)
BUSH_SPRITES = {
    1: ("assets/sprites/objects/bush.png",    (34, 139,  34)),   # Verde bosque
    2: ("assets/sprites/objects/bush_w2.png", (60, 100, 160)),   # Azul ártico / cristal
    3: ("assets/sprites/objects/bush_w3.png", (100,  20,   0)),  # Rojo infernal
}


class Bush(pygame.sprite.Sprite):
    def __init__(self, pos, world=1):
        super().__init__()

        size = random.randint(70, 120)

        sprite_path, fallback_color = BUSH_SPRITES.get(world, BUSH_SPRITES[1])
        self.image = load_sprite(sprite_path, (size + 40, size), fallback_color)

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)

        # Colisión en la parte baja del tronco
        trunk_w = int((size + 40) * 0.18)
        trunk_h = int(size * 0.22)
        self.hit_rect = pygame.Rect(0, 0, trunk_w, trunk_h)

        # --- LA SOLUCIÓN DEFINITIVA ---
        # get_bounding_rect() encuentra el rectángulo exacto que ocupa el dibujo,
        # ignorando todito el fondo transparente.
        bounding_rect = self.image.get_bounding_rect()

        # Trasladamos esa posición visual a las coordenadas reales del mundo
        visual_centerx = self.rect.left + bounding_rect.centerx
        visual_bottom = self.rect.top + bounding_rect.bottom

        # Ahora anclamos la colisión a la base REAL del dibujo, no al PNG completo
        self.hit_rect.midbottom = (visual_centerx, visual_bottom)