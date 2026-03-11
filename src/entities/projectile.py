import pygame
from src.utils.settings import load_sprite


class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, stats):
        super().__init__()
        self.image = load_sprite(f"assets/sprites/{stats['type']}.png", (40, 40), stats["color"])

        # Rotar la imagen hacia la dirección en la que viaja
        angle = direction.angle_to(pygame.math.Vector2(1, 0))
        self.image = pygame.transform.rotate(self.image, angle)

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.direction = direction
        self.speed = stats["speed"]
        self.damage = stats["damage"]
        self.lifetime = 120  # Dura unos 2 segundos

    def update(self):
        self.pos += self.direction * self.speed
        self.rect.center = self.pos
        self.lifetime -= 1

        if self.lifetime <= 0:
            self.kill()