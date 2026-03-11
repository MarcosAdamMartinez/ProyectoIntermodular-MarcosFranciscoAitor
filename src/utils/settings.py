import pygame
import os

# Pantalla
WIDTH = 980
HEIGHT = 520
FPS = 60

# Colores
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Jugador base
PLAYER_SIZE = 80

# --- DATOS DE PERSONAJES ---
CHARACTERS = {
    "caballero": {
        "speed": 4,
        "hp": 150,
        "color": BLUE,
        "sprite": "assets/sprites/knight.png",
        "starting_weapon": "espada"
    },
    "mago": {
        "speed": 6,
        "hp": 80,
        "color": (150, 0, 255),
        "sprite": "assets/sprites/mage.png",
        "starting_weapon": "varita"
    }
}

# --- DATOS DE ARMAS ---
WEAPONS = {
    "espada": {"cooldown": 60, "damage": 25, "speed": 0.5, "color": WHITE, "type": "melee"},
    "varita": {"cooldown": 45, "damage": 10, "speed": 10, "color": YELLOW, "type": "ranged"}
}


def load_sprite(path, size, fallback_color, remove_bg=True):
    """Carga una imagen, quita el fondo si se pide, o devuelve un cuadrado si no existe."""
    if os.path.exists(path):
        image = pygame.image.load(path).convert_alpha()

        # Solo borramos el fondo si remove_bg es True
        if remove_bg:
            background_color = image.get_at((0, 0))
            image.set_colorkey(background_color)

        return pygame.transform.scale(image, size)
    else:
        surf = pygame.Surface(size)
        surf.fill(fallback_color)
        return surf