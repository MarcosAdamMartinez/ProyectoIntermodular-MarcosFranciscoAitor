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
        "speed": 14,
        "hp": 1000,
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
    "my_uncle": {
        "speed": 5,
        "hp": 160,
        "color": GREY,
        "sprite": "assets/sprites/players/my_uncle.png",
        "anim_folder": "my_uncle",
        "starting_weapon": "banana"
    }
}

# DATOS DE ARMAS
WEAPONS = {
    "espada": {"cooldown": 10, "damage": 25000, "speed": 0,  "color": WHITE,  "type": "melee",  "melee": True},
    "varita": {"cooldown": 35, "damage": 15,  "speed": 10, "color": YELLOW, "type": "ranged", "burn": True,
               "burn_damage": 6, "burn_radius": 35},
    "banana": {"cooldown": 30, "damage": 10,  "speed": 7,  "color": YELLOW, "type": "banana", "boomerang": True,
               "frags": 1},
}

# Qué arma desbloquea cada personaje al alcanzar los niveles especiales
# (las armas de los otros dos héroes)
WEAPON_UNLOCKS = {
    # nivel: {personaje_activo: [arma1, arma2]}
    25:  {
        "caballero": ["varita", "banana"],
        "mago":      ["espada", "banana"],
        "my_uncle":  ["espada", "varita"],
    },
    50:  {
        "caballero": ["varita", "banana"],
        "mago":      ["espada", "banana"],
        "my_uncle":  ["espada", "varita"],
    },
}
# Niveles en los que se ofrece el menú de desbloqueo de arma
WEAPON_UNLOCK_LEVELS = [25, 50]

# Daño por contacto de cada tipo de enemigo (por frame tocando al jugador)
ENEMY_CONTACT_DAMAGE = {
    "zombie":      13,
    "slime":       2,
    "goblin":      10,
    "skeleton":    25,
    "golem":       20,
    "bat":         30,
    "demon":       35,
    "giga_zombie": 15,
    "yeti":        27,
    "minotaur":    40,
    "boss":        30,
}

# DATOS DE MEJORAS
UPGRADES = [
    {"id": "hp_up",      "name": "Corazon Fuerte",  "desc": "+40 Vida Maxima",               "type": "max_hp",  "value": 40},
    {"id": "speed_up",   "name": "Botas Ligeras",    "desc": "+1 Velocidad de movimiento",    "type": "speed",   "value": 1},
    {"id": "magnet_up",  "name": "Iman Magico",      "desc": "+60 Rango de recogida",         "type": "magnet",  "value": 60},
    {"id": "health_up",  "name": "Beso de la Diosa", "desc": "+50 Vida",                      "type": "hp",      "value": 50}
]

# Mejoras específicas por arma — se mezclan con UPGRADES en el menú de subida
# Cada entrada lleva "weapon" (nombre del arma a la que aplica) y el icono se
# muestra junto al sprite del arma para que quede claro a qué afecta.
WEAPON_UPGRADES = {
    "espada": [
        # +30 daño (era +5, con la espada haciendo 100 base era insignificante)
        {"id": "sword_dmg",  "weapon": "espada", "name": "Filo Afilado",    "desc": "+5 daño de espada",       "type": "w_damage",   "value": 5},
        # 10% más rápida (era 15% — con stacks se vuelve trivial)
        {"id": "sword_cd",   "weapon": "espada", "name": "Estocada Rapida", "desc": "Espada 10% más rápida",    "type": "w_cooldown", "value": 0.90},
    ],
    "varita": [
        # +8 daño (era +5; la varita hace 10 base, 5 era irrelevante)
        {"id": "wand_dmg",    "weapon": "varita", "name": "Magia Potente",   "desc": "+8 daño de varita",         "type": "w_damage",     "value": 8},
        # 10% más rápida (era 15% — se stackeaba demasiado bien)
        {"id": "wand_cd",     "weapon": "varita", "name": "Cadencia Arcana", "desc": "Varita 10% más rápida",     "type": "w_cooldown",   "value": 0.90},
        # +1 daño/tick de quemadura (era +2; con múltiples burn zones se duplica)
        {"id": "burn_dmg",    "weapon": "varita", "name": "Llama Voraz",     "desc": "+10 daño de quemadura/tick", "type": "w_burn_dmg",   "value": 10},
        # +10 radio (era +15 — hacía que todas las zonas se solaparan trivialmente)
        {"id": "burn_rad",    "weapon": "varita", "name": "Hoguera",         "desc": "+10 radio de quemadura",    "type": "w_burn_rad",   "value": 10},
    ],
    "banana": [
        # +8 daño (era +5; banana hace 10 base, era irrelevante)
        {"id": "ban_dmg",   "weapon": "banana", "name": "Banana Madura",   "desc": "+8 daño de banana",          "type": "w_damage",   "value": 8},
        # 10% más rápida (era 15%)
        {"id": "ban_cd",    "weapon": "banana", "name": "Manos de Mono",   "desc": "Banana 10% más rápida",      "type": "w_cooldown", "value": 0.90},
        # +1 fragmento (sin cambio, ya es moderado)
        {"id": "ban_frags", "weapon": "banana", "name": "Racimo",          "desc": "+1 fragmento al impactar",   "type": "w_frags",    "value": 1},
    ],
}

def load_sprite(path, size, fallback_color, remove_bg=True):
    """Carga una imagen y la escala. Preserva transparencia alfa correctamente."""
    if os.path.exists(path):
        image = pygame.image.load(path).convert_alpha()
        # Solo usar colorkey si la imagen NO tiene canal alfa real
        # (imágenes con alfa propio ya tienen transparencia sin necesitar colorkey)
        if remove_bg:
            # Comprobar si el pixel (0,0) tiene alfa = 255 (sin transparencia propia)
            # Solo en ese caso aplicar colorkey para quitar el fondo de color sólido
            px = image.get_at((0, 0))
            if px.a == 255:
                image.set_colorkey((px.r, px.g, px.b))
        scaled = pygame.Surface(size, pygame.SRCALPHA)
        tmp = pygame.transform.scale(image, size)
        scaled.blit(tmp, (0, 0))
        return scaled
    else:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((*fallback_color, 255))
        return surf