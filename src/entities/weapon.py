import pygame
from src.utils.settings import WEAPONS
from src.entities.projectile import Projectile


class Weapon:
    def __init__(self, name, owner):
        self.name = name
        self.owner = owner

        self.stats = WEAPONS[name].copy()
        self.cooldown_timer = 0

        self._base_shoot_vol = 0.04
        try:
            self.shoot_sound = pygame.mixer.Sound(f"assets/sounds/weapons/{name}.mp3")
            self.shoot_sound.set_volume(self._base_shoot_vol)
        except:
            self.shoot_sound = None

    def apply_volume_scale(self, factor):
        if self.shoot_sound:
            self.shoot_sound.set_volume(self._base_shoot_vol * factor)

    def update(self, enemies, sprite_group, proj_group):
        self.cooldown_timer += 1
        if self.cooldown_timer >= self.stats["cooldown"]:
            self.fire(enemies, sprite_group, proj_group)
            self.cooldown_timer = 0

    def fire(self, enemies, sprite_group, proj_group):
        if not enemies: return

        closest_enemy = min(enemies, key=lambda e: self.owner.pos.distance_to(e.pos))
        direction = (closest_enemy.pos - self.owner.pos)

        if direction.length() > 0:
            direction = direction.normalize()
            proj = Projectile(self.owner.pos, direction, self.stats, self.owner)
            sprite_group.add(proj)
            proj_group.add(proj)

            if self.shoot_sound:
                self.shoot_sound.play()