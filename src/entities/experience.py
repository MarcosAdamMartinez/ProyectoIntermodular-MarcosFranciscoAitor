import pygame
from src.utils.settings import load_sprite, GREEN

class Exp(pygame.sprite.Sprite):
    def __init__(self, pos, xp_value=10):
        super().__init__()

        self.image = load_sprite("assets/sprites/objects/exp.png", (15, 15), GREEN)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)

        self.xp_value = xp_value
        self.target = None
        # Velocidad base — se sobreescribe dinámicamente para garantizar
        # que el orbe siempre alcanza al jugador sin importar su speed
        self._base_speed = 10

    def update(self):
        if self.target:
            dx = self.target.pos.x - self.pos.x
            dy = self.target.pos.y - self.pos.y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 1.0:
                dist = dist_sq ** 0.5
                # Velocidad dinámica: siempre al menos 1.5× la del jugador,
                # y escala con la distancia para que los orbes lejanos
                # "se disparen" hacia el jugador al entrar en rango
                player_speed = getattr(self.target, 'speed', 10)
                speed = max(self._base_speed, player_speed * 1.5, dist * 0.18)
                inv = speed / dist
                self.pos.x += dx * inv
                self.pos.y += dy * inv
                self.rect.centerx = int(self.pos.x)
                self.rect.centery  = int(self.pos.y)