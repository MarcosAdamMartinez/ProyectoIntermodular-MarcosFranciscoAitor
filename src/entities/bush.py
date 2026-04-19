import pygame
import random
from src.utils.settings import load_sprite


class Bush(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        # Le damos un tamaño aleatorio para generar variedad visual
        size = random.randint(70, 120)

        # Cargamos el sprite (o un cuadrado verde oscuro si falta el archivo)
        self.image = load_sprite("assets/sprites/objects/bush.png", (size + 40, size), (34, 139, 34))

        # Le aplicamos una rotación aleatoria de 0 a 360 grados para que parezcan diferentes plantas

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)