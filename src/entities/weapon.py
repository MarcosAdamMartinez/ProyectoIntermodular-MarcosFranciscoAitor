import pygame
from src.utils.settings import WEAPONS
from src.entities.projectile import Projectile


class Weapon:
    def __init__(self, name, owner):
        self.name = name
        self.owner = owner
        self.stats = WEAPONS[name]
        self.cooldown_timer = 0

    def update(self, enemies, sprite_group, proj_group):
        self.cooldown_timer += 1
        if self.cooldown_timer >= self.stats["cooldown"]:
            self.fire(enemies, sprite_group, proj_group)
            self.cooldown_timer = 0

    def fire(self, enemies, sprite_group, proj_group):
        if not enemies: return

        # Apuntar al enemigo más cercano
        closest_enemy = min(enemies, key=lambda e: self.owner.pos.distance_to(e.pos))
        direction = (closest_enemy.pos - self.owner.pos)

        if direction.length() > 0:
            direction = direction.normalize()
            proj = Projectile(self.owner.pos, direction, self.stats)
            sprite_group.add(proj)
            proj_group.add(proj)