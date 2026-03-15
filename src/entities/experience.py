import pygame
from src.utils.settings import load_sprite, GREEN


# Definimos la clase de nuestra gema de experiencia para que pueda ser dibujada por la camara
class Exp(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        # Cargamos la imagen de la gema o un cuadrado verde si no existe el archivo
        self.image = load_sprite("assets/sprites/exp.png", (15, 15), GREEN)
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)

        # Asignamos la cantidad de experiencia que da la velocidad a la que vuela y su objetivo inicial
        self.xp_value = 10
        self.speed = 8
        self.target = None

    def update(self):
        # Si la gema ha detectado al jugador comenzara a moverse hacia su posicion
        if self.target:
            direction = self.target.pos - self.pos
            if direction.length() > 0:
                direction = direction.normalize()
                self.pos += direction * self.speed
                self.rect.center = self.pos