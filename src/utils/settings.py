import pygame
import os

# Pantalla
WIDTH = 1720
HEIGHT = 920
FPS = 60

# Colores
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
GREY = (159, 161, 164)
DARK_GREY = (74, 74, 74)
RED = (255, 0, 0)
BAR_RED = (100, 0, 0)
GREEN = (0, 255, 0)
BAR_GREEN = (0, 255, 0)
BORDER_GREEN = (20, 80, 20)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
LIGHT_YELLOW = (255, 255, 100)
DEATH_TEXT = (195, 196, 159)
BTN_BG = (32, 33, 36)
BTN_HOVER = (60, 64, 67)
BTN_BORDER = (95, 99, 104)
BTN_SHADOW = (15, 15, 18)

# Jugador base
PLAYER_SIZE = 100

# DATOS DE PERSONAJES
CHARACTERS = {
    "caballero": {
        "speed": 4,
        "hp": 150,
        "color": BLUE,
        "sprite": "assets/sprites/players/knight.png",
        "anim_folder": "knight",
        "starting_weapon": "espada"
    },
    "mago": {
        "speed": 6,
        "hp": 80,
        "color": (150, 0, 255),
        "sprite": "assets/sprites/players/mage.png",
        "anim_folder": "mage",
        "starting_weapon": "varita"
    },
    "my_uncle": {
        "speed": 5,
        "hp": 100,
        "color": GREY,
        "sprite": "assets/sprites/players/my_uncle.png",
        "anim_folder": "my_uncle",
        "starting_weapon": "banana"
    }
}

# DATOS DE ARMAS
WEAPONS = {
    "espada": {"cooldown": 20, "damage": 100, "speed": 0, "color": WHITE, "type": "melee", "melee": True},
    "varita": {"cooldown": 45, "damage": 10, "speed": 10, "color": YELLOW, "type": "ranged"},
    "banana": {"cooldown": 30, "damage": 10, "speed": 7, "color": YELLOW, "type": "banana", "boomerang": True}
}

# DATOS DE MEJORAS
UPGRADES = [
    {"id": "hp_up",      "name": "Corazon Fuerte",  "desc": "+20 Vida Maxima",               "type": "max_hp",  "value": 20},
    {"id": "speed_up",   "name": "Botas Ligeras",    "desc": "+1 Velocidad de movimiento",    "type": "speed",   "value": 1},
    {"id": "dmg_up",     "name": "Fuerza Bruta",     "desc": "+5 de daño a todas las armas",  "type": "damage",  "value": 5},
    {"id": "cd_down",    "name": "Manos Rapidas",    "desc": "Disparas mas rapido",            "type": "cooldown","value": 0.85},
    {"id": "magnet_up",  "name": "Iman Magico",      "desc": "+60 Rango de recogida",         "type": "magnet",  "value": 60},
    {"id": "health_up",  "name": "Beso de la Diosa", "desc": "+40 Vida",                      "type": "hp",      "value": 40}
]

def load_sprite(path, size, fallback_color, remove_bg=True):
    """Carga una imagen, quita el fondo si se pide, o devuelve un cuadrado si no existe."""
    if os.path.exists(path):
        image = pygame.image.load(path).convert_alpha()
        if remove_bg:
            background_color = image.get_at((0, 0))
            image.set_colorkey(background_color)
        return pygame.transform.scale(image, size)
    else:
        surf = pygame.Surface(size)
        surf.fill(fallback_color)
        return surf