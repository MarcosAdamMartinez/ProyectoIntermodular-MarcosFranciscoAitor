# Importamos pygame, el diccionario de armas de settings y la clase de proyectil
import pygame
from src.utils.settings import WEAPONS
from src.entities.projectile import Projectile


# Clase que representa un arma equipada por el jugador
class Weapon:
    def __init__(self, name, owner):
        self.name = name
        # El jugador que lleva esta arma (necesario para saber desde dónde disparar)
        self.owner = owner

        # Copiamos las stats del arma para poder modificarlas con upgrades sin tocar el original
        self.stats = WEAPONS[name].copy()
        self.cooldown_timer = 0

        # Intentamos cargar el sonido de disparo del arma
        self.base_shoot_vol = 0.04
        try:
            self.shoot_sound = pygame.mixer.Sound(f"assets/sounds/weapons/{name}.mp3")
            self.shoot_sound.set_volume(self.base_shoot_vol)
        except:
            self.shoot_sound = None

    def apply_volume_scale(self, factor):
        # Ajustamos el volumen del disparo al factor global de la sesión
        if self.shoot_sound:
            self.shoot_sound.set_volume(self.base_shoot_vol * factor)

    def update(self, enemies, sprite_group, proj_group):
        # Sumamos un tick al cooldown y disparamos cuando se completa el tiempo de recarga
        self.cooldown_timer += 1
        if self.cooldown_timer >= self.stats["cooldown"]:
            self.fire(enemies, sprite_group, proj_group)
            self.cooldown_timer = 0

    def fire(self, enemies, sprite_group, proj_group):
        # Solo disparamos si hay enemigos en pantalla
        if not enemies: return

        # Buscamos el enemigo más cercano al dueño del arma
        closest_enemy = min(enemies, key=lambda e: self.owner.pos.distance_to(e.pos))
        direction = (closest_enemy.pos - self.owner.pos)

        if direction.length() > 0:
            direction = direction.normalize()
            # Creamos el proyectil y lo añadimos a los grupos de sprites correspondientes
            proj = Projectile(self.owner.pos, direction, self.stats, self.owner)
            sprite_group.add(proj)
            proj_group.add(proj)

            if self.shoot_sound:
                self.shoot_sound.play()