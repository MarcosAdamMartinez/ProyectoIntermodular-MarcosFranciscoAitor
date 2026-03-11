import pygame
import random
from src.utils.settings import *


class Enemy(pygame.sprite.Sprite):
    def __init__(self, target):
        super().__init__()
        self.image = load_sprite("assets/sprites/zombie.png", (100, 90), RED)

        # Aparecer en un radio alrededor del jugador
        spawn_radius = 400
        angle = random.uniform(0, 360)
        offset = pygame.math.Vector2(spawn_radius, 0).rotate(angle)
        spawn_pos = target.pos + offset

        self.rect = self.image.get_rect(center=(spawn_pos.x, spawn_pos.y))
        self.pos = pygame.math.Vector2(spawn_pos)
        self.target = target
        self.speed = random.uniform(1.5, 2.5)
        self.hp = 20

    def update(self):
        direction = (self.target.pos - self.pos)
        if direction.length() > 0:
            direction = direction.normalize()
            self.pos += direction * self.speed
            self.rect.center = self.pos

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()