import pygame
import random
from src.utils.settings import *


# Definimos la clase del enemigo basandonos en los sprites de Pygame para integrarlo en nuestro juego
class Enemy(pygame.sprite.Sprite):
    def __init__(self, target):
        super().__init__()

        # Cargamos la imagen de nuestro zombi ajustando sus dimensiones y asignando un color rojo por si la imagen no carga
        self.image = load_sprite("assets/sprites/zombie.png", (100, 90), RED)

        # Calculamos el punto de aparicion para que el enemigo nazca en un radio circular constante alrededor del jugador
        spawn_radius = 400

        # Elegimos un angulo aleatorio y usamos las matematicas de vectores para encontrar la coordenada exacta donde lo colocaremos
        angle = random.uniform(0, 360)
        offset = pygame.math.Vector2(spawn_radius, 0).rotate(angle)
        spawn_pos = target.pos + offset

        # Establecemos la caja de colisiones en la posicion calculada y preparamos la variable para guardar su ubicacion actual
        self.rect = self.image.get_rect(center=(spawn_pos.x, spawn_pos.y))
        self.pos = pygame.math.Vector2(spawn_pos)

        # Guardamos la referencia a nuestro jugador objetivo para que el zombi sepa a quien debe perseguir despues
        self.target = target

        # Le asignamos una velocidad al azar para que los enemigos no se muevan todos exactamente igual y definimos su salud inicial
        self.speed = random.uniform(1.5, 2.5)
        self.hp = 20

    def update(self):
        # Calculamos la distancia y la trayectoria exacta entre nosotros y nuestro objetivo principal
        direction = (self.target.pos - self.pos)

        # Verificamos que no hayamos alcanzado ya la misma posicion que el jugador para evitar errores en los calculos
        if direction.length() > 0:
            # Normalizamos el vector de la direccion para que el movimiento sea fluido e idoneo sin importar hacia donde vayamos
            direction = direction.normalize()

            # Actualizamos nuestra posicion sumando la direccion hacia el objetivo multiplicada por la velocidad que le dimos al nacer
            self.pos += direction * self.speed

            # Centramos la caja de colisiones del enemigo en esta nueva posicion recien calculada
            self.rect.center = self.pos

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()
            return True # Avisamos de que el enemigo acaba de morir
        return False
