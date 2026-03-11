import pygame
from src.utils.settings import *
from src.entities.weapon import Weapon


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, character_name, sprite_group, proj_group):
        super().__init__()
        stats = CHARACTERS[character_name]

        self.image = load_sprite(stats["sprite"], (PLAYER_SIZE, PLAYER_SIZE + 10), stats["color"])
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)

        self.speed = stats["speed"]
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]

        self.weapons = []
        self.sprite_group = sprite_group
        self.proj_group = proj_group
        self.add_weapon(stats["starting_weapon"])

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