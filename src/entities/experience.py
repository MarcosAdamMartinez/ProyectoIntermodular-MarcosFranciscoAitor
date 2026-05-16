# Importamos pygame y los ajustes de color y carga de sprites
import pygame
from src.utils.settings import load_sprite, GREEN

# Clase que representa un orbe de experiencia que suelta un enemigo al morir
class Exp(pygame.sprite.Sprite):
    def __init__(self, pos, xp_value=10):
        super().__init__()

        # Cargamos el sprite del orbe; si no existe usamos un cuadrado verde
        self.image = load_sprite("assets/sprites/objects/exp.png", (15, 15), GREEN)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)

        self.xp_value = xp_value
        # target es None hasta que el imán del jugador lo activa
        self.target = None
        # Velocidad base del orbe cuando se dirige al jugador
        self.base_speed = 10

    def update(self):
        # Solo nos movemos si tenemos un objetivo (el jugador dentro del radio del imán)
        if self.target:
            dx = self.target.pos.x - self.pos.x
            dy = self.target.pos.y - self.pos.y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 1.0:
                dist = dist_sq ** 0.5
                # La velocidad escala con la distancia para que los orbes lejanos lleguen rápido
                player_speed = getattr(self.target, 'speed', 10)
                speed = max(self.base_speed, player_speed * 1.5, dist * 0.18)
                inv = speed / dist
                self.pos.x += dx * inv
                self.pos.y += dy * inv
                self.rect.centerx = int(self.pos.x)
                self.rect.centery  = int(self.pos.y)