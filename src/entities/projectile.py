import pygame
import math
from src.utils.settings import load_sprite


# Definimos la clase para nuestros proyectiles heredando de los sprites de Pygame
class Projectile(pygame.sprite.Sprite):
    def __init__(self, pos, direction, stats, owner):  # Anadimos el owner al init
        super().__init__()

        # Guardamos la referencia a quien nos lanzo para saber a donde volver
        self.owner = owner

        # Comprobamos si esta arma tiene la propiedad de regresar usando get para evitar errores si no existe
        self.is_boomerang = stats.get("boomerang", False)
        self.returning = False

        # Creamos una lista vacia para recordar a que enemigos hemos golpeado ya y no hacerles dano infinito
        self.hit_enemies = []

        # Cargamos la imagen original de nuestro proyectil
        original_image = load_sprite(f"assets/sprites/{stats['type']}.png", (40, 40), stats["color"])
        angle = math.degrees(math.atan2(-direction.y, direction.x))
        self.image = pygame.transform.rotate(original_image, angle)

        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.math.Vector2(pos)
        self.direction = direction
        self.speed = stats["speed"]
        self.damage = stats["damage"]

        # Si es un boomerang este lifetime sera la distancia maxima a la que llegara antes de volver
        self.lifetime = 30

    def update(self):
        # Si nuestra arma tiene la propiedad de volver como el platano ejecutamos esta logica
        if self.is_boomerang:
            if not self.returning:
                # Volamos hacia adelante y restamos nuestro tiempo
                self.pos += self.direction * self.speed
                self.lifetime -= 1
                if self.lifetime <= 0:
                    # Cuando el tiempo se agota activamos el modo de regreso
                    self.returning = True
            else:
                # Calculamos el vector exacto desde nuestra posicion actual hasta la mano del jugador
                return_dir = self.owner.pos - self.pos

                # Si estamos lo suficientemente cerca del jugador como para que nos atrape nos eliminamos
                if return_dir.length() < self.speed + 10:
                    self.kill()
                else:
                    # Si aun estamos lejos volamos directamente hacia el
                    return_dir = return_dir.normalize()
                    self.pos += return_dir * (self.speed + 2)  # Volvemos un pelin mas rapido
        else:
            # Logica normal para proyectiles que no regresan (magia flechas etc)
            self.pos += self.direction * self.speed
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.kill()

        self.rect.center = self.pos