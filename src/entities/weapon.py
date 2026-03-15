import pygame
from src.utils.settings import WEAPONS
from src.entities.projectile import Projectile


# Definimos la clase base para las armas que usaran nuestros personajes durante la partida
class Weapon:
    def __init__(self, name, owner):
        # Guardamos el nombre del arma y la referencia al personaje que la lleva para saber desde donde disparar
        self.name = name
        self.owner = owner

        # Buscamos las estadisticas especificas de este armamento en nuestro diccionario global de configuracion
        self.stats = WEAPONS[name].copy()

        # Inicializamos un temporizador a cero para controlar el tiempo exacto que debemos esperar entre cada ataque
        self.cooldown_timer = 0

    def update(self, enemies, sprite_group, proj_group):
        # Aumentamos nuestro contador de tiempo en cada fotograma que procesa el motor del juego
        self.cooldown_timer += 1

        # Comprobamos si el temporizador ha superado el tiempo de recarga y de ser asi disparamos y reiniciamos el reloj
        if self.cooldown_timer >= self.stats["cooldown"]:
            self.fire(enemies, sprite_group, proj_group)
            self.cooldown_timer = 0

    def fire(self, enemies, sprite_group, proj_group):
        # Verificamos que existan enemigos vivos en el mapa porque de lo contrario no tiene sentido intentar atacar
        if not enemies: return

        # Buscamos cual es el monstruo que se encuentra mas cerca de nosotros calculando la distancia matematica entre ambas posiciones
        closest_enemy = min(enemies, key=lambda e: self.owner.pos.distance_to(e.pos))

        # Calculamos la trayectoria exacta restando la coordenada de nuestro objetivo menos nuestra ubicacion actual
        direction = (closest_enemy.pos - self.owner.pos)

        # Nos aseguramos de que el vector de direccion tenga una longitud valida para evitar fallos al normalizarlo
        if direction.length() > 0:
            direction = direction.normalize()

            # Instanciamos un nuevo proyectil entregandole nuestro punto de origen la direccion de vuelo y el poder de dano
            proj = Projectile(self.owner.pos, direction, self.stats)

            # Agregamos el ataque recien creado a los grupos de dibujo y logica para que el motor grafico lo muestre en la pantalla
            sprite_group.add(proj)
            proj_group.add(proj)