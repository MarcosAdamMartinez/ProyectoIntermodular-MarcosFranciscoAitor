import pygame
from src.utils.settings import *
from src.entities.weapon import Weapon
import src.core.engine as engine


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, character_name, sprite_group, proj_group):
        super().__init__()

        stats = CHARACTERS[character_name]

        if character_name == "my_uncle":
            self.image = load_sprite(stats["sprite"], (PLAYER_SIZE + 60, PLAYER_SIZE - 10), stats["color"])
        else:
            self.image = load_sprite(stats["sprite"], (PLAYER_SIZE + 30, PLAYER_SIZE), stats["color"])

        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)

        self.speed   = stats["speed"]
        self.hp      = stats["hp"]
        self.max_hp  = stats["hp"]

        self.weapons      = []
        self.sprite_group = sprite_group
        self.proj_group   = proj_group

        self.add_weapon(stats["starting_weapon"])

        self.xp               = 0
        self.level            = 1
        self.xp_to_next_level = 50
        self.magnet_radius    = 50

        self.pending_level_ups = 0

        self._base_levelup_vol = 0.05
        try:
            self.level_up_sound = pygame.mixer.Sound("assets/sounds/player/level_up.mp3")
            self.level_up_sound.set_volume(self._base_levelup_vol)
        except:
            self.level_up_sound = None

    def apply_volume_scale(self, factor):
        if self.level_up_sound:
            self.level_up_sound.set_volume(self._base_levelup_vol * factor)
        for weapon in self.weapons:
            weapon.apply_volume_scale(factor)

    def add_weapon(self, weapon_name):
        self.weapons.append(Weapon(weapon_name, self))

    def update(self, enemies):
        keys = pygame.key.get_pressed()
        input_vector = pygame.math.Vector2(0, 0)

        if keys[pygame.K_w]: input_vector.y -= 1
        if keys[pygame.K_s]: input_vector.y += 1
        if keys[pygame.K_a]: input_vector.x -= 1
        if keys[pygame.K_d]: input_vector.x += 1

        if input_vector.length() > 0:
            input_vector = input_vector.normalize()

        self.pos += input_vector * self.speed
        self.rect.center = self.pos

        for weapon in self.weapons:
            weapon.update(enemies, self.sprite_group, self.proj_group)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            print("¡Has muerto!")

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        if self.level_up_sound:
            self.level_up_sound.play()
        self.xp -= self.xp_to_next_level
        self.level += 1
        self.xp_to_next_level = int(self.xp_to_next_level * 1.1)
        self.pending_level_ups += 1

    def apply_upgrade(self, upgrade):
        if upgrade["type"] == "max_hp":
            self.max_hp += upgrade["value"]
            self.hp     += upgrade["value"]
        elif upgrade["type"] == "speed":
            self.speed += upgrade["value"]
        elif upgrade["type"] == "damage":
            for weapon in self.weapons:
                weapon.stats["damage"] += upgrade["value"]
        elif upgrade["type"] == "cooldown":
            for weapon in self.weapons:
                weapon.stats["cooldown"] = max(10, int(weapon.stats["cooldown"] * upgrade["value"]))
        elif upgrade["type"] == "magnet":
            self.magnet_radius += upgrade["value"]
        elif upgrade["type"] == "hp":
            if not self.hp + upgrade["value"] > self.max_hp:
                self.hp += upgrade["value"]
            else:
                self.hp = self.max_hp