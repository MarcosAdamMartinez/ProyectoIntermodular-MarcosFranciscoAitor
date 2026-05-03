import pygame
from src.utils.settings import *
from src.entities.weapon import Weapon
from src.utils.animation import AnimationController
import src.core.engine as engine


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, character_name, sprite_group, proj_group):
        super().__init__()

        stats = CHARACTERS[character_name]

        if character_name == "my_uncle":
            sprite_size = (PLAYER_SIZE + 60, PLAYER_SIZE - 10)
        else:
            sprite_size = (PLAYER_SIZE + 80, PLAYER_SIZE + 50)

        # Imagen estática de fallback (misma lógica de siempre)
        fallback = load_sprite(stats["sprite"], sprite_size, stats["color"])

        # ── Sistema de animación ─────────────────────────────────────────────
        anim_base = f"assets/sprites/players/{stats.get('anim_folder', character_name)}"
        self._anim = AnimationController(anim_base, sprite_size, fallback, fps=8)

        self.image = self._anim.update()
        self.rect  = self.image.get_rect(center=(x, y))
        self.pos   = pygame.math.Vector2(x, y)

        self.speed  = stats["speed"]
        self.hp     = stats["hp"]
        self.max_hp = stats["hp"]

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

    # ------------------------------------------------------------------ #

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

        moving = input_vector.length() > 0

        if moving:
            input_vector = input_vector.normalize()
            # Elegir dirección horizontal para la animación
            if input_vector.x >= 0:
                self._anim.set_state("walk_right")
            else:
                self._anim.set_state("walk_left")
        else:
            self._anim.set_state("idle")

        self.pos += input_vector * self.speed
        self.rect.center = self.pos

        # Actualizar frame de animación
        center = self.rect.center
        self.image = self._anim.update()
        self.rect  = self.image.get_rect(center=center)

        for weapon in self.weapons:
            weapon.update(enemies, self.sprite_group, self.proj_group)

    def take_damage(self, amount):
        self.hp -= amount
        self._anim.trigger_hurt()   # dispara animación de hurt si existe
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
        elif upgrade["type"] == "new_weapon":
            weapon_name = upgrade["value"]
            owned = {w.name for w in self.weapons}
            if weapon_name not in owned:
                self.add_weapon(weapon_name)