import pygame
import math
from src.utils.settings import load_sprite


class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, stats):
        super().__init__()
        original_image = load_sprite(f"assets/sprites/{stats['type']}.png", (60, 60), stats["color"])

        # Calculamos el ángulo exacto hacia el objetivo
        angle = math.degrees(math.atan2(-direction.y, direction.x))

        # Ajuste de la imagen
        # Rotamos la imagen una sola vez
        self.image = pygame.transform.rotate(original_image, angle)

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.direction = direction
        self.speed = stats["speed"]
        self.damage = stats["damage"]
        self.lifetime = 120

    def update(self):
        self.pos += self.direction * self.speed
        self.rect.center = self.pos
        self.lifetime -= 1

        if self.lifetime <= 0:
            self.kill()