import pygame
import math
from src.utils.settings import load_sprite

class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, stats, owner):
        super().__init__()

        self.owner = owner
        self.stats = stats
        self.is_boomerang = stats.get("boomerang", False)
        self.is_melee = stats.get("melee", False)
        self.returning = False
        self.hit_enemies = []

        self.speed = stats["speed"]
        self.damage = stats["damage"]
        self.direction = direction

        self.origin_pos = pygame.math.Vector2(pos)

        if self.is_melee:
            w_size = (90, 90)
        elif self.is_boomerang:
            w_size = (50, 50)
        else:
            w_size = (70, 70)

        self.original_image = load_sprite(f"assets/sprites/weapons/{stats['type']}.png", w_size, stats["color"])

        if self.is_melee:
            self.original_image = load_sprite(f"assets/sprites/weapons/melee.png", w_size, stats["color"])
            self.base_angle = math.degrees(math.atan2(-direction.y, direction.x))
            self.current_angle = self.base_angle + 45
            self.sweep_speed = -3
            self.distance = 45
            self._update_melee_pos()
        else:
            angle = math.degrees(math.atan2(-direction.y, direction.x))
            self.image = pygame.transform.rotate(self.original_image, angle)
            self.rect = self.image.get_rect(center=pos)
            self.pos = pygame.math.Vector2(pos)
            self.lifetime = 30

    def _update_melee_pos(self):
        offset = pygame.math.Vector2(self.distance, 0).rotate(-self.current_angle)
        self.pos = self.owner.pos + offset
        self.image = pygame.transform.rotate(self.original_image, self.current_angle - 45)
        self.rect = self.image.get_rect(center=self.pos)

    def update(self):
        if self.is_melee:
            self.current_angle += self.sweep_speed
            self._update_melee_pos()
            if self.current_angle <= self.base_angle - 45:
                self.kill()

        elif self.is_boomerang:
            if not self.returning:
                self.pos += self.direction * self.speed
                self.lifetime -= 1
                if self.lifetime <= 0:
                    self.returning = True
            else:
                return_dir = self.origin_pos - self.pos
                if return_dir.length() < self.speed + 10:
                    self.kill()
                else:
                    return_dir = return_dir.normalize()
                    self.pos += return_dir * (self.speed + 2)
            self.rect.center = self.pos
        else:
            self.pos += self.direction * self.speed
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.kill()
            self.rect.center = self.pos