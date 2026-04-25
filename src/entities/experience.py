import pygame
from src.utils.settings import load_sprite, GREEN

class Exp(pygame.sprite.Sprite):
    def __init__(self, pos, xp_value=10):
        super().__init__()

        self.image = load_sprite("assets/sprites/objects/exp.png", (15, 15), GREEN)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)

        self.xp_value = xp_value
        self.speed = 8
        self.target = None

    def update(self):
        if self.target:
            direction = self.target.pos - self.pos
            if direction.length() > 0:
                direction = direction.normalize()
                self.pos += direction * self.speed
                self.rect.center = self.pos