import pygame
import random
from src.utils.settings import *


# Definimos la clase del enemigo basandonos en los sprites de Pygame
class Enemy(pygame.sprite.Sprite):
    def __init__(self, target, enemy_type="zombie"):
        super().__init__()

        self.enemy_type = enemy_type

        # Asignamos estadisticas y sprites segun el tipo de enemigo
        if enemy_type == "zombie":
            size = (100, 90)
            color = RED
            self.speed = random.uniform(1.5, 2.5)
            self.hp = 20
        elif enemy_type == "slime":
            size = (100, 100)
            color = (0, 200, 100)  # Verde lima si no hay sprite
            self.speed = random.uniform(1.2, 2.0)
            self.hp = 12
        elif enemy_type == "goblin":
            size = (90, 80)
            color = (0, 150, 0)  # Verde si no hay sprite
            self.speed = random.uniform(2.0, 3.0)
            self.hp = 45
        elif enemy_type == "skeleton":
            size = (95, 95)
            color = (200, 200, 200)  # Gris claro si no hay sprite
            self.speed = random.uniform(2.5, 3.5)
            self.hp = 80
        elif enemy_type == "golem":
            size = (130, 130)
            color = (100, 80, 60)  # Marrón piedra si no hay sprite
            self.speed = random.uniform(1.0, 1.8)
            self.hp = 180
        elif enemy_type == "bat":
            size = (70, 60)
            color = (80, 0, 80)  # Morado oscuro si no hay sprite
            self.speed = random.uniform(3.0, 4.5)
            self.hp = 30
        elif enemy_type == "demon":
            size = (110, 110)
            color = (180, 20, 20)  # Rojo demonio si no hay sprite
            self.speed = random.uniform(2.5, 3.5)
            self.hp = 150
        elif enemy_type == "giga_zombie":
            size = (200, 200)
            color = (180, 30, 0)  # Rojo zombificado si no hay sprite
            self.speed = random.uniform(1.0, 1.5)
            self.hp = 500
        elif enemy_type == "yeti":
            size = (200, 200)
            color = (200, 230, 255)  # Blanco azulado si no hay sprite
            self.speed = random.uniform(1.2, 1.8)
            self.hp = 700
        elif enemy_type == "minotaur":
            size = (220, 220)
            color = (120, 40, 10)  # Marrón rojizo si no hay sprite
            self.speed = random.uniform(1.5, 2.2)
            self.hp = 1000

        # Cargamos la imagen correspondiente (Ej: assets/sprites/goblin.png)
        self.image = load_sprite(f"assets/sprites/enemies/{enemy_type}.png", size, color)

        # Calculamos el punto de aparicion circular
        boss_types = {"giga_zombie", "yeti", "minotaur"}
        spawn_radius = 500 if enemy_type in boss_types else 400

        angle = random.uniform(0, 360)
        offset = pygame.math.Vector2(spawn_radius, 0).rotate(angle)
        spawn_pos = target.pos + offset

        self.rect = self.image.get_rect(center=(spawn_pos.x, spawn_pos.y))
        self.pos = pygame.math.Vector2(spawn_pos)

        self.target = target

        # --- CARGAR SONIDO DE RECIBIR DAÑO (ÚNICO SONIDO DEL ENEMIGO) ---
        self._base_hurt_vol = 0.04
        try:
            self.hurt_sound = pygame.mixer.Sound(f"assets/sounds/enemies/{enemy_type}_hurt.mp3")
            self.hurt_sound.set_volume(self._base_hurt_vol)
        except:
            self.hurt_sound = None

    def apply_volume_scale(self, factor):
        if self.hurt_sound:
            self.hurt_sound.set_volume(self._base_hurt_vol * factor)

    def update(self):
        direction = (self.target.pos - self.pos)

        if direction.length() > 0:
            direction = direction.normalize()
            self.pos += direction * self.speed
            self.rect.center = self.pos

    def take_damage(self, amount):
        # --- REPRODUCIR SONIDO AL RECIBIR DAÑO ---
        if self.hurt_sound:
            self.hurt_sound.play()

        self.hp -= amount
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def is_boss_type(self):
        return self.enemy_type in {"giga_zombie", "yeti", "minotaur"}