import pygame
import math
from src.utils.settings import load_sprite


# Definimos la clase para nuestros proyectiles heredando de los sprites de Pygame para integrarlos en el motor del juego
class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, stats):
        super().__init__()

        # Cargamos la imagen original de nuestro proyectil dependiendo del tipo de arma y le asignamos un color por defecto si no existe
        original_image = load_sprite(f"assets/sprites/{stats['type']}.png", (60, 60), stats["color"])

        # Calculamos el angulo matematico exacto hacia nuestro objetivo usando arcotangente para saber hacia donde debe mirar el sprite
        angle = math.degrees(math.atan2(-direction.y, direction.x))

        # Rotamos la imagen original una unica vez usando el angulo que acabamos de calcular para que el ataque visualmente apunte a la direccion correcta
        self.image = pygame.transform.rotate(original_image, angle)

        # Centramos la caja de colisiones de nuestro proyectil exactamente en la posicion inicial que recibimos por parametro
        self.rect = self.image.get_rect(center=pos)

        # Guardamos el vector de posicion inicial y la direccion hacia la que volaremos
        self.pos = pygame.math.Vector2(pos)
        self.direction = direction

        # Asignamos la velocidad de vuelo el dano que causaremos al impactar y el tiempo de vida en fotogramas que durara el proyectil
        self.speed = stats["speed"]
        self.damage = stats["damage"]
        self.lifetime = 120

    def update(self):
        # Actualizamos nuestra posicion en la pantalla sumando a las coordenadas la direccion de movimiento multiplicada por la velocidad
        self.pos += self.direction * self.speed

        # Movemos nuestra caja de colisiones para que siempre acompane a la nueva posicion del dibujo en la pantalla
        self.rect.center = self.pos

        # Reducimos el tiempo de vida de nuestro proyectil en cada fotograma para que no viaje por la pantalla eternamente
        self.lifetime -= 1

        # Comprobamos si el tiempo de vida util ha llegado a su fin y de ser asi eliminamos el proyectil para liberar la memoria del juego
        if self.lifetime <= 0:
            self.kill()