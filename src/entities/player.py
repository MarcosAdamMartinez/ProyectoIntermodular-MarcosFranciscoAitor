import pygame
from src.utils.settings import *
from src.entities.weapon import Weapon
import src.core.engine as engine


# Definimos la clase de nuestro jugador principal heredando de los sprites de Pygame para poder dibujarlo en pantalla
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, character_name, sprite_group, proj_group):
        super().__init__()

        # Buscamos las estadisticas base de nuestro personaje en el diccionario de configuracion
        stats = CHARACTERS[character_name]

        # Cargamos el sprite de nuestro heroe ajustando su tamano y definiendo un color de respaldo por si falla la imagen
        if character_name == "my_uncle":
            self.image = load_sprite(stats["sprite"], (PLAYER_SIZE + 60, PLAYER_SIZE - 10), stats["color"])
        else:
            self.image = load_sprite(stats["sprite"], (PLAYER_SIZE + 30, PLAYER_SIZE), stats["color"])

        # Preparamos la caja de colisiones y el vector de posicion exacta en el mapa
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.math.Vector2(x, y)

        # Asignamos la velocidad de movimiento y los puntos de vida iniciales y maximos que le corresponden a este personaje
        self.speed = stats["speed"]
        self.hp = stats["hp"]
        self.max_hp = stats["hp"]

        # Creamos un inventario vacio para nuestras armas y guardamos la referencia a los grupos de sprites
        self.weapons = []
        self.sprite_group = sprite_group
        self.proj_group = proj_group

        # Le entregamos a nuestro jugador su arma inicial basandonos en las estadisticas cargadas
        self.add_weapon(stats["starting_weapon"])

        # Inicializamos las estadisticas de progreso del jugador
        self.xp = 0
        self.level = 1
        self.xp_to_next_level = 50
        self.magnet_radius = 50  # Distancia a la que las gemas empiezan a volar hacia nosotros

        self.pending_level_ups = 0

        self._base_levelup_vol = 0.05
        try:
            self.level_up_sound = pygame.mixer.Sound("assets/sounds/player/level_up.mp3")
            self.level_up_sound.set_volume(self._base_levelup_vol)
        except:
            self.level_up_sound = None

    def apply_volume_scale(self, factor):
        if self.level_up_sound:
            self.level_up_sound.set_volume(self._base_levelup_vol * factor)
        for weapon in self.weapons:
            weapon.apply_volume_scale(factor)

    def add_weapon(self, weapon_name):
        # Creamos una funcion para poder equipar nuevas armas al inventario de nuestro personaje durante la partida
        self.weapons.append(Weapon(weapon_name, self))

    def update(self, enemies):
        # En cada fotograma leemos que teclas estamos pulsando para calcular hacia donde queremos movernos
        keys = pygame.key.get_pressed()
        input_vector = pygame.math.Vector2(0, 0)

        # Comprobamos las teclas direccionales y modificamos nuestro vector de movimiento segun corresponda
        if keys[pygame.K_w]: input_vector.y -= 1
        if keys[pygame.K_s]: input_vector.y += 1
        if keys[pygame.K_a]: input_vector.x -= 1
        if keys[pygame.K_d]: input_vector.x += 1

        # Verificamos si nos estamos moviendo y normalizamos el vector para evitar que caminemos mas rapido al ir en diagonal
        if input_vector.length() > 0:
            input_vector = input_vector.normalize()

        # Actualizamos nuestra posicion matematica multiplicando la direccion por nuestra velocidad y centramos la caja de colisiones ahi
        self.pos += input_vector * self.speed
        self.rect.center = self.pos

        # Recorremos todas las armas que llevamos equipadas y las actualizamos para que puedan apuntar y disparar a los enemigos
        for weapon in self.weapons:
            weapon.update(enemies, self.sprite_group, self.proj_group)

    def take_damage(self, amount):
        # Disminuimos nuestros puntos de vida actuales restando la cantidad de dano que hayamos recibido
        self.hp -= amount

        # Comprobamos si nuestra salud ha llegado a cero y de ser asi imprimimos un mensaje confirmando que hemos caido
        if self.hp <= 0:
            print("¡Has muerto!")

    def gain_xp(self, amount):
        # Sumamos la experiencia recogida y comprobamos si hemos alcanzado el limite para subir
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.level_up_sound.play()

        # Restamos la experiencia requerida por si recogimos de mas y subimos el nivel
        self.xp -= self.xp_to_next_level
        self.level += 1

        # Aumentamos la cantidad necesaria para el proximo nivel multiplicandola
        self.xp_to_next_level = int(self.xp_to_next_level * 1.1)

        self.pending_level_ups += 1

    def apply_upgrade(self, upgrade):
        if upgrade["type"] == "max_hp":
            self.max_hp += upgrade["value"]
            self.hp += upgrade["value"]
        elif upgrade["type"] == "speed":
            self.speed += upgrade["value"]
        elif upgrade["type"] == "damage":
            for weapon in self.weapons:
                weapon.stats["damage"] += upgrade["value"]
        elif upgrade["type"] == "cooldown":
            for weapon in self.weapons:
                weapon.stats["cooldown"] = max(10, int(weapon.stats["cooldown"] * upgrade["value"]))
        elif upgrade["type"] == "magnet":
            self.magnet_radius += upgrade["value"]
        elif upgrade["type"] == "hp":
            if not self.hp + upgrade["value"] > self.max_hp:
                self.hp += upgrade["value"]
            else:
                self.hp = self.max_hp