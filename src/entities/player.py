# Importamos pygame, las settings globales, el sistema de armas y animación
import pygame
from src.utils.settings import *
from src.entities.weapon import Weapon
from src.utils.animation import AnimationController
import src.core.engine as engine


# Clase principal del jugador: maneja movimiento, animación, XP, armas y upgrades
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, character_name, sprite_group, proj_group):
        super().__init__()

        # Leemos las stats del personaje elegido desde settings
        stats = CHARACTERS[character_name]

        # my_uncle tiene un tamaño especial por su sprite particular
        if character_name == "my_uncle":
            sprite_size = (PLAYER_SIZE + 60, PLAYER_SIZE - 10)
        else:
            sprite_size = (PLAYER_SIZE + 80, PLAYER_SIZE + 50)

        # Imagen estática de fallback por si no hay carpeta de animación
        fallback = load_sprite(stats["sprite"], sprite_size, stats["color"])

        # Inicializamos el controlador de animación con la carpeta del personaje
        anim_base = f"assets/sprites/players/{stats.get('anim_folder', character_name)}"
        self.anim = AnimationController(anim_base, sprite_size, fallback, fps=8)

        self.image = self.anim.update()
        self.rect  = self.image.get_rect(center=(x, y))
        self.pos   = pygame.math.Vector2(x, y)

        # Stats del jugador sacadas de la configuración del personaje
        self.speed  = stats["speed"]
        self.hp     = stats["hp"]
        self.max_hp = stats["hp"]

        # Lista de armas activas y grupos de sprites donde se añaden los proyectiles
        self.weapons      = []
        self.sprite_group = sprite_group
        self.proj_group   = proj_group

        # Equipamos el arma inicial del personaje
        self.add_weapon(stats["starting_weapon"])

        # Variables de progresión: XP, nivel y radio del imán de gemas
        self.xp               = 0
        self.level            = 1
        self.xp_to_next_level = 50
        self.magnet_radius    = 50

        # Contador de subidas de nivel pendientes de procesar (menú de mejoras)
        self.pending_level_ups = 0

        # Intentamos cargar el sonido de subida de nivel
        self.base_levelup_vol = 0.05
        try:
            self.level_up_sound = pygame.mixer.Sound("assets/sounds/player/level_up.mp3")
            self.level_up_sound.set_volume(self.base_levelup_vol)
        except:
            self.level_up_sound = None

    def apply_volume_scale(self, factor):
        # Propagamos el factor de volumen al sonido de subida de nivel y a todas las armas
        if self.level_up_sound:
            self.level_up_sound.set_volume(self.base_levelup_vol * factor)
        for weapon in self.weapons:
            weapon.apply_volume_scale(factor)

    def add_weapon(self, weapon_name):
        # Añadimos una nueva arma a la lista del jugador
        self.weapons.append(Weapon(weapon_name, self))

    def update(self, enemies):
        # Leemos las teclas WASD y calculamos el vector de movimiento
        keys = pygame.key.get_pressed()
        input_vector = pygame.math.Vector2(0, 0)

        if keys[pygame.K_w]: input_vector.y -= 1
        if keys[pygame.K_s]: input_vector.y += 1
        if keys[pygame.K_a]: input_vector.x -= 1
        if keys[pygame.K_d]: input_vector.x += 1

        moving = input_vector.length() > 0

        if moving:
            input_vector = input_vector.normalize()
            # Elegimos walk_right o walk_left según la dirección horizontal
            if input_vector.x >= 0:
                self.anim.set_state("walk_right")
            else:
                self.anim.set_state("walk_left")
        else:
            self.anim.set_state("idle")

        # Movemos al jugador y actualizamos su rect
        self.pos += input_vector * self.speed
        self.rect.center = self.pos

        # Actualizamos la animación conservando el centro para no hacer saltar el sprite
        center = self.rect.center
        self.image = self.anim.update()
        self.rect  = self.image.get_rect(center=center)

        # Actualizamos todas las armas equipadas
        for weapon in self.weapons:
            weapon.update(enemies, self.sprite_group, self.proj_group)

    def take_damage(self, amount):
        # Restamos HP y disparamos la animación de daño
        self.hp -= amount
        self.anim.trigger_hurt()
        if self.hp <= 0:
            print("¡Has muerto!")

    def gain_xp(self, amount):
        # Acumulamos XP y subimos de nivel si llegamos al umbral
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        # Subimos de nivel, ajustamos el umbral de XP y apuntamos la subida como pendiente
        if self.level_up_sound:
            self.level_up_sound.play()
        self.xp -= self.xp_to_next_level
        self.level += 1
        # Cada nivel requiere un 10% más de XP que el anterior
        self.xp_to_next_level = int(self.xp_to_next_level * 1.1)
        self.pending_level_ups += 1

    def apply_upgrade(self, upgrade):
        utype = upgrade["type"]

        # Mejoras que afectan al jugador directamente
        if utype == "max_hp":
            self.max_hp += upgrade["value"]
            self.hp     += upgrade["value"]
        elif utype == "speed":
            self.speed += upgrade["value"]
        elif utype == "magnet":
            self.magnet_radius += upgrade["value"]
        elif utype == "hp":
            self.hp = min(self.hp + upgrade["value"], self.max_hp)
        elif utype == "new_weapon":
            weapon_name = upgrade["value"]
            # Solo añadimos el arma si el jugador no la tiene ya
            if weapon_name not in {w.name for w in self.weapons}:
                self.add_weapon(weapon_name)

        # Mejoras que afectan a un arma específica del jugador
        elif utype == "w_damage":
            for w in self.weapons:
                if w.name == upgrade.get("weapon"):
                    w.stats["damage"] += upgrade["value"]
        elif utype == "w_cooldown":
            for w in self.weapons:
                if w.name == upgrade.get("weapon"):
                    w.stats["cooldown"] = max(10, int(w.stats["cooldown"] * upgrade["value"]))
        elif utype == "w_burn_dmg":
            for w in self.weapons:
                if w.name == upgrade.get("weapon"):
                    w.stats["burn_damage"] = w.stats.get("burn_damage", 3) + upgrade["value"]
        elif utype == "w_burn_rad":
            for w in self.weapons:
                if w.name == upgrade.get("weapon"):
                    w.stats["burn_radius"] = w.stats.get("burn_radius", 35) + upgrade["value"]
        elif utype == "w_frags":
            for w in self.weapons:
                if w.name == upgrade.get("weapon"):
                    w.stats["frags"] = w.stats.get("frags", 2) + upgrade["value"]