# Importamos pygame y os para la función de carga de sprites
import pygame
import os

# Resolución de la ventana y FPS objetivo
WIDTH = 1720
HEIGHT = 920
FPS = 60

# Paleta de colores usada en toda la aplicación
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

# Tamaño base del sprite del jugador en píxeles
PLAYER_SIZE = 100

# Configuración de cada personaje jugable: stats, sprite y arma inicial
CHARACTERS = {
    "caballero": {
        "speed": 4,
        "hp": 240,
        "color": BLUE,
        "sprite": "assets/sprites/players/knight.png",
        "anim_folder": "knight",
        "starting_weapon": "espada"
    },
    "mago": {
        "speed": 6,
        "hp": 120,
        "color": (150, 0, 255),
        "sprite": "assets/sprites/players/mage.png",
        "anim_folder": "mage",
        "starting_weapon": "varita"
    },
    "primal_man": {
        "speed": 5,
        "hp": 160,
        "color": GREY,
        "sprite": "assets/sprites/players/primal_man.png",
        "anim_folder": "primal_man",
        "starting_weapon": "banana"
    }
}

# Configuración de cada arma: cooldown, daño, velocidad, color, tipo y propiedades especiales
WEAPONS = {
    "espada": {"cooldown": 40, "damage": 25, "speed": 0,  "color": WHITE,  "type": "melee",  "melee": True},
    "varita": {"cooldown": 35, "damage": 15,  "speed": 10, "color": YELLOW, "type": "ranged", "burn": True,
               "burn_damage": 6, "burn_radius": 35},
    "banana": {"cooldown": 30, "damage": 10,  "speed": 7,  "color": YELLOW, "type": "banana", "boomerang": True,
               "frags": 1},
}

# Daño por contacto que aplica cada tipo de enemigo por frame al tocar al jugador
ENEMY_CONTACT_DAMAGE = {
    "zombie":      16,
    "slime":       4,
    "goblin":      12,
    "skeleton":    30,
    "golem":       25,
    "bat":         20,
    "demon":       35,
    "giga_zombie": 25,
    "yeti":        40,
    "minotaur":   60,
    "boss":        30,
}

# Lista de mejoras genéricas que puede obtener el jugador al subir de nivel
UPGRADES = [
    {"id": "hp_up",      "name": "Corazon Fuerte",  "desc": "+40 Vida Maxima",               "type": "max_hp",  "value": 40},
    {"id": "speed_up",   "name": "Botas Ligeras",    "desc": "+1 Velocidad de movimiento",    "type": "speed",   "value": 1},
    {"id": "magnet_up",  "name": "Iman Magico",      "desc": "+60 Rango de recogida",         "type": "magnet",  "value": 60},
    {"id": "health_up",  "name": "Beso de la Diosa", "desc": "+50 Vida",                      "type": "hp",      "value": 50}
]

# Mejoras específicas para cada arma, se mezclan con UPGRADES al mostrar el menú de subida
WEAPON_UPGRADES = {
    "espada": [
        {"id": "sword_dmg",  "weapon": "espada", "name": "Filo Afilado",    "desc": "+5 daño de espada",       "type": "w_damage",   "value": 5},
        {"id": "sword_cd",   "weapon": "espada", "name": "Estocada Rapida", "desc": "Espada 10% más rápida",    "type": "w_cooldown", "value": 0.90},
    ],
    "varita": [
        {"id": "wand_dmg",    "weapon": "varita", "name": "Magia Potente",   "desc": "+8 daño de varita",         "type": "w_damage",     "value": 8},
        {"id": "wand_cd",     "weapon": "varita", "name": "Cadencia Arcana", "desc": "Varita 10% más rápida",     "type": "w_cooldown",   "value": 0.90},
        {"id": "burn_dmg",    "weapon": "varita", "name": "Llama Voraz",     "desc": "+10 daño de quemadura/tick", "type": "w_burn_dmg",   "value": 10},
        {"id": "burn_rad",    "weapon": "varita", "name": "Hoguera",         "desc": "+10 radio de quemadura",    "type": "w_burn_rad",   "value": 10},
    ],
    "banana": [
        {"id": "ban_dmg",   "weapon": "banana", "name": "Banana Madura",   "desc": "+8 daño de banana",          "type": "w_damage",   "value": 8},
        {"id": "ban_cd",    "weapon": "banana", "name": "Manos de Mono",   "desc": "Banana 10% más rápida",      "type": "w_cooldown", "value": 0.90},
        {"id": "ban_frags", "weapon": "banana", "name": "Racimo",          "desc": "+1 fragmento al impactar",   "type": "w_frags",    "value": 1},
    ],
}

def load_sprite(path, size, fallback_color, remove_bg=True):
    # Cargamos el sprite desde disco si existe; si no, devolvemos un rectángulo de color sólido
    if os.path.exists(path):
        image = pygame.image.load(path).convert_alpha()
        if remove_bg:
            # Solo aplicamos colorkey si el pixel (0,0) es completamente opaco (sin alfa propio)
            px = image.get_at((0, 0))
            if px.a == 255:
                image.set_colorkey((px.r, px.g, px.b))
        # Escalamos la imagen al tamaño pedido preservando el canal alfa
        scaled = pygame.Surface(size, pygame.SRCALPHA)
        tmp = pygame.transform.scale(image, size)
        scaled.blit(tmp, (0, 0))
        return scaled
    else:
        # Fallback: superficie de color sólido con el color de emergencia
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((*fallback_color, 255))
        return surf